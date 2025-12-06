"""
主窗口 - 左侧边栏布局
"""
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QTableWidget, QTableWidgetItem,
                             QMessageBox, QHeaderView, QFrame, QSpacerItem, QSizePolicy,
                             QGraphicsDropShadowEffect, QScrollArea, QCheckBox, 
                             QListWidget, QListWidgetItem, QGridLayout, QDialog, QLineEdit,
                             QTabWidget, QComboBox, QInputDialog, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize, QPoint, QTimer
from PyQt6.QtGui import QFont, QColor, QAction
import qtawesome as qta
from database import DatabaseManager
from .card_manager import CardManagerDialog
from .card_edit_approval import MessageCenterDialog
from .link_manager import LinkManagerDialog
from .auto_fill_window import AutoFillWindow
from .new_fill_window import NewFillWindow
from .admin_main_window import AdminMainWindow as AdminWindow
from .notice_plaza_window import NoticePlazaWindow
from .styles import GLOBAL_STYLE, COLORS, get_card_button_style, get_stats_card_style, get_title_style, get_subtitle_style
from .icons import Icons
import config
from collections import defaultdict
from database.models import SystemConfig

# 首页记录列表列宽配置
HOME_RECORD_COLUMNS = {
    'time': 140,
    'card': 160,
    'link': 220,
    'total': 70,
    'success': 70,
    'status': 70
}


class HomeRecordListHeader(QFrame):
    """首页记录列表表头"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setStyleSheet("""
            QFrame {
                background: white;
                border: none;
                border-bottom: 2px solid #F5F5F7;
            }
        """)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(12)
        
        columns = [
            ('时间', HOME_RECORD_COLUMNS['time']),
            ('名片', HOME_RECORD_COLUMNS['card']),
            ('链接', HOME_RECORD_COLUMNS['link']),
            ('填写字段', HOME_RECORD_COLUMNS['total']),
            ('成功数', HOME_RECORD_COLUMNS['success']),
            ('状态', HOME_RECORD_COLUMNS['status'])
        ]
        
        for name, width in columns:
            label = QLabel(name)
            label.setFixedWidth(width)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("""
                font-weight: 700;
                color: #86868B;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            """)
            layout.addWidget(label)
        
        layout.addStretch()


class HomeRecordRowWidget(QFrame):
    """首页记录行组件"""
    
    def __init__(self, record, parent=None):
        super().__init__(parent)
        self.record = record
        self.setFixedHeight(56)
        self.setStyleSheet("""
            HomeRecordRowWidget {
                background: white;
                border: none;
                border-bottom: 1px solid #FAFAFA;
            }
            HomeRecordRowWidget:hover {
                background: #F9FAFB;
            }
        """)
        self._setup_content()
        
    def _setup_content(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(12)
        
        # 1. 时间
        time_text = self.record.created_at.strftime("%Y-%m-%d %H:%M")
        time_label = QLabel(time_text)
        time_label.setFixedWidth(HOME_RECORD_COLUMNS['time'])
        time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_label.setStyleSheet("color: #86868B; font-size: 13px;")
        layout.addWidget(time_label)
        
        # 2. 名片
        card_name = "未知名片"
        try:
            if self.record.card:
                card_name = self.record.card.name
        except Exception:
            card_name = "名片已删除"
        
        card_label = QLabel(card_name)
        card_label.setFixedWidth(HOME_RECORD_COLUMNS['card'])
        card_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_label.setStyleSheet("color: #1D1D1F; font-size: 13px; font-weight: 500;")
        card_label.setToolTip(card_name)
        # 文本截断
        font_metrics = card_label.fontMetrics()
        elided = font_metrics.elidedText(card_name, Qt.TextElideMode.ElideRight, HOME_RECORD_COLUMNS['card'] - 10)
        card_label.setText(elided)
        layout.addWidget(card_label)
        
        # 3. 链接
        link_name = "未知链接"
        try:
            if self.record.link:
                link_name = self.record.link.name
        except Exception:
            link_name = "链接已删除"
        
        link_label = QLabel(link_name)
        link_label.setFixedWidth(HOME_RECORD_COLUMNS['link'])
        link_label.setStyleSheet("color: #007AFF; font-size: 13px;")
        link_label.setToolTip(link_name)
        # 文本截断
        elided = font_metrics.elidedText(link_name, Qt.TextElideMode.ElideRight, HOME_RECORD_COLUMNS['link'] - 10)
        link_label.setText(elided)
        layout.addWidget(link_label)
        
        # 4. 填写字段
        total_label = QLabel(str(self.record.total_count))
        total_label.setFixedWidth(HOME_RECORD_COLUMNS['total'])
        total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        total_label.setStyleSheet("color: #1D1D1F; font-size: 13px;")
        layout.addWidget(total_label)
        
        # 5. 成功数
        success_label = QLabel(str(self.record.fill_count))
        success_label.setFixedWidth(HOME_RECORD_COLUMNS['success'])
        success_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_label.setStyleSheet("color: #1D1D1F; font-size: 13px;")
        layout.addWidget(success_label)
        
        # 6. 状态
        status_container = QWidget()
        status_container.setFixedWidth(HOME_RECORD_COLUMNS['status'])
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        status_label = QLabel()
        if self.record.success:
            status_label.setText("✅ 成功")
            status_label.setStyleSheet("""
                color: #059669; 
                background: #ecfdf5; 
                padding: 4px 10px; 
                border-radius: 12px; 
                font-size: 12px; 
                font-weight: 600;
            """)
        else:
            status_label.setText("❌ 失败")
            status_label.setStyleSheet("""
                color: #dc2626; 
                background: #fef2f2; 
                padding: 4px 10px; 
                border-radius: 12px; 
                font-size: 12px; 
                font-weight: 600;
            """)
        status_layout.addWidget(status_label)
        layout.addWidget(status_container)
        
        layout.addStretch()


class HomeRecordListWidget(QWidget):
    """首页记录列表组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 表头
        self.header = HomeRecordListHeader()
        layout.addWidget(self.header)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background: white;
                border: none;
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #E5E5EA;
                border-radius: 3px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # 行容器
        self.rows_container = QWidget()
        self.rows_container.setStyleSheet("background: white;")
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(0)
        self.rows_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll.setWidget(self.rows_container)
        layout.addWidget(scroll, 1)
        
        # 空状态标签
        self.empty_label = None
        
    def clear_rows(self):
        """清空所有行"""
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if self.empty_label:
            self.empty_label.deleteLater()
            self.empty_label = None
            
    def _show_empty_state(self, message="暂无数据"):
        """显示空状态"""
        self.empty_label = QLabel(message)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("""
            color: #86868B;
            font-size: 14px;
            padding: 60px;
        """)
        self.rows_layout.addWidget(self.empty_label)
        
    def set_records(self, records):
        """设置记录列表"""
        self.clear_rows()
        
        if not records:
            self._show_empty_state("暂无填写记录\n选择名片和链接后开始自动填写")
            return
            
        for record in records:
            row = HomeRecordRowWidget(record)
            self.rows_layout.addWidget(row)
        
        # 添加弹性空间
        self.rows_layout.addStretch()


class MultiCardFillWindow(QMainWindow):
    """多名片填充窗口 - 多对多关系"""
    
    def __init__(self, selected_cards, selected_links, parent=None):
        super().__init__(parent)
        self.selected_cards = selected_cards
        self.selected_links = selected_links
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("开始填充")
        self.setGeometry(100, 100, 1400, 900)
        
        # 主容器
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        central_widget.setLayout(main_layout)
        
        # 设置背景色
        self.setStyleSheet("""
            QMainWindow {
                background: #F5F7FA;
            }
        """)
        
        # 顶部：链接选项卡
        link_tabs = QTabWidget()
        link_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                background: white;
            }
            QTabBar::tab {
                background: #F3F4F6;
                border: 1px solid #E5E7EB;
                padding: 12px 24px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                color: #6B7280;
            }
            QTabBar::tab:selected {
                background: white;
                color: #1F2937;
                border-bottom-color: white;
            }
            QTabBar::tab:hover {
                background: #E5E7EB;
            }
        """)
        
        # 为每个链接创建选项卡
        for link in self.selected_links:
            tab_widget = QWidget()
            tab_layout = QVBoxLayout()
            tab_layout.setContentsMargins(20, 20, 20, 20)
            tab_widget.setLayout(tab_layout)
            
            # 链接信息
            link_label = QLabel(f"链接: {link.name}")
            link_label.setStyleSheet("""
                font-size: 16px;
                font-weight: 600;
                color: #1F2937;
                padding: 10px;
            """)
            tab_layout.addWidget(link_label)
            
            # 创建水平滚动区域，包含所有名片窗口
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            scroll_area.setStyleSheet("""
                QScrollArea {
                    border: none;
                    background: transparent;
                }
            """)
            
            # 名片容器
            cards_container = QWidget()
            cards_layout = QHBoxLayout()
            cards_layout.setContentsMargins(0, 0, 0, 0)
            cards_layout.setSpacing(16)
            cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            cards_container.setLayout(cards_layout)
            
            # 为每个名片创建一个窗口
            for card in self.selected_cards:
                card_window = self.create_card_window(card, link)
                cards_layout.addWidget(card_window)
            
            scroll_area.setWidget(cards_container)
            tab_layout.addWidget(scroll_area)
            
            # 添加选项卡
            link_tabs.addTab(tab_widget, link.name)
        
        main_layout.addWidget(link_tabs)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        start_btn = QPushButton("开始填充")
        start_btn.setFixedSize(140, 44)
        start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #10B981, stop:1 #059669);
                border: none;
                border-radius: 8px;
                color: white;
                font-size: 15px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #059669, stop:1 #047857);
            }
            QPushButton:pressed {
                background: #047857;
            }
        """)
        button_layout.addWidget(start_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.setFixedSize(140, 44)
        close_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFFFFF, stop:1 #F3F4F6);
                border: 1.5px solid #E5E7EB;
                border-radius: 8px;
                color: #6B7280;
                font-size: 15px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F9FAFB, stop:1 #E5E7EB);
                border-color: #9CA3AF;
            }
            QPushButton:pressed {
                background: #E5E7EB;
            }
        """)
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        main_layout.addLayout(button_layout)
    
    def create_card_window(self, card, link):
        """创建单个名片窗口"""
        window = QFrame()
        window.setMinimumWidth(300)
        window.setMaximumWidth(350)
        window.setStyleSheet("""
            QFrame {
                background: white;
                border: 1.5px solid #E5E7EB;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        window.setLayout(layout)
        
        # 名片标题
        title = QLabel(card.name)
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: 700;
            color: #1F2937;
            padding-bottom: 8px;
            border-bottom: 2px solid #E5E7EB;
        """)
        layout.addWidget(title)
        
        # 解析并显示字段
        if hasattr(card, 'configs') and card.configs:
            import json
            try:
                if isinstance(card.configs, str):
                    configs = json.loads(card.configs)
                else:
                    configs = card.configs
                
                for config in configs:
                    if isinstance(config, dict):
                        field_widget = self.create_field_widget(
                            config.get('key', ''),
                            config.get('value', '')
                        )
                        layout.addWidget(field_widget)
            except Exception as e:
                print(f"解析配置失败: {e}")
        
        layout.addStretch()
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 4)
        window.setGraphicsEffect(shadow)
        
        return window
    
    def create_field_widget(self, key, value):
        """创建字段组件"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        widget.setLayout(layout)
        
        # 字段名标签
        key_label = QLabel(key)
        key_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 600;
            color: #6B7280;
        """)
        layout.addWidget(key_label)
        
        # 字段值输入框
        value_input = QLineEdit()
        value_input.setText(value)
        value_input.setStyleSheet("""
            QLineEdit {
                padding: 10px 12px;
                border: 1.5px solid #E5E7EB;
                border-radius: 6px;
                font-size: 14px;
                background: #F9FAFB;
                color: #1F2937;
            }
            QLineEdit:focus {
                border: 1.5px solid #3B82F6;
                background: white;
            }
            QLineEdit:hover {
                border-color: #9CA3AF;
            }
        """)
        layout.addWidget(value_input)
        
        return widget


class AddCategoryDialog(QDialog):
    """新增分类对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.category_name = None
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("新增分类")
        self.setFixedSize(400, 220)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        self.setLayout(layout)
        
        # 标题
        title = QLabel("分类名称")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #1D1D1F;")
        layout.addWidget(title)
        
        # 输入框
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("请输入分类名称")
        self.input_field.setMinimumHeight(44)
        self.input_field.setStyleSheet("""
            QLineEdit {
                padding: 0 15px;
                border: 1.5px solid #E5E7EB;
                border-radius: 8px;
                font-size: 14px;
                background: #F9FAFB;
            }
            QLineEdit:focus {
                border-color: #007AFF;
                background: white;
            }
        """)
        layout.addWidget(self.input_field)
        
        layout.addStretch()
        
        # 按钮组
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(100, 40)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #F3F4F6;
                border: none;
                border-radius: 8px;
                color: #4B5563;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover { background: #E5E7EB; }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("保存")
        save_btn.setFixedSize(100, 40)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background: #007AFF;
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover { background: #0062CC; }
        """)
        save_btn.clicked.connect(self.save_category)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        
        self.setStyleSheet("QDialog { background: white; }")
    
    def save_category(self):
        """保存分类"""
        category_name = self.input_field.text().strip()
        
        if not category_name:
            QMessageBox.warning(self, "提示", "请输入分类名称")
            return
        
        self.category_name = category_name
        self.accept()
    
    def get_category_name(self):
        """获取分类名称"""
        return self.category_name


