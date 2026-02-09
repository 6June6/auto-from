"""
日志系统测试脚本
用于验证日志系统是否正常工作
"""
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.logger import get_logger, setup_exception_hook


def test_basic_logging():
    """测试基本日志记录"""
    logger = get_logger()
    
    print("=" * 60)
    print("测试 1: 基本日志记录")
    print("=" * 60)
    
    # 测试各级别日志
    logger.log_debug("这是一条调试信息")
    logger.log_info("这是一条普通信息")
    logger.log_warning("这是一条警告信息")
    logger.log_error("这是一条错误信息")
    
    print("✅ 基本日志记录测试完成")
    print()


def test_user_info_logging():
    """测试带用户信息的日志"""
    logger = get_logger()
    
    print("=" * 60)
    print("测试 2: 带用户信息的日志")
    print("=" * 60)
    
    # 模拟用户信息
    user_info = {
        'username': 'test_user',
        'user_id': '507f1f77bcf86cd799439011',
        'device_id': 'test_device_123',
        'role': 'user'
    }
    
    logger.log_info("用户登录成功", user_info=user_info)
    logger.log_warning("用户配置不完整", user_info=user_info)
    logger.log_error("用户操作失败", user_info=user_info)
    
    print("✅ 带用户信息的日志测试完成")
    print()


def test_exception_logging():
    """测试异常日志记录"""
    logger = get_logger()
    
    print("=" * 60)
    print("测试 3: 异常日志记录")
    print("=" * 60)
    
    try:
        # 故意触发一个异常
        result = 10 / 0
    except Exception as e:
        logger.log_error(
            "测试异常捕获",
            exc_info=True,
            user_info={'username': 'test_user'}
        )
        print("✅ 已捕获并记录异常")
    
    print()


def test_crash_logging():
    """测试崩溃日志记录"""
    logger = get_logger()
    
    print("=" * 60)
    print("测试 4: 崩溃日志记录")
    print("=" * 60)
    
    try:
        # 故意触发一个更严重的异常
        some_object = None
        some_object.some_method()
    except Exception as e:
        import sys
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        user_info = {
            'username': 'crash_test_user',
            'user_id': '507f1f77bcf86cd799439012',
            'device_id': 'crash_test_device',
            'role': 'admin'
        }
        
        logger.log_crash(exc_type, exc_value, exc_traceback, user_info)
        print("✅ 已记录崩溃信息")
    
    print()


def test_exception_hook():
    """测试全局异常钩子"""
    print("=" * 60)
    print("测试 5: 全局异常钩子")
    print("=" * 60)
    
    def get_test_user_info():
        return {
            'username': 'hook_test_user',
            'user_id': '507f1f77bcf86cd799439013',
            'device_id': 'hook_test_device',
            'role': 'user'
        }
    
    setup_exception_hook(user_info_callback=get_test_user_info)
    print("✅ 全局异常钩子已设置")
    
    # 注意：不要在这里真的触发未捕获的异常，否则程序会退出
    print("⚠️  全局异常钩子将在未捕获异常时自动工作")
    print()


def test_log_directory():
    """测试日志目录"""
    logger = get_logger()
    log_dir = logger.get_log_dir()
    
    print("=" * 60)
    print("测试 6: 日志目录和文件")
    print("=" * 60)
    
    print(f"📂 日志目录: {log_dir}")
    
    if log_dir.exists():
        print("\n📄 日志文件列表:")
        for log_file in sorted(log_dir.glob('*')):
            size_kb = log_file.stat().st_size / 1024
            print(f"  - {log_file.name:30s} ({size_kb:,.1f} KB)")
        print("✅ 日志目录正常")
    else:
        print("❌ 日志目录不存在")
    
    print()


def main():
    """主测试函数"""
    print("\n")
    print("🧪 " + "=" * 56 + " 🧪")
    print("   日志系统测试")
    print("🧪 " + "=" * 56 + " 🧪")
    print("\n")
    
    try:
        # 运行所有测试
        test_basic_logging()
        test_user_info_logging()
        test_exception_logging()
        test_crash_logging()
        test_exception_hook()
        test_log_directory()
        
        # 总结
        logger = get_logger()
        print("=" * 60)
        print("✅ 所有测试完成")
        print("=" * 60)
        print(f"\n📊 测试报告:")
        print(f"  日志目录: {logger.get_log_dir()}")
        print(f"  崩溃日志: {logger.crash_log_file}")
        print(f"  错误日志: {logger.error_log_file}")
        print(f"  应用日志: {logger.app_log_file}")
        print()
        print("💡 建议:")
        print("  1. 使用 './view_logs.sh' 查看日志")
        print("  2. 检查日志文件是否包含测试数据")
        print("  3. 验证用户信息是否正确记录")
        print()
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
