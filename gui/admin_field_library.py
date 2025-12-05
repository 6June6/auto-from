"""
字段库管理模块
用于管理员维护平台字段库（系统级）
采用现代化玻璃拟态设计风格
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, 
    QMessageBox, QLineEdit, QFrame, QAbstractItemView, 
    QGraphicsDropShadowEffect, QDialog, QComboBox, QScrollArea, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor, QBrush
from database import DatabaseManager, FieldLibrary, User
from gui.styles import COLORS
from gui.icons import Icons

# 扩展颜色系统
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
    
    'border_light': '#e2e8f0',
    'background': '#f8fafc',
    'surface': '#ffffff',
}

class GlassFrame(QFrame):
    """玻璃拟态框架"""
    def __init__(self, parent=None, opacity=1.0, radius=16):
        super().__init__(parent)
        self.setStyleSheet(f"""
            GlassFrame {{
                background: rgba(255, 255, 255, {opacity});
                border: 1px solid rgba(255, 255, 255, 0.8);
                border-radius: {radius}px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 12))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)

class GradientButton(QPushButton):
    """渐变按钮"""
    def __init__(self, text, start_color, end_color, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(40)
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {start_color}, stop:1 {end_color});
                color: white;
                border: none;
                border-radius: 20px;
                font-weight: 600;
                font-size: 13px;
                padding: 0 20px;
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

