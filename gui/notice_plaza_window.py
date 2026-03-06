import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QScrollArea, QFrame, 
                             QGridLayout, QComboBox, QLineEdit, QCheckBox,
                             QButtonGroup, QDateEdit, QApplication, QMessageBox,
                             QGraphicsDropShadowEffect, QTextEdit, QLayout,
                             QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QDate, QEvent, QRect, QPoint
from PyQt6.QtGui import QColor, QFont, QIcon, QCursor

from database.db_manager import DatabaseManager
from .styles import COLORS, GLOBAL_STYLE
from .icons import Icons

class NestedScrollArea(QScrollArea):
    """不向父级冒泡滚轮事件的 ScrollArea"""
    def wheelEvent(self, event):
        sb = self.verticalScrollBar()
        if sb.isVisible():
            event.accept()
            sb.setValue(sb.value() - event.angleDelta().y())
        else:
            event.ignore()


class NestedTextEdit(QTextEdit):
    """不向父级冒泡滚轮事件的只读 TextEdit"""
    def wheelEvent(self, event):
        sb = self.verticalScrollBar()
        if sb.isVisible() and sb.maximum() > 0:
            event.accept()
            sb.setValue(sb.value() - event.angleDelta().y())
        else:
            event.ignore()

    def contextMenuEvent(self, event):
        event.ignore()


