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
    QDateEdit, QLayout, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QDateTime, QDate
from PyQt6.QtGui import QFont, QColor, QIcon, QPainter, QLinearGradient, QPen, QBrush
from database import DatabaseManager
from gui.icons import Icons
from gui.admin_base_components import (
    PREMIUM_COLORS, GlassFrame, GradientButton, CompactStatWidget, create_action_button
)
from datetime import datetime
from gui.link_manager import is_supported_platform, extract_urls


# ========== 通告列表自定义组件 ==========

# 列宽配置（简化版）
NOTICE_LIST_COLUMNS = {
    'platform': 80,
    'category': 140,
    'content': 360,
    'status': 80,
    'actions': 100,
}


class NoticeListHeader(QFrame):
    """通告列表表头"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(f"""
            NoticeListHeader {{
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
            ('平台', NOTICE_LIST_COLUMNS['platform']),
            ('类目', NOTICE_LIST_COLUMNS['category']),
            ('内容预览', NOTICE_LIST_COLUMNS['content']),
            ('状态', NOTICE_LIST_COLUMNS['status']),
            ('操作', NOTICE_LIST_COLUMNS['actions']),
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


class NoticeRowWidget(QFrame):
    """通告行组件（简化版）"""
    
    CONTENT_LINE_CHARS = 50
    CONTENT_MAX_LINES = 4
    
    edit_clicked = pyqtSignal(object)
    delete_clicked = pyqtSignal(object)
    
    @staticmethod
    def _normalize_lines(text):
        """将手动空格对齐的续行合并回上一个标签行，返回行列表"""
        import re
        lines = text.split('\n')
        merged = []
        for line in lines:
            stripped = line.strip().replace('\u3000', '').strip()
            if not stripped:
                merged.append('')
                continue
            if re.match(r'【.+?】', stripped):
                merged.append(stripped)
            else:
                if merged and merged[-1]:
                    merged[-1] += stripped
                else:
                    merged.append(stripped)
        return merged

    @staticmethod
    def _build_preview_html(lines, text_color):
        """将行列表转为 HTML，【标签】行用 table 两列对齐，含 URL 的行单独处理"""
        import re
        from html import escape
        tag_pattern = re.compile(r'^(【.+?】[：:]\s*)(.*)', re.DOTALL)
        url_pattern = re.compile(r'(https?://[^\s<>"{}|\\^`\[\]]+)')
        parts = [f'<div style="font-size:12px; color:{text_color}; line-height:1.5;">']
        for line in lines:
            if not line:
                continue
            m = tag_pattern.match(line)
            if m:
                label = escape(m.group(1))
                value = m.group(2)
                url_m = url_pattern.search(value)
                if url_m:
                    before = escape(value[:url_m.start()].strip())
                    url = escape(url_m.group(1))
                    after = escape(value[url_m.end():].strip())
                    value_html = ''
                    if before:
                        value_html += before
                    value_html += f'<div style="word-break:break-all; margin-top:1px;">{url}</div>'
                    if after:
                        value_html += after
                    parts.append(
                        f'<div style="margin:0;"><span style="font-weight:600;">{label}</span>{value_html}</div>'
                    )
                else:
                    value_escaped = escape(value)
                    value_escaped = value_escaped.replace('，', '，<br/>')
                    value_escaped = value_escaped.replace(',', ',<br/>')
                    parts.append(
                        f'<table cellspacing="0" cellpadding="0" style="border:none; margin:0;">'
                        f'<tr><td style="white-space:nowrap; vertical-align:top; font-weight:600; padding:0;">{label}</td>'
                        f'<td style="vertical-align:top; padding:0;">{value_escaped}</td></tr></table>'
                    )
            else:
                url_m = url_pattern.search(line)
                if url_m:
                    before = escape(line[:url_m.start()])
                    url = escape(url_m.group(1))
                    after = escape(line[url_m.end():])
                    parts.append(f'<p style="margin:0; word-break:break-all;">{before}{url}{after}</p>')
                else:
                    parts.append(f'<p style="margin:0;">{escape(line)}</p>')
        parts.append('</div>')
        return ''.join(parts)
    
    def __init__(self, notice, parent=None):
        super().__init__(parent)
        self.notice = notice
        self.setMinimumHeight(60)
        self.setMaximumHeight(self.CONTENT_MAX_LINES * 18 + 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet(f"""
            NoticeRowWidget {{
                background: white;
                border: none;
                border-bottom: 1px solid {PREMIUM_COLORS['border_light']};
            }}
            NoticeRowWidget:hover {{
                background: #fafbfc;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(0)
        
        # 1. 平台
        self._add_platform(layout)
        # 2. 类目
        self._add_category(layout)
        # 3. 内容预览
        self._add_content(layout)
        # 4. 状态
        self._add_status(layout)
        # 5. 操作
        self._add_actions(layout)
        
        layout.addStretch()
    
    def _add_platform(self, layout):
        container = QWidget()
        container.setFixedWidth(NOTICE_LIST_COLUMNS['platform'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        plat_lbl = QLabel(self.notice.platform)
        plat_lbl.setStyleSheet(f"""
            background: {PREMIUM_COLORS['primary']}15;
            color: {PREMIUM_COLORS['primary']};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 11px;
            font-weight: 600;
        """)
        c_layout.addWidget(plat_lbl)
        layout.addWidget(container)
    
    def _add_category(self, layout):
        container = QWidget()
        container.setFixedWidth(NOTICE_LIST_COLUMNS['category'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setSpacing(4)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        cats = self.notice.category if isinstance(self.notice.category, list) else ([self.notice.category] if self.notice.category else [])
        if cats:
            full_text = "、".join(cats)
            lbl = QLabel(full_text)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-size: 12px;")
            lbl.setToolTip(full_text)
            lbl.setMaximumWidth(NOTICE_LIST_COLUMNS['category'] - 8)
            c_layout.addWidget(lbl)
        else:
            lbl = QLabel("-")
            lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-size: 12px;")
            c_layout.addWidget(lbl)
        layout.addWidget(container)
    
    def _add_content(self, layout):
        """内容预览 - HTML 渲染，标签与内容两列对齐"""
        container = QWidget()
        container.setFixedWidth(NOTICE_LIST_COLUMNS['content'])
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 8, 0)
        
        raw = self.notice.content if self.notice.content else (self.notice.title or "")
        lines = NoticeRowWidget._normalize_lines(raw)
        html = NoticeRowWidget._build_preview_html(lines, PREMIUM_COLORS['text_heading'])
        
        content_area = QScrollArea()
        content_area.setWidgetResizable(True)
        content_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        content_area.setFixedHeight(self.CONTENT_MAX_LINES * 18 + 8)
        content_area.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{ background: transparent; width: 6px; }}
            QScrollBar::handle:vertical {{ background: {PREMIUM_COLORS['border']}; border-radius: 3px; min-height: 20px; }}
            QScrollBar::handle:vertical:hover {{ background: {PREMIUM_COLORS['text_hint']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        """)
        
        content_lbl = QLabel(html)
        content_lbl.setWordWrap(True)
        content_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        content_lbl.setStyleSheet("background: transparent;")
        content_lbl.setMaximumWidth(NOTICE_LIST_COLUMNS['content'] - 16)
        content_area.setWidget(content_lbl)
        c_layout.addWidget(content_area)
        
        content_lbl.setToolTip(raw[:500])
        layout.addWidget(container)
    
    def _add_status(self, layout):
        container = QWidget()
        container.setFixedWidth(NOTICE_LIST_COLUMNS['status'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        status_map = {
            'active': ('进行中', PREMIUM_COLORS['mint']),
            'expired': ('已过期', PREMIUM_COLORS['text_hint']),
            'closed': ('已关闭', PREMIUM_COLORS['coral'])
        }
        text, color = status_map.get(self.notice.status, (self.notice.status, PREMIUM_COLORS['text_body']))
        
        status_lbl = QLabel(text)
        status_lbl.setStyleSheet(f"color: {color}; font-weight: 600; font-size: 12px;")
        c_layout.addWidget(status_lbl)
        layout.addWidget(container)
    
    def _add_actions(self, layout):
        container = QWidget()
        container.setFixedWidth(NOTICE_LIST_COLUMNS['actions'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(6)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        btn_edit = create_action_button("编辑", PREMIUM_COLORS['gradient_blue_start'])
        btn_edit.clicked.connect(lambda: self.edit_clicked.emit(self.notice))
        c_layout.addWidget(btn_edit)
        
        btn_del = create_action_button("删除", PREMIUM_COLORS['coral'])
        btn_del.clicked.connect(lambda: self.delete_clicked.emit(self.notice))
        c_layout.addWidget(btn_del)
        
        layout.addWidget(container)


class NoticeListWidget(QWidget):
    """通告列表组件"""
    
    edit_notice = pyqtSignal(object)
    delete_notice = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.row_widgets = []
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.header = NoticeListHeader()
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
    
    def set_notices(self, notices):
        for widget in self.row_widgets:
            widget.deleteLater()
        self.row_widgets.clear()
        
        if not notices:
            empty_label = QLabel("暂无通告数据")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet(f"""
                color: {PREMIUM_COLORS['text_hint']};
                font-size: 14px;
                padding: 60px;
            """)
            self.content_layout.addWidget(empty_label)
            self.row_widgets.append(empty_label)
            return
        
        for notice in notices:
            row = NoticeRowWidget(notice)
            row.edit_clicked.connect(self.edit_notice.emit)
            row.delete_clicked.connect(self.delete_notice.emit)
            
            self.content_layout.addWidget(row)
            self.row_widgets.append(row)

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
    
    def _create_main_card(self, layout):
        """重写主卡片创建方法，使用自定义列表组件"""
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
        
        # 自定义通告列表（替代表格）
        self.notice_list = NoticeListWidget()
        self.notice_list.edit_notice.connect(self.edit_item)
        self.notice_list.delete_notice.connect(self.delete_item)
        card_layout.addWidget(self.notice_list, 1)
        
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
        # 不再需要，已在 _create_main_card 中直接创建自定义列表
        pass
        
    def get_stats_config(self):
        return [
            ("通告总数", 0, "📢", PREMIUM_COLORS['gradient_blue_start'], PREMIUM_COLORS['gradient_blue_end']),
            ("进行中", 0, "🔥", PREMIUM_COLORS['gradient_green_start'], PREMIUM_COLORS['gradient_green_end']),
            ("已结束", 0, "🏁", PREMIUM_COLORS['gradient_orange_start'], PREMIUM_COLORS['gradient_orange_end']),
        ]
        
    def load_data(self):
        keyword = self.search_input.text().strip()
        notices = self.db_manager.get_all_notices(
            keyword=keyword if keyword else None,
            status=None
        )
        
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
        
        # 使用自定义列表组件显示数据
        self.notice_list.set_notices(current_notices)
        self.update_pagination()

    def _check_unsupported_links(self, content):
        """检查内容中是否包含不支持的链接，返回 True 表示允许继续。"""
        urls = extract_urls(content)
        if not urls:
            QMessageBox.warning(self, "无法发布", "通告内容中未检测到任何链接，请添加链接后再发布。")
            return False

        unsupported = [url for url in urls if not is_supported_platform(url)]
        if not unsupported:
            return True

        preview_list = "\n".join(f"  • {u[:80]}" for u in unsupported[:5])
        extra = f"\n  ...等共 {len(unsupported)} 个" if len(unsupported) > 5 else ""
        QMessageBox.warning(
            self, "无法发布 - 包含不支持的链接",
            f"通告内容中包含 {len(unsupported)} 个不支持的链接：\n\n{preview_list}{extra}\n\n"
            f"目前支持的平台：腾讯文档、腾讯问卷、石墨文档、问卷星、金数据、飞书、"
            f"金山文档/WPS、问卷网、报名工具、番茄表单、见数、麦客表单\n\n"
            f"请修改通告内容，替换为支持的平台链接后再发布。"
        )
        return False

    def _check_duplicate_and_confirm(self, platform, content, exclude_id=None):
        """检查重复通告，若存在则询问用户是否继续。返回 True 表示允许继续操作。"""
        duplicates = self.db_manager.check_notice_duplicate(platform, content, exclude_id)
        if not duplicates:
            return True
        
        dup_info_parts = []
        for i, dup in enumerate(duplicates[:3], 1):
            preview = (dup.content or "")[:80].replace('\n', ' ')
            created = dup.created_at.strftime('%Y-%m-%d %H:%M') if dup.created_at else "未知"
            dup_info_parts.append(f"  {i}. [{dup.platform}] {preview}...  (创建于 {created})")
        
        dup_text = "\n".join(dup_info_parts)
        extra = f"\n  ...等共 {len(duplicates)} 条重复通告" if len(duplicates) > 3 else ""
        
        reply = QMessageBox.warning(
            self, "发现重复通告",
            f"检测到已存在包含相同链接的通告：\n\n{dup_text}{extra}\n\n是否仍要继续发布？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    def add_item(self):
        dialog = NoticeDialog(self, self.db_manager)
        if dialog.exec():
            data = dialog.get_data()
            if not self._check_unsupported_links(data.get('content', '')):
                return
            if not self._check_duplicate_and_confirm(data.get('platform', ''), data.get('content', '')):
                return
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
            if not self._check_unsupported_links(data.get('content', '')):
                return
            if not self._check_duplicate_and_confirm(data.get('platform', ''), data.get('content', ''), exclude_id=str(item.id)):
                return
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
    """简化版通告对话框 - 只需要平台、类目、内容"""
    def __init__(self, parent, db_manager, notice=None):
        self.db_manager = db_manager
        self.notice = notice
        super().__init__(parent, title="编辑通告" if notice else "发布通告", icon="📢")
        self.setup_ui()
        
    def setup_ui(self):
        self.setMinimumSize(650, 600)
        self.resize(650, 700)
        
        # 用 QScrollArea 包裹表单，使整体可滚动
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
            QScrollBar::handle:vertical {{ background: {PREMIUM_COLORS['border']}; border-radius: 4px; min-height: 30px; }}
            QScrollBar::handle:vertical:hover {{ background: {PREMIUM_COLORS['text_hint']}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        """)
        
        form_widget = QWidget()
        form_widget.setStyleSheet(self.input_style)
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(32, 24, 32, 20)
        form_layout.setSpacing(20)
        
        # 平台
        self.platform_combo = QComboBox()
        self.platform_combo.blockSignals(True)
        self.platform_combo.model().blockSignals(True)
        platforms = self.db_manager.get_all_platforms()
        self.platform_combo.addItems([p.name for p in platforms])
        self.platform_combo.model().blockSignals(False)
        self.platform_combo.blockSignals(False)
        if self.notice:
            self.platform_combo.setCurrentText(self.notice.platform)
        form_layout.addLayout(self.create_field("发布平台", self.platform_combo))
        
        # 类目（多选复选框）
        category_label = QLabel("通告类目（可多选）")
        category_label.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-weight: 600; font-size: 13px;")
        form_layout.addWidget(category_label)
        
        self.category_checkboxes = []
        categories = self.db_manager.get_all_notice_categories()
        existing_cats = []
        if self.notice and self.notice.category:
            existing_cats = self.notice.category if isinstance(self.notice.category, list) else [self.notice.category]
        
        cat_flow_widget = QWidget()
        from PyQt6.QtWidgets import QGridLayout
        cat_grid_layout = QGridLayout(cat_flow_widget)
        cat_grid_layout.setContentsMargins(0, 0, 0, 0)
        cat_grid_layout.setHorizontalSpacing(16)
        cat_grid_layout.setVerticalSpacing(10)
        
        cols_per_row = 4
        for i, c in enumerate(categories):
            cb = QCheckBox(c.name)
            cb.setStyleSheet(f"""
                QCheckBox {{
                    color: {PREMIUM_COLORS['text_heading']};
                    font-size: 13px;
                    spacing: 6px;
                }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    border-radius: 4px;
                    border: 1.5px solid {PREMIUM_COLORS['border']};
                    background: #f8fafc;
                }}
                QCheckBox::indicator:checked {{
                    background: {PREMIUM_COLORS['gradient_blue_start']};
                    border-color: {PREMIUM_COLORS['gradient_blue_start']};
                }}
                QCheckBox::indicator:hover {{
                    border-color: {PREMIUM_COLORS['gradient_blue_start']};
                }}
            """)
            if c.name in existing_cats:
                cb.setChecked(True)
            cat_grid_layout.addWidget(cb, i // cols_per_row, i % cols_per_row)
            self.category_checkboxes.append(cb)
        
        form_layout.addWidget(cat_flow_widget)
        
        # 状态选择
        status_layout = QHBoxLayout()
        status_layout.setSpacing(20)
        
        self.status_combo = QComboBox()
        self.status_combo.blockSignals(True)
        self.status_combo.model().blockSignals(True)
        self.status_combo.addItems(['active', 'expired', 'closed'])
        self.status_combo.model().blockSignals(False)
        self.status_combo.blockSignals(False)
        if self.notice:
            self.status_combo.setCurrentText(self.notice.status)
        status_layout.addLayout(self.create_field("状态", self.status_combo))
        status_layout.addStretch()
        form_layout.addLayout(status_layout)
        
        # 通告内容（长文本）
        content_label = QLabel("通告内容")
        content_label.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-weight: 600; font-size: 13px;")
        form_layout.addWidget(content_label)
        
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("请输入完整的通告信息，包括：\n• 通告标题/主题\n• 品牌名称\n• 产品情况\n• 粉丝要求\n• 报酬说明\n• 报名链接\n• 其他备注...")
        self.content_edit.setStyleSheet(f"""
            QTextEdit {{
                border: 1px solid {PREMIUM_COLORS['border_light']};
                border-radius: 10px;
                padding: 12px;
                background: #f8fafc;
                font-size: 14px;
                color: {PREMIUM_COLORS['text_heading']};
                line-height: 1.6;
            }}
            QTextEdit:focus {{
                border: 1px solid {PREMIUM_COLORS['gradient_blue_start']};
                background: white;
            }}
        """)
        self.content_edit.setMinimumHeight(280)
        
        if self.notice:
            if self.notice.content:
                self.content_edit.setPlainText(self.notice.content)
            else:
                old_content = self._build_content_from_old_fields()
                self.content_edit.setPlainText(old_content)
        
        form_layout.addWidget(self.content_edit)
        
        scroll_area.setWidget(form_widget)
        self.add_content(scroll_area, stretch=1)
        self.create_bottom_buttons()
    
    def _build_content_from_old_fields(self):
        """从旧字段构建内容（兼容旧数据）"""
        parts = []
        if self.notice.title:
            parts.append(f"【标题】{self.notice.title}")
        if self.notice.subject:
            parts.append(f"【主题】{self.notice.subject}")
        if self.notice.brand:
            parts.append(f"【品牌】{self.notice.brand}")
        if self.notice.product_info:
            parts.append(f"【产品】{self.notice.product_info}")
        if self.notice.requirements:
            parts.append(f"【要求】{self.notice.requirements}")
        if self.notice.min_fans:
            parts.append(f"【粉丝要求】{self.notice.min_fans}")
        if self.notice.reward:
            parts.append(f"【报酬】{self.notice.reward}")
        if self.notice.link:
            parts.append(f"【链接】{self.notice.link}")
        return "\n".join(parts)
        
    def get_data(self):
        selected_cats = [cb.text() for cb in self.category_checkboxes if cb.isChecked()]
        data = {
            'platform': self.platform_combo.currentText(),
            'category': selected_cats,
            'content': self.content_edit.toPlainText(),
            'status': self.status_combo.currentText(),
            'publish_date': datetime.now(),
        }
        return data
