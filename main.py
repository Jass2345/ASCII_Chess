from __future__ import annotations
import platform

def is_admin():
    """Check if the script is running with administrator privileges (Windows only)"""
    if platform.system() != "Windows":
        return True  # macOS/Linux에서는 항상 True 반환
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# Windows에서만 관리자 권한 확인 및 요청
if platform.system() == "Windows" and not is_admin():
    import sys
    import ctypes
    
    # 현재 스크립트의 절대 경로 가져오기
    import os
    script = os.path.abspath(sys.argv[0])
    
    print("폰트 설치를 위해 관리자 권한이 필요합니다. 권한을 요청합니다...")
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}"', None, 1)
    sys.exit(0)

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
    if platform.system() == "Windows":
        font_name = "menlo-regular.ttf"
        # 폰트 경로 확인
        font_path = os.path.join("ascii_chess", "fonts", font_name)
        if not os.path.exists(font_path):
            font_path = os.path.join("fonts", font_name)
        
        if not os.path.exists(font_path):
            print(f"✗ {font_path} 파일을 찾을 수 없습니다.")
            return False
            
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
        print("✓ macOS는 기본적으로 Menlo 폰트가 설치되어 있습니다.")
        return True
    
    else:
        print(f"✗ {platform.system()} 시스템은 자동 설치를 지원하지 않습니다.")
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
    parser = argparse.ArgumentParser(description="ASCII Chess GUI vs Stockfish")
    parser.add_argument("--engine-path", default=None, help="Path to Stockfish executable.")
    parser.add_argument("--min-rating", type=int, default=1350, help="Minimum Stockfish Elo.")
    parser.add_argument("--max-rating", type=int, default=2850, help="Maximum Stockfish Elo.")
    parser.add_argument("--think-time", type=float, default=0.5, help="Default think time per AI move.")
    parser.add_argument("--ascii-only", action="store_true", help="Use ASCII pieces instead of Unicode.")
    parser.add_argument("--no-auto-install", action="store_true", help="Skip python-chess auto-installation.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    deps = collect_dependency_status(
        engine_path=args.engine_path,
        auto_install=not args.no_auto_install,
    )

    if not deps.python_chess_ok:
        print(
            "python-chess could not be imported. Install it manually with `pip install python-chess` and re-run.",
            file=sys.stderr,
        )
        return 1

    if deps.stockfish_path is None:
        hint = (
            "Stockfish executable not found. Download it from https://stockfishchess.org/download/ "
            "and provide the path with --engine-path /path/to/stockfish."
        )
        print(hint, file=sys.stderr)
        return 1

    try:
        import tkinter as tk
    except Exception as exc:
        print(f"Failed to load Tkinter: {exc}", file=sys.stderr)
        return 1

    from ascii_chess.ai import EngineConfig
    from ascii_chess.gui import ChessGUI

    engine_config = EngineConfig(
        executable_path=deps.stockfish_path,
        min_rating=args.min_rating,
        max_rating=args.max_rating,
        default_think_time=args.think_time,
    )

    root = tk.Tk()
    ChessGUI(root, engine_config=engine_config, use_unicode=not args.ascii_only)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
