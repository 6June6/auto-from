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
from core.logger import get_logger, setup_exception_hook, setup_qt_exception_hook


def main():
    """主函数"""
    # 🛡️ 初始化日志系统 (必须在最开始)
    logger = get_logger()
    logger.log_info("="*60)
    logger.log_info(f"🚀 {config.APP_NAME} v{config.APP_VERSION} 启动")
    logger.log_info(f"📂 日志目录: {logger.get_log_dir()}")
    logger.log_info("="*60)
    
    # 用于存储当前登录用户的全局变量
    current_user_info = {'user': None}
    
    def get_current_user_info():
        """获取当前用户信息的回调函数"""
        if current_user_info['user']:
            try:
                return {
                    'username': current_user_info['user'].username,
                    'user_id': str(current_user_info['user'].id),
                    'device_id': current_user_info['user'].device_id if hasattr(current_user_info['user'], 'device_id') else 'Unknown',
                    'role': 'admin' if current_user_info['user'].is_admin() else 'user'
                }
            except Exception as e:
                logger.log_error(f"获取用户信息失败: {e}")
        return None
    
    # 🛡️ 设置全局异常钩子
    setup_exception_hook(user_info_callback=get_current_user_info)
    
    # 🛡️ 设置 Qt 异常钩子
    setup_qt_exception_hook()
    
    try:
        # ⚡️ 强制开启 GPU 加速配置 (必须在 QApplication 创建前设置)
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
            "--ignore-gpu-blocklist "
            "--enable-gpu-rasterization "
            "--enable-zero-copy "
            "--enable-accelerated-video-decode "
            "--enable-features=VaapiVideoDecoder,CanvasOopRasterization"
        )
        
        # 初始化数据库连接
        logger.log_info("🔧 初始化 MongoDB 数据库...")
        print("🔧 初始化 MongoDB 数据库...")
        
        if not init_database():
            error_msg = "数据库连接失败"
            logger.log_error(error_msg)
            print(f"❌ {error_msg}，程序退出")
            
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
        
        logger.log_info("✅ 数据库初始化完成")
        print("✅ 数据库初始化完成")
        
    except Exception as e:
        logger.log_error(f"初始化阶段异常: {e}", exc_info=True)
        raise
    
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
        
        # 更新当前用户信息
        current_user_info['user'] = user
        
        # 记录登录成功
        user_info = get_current_user_info()
        logger.log_info("✅ 用户登录成功", user_info=user_info)
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
        user_info = get_current_user_info()
        
        try:
            # 根据用户角色创建不同的窗口
            if user.is_admin():
                logger.log_info("📊 启动管理后台界面...", user_info=user_info)
                print("📊 启动管理后台界面...")
                main_window = AdminMainWindow(current_user=user)
            else:
                logger.log_info("📝 启动表单填写界面...", user_info=user_info)
                print("📝 启动表单填写界面...")
                main_window = MainWindow(current_user=user)
            
            # 将窗口保存到应用程序对象，防止被垃圾回收
            app._main_window = main_window
            
            # 显示主窗口
            main_window.show()
            logger.log_info("✅ 主窗口创建并显示成功", user_info=user_info)
            
        except Exception as e:
            error_msg = f"创建主窗口失败: {e}"
            logger.log_error(error_msg, exc_info=True, user_info=user_info)
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            
            # 显示错误对话框
            QMessageBox.critical(
                None,
                "启动失败",
                f"创建主窗口时发生错误:\n\n{str(e)}\n\n"
                f"详细日志已保存到:\n{logger.get_log_dir()}"
            )
    
    login_window = LoginWindow()
    login_window.login_success.connect(on_login_success)
    
    result = login_window.exec()
    
    if result != 1:  # 1 表示 Accepted
        # 用户取消登录
        logger.log_info("❌ 用户取消登录，程序退出")
        print("❌ 用户取消登录，程序退出")
        sys.exit(0)
    
    # 登录窗口关闭后，创建主窗口
    # 这样用户不会看到卡在"正在加载主界面"
    create_main_window()
    
    # 检查主窗口是否已创建
    if not main_window:
        logger.log_error("❌ 主窗口创建失败，程序退出")
        print("❌ 主窗口创建失败，程序退出")
        sys.exit(1)
    
    # 运行应用
    logger.log_info("🎯 应用程序进入主循环")
    exit_code = app.exec()
    logger.log_info(f"👋 应用程序正常退出 (exit_code: {exit_code})")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

