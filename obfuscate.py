#!/usr/bin/env python3
"""
代码混淆打包脚本
使用 PyArmor 进行代码混淆，然后用 PyInstaller 打包
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent

# 需要混淆的核心模块
CORE_MODULES = [
    'config.py',
    'config_secure.py',
    'core/',
    'database/',
]

# 不需要混淆的文件
EXCLUDE_FILES = [
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '*.bak',
    'test_*.py',
    'debug_*.py',
    'demo_*.py',
]

# 输出目录
DIST_DIR = BASE_DIR / 'dist'
OBFUSCATED_DIR = BASE_DIR / 'dist_obfuscated'


def check_pyarmor():
    """检查 PyArmor 是否安装"""
    try:
        result = subprocess.run(['pyarmor', '--version'], capture_output=True, text=True)
        print(f"✅ PyArmor 版本: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("❌ PyArmor 未安装，请运行: pip install pyarmor")
        return False


def check_nuitka():
    """检查 Nuitka 是否安装"""
    try:
        result = subprocess.run([sys.executable, '-m', 'nuitka', '--version'], capture_output=True, text=True)
        print(f"✅ Nuitka 可用")
        return True
    except:
        print("⚠️ Nuitka 未安装，可选运行: pip install nuitka")
        return False


def generate_encrypted_config():
    """生成加密配置"""
    print("\n📦 生成加密配置...")
    
    # 检查是否已存在加密配置
    secure_config_path = BASE_DIR / '.secure_config'
    if secure_config_path.exists():
        print("✅ 加密配置已存在")
        return True
    
    # 运行加密生成
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'core.crypto'],
            cwd=BASE_DIR,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.returncode == 0:
            print("✅ 加密配置生成成功")
            return True
        else:
            print(f"❌ 生成失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 生成加密配置失败: {e}")
        return False


def obfuscate_with_pyarmor():
    """使用 PyArmor 混淆代码"""
    print("\n🔒 使用 PyArmor 混淆代码...")
    
    if not check_pyarmor():
        return False
    
    # 清理旧的混淆目录
    if OBFUSCATED_DIR.exists():
        shutil.rmtree(OBFUSCATED_DIR)
    OBFUSCATED_DIR.mkdir(parents=True)
    
    try:
        # PyArmor 8.x 语法
        # 混淆整个项目
        cmd = [
            'pyarmor', 'gen',
            '--output', str(OBFUSCATED_DIR),
            '--recursive',
            '--obf-module', '1',  # 模块级混淆
            '--obf-code', '1',    # 代码级混淆
            '--assert-call',      # 断言调用保护
            '--assert-import',    # 断言导入保护
            'main.py',
        ]
        
        print(f"执行: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
        
        if result.returncode != 0:
            # 尝试 PyArmor 7.x 语法
            print("⚠️ PyArmor 8.x 命令失败，尝试 7.x 语法...")
            cmd = [
                'pyarmor', 'obfuscate',
                '--output', str(OBFUSCATED_DIR),
                '--recursive',
                '--bootstrap', '2',
                'main.py',
            ]
            result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ PyArmor 混淆成功")
            return True
        else:
            print(f"❌ PyArmor 混淆失败")
            return False
            
    except Exception as e:
        print(f"❌ PyArmor 混淆出错: {e}")
        return False


def copy_resources():
    """复制资源文件到混淆目录"""
    print("\n📁 复制资源文件...")
    
    # 需要复制的非 Python 文件
    resources = [
        '.secure_config',
        'requirements.txt',
    ]
    
    for res in resources:
        src = BASE_DIR / res
        dst = OBFUSCATED_DIR / res
        if src.exists():
            if src.is_file():
                shutil.copy2(src, dst)
            else:
                shutil.copytree(src, dst)
            print(f"  ✅ 复制 {res}")
    
    print("✅ 资源文件复制完成")


def build_with_pyinstaller():
    """使用 PyInstaller 打包混淆后的代码"""
    print("\n📦 使用 PyInstaller 打包...")
    
    # 检查混淆目录
    obf_main = OBFUSCATED_DIR / 'main.py'
    if not obf_main.exists():
        print("❌ 混淆后的 main.py 不存在")
        return False
    
    try:
        cmd = [
            sys.executable, '-m', 'PyInstaller',
            '--name', '自动表单填写工具',
            '--windowed',
            '--onefile',
            '--clean',
            '--noconfirm',
            '--add-data', f'{OBFUSCATED_DIR / ".secure_config"}:.',
            str(obf_main),
        ]
        
        # macOS 特定选项
        if sys.platform == 'darwin':
            cmd.extend(['--osx-bundle-identifier', 'com.autoform.filler'])
        
        print(f"执行: {' '.join(cmd[:5])}...")
        result = subprocess.run(cmd, cwd=OBFUSCATED_DIR, capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ PyInstaller 打包成功")
            return True
        else:
            print(f"❌ PyInstaller 打包失败")
            return False
            
    except Exception as e:
        print(f"❌ PyInstaller 打包出错: {e}")
        return False


def simple_obfuscate():
    """简单混淆方案（不依赖 PyArmor）"""
    print("\n🔒 使用简单混淆方案...")
    
    # 使用 compile 生成 .pyc 文件
    import py_compile
    import compileall
    
    if OBFUSCATED_DIR.exists():
        shutil.rmtree(OBFUSCATED_DIR)
    
    # 复制整个项目
    shutil.copytree(
        BASE_DIR,
        OBFUSCATED_DIR,
        ignore=shutil.ignore_patterns(
            '__pycache__', '*.pyc', '*.pyo', '.git', '.gitignore',
            'dist', 'build', '*.spec', 'dist_obfuscated',
            'test_*.py', 'debug_*.py', 'demo_*.py', '*.bak',
            '*.md', 'website', '.github'
        )
    )
    
    # 编译所有 Python 文件
    print("  编译 Python 文件...")
    compileall.compile_dir(OBFUSCATED_DIR, force=True, quiet=1)
    
    # 删除源文件，只保留 .pyc
    # 注意：这种方式保护较弱，但简单易用
    print("  清理源文件...")
    for py_file in OBFUSCATED_DIR.rglob('*.py'):
        # 保留 main.py 用于启动
        if py_file.name != 'main.py':
            pyc_file = py_file.parent / '__pycache__' / f'{py_file.stem}.cpython-{sys.version_info.major}{sys.version_info.minor}.pyc'
            if pyc_file.exists():
                # 移动 .pyc 到原位置
                new_pyc = py_file.with_suffix('.pyc')
                shutil.move(pyc_file, new_pyc)
                py_file.unlink()
    
    print("✅ 简单混淆完成")
    return True


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='代码混淆打包工具')
    parser.add_argument('--mode', choices=['full', 'simple', 'encrypt-only'], 
                       default='full', help='混淆模式')
    parser.add_argument('--no-pack', action='store_true', help='不打包，只混淆')
    args = parser.parse_args()
    
    print("=" * 50)
    print("🔐 代码混淆加固工具")
    print("=" * 50)
    
    # 1. 生成加密配置
    if not generate_encrypted_config():
        print("⚠️ 加密配置生成失败，继续...")
    
    if args.mode == 'encrypt-only':
        print("\n✅ 仅加密配置完成")
        return
    
    # 2. 混淆代码
    if args.mode == 'full':
        if not obfuscate_with_pyarmor():
            print("⚠️ PyArmor 混淆失败，使用简单方案...")
            if not simple_obfuscate():
                print("❌ 混淆失败")
                return
    else:
        if not simple_obfuscate():
            print("❌ 简单混淆失败")
            return
    
    # 3. 复制资源
    copy_resources()
    
    # 4. 打包
    if not args.no_pack:
        build_with_pyinstaller()
    
    print("\n" + "=" * 50)
    print("✅ 混淆加固完成!")
    print(f"   混淆目录: {OBFUSCATED_DIR}")
    print("=" * 50)


if __name__ == '__main__':
    main()
