"""
字典管理模块
重写后的字典管理界面，采用现代化玻璃拟态设计风格，与用户管理保持一致
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, 
    QMessageBox, QLineEdit, QDialog, QFrame,
    QGraphicsDropShadowEffect, QAbstractItemView
)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QTimer, QRect
from PyQt6.QtGui import QFont, QColor, QIcon, QPainter, QLinearGradient, QPen, QBrush, QPainterPath
from database.models import SystemConfig
from gui.styles import COLORS
from gui.icons import Icons

# 扩展颜色系统 - 与用户管理保持一致
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
        
        # 2. 表格
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['配置键', '说明', '当前值', '操作'])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        
        self.table.setColumnWidth(0, 200)
        self.table.setColumnWidth(3, 100)
        
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
        layout.addWidget(card, 1)
        
    def load_configs(self):
        """加载配置列表"""
        keyword = self.search_input.text().strip().lower()
        self.table.setRowCount(0)
        
        try:
            configs = SystemConfig.objects.all().order_by('key')
            
            # 内存过滤 (数据量小)
            if keyword:
                configs = [c for c in configs if keyword in c.key.lower() or keyword in (c.description or "").lower()]
            
            # 更新统计
            if "配置项总数" in self.stat_cards:
                self.stat_cards["配置项总数"].update_value(len(configs))
            
            self.table.setRowCount(len(configs))
            
            for row, config in enumerate(configs):
                self.table.setRowHeight(row, 60)
                
                # 0. Key
                key_widget = QWidget()
                key_layout = QHBoxLayout(key_widget)
                key_layout.setContentsMargins(12, 0, 4, 0)
                key_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                
                key_lbl = QLabel(config.key)
                key_lbl.setStyleSheet(f"font-weight: 700; color: {PREMIUM_COLORS['text_heading']}; font-family: monospace;")
                key_layout.addWidget(key_lbl)
                self.table.setCellWidget(row, 0, key_widget)
                
                # 1. Description
                desc_item = QTableWidgetItem(config.description or "-")
                desc_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                desc_item.setForeground(QBrush(QColor(PREMIUM_COLORS['text_body'])))
                self.table.setItem(row, 1, desc_item)
                
                # 2. Value
                val_widget = QWidget()
                val_layout = QHBoxLayout(val_widget)
                val_layout.setContentsMargins(4, 0, 4, 0)
                val_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                
                val_lbl = QLabel(config.value)
                val_lbl.setStyleSheet(f"color: {PREMIUM_COLORS['gradient_purple_start']}; font-weight: 600;")
                val_layout.addWidget(val_lbl)
                self.table.setCellWidget(row, 2, val_widget)
                
                # 3. Action
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(0, 0, 0, 0)
                action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
                edit_btn = QPushButton("编辑")
                edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                edit_btn.setFixedSize(50, 28)
                edit_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {PREMIUM_COLORS['gradient_purple_start']}15;
                        color: {PREMIUM_COLORS['gradient_purple_start']};
                        border: 1px solid {PREMIUM_COLORS['gradient_purple_start']}40;
                        border-radius: 4px;
                        font-size: 12px;
                        font-weight: 600;
                    }}
                    QPushButton:hover {{
                        background: {PREMIUM_COLORS['gradient_purple_start']};
                        color: white;
                        border-color: {PREMIUM_COLORS['gradient_purple_start']};
                    }}
                """)
                # 使用闭包捕获当前的 config 对象
                edit_btn.clicked.connect(lambda checked, c=config: self.edit_config(c))
                
                action_layout.addWidget(edit_btn)
                self.table.setCellWidget(row, 3, action_widget)
                
        except Exception as e:
            print(f"❌ 加载配置失败: {e}")
            import traceback
            traceback.print_exc()
            
    def edit_config(self, config_item):
        """编辑配置"""
        dialog = DictionaryEditDialog(config_item, self)
        if dialog.exec():
            self.load_configs()
