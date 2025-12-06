"""
管理员链接管理模块
采用现代化玻璃拟态设计风格
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QMessageBox, QLineEdit, QFrame, 
    QGraphicsDropShadowEffect, QScrollArea, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QColor, QDesktopServices
from database import DatabaseManager
from gui.icons import Icons
from gui.admin_base_components import (
    PREMIUM_COLORS, GlassFrame, CompactStatWidget, create_action_button, create_more_button
)
import datetime


# ========== 链接列表自定义组件 ==========

# 列宽配置
LINK_LIST_COLUMNS = {
    'user': 140,
    'link_info': 280,
    'category': 100,
    'status': 80,
    'created': 130,
    'actions': 100,
}


class LinkListHeader(QFrame):
    """链接列表表头"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(f"""
            LinkListHeader {{
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
            ('用户', LINK_LIST_COLUMNS['user']),
            ('链接信息', LINK_LIST_COLUMNS['link_info']),
            ('分类', LINK_LIST_COLUMNS['category']),
            ('状态', LINK_LIST_COLUMNS['status']),
            ('创建时间', LINK_LIST_COLUMNS['created']),
            ('操作', LINK_LIST_COLUMNS['actions']),
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


class LinkRowWidget(QFrame):
    """链接行组件"""
    
    visit_clicked = pyqtSignal(object)
    delete_clicked = pyqtSignal(object)
    
    def __init__(self, link, parent=None):
        super().__init__(parent)
        self.link = link
        self.setFixedHeight(64)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet(f"""
            LinkRowWidget {{
                background: white;
                border: none;
                border-bottom: 1px solid {PREMIUM_COLORS['border_light']};
            }}
            LinkRowWidget:hover {{
                background: #fafbfc;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(0)
        
        # 1. 用户
        self._add_user(layout)
        # 2. 链接信息
        self._add_link_info(layout)
        # 3. 分类
        self._add_category(layout)
        # 4. 状态
        self._add_status(layout)
        # 5. 创建时间
        self._add_created(layout)
        # 6. 操作
        self._add_actions(layout)
        
        layout.addStretch()
    
    def _add_user(self, layout):
        container = QWidget()
        container.setFixedWidth(LINK_LIST_COLUMNS['user'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 8, 0)
        c_layout.setSpacing(8)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        user_name = self.link.user.username if self.link.user else "未知用户"
        
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
    
    def _add_link_info(self, layout):
        container = QWidget()
        container.setFixedWidth(LINK_LIST_COLUMNS['link_info'])
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 8, 0)
        c_layout.setSpacing(2)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        name_lbl = QLabel(self.link.name)
        name_lbl.setStyleSheet(f"font-size: 13px; color: {PREMIUM_COLORS['text_body']}; font-weight: 600;")
        
        url_text = self.link.url[:40] + "..." if len(self.link.url) > 40 else self.link.url
        url_lbl = QLabel(url_text)
        url_lbl.setToolTip(self.link.url)
        url_lbl.setStyleSheet(f"font-size: 11px; color: {PREMIUM_COLORS['text_hint']};")
        
        c_layout.addWidget(name_lbl)
        c_layout.addWidget(url_lbl)
        layout.addWidget(container)
    
    def _add_category(self, layout):
        container = QWidget()
        container.setFixedWidth(LINK_LIST_COLUMNS['category'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        cat_lbl = QLabel(self.link.category or "默认")
        cat_lbl.setStyleSheet(f"""
            background: {PREMIUM_COLORS['text_hint']}15;
            color: {PREMIUM_COLORS['text_body']};
            border-radius: 10px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 500;
        """)
        c_layout.addWidget(cat_lbl)
        layout.addWidget(container)
    
    def _add_status(self, layout):
        container = QWidget()
        container.setFixedWidth(LINK_LIST_COLUMNS['status'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        is_active = self.link.status == 'active'
        status_text = "激活" if is_active else "归档"
        status_lbl = QLabel(status_text)
        
        if is_active:
            status_lbl.setStyleSheet(f"""
                background: {PREMIUM_COLORS['gradient_green_start']}15;
                color: {PREMIUM_COLORS['gradient_green_start']};
                padding: 3px 10px;
                border-radius: 10px;
                font-size: 11px;
                font-weight: 600;
            """)
        else:
            status_lbl.setStyleSheet(f"""
                background: {PREMIUM_COLORS['text_hint']}15;
                color: {PREMIUM_COLORS['text_hint']};
                padding: 3px 10px;
                border-radius: 10px;
                font-size: 11px;
                font-weight: 600;
            """)
        
        c_layout.addWidget(status_lbl)
        layout.addWidget(container)
    
    def _add_created(self, layout):
        container = QWidget()
        container.setFixedWidth(LINK_LIST_COLUMNS['created'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        time_str = self.link.created_at.strftime('%Y-%m-%d %H:%M')
        lbl = QLabel(time_str)
        lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-size: 12px;")
        c_layout.addWidget(lbl)
        layout.addWidget(container)
    
    def _add_actions(self, layout):
        container = QWidget()
        container.setFixedWidth(LINK_LIST_COLUMNS['actions'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(6)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # 访问按钮
        btn_visit = create_action_button("访问", PREMIUM_COLORS['gradient_blue_start'])
        btn_visit.clicked.connect(lambda: self.visit_clicked.emit(self.link))
        c_layout.addWidget(btn_visit)
        
        # 更多菜单
        more_btn = create_more_button()
        more_btn.clicked.connect(lambda: self._show_more_menu(more_btn))
        c_layout.addWidget(more_btn)
        
        layout.addWidget(container)
    
    def _show_more_menu(self, button):
        menu = QMenu(self)
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        menu.setStyleSheet(f"""
            QMenu {{
                background: white;
                border: 1px solid {PREMIUM_COLORS['border_light']};
                border-radius: 10px;
                padding: 6px;
            }}
            QMenu::item {{
                padding: 8px 20px;
                border-radius: 6px;
                color: {PREMIUM_COLORS['text_body']};
                font-size: 12px;
                font-weight: 500;
            }}
            QMenu::item:selected {{
                background: {PREMIUM_COLORS['background']};
                color: {PREMIUM_COLORS['gradient_blue_start']};
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect(menu)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 25))
        shadow.setOffset(0, 4)
        menu.setGraphicsEffect(shadow)
        
        delete_action = menu.addAction("🗑️ 删除链接")
        delete_action.triggered.connect(lambda: self.delete_clicked.emit(self.link))
        
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))


class LinkListWidget(QWidget):
    """链接列表组件"""
    
    visit_link = pyqtSignal(object)
    delete_link = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.row_widgets = []
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.header = LinkListHeader()
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
    
    def set_links(self, links):
        for widget in self.row_widgets:
            widget.deleteLater()
        self.row_widgets.clear()
        
        if not links:
            empty_label = QLabel("暂无链接数据")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet(f"""
                color: {PREMIUM_COLORS['text_hint']};
                font-size: 14px;
                padding: 60px;
            """)
            self.content_layout.addWidget(empty_label)
            self.row_widgets.append(empty_label)
            return
        
        for link in links:
            row = LinkRowWidget(link)
            row.visit_clicked.connect(self.visit_link.emit)
            row.delete_clicked.connect(self.delete_link.emit)
            
            self.content_layout.addWidget(row)
            self.row_widgets.append(row)

class AdminLinkManager(QWidget):
    """管理员链接管理页面"""
    
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
        
        title_label = QLabel("链接管理")
        title_label.setStyleSheet(f"""
            font-size: 24px; 
            font-weight: 800; 
            color: {PREMIUM_COLORS['text_heading']};
            background: transparent;
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addSpacing(16)
        
        cards_data = [
            ("链接总数", 0, "🔗", PREMIUM_COLORS['gradient_blue_start'], PREMIUM_COLORS['gradient_blue_end']),
            ("激活状态", 0, "✅", PREMIUM_COLORS['gradient_green_start'], PREMIUM_COLORS['gradient_green_end']),
            ("今日新增", 0, "📅", PREMIUM_COLORS['gradient_purple_start'], PREMIUM_COLORS['gradient_purple_end']),
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
        self.search_input.setPlaceholderText("搜索用户/链接名称/URL...")
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
        
        # 自定义链接列表
        self.link_list = LinkListWidget()
        self.link_list.visit_link.connect(self.visit_link)
        self.link_list.delete_link.connect(self.delete_link)
        
        card_layout.addWidget(self.link_list, 1)
        
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
        
        # 获取统计数据
        stats = self.db_manager.get_statistics()
        if "链接总数" in self.stat_cards:
            self.stat_cards["链接总数"].update_value(stats.get('total_links', 0))
        if "激活状态" in self.stat_cards:
            self.stat_cards["激活状态"].update_value(stats.get('active_links', 0))
        # 今日新增可以从 get_all_links_admin 过滤出来，或者简单地不显示准确的"今日新增"而显示其他
        # 这里为了简单，我们暂时不单独查询今日新增链接，或者如果需要可以加方法
        
        # 获取分页数据
        offset = (self.current_page - 1) * self.page_size
        result = self.db_manager.get_all_links_admin(keyword=keyword, limit=self.page_size, offset=offset)
        
        self.total_records = result['total']
        self.total_pages = max(1, (self.total_records + self.page_size - 1) // self.page_size)
        
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
            
        self.link_list.set_links(result['links'])
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
    
    def visit_link(self, link):
        """访问链接"""
        QDesktopServices.openUrl(QUrl(link.url))
        
    def delete_link(self, link):
        """删除链接"""
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除链接 '{link.name}' 吗？\n此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if DatabaseManager.delete_link(str(link.id)):
                self.load_data()
                QMessageBox.information(self, "成功", "链接已删除")

