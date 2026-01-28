"""
打包脚本 - 自动表单填写工具
支持 macOS 和 Windows
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

def clean_build():
    """清理构建目录"""
    print("🧹 清理旧的构建文件...")
    dirs_to_remove = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"  删除: {dir_name}")
    
    # 删除 .spec 文件
    for spec_file in Path('.').glob('*.spec'):
        spec_file.unlink()
        print(f"  删除: {spec_file}")
    print("✅ 清理完成\n")

def install_pyinstaller():
    """安装 PyInstaller"""
    print("📦 检查 PyInstaller...")
    try:
        import PyInstaller
        print("✅ PyInstaller 已安装\n")
        return True
    except ImportError:
        print("⚠️  PyInstaller 未安装，正在安装...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("✅ PyInstaller 安装完成\n")
        return True

def build_app():
    """打包应用"""
    print("🚀 开始打包应用...\n")
    
    # 获取当前操作系统
    is_mac = sys.platform == 'darwin'
    is_windows = sys.platform == 'win32'
    
    # 基础打包命令
    cmd = [
        'pyinstaller',
        '--name=自动表单填写工具',
        '--windowed',  # 不显示控制台窗口
        '--onedir',    # 打包成目录（比 onefile 启动更快）
        '--clean',     # 清理临时文件
        'main.py'
    ]
    
    # macOS 特定配置
    if is_mac:
        print("🍎 检测到 macOS 系统")
        cmd.extend([
            '--osx-bundle-identifier=com.autofill.app',
        ])
    
    # Windows 特定配置
    elif is_windows:
        print("🪟 检测到 Windows 系统")
        # 可以后续添加图标: --icon=icon.ico
        pass
    
    # 添加数据文件
    # cmd.extend(['--add-data', 'data:data'])  # 如果需要打包数据库
    
    print(f"📝 执行命令: {' '.join(cmd)}\n")
    
    try:
        subprocess.run(cmd, check=True)
        print("\n✅ 打包成功！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 打包失败: {e}")
        return False

def create_readme():
    """创建使用说明"""
    readme_content = """
# 自动表单填写工具 - 使用说明

## 📦 安装包内容

- 主程序：自动表单填写工具
- 依赖库：已全部打包，无需额外安装

## 🚀 使用方法

### macOS:
1. 打开 `dist/自动表单填写工具` 文件夹
2. 双击运行 `自动表单填写工具` 应用
3. 如果提示"无法打开"，请在系统偏好设置 > 安全性与隐私 中允许运行

### Windows:
1. 打开 `dist/自动表单填写工具` 文件夹
2. 双击运行 `自动表单填写工具.exe`
3. 如果 Windows Defender 提示，点击"更多信息">"仍要运行"

## 📝 首次使用

1. 程序使用云端 MongoDB 数据库，无需本地配置
2. 首次运行请使用管理员账号登录
3. 登录后可管理名片和表单链接

## ⚙️ 功能说明

- **自动填写**: 选择名片和链接后自动填写表单
- **名片管理**: 管理填写配置模板
- **链接管理**: 管理常用表单链接
- **诊断页面**: 查看页面结构和输入框信息
- **用户管理**: (管理员) 管理用户和权限

## ⚠️ 注意事项

1. 确保网络连接正常，程序需要连接云端数据库
2. 部分网站可能有反爬虫机制
3. 建议先用测试链接测试功能

## 🐛 问题反馈

如有问题请联系开发者
"""
    
    with open('dist/README.txt', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print("\n📄 已创建 README.txt")

def main():
    """主函数"""
    print("="*60)
    print("  🚀 自动表单填写工具 - 打包程序")
    print("="*60)
    print()
    
    # 1. 清理旧文件
    clean_build()
    
    # 2. 安装 PyInstaller
    if not install_pyinstaller():
        return
    
    # 3. 打包应用
    if not build_app():
        return
    
    # 4. 创建说明文档
    create_readme()
    
    print("\n" + "="*60)
    print("  ✅ 打包完成！")
    print("="*60)
    print(f"\n📁 打包文件位置: dist/自动表单填写工具/")
    print()
    print("📌 下一步:")
    print("  1. 测试运行 dist/自动表单填写工具/ 中的应用")
    print("  2. 如需分发，压缩整个文件夹")
    print("  3. 可以重命名文件夹或添加版本号")
    print()

if __name__ == "__main__":
    main()

