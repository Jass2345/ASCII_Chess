from __future__ import annotations

def is_admin():
    """Check if the script is running with administrator privileges"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """Rerun the script with administrator privileges"""
    import sys
    import ctypes
    
    if not is_admin():
        print("관리자 권한이 필요합니다. 권한을 요청합니다...")
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit(0)

# 관리자 권한 확인 및 요청
run_as_admin()

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

def check_and_install_package(package_name):
    # python-chess의 실제 임포트 이름은 'chess'이므로 처리
    import_name = package_name.replace('-', '_')
    if package_name == "python-chess":
        import_name = "chess"
    
    try:
        __import__(import_name)
        print(f"✓ {package_name} 패키지가 이미 설치되어 있습니다.")
        return True
    except ImportError:
        print(f"{package_name} 패키지가 설치되어 있지 않아 설치를 시도합니다...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            print(f"✓ {package_name} 패키지 설치 완료")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ {package_name} 패키지 설치 실패: {e}")
            return False

def install_font():
    font_name = "menlo-regular.ttf"
    # 폰트 경로를 ascii_chess/fonts/로 수정
    font_path = os.path.join("ascii_chess", "fonts", font_name)
    
    # 상대 경로로도 시도 (이전 버전과의 호환성을 위해)
    if not os.path.exists(font_path):
        font_path = os.path.join("fonts", font_name)
    
    if not os.path.exists(font_path):
        print(f"✗ {font_path} 파일을 찾을 수 없습니다.")
        return False
        
    if platform.system() == "Windows":
        try:
            import ctypes
            import winreg
            
            font_dir = os.path.join(os.environ['WINDIR'], 'Fonts')
            target_path = os.path.join(font_dir, font_name)
            
            if os.path.exists(target_path):
                print(f"✓ {font_name} 폰트가 이미 설치되어 있습니다.")
                return True
                
            shutil.copy2(font_path, font_dir)
            
            # 폰트 등록
            if not ctypes.windll.gdi32.AddFontResourceW(target_path):
                print("✗ 폰트 등록에 실패했습니다.")
                return False
                
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x001D, 0, 0)
            
            # 레지스트리에 등록
            try:
                key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, 
                                     r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts')
                winreg.SetValueEx(key, font_name, 0, winreg.REG_SZ, font_name)
                winreg.CloseKey(key)
            except WindowsError as e:
                print(f"✗ 레지스트리 등록 실패: {e}")
                return False
                
            print(f"✓ {font_name} 폰트가 성공적으로 설치되었습니다.")
            return True
            
        except Exception as e:
            print(f"✗ 폰트 설치 중 오류 발생: {e}")
            return False
            
    elif platform.system() == "Darwin":  # macOS
        try:
            font_dir = os.path.expanduser("~/Library/Fonts")
            os.makedirs(font_dir, exist_ok=True)
            target_path = os.path.join(font_dir, font_name)
            
            if os.path.exists(target_path):
                print(f"✓ {font_name} 폰트가 이미 설치되어 있습니다.")
                return True
                
            shutil.copy2(font_path, target_path)
            print(f"✓ {font_name} 폰트가 성공적으로 설치되었습니다.")
            print("※ 일부 프로그램의 경우 재시작 후에 폰트가 적용될 수 있습니다.")
            return True
            
        except Exception as e:
            print(f"✗ 폰트 설치 중 오류 발생: {e}")
            return False
    else:
        print(f"✗ {platform.system()} 시스템은 자동 설치를 지원하지 않습니다.")
        print(f"수동으로 {font_path} 파일을 시스템 폰트 폴더에 복사해주세요.")
        return False

# 필요한 패키지 설치
if not check_and_install_package("python-chess"):
    print("\n필수 패키지 설치에 실패하여 프로그램을 실행할 수 없습니다.")
    if platform.system() == "Windows":
        input("계속하려면 엔터 키를 누르세요...")
    sys.exit(1)

# 폰트 설치 시도 (실패해도 프로그램은 계속 실행)
print("\n필요한 폰트를 확인 중입니다...")
install_font()

from ascii_chess.deps import collect_dependency_status


def parse_args(argv: list[str]) -> argparse.Namespace:
    # 명령줄 인자 정의 및 파싱
    parser = argparse.ArgumentParser(description="ASCII CLI Chess vs Stockfish")
    parser.add_argument(
        "--engine-path",
        help="Path to Stockfish executable (defaults to checking PATH).",
        default=None,
    )
    parser.add_argument(
        "--min-rating",
        type=int,
        default=1350,
        help="Minimum Elo allowed for the AI (default: 1350, Stockfish limit).",
    )
    parser.add_argument(
        "--max-rating",
        type=int,
        default=2850,
        help="Maximum Elo allowed for the AI (default: 2850).",
    )
    parser.add_argument(
        "--think-time",
        type=float,
        default=0.5,
        help="Default thinking time per AI move in seconds (default: 0.5).",
    )
    parser.add_argument(
        "--ascii-only",
        action="store_true",
        help="Force ASCII board rendering instead of Unicode chess glyphs.",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run the classic CLI experience instead of the GUI.",
    )
    parser.add_argument(
        "--no-auto-install",
        action="store_true",
        help="Skip automatic installation attempt for python-chess.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    # 실행 환경 점검 후 CLI 또는 GUI 진입점을 수행
    args = parse_args(argv or sys.argv[1:])

    deps = collect_dependency_status(
        engine_path=args.engine_path,
        auto_install=not args.no_auto_install,
    )

    if not deps.python_chess_ok:
        print(
            "python-chess could not be imported. "
            "Install it manually with `pip install python-chess` and re-run.",
            file=sys.stderr,
        )
        return 1

    if deps.stockfish_path is None:
        hint = (
            "Stockfish executable not found. Download it from "
            "https://stockfishchess.org/download/ and provide the path with "
            "--engine-path /path/to/stockfish."
        )
        print(hint, file=sys.stderr)
        return 1

    from ascii_chess.ai import EngineConfig
    from ascii_chess.game import GameController
    from ascii_chess.renderer import AsciiRenderer

    engine_config = EngineConfig(
        executable_path=deps.stockfish_path,
        min_rating=args.min_rating,
        max_rating=args.max_rating,
        default_think_time=args.think_time,
    )

    if args.cli:
        renderer = AsciiRenderer(use_unicode=not args.ascii_only)
        try:
            controller = GameController(renderer=renderer, engine_config=engine_config)
        except RuntimeError as exc:
            print(f"Failed to initialise game: {exc}", file=sys.stderr)
            return 1
        controller.run()
        return 0

    try:
        import tkinter as tk
    except Exception as exc:  # pragma: no cover - Tk may be missing
        print(f"Failed to load Tkinter: {exc}", file=sys.stderr)
        return 1

    from ascii_chess.gui import ChessGUI

    root = tk.Tk()
    ChessGUI(root, engine_config=engine_config, use_unicode=not args.ascii_only)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
