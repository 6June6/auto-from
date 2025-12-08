"""
字典管理模块
重写后的字典管理界面，采用现代化玻璃拟态设计风格，与用户管理保持一致
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QMessageBox, QLineEdit, QDialog, QFrame,
    QGraphicsDropShadowEffect, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from database.models import SystemConfig
from gui.icons import Icons
from gui.admin_base_components import (
    PREMIUM_COLORS, GlassFrame, GradientButton, CompactStatWidget, create_action_button
)


# ========== 字典列表自定义组件 ==========

# 列宽配置
DICT_LIST_COLUMNS = {
    'key': 200,
    'desc': 200,
    'value': 200,
    'actions': 80,
}


class DictListHeader(QFrame):
    """字典列表表头"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(f"""
            DictListHeader {{
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
            ('配置键', DICT_LIST_COLUMNS['key']),
            ('说明', DICT_LIST_COLUMNS['desc']),
            ('当前值', DICT_LIST_COLUMNS['value']),
            ('操作', DICT_LIST_COLUMNS['actions']),
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


class DictRowWidget(QFrame):
    """字典行组件"""
    
    edit_clicked = pyqtSignal(object)
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setFixedHeight(60)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet(f"""
            DictRowWidget {{
                background: white;
                border: none;
                border-bottom: 1px solid {PREMIUM_COLORS['border_light']};
            }}
            DictRowWidget:hover {{
                background: #fafbfc;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(0)
        
        # 1. 配置键
        self._add_key(layout)
        # 2. 说明
        self._add_desc(layout)
        # 3. 当前值
        self._add_value(layout)
        # 4. 操作
        self._add_actions(layout)
        
        layout.addStretch()
    
    def _add_key(self, layout):
        container = QWidget()
        container.setFixedWidth(DICT_LIST_COLUMNS['key'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 8, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        lbl = QLabel(self.config.key)
        lbl.setStyleSheet(f"font-weight: 700; color: {PREMIUM_COLORS['text_heading']}; font-family: monospace; font-size: 13px;")
        lbl.setToolTip(self.config.key)
        c_layout.addWidget(lbl)
        layout.addWidget(container)
    
    def _add_desc(self, layout):
        container = QWidget()
        container.setFixedWidth(DICT_LIST_COLUMNS['desc'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 8, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        desc = self.config.description or "-"
        if len(desc) > 25:
            desc = desc[:25] + "..."
        lbl = QLabel(desc)
        lbl.setToolTip(self.config.description or "")
        lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-size: 12px;")
        c_layout.addWidget(lbl)
        layout.addWidget(container)
    
    def _add_value(self, layout):
        container = QWidget()
        container.setFixedWidth(DICT_LIST_COLUMNS['value'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 8, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        val = self.config.value or "-"
        if len(val) > 25:
            val = val[:25] + "..."
        lbl = QLabel(val)
        lbl.setToolTip(self.config.value or "")
        lbl.setStyleSheet(f"color: {PREMIUM_COLORS['gradient_purple_start']}; font-weight: 600; font-size: 12px;")
        c_layout.addWidget(lbl)
        layout.addWidget(container)
    
    def _add_actions(self, layout):
        container = QWidget()
        container.setFixedWidth(DICT_LIST_COLUMNS['actions'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_edit = create_action_button("编辑", PREMIUM_COLORS['gradient_purple_start'])
        btn_edit.clicked.connect(lambda: self.edit_clicked.emit(self.config))
        c_layout.addWidget(btn_edit)
        layout.addWidget(container)


class DictListWidget(QWidget):
    """字典列表组件"""
    
    edit_config = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.row_widgets = []
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.header = DictListHeader()
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
    
    def set_configs(self, configs):
        for widget in self.row_widgets:
            widget.deleteLater()
        self.row_widgets.clear()
        
        if not configs:
            empty_label = QLabel("暂无配置项")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet(f"""
                color: {PREMIUM_COLORS['text_hint']};
                font-size: 14px;
                padding: 60px;
            """)
            self.content_layout.addWidget(empty_label)
            self.row_widgets.append(empty_label)
            return
        
        for config in configs:
            row = DictRowWidget(config)
            row.edit_clicked.connect(self.edit_config.emit)
            
            self.content_layout.addWidget(row)
            self.row_widgets.append(row)

class DictionaryEditDialog(QDialog):
    """字典编辑对话框 - 现代化风格"""
    
    def __init__(self, config_item, parent=None):
        super().__init__(parent)
        self.config_item = config_item
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("编辑配置")
        self.setFixedSize(460, 400)
        self.setStyleSheet("QDialog { background-color: white; }")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # === 1. 顶部 Header ===
        header = QFrame()
        header.setFixedHeight(100)
        header.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {PREMIUM_COLORS['gradient_purple_start']}, 
                    stop:1 {PREMIUM_COLORS['gradient_purple_end']});
            }}
        """)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(32, 0, 32, 0)
        header_layout.setSpacing(20)
        
        title_info = QVBoxLayout()
        title_info.setSpacing(6)
        title_info.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        title_lbl = QLabel("编辑配置")
        title_lbl.setStyleSheet("color: white; font-size: 26px; font-weight: 800;")
        
        subtitle_lbl = QLabel(f"正在修改: {self.config_item.key}")
        subtitle_lbl.setStyleSheet("color: rgba(255,255,255,0.85); font-size: 13px; font-weight: 500;")
        
        title_info.addWidget(title_lbl)
        title_info.addWidget(subtitle_lbl)
        
        icon_bg = QLabel("⚙️")
        icon_bg.setFixedSize(56, 56)
        icon_bg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_bg.setStyleSheet("""
            background: rgba(255,255,255,0.2);
            border-radius: 28px;
            font-size: 26px;
        """)
        
        header_layout.addLayout(title_info)
        header_layout.addWidget(icon_bg)
        layout.addWidget(header)
        
        # === 2. 表单区域 ===
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(32, 32, 32, 20)
        form_layout.setSpacing(20)
        
        self.input_style = f"""
            QLineEdit {{
                border: 1px solid {PREMIUM_COLORS['border_light']};
                border-radius: 10px;
                padding: 0 12px;
                background: #f8fafc;
                height: 42px;
                font-size: 14px;
                color: {PREMIUM_COLORS['text_heading']};
            }}
            QLineEdit:focus {{
                border: 1px solid {PREMIUM_COLORS['gradient_purple_start']};
                background: white;
            }}
        """
        form_widget.setStyleSheet(self.input_style)
        
        # 说明 (只读)
        desc_label = QLabel(self.config_item.description or "无说明")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"""
            background: {PREMIUM_COLORS['surface']};
            color: {PREMIUM_COLORS['text_body']};
            padding: 12px;
            border-radius: 8px;
            border: 1px solid {PREMIUM_COLORS['border_light']};
        """)
        form_layout.addLayout(self._create_field_label("配置说明", desc_label))
        
        # 值 (可编辑)
        self.value_input = QLineEdit(self.config_item.value)
        self.value_input.setPlaceholderText("请输入配置值")
        form_layout.addLayout(self._create_field("当前值", self.value_input, "修改后的配置将立即生效"))
        
        form_layout.addStretch()
        layout.addWidget(form_widget)
        
        # === 3. 底部按钮 ===
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
            "保存更改", 
            PREMIUM_COLORS['gradient_purple_start'], 
            PREMIUM_COLORS['gradient_purple_end']
        )
        save_btn.setFixedSize(140, 44)
        save_btn.clicked.connect(self.save_config)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
        
    def _create_field(self, label_text, widget, hint_text=None):
        layout = QVBoxLayout()
        layout.setSpacing(6)
        
        label = QLabel(label_text)
        label.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-weight: 600; font-size: 13px;")
        layout.addWidget(label)
        layout.addWidget(widget)
        
        if hint_text:
            hint = QLabel(hint_text)
            hint.setStyleSheet(f"color: {PREMIUM_COLORS['text_hint']}; font-size: 11px;")
            layout.addWidget(hint)
            
        return layout

    def _create_field_label(self, label_text, widget):
        """专为QLabel这种非输入框设计的布局"""
        layout = QVBoxLayout()
        layout.setSpacing(6)
        label = QLabel(label_text)
        label.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-weight: 600; font-size: 13px;")
        layout.addWidget(label)
        layout.addWidget(widget)
        return layout

    def save_config(self):
        new_value = self.value_input.text().strip()
        if not new_value:
            QMessageBox.warning(self, "错误", "配置值不能为空")
            return
            
        try:
            SystemConfig.set(self.config_item.key, new_value)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

