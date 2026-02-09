"""
日志管理模块
提供统一的日志记录功能,支持控制台、文件、异常捕获
"""
import logging
import sys
import traceback
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler
import json
import platform


class CrashLogger:
    """闪退日志记录器 - 专门用于捕获和记录程序崩溃"""
    
    def __init__(self, log_dir: Path = None):
        """
        初始化闪退日志记录器
        
        Args:
            log_dir: 日志目录,默认为用户目录下的 .auto-form-filler/logs
        """
        if log_dir is None:
            log_dir = Path.home() / '.auto-form-filler' / 'logs'
        
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 日志文件路径
        self.crash_log_file = self.log_dir / 'crash.log'
        self.error_log_file = self.log_dir / 'error.log'
        self.app_log_file = self.log_dir / 'app.log'
        
        # 初始化日志记录器
        self._setup_loggers()
    
    def _setup_loggers(self):
        """设置各类日志记录器"""
        # 1. 崩溃日志 (只记录严重错误)
        self.crash_logger = logging.getLogger('crash')
        self.crash_logger.setLevel(logging.CRITICAL)
        self.crash_logger.propagate = False
        
        crash_handler = RotatingFileHandler(
            self.crash_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        crash_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        crash_handler.setFormatter(crash_formatter)
        self.crash_logger.addHandler(crash_handler)
        
        # 2. 错误日志 (记录所有异常)
        self.error_logger = logging.getLogger('error')
        self.error_logger.setLevel(logging.ERROR)
        self.error_logger.propagate = False
        
        error_handler = RotatingFileHandler(
            self.error_log_file,
            maxBytes=20*1024*1024,  # 20MB
            backupCount=10,
            encoding='utf-8'
        )
        error_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | [%(filename)s:%(lineno)d] | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        error_handler.setFormatter(error_formatter)
        self.error_logger.addHandler(error_handler)
        
        # 3. 应用日志 (记录所有级别)
        self.app_logger = logging.getLogger('app')
        self.app_logger.setLevel(logging.DEBUG)
        self.app_logger.propagate = False
        
        # 文件处理器
        app_handler = RotatingFileHandler(
            self.app_log_file,
            maxBytes=50*1024*1024,  # 50MB
            backupCount=10,
            encoding='utf-8'
        )
        app_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | [%(filename)s:%(lineno)d] | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        app_handler.setFormatter(app_formatter)
        self.app_logger.addHandler(app_handler)
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(levelname)s | %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.app_logger.addHandler(console_handler)
    
    def log_crash(self, exc_type, exc_value, exc_traceback, user_info=None):
        """
        记录崩溃信息
        
        Args:
            exc_type: 异常类型
            exc_value: 异常值
            exc_traceback: 异常堆栈
            user_info: 用户信息字典
        """
        try:
            # 生成详细的崩溃报告
            crash_report = self._generate_crash_report(
                exc_type, exc_value, exc_traceback, user_info
            )
            
            # 记录到崩溃日志
            self.crash_logger.critical(
                f"\n{'='*80}\n"
                f"🔴 程序崩溃\n"
                f"{'='*80}\n"
                f"{crash_report}\n"
                f"{'='*80}\n"
            )
            
            # 同时保存为独立的 JSON 文件
            self._save_crash_json(crash_report, user_info)
            
        except Exception as e:
            # 确保日志记录本身不会导致崩溃
            print(f"❌ 记录崩溃日志失败: {e}", file=sys.stderr)
    
    def _generate_crash_report(self, exc_type, exc_value, exc_traceback, user_info):
        """生成详细的崩溃报告"""
        report_lines = []
        
        # 时间戳
        report_lines.append(f"崩溃时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 用户信息
        if user_info:
            report_lines.append(f"\n用户信息:")
            report_lines.append(f"  用户名: {user_info.get('username', 'Unknown')}")
            report_lines.append(f"  用户ID: {user_info.get('user_id', 'Unknown')}")
            report_lines.append(f"  设备ID: {user_info.get('device_id', 'Unknown')}")
            report_lines.append(f"  角色: {user_info.get('role', 'Unknown')}")
        
        # 系统信息
        report_lines.append(f"\n系统信息:")
        report_lines.append(f"  操作系统: {platform.system()} {platform.release()}")
        report_lines.append(f"  系统版本: {platform.version()}")
        report_lines.append(f"  Python版本: {sys.version}")
        report_lines.append(f"  架构: {platform.machine()}")
        
        # 异常信息
        report_lines.append(f"\n异常类型: {exc_type.__name__}")
        report_lines.append(f"异常信息: {str(exc_value)}")
        
        # 堆栈跟踪
        report_lines.append(f"\n堆栈跟踪:")
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        report_lines.extend(['  ' + line for line in ''.join(tb_lines).split('\n')])
        
        return '\n'.join(report_lines)
    
    def _save_crash_json(self, crash_report, user_info):
        """保存崩溃报告为 JSON 格式"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            crash_json_file = self.log_dir / f'crash_{timestamp}.json'
            
            crash_data = {
                'timestamp': datetime.now().isoformat(),
                'user_info': user_info or {},
                'system_info': {
                    'os': platform.system(),
                    'os_version': platform.version(),
                    'python_version': sys.version,
                    'machine': platform.machine()
                },
                'crash_report': crash_report
            }
            
            with open(crash_json_file, 'w', encoding='utf-8') as f:
                json.dump(crash_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"❌ 保存崩溃 JSON 失败: {e}", file=sys.stderr)
    
    def log_error(self, message, exc_info=None, user_info=None):
        """
        记录错误信息
        
        Args:
            message: 错误消息
            exc_info: 异常信息
            user_info: 用户信息
        """
        log_msg = message
        if user_info:
            user_str = f"[User: {user_info.get('username', 'Unknown')}]"
            log_msg = f"{user_str} {message}"
        
        self.error_logger.error(log_msg, exc_info=exc_info)
    
    def log_info(self, message, user_info=None):
        """记录普通信息"""
        log_msg = message
        if user_info:
            user_str = f"[User: {user_info.get('username', 'Unknown')}]"
            log_msg = f"{user_str} {message}"
        
        self.app_logger.info(log_msg)
    
    def log_debug(self, message, user_info=None):
        """记录调试信息"""
        log_msg = message
        if user_info:
            user_str = f"[User: {user_info.get('username', 'Unknown')}]"
            log_msg = f"{user_str} {message}"
        
        self.app_logger.debug(log_msg)
    
    def log_warning(self, message, user_info=None):
        """记录警告信息"""
        log_msg = message
        if user_info:
            user_str = f"[User: {user_info.get('username', 'Unknown')}]"
            log_msg = f"{user_str} {message}"
        
        self.app_logger.warning(log_msg)
    
    def get_log_dir(self):
        """获取日志目录路径"""
        return self.log_dir


# 全局日志实例
_crash_logger = None


def get_logger():
    """获取全局日志实例"""
    global _crash_logger
    if _crash_logger is None:
        _crash_logger = CrashLogger()
    return _crash_logger


def setup_exception_hook(user_info_callback=None):
    """
    设置全局异常钩子,捕获所有未处理的异常
    
    Args:
        user_info_callback: 回调函数,用于获取当前用户信息
    """
    logger = get_logger()
    
    # 保存原始的异常钩子
    original_excepthook = sys.excepthook
    
    def exception_handler(exc_type, exc_value, exc_traceback):
        """自定义异常处理器"""
        # 获取用户信息
        user_info = None
        if user_info_callback and callable(user_info_callback):
            try:
                user_info = user_info_callback()
            except:
                pass
        
        # 记录崩溃信息
        logger.log_crash(exc_type, exc_value, exc_traceback, user_info)
        
        # 调用原始的异常钩子
        original_excepthook(exc_type, exc_value, exc_traceback)
    
    # 设置自定义异常钩子
    sys.excepthook = exception_handler
    
    logger.log_info("🛡️ 全局异常钩子已设置")


def setup_qt_exception_hook():
    """设置 Qt 异常钩子,捕获 Qt 事件循环中的异常"""
    logger = get_logger()
    
    try:
        from PyQt6.QtCore import qInstallMessageHandler, QtMsgType
        
        def qt_message_handler(msg_type, context, message):
            """Qt 消息处理器"""
            if msg_type == QtMsgType.QtCriticalMsg or msg_type == QtMsgType.QtFatalMsg:
                logger.log_error(
                    f"Qt Critical/Fatal: {message}\n"
                    f"  File: {context.file}\n"
                    f"  Line: {context.line}\n"
                    f"  Function: {context.function}"
                )
            elif msg_type == QtMsgType.QtWarningMsg:
                logger.log_warning(
                    f"Qt Warning: {message}\n"
                    f"  File: {context.file}\n"
                    f"  Line: {context.line}"
                )
        
        qInstallMessageHandler(qt_message_handler)
        logger.log_info("🛡️ Qt 消息处理器已设置")
        
    except Exception as e:
        logger.log_error(f"设置 Qt 异常钩子失败: {e}")
