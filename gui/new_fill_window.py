"""
新的开始填充页面 - 符合设计图2
支持多名片、多链接的填充，带标签页切换
"""
from PyQt6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QComboBox, QMessageBox, QFrame, QScrollArea,
                             QGraphicsDropShadowEffect, QApplication, QTabWidget,
                             QGridLayout, QSizePolicy, QStackedWidget, QLineEdit, QInputDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QUrl, QSize
from PyQt6.QtGui import QColor, QClipboard
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
import qtawesome as qta
import json
from collections import defaultdict
from database import DatabaseManager
from core import AutoFillEngineV2, TencentDocsFiller
from .baoming_tool_window import BaomingToolWindow
from .styles import COLORS
from .icons import Icons
import config


class NewFillWindow(QDialog):
    """新的填充窗口 - 多名片多链接，带标签页"""
    
    fill_completed = pyqtSignal()
    
    def __init__(self, selected_cards, selected_links, parent=None, current_user=None, columns=4, fill_mode="multi"):
        super().__init__(parent)
        self.selected_cards = selected_cards  # 选中的名片列表
        self.selected_links = selected_links  # 选中的链接列表
        self.current_user = current_user
        self.columns = columns
        self.fill_mode = fill_mode
        self.db_manager = DatabaseManager()
        self.auto_fill_engine = AutoFillEngineV2()
        self.tencent_docs_engine = TencentDocsFiller()
        self.current_card = None  # 当前查看的名片
        self.web_views_by_link = {}  # {link_id: [web_views]}
        
        # 单开模式下，默认选中第一个名片
        if self.fill_mode == "single" and self.selected_cards:
            self.current_card = self.selected_cards[0]
            
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("开始填充")
        self.setWindowState(Qt.WindowState.WindowMaximized)
        # ⚡️ 修复：使用 WindowModal 而不是 ApplicationModal，避免阻塞整个应用
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Window)
        
        # 设置背景色
        self.setStyleSheet(f"""
            QWidget {{
                background: {COLORS['background']};
            }}
        """)
        
        # 主布局
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)
        
        # 左侧：标签页 + WebView 网格
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)
        
        # 右侧：类别、名片选择、名片信息
        self.right_panel = self.create_right_panel()
        main_layout.addWidget(self.right_panel)
        
        # 动画状态标记
        self.is_panel_animating = False
        
        # 悬浮的展开按钮 (默认隐藏)
        self.expand_btn = QPushButton(self)
        self.expand_btn.setIcon(Icons.chevron_left('gray'))
        self.expand_btn.setFixedSize(32, 32)
        self.expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.expand_btn.setStyleSheet(f"""
            QPushButton {{
                background: white;
                border: 1px solid {COLORS['border']};
                border-top-left-radius: 4px;
                border-bottom-left-radius: 4px;
            }}
            QPushButton:hover {{
                background: {COLORS['surface_hover']};
            }}
        """)
        self.expand_btn.hide()
        self.expand_btn.clicked.connect(self.show_right_panel)
        self.expand_btn.raise_() # 确保在最上层
        
        # ⚡️ 窗口打开后自动开始加载WebView
        QTimer.singleShot(500, self.auto_start_loading_webviews)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'expand_btn'):
            self.expand_btn.move(self.width() - 32, 60)

    def hide_right_panel(self):
        """隐藏右侧面板 - 快速平滑"""
        if not hasattr(self, 'right_panel') or self.is_panel_animating:
            return
        
        self.is_panel_animating = True
        
        # 快速3步收缩动画
        steps = [300, 150, 0]
        
        def animate_step(i):
            if i >= len(steps):
                self.right_panel.hide()
                self.right_panel.setMinimumWidth(400)
                self.right_panel.setMaximumWidth(400)
                self.expand_btn.show()
                self.is_panel_animating = False
                return
            
            self.right_panel.setMaximumWidth(steps[i])
            self.right_panel.setMinimumWidth(0)
            QTimer.singleShot(30, lambda: animate_step(i + 1))
        
        animate_step(0)
            
    def show_right_panel(self):
        """显示右侧面板 - 快速平滑"""
        if not hasattr(self, 'right_panel') or self.is_panel_animating:
            return
        
        self.is_panel_animating = True
        self.expand_btn.hide()
        
        # 先设置初始状态
        self.right_panel.setMinimumWidth(0)
        self.right_panel.setMaximumWidth(0)
        self.right_panel.show()
        
        # 快速3步展开动画
        steps = [150, 300, 400]
        
        def animate_step(i):
            if i >= len(steps):
                self.right_panel.setMinimumWidth(400)
                self.right_panel.setMaximumWidth(400)
                self.is_panel_animating = False
                return
            
            self.right_panel.setMaximumWidth(steps[i])
            QTimer.singleShot(30, lambda: animate_step(i + 1))
        
        QTimer.singleShot(10, lambda: animate_step(0))
    
    def create_left_panel(self) -> QWidget:
        """创建左侧面板（顶部导航 + 标签页 + WebView）"""
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background: #F5F7FA;
                border: none;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        panel.setLayout(layout)
        
        # 鉴于时间，我们使用 QTabWidget，并把 返回按钮设置为 CornerWidget (TopLeftCorner)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True) # 文档模式，去掉边框
        self.tab_widget.setUsesScrollButtons(True)  # 启用滚动按钮
        self.tab_widget.setElideMode(Qt.TextElideMode.ElideRight)  # 文字过长时显示省略号
        
        # 优化 Tab 样式：胶囊型 + 悬浮效果 + 阴影
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: #F5F7FA;
                border-top: 1px solid #E5E5EA;
            }}
            QTabWidget::tab-bar {{
                alignment: left;
            }}
            QTabBar::tab {{
                background: transparent;
                color: #6E6E73;
                padding: 8px 20px;
                min-width: 90px;
                font-size: 14px;
                font-weight: 500;
                margin: 8px 4px;
                border-radius: 16px; /* 胶囊形状 */
            }}
            QTabBar::tab:selected {{
                background: white;
                color: {COLORS['primary']};
                font-weight: 600;
                /* 选中时的阴影效果 */
                border: 1px solid #E5E5EA;
            }}
            QTabBar::tab:hover {{
                background: rgba(0, 0, 0, 0.04);
                color: #1D1D1F;
            }}
            /* 滚动按钮样式 */
            QTabBar::scroller {{
                width: 24px;
            }}
            QTabBar QToolButton {{
                border: none;
                background: transparent;
                border-radius: 4px;
            }}
            QTabBar QToolButton:hover {{
                background: rgba(0, 0, 0, 0.05);
            }}
        """)
        
        # 添加"首页"标签
        home_tab = QWidget() # 空Widget，仅作为触发器
        self.tab_widget.addTab(home_tab, "首页")
        self.tab_widget.setTabToolTip(0, "返回主界面")
        
        for i, link in enumerate(self.selected_links):
            tab_content = self.create_link_tab_content(link)
            self.tab_widget.addTab(tab_content, link.name)
            
            # 设置鼠标悬浮显示的更多信息
            status_text = "正常" if link.status else "已禁用"
            # 使用更好看的 Tooltip 样式
            tooltip = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: -apple-system, sans-serif; color: #333; }}
                    h4 {{ margin: 0 0 8px 0; color: {COLORS['primary']}; }}
                    p {{ margin: 4px 0; font-size: 12px; }}
                </style>
            </head>
            <body>
                <h4>{link.name}</h4>
                <p>🔗 <b>URL:</b> {link.url}</p>
                <p>🏷️ <b>分类:</b> {link.category if link.category else '未分类'}</p>
                <p>📊 <b>状态:</b> {status_text}</p>
            </body>
            </html>
            """
            self.tab_widget.setTabToolTip(i + 1, tooltip.strip())
            
        # 设置当前选中为第一个链接（索引1）
        if self.selected_links:
            self.tab_widget.setCurrentIndex(1)
            
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        layout.addWidget(self.tab_widget)
        
        return panel
    
    def create_link_tab_content(self, link) -> QWidget:
        """创建单个链接的标签页内容 - 延迟加载优化"""
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        container.setLayout(layout)
        
        # 链接标题容器
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        link_label = QLabel(f"链接: {link.name}")
        link_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {COLORS['text_primary']};
            padding: 10px;
        """)
        header_layout.addWidget(link_label)
        header_layout.addStretch()
        
        # 单开/多开 切换开关
        self.mode_switch_btn = QPushButton("切换模式: 单开")
        if self.fill_mode == "multi":
             self.mode_switch_btn.setText("切换模式: 多开")
             
        self.mode_switch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_switch_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 6px 12px;
                color: {COLORS['text_primary']};
            }}
            QPushButton:hover {{
                background: {COLORS['surface_hover']};
            }}
        """)
        self.mode_switch_btn.clicked.connect(lambda: self.toggle_fill_mode(link))
        header_layout.addWidget(self.mode_switch_btn)
        
        layout.addWidget(header_container)
        
        # 横向滚动区域（包含多个名片WebView占位符）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # ⚡️ 确保滚动区域不阻止鼠标事件传递给WebView
        scroll_area.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)
        
        # 名片容器（网格布局）
        cards_container = QWidget()
        
        # ⚡️ 确保容器不阻止鼠标事件
        cards_container.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        cards_layout = QGridLayout()
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(16)
        cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        cards_container.setLayout(cards_layout)
        
        # ⚡️ 优化：不立即创建WebView，只创建占位符
        link_webview_info = []
        MAX_COLUMNS = self.columns  # 使用传入的列数设置
        
        if self.fill_mode == "single":
            # 单开模式：只创建一个居中的占位符，并尽量撑满
            cards_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # 使用当前选中的名片（默认第一个）
            card = self.current_card if self.current_card else self.selected_cards[0]
            
            # 创建占位容器 - 宽度撑满，高度尽量大
            placeholder = self.create_placeholder(card, link, 0)
            
            # 关键修改：移除固定大小限制，允许自适应
            placeholder.setMinimumWidth(800) 
            placeholder.setMinimumHeight(600)
            placeholder.setMaximumWidth(16777215) # QWIDGETSIZE_MAX
            
            # 设置SizePolicy为Expanding
            placeholder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            
            cards_layout.addWidget(placeholder, 0, 0)
            
            # 存储创建信息
            link_webview_info.append({
                'card': card,
                'link': link,
                'index': 0,
                'placeholder': placeholder,
                'web_view': None,  # 延迟创建
                'loaded': False
            })
            
        else:
            # 多开模式：创建网格
            cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            
            for index, card in enumerate(self.selected_cards):
                # 计算行列
                row = index // MAX_COLUMNS
                col = index % MAX_COLUMNS
                
                # 创建占位容器
                placeholder = self.create_placeholder(card, link, index)
                cards_layout.addWidget(placeholder, row, col)
                
                # 存储创建信息（延迟创建）
                link_webview_info.append({
                    'card': card,
                    'link': link,
                    'index': index,
                    'placeholder': placeholder,
                    'web_view': None,  # 延迟创建
                    'loaded': False
                })
        
        # 存储该链接的WebView信息
        self.web_views_by_link[str(link.id)] = link_webview_info
        
        print(f"✅ 为链接 '{link.name}' 准备了 {len(link_webview_info)} 个占位符（延迟加载）")
        
        scroll_area.setWidget(cards_container)
        layout.addWidget(scroll_area, 1)
        
        return container
    
    def toggle_fill_mode(self, link):
        """切换单开/多开模式"""
        new_mode = "single" if self.fill_mode == "multi" else "multi"
        
        print(f"🔄 切换模式: {self.fill_mode} -> {new_mode}")
        self.fill_mode = new_mode
        
        # 更新按钮文字
        if self.fill_mode == "multi":
            self.mode_switch_btn.setText("切换模式: 多开")
        else:
            self.mode_switch_btn.setText("切换模式: 单开")
            
        # ⚡️ 清空当前链接的 WebView 缓存信息，确保重新创建
        link_id = str(link.id)
        if link_id in self.web_views_by_link:
            del self.web_views_by_link[link_id]
            
        # 同时也清理加载队列，防止旧任务干扰
        if hasattr(self, 'loading_queues') and link_id in self.loading_queues:
            del self.loading_queues[link_id]
            
        # 强制重新创建当前 Tab 的内容
        # 获取当前 Tab 的索引
        current_index = self.tab_widget.currentIndex()
        
        # ⚡️ 关键修复：暂时断开 currentChanged 信号，防止 removeTab 触发窗口关闭
        # 因为 on_tab_changed 中检查 index == 0 会关闭窗口
        self.tab_widget.currentChanged.disconnect(self.on_tab_changed)
        
        try:
            # 移除当前 Tab
            self.tab_widget.removeTab(current_index)
            
            # 重新创建内容
            new_content = self.create_link_tab_content(link)
            
            # 插入回原来的位置
            self.tab_widget.insertTab(current_index, new_content, link.name)
            self.tab_widget.setCurrentIndex(current_index)
        finally:
            # 重新连接信号
            self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        # ⚡️ 重新触发加载逻辑：因为清理了 web_views_by_link，on_tab_changed 会认为这是首次访问，从而调用 load_webviews_only
        # 我们需要确保 load_webviews_only 被调用
        
        # 手动构造 webview_infos (因为 create_link_tab_content 已经重建了它们并存入 web_views_by_link)
        webview_infos = self.web_views_by_link.get(link_id, [])
        
        if webview_infos:
             print(f"⚡️ 模式切换后，重新触发加载流程 ({len(webview_infos)} 个视图)")
             
             # ⚡️ 关键修复：在 info 中设置标记，让 WebView 创建后能获取到这个标记
             # 因为此时 web_view 还是 None（延迟加载），不能直接设置 property
             for info in webview_infos:
                 info['auto_fill_after_switch'] = True
             
             self.load_webviews_only(webview_infos)
                     
        else:
             print("⚠️ 模式切换后未找到 WebView 信息")
    
    def create_placeholder(self, card, link, index: int) -> QFrame:
        """创建WebView占位符"""
        container = QFrame()
        container.setMinimumWidth(350)
        container.setMaximumWidth(400)
        container.setMinimumHeight(500)
        # 新的卡片样式：更柔和的阴影，更纯净的背景，去除了边框（用阴影代替）
        container.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-radius: 16px;
                border: 1px solid rgba(0, 0, 0, 0.06); /* 极淡的边框 */
            }}
        """)
        
        # ⚡️ 确保容器不阻止鼠标事件
        container.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        
        # ⚡️ 启用实时渲染，避免延迟
        container.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        container.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        container.setLayout(layout)
        
        # 头部：名片名称 - 重新设计：白色背景，底部细微分割线
        header = QFrame()
        header.setFixedHeight(56)  # 稍微增加高度，更透气
        header.setStyleSheet(f"""
            QFrame {{
                background: white; /* 改为白色背景 */
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
                border-bottom: 1px solid #F5F5F5;
            }}
        """)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(16, 0, 16, 0)  # 左右内边距
        header_layout.setSpacing(12)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        header.setLayout(header_layout)
        
        # 图标 - 换成深色图标
        icon_label = QLabel()
        icon_label.setFixedSize(24, 24) # 稍微放大图标
        # 使用深色图标
        icon_label.setPixmap(Icons.get('fa5s.user-circle', '#333333').pixmap(24, 24))
        header_layout.addWidget(icon_label)
        
        name_label = QLabel(card.name)
        name_label.setStyleSheet(f"""
            font-size: 15px;
            font-weight: 700; /* 加粗 */
            color: #1D1D1F; /* 深色文字 */
        """)
        header_layout.addWidget(name_label)
        
        header_layout.addStretch()
        
        # 刷新按钮 - 图标按钮风格
        refresh_btn = QPushButton()
        refresh_btn.setIcon(Icons.refresh('#666666'))
        refresh_btn.setIconSize(QSize(16, 16))
        refresh_btn.setFixedSize(32, 32)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setToolTip("刷新页面")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 16px;
            }
            QPushButton:hover {
                background: #F2F2F7;
                border: 1px solid #E5E5EA;
            }
        """)
        refresh_btn.clicked.connect(lambda: self.refresh_webview(str(link.id), index))
        header_layout.addWidget(refresh_btn)
        
        # 填充按钮 - 重新设计
        fill_btn = QPushButton("填充")
        fill_btn.setIcon(Icons.play('white')) # 白色图标
        fill_btn.setIconSize(QSize(12, 12))
        # fill_btn.setFixedSize(84, 32) # 移除固定尺寸，改用最小宽度和固定高度
        fill_btn.setMinimumWidth(80)
        fill_btn.setFixedHeight(34)
        fill_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # 扁平化设计，移除复杂渐变和margin
        fill_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 17px; /* 高度的一半 */
                font-size: 13px;
                font-weight: 600;
                padding: 0 12px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {COLORS['primary_dark']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary_dark']};
                padding-top: 2px; /* 按下效果 */
            }}
        """)
        fill_btn.clicked.connect(lambda: self.fill_single_webview(str(link.id), index))
        header_layout.addWidget(fill_btn)
        
        layout.addWidget(header)
        
        # 占位内容
        content = QFrame()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content.setLayout(content_layout)
        
        # 占位图标和文字
        hint_container = QWidget()
        hint_vbox = QVBoxLayout(hint_container)
        
        loading_icon = QLabel()
        loading_icon.setPixmap(Icons.get('fa5s.hourglass-half', '#CCCCCC').pixmap(48, 48))
        loading_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        hint_label = QLabel("正在准备加载...")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setStyleSheet(f"""
            font-size: 14px;
            color: {COLORS['text_tertiary']};
            margin-top: 12px;
        """)
        
        hint_vbox.addStretch()
        hint_vbox.addWidget(loading_icon)
        hint_vbox.addWidget(hint_label)
        hint_vbox.addStretch()
        
        content_layout.addWidget(hint_container)
        
        layout.addWidget(content, 1)  # 确保占位内容占满剩余空间
        
        return container
    
    def create_card_webview(self, card, link, index: int) -> tuple:
        """创建单个名片的WebView卡片
        
        Returns:
            (container, web_view) 元组
        """
        container = QFrame()
        container.setMinimumWidth(350)
        container.setMaximumWidth(400)
        container.setMinimumHeight(500)
        # 新的卡片样式
        container.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-radius: 16px;
                border: 1px solid rgba(0, 0, 0, 0.06);
            }}
        """)
        
        # ⚡️ 启用实时渲染
        container.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        container.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        container.setLayout(layout)
        
        # 头部：名片名称 - 与 placeholder 保持一致
        header = QFrame()
        header.setFixedHeight(56)
        header.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
                border-bottom: 1px solid #F5F5F5;
            }}
        """)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(16, 0, 16, 0)
        header_layout.setSpacing(12)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        header.setLayout(header_layout)
        
        # 图标
        icon_label = QLabel()
        icon_label.setFixedSize(24, 24)
        icon_label.setPixmap(Icons.get('fa5s.user-circle', '#333333').pixmap(24, 24))
        header_layout.addWidget(icon_label)
        
        name_label = QLabel(card.name)
        name_label.setStyleSheet(f"""
            font-size: 15px;
            font-weight: 700;
            color: #1D1D1F;
        """)
        header_layout.addWidget(name_label)
        
        header_layout.addStretch()
        
        # 刷新按钮
        refresh_btn = QPushButton()
        refresh_btn.setIcon(Icons.refresh('#666666'))
        refresh_btn.setIconSize(QSize(16, 16))
        refresh_btn.setFixedSize(32, 32)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setToolTip("刷新页面")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 16px;
            }
            QPushButton:hover {
                background: #F2F2F7;
                border: 1px solid #E5E5EA;
            }
        """)
        refresh_btn.clicked.connect(lambda: self.handle_refresh_click(web_view, link, card))
        header_layout.addWidget(refresh_btn)
        
        # 填充按钮
        fill_btn = QPushButton("填充")
        fill_btn.setIcon(Icons.play('white'))
        fill_btn.setIconSize(QSize(12, 12))
        # fill_btn.setFixedSize(90, 36) # 移除固定尺寸
        fill_btn.setMinimumWidth(80)
        fill_btn.setFixedHeight(34)
        fill_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fill_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 17px;
                font-size: 13px;
                font-weight: 600;
                padding: 0 12px;
                text-align: center;
            }}
            QPushButton:hover {{
                background-color: {COLORS['primary_dark']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary_dark']};
                padding-top: 2px;
            }}
        """)
        fill_btn.clicked.connect(lambda: self.handle_fill_click(web_view, link, card))
        header_layout.addWidget(fill_btn)
        
        layout.addWidget(header)
        
        # WebView - 参考 auto_fill_window.py 的创建方式
        web_view = QWebEngineView()
        web_view.setMinimumHeight(450)
        
        # ⚡️ 确保WebView可以交互和实时渲染
        web_view.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        web_view.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # ⚡️ 禁用双缓冲优化，确保实时渲染
        web_view.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        web_view.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        web_view.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors, False)
        
        # 创建独立 Profile（参考 auto_fill_window.py）
        profile = QWebEngineProfile(f"profile_{index}_{id(card)}_{id(link)}", web_view)
        
        # 设置为离线模式（不持久化到磁盘，每个实例完全独立）
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
        
        # 设置中文语言
        profile.setHttpAcceptLanguage("zh-CN,zh;q=0.9,en;q=0.8")
        
        # 设置 User-Agent
        user_agent = profile.httpUserAgent()
        if 'zh-CN' not in user_agent:
            profile.setHttpUserAgent(user_agent + " Language/zh-CN")
        
        # 禁用控制台消息输出
        class WebEnginePage(QWebEnginePage):
            def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
                pass  # 不输出 JS 控制台消息
        
        web_view.setPage(WebEnginePage(profile, web_view))
        
        # 检测是否是报名工具链接
        if 'baominggongju.com' in link.url:
            # 报名工具直接显示自定义登录页面，不加载原始URL
            print(f"  📱 检测到报名工具链接，直接显示登录页面")
            # 延迟初始化报名工具（等待 WebView 完全创建）
            QTimer.singleShot(100, lambda: self.init_baoming_tool_for_webview(web_view, link.url, card))
        else:
            # 其他链接正常加载
            web_view.setUrl(QUrl(link.url))
        
        # ⚡️ 强制刷新，确保加载立即可见
        web_view.show()
        web_view.update()
        
        print(f"  🔒 WebView #{index+1} 使用独立 Profile: {profile.storageName()}")
        print(f"  🌐 加载 WebView: {card.name} -> {link.url}")
        
        # 存储相关信息
        web_view.setProperty("card_data", card)
        web_view.setProperty("link_data", link)
        web_view.setProperty("status", "loading")
        web_view.setProperty("index", index)
        
        # 监听加载完成
        web_view.loadFinished.connect(lambda success: self.on_webview_loaded(web_view, success))
        
        layout.addWidget(web_view, 1)  # stretch factor = 1，让WebView占满剩余空间
        
        return (container, web_view)
    
    def create_right_panel(self) -> QWidget:
        """创建右侧面板"""
        self.right_panel = QFrame()
        self.right_panel.setMinimumWidth(400)
        self.right_panel.setMaximumWidth(400)
        self.right_panel.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-left: 1px solid #E0E0E0;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        self.right_panel.setLayout(layout)
        
        # 顶部工具栏：折叠按钮 + 刷新按钮
        top_toolbar = QHBoxLayout()
        top_toolbar.setSpacing(8)
        
        # 折叠按钮
        collapse_btn = QPushButton()
        collapse_btn.setIcon(Icons.chevron_right('gray'))
        collapse_btn.setFixedSize(32, 32)
        collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        collapse_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background: {COLORS['surface_hover']};
                border-color: {COLORS['primary']};
            }}
        """)
        collapse_btn.clicked.connect(self.hide_right_panel)
        top_toolbar.addWidget(collapse_btn)
        
        top_toolbar.addStretch()
        
        # 全部刷新按钮
        refresh_all_btn = QPushButton("刷新")
        refresh_all_btn.setIcon(Icons.refresh('gray'))
        refresh_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_all_btn.setStyleSheet(f"""
            QPushButton {{
                background: white;
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {COLORS['surface_hover']};
                color: {COLORS['primary']};
                border-color: {COLORS['primary']};
            }}
        """)
        refresh_all_btn.clicked.connect(self.refresh_all_webviews)
        top_toolbar.addWidget(refresh_all_btn)
        
        layout.addLayout(top_toolbar)
        
        # 类别选择区域 - 优化布局
        category_box = QFrame()
        category_box.setStyleSheet("""
            QFrame {
                background: #F8F9FA;
                border-radius: 8px;
                padding: 12px;
                margin-bottom: 8px;
            }
        """)
        cat_layout = QHBoxLayout()
        cat_layout.setContentsMargins(0, 0, 0, 0)
        cat_layout.setSpacing(12)
        category_box.setLayout(cat_layout)
        
        # 左侧占位
        cat_layout.addStretch()
        
        # 中间：类别名称 + 下箭头 (合并在一个容器中)
        center_container = QWidget()
        center_container.setStyleSheet(f"""
            QWidget {{
                background: white;
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 6px 12px;
            }}
        """)
        center_layout = QHBoxLayout()
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)
        center_container.setLayout(center_layout)
        
        self.category_label = QLabel("美妆类")
        self.category_label.setStyleSheet(f"""
            font-size: 15px;
            font-weight: 600;
            color: {COLORS['text_primary']};
            border: none;
            background: transparent;
        """)
        center_layout.addWidget(self.category_label)
        
        arrow_label = QLabel()
        arrow_label.setPixmap(Icons.chevron_down('gray').pixmap(12, 12))
        arrow_label.setStyleSheet("border: none; background: transparent;")
        center_layout.addWidget(arrow_label)
        
        cat_layout.addWidget(center_container)
        
        # 右侧：切换按钮
        switch_cat_btn = QPushButton("切换")
        switch_cat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        switch_cat_btn.setFixedSize(52, 30)
        switch_cat_btn.setStyleSheet(f"""
            QPushButton {{
                background: white;
                color: {COLORS['primary']};
                border: 1px solid {COLORS['primary']};
                border-radius: 4px;
                font-size: 13px;
                padding: 0;
            }}
            QPushButton:hover {{
                background: {COLORS['primary']};
                color: white;
            }}
        """)
        
        # 真正的类别选择器（隐藏）
        self.category_combo = QComboBox()
        self.category_combo.setStyleSheet(f"""
            QComboBox {{
                background: white;
                color: {COLORS['text_primary']};
            }}
        """)
        self.category_combo.currentTextChanged.connect(self.on_category_changed)
        
        # 连接逻辑
        switch_cat_btn.clicked.connect(self.category_combo.showPopup)
        self.category_combo.currentTextChanged.connect(lambda t: self.category_label.setText(t if t else "选择分类"))
        
        cat_layout.addWidget(switch_cat_btn)
        cat_layout.addStretch() # 右侧也加弹簧，保持居中
        
        layout.addWidget(category_box)
        layout.addWidget(self.category_combo)
        self.category_combo.hide() 
        
        # 名片列表（可滚动）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #E0E0E0;
                border-radius: 3px;
            }
        """)
        
        self.cards_list_widget = QWidget()
        self.cards_list_layout = QVBoxLayout()
        self.cards_list_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_list_layout.setSpacing(4)
        self.cards_list_widget.setLayout(self.cards_list_layout)
        
        scroll.setWidget(self.cards_list_widget)
        layout.addWidget(scroll, 4)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background: #E0E0E0; max-height: 1px;")
        layout.addWidget(line)
        
        # 堆叠容器
        self.right_panel_stack = QStackedWidget()
        self.card_info_section = self.create_card_info_section()
        self.right_panel_stack.addWidget(self.card_info_section)
        self.card_edit_section = self.create_card_edit_section()
        self.right_panel_stack.addWidget(self.card_edit_section)
        
        layout.addWidget(self.right_panel_stack, 6)
        
        # 加载数据
        # ⚡️ 修复：临时阻塞信号，避免 load_categories() 触发 on_category_changed 导致 load_cards_list() 被调用两次
        self.category_combo.blockSignals(True)
        self.load_categories()
        self.category_combo.blockSignals(False)
        
        # 手动更新标签文字
        if self.category_combo.count() > 0:
            self.category_label.setText(self.category_combo.currentText())
        
        # 只调用一次 load_cards_list
        self.load_cards_list()
        
        return self.right_panel
    
    def create_card_edit_section(self) -> QWidget:
        """创建名片编辑区域 - 按原型图设计"""
        section = QFrame()
        section.setStyleSheet(f"""
            QFrame {{
                background: white;
                border: none;
                padding: 0px;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(0)
        section.setLayout(layout)
        
        # 顶部标题栏：名片名称输入 + 新增多个字段提示 + 保存按钮
        header = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 16)
        header_layout.setSpacing(12)
        header.setLayout(header_layout)
        
        # 左侧：名片名称输入框
        self.edit_name_input = QLineEdit()
        self.edit_name_input.setPlaceholderText("名片名称")
        self.edit_name_input.setStyleSheet(f"""
            QLineEdit {{
                padding: 8px 12px;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 600;
                background: white;
                color: #333;
            }}
            QLineEdit:focus {{
                border: 1px solid {COLORS['primary']};
            }}
        """)
        header_layout.addWidget(self.edit_name_input, 1)
        
        # 右侧：保存按钮
        save_btn = QPushButton("保存")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # save_btn.setFixedSize(68, 36) # 移除固定尺寸
        save_btn.setMinimumWidth(72)
        save_btn.setFixedHeight(36)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
                padding: 0 12px;
            }}
            QPushButton:hover {{ background: #4DA3FF; }}
        """)
        save_btn.clicked.connect(self.save_card_edit)
        header_layout.addWidget(save_btn)
        
        layout.addWidget(header)
        
        # 分类选择行（隐藏的下拉框）
        cat_row = QWidget()
        cat_row_layout = QHBoxLayout()
        cat_row_layout.setContentsMargins(0, 0, 0, 12)
        cat_row_layout.setSpacing(8)
        cat_row.setLayout(cat_row_layout)
        
        cat_label = QLabel("新增多个字段请用逗号隔开")
        cat_label.setStyleSheet(f"""
            font-size: 13px;
            color: {COLORS['text_secondary']};
        """)
        cat_row_layout.addWidget(cat_label)
        cat_row_layout.addStretch()
        
        # 隐藏的分类选择器
        self.edit_category_combo = QComboBox()
        self.edit_category_combo.hide()
        
        layout.addWidget(cat_row)
        
        # 字段列表容器（滚动）- 确保有足够的空间
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background: transparent;
                min-height: 300px; /* 确保最小高度 */
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #D0D0D0;
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #A0A0A0;
            }
        """)
        
        self.edit_fields_widget = QWidget()
        self.edit_fields_layout = QVBoxLayout()
        self.edit_fields_layout.setContentsMargins(0, 0, 8, 0)  # 右侧留出滚动条空间
        self.edit_fields_layout.setSpacing(12)  # 增加字段间距
        self.edit_fields_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.edit_fields_widget.setLayout(self.edit_fields_layout)
        
        scroll_area.setWidget(self.edit_fields_widget)
        layout.addWidget(scroll_area, 1)  # stretch factor = 1，占据所有剩余空间
        
        self.edit_field_rows = [] # 存储当前编辑的字段行引用
        
        return section

    def create_card_info_section(self) -> QWidget:
        """创建名片信息区域"""
        section = QFrame()
        section.setStyleSheet(f"""
            QFrame {{
                background: white;
                border: none;
                padding: 0px;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 10, 20, 20) # 增加内边距
        layout.setSpacing(16)
        section.setLayout(layout)
        
        # 1. 顶部标题栏：名片名称 + 操作按钮
        header = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header.setLayout(header_layout)
        
        # 名片名称
        self.card_info_title = QLabel("名片名称")
        self.card_info_title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 600;
            color: {COLORS['text_primary']};
        """)
        header_layout.addWidget(self.card_info_title)
        
        header_layout.addStretch()
        
        # 按钮样式
        btn_style = f"""
            QPushButton {{
                background: white;
                color: #595959; /* 深灰色文字 */
                border: 1px solid #D9D9D9;
                border-radius: 4px;
                font-size: 12px;
                padding: 4px 10px;
                min-width: 60px; /* 确保最小宽度 */
            }}
            QPushButton:hover {{
                color: {COLORS['primary']};
                border-color: {COLORS['primary']};
                background: {COLORS['surface_hover']};
            }}
        """
        
        # 重新导入按钮
        reimport_btn = QPushButton("重新导入")
        reimport_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reimport_btn.setStyleSheet(btn_style)
        reimport_btn.clicked.connect(self.reimport_card)
        header_layout.addWidget(reimport_btn)
        
        # 修改字段按钮
        modify_btn = QPushButton("修改字段")
        modify_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        modify_btn.setStyleSheet(btn_style)
        modify_btn.clicked.connect(self.modify_card_fields)
        header_layout.addWidget(modify_btn)
        
        layout.addWidget(header)
        
        # 2. 字段列表容器 (滚动)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #E0E0E0;
                border-radius: 3px;
            }
        """)
        
        self.card_fields_widget = QWidget()
        self.card_fields_layout = QVBoxLayout()
        self.card_fields_layout.setContentsMargins(0, 0, 0, 0)
        self.card_fields_layout.setSpacing(12)
        self.card_fields_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.card_fields_widget.setLayout(self.card_fields_layout)
        
        scroll_area.setWidget(self.card_fields_widget)
        layout.addWidget(scroll_area)
        
        # 3. 底部黄色提示框
        self.note_label = QLabel("多开时，在固定模版内修改字段值和名同步给其他的名片")
        self.note_label.setWordWrap(True)
        self.note_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #595959;
                background: #FFFBE6; /* 浅黄色背景 */
                border: 1px solid #FFE58F; /* 深黄色边框 */
                border-radius: 4px;
                padding: 12px;
            }
        """)
        layout.addWidget(self.note_label)
        
        return section

    def show_card_info(self, card):
        """显示名片信息"""
        self.current_card = card
        
        # 更新标题
        self.card_info_title.setText(card.name)
        
        print(f"\n🔍 显示名片信息: {card.name}")
        
        # 清空字段列表
        while self.card_fields_layout.count():
            child = self.card_fields_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # 显示字段
        if hasattr(card, 'configs') and card.configs:
            field_count = 0
            for config in card.configs:
                key = ""
                value = ""
                
                # 兼容字典和对象两种格式
                if isinstance(config, dict):
                    key = config.get('key', '')
                    value = config.get('value', '')
                elif hasattr(config, 'key'): # 对象格式
                    key = config.key
                    value = getattr(config, 'value', '')
                
                if key:
                    field_widget = self.create_field_item(key, str(value) if value is not None else "")
                    self.card_fields_layout.addWidget(field_widget)
                    field_count += 1
            
            print(f"  - 总共添加了 {field_count} 个字段")
            
            if field_count == 0:
                self.show_empty_hint("该名片暂无字段信息")
        else:
            print(f"  - ⚠️ 名片没有configs或configs为空")
            self.show_empty_hint("该名片暂无配置数据")
            
    def show_empty_hint(self, text):
        """显示空状态提示"""
        hint_label = QLabel(text)
        hint_label.setStyleSheet(f"""
            font-size: 13px;
            color: {COLORS['text_secondary']};
            padding: 20px;
        """)
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card_fields_layout.addWidget(hint_label)
    
    def load_categories(self):
        """加载分类列表（仅包含已选名片的分类）"""
        self.category_combo.clear()
        
        # 获取已选名片的分类
        categories = set()
        for card in self.selected_cards:
            category = card.category if hasattr(card, 'category') and card.category else "默认分类"
            categories.add(category)
        
        if categories:
            for category in sorted(categories):
                self.category_combo.addItem(category)
            
            # 默认选中第一个分类
            if self.category_combo.count() > 0:
                current_cat = self.category_combo.itemText(0)
                self.category_label.setText(current_cat)
        else:
            self.category_combo.addItem("默认分类")
            self.category_label.setText("默认分类")
            
    def on_category_changed(self, category: str):
        """类别改变时"""
        if category:
            self.category_label.setText(category)
        self.load_cards_list()
    
    def load_cards_list(self, target_card_id=None):
        """加载名片列表（仅显示已选名片）"""
        # 清空现有列表
        while self.cards_list_layout.count():
            child = self.cards_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        category = self.category_combo.currentText()
        if not category:
            return
        
        # 显示该类别下的已选名片
        for card in self.selected_cards:
            card_category = card.category if hasattr(card, 'category') and card.category else "默认分类"
            if card_category == category:
                card_btn = self.create_card_list_item(card)
                self.cards_list_layout.addWidget(card_btn)
        
        self.cards_list_layout.addStretch()
        
        # 选中逻辑
        target_btn = None
        if target_card_id:
            for i in range(self.cards_list_layout.count()):
                item = self.cards_list_layout.itemAt(i)
                if item and item.widget():
                    btn = item.widget()
                    if isinstance(btn, QPushButton) and btn.property("card_id") == str(target_card_id):
                        target_btn = btn
                        break
        
        if target_btn:
            target_btn.click()
        elif self.cards_list_layout.count() > 1: # 至少有一个名片 (stretch占了一个)
            first_item = self.cards_list_layout.itemAt(0)
            if first_item and first_item.widget():
                first_item.widget().click()
                
    def refresh_all_webviews(self):
        """刷新当前页面的所有WebView"""
        current_index = self.tab_widget.currentIndex()
        # 0是首页
        if current_index <= 0:
            QMessageBox.information(self, "提示", "请先进入某个链接页面")
            return
            
        real_index = current_index - 1
        if real_index < len(self.selected_links):
            link = self.selected_links[real_index]
            webview_infos = self.web_views_by_link.get(str(link.id), [])
            
            print(f"⟳ 刷新所有WebView: {link.name}")
            for info in webview_infos:
                if info['web_view']:
                    info['web_view'].reload()
                    info['web_view'].setProperty("status", "loading")
            
            QMessageBox.information(self, "提示", "正在刷新当前页面所有名片...")
    
    def create_card_list_item(self, card) -> QPushButton:
        """创建名片列表项"""
        btn = QPushButton(card.name)
        btn.setMinimumHeight(44) # 稍微加高
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setProperty("card_id", str(card.id))
        
        # 移除默认图标，使用自定义布局
        # btn.setIcon(Icons.user('gray'))
        # btn.setIconSize(QSize(16, 16))
        
        # 重新设计样式：类似于联系人列表
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS['text_primary']};
                border: none;
                border-radius: 8px;
                padding: 0 16px;
                text-align: left; /* 左对齐 */
                font-size: 14px;
                margin: 2px 4px;
            }}
            QPushButton:hover {{
                background: {COLORS['surface_hover']};
            }}
            QPushButton:checked {{
                background: {COLORS['surface_hover']}; /* 选中时保持浅灰背景 */
                color: {COLORS['primary']};
                font-weight: 600;
                border-left: 3px solid {COLORS['primary']}; /* 左侧指示条 */
                border-radius: 0 8px 8px 0; /* 左侧直角 */
                padding-left: 13px; /* 补偿边框宽度 */
            }}
        """)
        btn.setCheckable(True) # 支持选中状态
        
        # 点击逻辑：处理选中状态互斥
        def on_click():
            # 取消其他按钮的选中状态
            for i in range(self.cards_list_layout.count()):
                item = self.cards_list_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if isinstance(widget, QPushButton) and widget != btn:
                        widget.setChecked(False)
                        # 恢复样式
                        # widget.setIcon(Icons.user('gray'))

            btn.setChecked(True)
            # btn.setIcon(Icons.check_circle('primary')) # 不再需要切换图标
            
            # 单开模式下，点击切换WebView内容
            if self.fill_mode == "single" and self.current_card != card:
                self.switch_card_single_mode(card)
            
            self.show_card_info(card)
            
        btn.clicked.connect(on_click)
        return btn
    
    def show_card_info(self, card):
        """显示名片信息"""
        self.current_card = card
        
        print(f"\n🔍 显示名片信息: {card.name}")
        
        # 清空字段列表
        while self.card_fields_layout.count():
            child = self.card_fields_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # 显示字段
        if hasattr(card, 'configs') and card.configs:
            field_count = 0
            for config in card.configs:
                key = ""
                value = ""
                
                # 兼容字典和对象两种格式
                if isinstance(config, dict):
                    key = config.get('key', '')
                    value = config.get('value', '')
                elif hasattr(config, 'key'): # 对象格式
                    key = config.key
                    value = getattr(config, 'value', '')
                
                if key:
                    # print(f"  - 添加字段: {key} = {value}")
                    field_widget = self.create_field_item(key, str(value) if value is not None else "")
                    self.card_fields_layout.addWidget(field_widget)
                    field_count += 1
            
            print(f"  - 总共添加了 {field_count} 个字段")
            
            if field_count == 0:
                self.show_empty_hint("该名片暂无字段信息")
        else:
            print(f"  - ⚠️ 名片没有configs或configs为空")
            self.show_empty_hint("该名片暂无配置数据")
            
    def show_empty_hint(self, text):
        """显示空状态提示"""
        hint_label = QLabel(text)
        hint_label.setStyleSheet(f"""
            font-size: 13px;
            color: {COLORS['text_secondary']};
            padding: 20px;
        """)
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card_fields_layout.addWidget(hint_label)
    
    def create_field_item(self, key: str, value: str) -> QWidget:
        """创建字段项（带复制按钮）- 重新设计"""
        widget = QFrame()
        # 卡片化设计
        widget.setStyleSheet(f"""
            QFrame {{
                background: white;
                border: 1px solid #F0F0F5;
                border-radius: 8px;
                padding: 8px 12px;
                margin-bottom: 4px;
            }}
            QFrame:hover {{
                border-color: {COLORS['primary_light']};
                background: #FAFBFC;
            }}
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        widget.setLayout(layout)
        
        # 字段名（垂直布局中的上方或左侧）
        # 这里使用更紧凑的布局：左侧 Label，右侧 Value + Copy
        
        key_label = QLabel(key)
        key_label.setFixedWidth(90)
        key_label.setStyleSheet(f"""
            font-size: 12px;
            font-weight: 600;
            color: {COLORS['text_secondary']};
            border: none;
            background: transparent;
        """)
        layout.addWidget(key_label)
        
        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setFixedWidth(1)
        line.setStyleSheet("background: #E5E5EA; border: none;")
        layout.addWidget(line)
        
        # 值
        value_text = value if value else "（空）"
        value_label = QLabel(value_text)
        value_label.setStyleSheet(f"""
            font-size: 13px;
            color: {COLORS['text_primary']};
            border: none;
            background: transparent;
        """)
        layout.addWidget(value_label, 1)
        
        # 复制按钮（仅图标）
        copy_btn = QPushButton()
        copy_btn.setIcon(Icons.copy('gray'))
        copy_btn.setFixedSize(28, 28)
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setToolTip("复制内容")
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background: #E5E5EA;
            }}
        """)
        copy_btn.clicked.connect(lambda: self.copy_to_clipboard(value))
        layout.addWidget(copy_btn)
        
        return widget
    
    def copy_to_clipboard(self, text: str):
        """复制到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        # 可以添加一个简单的提示
        print(f"已复制: {text}")
    
    def toggle_right_panel(self, panel: QFrame, btn: QPushButton):
        """折叠/展开右侧面板"""
        if panel.isVisible():
            panel.setVisible(False)
            btn.setIcon(Icons.chevron_left('gray'))
        else:
            panel.setVisible(True)
            btn.setIcon(Icons.chevron_right('gray'))

    def modify_card_fields(self):
        """修改字段 - 切换到编辑模式"""
        if not self.current_card:
            QMessageBox.warning(self, "提示", "请先选择名片")
            return
        
        # 填充编辑数据
        self.edit_name_input.setText(self.current_card.name)
        
        # 填充分类
        self.edit_category_combo.clear()
        # 获取当前所有分类（复用现有的category_combo的数据）
        for i in range(self.category_combo.count()):
            self.edit_category_combo.addItem(self.category_combo.itemText(i))
        
        current_cat = self.current_card.category if hasattr(self.current_card, 'category') and self.current_card.category else "默认分类"
        self.edit_category_combo.setCurrentText(current_cat)
        
        # 清空旧字段
        while self.edit_fields_layout.count():
            child = self.edit_fields_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.edit_field_rows = []
        
        # 填充字段
        if hasattr(self.current_card, 'configs') and self.current_card.configs:
            import json
            configs = self.current_card.configs
            # 兼容字符串格式
            if isinstance(configs, str):
                try:
                    configs = json.loads(configs)
                except:
                    configs = []
            
            for config in configs:
                key = ""
                value = ""
                if isinstance(config, dict):
                    key = config.get('key', '')
                    value = config.get('value', '')
                elif hasattr(config, 'key'): 
                    key = config.key
                    value = getattr(config, 'value', '')
                
                self.add_edit_field_row(key, str(value) if value is not None else "")
        
        # 切换到编辑页 (index 1)
        self.right_panel_stack.setCurrentIndex(1)
    
    def cancel_card_edit(self):
        """取消编辑"""
        self.right_panel_stack.setCurrentIndex(0)
        
    def save_card_edit(self):
        """保存编辑"""
        name = self.edit_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入名片名称")
            return
            
        # 使用当前名片的分类（不修改分类）
        category = self.current_card.category if hasattr(self.current_card, 'category') and self.current_card.category else "默认分类"
        
        # 收集字段
        configs = []
        for row_widget in self.edit_field_rows:
            key, value = row_widget.get_data()
            if key:  # 只添加有字段名的
                configs.append({"key": key, "value": value})
        
        if not configs:
            QMessageBox.warning(self, "提示", "请至少添加一个字段")
            return
            
        # 保存到数据库
        try:
            self.db_manager.update_card(
                card_id=self.current_card.id,
                name=name,
                configs=configs,
                category=category
            )
            
            # 更新内存中的对象
            self.current_card.name = name
            self.current_card.configs = configs
            self.current_card.category = category
            
            # 刷新界面
            # 暂时屏蔽信号，防止 load_categories 和 setCurrentIndex 触发 load_cards_list
            self.category_combo.blockSignals(True)
            try:
                self.load_categories()
                
                # 确保选中正确的分类
                index = self.category_combo.findText(category)
                if index >= 0:
                    self.category_combo.setCurrentIndex(index)
                    self.category_label.setText(category)
            finally:
                self.category_combo.blockSignals(False)
                
            # 手动加载列表并选中当前名片
            self.load_cards_list(target_card_id=self.current_card.id)
            # self.show_card_info(self.current_card) # load_cards_list 会自动处理选中和显示
            
            # 切回详情页
            self.right_panel_stack.setCurrentIndex(0)
            
            # 简单提示（不弹窗）
            print(f"✅ 名片 '{name}' 更新成功")
            
        except Exception as e:
            QMessageBox.warning(self, "失败", f"保存失败：{str(e)}")

    def add_edit_field_row(self, key="", value=""):
        """添加编辑字段行"""
        row = EditFieldRow(key, value, self)
        self.edit_fields_layout.addWidget(row)
        self.edit_field_rows.append(row)
        
    def remove_edit_field_row(self, row):
        """删除编辑字段行"""
        if row in self.edit_field_rows:
            self.edit_field_rows.remove(row)
            row.deleteLater()

    def reimport_card(self):
        """重新导入/刷新名片数据（不切换名片，仅更新当前名片的数据）"""
        print("🔄 重新导入名片...")
        if not self.current_card:
            QMessageBox.warning(self, "提示", "请先选择名片")
            return
        
        # 获取当前标签页对应的链接
        current_index = self.tab_widget.currentIndex()
        if current_index <= 0:
            QMessageBox.warning(self, "提示", "请先进入某个链接页面")
            return
        
        real_index = current_index - 1
        if real_index >= len(self.selected_links):
            QMessageBox.warning(self, "提示", "当前链接无效")
            return
        
        current_link = self.selected_links[real_index]
        link_id = str(current_link.id)
        
        # 获取该链接下的所有 WebView 信息
        webview_infos = self.web_views_by_link.get(link_id, [])
        
        # 找到当前名片对应的 WebView 信息 (兼容单开和多开模式)
        target_info = None
        
        if self.fill_mode == "single":
            # 单开模式下，只有一个 WebView，且它当前就显示的是 self.current_card
            if webview_infos:
                target_info = webview_infos[0]
        else:
            # 多开模式下，根据名片ID查找
            for info in webview_infos:
                if info.get('card') and str(info['card'].id) == str(self.current_card.id):
                    target_info = info
                    break
        
        if target_info:
            if target_info.get('web_view'):
                # 确保使用最新的名片数据
                latest_card = self.current_card
                # 尝试从数据库刷新以防万一
                try:
                    db_card = self.db_manager.get_card_by_id(self.current_card.id)
                    if db_card:
                        # 处理可能的 reload 方法缺失
                        if hasattr(db_card, 'reload'):
                            db_card.reload()
                        latest_card = db_card
                        # 更新缓存中的 card，以便下次使用
                        target_info['card'] = latest_card
                        # 更新 WebView 的属性
                        target_info['web_view'].setProperty("card_data", latest_card)
                except Exception as e:
                    print(f"⚠️ 刷新名片失败: {e}")

                # 设置标记，告诉 WebView 加载完成后自动填充
                print(f"⚡️ 手动触发填充（重新导入）: {latest_card.name}")
                
                # 标记此 WebView 需要在稍后自动填充（如果此时正好在加载中）
                target_info['web_view'].setProperty("auto_fill_after_load", True)
                
                # 立即尝试填充
                self.execute_auto_fill_for_webview(target_info['web_view'], latest_card)
                return
            else:
                QMessageBox.warning(self, "提示", "页面尚未加载完成，请稍候")
                return
        
        QMessageBox.warning(self, "提示", "未找到该名片对应的表单")

    def create_card_list_item(self, card) -> QPushButton:
        """创建名片列表项 - 一比一还原设计图"""
        btn = QPushButton(card.name)
        btn.setMinimumHeight(56) # 加高，更像列表项
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setProperty("card_id", str(card.id))
        
        # 恢复图标显示
        btn.setIcon(Icons.get('fa5s.user-circle', COLORS['text_secondary']))
        btn.setIconSize(QSize(20, 20))
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background: white;
                color: {COLORS['text_primary']};
                border: 1px solid transparent;
                border-radius: 8px;
                text-align: left;
                padding-left: 16px;
                font-size: 15px;
                margin-bottom: 4px;
            }}
            QPushButton:hover {{
                background: {COLORS['surface_hover']};
            }}
            QPushButton:checked {{
                background: #E6F7FF;
                color: {COLORS['primary']};
                border: 1px solid {COLORS['primary']};
                font-weight: 600;
            }}
        """)
        btn.setCheckable(True) # 支持选中状态
        
        # 点击逻辑：处理选中状态互斥
        def on_click():
            # 取消其他按钮的选中状态
            for i in range(self.cards_list_layout.count()):
                item = self.cards_list_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if isinstance(widget, QPushButton) and widget != btn:
                        widget.setChecked(False)
                        widget.setIcon(Icons.get('fa5s.user-circle', COLORS['text_secondary']))

            btn.setChecked(True)
            # 选中时图标变色
            btn.setIcon(Icons.check_circle('primary'))
            
            # 单开模式下，点击切换WebView内容
            if self.fill_mode == "single" and self.current_card != card:
                self.switch_card_single_mode(card)
                
            self.show_card_info(card)
            
        btn.clicked.connect(on_click)
        return btn

    def switch_card_single_mode(self, new_card):
        """单开模式：切换名片"""
        print(f"🔄 单开模式切换名片: {self.current_card.name if self.current_card else 'None'} -> {new_card.name}")
        
        # 获取当前活动的链接Tab
        current_index = self.tab_widget.currentIndex()
        if current_index <= 0: # 首页
            return
            
        real_index = current_index - 1
        if real_index >= len(self.selected_links):
            return
            
        link = self.selected_links[real_index]
        link_id = str(link.id)
        
        # 获取该链接的WebView信息 (单开模式下只有一个)
        webview_infos = self.web_views_by_link.get(link_id, [])
        if not webview_infos:
            return
            
        info = webview_infos[0] # 只有一个
        
        # 1. 清理旧的缓存和Token (关键步骤)
        if info['web_view']:
            # 尝试清理 LocalStorage/SessionStorage
            info['web_view'].page().runJavaScript("localStorage.clear(); sessionStorage.clear();")
            
            # 清除Cookies
            profile = info['web_view'].page().profile()
            cookie_store = profile.cookieStore()
            cookie_store.deleteAllCookies()
            
            # 清除Http缓存
            profile.clearHttpCache()
            
            # 加载空白页，视觉上重置
            info['web_view'].load(QUrl("about:blank"))
            
            print("🧹 已清理WebView缓存、Storage和Cookies，并重置为空白页")

        # 2. 更新绑定的名片
        info['card'] = new_card
        
        if info['web_view']:
            info['web_view'].setProperty("card_data", new_card)
        
        # 3. 更新UI显示 (占位符标题)
        placeholder = info['placeholder']
        try:
            # 结构: placeholder -> layout -> header -> header_layout -> name_label (index 1)
            if placeholder.layout() and placeholder.layout().count() > 0:
                header_item = placeholder.layout().itemAt(0)
                if header_item and header_item.widget():
                    header = header_item.widget()
                    if header.layout() and header.layout().count() > 1:
                        name_label_item = header.layout().itemAt(1)
                        if name_label_item and name_label_item.widget():
                            name_label = name_label_item.widget()
                            if isinstance(name_label, QLabel):
                                name_label.setText(new_card.name)
        except Exception as e:
            print(f"⚠️ 更新占位符标题失败: {e}")

        # 4. 重新加载WebView (延迟执行，等待空白页生效及缓存清理彻底)
        if info['web_view']:
             def reload_target():
                print(f"🚀 重新加载链接: {link.url}")
                # 标记这是一个切换名片后的加载，需要自动填充
                info['web_view'].setProperty("auto_fill_on_switch", True)
                info['web_view'].load(QUrl(link.url))
                info['loaded'] = False
             
             # 延迟 300ms 再加载目标页面
             QTimer.singleShot(300, reload_target)
             
        # 5. 手动触发填充（补救措施）
        # 目标加载启动后，再过 2000ms 检查 (总共 2300ms 后)
        QTimer.singleShot(2300, lambda: self._check_and_fill_if_needed(info['web_view'], new_card))

    def _check_and_fill_if_needed(self, web_view, card):
        """检查页面是否需要补救填充"""
        if web_view.property("auto_fill_on_switch"):
             print(f"⚡️ [补救措施] 页面加载信号未触发，强制执行填充: {card.name}")
             web_view.setProperty("auto_fill_on_switch", False)
             self.execute_auto_fill_for_webview(web_view, card)

    def auto_start_loading_webviews(self):
        """窗口打开后初始化（不再自动开始加载，改为点击Tab加载）"""
        print(f"\n{'='*60}")
        print(f"🚀 窗口初始化完成 - 等待点击Tab加载")
        print(f"  链接数量: {len(self.selected_links)}")
        print(f"  名片数量: {len(self.selected_cards)}")
        print(f"{'='*60}\n")
        
        # 初始化自动填充追踪
        self.auto_fill_enabled = True  # 恢复为True，确保自动填充
        self.links_ready_for_fill = set()  # 记录准备好填充的链接
        
        # ⚡️ 优化：不再自动加载所有，只加载当前选中的Tab
        # 获取当前选中的Tab索引
        current_index = self.tab_widget.currentIndex()
        if current_index > 0:
            # 手动触发一次Tab切换事件来加载第一个页面
            self.on_tab_changed(current_index)
        else:
            print("  ⚠️ 当前停留在首页，等待用户点击Tab")
    
    def on_tab_changed(self, index: int):
        """标签页切换时的处理"""
        if index == 0:
            # 点击了首页，关闭窗口
            self.close()
            return

        # 实际内容的索引需要 -1（因为加了首页Tab）
        real_index = index - 1
        if real_index < 0 or real_index >= len(self.selected_links):
            return
        
        current_link = self.selected_links[real_index]
        print(f"\n📑 切换到标签页: {current_link.name}")
        
        link_id = str(current_link.id)
        
        # ⚡️ 强制刷新当前标签页的UI
        current_widget = self.tab_widget.currentWidget()
        if current_widget:
            current_widget.update()
            QApplication.processEvents()
            
        # 获取该链接的WebView信息
        webview_infos = self.web_views_by_link.get(link_id, [])
        
        # ⚡️ 懒加载检查：如果该链接尚未初始化加载队列，则开始加载
        if not hasattr(self, 'loading_queues') or link_id not in self.loading_queues:
             print(f"⚡️ 首次访问，开始加载链接 '{current_link.name}' 的WebView...")
             # 这会初始化队列并开始加载第一批
             self.load_webviews_only(webview_infos)
        else:
             # 如果已经初始化过，检查是否有挂起的加载任务（继续加载剩余的）
             # 或者只是单纯的切换显示（WebView已经创建）
             pass
        
    def refresh_webview(self, link_id: str, index: int):
        """刷新指定的WebView"""
        webview_infos = self.web_views_by_link.get(link_id, [])
        if index < len(webview_infos):
            info = webview_infos[index]
            if info['web_view']:
                print(f"⟳ 刷新 WebView: {info['card'].name}")
                
                # ⚡️ 修复：刷新时不自动填充
                info['web_view'].setProperty("is_auto_fill_active", False)
                info['web_view'].setProperty("auto_fill_after_load", False)
                info['web_view'].setProperty("auto_fill_after_switch", False)
                
                info['web_view'].reload()
                info['web_view'].setProperty("status", "loading")
            else:
                print(f"⚠️ WebView 尚未加载，无法刷新")
    
    def fill_single_webview(self, link_id: str, index: int):
        """填充单个WebView"""
        # 检查用户是否可以继续使用（过期/次数限制）
        if self.current_user:
            from core.auth import check_user_can_use
            can_use, message = check_user_can_use(self.current_user)
            if not can_use:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "使用受限", f"{message}\n\n请联系平台客服续费后继续使用。")
                return
        
        webview_infos = self.web_views_by_link.get(link_id, [])
        if index < len(webview_infos):
            info = webview_infos[index]
            if info['web_view']:
                print(f"⚡️ 手动触发填充: {info['card'].name}")
                self.execute_auto_fill_for_webview(info['web_view'], info['card'])
            else:
                QMessageBox.warning(self, "提示", "页面尚未加载完成，请稍候")

    def auto_fill_for_link(self, link_id: str):
        """为指定链接自动填充"""
        # 检查用户是否可以继续使用（过期/次数限制）
        if self.current_user:
            from core.auth import check_user_can_use
            can_use, message = check_user_can_use(self.current_user)
            if not can_use:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "使用受限", f"{message}\n\n请联系平台客服续费后继续使用。")
                return
        
        webview_infos = self.web_views_by_link.get(link_id, [])
        
        if not webview_infos:
            print(f"❌ 未找到链接 {link_id} 的WebView信息")
            return
        
        # 收集所有已加载的WebView
        loaded_webviews = []
        for info in webview_infos:
            if info['web_view'] and info['web_view'].property("status") == "loaded":
                loaded_webviews.append(info['web_view'])
        
        print(f"\n{'='*60}")
        print(f"🚀 开始填充链接 {link_id} 的 {len(loaded_webviews)} 个表单")
        print(f"{'='*60}\n")
        
        for index, web_view in enumerate(loaded_webviews):
            card_data = web_view.property("card_data")
            
            print(f"📝 填写 WebView #{index+1}: {card_data.name}")
            web_view.setProperty("status", "filling")
            # ⚡️ 关键修复：设置 is_auto_fill_active 标记
            # 这样登录后页面刷新时，on_webview_loaded 能够检测到并自动重填
            web_view.setProperty("is_auto_fill_active", True)
            self.execute_auto_fill_for_webview(web_view, card_data)
    
    def load_webviews_only(self, webview_infos):
        """批量加载WebView（不立即填充）"""
        if not webview_infos:
            print("⚠️ 没有 WebView 信息可供加载")
            return

        if not hasattr(self, 'loading_queues'):
            self.loading_queues = {}  # {link_id: queue}
            self.loaded_views = []
        
        try:
            link_id = str(webview_infos[0]['link'].id)
        except (IndexError, KeyError, AttributeError) as e:
            print(f"❌ 获取 link_id 失败: {e}")
            return
        
        # ⚡️ 优化：只将任务放入队列，不再这里直接创建WebView
        # 使用 list(webview_infos) 创建副本，避免引用问题
        self.loading_queues[link_id] = list(webview_infos)
        
        # 开始分批加载
        if not hasattr(self, 'current_batches'):
            self.current_batches = {}
        self.current_batches[link_id] = 0
        
        # 立即开始第一批加载
        BATCH_SIZE = 2
        self.load_next_batch_for_link(link_id, BATCH_SIZE)
        
        # ⚡️ 自动填充逻辑：如果是在单开模式下加载，且这是一个重新加载的操作
        if self.fill_mode == "single":
            # 检查是否需要设置 auto_fill_on_switch
            # 这里我们不能直接设置，因为 WebView 可能还没创建
            # 我们已经在 toggle_fill_mode 中处理了这种情况，或者依靠 on_batch_webview_loaded 来处理
            pass
    
    def create_webview_for_placeholder(self, info) -> QWebEngineView:
        """为占位符创建实际的WebView"""
        card = info['card']
        link = info['link']
        index = info['index']
        placeholder = info['placeholder']
        
        # 清空占位符内容（保留header，移除content）
        placeholder_layout = placeholder.layout()
        while placeholder_layout.count() > 1:  # 保留header
            child = placeholder_layout.takeAt(1)
            if child.widget():
                child.widget().deleteLater()
        
        # 创建WebView
        web_view = QWebEngineView()
        web_view.setMinimumHeight(450)
        
        # ⚡️ 确保WebView可以交互和实时渲染
        web_view.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        web_view.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # ⚡️ 禁用双缓冲优化，确保实时渲染
        web_view.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        web_view.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        web_view.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors, False)
        
        # 创建独立 Profile
        profile = QWebEngineProfile(f"profile_{index}_{id(card)}_{id(link)}", web_view)
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
        profile.setHttpAcceptLanguage("zh-CN,zh;q=0.9,en;q=0.8")
        
        user_agent = profile.httpUserAgent()
        if 'zh-CN' not in user_agent:
            profile.setHttpUserAgent(user_agent + " Language/zh-CN")
        
        class WebEnginePage(QWebEnginePage):
            def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
                pass
        
        web_view.setPage(WebEnginePage(profile, web_view))
        
        # 存储相关信息
        web_view.setProperty("card_data", card)
        web_view.setProperty("link_data", link)
        web_view.setProperty("status", "created")
        web_view.setProperty("index", index)
        web_view.setProperty("info", info)
        # ⚡️ 保存原始 URL，防止 data URL 覆盖导致无法识别表单类型
        web_view.setProperty("original_url", link.url)
        
        # 监听加载完成
        web_view.loadFinished.connect(lambda success: self.on_batch_webview_loaded(web_view, success))
        
        # 添加到占位符（确保WebView占满剩余空间）
        placeholder_layout.addWidget(web_view, 1)  # stretch factor = 1
        
        # ⚡️ 强制刷新UI，确保WebView立即显示
        web_view.show()
        placeholder.update()
        QApplication.processEvents()  # 处理挂起的事件，立即刷新UI
        
        return web_view
    
    def load_next_batch_for_link(self, link_id: str, batch_size: int):
        """为指定链接加载下一批WebView"""
        if not hasattr(self, 'loading_queues') or link_id not in self.loading_queues:
            return
        
        queue = self.loading_queues[link_id]
        if not queue:
            print(f"\n✅ 链接 {link_id} 的所有WebView已加载完成")
            return
        
        # 取出一批
        batch = queue[:batch_size]
        self.loading_queues[link_id] = queue[batch_size:]
        
        self.current_batches[link_id] += 1
        print(f"\n📦 链接 {link_id} - 加载批次 #{self.current_batches[link_id]}（{len(batch)} 个）")
        
        # 开始加载
        for info in batch:
            # ⚡️ 优化：在需要加载时才创建WebView对象
            if not info['web_view']:
                print(f"  🔨 延迟实例化 WebView: {info['card'].name}")
                web_view = self.create_webview_for_placeholder(info)
                info['web_view'] = web_view
                info['loaded'] = False
            
            web_view = info['web_view']
            link = info['link']
            card = info['card']
            
            print(f"  🌐 加载: {card.name} -> {link.url}")
            
            # 检测是否是报名工具链接
            if 'baominggongju.com' in link.url:
                print(f"    📱 报名工具链接，显示登录页面")
                QTimer.singleShot(100, lambda wv=web_view, u=link.url, c=card: self.init_baoming_tool_for_webview(wv, u, c))
            else:
                web_view.setUrl(QUrl(link.url))
            
            web_view.setProperty("status", "loading")
            
            # ⚡️ 强制刷新，确保加载立即可见
            web_view.show()
            web_view.update()
    
    def load_next_batch(self, batch_size):
        """加载下一批WebView（兼容旧方法）"""
        if not hasattr(self, 'loading_queue') or not self.loading_queue:
            print("\n✅ 所有WebView已创建")
            return
        
        # 取出一批
        batch = self.loading_queue[:batch_size]
        self.loading_queue = self.loading_queue[batch_size:]
        
        print(f"\n📦 加载批次 #{self.current_batch + 1}（{len(batch)} 个）")
        self.current_batch += 1
        
        # 开始加载
        for info in batch:
            web_view = info['web_view']
            link = info['link']
            card = info['card']
            
            print(f"  🌐 加载: {card.name} -> {link.url}")
            
            # 检测是否是报名工具链接
            if 'baominggongju.com' in link.url:
                print(f"    📱 报名工具链接，显示登录页面")
                QTimer.singleShot(100, lambda wv=web_view, u=link.url, c=card: self.init_baoming_tool_for_webview(wv, u, c))
            else:
                web_view.setUrl(QUrl(link.url))
            
            web_view.setProperty("status", "loading")
            
            # ⚡️ 强制刷新，确保加载立即可见
            web_view.show()
            web_view.update()
    
    def on_batch_webview_loaded(self, web_view: QWebEngineView, success: bool):
        """批量加载时的回调"""
        card_data = web_view.property("card_data")
        link_data = web_view.property("link_data")
        index = web_view.property("index")
        info = web_view.property("info")
        
        if not success:
            web_view.setProperty("status", "failed")
            print(f"❌ WebView #{index+1} ({card_data.name}) 加载失败")
            return
        
        web_view.setProperty("status", "loaded")
        if info:
            info['loaded'] = True
        self.loaded_views.append(web_view)
        print(f"✅ WebView #{index+1} ({card_data.name}) 加载完成")
        
        # ⚡️ 加载完成后强制刷新UI
        web_view.update()
        QApplication.processEvents()
        
        # ⚡️ 逻辑优化：如果是被手动禁用（如刷新）的自动填充，
        # 在页面加载完成2秒后，自动恢复自动填充能力（is_auto_fill_active -> True）
        # 这样下次如果页面发生跳转（如登录后），就能自动填充了
        if web_view.property("is_auto_fill_active") is False:
            print(f"⚡️ 检测到自动填充被临时禁用，将在2秒后恢复能力（但不执行填充）")
            QTimer.singleShot(2000, lambda: web_view.setProperty("is_auto_fill_active", True))

        # ⚡️ 智能重填逻辑：如果之前已经填充过（is_auto_fill_active=True），
        # 且页面重新加载了（可能是登录后跳转回来），则自动再次填充
        if web_view.property("is_auto_fill_active"):
            # ⚡️ 报名工具特殊处理：如果已经渲染了自定义表单页面，不要重复触发填充
            # 因为报名工具的 setHtml() 会触发 loadFinished，导致无限循环
            if web_view.property("baoming_page_rendered"):
                print(f"⚡️ 报名工具页面已渲染，跳过自动重填: {card_data.name}")
                return  # 跳过，不触发填充
            
            print(f"⚡️ 检测到页面刷新且填充模式已激活，准备自动重填: {card_data.name}")
            # 延迟2秒执行，给予页面充分的初始化时间（特别是登录后的重定向）
            QTimer.singleShot(2000, lambda: self.execute_auto_fill_for_webview(web_view, card_data))
            return  # 不再继续执行后续的首次加载逻辑
        
        # ⚡️ 模式切换后自动填充：检查 info 中的 auto_fill_after_switch 标记
        if info and info.get('auto_fill_after_switch'):
            print(f"⚡️ 模式切换后加载完成，准备自动填充: {card_data.name}")
            info['auto_fill_after_switch'] = False  # 清除标记，避免重复填充
            # 设置 is_auto_fill_active，这样后续刷新也能自动填充
            web_view.setProperty("is_auto_fill_active", True)
            # 延迟执行填充，确保页面完全就绪
            QTimer.singleShot(1500, lambda: self.execute_auto_fill_for_webview(web_view, card_data))
            # 注意：不 return，继续执行后续逻辑以便处理批次加载
        
        # 获取当前WebView所属的链接
        link_id = str(link_data.id)
        webview_infos = self.web_views_by_link.get(link_id, [])
        
        # 统计该链接的加载状态
        loading_count = sum(1 for info in webview_infos 
                          if info['web_view'] and info['web_view'].property("status") == "loading")
        
        if loading_count == 0:
            # 当前链接的当前批次加载完成
            BATCH_SIZE = 2
            if hasattr(self, 'loading_queues') and link_id in self.loading_queues and self.loading_queues[link_id]:
                # 继续加载该链接的下一批
                print(f"\n⏭️  链接 {link_id} 继续加载下一批（剩余 {len(self.loading_queues[link_id])} 个）")
                # 使用默认参数捕获link_id的当前值，避免闭包问题
                QTimer.singleShot(500, lambda lid=link_id: self.load_next_batch_for_link(lid, BATCH_SIZE))
            else:
                # 该链接的所有WebView加载完成
                loaded_count = sum(1 for info in webview_infos if info.get('loaded', False))
                print(f"\n🎉 链接 '{link_data.name}' 的所有WebView加载完成 ({loaded_count}/{len(webview_infos)})")
                
                # ⚡️ 自动填充模式：该链接加载完成后立即开始填充
                if hasattr(self, 'auto_fill_enabled') and self.auto_fill_enabled:
                    if link_id not in self.links_ready_for_fill:
                        self.links_ready_for_fill.add(link_id)
                        print(f"\n🚀 自动开始填充链接 '{link_data.name}' 的表单...")
                        # 使用默认参数捕获link_id的当前值，避免闭包问题
                        QTimer.singleShot(1000, lambda lid=link_id: self.auto_fill_for_link(lid))
    
    def on_webview_loaded(self, web_view: QWebEngineView, success: bool):
        """WebView加载完成"""
        card_data = web_view.property("card_data")
        link_data = web_view.property("link_data")
        index = web_view.property("index")
        
        if not success:
            web_view.setProperty("status", "failed")
            print(f"❌ WebView #{index+1} ({card_data.name}) 加载失败")
            return
        
        web_view.setProperty("status", "loaded")
        print(f"✅ WebView #{index+1} ({card_data.name}) 加载完成 - {link_data.name}")
        
        # ⚡️ 逻辑优化：如果是被手动禁用（如刷新）的自动填充，
        # 在页面加载完成2秒后，自动恢复自动填充能力（is_auto_fill_active -> True）
        # 这样下次如果页面发生跳转（如登录后），就能自动填充了
        if web_view.property("is_auto_fill_active") is False:
            print(f"⚡️ 检测到自动填充被临时禁用，将在2秒后恢复能力（但不执行填充）")
            QTimer.singleShot(2000, lambda: web_view.setProperty("is_auto_fill_active", True))

        # ⚡️ 智能重填逻辑：如果之前点击了"填充"，且页面重新加载了（可能是登录跳转回来），则自动再次填充
        if web_view.property("is_auto_fill_active"):
            # ⚡️ 报名工具特殊处理：如果已经渲染了自定义表单页面，不要重复触发填充
            # 因为报名工具的 setHtml() 会触发 loadFinished，导致无限循环
            if web_view.property("baoming_page_rendered"):
                print(f"⚡️ 报名工具页面已渲染，跳过自动重填: {card_data.name}")
                return  # 跳过，不触发填充
            
            print(f"⚡️ 检测到页面刷新且填充模式已激活，准备自动重填: {card_data.name}")
            # 延迟2秒执行，给予页面充分的初始化时间（特别是登录后的重定向）
            QTimer.singleShot(2000, lambda: self.execute_auto_fill_for_webview(web_view, card_data))
        
        # 检查是否是切换名片后的重新加载
        if web_view.property("auto_fill_on_switch"):
             print(f"⚡️ 切换名片后加载完成，准备自动填充: {card_data.name}")
             web_view.setProperty("auto_fill_on_switch", False) # 清除标记
             # 延迟执行填充，确保页面完全就绪
             QTimer.singleShot(1000, lambda: self.execute_auto_fill_for_webview(web_view, card_data))
        
        # 检查是否有自动填充标记（重新导入时使用）
        if web_view.property("auto_fill_after_load"):
            print(f"⚡️ 页面刷新完成，正在重新导入数据: {card_data.name}")
            web_view.setProperty("auto_fill_after_load", False)
            # 延迟执行填充，确保页面完全就绪
            QTimer.singleShot(1500, lambda: self.execute_auto_fill_for_webview(web_view, card_data))
        
        # 检查当前标签页的所有WebView是否都加载完成
        current_index = self.tab_widget.currentIndex()
        
        # 跳过首页 (index 0)
        if current_index <= 0:
            return

        real_index = current_index - 1
        if real_index < len(self.selected_links):
            current_link = self.selected_links[real_index]
            web_views = self.web_views_by_link.get(str(current_link.id), [])
            
            # 检查是否所有页面都加载完成
            all_loaded = all(
                wv.property("status") in ["loaded", "failed"]
                for wv in web_views
            )
            
            if all_loaded:
                loaded_count = sum(1 for wv in web_views if wv.property("status") == "loaded")
                print(f"\n✅ 当前标签页所有表单已加载完成 ({loaded_count}/{len(web_views)})\n")
    
    
    def execute_auto_fill_for_webview(self, web_view: QWebEngineView, card):
        """为单个WebView执行自动填写（参考 auto_fill_window.py）"""
        current_url = web_view.url().toString()
        
        # ⚡️ 优先使用原始 URL（防止 data: URL 干扰）
        original_url = web_view.property("original_url")
        if original_url and 'baominggongju.com' in original_url:
            current_url = original_url
            form_type = 'baominggongju'
            print(f"  🔧 [自动修正] 使用原始URL: {current_url}")
        else:
            form_type = self.detect_form_type(current_url)
        
        # ⚡️ 再次检查标记
        if form_type == 'unknown':
            filler = web_view.property("baoming_filler")
            target_type = web_view.property("target_form_type")
            
            if filler or target_type == 'baominggongju':
                form_type = 'baominggongju'
                print(f"  🔧 [自动修正] 检测到报名工具自定义页面，强制类型为 baominggongju")
        
        print(f"  🔍 检测到表单类型: {form_type}")
        
        # 准备填写数据
        if form_type == 'tencent_docs':
            # 腾讯文档需要字典格式
            fill_data = {}
            for config in card.configs:
                if isinstance(config, dict):
                    fill_data[config.get('key', '')] = config.get('value', '')
                else:
                    # 处理旧格式
                    fill_data[config.key] = config.value
            
            # 使用腾讯文档填写引擎
            js_code = self.tencent_docs_engine.generate_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟3秒后获取结果
            QTimer.singleShot(3000, lambda: self.get_fill_result(web_view, card, 'tencent_docs'))
            
        elif form_type == 'mikecrm':
            # 麦客CRM需要列表格式
            fill_data = []
            for config in card.configs:
                if isinstance(config, dict):
                    fill_data.append({
                        'key': config.get('key', ''),
                        'value': config.get('value', '')
                    })
                else:
                    # 处理旧格式
                    fill_data.append({
                        'key': config.key,
                        'value': config.value
                    })
            
            # 使用麦客CRM填写引擎
            js_code = self.auto_fill_engine.generate_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟3秒后获取结果
            QTimer.singleShot(3000, lambda: self.get_fill_result(web_view, card, 'mikecrm'))
        
        elif form_type == 'wjx':
            # 问卷星需要列表格式
            fill_data = []
            for config in card.configs:
                if isinstance(config, dict):
                    fill_data.append({
                        'key': config.get('key', ''),
                        'value': config.get('value', '')
                    })
                else:
                    fill_data.append({
                        'key': config.key,
                        'value': config.value
                    })
            
            # 使用问卷星专用填充脚本
            js_code = self.generate_wjx_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟3秒后获取结果
            QTimer.singleShot(3000, lambda: self.get_fill_result(web_view, card, 'wjx'))
        
        elif form_type == 'jinshuju':
            # 金数据需要列表格式
            fill_data = []
            for config in card.configs:
                if isinstance(config, dict):
                    fill_data.append({
                        'key': config.get('key', ''),
                        'value': config.get('value', '')
                    })
                else:
                    fill_data.append({
                        'key': config.key,
                        'value': config.value
                    })
            
            # 使用金数据专用填充脚本
            js_code = self.generate_jinshuju_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟3秒后获取结果
            QTimer.singleShot(3000, lambda: self.get_fill_result(web_view, card, 'jinshuju'))
        
        elif form_type == 'shimo':
            # 石墨文档需要列表格式
            fill_data = []
            for config in card.configs:
                if isinstance(config, dict):
                    fill_data.append({
                        'key': config.get('key', ''),
                        'value': config.get('value', '')
                    })
                else:
                    fill_data.append({
                        'key': config.key,
                        'value': config.value
                    })
            
            # 使用石墨文档专用填充脚本
            js_code = self.generate_shimo_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟3秒后获取结果
            QTimer.singleShot(3000, lambda: self.get_fill_result(web_view, card, 'shimo'))
        
        elif form_type == 'credamo':
            # 见数平台需要列表格式
            fill_data = []
            for config in card.configs:
                if isinstance(config, dict):
                    fill_data.append({
                        'key': config.get('key', ''),
                        'value': config.get('value', '')
                    })
                else:
                    fill_data.append({
                        'key': config.key,
                        'value': config.value
                    })
            
            # 使用见数专用填充脚本
            js_code = self.generate_credamo_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟3秒后获取结果
            QTimer.singleShot(3000, lambda: self.get_fill_result(web_view, card, 'credamo'))
        
        elif form_type == 'wenjuan':
            # 问卷网需要列表格式
            fill_data = []
            for config in card.configs:
                if isinstance(config, dict):
                    fill_data.append({
                        'key': config.get('key', ''),
                        'value': config.get('value', '')
                    })
                else:
                    fill_data.append({
                        'key': config.key,
                        'value': config.value
                    })
            
            # 使用问卷网专用填充脚本
            js_code = self.generate_wenjuan_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟3秒后获取结果
            QTimer.singleShot(3000, lambda: self.get_fill_result(web_view, card, 'wenjuan'))
        
        elif form_type == 'fanqier':
            # 番茄表单需要列表格式
            fill_data = []
            for config in card.configs:
                if isinstance(config, dict):
                    fill_data.append({
                        'key': config.get('key', ''),
                        'value': config.get('value', '')
                    })
                else:
                    fill_data.append({
                        'key': config.key,
                        'value': config.value
                    })
            
            # 使用番茄表单专用填充脚本
            js_code = self.generate_fanqier_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟3秒后获取结果
            QTimer.singleShot(3000, lambda: self.get_fill_result(web_view, card, 'fanqier'))
        
        elif form_type == 'feishu':
            # 飞书问卷需要列表格式
            fill_data = []
            for config in card.configs:
                if isinstance(config, dict):
                    fill_data.append({
                        'key': config.get('key', ''),
                        'value': config.get('value', '')
                    })
                else:
                    fill_data.append({
                        'key': config.key,
                        'value': config.value
                    })
            
            # 使用飞书问卷专用填充脚本
            js_code = self.generate_feishu_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟3秒后获取结果
            QTimer.singleShot(3000, lambda: self.get_fill_result(web_view, card, 'feishu'))
        
        elif form_type == 'kdocs':
            # WPS表单需要列表格式
            fill_data = []
            for config in card.configs:
                if isinstance(config, dict):
                    fill_data.append({
                        'key': config.get('key', ''),
                        'value': config.get('value', '')
                    })
                else:
                    fill_data.append({
                        'key': config.key,
                        'value': config.value
                    })
            
            # 使用WPS表单专用填充脚本
            js_code = self.generate_kdocs_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟3秒后获取结果
            QTimer.singleShot(3000, lambda: self.get_fill_result(web_view, card, 'kdocs'))
        
        elif form_type == 'tencent_wj':
            # 腾讯问卷需要列表格式
            fill_data = []
            for config in card.configs:
                if isinstance(config, dict):
                    fill_data.append({
                        'key': config.get('key', ''),
                        'value': config.get('value', '')
                    })
                else:
                    fill_data.append({
                        'key': config.key,
                        'value': config.value
                    })
            
            # 使用腾讯问卷专用填充脚本
            js_code = self.generate_tencent_wj_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟3秒后获取结果
            QTimer.singleShot(3000, lambda: self.get_fill_result(web_view, card, 'tencent_wj'))
        
        elif form_type == 'baominggongju':
            # 报名工具需要特殊处理
            print(f"  📱 报名工具处理...")
            
            # 准备名片配置数据
            card_config = []
            for config in card.configs:
                if isinstance(config, dict):
                    card_config.append({
                        'name': config.get('key', ''),
                        'value': config.get('value', '')
                    })
                else:
                    card_config.append({
                        'name': config.key,
                        'value': config.value
                    })
            
            # 检查是否已经有登录状态的 filler
            existing_filler = web_view.property("baoming_filler")
            if existing_filler and existing_filler.api.access_token:
                print(f"  ✅ 检测到已登录状态，直接更新表单数据")
                
                # 停止旧的提交检查定时器
                submit_timer = web_view.property("submit_timer")
                if submit_timer:
                    submit_timer.stop()
                    web_view.setProperty("submit_timer", None)
                
                # 更新存储的配置和Card对象
                web_view.setProperty("baoming_card_config", card_config)
                web_view.setProperty("baoming_card", card)
                
                # 重新匹配并显示表单
                try:
                    filled_data = existing_filler.match_and_fill(card_config)
                    self.show_baoming_form_page(web_view, existing_filler, filled_data, card)
                    print(f"  ✅ 已重新渲染表单")
                except Exception as e:
                    print(f"  ⚠️ 重新渲染失败: {e}")
                    # 如果失败，回退到重新初始化
                    self.setup_baoming_tool_in_webview(current_url, card_config, web_view, card)
            else:
                # 未登录或首次加载，执行完整初始化
                print(f"  🔄 未登录，开始初始化流程")
                self.setup_baoming_tool_in_webview(current_url, card_config, web_view, card)
        else:
            print(f"  ⚠️  未知表单类型: {current_url}")
            web_view.setProperty("status", "unknown_type")
    
    def handle_refresh_click(self, web_view: QWebEngineView, link, card):
        """处理刷新按钮点击"""
        # ⚡️ 修复：刷新时不自动填充
        # 设置 is_auto_fill_active 标记为 False
        # 这样手动点击刷新时，不会触发自动填充逻辑
        web_view.setProperty("is_auto_fill_active", False)
        print(f"  🔄 手动刷新页面，关闭自动填充标记 is_auto_fill_active=False")
        
        # 还要清除其他可能触发填充的标记
        web_view.setProperty("auto_fill_after_load", False)
        web_view.setProperty("auto_fill_after_switch", False)
        
        # 检测是否是报名工具
        if 'baominggongju.com' in link.url:
            print(f"  🔄 [报名工具] 刷新：重新获取二维码，URL: {link.url}")
            
            # 1. 停止所有定时器并断开连接
            login_timer = web_view.property("login_timer")
            if login_timer:
                login_timer.stop()
                try:
                    login_timer.timeout.disconnect()
                except:
                    pass
                login_timer.deleteLater()
                web_view.setProperty("login_timer", None)
                
            submit_timer = web_view.property("submit_timer")
            if submit_timer:
                submit_timer.stop()
                try:
                    submit_timer.timeout.disconnect()
                except:
                    pass
                submit_timer.deleteLater()
                web_view.setProperty("submit_timer", None)
            
            # 2. 清空旧的 filler 和数据
            web_view.setProperty("baoming_filler", None)
            web_view.setProperty("baoming_card_config", None)
            web_view.setProperty("baoming_filled_data", None)
            # ⚡️ 清除页面渲染标记，允许重新初始化
            web_view.setProperty("baoming_page_rendered", False)
            
            # 3. 显示加载中提示
            loading_html = """
            <!DOCTYPE html>
            <html>
            <body style="margin:0;padding:0;background:#f0f2f5;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;">
                <div style="text-align:center;color:#666;">
                    <div style="font-size:32px;margin-bottom:16px;">🔄</div>
                    <div>正在刷新二维码...</div>
                </div>
            </body>
            </html>
            """
            web_view.setHtml(loading_html)
            
            # 4. 延迟重新初始化（确保资源释放）
            # ⚡️ 使用默认参数捕获当前值，避免闭包问题
            print(f"  ⏳ [报名工具] 800ms后重新初始化...")
            QTimer.singleShot(800, lambda wv=web_view, u=link.url, c=card: self.init_baoming_tool_for_webview(wv, u, c))
        else:
            # 普通页面直接刷新
            web_view.reload()
    
    def handle_fill_click(self, web_view: QWebEngineView, link, card):
        """处理填充按钮点击"""
        # 检查用户是否可以继续使用（过期/次数限制）
        if self.current_user:
            from core.auth import check_user_can_use
            can_use, message = check_user_can_use(self.current_user)
            if not can_use:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "使用受限", f"{message}\n\n请联系平台客服续费后继续使用。")
                return
        
        # ⚡️ 启用"智能重填模式"：当页面后续发生刷新（如登录后跳转）时，会自动再次尝试填充
        web_view.setProperty("is_auto_fill_active", True)
        
        # ⚡️ 关键修复：重新从数据库获取最新的名片数据
        try:
            if hasattr(card, 'id'):
                latest_card = self.db_manager.get_card_by_id(card.id)
                if latest_card:
                    latest_card.reload() # 强制刷新数据
                    card = latest_card
                    print(f"  🔄 [填充] 已获取最新名片数据: {card.name}")
                    # 打印第一个配置项的值用于调试
                    if card.configs:
                        print(f"  🔍 配置示例: {card.configs[0].key}={card.configs[0].value}")
        except Exception as e:
            print(f"  ⚠️ 获取最新名片失败: {e}")

        # 统一使用 execute_auto_fill_for_webview，它现在已经足够健壮
        # 能够处理报名工具的 data URL、登录状态保持等情况
        self.execute_auto_fill_for_webview(web_view, card)
    
    def init_baoming_tool_for_webview(self, web_view: QWebEngineView, url: str, card):
        """初始化报名工具（从WebView创建时调用）"""
        # ⚡️ 关键修复：重新从数据库获取最新的名片数据
        try:
            if hasattr(card, 'id'):
                latest_card = self.db_manager.get_card_by_id(card.id)
                if latest_card:
                    card = latest_card
                    print(f"  🔄 [初始化] 已获取最新名片数据: {card.name}")
        except Exception as e:
            print(f"  ⚠️ [初始化] 获取最新名片失败: {e}")

        # 准备名片配置数据
        card_config = []
        for config in card.configs:
            if isinstance(config, dict):
                card_config.append({
                    'name': config.get('key', ''),
                    'value': config.get('value', '')
                })
            else:
                card_config.append({
                    'name': config.key,
                    'value': config.value
                })
        
        # 调试打印
        print(f"  📋 [初始化] 名片配置 ({len(card_config)}): {[c['name'] + '=' + c['value'] for c in card_config]}")
        
        # 调用设置方法
        self.setup_baoming_tool_in_webview(url, card_config, web_view, card)
    
    def setup_baoming_tool_in_webview(self, url: str, card_config: list, web_view: QWebEngineView, card):
        """在WebView中设置报名工具界面"""
        from core.baoming_tool_filler import BaomingToolFiller
        
        # 创建填充器实例并绑定到 web_view
        filler = BaomingToolFiller()
        web_view.setProperty("baoming_filler", filler)
        web_view.setProperty("baoming_card_config", card_config)
        web_view.setProperty("baoming_card", card)
        # ⚡️ 标记目标表单类型，以便在 data URL 时能正确识别
        web_view.setProperty("target_form_type", "baominggongju")
        # ⚡️ 清除页面渲染标记，开始新的初始化流程
        web_view.setProperty("baoming_page_rendered", False)
        
        # 初始化
        print(f"  🔧 [报名工具] 开始初始化: {url}")
        success, msg = filler.initialize(url)
        if not success:
            print(f"  ❌ [报名工具] 初始化失败: {msg}")
            self.show_baoming_error_page(web_view, msg)
            return
        print(f"  ✅ [报名工具] 初始化成功")
        
        # 获取二维码
        print(f"  🔧 [报名工具] 获取二维码...")
        success, qr_data, code = filler.get_qr_code()
        if not success:
            print(f"  ❌ [报名工具] 获取二维码失败: {qr_data}")
            self.show_baoming_error_page(web_view, qr_data)
            return
        print(f"  ✅ [报名工具] 二维码获取成功")
        
        # 显示登录页面
        self.show_baoming_login_page(web_view, qr_data)
        print(f"  📱 [报名工具] 登录页面已显示，开始轮询...")
        
        # 开始轮询登录状态
        self.start_baoming_login_polling(web_view, filler, card_config, card)
    
    def show_baoming_error_page(self, web_view: QWebEngineView, error_msg: str):
        """显示报名工具错误页面（新设计）"""
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    background: #f0f2f5;
                    color: #333;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    padding: 20px;
                }}
                .error-container {{
                    text-align: center;
                    padding: 40px 30px;
                    background: #fff;
                    border-radius: 16px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.08);
                    max-width: 400px;
                    width: 100%;
                }}
                .error-icon {{ 
                    font-size: 48px; 
                    margin-bottom: 24px;
                    display: inline-block;
                    background: #fff1f0;
                    width: 80px;
                    height: 80px;
                    line-height: 80px;
                    border-radius: 50%;
                }}
                .error-title {{
                    font-size: 20px;
                    font-weight: 700;
                    color: #1a1a1a;
                    margin-bottom: 12px;
                }}
                .error-msg {{ 
                    color: #666; 
                    font-size: 15px;
                    line-height: 1.5;
                }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <div class="error-icon">❌</div>
                <div class="error-title">操作失败</div>
                <div class="error-msg">{error_msg}</div>
            </div>
        </body>
        </html>
        '''
        # ⚡️ 标记报名工具页面已渲染，防止无限刷新
        web_view.setProperty("baoming_page_rendered", True)
        web_view.setHtml(html)
    
    def show_baoming_login_page(self, web_view: QWebEngineView, qr_data: str):
        """显示报名工具登录页面（新设计）"""
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    background: #f0f2f5;
                    color: #333;
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                }}
                .container {{
                    text-align: center;
                    background: #fff;
                    border-radius: 16px;
                    padding: 40px 30px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.08);
                    max-width: 400px;
                    width: 100%;
                }}
                .title {{
                    font-size: 24px;
                    font-weight: 700;
                    margin-bottom: 8px;
                    color: #1a1a1a;
                }}
                .subtitle {{
                    color: #666;
                    margin-bottom: 32px;
                    font-size: 14px;
                }}
                .qr-container {{
                    background: #fff;
                    padding: 10px;
                    border-radius: 12px;
                    border: 1px solid #eee;
                    display: inline-block;
                    margin-bottom: 16px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                }}
                .qr-container img {{
                    width: 200px;
                    height: 200px;
                    display: block;
                    border-radius: 4px;
                }}
                .refresh-btn {{
                    background: #fff;
                    border: 1px solid #ddd;
                    color: #666;
                    padding: 8px 20px;
                    border-radius: 20px;
                    font-size: 13px;
                    cursor: pointer;
                    margin-bottom: 16px;
                    transition: all 0.2s;
                }}
                .refresh-btn:hover {{
                    background: #f5f5f5;
                    border-color: #1890ff;
                    color: #1890ff;
                }}
                .refresh-btn:disabled {{
                    opacity: 0.6;
                    cursor: not-allowed;
                }}
                .status {{
                    font-size: 14px;
                    padding: 10px 20px;
                    border-radius: 20px;
                    display: inline-block;
                    background: #f5f5f5;
                    color: #666;
                    font-weight: 500;
                }}
                .status.success {{
                    background: #e6fffa;
                    color: #52c41a;
                }}
                .status.error {{
                    background: #fff1f0;
                    color: #f5222d;
                }}
                .status.waiting {{
                    background: #e6f7ff;
                    color: #1890ff;
                }}
                @keyframes pulse {{
                    0%, 100% {{ opacity: 1; }}
                    50% {{ opacity: 0.6; }}
                }}
                .loading {{ animation: pulse 1.5s infinite; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="title">📱 扫码登录</div>
                <div class="subtitle">请使用微信扫描下方二维码登录报名工具</div>
                <div class="qr-container">
                    <img id="qrcode" src="{qr_data}" alt="登录二维码">
                </div>
                <div>
                    <button class="refresh-btn" id="refreshBtn" onclick="refreshQrCode()">🔄 刷新二维码</button>
                </div>
                <div class="status waiting loading" id="status">等待扫码...</div>
            </div>
            <script>
                window.__refreshQrCode__ = false;
                
                function refreshQrCode() {{
                    var btn = document.getElementById('refreshBtn');
                    var status = document.getElementById('status');
                    btn.disabled = true;
                    btn.textContent = '正在刷新...';
                    status.textContent = '正在获取新二维码...';
                    status.className = 'status';
                    window.__refreshQrCode__ = true;
                }}
                
                function updateQrCode(newQrData) {{
                    var img = document.getElementById('qrcode');
                    var btn = document.getElementById('refreshBtn');
                    var status = document.getElementById('status');
                    img.src = newQrData;
                    btn.disabled = false;
                    btn.textContent = '🔄 刷新二维码';
                    status.textContent = '等待扫码...';
                    status.className = 'status waiting loading';
                    window.__refreshQrCode__ = false;
                }}
                
                function showRefreshError(msg) {{
                    var btn = document.getElementById('refreshBtn');
                    var status = document.getElementById('status');
                    btn.disabled = false;
                    btn.textContent = '🔄 刷新二维码';
                    status.textContent = '❌ ' + msg;
                    status.className = 'status error';
                    window.__refreshQrCode__ = false;
                }}
            </script>
        </body>
        </html>
        '''
        # ⚡️ 标记报名工具页面已渲染，防止无限刷新
        web_view.setProperty("baoming_page_rendered", True)
        web_view.setHtml(html)
    
    def start_baoming_login_polling(self, web_view: QWebEngineView, filler, card_config: list, card):
        """开始轮询报名工具登录状态"""
        # 创建定时器
        timer = QTimer(self)
        timer.setProperty("web_view", web_view)
        timer.setProperty("filler", filler)
        timer.setProperty("card_config", card_config)
        timer.setProperty("card", card)
        timer.setProperty("poll_count", 0)
        
        def check_login():
            poll_count = timer.property("poll_count") or 0
            timer.setProperty("poll_count", poll_count + 1)
            
            # 先检查是否需要刷新二维码
            def handle_refresh_check(need_refresh):
                if need_refresh:
                    print(f"  🔄 [报名工具] 检测到刷新二维码请求")
                    # 重置轮询计数
                    timer.setProperty("poll_count", 0)
                    # 调用API获取新二维码
                    self.refresh_baoming_qrcode(web_view, filler)
                else:
                    # 继续正常的登录检查
                    do_login_check()
            
            web_view.page().runJavaScript("window.__refreshQrCode__ === true", handle_refresh_check)
        
        def do_login_check():
            poll_count = timer.property("poll_count") or 0
            
            # 最多轮询120次（4分钟）
            if poll_count >= 120:
                timer.stop()
                web_view.page().runJavaScript(
                    "document.getElementById('status').textContent = '登录超时，请点击刷新二维码';"
                    "document.getElementById('status').className = 'status error';"
                )
                return
            
            status, msg, user_info = filler.check_login()
            
            if status == 0:
                # 登录成功
                timer.stop()
                uname = user_info.get('uname', '用户') if user_info else '用户'
                print(f"  ✅ [报名工具] 登录成功: {uname}")
                web_view.page().runJavaScript(
                    f"document.getElementById('status').textContent = '✅ 登录成功: {uname}';"
                    "document.getElementById('status').className = 'status success';"
                )
                # 延迟加载表单
                print(f"  ⏳ [报名工具] 1秒后加载表单...")
                # ⚡️ 使用默认参数捕获当前值，避免闭包问题
                QTimer.singleShot(1000, lambda wv=web_view, f=filler, cc=card_config, c=card: self.load_baoming_form(wv, f, cc, c))
            elif status == -1:
                # 等待中（不打印，避免日志过多）
                pass
            else:
                # 失败（可能是二维码过期等）
                print(f"  ⚠️ [报名工具] 登录状态: {msg}")
                web_view.page().runJavaScript(
                    f"document.getElementById('status').textContent = '{msg}，请刷新二维码';"
                    "document.getElementById('status').className = 'status error';"
                )
        
        timer.timeout.connect(check_login)
        timer.start(2000)  # 每2秒检查一次
        
        # 保存定时器引用
        web_view.setProperty("login_timer", timer)
    
    def refresh_baoming_qrcode(self, web_view: QWebEngineView, filler):
        """刷新报名工具二维码"""
        print(f"  🔄 [报名工具] 开始刷新二维码...")
        
        try:
            # 调用API获取新二维码
            success, qr_data, code = filler.get_qr_code()
            
            if success:
                print(f"  ✅ [报名工具] 新二维码获取成功")
                # 更新页面上的二维码
                escaped_qr = qr_data.replace("'", "\\'")
                web_view.page().runJavaScript(f"updateQrCode('{escaped_qr}');")
            else:
                print(f"  ❌ [报名工具] 获取二维码失败: {qr_data}")
                escaped_msg = qr_data.replace("'", "\\'")
                web_view.page().runJavaScript(f"showRefreshError('{escaped_msg}');")
        except Exception as e:
            print(f"  ❌ [报名工具] 刷新二维码异常: {e}")
            web_view.page().runJavaScript(f"showRefreshError('刷新失败，请重试');")

    
    def load_baoming_form(self, web_view: QWebEngineView, filler, card_config: list, card):
        """加载报名工具表单"""
        print(f"  📋 [报名工具] 开始加载表单...")
        
        # 获取表单数据
        success, msg = filler.load_form()
        if not success:
            print(f"  ❌ [报名工具] 加载表单失败: {msg}")
            self.show_baoming_error_page(web_view, msg)
            return
        
        print(f"  ✅ [报名工具] 表单加载成功，开始匹配填充...")
        # 自动匹配填充
        filled_data = filler.match_and_fill(card_config)
        
        # 生成表单HTML
        self.show_baoming_form_page(web_view, filler, filled_data, card)
    
    def show_baoming_form_page(self, web_view: QWebEngineView, filler, filled_data: list, card):
        """显示报名工具表单页面（新设计）"""
        import json
        
        # 生成表单字段HTML
        fields_html = ''
        for i, field in enumerate(filled_data):
            field_name = field.get('field_name', '')
            field_key = field.get('field_key', '')
            field_value = field.get('field_value', '')
            
            # 检查是否已填充
            is_filled = bool(field_value)
            status_icon = '✅' if is_filled else '⚠️'
            input_class = 'filled' if is_filled else ''
            
            fields_html += f'''
            <div class="field-group">
                <div class="field-header">
                    <label>{field_name}</label>
                    <span class="field-status">{status_icon}</span>
                </div>
                <input type="text" 
                       class="{input_class}"
                       id="field_{i}" 
                       data-key="{field_key}" 
                       data-name="{field_name}"
                       value="{field_value}" 
                       placeholder="请输入{field_name}">
            </div>
            '''
        
        # 计算填充数量
        filled_count = sum(1 for f in filled_data if f.get('field_value'))
        total_count = len(filled_data)
        
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    background: #f0f2f5;
                    color: #333;
                    min-height: 100vh;
                    padding: 20px;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 24px;
                    background: #fff;
                    padding: 20px;
                    border-radius: 16px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                }}
                .title {{
                    font-size: 20px;
                    font-weight: 700;
                    color: #1a1a1a;
                    margin-bottom: 8px;
                }}
                .subtitle {{
                    color: #666;
                    font-size: 14px;
                    display: inline-block;
                    background: #f5f5f5;
                    padding: 4px 12px;
                    border-radius: 12px;
                }}
                .form-container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background: #fff;
                    border-radius: 16px;
                    padding: 30px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                }}
                .field-group {{
                    margin-bottom: 20px;
                }}
                .field-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 8px;
                }}
                .field-header label {{
                    font-size: 14px;
                    font-weight: 600;
                    color: #444;
                }}
                .field-status {{
                    font-size: 12px;
                }}
                input {{
                    width: 100%;
                    padding: 12px 16px;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    background: #fff;
                    color: #333;
                    font-size: 14px;
                    outline: none;
                    transition: all 0.2s;
                }}
                input:focus {{
                    border-color: #1890ff;
                    box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.1);
                }}
                input.filled {{
                    background: #f6ffed;
                    border-color: #b7eb8f;
                }}
                input::placeholder {{
                    color: #bfbfbf;
                }}
                .submit-btn {{
                    width: 100%;
                    padding: 14px;
                    background: linear-gradient(135deg, #1890ff, #096dd9);
                    color: #fff;
                    border: none;
                    border-radius: 10px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    margin-top: 24px;
                    transition: all 0.2s;
                    box-shadow: 0 4px 12px rgba(24, 144, 255, 0.3);
                }}
                .submit-btn:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 6px 16px rgba(24, 144, 255, 0.4);
                }}
                .submit-btn:disabled {{
                    background: #d9d9d9;
                    cursor: not-allowed;
                    transform: none;
                    box-shadow: none;
                }}
                .result {{
                    text-align: center;
                    margin-top: 16px;
                    font-size: 14px;
                    padding: 12px;
                    border-radius: 8px;
                    display: none;
                    font-weight: 500;
                }}
                .result.success {{
                    background: #f6ffed;
                    color: #52c41a;
                    border: 1px solid #b7eb8f;
                }}
                .result.error {{
                    background: #fff1f0;
                    color: #f5222d;
                    border: 1px solid #ffa39e;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="title">📋 报名工具表单</div>
                <div class="subtitle">✅ 已自动填充 {filled_count}/{total_count} 个字段</div>
            </div>
            <div class="form-container">
                {fields_html}
                <button class="submit-btn" onclick="submitForm()">📤 立即提交表单</button>
                <div class="result" id="result"></div>
            </div>
            
            <script>
                function submitForm() {{
                    var btn = document.querySelector('.submit-btn');
                    btn.disabled = true;
                    btn.textContent = '正在提交...';
                    
                    var fields = document.querySelectorAll('input');
                    var data = [];
                    fields.forEach(function(input) {{
                        var key = input.getAttribute('data-key');
                        // 如果 field_key 是纯数字，转回整数类型（API 需要保持原始类型）
                        if (/^\d+$/.test(key)) {{
                            key = parseInt(key, 10);
                        }}
                        data.push({{
                            field_name: input.getAttribute('data-name'),
                            field_key: key,
                            field_value: input.value,
                            ignore: 0
                        }});
                    }});
                    
                    window.__submitData__ = data;
                    window.__submitReady__ = true;
                }}
                
                function showResult(success, message) {{
                    var result = document.getElementById('result');
                    var btn = document.querySelector('.submit-btn');
                    result.textContent = message;
                    result.className = 'result ' + (success ? 'success' : 'error');
                    result.style.display = 'block';
                    btn.disabled = false;
                    btn.textContent = '📤 立即提交表单';
                }}
            </script>
        </body>
        </html>
        '''
        # ⚡️ 标记报名工具页面已渲染，防止无限刷新
        web_view.setProperty("baoming_page_rendered", True)
        web_view.setHtml(html)
        
        # 保存数据用于提交
        web_view.setProperty("baoming_filler", filler)
        web_view.setProperty("baoming_filled_data", filled_data)
        
        # 开始检查提交
        self.start_baoming_submit_check(web_view, filler, card)
    
    def start_baoming_submit_check(self, web_view: QWebEngineView, filler, card):
        """开始检查报名工具提交"""
        timer = QTimer(self)
        
        def check_submit():
            web_view.page().runJavaScript(
                "window.__submitReady__ === true",
                lambda ready: self.handle_baoming_submit(web_view, filler, card, timer) if ready else None
            )
        
        timer.timeout.connect(check_submit)
        timer.start(500)  # 每500ms检查一次
        
        web_view.setProperty("submit_timer", timer)
    
    def handle_baoming_submit(self, web_view: QWebEngineView, filler, card, timer):
        """处理报名工具提交"""
        # 停止检查
        timer.stop()
        
        # 重置标志
        web_view.page().runJavaScript("window.__submitReady__ = false;")
        
        # 获取提交数据
        def do_submit(data):
            if not data:
                web_view.page().runJavaScript("showResult(false, '获取表单数据失败');")
                self.start_baoming_submit_check(web_view, filler, card)
                return
            
            # 提交
            success, msg = filler.submit(data)
            
            if success:
                web_view.page().runJavaScript(f"showResult(true, '✅ 提交成功！');")
                print(f"  ✅ 报名工具提交成功")
            else:
                web_view.page().runJavaScript(f"showResult(false, '❌ {msg}');")
                print(f"  ❌ 报名工具提交失败: {msg}")
            
            # 继续检查下一次提交
            self.start_baoming_submit_check(web_view, filler, card)
        
        web_view.page().runJavaScript("window.__submitData__", do_submit)
    
    def detect_form_type(self, url: str) -> str:
        """检测表单类型"""
        if 'docs.qq.com/form' in url:
            return 'tencent_docs'
        elif 'mikecrm.com' in url:
            return 'mikecrm'
        elif 'wjx.cn' in url:
            return 'wjx'
        elif 'jsj.top' in url or 'jinshuju.net' in url:
            return 'jinshuju'
        elif 'shimo.im' in url:
            return 'shimo'
        elif 'baominggongju.com' in url or 'p.baominggongju.com' in url:
            return 'baominggongju'
        elif 'credamo.com' in url:
            return 'credamo'
        elif 'wenjuan.com' in url:
            return 'wenjuan'
        elif 'fanqier.cn' in url:
            return 'fanqier'
        elif 'feishu.cn' in url:
            return 'feishu'
        elif 'kdocs.cn' in url:
            return 'kdocs'
        elif 'wj.qq.com' in url:
            return 'tencent_wj'
        else:
            return 'unknown'
    
    def generate_wjx_fill_script(self, fill_data: list) -> str:
        """生成问卷星专用的填充脚本 - 使用评分匹配系统"""
        import json
        fill_data_json = json.dumps(fill_data, ensure_ascii=False)
        
        js_code = f"""
