"""
链接管理对话框
"""
import re
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QLineEdit, QLabel, QWidget,
                             QFormLayout, QComboBox, QTextEdit, QGroupBox,
                             QSplitter, QProgressBar)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from database import DatabaseManager, Link
from core.ai_parser import AIParser
from .icons import Icons


class LinkManagerDialog(QDialog):
    """链接管理对话框"""
    
    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.current_user = current_user
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("链接管理")
        self.setGeometry(150, 150, 1000, 600)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 标题
        title_label = QLabel("🔗 链接管理")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(title_label)
        
        # 筛选区域
        filter_layout = QHBoxLayout()
        filter_label = QLabel("状态筛选:")
        filter_layout.addWidget(filter_label)
        
        self.status_combo = QComboBox()
        self.status_combo.addItems(["全部", "激活", "归档", "已删除"])
        self.status_combo.currentTextChanged.connect(self.load_data)
        filter_layout.addWidget(self.status_combo)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["名称", "URL", "分类", "状态", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setDefaultSectionSize(45)  # 增加行高，防止按钮显示不全
        layout.addWidget(self.table)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        btn_add = QPushButton("➕ 新增链接")
        btn_add.clicked.connect(self.add_link)
        btn_add.setStyleSheet("background-color: #28a745; color: white; padding: 10px; font-weight: bold;")
        button_layout.addWidget(btn_add)
        
        btn_refresh = QPushButton("🔄 刷新")
        btn_refresh.clicked.connect(self.load_data)
        button_layout.addWidget(btn_refresh)
        
        button_layout.addStretch()
        
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        button_layout.addWidget(btn_close)
        
        layout.addLayout(button_layout)
        
        # 加载数据
        self.load_data()
    
    def get_filter_status(self) -> str:
        """获取筛选状态"""
        status_map = {
            "全部": None,
            "激活": "active",
            "归档": "archived",
            "已删除": "deleted"
        }
        return status_map.get(self.status_combo.currentText())
    
    def load_data(self):
        """加载数据"""
        status = self.get_filter_status()
        links = self.db_manager.get_all_links(status, user=self.current_user)
        self.table.setRowCount(len(links))
        
        for i, link in enumerate(links):
            # 名称
            self.table.setItem(i, 0, QTableWidgetItem(link.name))
            
            # URL
            url_text = link.url[:50] + "..." if len(link.url) > 50 else link.url
            self.table.setItem(i, 1, QTableWidgetItem(url_text))
            
            # 分类
            self.table.setItem(i, 2, QTableWidgetItem(link.category or "-"))
            
            # 状态
            status_map = {
                "active": "✅ 激活",
                "archived": "📦 归档",
                "deleted": "🗑️ 已删除"
            }
            self.table.setItem(i, 3, QTableWidgetItem(status_map.get(link.status, link.status)))
            
            # 操作按钮
            action_widget = QWidget()
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(6)
            action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            action_widget.setLayout(action_layout)
            
            # 样式
            btn_style = """
                QPushButton {
                    background: transparent;
                    border: 1px solid transparent;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background: #F0F2F5;
                    border-color: #DCDFE6;
                }
                QPushButton:pressed {
                    background: #E4E7ED;
                }
            """
            
            # 编辑按钮
            btn_edit = QPushButton()
            btn_edit.setIcon(Icons.edit('primary'))
            btn_edit.setFixedSize(28, 28)
            btn_edit.setToolTip("编辑")
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setStyleSheet(btn_style)
            btn_edit.clicked.connect(lambda checked, l=link: self.edit_link(l))
            action_layout.addWidget(btn_edit)
            
            # 复制按钮
            btn_copy = QPushButton()
            btn_copy.setIcon(Icons.copy('info'))
            btn_copy.setFixedSize(28, 28)
            btn_copy.setToolTip("复制URL")
            btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_copy.setStyleSheet(btn_style)
            btn_copy.clicked.connect(lambda checked, l=link: self.copy_url(l))
            action_layout.addWidget(btn_copy)
            
            # 删除按钮
            btn_delete = QPushButton()
            btn_delete.setIcon(Icons.delete('danger'))
            btn_delete.setFixedSize(28, 28)
            btn_delete.setToolTip("删除")
            btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_delete.setStyleSheet(btn_style)
            btn_delete.clicked.connect(lambda checked, l=link: self.delete_link(l))
            action_layout.addWidget(btn_delete)
            
            self.table.setCellWidget(i, 4, action_widget)
    
    def add_link(self):
        """新增链接 - 智能批量添加"""
        dialog = SmartAddLinkDialog(self, current_user=self.current_user)
        if dialog.exec():
            self.load_data()
    
    def edit_link(self, link: Link):
        """编辑链接"""
        dialog = LinkEditDialog(self, link, current_user=self.current_user)
        if dialog.exec():
            self.load_data()
    
    def copy_url(self, link: Link):
        """复制URL"""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(link.url)
        QMessageBox.information(self, "成功", "URL 已复制到剪贴板")
    
    def delete_link(self, link: Link):
        """删除链接"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除链接 '{link.name}' 吗？\n此操作不可撤销！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.db_manager.delete_link(link.id):
                QMessageBox.information(self, "成功", "链接已删除")
                self.load_data()
            else:
                QMessageBox.critical(self, "错误", "删除失败")


class AIParseThread(QThread):
    """AI 解析线程"""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, text):
        super().__init__()
        self.text = text
        
    def run(self):
        try:
            links = AIParser.parse_links(self.text)
            self.finished.emit(links)
        except Exception as e:
            self.error.emit(str(e))


class SmartAddLinkDialog(QDialog):
    """智能批量添加链接对话框"""
    
    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.current_user = current_user
        self.parsed_links = []  # 存储解析结果
        self.ai_thread = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("新增链接 - 智能解析 (DeepSeek 支持)")
        self.resize(1000, 700)
        
        # 主布局
        layout = QVBoxLayout()
        layout.setSpacing(15)
        self.setLayout(layout)
        
        # 说明
        info_label = QLabel("💡 提示：直接粘贴包含链接的文本（如聊天记录）。可以使用「本地正则解析」快速提取，或使用「AI 智能解析」获得更准确的标题和分类。")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 分割器：上部输入，下部预览
        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter, 1)
        
        # 上部：输入区域
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        input_header = QHBoxLayout()
        input_label = QLabel("粘贴文本:")
        input_label.setStyleSheet("font-weight: bold;")
        input_header.addWidget(input_label)
        input_header.addStretch()
        
        # AI 解析按钮
        self.btn_ai_parse = QPushButton("✨ DeepSeek 智能解析")
        self.btn_ai_parse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ai_parse.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #8b5cf6);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #7c3aed);
            }
            QPushButton:disabled {
                background: #ccc;
            }
        """)
        self.btn_ai_parse.clicked.connect(self.start_ai_parse)
        input_header.addWidget(self.btn_ai_parse)
        
        input_layout.addLayout(input_header)
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("在此粘贴包含链接的文本...\n例如：\nhttps://docs.qq.com/form/page/xx 邀请你填写《XX报名表》")
        self.text_edit.textChanged.connect(self.on_text_changed)
        input_layout.addWidget(self.text_edit)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 不确定进度
        self.progress_bar.hide()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bbb;
                border-radius: 4px;
                text-align: center;
                background: #f0f0f0;
                height: 6px;
            }
            QProgressBar::chunk {
                background-color: #6366f1;
                width: 20px;
            }
        """)
        input_layout.addWidget(self.progress_bar)
        
        splitter.addWidget(input_widget)
        
        # 下部：解析结果
        result_widget = QWidget()
        result_layout = QVBoxLayout(result_widget)
        result_layout.setContentsMargins(0, 0, 0, 0)
        
        result_header = QHBoxLayout()
        result_label = QLabel("解析结果:")
        result_label.setStyleSheet("font-weight: bold;")
        result_header.addWidget(result_label)
        
        self.count_label = QLabel("共找到 0 个链接")
        self.count_label.setStyleSheet("color: #007AFF;")
        result_header.addWidget(self.count_label)
        result_header.addStretch()
        
        result_layout.addLayout(result_header)
        
        # 结果表格
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["链接名称", "URL", "分类", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        result_layout.addWidget(self.table)
        
        splitter.addWidget(result_widget)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        # 手动添加单条按钮
        btn_add_single = QPushButton("手动添加单条")
        btn_add_single.clicked.connect(self.add_empty_row)
        button_layout.addWidget(btn_add_single)
        
        button_layout.addStretch()
        
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setFixedSize(100, 40)
        button_layout.addWidget(btn_cancel)
        
        self.btn_save = QPushButton("保存全部")
        self.btn_save.clicked.connect(self.save_all)
        self.btn_save.setFixedSize(120, 40)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                color: white;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0062CC;
            }
            QPushButton:disabled {
                background-color: #CCC;
            }
        """)
        button_layout.addWidget(self.btn_save)
        
        layout.addLayout(button_layout)
        
        # 定时器用于防抖解析（本地正则）
        self.parse_timer = QTimer()
        self.parse_timer.setSingleShot(True)
        self.parse_timer.timeout.connect(self.parse_content_regex)
        
        # 初始禁用保存
        self.btn_save.setEnabled(False)

    def on_text_changed(self):
        """文本变化时触发防抖解析（仅本地）"""
        # 如果 AI 正在解析，不打断
        if self.ai_thread and self.ai_thread.isRunning():
            return
        
        # 自动触发 DeepSeek 解析（延迟 1 秒）
        # 之前的 parse_timer 是本地正则，这里改为自动调用 start_ai_parse
        # 但为了避免太频繁请求 API，设置较长的防抖时间
        
        # 先停止之前的计时器
        self.parse_timer.stop()
        
        # 如果文本为空，清空表格
        if not self.text_edit.toPlainText().strip():
            self.table.setRowCount(0)
            self.update_status()
            return

        # 自动触发 AI 解析
        # 注意：这会消耗 token，用户可能只想粘贴一下，所以还是保留手动点击或非常长的延迟比较好？
        # 用户的需求是“默认就是 deepseek”，所以我们可以在这里自动触发
        
        # 断开之前的连接（如果有）
        try:
            self.parse_timer.timeout.disconnect()
        except:
            pass
            
        self.parse_timer.timeout.connect(self.start_ai_parse)
        self.parse_timer.start(1500)  # 1.5秒后自动开始解析
    
    def start_ai_parse(self):
        """开始 AI 解析"""
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "提示", "请先粘贴文本")
            return
            
        self.btn_ai_parse.setEnabled(False)
        self.btn_ai_parse.setText("🔄 正在解析...")
        self.progress_bar.show()
        
        self.ai_thread = AIParseThread(text)
        self.ai_thread.finished.connect(self.on_ai_parse_finished)
        self.ai_thread.error.connect(self.on_ai_parse_error)
        self.ai_thread.start()
        
    def on_ai_parse_finished(self, links):
        """AI 解析完成"""
        self.btn_ai_parse.setEnabled(True)
        self.btn_ai_parse.setText("✨ DeepSeek 智能解析")
        self.progress_bar.hide()
        
        if not links:
            QMessageBox.information(self, "提示", "未识别到有效的链接信息")
            return
            
        self.populate_table(links)
        QMessageBox.information(self, "成功", f"AI 成功解析出 {len(links)} 个链接！")
        
    def on_ai_parse_error(self, error_msg):
        """AI 解析出错"""
        self.btn_ai_parse.setEnabled(True)
        self.btn_ai_parse.setText("✨ DeepSeek 智能解析")
        self.progress_bar.hide()
        QMessageBox.warning(self, "解析失败", f"AI 解析出错: {error_msg}\n请检查网络或配置。")
    
    def parse_content_regex(self):
        """本地正则解析（快速预览）"""
        text = self.text_edit.toPlainText()
        if not text:
            return
            
        # 简单的正则提取，作为 AI 的补充或快速预览
        url_pattern = r'https?://[a-zA-Z0-9\-._~:/?#[\]@!$&\'()*+,;=%]+'
        matches = list(re.finditer(url_pattern, text))
        
        if not matches and self.table.rowCount() > 0:
            return

        links = []
        seen_urls = set() # 正则模式下还是简单去重一下，避免刷屏，AI模式下由AI决定
        
        for match in matches:
            url = match.group()
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            # 简单标题提取
            start, end = match.span()
            context = text[max(0, start - 50):min(len(text), end + 50)]
            
            name = "新链接"
            title_match = re.search(r'《(.*?)》', context)
            if title_match:
                name = title_match.group(1)
            else:
                title_match = re.search(r'【(.*?)】', context)
                if title_match:
                     if "腾讯文档" not in title_match.group(1) and "金山文档" not in title_match.group(1):
                        name = title_match.group(1)
            
            category = self.guess_category(url)
            links.append({"name": name, "url": url, "category": category})
            
        self.populate_table(links)

    def populate_table(self, links):
        """填充表格"""
        self.table.setRowCount(0)
        self.parsed_links = links
        
        for link in links:
            name = link.get('name', '')
            url = link.get('url', '')
            category = link.get('category', '其他')
            
            self.add_row(name, url, category)
            
        self.update_status()

    def guess_category(self, url):
        """根据 URL 猜测分类"""
        if "docs.qq.com" in url:
            return "腾讯文档"
        elif "shimo.im" in url:
            return "石墨文档"
        elif "wjx.cn" in url:
            return "问卷星"
        elif "jinshuju" in url:
            return "金数据"
        elif "feishu.cn" in url:
            return "飞书"
        elif "kdocs.cn" in url:
            return "WPS"
        elif "wenjuan.com" in url:
            return "问卷网"
        return "其他"

    def add_row(self, name, url, category):
        """添加一行到表格"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # 名称（可编辑）
        name_item = QTableWidgetItem(name)
        self.table.setItem(row, 0, name_item)
        
        # URL（可编辑）
        url_item = QTableWidgetItem(url)
        self.table.setItem(row, 1, url_item)
        
        # 分类（可编辑）
        cat_item = QTableWidgetItem(category)
        self.table.setItem(row, 2, cat_item)
        
        # 操作按钮
        btn_del = QPushButton("删除")
        btn_del.setStyleSheet("color: red; border: none; background: transparent;")
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.clicked.connect(lambda: self.remove_row(row))
        self.table.setCellWidget(row, 3, btn_del)

    def add_empty_row(self):
        """手动添加空行"""
        self.add_row("", "", "其他")
        self.update_status()

    def remove_row(self, row):
        """删除行"""
        self.table.removeRow(row)
        self.update_status()
        
        # 重新绑定删除按钮
        for i in range(self.table.rowCount()):
            btn = self.table.cellWidget(i, 3)
            if btn:
                new_btn = QPushButton("删除")
                new_btn.setStyleSheet("color: red; border: none; background: transparent;")
                new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                new_btn.clicked.connect(lambda checked, r=i: self.remove_row(r))
                self.table.setCellWidget(i, 3, new_btn)

    def update_status(self):
        """更新状态标签"""
        count = self.table.rowCount()
        self.count_label.setText(f"共找到 {count} 个链接")
        self.btn_save.setEnabled(count > 0)

    def save_all(self):
        """保存所有链接"""
        count = self.table.rowCount()
        if count == 0:
            return
            
        success_count = 0
        updated_count = 0
        error_count = 0
        
        for i in range(count):
            name = self.table.item(i, 0).text().strip()
            url = self.table.item(i, 1).text().strip()
            category = self.table.item(i, 2).text().strip()
            
            if not url:
                continue
                
            if not name:
                name = "未命名链接"
            
            try:
                # 检查是否已存在（按当前用户筛选）
                existing_link = self.db_manager.get_link_by_url(url, user=self.current_user)
                if existing_link:
                    # 更新现有链接
                    self.db_manager.update_link(
                        existing_link.id,
                        name=name,
                        category=category,
                        status='active',  # 重新激活
                        description=f"批量导入更新 - {name}"
                    )
                    print(f"更新已存在链接: {url}")
                    updated_count += 1
                else:
                    # 创建新链接
                    self.db_manager.create_link(
                        name=name,
                        url=url,
                        user=self.current_user,
                        status='active',
                        category=category,
                        description=f"批量导入 - {name}"
                    )
                    success_count += 1
            except Exception as e:
                print(f"保存链接失败: {e}")
                error_count += 1
        
        msg = f"处理完成：\n新增 {success_count} 个\n更新 {updated_count} 个"
        if error_count > 0:
            msg += f"\n失败 {error_count} 个"
            QMessageBox.warning(self, "导入完成", msg)
        else:
            QMessageBox.information(self, "导入完成", msg)
            
        self.accept()


class LinkEditDialog(QDialog):
    """链接编辑对话框"""
    
    def __init__(self, parent=None, link: Link = None, current_user=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.link = link
        self.current_user = current_user
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        title = "编辑链接" if self.link else "新增链接"
        self.setWindowTitle(title)
        self.setGeometry(250, 250, 600, 400)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 表单
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入链接名称")
        if self.link:
            self.name_input.setText(self.link.name)
        form_layout.addRow("链接名称:*", self.name_input)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("输入完整 URL（如：https://example.com）")
        if self.link:
            self.url_input.setText(self.link.url)
        form_layout.addRow("URL:*", self.url_input)
        
        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("输入分类（如：测试、抖音、小红书）")
        if self.link:
            self.category_input.setText(self.link.category or "")
        form_layout.addRow("分类:", self.category_input)
        
        self.status_combo = QComboBox()
        self.status_combo.addItems(["激活", "归档", "已删除"])
        if self.link:
            status_index = {"active": 0, "archived": 1, "deleted": 2}.get(self.link.status, 0)
            self.status_combo.setCurrentIndex(status_index)
        form_layout.addRow("状态:", self.status_combo)
        
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("输入描述（可选）")
        if self.link:
            self.desc_input.setText(self.link.description or "")
        form_layout.addRow("描述:", self.desc_input)
        
        layout.addLayout(form_layout)
        
        # 提示
        hint_label = QLabel("* 必填项")
        hint_label.setStyleSheet("color: #999; font-size: 12px;")
        layout.addWidget(hint_label)
        
        layout.addStretch()
        
        # 按钮
        button_layout = QHBoxLayout()
        
        btn_save = QPushButton("💾 保存")
        btn_save.clicked.connect(self.save)
        btn_save.setStyleSheet("background-color: #667eea; color: white; padding: 10px;")
        button_layout.addWidget(btn_save)
        
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancel)
        
        layout.addLayout(button_layout)
    
    def save(self):
        """保存"""
        name = self.name_input.text().strip()
        url = self.url_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "警告", "请输入链接名称")
            return
        
        if not url:
            QMessageBox.warning(self, "警告", "请输入 URL")
            return
        
        if not url.startswith(('http://', 'https://')):
            QMessageBox.warning(self, "警告", "URL 必须以 http:// 或 https:// 开头")
            return
        
        category = self.category_input.text().strip() or None
        description = self.desc_input.text().strip() or None
        
        status_map = {
            "激活": "active",
            "归档": "archived",
            "已删除": "deleted"
        }
        status = status_map[self.status_combo.currentText()]
        
        try:
            if self.link:
                # 更新
                self.db_manager.update_link(
                    self.link.id,
                    name=name,
                    url=url,
                    category=category,
                    status=status,
                    description=description
                )
                QMessageBox.information(self, "成功", "链接已更新")
            else:
                # 新增
                self.db_manager.create_link(name, url, self.current_user, status, category, description)
                QMessageBox.information(self, "成功", "链接已创建")
            
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
