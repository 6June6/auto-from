"""
字段库管理模块
用于管理员维护平台字段库（系统级）
采用现代化玻璃拟态设计风格
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QMessageBox, QLineEdit, QFrame, 
    QGraphicsDropShadowEffect, QDialog, QComboBox, QScrollArea, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from database import DatabaseManager, FieldLibrary, User
from gui.admin_base_components import (
    PREMIUM_COLORS, GlassFrame, GradientButton, CompactStatWidget, create_action_button
)


# ========== 字段库列表自定义组件 ==========

# 列宽配置
FIELD_LIST_COLUMNS = {
    'name': 180,
    'category': 100,
    'desc': 160,
    'default': 120,
    'order': 60,
    'status': 80,
    'actions': 180,
}


class FieldListHeader(QFrame):
    """字段库列表表头"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(f"""
            FieldListHeader {{
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
            ('字段名称', FIELD_LIST_COLUMNS['name']),
            ('分类', FIELD_LIST_COLUMNS['category']),
            ('说明', FIELD_LIST_COLUMNS['desc']),
            ('默认值', FIELD_LIST_COLUMNS['default']),
            ('排序', FIELD_LIST_COLUMNS['order']),
            ('状态', FIELD_LIST_COLUMNS['status']),
            ('操作', FIELD_LIST_COLUMNS['actions']),
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


class FieldRowWidget(QFrame):
    """字段行组件"""
    
    push_clicked = pyqtSignal(object)
    edit_clicked = pyqtSignal(object)
    toggle_clicked = pyqtSignal(object)
    
    def __init__(self, field, parent=None):
        super().__init__(parent)
        self.field = field
        self.setFixedHeight(64)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet(f"""
            FieldRowWidget {{
                background: white;
                border: none;
                border-bottom: 1px solid {PREMIUM_COLORS['border_light']};
            }}
            FieldRowWidget:hover {{
                background: #fafbfc;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(0)
        
        # 1. 字段名称
        self._add_name(layout)
        # 2. 分类
        self._add_category(layout)
        # 3. 说明
        self._add_desc(layout)
        # 4. 默认值
        self._add_default(layout)
        # 5. 排序
        self._add_order(layout)
        # 6. 状态
        self._add_status(layout)
        # 7. 操作
        self._add_actions(layout)
        
        layout.addStretch()
    
    def _add_name(self, layout):
        container = QWidget()
        container.setFixedWidth(FIELD_LIST_COLUMNS['name'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 8, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        name_lbl = QLabel(self.field.name)
        name_lbl.setStyleSheet(f"font-weight: 600; color: {PREMIUM_COLORS['text_heading']}; font-size: 13px;")
        name_lbl.setWordWrap(True)
        c_layout.addWidget(name_lbl)
        layout.addWidget(container)
    
    def _add_category(self, layout):
        container = QWidget()
        container.setFixedWidth(FIELD_LIST_COLUMNS['category'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        cat_lbl = QLabel(self.field.category or '通用')
        cat_lbl.setStyleSheet(f"""
            background: {PREMIUM_COLORS['text_hint']}15;
            color: {PREMIUM_COLORS['text_body']};
            border-radius: 10px;
            padding: 4px 8px;
            font-size: 11px;
            font-weight: 500;
        """)
        c_layout.addWidget(cat_lbl)
        layout.addWidget(container)
    
    def _add_desc(self, layout):
        container = QWidget()
        container.setFixedWidth(FIELD_LIST_COLUMNS['desc'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        desc = self.field.description or '-'
        if len(desc) > 15:
            desc = desc[:15] + '...'
        lbl = QLabel(desc)
        lbl.setToolTip(self.field.description or '')
        lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-size: 12px;")
        c_layout.addWidget(lbl)
        layout.addWidget(container)
    
    def _add_default(self, layout):
        container = QWidget()
        container.setFixedWidth(FIELD_LIST_COLUMNS['default'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        default_val = self.field.default_value or '-'
        if len(default_val) > 12:
            default_val = default_val[:12] + '...'
        lbl = QLabel(default_val)
        lbl.setToolTip(self.field.default_value or '')
        lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_hint']}; font-size: 12px;")
        c_layout.addWidget(lbl)
        layout.addWidget(container)
    
    def _add_order(self, layout):
        container = QWidget()
        container.setFixedWidth(FIELD_LIST_COLUMNS['order'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl = QLabel(str(self.field.order))
        lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-size: 12px;")
        c_layout.addWidget(lbl)
        layout.addWidget(container)
    
    def _add_status(self, layout):
        container = QWidget()
        container.setFixedWidth(FIELD_LIST_COLUMNS['status'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        status_lbl = QLabel()
        if self.field.is_active:
            status_lbl.setText("✅ 启用")
            status_lbl.setStyleSheet("color: #059669; background: #ecfdf5; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;")
        else:
            status_lbl.setText("⛔ 禁用")
            status_lbl.setStyleSheet("color: #dc2626; background: #fef2f2; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;")
        
        c_layout.addWidget(status_lbl)
        layout.addWidget(container)
    
    def _add_actions(self, layout):
        container = QWidget()
        container.setFixedWidth(FIELD_LIST_COLUMNS['actions'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(6)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # 推送按钮
        btn_push = create_action_button("推送", PREMIUM_COLORS['gradient_orange_start'])
        btn_push.clicked.connect(lambda: self.push_clicked.emit(self.field))
        c_layout.addWidget(btn_push)
        
        # 编辑按钮
        btn_edit = create_action_button("编辑", PREMIUM_COLORS['gradient_blue_start'])
        btn_edit.clicked.connect(lambda: self.edit_clicked.emit(self.field))
        c_layout.addWidget(btn_edit)
        
        # 禁用/启用按钮
        if self.field.is_active:
            btn_toggle = create_action_button("禁用", PREMIUM_COLORS['coral'])
        else:
            btn_toggle = create_action_button("启用", PREMIUM_COLORS['gradient_green_start'])
        btn_toggle.clicked.connect(lambda: self.toggle_clicked.emit(self.field))
        c_layout.addWidget(btn_toggle)
        
        layout.addWidget(container)


class FieldListWidget(QWidget):
    """字段库列表组件"""
    
    push_field = pyqtSignal(object)
    edit_field = pyqtSignal(object)
    toggle_field = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.row_widgets = []
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.header = FieldListHeader()
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
    
    def set_fields(self, fields):
        for widget in self.row_widgets:
            widget.deleteLater()
        self.row_widgets.clear()
        
        if not fields:
            empty_label = QLabel("暂无字段数据")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet(f"""
                color: {PREMIUM_COLORS['text_hint']};
                font-size: 14px;
                padding: 60px;
            """)
            self.content_layout.addWidget(empty_label)
            self.row_widgets.append(empty_label)
            return
        
        for field in fields:
            row = FieldRowWidget(field)
            row.push_clicked.connect(self.push_field.emit)
            row.edit_clicked.connect(self.edit_field.emit)
            row.toggle_clicked.connect(self.toggle_field.emit)
            
            self.content_layout.addWidget(row)
            self.row_widgets.append(row)

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
        
        # 字段名称（带加号按钮）
        self.name_input = self._create_input_field_with_add_btn("字段名称", "支持别名，用顿号分隔 (e.g. 手机号、电话)")
        form_layout.addWidget(self.name_input)
        
        # 分类
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        # 获取现有分类
        existing_cats = self.db_manager.get_field_library_categories()
        default_cats = ['基本信息', '平台数据', '报价相关', '小红书', '抖音', '微博', '快手', '通用']
        all_cats = sorted(list(set(existing_cats + default_cats)))
        self.category_combo.blockSignals(True)
        self.category_combo.model().blockSignals(True)
        self.category_combo.addItems(all_cats)
        self.category_combo.model().blockSignals(False)
        self.category_combo.blockSignals(False)
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
    
    def _create_input_field_with_add_btn(self, label_text, placeholder="", default_val=""):
        """创建带加号按钮的输入框（用于添加别名）"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        label = QLabel(label_text)
        label.setStyleSheet(f"font-weight: 600; color: {PREMIUM_COLORS['text_body']};")
        layout.addWidget(label)
        
        # 输入框容器（包含输入框和内嵌加号按钮）
        input_container = QWidget()
        input_container.setMinimumHeight(40)
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(0)
        
        input_field = QLineEdit()
        input_field.setPlaceholderText(placeholder)
        input_field.setText(default_val)
        input_field.setMinimumHeight(40)
        input_field.setStyleSheet(f"""
            QLineEdit {{
                padding: 0 40px 0 10px;
                border: 1px solid {PREMIUM_COLORS['border_light']};
                border-radius: 8px;
                background: #f8fafc;
            }}
            QLineEdit:focus {{
                border: 1px solid {PREMIUM_COLORS['primary']};
                background: white;
            }}
        """)
        input_layout.addWidget(input_field)
        
        # 加号按钮（内嵌在输入框右侧）
        add_btn = QPushButton("+")
        add_btn.setFixedSize(28, 28)
        add_btn.setToolTip("添加字段别名（用顿号分隔）")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PREMIUM_COLORS['gradient_blue_start']};
                color: white;
                border: none;
                border-radius: 14px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {PREMIUM_COLORS['gradient_blue_end']};
            }}
            QPushButton:pressed {{
                background: #4338ca;
            }}
        """)
        add_btn.clicked.connect(lambda: self._add_field_alias(input_field))
        
        # 将加号按钮定位在输入框内部右侧
        add_btn.setParent(input_container)
        add_btn.raise_()
        
        # 更新按钮位置
        def update_add_btn_pos():
            add_btn.move(input_container.width() - 34, (input_container.height() - 28) // 2)
        
        # 监听容器大小变化
        input_container.resizeEvent = lambda e: update_add_btn_pos()
        
        layout.addWidget(input_container)
        container.input = input_field
        return container
    
    def _add_field_alias(self, input_field):
        """添加字段别名"""
        dialog = QDialog(self)
        dialog.setWindowTitle("添加字段别名")
        dialog.setFixedWidth(400)
        dialog.setStyleSheet(f"""
            QDialog {{ background: {PREMIUM_COLORS['surface']}; }}
            QLabel {{ color: {PREMIUM_COLORS['text_body']}; font-size: 13px; }}
            QLineEdit {{ 
                padding: 10px 12px; 
                border: 2px solid {PREMIUM_COLORS['gradient_blue_start']}; 
                border-radius: 8px; 
                font-size: 14px;
                background: white;
            }}
            QLineEdit:focus {{ border-color: {PREMIUM_COLORS['gradient_blue_end']}; }}
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        label = QLabel("请输入新的字段名（将用顿号拼接到现有字段名后）：")
        label.setWordWrap(True)
        layout.addWidget(label)
        
        alias_input = QLineEdit()
        alias_input.setPlaceholderText("输入字段别名，如：电话、联系方式")
        layout.addWidget(alias_input)
        
        # 当前值预览
        current_text = input_field.text().strip()
        if current_text:
            preview_label = QLabel(f"当前值: {current_text}")
            preview_label.setStyleSheet(f"color: {PREMIUM_COLORS['text_hint']}; font-size: 12px;")
            layout.addWidget(preview_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(80, 36)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PREMIUM_COLORS['background']};
                color: {PREMIUM_COLORS['text_body']};
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {PREMIUM_COLORS['border_light']}; }}
        """)
        cancel_btn.clicked.connect(dialog.reject)
        
        ok_btn = QPushButton("确定")
        ok_btn.setFixedSize(80, 36)
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 {PREMIUM_COLORS['gradient_blue_start']}, 
                    stop:1 {PREMIUM_COLORS['gradient_blue_end']});
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
        """)
        ok_btn.clicked.connect(dialog.accept)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)
        
        alias_input.setFocus()
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            text = alias_input.text().strip()
            if text:
                current_text = input_field.text().strip()
                if current_text:
                    new_text = f"{current_text}、{text}"
                else:
                    new_text = text
                input_field.setText(new_text)

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
        self.category_filter.blockSignals(True)
        self.category_filter.model().blockSignals(True)
        self.category_filter.addItems(["全部"])
        self.category_filter.model().blockSignals(False)
        self.category_filter.blockSignals(False)
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
        
        # 自定义字段列表
        self.field_list = FieldListWidget()
        self.field_list.push_field.connect(self.push_to_user)
        self.field_list.edit_field.connect(self.edit_field)
        self.field_list.toggle_field.connect(self.toggle_field_status)
        
        card_layout.addWidget(self.field_list, 1)
        
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
        self.category_filter.model().blockSignals(True)
        self.category_filter.clear()
        cats = self.db_manager.get_field_library_categories()
        self.category_filter.addItems(["全部"] + cats)
        self.category_filter.setCurrentText(current if current in cats or current == "全部" else "全部")
        self.category_filter.model().blockSignals(False)
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
        
        self.field_list.set_fields(fields)
        self.update_pagination()
        
    def push_to_user(self, field):
        """推送字段到用户 - 行组件信号处理"""
        current_user = None
        parent = self.window()
        if hasattr(parent, 'current_user'):
            current_user = parent.current_user
            
        dialog = PushToUserDialog(field, self.db_manager, current_user, self)
        dialog.exec()
    
    def edit_field(self, field):
        """编辑字段 - 行组件信号处理"""
        self.show_add_dialog(field)
    
    def toggle_field_status(self, field):
        """切换字段状态 - 行组件信号处理"""
        self.toggle_status(field)
            
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
