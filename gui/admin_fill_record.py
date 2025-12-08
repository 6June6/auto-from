"""
用户填充记录管理模块
采用现代化玻璃拟态设计风格
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QLineEdit, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from database import DatabaseManager
from gui.icons import Icons
from gui.admin_base_components import PREMIUM_COLORS, GlassFrame, CompactStatWidget
import datetime


# ========== 填充记录列表自定义组件 ==========

# 列宽配置
RECORD_LIST_COLUMNS = {
    'user': 140,
    'card': 180,
    'link': 200,
    'status': 80,
    'detail': 100,
    'time': 140,
}


class RecordListHeader(QFrame):
    """填充记录列表表头"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(f"""
            RecordListHeader {{
                background: {PREMIUM_COLORS['background']};
                border: none;
                border-bottom: 1px solid {PREMIUM_COLORS['border_light']};
            }}
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(0)
        
        headers = [
            ('用户', RECORD_LIST_COLUMNS['user']),
            ('名片', RECORD_LIST_COLUMNS['card']),
            ('链接', RECORD_LIST_COLUMNS['link']),
            ('状态', RECORD_LIST_COLUMNS['status']),
            ('填写详情', RECORD_LIST_COLUMNS['detail']),
            ('时间', RECORD_LIST_COLUMNS['time']),
        ]
        
        for text, width in headers:
            lbl = QLabel(text)
            lbl.setFixedWidth(width)
            lbl.setStyleSheet(f"""
                color: {PREMIUM_COLORS['text_hint']};
                font-size: 12px;
                font-weight: 700;
                text-transform: uppercase;
                padding-left: 4px;
            """)
            layout.addWidget(lbl)
        
        layout.addStretch()


class RecordRowWidget(QFrame):
    """填充记录行组件"""
    
    def __init__(self, record, parent=None):
        super().__init__(parent)
        self.record = record
        self.setFixedHeight(64)
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet(f"""
            RecordRowWidget {{
                background: white;
                border: none;
                border-bottom: 1px solid {PREMIUM_COLORS['border_light']};
            }}
            RecordRowWidget:hover {{
                background: #fafbfc;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(0)
        
        # 1. 用户
        self._add_user(layout)
        # 2. 名片
        self._add_card(layout)
        # 3. 链接
        self._add_link(layout)
        # 4. 状态
        self._add_status(layout)
        # 5. 填写详情
        self._add_detail(layout)
        # 6. 时间
        self._add_time(layout)
        
        layout.addStretch()
    
    def _add_user(self, layout):
        container = QWidget()
        container.setFixedWidth(RECORD_LIST_COLUMNS['user'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 8, 0)
        c_layout.setSpacing(8)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        user_name = "未知用户"
        if self.record.card and self.record.card.user:
            user_name = self.record.card.user.username
        elif self.record.link and self.record.link.user:
            user_name = self.record.link.user.username
        
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
        name_lbl.setStyleSheet(f"font-weight: 600; color: {PREMIUM_COLORS['text_heading']}; font-size: 13px;")
        
        c_layout.addWidget(avatar)
        c_layout.addWidget(name_lbl)
        layout.addWidget(container)
    
    def _add_card(self, layout):
        container = QWidget()
        container.setFixedWidth(RECORD_LIST_COLUMNS['card'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 8, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        card_name = self.record.card.name if self.record.card else "已删除名片"
        lbl = QLabel(card_name)
        lbl.setToolTip(card_name)
        lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-size: 13px;")
        c_layout.addWidget(lbl)
        layout.addWidget(container)
    
    def _add_link(self, layout):
        container = QWidget()
        container.setFixedWidth(RECORD_LIST_COLUMNS['link'])
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 8, 0)
        c_layout.setSpacing(2)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        link_name = self.record.link.name if self.record.link else "已删除链接"
        link_url = self.record.link.url if self.record.link else ""
        
        name_lbl = QLabel(link_name)
        name_lbl.setStyleSheet(f"font-size: 13px; color: {PREMIUM_COLORS['text_body']};")
        
        url_text = link_url[:30] + "..." if len(link_url) > 30 else link_url
        url_lbl = QLabel(url_text)
        url_lbl.setToolTip(link_url)
        url_lbl.setStyleSheet(f"font-size: 11px; color: {PREMIUM_COLORS['text_hint']};")
        
        c_layout.addWidget(name_lbl)
        c_layout.addWidget(url_lbl)
        layout.addWidget(container)
    
    def _add_status(self, layout):
        container = QWidget()
        container.setFixedWidth(RECORD_LIST_COLUMNS['status'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        status_lbl = QLabel("成功" if self.record.success else "失败")
        if self.record.success:
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
            if self.record.error_message:
                status_lbl.setToolTip(self.record.error_message)
        
        c_layout.addWidget(status_lbl)
        layout.addWidget(container)
    
    def _add_detail(self, layout):
        container = QWidget()
        container.setFixedWidth(RECORD_LIST_COLUMNS['detail'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        detail_text = f"{self.record.fill_count} / {self.record.total_count}"
        lbl = QLabel(detail_text)
        lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-weight: 600; font-size: 13px;")
        c_layout.addWidget(lbl)
        layout.addWidget(container)
    
    def _add_time(self, layout):
        container = QWidget()
        container.setFixedWidth(RECORD_LIST_COLUMNS['time'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        time_str = self.record.created_at.strftime('%Y-%m-%d %H:%M')
        lbl = QLabel(time_str)
        lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-size: 12px;")
        c_layout.addWidget(lbl)
        layout.addWidget(container)


class RecordListWidget(QWidget):
    """填充记录列表组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.row_widgets = []
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.header = RecordListHeader()
        layout.addWidget(self.header)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
            QScrollBar::handle:vertical {{ background: {PREMIUM_COLORS['border']}; border-radius: 4px; min-height: 30px; }}
            QScrollBar::handle:vertical:hover {{ background: {PREMIUM_COLORS['text_hint']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        """)
        
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: white;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.content_widget)
        layout.addWidget(self.scroll_area, 1)
    
    def set_records(self, records):
        for widget in self.row_widgets:
            widget.deleteLater()
        self.row_widgets.clear()
        
        if not records:
            empty_label = QLabel("暂无填充记录")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet(f"""
                color: {PREMIUM_COLORS['text_hint']};
                font-size: 14px;
                padding: 60px;
            """)
            self.content_layout.addWidget(empty_label)
            self.row_widgets.append(empty_label)
            return
        
        for record in records:
            row = RecordRowWidget(record)
            self.content_layout.addWidget(row)
            self.row_widgets.append(row)

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
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setIcon(Icons.refresh())
        self.refresh_btn.setFixedSize(80, 36)
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setStyleSheet(f"""
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
        self.refresh_btn.clicked.connect(lambda: self.load_data())
        toolbar_layout.addWidget(self.refresh_btn)
        
        card_layout.addWidget(toolbar)
        
        # 自定义填充记录列表
        self.record_list = RecordListWidget()
        card_layout.addWidget(self.record_list, 1)
        
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
            
        self.record_list.set_records(result['records'])
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
        


