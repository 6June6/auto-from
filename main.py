"""
自动表单填写工具
主程序入口
MongoDB 版本
"""
import sys
import os  # 添加 os 导入
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from database import init_database
from gui import MainWindow
from gui.login_window import LoginWindow
from gui.admin_main_window import AdminMainWindow
from core.auth import login_with_token
import config


def try_auto_login():
    """尝试使用保存的 token 自动登录"""
    try:
        # 读取保存的 token
        auth_dir = Path.home() / '.auto-form-filler'
        token_file = auth_dir / '.token'
        
        if not token_file.exists():
            print("ℹ️ 未找到保存的登录信息，需要手动登录")
            return None
        
        token = token_file.read_text().strip()
        if not token:
            print("ℹ️ Token 为空，需要手动登录")
            return None
        
        print("🔐 尝试自动登录...")
        success, message, user = login_with_token(token)
        
        if success:
            print(f"✅ 自动登录成功: {user.username}")
            return user
        else:
            print(f"ℹ️ 自动登录失败: {message}")
            # 删除无效的 token
            try:
                token_file.unlink()
            except:
                pass
            return None
            
    except Exception as e:
        print(f"⚠️ 自动登录异常: {e}")
        return None


def main():
    """主函数"""
    # ⚡️ 强制开启 GPU 加速配置 (必须在 QApplication 创建前设置)
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
        "--ignore-gpu-blocklist "
        "--enable-gpu-rasterization "
        "--enable-zero-copy "
        "--enable-accelerated-video-decode "
        "--enable-features=VaapiVideoDecoder,CanvasOopRasterization"
    )
    
    # 初始化数据库连接
    print("🔧 初始化 MongoDB 数据库...")
    if not init_database():
        print("❌ 数据库连接失败，程序退出")
        # 显示错误对话框
        app = QApplication(sys.argv)
        QMessageBox.critical(
            None,
            "数据库连接失败",
            f"无法连接到 MongoDB 数据库。\n\n"
            f"请检查:\n"
            f"1. MongoDB 服务是否正常运行\n"
            f"2. 网络连接是否正常\n"
            f"3. config.py 中的连接字符串是否正确\n\n"
            f"数据库: {config.MONGODB_DB_NAME}"
        )
        sys.exit(1)
    
    print("✅ 数据库初始化完成")
    
    # ⚡️ 开启 OpenGL 上下文共享 (优化 WebEngine 渲染)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    
    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)
    
    # 设置高 DPI 支持（PyQt6 默认启用，无需手动设置）
    # app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    
    # 尝试自动登录
    current_user = try_auto_login()
    
    if not current_user:
        # 自动登录失败，显示登录窗口
        login_window = LoginWindow()
        result = login_window.exec()
        if result != 1:  # 1 表示 Accepted
            # 用户取消登录
            print("❌ 用户取消登录，程序退出")
            sys.exit(0)
        
        # 获取登录用户
        current_user = login_window.get_current_user()
        if not current_user:
            print("❌ 未获取到登录用户，程序退出")
            sys.exit(1)
        
        print(f"✅ 用户 {current_user.username} 登录成功")
    else:
        print(f"✅ 用户 {current_user.username} 自动登录成功")
    
    # 根据用户角色显示不同的窗口
    if current_user.is_admin():
        # 管理员：显示管理后台界面
        print("📊 启动管理后台界面...")
        window = AdminMainWindow(current_user=current_user)
    else:
        # 普通用户：显示表单填写界面
        print("📝 启动表单填写界面...")
        window = MainWindow(current_user=current_user)
    
    # 将窗口保存到应用程序对象，防止被垃圾回收
    app._main_window = window
    window.show()
    
    # 运行应用
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

