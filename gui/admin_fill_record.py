"""
用户填充记录管理模块
采用现代化玻璃拟态设计风格
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, 
    QMessageBox, QLineEdit, QFrame, QGraphicsDropShadowEffect, 
    QAbstractItemView, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QBrush
from database import DatabaseManager
from gui.styles import COLORS
from gui.icons import Icons
import datetime

# 扩展颜色系统
PREMIUM_COLORS = {
    **COLORS,
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
    'glass_bg': 'rgba(255, 255, 255, 0.85)',
    'glass_border': 'rgba(255, 255, 255, 0.6)',
    'text_heading': '#2d3748',
    'text_body': '#4a5568',
    'text_hint': '#a0aec0',
    'mint': '#00d9a6',
    'coral': '#ff6b6b',
    'background': '#f8fafc',
    'border': '#e2e8f0',
    'border_light': '#f1f5f9',
    'primary': '#667eea',
    'surface': '#ffffff',
    'primary_light': '#8b9df0',
}

class GlassFrame(QFrame):
    """玻璃拟态框架"""
    def __init__(self, parent=None, opacity=0.9, radius=24):
        super().__init__(parent)
        self.opacity = opacity
        self.radius = radius
        self.setStyleSheet(f"""
            GlassFrame {{
                background: rgba(255, 255, 255, {self.opacity});
                border: 1px solid rgba(255, 255, 255, 0.6);
                border-radius: {self.radius}px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(31, 38, 135, 15))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)

class CompactStatWidget(QFrame):
    """紧凑型统计组件"""
    def __init__(self, title, value, icon, color_start, color_end, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 50)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)
        
        self.setStyleSheet(f"""
            CompactStatWidget {{
                background: white;
                border-radius: 12px;
                border: 1px solid {PREMIUM_COLORS['border_light']};
            }}
        """)
        
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
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self.value_lbl = QLabel(str(value))
        self.value_lbl.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {PREMIUM_COLORS['text_heading']};")
        text_layout.addWidget(self.value_lbl)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 10px; color: {PREMIUM_COLORS['text_hint']};")
        text_layout.addWidget(title_lbl)
        
        layout.addLayout(text_layout)
        
    def update_value(self, value):
        self.value_lbl.setText(str(value))

