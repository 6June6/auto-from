"""
通告管理模块
重新设计版本，参考用户管理界面的现代化风格
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, 
    QMessageBox, QLineEdit, QDialog, QComboBox, QFrame,
    QCheckBox, QGraphicsDropShadowEffect, QAbstractItemView, 
    QDateTimeEdit, QSpinBox, QScrollArea, QTabWidget, QTabBar,
    QDateEdit, QLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QDateTime, QDate
from PyQt6.QtGui import QFont, QColor, QIcon, QPainter, QLinearGradient, QPen, QBrush
from database import DatabaseManager
from gui.styles import COLORS
from gui.icons import Icons
from datetime import datetime

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
    'dark_accent': '#1a1a2e',
    'text_heading': '#2d3748',
    'text_body': '#4a5568',
    'text_hint': '#a0aec0',
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

class BaseDialog(QDialog):
    """基础弹框样式"""
    def __init__(self, parent=None, title="", icon="✏️"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setStyleSheet("QDialog { background-color: white; }")
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 1. 顶部 Header
        header = QFrame()
        header.setFixedHeight(90)
        header.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {PREMIUM_COLORS['gradient_blue_start']}, 
                    stop:1 {PREMIUM_COLORS['gradient_blue_end']});
            }}
        """)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(32, 0, 32, 0)
        header_layout.setSpacing(16)
        
        title_info = QVBoxLayout()
        title_info.setSpacing(4)
        title_info.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: white; font-size: 24px; font-weight: 800;")
        
        title_info.addWidget(title_lbl)
        
        icon_bg = QLabel(icon)
        icon_bg.setFixedSize(48, 48)
        icon_bg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_bg.setStyleSheet("""
            background: rgba(255,255,255,0.2);
            border-radius: 24px;
            font-size: 24px;
        """)
        
        header_layout.addLayout(title_info)
        header_layout.addWidget(icon_bg)
        self.main_layout.addWidget(header)
        
        # 2. 内容区域
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(32, 32, 32, 20)
        self.content_layout.setSpacing(20)
        
        self.input_style = f"""
            QLineEdit, QComboBox, QDateTimeEdit, QSpinBox, QDateEdit {{
                border: 1px solid {PREMIUM_COLORS['border_light']};
                border-radius: 10px;
                padding: 0 12px;
                background: #f8fafc;
                height: 42px;
                font-size: 14px;
                color: {PREMIUM_COLORS['text_heading']};
                selection-background-color: {PREMIUM_COLORS['primary_light']};
            }}
            QLineEdit:focus, QComboBox:focus, QDateTimeEdit:focus, QSpinBox:focus, QDateEdit:focus {{
                border: 1px solid {PREMIUM_COLORS['gradient_blue_start']};
                background: white;
            }}
            QLineEdit:hover, QComboBox:hover, QDateTimeEdit:hover, QSpinBox:hover, QDateEdit:hover {{
                background: white;
                border-color: #cbd5e1;
            }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QLabel {{
                color: {PREMIUM_COLORS['text_body']};
                font-weight: 600;
                font-size: 13px;
            }}
        """
        self.content_widget.setStyleSheet(self.input_style)
        
    def add_content(self, widget, stretch=0):
        self.main_layout.addWidget(widget, stretch)
        
    def add_form_content(self, item):
        if isinstance(item, QLayout):
            self.content_layout.addLayout(item)
        else:
            self.content_layout.addWidget(item)
        
    def create_bottom_buttons(self):
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(32, 0, 32, 32)
        btn_layout.setSpacing(16)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFixedSize(100, 44)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: white;
                color: {PREMIUM_COLORS['text_body']}; 
                border: 1px solid {PREMIUM_COLORS['border']}; 
                border-radius: 22px; 
                font-weight: 600;
                font-size: 14px;
            }}
            QPushButton:hover {{ 
                background: {PREMIUM_COLORS['background']}; 
                border-color: {PREMIUM_COLORS['text_body']};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = GradientButton(
            "保存", 
            PREMIUM_COLORS['gradient_blue_start'], 
            PREMIUM_COLORS['gradient_blue_end']
        )
        save_btn.setFixedSize(140, 44)
        save_btn.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        
        self.main_layout.addLayout(btn_layout)

    def create_field(self, label_text, widget):
        layout = QVBoxLayout()
        layout.setSpacing(6)
        label = QLabel(label_text)
        layout.addWidget(label)
        layout.addWidget(widget)
        return layout

class AdminNoticeManager(QWidget):
    """通告管理主界面"""
    def __init__(self, current_user=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.db_manager = DatabaseManager()
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # 标题栏
        title_label = QLabel("通告管理中心")
        title_label.setStyleSheet(f"""
            font-size: 24px; 
            font-weight: 800; 
            color: {PREMIUM_COLORS['text_heading']};
            background: transparent;
        """)
        layout.addWidget(title_label)
        
        # 标签页
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: transparent;
            }}
            QTabWidget::tab-bar {{
                alignment: left;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {PREMIUM_COLORS['text_hint']};
                font-weight: 600;
                font-size: 14px;
                padding: 8px 20px;
                margin-right: 16px;
                border-bottom: 3px solid transparent;
            }}
            QTabBar::tab:selected {{
                color: {PREMIUM_COLORS['gradient_blue_start']};
                border-bottom: 3px solid {PREMIUM_COLORS['gradient_blue_start']};
            }}
            QTabBar::tab:hover {{
                color: {PREMIUM_COLORS['text_body']};
            }}
        """)
        
        self.notice_manager = NoticeManager(self.db_manager, self.current_user)
        self.platform_manager = PlatformManager(self.db_manager)
        self.category_manager = CategoryManager(self.db_manager)
        
        self.tabs.addTab(self.notice_manager, "通告列表")
        self.tabs.addTab(self.platform_manager, "平台管理")
        self.tabs.addTab(self.category_manager, "类目管理")
        
        layout.addWidget(self.tabs)

class ModernBaseManager(QWidget):
    """现代化基础管理组件"""
    ITEM_NAME = "项目"
    
    def __init__(self, db_manager, current_user=None):
        super().__init__()
        self.db_manager = db_manager
        self.current_user = current_user
        self.stat_cards = {}
        self.current_page = 1
        self.page_size = 15
        self.total_items = 0
        self.total_pages = 1
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(16)
        
        # 顶部统计和操作
        self._create_header(layout)
        
        # 主表格卡片
        self._create_main_card(layout)
        
        self.load_data()
        
    def _create_header(self, layout):
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)
        
        # 统计卡片
        stats = self.get_stats_config()
        for title, value, icon, start, end in stats:
            card = CompactStatWidget(title, value, icon, start, end)
            self.stat_cards[title] = card
            header_layout.addWidget(card)
            
        header_layout.addStretch()
        
        # 添加按钮
        add_btn = GradientButton(
            f"+ 添加{self.ITEM_NAME}",
            PREMIUM_COLORS['gradient_blue_start'],
            PREMIUM_COLORS['gradient_blue_end']
        )
        add_btn.setFixedSize(140, 40)
        add_btn.clicked.connect(self.add_item)
        header_layout.addWidget(add_btn)
        
        layout.addLayout(header_layout)
        
    def _create_main_card(self, layout):
        card = GlassFrame(opacity=1.0, radius=16)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        
        # 工具栏
        toolbar = QFrame()
        toolbar.setFixedHeight(56)
        toolbar.setStyleSheet(f"border-bottom: 1px solid {PREMIUM_COLORS['border_light']}; background: transparent;")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 0, 16, 0)
        
        # 搜索框
        search_container = QFrame()
        search_container.setFixedSize(260, 36)
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
        self.search_input.setPlaceholderText(f"搜索{self.ITEM_NAME}...")
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
        
        # 表格
        self.table = QTableWidget()
        self.setup_table()
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
        
        # 分页
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
        
        layout.addWidget(card)

    def setup_table(self):
        pass
        
    def get_stats_config(self):
        return []
        
    def load_data(self):
        pass
        
    def add_item(self):
        pass
        
    def on_search(self):
        self.current_page = 1
        self.load_data()
        
    def change_page(self):
        sender = self.sender()
        if sender == self.prev_btn:
            self.current_page = max(1, self.current_page - 1)
        else:
            self.current_page = min(self.total_pages, self.current_page + 1)
        self.load_data()
        
    def update_pagination(self):
        start = (self.current_page - 1) * self.page_size + 1
        end = min(self.current_page * self.page_size, self.total_items)
        
        if self.total_items > 0:
            self.page_info_label.setText(f"显示 {start}-{end} 条，共 {self.total_items} 条")
        else:
            self.page_info_label.setText("暂无数据")
            
        self.page_num_label.setText(f"{self.current_page} / {self.total_pages}")
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < self.total_pages)

    def create_op_btn(self, text, color, callback):
        btn = QPushButton(text)
        btn.setFixedSize(44, 24)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {color};
                border: 1px solid {color}40;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {color}10;
                border-color: {color};
            }}
        """)
        btn.clicked.connect(callback)
        return btn

