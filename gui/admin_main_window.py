"""
管理后台主界面
现代化设计版本 - 重新设计
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QStackedWidget, QFrame, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QLineEdit, 
    QMessageBox, QDialog, QGraphicsDropShadowEffect, QScrollArea
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor, QIcon, QPainter, QLinearGradient, QBrush, QPen, QPainterPath
from database import DatabaseManager
from .admin_card_manager import AdminCardManager
from .admin_audit_log import AdminAuditLogManager
from .admin_fill_record import AdminFillRecordManager
from .admin_link_manager import AdminLinkManager
from .admin_field_library import AdminFieldLibraryManager
from .admin_fixed_template import AdminFixedTemplateManager
from .admin_notice_manager import AdminNoticeManager
from .link_manager import LinkManagerDialog
from .admin_user_manager import UserManagementWidget
from .admin_dictionary_manager import AdminDictionaryManager
from gui.styles import COLORS
from gui.icons import Icons
import config


# 高级配色方案
SIDEBAR_COLORS = {
    'bg_start': '#1a1c2e',  # 深蓝紫
    'bg_end': '#11121f',    # 深黑
    'text_normal': '#8f9eb3',
    'text_active': '#ffffff',
    'hover_bg': 'rgba(255, 255, 255, 0.08)',
    'active_bg': 'qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(102, 126, 234, 0.2), stop:1 rgba(118, 75, 162, 0.1))',
    'active_border': '#667eea',  # 亮蓝紫色
    'divider': 'rgba(255, 255, 255, 0.1)',
}

class MenuListWidget(QListWidget):
    """自定义菜单列表"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                outline: none;
                padding: 10px;
            }}
            QListWidget::item {{
                color: {SIDEBAR_COLORS['text_normal']};
                padding: 14px 20px;
                border-radius: 12px;
                margin-bottom: 6px;
                font-size: 14px;
                font-weight: 500;
                border: 1px solid transparent;
            }}
            QListWidget::item:hover {{
                background: {SIDEBAR_COLORS['hover_bg']};
                color: white;
            }}
            QListWidget::item:selected {{
                background: {SIDEBAR_COLORS['active_bg']};
                color: {SIDEBAR_COLORS['text_active']};
                border: 1px solid rgba(102, 126, 234, 0.3);
                font-weight: 600;
            }}
        """)

class SimpleChart(QWidget):
    """简单的平滑曲线图组件"""
    def __init__(self, data, color, fill=True, parent=None):
        super().__init__(parent)
        self.data = data
        self.color = QColor(color)
        self.fill = fill
        self.setFixedHeight(60) # 默认高度
        self.setStyleSheet("background: transparent;")

    def paintEvent(self, event):
        if not self.data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # 计算比例
        max_val = max(self.data) if self.data else 1
        min_val = min(self.data) if self.data else 0
        if max_val == min_val: max_val += 1
        
        step_x = w / (len(self.data) - 1) if len(self.data) > 1 else w
        
        # 生成路径
        path = QPen(self.color, 2)
        painter.setPen(path)
        
        # 贝塞尔曲线逻辑简化：直接连线或简单平滑
        # 这里使用简单的连线，但带一点抗锯齿看起来就不错
        # 如果要平滑，需要计算控制点，为了代码量这里先用直线，或者用 QPainterPath.cubicTo
        
        from PyQt6.QtGui import QPainterPath
        path = QPainterPath()
        
        points = []
        for i, val in enumerate(self.data):
            x = i * step_x
            # 留出上下边距
            padding = 5
            avail_h = h - 2 * padding
            y = h - padding - ((val - min_val) / (max_val - min_val)) * avail_h
            points.append((x, y))
            
        if points:
            path.moveTo(points[0][0], points[0][1])
            for x, y in points[1:]:
                # 简单平滑：用 cubicTo
                # 这里简单处理：直接 lineTo 
                path.lineTo(x, y)
                
        painter.drawPath(path)
        
        # 填充渐变
        if self.fill:
            # 闭合路径
            fill_path = QPainterPath(path)
            fill_path.lineTo(w, h)
            fill_path.lineTo(0, h)
            fill_path.closeSubpath()
            
            gradient = QLinearGradient(0, 0, 0, h)
            c = QColor(self.color)
            c.setAlpha(50)
            gradient.setColorAt(0, c)
            c.setAlpha(0)
            gradient.setColorAt(1, c)
            
            painter.fillPath(fill_path, gradient)

class AdminMainWindow(QMainWindow):
    """管理后台主窗口"""
    
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.db_manager = DatabaseManager()
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f"{config.APP_NAME} - 管理后台")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet(f"background-color: {COLORS['background']};")
        
        # 主容器
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        central_widget.setLayout(main_layout)
        
        # 左侧边栏 (带渐变背景)
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)
        
        # 右侧主内容区
        content_area = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_area.setLayout(content_layout)
        
        # 顶部导航栏
        topbar = self.create_topbar()
        content_layout.addWidget(topbar)
        
        # 内容堆栈
        self.content_stack = QStackedWidget()
        content_layout.addWidget(self.content_stack)
        
        # 添加各个页面
        self.add_pages()
        
        main_layout.addWidget(content_area, 1)
        
        # 连接信号
        self.menu_list.currentRowChanged.connect(self.change_page)
        self.menu_list.setCurrentRow(0)
        
    def create_sidebar(self):
        """创建侧边栏"""
        sidebar = QFrame()
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {SIDEBAR_COLORS['bg_start']},
                    stop:1 {SIDEBAR_COLORS['bg_end']});
                border: none;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar.setLayout(layout)
        
        # 1. Logo区域
        logo_frame = QFrame()
        logo_frame.setFixedHeight(100)
        logo_frame.setStyleSheet("background: transparent;")
        logo_layout = QHBoxLayout()
        logo_layout.setContentsMargins(30, 30, 30, 20)
        logo_layout.setSpacing(15)
        logo_frame.setLayout(logo_layout)
        
        # Logo图标容器 (带发光效果)
        logo_icon_container = QFrame()
        logo_icon_container.setFixedSize(40, 40)
        logo_icon_container.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                stop:0 #667eea, stop:1 #764ba2);
            border-radius: 12px;
        """)
        logo_icon_layout = QVBoxLayout(logo_icon_container)
        logo_icon_layout.setContentsMargins(0, 0, 0, 0)
        logo_icon = QLabel()
        logo_icon.setPixmap(Icons.chart('white').pixmap(24, 24))
        logo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_icon_layout.addWidget(logo_icon)
        
        logo_layout.addWidget(logo_icon_container)
        
        # Logo文字
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        title_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        logo_text = QLabel("自动填充")
        logo_text.setFont(QFont("SF Pro Display", 18, QFont.Weight.Bold))
        logo_text.setStyleSheet("color: white; letter-spacing: 0.5px;")
        
        sub_text = QLabel("管理后台 PRO")
        sub_text.setFont(QFont("SF Pro Display", 10, QFont.Weight.DemiBold))
        sub_text.setStyleSheet("color: rgba(255,255,255,0.5); letter-spacing: 2px; text-transform: uppercase;")
        
        title_layout.addWidget(logo_text)
        title_layout.addWidget(sub_text)
        logo_layout.addLayout(title_layout)
        logo_layout.addStretch()
        
        layout.addWidget(logo_frame)
        
        # 分割线
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background: {SIDEBAR_COLORS['divider']}; margin: 0 30px;")
        layout.addWidget(line)
        
        layout.addSpacing(20)
        
        # 2. 菜单列表
        self.menu_list = MenuListWidget()
        
        # 添加菜单项
        menu_items = [
            ("仪表盘", Icons.chart('white'), 0),
            ("用户管理", Icons.users('white'), 1),
            ("名片管理", Icons.card('white'), 2), 
            ("审核记录", Icons.verify('white'), 3), 
            ("填充记录", Icons.edit('white'), 4),
            ("链接管理", Icons.link('white'), 5), 
            ("字段库管理", Icons.database('white'), 6), 
            ("固定模板", Icons.copy('white'), 7),
            ("通告管理", Icons.broadcast('white'), 8),
            ("字典管理", Icons.settings('white'), 9),
        ]
        
        for text, icon, index in menu_items:
            # 检查图标是否存在，如果不存在使用默认图标
            if not icon or icon.isNull():
                 icon = Icons.circle('white')
                 
            item = QListWidgetItem(icon, f"  {text}")
            item.setData(Qt.ItemDataRole.UserRole, index)
            self.menu_list.addItem(item)
            
        # 让菜单列表占据所有可用空间
        layout.addWidget(self.menu_list, 1)
        
        # 3. 底部用户信息栏 (重新设计)
        bottom_container = QWidget()
        bottom_container.setStyleSheet("background: transparent;")
        bottom_layout = QVBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(15, 10, 15, 20)
        bottom_layout.setSpacing(0)

        # 用户卡片背景容器
        user_card = QFrame()
        user_card.setObjectName("UserCard")
        user_card.setStyleSheet(f"""
            #UserCard {{
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }}
            #UserCard:hover {{
                background-color: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
        """)
        
        # 卡片内部布局
        card_layout = QHBoxLayout(user_card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(12)

        # 1. 头像
        avatar_size = 42
        avatar_label = QLabel(self.current_user.username[0].upper() if self.current_user.username else "?")
        avatar_label.setFixedSize(avatar_size, avatar_size)
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_label.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                stop:0 #6a11cb, stop:1 #2575fc);
            color: white;
            border-radius: {avatar_size // 2}px;
            font-weight: bold;
            font-size: 18px;
            border: 2px solid rgba(255,255,255,0.2);
        """)
        card_layout.addWidget(avatar_label)

        # 2. 用户信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        info_layout.setContentsMargins(0, 2, 0, 2)
        
        username_label = QLabel(self.current_user.username)
        username_label.setStyleSheet("""
            color: white;
            font-size: 15px;
            font-weight: 600;
            background: transparent;
        """)
        
        # 获取角色显示
        is_admin = True
        if hasattr(self.current_user, 'is_admin'):
            if callable(self.current_user.is_admin):
                is_admin = self.current_user.is_admin()
            else:
                is_admin = self.current_user.is_admin
        
        role_text = "超级管理员" if is_admin else "普通用户"
        role_label = QLabel(role_text)
        role_label.setStyleSheet("""
            color: rgba(255, 255, 255, 0.6);
            font-size: 12px;
            background: transparent;
        """)
        
        info_layout.addWidget(username_label)
        info_layout.addWidget(role_label)
        info_layout.addStretch()
        
        card_layout.addLayout(info_layout)
        
        # 3. 操作按钮 (切换账号)
        switch_btn = QPushButton()
        switch_btn.setIcon(Icons.sync('white'))
        switch_btn.setFixedSize(28, 28)
        switch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        switch_btn.setToolTip("切换账号")
        switch_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.25);
            }
        """)
        switch_btn.clicked.connect(self.switch_account)
        
        card_layout.addWidget(switch_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        bottom_layout.addWidget(user_card)
        layout.addWidget(bottom_container)
        
        return sidebar
    
    def create_topbar(self):
        """创建顶部栏"""
        topbar = QFrame()
        topbar.setFixedHeight(70)
        topbar.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-bottom: 1px solid {COLORS['border_light']};
            }}
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(30, 0, 30, 0)
        layout.setSpacing(16)
        topbar.setLayout(layout)
        
        # 当前页面标题（动态更新）
        self.page_title_label = QLabel("仪表盘")
        self.page_title_label.setStyleSheet(f"""
            font-size: 20px; 
            font-weight: 700; 
            color: {COLORS['text_primary']};
        """)
        layout.addWidget(self.page_title_label)
        
        layout.addStretch()
        
        # 时间显示 (可选)
        from datetime import datetime
        date_label = QLabel(datetime.now().strftime("%Y年%m月%d日"))
        date_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; margin-right: 20px;")
        layout.addWidget(date_label)
        
        # 退出按钮 (优化样式)
        logout_btn = QPushButton("退出系统")
        logout_btn.setIcon(Icons.sign_out(COLORS['danger']))
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['danger']}10;
                color: {COLORS['danger']};
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {COLORS['danger']}20;
            }}
        """)
        logout_btn.clicked.connect(self.logout)
        layout.addWidget(logout_btn)
        
        return topbar
    
    def add_pages(self):
        """添加各个页面"""
        # 0. 仪表盘 (新首页)
        dashboard_page = self.create_dashboard_page()
        self.content_stack.addWidget(dashboard_page)

        # 1. 用户管理页面
        self.user_page = UserManagementWidget()
        self.content_stack.addWidget(self.user_page)
        
        # 2. 名片管理页面
        card_page = self.create_card_management_page()
        self.content_stack.addWidget(card_page)
        
        # 3. 审核记录页面
        audit_page = self.create_audit_log_page()
        self.content_stack.addWidget(audit_page)
        
        # 4. 填充记录页面
        self.fill_record_page = AdminFillRecordManager()
        self.content_stack.addWidget(self.fill_record_page)
        
        # 5. 链接管理页面
        link_page = AdminLinkManager()
        self.content_stack.addWidget(link_page)
        
        # 6. 字段库管理页面
        field_library_page = self.create_field_library_page()
        self.content_stack.addWidget(field_library_page)
        
        # 7. 固定模板管理页面
        self.fixed_template_page = AdminFixedTemplateManager()
        self.content_stack.addWidget(self.fixed_template_page)
        
        # 8. 通告管理页面
        self.notice_page = AdminNoticeManager(current_user=self.current_user)
        self.content_stack.addWidget(self.notice_page)

        # 9. 字典管理页面
        self.dictionary_page = AdminDictionaryManager()
        self.content_stack.addWidget(self.dictionary_page)

    def change_page(self, index):
        """切换页面"""
        self.content_stack.setCurrentIndex(index)
        
        # 更新顶部标题
        item = self.menu_list.item(index)
        if item:
            self.page_title_label.setText(item.text().strip())

    def create_device_management_page(self):
        """创建设备管理页面"""
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)
        page.setLayout(layout)
        
        # 标题
        title_label = QLabel("设备管理")
        title_label.setStyleSheet(f"font-size: 28px; font-weight: 800; color: {COLORS['text_primary']};")
        layout.addWidget(title_label)
        
        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.addStretch()
        
        refresh_btn = QPushButton("刷新列表")
        refresh_btn.setIcon(Icons.refresh(COLORS['primary']))
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['surface']};
                color: {COLORS['primary']};
                border: 1px solid {COLORS['primary']};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {COLORS['primary']}10;
            }}
        """)
        refresh_btn.clicked.connect(self.refresh_devices)
        toolbar.addWidget(refresh_btn)
        layout.addLayout(toolbar)
        
        # 设备表格容器
        table_frame = QFrame()
        table_frame.setStyleSheet(f"background: {COLORS['surface']}; border-radius: 16px;")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 12))
        shadow.setOffset(0, 8)
        table_frame.setGraphicsEffect(shadow)
        
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(0, 0, 0, 0)
        
        self.device_table = QTableWidget()
        self.device_table.setColumnCount(6)
        self.device_table.setHorizontalHeaderLabels(['用户', '设备名称', '设备类型', '设备ID', '最后登录', '操作'])
        self.device_table.verticalHeader().setVisible(False)
        self.device_table.setShowGrid(False)
        self.device_table.setStyleSheet(f"""
            QTableWidget {{ background: transparent; border: none; }}
            QHeaderView::section {{ background: {COLORS['background']}; border: none; padding: 12px; font-weight: 600; }}
            QTableWidget::item {{ padding: 12px; border-bottom: 1px solid {COLORS['border_light']}; }}
        """)
        header = self.device_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        table_layout.addWidget(self.device_table)
        layout.addWidget(table_frame)
        
        self.load_devices()
        return page

    def create_card_management_page(self):
        return AdminCardManager(current_admin=self.current_user)

    def create_audit_log_page(self):
        return AdminAuditLogManager()

    def create_link_management_page(self):
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)
        page.setLayout(layout)
        
        layout.addWidget(QLabel("链接管理", styleSheet=f"font-size: 28px; font-weight: 800; color: {COLORS['text_primary']};"))
        
        stats = self.db_manager.get_statistics()
        stats_layout = QHBoxLayout()
        stats_layout.addWidget(self.create_stat_card("链接总数", str(stats['total_links']), COLORS['primary']))
        stats_layout.addWidget(self.create_stat_card("激活链接", str(stats['active_links']), COLORS['success']))
        layout.addLayout(stats_layout)
        
        add_btn = QPushButton("打开链接管理器")
        add_btn.setFixedSize(200, 50)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['success']}; color: white; border-radius: 8px; font-weight: 600; font-size: 16px; border: none;
            }}
            QPushButton:hover {{ background: #28A745; }}
        """)
        add_btn.clicked.connect(self.open_link_manager)
        layout.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        return page

    def create_field_library_page(self):
        return AdminFieldLibraryManager()

    def create_dashboard_page(self):
        """创建仪表盘首页 - 增强版"""
        page = QWidget()
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content_widget = QWidget()
        content_widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(40, 30, 40, 40)
        layout.setSpacing(24)
        
        # 1. 顶部栏 (欢迎语 + 搜索/操作)
        from datetime import datetime
        hour = datetime.now().hour
        greeting = "早上好" if 5 <= hour < 12 else "下午好" if 12 <= hour < 18 else "晚上好"
        
        header_layout = QHBoxLayout()
        
        welcome_text = QVBoxLayout()
        welcome_title = QLabel(f"{greeting}，管理员")
        welcome_title.setStyleSheet(f"font-size: 26px; font-weight: 800; color: {COLORS['text_primary']};")
        welcome_sub = QLabel(f"今天是 {datetime.now().strftime('%Y年%m月%d日')} | 系统运行平稳")
        welcome_sub.setStyleSheet(f"font-size: 13px; color: {COLORS['text_secondary']}; margin-top: 4px;")
        welcome_text.addWidget(welcome_title)
        welcome_text.addWidget(welcome_sub)
        
        header_layout.addLayout(welcome_text)
        header_layout.addStretch()
        
        # 搜索框 (UI示意)
        search_box = QLineEdit()
        search_box.setPlaceholderText("全局搜索...")
        search_box.setFixedSize(240, 40)
        search_box.setStyleSheet(f"""
            QLineEdit {{
                background: white; border: 1px solid {COLORS['border_light']}; border-radius: 20px; padding: 0 16px;
            }}
            QLineEdit:focus {{ border-color: {COLORS['primary']}; }}
        """)
        header_layout.addWidget(search_box)
        
        layout.addLayout(header_layout)
        
        # 获取统计数据
        stats = self.db_manager.get_statistics()
        daily_stats = self.db_manager.get_daily_fill_stats(7)
        platform_dist = self.db_manager.get_platform_distribution()
        active_users = self.db_manager.get_active_user_count(1)
        
        # 2. 核心指标卡片 (4列布局)
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)
        
        # 计算趋势
        today_count = stats.get('today_records', 0)
        yesterday_count = stats.get('yesterday_records', 0)
        fill_trend_val = 0
        if yesterday_count > 0:
            fill_trend_val = round(((today_count - yesterday_count) / yesterday_count) * 100, 1)
        
        # 模拟数据趋势 (7天) -> 替换为真实数据
        trend_data = daily_stats
        
        # 卡片数据配置
        metrics = [
            {
                "title": "总用户", 
                "value": str(stats.get('total_cards', 0)), # 暂用 total_cards 如果 total_users 没有
                "icon": Icons.users('white'),
                "color": "#4F46E5", "bg_color": "#EEF2FF",
                "trend": f"{active_users} 活跃", "trend_up": True # 显示活跃用户数
            },
            {
                "title": "名片总数", 
                "value": str(stats.get('total_cards', 0)),
                "icon": Icons.card('white'),
                "color": "#0EA5E9", "bg_color": "#F0F9FF",
                "trend": "+0%", "trend_up": True
            },
            {
                "title": "累计填充", 
                "value": str(stats.get('total_records', 0)),
                "icon": Icons.edit('white'),
                "color": "#10B981", "bg_color": "#ECFDF5",
                "trend": f"+{today_count}", "trend_up": True
            },
            {
                "title": "今日填充", 
                "value": str(stats.get('today_records', 0)),
                "icon": Icons.chart('white'),
                "color": "#F59E0B", "bg_color": "#FFFBEB",
                "trend": f"{'+' if fill_trend_val >= 0 else ''}{fill_trend_val}%", "trend_up": fill_trend_val >= 0
            }
        ]
        
        # 修正用户数
        try:
            from database.models import User
            user_count = User.objects.count()
            metrics[0]["value"] = str(user_count)
        except:
            pass

        for m in metrics:
            card = self.create_dashboard_card(m['title'], m['value'], m['icon'], m['color'], m['bg_color'], m.get('trend'), m.get('trend_up'))
            cards_layout.addWidget(card)
            
        layout.addLayout(cards_layout)
        
        # 3. 数据图表区 (填充趋势 + 平台分布)
        charts_row = QHBoxLayout()
        charts_row.setSpacing(20)
        
        # 3.1 填充趋势图 (左侧 2/3)
        trend_card = QFrame()
        trend_card.setStyleSheet(f"background: white; border-radius: 16px; border: none;")
        trend_shadow = QGraphicsDropShadowEffect(self)
        trend_shadow.setBlurRadius(20); trend_shadow.setColor(QColor(0,0,0,8)); trend_shadow.setOffset(0,6)
        trend_card.setGraphicsEffect(trend_shadow)
        
        trend_layout = QVBoxLayout(trend_card)
        trend_layout.setContentsMargins(24, 24, 24, 24)
        
        # 计算周趋势
        week_total = sum(daily_stats)
        week_avg = round(week_total / 7, 1)
        
        t_header = QHBoxLayout()
        t_header.addWidget(QLabel("近7日填充趋势", styleSheet=f"font-size: 16px; font-weight: 700; color: {COLORS['text_primary']};"))
        t_header.addStretch()
        t_header.addWidget(QLabel(f"周平均 {week_avg}", styleSheet=f"color: {COLORS['success']}; font-weight: 600; font-size: 13px;"))
        trend_layout.addLayout(t_header)
        
        # 插入自定义图表
        chart = SimpleChart(daily_stats, COLORS['primary'], fill=True)
        chart.setFixedHeight(120) # 增加高度
        trend_layout.addSpacing(10)
        trend_layout.addWidget(chart)
        
        charts_row.addWidget(trend_card, 2)
        
        # 3.2 平台分布 (右侧 1/3)
        dist_card = QFrame()
        dist_card.setStyleSheet(f"background: white; border-radius: 16px; border: none;")
        dist_shadow = QGraphicsDropShadowEffect(self)
        dist_shadow.setBlurRadius(20); dist_shadow.setColor(QColor(0,0,0,8)); dist_shadow.setOffset(0,6)
        dist_card.setGraphicsEffect(dist_shadow)
        
        dist_layout = QVBoxLayout(dist_card)
        dist_layout.setContentsMargins(24, 24, 24, 24)
        dist_layout.addWidget(QLabel("平台活跃度分布", styleSheet=f"font-size: 16px; font-weight: 700; color: {COLORS['text_primary']}; margin-bottom: 12px;"))
        
        # 使用真实分布数据
        platforms = [(p['name'], p['value'], p['color']) for p in platform_dist]
        if not platforms:
            platforms = [("暂无数据", 0, "#9CA3AF")]
        
        # 只显示前4个
        for name, pct, color in platforms[:4]:
            row = QHBoxLayout()
            row.setSpacing(10)
            row.addWidget(QLabel(name, styleSheet=f"color: {COLORS['text_secondary']}; font-size: 13px; min-width: 60px;"))
            
            # 进度条
            progress = QFrame()
            progress.setFixedHeight(8)
            progress.setStyleSheet(f"""
                background-color: {COLORS['border_light']};
                border-radius: 4px;
            """)
            # 使用内部 frame 模拟进度
            p_layout = QHBoxLayout(progress)
            p_layout.setContentsMargins(0,0,0,0)
            p_layout.setSpacing(0)
            
            if pct > 0:
                fill = QFrame()
                fill.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
                p_layout.addWidget(fill, pct)
                p_layout.addStretch(100 - pct)
            else:
                p_layout.addStretch()
            
            row.addWidget(progress, 1)
            row.addWidget(QLabel(f"{pct}%", styleSheet=f"color: {COLORS['text_primary']}; font-weight: 600; font-size: 12px; min-width: 30px; alignment: right;"))
            
            dist_layout.addLayout(row)
            
        dist_layout.addStretch()
        charts_row.addWidget(dist_card, 1)
        
        layout.addLayout(charts_row)
        
        # 4. 底部内容区 (三列布局：动态 | 快捷入口 | 系统公告)
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(20)
        
        # 4.1 左侧：最新动态 (保持原有逻辑，优化样式)
        recent_panel = self.create_panel_frame("最新动态")
        recent_layout = recent_panel.layout()
        
        # 头部按钮
        view_all_btn = QPushButton("查看全部")
        view_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        view_all_btn.setStyleSheet(f"color: {COLORS['primary']}; border: none; font-weight: 600; font-size: 13px;")
        view_all_btn.clicked.connect(lambda: self.menu_list.setCurrentRow(4))
        # 重新获取 header layout (hacky way, or recreate header)
        
        records_data = self.db_manager.get_all_fill_records(limit=4)
        if records_data and records_data['records']:
            for i, record in enumerate(records_data['records']):
                item = self.create_recent_record_item(record)
                recent_layout.addWidget(item)
                if i < len(records_data['records']) - 1:
                    # line = QFrame()
                    # line.setFixedHeight(1)
                    # line.setStyleSheet(f"background: #F3F4F6; margin: 6px 0;")
                    # recent_layout.addWidget(line)
                    # 使用空白间距替代分割线
                    pass
        else:
            recent_layout.addWidget(QLabel("暂无数据", styleSheet=f"color: {COLORS['text_secondary']}; alignment: center; padding: 20px;"))
            
        recent_layout.addStretch()
        bottom_row.addWidget(recent_panel, 2) # 40%
        
        # 4.2 中间：快捷操作 (Grid)
        actions_panel = self.create_panel_frame("快捷入口")
        actions_layout = actions_panel.layout()
        
        grid = QVBoxLayout() # 垂直排列几行
        grid.setSpacing(12)
        
        # Row 1
        r1 = QHBoxLayout(); r1.setSpacing(12)
        btn1 = self.create_action_button("审核名片", Icons.verify('white'), "#7C3AED"); btn1.clicked.connect(lambda: self.menu_list.setCurrentRow(3))
        btn2 = self.create_action_button("发布通告", Icons.broadcast('white'), "#EA580C"); btn2.clicked.connect(lambda: self.menu_list.setCurrentRow(7))
        r1.addWidget(btn1); r1.addWidget(btn2)
        grid.addLayout(r1)
        
        # Row 2
        r2 = QHBoxLayout(); r2.setSpacing(12)
        btn3 = self.create_action_button("用户管理", Icons.users('white'), "#0EA5E9"); btn3.clicked.connect(lambda: self.menu_list.setCurrentRow(1))
        btn4 = self.create_action_button("字段库", Icons.database('white'), "#10B981"); btn4.clicked.connect(lambda: self.menu_list.setCurrentRow(6))
        r2.addWidget(btn3); r2.addWidget(btn4)
        grid.addLayout(r2)
        
        actions_layout.addLayout(grid)
        actions_layout.addStretch()
        bottom_row.addWidget(actions_panel, 2) # 40%
        
        # 4.3 右侧：系统概览/公告
        system_panel = self.create_panel_frame("系统概览")
        sys_layout = system_panel.layout()
        
        # 待处理项
        pending_count = self.db_manager.get_pending_edit_requests_count(None)
        sys_layout.addWidget(self.create_overview_item("待审名片", str(pending_count), pending_count > 0))
        
        # line = QFrame(); line.setFixedHeight(1); line.setStyleSheet(f"background: #F3F4F6; margin: 8px 0;")
        # sys_layout.addWidget(line)
        sys_layout.addSpacing(8) # 使用间距代替分割线
        
        sys_layout.addWidget(self.create_overview_item("填充成功率", f"{stats.get('success_rate', 0)}%", False))
        
        # line2 = QFrame(); line2.setFixedHeight(1); line2.setStyleSheet(f"background: #F3F4F6; margin: 8px 0;")
        # sys_layout.addWidget(line2)
        sys_layout.addSpacing(8)
        
        sys_layout.addWidget(self.create_overview_item("活跃用户", str(active_users), False))
        
        sys_layout.addStretch()
        
        # 版本信息
        ver_lbl = QLabel(f"Version {config.APP_VERSION}", styleSheet=f"color: {COLORS['text_secondary']}; font-size: 11px; margin-top: 10px;")
        sys_layout.addWidget(ver_lbl)
        
        bottom_row.addWidget(system_panel, 1) # 20%
        
        layout.addLayout(bottom_row)
        layout.addStretch()
        
        scroll.setWidget(content_widget)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        
        return page

    def create_panel_frame(self, title):
        """通用面板框架"""
        frame = QFrame()
        # 移除边框，纯白背景
        frame.setStyleSheet(f"""
            QFrame {{
                background: white; border-radius: 16px; border: none;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20); shadow.setColor(QColor(0,0,0,8)); shadow.setOffset(0,6)
        frame.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 20, 24, 24)
        
        header = QHBoxLayout()
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {COLORS['text_primary']};")
        header.addWidget(t_lbl)
        header.addStretch()
        layout.addLayout(header)
        layout.addSpacing(10)
        
        return frame

    def create_dashboard_card(self, title, value, icon, color, bg_color, trend=None, trend_up=True):
        """创建简洁风格的仪表盘卡片"""
        card = QFrame()
        card.setFixedHeight(140)
        # 移除边框，仅保留白色背景和圆角
        card.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-radius: 16px;
                border: none;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 8)) # 更淡的阴影
        shadow.setOffset(0, 6)
        card.setGraphicsEffect(shadow)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(20)
        
        # 左侧：图标容器
        icon_container = QLabel()
        icon_container.setFixedSize(56, 56)
        icon_container.setStyleSheet(f"""
            background-color: {bg_color};
            border-radius: 28px;
        """)
        icon_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(icon.pixmap(24, 24))
        
        ic_layout = QVBoxLayout(icon_container)
        ic_layout.setContentsMargins(0,0,0,0)
        ic_layout.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(icon_container)
        
        # 右侧：数据
        data_layout = QVBoxLayout()
        data_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        data_layout.setSpacing(4)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px; font-weight: 500; border: none; background: transparent;")
        
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 32px; font-weight: 800; border: none; background: transparent;")
        
        data_layout.addWidget(val_lbl)
        data_layout.addWidget(title_lbl)
        
        # 趋势指标
        if trend:
            trend_widget = QWidget()
            t_layout = QHBoxLayout(trend_widget)
            t_layout.setContentsMargins(0, 4, 0, 0)
            t_layout.setSpacing(4)
            
            # 箭头
            arrow = QLabel("↑" if trend_up else "↓")
            trend_color = COLORS['success'] if trend_up else COLORS['danger']
            arrow.setStyleSheet(f"color: {trend_color}; font-weight: bold; font-size: 12px;")
            
            lbl = QLabel(f"{trend} 较昨日")
            lbl.setStyleSheet(f"color: {trend_color}; font-size: 12px; font-weight: 600;")
            
            t_layout.addWidget(arrow)
            t_layout.addWidget(lbl)
            t_layout.addStretch()
            
            data_layout.addWidget(trend_widget)
        
        layout.addLayout(data_layout)
        layout.addStretch()
        
        return card

    def create_recent_record_item(self, record):
        """创建简洁的列表项"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(16)
        
        # 极简状态点
        status_dot = QLabel()
        status_dot.setFixedSize(8, 8) # 更小的圆点
        color = COLORS['success'] if record.success else COLORS['danger']
        status_dot.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
        layout.addWidget(status_dot)
        
        # 内容
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        title_text = f"{record.card.name}"
        title = QLabel(title_text)
        title.setStyleSheet(f"font-weight: 600; font-size: 14px; color: {COLORS['text_primary']};")
        
        # 链接名字如果不长，可以显示
        link_name = record.link.name if record.link else '未知链接'
        if len(link_name) > 15:
            link_name = link_name[:15] + "..."
            
        sub_text = f"{link_name} · {record.created_at.strftime('%H:%M')}" # 只显示时间，日期不重要因为是最新
        subtitle = QLabel(sub_text)
        subtitle.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        
        info_layout.addWidget(title)
        info_layout.addWidget(subtitle)
        layout.addLayout(info_layout)
        
        layout.addStretch()
        
        # 结果
        result_text = f"{record.fill_count}/{record.total_count}"
        result_lbl = QLabel(result_text)
        result_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-family: monospace; font-size: 13px;")
        layout.addWidget(result_lbl)
        
        return widget

    def create_action_button(self, text, icon, color):
        """创建简洁的操作按钮"""
        btn = QPushButton()
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(60) # 减小高度
        
        layout = QHBoxLayout(btn)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)
        
        # 纯色背景的小图标容器
        icon_box = QLabel()
        icon_box.setFixedSize(32, 32)
        icon_box.setStyleSheet("background: rgba(255,255,255,0.2); border-radius: 8px;")
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        ib_layout = QVBoxLayout(icon_box)
        ib_layout.setContentsMargins(0,0,0,0)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(icon.pixmap(18, 18))
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        ib_layout.addWidget(icon_lbl)
        
        layout.addWidget(icon_box)
        
        # 文字
        lbl = QLabel(text)
        lbl.setStyleSheet("color: white; font-size: 14px; font-weight: 600; border: none; background: transparent;")
        layout.addWidget(lbl)
        layout.addStretch()
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border-radius: 12px;
                border: 2px solid transparent;
            }}
            QPushButton:hover {{
                border: 2px solid rgba(255, 255, 255, 0.5);
            }}
            QPushButton:pressed {{
                background-color: {color}DD;
                border: none;
            }}
        """)
        
        return btn
        
    def create_overview_item(self, title, value, is_warning):
        """创建概览项"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 8)
        
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px;")
        layout.addWidget(t_lbl)
        
        layout.addStretch()
        
        v_lbl = QLabel(value)
        color = COLORS['warning'] if is_warning else COLORS['text_primary']
        weight = "800" if is_warning else "600"
        v_lbl.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: {weight};")
        layout.addWidget(v_lbl)
        
        return widget

    def load_devices(self):
        """加载设备列表"""
        from database.models import Device
        self.device_table.setRowCount(0)
        devices = Device.objects.all().order_by('-last_login')
        
        for device in devices:
            row = self.device_table.rowCount()
            self.device_table.insertRow(row)
            self.device_table.setRowHeight(row, 50)
            
            username = device.user.username if device.user else "未知"
            self.device_table.setItem(row, 0, QTableWidgetItem(username))
            self.device_table.setItem(row, 1, QTableWidgetItem(device.device_name))
            
            device_type = device.device_type or "Unknown"
            type_item = QTableWidgetItem(device_type)
            if device_type == "Darwin": type_item.setText("🍎 macOS")
            elif device_type == "Windows": type_item.setText("💻 Windows")
            elif device_type == "Linux": type_item.setText("🐧 Linux")
            self.device_table.setItem(row, 2, type_item)
            
            device_id_short = device.device_id[:30] + "..." if len(device.device_id) > 30 else device.device_id
            self.device_table.setItem(row, 3, QTableWidgetItem(device_id_short))
            
            last_login = device.last_login.strftime('%Y-%m-%d %H:%M') if device.last_login else '-'
            self.device_table.setItem(row, 4, QTableWidgetItem(last_login))
            
            action_widget = self.create_device_action_buttons(device)
            self.device_table.setCellWidget(row, 5, action_widget)

    def create_device_action_buttons(self, device):
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)
        
        remove_btn = QPushButton("移除")
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['danger']}; color: white; border: none; border-radius: 4px; padding: 4px 12px; font-size: 12px;
            }}
            QPushButton:hover {{ background: #CC0000; }}
        """)
        remove_btn.clicked.connect(lambda: self.remove_device(device))
        layout.addWidget(remove_btn)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def remove_device(self, device):
        reply = QMessageBox.question(
            self, "确认移除",
            f"确定要移除设备 {device.device_name} 吗？\n该设备用户将需要重新登录。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                device.delete()  # 直接删除设备记录
                self.load_devices()
                QMessageBox.information(self, "成功", "设备已移除")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"移除设备失败：{str(e)}")

    def refresh_devices(self):
        self.load_devices()

    def open_link_manager(self):
        dialog = LinkManagerDialog(self)
        dialog.exec()
    
    def switch_account(self):
        from core.auth import clear_token
        from gui.login_window import LoginWindow
        from PyQt6.QtWidgets import QApplication
        
        reply = QMessageBox.question(self, "切换账号", "确定要切换账号吗？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            clear_token()
            login_window = LoginWindow()
            if login_window.exec() == 1:
                new_user = login_window.get_current_user()
                if new_user:
                    self.close()
                    if new_user.is_admin():
                        new_window = AdminMainWindow(current_user=new_user)
                    else:
                        from gui import MainWindow
                        new_window = MainWindow(current_user=new_user)
                    QApplication.instance()._main_window = new_window
                    new_window.show()
            else:
                import sys; sys.exit(0)

    def logout(self):
        reply = QMessageBox.question(self, "退出程序", "确定要退出程序吗？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            from core.auth import clear_token
            clear_token()
            self.close()
            import sys; sys.exit(0)