class AddCardDialog(QDialog):
    """添加名片对话框"""
    
    def __init__(self, parent=None, db_manager=None, current_user=None, card=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_user = current_user
        self.card = card  # 编辑模式时传入的名片对象
        self.field_rows = []  # 存储字段行
        self.init_ui()
        
        # 如果是编辑模式，回显数据；否则加载固定模板
        if self.card:
            self.load_card_data()
        else:
            # 新增模式：加载固定模板作为默认配置
            self.load_fixed_templates()
    
    def init_ui(self):
        """初始化UI"""
        # 根据模式设置标题
        if self.card:
            self.setWindowTitle("编辑名片")
        else:
            self.setWindowTitle("添加名片")
        self.setFixedSize(820, 680)
        self.setModal(True)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(35, 35, 35, 35)
        main_layout.setSpacing(24)
        self.setLayout(main_layout)
        
        # 名片名称行
        name_layout = QHBoxLayout()
        name_layout.setSpacing(15)
        
        name_label = QLabel("名片名称")
        name_label.setFixedWidth(85)
        name_label.setStyleSheet("""
            font-size: 14px; 
            font-weight: 600; 
            color: #1D1D1F;
            padding-top: 4px;
        """)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入")
        self.name_input.setMinimumHeight(42)
        self.name_input.setStyleSheet("""
            QLineEdit {
                padding: 10px 15px;
                border: 1.5px solid #E5E5EA;
                border-radius: 8px;
                font-size: 14px;
                background: #FAFAFA;
            }
            QLineEdit:focus {
                border: 1.5px solid #007AFF;
                background: white;
            }
            QLineEdit:hover {
                border-color: #C7C7CC;
                background: white;
            }
        """)
        
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        main_layout.addLayout(name_layout)
        
        # 选择分类行
        category_layout = QHBoxLayout()
        category_layout.setSpacing(15)
        
        category_label = QLabel("选择分类")
        category_label.setFixedWidth(85)
        category_label.setStyleSheet("""
            font-size: 14px; 
            font-weight: 600; 
            color: #1D1D1F;
            padding-top: 4px;
        """)
        
        from PyQt6.QtWidgets import QComboBox
        self.category_combo = QComboBox()
        self.category_combo.setMinimumHeight(42)
        self.category_combo.setStyleSheet("""
            QComboBox {
                padding: 10px 15px;
                border: 1.5px solid #E5E5EA;
                border-radius: 8px;
                font-size: 14px;
                background: #FAFAFA;
            }
            QComboBox:hover {
                border-color: #C7C7CC;
                background: white;
            }
            QComboBox:focus {
                border: 1.5px solid #007AFF;
                background: white;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #666;
                width: 0;
                height: 0;
            }
        """)
        self.load_categories()
        
        # 右侧按钮
        import_template_btn = QPushButton("导入官方模版")
        import_template_btn.setMinimumHeight(42)
        import_template_btn.setStyleSheet(self.get_button_style())
        import_template_btn.clicked.connect(self.import_from_field_library)
        
        new_field_btn = QPushButton("新增字段")
        new_field_btn.setMinimumHeight(42)
        new_field_btn.setStyleSheet(self.get_button_style())
        new_field_btn.clicked.connect(lambda: self.add_field_row())
        
        category_layout.addWidget(category_label)
        category_layout.addWidget(self.category_combo, 1)
        category_layout.addWidget(import_template_btn)
        category_layout.addWidget(new_field_btn)
        main_layout.addLayout(category_layout)
        
        # 字段列表区域（带滚动）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        self.fields_container = QWidget()
        self.fields_layout = QVBoxLayout()
        self.fields_layout.setContentsMargins(0, 0, 0, 0)
        self.fields_layout.setSpacing(12)
        self.fields_container.setLayout(self.fields_layout)
        
        scroll.setWidget(self.fields_container)
        main_layout.addWidget(scroll, 1)
        
        # 不添加默认字段，让用户自己添加或从官方模版导入
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        button_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(130, 44)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFFFFF, stop:1 #F5F5F5);
                border: 1.5px solid #E5E5EA;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                color: #666;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F5F5F5, stop:1 #ECECEC);
                border-color: #C7C7CC;
                color: #333;
            }
            QPushButton:pressed {
                background: #E0E0E0;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("保存")
        save_btn.setFixedSize(130, 44)
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #007AFF, stop:1 #0062CC);
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                color: white;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0062CC, stop:1 #0051D5);
            }
            QPushButton:pressed {
                background: #0051A8;
            }
        """)
        save_btn.clicked.connect(self.save_card)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)
        main_layout.addLayout(button_layout)
        
        # 设置对话框样式
        self.setStyleSheet("""
            QDialog {
                background: #FFFFFF;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
        """)
    
    def get_button_style(self):
        """获取按钮样式"""
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #FFFFFF, stop:1 #F8F8F8);
                border: 1.5px solid #E5E5EA;
                border-radius: 8px;
                padding: 10px 18px;
                font-size: 13px;
                font-weight: 500;
                color: #1D1D1F;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F0F0F0, stop:1 #E8E8E8);
                border-color: #007AFF;
            }
            QPushButton:pressed {
                background: #E0E0E0;
                border-color: #0062CC;
            }
        """
    
    def load_categories(self):
        """加载分类列表"""
        self.category_combo.clear()
        
        # 从 Category 表获取用户的分类
        user_categories = self.db_manager.get_user_categories(self.current_user)
        
        # 同时从现有名片中获取分类（兼容旧数据）
        cards = self.db_manager.get_all_cards(user=self.current_user)
        card_categories = set()
        for card in cards:
            category = card.category if hasattr(card, 'category') and card.category else None
            if category:
                card_categories.add(category)
        
        # 合并所有分类（去重）
        all_categories = set()
        for cat in user_categories:
            all_categories.add(cat.name)
        all_categories.update(card_categories)
        
        # 添加到下拉框
        for category in sorted(all_categories):
            self.category_combo.addItem(category)
        
        # 如果没有分类，添加默认分类
        if self.category_combo.count() == 0:
            self.category_combo.addItem("默认分类")
    
    def add_field_row(self, key="", value="", fixed_template_id=None):
        """添加字段行"""
        # 创建可拖拽的行组件
        row_widget = DraggableFieldRow(key, value, self, fixed_template_id)
        
        # 添加到列表
        self.field_rows.append({
            'widget': row_widget,
            'key_input': row_widget.key_input,
            'value_input': row_widget.value_input,
            'drag_btn': row_widget.drag_btn,
            'fixed_template_id': fixed_template_id  # 存储固定模板ID
        })
        
        # 添加到布局
        self.fields_layout.addWidget(row_widget)
    
    def remove_field_row(self, row_widget):
        """删除字段行"""
        for row_data in self.field_rows:
            if row_data['widget'] == row_widget:
                self.field_rows.remove(row_data)
                row_widget.deleteLater()
                break
    
    def add_field_alias(self, key_input):
        """添加字段别名"""
        from PyQt6.QtWidgets import QInputDialog
        
        text, ok = QInputDialog.getText(
            self,
            "添加字段别名",
            "请输入新的字段名（将用顿号拼接到现有字段名后）:",
            QLineEdit.EchoMode.Normal
        )
        
        if ok and text.strip():
            current_text = key_input.text().strip()
            if current_text:
                new_text = f"{current_text}、{text.strip()}"
            else:
                new_text = text.strip()
            key_input.setText(new_text)
    
    def move_field_row(self, from_index, to_index):
        """移动字段行位置"""
        if from_index == to_index:
            return
        
        row_data = self.field_rows.pop(from_index)
        self.field_rows.insert(to_index, row_data)
        
        widget = row_data['widget']
        self.fields_layout.removeWidget(widget)
        self.fields_layout.insertWidget(to_index, widget)
    
    def import_from_field_library(self):
        """从官方字段库导入字段"""
        # 打开字段库选择对话框（简化版，只选字段不选名片）
        dialog = FieldLibraryImportDialog(self.db_manager, self)
        if dialog.exec():
            selected_fields = dialog.get_selected_fields()
            
            if selected_fields:
                # 获取当前已有的字段名（用于去重）
                existing_keys = set()
                for row in self.field_rows:
                    key = row['key_input'].text().strip().lower()
                    for name in key.split('、'):
                        existing_keys.add(name.strip().lower())
                
                added_count = 0
                skipped_count = 0
                
                for field in selected_fields:
                    # 检查是否重复
                    field_names = field.name.split('、')
                    is_duplicate = False
                    for name in field_names:
                        if name.strip().lower() in existing_keys:
                            is_duplicate = True
                            break
                    
                    if is_duplicate:
                        skipped_count += 1
                        continue
                    
                    # 添加字段行
                    self.add_field_row(field.name, field.default_value or '')
                    
                    # 更新已存在集合
                    for name in field_names:
                        existing_keys.add(name.strip().lower())
                    added_count += 1
                
                # 显示结果
                if added_count > 0:
                    msg = f"成功导入 {added_count} 个字段"
                    if skipped_count > 0:
                        msg += f"，跳过 {skipped_count} 个重复字段"
                    QMessageBox.information(self, "导入成功", msg)
                elif skipped_count > 0:
                    QMessageBox.warning(self, "提示", f"所选 {skipped_count} 个字段已存在，无需重复导入")
    
    def save_card(self):
        """保存名片"""
        name = self.name_input.text().strip()
        category = self.category_combo.currentText()
        
        if not name:
            QMessageBox.warning(self, "提示", "请输入名片名称")
            return
        
        # 收集字段（按顺序）
        configs = []
        print(f"DEBUG: 准备保存名片，当前字段行数: {len(self.field_rows)}")
        
        for i, row_data in enumerate(self.field_rows):
            try:
                key = row_data['key_input'].text().strip()
                value = row_data['value_input'].text().strip()
                print(f"  - 行 {i}: key='{key}', value='{value}'")
                
                if key:  # 只添加有字段名的
                    config = {"key": key, "value": value}
                    # 添加固定模板ID（如果有）
                    template_id = row_data.get('fixed_template_id')
                    if template_id:
                        config['fixed_template_id'] = template_id
                    configs.append(config)
            except RuntimeError:
                print(f"  - 行 {i}: 组件已被删除，跳过")
                continue
        
        print(f"DEBUG: 收集到的有效配置数: {len(configs)}")
        
        if not configs:
            QMessageBox.warning(self, "提示", "请至少添加一个字段")
            return
        
        # 保存到数据库
        try:
            if self.card:
                # 编辑模式：更新现有名片
                self.db_manager.update_card(
                    card_id=self.card.id,
                    name=name,
                    configs=configs,
                    category=category
                )
                QMessageBox.information(self, "成功", "名片更新成功！")
            else:
                # 添加模式：创建新名片
                self.db_manager.create_card(
                    name=name,
                    configs=configs,
                    user=self.current_user,
                    category=category
                )
                QMessageBox.information(self, "成功", "名片创建成功！")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "失败", f"保存名片失败：{str(e)}")
    
    def load_card_data(self):
        """加载名片数据（编辑模式）"""
        if not self.card:
            return
        
        print(f"DEBUG: 加载名片数据: {self.card.name}")
        
        # 回显名片名称
        self.name_input.setText(self.card.name)
        
        # 回显分类
        category = self.card.category if hasattr(self.card, 'category') and self.card.category else "默认分类"
        index = self.category_combo.findText(category)
        if index >= 0:
            self.category_combo.setCurrentIndex(index)
        
        # 清空现有字段（如果有）
        print(f"DEBUG: 清空现有字段，当前数量: {len(self.field_rows)}")
        while self.field_rows:
            row_data = self.field_rows[0]
            self.remove_field_row(row_data['widget'])
        
        # 回显字段配置
        if hasattr(self.card, 'configs') and self.card.configs:
            import json
            try:
                # 尝试解析configs
                if isinstance(self.card.configs, str):
                    configs = json.loads(self.card.configs)
                else:
                    configs = self.card.configs
                
                print(f"DEBUG: 解析出 {len(configs)} 个配置项")
                
                # 添加字段行
                for config in configs:
                    key = ""
                    value = ""
                    fixed_template_id = None
                    if isinstance(config, dict):
                        key = config.get('key', '')
                        value = config.get('value', '')
                        fixed_template_id = config.get('fixed_template_id')
                    elif hasattr(config, 'key'):  # 对象格式
                        key = config.key
                        value = getattr(config, 'value', '')
                        fixed_template_id = getattr(config, 'fixed_template_id', None)
                        
                    self.add_field_row(key, value, fixed_template_id)
            except Exception as e:
                print(f"解析配置失败: {e}")


    def load_fixed_templates(self):
        """加载固定模板到字段列表（新增名片时调用）"""
        try:
            templates = self.db_manager.get_all_fixed_templates(is_active=True)
            if templates:
                for template in templates:
                    self.add_field_row(
                        template.field_name,
                        template.field_value,
                        str(template.id)  # 固定模板ID
                    )
                print(f"DEBUG: 已加载 {len(templates)} 个固定模板")
            else:
                print("DEBUG: 没有可用的固定模板")
        except Exception as e:
            print(f"加载固定模板失败: {e}")


class DraggableFieldRow(QWidget):
    """可拖拽的字段行"""
    
    def __init__(self, key="", value="", parent_dialog=None, fixed_template_id=None):
        super().__init__()
        self.parent_dialog = parent_dialog
        self.dragging = False
        self.drag_start_pos = None
        self.fixed_template_id = fixed_template_id  # 固定模板ID，用户自己添加的为None
        self.init_ui(key, value)
    
    def init_ui(self, key, value):
        """初始化UI"""
        self.setStyleSheet("""
            DraggableFieldRow {
                background: #FAFAFA;
                border-radius: 10px;
                padding: 6px;
            }
        """)
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(10, 8, 10, 8)
        row_layout.setSpacing(12)
        self.setLayout(row_layout)
        
        # 字段名标签
        key_label = QLabel("字段名")
        key_label.setFixedWidth(60)
        key_label.setStyleSheet("""
            font-size: 13px; 
            color: #666;
            font-weight: 500;
        """)
        row_layout.addWidget(key_label)
        
        # 字段名输入
        self.key_input = QLineEdit()
        self.key_input.setText(key)
        self.key_input.setMinimumHeight(38)
        self.key_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 14px;
                border: 1.5px solid #E5E5EA;
                border-radius: 8px;
                font-size: 13px;
                background: white;
            }
            QLineEdit:focus {
                border: 1.5px solid #007AFF;
            }
            QLineEdit:hover {
                border-color: #C7C7CC;
            }
        """)
        row_layout.addWidget(self.key_input, 1)
        
        # 加号按钮
        add_btn = QPushButton()
        add_btn.setIcon(Icons.plus_circle('primary'))
        add_btn.setFixedSize(32, 32)
        add_btn.setToolTip("添加字段别名")
        add_btn.setStyleSheet("""
            QPushButton {
                background: white;
                border: 1.5px solid #E5E5EA;
                border-radius: 16px;
                padding: 4px;
            }
            QPushButton:hover {
                border-color: #007AFF;
                background: #F0F8FF;
            }
            QPushButton:pressed {
                background: #E0F0FF;
            }
        """)
        add_btn.clicked.connect(lambda: self.parent_dialog.add_field_alias(self.key_input))
        row_layout.addWidget(add_btn)
        
        # 字段值标签
        value_label = QLabel("字段值")
        value_label.setFixedWidth(60)
        value_label.setStyleSheet("""
            font-size: 13px; 
            color: #666;
            font-weight: 500;
        """)
        row_layout.addWidget(value_label)
        
        # 字段值输入
        self.value_input = QLineEdit()
        self.value_input.setText(value)
        self.value_input.setMinimumHeight(38)
        self.value_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 14px;
                border: 1.5px solid #E5E5EA;
                border-radius: 8px;
                font-size: 13px;
                background: white;
            }
            QLineEdit:focus {
                border: 1.5px solid #007AFF;
            }
            QLineEdit:hover {
                border-color: #C7C7CC;
            }
        """)
        row_layout.addWidget(self.value_input, 1)
        
        # 删除按钮
        delete_btn = QPushButton()
        delete_btn.setIcon(Icons.trash('danger'))
        delete_btn.setFixedSize(32, 32)
        delete_btn.setToolTip("删除此字段")
        delete_btn.setStyleSheet("""
            QPushButton {
                background: white;
                border: 1.5px solid #E5E5EA;
                border-radius: 8px;
                padding: 4px;
            }
            QPushButton:hover {
                background: #FFE5E5;
                border-color: #FF3B30;
            }
            QPushButton:pressed {
                background: #FFD0D0;
            }
        """)
        delete_btn.clicked.connect(lambda: self.parent_dialog.remove_field_row(self))
        row_layout.addWidget(delete_btn)
        
        # 拖动排序按钮
        self.drag_btn = QPushButton()
        self.drag_btn.setIcon(Icons.drag('gray'))
        self.drag_btn.setFixedSize(32, 32)
        self.drag_btn.setToolTip("按住拖动可调整字段顺序")
        self.drag_btn.setCursor(Qt.CursorShape.SizeVerCursor)
        self.drag_btn.setStyleSheet("""
            QPushButton {
                background: white;
                border: 1.5px solid #E5E5EA;
                border-radius: 8px;
                padding: 4px;
            }
            QPushButton:hover {
                background: #F0F0F0;
                border-color: #007AFF;
            }
            QPushButton:pressed {
                background: #E0E0E0;
            }
        """)
        self.drag_btn.setMouseTracking(True)
        self.drag_btn.installEventFilter(self)
        row_layout.addWidget(self.drag_btn)
    
    def eventFilter(self, obj, event):
        """事件过滤器 - 处理拖拽"""
        if obj == self.drag_btn:
            from PyQt6.QtCore import QEvent
            from PyQt6.QtGui import QMouseEvent
            
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.dragging = True
                    self.drag_start_pos = event.globalPosition().toPoint()
                    self.setStyleSheet("""
                        DraggableFieldRow {
                            background: #E3F2FD;
                            border: 2px solid #007AFF;
                            border-radius: 10px;
                            padding: 6px;
                        }
                    """)
                    return True
            
            elif event.type() == QEvent.Type.MouseMove:
                if self.dragging:
                    # 计算移动距离
                    delta = event.globalPosition().toPoint() - self.drag_start_pos
                    if abs(delta.y()) > 10:  # 移动超过10px才触发
                        self.handle_drag(delta.y())
                    return True
            
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if self.dragging:
                    self.dragging = False
                    self.setStyleSheet("""
                        DraggableFieldRow {
                            background: #FAFAFA;
                            border-radius: 10px;
                            padding: 6px;
                        }
                    """)
                    return True
        
        return super().eventFilter(obj, event)
    
    def handle_drag(self, delta_y):
        """处理拖拽移动"""
        if not self.parent_dialog:
            return
        
        # 获取当前索引
        current_index = None
        for i, row_data in enumerate(self.parent_dialog.field_rows):
            if row_data['widget'] == self:
                current_index = i
                break
        
        if current_index is None:
            return
        
        # 根据移动方向判断目标位置
        row_height = self.height()
        move_rows = delta_y // row_height
        
        if move_rows == 0:
            return
        
        target_index = current_index + move_rows
        target_index = max(0, min(target_index, len(self.parent_dialog.field_rows) - 1))
        
        if target_index != current_index:
            self.parent_dialog.move_field_row(current_index, target_index)
            self.drag_start_pos = self.drag_btn.mapToGlobal(self.drag_btn.rect().center())


class CollapsibleCategoryWidget(QWidget):
    """可折叠的分类组件 - 优化版"""
    
    category_clicked = pyqtSignal(str)
    rename_clicked = pyqtSignal(str)  # 重命名分类信号
    delete_clicked = pyqtSignal(str)  # 删除分类信号
    
    def __init__(self, category_name: str, parent=None):
        super().__init__(parent)
        self.category_name = category_name
        self.is_collapsed = False
        self.cards_container = None
        self.card_widgets = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 2)
        layout.setSpacing(0)
        self.setLayout(layout)
        
        # 分类标题栏 - 使用 QWidget 而不是 QPushButton
        header = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(8, 8, 8, 8)
        header_layout.setSpacing(8)
        header.setLayout(header_layout)
        header.setStyleSheet("""
            QWidget {
                background: transparent;
                border-radius: 6px;
            }
            QWidget:hover {
                background: #F2F2F7;
            }
        """)
        
        # 折叠按钮（箭头 + 名称）
        collapse_btn = QPushButton()
        collapse_btn_layout = QHBoxLayout()
        collapse_btn_layout.setContentsMargins(0, 0, 0, 0)
        collapse_btn_layout.setSpacing(8)
        collapse_btn.setLayout(collapse_btn_layout)
        collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        collapse_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                text-align: left;
            }
        """)
        collapse_btn.clicked.connect(self.toggle_collapse)
        
        # 箭头
        self.arrow_label = QLabel("▼")
        self.arrow_label.setStyleSheet("color: #8E8E93; font-size: 10px;")
        collapse_btn_layout.addWidget(self.arrow_label)
        
        # 分类名称
        self.name_label = QLabel(self.category_name)
        self.name_label.setStyleSheet("""
            font-size: 13px;
            font-weight: 600;
            color: #8E8E93;
        """)
        collapse_btn_layout.addWidget(self.name_label)
        
        header_layout.addWidget(collapse_btn)
        header_layout.addStretch()
        
        # 编辑按钮
        edit_btn = QPushButton()
        edit_btn.setIcon(qta.icon('fa5s.edit', color='#8E8E93'))
        edit_btn.setFixedSize(24, 24)
        edit_btn.setToolTip("重命名分类")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #E5E5EA;
            }
        """)
        edit_btn.clicked.connect(lambda: self.rename_clicked.emit(self.category_name))
        header_layout.addWidget(edit_btn)
        
        # 删除按钮
        delete_btn = QPushButton()
        delete_btn.setIcon(qta.icon('fa5s.trash', color='#FF3B30'))
        delete_btn.setFixedSize(24, 24)
        delete_btn.setToolTip("删除分类")
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #FFE5E5;
            }
        """)
        delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self.category_name))
        header_layout.addWidget(delete_btn)
        
        # 复选框
        self.category_checkbox = QCheckBox()
        self.category_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.category_checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 16px; height: 16px;
                border-radius: 4px;
                border: 1px solid #D1D1D6;
                background: white;
            }
            QCheckBox::indicator:checked {
                background: #007AFF; border-color: #007AFF;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEgNEw0LjUgNy41TDExIDEiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+PC9zdmc+);
            }
        """)
        self.category_checkbox.stateChanged.connect(self.on_category_checkbox_changed)
        header_layout.addWidget(self.category_checkbox)
        
        layout.addWidget(header)
        
        # 内容容器
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout()
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(0)
        self.cards_container.setLayout(self.cards_layout)
        layout.addWidget(self.cards_container)

    def set_content_widget(self, widget):
        """设置内容组件"""
        if self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.cards_layout.addWidget(widget)
    
    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        self.cards_container.setVisible(not self.is_collapsed)
        self.arrow_label.setText("▶" if self.is_collapsed else "▼")
    
    def on_category_checkbox_changed(self, state):
        is_checked = (state == Qt.CheckState.Checked.value)
        for card_widget in self.card_widgets:
            card_widget.set_selected(is_checked)
            card_widget.selection_changed.emit(card_widget.card, is_checked)
    
    def update_category_name(self, new_name: str):
        """更新分类名称显示"""
        self.category_name = new_name
        self.name_label.setText(new_name)