class NoticeManager(ModernBaseManager):
    ITEM_NAME = "通告"
    
    def setup_table(self):
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["标题", "平台", "类目", "品牌", "发布时间", "状态", "操作"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        
        self.table.setColumnWidth(1, 80)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(5, 80)
        self.table.setColumnWidth(6, 120)
        
    def get_stats_config(self):
        return [
            ("通告总数", 0, "📢", PREMIUM_COLORS['gradient_blue_start'], PREMIUM_COLORS['gradient_blue_end']),
            ("进行中", 0, "🔥", PREMIUM_COLORS['gradient_green_start'], PREMIUM_COLORS['gradient_green_end']),
            ("已结束", 0, "🏁", PREMIUM_COLORS['gradient_orange_start'], PREMIUM_COLORS['gradient_orange_end']),
        ]
        
    def load_data(self):
        keyword = self.search_input.text().strip()
        notices = self.db_manager.get_all_notices(keyword=keyword if keyword else None)
        
        # 统计
        total = len(notices)
        active = sum(1 for n in notices if n.status == 'active')
        ended = sum(1 for n in notices if n.status != 'active')
        
        self.stat_cards["通告总数"].update_value(total)
        self.stat_cards["进行中"].update_value(active)
        self.stat_cards["已结束"].update_value(ended)
        
        # 分页
        self.total_items = total
        self.total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
            
        start = (self.current_page - 1) * self.page_size
        current_notices = notices[start:start + self.page_size]
        
        self.table.setRowCount(len(current_notices))
        for i, n in enumerate(current_notices):
            self.table.setRowHeight(i, 60)
            
            # 标题
            title_widget = QWidget()
            title_layout = QHBoxLayout(title_widget)
            title_layout.setContentsMargins(12, 0, 4, 0)
            title_lbl = QLabel(n.title)
            title_lbl.setStyleSheet(f"font-weight: 600; color: {PREMIUM_COLORS['text_heading']}; font-size: 13px;")
            title_layout.addWidget(title_lbl)
            self.table.setCellWidget(i, 0, title_widget)
            
            # 平台
            plat_lbl = QLabel(n.platform)
            plat_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            plat_lbl.setStyleSheet(f"""
                background: {PREMIUM_COLORS['primary']}15;
                color: {PREMIUM_COLORS['primary']};
                border-radius: 4px;
                padding: 4px;
                font-size: 12px;
                font-weight: 600;
            """)
            # 居中容器
            plat_widget = QWidget()
            plat_layout = QHBoxLayout(plat_widget)
            plat_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            plat_layout.addWidget(plat_lbl)
            self.table.setCellWidget(i, 1, plat_widget)
            
            # 类目
            cat_item = QTableWidgetItem(n.category)
            cat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 2, cat_item)
            
            # 品牌
            brand_item = QTableWidgetItem(n.brand)
            brand_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 3, brand_item)
            
            # 时间
            date_str = n.publish_date.strftime('%Y-%m-%d') if n.publish_date else ""
            time_item = QTableWidgetItem(date_str)
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 4, time_item)
            
            # 状态
            status_widget = QWidget()
            status_layout = QHBoxLayout(status_widget)
            status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            status_map = {
                'active': ('进行中', PREMIUM_COLORS['mint']),
                'expired': ('已过期', PREMIUM_COLORS['text_hint']),
                'closed': ('已关闭', PREMIUM_COLORS['coral'])
            }
            text, color = status_map.get(n.status, (n.status, PREMIUM_COLORS['text_body']))
            
            status_lbl = QLabel(text)
            status_lbl.setStyleSheet(f"color: {color}; font-weight: 600; font-size: 12px;")
            status_layout.addWidget(status_lbl)
            self.table.setCellWidget(i, 5, status_widget)
            
            # 操作
            ops_widget = QWidget()
            ops_layout = QHBoxLayout(ops_widget)
            ops_layout.setContentsMargins(4, 0, 4, 0)
            ops_layout.setSpacing(8)
            ops_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            btn_edit = self.create_op_btn("编辑", PREMIUM_COLORS['gradient_blue_start'], lambda _, item=n: self.edit_item(item))
            btn_del = self.create_op_btn("删除", PREMIUM_COLORS['coral'], lambda _, item=n: self.delete_item(item))
            
            ops_layout.addWidget(btn_edit)
            ops_layout.addWidget(btn_del)
            self.table.setCellWidget(i, 6, ops_widget)
            
        self.update_pagination()

    def add_item(self):
        dialog = NoticeDialog(self, self.db_manager)
        if dialog.exec():
            data = dialog.get_data()
            if self.current_user:
                data['created_by'] = self.current_user
            try:
                self.db_manager.create_notice(**data)
                self.load_data()
                QMessageBox.information(self, "成功", "通告已发布")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"发布失败: {str(e)}")

    def edit_item(self, item):
        dialog = NoticeDialog(self, self.db_manager, item)
        if dialog.exec():
            data = dialog.get_data()
            try:
                self.db_manager.update_notice(str(item.id), **data)
                self.load_data()
                QMessageBox.information(self, "成功", "通告已更新")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新失败: {str(e)}")
                
    def delete_item(self, item):
        reply = QMessageBox.question(self, "确认删除", f"确定要删除通告“{item.title}”吗？", 
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.db_manager.delete_notice(str(item.id)):
                self.load_data()
            else:
                QMessageBox.critical(self, "错误", "删除失败")

class PlatformManager(ModernBaseManager):
    ITEM_NAME = "平台"
    
    def setup_table(self):
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["名称", "图标", "排序", "状态", "操作"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 150)
        
    def get_stats_config(self):
        return [
            ("平台总数", 0, "📱", PREMIUM_COLORS['gradient_purple_start'], PREMIUM_COLORS['gradient_purple_end']),
            ("已启用", 0, "✅", PREMIUM_COLORS['gradient_green_start'], PREMIUM_COLORS['gradient_green_end']),
        ]
        
    def load_data(self):
        platforms = self.db_manager.get_all_platforms()
        
        total = len(platforms)
        active = sum(1 for p in platforms if p.is_active)
        
        self.stat_cards["平台总数"].update_value(total)
        self.stat_cards["已启用"].update_value(active)
        
        self.total_items = total
        self.table.setRowCount(len(platforms))
        
        for i, p in enumerate(platforms):
            self.table.setRowHeight(i, 50)
            
            name_item = QTableWidgetItem(p.name)
            name_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            self.table.setItem(i, 0, name_item)
            
            self.table.setItem(i, 1, QTableWidgetItem(p.icon or ""))
            self.table.setItem(i, 2, QTableWidgetItem(str(p.order)))
            
            status_text = "启用" if p.is_active else "禁用"
            status_color = PREMIUM_COLORS['mint'] if p.is_active else PREMIUM_COLORS['text_hint']
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QColor(status_color))
            self.table.setItem(i, 3, status_item)
            
            ops_widget = QWidget()
            ops_layout = QHBoxLayout(ops_widget)
            ops_layout.setContentsMargins(4, 0, 4, 0)
            ops_layout.setSpacing(8)
            ops_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            btn_edit = self.create_op_btn("编辑", PREMIUM_COLORS['gradient_blue_start'], lambda _, item=p: self.edit_item(item))
            btn_del = self.create_op_btn("删除", PREMIUM_COLORS['coral'], lambda _, item=p: self.delete_item(item))
            
            ops_layout.addWidget(btn_edit)
            ops_layout.addWidget(btn_del)
            self.table.setCellWidget(i, 4, ops_widget)
            
        self.update_pagination()

    def add_item(self):
        dialog = PlatformDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            try:
                self.db_manager.create_platform(**data)
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建失败: {str(e)}")

    def edit_item(self, item):
        dialog = PlatformDialog(self, item)
        if dialog.exec():
            data = dialog.get_data()
            try:
                self.db_manager.update_platform(str(item.id), **data)
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新失败: {str(e)}")
                
    def delete_item(self, item):
        if QMessageBox.question(self, "确认", f"确定要删除平台 {item.name} 吗？") == QMessageBox.StandardButton.Yes:
            if self.db_manager.delete_platform(str(item.id)):
                self.load_data()
            else:
                QMessageBox.critical(self, "错误", "删除失败")

