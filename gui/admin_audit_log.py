"""
审核记录管理模块
用于管理员查看和处理名片修改请求
采用现代化玻璃拟态设计风格
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, 
    QMessageBox, QLineEdit, QFrame, QAbstractItemView, 
    QGraphicsDropShadowEffect, QDialog, QScrollArea, QComboBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor, QBrush
from database import DatabaseManager, CardEditRequest
from gui.styles import COLORS
from gui.icons import Icons
import datetime
import json

# 扩展颜色系统 - 与 admin_card_manager 保持一致
PREMIUM_COLORS = {
    **COLORS,
    # 渐变色组
    'gradient_blue_start': '#667eea',
    'gradient_blue_end': '#764ba2',
    'gradient_green_start': '#11998e',
    'gradient_green_end': '#38ef7d',
    'gradient_orange_start': '#f093fb',
    'gradient_orange_end': '#f5576c',
    'gradient_purple_start': '#4facfe',
    'gradient_purple_end': '#00f2fe',
    'gradient_gold_start': '#f7971e',
    'gradient_gold_end': '#ffd200',
    
    # 玻璃效果
    'glass_bg': 'rgba(255, 255, 255, 0.85)',
    'glass_border': 'rgba(255, 255, 255, 0.6)',
    'glass_shadow': 'rgba(31, 38, 135, 0.07)',
    
    # 深色点缀
    'dark_accent': '#1a1a2e',
    'text_heading': '#2d3748',
    'text_body': '#4a5568',
    'text_hint': '#a0aec0',
    
    # 功能色
    'mint': '#00d9a6',
    'coral': '#ff6b6b',
    'lavender': '#a29bfe',
    'sky': '#74b9ff',
}

class GlassFrame(QFrame):
    """玻璃拟态框架"""
    
    def __init__(self, parent=None, opacity=0.9, radius=24, hover_effect=False):
        super().__init__(parent)
        self.opacity = opacity
        self.radius = radius
        self.hover_effect = hover_effect
        self._setup_style()
    
    def _setup_style(self):
        self.setStyleSheet(f"""
            GlassFrame {{
                background: rgba(255, 255, 255, {self.opacity});
                border: 1px solid rgba(255, 255, 255, 0.8);
                border-radius: {self.radius}px;
            }}
            GlassFrame:hover {{
                background: rgba(255, 255, 255, {min(1.0, self.opacity + 0.05)});
                border-color: rgba(255, 255, 255, 1.0);
            }}
        """ if self.hover_effect else f"""
            GlassFrame {{
                background: rgba(255, 255, 255, {self.opacity});
                border: 1px solid rgba(255, 255, 255, 0.6);
                border-radius: {self.radius}px;
            }}
        """)
        
        # 添加高级阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(31, 38, 135, 15))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)

class GradientButton(QPushButton):
    """渐变按钮"""
    
    def __init__(self, text, start_color, end_color, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(44)
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {start_color}, stop:1 {end_color});
                color: white;
                border: none;
                border-radius: 22px;
                font-weight: 600;
                font-size: 14px;
                padding: 0 24px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {end_color}, stop:1 {start_color});
            }}
            QPushButton:pressed {{
                padding-top: 2px;
            }}
        """)

