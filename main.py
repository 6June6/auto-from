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
import config


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
    
    # 用于存储主窗口的变量
    main_window = None
    pending_user = None  # 待处理的用户
    
    def on_login_success(user):
        """登录成功回调 - 先关闭登录窗口，再创建主窗口"""
        nonlocal pending_user
        pending_user = user
        print(f"✅ 用户 {user.username} 登录成功")
        
        # 立即关闭登录窗口，不等待主窗口创建
        # 这样用户不会看到卡在"正在加载主界面"
        login_window.close_after_ready()
    
    def create_main_window():
        """登录窗口关闭后创建主窗口"""
        nonlocal main_window, pending_user
        
        if not pending_user:
            return
        
        user = pending_user
        
        try:
            # 根据用户角色创建不同的窗口
            if user.is_admin():
                print("📊 启动管理后台界面...")
                main_window = AdminMainWindow(current_user=user)
            else:
                print("📝 启动表单填写界面...")
                main_window = MainWindow(current_user=user)
            
            # 将窗口保存到应用程序对象，防止被垃圾回收
            app._main_window = main_window
            
            # 显示主窗口
            main_window.show()
            
        except Exception as e:
            print(f"❌ 创建主窗口失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 显示登录窗口（会自动检测并尝试自动登录）
    login_window = LoginWindow(auto_login=True)
    login_window.login_success.connect(on_login_success)
    
    result = login_window.exec()
    
    if result != 1:  # 1 表示 Accepted
        # 用户取消登录
        print("❌ 用户取消登录，程序退出")
        sys.exit(0)
    
    # 登录窗口关闭后，创建主窗口
    # 这样用户不会看到卡在"正在加载主界面"
    create_main_window()
    
    # 检查主窗口是否已创建
    if not main_window:
        print("❌ 主窗口创建失败，程序退出")
        sys.exit(1)
    
    # 运行应用
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

