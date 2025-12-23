"""
消息中心模块
用于用户查看和处理系统通知、名片修改请求等
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QMessageBox, QFrame, QScrollArea, QDialog,
    QGraphicsDropShadowEffect, QTextEdit, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QIcon
import qtawesome as qta
from database import DatabaseManager, CardEditRequest, Notification
import json

# 颜色主题
COLORS = {
    'primary': '#667eea',
    'primary_light': '#8b9df0',
    'success': '#10b981',
    'danger': '#ef4444',
    'warning': '#f59e0b',
    'background': '#f8fafc',
    'surface': '#ffffff',
    'border': '#e2e8f0',
    'border_light': '#f1f5f9',
    'text_primary': '#1e293b',
    'text_secondary': '#64748b',
    'text_hint': '#94a3b8',
}


class CardEditApprovalDialog(QDialog):
    """名片修改审批对话框 (详情页)"""
    
    approved = pyqtSignal()  # 审批完成信号
    
    def __init__(self, request: CardEditRequest, parent=None):
        super().__init__(parent)
        self.request = request
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("请求详情")
        self.setFixedSize(700, 800)
        self.setStyleSheet("""
            QDialog { background-color: #F9FAFB; }
            QLabel { font-family: 'Segoe UI', sans-serif; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # === 1. Header ===
        header = QWidget()
        header.setFixedHeight(120)
        # 移除底部分割线，用阴影代替
        header.setStyleSheet("background-color: white;")
        
        header_shadow = QGraphicsDropShadowEffect(header)
        header_shadow.setBlurRadius(10)
        header_shadow.setColor(QColor(0, 0, 0, 5))
        header_shadow.setOffset(0, 2)
        header.setGraphicsEffect(header_shadow)
        
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(40, 30, 40, 30)
        header_layout.setSpacing(12)
        
        # Title Row
        title_row = QHBoxLayout()
        title_row.setSpacing(16)
        
        # Avatar/Icon
        icon_lbl = QLabel("✏️")
        icon_lbl.setFixedSize(48, 48)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("""
            background-color: #EEF2FF;
            font-size: 24px;
            border-radius: 24px;
        """)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        main_title = QLabel("名片修改请求")
        main_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #111827;")
        
        sub_title = QLabel(f"由 {self.request.admin.username if self.request.admin else '未知'} 提交 • {self.request.created_at.strftime('%Y-%m-%d %H:%M')}")
        sub_title.setStyleSheet("font-size: 13px; color: #6B7280; font-weight: 500;")
        
        text_layout.addWidget(main_title)
        text_layout.addWidget(sub_title)
        
        title_row.addWidget(icon_lbl)
        title_row.addLayout(text_layout)
        title_row.addStretch()
        
        header_layout.addLayout(title_row)
        layout.addWidget(header)
        
        # === 2. Content Area ===
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 8px; background: transparent; }
            QScrollBar::handle:vertical { background: #D1D5DB; border-radius: 4px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 32, 40, 40)
        content_layout.setSpacing(32)
        
        # 变更内容区块
        content_layout.addWidget(self._create_section_header("基础信息变更"))
        
        # Name Comparison
        content_layout.addWidget(self._create_compare_row(
            "名片名称", 
            self.request.original_name, 
            self.request.modified_name
        ))
        
        # Category Comparison
        content_layout.addWidget(self._create_compare_row(
            "分类", 
            self.request.original_category or "默认分类", 
            self.request.modified_category or "默认分类"
        ))
        
        # Description Comparison
        content_layout.addWidget(self._create_compare_row(
            "描述", 
            self.request.original_description or "无", 
            self.request.modified_description or "无"
        ))
        
        # Configs
        content_layout.addSpacing(16)
        content_layout.addWidget(self._create_section_header("配置项变更"))
        content_layout.addWidget(self._create_configs_compare())
        
        # Admin Comment
        if self.request.admin_comment:
            content_layout.addSpacing(16)
            content_layout.addWidget(self._create_section_header("备注信息"))
            
            comment_box = QFrame()
            comment_box.setStyleSheet("""
                background-color: #FFFBEB; 
                border: 1px solid #FCD34D; 
                border-radius: 8px;
            """)
            c_layout = QVBoxLayout(comment_box)
            c_layout.setContentsMargins(16, 12, 16, 12)
            
            comment_lbl = QLabel(self.request.admin_comment)
            comment_lbl.setWordWrap(True)
            comment_lbl.setStyleSheet("color: #92400E; font-size: 13px; line-height: 1.4;")
            c_layout.addWidget(comment_lbl)
            
            content_layout.addWidget(comment_box)
            
        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # === 3. Footer Actions ===
        footer = QFrame()
        footer.setFixedHeight(80)
        # 移除上边框，改用阴影
        footer.setStyleSheet("background: white;")
        
        footer_shadow = QGraphicsDropShadowEffect(footer)
        footer_shadow.setBlurRadius(16)
        footer_shadow.setColor(QColor(0, 0, 0, 6))
        footer_shadow.setOffset(0, -4) # 向上阴影
        footer.setGraphicsEffect(footer_shadow)
        
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(40, 0, 40, 0)
        footer_layout.setSpacing(16)
        
        footer_layout.addStretch()
        
        # 只有待处理状态才显示操作按钮
        if self.request.status == 'pending':
            reject_btn = QPushButton("拒绝请求")
            reject_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            reject_btn.setFixedSize(100, 40)
            reject_btn.setStyleSheet("""
                QPushButton {
                    background: white;
                    color: #DC2626;
                    border: 1px solid #FECACA;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 13px;
                }
                QPushButton:hover { 
                    background: #FEF2F2; 
                    border-color: #FCA5A5;
                }
            """)
            reject_btn.clicked.connect(self.reject_request)
            
            approve_btn = QPushButton("同意修改")
            approve_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            approve_btn.setFixedSize(100, 40)
            approve_btn.setStyleSheet("""
                QPushButton {
                    background: #111827;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 13px;
                }
                QPushButton:hover { background: #1F2937; }
                QPushButton:pressed { background: black; }
            """)
            approve_btn.clicked.connect(self.approve_request)
            
            footer_layout.addWidget(reject_btn)
            footer_layout.addWidget(approve_btn)
        else:
            status_text = "已同意" if self.request.status == 'approved' else "已拒绝"
            status_color = "#059669" if self.request.status == 'approved' else "#DC2626"
            status_lbl = QLabel(f"该请求{status_text}")
            status_lbl.setStyleSheet(f"color: {status_color}; font-weight: 600; font-size: 14px;")
            footer_layout.addWidget(status_lbl)
            
            close_btn = QPushButton("关闭")
            close_btn.setFixedSize(100, 40)
            close_btn.setStyleSheet("""
                QPushButton {
                    background: white;
                    border: 1px solid #E5E7EB;
                    border-radius: 8px;
                    color: #374151;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton:hover { background: #F9FAFB; }
            """)
            close_btn.clicked.connect(self.accept)
            footer_layout.addWidget(close_btn)
        
        layout.addWidget(footer)

    def _create_section_header(self, title):
        lbl = QLabel(title)
        lbl.setStyleSheet("""
            color: #6B7280; 
            font-size: 12px; 
            font-weight: 700; 
            letter-spacing: 0.5px;
            text-transform: uppercase;
        """)
        return lbl

    def _create_compare_row(self, label, old_val, new_val):
        """创建整洁的对比行"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Label
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #374151; font-size: 13px; font-weight: 600;")
        layout.addWidget(lbl)
        
        # Comparison Box
        box = QFrame()
        # 移除边框，改用极浅背景和圆角
        box.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: none; 
                border-radius: 8px;
            }
        """)
        # Box Shadow
        box_shadow = QGraphicsDropShadowEffect(box)
        box_shadow.setBlurRadius(8)
        box_shadow.setColor(QColor(0, 0, 0, 4))
        box_shadow.setOffset(0, 1)
        box.setGraphicsEffect(box_shadow)

        box_layout = QHBoxLayout(box)
        box_layout.setContentsMargins(16, 12, 16, 12)
        box_layout.setSpacing(0)
        
        # Old Value
        old_lbl = QLabel(old_val or "-")
        old_lbl.setStyleSheet("color: #6B7280; font-size: 14px;")
        old_lbl.setWordWrap(True)
        
        # Arrow
        arrow = QLabel("→")
        arrow.setFixedWidth(40)
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow.setStyleSheet("color: #9CA3AF; font-size: 16px;")
        
        # New Value
        is_changed = old_val != new_val
        new_lbl = QLabel(new_val or "-")
        new_lbl.setStyleSheet(f"color: {'#059669' if is_changed else '#111827'}; font-size: 14px; font-weight: {'600' if is_changed else '400'};")
        new_lbl.setWordWrap(True)
        
        box_layout.addWidget(old_lbl, 1)
        box_layout.addWidget(arrow)
        box_layout.addWidget(new_lbl, 1)
        
        layout.addWidget(box)
        return container
    
    def _create_configs_compare(self):
        """创建配置项对比 - Clean Table Style"""
        card = QFrame()
        # 移除边框，优化表格样式
        card.setStyleSheet("""
            QFrame {
                background: white;
                border: none;
                border-radius: 8px;
            }
        """)
        
        card_shadow = QGraphicsDropShadowEffect(card)
        card_shadow.setBlurRadius(8)
        card_shadow.setColor(QColor(0, 0, 0, 4))
        card_shadow.setOffset(0, 1)
        card.setGraphicsEffect(card_shadow)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 解析配置
        original_configs = json.loads(self.request.original_configs) if self.request.original_configs else []
        modified_configs = json.loads(self.request.modified_configs) if self.request.modified_configs else []
        
        original_dict = {c['key']: c['value'] for c in original_configs}
        modified_dict = {c['key']: c['value'] for c in modified_configs}
        
        all_keys = set(original_dict.keys()) | set(modified_dict.keys())
        
        if not all_keys:
            empty_lbl = QLabel("无配置项变更")
            empty_lbl.setStyleSheet("color: #9CA3AF; font-size: 13px; padding: 20px;")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(empty_lbl)
            return card
        
        sorted_keys = sorted(all_keys)
        for i, key in enumerate(sorted_keys):
            old_val = original_dict.get(key, "")
            new_val = modified_dict.get(key, "")
            
            row = QWidget()
            row.setStyleSheet("background-color: white;" if i % 2 == 0 else "background-color: #F9FAFB;")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(16, 12, 16, 12)
            
            # Key
            key_lbl = QLabel(key)
            key_lbl.setFixedWidth(140)
            key_lbl.setStyleSheet("color: #4B5563; font-weight: 600; font-size: 12px;")
            row_layout.addWidget(key_lbl)
            
            # Status Badge
            status_lbl = QLabel()
            status_lbl.setFixedWidth(50)
            status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            if key not in original_dict:
                status_lbl.setText("新增")
                status_lbl.setStyleSheet("color: #059669; background: #D1FAE5; border-radius: 4px; font-size: 10px; padding: 2px;")
            elif key not in modified_dict:
                status_lbl.setText("删除")
                status_lbl.setStyleSheet("color: #DC2626; background: #FEE2E2; border-radius: 4px; font-size: 10px; padding: 2px;")
            elif old_val != new_val:
                status_lbl.setText("修改")
                status_lbl.setStyleSheet("color: #D97706; background: #FEF3C7; border-radius: 4px; font-size: 10px; padding: 2px;")
            else:
                status_lbl.setText("未变")
                status_lbl.setStyleSheet("color: #9CA3AF; font-size: 10px;")
            
            row_layout.addWidget(status_lbl)
            
            # Values
            val_layout = QVBoxLayout()
            val_layout.setSpacing(2)
            
            if old_val != new_val:
                # Show change
                if old_val:
                    old_txt = QLabel(f"{old_val}")
                    old_txt.setStyleSheet("color: #9CA3AF; font-size: 11px; text-decoration: line-through;")
                    val_layout.addWidget(old_txt)
                
                new_txt = QLabel(f"{new_val}")
                new_txt.setStyleSheet("color: #111827; font-size: 12px; font-weight: 500;")
                new_txt.setWordWrap(True)
                val_layout.addWidget(new_txt)
            else:
                val_txt = QLabel(f"{new_val}")
                val_txt.setStyleSheet("color: #374151; font-size: 12px;")
                val_layout.addWidget(val_txt)
                
            row_layout.addLayout(val_layout)
            
            layout.addWidget(row)
            
            # Separator
            if i < len(sorted_keys) - 1:
                line = QFrame()
                line.setFixedHeight(1)
                line.setStyleSheet("background: #E5E7EB;")
                layout.addWidget(line)
        
        return card
    
    def approve_request(self):
        """同意修改请求"""
        confirm = QMessageBox.question(
            self, "确认同意",
            "确定要同意此修改请求吗？\n修改将立即生效。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            if DatabaseManager.approve_card_edit_request(str(self.request.id)):
                QMessageBox.information(self, "成功", "已同意修改，名片已更新")
                self.approved.emit()
                self.accept()
            else:
                QMessageBox.critical(self, "错误", "操作失败")
    
    def reject_request(self):
        """拒绝修改请求"""
        confirm = QMessageBox.question(
            self, "确认拒绝",
            "确定要拒绝此修改请求吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            if DatabaseManager.reject_card_edit_request(str(self.request.id)):
                QMessageBox.information(self, "已拒绝", "已拒绝此修改请求")
                self.approved.emit()
                self.accept()
            else:
                QMessageBox.critical(self, "错误", "操作失败")


class MessageBadge(QWidget):
    """消息徽章组件 - 显示未读消息数"""
    
    clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.count = 0
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.badge = QPushButton()
        self.badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.badge.setFixedSize(24, 24)
        self.badge.clicked.connect(self.clicked.emit)
        self.update_count(0)
        
        layout.addWidget(self.badge)
        
    def update_count(self, count):
        self.count = count
        if count > 0:
            self.badge.setText(str(count) if count < 100 else "99+")
            self.badge.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['danger']};
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-size: 11px;
                    font-weight: 700;
                }}
                QPushButton:hover {{ background: #dc2626; }}
            """)
            self.show()
        else:
            self.hide()


class MessageCenterDialog(QDialog):
    """消息中心对话框"""
    
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        
        # 分页相关
        self.current_page = 1
        self.page_size = 10
        self.total_count = 0
        self.total_pages = 1
        
        self.init_ui()
        self.load_messages()
        
    def init_ui(self):
        self.setWindowTitle("消息中心")
        self.setFixedSize(640, 820)
        self.setStyleSheet("""
            QDialog { 
                background-color: #F9FAFB;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QWidget()
        header.setFixedHeight(110)
        header.setStyleSheet("background-color: transparent;")
        
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(32, 36, 32, 12)
        header_layout.setSpacing(6)
        
        title_row = QHBoxLayout()
        
        title_lbl = QLabel("消息中心")
        title_lbl.setStyleSheet("""
            color: #111827; 
            font-size: 26px; 
            font-weight: 800; 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            letter-spacing: -0.5px;
        """)
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        
        # 标记全部已读按钮
        mark_read_btn = QPushButton("全部已读")
        mark_read_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        mark_read_btn.setStyleSheet("""
            QPushButton {
                color: #667eea;
                background: transparent;
                border: none;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover { color: #5568d3; }
        """)
        mark_read_btn.clicked.connect(self.mark_all_read)
        title_row.addWidget(mark_read_btn)
        
        header_layout.addLayout(title_row)
        
        subtitle_lbl = QLabel("查看您的所有通知和待办事项")
        subtitle_lbl.setStyleSheet("""
            color: #6B7280; 
            font-size: 14px; 
            font-weight: 500;
        """)
        header_layout.addWidget(subtitle_lbl)
        
        layout.addWidget(header)
        
        # 列表区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 6px; background: transparent; }
            QScrollBar::handle:vertical { background: #E5E7EB; border-radius: 3px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        
        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(32, 10, 32, 16)
        self.list_layout.setSpacing(12)
        
        scroll.setWidget(self.list_widget)
        layout.addWidget(scroll)
        
        # 分页控件
        pagination_container = QFrame()
        pagination_container.setFixedHeight(50)
        pagination_container.setStyleSheet("background: transparent;")
        pagination_layout = QHBoxLayout(pagination_container)
        pagination_layout.setContentsMargins(32, 0, 32, 0)
        
        pagination_layout.addStretch()
        
        # 上一页按钮
        self.prev_btn = QPushButton("‹")
        self.prev_btn.setFixedSize(32, 32)
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background: white;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                color: #374151;
                font-size: 18px;
                font-weight: 600;
            }
            QPushButton:hover { background: #F9FAFB; border-color: #D1D5DB; }
            QPushButton:disabled { color: #D1D5DB; background: #F9FAFB; }
        """)
        self.prev_btn.clicked.connect(self.prev_page)
        pagination_layout.addWidget(self.prev_btn)
        
        pagination_layout.addSpacing(8)
        
        # 页码显示
        self.page_label = QLabel("1 / 1")
        self.page_label.setStyleSheet("""
            color: #6B7280;
            font-size: 13px;
            font-weight: 500;
            padding: 0 12px;
        """)
        pagination_layout.addWidget(self.page_label)
        
        pagination_layout.addSpacing(8)
        
        # 下一页按钮
        self.next_btn = QPushButton("›")
        self.next_btn.setFixedSize(32, 32)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background: white;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                color: #374151;
                font-size: 18px;
                font-weight: 600;
            }
            QPushButton:hover { background: #F9FAFB; border-color: #D1D5DB; }
            QPushButton:disabled { color: #D1D5DB; background: #F9FAFB; }
        """)
        self.next_btn.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.next_btn)
        
        pagination_layout.addStretch()
        
        layout.addWidget(pagination_container)
        
        # 底部 - Minimal Footer
        footer = QFrame()
        footer.setFixedHeight(60)
        footer.setStyleSheet("background: transparent;")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(32, 0, 32, 16)
        
        footer_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.setMinimumWidth(120)
        close_btn.setFixedHeight(40)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #F3F4F6;
                color: #374151;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
                padding: 8px 24px;
            }
            QPushButton:hover { 
                background: #E5E7EB; 
                color: #111827;
            }
        """)
        close_btn.clicked.connect(self.accept)
        footer_layout.addWidget(close_btn)
        
        layout.addWidget(footer)
    
    def load_messages(self):
        """加载消息列表"""
        # 清空列表
        while self.list_layout.count():
            child = self.list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # 获取总数
        all_notifications = DatabaseManager.get_user_notifications(user=self.user, limit=1000)
        self.total_count = len(all_notifications) if all_notifications else 0
        self.total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
        
        # 确保当前页有效
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
        if self.current_page < 1:
            self.current_page = 1
        
        # 更新分页控件
        self.update_pagination()
        
        if not all_notifications:
            empty_lbl = QLabel("暂无消息")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("color: #9CA3AF; font-size: 14px; padding: 60px;")
            self.list_layout.addWidget(empty_lbl)
            self.list_layout.addStretch()
            return
        
        # 计算分页
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = start_idx + self.page_size
        page_notifications = all_notifications[start_idx:end_idx]
        
        for notif in page_notifications:
            card = self._create_message_card(notif)
            self.list_layout.addWidget(card)
        
        self.list_layout.addStretch()
    
    def update_pagination(self):
        """更新分页控件状态"""
        self.page_label.setText(f"{self.current_page} / {self.total_pages}")
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < self.total_pages)
    
    def prev_page(self):
        """上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_messages()
    
    def next_page(self):
        """下一页"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.load_messages()
    
    def _create_message_card(self, notification: Notification):
        """创建消息卡片"""
        card = QFrame()
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.mousePressEvent = lambda e, n=notification: self.handle_message_click(n)
        
        # 根据已读/未读状态设置样式
        bg_color = "white"
        border = "none"
        
        if not notification.is_read:
            bg_color = "#F5F7FF" # 浅蓝背景表示未读
            
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 12px;
                border: {border};
            }}
            QFrame:hover {{
                background-color: #F8FAFC;
            }}
        """)
        
        # Soft shadow
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 8))
        shadow.setOffset(0, 2)
        card.setGraphicsEffect(shadow)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Icon based on type
        icon_char = "🔔"
        icon_bg = "#F3F4F6"
        icon_fg = "#4B5563"
        status_widget = None
        
        if notification.type == 'card_edit':
            icon_char = "📝"
            icon_bg = "#EEF2FF"
            icon_fg = "#6366F1"
            
            # 获取关联的名片修改请求状态
            if notification.related_id:
                try:
                    req = DatabaseManager.get_card_edit_request_by_id(notification.related_id)
                    if req:
                        status_text = "未知"
                        status_bg = "#F3F4F6"
                        status_fg = "#6B7280"
                        
                        if req.status == 'pending':
                            status_text = "待审批"
                            status_bg = "#FFF7ED"
                            status_fg = "#C2410C"
                        elif req.status == 'approved':
                            status_text = "已通过"
                            status_bg = "#ECFDF5"
                            status_fg = "#059669"
                        elif req.status == 'rejected':
                            status_text = "已拒绝"
                            status_bg = "#FEF2F2"
                            status_fg = "#DC2626"
                            
                        status_widget = QLabel(status_text)
                        status_widget.setStyleSheet(f"""
                            background-color: {status_bg};
                            color: {status_fg};
                            padding: 2px 8px;
                            border-radius: 6px;
                            font-size: 11px;
                            font-weight: 600;
                        """)
                except Exception:
                    pass

        elif notification.type == 'system':
            icon_char = "📢"
            icon_bg = "#FEF3C7"
            icon_fg = "#D97706"
        
        elif notification.type == 'field_push':
            icon_char = "✨"
            icon_bg = "#ECFDF5"
            icon_fg = "#10B981"
            
            # 显示是否已处理
            if notification.is_read:
                status_widget = QLabel("已处理")
                status_widget.setStyleSheet("""
                    background-color: #F3F4F6;
                    color: #6B7280;
                    padding: 2px 8px;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 600;
                """)
            else:
                status_widget = QLabel("待确认")
                status_widget.setStyleSheet("""
                    background-color: #ECFDF5;
                    color: #059669;
                    padding: 2px 8px;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: 600;
                """)
            
        icon_lbl = QLabel(icon_char)
        icon_lbl.setFixedSize(40, 40)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(f"""
            background-color: {icon_bg}; 
            color: {icon_fg}; 
            border-radius: 20px; 
            font-size: 18px;
        """)
        layout.addWidget(icon_lbl)
        
        # Content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)
        
        title_row = QHBoxLayout()
        title_lbl = QLabel(notification.title)
        title_lbl.setStyleSheet(f"""
            font-size: 15px; 
            font-weight: 700; 
            color: #111827;
        """)
        title_row.addWidget(title_lbl)
        
        # 显示状态标签
        if status_widget:
            title_row.addWidget(status_widget)
        
        if not notification.is_read:
            badge = QLabel("NEW")
            badge.setStyleSheet("""
                color: #DC2626; 
                background: #FEE2E2; 
                padding: 2px 6px; 
                border-radius: 4px; 
                font-size: 10px; 
                font-weight: 700;
            """)
            title_row.addWidget(badge)
        title_row.addStretch()
        
        content_lbl = QLabel(notification.content)
        content_lbl.setWordWrap(True)
        content_lbl.setStyleSheet("color: #6B7280; font-size: 13px; line-height: 1.4;")
        
        time_lbl = QLabel(notification.created_at.strftime('%m-%d %H:%M'))
        time_lbl.setStyleSheet("color: #9CA3AF; font-size: 11px; margin-top: 4px;")
        
        content_layout.addLayout(title_row)
        content_layout.addWidget(content_lbl)
        content_layout.addWidget(time_lbl)
        
        layout.addLayout(content_layout)
        
        # Arrow (更加隐蔽)
        arrow = QLabel("›")
        arrow.setStyleSheet("color: #E5E7EB; font-size: 20px; font-weight: 300;")
        layout.addWidget(arrow)
        
        return card
    
    def handle_message_click(self, notification: Notification):
        """处理消息点击"""
        # 根据类型处理点击
        if notification.type == 'card_edit' and notification.related_id:
            # 标记为已读
            if not notification.is_read:
                DatabaseManager.mark_notification_read(str(notification.id))
                notification.is_read = True
                self.load_messages()
                
            request = DatabaseManager.get_card_edit_request_by_id(notification.related_id)
            if request:
                dialog = CardEditApprovalDialog(request, self)
                dialog.approved.connect(self.load_messages) # 如果处理了，刷新列表
                dialog.exec()
            else:
                QMessageBox.warning(self, "提示", "该请求已不存在或已被删除")
        
        elif notification.type == 'field_push' and notification.related_id:
            # 对于字段推送，只有未读的才弹出确认框
            if not notification.is_read:
                # 延迟导入避免循环依赖
                from .main_window import FieldPushReceivedDialog
                
                dialog = FieldPushReceivedDialog(notification, self.parent())
                if dialog.exec():
                    # 用户已处理，刷新列表
                    self.load_messages()
            else:
                QMessageBox.information(self, "提示", "此字段推送已处理")
        
        else:
            # 其他类型消息仅标记已读
            if not notification.is_read:
                DatabaseManager.mark_notification_read(str(notification.id))
                notification.is_read = True
                self.load_messages()
    
    def mark_all_read(self):
        """全部已读"""
        if DatabaseManager.mark_all_notifications_read(self.user):
            self.load_messages()
