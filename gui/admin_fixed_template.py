"""
固定模板管理模块
用于管理员维护系统级固定模板（字段名+字段值）
采用现代化玻璃拟态设计风格，使用自定义列表组件
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QMessageBox, QLineEdit, QFrame, QScrollArea,
    QDialog, QComboBox, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from database import DatabaseManager, FixedTemplate
from gui.admin_base_components import (
    PREMIUM_COLORS, GlassFrame, GradientButton, CompactStatWidget,
    BaseListHeader, BaseRowWidget, BaseListWidget, 
    create_action_button
)

# 固定模板列表列宽配置
TEMPLATE_LIST_COLUMNS = {
    'field_name': 180,
    'field_value': 200,
    'category': 100,
    'description': 150,
    'order': 60,
    'status': 80,
    'actions': 140
}


class TemplateListHeader(BaseListHeader):
    """固定模板列表头部"""
    
    def __init__(self, parent=None):
        columns = [
            ('字段名', TEMPLATE_LIST_COLUMNS['field_name']),
            ('字段值', TEMPLATE_LIST_COLUMNS['field_value']),
            ('分类', TEMPLATE_LIST_COLUMNS['category']),
            ('说明', TEMPLATE_LIST_COLUMNS['description']),
            ('排序', TEMPLATE_LIST_COLUMNS['order']),
            ('状态', TEMPLATE_LIST_COLUMNS['status']),
            ('操作', TEMPLATE_LIST_COLUMNS['actions'])
        ]
        super().__init__(columns, parent)


class TemplateRowWidget(BaseRowWidget):
    """固定模板行组件"""
    
    edit_clicked = pyqtSignal(object)
    toggle_clicked = pyqtSignal(object)
    
    def __init__(self, template, parent=None):
        super().__init__(parent)
        self.template = template
        self._setup_content()
        
    def _setup_content(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        # 1. 字段名
        name_label = QLabel(self.template.field_name)
        name_label.setFixedWidth(TEMPLATE_LIST_COLUMNS['field_name'])
        name_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        name_label.setStyleSheet(f"color: {PREMIUM_COLORS['text_heading']};")
        name_label.setWordWrap(True)
        layout.addWidget(name_label)
        
        # 2. 字段值
        value_text = self.template.field_value or '-'
        if len(value_text) > 25:
            value_text = value_text[:25] + '...'
        value_label = QLabel(value_text)
        value_label.setFixedWidth(TEMPLATE_LIST_COLUMNS['field_value'])
        value_label.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-size: 13px;")
        value_label.setToolTip(self.template.field_value or '')
        layout.addWidget(value_label)
        
        # 3. 分类
        cat_container = QWidget()
        cat_container.setFixedWidth(TEMPLATE_LIST_COLUMNS['category'])
        cat_layout = QHBoxLayout(cat_container)
        cat_layout.setContentsMargins(0, 0, 0, 0)
        cat_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        cat_label = QLabel(self.template.category or '通用')
        cat_label.setStyleSheet(f"""
            background: {PREMIUM_COLORS['text_hint']}15;
            color: {PREMIUM_COLORS['text_body']};
            border-radius: 10px;
            padding: 4px 8px;
            font-size: 11px;
            font-weight: 500;
        """)
        cat_layout.addWidget(cat_label)
        cat_layout.addStretch()
        layout.addWidget(cat_container)
        
        # 4. 说明
        desc_text = self.template.description or '-'
        if len(desc_text) > 15:
            desc_text = desc_text[:15] + '...'
        desc_label = QLabel(desc_text)
        desc_label.setFixedWidth(TEMPLATE_LIST_COLUMNS['description'])
        desc_label.setStyleSheet(f"color: {PREMIUM_COLORS['text_hint']}; font-size: 12px;")
        desc_label.setToolTip(self.template.description or '')
        layout.addWidget(desc_label)
        
        # 5. 排序
        order_label = QLabel(str(self.template.order))
        order_label.setFixedWidth(TEMPLATE_LIST_COLUMNS['order'])
        order_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        order_label.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-size: 12px;")
        layout.addWidget(order_label)
        
        # 6. 状态
        status_container = QWidget()
        status_container.setFixedWidth(TEMPLATE_LIST_COLUMNS['status'])
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        status_label = QLabel()
        if self.template.is_active:
            status_label.setText("✅ 启用")
            status_label.setStyleSheet("""
                color: #059669; 
                background: #ecfdf5; 
                padding: 4px 8px; 
                border-radius: 6px; 
                font-size: 11px; 
                font-weight: 600;
            """)
        else:
            status_label.setText("⛔ 禁用")
            status_label.setStyleSheet("""
                color: #dc2626; 
                background: #fef2f2; 
                padding: 4px 8px; 
                border-radius: 6px; 
                font-size: 11px; 
                font-weight: 600;
            """)
        status_layout.addWidget(status_label)
        status_layout.addStretch()
        layout.addWidget(status_container)
        
        # 7. 操作
        actions_container = QWidget()
        actions_container.setFixedWidth(TEMPLATE_LIST_COLUMNS['actions'])
        actions_layout = QHBoxLayout(actions_container)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(8)
        actions_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        # 编辑按钮
        edit_btn = create_action_button(
            "编辑", 
            PREMIUM_COLORS['gradient_blue_start'],
            size=(50, 26)
        )
        edit_btn.clicked.connect(lambda: self.edit_clicked.emit(self.template))
        actions_layout.addWidget(edit_btn)
        
        # 启用/禁用按钮
        if self.template.is_active:
            toggle_btn = create_action_button(
                "禁用",
                PREMIUM_COLORS['coral'],
                size=(50, 26)
            )
        else:
            toggle_btn = create_action_button(
                "启用",
                PREMIUM_COLORS['gradient_green_start'],
                size=(50, 26)
            )
        toggle_btn.clicked.connect(lambda: self.toggle_clicked.emit(self.template))
        actions_layout.addWidget(toggle_btn)
        
        actions_layout.addStretch()
        layout.addWidget(actions_container)
        
        layout.addStretch()


class TemplateListWidget(BaseListWidget):
    """固定模板列表组件"""
    
    edit_template = pyqtSignal(object)
    toggle_template = pyqtSignal(object)
        
    def __init__(self, parent=None):
        super().__init__(TemplateListHeader, parent)
        
    def set_templates(self, templates):
        """设置模板列表"""
        self.clear_rows()
        
        if not templates:
            self._show_empty_state("暂无固定模板")
            return
            
        for template in templates:
            row = TemplateRowWidget(template)
            row.edit_clicked.connect(self.edit_template.emit)
            row.toggle_clicked.connect(self.toggle_template.emit)
            self.add_row(row)


class AddTemplateDialog(QDialog):
    """添加/编辑固定模板对话框"""
    
    def __init__(self, parent=None, template=None, db_manager=None, current_user=None):
        super().__init__(parent)
        self.template = template
        self.db_manager = db_manager or DatabaseManager()
        self.current_user = current_user
        self.init_ui()
        
    def init_ui(self):
        title = "编辑模板" if self.template else "添加模板"
        self.setWindowTitle(title)
        self.setFixedSize(550, 620)
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
        self.name_input = self._create_input_field("字段名称", "支持别名，用顿号分隔 (e.g. 手机号、电话、联系方式)")
        form_layout.addWidget(self.name_input)
        
        # 字段值
        value_container = QWidget()
        value_layout = QVBoxLayout(value_container)
        value_layout.setContentsMargins(0, 0, 0, 0)
        value_layout.setSpacing(6)
        
        value_label = QLabel("字段值 (选填)")
        value_label.setStyleSheet(f"font-weight: 600; color: {PREMIUM_COLORS['text_body']};")
        value_layout.addWidget(value_label)
        
        self.value_input = QTextEdit()
        self.value_input.setPlaceholderText("填写固定的字段值 (选填)...")
        self.value_input.setMinimumHeight(80)
        self.value_input.setMaximumHeight(120)
        self.value_input.setStyleSheet(f"""
            QTextEdit {{
                padding: 10px;
                border: 1px solid {PREMIUM_COLORS['border_light']};
                border-radius: 8px;
                background: #f8fafc;
                font-size: 13px;
            }}
            QTextEdit:focus {{
                border: 1px solid {PREMIUM_COLORS['primary']};
                background: white;
            }}
        """)
        value_layout.addWidget(self.value_input)
        form_layout.addWidget(value_container)
        
        # 分类
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        # 获取现有分类
        existing_cats = self.db_manager.get_fixed_template_categories()
        default_cats = ['通用', '基本信息', '平台数据', '小红书', '抖音', '微博', '快手', '收货信息']
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
        
        # 占位提示
        self.placeholder_input = self._create_input_field("占位提示", "用户添加名片时的输入提示（选填）")
        form_layout.addWidget(self.placeholder_input)
        
        # 说明
        self.desc_input = self._create_input_field("说明", "模板用途说明（选填）")
        form_layout.addWidget(self.desc_input)
        
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
        if self.template:
            self.name_input.input.setText(self.template.field_name)
            self.value_input.setText(self.template.field_value)
            self.category_combo.setCurrentText(self.template.category)
            self.placeholder_input.input.setText(self.template.placeholder or '')
            self.desc_input.input.setText(self.template.description or '')
            self.order_input.input.setText(str(self.template.order))
            
    def _create_input_field(self, label_text, placeholder="", default_val=""):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
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
        field_name = self.name_input.input.text().strip()
        field_value = self.value_input.toPlainText().strip()
        
        if not field_name:
            QMessageBox.warning(self, "提示", "请输入字段名称")
            return
            
        try:
            order = int(self.order_input.input.text().strip() or "0")
        except ValueError:
            order = 0
            
        data = {
            'field_name': field_name,
            'field_value': field_value,
            'placeholder': self.placeholder_input.input.text().strip(),
            'category': self.category_combo.currentText().strip() or '通用',
            'description': self.desc_input.input.text().strip(),
            'order': order
        }
        
        try:
            if self.template:
                self.db_manager.update_fixed_template(str(self.template.id), **data)
            else:
                self.db_manager.create_fixed_template(
                    created_by=self.current_user,
                    **data
                )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")


class AdminFixedTemplateManager(QWidget):
    """管理员固定模板管理页面"""
    
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
        title_label = QLabel("固定模板管理")
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
            ("总模板数", 0, "📋", PREMIUM_COLORS['gradient_purple_start'], PREMIUM_COLORS['gradient_purple_end']),
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
        add_btn = QPushButton("添加模板")
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
        self.search_input.setPlaceholderText("搜索字段名或字段值...")
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
        
        # 自定义模板列表（替代表格）
        self.template_list = TemplateListWidget()
        self.template_list.edit_template.connect(self.show_add_dialog)
        self.template_list.toggle_template.connect(self.toggle_status)
        card_layout.addWidget(self.template_list, 1)
        
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
        cats = self.db_manager.get_fixed_template_categories()
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
        if category == "全部":
            category = None
        
        search_text = self.search_input.text().strip().lower()
        
        all_templates = self.db_manager.get_all_fixed_templates(category=category, is_active=None)
        
        # Client-side filtering for search
        if search_text:
            all_templates = [t for t in all_templates 
                          if search_text in t.field_name.lower() 
                          or search_text in (t.field_value or '').lower()
                          or search_text in (t.description or '').lower()]
            
        # Update Stats
        total_count = len(all_templates)
        enabled_count = sum(1 for t in all_templates if t.is_active)
        
        if "总模板数" in self.stat_widgets:
            self.stat_widgets["总模板数"].update_value(total_count)
        if "已启用" in self.stat_widgets:
            self.stat_widgets["已启用"].update_value(enabled_count)
            
        # Pagination
        self.total_records = total_count
        self.total_pages = max(1, (self.total_records + self.page_size - 1) // self.page_size)
        
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
            
        start_idx = (self.current_page - 1) * self.page_size
        end_idx = start_idx + self.page_size
        templates = all_templates[start_idx:end_idx]
        
        # 使用自定义列表组件显示数据
        self.template_list.set_templates(templates)
        self.update_pagination()
            
    def show_add_dialog(self, template=None):
        # 获取当前主窗口的用户信息
        current_user = None
        parent = self.window()
        if hasattr(parent, 'current_user'):
            current_user = parent.current_user
            
        dialog = AddTemplateDialog(self, template, self.db_manager, current_user)
        if dialog.exec():
            self.refresh_categories()  # 分类可能更新
            self.load_data()
            
    def toggle_status(self, template):
        try:
            new_status = not template.is_active
            self.db_manager.update_fixed_template(template_id=str(template.id), is_active=new_status)
            self.load_data()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"操作失败: {str(e)}")
