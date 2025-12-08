"""
名片管理模块 (管理员版)
采用现代化玻璃拟态设计风格
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QMessageBox, QLineEdit, QFrame, 
    QGraphicsDropShadowEffect, QDialog, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from database import DatabaseManager, Card, User, CardEditRequest
from gui.icons import Icons
from gui.admin_base_components import (
    PREMIUM_COLORS, GlassFrame, GradientButton, CompactStatWidget,
    BaseListHeader, BaseRowWidget, BaseListWidget, create_action_button
)
import datetime
import json
from gui.card_manager import CardEditDialog  # For reference


# ========== 名片列表自定义组件 ==========

# 列宽配置
CARD_LIST_COLUMNS = {
    'name': 180,
    'user': 120,
    'category': 100,
    'configs': 80,
    'created': 130,
    'updated': 130,
    'actions': 160,
}


class CardListHeader(QFrame):
    """名片列表表头"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(f"""
            CardListHeader {{
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
            ('名片名称', CARD_LIST_COLUMNS['name']),
            ('所属用户', CARD_LIST_COLUMNS['user']),
            ('分类', CARD_LIST_COLUMNS['category']),
            ('配置项', CARD_LIST_COLUMNS['configs']),
            ('创建时间', CARD_LIST_COLUMNS['created']),
            ('更新时间', CARD_LIST_COLUMNS['updated']),
            ('操作', CARD_LIST_COLUMNS['actions']),
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


class CardRowWidget(QFrame):
    """名片行组件"""
    
    view_clicked = pyqtSignal(object)
    edit_clicked = pyqtSignal(object)
    delete_clicked = pyqtSignal(object)
    
    def __init__(self, card, parent=None):
        super().__init__(parent)
        self.card = card
        self.setFixedHeight(64)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet(f"""
            CardRowWidget {{
                background: white;
                border: none;
                border-bottom: 1px solid {PREMIUM_COLORS['border_light']};
            }}
            CardRowWidget:hover {{
                background: #fafbfc;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(0)
        
        # 1. 名片名称
        self._add_name(layout)
        # 2. 所属用户
        self._add_user(layout)
        # 3. 分类
        self._add_category(layout)
        # 4. 配置项数
        self._add_configs(layout)
        # 5. 创建时间
        self._add_created(layout)
        # 6. 更新时间
        self._add_updated(layout)
        # 7. 操作
        self._add_actions(layout)
        
        layout.addStretch()
    
    def _add_name(self, layout):
        container = QWidget()
        container.setFixedWidth(CARD_LIST_COLUMNS['name'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 8, 0)
        c_layout.setSpacing(10)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        icon_lbl = QLabel("📇")
        icon_lbl.setStyleSheet("font-size: 18px;")
        
        name_box = QVBoxLayout()
        name_box.setSpacing(2)
        name_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        name_lbl = QLabel(self.card.name)
        name_lbl.setStyleSheet(f"font-weight: 600; color: {PREMIUM_COLORS['text_heading']}; font-size: 13px;")
        
        desc_lbl = QLabel(self.card.description[:20] + "..." if self.card.description and len(self.card.description) > 20 else (self.card.description or "无描述"))
        desc_lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_hint']}; font-size: 11px;")
        
        name_box.addWidget(name_lbl)
        name_box.addWidget(desc_lbl)
        
        c_layout.addWidget(icon_lbl)
        c_layout.addLayout(name_box)
        layout.addWidget(container)
    
    def _add_user(self, layout):
        container = QWidget()
        container.setFixedWidth(CARD_LIST_COLUMNS['user'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setSpacing(6)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        if self.card.user:
            avatar = QLabel(self.card.user.username[0].upper())
            avatar.setFixedSize(24, 24)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar.setStyleSheet(f"""
                background: {PREMIUM_COLORS['gradient_blue_start']};
                color: white;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 600;
            """)
            
            name_lbl = QLabel(self.card.user.username)
            name_lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-size: 13px;")
            
            c_layout.addWidget(avatar)
            c_layout.addWidget(name_lbl)
        else:
            lbl = QLabel("未知用户")
            lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_hint']}; font-size: 13px;")
            c_layout.addWidget(lbl)
        
        layout.addWidget(container)
    
    def _add_category(self, layout):
        container = QWidget()
        container.setFixedWidth(CARD_LIST_COLUMNS['category'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        cat_lbl = QLabel(self.card.category or "默认分类")
        cat_lbl.setStyleSheet(f"""
            background: {PREMIUM_COLORS['text_hint']}15;
            color: {PREMIUM_COLORS['text_body']};
            border: 1px solid {PREMIUM_COLORS['text_hint']}40;
            border-radius: 11px;
            padding: 2px 10px;
            font-size: 11px;
            font-weight: 500;
        """)
        c_layout.addWidget(cat_lbl)
        layout.addWidget(container)
    
    def _add_configs(self, layout):
        container = QWidget()
        container.setFixedWidth(CARD_LIST_COLUMNS['configs'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        count_lbl = QLabel(str(len(self.card.configs)))
        count_lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-size: 13px; font-weight: 600;")
        c_layout.addWidget(count_lbl)
        layout.addWidget(container)
    
    def _add_created(self, layout):
        container = QWidget()
        container.setFixedWidth(CARD_LIST_COLUMNS['created'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        created_str = self.card.created_at.strftime('%Y-%m-%d %H:%M') if self.card.created_at else '-'
        lbl = QLabel(created_str)
        lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-size: 12px;")
        c_layout.addWidget(lbl)
        layout.addWidget(container)
    
    def _add_updated(self, layout):
        container = QWidget()
        container.setFixedWidth(CARD_LIST_COLUMNS['updated'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        updated_str = self.card.updated_at.strftime('%Y-%m-%d %H:%M') if self.card.updated_at else '-'
        lbl = QLabel(updated_str)
        lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_hint']}; font-size: 12px;")
        c_layout.addWidget(lbl)
        layout.addWidget(container)
    
    def _add_actions(self, layout):
        container = QWidget()
        container.setFixedWidth(CARD_LIST_COLUMNS['actions'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(6)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # 查看按钮
        btn_view = create_action_button("查看", PREMIUM_COLORS['gradient_blue_start'])
        btn_view.clicked.connect(lambda: self.view_clicked.emit(self.card))
        c_layout.addWidget(btn_view)
        
        # 编辑按钮
        btn_edit = create_action_button("编辑", PREMIUM_COLORS['gradient_orange_start'])
        btn_edit.clicked.connect(lambda: self.edit_clicked.emit(self.card))
        c_layout.addWidget(btn_edit)
        
        # 删除按钮
        btn_del = create_action_button("删除", PREMIUM_COLORS['coral'])
        btn_del.clicked.connect(lambda: self.delete_clicked.emit(self.card))
        c_layout.addWidget(btn_del)
        
        layout.addWidget(container)


class CardListWidget(QWidget):
    """名片列表组件"""
    
    view_card = pyqtSignal(object)
    edit_card = pyqtSignal(object)
    delete_card = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.row_widgets = []
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.header = CardListHeader()
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
    
    def set_cards(self, cards):
        # 清空现有行
        for widget in self.row_widgets:
            widget.deleteLater()
        self.row_widgets.clear()
        
        if not cards:
            empty_label = QLabel("暂无名片数据")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet(f"""
                color: {PREMIUM_COLORS['text_hint']};
                font-size: 14px;
                padding: 60px;
            """)
            self.content_layout.addWidget(empty_label)
            self.row_widgets.append(empty_label)
            return
        
        for card in cards:
            row = CardRowWidget(card)
            row.view_clicked.connect(self.view_card.emit)
            row.edit_clicked.connect(self.edit_card.emit)
            row.delete_clicked.connect(self.delete_card.emit)
            
            self.content_layout.addWidget(row)
            self.row_widgets.append(row)

class AdminCardViewDialog(QDialog):
    """管理员名片查看对话框 - 重新设计版"""
    
    def __init__(self, card: Card, parent=None):
        super().__init__(parent)
        self.card = card
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle(f"名片详情 - {self.card.name}")
        self.setFixedSize(500, 650)
        self.setStyleSheet("QDialog { background-color: #f8fafc; }")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # === 1. 顶部 Header (渐变背景) ===
        header = QFrame()
        header.setFixedHeight(140)
        header.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {PREMIUM_COLORS['gradient_blue_start']}, 
                    stop:1 {PREMIUM_COLORS['gradient_blue_end']});
            }}
        """)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(30, 20, 30, 20)
        header_layout.setSpacing(15)
        
        # 顶部行：分类标签 + 用户信息
        top_row = QHBoxLayout()
        
        # 分类标签
        cat_lbl = QLabel(self.card.category or "默认分类")
        cat_lbl.setStyleSheet("""
            background: rgba(255, 255, 255, 0.2);
            color: white;
            border-radius: 12px;
            padding: 4px 12px;
            font-size: 12px;
            font-weight: 600;
        """)
        top_row.addWidget(cat_lbl)
        top_row.addStretch()
        
        # 用户信息
        if self.card.user:
            user_icon = QLabel("👤")
            user_icon.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 14px;")
            user_name = QLabel(self.card.user.username)
            user_name.setStyleSheet("color: white; font-weight: 600; font-size: 13px;")
            top_row.addWidget(user_icon)
            top_row.addWidget(user_name)
            
        header_layout.addLayout(top_row)
        
        # 名片名称与描述
        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)
        
        title_row = QHBoxLayout()
        icon_lbl = QLabel("📇")
        icon_lbl.setStyleSheet("font-size: 28px;")
        name_lbl = QLabel(self.card.name)
        name_lbl.setStyleSheet("color: white; font-size: 24px; font-weight: 800;")
        title_row.addWidget(icon_lbl)
        title_row.addWidget(name_lbl)
        title_row.addStretch()
        info_layout.addLayout(title_row)
        
        if self.card.description:
            desc_lbl = QLabel(self.card.description)
            desc_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.8); font-size: 13px;")
            desc_lbl.setWordWrap(True)
            info_layout.addWidget(desc_lbl)
            
        header_layout.addLayout(info_layout)
        layout.addWidget(header)
        
        # === 2. 内容区域 (滚动) ===
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 8px; background: transparent; }
            QScrollBar::handle:vertical { background: #cbd5e1; border-radius: 4px; }
        """)
        
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(20)
        
        # 配置项列表容器
        config_card = QFrame()
        config_card.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-radius: 16px;
                border: 1px solid {PREMIUM_COLORS['border_light']};
            }}
        """)
        # 添加阴影
        shadow = QGraphicsDropShadowEffect(config_card)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 10))
        shadow.setOffset(0, 4)
        config_card.setGraphicsEffect(shadow)
        
        config_layout = QVBoxLayout(config_card)
        config_layout.setContentsMargins(0, 0, 0, 0)
        config_layout.setSpacing(0)
        
        # 标题行
        title_bar = QFrame()
        title_bar.setFixedHeight(48)
        title_bar.setStyleSheet(f"""
            border-bottom: 1px solid {PREMIUM_COLORS['border_light']};
            border-top-left-radius: 16px;
            border-top-right-radius: 16px;
            background: #f8fafc;
        """)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(20, 0, 20, 0)
        
        list_title = QLabel("配置详情")
        list_title.setStyleSheet(f"color: {PREMIUM_COLORS['text_heading']}; font-weight: 700; font-size: 14px;")
        count_badge = QLabel(f"{len(self.card.configs)} 项")
        count_badge.setStyleSheet(f"""
            background: {PREMIUM_COLORS['gradient_blue_start']}20;
            color: {PREMIUM_COLORS['gradient_blue_start']};
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 600;
        """)
        
        title_layout.addWidget(list_title)
        title_layout.addStretch()
        title_layout.addWidget(count_badge)
        config_layout.addWidget(title_bar)
        
        # 配置项列表
        if not self.card.configs:
            empty_lbl = QLabel("暂无配置项")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setFixedHeight(100)
            empty_lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_hint']}; font-size: 13px;")
            config_layout.addWidget(empty_lbl)
        else:
            for i, config in enumerate(self.card.configs):
                row = QFrame()
                row.setStyleSheet(f"""
                    QFrame {{
                        background: transparent;
                        border-bottom: 1px solid {PREMIUM_COLORS['border_light'] if i < len(self.card.configs)-1 else 'transparent'};
                    }}
                    QFrame:hover {{
                        background: #f8fafc;
                    }}
                """)
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(20, 12, 20, 12)
                row_layout.setSpacing(12)
                
                key_lbl = QLabel(config.key)
                key_lbl.setFixedWidth(120)
                key_lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-weight: 600; font-size: 13px;")
                key_lbl.setWordWrap(True)
                
                val_lbl = QLabel(config.value)
                val_lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_heading']}; font-size: 13px;")
                val_lbl.setWordWrap(True)
                val_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                
                row_layout.addWidget(key_lbl)
                row_layout.addWidget(val_lbl, 1)
                
                config_layout.addWidget(row)
                
        content_layout.addWidget(config_card)
        content_layout.addStretch()
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # === 3. 底部按钮 ===
        btn_container = QFrame()
        btn_container.setStyleSheet("background: white; border-top: 1px solid #e2e8f0;")
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(24, 16, 24, 16)
        
        # 创建时间提示
        time_info = QLabel(f"创建于 {self.card.created_at.strftime('%Y-%m-%d')}")
        time_info.setStyleSheet(f"color: {PREMIUM_COLORS['text_hint']}; font-size: 12px;")
        btn_layout.addWidget(time_info)
        
        btn_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedSize(100, 36)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PREMIUM_COLORS['surface']};
                color: {PREMIUM_COLORS['text_body']};
                border: 1px solid {PREMIUM_COLORS['border']};
                border-radius: 18px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {PREMIUM_COLORS['background']};
                border-color: {PREMIUM_COLORS['text_body']};
            }}
        """)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addWidget(btn_container)


class AdminCardEditDialog(QDialog):
    """管理员名片编辑对话框 - 提交修改请求（需要用户同意）"""
    
    def __init__(self, card: Card, admin_user, parent=None):
        super().__init__(parent)
        self.card = card
        self.admin_user = admin_user
        self.config_widgets = []
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle(f"编辑名片 - {self.card.name}")
        self.setFixedSize(600, 700)
        self.setStyleSheet("QDialog { background-color: #f8fafc; }")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # === 1. 顶部 Header ===
        header = QFrame()
        header.setFixedHeight(100)
        header.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {PREMIUM_COLORS['gradient_orange_start']}, 
                    stop:1 {PREMIUM_COLORS['gradient_orange_end']});
            }}
        """)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(30, 20, 30, 20)
        header_layout.setSpacing(8)
        
        title_row = QHBoxLayout()
        icon_lbl = QLabel("✏️")
        icon_lbl.setStyleSheet("font-size: 24px;")
        title_lbl = QLabel("编辑名片")
        title_lbl.setStyleSheet("color: white; font-size: 22px; font-weight: 800;")
        title_row.addWidget(icon_lbl)
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        header_layout.addLayout(title_row)
        
        hint_lbl = QLabel("⚠️ 修改需要用户同意后才会生效")
        hint_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.9); font-size: 13px; font-weight: 500;")
        header_layout.addWidget(hint_lbl)
        
        layout.addWidget(header)
        
        # === 2. 表单区域 ===
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 8px; background: transparent; }
            QScrollBar::handle:vertical { background: #cbd5e1; border-radius: 4px; }
        """)
        
        form_widget = QWidget()
        form_widget.setStyleSheet("background: transparent;")
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(24, 24, 24, 24)
        form_layout.setSpacing(16)
        
        # 输入框样式
        input_style = f"""
            QLineEdit, QComboBox {{
                border: 1px solid {PREMIUM_COLORS['border_light']};
                border-radius: 10px;
                padding: 12px 16px;
                background: white;
                font-size: 14px;
                color: {PREMIUM_COLORS['text_heading']};
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid {PREMIUM_COLORS['gradient_blue_start']};
            }}
        """
        
        # 名称输入
        name_card = self._create_field_card("名片名称", "📇")
        self.name_input = QLineEdit()
        self.name_input.setText(self.card.name)
        self.name_input.setStyleSheet(input_style)
        name_card.layout().addWidget(self.name_input)
        form_layout.addWidget(name_card)
        
        # 分类输入
        cat_card = self._create_field_card("分类", "📁")
        self.category_input = QLineEdit()
        self.category_input.setText(self.card.category or "默认分类")
        self.category_input.setStyleSheet(input_style)
        cat_card.layout().addWidget(self.category_input)
        form_layout.addWidget(cat_card)
        
        # 描述输入
        desc_card = self._create_field_card("描述", "📝")
        self.desc_input = QLineEdit()
        self.desc_input.setText(self.card.description or "")
        self.desc_input.setPlaceholderText("可选")
        self.desc_input.setStyleSheet(input_style)
        desc_card.layout().addWidget(self.desc_input)
        form_layout.addWidget(desc_card)
        
        # 配置项区域
        config_card = QFrame()
        config_card.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-radius: 12px;
                border: 1px solid {PREMIUM_COLORS['border_light']};
            }}
        """)
        config_layout = QVBoxLayout(config_card)
        config_layout.setContentsMargins(16, 16, 16, 16)
        config_layout.setSpacing(12)
        
        config_header = QHBoxLayout()
        config_title = QLabel("📋 配置项")
        config_title.setStyleSheet(f"font-weight: 700; font-size: 14px; color: {PREMIUM_COLORS['text_heading']};")
        config_header.addWidget(config_title)
        config_header.addStretch()
        
        add_btn = QPushButton("+ 添加")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PREMIUM_COLORS['gradient_green_start']};
                color: white;
                border: none;
                border-radius: 14px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {PREMIUM_COLORS['gradient_green_end']}; }}
        """)
        add_btn.clicked.connect(lambda: self.add_config_row())
        config_header.addWidget(add_btn)
        config_layout.addLayout(config_header)
        
        # 配置项列表容器
        self.config_container = QVBoxLayout()
        self.config_container.setSpacing(8)
        config_layout.addLayout(self.config_container)
        
        # 加载现有配置
        for config in self.card.configs:
            self.add_config_row(config.key, config.value)
        
        if not self.card.configs:
            self.add_config_row()
            
        form_layout.addWidget(config_card)
        
        # 管理员备注
        comment_card = self._create_field_card("管理员备注（用户可见）", "💬")
        self.comment_input = QLineEdit()
        self.comment_input.setPlaceholderText("说明修改原因...")
        self.comment_input.setStyleSheet(input_style)
        comment_card.layout().addWidget(self.comment_input)
        form_layout.addWidget(comment_card)
        
        form_layout.addStretch()
        scroll.setWidget(form_widget)
        layout.addWidget(scroll)
        
        # === 3. 底部按钮 ===
        btn_container = QFrame()
        btn_container.setStyleSheet("background: white; border-top: 1px solid #e2e8f0;")
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(24, 16, 24, 16)
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFixedSize(100, 40)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: white;
                color: {PREMIUM_COLORS['text_body']};
                border: 1px solid {PREMIUM_COLORS['border']};
                border-radius: 20px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {PREMIUM_COLORS['background']}; }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        submit_btn = QPushButton("提交修改请求")
        submit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        submit_btn.setFixedSize(140, 40)
        submit_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {PREMIUM_COLORS['gradient_orange_start']}, 
                    stop:1 {PREMIUM_COLORS['gradient_orange_end']});
                color: white;
                border: none;
                border-radius: 20px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {PREMIUM_COLORS['gradient_orange_end']}, 
                    stop:1 {PREMIUM_COLORS['gradient_orange_start']});
            }}
        """)
        submit_btn.clicked.connect(self.submit_request)
        btn_layout.addWidget(submit_btn)
        
        layout.addWidget(btn_container)
    
    def _create_field_card(self, title, icon):
        """创建字段卡片"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-radius: 12px;
                border: 1px solid {PREMIUM_COLORS['border_light']};
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        label = QLabel(f"{icon} {title}")
        label.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {PREMIUM_COLORS['text_body']};")
        layout.addWidget(label)
        
        return card
    
    def add_config_row(self, key: str = "", value: str = ""):
        """添加配置项行"""
        row_frame = QFrame()
        row_frame.setStyleSheet(f"""
            QFrame {{
                background: {PREMIUM_COLORS['background']};
                border-radius: 8px;
            }}
        """)
        row_layout = QHBoxLayout(row_frame)
        row_layout.setContentsMargins(10, 8, 10, 8)
        row_layout.setSpacing(8)
        
        key_input = QLineEdit()
        key_input.setPlaceholderText("字段名")
        key_input.setText(key)
        key_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {PREMIUM_COLORS['border_light']};
                border-radius: 6px;
                padding: 8px;
                background: white;
                font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {PREMIUM_COLORS['gradient_blue_start']}; }}
        """)
        row_layout.addWidget(key_input, 1)
        
        value_input = QLineEdit()
        value_input.setPlaceholderText("值")
        value_input.setText(value)
        value_input.setStyleSheet(key_input.styleSheet())
        row_layout.addWidget(value_input, 2)
        
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(28, 28)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PREMIUM_COLORS['coral']}20;
                color: {PREMIUM_COLORS['coral']};
                border: none;
                border-radius: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {PREMIUM_COLORS['coral']}; color: white; }}
        """)
        del_btn.clicked.connect(lambda: self.remove_config_row(row_frame))
        row_layout.addWidget(del_btn)
        
        self.config_widgets.append((key_input, value_input, row_frame))
        self.config_container.addWidget(row_frame)
    
    def remove_config_row(self, row_frame):
        """删除配置项行"""
        self.config_widgets = [(k, v, w) for k, v, w in self.config_widgets if w != row_frame]
        row_frame.deleteLater()
    
    def submit_request(self):
        """提交修改请求"""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入名片名称")
            return
        
        # 收集配置项
        configs = []
        for key_input, value_input, _ in self.config_widgets:
            key = key_input.text().strip()
            value = value_input.text().strip()
            if key and value:
                configs.append({'key': key, 'value': value, 'order': len(configs)})
        
        if not configs:
            QMessageBox.warning(self, "提示", "请至少添加一个配置项")
            return
        
        try:
            DatabaseManager.create_card_edit_request(
                card_id=str(self.card.id),
                admin=self.admin_user,
                modified_name=name,
                modified_description=self.desc_input.text().strip(),
                modified_category=self.category_input.text().strip() or "默认分类",
                modified_configs=configs,
                admin_comment=self.comment_input.text().strip()
            )
            
            QMessageBox.information(
                self, "成功", 
                f"修改请求已提交！\n\n用户 {self.card.user.username} 将会收到通知，\n同意后修改才会生效。"
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"提交失败: {str(e)}")


class AdminCardManager(QWidget):
    """管理员名片管理页面"""
    
    def __init__(self, parent=None, current_admin=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.current_admin = current_admin  # 当前管理员用户
        self.current_page = 1
        self.page_size = 15
        self.total_cards = 0
        self.total_pages = 1
        self.stat_cards = {}
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
        
        # === 顶部区域 (标题 + 统计 + 操作) ===
        self._create_header(main_layout)
        
        # === 主表格区域 (包含工具栏和分页) ===
        self._create_main_card(main_layout)
        
        # 加载数据
        self.load_cards()
    
    def _create_header(self, layout):
        """创建顶部区域：标题、统计"""
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)
        
        # 1. 标题
        title_label = QLabel("名片管理中心")
        title_label.setStyleSheet(f"""
            font-size: 24px; 
            font-weight: 800; 
            color: {PREMIUM_COLORS['text_heading']};
            background: transparent;
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addSpacing(16)
        
        # 2. 统计组件 (紧凑型)
        cards_data = [
            ("总名片数", 0, "📇", PREMIUM_COLORS['gradient_blue_start'], PREMIUM_COLORS['gradient_blue_end']),
            ("今日新增", 0, "🆕", PREMIUM_COLORS['gradient_green_start'], PREMIUM_COLORS['gradient_green_end']),
        ]
        
        for title, value, icon, start, end in cards_data:
            card = CompactStatWidget(title, value, icon, start, end)
            self.stat_cards[title] = card
            header_layout.addWidget(card)
            
        header_layout.addStretch()
        
        # 3. 刷新按钮 (代替添加按钮，因为管理员一般不帮用户添加名片，或者通过模拟登录添加)
        refresh_btn = GradientButton(
            "刷新数据",
            PREMIUM_COLORS['gradient_blue_start'],
            PREMIUM_COLORS['gradient_blue_end']
        )
        refresh_btn.setFixedSize(120, 40)
        refresh_btn.setStyleSheet(refresh_btn.styleSheet() + """
            QPushButton {
                font-size: 13px;
                border-radius: 20px;
                padding: 0 16px;
            }
        """)
        refresh_btn.clicked.connect(self.load_cards)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
    def _create_main_card(self, layout):
        """创建主内容卡片：工具栏 + 名片列表 + 分页"""
        card = GlassFrame(opacity=1.0, radius=16)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        
        # 1. 工具栏 (搜索)
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
        self.search_input.setPlaceholderText("搜索名片名称或所属用户...")
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
        
        card_layout.addWidget(toolbar)
        
        # 2. 自定义名片列表
        self.card_list = CardListWidget()
        self.card_list.view_card.connect(self.view_card)
        self.card_list.edit_card.connect(self.edit_card)
        self.card_list.delete_card.connect(self.delete_card)
        
        card_layout.addWidget(self.card_list, 1)
        
        # 3. 分页
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
        
        # 翻页按钮
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

    def change_page(self):
        sender = self.sender()
        if sender == self.prev_btn:
            self.go_to_page(self.current_page - 1)
        else:
            self.go_to_page(self.current_page + 1)
            
    def on_search(self):
        self.current_page = 1
        self.load_cards()
        
    def go_to_page(self, page):
        if 1 <= page <= self.total_pages:
            self.current_page = page
            self.load_cards()
            
    def load_cards(self):
        keyword = self.search_input.text().strip().lower()
        all_cards = self.db_manager.get_all_cards()
        
        # 过滤
        if keyword:
            filtered_cards = []
            for card in all_cards:
                username = card.user.username.lower() if card.user else ""
                if keyword in card.name.lower() or keyword in username:
                    filtered_cards.append(card)
            all_cards = filtered_cards
        
        # 更新统计
        total_count = len(all_cards)
        today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = sum(1 for c in all_cards if c.created_at >= today_start)
        
        if "总名片数" in self.stat_cards:
            self.stat_cards["总名片数"].update_value(total_count)
        if "今日新增" in self.stat_cards:
            self.stat_cards["今日新增"].update_value(today_count)
            
        # 分页处理
        self.total_cards = total_count
        self.total_pages = max(1, (self.total_cards + self.page_size - 1) // self.page_size)
        
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
            
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = start_idx + self.page_size
        cards = all_cards[start_idx:end_idx]
        
        self.card_list.set_cards(cards)
        self.update_pagination()
        
    def update_pagination(self):
        start = (self.current_page - 1) * self.page_size + 1
        end = min(self.current_page * self.page_size, self.total_cards)
        
        if self.total_cards > 0:
            self.page_info_label.setText(f"显示 {start}-{end} 条，共 {self.total_cards} 条")
        else:
            self.page_info_label.setText("暂无数据")
            
        self.page_num_label.setText(f"{self.current_page} / {self.total_pages}")
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < self.total_pages)
            
    def view_card(self, card):
        """查看名片详情"""
        dialog = AdminCardViewDialog(card, self)
        dialog.exec()
    
    def edit_card(self, card):
        """编辑名片 - 提交修改请求"""
        if not self.current_admin:
            QMessageBox.warning(self, "错误", "无法获取当前管理员信息")
            return
        
        dialog = AdminCardEditDialog(card, self.current_admin, self)
        if dialog.exec():
            self.load_cards()
        
    def delete_card(self, card):
        """删除名片"""
        confirm = QMessageBox.warning(
            self, "确认删除",
            f"确定要删除名片 '{card.name}' 吗？\n此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            if self.db_manager.delete_card(str(card.id)):
                QMessageBox.information(self, "成功", "名片已删除")
                self.load_cards()
            else:
                QMessageBox.critical(self, "错误", "删除名片失败")