class TagButton(QPushButton):
    """标签按钮 - 紧凑胶囊样式"""
    def __init__(self, text, parent=None, is_active=False):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setChecked(is_active)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(30)
        self.update_style()
        self.toggled.connect(self.update_style)
    
    def update_style(self):
        if self.isChecked():
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                              stop:0 {COLORS['primary']}, 
                                              stop:1 {COLORS['primary_dark']});
                    color: white;
                    border: none;
                    border-radius: 15px;
                    padding: 0 14px;
                    font-weight: 600;
                    font-size: 13px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: #F5F5F7;
                    color: {COLORS['text_secondary']};
                    border: 1px solid #E5E5EA;
                    border-radius: 15px;
                    padding: 0 14px;
                    font-size: 13px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: #E8E8ED;
                    border-color: {COLORS['primary']};
                    color: {COLORS['primary']};
                }}
            """)

class FlowLayout(QLayout):
    """自动换行的流式布局"""
    def __init__(self, parent=None, margin=0, spacing=6):
        super().__init__(parent)
        self._items = []
        self._spacing = spacing
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect, test_only):
        m = self.contentsMargins()
        effective = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y = effective.x(), effective.y()
        line_height = 0

        for item in self._items:
            w = item.sizeHint().width()
            h = item.sizeHint().height()
            if x + w > effective.right() + 1 and line_height > 0:
                x = effective.x()
                y += line_height + self._spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x += w + self._spacing
            line_height = max(line_height, h)

        return y + line_height - rect.y() + m.bottom()


class FlowTagsWidget(QWidget):
    """使用 FlowLayout 展示多个类目标签，自动换行"""
    def __init__(self, tags, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        flow = FlowLayout(self, margin=0, spacing=5)
        for tag_text in tags:
            lbl = QLabel(tag_text)
            lbl.setStyleSheet("""
                background-color: #FEF3C7;
                color: #D97706;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
            """)
            lbl.adjustSize()
            lbl.setFixedSize(lbl.sizeHint())
            flow.addWidget(lbl)


class NoticeCardWidget(QFrame):
    """通告卡片组件 - 简化版，直接显示内容"""
    
    join_clicked = pyqtSignal(object)  # 链接信号，传递卡片自身
    
    MAX_VISIBLE_TAGS = 2
    
    def __init__(self, notice, parent=None, is_added=False, selected_category=None):
        super().__init__(parent)
        self.notice = notice
        self.is_loading = False
        self.is_added = is_added
        self.selected_category = selected_category
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.init_ui()
        
    def init_ui(self):
        self.setFixedWidth(300)  # 更紧凑的宽度
        self.setFixedHeight(340)  # 增加高度以显示更多内容
        
        # 阴影效果
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(12)
        self.shadow.setColor(QColor(0, 0, 0, 15))
        self.shadow.setOffset(0, 3)
        self.setGraphicsEffect(self.shadow)
        
        # 卡片基础样式
        self.setStyleSheet(f"""
            NoticeCardWidget {{
                background-color: white;
                border-radius: 12px;
                border: 1px solid {COLORS['border_light']};
            }}
            NoticeCardWidget:hover {{
                border: 1px solid {COLORS['primary_light']};
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        self.setLayout(layout)
        
        # 1. 头部：平台 + 类目标签(最多2个) + 日期，同一行
        top_row = QHBoxLayout()
        top_row.setSpacing(6)
        
        platform_tag = QLabel(self.notice.platform)
        platform_tag.setStyleSheet(f"""
            background-color: #EEF2FF;
            color: {COLORS['primary']};
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 12px;
            font-weight: 600;
        """)
        platform_tag.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        top_row.addWidget(platform_tag)
        
        cats = self.notice.category if isinstance(self.notice.category, list) else ([self.notice.category] if self.notice.category else [])
        cats = [c for c in cats if c]
        
        if cats and self.selected_category and self.selected_category in cats:
            cats = [self.selected_category] + [c for c in cats if c != self.selected_category]
        
        visible_cats = cats[:self.MAX_VISIBLE_TAGS]
        hidden_count = len(cats) - len(visible_cats)
        
        for tag_text in visible_cats:
            lbl = QLabel(tag_text)
            lbl.setStyleSheet("""
                background-color: #FEF3C7;
                color: #D97706;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
            """)
            lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            top_row.addWidget(lbl)
        
        if hidden_count > 0:
            more_lbl = QLabel(f"+{hidden_count}")
            more_lbl.setStyleSheet(f"""
                background-color: #F3F4F6;
                color: {COLORS['text_tertiary']};
                border-radius: 4px;
                padding: 3px 6px;
                font-size: 11px;
                font-weight: 600;
            """)
            more_lbl.setToolTip("、".join(cats[self.MAX_VISIBLE_TAGS:]))
            more_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            top_row.addWidget(more_lbl)
        
        top_row.addStretch()
        
        if self.notice.publish_date:
            date_str = self.notice.publish_date.strftime('%m-%d')
            date_label = QLabel(date_str)
            date_label.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 12px;")
            top_row.addWidget(date_label)
        
        layout.addLayout(top_row)
        
        # 2. 通告内容 - 使用只读 QTextEdit，自带完整滚动支持
        content = self._get_full_content()
        
        self.content_edit = NestedTextEdit()
        self.content_edit.setPlainText(content)
        self.content_edit.setReadOnly(True)
        self.content_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.content_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
                color: {COLORS['text_primary']};
                line-height: 1.5;
            }}
            QScrollBar:vertical {{
                width: 4px;
                background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: #D1D5DB;
                border-radius: 2px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        layout.addWidget(self.content_edit, 1)
        
        # 3. 底部按钮 - 根据是否已添加显示不同状态
        self.join_btn = QPushButton()
        self.join_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.join_btn.setFixedHeight(38)
        
        if self.is_added:
            self._set_added_style()
        else:
            self.join_btn.setText("加入链接")
            self._update_btn_style()
            self.join_btn.clicked.connect(lambda: self.join_clicked.emit(self))
        
        layout.addWidget(self.join_btn)
    
    def _update_btn_style(self, loading=False):
        """更新按钮样式"""
        font_family = '"PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif'
        if loading:
            self.join_btn.setStyleSheet(f"""
                QPushButton {{
                    background: #9CA3AF;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 14px;
                    font-family: {font_family};
                    padding: 4px 0;
                }}
            """)
        else:
            self.join_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['primary']};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 14px;
                    font-family: {font_family};
                    padding: 4px 0;
                }}
                QPushButton:hover {{
                    background: {COLORS['primary_light']};
                }}
                QPushButton:pressed {{
                    background: {COLORS['primary_dark']};
                }}
            """)
    
    def _set_added_style(self):
        """设置已添加状态样式"""
        self.is_added = True
        self.join_btn.setText("已添加 ✓")
        self.join_btn.setEnabled(False)
        font_family = '"PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif'
        self.join_btn.setStyleSheet(f"""
            QPushButton {{
                background: #10B981;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
                font-family: {font_family};
                padding: 4px 0;
            }}
        """)
    
    def set_loading(self, loading: bool):
        """设置 loading 状态"""
        self.is_loading = loading
        self.join_btn.setEnabled(not loading)
        self.join_btn.setText("添加中..." if loading else "加入链接")
        self._update_btn_style(loading)
        QApplication.processEvents()  # 立即更新UI
    
    def _get_full_content(self):
        """获取完整内容"""
        if self.notice.content:
            return self.notice.content
        # 兼容旧数据
        parts = []
        if self.notice.title:
            parts.append(self.notice.title)
        if self.notice.brand:
            parts.append(f"品牌：{self.notice.brand}")
        if self.notice.product_info:
            parts.append(f"产品：{self.notice.product_info}")
        if self.notice.reward:
            parts.append(f"报酬：{self.notice.reward}")
        if self.notice.link:
            parts.append(f"链接：{self.notice.link}")
        return "\n".join(parts) if parts else "暂无内容"

    def enterEvent(self, event):
        # 鼠标悬停效果
        self.shadow.setBlurRadius(25)
        self.shadow.setColor(QColor(0, 0, 0, 30))
        self.shadow.setOffset(0, 8)
        super().enterEvent(event)

    def leaveEvent(self, event):
        # 鼠标移开恢复
        self.shadow.setBlurRadius(15)
        self.shadow.setColor(QColor(0, 0, 0, 20))
        self.shadow.setOffset(0, 4)
        super().leaveEvent(event)


class NoticePlazaWindow(QMainWindow):
    """通告广场窗口"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.current_category = None
        self.current_platform = None
        self.page = 1
        self.page_size = 12  # 3x4 或 4x3
        
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        self.setWindowTitle("通告广场")
        self.setGeometry(100, 100, 1280, 850)
        self.setStyleSheet(GLOBAL_STYLE)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        central_widget.setLayout(main_layout)
        
        # 顶部：筛选区头部（控制折叠）- 紧凑版
        filter_header = QWidget()
        filter_header.setFixedHeight(44)
        filter_header.setStyleSheet("background-color: white;")
        filter_header_layout = QHBoxLayout()
        filter_header_layout.setContentsMargins(24, 0, 24, 0)
        
        filter_title = QLabel("筛选条件")
        filter_title.setStyleSheet(f"font-weight: 700; font-size: 16px; color: {COLORS['text_primary']};")
        filter_header_layout.addWidget(filter_title)
        
        filter_header_layout.addStretch()
        
        self.toggle_filter_btn = QPushButton("收起筛选 🔼")
        self.toggle_filter_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_filter_btn.setStyleSheet(f"""
            QPushButton {{
                border: none;
                color: {COLORS['text_secondary']};
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                color: {COLORS['primary']};
            }}
        """)
        self.toggle_filter_btn.clicked.connect(self.toggle_filters)
        filter_header_layout.addWidget(self.toggle_filter_btn)
        
        filter_header.setLayout(filter_header_layout)
        main_layout.addWidget(filter_header)

        # 顶部：筛选区内容 - 紧凑布局
        self.filter_container = QWidget()
        self.filter_container.setStyleSheet(f"background-color: white; border-bottom: 1px solid {COLORS['border']};")
        filter_layout = QVBoxLayout()
        filter_layout.setContentsMargins(24, 12, 24, 16)
        filter_layout.setSpacing(10)
        self.filter_container.setLayout(filter_layout)
        
        # 1. 类目筛选 - 单行紧凑
        category_layout = QHBoxLayout()
        category_layout.setSpacing(12)
        cat_label = QLabel("类目：")
        cat_label.setFixedWidth(45)
        cat_label.setStyleSheet(f"font-weight: 600; font-size: 14px; color: {COLORS['text_primary']};")
        category_layout.addWidget(cat_label)
        
        self.category_group = QButtonGroup(self)
        self.category_group.setExclusive(True)
        self.category_layout_container = QHBoxLayout()
        self.category_layout_container.setSpacing(8)
        
        category_layout.addLayout(self.category_layout_container)
        category_layout.addStretch()
        filter_layout.addLayout(category_layout)
        
        # 2. 平台筛选 - 单行紧凑
        platform_layout = QHBoxLayout()
        platform_layout.setSpacing(12)
        plat_label = QLabel("平台：")
        plat_label.setFixedWidth(45)
        plat_label.setStyleSheet(f"font-weight: 600; font-size: 14px; color: {COLORS['text_primary']};")
        platform_layout.addWidget(plat_label)
        
        self.platform_group = QButtonGroup(self)
        self.platform_group.setExclusive(True)
        self.platform_layout_container = QHBoxLayout()
        self.platform_layout_container.setSpacing(8)
        
        platform_layout.addLayout(self.platform_layout_container)
        platform_layout.addStretch()
        filter_layout.addLayout(platform_layout)
        
        # 3. 搜索和筛选按钮 - 同一行
        action_layout = QHBoxLayout()
        action_layout.setSpacing(12)
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索通告内容...")
        self.search_input.setFixedHeight(36)
        self.search_input.setMinimumWidth(250)
        self.search_input.setMaximumWidth(400)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background: #F3F4F6;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                padding: 0 12px;
                color: {COLORS['text_primary']};
                font-size: 14px;
            }}
            QLineEdit:focus {{
                background: white;
                border-color: {COLORS['primary']};
            }}
        """)
        self.search_input.returnPressed.connect(self.refresh_notices)
        action_layout.addWidget(self.search_input)
        
        action_layout.addStretch()
        
        # 筛选按钮
        search_btn = QPushButton("筛选")
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.setFixedSize(80, 36)
        search_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: {COLORS['primary_light']};
            }}
            QPushButton:pressed {{
                background: {COLORS['primary_dark']};
            }}
        """)
        search_btn.clicked.connect(self.refresh_notices)
        action_layout.addWidget(search_btn)
        
        filter_layout.addLayout(action_layout)
        
        main_layout.addWidget(self.filter_container)
        
        # 中间：内容区 - 紧凑网格
        content_area = QScrollArea()
        content_area.setWidgetResizable(True)
        content_area.setFrameShape(QFrame.Shape.NoFrame)
        content_area.setStyleSheet(f"background-color: {COLORS['background']};")
        
        self.cards_container = QWidget()
        self.cards_grid = QGridLayout()
        self.cards_grid.setSpacing(16)
        self.cards_grid.setContentsMargins(20, 16, 20, 16)
        self.cards_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.cards_container.setLayout(self.cards_grid)
        
        content_area.setWidget(self.cards_container)
        main_layout.addWidget(content_area)
        
        # 底部：分页 - 紧凑版
        footer_container = QWidget()
        footer_container.setFixedHeight(56)
        footer_container.setStyleSheet("background-color: white; border-top: 1px solid #E5E5EA;")
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(24, 0, 24, 0)
        
        # 分页按钮样式
        page_btn_style = f"""
            QPushButton {{
                background: white;
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                color: {COLORS['text_primary']};
                font-weight: 600;
            }}
            QPushButton:hover {{
                border-color: {COLORS['primary']};
                color: {COLORS['primary']};
            }}
            QPushButton:disabled {{
                background: #F3F4F6;
                border-color: transparent;
                color: {COLORS['text_tertiary']};
            }}
        """
        
        self.prev_btn = QPushButton("<")
        self.prev_btn.setFixedSize(40, 40)
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.setStyleSheet(page_btn_style)
        self.prev_btn.clicked.connect(self.prev_page)
        
        self.page_label = QLabel("1 / 1")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setFixedWidth(80)
        self.page_label.setStyleSheet(f"font-weight: 600; color: {COLORS['text_secondary']};")
        
        self.next_btn = QPushButton(">")
        self.next_btn.setFixedSize(40, 40)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setStyleSheet(page_btn_style)
        self.next_btn.clicked.connect(self.next_page)
        
        self.home_btn = QPushButton("⌂")
        self.home_btn.setFixedSize(40, 40)
        self.home_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.home_btn.setToolTip("返回第一页")
        self.home_btn.setStyleSheet(f"""
            QPushButton {{
                background: white;
                border: 1px solid {COLORS['primary']};
                border-radius: 8px;
                color: {COLORS['primary']};
                font-weight: 700;
                font-size: 18px;
            }}
            QPushButton:hover {{
                background: {COLORS['primary']};
                color: white;
            }}
            QPushButton:disabled {{
                background: #F3F4F6;
                border-color: transparent;
                color: {COLORS['text_tertiary']};
            }}
        """)
        self.home_btn.clicked.connect(self.go_first_page)

        footer_layout.addStretch()
        footer_layout.addWidget(self.home_btn)
        footer_layout.addWidget(self.prev_btn)
        footer_layout.addWidget(self.page_label)
        footer_layout.addWidget(self.next_btn)
        footer_layout.addStretch()
        
        footer_container.setLayout(footer_layout)
        main_layout.addWidget(footer_container)
    
    def toggle_filters(self):
        """切换筛选区显示状态"""
        if self.filter_container.isVisible():
            self.filter_container.setVisible(False)
            self.toggle_filter_btn.setText("展开筛选 🔽")
            # 添加底边框给header，因为filter_container隐藏了，它的底边框也不见了
            self.toggle_filter_btn.parentWidget().setStyleSheet(f"background-color: white; border-bottom: 1px solid {COLORS['border']};")
        else:
            self.filter_container.setVisible(True)
            self.toggle_filter_btn.setText("收起筛选 🔼")
            # 移除header的底边框，使用filter_container的底边框
            self.toggle_filter_btn.parentWidget().setStyleSheet("background-color: white;")

    def load_data(self):
        """加载初始化数据"""
        # 加载类目
        categories = self.db_manager.get_all_notice_categories()
        # 添加"全部"选项
        all_cat_btn = TagButton("全部", is_active=True)
        all_cat_btn.clicked.connect(lambda: self.on_category_changed(None))
        self.category_group.addButton(all_cat_btn)
        self.category_layout_container.addWidget(all_cat_btn)
        
        for cat in categories:
            btn = TagButton(cat.name)
            btn.clicked.connect(lambda checked, c=cat.name: self.on_category_changed(c))
            self.category_group.addButton(btn)
            self.category_layout_container.addWidget(btn)
            
        # 加载平台
        platforms = self.db_manager.get_all_platforms()
        all_plat_btn = TagButton("全部", is_active=True)
        all_plat_btn.clicked.connect(lambda: self.on_platform_changed(None))
        self.platform_group.addButton(all_plat_btn)
        self.platform_layout_container.addWidget(all_plat_btn)
        
        for plat in platforms:
            btn = TagButton(plat.name)
            btn.clicked.connect(lambda checked, p=plat.name: self.on_platform_changed(p))
            self.platform_group.addButton(btn)
            self.platform_layout_container.addWidget(btn)
        
        # 加载通告
        self.refresh_notices()
        
    def on_category_changed(self, category):
        self.current_category = category
        self.page = 1
        self.refresh_notices()
        
    def on_platform_changed(self, platform):
        self.current_platform = platform
        self.page = 1
        self.refresh_notices()
        
    def refresh_notices(self):
        """刷新通告列表"""
        import re
        
        # 清空现有的
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 获取搜索关键词
        keyword = self.search_input.text().strip() if hasattr(self, 'search_input') else None
        
        # 获取数据
        notices = self.db_manager.get_all_notices(
            category=self.current_category,
            platform=self.current_platform,
            keyword=keyword if keyword else None
        )
        
        # 简单的分页逻辑
        total = len(notices)
        total_pages = (total + self.page_size - 1) // self.page_size
        if total_pages == 0: total_pages = 1
        
        self.page_label.setText(f"{self.page} / {total_pages}")
        self.home_btn.setEnabled(self.page > 1)
        self.prev_btn.setEnabled(self.page > 1)
        self.next_btn.setEnabled(self.page < total_pages)
        
        start = (self.page - 1) * self.page_size
        end = start + self.page_size
        current_notices = notices[start:end]
        
        # 获取当前用户已添加的链接URL集合（用于判断是否已添加）
        user = self.parent().current_user if self.parent() else None
        user_link_urls = set()
        if user:
            try:
                user_links = self.db_manager.get_all_links(user=user)
                user_link_urls = {link.url for link in user_links}
            except Exception:
                pass
        
        # 渲染卡片
        cols = 4  # 固定4列
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        
        for i, notice in enumerate(current_notices):
            # 检查该通告的链接是否已添加
            is_added = False
            if user_link_urls:
                content = notice.content if notice.content else ""
                links = re.findall(url_pattern, content)
                if links and links[0] in user_link_urls:
                    is_added = True
            
            card = NoticeCardWidget(notice, is_added=is_added, selected_category=self.current_category)
            card.join_clicked.connect(self.add_to_my_links)
            row = i // cols
            col = i % cols
            self.cards_grid.addWidget(card, row, col)
            
    def go_first_page(self):
        if self.page > 1:
            self.page = 1
            self.refresh_notices()

    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.refresh_notices()
            
    def next_page(self):
        self.page += 1
        self.refresh_notices()
        
    def _is_supported_platform(self, url):
        """检查链接是否为支持的平台"""
        supported_domains = [
            "docs.qq.com", "wj.qq.com", "shimo.im",
            "wjx.cn", "wjx.top", "jsj.top", "jinshuju.net",
            "feishu.cn", "kdocs.cn", "wps.cn", "wps.com",
            "wenjuan.com", "baominggongju.com", "fanqier.cn",
            "credamo.com", "mikecrm.com", "mike-x.com",
        ]
        return any(domain in url for domain in supported_domains)

    def add_to_my_links(self, card: NoticeCardWidget):
        """将通告直接添加到我的链接"""
        import re
        
        notice = card.notice
        
        card.set_loading(True)
        
        try:
            content = notice.content if notice.content else ""
            if not content and notice.title:
                parts = []
                if notice.title:
                    parts.append(f"标题：{notice.title}")
                if notice.brand:
                    parts.append(f"品牌：{notice.brand}")
                if notice.product_info:
                    parts.append(f"产品：{notice.product_info}")
                if notice.reward:
                    parts.append(f"报酬：{notice.reward}")
                if notice.link:
                    parts.append(f"链接：{notice.link}")
                content = "\n".join(parts)
            
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            links = re.findall(url_pattern, content)
            
            if not links:
                QMessageBox.warning(self, "提示", "未在通告内容中检测到有效链接！")
                return
            
            user = self.parent().current_user if self.parent() else None
            if not user:
                QMessageBox.warning(self, "提示", "请先登录后再添加链接！")
                return
            
            link_url = links[0]
            
            if not self._is_supported_platform(link_url):
                QMessageBox.warning(self, "提示", "您上传的链接平台暂不支持")
                return
            
            existing_link = self.db_manager.get_link_by_url(link_url, user=user)
            if existing_link:
                reply = QMessageBox.question(
                    self, "提示", "该链接已上传，是否继续上传？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            link_name = f"【{notice.platform}】{content[:30]}..." if len(content) > 30 else f"【{notice.platform}】{content}"
            link_name = link_name.replace('\n', ' ')
            
            self.db_manager.create_link(
                name=link_name,
                url=link_url,
                user=user,
                status='active',
                category=(notice.category[0] if isinstance(notice.category, list) and notice.category else (notice.category or '默认分类')),
                description=f"来自通告广场"
            )
            
            if self.parent() and hasattr(self.parent(), 'refresh_links_list'):
                self.parent().refresh_links_list()
            
            card._set_added_style()
            
        except Exception as e:
            QMessageBox.warning(self, "失败", f"添加链接失败：{str(e)}")
            card.set_loading(False)
        finally:
            if card.join_btn.text() == "添加中...":
                card.set_loading(False)

    def copy_link(self, link):
        QApplication.clipboard().setText(link)
        QMessageBox.information(self, "成功", "报名链接已复制到剪贴板！")

if __name__ == "__main__":
    # 测试代码
    from database.models import init_database
    init_database()
    
    app = QApplication(sys.argv)
    window = NoticePlazaWindow()
    window.show()
    sys.exit(app.exec())