class DraggableCardGrid(QWidget):
    """支持拖拽排序的名片宫格容器 - 带动画效果"""
    
    order_changed = pyqtSignal(list)  # 排序改变信号，传递 [(card_id, new_order), ...]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.card_widgets = []
        self.dragged_widget = None
        self.dragged_card_id = None
        self.current_placeholder_index = -1  # 当前占位符位置
        self.animations = []  # 存储动画对象
        
        self.MAX_COLUMNS = 4
        self.CARD_SIZE = 88
        self.SPACING = 8
        self.MARGIN = 8
        
        self.setAcceptDrops(True)
        self.setStyleSheet("background: transparent;")
        self.setMinimumHeight(self.CARD_SIZE + self.MARGIN * 2)
    
    def add_card_widget(self, card_widget):
        """添加名片组件"""
        card_widget.setParent(self)
        self.card_widgets.append(card_widget)
        self._update_positions(animate=False)
        self._update_height()
    
    def _get_position_for_index(self, index):
        """根据索引计算位置"""
        row = index // self.MAX_COLUMNS
        col = index % self.MAX_COLUMNS
        x = self.MARGIN + col * (self.CARD_SIZE + self.SPACING)
        y = self.MARGIN + row * (self.CARD_SIZE + self.SPACING)
        return QPoint(x, y)
    
    def _update_height(self):
        """更新容器高度"""
        if not self.card_widgets:
            self.setMinimumHeight(self.CARD_SIZE + self.MARGIN * 2)
            return
        rows = (len(self.card_widgets) + self.MAX_COLUMNS - 1) // self.MAX_COLUMNS
        height = self.MARGIN * 2 + rows * self.CARD_SIZE + (rows - 1) * self.SPACING
        self.setMinimumHeight(height)
    
    def _update_positions(self, animate=True, skip_widget=None, placeholder_index=-1):
        """更新所有卡片位置，可选动画效果"""
        # 停止之前的动画
        for anim in self.animations:
            anim.stop()
        self.animations.clear()
        
        # 计算每个卡片的目标位置
        visual_index = 0
        for i, widget in enumerate(self.card_widgets):
            if widget == skip_widget:
                continue  # 跳过正在拖拽的卡片
            
            # 如果有占位符，在占位符位置之后的卡片需要后移一位
            target_index = visual_index
            if placeholder_index >= 0 and visual_index >= placeholder_index:
                target_index = visual_index + 1
            
            target_pos = self._get_position_for_index(target_index)
            
            if animate and widget.pos() != target_pos:
                # 创建位置动画
                anim = QPropertyAnimation(widget, b"pos")
                anim.setDuration(150)  # 150ms 动画
                anim.setStartValue(widget.pos())
                anim.setEndValue(target_pos)
                anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                anim.start()
                self.animations.append(anim)
            else:
                widget.move(target_pos)
            
            visual_index += 1
    
    def _get_insert_index_from_pos(self, pos):
        """根据鼠标位置计算插入索引"""
        # 计算鼠标在哪一行哪一列
        col = (pos.x() - self.MARGIN + self.SPACING // 2) // (self.CARD_SIZE + self.SPACING)
        row = (pos.y() - self.MARGIN + self.SPACING // 2) // (self.CARD_SIZE + self.SPACING)
        
        col = max(0, min(col, self.MAX_COLUMNS - 1))
        row = max(0, row)
        
        index = row * self.MAX_COLUMNS + col
        
        # 不能超过当前卡片数量
        max_index = len(self.card_widgets)
        if self.dragged_widget:
            max_index -= 1  # 拖拽时，最大索引减1
        
        return min(index, max_index)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('application/x-card-widget'):
            card_id = event.mimeData().data('application/x-card-widget').data().decode()
            
            # 检查被拖拽的卡片是否属于当前容器（禁止跨分类移动）
            found = False
            for widget in self.card_widgets:
                if str(widget.card.id) == card_id:
                    self.dragged_card_id = card_id
                    self.dragged_widget = widget
                    widget.hide()  # 隐藏正在拖拽的卡片
                    found = True
                    break
            
            if found:
                event.acceptProposedAction()
            else:
                # 卡片不属于当前容器，拒绝拖拽
                event.ignore()
    
    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat('application/x-card-widget'):
            # 只有当卡片属于当前容器时才处理
            if self.dragged_widget is None:
                event.ignore()
                return
            event.acceptProposedAction()
            
            # 计算新的插入位置
            pos = event.position().toPoint()
            new_placeholder_index = self._get_insert_index_from_pos(pos)
            
            # 如果位置改变了，更新动画
            if new_placeholder_index != self.current_placeholder_index:
                self.current_placeholder_index = new_placeholder_index
                self._update_positions(
                    animate=True, 
                    skip_widget=self.dragged_widget,
                    placeholder_index=new_placeholder_index
                )
    
    def dragLeaveEvent(self, event):
        """拖拽离开时恢复原始位置"""
        self.current_placeholder_index = -1
        
        if self.dragged_widget:
            # 显示卡片并恢复到原始位置
            self.dragged_widget.show()
            self.dragged_widget.setGraphicsEffect(None)
        
        # 所有卡片恢复到原始位置
        self._update_positions(animate=True)
    
    def dropEvent(self, event):
        if event.mimeData().hasFormat('application/x-card-widget'):
            # 只有当卡片属于当前容器时才处理
            if self.dragged_widget is None:
                event.ignore()
                return
            
            event.acceptProposedAction()
            
            # 使用当前占位符位置作为目标位置
            target_index = self.current_placeholder_index
            if target_index < 0:
                target_index = len(self.card_widgets) - 1
            
            # 找到原始位置
            source_index = self.card_widgets.index(self.dragged_widget)
            
            # 保存被拖拽的 widget 引用
            dropped_widget = self.dragged_widget
            
            # 重置拖拽状态（先重置，这样 _update_positions 不会跳过这个 widget）
            self.dragged_widget = None
            self.dragged_card_id = None
            self.current_placeholder_index = -1
            
            # 如果位置有变化，重新排序列表
            if target_index != source_index:
                self.card_widgets.remove(dropped_widget)
                # 调整目标索引
                if target_index > source_index:
                    target_index = min(target_index, len(self.card_widgets))
                self.card_widgets.insert(target_index, dropped_widget)
                
                # 发送排序变化信号
                self._emit_order_changed()
            
            # 计算被拖拽卡片的最终目标位置
            final_index = self.card_widgets.index(dropped_widget)
            target_pos = self._get_position_for_index(final_index)
            
            # 显示卡片（先放到目标位置附近，带一点偏移，然后动画归位）
            dropped_widget.setGraphicsEffect(None)
            dropped_widget.show()
            
            # 停止所有动画
            for anim in self.animations:
                anim.stop()
            self.animations.clear()
            
            # 所有卡片同时动画到各自的目标位置
            for i, widget in enumerate(self.card_widgets):
                pos = self._get_position_for_index(i)
                
                if widget.pos() != pos or widget == dropped_widget:
                    anim = QPropertyAnimation(widget, b"pos")
                    
                    if widget == dropped_widget:
                        # 被放下的卡片使用稍长的动画，带弹性效果
                        anim.setDuration(250)
                        anim.setEasingCurve(QEasingCurve.Type.OutBack)
                    else:
                        # 其他卡片快速归位
                        anim.setDuration(180)
                        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                    
                    anim.setStartValue(widget.pos())
                    anim.setEndValue(pos)
                    anim.start()
                    self.animations.append(anim)
            
            self._update_height()
    
    def _emit_order_changed(self):
        """发送排序变化信号"""
        order_list = []
        for i, widget in enumerate(self.card_widgets):
            order_list.append({
                'id': str(widget.card.id),
                'order': i
            })
        self.order_changed.emit(order_list)
    
    def resizeEvent(self, event):
        """窗口大小改变时重新布局"""
        super().resizeEvent(event)
        self._update_positions(animate=False)


class CardItemWidget(QWidget):
    """名片项组件 - 宫格样式，支持长按拖拽"""
    
    edit_clicked = pyqtSignal(object)
    delete_clicked = pyqtSignal(object)
    selection_changed = pyqtSignal(object, bool)
    
    LONG_PRESS_DURATION = 300  # 长按时间 (ms)
    
    def __init__(self, card, parent=None):
        super().__init__(parent)
        self.card = card
        self.is_selected = False
        self.drag_start_position = None
        self.long_press_timer = None
        self.is_long_pressed = False
        self.init_ui()
    
    def init_ui(self):
        # 极简紧凑设计 - 适应4列 (88x88 px)
        self.setFixedSize(88, 88)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        self.setLayout(layout)
        
        # Top Row: Checkbox + Tiny Actions
        top_row = QHBoxLayout()
        top_row.setSpacing(2)
        
        # Checkbox (Small)
        self.checkbox = QCheckBox()
        self.checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 12px; height: 12px;
                border-radius: 6px;
                border: 1px solid #C7C7CC;
                background: white;
            }
            QCheckBox::indicator:checked {
                background: #007AFF; border-color: #007AFF;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEgNEw0LjUgNy41TDExIDEiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+PC9zdmc+);
            }
        """)
        self.checkbox.clicked.connect(self.toggle_selection)
        top_row.addWidget(self.checkbox)
        
        top_row.addStretch()
        
        # Tiny Action Buttons
        def create_tiny_btn(icon, tooltip, cb):
            btn = QPushButton()
            btn.setFixedSize(16, 16)
            btn.setIcon(icon)
            btn.setIconSize(QSize(10, 10))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tooltip)
            btn.setStyleSheet("QPushButton { border: none; background: transparent; } QPushButton:hover { background: #E5E5EA; border-radius: 3px; }")
            btn.clicked.connect(cb)
            return btn

        edit_btn = create_tiny_btn(Icons.edit('#8E8E93'), "编辑", lambda: self.edit_clicked.emit(self.card))
        del_btn = create_tiny_btn(Icons.trash('#FF3B30'), "删除", lambda: self.delete_clicked.emit(self.card))
        
        top_row.addWidget(edit_btn)
        top_row.addWidget(del_btn)
        
        layout.addLayout(top_row)
        
        # Icon (Centered)
        icon_label = QLabel("👤")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 18px; color: #8E8E93;")
        layout.addWidget(icon_label)
        
        # Name (Centered)
        name_label = QLabel(self.card.name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("""
            font-size: 11px;
            font-weight: 500;
            color: #1D1D1F;
        """)
        # Elide text
        font_metrics = name_label.fontMetrics()
        elided_text = font_metrics.elidedText(self.card.name, Qt.TextElideMode.ElideRight, 80)
        name_label.setText(elided_text)
        
        layout.addWidget(name_label)
        
        self.update_style()

    def toggle_selection(self):
        self.is_selected = not self.is_selected
        self.checkbox.setChecked(self.is_selected)
        self.update_style()
        self.selection_changed.emit(self.card, self.is_selected)
        
    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.checkbox.setChecked(selected)
        self.update_style()
        
    def update_style(self):
        if self.is_selected:
            self.setStyleSheet("""
                CardItemWidget {
                    background: #F2F8FD;
                    border: 1px solid #007AFF;
                    border-radius: 10px;
                }
            """)
        else:
            self.setStyleSheet("""
                CardItemWidget {
                    background: white;
                    border: 1px solid #E5E5EA;
                    border-radius: 10px;
                }
                CardItemWidget:hover {
                    border-color: #C7C7CC;
                    background: #F9F9F9;
                    margin-top: -2px; /* Hover lift effect */
                }
            """)
    
    def mousePressEvent(self, event):
        """鼠标按下事件 - 开始长按检测"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()
            self.is_long_pressed = False
            
            # 启动长按计时器
            from PyQt6.QtCore import QTimer
            self.long_press_timer = QTimer()
            self.long_press_timer.setSingleShot(True)
            self.long_press_timer.timeout.connect(self._on_long_press)
            self.long_press_timer.start(self.LONG_PRESS_DURATION)
        
        super().mousePressEvent(event)
    
    def _on_long_press(self):
        """长按触发"""
        self.is_long_pressed = True
        # 添加视觉反馈 - 轻微放大和阴影
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(15)
        effect.setXOffset(0)
        effect.setYOffset(5)
        effect.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(effect)
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 检测拖拽"""
        if not self.drag_start_position:
            return
        
        # 计算移动距离
        distance = (event.pos() - self.drag_start_position).manhattanLength()
        
        # 如果已长按且移动了足够距离，开始拖拽
        if self.is_long_pressed and distance > 10:
            self.start_drag()
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        # 取消长按计时器
        if self.long_press_timer:
            self.long_press_timer.stop()
            self.long_press_timer = None
        
        # 重置状态
        self.drag_start_position = None
        self.is_long_pressed = False
        self.setGraphicsEffect(None)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        
        super().mouseReleaseEvent(event)
    
    def start_drag(self):
        """开始拖拽操作"""
        from PyQt6.QtGui import QDrag
        from PyQt6.QtCore import QMimeData, QByteArray
        
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # 存储名片 ID
        card_id = str(self.card.id)
        mime_data.setData('application/x-card-widget', QByteArray(card_id.encode()))
        
        drag.setMimeData(mime_data)
        
        # 创建拖拽时的缩略图
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(self.drag_start_position)
        
        # 执行拖拽
        drag.exec(Qt.DropAction.MoveAction)
        
        # 重置状态
        self.drag_start_position = None
        self.is_long_pressed = False
        self.setGraphicsEffect(None)
        self.setCursor(Qt.CursorShape.ArrowCursor)


class ChangePasswordDialog(QDialog):
    """修改密码对话框"""
    
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("修改密码")
        self.setFixedSize(420, 400)  # 增加高度和宽度
        self.setStyleSheet("""
            QDialog { background: white; }
            QLabel { font-size: 14px; color: #333; font-weight: 500; }
            QLineEdit {
                padding: 10px;
                border: 1.5px solid #E5E7EB;
                border-radius: 6px;
                background: #F9FAFB;
                font-size: 14px;
                min-height: 20px;  # 确保最小高度
            }
            QLineEdit:focus { border-color: #007AFF; background: white; }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        self.setLayout(layout)
        
        # 标题
        title = QLabel("修改密码")
        title.setStyleSheet("font-size: 18px; font-weight: 700; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # 原密码
        layout.addWidget(QLabel("原密码"))
        self.old_pwd = QLineEdit()
        self.old_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.old_pwd.setPlaceholderText("请输入当前密码")
        self.old_pwd.setMinimumHeight(40) # 设置输入框高度
        layout.addWidget(self.old_pwd)
        
        # 新密码
        layout.addWidget(QLabel("新密码"))
        self.new_pwd = QLineEdit()
        self.new_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pwd.setPlaceholderText("请输入新密码")
        self.new_pwd.setMinimumHeight(40) # 设置输入框高度
        layout.addWidget(self.new_pwd)
        
        # 确认密码
        layout.addWidget(QLabel("确认新密码"))
        self.confirm_pwd = QLineEdit()
        self.confirm_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pwd.setPlaceholderText("请再次输入新密码")
        self.confirm_pwd.setMinimumHeight(40) # 设置输入框高度
        layout.addWidget(self.confirm_pwd)
        
        layout.addStretch()
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15) # 增加按钮间距
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setMinimumHeight(40) # 设置按钮高度
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #F3F4F6; border: none; padding: 8px 20px;
                border-radius: 6px; color: #4B5563; font-weight: 600;
                min-width: 80px;
            }
            QPushButton:hover { background: #E5E7EB; }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("确认修改")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setMinimumHeight(40) # 设置按钮高度
        save_btn.setStyleSheet("""
            QPushButton {
                background: #007AFF; border: none; padding: 8px 20px;
                border-radius: 6px; color: white; font-weight: 600;
                min-width: 80px;
            }
            QPushButton:hover { background: #0062CC; }
        """)
        save_btn.clicked.connect(self.save_password)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        
    def save_password(self):
        old_pass = self.old_pwd.text()
        new_pass = self.new_pwd.text()
        confirm_pass = self.confirm_pwd.text()
        
        if not old_pass or not new_pass:
            QMessageBox.warning(self, "提示", "请填写完整信息")
            return
            
        if not self.user.check_password(old_pass):
            QMessageBox.warning(self, "错误", "原密码错误")
            return
            
        if new_pass != confirm_pass:
            QMessageBox.warning(self, "错误", "两次输入的新密码不一致")
            return
            
        if len(new_pass) < 6:
            QMessageBox.warning(self, "提示", "新密码长度不能少于6位")
            return
            
        try:
            self.user.set_password(new_pass)
            self.user.save()
            QMessageBox.information(self, "成功", "密码修改成功！")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"修改失败: {str(e)}")


class FieldLibraryDialog(QDialog):
    """字段库选择对话框 - 用户从后台维护的字段库中选择字段添加到名片"""
    
    def __init__(self, db_manager, cards, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.cards = cards  # 用户的名片列表
        self.selected_fields = []  # 选中的字段
        self.selected_cards = []  # 选中的目标名片（支持多选）
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("字段库")
        self.setFixedSize(700, 600)
        self.setStyleSheet("QDialog { background: white; }")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        self.setLayout(layout)
        
        # 标题
        title = QLabel("字段库")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1D1D1F;")
        layout.addWidget(title)
        
        # 字段分类标签
        category_label = QLabel("选择字段（可多选）")
        category_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #666; margin-top: 10px;")
        layout.addWidget(category_label)
        
        # 字段库滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        fields_container = QWidget()
        self.fields_layout = QVBoxLayout()
        self.fields_layout.setContentsMargins(0, 0, 0, 0)
        self.fields_layout.setSpacing(12)
        fields_container.setLayout(self.fields_layout)
        
        scroll.setWidget(fields_container)
        layout.addWidget(scroll, 1)
        
        # 加载字段库
        self.load_field_library()
        
        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background: #E5E7EB; max-height: 1px;")
        layout.addWidget(sep)
        
        # 选择名片区域
        card_section = QVBoxLayout()
        card_section.setSpacing(10)
        
        card_label = QLabel("选择名片（可多选）")
        card_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #666;")
        card_section.addWidget(card_label)
        
        # 名片选择区域（横向滚动的标签）
        cards_scroll = QScrollArea()
        cards_scroll.setWidgetResizable(True)
        cards_scroll.setFrameShape(QFrame.Shape.NoFrame)
        cards_scroll.setFixedHeight(50)
        cards_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        cards_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        cards_container = QWidget()
        self.cards_layout = QHBoxLayout()
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        cards_container.setLayout(self.cards_layout)
        
        # 添加名片标签
        self.card_buttons = []
        for card in self.cards:
            btn = QPushButton(card.name)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: white;
                    border: 1.5px solid #E5E7EB;
                    border-radius: 16px;
                    padding: 6px 14px;
                    font-size: 13px;
                    color: #374151;
                }
                QPushButton:checked {
                    background: #007AFF;
                    border-color: #007AFF;
                    color: white;
                }
                QPushButton:hover:!checked {
                    border-color: #007AFF;
                    background: #F0F8FF;
                }
            """)
            btn.clicked.connect(lambda checked, c=card, b=btn: self.on_card_toggled(c, b))
            self.cards_layout.addWidget(btn)
            self.card_buttons.append({'button': btn, 'card': card})
        
        # 添加名片按钮
        add_card_btn = QPushButton("添加名片")
        add_card_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_card_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1.5px dashed #007AFF;
                border-radius: 16px;
                padding: 6px 14px;
                font-size: 13px;
                color: #007AFF;
            }
            QPushButton:hover {
                background: #F0F8FF;
            }
        """)
        add_card_btn.clicked.connect(self.add_new_card)
        self.cards_layout.addWidget(add_card_btn)
        
        self.cards_layout.addStretch()
        
        cards_scroll.setWidget(cards_container)
        card_section.addWidget(cards_scroll)
        
        layout.addLayout(card_section)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(100, 40)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #F3F4F6;
                border: none;
                border-radius: 8px;
                color: #4B5563;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover { background: #E5E7EB; }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("保存")
        save_btn.setFixedSize(100, 40)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background: #007AFF;
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover { background: #0062CC; }
        """)
        save_btn.clicked.connect(self.save_fields)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
    
    def load_field_library(self):
        """加载字段库"""
        # 清空现有内容
        while self.fields_layout.count():
            item = self.fields_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 获取字段库
        fields = self.db_manager.get_all_field_library(is_active=True)
        
        if not fields:
            empty_label = QLabel("暂无字段，请联系管理员添加")
            empty_label.setStyleSheet("color: #999; font-size: 14px; padding: 20px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.fields_layout.addWidget(empty_label)
            return
        
        # 按分类分组
        from collections import defaultdict
        fields_by_category = defaultdict(list)
        for field in fields:
            fields_by_category[field.category or '通用'].append(field)
        
        # 为每个分类创建区域
        self.field_checkboxes = {}
        
        for category, category_fields in sorted(fields_by_category.items()):
            # 分类标题
            cat_label = QLabel(category)
            cat_label.setStyleSheet("""
                font-size: 13px;
                font-weight: 600;
                color: #8E8E93;
                padding: 8px 0 4px 0;
            """)
            self.fields_layout.addWidget(cat_label)
            
            # 字段按钮区域（流式布局）
            flow_widget = QWidget()
            flow_layout = QHBoxLayout()
            flow_layout.setContentsMargins(0, 0, 0, 0)
            flow_layout.setSpacing(8)
            flow_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            
            # 使用 FlowLayout 或简单的 wrap
            # 这里使用 Grid 模拟流式布局
            grid_widget = QWidget()
            grid_layout = QGridLayout()
            grid_layout.setContentsMargins(0, 0, 0, 0)
            grid_layout.setSpacing(8)
            grid_widget.setLayout(grid_layout)
            
            cols = 6  # 每行6个
            for i, field in enumerate(category_fields):
                btn = QPushButton(field.name.split('、')[0])  # 只显示第一个名称
                btn.setCheckable(True)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setToolTip(f"{field.name}\n{field.description or ''}")
                btn.setStyleSheet("""
                    QPushButton {
                        background: white;
                        border: 1px solid #E5E7EB;
                        border-radius: 6px;
                        padding: 8px 12px;
                        font-size: 13px;
                        color: #374151;
                        min-width: 60px;
                    }
                    QPushButton:checked {
                        background: #007AFF;
                        border-color: #007AFF;
                        color: white;
                    }
                    QPushButton:hover:!checked {
                        border-color: #007AFF;
                        background: #F0F8FF;
                    }
                """)
                
                row = i // cols
                col = i % cols
                grid_layout.addWidget(btn, row, col)
                
                self.field_checkboxes[str(field.id)] = {
                    'button': btn,
                    'field': field
                }
            
            self.fields_layout.addWidget(grid_widget)
        
        self.fields_layout.addStretch()
    
    def on_card_toggled(self, card, button):
        """切换名片选中状态（支持多选）"""
        # 不需要取消其他按钮，直接切换当前按钮状态即可
        pass
    
    def add_new_card(self):
        """添加新名片（跳转到添加名片对话框）"""
        QMessageBox.information(self, "提示", "请先在主界面点击「添加名片」创建名片后再来添加字段")
    
    def save_fields(self):
        """保存选中的字段到名片"""
        # 收集选中的字段
        self.selected_fields = []
        for field_id, data in self.field_checkboxes.items():
            if data['button'].isChecked():
                self.selected_fields.append(data['field'])
        
        if not self.selected_fields:
            QMessageBox.warning(self, "提示", "请选择至少一个字段")
            return
        
        # 收集选中的名片（多选）
        self.selected_cards = []
        for card_data in self.card_buttons:
            if card_data['button'].isChecked():
                self.selected_cards.append(card_data['card'])
        
        if not self.selected_cards:
            QMessageBox.warning(self, "提示", "请选择至少一个名片")
            return
        
        self.accept()
    
    def get_selected_fields(self):
        """获取选中的字段"""
        return self.selected_fields
    
    def get_selected_cards(self):
        """获取选中的名片列表（多选）"""
        return self.selected_cards


class FieldLibraryImportDialog(QDialog):
    """字段库导入对话框 - 简化版，仅用于添加名片时导入字段"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.selected_fields = []
        self.field_checkboxes = {}
        self.all_fields = []  # 存储所有字段用于搜索
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("导入官方模版")
        self.setFixedSize(600, 550)
        self.setStyleSheet("QDialog { background: white; }")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        self.setLayout(layout)
        
        # 标题
        title = QLabel("选择要导入的字段")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #1D1D1F;")
        layout.addWidget(title)
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索字段...")
        self.search_input.setMinimumHeight(38)
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 1.5px solid #E5E5EA;
                border-radius: 8px;
                font-size: 14px;
                background: #F9FAFB;
            }
            QLineEdit:focus {
                border-color: #007AFF;
                background: white;
            }
        """)
        self.search_input.textChanged.connect(self.on_search_changed)
        layout.addWidget(self.search_input)
        
        # 提示
        hint = QLabel("点击选择需要的字段，支持多选")
        hint.setStyleSheet("font-size: 13px; color: #8E8E93;")
        layout.addWidget(hint)
        
        # 字段库滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        fields_container = QWidget()
        self.fields_layout = QVBoxLayout()
        self.fields_layout.setContentsMargins(0, 0, 0, 0)
        self.fields_layout.setSpacing(12)
        fields_container.setLayout(self.fields_layout)
        
        scroll.setWidget(fields_container)
        layout.addWidget(scroll, 1)
        
        # 加载字段库
        self.load_field_library()
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(100, 40)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #F5F5F5;
                border: 1px solid #E5E5EA;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                color: #666;
            }
            QPushButton:hover {
                background: #EBEBEB;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        import_btn = QPushButton("导入选中")
        import_btn.setFixedSize(100, 40)
        import_btn.setStyleSheet("""
            QPushButton {
                background: #007AFF;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                color: white;
            }
            QPushButton:hover {
                background: #0062CC;
            }
        """)
        import_btn.clicked.connect(self.confirm_import)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(import_btn)
        layout.addLayout(btn_layout)
    
    def load_field_library(self, search_text=""):
        """加载字段库"""
        # 保存当前选中状态
        selected_ids = set()
        for field_id, data in self.field_checkboxes.items():
            if data['button'].isChecked():
                selected_ids.add(field_id)
        
        # 清空现有内容
        while self.fields_layout.count():
            item = self.fields_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.field_checkboxes = {}
        
        # 获取字段库（只在首次加载时获取）
        if not self.all_fields:
            self.all_fields = self.db_manager.get_all_field_library(is_active=True)
        
        fields = self.all_fields
        
        if not fields:
            empty_label = QLabel("暂无字段模版\n请联系管理员添加")
            empty_label.setStyleSheet("color: #999; font-size: 14px; padding: 40px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.fields_layout.addWidget(empty_label)
            return
        
        # 搜索过滤
        search_text = search_text.strip().lower()
        if search_text:
            fields = [f for f in fields if search_text in f.name.lower()]
        
        if not fields:
            empty_label = QLabel(f"未找到包含 \"{search_text}\" 的字段")
            empty_label.setStyleSheet("color: #999; font-size: 14px; padding: 40px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.fields_layout.addWidget(empty_label)
            return
        
        # 按分类分组
        from collections import defaultdict
        fields_by_category = defaultdict(list)
        for field in fields:
            fields_by_category[field.category or '通用'].append(field)
        
        # 为每个分类创建区域
        for category, category_fields in sorted(fields_by_category.items()):
            # 分类标题
            cat_label = QLabel(category)
            cat_label.setStyleSheet("""
                font-size: 13px;
                font-weight: 600;
                color: #8E8E93;
                padding: 8px 0 4px 0;
            """)
            self.fields_layout.addWidget(cat_label)
            
            # 字段网格
            grid_widget = QWidget()
            grid_layout = QGridLayout()
            grid_layout.setContentsMargins(0, 0, 0, 0)
            grid_layout.setSpacing(8)
            grid_widget.setLayout(grid_layout)
            
            cols = 2  # 改为2列，让文字显示更完整
            for i, field in enumerate(category_fields):
                btn = QPushButton(field.name)
                btn.setCheckable(True)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setToolTip(f"默认值: {field.default_value}" if field.default_value else "无默认值")
                btn.setStyleSheet("""
                    QPushButton {
                        background: #F9FAFB;
                        border: 1.5px solid #E5E7EB;
                        border-radius: 8px;
                        padding: 10px 12px;
                        font-size: 13px;
                        color: #374151;
                        text-align: left;
                    }
                    QPushButton:checked {
                        background: #EBF5FF;
                        border-color: #007AFF;
                        color: #007AFF;
                    }
                    QPushButton:hover:!checked {
                        border-color: #007AFF;
                        background: #F0F8FF;
                    }
                """)
                
                # 恢复选中状态
                if str(field.id) in selected_ids:
                    btn.setChecked(True)
                
                row = i // cols
                col = i % cols
                grid_layout.addWidget(btn, row, col)
                
                self.field_checkboxes[str(field.id)] = {
                    'button': btn,
                    'field': field
                }
            
            self.fields_layout.addWidget(grid_widget)
        
        self.fields_layout.addStretch()
    
    def on_search_changed(self, text):
        """搜索文本变化时过滤字段"""
        self.load_field_library(text)
    
    def confirm_import(self):
        """确认导入"""
        self.selected_fields = []
        for field_id, data in self.field_checkboxes.items():
            if data['button'].isChecked():
                self.selected_fields.append(data['field'])
        
        if not self.selected_fields:
            QMessageBox.warning(self, "提示", "请选择至少一个字段")
            return
        
        self.accept()
    
    def get_selected_fields(self):
        """获取选中的字段"""
        return self.selected_fields


class AllRecordsDialog(QDialog):
    """所有填写记录对话框"""
    
    def __init__(self, parent=None, db_manager=None, current_user=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_user = current_user
        self.current_page = 1
        self.page_size = 50
        self.total_records = 0
        self.init_ui()
        self.load_records()
    
    def init_ui(self):
        self.setWindowTitle("所有填写记录")
        self.setMinimumSize(900, 600)
        self.resize(1000, 700)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        self.setLayout(layout)
        
        # 标题栏
        header = QHBoxLayout()
        title = QLabel("📋 所有填写记录")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: 700;
            color: #1D1D1F;
        """)
        header.addWidget(title)
        header.addStretch()
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.setIcon(Icons.refresh(COLORS['primary']))
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['primary']}15;
                color: {COLORS['primary']};
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {COLORS['primary']}25;
            }}
        """)
        refresh_btn.clicked.connect(self.load_records)
        header.addWidget(refresh_btn)
        
        layout.addLayout(header)
        
        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "时间", "名片", "链接", "填写字段", "成功数", "状态"
        ])
        
        # 设置列宽
        header_view = self.table.horizontalHeader()
        header_view.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 160)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(1, 180)  # 增加宽度以完整显示名片名称
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 90)
        
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        
        self.table.setStyleSheet("""
            QTableWidget {
                background: white;
                border: 1px solid #E5E5EA;
                border-radius: 12px;
                selection-background-color: #F2F8FF;
            }
            QHeaderView::section {
                background: #F9FAFB;
                padding: 12px 0px;
                border: none;
                border-bottom: 1px solid #E5E5EA;
                font-weight: 600;
                color: #6B7280;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 10px 0px;
                border-bottom: 1px solid #F3F4F6;
                color: #1F2937;
            }
            QTableWidget::item:alternate {
                background: #FAFAFA;
            }
            QTableWidget::item:selected {
                background-color: #EBF5FF;
            }
        """)
        
        layout.addWidget(self.table, 1)
        
        # 分页栏
        pagination = QHBoxLayout()
        pagination.addStretch()
        
        self.page_label = QLabel("第 1 页")
        self.page_label.setStyleSheet("color: #6B7280; font-size: 13px;")
        pagination.addWidget(self.page_label)
        
        prev_btn = QPushButton("上一页")
        prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        prev_btn.setStyleSheet("""
            QPushButton {
                background: white;
                border: 1px solid #E5E5EA;
                border-radius: 6px;
                padding: 6px 12px;
                color: #374151;
            }
            QPushButton:hover {
                background: #F9FAFB;
            }
        """)
        prev_btn.clicked.connect(self.prev_page)
        pagination.addWidget(prev_btn)
        
        next_btn = QPushButton("下一页")
        next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        next_btn.setStyleSheet("""
            QPushButton {
                background: white;
                border: 1px solid #E5E5EA;
                border-radius: 6px;
                padding: 6px 12px;
                color: #374151;
            }
            QPushButton:hover {
                background: #F9FAFB;
            }
        """)
        next_btn.clicked.connect(self.next_page)
        pagination.addWidget(next_btn)
        
        pagination.addStretch()
        layout.addLayout(pagination)
        
        # 底部关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 32px;
                font-weight: 600;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: {COLORS['primary_dark']};
            }}
        """)
        close_btn.clicked.connect(self.accept)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
    
    def load_records(self):
        """加载记录"""
        offset = (self.current_page - 1) * self.page_size
        records = self.db_manager.get_fill_records(limit=self.page_size, offset=offset, user=self.current_user)
        
        self.table.setRowCount(len(records))
        
        for i, record in enumerate(records):
            # 时间
            item_time = QTableWidgetItem(record.created_at.strftime("%Y-%m-%d %H:%M:%S"))
            item_time.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, item_time)
            
            # 名片
            card_name = "未知名片"
            try:
                if record.card:
                    card_name = record.card.name
            except:
                card_name = "名片已删除"
            item_card = QTableWidgetItem(card_name)
            item_card.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 1, item_card)
            
            # 链接
            link_name = "未知链接"
            try:
                if record.link:
                    link_name = record.link.name
            except:
                link_name = "链接已删除"
            item_link = QTableWidgetItem(link_name)
            self.table.setItem(i, 2, item_link)
            
            # 填写字段
            item_total = QTableWidgetItem(str(record.total_count))
            item_total.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 3, item_total)
            
            # 成功数
            item_fill = QTableWidgetItem(str(record.fill_count))
            item_fill.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 4, item_fill)
            
            # 状态
            status_item = QTableWidgetItem("✅ 成功" if record.success else "❌ 失败")
            status_item.setForeground(Qt.GlobalColor.green if record.success else Qt.GlobalColor.red)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 5, status_item)
        
        self.page_label.setText(f"第 {self.current_page} 页 · 共 {len(records)} 条")
    
    def prev_page(self):
        """上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self.load_records()
    
    def next_page(self):
        """下一页"""
        self.current_page += 1
        self.load_records()


class UserAvatarMenu(QPushButton):
    """用户头像菜单组件 - 文字+图标样式"""
    
    def __init__(self, user, parent_window):
        super().__init__()
        self.user = user
        self.parent_window = parent_window
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # 设置内容: 图标 + 用户名
        self.setText(f" {self.user.username if self.user else '未登录'}")
        self.setIcon(Icons.user('#1D1D1F'))
        self.setIconSize(QSize(20, 20))
        
        # 样式
        self.setStyleSheet("""
            UserAvatarMenu {
                background: transparent;
                color: #1D1D1F;
                font-size: 14px;
                font-weight: 500;
                border: none;
                padding: 6px 10px;
                border-radius: 6px;
                text-align: left;
            }
            UserAvatarMenu:hover {
                background: #F5F5F7;
            }
            UserAvatarMenu::menu-indicator {
                image: none;
            }
        """)
        
        # 初始化菜单
        self.menu = QMenu(self)
        self.init_menu()
        
    def init_menu(self):
        # 设置菜单样式
        self.menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                padding: 8px 0;
            }
            QMenu::item {
                padding: 10px 24px;
                font-size: 14px;
                color: #374151;
            }
            QMenu::item:selected {
                background-color: #F3F4F6;
                color: #111827;
            }
            QMenu::separator {
                height: 1px;
                background: #E5E7EB;
                margin: 6px 0;
            }
            QMenu::icon {
                padding-left: 12px;
            }
        """)
        self.menu.setWindowFlags(self.menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(self.menu)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 4)
        self.menu.setGraphicsEffect(shadow)
        
        # 用户信息头部 (Disabled Item as Header)
        header = QAction(f"👤 {self.user.username}", self.menu)
        header.setEnabled(False)
        self.menu.addAction(header)
        
        self.menu.addSeparator()
        
        # 修改密码
        action_pwd = QAction(Icons.lock('#666'), "修改密码", self.menu)
        action_pwd.triggered.connect(self.change_password)
        self.menu.addAction(action_pwd)
        
        # 切换账号
        action_switch = QAction(Icons.refresh('#666'), "切换账号", self.menu)
        action_switch.triggered.connect(self.parent_window.switch_account)
        self.menu.addAction(action_switch)
        
        self.menu.addSeparator()
        
        # 退出系统
        from PyQt6.QtWidgets import QApplication
        action_exit = QAction(Icons.sign_out('#FF3B30'), "退出系统", self.menu)
        action_exit.triggered.connect(QApplication.instance().quit)
        self.menu.addAction(action_exit)
        
    def enterEvent(self, event):
        """鼠标悬浮显示菜单"""
        if not self.menu.isVisible():
            # 计算位置：在头像正下方
            pos = self.mapToGlobal(QPoint(0, self.height() + 5))
            self.menu.popup(pos)
        super().enterEvent(event)

    def change_password(self):
        dialog = ChangePasswordDialog(self.user, self.parent_window)
        dialog.exec()



