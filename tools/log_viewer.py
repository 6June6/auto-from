"""
日志查看器工具
用于查看和分析应用程序日志
"""
import sys
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QComboBox, QFileDialog,
    QMessageBox, QTabWidget, QListWidget, QListWidgetItem,
    QSplitter, QLineEdit
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QTextCursor

# 添加项目根目录到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.logger import get_logger


class LogViewerWindow(QMainWindow):
    """日志查看器主窗口"""
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger()
        self.log_dir = self.logger.get_log_dir()
        self.current_log_file = None
        self.auto_refresh = False
        
        self.init_ui()
        self.load_log_files()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle(f"日志查看器 - {self.log_dir}")
        self.setGeometry(100, 100, 1200, 800)
        
        # 主容器
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # 顶部工具栏
        toolbar = self._create_toolbar()
        main_layout.addLayout(toolbar)
        
        # 分割器：左侧文件列表，右侧内容显示
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：文件列表
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.on_file_selected)
        splitter.addWidget(self.file_list)
        
        # 右侧：选项卡式内容显示
        self.tab_widget = QTabWidget()
        
        # Tab 1: 完整日志
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 10))
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.tab_widget.addTab(self.log_text, "完整日志")
        
        # Tab 2: 错误日志
        self.error_text = QTextEdit()
        self.error_text.setReadOnly(True)
        self.error_text.setFont(QFont("Courier New", 10))
        self.error_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.tab_widget.addTab(self.error_text, "仅错误")
        
        # Tab 3: 崩溃详情
        self.crash_text = QTextEdit()
        self.crash_text.setReadOnly(True)
        self.crash_text.setFont(QFont("Courier New", 10))
        self.crash_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.tab_widget.addTab(self.crash_text, "崩溃详情")
        
        splitter.addWidget(self.tab_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(splitter)
        
        # 底部状态栏
        self.status_label = QLabel("就绪")
        main_layout.addWidget(self.status_label)
        
        # 自动刷新定时器
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_current_log)
        
        # 应用样式
        self._apply_styles()
    
    def _create_toolbar(self):
        """创建工具栏"""
        toolbar = QHBoxLayout()
        
        # 日志类型选择
        toolbar.addWidget(QLabel("日志类型:"))
        self.log_type_combo = QComboBox()
        self.log_type_combo.addItems(["所有日志", "应用日志", "错误日志", "崩溃日志"])
        self.log_type_combo.currentTextChanged.connect(self.filter_log_files)
        toolbar.addWidget(self.log_type_combo)
        
        toolbar.addSpacing(20)
        
        # 搜索框
        toolbar.addWidget(QLabel("搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入关键词搜索...")
        self.search_input.textChanged.connect(self.search_logs)
        toolbar.addWidget(self.search_input)
        
        toolbar.addSpacing(20)
        
        # 刷新按钮
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.refresh_current_log)
        toolbar.addWidget(refresh_btn)
        
        # 自动刷新按钮
        self.auto_refresh_btn = QPushButton("🔁 自动刷新: 关")
        self.auto_refresh_btn.setCheckable(True)
        self.auto_refresh_btn.clicked.connect(self.toggle_auto_refresh)
        toolbar.addWidget(self.auto_refresh_btn)
        
        # 打开目录按钮
        open_dir_btn = QPushButton("📂 打开日志目录")
        open_dir_btn.clicked.connect(self.open_log_directory)
        toolbar.addWidget(open_dir_btn)
        
        # 清理日志按钮
        clear_btn = QPushButton("🗑️ 清理旧日志")
        clear_btn.clicked.connect(self.clear_old_logs)
        toolbar.addWidget(clear_btn)
        
        toolbar.addStretch()
        
        return toolbar
    
    def _apply_styles(self):
        """应用界面样式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 8px;
            }
            QListWidget {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #3b82f6;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #e0e0e0;
            }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
            QLabel {
                color: #333;
                font-weight: bold;
            }
            QLineEdit {
                padding: 6px;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: white;
            }
            QComboBox {
                padding: 6px;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: white;
            }
        """)
    
    def load_log_files(self):
        """加载日志文件列表"""
        self.file_list.clear()
        
        if not self.log_dir.exists():
            self.status_label.setText("❌ 日志目录不存在")
            return
        
        # 获取所有日志文件
        log_files = []
        
        for pattern in ['*.log', '*.json']:
            log_files.extend(self.log_dir.glob(pattern))
        
        # 按修改时间排序（最新的在前）
        log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        # 添加到列表
        for log_file in log_files:
            stat = log_file.stat()
            size_mb = stat.st_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            
            item_text = f"{log_file.name}\n  大小: {size_mb:.2f} MB | 修改: {mtime}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, log_file)
            
            # 根据文件类型设置图标
            if 'crash' in log_file.name:
                item.setForeground(QColor('#ef4444'))
            elif 'error' in log_file.name:
                item.setForeground(QColor('#f59e0b'))
            else:
                item.setForeground(QColor('#3b82f6'))
            
            self.file_list.addItem(item)
        
        self.status_label.setText(f"✅ 找到 {len(log_files)} 个日志文件")
    
    def filter_log_files(self, log_type):
        """根据类型过滤日志文件"""
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            log_file = item.data(Qt.ItemDataRole.UserRole)
            
            if log_type == "所有日志":
                item.setHidden(False)
            elif log_type == "应用日志":
                item.setHidden('app.log' not in log_file.name)
            elif log_type == "错误日志":
                item.setHidden('error.log' not in log_file.name)
            elif log_type == "崩溃日志":
                item.setHidden('crash' not in log_file.name)
    
    def on_file_selected(self, item):
        """文件选中事件"""
        log_file = item.data(Qt.ItemDataRole.UserRole)
        self.current_log_file = log_file
        self.load_log_content(log_file)
    
    def load_log_content(self, log_file: Path):
        """加载日志内容"""
        try:
            # 读取文件内容
            content = log_file.read_text(encoding='utf-8')
            
            # 显示完整日志
            self.log_text.setPlainText(content)
            self.log_text.moveCursor(QTextCursor.MoveOperation.End)
            
            # 提取错误日志
            error_lines = []
            for line in content.split('\n'):
                if any(keyword in line for keyword in ['ERROR', 'CRITICAL', '❌', '异常', 'Exception', 'Traceback']):
                    error_lines.append(line)
            
            self.error_text.setPlainText('\n'.join(error_lines))
            
            # 如果是崩溃日志，显示详情
            if 'crash' in log_file.name:
                self.crash_text.setPlainText(content)
            else:
                self.crash_text.setPlainText("此文件不是崩溃日志")
            
            self.status_label.setText(f"✅ 已加载: {log_file.name}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"读取日志文件失败:\n{e}")
    
    def refresh_current_log(self):
        """刷新当前日志"""
        if self.current_log_file and self.current_log_file.exists():
            self.load_log_content(self.current_log_file)
        
        # 刷新文件列表
        self.load_log_files()
    
    def toggle_auto_refresh(self, checked):
        """切换自动刷新"""
        self.auto_refresh = checked
        
        if checked:
            self.auto_refresh_btn.setText("🔁 自动刷新: 开 (5s)")
            self.refresh_timer.start(5000)  # 每5秒刷新一次
        else:
            self.auto_refresh_btn.setText("🔁 自动刷新: 关")
            self.refresh_timer.stop()
    
    def search_logs(self, keyword):
        """搜索日志内容"""
        if not keyword:
            return
        
        # 在当前显示的日志中搜索
        current_tab = self.tab_widget.currentWidget()
        if isinstance(current_tab, QTextEdit):
            # 高亮显示搜索结果
            cursor = current_tab.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            current_tab.setTextCursor(cursor)
            
            # 查找并高亮
            current_tab.find(keyword)
    
    def open_log_directory(self):
        """打开日志目录"""
        import subprocess
        import platform
        
        try:
            system = platform.system()
            if system == 'Darwin':  # macOS
                subprocess.run(['open', str(self.log_dir)])
            elif system == 'Windows':
                subprocess.run(['explorer', str(self.log_dir)])
            else:  # Linux
                subprocess.run(['xdg-open', str(self.log_dir)])
        except Exception as e:
            QMessageBox.warning(self, "提示", f"无法打开目录:\n{e}")
    
    def clear_old_logs(self):
        """清理旧日志"""
        reply = QMessageBox.question(
            self,
            "确认清理",
            "确定要清理7天前的旧日志吗？\n\n此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from datetime import timedelta
                cutoff_time = datetime.now() - timedelta(days=7)
                
                deleted_count = 0
                for log_file in self.log_dir.glob('*'):
                    if log_file.is_file():
                        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                        if mtime < cutoff_time:
                            log_file.unlink()
                            deleted_count += 1
                
                QMessageBox.information(self, "清理完成", f"已删除 {deleted_count} 个旧日志文件")
                self.load_log_files()
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"清理失败:\n{e}")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = LogViewerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