class AdminFillRecordManager(QWidget):
    """管理员填充记录管理"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.current_page = 1
        self.page_size = 15
        self.total_records = 0
        self.total_pages = 1
        self.stat_cards = {}
        self.init_ui()
        
    def init_ui(self):
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
        
        self._create_header(main_layout)
        self._create_main_card(main_layout)
        
        self.load_data()
        
    def _create_header(self, layout):
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)
        
        title_label = QLabel("填充记录管理")
        title_label.setStyleSheet(f"""
            font-size: 24px; 
            font-weight: 800; 
            color: {PREMIUM_COLORS['text_heading']};
            background: transparent;
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addSpacing(16)
        
        cards_data = [
            ("总记录数", 0, "📝", PREMIUM_COLORS['gradient_blue_start'], PREMIUM_COLORS['gradient_blue_end']),
            ("今日记录", 0, "📅", PREMIUM_COLORS['gradient_green_start'], PREMIUM_COLORS['gradient_green_end']),
            ("成功率", "0%", "📈", PREMIUM_COLORS['gradient_gold_start'], PREMIUM_COLORS['gradient_gold_end']),
        ]
        
        for title, value, icon, start, end in cards_data:
            card = CompactStatWidget(title, value, icon, start, end)
            self.stat_cards[title] = card
            header_layout.addWidget(card)
            
        header_layout.addStretch()
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
        
        # Search
        search_container = QFrame()
        search_container.setFixedSize(300, 36)
        search_container.setStyleSheet(f"""
            QFrame {{
                background: {PREMIUM_COLORS['background']};
                border-radius: 8px;
                border: 1px solid transparent;
            }}
            QFrame:hover {{
                background: white;
                border-color: {PREMIUM_COLORS['border']};
            }}
        """)
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(10, 0, 10, 0)
        search_layout.setSpacing(8)
        
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("font-size: 14px; color: #a0aec0; border: none; background: transparent;")
        search_layout.addWidget(search_icon)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索用户/名片/链接...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                background: transparent;
                font-size: 13px;
                color: {PREMIUM_COLORS['text_heading']};
                padding: 0;
            }}
        """)
        self.search_input.textChanged.connect(self.on_search)
        search_layout.addWidget(self.search_input)
        toolbar_layout.addWidget(search_container)
        
        toolbar_layout.addStretch()
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.setIcon(Icons.refresh())
        refresh_btn.setFixedSize(80, 36)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {PREMIUM_COLORS['border']};
                border-radius: 8px;
                color: {PREMIUM_COLORS['text_body']};
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {PREMIUM_COLORS['background']};
                color: {PREMIUM_COLORS['gradient_blue_start']};
                border-color: {PREMIUM_COLORS['gradient_blue_start']};
            }}
        """)
        refresh_btn.clicked.connect(self.load_data)
        toolbar_layout.addWidget(refresh_btn)
        
        card_layout.addWidget(toolbar)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['用户', '名片', '链接', '状态', '填写详情', '时间'])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        
        self.table.setColumnWidth(3, 80)
        self.table.setColumnWidth(4, 120)
        self.table.setColumnWidth(5, 140)
        
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background: transparent;
                border: none;
            }}
            QTableWidget::item {{
                border-bottom: 1px solid {PREMIUM_COLORS['border_light']};
                padding: 0px;
            }}
            QTableWidget::item:selected {{
                background-color: {PREMIUM_COLORS['primary']}08;
            }}
            QHeaderView::section {{
                background: {PREMIUM_COLORS['background']}80;
                color: {PREMIUM_COLORS['text_hint']};
                padding: 10px 8px;
                border: none;
                border-bottom: 1px solid {PREMIUM_COLORS['border_light']};
                font-weight: 700;
                font-size: 12px;
                text-transform: uppercase;
            }}
        """)
        
        card_layout.addWidget(self.table, 1)
        
        # Pagination
        pagination = QFrame()
        pagination.setFixedHeight(50)
        pagination.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-top: 1px solid {PREMIUM_COLORS['border_light']};
                border-bottom-left-radius: 16px;
                border-bottom-right-radius: 16px;
            }}
        """)
        pagination_layout = QHBoxLayout(pagination)
        pagination_layout.setContentsMargins(16, 0, 16, 0)
        
        self.page_info_label = QLabel()
        self.page_info_label.setStyleSheet(f"color: {PREMIUM_COLORS['text_hint']}; font-size: 12px;")
        pagination_layout.addWidget(self.page_info_label)
        
        pagination_layout.addStretch()
        
        page_btns = QHBoxLayout()
        page_btns.setSpacing(8)
        
        self.prev_btn = QPushButton("‹")
        self.next_btn = QPushButton("›")
        
        btn_style = f"""
            QPushButton {{
                background: {PREMIUM_COLORS['surface']};
                border: 1px solid {PREMIUM_COLORS['border']};
                border-radius: 14px;
                color: {PREMIUM_COLORS['text_body']};
                font-size: 16px;
                font-weight: bold;
                padding-bottom: 2px;
            }}
            QPushButton:hover {{
                background: {PREMIUM_COLORS['primary']}15;
                color: {PREMIUM_COLORS['primary']};
                border-color: {PREMIUM_COLORS['primary']};
            }}
            QPushButton:disabled {{
                background: {PREMIUM_COLORS['background']};
                color: {PREMIUM_COLORS['border']};
                border-color: {PREMIUM_COLORS['border_light']};
            }}
        """
        
        for btn in [self.prev_btn, self.next_btn]:
            btn.setFixedSize(28, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(self.change_page)
            
        page_btns.addWidget(self.prev_btn)
        
        self.page_num_label = QLabel("1 / 1")
        self.page_num_label.setStyleSheet(f"""
            color: {PREMIUM_COLORS['text_heading']}; 
            font-weight: 600;
            font-size: 12px;
            padding: 0 8px;
        """)
        page_btns.addWidget(self.page_num_label)
        page_btns.addWidget(self.next_btn)
        
        pagination_layout.addLayout(page_btns)
        card_layout.addWidget(pagination)
        
        layout.addWidget(card, 1)
        
    def on_search(self):
        self.current_page = 1
        self.load_data()
        
    def change_page(self):
        sender = self.sender()
        if sender == self.prev_btn:
            self.go_to_page(self.current_page - 1)
        else:
            self.go_to_page(self.current_page + 1)
            
    def go_to_page(self, page):
        if 1 <= page <= self.total_pages:
            self.current_page = page
            self.load_data()
            
    def load_data(self):
        keyword = self.search_input.text().strip()
        
        # 获取统计
        stats = self.db_manager.get_statistics()
        if "总记录数" in self.stat_cards:
            self.stat_cards["总记录数"].update_value(stats.get('total_records', 0))
        if "今日记录" in self.stat_cards:
            self.stat_cards["今日记录"].update_value(stats.get('today_records', 0))
        if "成功率" in self.stat_cards:
            rate = stats.get('success_rate', 0)
            self.stat_cards["成功率"].update_value(f"{rate}%")
            
        # 获取分页数据
        offset = (self.current_page - 1) * self.page_size
        result = self.db_manager.get_all_fill_records(keyword=keyword, limit=self.page_size, offset=offset)
        
        self.total_records = result['total']
        self.total_pages = max(1, (self.total_records + self.page_size - 1) // self.page_size)
        
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
            
        self.update_table(result['records'])
        self.update_pagination()
        
    def update_pagination(self):
        start = (self.current_page - 1) * self.page_size + 1
        end = min(self.current_page * self.page_size, self.total_records)
        
        if self.total_records > 0:
            self.page_info_label.setText(f"显示 {start}-{end} 条，共 {self.total_records} 条")
        else:
            self.page_info_label.setText("暂无数据")
            
        self.page_num_label.setText(f"{self.current_page} / {self.total_pages}")
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < self.total_pages)
        
    def update_table(self, records):
        self.table.setRowCount(len(records))
        
        for row, record in enumerate(records):
            self.table.setRowHeight(row, 60)
            
            # 1. 用户
            user_widget = QWidget()
            user_layout = QHBoxLayout(user_widget)
            user_layout.setContentsMargins(12, 0, 4, 0)
            user_layout.setSpacing(10)
            user_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            user_name = "未知用户"
            if record.card and record.card.user:
                user_name = record.card.user.username
            elif record.link and record.link.user:
                user_name = record.link.user.username
                
            avatar = QLabel(user_name[0].upper())
            avatar.setFixedSize(32, 32)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            colors = [
                (PREMIUM_COLORS['gradient_green_start'], PREMIUM_COLORS['gradient_green_end']),
                (PREMIUM_COLORS['gradient_orange_start'], PREMIUM_COLORS['gradient_orange_end']),
                (PREMIUM_COLORS['gradient_purple_start'], PREMIUM_COLORS['gradient_purple_end']),
            ]
            c_start, c_end = colors[sum(ord(c) for c in user_name) % len(colors)]
            
            avatar.setStyleSheet(f"""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {c_start}, stop:1 {c_end});
                color: white;
                border-radius: 16px;
                font-size: 14px;
                font-weight: 700;
            """)
            
            name_lbl = QLabel(user_name)
            name_lbl.setStyleSheet(f"font-weight: 700; color: {PREMIUM_COLORS['text_heading']};")
            
            user_layout.addWidget(avatar)
            user_layout.addWidget(name_lbl)
            self.table.setCellWidget(row, 0, user_widget)
            
            # 2. 名片
            card_name = record.card.name if record.card else "已删除名片"
            card_item = QTableWidgetItem(card_name)
            card_item.setToolTip(card_name)
            self.table.setItem(row, 1, card_item)
            
            # 3. 链接
            link_name = record.link.name if record.link else "已删除链接"
            link_url = record.link.url if record.link else ""
            link_widget = QWidget()
            link_layout = QVBoxLayout(link_widget)
            link_layout.setContentsMargins(4, 0, 4, 0)
            link_layout.setSpacing(2)
            link_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            
            lname_lbl = QLabel(link_name)
            lname_lbl.setStyleSheet(f"font-size: 13px; color: {PREMIUM_COLORS['text_body']};")
            lurl_lbl = QLabel(link_url)
            lurl_lbl.setStyleSheet(f"font-size: 11px; color: {PREMIUM_COLORS['text_hint']};")
            
            link_layout.addWidget(lname_lbl)
            link_layout.addWidget(lurl_lbl)
            self.table.setCellWidget(row, 2, link_widget)
            
            # 4. 状态
            status_widget = QWidget()
            status_layout = QHBoxLayout(status_widget)
            status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            status_lbl = QLabel("成功" if record.success else "失败")
            if record.success:
                status_lbl.setStyleSheet(f"""
                    background: {PREMIUM_COLORS['gradient_green_start']}15;
                    color: {PREMIUM_COLORS['gradient_green_start']};
                    padding: 4px 12px;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 600;
                """)
            else:
                status_lbl.setStyleSheet(f"""
                    background: {PREMIUM_COLORS['coral']}15;
                    color: {PREMIUM_COLORS['coral']};
                    padding: 4px 12px;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: 600;
                """)
                # 失败原因提示
                if record.error_message:
                    status_lbl.setToolTip(record.error_message)
                    
            status_layout.addWidget(status_lbl)
            self.table.setCellWidget(row, 3, status_widget)
            
            # 5. 填写详情
            detail_widget = QWidget()
            detail_layout = QHBoxLayout(detail_widget)
            detail_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            detail_text = f"{record.fill_count} / {record.total_count}"
            detail_lbl = QLabel(detail_text)
            detail_lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-weight: 600;")
            detail_layout.addWidget(detail_lbl)
            self.table.setCellWidget(row, 4, detail_widget)
            
            # 6. 时间
            time_str = record.created_at.strftime('%Y-%m-%d %H:%M')
            time_item = QTableWidgetItem(time_str)
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, time_item)