class CategoryManager(ModernBaseManager):
    ITEM_NAME = "类目"
    
    def setup_table(self):
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["名称", "排序", "状态", "操作"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 150)
        
    def get_stats_config(self):
        return [
            ("类目总数", 0, "🏷️", PREMIUM_COLORS['gradient_gold_start'], PREMIUM_COLORS['gradient_gold_end']),
        ]
        
    def load_data(self):
        categories = self.db_manager.get_all_notice_categories()
        self.stat_cards["类目总数"].update_value(len(categories))
        
        self.total_items = len(categories)
        self.table.setRowCount(len(categories))
        
        for i, c in enumerate(categories):
            self.table.setRowHeight(i, 50)
            
            self.table.setItem(i, 0, QTableWidgetItem(c.name))
            self.table.setItem(i, 1, QTableWidgetItem(str(c.order)))
            
            status_text = "启用" if c.is_active else "禁用"
            status_color = PREMIUM_COLORS['mint'] if c.is_active else PREMIUM_COLORS['text_hint']
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QColor(status_color))
            self.table.setItem(i, 2, status_item)
            
            ops_widget = QWidget()
            ops_layout = QHBoxLayout(ops_widget)
            ops_layout.setContentsMargins(4, 0, 4, 0)
            ops_layout.setSpacing(8)
            ops_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            btn_edit = self.create_op_btn("编辑", PREMIUM_COLORS['gradient_blue_start'], lambda _, item=c: self.edit_item(item))
            btn_del = self.create_op_btn("删除", PREMIUM_COLORS['coral'], lambda _, item=c: self.delete_item(item))
            
            ops_layout.addWidget(btn_edit)
            ops_layout.addWidget(btn_del)
            self.table.setCellWidget(i, 3, ops_widget)
            
        self.update_pagination()

    def add_item(self):
        dialog = CategoryDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            try:
                self.db_manager.create_notice_category(**data)
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建失败: {str(e)}")

    def edit_item(self, item):
        dialog = CategoryDialog(self, item)
        if dialog.exec():
            data = dialog.get_data()
            try:
                self.db_manager.update_notice_category(str(item.id), **data)
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新失败: {str(e)}")
                
    def delete_item(self, item):
        if QMessageBox.question(self, "确认", f"确定要删除类目 {item.name} 吗？") == QMessageBox.StandardButton.Yes:
            if self.db_manager.delete_notice_category(str(item.id)):
                self.load_data()
            else:
                QMessageBox.critical(self, "错误", "删除失败")