class CompactStatWidget(QFrame):
    """紧凑型统计组件"""
    def __init__(self, title, value, icon, color_start, color_end, parent=None):
        super().__init__(parent)
        self.value = value
        self._setup_ui(title, icon, color_start, color_end)
        
    def _setup_ui(self, title, icon, color_start, color_end):
        self.setFixedSize(140, 50)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)
        
        # 背景样式
        self.setStyleSheet(f"""
            CompactStatWidget {{
                background: white;
                border-radius: 12px;
                border: 1px solid {PREMIUM_COLORS['border_light']};
            }}
        """)
        
        # 图标
        icon_lbl = QLabel(icon)
        icon_lbl.setFixedSize(32, 32)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {color_start}, stop:1 {color_end});
            color: white;
            border-radius: 8px;
            font-size: 16px;
        """)
        layout.addWidget(icon_lbl)
        
        # 文本
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.value_lbl = QLabel(str(self.value))
        self.value_lbl.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {PREMIUM_COLORS['text_heading']};")
        text_layout.addWidget(self.value_lbl)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 10px; color: {PREMIUM_COLORS['text_hint']};")
        text_layout.addWidget(title_lbl)
        
        layout.addLayout(text_layout)
        
    def update_value(self, value):
        self.value = value
        self.value_lbl.setText(str(value))

class AdminAuditLogDetailDialog(QDialog):
    """审核记录详情对话框"""
    
    def __init__(self, request: CardEditRequest, parent=None):
        super().__init__(parent)
        self.request = request
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("审核记录详情")
        self.setFixedSize(500, 650)
        self.setStyleSheet("QDialog { background-color: #f8fafc; }")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setFixedHeight(100)
        
        # 根据状态设置不同的Header背景色
        if self.request.status == 'approved':
            bg_start, bg_end = PREMIUM_COLORS['gradient_green_start'], PREMIUM_COLORS['gradient_green_end']
            status_text = "已通过"
            icon = "✅"
        elif self.request.status == 'rejected':
            bg_start, bg_end = PREMIUM_COLORS['coral'], '#ff8787'
            status_text = "已拒绝"
            icon = "❌"
        else:
            bg_start, bg_end = PREMIUM_COLORS['gradient_orange_start'], PREMIUM_COLORS['gradient_orange_end']
            status_text = "待审批"
            icon = "⏳"
            
        header.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {bg_start}, stop:1 {bg_end});
            }}
        """)
        
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(30, 20, 30, 20)
        
        title_row = QHBoxLayout()
        title_lbl = QLabel(f"{icon} {status_text}")
        title_lbl.setStyleSheet("color: white; font-size: 22px; font-weight: 800;")
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        header_layout.addLayout(title_row)
        
        sub_lbl = QLabel(f"申请ID: {self.request.id}")
        sub_lbl.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 12px;")
        header_layout.addWidget(sub_lbl)
        
        layout.addWidget(header)
        
        # Content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(16)
        
        # 基本信息卡片
        info_card = self._create_section("基本信息")
        info_layout = info_card.layout()
        
        info_layout.addWidget(self._create_info_row("目标名片", self.request.card.name if self.request.card else self.request.original_name))
        info_layout.addWidget(self._create_info_row("所属用户", self.request.user.username if self.request.user else "未知"))
        info_layout.addWidget(self._create_info_row("申请管理员", self.request.admin.username if self.request.admin else "未知"))
        info_layout.addWidget(self._create_info_row("提交时间", self.request.created_at))
        if self.request.processed_at:
            info_layout.addWidget(self._create_info_row("处理时间", self.request.processed_at))
            
        content_layout.addWidget(info_card)
        
        # 备注信息
        if self.request.admin_comment or self.request.user_comment:
            comment_card = self._create_section("备注信息")
            c_layout = comment_card.layout()
            if self.request.admin_comment:
                c_layout.addWidget(self._create_info_row("管理员备注", self.request.admin_comment))
            if self.request.user_comment:
                c_layout.addWidget(self._create_info_row("用户反馈", self.request.user_comment))
            content_layout.addWidget(comment_card)
            
        # 变更内容
        change_card = self._create_section("变更摘要")
        ch_layout = change_card.layout()
        
        if self.request.original_name != self.request.modified_name:
            ch_layout.addWidget(self._create_change_row("名片名称", self.request.original_name, self.request.modified_name))
            
        if self.request.original_category != self.request.modified_category:
            ch_layout.addWidget(self._create_change_row("分类", self.request.original_category, self.request.modified_category))
            
        ch_layout.addWidget(QLabel("详细配置变更请在名片详情中查看"))
        content_layout.addWidget(change_card)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # Footer
        footer = QFrame()
        footer.setStyleSheet("background: white; border-top: 1px solid #e2e8f0;")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 16, 20, 16)
        
        if self.request.status == 'pending':
            del_btn = QPushButton("撤销申请")
            del_btn.setStyleSheet(f"color: {PREMIUM_COLORS['coral']}; background: transparent; font-weight: 600; border: none;")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(self.delete_request)
            footer_layout.addWidget(del_btn)
            
        footer_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.setFixedSize(80, 36)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PREMIUM_COLORS['surface']};
                border: 1px solid {PREMIUM_COLORS['border']};
                border-radius: 18px;
                color: {PREMIUM_COLORS['text_body']};
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {PREMIUM_COLORS['background']}; }}
        """)
        close_btn.clicked.connect(self.accept)
        footer_layout.addWidget(close_btn)
        
        layout.addWidget(footer)
        
    def _create_section(self, title):
        frame = QFrame()
        frame.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e2e8f0;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_heading']}; font-weight: 700; font-size: 14px;")
        layout.addWidget(title_lbl)
        
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: #f1f5f9;")
        layout.addWidget(line)
        
        return frame
        
    def _create_info_row(self, label, value):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        l_lbl = QLabel(label)
        l_lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_hint']}; font-size: 13px;")
        l_lbl.setFixedWidth(80)
        
        v_lbl = QLabel(str(value) if value else "-")
        v_lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-size: 13px; font-weight: 500;")
        v_lbl.setWordWrap(True)
        
        layout.addWidget(l_lbl)
        layout.addWidget(v_lbl)
        return container
        
    def _create_change_row(self, label, old, new):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        l_lbl = QLabel(label)
        l_lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_heading']}; font-weight: 600; font-size: 12px;")
        layout.addWidget(l_lbl)
        
        row = QHBoxLayout()
        old_lbl = QLabel(old)
        old_lbl.setStyleSheet("color: #9ca3af; text-decoration: line-through;")
        
        arrow = QLabel("→")
        arrow.setStyleSheet("color: #cbd5e1;")
        
        new_lbl = QLabel(new)
        new_lbl.setStyleSheet(f"color: {PREMIUM_COLORS['gradient_blue_start']}; font-weight: 600;")
        
        row.addWidget(old_lbl)
        row.addWidget(arrow)
        row.addWidget(new_lbl)
        row.addStretch()
        
        layout.addLayout(row)
        return container

    def delete_request(self):
        confirm = QMessageBox.question(
            self, "确认撤销",
            "确定要撤销此修改申请吗？\n撤销后用户将不再看到此请求。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            if DatabaseManager.delete_card_edit_request(self.request.id):
                QMessageBox.information(self, "成功", "已撤销申请")
                self.accept()
            else:
                QMessageBox.critical(self, "错误", "操作失败")

class AdminAuditLogManager(QWidget):
    """管理员审核记录页面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.current_page = 1
        self.page_size = 15
        self.total_records = 0
        self.total_pages = 1
        self.stat_widgets = {}
        self.init_ui()
        
    def init_ui(self):
        # 主背景
        self.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0.5, y2:1,
                    stop:0 #f8fafc, 
                    stop:0.6 #f1f5f9,
                    stop:1 #eef2f7);
            }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)
        
        # === Header ===
        self._create_header(main_layout)
        
        # === Main Content ===
        self._create_main_card(main_layout)
        
        self.load_data()
        
    def _create_header(self, layout):
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)
        
        title_label = QLabel("审核记录中心")
        title_label.setStyleSheet(f"""
            font-size: 24px; 
            font-weight: 800; 
            color: {PREMIUM_COLORS['text_heading']};
            background: transparent;
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addSpacing(16)
        
        # Stats
        stats_data = [
            ("待审批", 0, "⏳", PREMIUM_COLORS['gradient_orange_start'], PREMIUM_COLORS['gradient_orange_end']),
            ("已通过", 0, "✅", PREMIUM_COLORS['gradient_green_start'], PREMIUM_COLORS['gradient_green_end']),
            ("已拒绝", 0, "❌", PREMIUM_COLORS['coral'], '#ff8787'),
        ]
        
        for title, value, icon, start, end in stats_data:
            widget = CompactStatWidget(title, value, icon, start, end)
            self.stat_widgets[title] = widget
            header_layout.addWidget(widget)
            
        header_layout.addStretch()
        
        refresh_btn = GradientButton(
            "刷新数据",
            PREMIUM_COLORS['gradient_blue_start'],
            PREMIUM_COLORS['gradient_blue_end']
        )
        refresh_btn.setFixedSize(120, 40)
        refresh_btn.clicked.connect(self.load_data)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
    def _create_main_card(self, layout):
        card = GlassFrame(opacity=1.0, radius=16)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        
        # Toolbar
        toolbar = QFrame()
        toolbar.setFixedHeight(56)
        toolbar.setStyleSheet(f"border-bottom: 1px solid {PREMIUM_COLORS['border_light']}; background: transparent;")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 0, 16, 0)
        
        # Filter
        self.status_filter = QComboBox()
        self.status_filter.addItems(["全部状态", "待审批", "已通过", "已拒绝"])
        self.status_filter.setFixedSize(100, 32)
        self.status_filter.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid {PREMIUM_COLORS['border_light']};
                border-radius: 6px;
                padding: 0 10px;
                background: white;
            }}
        """)
        self.status_filter.currentTextChanged.connect(self.on_search)
        toolbar_layout.addWidget(self.status_filter)
        
        # Search
        search_container = QFrame()
        search_container.setFixedSize(260, 32)
        search_container.setStyleSheet(f"""
            QFrame {{
                background: {PREMIUM_COLORS['background']};
                border-radius: 16px;
            }}
        """)
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(10, 0, 10, 0)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索名片名称或用户名...")
        self.search_input.setStyleSheet("border: none; background: transparent;")
        self.search_input.textChanged.connect(self.on_search)
        search_layout.addWidget(QLabel("🔍"))
        search_layout.addWidget(self.search_input)
        toolbar_layout.addWidget(search_container)
        
        toolbar_layout.addStretch()
        card_layout.addWidget(toolbar)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(['目标名片', '所属用户', '申请人', '状态', '提交时间', '处理时间', '操作'])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 140)
        self.table.setColumnWidth(5, 140)
        self.table.setColumnWidth(6, 100)
        
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        self.table.setStyleSheet(f"""
            QTableWidget {{ background: transparent; border: none; }}
            QTableWidget::item {{ border-bottom: 1px solid {PREMIUM_COLORS['border_light']}; padding: 0px; }}
            QHeaderView::section {{
                background: {PREMIUM_COLORS['background']}80;
                color: {PREMIUM_COLORS['text_hint']};
                padding: 10px 8px;
                border: none;
                border-bottom: 1px solid {PREMIUM_COLORS['border_light']};
                font-weight: 700;
            }}
        """)
        
        card_layout.addWidget(self.table, 1)
        
        # Pagination
        pagination = QFrame()
        pagination.setFixedHeight(50)
        pagination.setStyleSheet(f"background: white; border-top: 1px solid {PREMIUM_COLORS['border_light']}; border-bottom-left-radius: 16px; border-bottom-right-radius: 16px;")
        p_layout = QHBoxLayout(pagination)
        p_layout.setContentsMargins(16, 0, 16, 0)
        
        self.page_info = QLabel("0 / 0")
        p_layout.addWidget(self.page_info)
        p_layout.addStretch()
        
        self.prev_btn = QPushButton("‹")
        self.next_btn = QPushButton("›")
        for btn in [self.prev_btn, self.next_btn]:
            btn.setFixedSize(28, 28)
            btn.clicked.connect(self.change_page)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {PREMIUM_COLORS['surface']};
                    border: 1px solid {PREMIUM_COLORS['border']};
                    border-radius: 14px;
                }}
                QPushButton:hover {{ background: {PREMIUM_COLORS['primary']}15; border-color: {PREMIUM_COLORS['primary']}; }}
            """)
            
        p_layout.addWidget(self.prev_btn)
        p_layout.addWidget(self.next_btn)
        
        card_layout.addWidget(pagination)
        layout.addWidget(card, 1)
        
    def change_page(self):
        sender = self.sender()
        if sender == self.prev_btn:
            self.current_page -= 1
        else:
            self.current_page += 1
        self.load_data()
        
    def on_search(self):
        self.current_page = 1
        self.load_data()
        
    def load_data(self):
        keyword = self.search_input.text().strip().lower()
        status_map = {"待审批": "pending", "已通过": "approved", "已拒绝": "rejected"}
        status = status_map.get(self.status_filter.currentText())
        
        # Get all requests
        requests = DatabaseManager.get_card_edit_requests(status=status)
        
        # Client-side filter
        if keyword:
            filtered = []
            for r in requests:
                c_name = r.card.name if r.card else r.original_name or ""
                u_name = r.user.username if r.user else ""
                if keyword in c_name.lower() or keyword in u_name.lower():
                    filtered.append(r)
            requests = filtered
            
        # Update Stats
        pending = sum(1 for r in requests if r.status == 'pending')
        approved = sum(1 for r in requests if r.status == 'approved')
        rejected = sum(1 for r in requests if r.status == 'rejected')
        
        if "待审批" in self.stat_widgets: self.stat_widgets["待审批"].update_value(pending)
        if "已通过" in self.stat_widgets: self.stat_widgets["已通过"].update_value(approved)
        if "已拒绝" in self.stat_widgets: self.stat_widgets["已拒绝"].update_value(rejected)
        
        # Pagination
        self.total_records = len(requests)
        self.total_pages = max(1, (self.total_records + self.page_size - 1) // self.page_size)
        self.current_page = max(1, min(self.current_page, self.total_pages))
        
        start = (self.current_page - 1) * self.page_size
        page_data = requests[start:start+self.page_size]
        
        self.update_table(page_data)
        
        self.page_info.setText(f"显示 {start+1}-{min(start+self.page_size, self.total_records)} 条，共 {self.total_records} 条")
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < self.total_pages)
        
    def update_table(self, requests):
        self.table.setRowCount(len(requests))
        
        for row, req in enumerate(requests):
            self.table.setRowHeight(row, 60)
            
            # 1. Card Name
            name_item = QTableWidgetItem(req.card.name if req.card else (req.original_name or "未知名片"))
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            name_item.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            self.table.setItem(row, 0, name_item)
            
            # 2. User
            user_item = QTableWidgetItem(req.user.username if req.user else "未知")
            user_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, user_item)
            
            # 3. Admin
            admin_item = QTableWidgetItem(req.admin.username if req.admin else "未知")
            admin_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, admin_item)
            
            # 4. Status
            status_widget = QWidget()
            s_layout = QHBoxLayout(status_widget)
            s_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            s_lbl = QLabel()
            if req.status == 'pending':
                s_lbl.setText("⏳ 待审批")
                s_lbl.setStyleSheet("color: #d97706; background: #fff7ed; padding: 4px 12px; border-radius: 12px; font-weight: 600;")
            elif req.status == 'approved':
                s_lbl.setText("✅ 已通过")
                s_lbl.setStyleSheet("color: #059669; background: #ecfdf5; padding: 4px 12px; border-radius: 12px; font-weight: 600;")
            else:
                s_lbl.setText("❌ 已拒绝")
                s_lbl.setStyleSheet("color: #dc2626; background: #fef2f2; padding: 4px 12px; border-radius: 12px; font-weight: 600;")
            
            s_layout.addWidget(s_lbl)
            self.table.setCellWidget(row, 3, status_widget)
            
            # 5. Created At
            c_time = req.created_at.strftime('%Y-%m-%d %H:%M') if req.created_at else "-"
            self.table.setItem(row, 4, QTableWidgetItem(c_time))
            self.table.item(row, 4).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # 6. Processed At
            p_time = req.processed_at.strftime('%Y-%m-%d %H:%M') if req.processed_at else "-"
            self.table.setItem(row, 5, QTableWidgetItem(p_time))
            self.table.item(row, 5).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # 7. Actions
            btn = QPushButton("查看")
            btn.setFixedSize(60, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: white;
                    border: 1px solid {PREMIUM_COLORS['primary']};
                    color: {PREMIUM_COLORS['primary']};
                    border-radius: 14px;
                    font-weight: 600;
                }}
                QPushButton:hover {{ background: {PREMIUM_COLORS['primary']}10; }}
            """)
            btn.clicked.connect(lambda _, r=req: self.view_detail(r))
            
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.setContentsMargins(0,0,0,0)
            layout.addWidget(btn)
            self.table.setCellWidget(row, 6, container)
            
    def view_detail(self, req):
        dialog = AdminAuditLogDetailDialog(req, self)
        if dialog.exec():
            self.load_data()