(function() {{
    console.log('🚀 开始填写问卷星表单...');
    
    const fillData = {fill_data_json};
    let fillCount = 0;
    const results = [];
    
    // 等待输入框加载完成
    function waitForInputs(maxAttempts = 15, interval = 400) {{
        return new Promise((resolve) => {{
            let attempts = 0;
            const checkInputs = setInterval(() => {{
                const inputs = document.querySelectorAll('input, textarea');
                attempts++;
                console.log(`🔍 尝试 ${{attempts}}/${{maxAttempts}}: 找到 ${{inputs.length}} 个输入框`);
                
                if (inputs.length > 0 || attempts >= maxAttempts) {{
                    clearInterval(checkInputs);
                    resolve(inputs.length > 0);
                }}
            }}, interval);
        }});
    }}
    
    // 获取所有可见的输入框
    function getAllInputs() {{
        const inputs = [];
        document.querySelectorAll('input, textarea').forEach(input => {{
            const style = window.getComputedStyle(input);
            if (style.display !== 'none' && style.visibility !== 'hidden') {{
                inputs.push(input);
            }}
        }});
        return inputs;
    }}
    
    // 【核心】获取输入框的所有可能标识
    function getInputIdentifiers(input) {{
        const identifiers = [];
        
        // 1. aria-labelledby
        const ariaLabelledBy = input.getAttribute('aria-labelledby');
        if (ariaLabelledBy) {{
            ariaLabelledBy.split(' ').forEach(id => {{
                const el = document.getElementById(id);
                if (el) {{
                    const text = (el.innerText || el.textContent || '').trim();
                    if (text && text !== '.') identifiers.push(text);
                }}
            }});
        }}
        
        // 2. Label 标签
        if (input.labels && input.labels.length > 0) {{
            input.labels.forEach(label => {{
                const text = (label.innerText || label.textContent || '').trim();
                if (text) identifiers.push(text);
            }});
        }}
        
        // 3. 通过 for 属性查找 label
        if (input.id) {{
            const label = document.querySelector(`label[for="${{input.id}}"]`);
            if (label) {{
                const text = (label.innerText || label.textContent || '').trim();
                if (text) identifiers.push(text);
            }}
        }}
        
        // 4. 基本属性
        if (input.placeholder) identifiers.push(input.placeholder.trim());
        if (input.name) identifiers.push(input.name.trim());
        if (input.id) identifiers.push(input.id.trim());
        if (input.title) identifiers.push(input.title.trim());
        if (input.getAttribute('aria-label')) identifiers.push(input.getAttribute('aria-label').trim());
        
        // 5. 【问卷星特有】查找问题容器中的标题
        let parent = input.closest('.field, .ui-field, .q-inner, .topichtml, [topics], [class*="question"]');
        if (parent) {{
            const titleEl = parent.querySelector('.field-label, .topichtml, .topic-title, .q-title, [class*="title"], label');
            if (titleEl) {{
                const text = (titleEl.innerText || titleEl.textContent || '').trim();
                if (text && !identifiers.includes(text)) identifiers.push(text);
            }}
        }}
        
        // 6. 父元素中的 label 和文本
        parent = input.parentElement;
        for (let depth = 0; depth < 5 && parent; depth++) {{
            const labelEl = parent.querySelector('label');
            if (labelEl) {{
                const text = (labelEl.innerText || labelEl.textContent || '').trim();
                if (text && !identifiers.includes(text)) identifiers.push(text);
            }}
            
            Array.from(parent.childNodes).forEach(node => {{
                if (node.nodeType === Node.TEXT_NODE) {{
                    const text = node.textContent.trim();
                    if (text && text.length > 0 && text.length < 50 && !identifiers.includes(text)) {{
                        identifiers.push(text);
                    }}
                }}
            }});
            
            parent = parent.parentElement;
        }}
        
        // 7. 前置兄弟元素
        let sibling = input.previousElementSibling;
        let siblingCount = 0;
        while (sibling && siblingCount < 3) {{
            const text = (sibling.innerText || sibling.textContent || '').trim();
            if (text && text.length < 50 && !identifiers.includes(text)) {{
                identifiers.push(text);
            }}
            sibling = sibling.previousElementSibling;
            siblingCount++;
        }}
        
        // 8. 向上查找前置兄弟
        parent = input.parentElement;
        for (let depth = 0; depth < 8 && parent; depth++) {{
            const prevSib = parent.previousElementSibling;
            if (prevSib) {{
                const text = (prevSib.innerText || prevSib.textContent || '').trim();
                if (text && text.length > 1 && text.length < 50 && !identifiers.includes(text)) {{
                    identifiers.push(text);
                    break;
                }}
            }}
            parent = parent.parentElement;
        }}
        
        return identifiers;
    }}
    
    // 清理文本
    function cleanText(text) {{
        if (!text) return '';
        return String(text).toLowerCase().replace(/[：:*？?！!。.、，,\\s\\-_\\(\\)（）【】\\[\\]]/g, '').trim();
    }}
    
    // 【核心】评分匹配
    function matchKeyword(identifiers, keyword) {{
        const cleanKeyword = cleanText(keyword);
        if (!cleanKeyword) return {{ matched: false, identifier: null, score: 0 }};
        
        const subKeywords = keyword.split(/[|,;，；、]/).map(k => cleanText(k)).filter(k => k);
        if (subKeywords.length === 0) subKeywords.push(cleanKeyword);
        
        let bestScore = 0;
        let bestIdentifier = null;
        
        for (const subKey of subKeywords) {{
            for (const identifier of identifiers) {{
                const cleanIdentifier = cleanText(identifier);
                if (!cleanIdentifier) continue;
                
                let currentScore = 0;
                
                if (cleanIdentifier === subKey) {{
                    currentScore = 100;
                }} else if (cleanIdentifier.includes(subKey)) {{
                    const ratio = subKey.length / cleanIdentifier.length;
                    currentScore = 80 + (ratio * 10); 
                }} else if (subKey.includes(cleanIdentifier)) {{
                    currentScore = 70;
                }} else {{
                    let commonChars = 0;
                    for (const char of subKey) {{
                        if (cleanIdentifier.includes(char)) commonChars++;
                    }}
                    const similarity = commonChars / subKey.length;
                    if (similarity >= 0.5) {{
                        currentScore = Math.floor(similarity * 60);
                    }}
                }}
                
                if (currentScore > bestScore) {{
                    bestScore = currentScore;
                    bestIdentifier = identifier;
                }}
            }}
        }}
        
        return {{ matched: bestScore > 0, identifier: bestIdentifier, score: bestScore }};
    }}
    
    // 填充输入框
    function fillInput(input, value) {{
        input.focus();
        input.value = value;
        
        ['input', 'change', 'blur', 'keyup', 'keydown'].forEach(eventName => {{
            input.dispatchEvent(new Event(eventName, {{ bubbles: true, cancelable: true }}));
        }});
        
        try {{
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            if (nativeInputValueSetter) {{
                nativeInputValueSetter.call(input, value);
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }} catch (e) {{}}
        
        try {{
            const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
            if (nativeTextAreaValueSetter && input.tagName === 'TEXTAREA') {{
                nativeTextAreaValueSetter.call(input, value);
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }} catch (e) {{}}
        
        input.blur();
    }}
    
    // 主执行函数 - 以输入框为主体，为每个输入框找最佳匹配的名片字段
    async function executeAutoFill() {{
        const hasInputs = await waitForInputs();
        
        if (!hasInputs) {{
            window.__autoFillResult__ = {{ fillCount: 0, totalCount: fillData.length, status: 'completed', results: [] }};
            return;
        }}
        
        console.log('\\n📋 扫描页面输入框...');
        const allInputs = getAllInputs();
        console.log(`找到 ${{allInputs.length}} 个输入框`);
        
        allInputs.forEach((input, index) => {{
            const identifiers = getInputIdentifiers(input);
            console.log(`\\n输入框 ${{index + 1}}: ${{identifiers.slice(0, 3).join(' | ')}}`);
        }});
        
        console.log('\\n🎯 开始匹配和填写...');
        
        // 以输入框为主体遍历，为每个输入框找最佳匹配的名片字段
        allInputs.forEach((input, index) => {{
            const identifiers = getInputIdentifiers(input);
            let bestMatch = {{ item: null, score: 0, identifier: null }};
            
            // 在所有名片字段中找最佳匹配
            fillData.forEach(item => {{
                const matchResult = matchKeyword(identifiers, item.key);
                if (matchResult.matched && matchResult.score > bestMatch.score) {{
                    bestMatch = {{ item: item, score: matchResult.score, identifier: matchResult.identifier }};
                }}
            }});
            
            // 如果找到匹配且分数足够高，填写
            if (bestMatch.item && bestMatch.score >= 50) {{
                fillInput(input, bestMatch.item.value);
                console.log(`✅ 填写输入框${{index + 1}}: "${{bestMatch.item.key}}" = "${{bestMatch.item.value}}" (匹配: "${{bestMatch.identifier}}", 分数: ${{bestMatch.score}})`);
                fillCount++;
                results.push({{ key: bestMatch.item.key, value: bestMatch.item.value, matched: bestMatch.identifier, score: bestMatch.score, success: true }});
            }}
        }});
        
        // 记录未匹配的名片字段
        const filledKeys = new Set(results.filter(r => r.success).map(r => r.key));
        fillData.forEach(item => {{
            if (!filledKeys.has(item.key)) {{
                // 检查是否至少有一个结果包含这个key
                const hasResult = results.some(r => r.key === item.key);
                if (!hasResult) {{
                    console.warn(`⚠️ 名片字段未使用: "${{item.key}}"`);
                    results.push({{ key: item.key, value: item.value, matched: null, score: 0, success: false }});
                }}
            }}
        }});
        
        window.__autoFillResult__ = {{ fillCount: fillCount, totalCount: allInputs.length, status: 'completed', results: results }};
        console.log(`\\n✅ 问卷星填写完成: ${{fillCount}}/${{allInputs.length}} 个输入框`);
    }}
    
    executeAutoFill();
    return '问卷星填写脚本已执行';
}})();
        """
        return js_code
    
    def generate_jinshuju_fill_script(self, fill_data: list) -> str:
        """生成金数据专用的填充脚本 - 使用评分匹配系统"""
        import json
        fill_data_json = json.dumps(fill_data, ensure_ascii=False)
        
        js_code = f"""
(function() {{
    console.log('🚀 开始填写金数据表单...');
    
    const fillData = {fill_data_json};
    let fillCount = 0;
    const results = [];
    
    // 等待输入框加载完成
    function waitForInputs(maxAttempts = 15, interval = 400) {{
        return new Promise((resolve) => {{
            let attempts = 0;
            const checkInputs = setInterval(() => {{
                const inputs = document.querySelectorAll('input, textarea');
                attempts++;
                console.log(`🔍 尝试 ${{attempts}}/${{maxAttempts}}: 找到 ${{inputs.length}} 个输入框`);
                
                if (inputs.length > 0 || attempts >= maxAttempts) {{
                    clearInterval(checkInputs);
                    resolve(inputs.length > 0);
                }}
            }}, interval);
        }});
    }}
    
    // 获取所有可见的输入框
    function getAllInputs() {{
        const inputs = [];
        document.querySelectorAll('input, textarea').forEach(input => {{
            const style = window.getComputedStyle(input);
            if (style.display !== 'none' && style.visibility !== 'hidden') {{
                inputs.push(input);
            }}
        }});
        return inputs;
    }}
    
    // 【核心】获取输入框的所有可能标识
    function getInputIdentifiers(input) {{
        const identifiers = [];
        
        // 1. aria-labelledby
        const ariaLabelledBy = input.getAttribute('aria-labelledby');
        if (ariaLabelledBy) {{
            ariaLabelledBy.split(' ').forEach(id => {{
                const el = document.getElementById(id);
                if (el) {{
                    const text = (el.innerText || el.textContent || '').trim();
                    if (text && text !== '.') identifiers.push(text);
                }}
            }});
        }}
        
        // 2. Label 标签
        if (input.labels && input.labels.length > 0) {{
            input.labels.forEach(label => {{
                const text = (label.innerText || label.textContent || '').trim();
                if (text) identifiers.push(text);
            }});
        }}
        
        // 3. 通过 for 属性查找 label
        if (input.id) {{
            const label = document.querySelector(`label[for="${{input.id}}"]`);
            if (label) {{
                const text = (label.innerText || label.textContent || '').trim();
                if (text) identifiers.push(text);
            }}
        }}
        
        // 4. 基本属性
        if (input.placeholder) identifiers.push(input.placeholder.trim());
        if (input.name) identifiers.push(input.name.trim());
        if (input.id) identifiers.push(input.id.trim());
        if (input.title) identifiers.push(input.title.trim());
        if (input.getAttribute('aria-label')) identifiers.push(input.getAttribute('aria-label').trim());
        
        // 5. 【金数据特有】查找字段容器中的标签
        let parent = input.closest('.field, .form-field, .entry-field, [class*="field"], [data-layout]');
        if (parent) {{
            const titleEl = parent.querySelector('.label, .title, .field-label, .entry-label, [class*="label"], [class*="title"]');
            if (titleEl) {{
                const text = (titleEl.innerText || titleEl.textContent || '').trim();
                if (text && !identifiers.includes(text)) identifiers.push(text);
            }}
        }}
        
        // 6. 父元素中的 label 和文本
        parent = input.parentElement;
        for (let depth = 0; depth < 5 && parent; depth++) {{
            const labelEl = parent.querySelector('label');
            if (labelEl) {{
                const text = (labelEl.innerText || labelEl.textContent || '').trim();
                if (text && !identifiers.includes(text)) identifiers.push(text);
            }}
            
            Array.from(parent.childNodes).forEach(node => {{
                if (node.nodeType === Node.TEXT_NODE) {{
                    const text = node.textContent.trim();
                    if (text && text.length > 0 && text.length < 50 && !identifiers.includes(text)) {{
                        identifiers.push(text);
                    }}
                }}
            }});
            
            parent = parent.parentElement;
        }}
        
        // 7. 前置兄弟元素
        let sibling = input.previousElementSibling;
        let siblingCount = 0;
        while (sibling && siblingCount < 3) {{
            const text = (sibling.innerText || sibling.textContent || '').trim();
            if (text && text.length < 50 && !identifiers.includes(text)) {{
                identifiers.push(text);
            }}
            sibling = sibling.previousElementSibling;
            siblingCount++;
        }}
        
        // 8. 向上查找前置兄弟
        parent = input.parentElement;
        for (let depth = 0; depth < 8 && parent; depth++) {{
            const prevSib = parent.previousElementSibling;
            if (prevSib) {{
                const text = (prevSib.innerText || prevSib.textContent || '').trim();
                if (text && text.length > 1 && text.length < 50 && !identifiers.includes(text)) {{
                    identifiers.push(text);
                    break;
                }}
            }}
            parent = parent.parentElement;
        }}
        
        return identifiers;
    }}
    
    // 清理文本
    function cleanText(text) {{
        if (!text) return '';
        return String(text).toLowerCase().replace(/[：:*？?！!。.、，,\\s\\-_\\(\\)（）【】\\[\\]]/g, '').trim();
    }}
    
    // 【核心】评分匹配
    function matchKeyword(identifiers, keyword) {{
        const cleanKeyword = cleanText(keyword);
        if (!cleanKeyword) return {{ matched: false, identifier: null, score: 0 }};
        
        const subKeywords = keyword.split(/[|,;，；、]/).map(k => cleanText(k)).filter(k => k);
        if (subKeywords.length === 0) subKeywords.push(cleanKeyword);
        
        let bestScore = 0;
        let bestIdentifier = null;
        
        for (const subKey of subKeywords) {{
            for (const identifier of identifiers) {{
                const cleanIdentifier = cleanText(identifier);
                if (!cleanIdentifier) continue;
                
                let currentScore = 0;
                
                if (cleanIdentifier === subKey) {{
                    currentScore = 100;
                }} else if (cleanIdentifier.includes(subKey)) {{
                    const ratio = subKey.length / cleanIdentifier.length;
                    currentScore = 80 + (ratio * 10); 
                }} else if (subKey.includes(cleanIdentifier)) {{
                    currentScore = 70;
                }} else {{
                    let commonChars = 0;
                    for (const char of subKey) {{
                        if (cleanIdentifier.includes(char)) commonChars++;
                    }}
                    const similarity = commonChars / subKey.length;
                    if (similarity >= 0.5) {{
                        currentScore = Math.floor(similarity * 60);
                    }}
                }}
                
                if (currentScore > bestScore) {{
                    bestScore = currentScore;
                    bestIdentifier = identifier;
                }}
            }}
        }}
        
        return {{ matched: bestScore > 0, identifier: bestIdentifier, score: bestScore }};
    }}
    
    // 填充输入框
    function fillInput(input, value) {{
        input.focus();
        input.value = value;
        
        ['input', 'change', 'blur', 'keyup', 'keydown'].forEach(eventName => {{
            input.dispatchEvent(new Event(eventName, {{ bubbles: true, cancelable: true }}));
        }});
        
        try {{
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            if (nativeInputValueSetter) {{
                nativeInputValueSetter.call(input, value);
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }} catch (e) {{}}
        
        try {{
            const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
            if (nativeTextAreaValueSetter && input.tagName === 'TEXTAREA') {{
                nativeTextAreaValueSetter.call(input, value);
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }} catch (e) {{}}
        
        input.blur();
    }}
    
    // 主执行函数 - 以输入框为主体，为每个输入框找最佳匹配的名片字段
    async function executeAutoFill() {{
        const hasInputs = await waitForInputs();
        
        if (!hasInputs) {{
            window.__autoFillResult__ = {{ fillCount: 0, totalCount: fillData.length, status: 'completed', results: [] }};
            return;
        }}
        
        console.log('\\n📋 扫描页面输入框...');
        const allInputs = getAllInputs();
        console.log(`找到 ${{allInputs.length}} 个输入框`);
        
        allInputs.forEach((input, index) => {{
            const identifiers = getInputIdentifiers(input);
            console.log(`\\n输入框 ${{index + 1}}: ${{identifiers.slice(0, 3).join(' | ')}}`);
        }});
        
        console.log('\\n🎯 开始匹配和填写...');
        
        // 以输入框为主体遍历，为每个输入框找最佳匹配的名片字段
        allInputs.forEach((input, index) => {{
            const identifiers = getInputIdentifiers(input);
            let bestMatch = {{ item: null, score: 0, identifier: null }};
            
            // 在所有名片字段中找最佳匹配
            fillData.forEach(item => {{
                const matchResult = matchKeyword(identifiers, item.key);
                if (matchResult.matched && matchResult.score > bestMatch.score) {{
                    bestMatch = {{ item: item, score: matchResult.score, identifier: matchResult.identifier }};
                }}
            }});
            
            // 如果找到匹配且分数足够高，填写
            if (bestMatch.item && bestMatch.score >= 50) {{
                fillInput(input, bestMatch.item.value);
                console.log(`✅ 填写输入框${{index + 1}}: "${{bestMatch.item.key}}" = "${{bestMatch.item.value}}" (匹配: "${{bestMatch.identifier}}", 分数: ${{bestMatch.score}})`);
                fillCount++;
                results.push({{ key: bestMatch.item.key, value: bestMatch.item.value, matched: bestMatch.identifier, score: bestMatch.score, success: true }});
            }}
        }});
        
        // 记录未匹配的名片字段
        const filledKeys = new Set(results.filter(r => r.success).map(r => r.key));
        fillData.forEach(item => {{
            if (!filledKeys.has(item.key)) {{
                const hasResult = results.some(r => r.key === item.key);
                if (!hasResult) {{
                    console.warn(`⚠️ 名片字段未使用: "${{item.key}}"`);
                    results.push({{ key: item.key, value: item.value, matched: null, score: 0, success: false }});
                }}
            }}
        }});
        
        window.__autoFillResult__ = {{ fillCount: fillCount, totalCount: allInputs.length, status: 'completed', results: results }};
        console.log(`\\n✅ 金数据填写完成: ${{fillCount}}/${{allInputs.length}} 个输入框`);
    }}
    
    executeAutoFill();
    return '金数据填写脚本已执行';
}})();
        """
        return js_code
    
    def generate_shimo_fill_script(self, fill_data: list) -> str:
        """生成石墨文档专用的填充脚本 - 复用AutoFillEngineV2的成熟匹配逻辑"""
        import json
        fill_data_json = json.dumps(fill_data, ensure_ascii=False)
        
        js_code = f"""
(function() {{
    console.log('🚀 开始填写石墨文档表单...');
    
    const fillData = {fill_data_json};
    let fillCount = 0;
    const results = [];
    
    // 等待输入框加载完成
    function waitForInputs(maxAttempts = 15, interval = 400) {{
        return new Promise((resolve) => {{
            let attempts = 0;
            const checkInputs = setInterval(() => {{
                const inputs = document.querySelectorAll('input, textarea');
                attempts++;
                console.log(`🔍 尝试 ${{attempts}}/${{maxAttempts}}: 找到 ${{inputs.length}} 个输入框`);
                
                if (inputs.length > 0 || attempts >= maxAttempts) {{
                    clearInterval(checkInputs);
                    resolve(inputs.length > 0);
                }}
            }}, interval);
        }});
    }}
    
    // 获取所有可见的输入框
    function getAllInputs() {{
        const inputs = [];
        document.querySelectorAll('input, textarea').forEach(input => {{
            const style = window.getComputedStyle(input);
            if (style.display !== 'none' && style.visibility !== 'hidden') {{
                inputs.push(input);
            }}
        }});
        return inputs;
    }}
    
    // 【核心】获取输入框的所有可能标识 - 参考AutoFillEngineV2
    function getInputIdentifiers(input) {{
        const identifiers = [];
        
        // 1. aria-labelledby 查找
        const ariaLabelledBy = input.getAttribute('aria-labelledby');
        if (ariaLabelledBy) {{
            ariaLabelledBy.split(' ').forEach(id => {{
                const el = document.getElementById(id);
                if (el) {{
                    const text = (el.innerText || el.textContent || '').trim();
                    if (text && text !== '.') identifiers.push(text);
                }}
            }});
        }}
        
        // 2. Label 标签
        if (input.labels && input.labels.length > 0) {{
            input.labels.forEach(label => {{
                const text = (label.innerText || label.textContent || '').trim();
                if (text) identifiers.push(text);
            }});
        }}
        
        // 3. 通过 for 属性查找 label
        if (input.id) {{
            const label = document.querySelector(`label[for="${{input.id}}"]`);
            if (label) {{
                const text = (label.innerText || label.textContent || '').trim();
                if (text) identifiers.push(text);
            }}
        }}
        
        // 4. placeholder, name, id, title, aria-label
        if (input.placeholder) identifiers.push(input.placeholder.trim());
        if (input.name) identifiers.push(input.name.trim());
        if (input.id) identifiers.push(input.id.trim());
        if (input.title) identifiers.push(input.title.trim());
        if (input.getAttribute('aria-label')) identifiers.push(input.getAttribute('aria-label').trim());
        
        // 5. 【石墨文档特殊】向上查找包含序号的问题容器
        let parent = input.parentElement;
        for (let depth = 0; depth < 10 && parent; depth++) {{
            const parentText = (parent.innerText || '').trim();
            // 匹配 "01.* 小红书名字" 格式
            const match = parentText.match(/^(\\d{{1,2}})\\.\\s*\\*?\\s*([^\\n]+)/);
            if (match) {{
                const labelText = match[2].trim();
                if (labelText && !identifiers.includes(labelText)) {{
                    identifiers.push(labelText);
                }}
                break; // 找到就停止
            }}
            parent = parent.parentElement;
        }}
        
        // 6. 父元素中的 label 和直接文本
        parent = input.parentElement;
        for (let depth = 0; depth < 5 && parent; depth++) {{
            // 查找 label 元素
            const labelEl = parent.querySelector('label');
            if (labelEl) {{
                const text = (labelEl.innerText || labelEl.textContent || '').trim();
                if (text && !identifiers.includes(text)) identifiers.push(text);
            }}
            
            // 获取父元素的直接文本内容
            Array.from(parent.childNodes).forEach(node => {{
                if (node.nodeType === Node.TEXT_NODE) {{
                    const text = node.textContent.trim();
                    if (text && text.length > 0 && text.length < 50 && !identifiers.includes(text)) {{
                        identifiers.push(text);
                    }}
                }}
            }});
            
            parent = parent.parentElement;
        }}
        
        // 7. 前置兄弟元素
        let sibling = input.previousElementSibling;
        let siblingCount = 0;
        while (sibling && siblingCount < 3) {{
            const text = (sibling.innerText || sibling.textContent || '').trim();
            // 清理序号
            const cleanText = text.replace(/^\\d{{1,2}}\\.\\s*\\*?\\s*/, '').trim();
            if (cleanText && cleanText.length < 50 && !identifiers.includes(cleanText)) {{
                identifiers.push(cleanText);
            }}
            sibling = sibling.previousElementSibling;
            siblingCount++;
        }}
        
        // 8. 向上遍历查找前置兄弟
        parent = input.parentElement;
        for (let depth = 0; depth < 8 && parent; depth++) {{
            const prevSib = parent.previousElementSibling;
            if (prevSib) {{
                const text = (prevSib.innerText || prevSib.textContent || '').trim();
                // 清理序号
                const cleanText = text.replace(/^\\d{{1,2}}\\.\\s*\\*?\\s*/, '').trim();
                if (cleanText && cleanText.length > 1 && cleanText.length < 50 && !identifiers.includes(cleanText)) {{
                    identifiers.push(cleanText);
                    break;
                }}
            }}
            parent = parent.parentElement;
        }}
        
        return identifiers;
    }}
    
    // 清理文本用于匹配
    function cleanText(text) {{
        if (!text) return '';
        return String(text)
            .toLowerCase()
            .replace(/[：:*？?！!。.、，,\\s\\-_\\(\\)（）【】\\[\\]]/g, '')
            .trim();
    }}
    
    // 【核心】匹配关键词 - 评分系统
    function matchKeyword(identifiers, keyword) {{
        const cleanKeyword = cleanText(keyword);
        if (!cleanKeyword) return {{ matched: false, identifier: null, score: 0 }};
        
        // 支持顿号、逗号、竖线分隔的多个关键词
        const subKeywords = keyword.split(/[|,;，；、]/).map(k => cleanText(k)).filter(k => k);
        if (subKeywords.length === 0) subKeywords.push(cleanKeyword);
        
        let bestScore = 0;
        let bestIdentifier = null;
        
        for (const subKey of subKeywords) {{
            for (const identifier of identifiers) {{
                const cleanIdentifier = cleanText(identifier);
                if (!cleanIdentifier) continue;
                
                let currentScore = 0;
                
                // 1. 完全匹配 (最高优先级)
                if (cleanIdentifier === subKey) {{
                    currentScore = 100;
                }} 
                // 2. 包含匹配 (次高优先级)
                else if (cleanIdentifier.includes(subKey)) {{
                    const ratio = subKey.length / cleanIdentifier.length;
                    currentScore = 80 + (ratio * 10); 
                }}
                else if (subKey.includes(cleanIdentifier)) {{
                    currentScore = 70;
                }}
                // 3. 部分字符匹配
                else {{
                    let commonChars = 0;
                    for (const char of subKey) {{
                        if (cleanIdentifier.includes(char)) commonChars++;
                    }}
                    const similarity = commonChars / subKey.length;
                    if (similarity >= 0.5) {{
                        currentScore = Math.floor(similarity * 60);
                    }}
                }}
                
                if (currentScore > bestScore) {{
                    bestScore = currentScore;
                    bestIdentifier = identifier;
                }}
            }}
        }}
        
        return {{ matched: bestScore > 0, identifier: bestIdentifier, score: bestScore }};
    }}
    
    // 填充输入框 - React 兼容
    function fillInput(input, value) {{
        input.focus();
        input.value = value;
        
        // 触发所有事件
        ['input', 'change', 'blur', 'keyup', 'keydown'].forEach(eventName => {{
            input.dispatchEvent(new Event(eventName, {{ bubbles: true, cancelable: true }}));
        }});
        
        // React/Vue 原生 setter
        try {{
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            if (nativeInputValueSetter) {{
                nativeInputValueSetter.call(input, value);
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }} catch (e) {{}}
        
        try {{
            const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype, 'value'
            ).set;
            if (nativeTextAreaValueSetter && input.tagName === 'TEXTAREA') {{
                nativeTextAreaValueSetter.call(input, value);
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }} catch (e) {{}}
        
        input.blur();
    }}
    
    // 主执行函数 - 以输入框为主体，为每个输入框找最佳匹配的名片字段
    async function executeAutoFill() {{
        const hasInputs = await waitForInputs();
        
        if (!hasInputs) {{
            window.__autoFillResult__ = {{
                fillCount: 0,
                totalCount: fillData.length,
                status: 'completed',
                results: []
            }};
            return;
        }}
        
        console.log('\\n📋 扫描页面输入框...');
        const allInputs = getAllInputs();
        console.log(`找到 ${{allInputs.length}} 个输入框`);
        
        // 打印所有输入框的标识信息
        allInputs.forEach((input, index) => {{
            const identifiers = getInputIdentifiers(input);
            console.log(`\\n输入框 ${{index + 1}}: ${{identifiers.slice(0, 3).join(' | ')}}`);
        }});
        
        console.log('\\n🎯 开始匹配和填写...');
        
        // 以输入框为主体遍历，为每个输入框找最佳匹配的名片字段
        allInputs.forEach((input, index) => {{
            const identifiers = getInputIdentifiers(input);
            let bestMatch = {{ item: null, score: 0, identifier: null }};
            
            // 在所有名片字段中找最佳匹配
            fillData.forEach(item => {{
                const matchResult = matchKeyword(identifiers, item.key);
                if (matchResult.matched && matchResult.score > bestMatch.score) {{
                    bestMatch = {{ item: item, score: matchResult.score, identifier: matchResult.identifier }};
                }}
            }});
            
            // 如果找到匹配且分数足够高，填写
            if (bestMatch.item && bestMatch.score >= 50) {{
                fillInput(input, bestMatch.item.value);
                console.log(`✅ 填写输入框${{index + 1}}: "${{bestMatch.item.key}}" = "${{bestMatch.item.value}}" (匹配: "${{bestMatch.identifier}}", 分数: ${{bestMatch.score}})`);
                fillCount++;
                results.push({{
                    key: bestMatch.item.key,
                    value: bestMatch.item.value,
                    matched: bestMatch.identifier,
                    score: bestMatch.score,
                    success: true
                }});
            }}
        }});
        
        // 记录未匹配的名片字段
        const filledKeys = new Set(results.filter(r => r.success).map(r => r.key));
        fillData.forEach(item => {{
            if (!filledKeys.has(item.key)) {{
                const hasResult = results.some(r => r.key === item.key);
                if (!hasResult) {{
                    console.warn(`⚠️ 名片字段未使用: "${{item.key}}"`);
                    results.push({{
                        key: item.key,
                        value: item.value,
                        matched: null,
                        score: 0,
                        success: false
                    }});
                }}
            }}
        }});
        
        window.__autoFillResult__ = {{
            fillCount: fillCount,
            totalCount: allInputs.length,
            status: 'completed',
            results: results
        }};
        
        console.log(`\\n✅ 石墨文档填写完成: ${{fillCount}}/${{allInputs.length}} 个输入框`);
    }}
    
    executeAutoFill();
    return '石墨文档填写脚本已执行';
}})();
        """
        return js_code
    
    def generate_credamo_fill_script(self, fill_data: list) -> str:
        """生成见数(Credamo)专用的填充脚本 - Vue框架适配"""
        import json
        fill_data_json = json.dumps(fill_data, ensure_ascii=False)
        
        js_code = f"""
(function() {{
    console.log('🚀 开始填写见数(Credamo)表单...');
    
    const fillData = {fill_data_json};
    let fillCount = 0;
    const results = [];
    
    // 等待Vue组件和输入框加载完成
    function waitForInputs(maxAttempts = 20, interval = 500) {{
        return new Promise((resolve) => {{
            let attempts = 0;
            const checkInputs = setInterval(() => {{
                // 见数特有的输入框选择器
                const inputs = document.querySelectorAll('input[type="text"], input:not([type]), textarea, .el-input__inner, .el-textarea__inner, [contenteditable="true"]');
                attempts++;
                console.log(`🔍 尝试 ${{attempts}}/${{maxAttempts}}: 找到 ${{inputs.length}} 个输入框`);
                
                if (inputs.length > 0 || attempts >= maxAttempts) {{
                    clearInterval(checkInputs);
                    resolve(inputs.length > 0);
                }}
            }}, interval);
        }});
    }}
    
    // 获取所有可见的输入框（包括Vue/Element-UI组件）
    function getAllInputs() {{
        const inputs = [];
        // 见数使用Vue/Element-UI，查找多种输入框类型
        const selectors = [
            'input[type="text"]',
            'input:not([type])',
            'textarea',
            '.el-input__inner',
            '.el-textarea__inner',
            '[contenteditable="true"]',
            '.ant-input',
            '.ivu-input'
        ];
        
        document.querySelectorAll(selectors.join(', ')).forEach(input => {{
            const style = window.getComputedStyle(input);
            if (style.display !== 'none' && style.visibility !== 'hidden' && input.offsetParent !== null) {{
                // 排除隐藏的和只读的
                if (!input.disabled && !input.readOnly) {{
                    inputs.push(input);
                }}
            }}
        }});
        return inputs;
    }}
    
    // 【核心】获取输入框的所有可能标识 - 见数特殊适配
    function getInputIdentifiers(input) {{
        const identifiers = [];
        
        // 1. aria-labelledby
        const ariaLabelledBy = input.getAttribute('aria-labelledby');
        if (ariaLabelledBy) {{
            ariaLabelledBy.split(' ').forEach(id => {{
                const el = document.getElementById(id);
                if (el) {{
                    const text = (el.innerText || el.textContent || '').trim();
                    if (text && text !== '.') identifiers.push(text);
                }}
            }});
        }}
        
        // 2. Label 标签
        if (input.labels && input.labels.length > 0) {{
            input.labels.forEach(label => {{
                const text = (label.innerText || label.textContent || '').trim();
                if (text) identifiers.push(text);
            }});
        }}
        
        // 3. 通过 for 属性查找 label
        if (input.id) {{
            const label = document.querySelector(`label[for="${{input.id}}"]`);
            if (label) {{
                const text = (label.innerText || label.textContent || '').trim();
                if (text) identifiers.push(text);
            }}
        }}
        
        // 4. 基本属性
        if (input.placeholder) identifiers.push(input.placeholder.trim());
        if (input.name) identifiers.push(input.name.trim());
        if (input.id) identifiers.push(input.id.trim());
        if (input.title) identifiers.push(input.title.trim());
        if (input.getAttribute('aria-label')) identifiers.push(input.getAttribute('aria-label').trim());
        
        // 5. 【见数特有】查找问题容器中的标题（Vue组件结构）
        let parent = input.closest('.question-item, .form-item, .el-form-item, .survey-question, [class*="question"], [class*="field"]');
        if (parent) {{
            // 查找标题元素
            const titleEl = parent.querySelector('.question-title, .el-form-item__label, .form-label, .title, label, [class*="title"], [class*="label"]');
            if (titleEl) {{
                const text = (titleEl.innerText || titleEl.textContent || '').trim();
                // 清理序号和星号
                const cleanText = text.replace(/^[\\d\\*\\.、]+\\s*/, '').replace(/[\\*必填]/g, '').trim();
                if (cleanText && !identifiers.includes(cleanText)) identifiers.push(cleanText);
            }}
        }}
        
        // 6. 【见数特有】查找 regular-answer 容器中的描述文字
        parent = input.closest('.regular-answer, .answer-wrapper, .input-wrapper');
        if (parent) {{
            const prevEl = parent.previousElementSibling;
            if (prevEl) {{
                const text = (prevEl.innerText || prevEl.textContent || '').trim();
                const cleanText = text.replace(/^[\\d\\*\\.、]+\\s*/, '').replace(/[\\*必填]/g, '').trim();
                if (cleanText && cleanText.length < 100 && !identifiers.includes(cleanText)) {{
                    identifiers.push(cleanText);
                }}
            }}
        }}
        
        // 7. 父元素中的 label 和直接文本
        parent = input.parentElement;
        for (let depth = 0; depth < 6 && parent; depth++) {{
            // 查找 label 元素
            const labelEl = parent.querySelector('label, .label, [class*="label"]');
            if (labelEl && labelEl !== input) {{
                const text = (labelEl.innerText || labelEl.textContent || '').trim();
                const cleanText = text.replace(/^[\\d\\*\\.、]+\\s*/, '').replace(/[\\*必填]/g, '').trim();
                if (cleanText && !identifiers.includes(cleanText)) identifiers.push(cleanText);
            }}
            
            // 获取父元素的直接文本内容
            Array.from(parent.childNodes).forEach(node => {{
                if (node.nodeType === Node.TEXT_NODE) {{
                    const text = node.textContent.trim();
                    if (text && text.length > 1 && text.length < 50 && !identifiers.includes(text)) {{
                        identifiers.push(text);
                    }}
                }}
            }});
            
            parent = parent.parentElement;
        }}
        
        // 8. 前置兄弟元素
        let sibling = input.previousElementSibling;
        let siblingCount = 0;
        while (sibling && siblingCount < 3) {{
            const text = (sibling.innerText || sibling.textContent || '').trim();
            const cleanText = text.replace(/^[\\d\\*\\.、]+\\s*/, '').replace(/[\\*必填]/g, '').trim();
            if (cleanText && cleanText.length < 80 && !identifiers.includes(cleanText)) {{
                identifiers.push(cleanText);
            }}
            sibling = sibling.previousElementSibling;
            siblingCount++;
        }}
        
        // 9. 向上遍历查找前置兄弟（Vue组件嵌套较深）
        parent = input.parentElement;
        for (let depth = 0; depth < 10 && parent; depth++) {{
            const prevSib = parent.previousElementSibling;
            if (prevSib) {{
                const text = (prevSib.innerText || prevSib.textContent || '').trim();
                const cleanText = text.replace(/^[\\d\\*\\.、]+\\s*/, '').replace(/[\\*必填]/g, '').trim();
                if (cleanText && cleanText.length > 1 && cleanText.length < 80 && !identifiers.includes(cleanText)) {{
                    identifiers.push(cleanText);
                    break;
                }}
            }}
            parent = parent.parentElement;
        }}
        
        return identifiers;
    }}
    
    // 清理文本用于匹配
    function cleanText(text) {{
        if (!text) return '';
        return String(text)
            .toLowerCase()
            .replace(/[：:*？?！!。.、，,\\s\\-_\\(\\)（）【】\\[\\]]/g, '')
            .trim();
    }}
    
    // 【核心】匹配关键词 - 评分系统
    function matchKeyword(identifiers, keyword) {{
        const cleanKeyword = cleanText(keyword);
        if (!cleanKeyword) return {{ matched: false, identifier: null, score: 0 }};
        
        // 支持顿号、逗号、竖线分隔的多个关键词
        const subKeywords = keyword.split(/[|,;，；、]/).map(k => cleanText(k)).filter(k => k);
        if (subKeywords.length === 0) subKeywords.push(cleanKeyword);
        
        let bestScore = 0;
        let bestIdentifier = null;
        
        for (const subKey of subKeywords) {{
            for (const identifier of identifiers) {{
                const cleanIdentifier = cleanText(identifier);
                if (!cleanIdentifier) continue;
                
                let currentScore = 0;
                
                // 1. 完全匹配 (最高优先级)
                if (cleanIdentifier === subKey) {{
                    currentScore = 100;
                }} 
                // 2. 包含匹配 (次高优先级)
                else if (cleanIdentifier.includes(subKey)) {{
                    const ratio = subKey.length / cleanIdentifier.length;
                    currentScore = 80 + (ratio * 10); 
                }}
                else if (subKey.includes(cleanIdentifier)) {{
                    currentScore = 70;
                }}
                // 3. 部分字符匹配
                else {{
                    let commonChars = 0;
                    for (const char of subKey) {{
                        if (cleanIdentifier.includes(char)) commonChars++;
                    }}
                    const similarity = commonChars / subKey.length;
                    if (similarity >= 0.5) {{
                        currentScore = Math.floor(similarity * 60);
                    }}
                }}
                
                if (currentScore > bestScore) {{
                    bestScore = currentScore;
                    bestIdentifier = identifier;
                }}
            }}
        }}
        
        return {{ matched: bestScore > 0, identifier: bestIdentifier, score: bestScore }};
    }}
    
    // 填充输入框 - Vue/Element-UI 兼容
    function fillInput(input, value) {{
        input.focus();
        
        // 清空原有值
        input.value = '';
        
        // 设置新值
        input.value = value;
        
        // 触发所有可能的事件（Vue/React 兼容）
        ['input', 'change', 'blur', 'keyup', 'keydown', 'keypress'].forEach(eventName => {{
            input.dispatchEvent(new Event(eventName, {{ bubbles: true, cancelable: true }}));
        }});
        
        // React/Vue 原生 setter 触发
        try {{
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            if (nativeInputValueSetter) {{
                nativeInputValueSetter.call(input, value);
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }} catch (e) {{}}
        
        try {{
            const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype, 'value'
            ).set;
            if (nativeTextAreaValueSetter && input.tagName === 'TEXTAREA') {{
                nativeTextAreaValueSetter.call(input, value);
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }} catch (e) {{}}
        
        // Vue 特殊处理：触发 compositionend 事件
        try {{
            input.dispatchEvent(new CompositionEvent('compositionend', {{ bubbles: true, data: value }}));
        }} catch (e) {{}}
        
        input.blur();
    }}
    
    // 主执行函数 - 以输入框为主体，为每个输入框找最佳匹配的名片字段
    async function executeAutoFill() {{
        const hasInputs = await waitForInputs();
        
        if (!hasInputs) {{
            console.warn('⚠️ 未找到任何输入框');
            window.__autoFillResult__ = {{
                fillCount: 0,
                totalCount: fillData.length,
                status: 'completed',
                results: []
            }};
            return;
        }}
        
        console.log('\\n📋 扫描页面输入框...');
        const allInputs = getAllInputs();
        console.log(`找到 ${{allInputs.length}} 个可填写的输入框`);
        
        // 打印所有输入框的标识信息（调试用）
        allInputs.forEach((input, index) => {{
            const identifiers = getInputIdentifiers(input);
            console.log(`\\n输入框 ${{index + 1}}: ${{identifiers.slice(0, 3).join(' | ')}}`);
        }});
        
        console.log('\\n🎯 开始匹配和填写...');
        
        // 以输入框为主体遍历，为每个输入框找最佳匹配的名片字段
        allInputs.forEach((input, index) => {{
            const identifiers = getInputIdentifiers(input);
            let bestMatch = {{ item: null, score: 0, identifier: null }};
            
            // 在所有名片字段中找最佳匹配
            fillData.forEach(item => {{
                const matchResult = matchKeyword(identifiers, item.key);
                if (matchResult.matched && matchResult.score > bestMatch.score) {{
                    bestMatch = {{ item: item, score: matchResult.score, identifier: matchResult.identifier }};
                }}
            }});
            
            // 如果找到匹配且分数足够高，填写
            if (bestMatch.item && bestMatch.score >= 50) {{
                fillInput(input, bestMatch.item.value);
                console.log(`✅ 填写输入框${{index + 1}}: "${{bestMatch.item.key}}" = "${{bestMatch.item.value}}" (匹配: "${{bestMatch.identifier}}", 分数: ${{bestMatch.score}})`);
                fillCount++;
                results.push({{
                    key: bestMatch.item.key,
                    value: bestMatch.item.value,
                    matched: bestMatch.identifier,
                    score: bestMatch.score,
                    success: true
                }});
            }}
        }});
        
        // 记录未匹配的名片字段
        const filledKeys = new Set(results.filter(r => r.success).map(r => r.key));
        fillData.forEach(item => {{
            if (!filledKeys.has(item.key)) {{
                const hasResult = results.some(r => r.key === item.key);
                if (!hasResult) {{
                    console.warn(`⚠️ 名片字段未使用: "${{item.key}}"`);
                    results.push({{
                        key: item.key,
                        value: item.value,
                        matched: null,
                        score: 0,
                        success: false
                    }});
                }}
            }}
        }});
        
        window.__autoFillResult__ = {{
            fillCount: fillCount,
            totalCount: allInputs.length,
            status: 'completed',
            results: results
        }};
        
        console.log(`\\n✅ 见数表单填写完成: ${{fillCount}}/${{allInputs.length}} 个输入框`);
    }}
    
    executeAutoFill();
    return '见数(Credamo)填写脚本已执行';
}})();
        """
        return js_code
    
    def generate_wenjuan_fill_script(self, fill_data: list) -> str:
        """生成问卷网(wenjuan.com)专用的填充脚本 - Vue框架适配"""
        import json
        fill_data_json = json.dumps(fill_data, ensure_ascii=False)
        
        js_code = f"""
(function() {{
    console.log('🚀 开始填写问卷网表单...');
    
    const fillData = {fill_data_json};
    let fillCount = 0;
    const results = [];
    
    // 等待Vue组件和输入框加载完成
    function waitForInputs(maxAttempts = 20, interval = 500) {{
        return new Promise((resolve) => {{
            let attempts = 0;
            const checkInputs = setInterval(() => {{
                // 问卷网特有的输入框选择器
                const inputs = document.querySelectorAll('input[type="text"], input:not([type]), textarea, .el-input__inner, .el-textarea__inner, .survey-input, .wj-input');
                attempts++;
                console.log(`🔍 尝试 ${{attempts}}/${{maxAttempts}}: 找到 ${{inputs.length}} 个输入框`);
                
                if (inputs.length > 0 || attempts >= maxAttempts) {{
                    clearInterval(checkInputs);
                    resolve(inputs.length > 0);
                }}
            }}, interval);
        }});
    }}
    
    // 获取所有可见的输入框
    function getAllInputs() {{
        const inputs = [];
        const selectors = [
            'input[type="text"]',
            'input:not([type])',
            'textarea',
            '.el-input__inner',
            '.el-textarea__inner',
            '.survey-input input',
            '.wj-input input',
            '[contenteditable="true"]'
        ];
        
        document.querySelectorAll(selectors.join(', ')).forEach(input => {{
            const style = window.getComputedStyle(input);
            if (style.display !== 'none' && style.visibility !== 'hidden' && input.offsetParent !== null) {{
                if (!input.disabled && !input.readOnly) {{
                    inputs.push(input);
                }}
            }}
        }});
        return inputs;
    }}
    
    // 【核心】获取输入框的所有可能标识 - 问卷网特殊适配
    function getInputIdentifiers(input) {{
        const identifiers = [];
        
        // 1. aria-labelledby
        const ariaLabelledBy = input.getAttribute('aria-labelledby');
        if (ariaLabelledBy) {{
            ariaLabelledBy.split(' ').forEach(id => {{
                const el = document.getElementById(id);
                if (el) {{
                    const text = (el.innerText || el.textContent || '').trim();
                    if (text && text !== '.') identifiers.push(text);
                }}
            }});
        }}
        
        // 2. Label 标签
        if (input.labels && input.labels.length > 0) {{
            input.labels.forEach(label => {{
                const text = (label.innerText || label.textContent || '').trim();
                if (text) identifiers.push(text);
            }});
        }}
        
        // 3. 通过 for 属性查找 label
        if (input.id) {{
            const label = document.querySelector(`label[for="${{input.id}}"]`);
            if (label) {{
                const text = (label.innerText || label.textContent || '').trim();
                if (text) identifiers.push(text);
            }}
        }}
        
        // 4. 基本属性
        if (input.placeholder) identifiers.push(input.placeholder.trim());
        if (input.name) identifiers.push(input.name.trim());
        if (input.id) identifiers.push(input.id.trim());
        if (input.title) identifiers.push(input.title.trim());
        if (input.getAttribute('aria-label')) identifiers.push(input.getAttribute('aria-label').trim());
        
        // 5. 【问卷网特有】查找问题容器中的标题
        let parent = input.closest('.survey-question, .question-item, .wj-question, .el-form-item, [class*="question"]');
        if (parent) {{
            const titleEl = parent.querySelector('.question-title, .wj-title, .el-form-item__label, .title, label, [class*="title"]');
            if (titleEl) {{
                const text = (titleEl.innerText || titleEl.textContent || '').trim();
                // 清理序号和星号 (如 "* 1. 小红书名字")
                const cleanText = text.replace(/^[\\*\\s]*\\d+[\\. 、]+\\s*/, '').replace(/[\\*必填]/g, '').trim();
                if (cleanText && !identifiers.includes(cleanText)) identifiers.push(cleanText);
            }}
        }}
        
        // 6. 【问卷网特有】从 survey-wrapper 中获取问题文本
        parent = input.closest('.survey-wrapper, .survey-web-wrapper');
        if (parent) {{
            // 查找所有问题标题
            const allTitles = parent.querySelectorAll('.question-title, .wj-title, [class*="title"]');
            // 找到离当前input最近的标题
            let closestTitle = null;
            let closestDistance = Infinity;
            
            allTitles.forEach(title => {{
                const titleRect = title.getBoundingClientRect();
                const inputRect = input.getBoundingClientRect();
                const distance = Math.abs(titleRect.bottom - inputRect.top);
                if (distance < closestDistance && titleRect.bottom < inputRect.top + 50) {{
                    closestDistance = distance;
                    closestTitle = title;
                }}
            }});
            
            if (closestTitle) {{
                const text = (closestTitle.innerText || closestTitle.textContent || '').trim();
                const cleanText = text.replace(/^[\\*\\s]*\\d+[\\. 、]+\\s*/, '').replace(/[\\*必填]/g, '').trim();
                if (cleanText && !identifiers.includes(cleanText)) identifiers.push(cleanText);
            }}
        }}
        
        // 7. 父元素中的 label 和直接文本
        parent = input.parentElement;
        for (let depth = 0; depth < 8 && parent; depth++) {{
            const labelEl = parent.querySelector('label, .label, [class*="label"]');
            if (labelEl && labelEl !== input) {{
                const text = (labelEl.innerText || labelEl.textContent || '').trim();
                const cleanText = text.replace(/^[\\*\\s]*\\d+[\\. 、]+\\s*/, '').replace(/[\\*必填]/g, '').trim();
                if (cleanText && !identifiers.includes(cleanText)) identifiers.push(cleanText);
            }}
            
            Array.from(parent.childNodes).forEach(node => {{
                if (node.nodeType === Node.TEXT_NODE) {{
                    const text = node.textContent.trim();
                    if (text && text.length > 1 && text.length < 50 && !identifiers.includes(text)) {{
                        identifiers.push(text);
                    }}
                }}
            }});
            
            parent = parent.parentElement;
        }}
        
        // 8. 前置兄弟元素
        let sibling = input.previousElementSibling;
        let siblingCount = 0;
        while (sibling && siblingCount < 3) {{
            const text = (sibling.innerText || sibling.textContent || '').trim();
            const cleanText = text.replace(/^[\\*\\s]*\\d+[\\. 、]+\\s*/, '').replace(/[\\*必填]/g, '').trim();
            if (cleanText && cleanText.length < 80 && !identifiers.includes(cleanText)) {{
                identifiers.push(cleanText);
            }}
            sibling = sibling.previousElementSibling;
            siblingCount++;
        }}
        
        // 9. 向上遍历查找前置兄弟
        parent = input.parentElement;
        for (let depth = 0; depth < 10 && parent; depth++) {{
            const prevSib = parent.previousElementSibling;
            if (prevSib) {{
                const text = (prevSib.innerText || prevSib.textContent || '').trim();
                const cleanText = text.replace(/^[\\*\\s]*\\d+[\\. 、]+\\s*/, '').replace(/[\\*必填]/g, '').trim();
                if (cleanText && cleanText.length > 1 && cleanText.length < 80 && !identifiers.includes(cleanText)) {{
                    identifiers.push(cleanText);
                    break;
                }}
            }}
            parent = parent.parentElement;
        }}
        
        return identifiers;
    }}
    
    // 清理文本用于匹配
    function cleanText(text) {{
        if (!text) return '';
        return String(text)
            .toLowerCase()
            .replace(/[：:*？?！!。.、，,\\s\\-_\\(\\)（）【】\\[\\]]/g, '')
            .trim();
    }}
    
    // 【核心】匹配关键词 - 评分系统
    function matchKeyword(identifiers, keyword) {{
        const cleanKeyword = cleanText(keyword);
        if (!cleanKeyword) return {{ matched: false, identifier: null, score: 0 }};
        
        const subKeywords = keyword.split(/[|,;，；、]/).map(k => cleanText(k)).filter(k => k);
        if (subKeywords.length === 0) subKeywords.push(cleanKeyword);
        
        let bestScore = 0;
        let bestIdentifier = null;
        
        for (const subKey of subKeywords) {{
            for (const identifier of identifiers) {{
                const cleanIdentifier = cleanText(identifier);
                if (!cleanIdentifier) continue;
                
                let currentScore = 0;
                
                if (cleanIdentifier === subKey) {{
                    currentScore = 100;
                }} 
                else if (cleanIdentifier.includes(subKey)) {{
                    const ratio = subKey.length / cleanIdentifier.length;
                    currentScore = 80 + (ratio * 10); 
                }}
                else if (subKey.includes(cleanIdentifier)) {{
                    currentScore = 70;
                }}
                else {{
                    let commonChars = 0;
                    for (const char of subKey) {{
                        if (cleanIdentifier.includes(char)) commonChars++;
                    }}
                    const similarity = commonChars / subKey.length;
                    if (similarity >= 0.5) {{
                        currentScore = Math.floor(similarity * 60);
                    }}
                }}
                
                if (currentScore > bestScore) {{
                    bestScore = currentScore;
                    bestIdentifier = identifier;
                }}
            }}
        }}
        
        return {{ matched: bestScore > 0, identifier: bestIdentifier, score: bestScore }};
    }}
    
    // 填充输入框 - Vue 兼容
    function fillInput(input, value) {{
        input.focus();
        input.value = '';
        input.value = value;
        
        ['input', 'change', 'blur', 'keyup', 'keydown', 'keypress'].forEach(eventName => {{
            input.dispatchEvent(new Event(eventName, {{ bubbles: true, cancelable: true }}));
        }});
        
        try {{
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            if (nativeInputValueSetter) {{
                nativeInputValueSetter.call(input, value);
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }} catch (e) {{}}
        
        try {{
            const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype, 'value'
            ).set;
            if (nativeTextAreaValueSetter && input.tagName === 'TEXTAREA') {{
                nativeTextAreaValueSetter.call(input, value);
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }} catch (e) {{}}
        
        try {{
            input.dispatchEvent(new CompositionEvent('compositionend', {{ bubbles: true, data: value }}));
        }} catch (e) {{}}
        
        input.blur();
    }}
    
    // 主执行函数 - 以输入框为主体，为每个输入框找最佳匹配的名片字段
    async function executeAutoFill() {{
        const hasInputs = await waitForInputs();
        
        if (!hasInputs) {{
            console.warn('⚠️ 未找到任何输入框');
            window.__autoFillResult__ = {{
                fillCount: 0,
                totalCount: fillData.length,
                status: 'completed',
                results: []
            }};
            return;
        }}
        
        console.log('\\n📋 扫描页面输入框...');
        const allInputs = getAllInputs();
        console.log(`找到 ${{allInputs.length}} 个可填写的输入框`);
        
        allInputs.forEach((input, index) => {{
            const identifiers = getInputIdentifiers(input);
            console.log(`\\n输入框 ${{index + 1}}: ${{identifiers.slice(0, 3).join(' | ')}}`);
        }});
        
        console.log('\\n🎯 开始匹配和填写...');
        
        // 以输入框为主体遍历，为每个输入框找最佳匹配的名片字段
        allInputs.forEach((input, index) => {{
            const identifiers = getInputIdentifiers(input);
            let bestMatch = {{ item: null, score: 0, identifier: null }};
            
            // 在所有名片字段中找最佳匹配
            fillData.forEach(item => {{
                const matchResult = matchKeyword(identifiers, item.key);
                if (matchResult.matched && matchResult.score > bestMatch.score) {{
                    bestMatch = {{ item: item, score: matchResult.score, identifier: matchResult.identifier }};
                }}
            }});
            
            // 如果找到匹配且分数足够高，填写
            if (bestMatch.item && bestMatch.score >= 50) {{
                fillInput(input, bestMatch.item.value);
                console.log(`✅ 填写输入框${{index + 1}}: "${{bestMatch.item.key}}" = "${{bestMatch.item.value}}" (匹配: "${{bestMatch.identifier}}", 分数: ${{bestMatch.score}})`);
                fillCount++;
                results.push({{
                    key: bestMatch.item.key,
                    value: bestMatch.item.value,
                    matched: bestMatch.identifier,
                    score: bestMatch.score,
                    success: true
                }});
            }}
        }});
        
        // 记录未匹配的名片字段
        const filledKeys = new Set(results.filter(r => r.success).map(r => r.key));
        fillData.forEach(item => {{
            if (!filledKeys.has(item.key)) {{
                const hasResult = results.some(r => r.key === item.key);
                if (!hasResult) {{
                    console.warn(`⚠️ 名片字段未使用: "${{item.key}}"`);
                    results.push({{
                        key: item.key,
                        value: item.value,
                        matched: null,
                        score: 0,
                        success: false
                    }});
                }}
            }}
        }});
        
        window.__autoFillResult__ = {{
            fillCount: fillCount,
            totalCount: allInputs.length,
            status: 'completed',
            results: results
        }};
        
        console.log(`\\n✅ 问卷网填写完成: ${{fillCount}}/${{allInputs.length}} 个输入框`);
    }}
    
    executeAutoFill();
    return '问卷网填写脚本已执行';
}})();
        """
        return js_code
    
    def generate_fanqier_fill_script(self, fill_data: list) -> str:
        """生成番茄表单(fanqier.cn)专用的填充脚本 - React框架适配"""
        import json
        fill_data_json = json.dumps(fill_data, ensure_ascii=False)
        
        js_code = f"""
(function() {{
    console.log('🍅 开始填写番茄表单...');
    
    const fillData = {fill_data_json};
    let fillCount = 0;
    const results = [];
    
    // 等待React组件和输入框加载完成
    function waitForInputs(maxAttempts = 20, interval = 500) {{
        return new Promise((resolve) => {{
            let attempts = 0;
            const checkInputs = setInterval(() => {{
                const inputs = document.querySelectorAll('input[type="text"], input:not([type]), textarea, .fq-input, .fanqier-input, [class*="input"]');
                attempts++;
                console.log(`🔍 尝试 ${{attempts}}/${{maxAttempts}}: 找到 ${{inputs.length}} 个输入框`);
                
                if (inputs.length > 0 || attempts >= maxAttempts) {{
                    clearInterval(checkInputs);
                    resolve(inputs.length > 0);
                }}
            }}, interval);
        }});
    }}
    
    // 获取所有可见的输入框
    function getAllInputs() {{
        const inputs = [];
        const selectors = [
            'input[type="text"]',
            'input:not([type])',
            'textarea',
            '.fq-input input',
            '.fanqier-input input',
            '[class*="TextInput"] input',
            '[class*="input-wrapper"] input',
            '[contenteditable="true"]'
        ];
        
        document.querySelectorAll(selectors.join(', ')).forEach(input => {{
            const style = window.getComputedStyle(input);
            if (style.display !== 'none' && style.visibility !== 'hidden' && input.offsetParent !== null) {{
                if (!input.disabled && !input.readOnly) {{
                    inputs.push(input);
                }}
            }}
        }});
        return inputs;
    }}
    
    // 获取输入框的所有可能标识
    function getInputIdentifiers(input) {{
        const identifiers = [];
        
        if (input.placeholder) identifiers.push(input.placeholder.trim());
        if (input.name) identifiers.push(input.name.trim());
        if (input.id) identifiers.push(input.id.trim());
        if (input.getAttribute('aria-label')) identifiers.push(input.getAttribute('aria-label').trim());
        
        // 番茄表单特有：查找问题容器
        let parent = input.closest('[class*="question"], [class*="field"], [class*="FormField"], [class*="item"]');
        if (parent) {{
            const titleEl = parent.querySelector('[class*="title"], [class*="label"], label, .question-title');
            if (titleEl) {{
                const text = (titleEl.innerText || titleEl.textContent || '').trim();
                const cleanText = text.replace(/^[\\*\\s]*\\d+[\\. 、]+\\s*/, '').replace(/[\\*必填]/g, '').trim();
                if (cleanText && !identifiers.includes(cleanText)) identifiers.push(cleanText);
            }}
        }}
        
        // 父元素遍历
        parent = input.parentElement;
        for (let depth = 0; depth < 8 && parent; depth++) {{
            const labelEl = parent.querySelector('label, [class*="label"], [class*="title"]');
            if (labelEl && labelEl !== input) {{
                const text = (labelEl.innerText || labelEl.textContent || '').trim();
                const cleanText = text.replace(/^[\\*\\s]*\\d+[\\. 、]+\\s*/, '').replace(/[\\*必填]/g, '').trim();
                if (cleanText && !identifiers.includes(cleanText)) identifiers.push(cleanText);
            }}
            parent = parent.parentElement;
        }}
        
        // 前置兄弟
        let sibling = input.previousElementSibling;
        let count = 0;
        while (sibling && count < 3) {{
            const text = (sibling.innerText || sibling.textContent || '').trim();
            const cleanText = text.replace(/^[\\*\\s]*\\d+[\\. 、]+\\s*/, '').replace(/[\\*必填]/g, '').trim();
            if (cleanText && cleanText.length < 80 && !identifiers.includes(cleanText)) {{
                identifiers.push(cleanText);
            }}
            sibling = sibling.previousElementSibling;
            count++;
        }}
        
        // 向上查找前置兄弟
        parent = input.parentElement;
        for (let depth = 0; depth < 10 && parent; depth++) {{
            const prevSib = parent.previousElementSibling;
            if (prevSib) {{
                const text = (prevSib.innerText || prevSib.textContent || '').trim();
                const cleanText = text.replace(/^[\\*\\s]*\\d+[\\. 、]+\\s*/, '').replace(/[\\*必填]/g, '').trim();
                if (cleanText && cleanText.length > 1 && cleanText.length < 80 && !identifiers.includes(cleanText)) {{
                    identifiers.push(cleanText);
                    break;
                }}
            }}
            parent = parent.parentElement;
        }}
        
        return identifiers;
    }}
    
    function cleanText(text) {{
        if (!text) return '';
        return String(text).toLowerCase().replace(/[：:*？?！!。.、，,\\s\\-_\\(\\)（）【】\\[\\]]/g, '').trim();
    }}
    
    function matchKeyword(identifiers, keyword) {{
        const cleanKeyword = cleanText(keyword);
        if (!cleanKeyword) return {{ matched: false, identifier: null, score: 0 }};
        
        const subKeywords = keyword.split(/[|,;，；、]/).map(k => cleanText(k)).filter(k => k);
        if (subKeywords.length === 0) subKeywords.push(cleanKeyword);
        
        let bestScore = 0;
        let bestIdentifier = null;
        
        for (const subKey of subKeywords) {{
            for (const identifier of identifiers) {{
                const cleanIdentifier = cleanText(identifier);
                if (!cleanIdentifier) continue;
                
                let currentScore = 0;
                if (cleanIdentifier === subKey) currentScore = 100;
                else if (cleanIdentifier.includes(subKey)) currentScore = 80 + (subKey.length / cleanIdentifier.length * 10);
                else if (subKey.includes(cleanIdentifier)) currentScore = 70;
                else {{
                    let common = 0;
                    for (const c of subKey) if (cleanIdentifier.includes(c)) common++;
                    if (common / subKey.length >= 0.5) currentScore = Math.floor(common / subKey.length * 60);
                }}
                
                if (currentScore > bestScore) {{
                    bestScore = currentScore;
                    bestIdentifier = identifier;
                }}
            }}
        }}
        
        return {{ matched: bestScore > 0, identifier: bestIdentifier, score: bestScore }};
    }}
    
    function fillInput(input, value) {{
        input.focus();
        input.value = '';
        input.value = value;
        
        ['input', 'change', 'blur', 'keyup', 'keydown'].forEach(e => {{
            input.dispatchEvent(new Event(e, {{ bubbles: true, cancelable: true }}));
        }});
        
        try {{
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            if (setter) {{ setter.call(input, value); input.dispatchEvent(new Event('input', {{ bubbles: true }})); }}
        }} catch (e) {{}}
        
        try {{ input.dispatchEvent(new CompositionEvent('compositionend', {{ bubbles: true, data: value }})); }} catch (e) {{}}
        
        input.blur();
    }}
    
    // 主执行函数 - 以输入框为主体，为每个输入框找最佳匹配的名片字段
    async function executeAutoFill() {{
        const hasInputs = await waitForInputs();
        if (!hasInputs) {{
            window.__autoFillResult__ = {{ fillCount: 0, totalCount: fillData.length, status: 'completed', results: [] }};
            return;
        }}
        
        const allInputs = getAllInputs();
        console.log(`找到 ${{allInputs.length}} 个输入框`);
        
        // 以输入框为主体遍历，为每个输入框找最佳匹配的名片字段
        allInputs.forEach((input, index) => {{
            const identifiers = getInputIdentifiers(input);
            let bestMatch = {{ item: null, score: 0, identifier: null }};
            
            // 在所有名片字段中找最佳匹配
            fillData.forEach(item => {{
                const matchResult = matchKeyword(identifiers, item.key);
                if (matchResult.matched && matchResult.score > bestMatch.score) {{
                    bestMatch = {{ item: item, score: matchResult.score, identifier: matchResult.identifier }};
                }}
            }});
            
            // 如果找到匹配且分数足够高，填写
            if (bestMatch.item && bestMatch.score >= 50) {{
                fillInput(input, bestMatch.item.value);
                console.log(`✅ 填写输入框${{index + 1}}: "${{bestMatch.item.key}}" = "${{bestMatch.item.value}}"`);
                fillCount++;
                results.push({{ key: bestMatch.item.key, value: bestMatch.item.value, matched: bestMatch.identifier, score: bestMatch.score, success: true }});
            }}
        }});
        
        // 记录未匹配的名片字段
        const filledKeys = new Set(results.filter(r => r.success).map(r => r.key));
        fillData.forEach(item => {{
            if (!filledKeys.has(item.key)) {{
                const hasResult = results.some(r => r.key === item.key);
                if (!hasResult) {{
                    console.warn(`⚠️ 名片字段未使用: "${{item.key}}"`);
                    results.push({{ key: item.key, value: item.value, matched: null, score: 0, success: false }});
                }}
            }}
        }});
        
        window.__autoFillResult__ = {{ fillCount, totalCount: allInputs.length, status: 'completed', results }};
        console.log(`✅ 番茄表单填写完成: ${{fillCount}}/${{allInputs.length}} 个输入框`);
    }}
    
    executeAutoFill();
    return '番茄表单填写脚本已执行';
}})();
        """
        return js_code
    
    def generate_feishu_fill_script(self, fill_data: list) -> str:
        """生成飞书问卷(feishu.cn)专用的填充脚本 - 富文本编辑器适配"""
        import json
        fill_data_json = json.dumps(fill_data, ensure_ascii=False)
        
        js_code = f"""
(function() {{
    console.log('🐦 开始填写飞书问卷...');
    
    const fillData = {fill_data_json};
    let fillCount = 0;
    const results = [];
    
    // 等待飞书表单加载完成
    function waitForForm(maxAttempts = 25, interval = 400) {{
        return new Promise((resolve) => {{
            let attempts = 0;
            const checkForm = setInterval(() => {{
                // 飞书问卷的字段卡片
                const cardItems = document.querySelectorAll('.base-form-container_card_item');
                attempts++;
                console.log(`🔍 尝试 ${{attempts}}/${{maxAttempts}}: 找到 ${{cardItems.length}} 个字段卡片`);
                
                if (cardItems.length > 0 || attempts >= maxAttempts) {{
                    clearInterval(checkForm);
                    resolve(cardItems.length > 0);
                }}
            }}, interval);
        }});
    }}
    
    // 获取所有字段信息（标题 + 编辑器）
    function getAllFields() {{
        const fields = [];
        
        // 飞书问卷使用 .base-form-container_card_item 作为字段容器
        document.querySelectorAll('.base-form-container_card_item').forEach((card, index) => {{
            // 获取字段标题
            const titleEl = card.querySelector('.base-form-container_title_wrapper span');
            const title = titleEl ? titleEl.innerText.trim() : '';
            
            // 获取可编辑的富文本区域（contenteditable="true"）
            const editor = card.querySelector('[contenteditable="true"].adit-container');
            
            if (title && editor) {{
                fields.push({{
                    index: index,
                    title: title,
                    editor: editor,
                    card: card
                }});
                console.log(`  字段 ${{index + 1}}: "${{title}}"`);
            }}
        }});
        
        return fields;
    }}
    
    // 清理文本用于匹配
    function cleanText(text) {{
        if (!text) return '';
        return String(text).toLowerCase().replace(/[：:*？?！!。.、，,\\s\\-_\\(\\)（）【】\\[\\]]/g, '').trim();
    }}
    
    // 匹配关键词 - 评分系统
    function matchKeyword(fieldTitle, keyword) {{
        const cleanTitle = cleanText(fieldTitle);
        const cleanKeyword = cleanText(keyword);
        
        if (!cleanKeyword || !cleanTitle) return {{ matched: false, score: 0 }};
        
        // 支持顿号、逗号、竖线分隔的多个关键词
        const subKeywords = keyword.split(/[|,;，；、]/).map(k => cleanText(k)).filter(k => k);
        if (subKeywords.length === 0) subKeywords.push(cleanKeyword);
        
        let bestScore = 0;
        
        for (const subKey of subKeywords) {{
            let currentScore = 0;
            
            // 完全匹配
            if (cleanTitle === subKey) {{
                currentScore = 100;
            }}
            // 包含匹配
            else if (cleanTitle.includes(subKey)) {{
                currentScore = 80 + (subKey.length / cleanTitle.length * 15);
            }}
            else if (subKey.includes(cleanTitle)) {{
                currentScore = 75;
            }}
            // 字符相似度匹配
            else {{
                let common = 0;
                for (const c of subKey) {{
                    if (cleanTitle.includes(c)) common++;
                }}
                const similarity = common / subKey.length;
                if (similarity >= 0.5) {{
                    currentScore = Math.floor(similarity * 60);
                }}
            }}
            
            if (currentScore > bestScore) {{
                bestScore = currentScore;
            }}
        }}
        
        return {{ matched: bestScore >= 50, score: bestScore }};
    }}
    
    // 填充富文本编辑器
    function fillEditor(editor, value) {{
        try {{
            // 聚焦编辑器
            editor.focus();
            
            // 清空现有内容
            editor.innerHTML = '';
            
            // 创建飞书编辑器的内容结构
            const lineDiv = document.createElement('div');
            lineDiv.setAttribute('data-node', 'true');
            lineDiv.className = 'ace-line wrapper';
            
            const wrapperDiv = document.createElement('div');
            wrapperDiv.setAttribute('data-line-wrapper', 'true');
            wrapperDiv.setAttribute('dir', 'auto');
            
            const span1 = document.createElement('span');
            span1.className = '';
            span1.setAttribute('data-leaf', 'true');
            
            const textSpan = document.createElement('span');
            textSpan.setAttribute('data-string', 'true');
            textSpan.textContent = value;
            
            span1.appendChild(textSpan);
            wrapperDiv.appendChild(span1);
            lineDiv.appendChild(wrapperDiv);
            editor.appendChild(lineDiv);
            
            // 触发输入事件
            editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
            editor.dispatchEvent(new Event('change', {{ bubbles: true }}));
            editor.dispatchEvent(new Event('blur', {{ bubbles: true }}));
            
            // 模拟键盘输入完成
            editor.dispatchEvent(new CompositionEvent('compositionend', {{ bubbles: true, data: value }}));
            
            console.log(`    ✅ 已填入: "${{value}}"`);
            return true;
        }} catch (e) {{
            console.error(`    ❌ 填充失败: ${{e.message}}`);
            return false;
        }}
    }}
    
    // 主执行函数 - 以字段为主体，为每个字段找最佳匹配的名片数据
    async function executeAutoFill() {{
        const hasForm = await waitForForm();
        
        if (!hasForm) {{
            console.warn('⚠️ 未找到飞书问卷表单');
            window.__autoFillResult__ = {{
                fillCount: 0,
                totalCount: fillData.length,
                status: 'completed',
                results: []
            }};
            return;
        }}
        
        console.log('\\n📋 扫描飞书问卷字段...');
        const allFields = getAllFields();
        console.log(`找到 ${{allFields.length}} 个可填写字段`);
        
        console.log('\\n🎯 开始匹配和填写...');
        
        // 以字段为主体遍历，为每个字段找最佳匹配的名片数据
        allFields.forEach((field, index) => {{
            let bestMatch = {{ item: null, score: 0 }};
            
            // 在所有名片字段中找最佳匹配
            fillData.forEach(item => {{
                const matchResult = matchKeyword(field.title, item.key);
                if (matchResult.matched && matchResult.score > bestMatch.score) {{
                    bestMatch = {{ item: item, score: matchResult.score }};
                }}
            }});
            
            // 如果找到匹配且分数足够高，填写
            if (bestMatch.item && bestMatch.score >= 50) {{
                const success = fillEditor(field.editor, bestMatch.item.value);
                if (success) {{
                    console.log(`✅ 填写字段${{index + 1}}: "${{bestMatch.item.key}}" -> "${{field.title}}" (分数: ${{bestMatch.score}})`);
                    fillCount++;
                    results.push({{
                        key: bestMatch.item.key,
                        value: bestMatch.item.value,
                        matched: field.title,
                        score: bestMatch.score,
                        success: true
                    }});
                }}
            }}
        }});
        
        // 记录未匹配的名片字段
        const filledKeys = new Set(results.filter(r => r.success).map(r => r.key));
        fillData.forEach(item => {{
            if (!filledKeys.has(item.key)) {{
                const hasResult = results.some(r => r.key === item.key);
                if (!hasResult) {{
                    console.warn(`⚠️ 名片字段未使用: "${{item.key}}"`);
                    results.push({{
                        key: item.key,
                        value: item.value,
                        matched: null,
                        score: 0,
                        success: false
                    }});
                }}
            }}
        }});
        
        window.__autoFillResult__ = {{
            fillCount: fillCount,
            totalCount: allFields.length,
            status: 'completed',
            results: results
        }};
        
        console.log(`\\n✅ 飞书问卷填写完成: ${{fillCount}}/${{allFields.length}} 个字段`);
    }}
    
    executeAutoFill();
    return '飞书问卷填写脚本已执行';
}})();
        """
        return js_code
    
    def generate_kdocs_fill_script(self, fill_data: list) -> str:
        """生成WPS表单(kdocs.cn)专用的填充脚本 - React框架适配"""
        import json
        fill_data_json = json.dumps(fill_data, ensure_ascii=False)
        
        js_code = f"""
(function() {{
    console.log('📝 开始填写WPS表单...');
    
    const fillData = {fill_data_json};
    let fillCount = 0;
    const results = [];
    
    function waitForInputs(maxAttempts = 20, interval = 500) {{
        return new Promise((resolve) => {{
            let attempts = 0;
            const checkInputs = setInterval(() => {{
                const inputs = document.querySelectorAll('input[type="text"], input:not([type]), textarea, [class*="input"] input, [class*="Input"] input');
                attempts++;
                console.log(`🔍 尝试 ${{attempts}}/${{maxAttempts}}: 找到 ${{inputs.length}} 个输入框`);
                
                if (inputs.length > 0 || attempts >= maxAttempts) {{
                    clearInterval(checkInputs);
                    resolve(inputs.length > 0);
                }}
            }}, interval);
        }});
    }}
    
    function getAllInputs() {{
        const inputs = [];
        const selectors = [
            'input[type="text"]',
            'input:not([type])',
            'textarea',
            '[class*="input"] input',
            '[class*="Input"] input',
            '[class*="text-input"] input',
            '[contenteditable="true"]'
        ];
        
        document.querySelectorAll(selectors.join(', ')).forEach(input => {{
            const style = window.getComputedStyle(input);
            if (style.display !== 'none' && style.visibility !== 'hidden' && input.offsetParent !== null) {{
                if (!input.disabled && !input.readOnly) {{
                    inputs.push(input);
                }}
            }}
        }});
        return inputs;
    }}
    
    function getInputIdentifiers(input) {{
        const identifiers = [];
        
        if (input.placeholder) identifiers.push(input.placeholder.trim());
        if (input.name) identifiers.push(input.name.trim());
        if (input.id) identifiers.push(input.id.trim());
        if (input.getAttribute('aria-label')) identifiers.push(input.getAttribute('aria-label').trim());
        
        // WPS特有：查找问题容器
        let parent = input.closest('[class*="question"], [class*="field"], [class*="form-item"], [class*="FormField"], [class*="container"]');
        if (parent) {{
            const titleEl = parent.querySelector('[class*="title"], [class*="label"], label, [class*="question-text"]');
            if (titleEl) {{
                const text = (titleEl.innerText || titleEl.textContent || '').trim();
                const cleanText = text.replace(/^[\\*\\s]*\\d+[\\. 、]+\\s*/, '').replace(/[\\*必填]/g, '').trim();
                if (cleanText && !identifiers.includes(cleanText)) identifiers.push(cleanText);
            }}
        }}
        
        // ksapc-theme-back 容器特殊处理
        parent = input.closest('.ksapc-theme-back, [class*="container"]');
        if (parent) {{
            const fullText = parent.innerText || '';
            // 匹配 "1.小红书账号" 这种格式
            const matches = fullText.match(/\\d+\\.([^\\d]+?)(?=\\d+\\.|提|$)/g);
            if (matches) {{
                matches.forEach(m => {{
                    const cleanM = m.replace(/^\\d+\\.\\s*/, '').trim();
                    if (cleanM && cleanM.length < 50 && !identifiers.includes(cleanM)) identifiers.push(cleanM);
                }});
            }}
        }}
        
        // 父元素遍历
        parent = input.parentElement;
        for (let depth = 0; depth < 8 && parent; depth++) {{
            const labelEl = parent.querySelector('label, [class*="label"], [class*="title"]');
            if (labelEl && labelEl !== input) {{
                const text = (labelEl.innerText || labelEl.textContent || '').trim();
                const cleanText = text.replace(/^[\\*\\s]*\\d+[\\. 、]+\\s*/, '').replace(/[\\*必填]/g, '').trim();
                if (cleanText && !identifiers.includes(cleanText)) identifiers.push(cleanText);
            }}
            parent = parent.parentElement;
        }}
        
        // 前置兄弟
        let sibling = input.previousElementSibling;
        let count = 0;
        while (sibling && count < 3) {{
            const text = (sibling.innerText || sibling.textContent || '').trim();
            const cleanText = text.replace(/^[\\*\\s]*\\d+[\\. 、]+\\s*/, '').replace(/[\\*必填]/g, '').trim();
            if (cleanText && cleanText.length < 80 && !identifiers.includes(cleanText)) {{
                identifiers.push(cleanText);
            }}
            sibling = sibling.previousElementSibling;
            count++;
        }}
        
        // 向上查找前置兄弟
        parent = input.parentElement;
        for (let depth = 0; depth < 10 && parent; depth++) {{
            const prevSib = parent.previousElementSibling;
            if (prevSib) {{
                const text = (prevSib.innerText || prevSib.textContent || '').trim();
                const cleanText = text.replace(/^[\\*\\s]*\\d+[\\. 、]+\\s*/, '').replace(/[\\*必填]/g, '').trim();
                if (cleanText && cleanText.length > 1 && cleanText.length < 80 && !identifiers.includes(cleanText)) {{
                    identifiers.push(cleanText);
                    break;
                }}
            }}
            parent = parent.parentElement;
        }}
        
        return identifiers;
    }}
    
    function cleanText(text) {{
        if (!text) return '';
        return String(text).toLowerCase().replace(/[：:*？?！!。.、，,\\s\\-_\\(\\)（）【】\\[\\]]/g, '').trim();
    }}
    
    function matchKeyword(identifiers, keyword) {{
        const cleanKeyword = cleanText(keyword);
        if (!cleanKeyword) return {{ matched: false, identifier: null, score: 0 }};
        
        const subKeywords = keyword.split(/[|,;，；、]/).map(k => cleanText(k)).filter(k => k);
        if (subKeywords.length === 0) subKeywords.push(cleanKeyword);
        
        let bestScore = 0;
        let bestIdentifier = null;
        
        for (const subKey of subKeywords) {{
            for (const identifier of identifiers) {{
                const cleanIdentifier = cleanText(identifier);
                if (!cleanIdentifier) continue;
                
                let currentScore = 0;
                if (cleanIdentifier === subKey) currentScore = 100;
                else if (cleanIdentifier.includes(subKey)) currentScore = 80 + (subKey.length / cleanIdentifier.length * 10);
                else if (subKey.includes(cleanIdentifier)) currentScore = 70;
                else {{
                    let common = 0;
                    for (const c of subKey) if (cleanIdentifier.includes(c)) common++;
                    if (common / subKey.length >= 0.5) currentScore = Math.floor(common / subKey.length * 60);
                }}
                
                if (currentScore > bestScore) {{
                    bestScore = currentScore;
                    bestIdentifier = identifier;
                }}
            }}
        }}
        
        return {{ matched: bestScore > 0, identifier: bestIdentifier, score: bestScore }};
    }}
    
    function fillInput(input, value) {{
        input.focus();
        input.value = '';
        input.value = value;
        
        ['input', 'change', 'blur', 'keyup', 'keydown'].forEach(e => {{
            input.dispatchEvent(new Event(e, {{ bubbles: true, cancelable: true }}));
        }});
        
        try {{
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            if (setter) {{ setter.call(input, value); input.dispatchEvent(new Event('input', {{ bubbles: true }})); }}
        }} catch (e) {{}}
        
        try {{ input.dispatchEvent(new CompositionEvent('compositionend', {{ bubbles: true, data: value }})); }} catch (e) {{}}
        
        input.blur();
    }}
    
    // 主执行函数 - 以输入框为主体，为每个输入框找最佳匹配的名片字段
    async function executeAutoFill() {{
        const hasInputs = await waitForInputs();
        if (!hasInputs) {{
            window.__autoFillResult__ = {{ fillCount: 0, totalCount: fillData.length, status: 'completed', results: [] }};
            return;
        }}
        
        const allInputs = getAllInputs();
        console.log(`找到 ${{allInputs.length}} 个输入框`);
        
        // 以输入框为主体遍历，为每个输入框找最佳匹配的名片字段
        allInputs.forEach((input, index) => {{
            const identifiers = getInputIdentifiers(input);
            let bestMatch = {{ item: null, score: 0, identifier: null }};
            
            // 在所有名片字段中找最佳匹配
            fillData.forEach(item => {{
                const matchResult = matchKeyword(identifiers, item.key);
                if (matchResult.matched && matchResult.score > bestMatch.score) {{
                    bestMatch = {{ item: item, score: matchResult.score, identifier: matchResult.identifier }};
                }}
            }});
            
            // 如果找到匹配且分数足够高，填写
            if (bestMatch.item && bestMatch.score >= 50) {{
                fillInput(input, bestMatch.item.value);
                console.log(`✅ 填写输入框${{index + 1}}: "${{bestMatch.item.key}}" = "${{bestMatch.item.value}}"`);
                fillCount++;
                results.push({{ key: bestMatch.item.key, value: bestMatch.item.value, matched: bestMatch.identifier, score: bestMatch.score, success: true }});
            }}
        }});
        
        // 记录未匹配的名片字段
        const filledKeys = new Set(results.filter(r => r.success).map(r => r.key));
        fillData.forEach(item => {{
            if (!filledKeys.has(item.key)) {{
                const hasResult = results.some(r => r.key === item.key);
                if (!hasResult) {{
                    console.warn(`⚠️ 名片字段未使用: "${{item.key}}"`);
                    results.push({{ key: item.key, value: item.value, matched: null, score: 0, success: false }});
                }}
            }}
        }});
        
        window.__autoFillResult__ = {{ fillCount, totalCount: allInputs.length, status: 'completed', results }};
        console.log(`✅ WPS表单填写完成: ${{fillCount}}/${{allInputs.length}} 个输入框`);
    }}
    
    executeAutoFill();
    return 'WPS表单填写脚本已执行';
}})();
        """
        return js_code
    
    def generate_tencent_wj_fill_script(self, fill_data: list) -> str:
        """生成腾讯问卷(wj.qq.com)专用的填充脚本"""
        import json
        fill_data_json = json.dumps(fill_data, ensure_ascii=False)
        
        js_code = f"""
(function() {{
    console.log('🐧 开始填写腾讯问卷...');
    
    const fillData = {fill_data_json};
    let fillCount = 0;
    const results = [];
    
    // 等待问卷加载完成
    function waitForForm(maxAttempts = 20, interval = 400) {{
        return new Promise((resolve) => {{
            let attempts = 0;
            const checkForm = setInterval(() => {{
                // 腾讯问卷的问题容器
                const questions = document.querySelectorAll('.question');
                attempts++;
                console.log(`🔍 尝试 ${{attempts}}/${{maxAttempts}}: 找到 ${{questions.length}} 个问题`);
                
                if (questions.length > 0 || attempts >= maxAttempts) {{
                    clearInterval(checkForm);
                    resolve(questions.length > 0);
                }}
            }}, interval);
        }});
    }}
    
    // 获取所有问题字段
    function getAllFields() {{
        const fields = [];
        
        // 腾讯问卷使用 .question 作为问题容器
        document.querySelectorAll('.question').forEach((question, index) => {{
            // 获取问题标题 - 在 .question-title .text .pe-line 中
            const titleEl = question.querySelector('.question-title .text .pe-line');
            const title = titleEl ? titleEl.innerText.trim() : '';
            
            // 获取输入框 - .inputs-input
            const input = question.querySelector('.inputs-input');
            
            if (title && input) {{
                fields.push({{
                    index: index,
                    title: title,
                    input: input,
                    question: question
                }});
                console.log(`  字段 ${{index + 1}}: "${{title}}"`);
            }}
        }});
        
        return fields;
    }}
    
    // 清理文本用于匹配
    function cleanText(text) {{
        if (!text) return '';
        return String(text).toLowerCase().replace(/[：:*？?！!。.、，,\\s\\-_\\(\\)（）【】\\[\\]小红书]/g, '').trim();
    }}
    
    // 匹配关键词 - 评分系统
    function matchKeyword(fieldTitle, keyword) {{
        const cleanTitle = cleanText(fieldTitle);
        const cleanKeyword = cleanText(keyword);
        
        if (!cleanKeyword || !cleanTitle) return {{ matched: false, score: 0 }};
        
        // 支持顿号、逗号、竖线分隔的多个关键词
        const subKeywords = keyword.split(/[|,;，；、]/).map(k => cleanText(k)).filter(k => k);
        if (subKeywords.length === 0) subKeywords.push(cleanKeyword);
        
        let bestScore = 0;
        
        for (const subKey of subKeywords) {{
            let currentScore = 0;
            
            // 完全匹配
            if (cleanTitle === subKey) {{
                currentScore = 100;
            }}
            // 包含匹配
            else if (cleanTitle.includes(subKey)) {{
                currentScore = 80 + (subKey.length / cleanTitle.length * 15);
            }}
            else if (subKey.includes(cleanTitle)) {{
                currentScore = 75;
            }}
            // 字符相似度匹配
            else {{
                let common = 0;
                for (const c of subKey) {{
                    if (cleanTitle.includes(c)) common++;
                }}
                const similarity = common / subKey.length;
                if (similarity >= 0.5) {{
                    currentScore = Math.floor(similarity * 60);
                }}
            }}
            
            if (currentScore > bestScore) {{
                bestScore = currentScore;
            }}
        }}
        
        return {{ matched: bestScore >= 50, score: bestScore }};
    }}
    
    // 填充输入框
    function fillInput(input, value) {{
        try {{
            input.focus();
            input.value = '';
            input.value = value;
            
            // 触发事件
            ['input', 'change', 'blur', 'keyup', 'keydown'].forEach(e => {{
                input.dispatchEvent(new Event(e, {{ bubbles: true, cancelable: true }}));
            }});
            
            // React 兼容
            try {{
                const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                if (setter) {{
                    setter.call(input, value);
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
            }} catch (e) {{}}
            
            input.blur();
            console.log(`    ✅ 已填入: "${{value}}"`);
            return true;
        }} catch (e) {{
            console.error(`    ❌ 填充失败: ${{e.message}}`);
            return false;
        }}
    }}
    
    // 主执行函数 - 以字段为主体，为每个字段找最佳匹配的名片数据
    async function executeAutoFill() {{
        const hasForm = await waitForForm();
        
        if (!hasForm) {{
            console.warn('⚠️ 未找到腾讯问卷表单');
            window.__autoFillResult__ = {{
                fillCount: 0,
                totalCount: fillData.length,
                status: 'completed',
                results: []
            }};
            return;
        }}
        
        console.log('\\n📋 扫描腾讯问卷字段...');
        const allFields = getAllFields();
        console.log(`找到 ${{allFields.length}} 个可填写字段`);
        
        console.log('\\n🎯 开始匹配和填写...');
        
        // 以字段为主体遍历，为每个字段找最佳匹配的名片数据
        allFields.forEach((field, index) => {{
            let bestMatch = {{ item: null, score: 0 }};
            
            // 在所有名片字段中找最佳匹配
            fillData.forEach(item => {{
                const matchResult = matchKeyword(field.title, item.key);
                if (matchResult.matched && matchResult.score > bestMatch.score) {{
                    bestMatch = {{ item: item, score: matchResult.score }};
                }}
            }});
            
            // 如果找到匹配且分数足够高，填写
            if (bestMatch.item && bestMatch.score >= 50) {{
                const success = fillInput(field.input, bestMatch.item.value);
                if (success) {{
                    console.log(`✅ 填写字段${{index + 1}}: "${{bestMatch.item.key}}" -> "${{field.title}}" (分数: ${{bestMatch.score}})`);
                    fillCount++;
                    results.push({{
                        key: bestMatch.item.key,
                        value: bestMatch.item.value,
                        matched: field.title,
                        score: bestMatch.score,
                        success: true
                    }});
                }}
            }}
        }});
        
        // 记录未匹配的名片字段
        const filledKeys = new Set(results.filter(r => r.success).map(r => r.key));
        fillData.forEach(item => {{
            if (!filledKeys.has(item.key)) {{
                const hasResult = results.some(r => r.key === item.key);
                if (!hasResult) {{
                    console.warn(`⚠️ 名片字段未使用: "${{item.key}}"`);
                    results.push({{
                        key: item.key,
                        value: item.value,
                        matched: null,
                        score: 0,
                        success: false
                    }});
                }}
            }}
        }});
        
        window.__autoFillResult__ = {{
            fillCount: fillCount,
            totalCount: allFields.length,
            status: 'completed',
            results: results
        }};
        
        console.log(`\\n✅ 腾讯问卷填写完成: ${{fillCount}}/${{allFields.length}} 个字段`);
    }}
    
    executeAutoFill();
    return '腾讯问卷填写脚本已执行';
}})();
        """
        return js_code
    
    def get_fill_result(self, web_view: QWebEngineView, card, form_type: str):
        """获取填写结果"""
        # 根据表单类型选择结果获取脚本
        if form_type == 'tencent_docs':
            get_result_script = self.tencent_docs_engine.generate_get_result_script()
        elif form_type == 'wjx':
            # 问卷星使用自定义结果获取脚本
            get_result_script = "(function() { return window.__autoFillResult__ || {status: 'waiting'}; })();"
        elif form_type == 'jinshuju':
            # 金数据使用自定义结果获取脚本
            get_result_script = "(function() { return window.__autoFillResult__ || {status: 'waiting'}; })();"
        elif form_type == 'shimo':
            # 石墨文档使用自定义结果获取脚本
            get_result_script = "(function() { return window.__autoFillResult__ || {status: 'waiting'}; })();"
        elif form_type == 'credamo':
            # 见数使用自定义结果获取脚本
            get_result_script = "(function() { return window.__autoFillResult__ || {status: 'waiting'}; })();"
        elif form_type == 'wenjuan':
            # 问卷网使用自定义结果获取脚本
            get_result_script = "(function() { return window.__autoFillResult__ || {status: 'waiting'}; })();"
        elif form_type == 'fanqier':
            # 番茄表单使用自定义结果获取脚本
            get_result_script = "(function() { return window.__autoFillResult__ || {status: 'waiting'}; })();"
        elif form_type == 'feishu':
            # 飞书问卷使用自定义结果获取脚本
            get_result_script = "(function() { return window.__autoFillResult__ || {status: 'waiting'}; })();"
        elif form_type == 'kdocs':
            # WPS表单使用自定义结果获取脚本
            get_result_script = "(function() { return window.__autoFillResult__ || {status: 'waiting'}; })();"
        elif form_type == 'tencent_wj':
            # 腾讯问卷使用自定义结果获取脚本
            get_result_script = "(function() { return window.__autoFillResult__ || {status: 'waiting'}; })();"
        else:
            get_result_script = self.auto_fill_engine.generate_get_result_script()
        
        def handle_result(result):
            link_data = web_view.property("link_data")
            
            if result and isinstance(result, dict):
                if result.get('status') == 'waiting' or result.get('status') == 'filling':
                    QTimer.singleShot(2000, lambda: self.get_fill_result(web_view, card, form_type))
                    return
                
                if form_type == 'tencent_docs':
                    filled = result.get('filled', [])
                    failed = result.get('failed', [])
                    fill_count = len(filled)
                    total_count = len(filled) + len(failed)
                else:
                    # 问卷星和麦客CRM使用相同的结果格式
                    fill_count = result.get('fillCount', 0)
                    total_count = result.get('totalCount', 0)
                
                # 保存记录
                self.db_manager.create_fill_record(
                    card.id,
                    link_data.id,
                    fill_count,
                    total_count,
                    success=(fill_count > 0)
                )
                
                # 填写成功后增加使用次数
                if fill_count > 0 and self.current_user:
                    from core.auth import increment_usage_count
                    increment_usage_count(self.current_user)
                
                web_view.setProperty("status", "filled")
                print(f"✅ {card.name}: 填写 {fill_count}/{total_count} 个字段")
                
                # 检查是否所有填写完成
                self.check_all_fills_completed()
        
        web_view.page().runJavaScript(get_result_script, handle_result)
    
    def check_all_fills_completed(self):
        """检查是否所有填写完成"""
        current_index = self.tab_widget.currentIndex()
        if current_index <= 0: # 0是首页
            return
        
        # 实际索引
        real_index = current_index - 1
        if real_index >= len(self.selected_links):
            return
            
        current_link = self.selected_links[real_index]
        webview_infos = self.web_views_by_link.get(str(current_link.id), [])
        
        # 收集所有WebView的状态
        all_completed = True
        success_count = 0
        failed_count = 0
        
        for info in webview_infos:
            if info['web_view']:
                status = info['web_view'].property("status")
                if status == "filled":
                    success_count += 1
                elif status in ["failed", "unknown_type"]:
                    failed_count += 1
                else:
                    all_completed = False
                    break
        
        if all_completed and (success_count + failed_count) > 0:
            self.fill_completed.emit()
            
            total = success_count + failed_count
            print(f"\n{'='*60}")
            print(f"✅ 所有表单填写完成！成功: {success_count}/{total}")
            print(f"{'='*60}\n")
            
            # 自动填充完成后不弹窗，避免打断用户
            # QMessageBox.information(
            #     self,
            #     "完成",
            #     f"所有名片填写完成！\n\n"
            #     f"成功: {success_count}\n"
            #     f"失败: {failed_count}\n"
            #     f"总计: {total} 个表单"
            # )


class EditFieldRow(QWidget):
    """编辑字段行组件 - 按原型图设计"""
    def __init__(self, key="", value="", parent_window=None):
        super().__init__()
        self.parent_window = parent_window
        self.init_ui(key, value)
        
    def init_ui(self, key, value):
        # 主容器 - 改回单行布局，符合设计图
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10) # 增加间距
        self.setLayout(layout)
        
        # 字段名输入框
        self.key_input = QLineEdit(key)
        self.key_input.setPlaceholderText("昵称")
        self.key_input.setFixedHeight(36) # 增加高度
        self.key_input.setMinimumWidth(100) # 设置最小宽度
        self.key_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 0 10px;
                font-size: 13px;
                background: white;
                color: #333;
            }}
            QLineEdit:focus {{
                border: 1px solid {COLORS['primary']};
                background: #FDFDFD;
            }}
        """)
        layout.addWidget(self.key_input, 3) # 占比改为3
        
        # 加号按钮
        plus_btn = QPushButton()
        plus_btn.setIcon(Icons.add('#999999'))
        plus_btn.setIconSize(QSize(12, 12))
        plus_btn.setFixedSize(24, 36) # 高度与输入框一致
        plus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        plus_btn.setStyleSheet(f"""
            QPushButton {{
                border: none;
                background: transparent;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background: #F0F0F0;
            }}
        """)
        plus_btn.clicked.connect(self.append_key_segment)
        layout.addWidget(plus_btn)
        
        # 字段值输入框
        self.value_input = QLineEdit(value)
        self.value_input.setPlaceholderText("值")
        self.value_input.setFixedHeight(36) # 增加高度
        self.value_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 0 10px;
                font-size: 13px;
                background: white;
                color: #333;
            }}
            QLineEdit:focus {{
                border: 1px solid {COLORS['primary']};
                background: #FDFDFD;
            }}
        """)
        layout.addWidget(self.value_input, 4) # 占比改为4
        
        # 复制按钮
        copy_btn = QPushButton("复制")
        copy_btn.setFixedSize(56, 36) # 增加宽度和高度
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background: white;
                color: #666;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                font-size: 12px;
                padding: 0;
            }}
            QPushButton:hover {{
                color: {COLORS['primary']};
                border-color: {COLORS['primary']};
                background: #F9F9F9;
            }}
        """)
        copy_btn.clicked.connect(lambda: self.copy_value())
        layout.addWidget(copy_btn)
        
    def copy_value(self):
        """复制字段值到剪贴板"""
        value = self.value_input.text()
        if value:
            clipboard = QApplication.clipboard()
            clipboard.setText(value)
            print(f"已复制: {value}")
            
    def append_key_segment(self):
        """追加字段名片段"""
        text, ok = QInputDialog.getText(
            self,
            "新增字段别名",
            "请输入要追加的别名（将自动用顿号拼接）:",
            QLineEdit.EchoMode.Normal,
            ""
        )
        
        if ok and text.strip():
            current_val = self.key_input.text().strip()
            new_segment = text.strip()
            
            if current_val:
                # 使用中文顿号拼接
                new_val = f"{current_val}、{new_segment}"
            else:
                new_val = new_segment
                
            self.key_input.setText(new_val)
        
    def get_data(self):
        return self.key_input.text().strip(), self.value_input.text().strip()
