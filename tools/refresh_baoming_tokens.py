#!/usr/bin/env python3
"""
报名工具 Token 定时刷新脚本
定期调用 API 保持 Token 活跃状态，防止过期

部署方式：
1. Cron 定时任务（推荐）
2. systemd timer
3. 直接运行（内置定时器）
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import time
import argparse
import logging
from typing import List, Tuple

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.models import init_database, BaomingToken, Card
from core.baoming_tool_filler import BaomingToolAPI


# 配置日志
def setup_logging(log_file: str = None, verbose: bool = False):
    """配置日志系统"""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # 日志格式
    log_format = '%(asctime)s [%(levelname)s] %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 配置根日志记录器
    handlers = []
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    handlers.append(console_handler)
    
    # 文件处理器
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        handlers.append(file_handler)
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )
    
    return logging.getLogger(__name__)


logger = None


def refresh_single_token(token: BaomingToken) -> Tuple[bool, str]:
    """
    刷新单个 Token
    
    Args:
        token: Token 记录对象
        
    Returns:
        Tuple[bool, str]: (是否成功, 消息)
    """
    try:
        card = token.card
        logger.info(f"🔄 刷新 Token: 名片 '{card.name}' (ID: {card.id})")
        
        # 创建 API 实例
        api = BaomingToolAPI()
        api.access_token = token.access_token
        
        # 随便找一个 eid 来测试（这里用一个默认值）
        # 实际上只要 token 有效，任何 eid 都可以用来验证
        api.eid = "69844bcf8eaa2449c7a37fae"  # 测试用的 eid
        
        # 调用 get_enroll_detail 接口来验证 Token
        success, msg, info_id = api.get_enroll_detail()
        
        if success or '未找到已有报名记录' in msg:
            # Token 有效（无论是否有报名记录，只要不是 token 失效错误）
            token.last_used = datetime.now()
            token.save()
            logger.info(f"  ✅ Token 有效，已更新使用时间")
            return True, "Token 有效"
        else:
            # 检查是否是 token 失效错误
            if 'token' in msg.lower() or '登录' in msg or '过期' in msg or '失效' in msg or '无效' in msg:
                logger.warning(f"  ⚠️ Token 已失效: {msg}")
                # 删除失效的 Token
                token.delete()
                logger.info(f"  🗑️ 已删除失效 Token")
                return False, f"Token 已失效并删除: {msg}"
            else:
                # 其他错误，暂时保留 Token
                logger.warning(f"  ⚠️ 刷新失败: {msg}")
                return False, f"刷新失败: {msg}"
                
    except Exception as e:
        logger.error(f"  ❌ 刷新异常: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False, f"刷新异常: {str(e)}"


def refresh_all_tokens(max_age_days: int = None) -> dict:
    """
    刷新所有 Token
    
    Args:
        max_age_days: 只刷新 N 天内使用过的 Token（None 表示全部刷新）
        
    Returns:
        dict: 刷新统计结果
    """
    logger.info("=" * 60)
    logger.info("🚀 开始刷新报名工具 Token")
    logger.info("=" * 60)
    
    # 查询需要刷新的 Token
    query = BaomingToken.objects
    
    if max_age_days:
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        query = query.filter(last_used__gte=cutoff_date)
        logger.info(f"📊 只刷新 {max_age_days} 天内使用过的 Token")
    
    tokens = list(query)
    total = len(tokens)
    
    logger.info(f"📊 找到 {total} 个 Token 需要刷新")
    
    if total == 0:
        logger.info("✅ 没有需要刷新的 Token")
        return {
            'total': 0,
            'success': 0,
            'failed': 0,
            'deleted': 0
        }
    
    logger.info("-" * 60)
    
    success_count = 0
    failed_count = 0
    deleted_count = 0
    
    for i, token in enumerate(tokens, 1):
        try:
            card = token.card
            logger.info(f"\n[{i}/{total}] 名片: {card.name}")
            logger.info(f"  用户: {token.uname}")
            logger.info(f"  最后使用: {token.last_used.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 检查 Token 是否存在（可能已被删除）
            if not BaomingToken.objects(id=token.id).first():
                logger.warning(f"  ⚠️ Token 已被删除，跳过")
                deleted_count += 1
                continue
            
            # 刷新 Token
            success, msg = refresh_single_token(token)
            
            if success:
                success_count += 1
            else:
                # 检查是否包含删除标记
                if '已删除' in msg or '并删除' in msg:
                    deleted_count += 1
                else:
                    failed_count += 1
            
            # 避免请求过快，休息 1 秒
            if i < total:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"  ❌ 处理 Token 异常: {e}")
            failed_count += 1
    
    logger.info("\n" + "-" * 60)
    logger.info("📊 刷新统计:")
    logger.info(f"  📝 总计: {total} 个")
    logger.info(f"  ✅ 成功: {success_count} 个")
    logger.info(f"  ❌ 失败: {failed_count} 个")
    logger.info(f"  🗑️ 删除: {deleted_count} 个")
    logger.info("=" * 60)
    logger.info("🎉 刷新完成")
    logger.info("=" * 60)
    
    return {
        'total': total,
        'success': success_count,
        'failed': failed_count,
        'deleted': deleted_count
    }


def cleanup_old_tokens(days: int = 30) -> int:
    """
    清理过期 Token
    
    Args:
        days: 删除 N 天未使用的 Token
        
    Returns:
        int: 删除的 Token 数量
    """
    logger.info(f"🧹 清理 {days} 天未使用的 Token...")
    
    cutoff_date = datetime.now() - timedelta(days=days)
    old_tokens = BaomingToken.objects(last_used__lt=cutoff_date)
    count = old_tokens.count()
    
    if count == 0:
        logger.info("  ✅ 没有需要清理的 Token")
        return 0
    
    logger.info(f"  发现 {count} 个过期 Token:")
    for token in old_tokens:
        card = token.card
        days_ago = (datetime.now() - token.last_used).days
        logger.info(f"    - {card.name}: 最后使用 {days_ago} 天前")
    
    old_tokens.delete()
    logger.info(f"  ✅ 已清理 {count} 个过期 Token")
    
    return count


def run_once(args):
    """运行一次刷新任务"""
    logger.info(f"⏰ 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 刷新 Token
    result = refresh_all_tokens(max_age_days=args.max_age_days)
    
    # 清理过期 Token
    if args.cleanup_days:
        cleanup_old_tokens(days=args.cleanup_days)
    
    return result


def run_scheduler(args):
    """
    运行定时任务
    使用 schedule 库实现定时刷新
    """
    try:
        import schedule
    except ImportError:
        logger.error("❌ 缺少 schedule 库，请安装: pip install schedule")
        return 1
    
    logger.info("🕐 定时任务模式")
    
    # 确定使用分钟还是小时
    if hasattr(args, 'interval_minutes') and args.interval_minutes:
        interval_value = args.interval_minutes
        interval_unit = "分钟"
        use_minutes = True
    else:
        interval_value = args.interval
        interval_unit = "小时"
        use_minutes = False
    
    logger.info(f"   刷新间隔: 每 {interval_value} {interval_unit}")
    logger.info(f"   立即执行: {'是' if args.run_immediately else '否'}")
    logger.info("-" * 60)
    
    # 定义任务
    def job():
        try:
            run_once(args)
        except Exception as e:
            logger.error(f"❌ 任务执行失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    # 设置定时任务
    if use_minutes:
        schedule.every(interval_value).minutes.do(job)
        check_interval = 10  # 每10秒检查一次（分钟级任务）
    else:
        schedule.every(interval_value).hours.do(job)
        check_interval = 60  # 每分钟检查一次（小时级任务）
    
    # 立即执行一次
    if args.run_immediately:
        logger.info("▶️ 立即执行一次刷新任务")
        job()
    
    logger.info(f"\n✅ 定时任务已启动，每 {interval_value} {interval_unit}执行一次")
    logger.info("   按 Ctrl+C 停止")
    logger.info("-" * 60)
    
    # 运行定时器
    try:
        while True:
            schedule.run_pending()
            time.sleep(check_interval)
    except KeyboardInterrupt:
        logger.info("\n⚠️ 用户中断，停止定时任务")
        return 0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='报名工具 Token 定时刷新脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 运行一次刷新
  python refresh_baoming_tokens.py
  
  # 定时刷新（每 6 小时）
  python refresh_baoming_tokens.py --scheduler --interval 6
  
  # 定时刷新（每 10 分钟）
  python refresh_baoming_tokens.py --scheduler --interval-minutes 10
  
  # 只刷新 7 天内使用过的 Token
  python refresh_baoming_tokens.py --max-age-days 7
  
  # 刷新并清理 30 天未使用的 Token
  python refresh_baoming_tokens.py --cleanup-days 30
  
  # Cron 定时任务（推荐）
  0 */6 * * * /usr/bin/python3 /path/to/refresh_baoming_tokens.py
        """
    )
    
    parser.add_argument(
        '--scheduler',
        action='store_true',
        help='启动内置定时器（需要安装 schedule 库）'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=6,
        help='定时器间隔（小时），默认 6 小时'
    )
    
    parser.add_argument(
        '--interval-minutes',
        type=int,
        help='定时器间隔（分钟），优先级高于 --interval'
    )
    
    parser.add_argument(
        '--run-immediately',
        action='store_true',
        help='定时器启动时立即执行一次'
    )
    
    parser.add_argument(
        '--max-age-days',
        type=int,
        help='只刷新 N 天内使用过的 Token（默认刷新全部）'
    )
    
    parser.add_argument(
        '--cleanup-days',
        type=int,
        help='清理 N 天未使用的 Token（默认不清理）'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        help='日志文件路径（默认只输出到控制台）'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出（调试模式）'
    )
    
    args = parser.parse_args()
    
    # 设置日志
    global logger
    logger = setup_logging(log_file=args.log_file, verbose=args.verbose)
    
    # 初始化数据库
    logger.info("🔧 正在连接数据库...")
    if not init_database():
        logger.error("❌ 数据库连接失败")
        return 1
    logger.info("✅ 数据库连接成功\n")
    
    # 运行模式
    if args.scheduler:
        return run_scheduler(args)
    else:
        run_once(args)
        return 0


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
