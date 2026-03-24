"""
Nuitka 打包脚本 - 自动表单填写工具
将 Python 源码编译为 C 代码再编译为原生二进制，实现代码混淆和保护
支持 macOS (Intel/ARM) 和 Windows
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path


APP_NAME = "自动表单填写工具"
ENTRY_POINT = "main.py"

INCLUDE_PACKAGES = [
    "core",
    "gui",
    "database",
    "PyQt6",
    "requests",
    "charset_normalizer",
    "chardet",
    "pymongo",
    "mongoengine",
    "dns",
    "certifi",
    "Crypto",
    "jwt",
    "openpyxl",
    "dateutil",
]

INCLUDE_MODULES = [
    "config",
    "PyQt6.sip",
    "dns.resolver",
    "dns.rdatatype",
    "dns.nameserver",
    "Crypto.Cipher",
    "Crypto.Cipher.AES",
    "Crypto.Util.Padding",
]

NOFOLLOW_IMPORTS = [
    "tools",
    "scripts",
    "setuptools",
    "pip",
    "wheel",
    "pytest",
    "unittest",
    "fastapi",
    "uvicorn",
]


def clean_build():
    """清理旧的构建文件"""
    print("清理旧的构建文件...")
    patterns = ["*.build", "*.dist", "*.onefile-build", "*.app", "build", "dist"]
    for pattern in patterns:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                shutil.rmtree(path)
                print(f"  删除目录: {path}")
            elif path.is_file():
                path.unlink()
                print(f"  删除文件: {path}")

    for spec_file in Path(".").glob("*.spec"):
        spec_file.unlink()
        print(f"  删除: {spec_file}")
    print("清理完成\n")


def check_nuitka():
    """检查并安装 Nuitka"""
    print("检查 Nuitka 环境...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "nuitka", "--version"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            version = result.stdout.strip().split("\n")[0]
            print(f"Nuitka 已安装: {version}\n")
            return True
    except Exception:
        pass

    print("Nuitka 未安装，正在安装...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "nuitka", "ordered-set", "zstandard"],
        check=True,
    )
    print("Nuitka 安装完成\n")
    return True


def build_nuitka_cmd():
    """构建 Nuitka 命令行参数"""
    is_mac = sys.platform == "darwin"
    is_windows = sys.platform == "win32"

    if is_windows:
        mode = "--onefile"
    else:
        mode = "--standalone"

    cmd = [
        sys.executable, "-m", "nuitka",
        mode,
        "--enable-plugin=pyqt6",
        "--assume-yes-for-downloads",
        "--remove-output",
        "--output-dir=dist",
    ]

    for pkg in INCLUDE_PACKAGES:
        cmd.append(f"--include-package={pkg}")

    for mod in INCLUDE_MODULES:
        cmd.append(f"--include-module={mod}")

    for no_follow in NOFOLLOW_IMPORTS:
        cmd.append(f"--nofollow-import-to={no_follow}")

    if is_mac:
        print("检测到 macOS 系统 (standalone + app bundle)")
        cmd.extend([
            "--macos-create-app-bundle",
            f"--macos-app-name={APP_NAME}",
        ])
        icns = Path("app_icon.icns")
        if icns.exists():
            cmd.append(f"--macos-app-icon={icns}")
            print(f"  使用图标: {icns}")

    elif is_windows:
        print("检测到 Windows 系统 (onefile 单 exe)")
        cmd.extend([
            "--windows-disable-console",
            f"--output-filename={APP_NAME}.exe",
        ])
        ico = Path("app_icon.ico")
        if ico.exists():
            cmd.append(f"--windows-icon-from-ico={ico}")
            print(f"  使用图标: {ico}")

    cmd.append(ENTRY_POINT)
    return cmd


def build_app():
    """执行 Nuitka 打包"""
    print("开始 Nuitka 编译打包 (这可能需要较长时间)...\n")

    cmd = build_nuitka_cmd()
    print(f"执行命令:\n  {' '.join(cmd)}\n")

    try:
        subprocess.run(cmd, check=True)
        print("\nNuitka 编译完成!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n编译失败: {e}")
        return False


def post_build():
    """编译后处理: 重命名输出"""
    dist_dir = Path("dist")
    is_windows = sys.platform == "win32"

    # Windows onefile: 直接输出单个 exe，无需处理
    if is_windows:
        exe = dist_dir / f"{APP_NAME}.exe"
        if exe.exists():
            print(f"Windows 单文件: {exe}")
            print(f"  文件大小: {exe.stat().st_size / 1024 / 1024:.1f} MB")
            return
        # fallback: 检查默认名称
        fallback = dist_dir / "main.exe"
        if fallback.exists():
            target = dist_dir / f"{APP_NAME}.exe"
            fallback.rename(target)
            print(f"Windows 单文件: {target}")
            return

    # macOS app bundle
    app_bundle = dist_dir / "main.app"
    if app_bundle.exists():
        target = dist_dir / f"{APP_NAME}.app"
        if target.exists():
            shutil.rmtree(target)
        app_bundle.rename(target)
        print(f"macOS 应用包: {target}")
        return

    # Linux / macOS standalone 目录
    main_dist = dist_dir / "main.dist"
    if main_dist.exists():
        target = dist_dir / APP_NAME
        if target.exists():
            shutil.rmtree(target)
        main_dist.rename(target)

        binary = target / "main"
        if binary.exists():
            new_binary = target / APP_NAME
            binary.rename(new_binary)
            print(f"可执行文件: {new_binary}")

        print(f"输出目录: {target}")


def main():
    is_windows = sys.platform == "win32"

    print("=" * 60)
    print(f"  Nuitka 打包 - {APP_NAME}")
    print(f"  Python 源码 -> C 代码 -> 原生二进制 (代码混淆保护)")
    if is_windows:
        print(f"  模式: onefile (单个 .exe)")
    else:
        print(f"  模式: standalone (应用包)")
    print("=" * 60)
    print()

    clean_build()

    if not check_nuitka():
        return

    if not build_app():
        return

    post_build()

    print("\n" + "=" * 60)
    print("  打包完成!")
    print("=" * 60)
    if is_windows:
        print(f"\n输出文件: dist/{APP_NAME}.exe")
    else:
        print(f"\n输出位置: dist/{APP_NAME}.app 或 dist/{APP_NAME}/")
    print()
    print("Nuitka 编译优势:")
    print("  1. Python 源码已编译为原生机器码，无法反编译为 .py")
    print("  2. 不含 .pyc 字节码文件，逆向难度极高")
    print("  3. 运行性能优于 PyInstaller 打包方式")
    print()


if __name__ == "__main__":
    main()
