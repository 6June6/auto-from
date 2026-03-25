"""
自动表单填写工具
主程序入口
MongoDB 版本
"""
import sys
import os
import traceback
import logging
from pathlib import Path
from datetime import datetime

# ============================================================
# 启动引导日志 (Bootstrap Logger)
# 在任何项目模块导入之前就建立，确保最早期的崩溃也能被记录
# ============================================================
_BOOT_LOG_DIR = Path.home() / '.auto-form-filler' / 'logs'
_BOOT_LOG_DIR.mkdir(parents=True, exist_ok=True)
_BOOT_LOG_FILE = _BOOT_LOG_DIR / 'boot.log'

_boot_logger = logging.getLogger('boot')
_boot_logger.setLevel(logging.DEBUG)
_boot_handler = logging.FileHandler(_BOOT_LOG_FILE, encoding='utf-8')
_boot_handler.setFormatter(logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
))
_boot_logger.addHandler(_boot_handler)


def _log(msg, level='info'):
    """写启动日志并同步打印到控制台"""
    getattr(_boot_logger, level)(msg)
    print(msg, flush=True)


def _log_fatal(title, detail):
    """记录致命错误，尝试弹出对话框后退出"""
    _boot_logger.critical(f"{title}\n{detail}")
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(
            None, title,
            f"{detail}\n\n详细日志已保存到:\n{_BOOT_LOG_FILE}"
        )
    except Exception:
        pass
    sys.exit(1)


# ============================================================
# 环境诊断
# ============================================================
_log("=" * 60)
_log(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
_log(f"Python: {sys.version}")
_log(f"平台: {sys.platform}")
_log(f"可执行文件: {sys.executable}")
_log(f"frozen: {getattr(sys, 'frozen', False)}")
if getattr(sys, 'frozen', False):
    _log(f"_MEIPASS: {getattr(sys, '_MEIPASS', 'N/A')}")
_log(f"工作目录: {os.getcwd()}")
_log(f"sys.path[:5]: {sys.path[:5]}")
_log("=" * 60)

# ============================================================
# 逐步导入项目模块，每步都带日志和异常捕获
# ============================================================
_IMPORT_STEPS = [
    ("config",                   "import config"),
    ("PyQt6.QtWidgets",          "from PyQt6.QtWidgets import QApplication, QMessageBox"),
    ("PyQt6.QtCore",             "from PyQt6.QtCore import Qt"),
    ("database",                 "from database import init_database"),
    ("gui.MainWindow",           "from gui import MainWindow"),
    ("gui.login_window",         "from gui.login_window import LoginWindow"),
    ("gui.admin_main_window",    "from gui.admin_main_window import AdminMainWindow"),
    ("core.logger",              "from core.logger import get_logger, setup_exception_hook, setup_qt_exception_hook"),
]

for step_name, step_code in _IMPORT_STEPS:
    try:
        _log(f"导入模块: {step_name} ...")
        exec(step_code, globals())
        _log(f"  OK: {step_name}")
    except Exception as e:
        tb = traceback.format_exc()
        _log(f"  FAILED: {step_name} -> {e}", level='error')
        _log(tb, level='error')
        _log_fatal(
            f"启动失败: 无法加载模块 {step_name}",
            f"错误类型: {type(e).__name__}\n"
            f"错误信息: {e}\n\n"
            f"完整堆栈:\n{tb}"
        )

_log("所有模块导入成功")


def main():
    """主函数"""
    logger = get_logger()
    logger.log_info("=" * 60)
    logger.log_info(f"{config.APP_NAME} v{config.APP_VERSION} 启动")
    logger.log_info(f"日志目录: {logger.get_log_dir()}")
    logger.log_info("=" * 60)

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

    setup_exception_hook(user_info_callback=get_current_user_info)
    setup_qt_exception_hook()

    try:
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
            "--ignore-gpu-blocklist "
            "--enable-gpu-rasterization "
            "--enable-zero-copy "
            "--enable-accelerated-video-decode "
            "--enable-features=VaapiVideoDecoder,CanvasOopRasterization"
        )

        _log("初始化 MongoDB 数据库...")
        if not init_database():
            _log_fatal("数据库连接失败",
                       "无法连接到 MongoDB 数据库。\n\n"
                       "请检查:\n1. MongoDB 服务是否正常运行\n"
                       "2. 网络连接是否正常\n"
                       f"3. 数据库: {config.MONGODB_DB_NAME}")

        _log("数据库初始化完成")

    except SystemExit:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        logger.log_error(f"初始化阶段异常: {e}", exc_info=True)
        _log(f"初始化异常: {e}\n{tb}", level='error')
        _log_fatal("初始化失败", f"{e}\n\n{tb}")

    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)

    main_window = None
    pending_user = None

    def on_login_success(user):
        """登录成功回调"""
        nonlocal pending_user
        pending_user = user
        current_user_info['user'] = user

        user_info = get_current_user_info()
        logger.log_info("用户登录成功", user_info=user_info)
        _log(f"用户 {user.username} 登录成功")
        login_window.close_after_ready()

    def create_main_window():
        """登录窗口关闭后创建主窗口"""
        nonlocal main_window, pending_user

        if not pending_user:
            return

        user = pending_user
        user_info = get_current_user_info()

        try:
            if user.is_admin():
                _log("启动管理后台界面...")
                logger.log_info("启动管理后台界面...", user_info=user_info)
                main_window = AdminMainWindow(current_user=user)
            else:
                _log("启动表单填写界面...")
                logger.log_info("启动表单填写界面...", user_info=user_info)
                main_window = MainWindow(current_user=user)

            app._main_window = main_window
            main_window.show()
            logger.log_info("主窗口创建并显示成功", user_info=user_info)

        except Exception as e:
            tb = traceback.format_exc()
            error_msg = f"创建主窗口失败: {e}"
            logger.log_error(error_msg, exc_info=True, user_info=user_info)
            _log(f"{error_msg}\n{tb}", level='error')

            QMessageBox.critical(
                None, "启动失败",
                f"创建主窗口时发生错误:\n\n{str(e)}\n\n"
                f"详细日志已保存到:\n{logger.get_log_dir()}"
            )

    login_window = LoginWindow()
    login_window.login_success.connect(on_login_success)

    result = login_window.exec()

    if result != 1:
        _log("用户取消登录，程序退出")
        logger.log_info("用户取消登录，程序退出")
        sys.exit(0)

    create_main_window()

    if not main_window:
        logger.log_error("主窗口创建失败，程序退出")
        _log("主窗口创建失败，程序退出", level='error')
        sys.exit(1)

    logger.log_info("应用程序进入主循环")
    exit_code = app.exec()
    logger.log_info(f"应用程序正常退出 (exit_code: {exit_code})")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