class AdminDictionaryManager(QWidget):
    """管理员字典/配置管理页面 - 极简布局版"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
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
        
        # === 顶部区域 (标题 + 统计) ===
        self._create_header(main_layout)
        
        # === 主表格区域 (包含工具栏) ===
        self._create_main_card(main_layout)
        
        # 加载数据
        self.load_configs()
        
    def _create_header(self, layout):
        """创建顶部区域：标题、统计"""
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)
        
        # 1. 标题
        title_label = QLabel("字典管理")
        title_label.setStyleSheet(f"""
            font-size: 24px; 
            font-weight: 800; 
            color: {PREMIUM_COLORS['text_heading']};
            background: transparent;
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addSpacing(16)
        
        # 2. 统计组件
        cards_data = [
            ("配置项总数", 0, "🔢", PREMIUM_COLORS['gradient_purple_start'], PREMIUM_COLORS['gradient_purple_end']),
        ]
        
        for title, value, icon, start, end in cards_data:
            card = CompactStatWidget(title, value, icon, start, end)
            self.stat_cards[title] = card
            header_layout.addWidget(card)
            
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
    def _create_main_card(self, layout):
        """创建主内容卡片：工具栏 + 表格"""
        card = GlassFrame(opacity=1.0, radius=16)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        
        # 1. 工具栏 (搜索 + 刷新)
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
        self.search_input.setPlaceholderText("搜索配置键...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                background: transparent;
                font-size: 13px;
                color: {PREMIUM_COLORS['text_heading']};
                padding: 0;
            }}
        """)
        self.search_input.textChanged.connect(self.load_configs)
        search_layout.addWidget(self.search_input)
        toolbar_layout.addWidget(search_container)
        
        toolbar_layout.addStretch()
        
        # 刷新按钮
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
                color: {PREMIUM_COLORS['gradient_purple_start']};
                border-color: {PREMIUM_COLORS['gradient_purple_start']};
            }}
        """)
        refresh_btn.clicked.connect(self.load_configs)
        toolbar_layout.addWidget(refresh_btn)
        
        card_layout.addWidget(toolbar)
        
        # 2. 自定义字典列表
        self.dict_list = DictListWidget()
        self.dict_list.edit_config.connect(self.edit_config)
        
        card_layout.addWidget(self.dict_list, 1)
        layout.addWidget(card, 1)
        
    def load_configs(self):
        """加载配置列表"""
        keyword = self.search_input.text().strip().lower()
        
        try:
            configs = SystemConfig.objects.all().order_by('key')
            
            # 内存过滤 (数据量小)
            if keyword:
                configs = [c for c in configs if keyword in c.key.lower() or keyword in (c.description or "").lower()]
            else:
                configs = list(configs)
            
            # 更新统计
            if "配置项总数" in self.stat_cards:
                self.stat_cards["配置项总数"].update_value(len(configs))
            
            # 使用自定义列表组件显示
            self.dict_list.set_configs(configs)
                
        except Exception as e:
            print(f"❌ 加载配置失败: {e}")
            import traceback
            traceback.print_exc()
            
    def edit_config(self, config_item):
        """编辑配置"""
        dialog = DictionaryEditDialog(config_item, self)
        if dialog.exec():
            self.load_configs()