# ================= Dialogs =================

class PlatformDialog(BaseDialog):
    def __init__(self, parent=None, platform=None):
        super().__init__(parent, title="编辑平台" if platform else "新增平台", icon="📱")
        self.platform = platform
        self.setup_ui()
        
    def setup_ui(self):
        self.setFixedSize(450, 500)
        
        self.name_input = QLineEdit(self.platform.name if self.platform else "")
        self.name_input.setPlaceholderText("请输入平台名称")
        self.add_form_content(self.create_field("名称", self.name_input))
        
        self.icon_input = QLineEdit(self.platform.icon if self.platform else "")
        self.icon_input.setPlaceholderText("请输入图标代码 (如 fa5s.video)")
        self.add_form_content(self.create_field("图标代码", self.icon_input))
        
        self.order_spin = QSpinBox()
        self.order_spin.setValue(self.platform.order if self.platform else 0)
        self.add_form_content(self.create_field("排序", self.order_spin))
        
        if self.platform:
            self.active_cb = QCheckBox("启用")
            self.active_cb.setChecked(self.platform.is_active)
            self.active_cb.setStyleSheet(f"color: {PREMIUM_COLORS['text_heading']}; font-size: 13px;")
            self.add_form_content(self.active_cb)
            
        self.add_content(self.content_widget)
        self.create_bottom_buttons()
        
    def get_data(self):
        data = {
            'name': self.name_input.text(),
            'icon': self.icon_input.text(),
            'order': self.order_spin.value()
        }
        if self.platform:
            data['is_active'] = self.active_cb.isChecked()
        return data

