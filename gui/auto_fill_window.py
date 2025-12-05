"""
自动填写窗口 - macOS Big Sur 风格
包含 WebView 和自动填写功能
支持多链接同时填写（最多9个）
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QListWidget, QListWidgetItem, QMessageBox,
                             QSplitter, QFrame, QScrollArea, QGroupBox, QGraphicsDropShadowEffect, QDialog, QGridLayout, QCheckBox, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QUrl, QPropertyAnimation, QEasingCurve, QPoint, QRect
from PyQt6.QtGui import QIcon, QColor
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
import json
from database import DatabaseManager, Card, Link
from core import AutoFillEngineV2, TencentDocsFiller
from core.diagnostic import PageDiagnostic
from .styles import GLOBAL_STYLE, COLORS, get_toolbar_button_style, get_config_panel_style, get_title_style
import config


class AnimatedMessageBox(QDialog):
    """带动画效果的消息框 - 模态对话框"""
    
    def __init__(self, parent, icon_type, title, message):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedWidth(500)
        self.setMinimumHeight(200)
        
        # 根据类型设置图标和颜色
        icon_map = {
            'information': ('ℹ️', COLORS['primary']),
            'warning': ('⚠️', '#ff9800'),
            'critical': ('❌', '#f44336'),
            'success': ('✅', '#4caf50')
        }
        
        icon_emoji, accent_color = icon_map.get(icon_type, ('ℹ️', COLORS['primary']))
        
        # 样式设置 - macOS 风格
        self.setStyleSheet(f"""
            QDialog {{
                background-color: white;
                border-radius: 12px;
            }}
            QLabel {{
                color: {COLORS['text_primary']};
                background: transparent;
            }}
            QPushButton {{
                background-color: {accent_color};
                color: white;
                font-size: 14px;
                font-weight: 600;
                padding: 10px 24px;
                border-radius: 8px;
                border: none;
                min-width: 100px;
            }}
            QPushButton:hover {{
                background-color: {accent_color};
                opacity: 0.9;
            }}
            QPushButton:pressed {{
                background-color: {accent_color};
                opacity: 0.8;
            }}
        """)
        
        # 内容布局
        layout = QVBoxLayout()
        layout.setContentsMargins(35, 35, 35, 35)
        layout.setSpacing(20)
        self.setLayout(layout)
        
        # 图标标题区域
        header_layout = QHBoxLayout()
        
        icon_label = QLabel(icon_emoji)
        icon_label.setStyleSheet(f"""
            font-size: 48px;
            padding: 10px;
        """)
        header_layout.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 700;
            color: {COLORS['text_primary']};
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(title_label, 1)
        
        layout.addLayout(header_layout)
        
        # 消息内容
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet(f"""
            font-size: 14px;
            color: {COLORS['text_secondary']};
            line-height: 1.6;
            padding: 10px 0;
        """)
        layout.addWidget(message_label)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_ok = QPushButton("确定")
        btn_ok.clicked.connect(self.accept)
        btn_ok.setDefault(True)
        btn_layout.addWidget(btn_ok)
        
        layout.addLayout(btn_layout)
        
        # 初始化动画属性
        self.setWindowOpacity(0.0)
        self._initial_geometry = None
        
    def showEvent(self, event):
        """窗口显示时的动画"""
        super().showEvent(event)
        
        # 首次显示时设置位置
        if self._initial_geometry is None:
            # 调整大小以适应内容
            self.adjustSize()
            
            # 居中显示
            if self.parent():
                parent_geo = self.parent().geometry()
                x = parent_geo.x() + (parent_geo.width() - self.width()) // 2
                y = parent_geo.y() + (parent_geo.height() - self.height()) // 2
            else:
                # 如果没有父窗口，居中到屏幕
                from PyQt6.QtGui import QGuiApplication
                screen = QGuiApplication.primaryScreen().geometry()
                x = screen.x() + (screen.width() - self.width()) // 2
                y = screen.y() + (screen.height() - self.height()) // 2
            
            # 保存最终位置
            self._initial_geometry = QRect(x, y, self.width(), self.height())
            
            # 设置初始位置（稍微偏下一点，用于滑入动画）
            start_y = y + 30
            self.setGeometry(x, start_y, self.width(), self.height())
            
            # 透明度动画（淡入）
            self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
            self.fade_animation.setDuration(350)
            self.fade_animation.setStartValue(0.0)
            self.fade_animation.setEndValue(1.0)
            self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            
            # 几何动画（从下方滑入）
            self.geometry_animation = QPropertyAnimation(self, b"geometry")
            self.geometry_animation.setDuration(350)
            self.geometry_animation.setStartValue(QRect(x, start_y, self.width(), self.height()))
            self.geometry_animation.setEndValue(self._initial_geometry)
            self.geometry_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            
            # 启动动画
            self.fade_animation.start()
            self.geometry_animation.start()
    
    def show_animated(self):
        """显示带动画的对话框"""
        return self.exec()


class AutoFillWindow(QWidget):
    """自动填写窗口 - 支持多链接同时填写"""
    
    fill_completed = pyqtSignal()  # 填写完成信号
    MAX_LINKS = 9  # 最多同时填写9个链接
    
    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.current_user = current_user  # 当前登录用户
        self.auto_fill_engine = AutoFillEngineV2()  # 麦客CRM 填写引擎
        self.tencent_docs_engine = TencentDocsFiller()  # 腾讯文档填写引擎
        self.selected_card = None
        self.selected_links = []  # 改为列表，支持多选
        self.web_views = []  # 存储多个WebView
        self.link_checkboxes = {}  # 存储链接复选框
        self.init_ui()
    
    def show_message(self, icon_type: str, title: str, message: str):
        """显示动画消息框
        
        Args:
            icon_type: 'information', 'warning', 'critical', 'success'
            title: 标题
            message: 消息内容
        """
        msg_box = AnimatedMessageBox(self, icon_type, title, message)
        msg_box.show_animated()
    
    def init_ui(self):
        """初始化UI - macOS 风格"""
        self.setWindowTitle("✏️ 自动填写")
        self.setGeometry(50, 50, 1600, 900)
        
        # 应用全局样式
        self.setStyleSheet(GLOBAL_STYLE)
        
        # 主布局
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)
        
        # 左侧面板（名片和链接选择）
        left_panel = self.create_left_panel()
        
        # 右侧面板（WebView）
        right_panel = self.create_right_panel()
        
        # 使用分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([380, 1220])
        
        main_layout.addWidget(splitter)
        
        # 加载数据
        self.load_cards()
        self.load_links()
    
    def create_left_panel(self) -> QWidget:
        """创建左侧面板 - 现代化设计"""
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 {COLORS['surface']}, 
                                            stop:1 {COLORS['surface_hover']});
                border-right: none;
            }}
        """)
        panel.setMaximumWidth(400)
        panel.setMinimumWidth(380)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        panel.setLayout(layout)
        
        # 顶部标题 - 更精美
        title_label = QLabel("✏️ 自动填写")
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_primary']};
                font-size: 24px;
                font-weight: 800;
                padding: 12px 0;
                letter-spacing: -0.5px;
            }}
        """)
        layout.addWidget(title_label)
        
        # 名片区域 - 优化标签样式
        card_label = QLabel("📇 选择名片")
        card_label.setStyleSheet(f"""
            font-size: 15px; 
            font-weight: 700; 
            color: {COLORS['text_primary']};
            padding: 10px 0px 6px 0px;
            letter-spacing: 0.3px;
        """)
        layout.addWidget(card_label)
        
        self.card_list = QListWidget()
        self.card_list.itemClicked.connect(self.on_card_selected)
        layout.addWidget(self.card_list)
        
        # 链接区域 - 支持多选（复选框）
        link_header = QHBoxLayout()
        link_label = QLabel("🔗 选择链接")
        link_label.setStyleSheet(f"""
            font-size: 15px; 
            font-weight: 700; 
            color: {COLORS['text_primary']};
            padding: 10px 0px 6px 0px;
            letter-spacing: 0.3px;
        """)
        link_header.addWidget(link_label)
        
        self.link_count_label = QLabel("(0/9)")
        self.link_count_label.setStyleSheet(f"""
            font-size: 13px; 
            color: {COLORS['text_secondary']};
            padding: 10px 0px 6px 0px;
        """)
        link_header.addWidget(self.link_count_label)
        link_header.addStretch()
        layout.addLayout(link_header)
        
        # 使用滚动区域来容纳链接复选框
        link_scroll = QScrollArea()
        link_scroll.setWidgetResizable(True)
        link_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)
        
        link_container = QWidget()
        self.link_layout = QVBoxLayout()
        self.link_layout.setSpacing(4)
        self.link_layout.setContentsMargins(0, 0, 0, 0)
        link_container.setLayout(self.link_layout)
        link_scroll.setWidget(link_container)
        
        layout.addWidget(link_scroll)
        
        # 开始按钮 - macOS 系统蓝
        self.btn_start = QPushButton("✏️ 开始自动填写")
        self.btn_start.setMinimumHeight(44)
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self.start_auto_fill)
        self.btn_start.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                font-size: 15px;
                font-weight: 600;
                padding: 12px;
                border-radius: 10px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #0051D5;
            }}
            QPushButton:pressed {{
                background-color: #003D99;
            }}
            QPushButton:disabled {{
                background-color: {COLORS['divider']};
                color: {COLORS['text_secondary']};
            }}
        """)
        layout.addWidget(self.btn_start)
        
        # 关闭按钮 - 次要样式
        btn_close = QPushButton("⬅️ 关闭窗口")
        btn_close.setMinimumHeight(38)
        btn_close.clicked.connect(self.close)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                color: {COLORS['text_primary']};
                font-size: 14px;
                font-weight: 500;
                padding: 10px;
                border-radius: 8px;
                border: 1px solid {COLORS['border']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['divider']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['border']};
            }}
        """)
        layout.addWidget(btn_close)
        
        return panel
    
    def create_right_panel(self) -> QWidget:
        """创建右侧面板 - 支持多个WebView"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        
        layout = QVBoxLayout()
        panel.setLayout(layout)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        # 返回按钮
        btn_back = QPushButton("⬅️ 返回")
        btn_back.clicked.connect(self.close)
        btn_back.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                padding: 8px 15px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        toolbar.addWidget(btn_back)
        
        self.url_label = QLabel("未加载页面")
        self.url_label.setStyleSheet("color: #666; padding: 5px; font-size: 12px;")
        toolbar.addWidget(self.url_label)
        
        toolbar.addStretch()
        
        btn_refresh = QPushButton("🔄 刷新全部")
        btn_refresh.clicked.connect(self.refresh_all_webviews)
        toolbar.addWidget(btn_refresh)
        
        btn_toggle_config = QPushButton("📋 配置面板")
        btn_toggle_config.clicked.connect(self.toggle_config_panel)
        toolbar.addWidget(btn_toggle_config)
        
        layout.addLayout(toolbar)
        
        # 内容区域（WebView网格 + 配置面板）
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 创建滚动区域包装 WebView 网格容器（支持横向和纵向滚动）
        webview_scroll_area = QScrollArea()
        webview_scroll_area.setWidgetResizable(True)
        webview_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        webview_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        webview_scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:horizontal, QScrollBar:vertical {
                background: #f5f5f5;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal, QScrollBar::handle:vertical {
                background: #c0c0c0;
                border-radius: 4px;
                min-width: 40px;
                min-height: 40px;
            }
            QScrollBar::handle:horizontal:hover, QScrollBar::handle:vertical:hover {
                background: #a0a0a0;
            }
        """)
        
        # WebView 网格容器
        self.webview_container = QWidget()
        self.webview_grid = QGridLayout()
        self.webview_grid.setSpacing(8)
        self.webview_grid.setContentsMargins(4, 4, 4, 4)
        self.webview_container.setLayout(self.webview_grid)
        
        # 设置大小策略，允许容器根据内容扩展
        self.webview_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # 添加提示标签（初始状态）
        self.empty_label = QLabel("请选择名片和链接后点击「开始填写」")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(f"""
            font-size: 16px;
            color: {COLORS['text_secondary']};
            padding: 40px;
        """)
        self.webview_grid.addWidget(self.empty_label, 0, 0)
        
        # 将网格容器放入滚动区域
        webview_scroll_area.setWidget(self.webview_container)
        
        content_splitter.addWidget(webview_scroll_area)
        
        # 配置面板
        self.config_panel = self.create_config_panel()
        self.config_panel.setMaximumWidth(300)
        self.config_panel.setVisible(False)
        content_splitter.addWidget(self.config_panel)
        
        content_splitter.setSizes([1000, 300])
        
        layout.addWidget(content_splitter)
        
        return panel
    
    def create_config_panel(self) -> QWidget:
        """创建配置面板"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setStyleSheet("background-color: #fffbea;")
        
        layout = QVBoxLayout()
        panel.setLayout(layout)
        
        title_label = QLabel("📋 当前配置")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px; background-color: #ffd04b;")
        layout.addWidget(title_label)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.config_content = QWidget()
        self.config_content_layout = QVBoxLayout()
        self.config_content.setLayout(self.config_content_layout)
        
        scroll.setWidget(self.config_content)
        layout.addWidget(scroll)
        
        return panel
    
    def load_cards(self):
        """加载名片列表 - 仅当前用户的名片"""
        self.card_list.clear()
        cards = self.db_manager.get_all_cards(user=self.current_user)
        
        for card in cards:
            item = QListWidgetItem(f"📇 {card.name} ({len(card.configs)} 项)")
            item.setData(Qt.ItemDataRole.UserRole, card)
            self.card_list.addItem(item)
    
    def load_links(self):
        """加载链接列表 - 使用复选框支持多选"""
        # 清空现有复选框
        while self.link_layout.count():
            child = self.link_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.link_checkboxes.clear()
        links = self.db_manager.get_all_links(status='active')
        
        for link in links:
            checkbox = QCheckBox(f"🔗 {link.name}")
            checkbox.setToolTip(link.url)
            checkbox.setProperty("link_data", link)  # 存储链接数据
            checkbox.stateChanged.connect(self.on_link_checkbox_changed)
            checkbox.setStyleSheet(f"""
                QCheckBox {{
                    color: {COLORS['text_primary']};
                    font-size: 13px;
                    padding: 8px;
                    background: {COLORS['surface']};
                    border-radius: 6px;
                }}
                QCheckBox:hover {{
                    background: {COLORS['surface_hover']};
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                }}
            """)
            
            self.link_layout.addWidget(checkbox)
            self.link_checkboxes[link.id] = checkbox
        
        self.link_layout.addStretch()
    
    def on_card_selected(self, item: QListWidgetItem):
        """名片被选中"""
        self.selected_card = item.data(Qt.ItemDataRole.UserRole)
        self.update_config_display()
        self.update_start_button()
    
    def on_link_checkbox_changed(self, state):
        """链接复选框状态变化"""
        # 更新选中的链接列表
        self.selected_links = []
        for link_id, checkbox in self.link_checkboxes.items():
            if checkbox.isChecked():
                link_data = checkbox.property("link_data")
                self.selected_links.append(link_data)
        
        # 如果超过最大数量，取消最后一个的选中状态
        if len(self.selected_links) > self.MAX_LINKS:
            sender = self.sender()
            if isinstance(sender, QCheckBox):
                sender.setChecked(False)
                self.show_message(
                    'warning',
                    '超出限制',
                    f'最多只能同时选择 {self.MAX_LINKS} 个链接'
                )
                return
        
        # 更新计数显示
        self.link_count_label.setText(f"({len(self.selected_links)}/{self.MAX_LINKS})")
        
        # 更新按钮状态
        self.update_start_button()
    
    def update_start_button(self):
        """更新开始按钮状态"""
        self.btn_start.setEnabled(
            self.selected_card is not None and len(self.selected_links) > 0
        )
        
        # 更新按钮文字
        if len(self.selected_links) > 0:
            self.btn_start.setText(f"✏️ 开始填写 ({len(self.selected_links)} 个表单)")
        else:
            self.btn_start.setText("✏️ 开始自动填写")
    
    def update_config_display(self):
        """更新配置显示"""
        # 清空现有内容
        while self.config_content_layout.count():
            child = self.config_content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        if not self.selected_card:
            empty_label = QLabel("未选择名片")
            empty_label.setStyleSheet("color: #999; padding: 20px;")
            self.config_content_layout.addWidget(empty_label)
            return
        
        # 显示名片名称
        name_label = QLabel(f"<b>{self.selected_card.name}</b>")
        name_label.setStyleSheet("padding: 10px; font-size: 14px;")
        self.config_content_layout.addWidget(name_label)
        
        # 显示配置项
        for config in self.selected_card.configs:
            config_frame = QGroupBox()
            config_frame.setStyleSheet("""
                QGroupBox {
                    background: white;
                    border-radius: 4px;
                    padding: 8px;
                    margin: 2px;
                }
            """)
            
            config_layout = QVBoxLayout()
            config_frame.setLayout(config_layout)
            
            key_label = QLabel(f"<b style='color: #667eea;'>{config.key}</b>")
            config_layout.addWidget(key_label)
            
            value_label = QLabel(config.value)
            value_label.setWordWrap(True)
            value_label.setStyleSheet("color: #333; padding-top: 5px;")
            config_layout.addWidget(value_label)
            
            self.config_content_layout.addWidget(config_frame)
        
        self.config_content_layout.addStretch()
    
    def create_webview_with_label(self, link: Link, index: int) -> QWidget:
        """创建带标签的WebView容器
        
        Args:
            link: 链接对象
            index: 索引（用于显示）
        
        Returns:
            包含标签和WebView的容器
        """
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        
        # 设置最小尺寸，确保每个 WebView 有足够的显示空间
        container.setMinimumSize(400, 300)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # 移除边距，使 WebView 占满容器
        layout.setSpacing(0)
        container.setLayout(layout)
        
        # 标签头部 - 已隐藏
        # header = QHBoxLayout()
        # 
        # label = QLabel(f"#{index+1} {link.name}")
        # label.setStyleSheet(f"""
        #     font-size: 12px;
        #     font-weight: 600;
        #     color: {COLORS['text_primary']};
        #     padding: 4px 8px;
        #     background: {COLORS['primary']};
        #     color: white;
        #     border-radius: 4px;
        # """)
        # label.setToolTip(link.url)
        # header.addWidget(label)
        # 
        # # 状态标签
        # status_label = QLabel("⏳ 加载中...")
        # status_label.setStyleSheet(f"""
        #     font-size: 11px;
        #     color: {COLORS['text_secondary']};
        #     padding: 4px;
        # """)
        # header.addWidget(status_label)
        # header.addStretch()
        # 
        # layout.addLayout(header)
        
        # WebView - 创建独立的 Profile（独立的 cookie、缓存、token）
        web_view = QWebEngineView()
        
        # 为每个 WebView 创建独立的离线 Profile（不共享数据）
        # 使用 off-the-record 模式，每个实例都有独立的存储
        profile = QWebEngineProfile(f"profile_{index}_{id(link)}", web_view)
        
        # 设置为离线模式（不持久化到磁盘，每个实例完全独立）
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
        
        # 设置中文语言
        profile.setHttpAcceptLanguage("zh-CN,zh;q=0.9,en;q=0.8")
        
        # 设置 User-Agent
        user_agent = profile.httpUserAgent()
        if 'zh-CN' not in user_agent:
            profile.setHttpUserAgent(user_agent + " Language/zh-CN")
        
        # 禁用控制台消息输出（减少日志）
        class WebEnginePage(QWebEnginePage):
            def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
                # print(f"JS [#{index+1}] ({level}): {message}")  # 已禁用详细日志
                pass  # 不输出 JS 控制台消息
        
        web_view.setPage(WebEnginePage(profile, web_view))
        web_view.setUrl(QUrl(link.url))
        
        print(f"  🔒 WebView #{index+1} 使用独立 Profile: {profile.storageName()}")
        
        # 存储相关信息（使用字符串状态代替QLabel，避免UI问题）
        web_view.setProperty("link_data", link)
        web_view.setProperty("status_text", "⏳ 加载中...")  # 使用字符串状态
        web_view.setProperty("index", index)
        
        # 监听加载完成
        web_view.loadFinished.connect(lambda success: self.on_webview_loaded(web_view, success))
        
        layout.addWidget(web_view)
        
        return container
    
    def calculate_grid_layout(self, count: int):
        """计算网格布局（行列数）
        
        Args:
            count: WebView数量
        
        Returns:
            (rows, cols) 元组
        """
        if count == 1:
            return (1, 1)
        elif count == 2:
            return (1, 2)
        elif count <= 4:
            return (2, 2)
        elif count <= 6:
            return (2, 3)
        else:  # 7-9
            return (3, 3)
    
    def start_auto_fill(self):
        """开始自动填写 - 支持多链接"""
        if not self.selected_card or len(self.selected_links) == 0:
            return
        
        # 显示加载提示
        link_names = "\n".join([f"  • {link.name}" for link in self.selected_links])
        self.show_message(
            'information',
            '开始填写',
            f"将同时加载 {len(self.selected_links)} 个表单\n"
            f"将在页面加载完成后 {config.AUTO_FILL_DELAY/1000} 秒开始自动填写\n\n"
            f"名片: {self.selected_card.name}\n\n"
            f"链接列表:\n{link_names}"
        )
        
        # 清空现有WebView
        self.clear_webviews()
        
        # 计算网格布局
        rows, cols = self.calculate_grid_layout(len(self.selected_links))
        
        # 创建多个WebView
        self.web_views = []
        for index, link in enumerate(self.selected_links):
            container = self.create_webview_with_label(link, index)
            
            # 获取WebView（索引0，唯一的widget）
            web_view = container.layout().itemAt(0).widget()
            self.web_views.append(web_view)
            
            # 计算位置
            row = index // cols
            col = index % cols
            self.webview_grid.addWidget(container, row, col)
        
        # 更新URL标签
        self.url_label.setText(f"正在加载 {len(self.selected_links)} 个表单...")
        
        # 显示配置面板
        self.config_panel.setVisible(True)
    
    def clear_webviews(self):
        """清空所有WebView"""
        # 清空网格布局
        while self.webview_grid.count():
            child = self.webview_grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.web_views = []
    
    def on_webview_loaded(self, web_view: QWebEngineView, success: bool):
        """单个WebView加载完成
        
        Args:
            web_view: WebView对象
            success: 是否加载成功
        """
        link_data = web_view.property("link_data")
        index = web_view.property("index")
        
        if not success:
            web_view.setProperty("status_text", "❌ 加载失败")
            print(f"❌ WebView #{index+1} ({link_data.name}) 加载失败")
            return
        
        web_view.setProperty("status_text", "✅ 已加载")
        print(f"✅ WebView #{index+1} ({link_data.name}) 加载完成")
        
        # 检查是否所有页面都加载完成
        all_loaded = all(
            wv.property("status_text") and 
            ("✅" in wv.property("status_text") or "❌" in wv.property("status_text"))
            for wv in self.web_views
        )
        
        if all_loaded:
            self.url_label.setText(f"所有表单已加载完成，准备自动填写...")
            # 延迟执行自动填写
            QTimer.singleShot(config.AUTO_FILL_DELAY, self.execute_all_auto_fill)
    
    def execute_all_auto_fill(self):
        """执行所有WebView的自动填写"""
        if not self.selected_card:
            return
        
        print(f"\n{'='*60}")
        print(f"🚀 开始同时填写 {len(self.web_views)} 个表单")
        print(f"{'='*60}\n")
        
        # 为每个WebView执行自动填写
        for index, web_view in enumerate(self.web_views):
            link_data = web_view.property("link_data")
            status_text = web_view.property("status_text")
            
            # 检查是否加载成功
            if status_text and "❌" in status_text:
                print(f"⏭️  跳过 WebView #{index+1} ({link_data.name}) - 加载失败")
                continue
            
            print(f"📝 填写 WebView #{index+1}: {link_data.name}")
            
            # 更新状态
            web_view.setProperty("status_text", "⏳ 填写中...")
            
            # 执行填写
            self.execute_auto_fill_for_webview(web_view, index)
        
        self.url_label.setText(f"正在填写 {len(self.web_views)} 个表单...")
    
    def detect_form_type(self, url: str) -> str:
        """
        检测表单类型
        
        Args:
            url: 表单URL
        
        Returns:
            'tencent_docs', 'mikecrm', 或 'unknown'
        """
        if 'docs.qq.com/form' in url:
            return 'tencent_docs'
        elif 'mikecrm.com' in url:
            return 'mikecrm'
        else:
            return 'unknown'
    
    def execute_auto_fill_for_webview(self, web_view: QWebEngineView, index: int):
        """为单个WebView执行自动填写
        
        Args:
            web_view: WebView对象
            index: 索引
        """
        if not self.selected_card:
            return
        
        link_data = web_view.property("link_data")
        current_url = web_view.url().toString()
        
        # 检测表单类型
        form_type = self.detect_form_type(current_url)
        print(f"  🔍 检测到表单类型: {form_type}")
        
        # 准备填写数据
        if form_type == 'tencent_docs':
            # 腾讯文档需要字典格式
            fill_data = {}
            for config in self.selected_card.configs:
                fill_data[config.key] = config.value
            
            # 使用腾讯文档填写引擎
            js_code = self.tencent_docs_engine.generate_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟3秒后获取结果
            QTimer.singleShot(3000, lambda: self.get_auto_fill_result_for_webview(web_view, index, 'tencent_docs'))
            
        elif form_type == 'mikecrm':
            # 麦客CRM需要列表格式
            fill_data = []
            for config in self.selected_card.configs:
                fill_data.append({
                    'key': config.key,
                    'value': config.value
                })
            
            # 使用麦客CRM填写引擎
            js_code = self.auto_fill_engine.generate_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟3秒后获取结果
            QTimer.singleShot(3000, lambda: self.get_auto_fill_result_for_webview(web_view, index, 'mikecrm'))
            
        else:
            print(f"  ⚠️  未知表单类型: {current_url}")
            web_view.setProperty("status_text", "❓ 未知类型")
    
    def get_auto_fill_result_for_webview(self, web_view: QWebEngineView, index: int, form_type: str):
        """
        获取单个WebView的自动填写结果
        
        Args:
            web_view: WebView对象
            index: 索引
            form_type: 表单类型 ('tencent_docs' 或 'mikecrm')
        """
        # 根据表单类型选择引擎
        if form_type == 'tencent_docs':
            engine = self.tencent_docs_engine
        else:
            engine = self.auto_fill_engine
        
        # 生成获取结果的脚本
        get_result_script = engine.generate_get_result_script()
        
        def handle_result(result):
            link_data = web_view.property("link_data")
            
            print(f"  📊 WebView #{index+1} ({link_data.name}) 结果: {result}")
            
            if result and isinstance(result, dict):
                # 检查是否还在等待
                if result.get('status') == 'waiting':
                    # 再等2秒重试
                    QTimer.singleShot(2000, lambda: self.get_auto_fill_result_for_webview(web_view, index, form_type))
                    return
                
                # 根据表单类型解析结果
                if form_type == 'tencent_docs':
                    filled = result.get('filled', [])
                    failed = result.get('failed', [])
                    fill_count = len(filled)
                    total_count = len(filled) + len(failed)
                else:
                    fill_count = result.get('fillCount', 0)
                    total_count = result.get('totalCount', 0)
                
                # 保存记录到数据库
                self.db_manager.create_fill_record(
                    self.selected_card.id,
                    link_data.id,
                    fill_count,
                    total_count,
                    success=(fill_count > 0)
                )
                
                # 更新状态
                if fill_count > 0:
                    web_view.setProperty("status_text", f"✅ 已填 {fill_count}/{total_count}")
                else:
                    web_view.setProperty("status_text", "❌ 填写失败")
                
                print(f"  {'✅' if fill_count > 0 else '❌'} WebView #{index+1}: 填写 {fill_count}/{total_count} 个字段")
            else:
                print(f"  ⚠️  WebView #{index+1}: 无法获取填写结果")
                web_view.setProperty("status_text", "❓ 结果未知")
            
            # 检查是否所有表单都完成填写
            self.check_all_fills_completed()
        
        web_view.page().runJavaScript(get_result_script, handle_result)
    
    def check_all_fills_completed(self):
        """检查是否所有表单都填写完成"""
        all_completed = True
        success_count = 0
        failed_count = 0
        
        for web_view in self.web_views:
            status_text = web_view.property("status_text")
            if status_text:
                if "✅ 已填" in status_text:
                    success_count += 1
                elif "❌" in status_text or "❓" in status_text:
                    failed_count += 1
                else:
                    all_completed = False
                    break
        
        if all_completed:
            # 发送信号
            self.fill_completed.emit()
            
            # 更新URL标签
            self.url_label.setText(f"全部完成！成功: {success_count}, 失败: {failed_count}")
            
            # 显示汇总消息 - 已禁用弹窗
            total = success_count + failed_count
            # msg = f"所有表单填写完成！\n\n"
            # msg += f"成功: {success_count} 个\n"
            # msg += f"失败: {failed_count} 个\n"
            # msg += f"总计: {total} 个表单"
            
            # if success_count > 0:
            #     self.show_message('success', '✅ 全部完成', msg)
            # else:
            #     self.show_message('warning', '⚠️ 填写结束', msg)
            
            print(f"\n{'='*60}")
            print(f"✅ 所有表单填写完成！成功: {success_count}/{total}")
            print(f"{'='*60}\n")
    
    def refresh_all_webviews(self):
        """刷新所有 WebView"""
        for web_view in self.web_views:
            web_view.reload()
        self.url_label.setText(f"正在刷新 {len(self.web_views)} 个表单...")
    
    def toggle_config_panel(self):
        """切换配置面板显示"""
        self.config_panel.setVisible(not self.config_panel.isVisible())



