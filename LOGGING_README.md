# 闪退日志监控系统 - 快速开始

## 🚀 快速开始

### 1. 测试日志系统

```bash
# 运行测试脚本
./test_logger.sh
```

### 2. 查看日志

```bash
# 使用图形界面查看器(推荐)
./view_logs.sh

# 或者直接查看文件
tail -f ~/.auto-form-filler/logs/crash.log
tail -f ~/.auto-form-filler/logs/error.log
tail -f ~/.auto-form-filler/logs/app.log
```

### 3. 排查闪退问题

```bash
# 搜索特定用户的日志
grep "用户名" ~/.auto-form-filler/logs/error.log

# 查看最新的崩溃记录
tail -50 ~/.auto-form-filler/logs/crash.log

# 查看崩溃详情
ls -t ~/.auto-form-filler/logs/crash_*.json | head -1 | xargs cat | python -m json.tool
```

## 📊 日志文件说明

| 文件 | 位置 | 内容 |
|------|------|------|
| crash.log | ~/.auto-form-filler/logs/ | 🔴 严重崩溃记录 |
| error.log | ~/.auto-form-filler/logs/ | ⚠️ 所有错误和异常 |
| app.log | ~/.auto-form-filler/logs/ | 📝 完整操作日志 |
| crash_*.json | ~/.auto-form-filler/logs/ | 📋 崩溃详细报告 |

## 🔍 关键功能

✅ **自动捕获所有异常** - 包括未处理的异常
✅ **记录用户信息** - 用户名、ID、设备号
✅ **详细堆栈跟踪** - 精确定位错误位置
✅ **系统环境信息** - OS、Python 版本等
✅ **自动日志轮转** - 防止日志文件过大
✅ **图形化查看器** - 方便查看和搜索

## 📱 实时监控

```bash
# 在一个终端窗口运行应用
python main.py

# 在另一个终端窗口实时监控日志
tail -f ~/.auto-form-filler/logs/error.log
```

## 🐛 调试流程

1. **用户报告闪退** → 获取用户名和闪退时间
2. **查看错误日志** → `grep "用户名" error.log`
3. **查看崩溃详情** → 找到对应时间的 crash_*.json
4. **分析堆栈跟踪** → 定位具体代码位置
5. **修复问题** → 根据日志信息修复代码

## 📚 详细文档

查看 `日志监控使用指南.md` 获取完整文档。

## ⚠️ 重要提示

- 日志文件存储在用户目录，不会影响应用程序目录
- 系统会自动管理日志文件大小和数量
- 日志不包含密码和敏感数据
- 建议定期清理旧日志(超过7天)

## 🆘 常见问题

**Q: 为什么找不到日志文件?**
A: 日志在 `~/.auto-form-filler/logs/` 目录，这是隐藏目录。

**Q: 日志文件太大怎么办?**
A: 使用日志查看器的"清理旧日志"功能，或手动删除旧备份。

**Q: 如何查看特定时间段的日志?**
A: 使用 grep 配合时间戳搜索，或在日志查看器中搜索。

**Q: 用户闪退但没有日志?**
A: 检查用户的 ~/.auto-form-filler/logs/ 目录权限，确保应用有写入权限。