class CategoryDialog(BaseDialog):
    def __init__(self, parent=None, category=None):
        super().__init__(parent, title="编辑类目" if category else "新增类目", icon="🏷️")
        self.category = category
        self.setup_ui()
        
    def setup_ui(self):
        self.setFixedSize(450, 400)
        
        self.name_input = QLineEdit(self.category.name if self.category else "")
        self.name_input.setPlaceholderText("请输入类目名称")
        self.add_form_content(self.create_field("名称", self.name_input))
        
        self.order_spin = QSpinBox()
        self.order_spin.setValue(self.category.order if self.category else 0)
        self.add_form_content(self.create_field("排序", self.order_spin))
        
        if self.category:
            self.active_cb = QCheckBox("启用")
            self.active_cb.setChecked(self.category.is_active)
            self.active_cb.setStyleSheet(f"color: {PREMIUM_COLORS['text_heading']}; font-size: 13px;")
            self.add_form_content(self.active_cb)
            
        self.add_content(self.content_widget)
        self.create_bottom_buttons()
        
    def get_data(self):
        data = {
            'name': self.name_input.text(),
            'order': self.order_spin.value()
        }
        if self.category:
            data['is_active'] = self.active_cb.isChecked()
        return data

class NoticeDialog(BaseDialog):
    def __init__(self, parent, db_manager, notice=None):
        self.db_manager = db_manager
        self.notice = notice
        super().__init__(parent, title="编辑通告" if notice else "发布通告", icon="📢")
        self.setup_ui()
        
    def setup_ui(self):
        self.setFixedSize(600, 700)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        # 内部容器
        scroll_content = QWidget()
        scroll_content.setStyleSheet(self.input_style)
        form_layout = QVBoxLayout(scroll_content)
        form_layout.setContentsMargins(32, 20, 32, 20)
        form_layout.setSpacing(20)
        
        # 标题
        self.title_input = QLineEdit(self.notice.title if self.notice else "")
        form_layout.addLayout(self.create_field("通告标题", self.title_input))
        
        # 平台 & 类目 (一行两列)
        row1 = QHBoxLayout()
        row1.setSpacing(20)
        
        self.platform_combo = QComboBox()
        platforms = self.db_manager.get_all_platforms()
        for p in platforms:
            self.platform_combo.addItem(p.name)
        if self.notice:
            self.platform_combo.setCurrentText(self.notice.platform)
            
        self.category_combo = QComboBox()
        categories = self.db_manager.get_all_notice_categories()
        for c in categories:
            self.category_combo.addItem(c.name)
        if self.notice:
            self.category_combo.setCurrentText(self.notice.category)
            
        row1.addLayout(self.create_field("发布平台", self.platform_combo))
        row1.addLayout(self.create_field("通告类目", self.category_combo))
        form_layout.addLayout(row1)
        
        # 品牌 & 产品 (一行两列)
        row2 = QHBoxLayout()
        row2.setSpacing(20)
        
        self.brand_input = QLineEdit(self.notice.brand if self.notice else "")
        self.brand_input.setPlaceholderText("品牌名称")
        row2.addLayout(self.create_field("品牌", self.brand_input))
        
        self.product_input = QLineEdit(self.notice.product_info if self.notice else "")
        self.product_input.setPlaceholderText("产品简要描述")
        row2.addLayout(self.create_field("产品情况", self.product_input))
        form_layout.addLayout(row2)
        
        # 要求 & 粉丝 (一行两列)
        row3 = QHBoxLayout()
        row3.setSpacing(20)
        
        self.req_input = QLineEdit(self.notice.requirements if self.notice else "")
        self.req_input.setPlaceholderText("例如：图文直发，无需寄回")
        row3.addLayout(self.create_field("粉丝要求描述", self.req_input))
        
        self.min_fans_spin = QSpinBox()
        self.min_fans_spin.setRange(0, 99999999)
        self.min_fans_spin.setValue(self.notice.min_fans if self.notice else 0)
        self.min_fans_spin.setSingleStep(1000)
        row3.addLayout(self.create_field("最低粉丝数", self.min_fans_spin))
        form_layout.addLayout(row3)
        
        # 报酬 & 链接
        self.reward_input = QLineEdit(self.notice.reward if self.notice else "")
        self.reward_input.setPlaceholderText("例如：300-500元")
        form_layout.addLayout(self.create_field("预计报酬", self.reward_input))
        
        self.link_input = QLineEdit(self.notice.link if self.notice else "")
        self.link_input.setPlaceholderText("https://...")
        form_layout.addLayout(self.create_field("报名链接", self.link_input))
        
        # 日期 & 状态 (一行两列)
        row4 = QHBoxLayout()
        row4.setSpacing(20)
        
        self.publish_date = QDateEdit()
        self.publish_date.setDisplayFormat("yyyy-MM-dd")
        self.publish_date.setCalendarPopup(True)
        if self.notice and self.notice.publish_date:
            self.publish_date.setDate(self.notice.publish_date.date())
        else:
            self.publish_date.setDate(QDate.currentDate())
            
        self.status_combo = QComboBox()
        self.status_combo.addItems(['active', 'expired', 'closed'])
        if self.notice:
            self.status_combo.setCurrentText(self.notice.status)
            
        row4.addLayout(self.create_field("发布日期", self.publish_date))
        row4.addLayout(self.create_field("当前状态", self.status_combo))
        form_layout.addLayout(row4)
        
        scroll.setWidget(scroll_content)
        self.add_content(scroll, stretch=1)
        self.create_bottom_buttons()
        
    def get_data(self):
        data = {
            'title': self.title_input.text(),
            'platform': self.platform_combo.currentText(),
            'category': self.category_combo.currentText(),
            'brand': self.brand_input.text(),
            'product_info': self.product_input.text(),
            'requirements': self.req_input.text(),
            'min_fans': self.min_fans_spin.value(),
            'reward': self.reward_input.text(),
            'link': self.link_input.text(),
            'publish_date': datetime.combine(self.publish_date.date().toPyDate(), datetime.min.time()),
            'status': self.status_combo.currentText()
        }
        return data