class PushToUserDialog(QDialog):
    """推送字段给用户对话框"""
    def __init__(self, field, db_manager, current_user, parent=None):
        super().__init__(parent)
        self.field = field
        self.db_manager = db_manager
        self.current_user = current_user
        self.selected_users = set()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle(f"推送字段: {self.field.name}")
        self.setFixedSize(500, 600)
        self.setStyleSheet(f"background-color: {PREMIUM_COLORS['surface']};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # 标题
        title = QLabel("选择要推送的用户")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {PREMIUM_COLORS['text_heading']};")
        layout.addWidget(title)
        
        # 搜索
        search_container = QFrame()
        search_container.setStyleSheet(f"""
            QFrame {{
                background: {PREMIUM_COLORS['background']};
                border-radius: 8px;
            }}
        """)
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(12, 8, 12, 8)
        
        search_icon = QLabel("🔍")
        search_input = QLineEdit()
        search_input.setPlaceholderText("搜索用户名...")
        search_input.setStyleSheet("border: none; background: transparent;")
        search_input.textChanged.connect(self.filter_users)
        
        search_layout.addWidget(search_icon)
        search_layout.addWidget(search_input)
        layout.addWidget(search_container)
        
        # 用户列表
        self.user_list = QListWidget()
        self.user_list.setStyleSheet(f"""
            QListWidget {{
                border: 1px solid {PREMIUM_COLORS['border_light']};
                border-radius: 8px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 12px;
                border-bottom: 1px solid {PREMIUM_COLORS['border_light']};
            }}
            QListWidget::item:selected {{
                background: {PREMIUM_COLORS['background']};
                color: {PREMIUM_COLORS['text_heading']};
            }}
        """)
        layout.addWidget(self.user_list)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PREMIUM_COLORS['background']};
                border: none;
                border-radius: 20px;
                padding: 8px 24px;
                font-weight: 600;
                color: {PREMIUM_COLORS['text_body']};
            }}
            QPushButton:hover {{ background: {PREMIUM_COLORS['border_light']}; }}
        """)
        cancel_btn.clicked.connect(self.reject)
        
        self.push_btn = GradientButton(
            "确认推送",
            PREMIUM_COLORS['gradient_blue_start'],
            PREMIUM_COLORS['gradient_blue_end']
        )
        self.push_btn.clicked.connect(self.do_push)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.push_btn)
        layout.addLayout(btn_layout)
        
        self.load_users()
        
    def load_users(self):
        self.users = self.db_manager.get_all_users()
        # 过滤掉管理员自己（可选）
        self.users = [u for u in self.users if u.id != self.current_user.id]
        self.update_list(self.users)
        
    def update_list(self, users):
        self.user_list.clear()
        for user in users:
            item = QListWidgetItem(self.user_list)
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(4, 0, 4, 0)
            
            # Checkbox logic handled manually or via QListWidgetItem checkstate
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, str(user.id))
            item.setText(f"  {user.username} ({'管理员' if user.role=='admin' else '用户'})")
            
            # Add to list
            self.user_list.addItem(item)
            
    def filter_users(self, text):
        text = text.lower()
        filtered = [u for u in self.users if text in u.username.lower()]
        self.update_list(filtered)
        
    def do_push(self):
        selected_ids = []
        for i in range(self.user_list.count()):
            item = self.user_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_ids.append(item.data(Qt.ItemDataRole.UserRole))
                
        if not selected_ids:
            QMessageBox.warning(self, "提示", "请至少选择一个用户")
            return
            
        count = self.db_manager.push_field_to_users(str(self.field.id), selected_ids, self.current_user)
        if count > 0:
            QMessageBox.information(self, "成功", f"已向 {count} 位用户发送推荐消息")
            self.accept()
        else:
            QMessageBox.warning(self, "失败", "推送失败")

class AddFieldDialog(QDialog):
    """添加/编辑字段对话框"""
    
    def __init__(self, parent=None, field=None, db_manager=None, current_user=None):
        super().__init__(parent)
        self.field = field
        self.db_manager = db_manager or DatabaseManager()
        self.current_user = current_user
        self.init_ui()
        
    def init_ui(self):
        title = "编辑字段" if self.field else "添加字段"
        self.setWindowTitle(title)
        self.setFixedSize(500, 580)
        self.setStyleSheet(f"background-color: {PREMIUM_COLORS['surface']};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 标题
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {PREMIUM_COLORS['text_heading']};")
        layout.addWidget(title_lbl)
        
        # 表单区域
        form_layout = QVBoxLayout()
        form_layout.setSpacing(15)
        
        # 字段名称
        self.name_input = self._create_input_field("字段名称", "支持别名，用顿号分隔 (e.g. 手机号、电话)")
        form_layout.addWidget(self.name_input)
        
        # 分类
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        # 获取现有分类
        existing_cats = self.db_manager.get_field_library_categories()
        default_cats = ['基本信息', '平台数据', '报价相关', '小红书', '抖音', '微博', '快手', '通用']
        all_cats = sorted(list(set(existing_cats + default_cats)))
        self.category_combo.addItems(all_cats)
        self.category_combo.setMinimumHeight(40)
        self.category_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 5px 10px;
                border: 1px solid {PREMIUM_COLORS['border_light']};
                border-radius: 8px;
                background: #f8fafc;
            }}
            QComboBox:focus {{ border: 1px solid {PREMIUM_COLORS['primary']}; background: white; }}
        """)
        
        cat_label = QLabel("分类")
        cat_label.setStyleSheet(f"font-weight: 600; color: {PREMIUM_COLORS['text_body']};")
        form_layout.addWidget(cat_label)
        form_layout.addWidget(self.category_combo)
        
        # 说明
        self.desc_input = self._create_input_field("说明", "字段用途说明")
        form_layout.addWidget(self.desc_input)
        
        # 默认值
        self.default_input = self._create_input_field("默认值示例", "选填")
        form_layout.addWidget(self.default_input)
        
        # 排序
        self.order_input = self._create_input_field("排序", "数字越小越靠前", "0")
        form_layout.addWidget(self.order_input)
        
        layout.addLayout(form_layout)
        layout.addStretch()
        
        # 按钮组
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(100, 40)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: #f1f5f9; border: none; border-radius: 20px;
                color: {PREMIUM_COLORS['text_body']}; font-weight: 600;
            }}
            QPushButton:hover {{ background: #e2e8f0; }}
        """)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("保存")
        save_btn.setFixedSize(100, 40)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {PREMIUM_COLORS['gradient_blue_start']}, stop:1 {PREMIUM_COLORS['gradient_blue_end']});
                border: none; border-radius: 20px;
                color: white; font-weight: 600;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
        """)
        save_btn.clicked.connect(self.save_data)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        
        # 回显数据
        if self.field:
            self.name_input.input.setText(self.field.name)
            self.category_combo.setCurrentText(self.field.category)
            self.desc_input.input.setText(self.field.description)
            self.default_input.input.setText(self.field.default_value)
            self.order_input.input.setText(str(self.field.order))
            
    def _create_input_field(self, label_text, placeholder="", default_val=""):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(6)
        
        label = QLabel(label_text)
        label.setStyleSheet(f"font-weight: 600; color: {PREMIUM_COLORS['text_body']};")
        layout.addWidget(label)
        
        input_field = QLineEdit()
        input_field.setPlaceholderText(placeholder)
        input_field.setText(default_val)
        input_field.setMinimumHeight(40)
        input_field.setStyleSheet(f"""
            QLineEdit {{
                padding: 0 10px;
                border: 1px solid {PREMIUM_COLORS['border_light']};
                border-radius: 8px;
                background: #f8fafc;
            }}
            QLineEdit:focus {{
                border: 1px solid {PREMIUM_COLORS['primary']};
                background: white;
            }}
        """)
        container.input = input_field
        layout.addWidget(input_field)
        return container

    def save_data(self):
        name = self.name_input.input.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入字段名称")
            return
            
        try:
            order = int(self.order_input.input.text().strip() or "0")
        except ValueError:
            order = 0
            
        data = {
            'name': name,
            'category': self.category_combo.currentText().strip() or '通用',
            'description': self.desc_input.input.text().strip(),
            'default_value': self.default_input.input.text().strip(),
            'order': order
        }
        
        try:
            if self.field:
                self.db_manager.update_field_library(str(self.field.id), **data)
            else:
                self.db_manager.create_field_library(
                    created_by=self.current_user,
                    **data
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

class AdminFieldLibraryManager(QWidget):
    """管理员字段库管理页面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.current_page = 1
        self.page_size = 15
        self.total_records = 0
        self.total_pages = 1
        self.stat_widgets = {}
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
        
        # === Header ===
        self._create_header(main_layout)
        
        # === Main Card ===
        self._create_main_card(main_layout)
        
        # Initial Load
        self.refresh_categories()
        self.load_data()
        
    def _create_header(self, layout):
        """创建顶部区域：标题、统计"""
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)
        
        # 1. 标题
        title_label = QLabel("字段库管理")
        title_label.setStyleSheet(f"""
            font-size: 24px; 
            font-weight: 800; 
            color: {PREMIUM_COLORS['text_heading']};
            background: transparent;
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addSpacing(16)
        
        # 2. 统计组件
        stats_data = [
            ("总字段数", 0, "📚", PREMIUM_COLORS['gradient_blue_start'], PREMIUM_COLORS['gradient_blue_end']),
            ("已启用", 0, "✅", PREMIUM_COLORS['gradient_green_start'], PREMIUM_COLORS['gradient_green_end']),
        ]
        
        for title, value, icon, start, end in stats_data:
            card = CompactStatWidget(title, value, icon, start, end)
            self.stat_widgets[title] = card
            header_layout.addWidget(card)
            
        header_layout.addStretch()
        
        # 3. 刷新按钮
        refresh_btn = GradientButton(
            "刷新列表",
            PREMIUM_COLORS['gradient_blue_start'],
            PREMIUM_COLORS['gradient_blue_end']
        )
        refresh_btn.setFixedSize(120, 40)
        refresh_btn.clicked.connect(self.load_data)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
    def _create_main_card(self, layout):
        """创建主内容区域"""
        card = GlassFrame(opacity=1.0, radius=16)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        
        # Toolbar
        toolbar = QFrame()
        toolbar.setFixedHeight(64)
        toolbar.setStyleSheet(f"border-bottom: 1px solid {PREMIUM_COLORS['border_light']}; background: transparent;")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(24, 0, 24, 0)
        toolbar_layout.setSpacing(16)
        
        # Add Button
        add_btn = QPushButton("添加字段")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setFixedSize(100, 36)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PREMIUM_COLORS['success']};
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: #28a745; }}
        """)
        add_btn.clicked.connect(self.show_add_dialog)
        toolbar_layout.addWidget(add_btn)
        
        # Filter
        self.category_filter = QComboBox()
        self.category_filter.setFixedSize(120, 36)
        self.category_filter.setStyleSheet(f"""
            QComboBox {{
                padding: 0 10px;
                border: 1px solid {PREMIUM_COLORS['border_light']};
                border-radius: 6px;
                background: white;
                color: {PREMIUM_COLORS['text_body']};
            }}
        """)
        self.category_filter.addItem("全部")
        self.category_filter.currentTextChanged.connect(self.on_search)
        toolbar_layout.addWidget(self.category_filter)
        
        toolbar_layout.addStretch()
        
        # Search
        search_container = QFrame()
        search_container.setFixedSize(260, 36)
        search_container.setStyleSheet(f"""
            QFrame {{
                background: #f1f5f9;
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
        self.search_input.setPlaceholderText("搜索字段名称...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: none; 
                background: transparent;
                font-size: 13px;
                color: #2d3748;
                padding: 0;
            }
        """)
        self.search_input.textChanged.connect(self.on_search)
        search_layout.addWidget(self.search_input)
        toolbar_layout.addWidget(search_container)
        
        card_layout.addWidget(toolbar)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(['字段名称', '分类', '说明', '默认值', '排序', '状态', '操作'])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch) # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)   # Category
        self.table.setColumnWidth(1, 100)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # Desc
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)   # Default
        self.table.setColumnWidth(3, 120)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)   # Order
        self.table.setColumnWidth(4, 60)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)   # Status
        self.table.setColumnWidth(5, 80)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)   # Actions
        self.table.setColumnWidth(6, 220) # 增加宽度以容纳"推送"按钮
        
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        self.table.setStyleSheet(f"""
            QTableWidget {{ background: transparent; border: none; }}
            QTableWidget::item {{ 
                border-bottom: 1px solid {PREMIUM_COLORS['border_light']}; 
                padding: 0 10px; 
            }}
            QTableWidget::item:selected {{
                background-color: {PREMIUM_COLORS['gradient_blue_start']}08;
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
                background: {PREMIUM_COLORS['gradient_blue_start']}15;
                color: {PREMIUM_COLORS['gradient_blue_start']};
                border-color: {PREMIUM_COLORS['gradient_blue_start']};
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
        
    def refresh_categories(self):
        current = self.category_filter.currentText()
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("全部")
        cats = self.db_manager.get_field_library_categories()
        self.category_filter.addItems(cats)
        self.category_filter.setCurrentText(current if current in cats or current == "全部" else "全部")
        self.category_filter.blockSignals(False)
        
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
        
    def load_data(self):
        category = self.category_filter.currentText()
        if category == "全部": category = None
        
        search_text = self.search_input.text().strip().lower()
        
        all_fields = self.db_manager.get_all_field_library(category=category, is_active=None)
        
        # Client-side filtering for search
        if search_text:
            all_fields = [f for f in all_fields if search_text in f.name.lower() or search_text in (f.description or '').lower()]
            
        # Update Stats
        total_count = len(all_fields)
        enabled_count = sum(1 for f in all_fields if f.is_active)
        
        if "总字段数" in self.stat_widgets:
            self.stat_widgets["总字段数"].update_value(total_count)
        if "已启用" in self.stat_widgets:
            self.stat_widgets["已启用"].update_value(enabled_count)
            
        # Pagination
        self.total_records = total_count
        self.total_pages = max(1, (self.total_records + self.page_size - 1) // self.page_size)
        
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
            
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = start_idx + self.page_size
        fields = all_fields[start_idx:end_idx]
        
        self.update_table(fields)
        self.update_pagination()
        
    def update_table(self, fields):
        self.table.setRowCount(len(fields))
        
        for row, field in enumerate(fields):
            self.table.setRowHeight(row, 60)
            
            # 1. Name
            name_item = QTableWidgetItem(field.name)
            name_item.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            name_item.setForeground(QColor(PREMIUM_COLORS['text_heading']))
            self.table.setItem(row, 0, name_item)
            
            # 2. Category
            cat_widget = QWidget()
            cat_layout = QHBoxLayout(cat_widget)
            cat_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cat_layout.setContentsMargins(0,0,0,0)
            
            cat_lbl = QLabel(field.category or '通用')
            cat_lbl.setStyleSheet(f"""
                background: {PREMIUM_COLORS['text_hint']}15;
                color: {PREMIUM_COLORS['text_body']};
                border-radius: 10px;
                padding: 4px 8px;
                font-size: 12px;
                font-weight: 500;
            """)
            cat_layout.addWidget(cat_lbl)
            self.table.setCellWidget(row, 1, cat_widget)
            
            # 3. Desc
            desc = field.description or '-'
            if len(desc) > 20: desc = desc[:20] + '...'
            self.table.setItem(row, 2, QTableWidgetItem(desc))
            
            # 4. Default
            default_val = field.default_value or '-'
            if len(default_val) > 15: default_val = default_val[:15] + '...'
            self.table.setItem(row, 3, QTableWidgetItem(default_val))
            
            # 5. Order
            order_item = QTableWidgetItem(str(field.order))
            order_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, order_item)
            
            # 6. Status Widget
            status_widget = QWidget()
            sl = QHBoxLayout(status_widget)
            sl.setContentsMargins(0,0,0,0)
            sl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            status_lbl = QLabel()
            if field.is_active:
                status_lbl.setText("✅ 启用")
                status_lbl.setStyleSheet("color: #059669; background: #ecfdf5; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: 600;")
            else:
                status_lbl.setText("⛔ 禁用")
                status_lbl.setStyleSheet("color: #dc2626; background: #fef2f2; padding: 4px 8px; border-radius: 6px; font-size: 12px; font-weight: 600;")
            sl.addWidget(status_lbl)
            self.table.setCellWidget(row, 5, status_widget)
            
            # 7. Actions
            action_widget = QWidget()
            al = QHBoxLayout(action_widget)
            al.setContentsMargins(0,0,0,0)
            al.setSpacing(8)
            al.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Push Button
            push_btn = QPushButton("推送")
            push_btn.setFixedSize(50, 28)
            push_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            push_btn.setStyleSheet(f"""
                QPushButton {{
                    background: white;
                    color: {PREMIUM_COLORS['gradient_orange_start']};
                    border: 1px solid {PREMIUM_COLORS['gradient_orange_start']}40;
                    border-radius: 4px;
                    font-weight: 600;
                    font-size: 12px;
                }}
                QPushButton:hover {{ 
                    background: {PREMIUM_COLORS['gradient_orange_start']}10; 
                    border-color: {PREMIUM_COLORS['gradient_orange_start']};
                }}
            """)
            push_btn.clicked.connect(lambda _, f=field: self.show_push_dialog(f))
            al.addWidget(push_btn)
            
            edit_btn = QPushButton("编辑")
            edit_btn.setFixedSize(50, 28)
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setStyleSheet(f"""
                QPushButton {{
                    background: white;
                    color: {PREMIUM_COLORS['gradient_blue_start']};
                    border: 1px solid {PREMIUM_COLORS['gradient_blue_start']}40;
                    border-radius: 4px;
                    font-weight: 600;
                    font-size: 12px;
                }}
                QPushButton:hover {{ 
                    background: {PREMIUM_COLORS['gradient_blue_start']}10; 
                    border-color: {PREMIUM_COLORS['gradient_blue_start']};
                }}
            """)
            edit_btn.clicked.connect(lambda _, f=field: self.show_add_dialog(f))
            al.addWidget(edit_btn)
            
            toggle_btn = QPushButton("禁用" if field.is_active else "启用")
            toggle_btn.setFixedSize(50, 28)
            toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            if field.is_active:
                color = PREMIUM_COLORS['coral']
                bg_hover = f"{PREMIUM_COLORS['coral']}10"
            else:
                color = PREMIUM_COLORS['gradient_green_start']
                bg_hover = f"{PREMIUM_COLORS['gradient_green_start']}10"
                
            toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background: white;
                    color: {color};
                    border: 1px solid {color}40;
                    border-radius: 4px;
                    font-weight: 600;
                    font-size: 12px;
                }}
                QPushButton:hover {{ 
                    background: {bg_hover}; 
                    border-color: {color};
                }}
            """)
            toggle_btn.clicked.connect(lambda _, f=field: self.toggle_status(f))
            al.addWidget(toggle_btn)
            
            self.table.setCellWidget(row, 6, action_widget)
            
    def show_add_dialog(self, field=None):
        # 获取当前主窗口的用户信息
        current_user = None
        parent = self.window()
        if hasattr(parent, 'current_user'):
            current_user = parent.current_user
            
        dialog = AddFieldDialog(self, field, self.db_manager, current_user)
        if dialog.exec():
            self.refresh_categories() # 分类可能更新
            self.load_data()
            
    def show_push_dialog(self, field):
        # 获取当前主窗口的用户信息
        current_user = None
        parent = self.window()
        if hasattr(parent, 'current_user'):
            current_user = parent.current_user
            
        dialog = PushToUserDialog(field, self.db_manager, current_user, self)
        dialog.exec()
            
    def toggle_status(self, field):
        try:
            new_status = not field.is_active
            self.db_manager.update_field_library(field_id=str(field.id), is_active=new_status)
            self.load_data()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"操作失败: {str(e)}")
