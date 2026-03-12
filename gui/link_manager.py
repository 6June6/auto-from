"""
链接管理对话框
"""
import re
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QMessageBox, QLineEdit, QLabel, QWidget,
                             QFormLayout, QComboBox, QTextEdit, QGroupBox,
                             QSplitter, QProgressBar, QFrame, QScrollArea,
                             QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QPalette, QTextCursor
from database import DatabaseManager, Link
from core.ai_parser import AIParser
from .icons import Icons
from .admin_base_components import PREMIUM_COLORS, create_action_button


# 链接列表列宽配置
LINK_LIST_COLUMNS = {
    'name': 150,
    'url': 240,
    'category': 90,
    'status': 70,
    'actions': 160
}

# QMessageBox 按钮样式修复
MESSAGEBOX_STYLE = """
    QMessageBox {
        background-color: #FFFFFF;
    }
    QMessageBox QLabel {
        color: #1D1D1F;
        font-size: 14px;
    }
    QMessageBox QPushButton {
        background-color: #007AFF;
        color: #FFFFFF;
        border: none;
        border-radius: 6px;
        padding: 8px 20px;
        font-size: 13px;
        font-weight: 600;
        min-width: 70px;
    }
    QMessageBox QPushButton:hover {
        background-color: #0056CC;
    }
    QMessageBox QPushButton:pressed {
        background-color: #004099;
    }
"""


def show_info(parent, title, message):
    """显示信息对话框"""
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setStyleSheet(MESSAGEBOX_STYLE)
    msg.exec()


def show_warning(parent, title, message):
    """显示警告对话框"""
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setStyleSheet(MESSAGEBOX_STYLE)
    msg.exec()


def show_error(parent, title, message):
    """显示错误对话框"""
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setStyleSheet(MESSAGEBOX_STYLE)
    msg.exec()


def show_question(parent, title, message):
    """显示确认对话框，返回是否点击了Yes"""
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Question)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    msg.setStyleSheet(MESSAGEBOX_STYLE)
    return msg.exec() == QMessageBox.StandardButton.Yes

from tools.link_utils import SUPPORTED_DOMAINS, is_supported_platform, extract_urls


# 解析结果列宽配置
PARSE_RESULT_COLUMNS = {
    'name': 170,
    'url': 300,
    'category': 90,
    'actions': 70
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
        
        columns = [
            ("名称", LINK_LIST_COLUMNS['name']),
            ("URL", LINK_LIST_COLUMNS['url']),
            ("分类", LINK_LIST_COLUMNS['category']),
            ("状态", LINK_LIST_COLUMNS['status']),
            ("操作", LINK_LIST_COLUMNS['actions']),
        ]
        
        for text, width in columns:
            lbl = QLabel(text)
            lbl.setFixedWidth(width)
            lbl.setStyleSheet(f"""
                color: {PREMIUM_COLORS['text_hint']};
                font-size: 12px;
                font-weight: 600;
            """)
            layout.addWidget(lbl)
        
        layout.addStretch()


class LinkRowWidget(QFrame):
    """链接行组件"""
    edit_clicked = pyqtSignal(object)
    copy_clicked = pyqtSignal(object)
    delete_clicked = pyqtSignal(object)
    
    def __init__(self, link, parent=None):
        super().__init__(parent)
        self.link = link
        self.setFixedHeight(56)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
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
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(0)
        
        # 名称
        name_lbl = QLabel(self.link.name)
        name_lbl.setFixedWidth(LINK_LIST_COLUMNS['name'])
        name_lbl.setStyleSheet(f"""
            color: {PREMIUM_COLORS['text_heading']};
            font-weight: 600;
            font-size: 13px;
        """)
        layout.addWidget(name_lbl)
        
        # URL（截断显示）
        url_text = self.link.url[:40] + "..." if len(self.link.url) > 40 else self.link.url
        url_lbl = QLabel(url_text)
        url_lbl.setFixedWidth(LINK_LIST_COLUMNS['url'])
        url_lbl.setToolTip(self.link.url)
        url_lbl.setStyleSheet(f"""
            color: {PREMIUM_COLORS['primary']};
            font-size: 12px;
        """)
        layout.addWidget(url_lbl)
        
        # 分类
        category_lbl = QLabel(self.link.category or "-")
        category_lbl.setFixedWidth(LINK_LIST_COLUMNS['category'])
        category_lbl.setStyleSheet(f"""
            color: {PREMIUM_COLORS['text_body']};
            font-size: 12px;
        """)
        layout.addWidget(category_lbl)
        
        # 状态标签
        status_widget = self._create_status_label()
        status_container = QWidget()
        status_container.setFixedWidth(LINK_LIST_COLUMNS['status'])
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.addWidget(status_widget)
        status_layout.addStretch()
        layout.addWidget(status_container)
        
        # 操作按钮
        actions_widget = QWidget()
        actions_widget.setFixedWidth(LINK_LIST_COLUMNS['actions'])
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(6)
        
        edit_btn = self._create_row_action_button("编辑", PREMIUM_COLORS['primary'])
        edit_btn.clicked.connect(lambda: self.edit_clicked.emit(self.link))
        actions_layout.addWidget(edit_btn)
        
        copy_btn = self._create_row_action_button("复制", PREMIUM_COLORS['info'])
        copy_btn.clicked.connect(lambda: self.copy_clicked.emit(self.link))
        actions_layout.addWidget(copy_btn)
        
        del_btn = self._create_row_action_button("删除", PREMIUM_COLORS['danger'])
        del_btn.clicked.connect(lambda: self.delete_clicked.emit(self.link))
        actions_layout.addWidget(del_btn)
        
        actions_layout.addStretch()
        layout.addWidget(actions_widget)
        
        layout.addStretch()
    
    def _create_status_label(self):
        """创建状态标签"""
        status_map = {
            "active": ("激活", "#34C759", "#E8F8ED"),
            "archived": ("归档", "#FF9500", "#FFF4E6"),
            "deleted": ("已删除", "#FF3B30", "#FFEBEB"),
        }
        text, color, bg_color = status_map.get(self.link.status, ("未知", "#999", "#f0f0f0"))
        
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFixedSize(52, 22)
        label.setStyleSheet(f"""
            background: {bg_color};
            color: {color};
            font-size: 11px;
            font-weight: 600;
            border-radius: 11px;
        """)
        return label
    
    def _create_row_action_button(self, text, color):
        """创建行操作按钮 - 使用实心彩色背景"""
        btn = QPushButton()
        btn.setFixedSize(48, 26)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: none;
                border-radius: 13px;
            }}
        """)
        
        # 使用 QLabel 作为按钮内容来确保文字颜色正确
        label = QLabel(text, btn)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                background: transparent;
                font-size: 11px;
                font-weight: 600;
            }
        """)
        label.setGeometry(0, 0, 48, 26)
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        return btn