class FieldPushReceivedDialog(QDialog):
    """推送字段接收对话框 - 高级设计风格"""
    
    def __init__(self, notification, parent=None):
        super().__init__(parent)
        self.notification = notification
        self.db_manager = DatabaseManager()
        self.selected_cards = set()
        
        # 解析字段信息
        field_id = self.notification.related_id
        self.field = DatabaseManager.get_field_library_by_id(field_id)
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("新字段推荐")
        self.setFixedSize(480, 700)
        # 去掉系统标题栏，使用自定义样式
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 背景容器 (圆角 + 阴影)
        self.bg_frame = QFrame()
        self.bg_frame.setObjectName("bg_frame")
        self.bg_frame.setStyleSheet("""
            #bg_frame {
                background-color: #FFFFFF;
                border-radius: 24px;
                border: 1px solid #F3F4F6;
            }
        """)
        
        # 添加阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 8)
        self.bg_frame.setGraphicsEffect(shadow)
        
        main_layout.addWidget(self.bg_frame)
        
        # 内容布局
        content_layout = QVBoxLayout(self.bg_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # 1. 顶部区域 (图标 + 标题)
        top_container = QWidget()
        top_layout = QVBoxLayout(top_container)
        top_layout.setContentsMargins(30, 40, 30, 20)
        top_layout.setSpacing(16)
        top_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 图标容器
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(64, 64)
        icon_lbl.setStyleSheet("""
            background-color: #F0FDF4;
            border-radius: 32px;
        """)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_pixmap = qta.icon('fa5s.magic', color='#10B981').pixmap(32, 32)
        icon_lbl.setPixmap(icon_pixmap)
        
        # 标题
        title_label = QLabel("发现新字段")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: 800;
            color: #111827;
            letter-spacing: -0.5px;
        """)
        
        # 字段信息区
        info_container = QFrame()
        info_container.setStyleSheet("""
            background-color: #F9FAFB;
            border-radius: 16px;
            border: 1px solid #F3F4F6;
        """)
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(20, 16, 20, 16)
        info_layout.setSpacing(8)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        field_name = self.field.name if self.field else "未知字段"
        name_lbl = QLabel(field_name)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setStyleSheet("font-size: 18px; font-weight: 700; color: #111827;")
        
        desc = self.field.description if self.field and self.field.description else "暂无说明"
        desc_lbl = QLabel(desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setStyleSheet("font-size: 13px; color: #6B7280; line-height: 1.4;")
        
        info_layout.addWidget(name_lbl)
        info_layout.addWidget(desc_lbl)
        
        if self.field and self.field.default_value:
            val_lbl = QLabel(self.field.default_value)
            val_lbl.setStyleSheet("""
                background-color: #E5E7EB;
                color: #4B5563;
                border-radius: 4px;
                padding: 2px 8px;
                font-family: monospace;
                font-size: 12px;
            """)
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            info_layout.addWidget(val_lbl)
            
        top_layout.addWidget(icon_lbl)
        top_layout.addWidget(title_label)
        top_layout.addWidget(info_container)
        
        content_layout.addWidget(top_container)
        
        # 2. 名片选择区
        select_container = QWidget()
        select_layout = QVBoxLayout(select_container)
        select_layout.setContentsMargins(24, 0, 24, 16)
        
        select_header = QHBoxLayout()
        select_title = QLabel("添加到名片")
        select_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #6B7280; text-transform: uppercase;")
        
        select_all_btn = QPushButton("全选")
        select_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        select_all_btn.setStyleSheet("""
            border: none; color: #10B981; font-weight: 600; font-size: 13px;
            background: transparent;
        """)
        select_all_btn.clicked.connect(self.select_all_cards)
        
        select_header.addWidget(select_title)
        select_header.addStretch()
        select_header.addWidget(select_all_btn)
        
        select_layout.addLayout(select_header)
        select_layout.addSpacing(10)
        
        # 名片列表
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                border: none;
                background: #F3F4F6;
                width: 4px;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical {
                background: #D1D5DB;
                border-radius: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        
        self.cards_widget_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_widget_container)
        self.cards_layout.setContentsMargins(0, 0, 8, 0)
        self.cards_layout.setSpacing(8)
        
        user_cards = DatabaseManager.get_all_cards(user=self.notification.user)
        self.checkboxes = []
        
        if not user_cards:
            empty_lbl = QLabel("暂无名片")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("color: #9CA3AF; padding: 20px;")
            self.cards_layout.addWidget(empty_lbl)
        else:
            for card in user_cards:
                has_field = any(c.key == field_name for c in card.configs)
                
                card_item = QFrame()
                card_item.setCursor(Qt.CursorShape.PointingHandCursor)
                
                # 列表项样式
                style = f"""
                    QFrame {{
                        background-color: {'#F9FAFB' if has_field else 'white'};
                        border: 1px solid {'#F3F4F6' if has_field else '#F3F4F6'};
                        border-radius: 12px;
                    }}
                """
                if not has_field:
                    style += """
                    QFrame:hover {
                        background-color: #F0FDF4;
                        border-color: #10B981;
                    }
                    """
                card_item.setStyleSheet(style)
                
                item_layout = QHBoxLayout(card_item)
                item_layout.setContentsMargins(16, 12, 16, 12)
                
                # 图标
                icon_lbl = QLabel()
                icon_lbl.setFixedSize(16, 16)
                icon_lbl.setPixmap(qta.icon('fa5s.address-card', color='#9CA3AF' if has_field else '#10B981').pixmap(16, 16))
                
                # 文本
                text_layout = QVBoxLayout()
                text_layout.setSpacing(2)
                name_l = QLabel(card.name)
                name_l.setStyleSheet(f"font-weight: 600; font-size: 14px; color: {'#9CA3AF' if has_field else '#1F2937'};")
                cat_l = QLabel(card.category)
                cat_l.setStyleSheet("font-size: 12px; color: #9CA3AF;")
                text_layout.addWidget(name_l)
                text_layout.addWidget(cat_l)
                
                item_layout.addWidget(icon_lbl)
                item_layout.addSpacing(12)
                item_layout.addLayout(text_layout)
                item_layout.addStretch()
                
                # 右侧状态/选择
                if has_field:
                    exist_lbl = QLabel("已存在")
                    exist_lbl.setStyleSheet("font-size: 11px; color: #9CA3AF; background: #F3F4F6; padding: 4px 8px; border-radius: 6px; font-weight: 600;")
                    item_layout.addWidget(exist_lbl)
                else:
                    # 复选框
                    cb = QCheckBox()
                    cb.setStyleSheet("""
                        QCheckBox::indicator { width: 22px; height: 22px; border-radius: 11px; border: 2px solid #E5E7EB; background: white; }
                        QCheckBox::indicator:checked { background-color: #10B981; border-color: #10B981; image: url(:/icons/check_white.svg); }
                        QCheckBox::indicator:hover { border-color: #10B981; }
                    """)
                    cb.setChecked(True)
                    self.selected_cards.add(str(card.id))
                    cb.stateChanged.connect(lambda state, cid=str(card.id): self.toggle_card(cid, state))
                    self.checkboxes.append(cb)
                    
                    # 点击整个卡片触发
                    card_item.mousePressEvent = lambda e, c=cb: c.click()
                    item_layout.addWidget(cb)
                
                self.cards_layout.addWidget(card_item)
        
        self.cards_layout.addStretch()
        scroll.setWidget(self.cards_widget_container)
        select_layout.addWidget(scroll)
        content_layout.addWidget(select_container)
        
        # 3. 底部按钮区
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(24, 0, 24, 24)
        btn_layout.setSpacing(12)
        
        ignore_btn = QPushButton("暂不添加")
        ignore_btn.setFixedSize(100, 48)
        ignore_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ignore_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #6B7280;
                border: none;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover { color: #374151; }
        """)
        ignore_btn.clicked.connect(self.ignore_push)
        
        add_btn = QPushButton("确认添加")
        add_btn.setFixedHeight(48)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet("""
            QPushButton {
                background: #10B981;
                border: none;
                border-radius: 24px;
                color: white;
                font-weight: 700;
                font-size: 16px;
                box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
            }
            QPushButton:hover { background: #059669; }
            QPushButton:pressed { background: #047857; }
        """)
        add_btn.clicked.connect(self.confirm_add)
        
        btn_layout.addWidget(ignore_btn)
        btn_layout.addWidget(add_btn)
        
        content_layout.addWidget(btn_container)

    def select_all_cards(self):
        all_checked = all(cb.isChecked() for cb in self.checkboxes)
        for cb in self.checkboxes:
            cb.setChecked(not all_checked)
            
    def toggle_card(self, card_id, state):
        if state == Qt.CheckState.Checked.value:
            self.selected_cards.add(card_id)
        else:
            self.selected_cards.discard(card_id)
            
    def ignore_push(self):
        # 标记已读
        DatabaseManager.mark_notification_read(str(self.notification.id))
        self.accept()
        
    def confirm_add(self):
        if not self.selected_cards:
            QMessageBox.warning(self, "提示", "请至少选择一张名片")
            return
            
        try:
            count = 0
            for card_id in self.selected_cards:
                card = DatabaseManager.get_card_by_id(card_id)
                if card and self.field:
                    # 再次检查是否已存在
                    if not any(c.key == self.field.name for c in card.configs):
                        # 转换为字典列表以便更新
                        configs = [{'key': c.key, 'value': c.value, 'order': c.order} for c in card.configs]
                        
                        # 添加新字段
                        new_item = {
                            'key': self.field.name,
                            'value': self.field.default_value or "",
                            'order': len(configs)
                        }
                        configs.append(new_item)
                        
                        # 更新名片
                        DatabaseManager.update_card(card_id, configs=configs)
                        count += 1
            
            # 标记已读
            DatabaseManager.mark_notification_read(str(self.notification.id))
            
            # 显示成功动画或提示
            QMessageBox.information(self, "成功", f"已成功将「{self.field.name}」添加到 {count} 张名片")
            self.accept()
            
            # 刷新主界面数据
            if self.parent():
                self.parent().refresh_data()
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加失败: {str(e)}")


class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self, current_user=None):
        super().__init__()
        self.current_user = current_user
        self.db_manager = DatabaseManager()
        self.auto_fill_window = None
        self.notice_plaza_window = None
        self.selected_cards = []  # 选中的名片
        self.selected_links = []  # 选中的链接
        self.fill_mode = "multi"  # 填充模式: "multi" (多开) 或 "single" (单开)
        self.window_columns = 4   # 多开窗口列数设置 (默认一行4个)
        self.links_empty_widget = None  # 链接空状态占位组件
        self.records_empty_widget = None  # 记录空状态占位组件
        self.init_ui()
        
        # 启动消息轮询定时器 (每5秒检查一次待审批消息)
        self.message_timer = QTimer(self)
        self.message_timer.timeout.connect(self.check_messages)
        self.message_timer.start(5000)  # 5000毫秒 = 5秒
        
        # 立即检查一次消息
        QTimer.singleShot(1000, self.check_messages)
    
    def check_messages(self):
        """轮询检查消息"""
        self.update_message_badge()
        self.check_field_push()
        
    def check_field_push(self):
        """检查是否有字段推送消息"""
        if not self.current_user:
            return
            
        try:
            # 获取所有未读消息
            notifications = self.db_manager.get_user_notifications(self.current_user, only_unread=True)
            
            # 筛选出 field_push 类型
            push_msgs = [n for n in notifications if n.type == 'field_push']
            
            # 如果有，弹窗处理（每次处理一个，避免弹窗重叠）
            if push_msgs:
                # 获取最新的一个
                msg = push_msgs[0]
                
                # 检查是否已经有弹窗在显示
                if hasattr(self, 'current_push_dialog') and self.current_push_dialog and self.current_push_dialog.isVisible():
                    return
                    
                self.current_push_dialog = FieldPushReceivedDialog(msg, self)
                self.current_push_dialog.show()
        except Exception as e:
            print(f"检查推送消息失败: {e}")
    
    def init_ui(self):
        """初始化UI - 左侧边栏布局"""
        self.setWindowTitle(f"{config.APP_NAME} v{config.APP_VERSION}")
        self.setGeometry(100, 100, 1400, 900)
        
        # 应用全局样式
        self.setStyleSheet(GLOBAL_STYLE + """
            QCheckBox {
                spacing: 8px;
                font-size: 13px;
                color: #1D1D1F;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid #D1D1D6;
            }
            QCheckBox::indicator:checked {
                background: #007AFF;
                border-color: #007AFF;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEgNEw0LjUgNy41TDExIDEiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+PC9zdmc+);
            }
            QListWidget {
                background: white;
                border: 1px solid #E5E5EA;
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 6px;
                margin-bottom: 4px;
            }
            QListWidget::item:hover {
                background: #F5F5F7;
            }
            QListWidget::item:selected {
                background: #E3F2FD;
                color: #007AFF;
            }
        """)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局 - 水平布局（左侧边栏 + 主内容）
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        central_widget.setLayout(main_layout)
        
        # 创建左侧边栏
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)
        
        # 创建主内容区
        self.main_content = self.create_main_content()
        main_layout.addWidget(self.main_content, 1)
        
        # 加载数据
        self.refresh_data()
    
    def create_sidebar(self) -> QFrame:
        """创建左侧边栏"""
        sidebar = QFrame()
        sidebar.setFixedWidth(450)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background: #FAFAFA;
                border-right: 1px solid #E5E5EA;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 24, 20, 24)
        layout.setSpacing(16)
        sidebar.setLayout(layout)
        
        # --- 顶部 Header 区域 ---
        
        # 1. 标题和全选控制
        header_row = QHBoxLayout()
        
        cards_title = QLabel("我的名片")
        cards_title.setStyleSheet("""
            font-size: 18px;
            font-weight: 700;
            color: #1D1D1F;
        """)
        header_row.addWidget(cards_title)
        header_row.addStretch()
        
        # 全选
        select_all_btn = QPushButton("全选")
        select_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        select_all_btn.setStyleSheet("""
            QPushButton {
                color: #007AFF;
                background: transparent;
                border: none;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover { text-decoration: underline; }
        """)
        select_all_btn.clicked.connect(self.select_all_cards)
        
        # 取消
        deselect_btn = QPushButton("取消")
        deselect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        deselect_btn.setStyleSheet("""
            QPushButton {
                color: #8E8E93;
                background: transparent;
                border: none;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover { color: #1D1D1F; }
        """)
        deselect_btn.clicked.connect(self.deselect_all_cards)
        
        header_row.addWidget(select_all_btn)
        header_row.addWidget(deselect_btn)
        
        layout.addLayout(header_row)
        
        # 2. 功能操作按钮
        actions_row = QHBoxLayout()
        actions_row.setSpacing(10)
        
        # 辅助函数：创建功能按钮
        def create_action_btn(text, color, callback):
            btn = QPushButton(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(38)
            
            # 计算浅色背景
            if color == "#FF9500": # Orange
                bg = "#FFF8E6"
                border = "#FFE0B2"
            elif color == "#34C759": # Green
                bg = "#E8F8ED"
                border = "#C3E6CB"
            elif color == "#007AFF": # Blue (Solid)
                bg = "#007AFF"
                border = "#007AFF"
            
            # 样式
            if color == "#007AFF": # 实心蓝色按钮
                style = f"""
                    QPushButton {{
                        background-color: {bg};
                        color: white;
                        border: none;
                        border-radius: 8px;
                        font-size: 13px;
                        font-weight: 600;
                        padding: 0 12px;
                    }}
                    QPushButton:hover {{ background-color: #0062CC; }}
                """
            else: # 浅色描边按钮
                style = f"""
                    QPushButton {{
                        background-color: {bg};
                        color: {color};
                        border: 1px solid {border};
                        border-radius: 8px;
                        font-size: 13px;
                        font-weight: 600;
                        padding: 0 12px;
                    }}
                    QPushButton:hover {{ 
                        background-color: {color}; 
                        color: white;
                        border-color: {color};
                    }}
                """
            
            btn.setStyleSheet(style)
            btn.clicked.connect(callback)
            return btn

        btn_field = create_action_btn("新增字段", "#FF9500", self.add_new_field)
        btn_cat = create_action_btn("新增分类", "#34C759", self.add_new_category)
        btn_add = create_action_btn("添加名片", "#007AFF", self.open_add_card_dialog)
        
        actions_row.addWidget(btn_field, 1)
        actions_row.addWidget(btn_cat, 1)
        actions_row.addWidget(btn_add, 1)
        
        layout.addLayout(actions_row)
        
        # --- 内容区域 ---
        
        # 名片容器（带滚动）
        cards_scroll = QScrollArea()
        cards_scroll.setWidgetResizable(True)
        cards_scroll.setFrameShape(QFrame.Shape.NoFrame)
        cards_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #D1D1D6;
                border-radius: 3px;
            }
        """)
        
        self.cards_container = QWidget()
        self.cards_container_layout = QVBoxLayout()
        self.cards_container_layout.setContentsMargins(0, 10, 0, 0)
        self.cards_container_layout.setSpacing(2)
        self.cards_container.setLayout(self.cards_container_layout)
        
        cards_scroll.setWidget(self.cards_container)
        layout.addWidget(cards_scroll, 1)
        
        # 用于存储所有名片组件
        self.card_widgets = []
        self.category_widgets = {}
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background: #E5E5EA; max-height: 1px;")
        layout.addWidget(separator)
        
        # ==================== 链接区域 (新布局) ====================
        
        # 1. 顶部功能按钮行 (单开/多开, 通告广场, 窗口设置)
        top_btns_layout = QHBoxLayout()
        top_btns_layout.setSpacing(8)
        
        # 通用按钮样式
        top_btn_style = """
            QPushButton {
                background: #F0F0F0;
                color: #555;
                border: 1px solid #CCC;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #E0E0E0;
                border-color: #999;
            }
        """
        
        orange_btn_style = """
            QPushButton {
                background: #E6A23C;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QPushButton:hover { background: #D99530; }
        """
        
        # 单开/多开模式切换按钮
        self.mode_btn = QPushButton("单开模式")
        self.mode_btn.setCheckable(True)
        self.mode_btn.setChecked(False) # 默认为单开(unchecked) or 多开? Logic will decide. 
        # 初始显示为单开模式 (User requested: "Switching between Single/Multi")
        # If button says "Single Open Mode", clicking it might switch to "Multi Open Mode"?
        # Or does the button text INDICATE current mode?
        # Let's assume text indicates current mode or what clicking will do.
        # Requirement: "If selected Multi... If Single..."
        # I will make it a Toggle Button.
        self.mode_btn.setStyleSheet("""
            QPushButton {
                background: #E0E0E0;
                color: #333;
                border: 1px solid #CCC;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QPushButton:checked {
                background: #666;
                color: white;
            }
        """)
        self.mode_btn.setText("多开模式") # Default to Multi as per "Default 4 per row" implication?
        self.mode_btn.setChecked(True)   # Default Checked = Multi
        self.mode_btn.clicked.connect(self.toggle_fill_mode)
        top_btns_layout.addWidget(self.mode_btn)

        # 通告广场
        plaza_btn = QPushButton("通告广场")
        plaza_btn.setStyleSheet(orange_btn_style)
        plaza_btn.clicked.connect(self.open_notice_plaza)
        top_btns_layout.addWidget(plaza_btn)

        # 窗口设置
        settings_btn = QPushButton("窗口设置")
        settings_btn.setStyleSheet(orange_btn_style)
        settings_btn.clicked.connect(self.open_window_settings)
        top_btns_layout.addWidget(settings_btn)
        
        top_btns_layout.addStretch()
        layout.addLayout(top_btns_layout)
        
        # 2. "我的链接" 和 "开始填充"
        mid_row_layout = QHBoxLayout()
        mid_row_layout.setContentsMargins(0, 10, 0, 10)
        
        links_title = QLabel("我的链接")
        links_title.setStyleSheet("""
            font-size: 16px;
            font-weight: 700;
            color: #1D1D1F;
        """)
        mid_row_layout.addWidget(links_title)
        
        mid_row_layout.addStretch()
        
        start_fill_btn = QPushButton("开始填充")
        start_fill_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        start_fill_btn.setStyleSheet("""
            QPushButton {
                background: #E6A23C;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover { background: #D99530; }
        """)
        start_fill_btn.clicked.connect(self.start_auto_fill)
        mid_row_layout.addWidget(start_fill_btn)
        
        layout.addLayout(mid_row_layout)
        
        # 3. 操作行 (图标工具栏)
        action_bar = QHBoxLayout()
        action_bar.setSpacing(4)
        action_bar.setContentsMargins(0, 4, 0, 4)
        
        def create_tool_btn(icon, color, tooltip, cb):
            btn = QPushButton()
            btn.setIcon(icon)
            btn.setFixedSize(32, 32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tooltip)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: 1px solid transparent;
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background: {color}15;
                    border-color: {color}30;
                }}
            """)
            btn.clicked.connect(cb)
            return btn

        # 全选
        btn_select = create_tool_btn(Icons.get('fa5s.check-square', '#007AFF'), '#007AFF', "全选链接", self.select_all_links)
        
        # 删除
        btn_delete = create_tool_btn(Icons.delete('#FF3B30'), '#FF3B30', "删除选中链接", self.delete_selected_links)
        
        # 复制
        btn_copy = create_tool_btn(Icons.copy('#007AFF'), '#007AFF', "复制选中链接", self.copy_selected_links)
        
        # 添加 (右侧)
        btn_add = create_tool_btn(Icons.add('#34C759'), '#34C759', "添加链接", self.open_link_manager)
        
        action_bar.addWidget(btn_select)
        action_bar.addWidget(btn_delete)
        action_bar.addWidget(btn_copy)
        action_bar.addStretch()
        action_bar.addWidget(btn_add)
        
        layout.addLayout(action_bar)
        
        # 4. 链接列表
        self.links_list = QListWidget()
        self.links_list.setFrameShape(QFrame.Shape.NoFrame)
        self.links_list.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
            }
            QListWidget::item {
                background: transparent;
                padding: 0px;
                margin-bottom: 4px;
            }
            QListWidget::item:hover {
                background: transparent;
            }
            QListWidget::item:selected {
                background: transparent;
            }
        """)
        self.links_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        
        layout.addWidget(self.links_list, 1)
        
        return sidebar
    
    def create_main_content(self) -> QWidget:
        """创建主内容区"""
        content = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(30)
        content.setLayout(layout)
        
        # 0. 账号状态警告横幅（过期或即将过期时显示）
        self.status_banner = self.create_status_banner()
        if self.status_banner:
            layout.addWidget(self.status_banner)
        
        # 1. Dashboard Header (Top Bar) - 现代化横幅设计
        header_container = QFrame()
        header_container.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                          stop:0 #FFFFFF, stop:1 #F5F7FA);
                border-radius: 20px;
                border: 1px solid #FFFFFF;
            }
        """)
        # 添加微妙阴影
        header_shadow = QGraphicsDropShadowEffect()
        header_shadow.setBlurRadius(20)
        header_shadow.setColor(QColor(0, 0, 0, 10))
        header_shadow.setOffset(0, 4)
        header_container.setGraphicsEffect(header_shadow)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(30, 24, 30, 24)
        header_container.setLayout(header_layout)
        
        # 左侧：问候语和日期
        welcome_vbox = QVBoxLayout()
        welcome_vbox.setSpacing(8)
        
        # 根据时间显示不同的问候
        from datetime import datetime
        hour = datetime.now().hour
        greeting = "早上好" if 5 <= hour < 12 else "下午好" if 12 <= hour < 18 else "晚上好"
        
        # 使用 Rich Text 增强排版
        user_name = self.current_user.username if self.current_user else '用户'
        welcome_label = QLabel(f"{greeting}，<span style='color:#007AFF'>{user_name}</span> 👋")
        welcome_label.setStyleSheet("""
            font-size: 28px;
            font-weight: 800;
            color: #1D1D1F;
            letter-spacing: -0.8px;
            border: none;
            background: transparent;
        """)
        
        date_label = QLabel(datetime.now().strftime("%Y年%m月%d日 · %A"))
        date_label.setStyleSheet("""
            font-size: 15px;
            font-weight: 500;
            color: #86868B;
            letter-spacing: 0.2px;
            border: none;
            background: transparent;
        """)
        
        welcome_vbox.addWidget(welcome_label)
        welcome_vbox.addWidget(date_label)
        
        # 添加账号状态信息
        status_info = self.create_user_status_label()
        if status_info:
            welcome_vbox.addWidget(status_info)
        
        header_layout.addLayout(welcome_vbox)
        
        header_layout.addStretch()
        
        # 右侧：Profile & Actions
        right_actions = QHBoxLayout()
        right_actions.setSpacing(16)
        
        # 消息按钮 (圆形，带背景)
        self.msg_btn = QPushButton()
        self.msg_btn.setIcon(Icons.bell('#1D1D1F'))
        self.msg_btn.setIconSize(QSize(20, 20))
        self.msg_btn.setFixedSize(44, 44)
        self.msg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.msg_btn.setStyleSheet("""
            QPushButton {
                background: white;
                border: 1px solid #E5E5EA;
                border-radius: 22px;
            }
            QPushButton:hover {
                background: #F5F5F7;
                border-color: #D1D1D6;
            }
        """)
        self.msg_btn.clicked.connect(self.show_pending_requests)
        
        # 消息红点徽章 - 显示待审批数量
        self.msg_badge = QLabel(self.msg_btn)
        self.msg_badge.setFixedSize(20, 20)
        self.msg_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.msg_badge.setStyleSheet("""
            background: #FF3B30; 
            border-radius: 10px; 
            border: 2px solid white;
            color: white;
            font-size: 10px;
            font-weight: bold;
        """)
        self.msg_badge.move(26, 2)
        self.msg_badge.hide()  # 默认隐藏，有消息时显示
        
        # 检查待审批请求数量
        self.update_message_badge()

        right_actions.addWidget(self.msg_btn)
        
        # 用户头像菜单
        user_avatar = UserAvatarMenu(self.current_user, self)
        right_actions.addWidget(user_avatar)
        
        header_layout.addLayout(right_actions)
        
        layout.addWidget(header_container)
        
        # 2. Statistics Dashboard (统计面板)
        stats_frame = self.create_statistics_panel()
        stats_frame.setObjectName('stats_panel')
        layout.addWidget(stats_frame)
        
        # 3. Recent Activity Section (最近活动)
        # 使用一个白色圆角卡片包裹表格
        table_container = QFrame()
        table_container.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #E5E5EA;
                border-radius: 24px;
            }
        """)
        # 添加阴影
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 12)) # 更加柔和
        shadow.setOffset(0, 8)
        table_container.setGraphicsEffect(shadow)
        
        table_layout = QVBoxLayout()
        table_layout.setContentsMargins(30, 30, 30, 30)
        table_layout.setSpacing(20)
        table_container.setLayout(table_layout)
        
        # 表格标题行
        table_header = QHBoxLayout()
        rec_title = QLabel("最近填写记录")
        rec_title.setStyleSheet("""
            font-size: 20px;
            font-weight: 700;
            color: #1D1D1F;
            letter-spacing: -0.5px;
            border: none;
        """)
        
        view_all_btn = QPushButton("查看全部")
        view_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        view_all_btn.setIcon(Icons.arrow_right(COLORS['primary']))
        view_all_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft) # 图标在右
        view_all_btn.setStyleSheet(f"""
            QPushButton {{
                color: {COLORS['primary']};
                background: transparent;
                border: none;
                font-weight: 600;
                font-size: 14px;
                padding: 8px 16px;
                border-radius: 8px;
            }}
            QPushButton:hover {{ 
                background: {COLORS['primary']}10;
            }}
        """)
        view_all_btn.clicked.connect(self.show_all_records)
        
        table_header.addWidget(rec_title)
        table_header.addStretch()
        table_header.addWidget(view_all_btn)
        table_layout.addLayout(table_header)
        
        # 使用自定义记录列表组件
        self.records_list = HomeRecordListWidget()
        table_layout.addWidget(self.records_list, 1)
        
        layout.addWidget(table_container, 1)
        
        return content

    def create_status_banner(self) -> QFrame:
        """创建账号状态警告横幅（过期或次数用尽时显示） - 高级 UI 设计版"""
        if not self.current_user:
            return None
            
        from core.auth import get_user_status_info
        status = get_user_status_info(self.current_user)
        
        # 管理员不显示
        if status['is_admin']:
            return None
            
        # 判断是否需要显示警告
        show_warning = False
        warning_type = None  # 'expired', 'expiring_soon', 'usage_exhausted', 'usage_low'
        main_title = ""
        sub_desc = ""
        
        if status['is_expired']:
            show_warning = True
            warning_type = 'expired'
            main_title = "您的账号会员权益已过期"
            sub_desc = f"过期时间：{status['expire_time_str']}，为了不影响您的正常使用，请尽快续费"
        elif status['usage_exhausted']:
            show_warning = True
            warning_type = 'usage_exhausted'
            main_title = "您的今日使用次数已耗尽"
            sub_desc = f"当前使用：{status['usage_count']}/{status['max_usage_count']}次，升级会员可解锁更多次数"
        elif status['days_remaining'] is not None and status['days_remaining'] <= 7:
            show_warning = True
            warning_type = 'expiring_soon'
            main_title = f"您的会员权益将在 {status['days_remaining']} 天后到期"
            sub_desc = f"有效期至：{status['expire_time_str']}，提前续费可享无缝服务体验"
        elif not status['usage_unlimited']:
            remaining = status['max_usage_count'] - status['usage_count']
            if remaining <= 10:
                show_warning = True
                warning_type = 'usage_low'
                main_title = f"剩余使用次数不足 {remaining} 次"
                sub_desc = f"当前进度：{status['usage_count']}/{status['max_usage_count']}，请注意及时补充次数"
        
        if not show_warning:
            return None
        
        # 设计主题配置
        if warning_type in ['expired', 'usage_exhausted']:
            # 红色/危险主题
            theme = {
                'bg_gradient': 'qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FEF2F2, stop:1 #FFF5F5)',
                'border': '#FECACA',
                'accent': '#EF4444',     # 图标和按钮色
                'text_main': '#991B1B',  # 深红文字
                'text_sub': '#B91C1C',   # 稍浅红文字
                'icon': '⛔',
                'btn_bg': '#EF4444',
                'btn_text': 'white',
                'btn_hover': '#DC2626'
            }
        else:
            # 橙色/警告主题
            theme = {
                'bg_gradient': 'qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FFFBEB, stop:1 #FFF7ED)',
                'border': '#FDE68A',
                'accent': '#F59E0B',     # 琥珀色
                'text_main': '#92400E',  # 深琥珀文字
                'text_sub': '#B45309',   # 稍浅
                'icon': '👑',
                'btn_bg': '#F59E0B',
                'btn_text': 'white',
                'btn_hover': '#D97706'
            }
        
        banner = QFrame()
        # 阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 10))
        shadow.setOffset(0, 4)
        banner.setGraphicsEffect(shadow)
        
        banner.setStyleSheet(f"""
            QFrame {{
                background: {theme['bg_gradient']};
                border: 1px solid {theme['border']};
                border-radius: 16px;
            }}
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        banner.setLayout(layout)
        
        # 1. 左侧图标容器
        icon_container = QLabel(theme['icon'])
        icon_container.setFixedSize(48, 48)
        icon_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 使用半透明背景色作为图标底色
        icon_bg_color = theme['accent']
        icon_container.setStyleSheet(f"""
            QLabel {{
                background-color: {icon_bg_color}20;  /* 20% 透明度 */
                color: {theme['accent']};
                border-radius: 24px;
                font-size: 24px;
                border: none;
            }}
        """)
        layout.addWidget(icon_container)
        
        # 2. 中间文本区域
        text_container = QWidget()
        text_container.setStyleSheet("background: transparent; border: none;")
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 2, 0, 2)
        text_layout.setSpacing(4)
        text_container.setLayout(text_layout)
        
        # 主标题
        title_label = QLabel(main_title)
        title_label.setStyleSheet(f"""
            color: {theme['text_main']};
            font-size: 16px;
            font-weight: 700;
            background: transparent;
            border: none;
        """)
        text_layout.addWidget(title_label)
        
        # 副标题
        desc_label = QLabel(sub_desc)
        desc_label.setStyleSheet(f"""
            color: {theme['text_sub']};
            font-size: 13px;
            font-weight: 500;
            background: transparent;
            border: none;
            opacity: 0.9;
        """)
        text_layout.addWidget(desc_label)
        
        layout.addWidget(text_container, 1) # 伸缩因子1，占据剩余空间
        
        # 3. 右侧操作按钮
        action_btn = QPushButton("立即续费")
        action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        action_btn.setFixedSize(100, 36)
        action_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['btn_bg']};
                color: {theme['btn_text']};
                border: none;
                border-radius: 18px;
                font-weight: 600;
                font-size: 13px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {theme['btn_hover']};
                margin-top: 1px; /* 轻微按压感 */
            }}
        """)
        action_btn.clicked.connect(self.show_contact_info)
        layout.addWidget(action_btn)
        
        return banner
    
    def create_user_status_label(self) -> QLabel:
        """创建用户状态信息标签"""
        if not self.current_user:
            return None
            
        from core.auth import get_user_status_info
        status = get_user_status_info(self.current_user)
        
        # 管理员显示特殊标识
        if status['is_admin']:
            label = QLabel("👑 管理员账号 · 无限制")
            label.setStyleSheet("""
                font-size: 13px;
                font-weight: 500;
                color: #007AFF;
                background: transparent;
                border: none;
            """)
            return label
        
        # 构建状态文本
        parts = []
        
        # 过期时间
        if status['is_expired']:
            parts.append(f"❌ 已过期")
        elif status['days_remaining'] is not None:
            if status['days_remaining'] <= 7:
                parts.append(f"⚠️ {status['days_remaining']}天后到期")
            else:
                parts.append(f"📅 到期：{status['expire_time_str']}")
        else:
            parts.append("📅 永不过期")
        
        # 使用次数
        if status['usage_exhausted']:
            parts.append(f"❌ 次数已用尽")
        elif status['usage_unlimited']:
            parts.append("🔄 不限次数")
        else:
            remaining = status['max_usage_count'] - status['usage_count']
            parts.append(f"🔄 剩余{remaining}次")
        
        status_text = " · ".join(parts)
        
        # 根据状态设置颜色
        if status['is_expired'] or status['usage_exhausted']:
            color = "#DC2626"
        elif (status['days_remaining'] is not None and status['days_remaining'] <= 7) or \
             (not status['usage_unlimited'] and status['max_usage_count'] - status['usage_count'] <= 10):
            color = "#D97706"
        else:
            color = "#86868B"
        
        label = QLabel(status_text)
        label.setStyleSheet(f"""
            font-size: 13px;
            font-weight: 500;
            color: {color};
            background: transparent;
            border: none;
        """)
        return label
    
    def show_contact_info(self):
        """显示联系客服信息"""
        wechat = SystemConfig.get('CONTACT_WECHAT', 'your_wechat_id')
        email = SystemConfig.get('CONTACT_EMAIL', 'your_email@example.com')
        phone = SystemConfig.get('CONTACT_PHONE', '138-0000-0000')
        work_hours = SystemConfig.get('CONTACT_WORK_HOURS', '周一至周五 9:00-18:00')
        
        QMessageBox.information(
            self,
            "联系客服",
            "请通过以下方式联系客服续费：\n\n"
            f"📱 微信：{wechat}\n"
            f"📧 邮箱：{email}\n"
            f"📞 电话：{phone}\n\n"
            f"工作时间：{work_hours}"
        )

    def create_statistics_panel(self) -> QFrame:
        """创建统计面板 - 现代 Dashboard 风格"""
        frame = QFrame()
        layout = QHBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(0, 0, 0, 0)
        frame.setLayout(layout)
        
        # 获取当前用户的统计数据
        stats = self.db_manager.get_statistics(user=self.current_user)
        
        # 计算真实的子文本
        active_links = stats.get('active_links', 0)
        today_records = stats.get('today_records', 0)
        success_rate = stats.get('success_rate', 0)
        
        # 使用 qtawesome 图标 - 显示真实数据
        stat_items = [
            ("名片总数", stats['total_cards'], 'fa5s.address-card', "#007AFF", ""),
            ("链接总数", stats['total_links'], 'fa5s.link', "#34C759", f"活跃 {active_links}" if active_links > 0 else ""),
            ("填写记录", stats['total_records'], 'fa5s.chart-bar', "#5856D6", f"今日 +{today_records}" if today_records > 0 else ""),
            ("成功次数", stats['success_records'], 'fa5s.check-circle', "#FF9500", f"成功率 {success_rate}%" if stats['total_records'] > 0 else "")
        ]
        
        for label, value, icon, color, subtext in stat_items:
            card = self.create_dashboard_card(label, value, icon, color, subtext)
            layout.addWidget(card)
            
        return frame

    def create_dashboard_card(self, label, value, icon_name, color, subtext) -> QFrame:
        """创建单个仪表盘卡片 - 极简现代风格"""
        card = QFrame()
        card.setMinimumHeight(140)
        card.setStyleSheet(f"""
            QFrame {{
                background: white;
                border: 1px solid white;
                border-radius: 24px;
            }}
            QFrame:hover {{
                background: #FFFFFF;
                border: 1px solid {color}40;
            }}
        """)
        
        # 阴影
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 10))
        shadow.setOffset(0, 6)
        card.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(8)
        card.setLayout(layout)
        
        # Top Section: Icon & Trend
        top_row = QHBoxLayout()
        
        # Icon Container
        icon_btn = QPushButton()
        icon_btn.setIcon(Icons.get(icon_name, color))
        icon_btn.setIconSize(QSize(24, 24))
        icon_btn.setFixedSize(48, 48)
        icon_btn.setFlat(True)
        icon_btn.setStyleSheet(f"""
            background: {color}15;
            border: none;
            border-radius: 16px;
            text-align: center;
        """)
        
        top_row.addWidget(icon_btn)
        top_row.addStretch()
        
        # Trend / Subtext Pill
        if subtext:
            trend_lbl = QLabel(subtext)
            trend_lbl.setStyleSheet(f"""
                font-size: 12px;
                font-weight: 600;
                color: {color};
                background: {color}10;
                border-radius: 12px;
                padding: 4px 10px;
            """)
            top_row.addWidget(trend_lbl)
            
        layout.addLayout(top_row)
        
        layout.addSpacing(10)
        
        # Value Section
        value_label = QLabel(str(value))
        value_label.setStyleSheet("""
            font-size: 36px;
            font-weight: 800;
            color: #1D1D1F;
            letter-spacing: -1px;
            border: none; background: transparent;
        """)
        layout.addWidget(value_label)
        
        # Label Section
        label_lbl = QLabel(label)
        label_lbl.setStyleSheet("""
            font-size: 14px;
            font-weight: 500;
            color: #86868B;
            border: none; background: transparent;
        """)
        layout.addWidget(label_lbl)
        
        return card

    def create_stat_item(self, icon: str, label: str, value: int, color: str, light_color: str = None) -> QWidget:
        """(Deprecated) 旧的统计项方法，保留以防万一被其他地方调用，但 create_statistics_panel 已不再使用它"""
        return self.create_dashboard_card(label, value, icon, color, "")
    
    def create_feature_button(self, title: str, description: str, color: str) -> QPushButton:
        """创建功能按钮 - 现代渐变卡片设计"""
        # 组合标题和描述文本
        button_text = f"{title}\n{description}"
        btn = QPushButton(button_text)
        
        # 设置按钮样式 - 现代化渐变设计
        btn.setMinimumHeight(140)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 {color}, 
                                            stop:1 {self._darken_color(color, 0.15)});
                color: white;
                border: none;
                border-radius: 18px;
                padding: 28px 24px;
                text-align: left;
                font-size: 16px;
                font-weight: 700;
                line-height: 1.8;
                letter-spacing: 0.3px;
            }}
            
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 {self._lighten_color(color)}, 
                                            stop:1 {color});
            }}
            
            QPushButton:pressed {{
                background: {self._darken_color(color, 0.2)};
                padding-top: 30px;
                padding-bottom: 26px;
            }}
        """)
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 35))
        shadow.setOffset(0, 4)
        btn.setGraphicsEffect(shadow)
        
        return btn
    
    def _lighten_color(self, color: str) -> str:
        """使颜色变亮"""
        if color == COLORS['primary']:
            return COLORS['primary_light']
        elif color == COLORS['success']:
            return COLORS['success_light']
        elif color == COLORS['warning']:
            return COLORS['warning_light']
        return color
    
    def _darken_color(self, color: str, amount: float) -> str:
        """使颜色变暗"""
        # 简单的颜色变暗处理
        if color == COLORS['primary']:
            return COLORS['primary_dark'] if amount < 0.18 else '#003D99'
        elif color == COLORS['success']:
            return '#28A745' if amount < 0.18 else '#1E7E34'
        elif color == COLORS['warning']:
            return '#E68A00' if amount < 0.18 else '#CC7A00'
        return color
    
    def refresh_data(self):
        """刷新数据"""
        # 刷新统计信息
        self.update_statistics()
        
        # 刷新名片列表
        self.refresh_cards_list()
        
        # 刷新链接列表
        self.refresh_links_list()
        
        # 刷新记录列表（使用自定义组件）
        records = self.db_manager.get_fill_records(limit=20, user=self.current_user)
        self.records_list.set_records(records)
    
    def refresh_cards_list(self):
        """刷新名片列表 - 按分类显示，支持拖拽排序"""
        # 清空现有内容
        self.card_widgets.clear()
        self.category_widgets.clear()
        
        # 清空布局
        while self.cards_container_layout.count():
            item = self.cards_container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 获取当前用户的名片
        cards = self.db_manager.get_all_cards(user=self.current_user)
        
        # 如果没有名片，显示空状态
        if not cards:
            empty_widget = self.create_empty_state(
                icon="fa5s.address-card",
                title="暂无名片",
                subtitle="点击上方「添加名片」按钮创建您的第一张名片",
                color="#007AFF"
            )
            self.cards_container_layout.addWidget(empty_widget)
            self.cards_container_layout.addStretch()
            return
        
        # 按分类分组
        cards_by_category = defaultdict(list)
        for card in cards:
            category = card.category if hasattr(card, 'category') and card.category else "默认分类"
            cards_by_category[category].append(card)
        
        # 为每个分类创建可折叠组件
        for category, category_cards in sorted(cards_by_category.items()):
            # 按 order 字段排序名片（order 越小越靠前）
            sorted_cards = sorted(category_cards, key=lambda c: getattr(c, 'order', 0) or 0)
            
            # 创建分类组件
            category_widget = CollapsibleCategoryWidget(category)
            self.category_widgets[category] = category_widget
            
            # 连接分类管理信号
            category_widget.rename_clicked.connect(self.rename_category)
            category_widget.delete_clicked.connect(self.delete_category)
            
            # 创建可拖拽宫格容器
            grid_container = DraggableCardGrid()
            grid_container.order_changed.connect(self.on_cards_order_changed)
            
            # 添加名片到宫格
            for card in sorted_cards:
                card_widget = CardItemWidget(card)
                card_widget.edit_clicked.connect(self.edit_card)
                card_widget.delete_clicked.connect(self.delete_card)
                card_widget.selection_changed.connect(self.on_card_selection_changed)
                
                grid_container.add_card_widget(card_widget)
                
                # 存储
                self.card_widgets.append(card_widget)
                category_widget.card_widgets.append(card_widget)
            
            category_widget.set_content_widget(grid_container)
            self.cards_container_layout.addWidget(category_widget)
        
        self.cards_container_layout.addStretch()
    
    def refresh_links_list(self):
        """刷新链接列表"""
        self.links_list.clear()
        
        # 移除旧的空状态占位组件（如果有）
        if hasattr(self, 'links_empty_widget') and self.links_empty_widget:
            self.links_empty_widget.setParent(None)
            self.links_empty_widget.deleteLater()
            self.links_empty_widget = None
        
        # 获取所有链接
        links = self.db_manager.get_all_links(user=self.current_user)
        
        # 如果没有链接，显示空状态
        if not links:
            self.links_empty_widget = self.create_empty_state(
                icon="fa5s.link",
                title="暂无链接",
                subtitle="点击「添加链接」按钮添加表单链接",
                color="#34C759"
            )
            # 将空状态添加到 links_list 的父容器中
            parent_layout = self.links_list.parent().layout()
            if parent_layout:
                parent_layout.addWidget(self.links_empty_widget)
            return
        
        for i, link in enumerate(links, 1):
            # 创建列表项 Widget
            row_widget = self.create_link_row_widget(i, link)
            
            # 创建 QListWidgetItem 并设置大小提示
            item = QListWidgetItem(self.links_list)
            item.setSizeHint(row_widget.sizeHint())
            # 存储 link 数据到 item 中，方便查找
            item.setData(Qt.ItemDataRole.UserRole, link)
            
            self.links_list.addItem(item)
            self.links_list.setItemWidget(item, row_widget)
            
    def create_link_row_widget(self, index, link):
        """创建链接列表行组件"""
        widget = QWidget()
        widget.setMinimumHeight(40)
        layout = QHBoxLayout()
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(12)
        widget.setLayout(layout)
        
        # 序号
        index_label = QLabel(str(index))
        index_label.setFixedWidth(24)
        index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        index_label.setStyleSheet("color: #606266; font-weight: bold;")
        layout.addWidget(index_label)
        
        # 复选框 (圆形样式)
        checkbox = QCheckBox()
        checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 1px solid #DCDFE6;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #E6A23C;
                border-color: #E6A23C;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEgNEw0LjUgNy41TDExIDEiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+PC9zdmc+);
            }
            QCheckBox::indicator:hover {
                border-color: #E6A23C;
            }
        """)
        layout.addWidget(checkbox)
        
        # 链接 URL (蓝色)
        # 优先显示标题，如果没有标题则显示 URL
        display_text = link.name if link.name and link.name.strip() else link.url
        
        # 简单的截断逻辑
        if len(display_text) > 35:
            display_text = display_text[:32] + "..."
            
        link_label = QLabel(display_text)
        link_label.setStyleSheet("color: #409EFF;")
        link_label.setToolTip(f"{link.name}\n{link.url}") # ToolTip显示完整信息
        layout.addWidget(link_label, 1) # stretch
        
        # 复制按钮
        copy_btn = QPushButton()
        copy_btn.setIcon(Icons.copy('primary'))
        copy_btn.setFixedSize(28, 28)
        copy_btn.setToolTip("复制链接")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
                padding: 4px;
            }
            QPushButton:hover {
                background: #ECF5FF;
                border-color: #409EFF;
            }
            QPushButton:pressed {
                background: #D9ECFF;
            }
        """)
        # 使用 functools.partial 或 lambda 绑定参数
        copy_btn.clicked.connect(lambda checked, u=link.url: self.copy_link_url(u))
        layout.addWidget(copy_btn)
        
        # 将 checkbox 绑定到 widget 属性，方便后续获取状态
        widget.checkbox = checkbox
        widget.link_data = link
        
        return widget

    def copy_link_url(self, url):
        """复制链接"""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(url)

    
    def update_statistics(self):
        """更新统计信息"""
        # 在主内容区找到统计面板并替换
        if hasattr(self, 'main_content') and self.main_content:
            layout = self.main_content.layout()
            if layout:
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item and item.widget():
                        widget = item.widget()
                        if hasattr(widget, 'objectName') and widget.objectName() == 'stats_panel':
                            # 移除旧面板
                            widget.setParent(None)
                            widget.deleteLater()
                            # 创建新面板
                            stats_frame = self.create_statistics_panel()
                            stats_frame.setObjectName('stats_panel')
                            layout.insertWidget(i, stats_frame)
                            return
        
        # 如果上面没找到，尝试在 centralWidget 中查找（兼容旧布局）
        layout = self.centralWidget().layout()
        if layout:
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if hasattr(widget, 'objectName') and widget.objectName() == 'stats_panel':
                        widget.setParent(None)
                        widget.deleteLater()
                        stats_frame = self.create_statistics_panel()
                        stats_frame.setObjectName('stats_panel')
                        layout.insertWidget(i, stats_frame)
                        return
    
    def update_message_badge(self):
        """更新消息徽章数量"""
        if not self.current_user:
            return
        
        try:
            count = DatabaseManager.get_unread_notifications_count(self.current_user)
            if count > 0:
                self.msg_badge.setText(str(count) if count < 100 else "99+")
                self.msg_badge.show()
            else:
                self.msg_badge.hide()
        except Exception as e:
            print(f"更新消息徽章失败: {e}")
            self.msg_badge.hide()
    
    def show_pending_requests(self):
        """显示消息中心"""
        if not self.current_user:
            QMessageBox.warning(self, "提示", "请先登录")
            return
        
        # 显示消息中心
        dialog = MessageCenterDialog(self.current_user, self)
        dialog.exec()
        
        # 刷新徽章和数据
        self.update_message_badge()
        self.refresh_data()
    
    def open_auto_fill(self):
        """打开自动填写窗口"""
        if self.auto_fill_window is None or not self.auto_fill_window.isVisible():
            self.auto_fill_window = AutoFillWindow(self, current_user=self.current_user)
            self.auto_fill_window.fill_completed.connect(self.refresh_data)
        self.auto_fill_window.show()
        self.auto_fill_window.raise_()
        self.auto_fill_window.activateWindow()
    
    def open_card_manager(self):
        """打开名片管理"""
        dialog = CardManagerDialog(self, current_user=self.current_user)
        if dialog.exec():
            self.refresh_data()
    
    def open_link_manager(self):
        """打开链接管理"""
        dialog = LinkManagerDialog(self, current_user=self.current_user)
        dialog.exec()
        # Always refresh data when dialog closes, as modifications are instant in the manager
        self.refresh_data()
            
    def open_notice_plaza(self):
        """打开通告广场"""
        if self.notice_plaza_window is None or not self.notice_plaza_window.isVisible():
            self.notice_plaza_window = NoticePlazaWindow(self)
        self.notice_plaza_window.show()
        self.notice_plaza_window.raise_()
        self.notice_plaza_window.activateWindow()
    
    def open_admin_panel(self):
        """打开管理后台"""
        if not self.current_user or not self.current_user.is_admin():
            QMessageBox.warning(self, "权限不足", "只有管理员才能访问用户管理功能")
            return
        
        dialog = AdminWindow(self.current_user, self)
        dialog.exec()
    
    def closeEvent(self, event):
        """窗口关闭时停止消息轮询定时器"""
        if hasattr(self, 'message_timer'):
            self.message_timer.stop()
        event.accept()
    
    def create_empty_state(self, icon: str, title: str, subtitle: str, color: str) -> QWidget:
        """创建空状态占位组件
        
        Args:
            icon: qtawesome 图标名称
            title: 标题文字
            subtitle: 副标题/描述文字
            color: 主题颜色
        
        Returns:
            空状态组件
        """
        widget = QWidget()
        widget.setMinimumHeight(200)
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        widget.setLayout(layout)
        
        # 图标
        icon_label = QPushButton()
        icon_label.setIcon(Icons.get(icon, color))
        icon_label.setIconSize(QSize(64, 64))
        icon_label.setFixedSize(100, 100)
        icon_label.setFlat(True)
        icon_label.setStyleSheet(f"""
            QPushButton {{
                background: {color}10;
                border: none;
                border-radius: 50px;
            }}
        """)
        icon_label.setEnabled(False)
        
        # 创建居中容器
        icon_container = QHBoxLayout()
        icon_container.addStretch()
        icon_container.addWidget(icon_label)
        icon_container.addStretch()
        layout.addLayout(icon_container)
        
        # 标题
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: 600;
            color: #1D1D1F;
            border: none;
            background: transparent;
        """)
        layout.addWidget(title_label)
        
        # 副标题
        subtitle_label = QLabel(subtitle)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setWordWrap(True)
        subtitle_label.setStyleSheet("""
            font-size: 14px;
            color: #86868B;
            border: none;
            background: transparent;
        """)
        layout.addWidget(subtitle_label)
        
        return widget
    
    def switch_account(self):
        """切换账号"""
        reply = QMessageBox.question(
            self,
            "切换账号",
            "确定要切换账号吗？\n\n当前账号将退出登录，您需要重新登录。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 清除保存的 token
            from core.auth import clear_token
            clear_token()
            
            # 显示登录窗口
            from gui.login_window import LoginWindow
            login_window = LoginWindow()
            result = login_window.exec()
            
            if result == 1:  # 1 表示 Accepted（登录成功）
                # 获取登录用户
                new_user = login_window.get_current_user()
                if new_user:
                    print(f"✅ 切换到用户: {new_user.username}")
                    
                    # 关闭当前窗口
                    self.close()
                    
                    # 根据用户角色显示不同的窗口
                    from PyQt6.QtWidgets import QApplication
                    app = QApplication.instance()
                    
                    if new_user.is_admin():
                        # 管理员：显示管理后台界面
                        from gui.admin_main_window import AdminMainWindow
                        new_window = AdminMainWindow(current_user=new_user)
                    else:
                        # 普通用户：显示表单填写界面
                        new_window = MainWindow(current_user=new_user)
                    
                    # 将新窗口保存到应用程序对象，防止被垃圾回收
                    app._main_window = new_window
                    new_window.show()
            else:
                # 用户取消登录，退出程序
                import sys
                sys.exit(0)

    # ====================
    #  查看全部记录
    # ====================
    
    def show_all_records(self):
        """显示所有填写记录的对话框"""
        dialog = AllRecordsDialog(self, self.db_manager, self.current_user)
        dialog.exec()

    # ====================
    #  恢复丢失的逻辑方法
    # ====================

    def get_sidebar_button_style(self, color: str) -> str:
        """获取侧边栏按钮样式"""
        return f"""
            QPushButton {{
                background: {color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
        """
    
    def get_text_button_style(self) -> str:
        """获取文本按钮样式"""
        return """
            QPushButton {
                background: transparent;
                color: #007AFF;
                border: none;
                padding: 4px 8px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """
    
    # 名片相关方法
    def open_add_card_dialog(self):
        """打开添加名片对话框"""
        dialog = AddCardDialog(self, db_manager=self.db_manager, current_user=self.current_user)
        if dialog.exec():
            self.refresh_data()
    
    def add_new_field(self):
        """新增字段 - 从字段库选择字段添加到名片（支持多选名片）
        
        每个选中的字段作为一个独立字段添加到名片（字段库里的字段本身可能包含多个别名用顿号分隔）
        例如：选择 "B站链接" (包含 "B站链接、B站主页链接") 和 "B站粉丝"
        会添加两个字段到名片：
        1. "B站链接、B站主页链接"
        2. "B站粉丝"
        """
        # 获取当前用户的名片
        cards = self.db_manager.get_all_cards(user=self.current_user)
        
        if not cards:
            QMessageBox.warning(self, "提示", "请先创建一个名片")
            return
        
        # 打开字段库选择对话框
        dialog = FieldLibraryDialog(self.db_manager, cards, self)
        if dialog.exec():
            selected_fields = dialog.get_selected_fields()
            selected_cards = dialog.get_selected_cards()  # 多选名片
            
            if selected_fields and selected_cards:
                try:
                    card_results = []
                    
                    # 遍历每个选中的名片
                    for selected_card in selected_cards:
                        # 获取当前名片的配置
                        current_configs = []
                        if hasattr(selected_card, 'configs') and selected_card.configs:
                            for config in selected_card.configs:
                                if isinstance(config, dict):
                                    current_configs.append(config)
                                else:
                                    current_configs.append({
                                        'key': config.key,
                                        'value': config.value
                                    })
                        
                        # 收集现有的所有字段名（用于去重检查）
                        existing_keys = set()
                        for config in current_configs:
                            keys = config.get('key', '').split('、')
                            for k in keys:
                                existing_keys.add(k.strip().lower())
                        
                        added_count = 0
                        # 遍历每个选中的字段，每个字段单独添加
                        for field in selected_fields:
                            # 检查该字段是否与现有字段有重复
                            field_names = field.name.split('、')
                            is_duplicate = False
                            for name in field_names:
                                if name.strip().lower() in existing_keys:
                                    is_duplicate = True
                                    break
                            
                            if not is_duplicate:
                                # 添加该字段（保持字段库中的完整名称，包含所有别名）
                                current_configs.append({
                                    'key': field.name,  # 使用字段库中的完整名称
                                    'value': field.default_value or ''
                                })
                                # 更新已存在集合
                                for name in field_names:
                                    existing_keys.add(name.strip().lower())
                                added_count += 1
                        
                        # 更新名片
                        if added_count > 0:
                            self.db_manager.update_card(
                                card_id=str(selected_card.id),
                                configs=current_configs
                            )
                            card_results.append(f"「{selected_card.name}」+{added_count}个字段")
                        else:
                            card_results.append(f"「{selected_card.name}」字段已存在")
                    
                    # 显示结果
                    success_count = sum(1 for r in card_results if '+' in r)
                    if success_count > 0:
                        # 显示添加的字段列表
                        field_names_display = '\n'.join([f"  • {f.name}" for f in selected_fields])
                        result_msg = f"添加成功！\n\n添加的字段：\n{field_names_display}\n\n" + "\n".join(card_results)
                        QMessageBox.information(self, "成功", result_msg)
                        self.refresh_data()
                    else:
                        QMessageBox.information(self, "提示", "所选字段已存在于所有选中的名片中")
                        
                except Exception as e:
                    QMessageBox.warning(self, "失败", f"添加字段失败：{str(e)}")
    
    def add_new_category(self):
        """新增分类"""
        dialog = AddCategoryDialog(self)
        if dialog.exec():
            category_name = dialog.get_category_name()
            if category_name:
                # 创建真正的分类记录
                try:
                    category = self.db_manager.create_user_category(
                        user=self.current_user,
                        name=category_name,
                        description=f"用户创建的分类"
                    )
                    if category:
                        QMessageBox.information(self, "成功", f"分类 \"{category_name}\" 创建成功！")
                        self.refresh_data()
                    else:
                        QMessageBox.warning(self, "提示", f"分类 \"{category_name}\" 已存在")
                except Exception as e:
                    QMessageBox.warning(self, "失败", f"创建分类失败：{str(e)}")
    
    def select_all_cards(self):
        """全选名片"""
        for card_widget in self.card_widgets:
            card_widget.set_selected(True)
    
    def deselect_all_cards(self):
        """取消全选名片"""
        for card_widget in self.card_widgets:
            card_widget.set_selected(False)
    
    def edit_card(self, card):
        """编辑名片"""
        # 打开添加名片对话框进行编辑
        dialog = AddCardDialog(self, db_manager=self.db_manager, current_user=self.current_user, card=card)
        if dialog.exec():
            self.refresh_data()
    
    def delete_card(self, card):
        """删除名片"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除名片 \"{card.name}\" 吗？\n\n删除后无法恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 转换 ObjectId 为字符串
            card_id = str(card.id)
            if self.db_manager.delete_card(card_id):
                QMessageBox.information(self, "成功", "名片删除成功！")
                self.refresh_data()
            else:
                QMessageBox.warning(self, "失败", "名片删除失败！")
    
    def rename_category(self, old_name: str):
        """重命名分类"""
        from database.models import Card, Category
        
        new_name, ok = QInputDialog.getText(
            self,
            "重命名分类",
            "请输入新的分类名称:",
            QLineEdit.EchoMode.Normal,
            old_name
        )
        
        if ok and new_name.strip() and new_name.strip() != old_name:
            new_name = new_name.strip()
            
            # 检查新名称是否已存在
            existing_cards = Card.objects(user=self.current_user, category=new_name).count()
            if existing_cards > 0:
                reply = QMessageBox.question(
                    self,
                    "分类已存在",
                    f"分类 '{new_name}' 已存在，是否合并到该分类？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            try:
                # 更新该分类下所有名片的分类名称
                cards = Card.objects(user=self.current_user, category=old_name)
                count = 0
                for card in cards:
                    card.category = new_name
                    card.save()
                    count += 1
                
                # 更新 Category 模型（如果存在）
                category_obj = Category.objects(user=self.current_user, name=old_name).first()
                if category_obj:
                    # 检查新名称的 Category 是否已存在
                    existing_category = Category.objects(user=self.current_user, name=new_name).first()
                    if existing_category:
                        # 如果新名称的 Category 已存在，删除旧的
                        category_obj.delete()
                    else:
                        # 否则重命名
                        category_obj.name = new_name
                        category_obj.save()
                
                QMessageBox.information(self, "成功", f"已将分类 '{old_name}' 重命名为 '{new_name}'，共 {count} 个名片")
                self.refresh_data()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"重命名分类失败: {str(e)}")
    
    def delete_category(self, category_name: str):
        """删除分类"""
        from database.models import Card, Category
        
        # 检查该分类下是否有名片
        cards_count = Card.objects(user=self.current_user, category=category_name).count()
        
        if cards_count > 0:
            # 自定义删除确认对话框
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("确认删除分类")
            msg_box.setText(f"分类 '{category_name}' 下有 {cards_count} 个名片")
            msg_box.setInformativeText("删除后这些名片将移动到「默认分类」。是否继续？")
            msg_box.setIcon(QMessageBox.Icon.Warning)
            
            # 自定义按钮
            btn_yes = msg_box.addButton("确定删除", QMessageBox.ButtonRole.YesRole)
            btn_yes.setIcon(qta.icon('fa5s.check', color='#FF3B30'))
            btn_no = msg_box.addButton("取消", QMessageBox.ButtonRole.NoRole)
            btn_no.setIcon(qta.icon('fa5s.times', color='#666'))
            
            msg_box.setDefaultButton(btn_no)
            
            # 设置样式
            msg_box.setStyleSheet("""
                QMessageBox {
                    background: white;
                }
                QPushButton {
                    min-width: 90px;
                    padding: 8px 16px;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: 600;
                }
            """)
            
            msg_box.exec()
            
            if msg_box.clickedButton() == btn_yes:
                try:
                    # 将名片移动到默认分类
                    cards = Card.objects(user=self.current_user, category=category_name)
                    for card in cards:
                        card.category = '默认分类'
                        card.save()
                    
                    # 删除数据库中的分类记录
                    category_obj = Category.objects(user=self.current_user, name=category_name).first()
                    if category_obj:
                        category_obj.delete()
                    
                    QMessageBox.information(self, "成功", f"已将 {cards_count} 个名片移动到「默认分类」")
                    self.refresh_data()
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"删除分类失败: {str(e)}")
        else:
            # 空分类，确认后直接删除
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除空分类 '{category_name}' 吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    category_obj = Category.objects(user=self.current_user, name=category_name).first()
                    if category_obj:
                        category_obj.delete()
                    QMessageBox.information(self, "成功", f"分类 '{category_name}' 已删除")
                    self.refresh_data()
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"删除分类失败: {str(e)}")
    
    def on_card_selection_changed(self, card, is_selected):
        """名片选中状态变化"""
        # 这里可以添加选中后的逻辑
        pass
    
    def on_cards_order_changed(self, order_list):
        """名片排序变化 - 保存到数据库
        
        Args:
            order_list: [{'id': card_id, 'order': order}, ...]
        """
        if self.db_manager.update_cards_order(order_list):
            print(f"✅ 名片排序已保存，共 {len(order_list)} 个名片")
        else:
            QMessageBox.warning(self, "提示", "保存排序失败，请重试")
    
    def get_selected_cards(self):
        """获取选中的名片"""
        return [widget.card for widget in self.card_widgets if widget.is_selected]
    
    def get_selected_links(self):
        """获取选中的链接"""
        links = []
        for i in range(self.links_list.count()):
            item = self.links_list.item(i)
            widget = self.links_list.itemWidget(item)
            if widget and hasattr(widget, 'checkbox') and widget.checkbox.isChecked():
                if hasattr(widget, 'link_data'):
                    links.append(widget.link_data)
        return links
    
    # 链接相关方法
    def select_all_links(self):
        """全选/取消全选链接"""
        count = self.links_list.count()
        if count == 0:
            return
        
        # 检查是否已经全部选中
        is_all_checked = True
        for i in range(count):
            item = self.links_list.item(i)
            widget = self.links_list.itemWidget(item)
            if widget and hasattr(widget, 'checkbox') and not widget.checkbox.isChecked():
                is_all_checked = False
                break
        
        # 切换状态
        target_state = not is_all_checked
        
        for i in range(count):
            item = self.links_list.item(i)
            widget = self.links_list.itemWidget(item)
            if widget and hasattr(widget, 'checkbox'):
                widget.checkbox.setChecked(target_state)
    
    def get_selected_links(self):
        """获取选中的链接列表"""
        selected_links = []
        for i in range(self.links_list.count()):
            item = self.links_list.item(i)
            widget = self.links_list.itemWidget(item)
            if widget and hasattr(widget, 'checkbox') and widget.checkbox.isChecked():
                if hasattr(widget, 'link_data'):
                    selected_links.append(widget.link_data)
        return selected_links
    
    def delete_selected_links(self):
        """删除选中的链接"""
        selected_links = self.get_selected_links()
        
        if not selected_links:
            QMessageBox.information(self, "提示", "请先选择要删除的链接")
            return
        
        # 确认删除
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除选中的 {len(selected_links)} 个链接吗？\n\n此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success_count = 0
            fail_count = 0
            
            for link in selected_links:
                try:
                    self.db_manager.delete_link(str(link.id))
                    success_count += 1
                except Exception as e:
                    print(f"删除链接失败: {e}")
                    fail_count += 1
            
            # 刷新列表
            self.refresh_links_list()
            self.update_statistics()
            
            if fail_count == 0:
                QMessageBox.information(self, "成功", f"已成功删除 {success_count} 个链接")
            else:
                QMessageBox.warning(self, "部分成功", f"成功删除 {success_count} 个链接，{fail_count} 个删除失败")
    
    def copy_selected_links(self):
        """复制选中链接的URL到剪贴板"""
        selected_links = self.get_selected_links()
        
        if not selected_links:
            QMessageBox.information(self, "提示", "请先选择要复制的链接")
            return
        
        # 收集所有 URL
        urls = [link.url for link in selected_links]
        
        # 复制到剪贴板（每个链接占一行）
        from PyQt6.QtWidgets import QApplication
        clipboard_text = "\n".join(urls)
        QApplication.clipboard().setText(clipboard_text)
        
        QMessageBox.information(self, "成功", f"已复制 {len(urls)} 个链接到剪贴板")
    
    def show_room_links(self):
        """显示房间链接"""
        QMessageBox.information(self, "提示", "房间链接功能")
    
    def toggle_fill_mode(self):
        """切换填充模式"""
        if self.mode_btn.isChecked():
            self.fill_mode = "multi"
            self.mode_btn.setText("多开模式")
        else:
            self.fill_mode = "single"
            self.mode_btn.setText("单开模式")
    
    def open_window_settings(self):
        """打开窗口设置"""
        items = ["一行4个 (默认)", "一行6个", "一行8个", "一行10个"]
        
        current_index = 0
        if self.window_columns == 6: current_index = 1
        elif self.window_columns == 8: current_index = 2
        elif self.window_columns == 10: current_index = 3
            
        item, ok = QInputDialog.getItem(self, "窗口设置", 
                                        "请选择多开窗口排列方式:", 
                                        items, current_index, False)
        if ok and item:
            if "4" in item: self.window_columns = 4
            elif "6" in item: self.window_columns = 6
            elif "8" in item: self.window_columns = 8
            elif "10" in item: self.window_columns = 10
            
    def start_auto_fill(self):
        """开始自动填充"""
        # if self.fill_mode == "single":
        #     QMessageBox.information(self, "提示", "该功能开发中")
        #     return
        
        selected_cards = self.get_selected_cards()
        selected_links = self.get_selected_links()
        
        if not selected_cards:
            QMessageBox.warning(self, "提示", "请选择至少一个名片")
            return
        
        if not selected_links:
            QMessageBox.warning(self, "提示", "请选择至少一个链接")
            return
        
        # 打开新的填充窗口（符合设计图）
        fill_window = NewFillWindow(
            selected_cards=selected_cards,
            selected_links=selected_links,
            parent=self,
            current_user=self.current_user,
            columns=self.window_columns,
            fill_mode=self.fill_mode
        )
        fill_window.exec()
    
    def show_user_menu(self):
        """显示用户菜单"""
        # 可以显示一个下拉菜单，包含切换账号、设置等选项
        self.switch_account()




