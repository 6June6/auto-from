#!/usr/bin/env python3
"""
开发模式启动脚本
自动监控文件变化并重启应用
"""
import sys
import time
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class CodeChangeHandler(FileSystemEventHandler):
    """代码变化处理器"""
    
    def __init__(self, restart_callback):
        self.restart_callback = restart_callback
        self.last_restart = 0
        self.debounce_seconds = 1  # 防抖时间
        
    def on_modified(self, event):
        # 只监控Python文件
        if event.src_path.endswith('.py'):
            current_time = time.time()
            # 防抖：避免短时间内多次重启
            if current_time - self.last_restart > self.debounce_seconds:
                print(f"\n📝 检测到文件变化: {event.src_path}")
                print("🔄 正在重启应用...\n")
                self.last_restart = current_time
                self.restart_callback()


class AppRunner:
    """应用运行器"""
    
    def __init__(self):
        self.process = None
        self.observer = None
        
    def start_app(self):
        """启动应用"""
        if self.process:
            self.stop_app()
        
        # 启动主程序
        self.process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # 实时输出日志
        def print_output():
            if self.process and self.process.stdout:
                for line in self.process.stdout:
                    print(line, end='')
        
        import threading
        threading.Thread(target=print_output, daemon=True).start()
    
    def stop_app(self):
        """停止应用"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            self.process = None
    
    def start_watching(self):
        """开始监控文件变化"""
        event_handler = CodeChangeHandler(self.start_app)
        self.observer = Observer()
        
        # 监控当前目录及子目录
        project_root = Path(__file__).parent
        
        # 监控gui目录
        gui_path = project_root / "gui"
        if gui_path.exists():
            self.observer.schedule(event_handler, str(gui_path), recursive=True)
        
        # 监控core目录
        core_path = project_root / "core"
        if core_path.exists():
            self.observer.schedule(event_handler, str(core_path), recursive=True)
        
        # 监控database目录
        db_path = project_root / "database"
        if db_path.exists():
            self.observer.schedule(event_handler, str(db_path), recursive=True)
        
        # 监控根目录的py文件
        self.observer.schedule(event_handler, str(project_root), recursive=False)
        
        self.observer.start()
        print("👀 文件监控已启动")
        print("📁 正在监控: gui/, core/, database/ 目录")
        print("💡 修改代码后会自动重启应用")
        print("⏹  按 Ctrl+C 退出\n")
    
    def run(self):
        """运行"""
        try:
            print("=" * 60)
            print("🚀 开发模式启动")
            print("=" * 60)
            
            # 启动应用
            self.start_app()
            
            # 开始监控
            self.start_watching()
            
            # 保持运行
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\n⏹  正在停止...")
            self.stop_app()
            if self.observer:
                self.observer.stop()
                self.observer.join()
            print("✅ 已退出开发模式")
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            self.stop_app()


if __name__ == "__main__":
    # 检查是否安装了watchdog
    try:
        import watchdog
    except ImportError:
        print("❌ 缺少依赖: watchdog")
        print("请运行: pip install watchdog")
        sys.exit(1)
    
    runner = AppRunner()
    runner.run()