class LinkListWidget(QWidget):
    """链接列表组件"""
    edit_link = pyqtSignal(object)
    copy_link = pyqtSignal(object)
    delete_link = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.row_widgets = []
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 表头
        self.header = LinkListHeader()
        layout.addWidget(self.header)
        
        # 滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background: {PREMIUM_COLORS['border']};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {PREMIUM_COLORS['text_hint']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)
        
        # 内容容器
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: white;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.content_widget)
        layout.addWidget(self.scroll_area, 1)
    
    def set_links(self, links):
        """设置链接数据"""
        # 清空现有行
        for widget in self.row_widgets:
            widget.deleteLater()
        self.row_widgets.clear()
        
        if not links:
            self._show_empty_state()
            return
        
        for link in links:
            row = LinkRowWidget(link)
            row.edit_clicked.connect(self.edit_link.emit)
            row.copy_clicked.connect(self.copy_link.emit)
            row.delete_clicked.connect(self.delete_link.emit)
            self.content_layout.addWidget(row)
            self.row_widgets.append(row)
    
    def _show_empty_state(self):
        """显示空状态"""
        empty_label = QLabel("暂无链接数据")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet(f"""
            color: {PREMIUM_COLORS['text_hint']};
            font-size: 14px;
            padding: 60px;
        """)
        self.content_layout.addWidget(empty_label)
        self.row_widgets.append(empty_label)


# ========== 解析结果列表组件 ==========

class ParseResultHeader(QFrame):
    """解析结果表头"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet(f"""
            ParseResultHeader {{
                background: {PREMIUM_COLORS['background']};
                border: none;
                border-bottom: 1px solid {PREMIUM_COLORS['border_light']};
            }}
        """)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(0)
        
        columns = [
            ("链接名称", PARSE_RESULT_COLUMNS['name']),
            ("URL", PARSE_RESULT_COLUMNS['url']),
            ("分类", PARSE_RESULT_COLUMNS['category']),
            ("操作", PARSE_RESULT_COLUMNS['actions']),
        ]
        
        for text, width in columns:
            lbl = QLabel(text)
            lbl.setFixedWidth(width)
            lbl.setStyleSheet(f"""
                color: {PREMIUM_COLORS['text_hint']};
                font-size: 12px;
                font-weight: 600;
            """)
            layout.addWidget(lbl)
        
        layout.addStretch()


class ParseResultRowWidget(QFrame):
    """解析结果行组件"""
    delete_clicked = pyqtSignal(object)  # 传递自身
    
    def __init__(self, name, url, category, parent=None):
        super().__init__(parent)
        self.name = name
        self.url = url
        self.category = category
        self.setFixedHeight(48)
        self.setStyleSheet(f"""
            ParseResultRowWidget {{
                background: white;
                border: none;
                border-bottom: 1px solid {PREMIUM_COLORS['border_light']};
            }}
            ParseResultRowWidget:hover {{
                background: #fafbfc;
            }}
        """)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(0)
        
        # 名称输入框
        self.name_input = QLineEdit(self.name)
        self.name_input.setFixedWidth(PARSE_RESULT_COLUMNS['name'] - 8)
        self.name_input.setPlaceholderText("链接名称")
        self.name_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {PREMIUM_COLORS['border']};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 12px;
                background: white;
            }}
            QLineEdit:focus {{
                border-color: {PREMIUM_COLORS['primary']};
            }}
        """)
        layout.addWidget(self.name_input)
        layout.addSpacing(8)
        
        # URL输入框
        self.url_input = QLineEdit(self.url)
        self.url_input.setFixedWidth(PARSE_RESULT_COLUMNS['url'] - 8)
        self.url_input.setPlaceholderText("URL")
        self.url_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {PREMIUM_COLORS['border']};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 12px;
                background: white;
                color: {PREMIUM_COLORS['primary']};
            }}
            QLineEdit:focus {{
                border-color: {PREMIUM_COLORS['primary']};
            }}
        """)
        layout.addWidget(self.url_input)
        layout.addSpacing(8)
        
        # 分类输入框
        self.category_input = QLineEdit(self.category)
        self.category_input.setFixedWidth(PARSE_RESULT_COLUMNS['category'] - 8)
        self.category_input.setPlaceholderText("分类")
        self.category_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {PREMIUM_COLORS['border']};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 12px;
                background: white;
            }}
            QLineEdit:focus {{
                border-color: {PREMIUM_COLORS['primary']};
            }}
        """)
        layout.addWidget(self.category_input)
        layout.addSpacing(8)
        
        # 删除按钮
        del_btn = QPushButton("删除")
        del_btn.setFixedHeight(26)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {PREMIUM_COLORS['danger']};
                border: none;
                font-size: 12px;
                padding: 0 8px;
            }}
            QPushButton:hover {{
                color: #FF1744;
                text-decoration: underline;
            }}
        """)
        del_btn.clicked.connect(lambda: self.delete_clicked.emit(self))
        layout.addWidget(del_btn)
        
        layout.addStretch()
    
    def get_data(self):
        """获取行数据"""
        return {
            'name': self.name_input.text().strip(),
            'url': self.url_input.text().strip(),
            'category': self.category_input.text().strip()
        }


class ParseResultListWidget(QWidget):
    """解析结果列表组件"""
    row_count_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.row_widgets = []
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 表头
        self.header = ParseResultHeader()
        layout.addWidget(self.header)
        
        # 滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: white;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {PREMIUM_COLORS['border']};
                border-radius: 3px;
            }}
        """)
        
        # 内容容器
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: white;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.content_widget)
        layout.addWidget(self.scroll_area, 1)
    
    def clear(self):
        """清空所有行"""
        for widget in self.row_widgets:
            widget.deleteLater()
        self.row_widgets.clear()
        self.row_count_changed.emit(0)
    
    def add_row(self, name, url, category):
        """添加一行"""
        row = ParseResultRowWidget(name, url, category)
        row.delete_clicked.connect(self._on_row_delete)
        self.content_layout.addWidget(row)
        self.row_widgets.append(row)
        self.row_count_changed.emit(len(self.row_widgets))
    
    def _on_row_delete(self, row_widget):
        """删除行"""
        if row_widget in self.row_widgets:
            self.row_widgets.remove(row_widget)
            row_widget.deleteLater()
            self.row_count_changed.emit(len(self.row_widgets))
    
    def get_all_data(self):
        """获取所有行数据"""
        return [row.get_data() for row in self.row_widgets]
    
    def row_count(self):
        """获取行数"""
        return len(self.row_widgets)


# ========== 主对话框 ==========

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
        self.setStyleSheet(f"background: {PREMIUM_COLORS['background']};")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        self.setLayout(layout)
        
        # 标题栏
        header_layout = QHBoxLayout()
        title_label = QLabel("🔗 链接管理")
        title_label.setStyleSheet(f"""
            font-size: 20px;
            font-weight: bold;
            color: {PREMIUM_COLORS['text_heading']};
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # 筛选和操作区域
        filter_card = QFrame()
        filter_card.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-radius: 12px;
                border: 1px solid {PREMIUM_COLORS['border_light']};
            }}
        """)
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(16, 12, 16, 12)
        
        filter_label = QLabel("状态筛选:")
        filter_label.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']};")
        filter_layout.addWidget(filter_label)
        
        self.status_combo = QComboBox()
        self.status_combo.addItems(["全部", "激活", "归档", "已删除"])
        self.status_combo.setFixedWidth(120)
        self.status_combo.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid {PREMIUM_COLORS['border']};
                border-radius: 6px;
                padding: 6px 12px;
                background: white;
            }}
            QComboBox:hover {{
                border-color: {PREMIUM_COLORS['primary']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
        """)
        self.status_combo.currentTextChanged.connect(self.load_data)
        filter_layout.addWidget(self.status_combo)
        
        filter_layout.addStretch()
        
        btn_add = QPushButton("➕ 新增链接")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setFixedHeight(36)
        btn_add.setStyleSheet(f"""
            QPushButton {{
                background: {PREMIUM_COLORS['success']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #2EAE5B;
            }}
        """)
        btn_add.clicked.connect(self.add_link)
        filter_layout.addWidget(btn_add)
        
        btn_refresh = QPushButton("🔄 刷新")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setFixedHeight(36)
        btn_refresh.setStyleSheet(f"""
            QPushButton {{
                background: white;
                color: {PREMIUM_COLORS['text_body']};
                border: 1px solid {PREMIUM_COLORS['border']};
                border-radius: 8px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background: {PREMIUM_COLORS['background']};
                border-color: {PREMIUM_COLORS['primary']};
            }}
        """)
        btn_refresh.clicked.connect(self.load_data)
        filter_layout.addWidget(btn_refresh)
        
        layout.addWidget(filter_card)
        
        # 列表区域
        list_card = QFrame()
        list_card.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-radius: 12px;
                border: 1px solid {PREMIUM_COLORS['border_light']};
            }}
        """)
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(0, 0, 0, 0)
        
        self.link_list = LinkListWidget()
        self.link_list.edit_link.connect(self.edit_link)
        self.link_list.copy_link.connect(self.copy_url)
        self.link_list.delete_link.connect(self.delete_link)
        list_layout.addWidget(self.link_list)
        
        layout.addWidget(list_card, 1)
        
        # 底部按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        btn_close = QPushButton("关闭")
        btn_close.setFixedSize(100, 40)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: white;
                color: {PREMIUM_COLORS['text_body']};
                border: 1px solid {PREMIUM_COLORS['border']};
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background: {PREMIUM_COLORS['background']};
            }}
        """)
        btn_close.clicked.connect(self.accept)
        bottom_layout.addWidget(btn_close)
        
        layout.addLayout(bottom_layout)
        
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
        self.link_list.set_links(links)
    
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
        show_info(self, "成功", "URL 已复制到剪贴板")
    
    def delete_link(self, link: Link):
        """删除链接"""
        if show_question(self, "确认删除", f"确定要删除链接 '{link.name}' 吗？\n此操作不可撤销！"):
            if self.db_manager.delete_link(link.id):
                show_info(self, "成功", "链接已删除")
                self.load_data()
            else:
                show_error(self, "错误", "删除失败")


class ChineseContextTextEdit(QTextEdit):
    """禁用右键菜单的 QTextEdit"""
    
    def contextMenuEvent(self, event):
        """禁用右键菜单"""
        event.ignore()


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
        self.parsed_links = []
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("新增链接 - 智能解析")
        self.resize(800, 500)
        self.setStyleSheet(f"background: {PREMIUM_COLORS['background']};")
        
        # 主布局
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        self.setLayout(layout)
        
        # 输入区域
        input_card = QFrame()
        input_card.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-radius: 12px;
                border: 1px solid {PREMIUM_COLORS['border_light']};
            }}
        """)
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(16, 16, 16, 16)
        
        input_header = QHBoxLayout()
        input_label = QLabel("粘贴文本")
        input_label.setStyleSheet(f"font-weight: 600; font-size: 14px; color: {PREMIUM_COLORS['text_heading']};")
        input_header.addWidget(input_label)
        input_header.addStretch()
        input_layout.addLayout(input_header)
        
        self.text_edit = ChineseContextTextEdit()
        self.text_edit.setPlaceholderText("在此粘贴包含链接的文本...\n例如：\nhttps://docs.qq.com/form/page/xx 邀请你填写《XX报名表》")
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                border: 1px solid {PREMIUM_COLORS['border']};
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                background: white;
            }}
            QTextEdit:focus {{
                border-color: {PREMIUM_COLORS['primary']};
            }}
        """)
        self.text_edit.textChanged.connect(self.on_text_changed)
        input_layout.addWidget(self.text_edit)
        
        # 状态栏（解析结果 + 粘贴按钮）
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 8, 0, 0)
        
        self.count_label = QLabel("解析结果：共找到 0 个链接")
        self.count_label.setStyleSheet(f"color: {PREMIUM_COLORS['primary']}; font-weight: 600; font-size: 13px;")
        status_layout.addWidget(self.count_label)
        
        status_layout.addStretch()
        
        btn_paste = QPushButton("📋 粘贴")
        btn_paste.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_paste.setFixedHeight(32)
        btn_paste.setMinimumWidth(100)
        btn_paste.setStyleSheet(f"""
            QPushButton {{
                background: #F0F0F0;
                color: {PREMIUM_COLORS['text_body']};
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 12px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background: #E0E0E0;
            }}
        """)
        btn_paste.clicked.connect(self.paste_from_clipboard)
        status_layout.addWidget(btn_paste)
        
        input_layout.addLayout(status_layout)
        
        layout.addWidget(input_card, 1)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        btn_cancel = QPushButton("取消")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setFixedSize(100, 40)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background: white;
                color: {PREMIUM_COLORS['text_body']};
                border: 1px solid {PREMIUM_COLORS['border']};
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background: {PREMIUM_COLORS['background']};
            }}
        """)
        btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancel)
        
        self.btn_save = QPushButton("保存全部")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setMinimumWidth(120)  # 使用最小宽度代替固定宽度
        self.btn_save.setFixedHeight(40)
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background: {PREMIUM_COLORS['primary']};
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background: #0056CC;
            }}
            QPushButton:disabled {{
                background: #CCC;
            }}
        """)
        self.btn_save.clicked.connect(self.save_all)
        self.btn_save.setEnabled(False)
        button_layout.addWidget(self.btn_save)
        
        layout.addLayout(button_layout)
        
        # 定时器用于防抖解析
        self.parse_timer = QTimer()
        self.parse_timer.setSingleShot(True)
        self.parse_timer.timeout.connect(self.parse_content)

    def on_text_changed(self):
        """文本变化时触发防抖解析"""
        self.parse_timer.stop()
        self.parse_timer.start(500)
    
    def paste_from_clipboard(self):
        """从剪贴板粘贴"""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            # 移动光标到末尾
            self.text_edit.moveCursor(QTextCursor.MoveOperation.End)
            
            # 如果已有文本且不以换行符结尾，先添加换行符
            current_text = self.text_edit.toPlainText()
            if current_text and not current_text.endswith('\n'):
                self.text_edit.insertPlainText('\n')
                
            # 插入文本
            self.text_edit.insertPlainText(text)
            
    def parse_content(self):
        """解析文本内容"""
        text = self.text_edit.toPlainText().strip()
        if not text:
            self.parsed_links = []
            self.update_status(0)
            return
            
        self.parsed_links = self.get_links_from_text(text)
        self.update_status(len(self.parsed_links))

    def update_status(self, count):
        """更新状态显示"""
        self.count_label.setText(f"解析结果：共找到 {count} 个链接")
        self.btn_save.setEnabled(count > 0)
        self.btn_save.setText(f"保存全部 ({count})")
            
    def get_links_from_text(self, text):
        """从文本中解析链接"""
        if not text:
            return []
            
        url_pattern = r'https?://[a-zA-Z0-9\-._~:/?#[\]@!$&\'()*+,;=%]+'
        matches = list(re.finditer(url_pattern, text))
        
        links = []
        seen_urls = set()
        
        for match in matches:
            url = match.group()
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            start, end = match.span()
            name = self._extract_link_name(text, start, end)
            category = self.guess_category(url)
            links.append({"name": name, "url": url, "category": category})
            
        return links
    
    def _extract_link_name(self, text, url_start, url_end):
        """从文本中提取链接名称
        
        优先级：
        0. 文本块的第一行（通常是标题）
        1. 同一行的前缀（如 "名称：URL" 格式）
        2. 上一行内容
        3. 附近的《》或【】标记
        """
        
        # 0. 首先尝试找到文本块的第一行作为标题
        # 向前查找空行（连续换行）或文本开头，确定文本块的起始位置
        block_start = 0
        search_pos = url_start
        
        while search_pos > 0:
            prev_newline = text.rfind('\n', 0, search_pos)
            if prev_newline == -1:
                block_start = 0
                break
            
            # 检查这个换行符之前是否还有一个换行符（即空行）
            if prev_newline > 0:
                char_before = text[prev_newline - 1] if prev_newline > 0 else ''
                # 检查前一行是否为空或只有空白
                line_before_start = text.rfind('\n', 0, prev_newline - 1)
                line_before_start = line_before_start + 1 if line_before_start != -1 else 0
                line_before_content = text[line_before_start:prev_newline].strip()
                
                # 如果前一行为空，说明找到了文本块的开始
                if not line_before_content:
                    block_start = prev_newline + 1
                    break
            
            search_pos = prev_newline
        
        # 获取文本块的第一行
        first_line_end = text.find('\n', block_start)
        if first_line_end == -1:
            first_line_end = len(text)
        
        first_line = text[block_start:first_line_end].strip()
        
        # 检查第一行是否适合作为标题
        # 条件：不为空、长度适中、不是URL、不是链接所在行
        if (first_line and 
            len(first_line) <= 60 and 
            not first_line.startswith('http') and 
            not re.search(r'https?://', first_line) and
            block_start + len(first_line) < url_start):  # 确保第一行不是链接所在行
            
            # 清除可能的序号前缀
            clean_title = re.sub(r'^[\d]+[.、)\]】]\s*', '', first_line).strip()
            
            # 排除一些不太像标题的内容（如纯标点、太短的内容）
            if clean_title and len(clean_title) >= 2:
                # 排除类似 "备注：xxx" 这样的字段行
                if not re.match(r'^[\u4e00-\u9fa5]{2,4}[：:]\s*\S', clean_title):
                    return clean_title
                # 如果是 "XXX：" 格式但内容本身像标题（较长且没有冒号后内容）
                elif re.match(r'^.+[：:]\s*$', first_line):
                    pass  # 继续往下找
                else:
                    return clean_title
        
        # 1. 尝试获取同一行的前缀
        line_start = text.rfind('\n', 0, url_start)
        line_start = line_start + 1 if line_start != -1 else 0
        prefix = text[line_start:url_start].strip()

        # 1.1 匹配 "名称：" 或 "名称: " 格式 (高优先级)
        name_match = re.match(r'^(.+?)[：:]\s*$', prefix)
        if name_match:
            name = name_match.group(1).strip()
            if name and len(name) <= 50: 
                return name

        # 1.2 匹配 "名称 URL" 格式 (清除序号)
        if prefix and len(prefix) <= 40 and not prefix.startswith('http'):
            clean_name = re.sub(r'^[\d]+[.、)\]】]\s*', '', prefix)
            clean_name = clean_name.strip()
            if clean_name:
                return clean_name

        # 2. 尝试获取上一行作为名称
        # 如果前缀为空，或者只是序号
        is_empty_prefix = not prefix or re.match(r'^[\d]+[.、)\]】]\s*$', prefix)
        
        if is_empty_prefix:
            prev_line_end = line_start - 1
            if prev_line_end > 0:
                prev_line_start = text.rfind('\n', 0, prev_line_end)
                prev_line_start = prev_line_start + 1 if prev_line_start != -1 else 0
                prev_line = text[prev_line_start:prev_line_end].strip()
                
                # 忽略太长的行或看起来像URL的行
                if prev_line and len(prev_line) <= 50 and not prev_line.startswith('http') and not re.search(r'https?://', prev_line):
                     # 清除序号
                    clean_name = re.sub(r'^[\d]+[.、)\]】]\s*', '', prev_line)
                    clean_name = clean_name.strip()
                    if clean_name:
                        return clean_name

        # 3. 尝试在附近寻找《》或【】
        # 限定搜索范围，避免跨越太远
        search_start = max(0, url_start - 100)
        search_end = min(len(text), url_end + 100)
        context = text[search_start:search_end]
        
        # 调整 context 相对于 url_start 的位置
        rel_url_start = url_start - search_start
        rel_url_end = url_end - search_start
        
        # 3.1 《标题》
        title_matches = list(re.finditer(r'《(.*?)》', context))
        if title_matches:
            best_match = None
            min_dist = float('inf')
            
            for m in title_matches:
                m_start, m_end = m.span()
                # 计算距离：匹配项到URL的最近距离
                if m_end <= rel_url_start:
                    dist = rel_url_start - m_end
                elif m_start >= rel_url_end:
                    dist = m_start - rel_url_end
                else:
                    dist = 0 # 重叠
                
                if dist < min_dist:
                    min_dist = dist
                    best_match = m
            
            if best_match and min_dist < 50:
                return best_match.group(1)

        # 3.2 【标题】
        title_matches = list(re.finditer(r'【(.*?)】', context))
        if title_matches:
            best_match = None
            min_dist = float('inf')
            
            for m in title_matches:
                m_start, m_end = m.span()
                if m_end <= rel_url_start:
                    dist = rel_url_start - m_end
                elif m_start >= rel_url_end:
                    dist = m_start - rel_url_end
                else:
                    dist = 0
                
                if dist < min_dist:
                    min_dist = dist
                    best_match = m
            
            if best_match and min_dist < 50:
                title = best_match.group(1)
                if "腾讯文档" not in title and "金山文档" not in title:
                    return title
        
        return "新链接"

    def guess_category(self, url):
        """根据 URL 猜测分类 - 支持12个平台"""
        if "docs.qq.com" in url:
            return "腾讯文档"
        elif "wj.qq.com" in url:
            return "腾讯问卷"
        elif "shimo.im" in url:
            return "石墨文档"
        elif "wjx.cn" in url or "wjx.top" in url:
            return "问卷星"
        elif "jsj.top" in url or "jinshuju.net" in url:
            return "金数据"
        elif "feishu.cn" in url:
            return "飞书"
        elif "kdocs.cn" in url or "wps.cn" in url or "wps.com" in url:
            return "金山文档"
        elif "wenjuan.com" in url:
            return "问卷网"
        elif "baominggongju.com" in url or "p.baominggongju.com" in url:
            return "报名工具"
        elif "fanqier.cn" in url:
            return "番茄表单"
        elif "credamo.com" in url:
            return "见数"
        elif "mikecrm.com" in url or "mike-x.com" in url:
            return "麦客表单"
        return "其他"
    
    def is_supported_platform(self, url):
        """检查链接是否为支持的平台"""
        return is_supported_platform(url)

    def save_all(self):
        """保存所有链接"""
        # 确保解析的是最新内容
        self.parse_content()
        all_data = self.parsed_links
        
        if not all_data:
            show_warning(self, "提示", "未找到有效链接")
            return
        
        # 预检查：找出已存在和不支持的链接
        existing_links = []
        unsupported_links = []
        valid_links = []
        
        for data in all_data:
            url = data['url']
            name = data['name'] or "未命名链接"
            
            if not url:
                continue
            
            # 检查是否支持该平台
            if not self.is_supported_platform(url):
                unsupported_links.append(name or url[:30])
                continue
            
            # 检查是否已存在
            existing = self.db_manager.get_link_by_url(url, user=self.current_user)
            if existing:
                existing_links.append(name or url[:30])
            
            valid_links.append((data, existing))
        
        # 显示预检查结果提示
        warning_msgs = []
        if unsupported_links:
            warning_msgs.append(f"⚠️ 以下 {len(unsupported_links)} 个链接平台暂不支持，将跳过：\n• " + "\n• ".join(unsupported_links[:5]))
            if len(unsupported_links) > 5:
                warning_msgs[-1] += f"\n...等共 {len(unsupported_links)} 个"
        
        if existing_links:
            warning_msgs.append(f"ℹ️ 以下 {len(existing_links)} 个链接已存在，将更新：\n• " + "\n• ".join(existing_links[:5]))
            if len(existing_links) > 5:
                warning_msgs[-1] += f"\n...等共 {len(existing_links)} 个"
        
        # 如果有警告，询问用户是否继续
        if warning_msgs:
            warning_text = "\n\n".join(warning_msgs)
            if valid_links:
                warning_text += f"\n\n确定要继续保存 {len(valid_links)} 个链接吗？"
                if not show_question(self, "保存确认", warning_text):
                    return
            else:
                show_warning(self, "无法保存", "没有可保存的有效链接。\n\n" + warning_text)
                return
        
        if not valid_links:
            show_warning(self, "提示", "没有可保存的有效链接")
            return
            
        # 执行保存（批量优化版）
        success_count = 0
        updated_count = 0
        error_count = 0
        
        # 分离需要新建和需要更新的链接
        links_to_create = []
        links_to_update = []
        
        for data, existing in valid_links:
            name = data['name'] or "未命名链接"
            url = data['url']
            category = data['category']
            
            if existing:
                links_to_update.append((existing, name, category))
            else:
                links_to_create.append({
                    'name': name,
                    'url': url,
                    'category': category,
                    'description': f"批量导入 - {name}"
                })
        
        # 批量创建新链接
        if links_to_create:
            result = self.db_manager.batch_create_links(links_to_create, self.current_user)
            success_count = result['success_count']
            error_count = result['error_count']
        
        # 更新已存在的链接（逐个更新，因为更新逻辑可能不同）
        for existing, name, category in links_to_update:
            try:
                self.db_manager.update_link(
                    existing.id,
                    name=name,
                    category=category,
                    status='active',
                    description=f"批量导入更新 - {name}"
                )
                updated_count += 1
            except Exception as e:
                print(f"更新链接失败: {e}")
                error_count += 1
        
        # 显示结果
        msg_parts = []
        if success_count > 0:
            msg_parts.append(f"✅ 新增 {success_count} 个")
        if updated_count > 0:
            msg_parts.append(f"🔄 更新 {updated_count} 个")
        if error_count > 0:
            msg_parts.append(f"❌ 失败 {error_count} 个")
        if unsupported_links:
            msg_parts.append(f"⏭️ 跳过 {len(unsupported_links)} 个（不支持）")
        
        msg = "处理完成：\n" + "\n".join(msg_parts)
        
        if error_count > 0:
            show_warning(self, "导入完成", msg)
        else:
            show_info(self, "导入完成", msg)
            
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
        self.setGeometry(250, 250, 550, 420)
        self.setStyleSheet(f"background: {PREMIUM_COLORS['background']};")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        self.setLayout(layout)
        
        # 标题
        title_label = QLabel(f"{'✏️' if self.link else '➕'} {title}")
        title_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {PREMIUM_COLORS['text_heading']};
        """)
        layout.addWidget(title_label)
        
        # 表单卡片
        form_card = QFrame()
        form_card.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-radius: 12px;
                border: 1px solid {PREMIUM_COLORS['border_light']};
            }}
        """)
        form_layout = QFormLayout(form_card)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(16)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # 输入框样式
        input_style = f"""
            QLineEdit {{
                border: 1px solid {PREMIUM_COLORS['border']};
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 13px;
                background: white;
            }}
            QLineEdit:focus {{
                border-color: {PREMIUM_COLORS['primary']};
            }}
        """
        
        label_style = f"color: {PREMIUM_COLORS['text_body']}; font-weight: 500;"
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入链接名称")
        self.name_input.setStyleSheet(input_style)
        if self.link:
            self.name_input.setText(self.link.name)
        name_label = QLabel("链接名称 *")
        name_label.setStyleSheet(label_style)
        form_layout.addRow(name_label, self.name_input)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("输入完整 URL（如：https://example.com）")
        self.url_input.setStyleSheet(input_style)
        if self.link:
            self.url_input.setText(self.link.url)
        url_label = QLabel("URL *")
        url_label.setStyleSheet(label_style)
        form_layout.addRow(url_label, self.url_input)
        
        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("输入分类（如：测试、抖音、小红书）")
        self.category_input.setStyleSheet(input_style)
        if self.link:
            self.category_input.setText(self.link.category or "")
        category_label = QLabel("分类")
        category_label.setStyleSheet(label_style)
        form_layout.addRow(category_label, self.category_input)
        
        self.status_combo = QComboBox()
        self.status_combo.addItems(["激活", "归档", "已删除"])
        self.status_combo.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid {PREMIUM_COLORS['border']};
                border-radius: 8px;
                padding: 10px 12px;
                background: white;
            }}
            QComboBox:hover {{
                border-color: {PREMIUM_COLORS['primary']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
        """)
        if self.link:
            status_index = {"active": 0, "archived": 1, "deleted": 2}.get(self.link.status, 0)
            self.status_combo.setCurrentIndex(status_index)
        status_label = QLabel("状态")
        status_label.setStyleSheet(label_style)
        form_layout.addRow(status_label, self.status_combo)
        
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("输入描述（可选）")
        self.desc_input.setStyleSheet(input_style)
        if self.link:
            self.desc_input.setText(self.link.description or "")
        desc_label = QLabel("描述")
        desc_label.setStyleSheet(label_style)
        form_layout.addRow(desc_label, self.desc_input)
        
        layout.addWidget(form_card)
        
        # 提示
        hint_label = QLabel("* 为必填项")
        hint_label.setStyleSheet(f"color: {PREMIUM_COLORS['text_hint']}; font-size: 12px;")
        layout.addWidget(hint_label)
        
        layout.addStretch()
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        btn_cancel = QPushButton("取消")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setFixedSize(100, 40)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background: white;
                color: {PREMIUM_COLORS['text_body']};
                border: 1px solid {PREMIUM_COLORS['border']};
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background: {PREMIUM_COLORS['background']};
            }}
        """)
        btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancel)
        
        btn_save = QPushButton("💾 保存")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setFixedSize(120, 40)
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5a6fd6, stop:1 #6a4190);
            }}
        """)
        btn_save.clicked.connect(self.save)
        button_layout.addWidget(btn_save)
        
        layout.addLayout(button_layout)
    
    def save(self):
        """保存"""
        name = self.name_input.text().strip()
        url = self.url_input.text().strip()
        
        if not name:
            show_warning(self, "警告", "请输入链接名称")
            return
        
        if not url:
            show_warning(self, "警告", "请输入 URL")
            return
        
        if not url.startswith(('http://', 'https://')):
            show_warning(self, "警告", "URL 必须以 http:// 或 https:// 开头")
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
                self.db_manager.update_link(
                    self.link.id,
                    name=name,
                    url=url,
                    category=category,
                    status=status,
                    description=description
                )
                show_info(self, "成功", "链接已更新")
            else:
                self.db_manager.create_link(name, url, self.current_user, status, category, description)
                show_info(self, "成功", "链接已创建")
            
            self.accept()
        except Exception as e:
            show_error(self, "错误", f"保存失败: {str(e)}")
