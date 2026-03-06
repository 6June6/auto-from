"""
新的开始填充页面 - 符合设计图2
支持多名片、多链接的填充，带标签页切换
"""
from PyQt6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QComboBox, QMessageBox, QFrame, QScrollArea,
                             QGraphicsDropShadowEffect, QApplication, QTabWidget,
                             QGridLayout, QSizePolicy, QStackedWidget, QLineEdit, QInputDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QUrl, QSize, QEvent, QPoint, QObject
from PyQt6.QtGui import QColor
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from .icons import safe_qta_icon as qta_icon
import json
import time
from collections import defaultdict
from database import DatabaseManager
from core import AutoFillEngineV2, TencentDocsFiller
from .baoming_tool_window import BaomingToolWindow
from .styles import COLORS
from .icons import Icons
import config


class ElidedLabel(QLabel):
    """支持自动省略的标签"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._full_text = text

    def setText(self, text):
        self._full_text = text
        self._update_elided_text()
        
    def resizeEvent(self, event):
        self._update_elided_text()
        super().resizeEvent(event)

    def _update_elided_text(self):
        font_metrics = self.fontMetrics()
        width = self.width()
        # 留出一点余量防止抖动
        if width <= 0: return
        
        elided = font_metrics.elidedText(self._full_text, Qt.TextElideMode.ElideRight, width)
        # 只有文本变化时才更新，避免循环
        if super().text() != elided:
            super().setText(elided)


class ClipboardWebPage(QWebEnginePage):
    """自定义 WebEnginePage - 监听 JavaScript 控制台消息来处理剪贴板操作"""
    
    COPY_PREFIX = "__CLIPBOARD_COPY__:"
    
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        """拦截 JavaScript 控制台消息，处理剪贴板操作"""
        if message.startswith(self.COPY_PREFIX):
            # 提取要复制的文本
            text = message[len(self.COPY_PREFIX):]
            if text:
                clipboard = QApplication.clipboard()
                clipboard.setText(text)
                print(f"[剪贴板] 已复制: {text[:50]}..." if len(text) > 50 else f"[剪贴板] 已复制: {text}")
            return
        # 其他消息正常输出（可选）
        # super().javaScriptConsoleMessage(level, message, lineNumber, sourceID)


class ChineseContextWebView(QWebEngineView):
    """自定义 WebView - 禁用右键菜单"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 使用自定义 Page 来处理剪贴板操作
        self._clipboard_page = ClipboardWebPage(self)
        self.setPage(self._clipboard_page)
    
    def contextMenuEvent(self, event):
        """禁用右键菜单"""
        event.ignore()


class StyledTooltip(QLabel):
    """自定义样式的工具提示 - 替代原生 ToolTip 以解决黑色背景问题"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        self.setStyleSheet("""
            QLabel {
                background-color: #FFFFFF;
                color: #1D1D1F;
                border: 1px solid #E5E5EA;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 500;
            }
        """)
        
        # 添加阴影
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(15)
        self.shadow.setColor(QColor(0, 0, 0, 30))
        self.shadow.setOffset(0, 4)
        self.setGraphicsEffect(self.shadow)
        
        self.adjustSize()

class ToolTipEventFilter(QObject):
    def __init__(self, text_getter, parent=None):
        super().__init__(parent)
        self.text_getter = text_getter # Function that returns text or None
        self.tooltip = None

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Enter:
            text = self.text_getter()
            if text:
                self.show_tooltip(obj, text)
        elif event.type() == QEvent.Type.Leave:
            self.hide_tooltip()
        elif event.type() == QEvent.Type.MouseButtonPress:
            self.hide_tooltip()
        return False

    def show_tooltip(self, widget, text):
        if self.tooltip:
            self.tooltip.close()
        
        self.tooltip = StyledTooltip(text)
        
        # 计算位置 - 默认在上方
        pos = widget.mapToGlobal(QPoint(0, 0))
        x = pos.x() + (widget.width() - self.tooltip.width()) // 2
        y = pos.y() - self.tooltip.height() - 5
        
        self.tooltip.move(x, y)
        self.tooltip.show()

    def hide_tooltip(self):
        if self.tooltip:
            self.tooltip.close()
            self.tooltip.deleteLater()
            self.tooltip = None


class FillCardItemWidget(QWidget):
    """填充页面的名片项组件 - 横条样式（参考首页设计）"""
    
    clicked = pyqtSignal(object)  # 点击信号，传递card对象
    
    def __init__(self, card, parent=None):
        super().__init__(parent)
        self.card = card
        self.is_selected = False
        self.init_ui()
    
    def init_ui(self):
        # 横条样式设计 - 紧凑版
        self.setFixedHeight(36)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 4, 6, 4)
        layout.setSpacing(4)
        self.setLayout(layout)
        
        # 名片名称 - 支持省略
        self.name_label = QLabel(self.card.name)
        self.name_label.setStyleSheet("""
            font-size: 12px;
            font-weight: 500;
            color: #1D1D1F;
        """)
        # 设置文本省略模式
        self.name_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        
        # 添加自定义 ToolTip 过滤器
        self.name_tooltip_filter = ToolTipEventFilter(self._get_name_tooltip)
        self.name_label.installEventFilter(self.name_tooltip_filter)
        
        layout.addWidget(self.name_label, 1)  # stretch=1 让名称占据剩余空间
        
        self.update_style()
    
    def _get_name_tooltip(self):
        """获取名片名称的 ToolTip 文本 (仅当被截断时显示)"""
        if self.name_label.text() != self.card.name:
            return self.card.name
        return None

    def resizeEvent(self, event):
        """大小改变时更新名称省略"""
        super().resizeEvent(event)
        self._update_elided_text()
    
    def _update_elided_text(self):
        """更新省略文本"""
        if hasattr(self, 'name_label'):
            # 计算可用宽度（减去边距）
            available_width = self.width() - 10 - 6 - 10  # 边距
            if available_width > 20:
                font_metrics = self.name_label.fontMetrics()
                elided_text = font_metrics.elidedText(self.card.name, Qt.TextElideMode.ElideRight, available_width)
                self.name_label.setText(elided_text)
    
    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.update_style()
    
    def update_style(self):
        if self.is_selected:
            self.setStyleSheet("""
                FillCardItemWidget {
                    background: #F2F8FD;
                    border: 2px solid #007AFF;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                FillCardItemWidget {
                    background: white;
                    border: 1px solid #D1D1D6;
                    border-radius: 8px;
                }
                FillCardItemWidget:hover {
                    border-color: #007AFF;
                    background: #FAFAFA;
                }
            """)
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.card)
        super().mousePressEvent(event)


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
        self._is_closing = False  # ⚡️ 标记窗口是否正在关闭
        self.selected_values = {}  # {card_id: {field_key: selected_value}} 存储用户选择的字段值
        self.current_card_values_map = {}  # 当前名片的字段多值列表 {key: values_list}
        self.current_card_combos = {}  # 当前名片的下拉框引用 {key: QComboBox}
        
        # ⚡️ Profile 缓存：同一名片 + 同一平台共享同一个 Profile 实例
        # key: "{card_id}_{form_type}", value: QWebEngineProfile 实例
        self.profile_cache = {}
        
        # ⚡️ 分类相关：按分类分组名片，默认显示第一个分类
        self.cards_by_category = {}  # {category: [cards]}
        self.category_list = []  # 分类列表（保持顺序）
        self.current_category = None  # 当前选中的分类
        self._init_categories()
        
        # 单开模式下，默认选中第一个名片
        if self.fill_mode == "single" and self.selected_cards:
            self.current_card = self.selected_cards[0]
            
        self.init_ui()
    
    def _init_categories(self):
        """初始化分类数据"""
        self.cards_by_category = {}
        for card in self.selected_cards:
            category = card.category if hasattr(card, 'category') and card.category else "默认分类"
            if category not in self.cards_by_category:
                self.cards_by_category[category] = []
                self.category_list.append(category)
            self.cards_by_category[category].append(card)
        
        # 默认选中第一个分类
        if self.category_list:
            self.current_category = self.category_list[0]
        
        print(f"📂 分类初始化完成: {len(self.category_list)} 个分类, 当前分类: {self.current_category}")
    
    def get_current_category_cards(self):
        """获取当前分类下的名片"""
        if self.current_category and self.current_category in self.cards_by_category:
            cards = self.cards_by_category[self.current_category]
            print(f"📂 获取分类 '{self.current_category}' 的名片: {[c.name for c in cards]}")
            return cards
        print(f"⚠️ 分类 '{self.current_category}' 不存在，返回所有名片")
        return self.selected_cards  # 如果没有分类，返回所有
    
    def _rebuild_current_tab_for_category(self):
        """重建当前标签页以显示新分类的名片"""
        # 获取当前标签页索引（索引0是首页，链接从索引1开始）
        current_index = self.tab_widget.currentIndex()
        # 首页（索引0）不需要重建
        if current_index <= 0:
            print(f"⚠️ 当前是首页，不重建 WebView")
            return
        
        # 计算实际链接索引（减去首页的偏移）
        real_index = current_index - 1
        if real_index >= len(self.selected_links):
            print(f"⚠️ 链接索引越界: {real_index} >= {len(self.selected_links)}")
            return
        
        # 获取当前链接
        link = self.selected_links[real_index]
        link_id = str(link.id)
        
        print(f"🔄 切换分类: {self.current_category}, 重建链接 '{link.name}' 的 WebView (tab={current_index}, link_idx={real_index})")
        
        # 清空该链接的 WebView 缓存
        if link_id in self.web_views_by_link:
            for info in self.web_views_by_link[link_id]:
                web_view = info.get('web_view')
                if web_view:
                    try:
                        web_view.stop()
                        web_view.loadFinished.disconnect()
                    except:
                        pass
            del self.web_views_by_link[link_id]
        
        if hasattr(self, 'loading_queues') and link_id in self.loading_queues:
            del self.loading_queues[link_id]
        
        # 重新创建该链接的标签页内容
        new_content = self.create_link_tab_content(link)
        
        # ⚡️ 关键修复：暂时断开 currentChanged 信号，防止 removeTab 触发窗口关闭
        # 因为 on_tab_changed 中检查 index == 0 会关闭窗口
        self.tab_widget.currentChanged.disconnect(self.on_tab_changed)
        
        try:
            # 替换标签页内容
            old_widget = self.tab_widget.widget(current_index)
            self.tab_widget.removeTab(current_index)
            self.tab_widget.insertTab(current_index, new_content, link.name or f"链接{current_index + 1}")
            self.tab_widget.setCurrentIndex(current_index)
            
            # 清理旧的 widget
            if old_widget:
                old_widget.deleteLater()
        finally:
            # 重新连接信号
            self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        # 自动开始加载新分类的 WebView 并填充
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(200, lambda: self.auto_start_loading_webviews())
    
    def closeEvent(self, event):
        """窗口关闭时清理所有资源，防止异步回调访问已销毁对象"""
        print("🛑 填充窗口正在关闭，清理资源...")
        self._is_closing = True
        
        # 停止所有定时器和清理 WebView
        for link_id, webview_infos in self.web_views_by_link.items():
            for info in webview_infos:
                web_view = info.get('web_view')
                if web_view:
                    try:
                        # 停止加载
                        web_view.stop()
                        # 断开所有信号连接
                        try:
                            web_view.loadFinished.disconnect()
                        except:
                            pass
                        # 清理报名工具定时器
                        login_timer = web_view.property("login_timer")
                        if login_timer:
                            login_timer.stop()
                            try:
                                login_timer.timeout.disconnect()
                            except:
                                pass
                        submit_timer = web_view.property("submit_timer")
                        if submit_timer:
                            submit_timer.stop()
                            try:
                                submit_timer.timeout.disconnect()
                            except:
                                pass
                    except Exception as e:
                        print(f"⚠️ 清理 WebView 时出错: {e}")
        
        # 清理加载队列
        if hasattr(self, 'loading_queues'):
            self.loading_queues.clear()
        
        # ⚡️ 清理加载超时定时器
        if hasattr(self, 'load_timeout_timers'):
            for timer in self.load_timeout_timers.values():
                if timer.isActive():
                    timer.stop()
            self.load_timeout_timers.clear()
        
        self.web_views_by_link.clear()
        
        # ⚡️ 清理 Profile 缓存
        if hasattr(self, 'profile_cache'):
            print(f"🧹 清理 {len(self.profile_cache)} 个 Profile 缓存...")
            self.profile_cache.clear()
        
        print("✅ 资源清理完成")
        
        super().closeEvent(event)
    
    def _is_valid(self) -> bool:
        """检查窗口是否仍然有效（未被关闭/销毁）"""
        if self._is_closing:
            return False
        try:
            from PyQt6 import sip
        except ImportError:
            import sip
        return not sip.isdeleted(self)
    
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
        
        # ⚡️ 延迟更新固定首页按钮位置（确保布局完成后）
        QTimer.singleShot(100, self._update_fixed_home_btn_position)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'expand_btn'):
            self.expand_btn.move(self.width() - 32, 60)
        # 更新固定首页按钮位置
        if hasattr(self, 'fixed_home_btn'):
            self._update_fixed_home_btn_position()
    
    def _update_fixed_home_btn_position(self):
        """更新固定首页按钮的位置"""
        if not hasattr(self, 'fixed_home_btn'):
            return
        # 定位在标签栏左侧，与标签对齐（margin-top: 4px）
        self.fixed_home_btn.move(0, 4)
    
    def _update_fixed_home_btn_style(self):
        """更新固定首页按钮的样式"""
        if not hasattr(self, 'fixed_home_btn'):
            return
        
        is_home_selected = self.tab_widget.currentIndex() == 0
        
        # 背景色与标签栏背景一致（不透明）
        tab_bar_bg = "#F5F5F7"
        
        if is_home_selected:
            # 选中状态样式 - 与标签选中样式一致
            self.fixed_home_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {tab_bar_bg};
                    color: {COLORS['primary']};
                    font-size: 14px;
                    font-weight: 600;
                    border: none;
                    border-radius: 0px;
                    padding: 8px 16px;
                    margin: 0px;
                }}
                QPushButton:hover {{
                    background: {tab_bar_bg};
                }}
            """)
        else:
            # 未选中状态样式 - 与标签未选中样式一致
            self.fixed_home_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {tab_bar_bg};
                    color: #6E6E73;
                    font-size: 14px;
                    font-weight: 500;
                    border: none;
                    border-radius: 0px;
                    padding: 8px 16px;
                    margin: 0px;
                }}
                QPushButton:hover {{
                    background: #EAEAEC;
                    color: #1D1D1F;
                }}
            """)
        
        # 确保位置正确
        self._update_fixed_home_btn_position()

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
                # ⚡️ 动画完成后刷新左侧面板布局
                QTimer.singleShot(50, self._refresh_left_panel_layout)
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
                # ⚡️ 动画完成后刷新左侧面板布局
                QTimer.singleShot(50, self._refresh_left_panel_layout)
                return
            
            self.right_panel.setMaximumWidth(steps[i])
            QTimer.singleShot(30, lambda: animate_step(i + 1))
        
        QTimer.singleShot(10, lambda: animate_step(0))
    
    def _refresh_left_panel_layout(self):
        """刷新左侧面板布局，解决右侧面板收起/展开后 WebView 显示异常的问题"""
        if not self._is_valid():
            return
        
        # 获取当前标签页索引
        current_index = self.tab_widget.currentIndex()
        if current_index <= 0:
            return
        
        real_index = current_index - 1
        if real_index >= len(self.selected_links):
            return
        
        current_link = self.selected_links[real_index]
        link_id = str(current_link.id)
        webview_infos = self.web_views_by_link.get(link_id, [])
        
        # ⚡️ 获取当前标签页的容器，用于刷新布局
        current_tab_widget = self.tab_widget.widget(current_index)
        cards_container = getattr(current_tab_widget, 'cards_container', None)
        scroll_area = getattr(current_tab_widget, 'scroll_area', None)
        
        # ⚡️ 强制刷新每个 WebView - 使用隐藏/显示技巧
        for info in webview_infos:
            web_view = info.get('web_view')
            placeholder = info.get('placeholder')
            
            if web_view:
                # ⚡️ 关键修复：临时隐藏再显示，强制 WebView 重新渲染
                web_view.hide()
            
            # ⚡️ 同时刷新占位符
            if placeholder:
                placeholder.updateGeometry()
        
        # ⚡️ 强制刷新父容器布局 - 关键修复
        if cards_container:
            if cards_container.layout():
                cards_container.layout().invalidate()
                cards_container.layout().activate()
            cards_container.updateGeometry()
            cards_container.update()
        
        if scroll_area:
            scroll_area.updateGeometry()
            scroll_area.update()
        
        # 处理事件队列
        QApplication.processEvents()
        
        # ⚡️ 延迟显示所有 WebView
        def show_all_webviews():
            if not self._is_valid():
                return
            
            # ⚡️ 再次刷新父容器布局
            if cards_container:
                if cards_container.layout():
                    cards_container.layout().invalidate()
                    cards_container.layout().activate()
                cards_container.updateGeometry()
            
            if scroll_area:
                scroll_area.updateGeometry()
            
            for info in webview_infos:
                web_view = info.get('web_view')
                placeholder = info.get('placeholder')
                
                if web_view:
                    web_view.show()
                    web_view.update()
                    # ⚡️ 强制 WebView 重新计算几何尺寸
                    web_view.updateGeometry()
                    
                if placeholder:
                    placeholder.updateGeometry()
            
            QApplication.processEvents()
        
        # 50ms 后显示
        QTimer.singleShot(50, show_all_webviews)
    
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
                left: 0;
            }}
            QTabBar {{
                background: transparent;
                qproperty-drawBase: 0;
            }}
            QTabBar::tab {{
                background: transparent;
                color: #6E6E73;
                padding: 8px 16px;
                margin-top: 4px;
                margin-bottom: 4px;
                margin-right: 4px;
                margin-left: 0px;
                
                min-width: 80px;
                max-width: 160px;
                height: 32px; /* 固定高度 */
                
                font-size: 14px;
                font-weight: 500;
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
            /* 滚动按钮样式 - 左右翻页箭头 */
            QTabBar::scroller {{
                width: 40px;
            }}
            QTabBar QToolButton {{
                border: 1px solid #D0D0D0;
                background: white;
                border-radius: 6px;
                width: 36px;
                height: 36px;
                margin: 2px 4px;
            }}
            QTabBar QToolButton:hover {{
                background: #F0F0F0;
                border-color: #007AFF;
            }}
            QTabBar QToolButton:pressed {{
                background: #E0E0E0;
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
        
        # ⚡️ 添加固定的"首页"按钮，覆盖在第一个标签位置上，防止滚动时被顶走
        self.fixed_home_btn = QPushButton("首页")
        self.fixed_home_btn.setParent(self.tab_widget)
        self.fixed_home_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # 高度 = 内容高度32px + padding 8px*2 = 48px，宽度留足够覆盖
        self.fixed_home_btn.setFixedSize(80, 48)
        self.fixed_home_btn.setAutoFillBackground(True)  # 启用自动填充背景
        self.fixed_home_btn.clicked.connect(self.close)
        self._update_fixed_home_btn_style()
        self.fixed_home_btn.raise_()  # 确保在最上层
        
        # 监听标签页变化，更新固定首页按钮样式
        self.tab_widget.currentChanged.connect(self._update_fixed_home_btn_style)
        
        return panel
    
    def create_link_tab_content(self, link) -> QWidget:
        """创建单个链接的标签页内容 - 延迟加载优化"""
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        container.setLayout(layout)
        
        # 横向滚动区域（包含多个名片WebView占位符）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # ⚡️ 设置尺寸策略为 Expanding，撑满可用空间
        scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
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
        
        # ⚡️ 设置尺寸策略为 Expanding，让容器撑满可用空间
        cards_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        cards_layout = QGridLayout()
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(16)
        cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        cards_container.setLayout(cards_layout)
        
        # ⚡️ 优化：不立即创建WebView，只创建占位符
        link_webview_info = []
        MAX_COLUMNS = self.columns  # 使用传入的列数设置
        
        # ⚡️ 获取当前分类的名片（多开模式且有多个分类时按分类筛选）
        cards_to_display = self.get_current_category_cards() if (self.fill_mode == "multi" and len(self.category_list) > 1) else self.selected_cards
        
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
            # 多开模式：创建网格（只显示当前分类的名片）
            cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            
            for index, card in enumerate(cards_to_display):
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
        
        # 保存 scroll_area 和 cards_container 引用，用于分类切换时重建
        container.scroll_area = scroll_area
        container.cards_container = cards_container
        container.cards_layout = cards_layout
        container.link = link
        container.built_category = self.current_category
        
        print(f"✅ 为链接 '{link.name}' 准备了 {len(link_webview_info)} 个占位符（分类: {self.current_category}）")
        
        scroll_area.setWidget(cards_container)
        layout.addWidget(scroll_area, 1)
        
        return container
    
    def toggle_fill_mode(self, link):
        """切换单开/多开模式"""
        new_mode = "single" if self.fill_mode == "multi" else "multi"
        
        print(f"🔄 切换模式: {self.fill_mode} -> {new_mode}")
        self.fill_mode = new_mode
            
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
        # container.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        # container.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        
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
        
        # 移除图标，直接显示名称
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
        # container.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        # container.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        
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
        
        # 移除图标，直接显示名称
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
        
        # WebView - 使用支持中文右键菜单的自定义类
        web_view = ChineseContextWebView()
        web_view.setMinimumHeight(450)
        
        # ⚡️ 确保WebView可以交互和实时渲染
        web_view.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        web_view.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # ⚡️ 禁用双缓冲优化，确保实时渲染
        # web_view.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        # web_view.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        web_view.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors, False)
        
        # ⚡️ 获取或创建 Profile（同一名片+同一平台共享登录状态）
        form_type = self.detect_form_type(link.url)
        profile = self.get_or_create_profile(str(card.id), form_type)
            
        # ⚡️ 事件过滤：点击卡片或Webview获得焦点时选中名片
        container.installEventFilter(self)
        header.installEventFilter(self)
        web_view.installEventFilter(self)
        
        # 绑定 card 对象，方便 eventFilter 获取
        container.setProperty("card_id", str(card.id))
        header.setProperty("card_id", str(card.id))
        web_view.setProperty("card_id", str(card.id))
        
        # 自定义 WebEnginePage，处理对话框和控制台消息  
        class CustomWebEnginePage(QWebEnginePage):
            def __init__(self, profile, parent=None):
                super().__init__(profile, parent)
                print("  🔧 CustomWebEnginePage 已创建")
            
            def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
                """重写此方法以捕获JavaScript控制台消息"""
                # 直接输出到终端
                print(f"  [JS] {message}", flush=True)
                if lineNumber > 0:
                    print(f"    位置: {sourceID}:{lineNumber}", flush=True)
            
            def javaScriptConfirm(self, securityOrigin, msg):
                """自动接受离开页面的确认对话框（如登录跳转时的 beforeunload）"""
                print(f"  [JS-CONFIRM] {msg}", flush=True)
                return True
        
        custom_page = CustomWebEnginePage(profile, web_view)
        web_view.setPage(custom_page)
        print(f"  🔧 已设置自定义Page，类型: {type(custom_page).__name__}")
        
        # 启用开发者工具（用于调试）
        from PyQt6.QtWebEngineCore import QWebEngineSettings
        settings = web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        
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
        
        # 折叠按钮（仅多开模式显示）
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
        # 单开模式下隐藏收起按钮
        if self.fill_mode == "single":
            collapse_btn.setVisible(False)
        top_toolbar.addWidget(collapse_btn)
        
        top_toolbar.addStretch()
        
        # 全部刷新按钮（现改为全局填充）
        refresh_all_btn = QPushButton("")
        refresh_all_btn.setIcon(Icons.edit('gray')) # 更换图标为编辑/填充相关
        refresh_all_btn.setToolTip("对当前页面执行全局填充")
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
        # top_toolbar.addWidget(refresh_all_btn)
        
        layout.addLayout(top_toolbar)
        
        # 类别选择区域 - 轻量分段控件风格
        cat_header = QHBoxLayout()
        cat_header.setSpacing(0)
        cat_header.setContentsMargins(0, 0, 0, 0)
        
        cat_title = QLabel("分类")
        cat_title.setStyleSheet(f"""
            font-size: 13px;
            font-weight: 600;
            color: #9CA3AF;
            letter-spacing: 0.5px;
        """)
        cat_header.addWidget(cat_title)
        cat_header.addStretch()
        layout.addLayout(cat_header)
        
        # 使用隐藏的 QComboBox 维持数据和信号，UI 用自定义按钮组
        self.category_combo = QComboBox()
        self.category_combo.hide()
        self.category_combo.currentTextChanged.connect(self.on_category_changed)
        
        # 分段按钮容器 - 横向可滚动
        self.cat_btn_scroll = QScrollArea()
        self.cat_btn_scroll.setWidgetResizable(True)
        self.cat_btn_scroll.setFixedHeight(42)
        self.cat_btn_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.cat_btn_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.cat_btn_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.cat_btn_container = QWidget()
        self.cat_btn_container.setStyleSheet("background: transparent;")
        self.cat_btn_layout = QHBoxLayout(self.cat_btn_container)
        self.cat_btn_layout.setContentsMargins(0, 0, 0, 0)
        self.cat_btn_layout.setSpacing(8)
        self.cat_btn_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        self.cat_btn_scroll.setWidget(self.cat_btn_container)
        layout.addWidget(self.cat_btn_scroll)
        
        self._cat_buttons = []
        
        # 名片列表（可滚动）- 改为网格布局
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
        self.cards_list_widget.setStyleSheet("background: transparent;")
        # 改用网格布局 - 一行2个名片（因为右侧面板宽度有限）
        self.cards_list_layout = QGridLayout()
        self.cards_list_layout.setContentsMargins(4, 4, 4, 4)
        self.cards_list_layout.setSpacing(8)
        self.cards_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
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
        self.edit_name_input.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
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
        reimport_btn = QPushButton("一键全填")
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
        
        # 1.5 批量选择第几个值
        batch_select_row = QWidget()
        batch_select_layout = QHBoxLayout()
        batch_select_layout.setContentsMargins(0, 0, 0, 0)
        batch_select_layout.setSpacing(8)
        batch_select_row.setLayout(batch_select_layout)
        
        batch_label = QLabel("粉丝赞藏填写")
        batch_label.setStyleSheet(f"""
            font-size: 12px;
            color: {COLORS['text_secondary']};
        """)
        batch_select_layout.addWidget(batch_label)
        
        self.batch_index_combo = QComboBox()
        self.batch_index_combo.setFixedWidth(150)  # 增加宽度以适应文字
        self.batch_index_combo.setFixedHeight(28)
        # 三种格式形式
        self.batch_index_combo.addItem("数字形式", 1)
        self.batch_index_combo.addItem("w形式", 2)
        self.batch_index_combo.addItem("w为单位", 3)
        # 默认选中第1个值（数字形式）
        self.batch_index_combo.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid #D9D9D9;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 13px;
                color: {COLORS['text_primary']};
                background: white;
            }}
            QComboBox:hover {{
                border-color: {COLORS['primary']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #999;
                margin-right: 6px;
            }}
        """)
        self.batch_index_combo.currentIndexChanged.connect(self.batch_select_by_index)
        batch_select_layout.addWidget(self.batch_index_combo)
        
        batch_label_suffix = QLabel("格式")
        batch_label_suffix.setStyleSheet(f"""
            font-size: 12px;
            color: {COLORS['text_secondary']};
        """)
        batch_select_layout.addWidget(batch_label_suffix)
        
        batch_select_layout.addStretch()
        layout.addWidget(batch_select_row)
        
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
        """加载分类列表（仅包含已选名片的分类）- 使用分段按钮"""
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        
        categories = self.category_list if self.category_list else ["默认分类"]
        for category in categories:
            self.category_combo.addItem(category)
        
        if self.current_category:
            index = self.category_combo.findText(self.current_category)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
        
        self.category_combo.blockSignals(False)
        
        self._rebuild_category_buttons()
            
    def on_category_changed(self, category: str):
        """类别改变时 - 重新生成当前链接的 webview 并自动填充"""
        self.current_category = category
        print(f"📂 分类切换: {category}, 当前分类名片数: {len(self.get_current_category_cards())}")
        
        self._update_category_button_styles()
        self.load_cards_list()
        
        if self.fill_mode == "multi" and len(self.category_list) > 1:
            self._rebuild_current_tab_for_category()
    
    def _rebuild_category_buttons(self):
        """重建分类分段按钮"""
        for btn in self._cat_buttons:
            btn.deleteLater()
        self._cat_buttons.clear()
        
        while self.cat_btn_layout.count():
            item = self.cat_btn_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        categories = self.category_list if self.category_list else ["默认分类"]
        
        for cat in categories:
            btn = QPushButton(cat)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(32)
            btn.setMinimumWidth(60)
            btn.setProperty("category", cat)
            btn.clicked.connect(lambda checked, c=cat: self._on_cat_btn_clicked(c))
            self.cat_btn_layout.addWidget(btn)
            self._cat_buttons.append(btn)
        
        self.cat_btn_layout.addStretch()
        self._update_category_button_styles()
    
    def _on_cat_btn_clicked(self, category: str):
        """分类按钮点击"""
        if self.category_combo.currentText() == category:
            return
        index = self.category_combo.findText(category)
        if index >= 0:
            self.category_combo.setCurrentIndex(index)
    
    def _update_category_button_styles(self):
        """更新分类按钮选中样式"""
        current = self.current_category or ""
        for btn in self._cat_buttons:
            cat = btn.property("category")
            if cat == current:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {COLORS['primary']};
                        color: white;
                        border: none;
                        border-radius: 16px;
                        font-size: 13px;
                        font-weight: 600;
                        padding: 0 16px;
                    }}
                    QPushButton:hover {{
                        background: {COLORS['primary_dark']};
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: #F3F4F6;
                        color: #6B7280;
                        border: none;
                        border-radius: 16px;
                        font-size: 13px;
                        font-weight: 500;
                        padding: 0 16px;
                    }}
                    QPushButton:hover {{
                        background: #E5E7EB;
                        color: #374151;
                    }}
                """)
    
    def load_cards_list(self, target_card_id=None):
        """加载名片列表（仅显示已选名片）- 网格布局"""
        # 清空现有列表
        while self.cards_list_layout.count():
            child = self.cards_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        category = self.category_combo.currentText()
        if not category:
            return
        
        # 收集该类别下的已选名片
        category_cards = []
        for card in self.selected_cards:
            card_category = card.category if hasattr(card, 'category') and card.category else "默认分类"
            if card_category == category:
                category_cards.append(card)
        
        # 使用网格布局添加名片 - 一行4个
        MAX_COLUMNS = 4
        target_widget = None
        
        for index, card in enumerate(category_cards):
            row = index // MAX_COLUMNS
            col = index % MAX_COLUMNS
            
            # 创建名片卡片（横条样式）
            card_widget = FillCardItemWidget(card)
            card_widget.clicked.connect(lambda c, w=card_widget: self.on_card_item_clicked(c, w))
            
            # 添加到网格
            self.cards_list_layout.addWidget(card_widget, row, col)
            
            # 记录目标卡片
            if target_card_id and str(card.id) == str(target_card_id):
                target_widget = card_widget
        
        # 选中逻辑
        if target_widget:
            target_widget.clicked.emit(target_widget.card)
        elif category_cards:
            # 默认选中第一个
            first_item = self.cards_list_layout.itemAtPosition(0, 0)
            if first_item and first_item.widget():
                widget = first_item.widget()
                if isinstance(widget, FillCardItemWidget):
                    widget.clicked.emit(widget.card)
                
    def refresh_all_webviews(self):
        """[修改为] 对当前页面的所有表单执行全局填充（不刷新页面）"""
        current_index = self.tab_widget.currentIndex()
        # 0是首页
        if current_index <= 0:
            # ⚡️ 使用非阻塞提示
            self._show_toast("请先进入某个链接页面")
            return
            
        real_index = current_index - 1
        if real_index >= len(self.selected_links):
            return
            
        link = self.selected_links[real_index]
        self._show_toast("正在为当前页面执行全局填充...")
        print(f"🚀 手动触发全局填充: {link.name}")
        
        # 调用自动填充逻辑
        self.auto_fill_for_link(str(link.id))

    def _unused_refresh_all_webviews(self):
        """[保留原逻辑] 刷新当前页面的所有WebView - 优化版本，避免卡顿"""
        current_index = self.tab_widget.currentIndex()
        # 0是首页
        if current_index <= 0:
            # ⚡️ 使用非阻塞提示
            self._show_toast("请先进入某个链接页面")
            return
            
        real_index = current_index - 1
        if real_index >= len(self.selected_links):
            return
            
        link = self.selected_links[real_index]
        webview_infos = self.web_views_by_link.get(str(link.id), [])
        
        if not webview_infos:
            self._show_toast("当前页面没有可刷新的名片")
            return
        
        # ⚡️ 先显示提示，避免用户以为卡住
        self._show_toast("正在刷新当前页面所有名片...")
        
        print(f"⟳ 刷新所有WebView: {link.name}")
        
        # ⚡️ 分批刷新，避免同时刷新多个 WebView 导致卡顿
        webviews_to_refresh = [info for info in webview_infos if info.get('web_view')]
        
        if not webviews_to_refresh:
            return
        
        # 使用队列分批刷新
        self._refresh_queue = list(webviews_to_refresh)
        self._refresh_batch_size = 2  # 每批刷新2个
        
        # 开始第一批刷新
        self._do_refresh_batch()
    
    def _do_refresh_batch(self):
        """执行一批刷新操作"""
        if not self._is_valid():
            return
        
        if not hasattr(self, '_refresh_queue') or not self._refresh_queue:
            return
        
        # 取出一批
        batch = self._refresh_queue[:self._refresh_batch_size]
        self._refresh_queue = self._refresh_queue[self._refresh_batch_size:]
        
        # 刷新这一批
        for info in batch:
            web_view = info.get('web_view')
            if web_view:
                try:
                    # ⚡️ 刷新时禁用自动填充
                    web_view.setProperty("is_auto_fill_active", False)
                    web_view.setProperty("auto_fill_after_load", False)
                    web_view.setProperty("auto_fill_after_switch", False)
                    web_view.reload()
                    web_view.setProperty("status", "loading")
                except Exception as e:
                    print(f"⚠️ 刷新 WebView 失败: {e}")
        
        # 处理事件队列，保持 UI 响应
        QApplication.processEvents()
        
        # 如果还有剩余，延迟继续刷新
        if self._refresh_queue:
            QTimer.singleShot(300, self._do_refresh_batch)
    
    def _show_toast(self, message: str, duration: int = 2000):
        """显示非阻塞的轻量级提示（Toast风格）"""
        # ⚡️ 使用 QLabel 作为轻量级提示，不阻塞 UI
        if not self._is_valid():
            return
        
        # 如果已有提示正在显示，先移除
        if hasattr(self, '_toast_label') and self._toast_label:
            try:
                self._toast_label.deleteLater()
            except:
                pass
        
        # 创建提示标签
        toast = QLabel(message, self)
        toast.setStyleSheet(f"""
            QLabel {{
                background: rgba(0, 0, 0, 0.75);
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
            }}
        """)
        toast.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toast.adjustSize()
        
        # 居中显示
        x = (self.width() - toast.width()) // 2
        y = self.height() // 2 - toast.height() // 2
        toast.move(x, y)
        toast.show()
        toast.raise_()
        
        self._toast_label = toast
        
        # 自动隐藏
        QTimer.singleShot(duration, lambda: self._hide_toast(toast))
    
    def _hide_toast(self, toast):
        """隐藏提示"""
        try:
            if toast:
                toast.hide()
                toast.deleteLater()
            if hasattr(self, '_toast_label') and self._toast_label == toast:
                self._toast_label = None
        except:
            pass
    
    def on_card_item_clicked(self, card, widget):
        """处理名片卡片点击事件"""
        # 取消其他卡片的选中状态
        for i in range(self.cards_list_layout.count()):
            item = self.cards_list_layout.itemAt(i)
            if item and item.widget():
                w = item.widget()
                if isinstance(w, FillCardItemWidget) and w != widget:
                    w.set_selected(False)
        
        # 选中当前卡片
        widget.set_selected(True)
        
        # 单开模式下，点击切换WebView内容
        if self.fill_mode == "single" and self.current_card != card:
            self.switch_card_single_mode(card)
        
        self.show_card_info(card)
    
    def show_card_info(self, card):
        """显示名片信息"""
        import json
        self.current_card = card
        
        print(f"\n🔍 显示名片信息: {card.name}")
        
        # 更新标题为名片名称
        self.card_info_title.setText(card.name)
        
        # ⚡️ 修复：保留用户之前选择的格式，不重置为数字形式
        # 只在用户第一次查看该名片时才设置为默认值（数字形式）
        if hasattr(self, 'batch_index_combo'):
            card_id = str(card.id)
            # 检查是否有保存的格式选择（使用实例属性存储每个名片的格式选择）
            if not hasattr(self, '_card_format_selections'):
                self._card_format_selections = {}  # {card_id: format_index}
            
            # 如果该名片有保存的格式选择，恢复它；否则使用默认值（数字形式）
            saved_format_index = self._card_format_selections.get(card_id, 0)
            
            self.batch_index_combo.blockSignals(True)
            self.batch_index_combo.setCurrentIndex(saved_format_index)
            self.batch_index_combo.blockSignals(False)
            
            print(f"  📋 恢复名片 '{card.name}' 的格式选择: {['数字形式', 'w形式', 'w为单位'][saved_format_index]}")
        
        # 清空字段列表
        while self.card_fields_layout.count():
            child = self.card_fields_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # 初始化当前名片的选择值存储和字段多值列表存储
        card_id = str(card.id)
        if card_id not in self.selected_values:
            self.selected_values[card_id] = {}
        
        # 存储每个字段的多值列表（用于批量选择）
        self.current_card_values_map = {}  # key -> values_list
        self.current_card_combos = {}  # key -> QComboBox 引用
        
        # 显示字段
        if hasattr(card, 'configs') and card.configs:
            field_count = 0
            for config in card.configs:
                key = ""
                value = ""
                value_count = 1
                
                # 兼容字典和对象两种格式
                if isinstance(config, dict):
                    key = config.get('key', '')
                    value = config.get('value', '')
                    value_count = config.get('value_count', 1) or 1
                elif hasattr(config, 'key'):  # 对象格式
                    key = config.key
                    value = getattr(config, 'value', '')
                    value_count = getattr(config, 'value_count', 1) or 1
                
                if key:
                    # 解析多值：检测 value 是否是 JSON 数组格式（兼容老数据）
                    values_list = []
                    if isinstance(value, str) and value.startswith('[') and value.endswith(']'):
                        try:
                            parsed = json.loads(value)
                            if isinstance(parsed, list):
                                values_list = parsed
                        except json.JSONDecodeError:
                            values_list = [value] if value else []
                    else:
                        values_list = [str(value)] if value is not None else []
                    
                    # 保存字段多值列表（用于批量选择）
                    self.current_card_values_map[key] = values_list
                    
                    # 如果还没有选择过，默认选择第一个值
                    if key not in self.selected_values[card_id] and values_list:
                        self.selected_values[card_id][key] = values_list[0]
                    
                    field_widget = self.create_field_item(key, values_list, card_id)
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
    
    def create_field_item(self, key: str, values: list, card_id: str) -> QWidget:
        """创建字段项 - 支持多值下拉选择
        
        Args:
            key: 字段名
            values: 字段值列表（可能只有一个值）
            card_id: 名片ID（用于存储选择）
        """
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
        
        # 字段名
        key_label = ElidedLabel(key)
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
        
        # 获取当前选中的值
        current_value = self.selected_values.get(card_id, {}).get(key, values[0] if values else "")
        
        # 值区域：单值显示 Label，多值显示下拉框
        if len(values) <= 1:
            # 单值：显示 Label
            value_text = values[0] if values else "（空）"
            value_label = ElidedLabel(value_text)
            value_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            value_label.setStyleSheet(f"""
                font-size: 13px;
                color: {COLORS['text_primary']};
                border: none;
                background: transparent;
            """)
            layout.addWidget(value_label, 1)
            copy_value = value_text
        else:
            # 多值：显示下拉选择框（禁用直接点击，只能通过批量选择切换）
            from PyQt6.QtWidgets import QComboBox
            combo = QComboBox()
            combo.setFixedHeight(28)
            combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            # 禁用下拉框，只能通过上方批量选择切换
            combo.setEnabled(False)
            combo.setStyleSheet(f"""
                QComboBox {{
                    border: 1px solid #FFB800;
                    border-radius: 4px;
                    padding: 2px 8px;
                    font-size: 13px;
                    color: {COLORS['text_primary']};
                    background: #FFFBF0;
                }}
                QComboBox:disabled {{
                    border: 1px solid #FFB800;
                    color: {COLORS['text_primary']};
                    background: #FFFBF0;
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 20px;
                }}
                QComboBox::down-arrow {{
                    image: none;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 5px solid #FFB800;
                    margin-right: 6px;
                }}
            """)
            
            # 添加选项
            for i, v in enumerate(values):
                display_text = v if v else f"（值{i+1}为空）"
                combo.addItem(display_text, v)  # userData 存储原始值
            
            # 设置当前选中项
            current_index = 0
            for i, v in enumerate(values):
                if v == current_value:
                    current_index = i
                    break
            combo.setCurrentIndex(current_index)
            
            # 选择变化时更新存储
            def on_value_changed(index):
                selected_val = combo.itemData(index)
                if card_id not in self.selected_values:
                    self.selected_values[card_id] = {}
                self.selected_values[card_id][key] = selected_val
                print(f"  📝 字段「{key}」选择了值: {selected_val}")
            
            combo.currentIndexChanged.connect(on_value_changed)
            layout.addWidget(combo, 1)
            
            # 复制按钮复制当前选中的值
            copy_value = current_value
            # 保存 combo 引用以便复制按钮获取最新值
            widget.combo = combo
            
            # 保存到批量选择引用中
            if hasattr(self, 'current_card_combos'):
                self.current_card_combos[key] = combo
        
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
        
        # 复制按钮：获取当前选中值
        def do_copy():
            if hasattr(widget, 'combo'):
                val = widget.combo.currentData()
            else:
                val = values[0] if values else ""
            self.copy_to_clipboard(val if val else "")
        
        copy_btn.clicked.connect(do_copy)
        layout.addWidget(copy_btn)
        
        return widget
    
    def copy_to_clipboard(self, text: str):
        """复制到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        # 可以添加一个简单的提示
        print(f"已复制: {text}")

    def batch_select_by_index(self, combo_index: int):
        """批量选择格式 - 对所有名片生效
        
        Args:
            combo_index: 下拉框的选中索引（0=数字形式, 1=w形式, 2=w为单位）
        """
        if combo_index < 0:
            return
        
        target_index = combo_index
        format_names = ["数字形式", "w形式", "w为单位"]
        format_name = format_names[combo_index] if combo_index < len(format_names) else f"格式{combo_index + 1}"
        print(f"📋 批量选择「{format_name}」（对所有名片生效）")
        
        import json
        
        # ⚡️ 修复：保存格式选择到实例变量
        if not hasattr(self, '_card_format_selections'):
            self._card_format_selections = {}
        
        # 遍历所有选中的名片
        for card in self.selected_cards:
            # 保存格式选择
            self._card_format_selections[str(card.id)] = target_index
            card_id = str(card.id)
            
            # 确保该名片在 selected_values 中有记录
            if card_id not in self.selected_values:
                self.selected_values[card_id] = {}
            
            # 检查名片是否有配置
            if not hasattr(card, 'configs') or not card.configs:
                continue
            
            # 遍历名片的所有字段配置
            for config in card.configs:
                key = ""
                value = ""
                
                # 兼容字典和对象两种格式
                if isinstance(config, dict):
                    key = config.get('key', '')
                    value = config.get('value', '')
                elif hasattr(config, 'key'):
                    key = config.key
                    value = getattr(config, 'value', '')
                
                if not key:
                    continue
                
                # 解析多值字段
                values_list = []
                if isinstance(value, str) and value.startswith('[') and value.endswith(']'):
                    try:
                        parsed = json.loads(value)
                        if isinstance(parsed, list):
                            values_list = parsed
                    except json.JSONDecodeError:
                        values_list = [value] if value else []
                else:
                    values_list = [str(value)] if value is not None else []
                
                # 只处理多值字段（多于1个值）
                if len(values_list) <= 1:
                    continue
                
                # 更新选中值
                if target_index < len(values_list):
                    selected_val = values_list[target_index]
                    self.selected_values[card_id][key] = selected_val
                    print(f"  ✓ [{card.name}] 字段「{key}」-> {format_name}: {selected_val}")
                else:
                    self.selected_values[card_id][key] = ""
                    print(f"  ⚠ [{card.name}] 字段「{key}」没有「{format_name}」对应的值（共{len(values_list)}个格式），设为空")
        
        # 更新当前名片的 UI 下拉框显示
        if self.current_card and hasattr(self, 'current_card_combos') and hasattr(self, 'current_card_values_map'):
            for key, combo in self.current_card_combos.items():
                values_list = self.current_card_values_map.get(key, [])
                
                if target_index < len(values_list):
                    combo.blockSignals(True)
                    combo.setCurrentIndex(target_index)
                    combo.blockSignals(False)
                else:
                    combo.blockSignals(True)
                    combo.setCurrentIndex(-1)
                    combo.blockSignals(False)
    
    def _apply_batch_format_for_card(self, card, format_index: int):
        """为单个名片应用批量格式选择（内部方法）
        
        Args:
            card: 名片对象
            format_index: 格式索引（0=数字形式, 1=w形式, 2=w为单位）
        """
        import json
        
        card_id = str(card.id)
        
        # 确保该名片在 selected_values 中有记录
        if card_id not in self.selected_values:
            self.selected_values[card_id] = {}
        
        # 检查名片是否有配置
        if not hasattr(card, 'configs') or not card.configs:
            return
        
        # 遍历名片的所有字段配置
        for config in card.configs:
            key = ""
            value = ""
            
            # 兼容字典和对象两种格式
            if isinstance(config, dict):
                key = config.get('key', '')
                value = config.get('value', '')
            elif hasattr(config, 'key'):
                key = config.key
                value = getattr(config, 'value', '')
            
            if not key:
                continue
            
            # 解析多值字段
            values_list = []
            if isinstance(value, str) and value.startswith('[') and value.endswith(']'):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        values_list = parsed
                except json.JSONDecodeError:
                    values_list = [value] if value else []
            else:
                values_list = [str(value)] if value is not None else []
            
            # 只处理多值字段（多于1个值）
            if len(values_list) <= 1:
                continue
            
            # 更新选中值
            if format_index < len(values_list):
                self.selected_values[card_id][key] = values_list[format_index]
            else:
                self.selected_values[card_id][key] = ""
    
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
            
            print(f"🔍 加载名片配置，共 {len(configs)} 个字段")
            
            template_ids = set()
            for config in configs:
                tid = config.get('fixed_template_id') if isinstance(config, dict) else getattr(config, 'fixed_template_id', None)
                if tid:
                    template_ids.add(tid)
            
            special_map = {}
            if template_ids:
                special_map = DatabaseManager.get_fixed_templates_special_map(list(template_ids))
            
            for config in configs:
                key = ""
                value = ""
                fixed_template_id = None
                if isinstance(config, dict):
                    key = config.get('key', '')
                    value = config.get('value', '')
                    fixed_template_id = config.get('fixed_template_id')
                elif hasattr(config, 'key'): 
                    key = config.key
                    value = getattr(config, 'value', '')
                    fixed_template_id = getattr(config, 'fixed_template_id', None)
                
                is_special = special_map.get(fixed_template_id, True) if fixed_template_id else True
                
                print(f"  - 加载字段: key={key}, fixed_template_id={fixed_template_id}, is_special={is_special}")
                self.add_edit_field_row(key, str(value) if value is not None else "", fixed_template_id, is_special)
        
        # 切换到编辑页 (index 1)
        self.right_panel_stack.setCurrentIndex(1)
        
        # ⚡️ 修复：立即处理事件，让布局先稳定
        QApplication.processEvents()
        
        # ⚡️ 修复：使用更长的延迟（100ms），确保右侧面板布局完成后再刷新左侧
        QTimer.singleShot(100, self._refresh_left_panel_layout)
    
    def cancel_card_edit(self):
        """取消编辑"""
        self.right_panel_stack.setCurrentIndex(0)
        
        # ⚡️ 修复：立即处理事件，让布局先稳定
        QApplication.processEvents()
        
        # ⚡️ 修复：使用更长的延迟（100ms），确保右侧面板布局完成后再刷新左侧
        QTimer.singleShot(100, self._refresh_left_panel_layout)
        
    def save_card_edit(self):
        """保存编辑"""
        # 1. 记录当前的格式选择（如：数字形式/w形式），避免保存后重置为默认
        current_batch_index = 0
        if hasattr(self, 'batch_index_combo'):
            current_batch_index = self.batch_index_combo.currentIndex()

        name = self.edit_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入名片名称")
            return
            
        # 使用当前名片的分类（不修改分类）
        category = self.current_card.category if hasattr(self.current_card, 'category') and self.current_card.category else "默认分类"
        
        # 收集字段
        configs = []
        print(f"🔍 收集编辑字段，共 {len(self.edit_field_rows)} 行")
        for row_widget in self.edit_field_rows:
            key, value, fixed_template_id = row_widget.get_data()
            print(f"  - key={key}, value={value}, fixed_template_id={fixed_template_id}")
            if key:  # 只添加有字段名的
                config = {"key": key, "value": value}
                if fixed_template_id:
                    config['fixed_template_id'] = fixed_template_id
                configs.append(config)
        print(f"🔍 最终收集到 {len(configs)} 个有效配置")
        
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
            
            # 刷新其他被同步的名片的内存数据
            self._refresh_synced_cards_data(configs)
            
            # 刷新界面
            # 暂时屏蔽信号，防止 load_categories 和 setCurrentIndex 触发 load_cards_list
            self.category_combo.blockSignals(True)
            try:
                self.load_categories()
                
                # 确保选中正确的分类
                index = self.category_combo.findText(category)
                if index >= 0:
                    self.category_combo.setCurrentIndex(index)
            finally:
                self.category_combo.blockSignals(False)
                
            # 手动加载列表并选中当前名片（注意：这会触发 show_card_info，从而将格式重置为0）
            self.load_cards_list(target_card_id=self.current_card.id)
            
            # 2. 恢复之前的格式选择
            if current_batch_index > 0 and hasattr(self, 'batch_index_combo'):
                print(f"🔄 保存后恢复格式选择: Index {current_batch_index}")
                self.batch_index_combo.setCurrentIndex(current_batch_index)
                # 强制应用一次格式，确保数据根据新保存的配置进行更新
                self.batch_select_by_index(current_batch_index)
            
            # 切回详情页
            self.right_panel_stack.setCurrentIndex(0)
            
            # ⚡️ 修复：立即处理事件，让布局先稳定
            QApplication.processEvents()
            
            # ⚡️ 修复：使用更长的延迟（100ms），确保右侧面板布局完成后再刷新左侧
            QTimer.singleShot(100, self._refresh_left_panel_layout)
            
            # 简单提示（不弹窗）
            print(f"✅ 名片 '{name}' 更新成功")
            
        except Exception as e:
            QMessageBox.warning(self, "失败", f"保存失败：{str(e)}")
    
    def _auto_save_current_edit(self):
        """自动保存当前编辑面板中的修改（静默保存，用于一键全填前）"""
        print(f"🔍 [自动保存] 开始检查...")
        
        # 检查是否有当前名片和编辑字段
        if not self.current_card:
            print(f"🔍 [自动保存] 跳过：没有当前名片")
            return
        
        if not hasattr(self, 'edit_field_rows'):
            print(f"🔍 [自动保存] 跳过：没有 edit_field_rows 属性")
            return
            
        if not self.edit_field_rows:
            print(f"🔍 [自动保存] 跳过：edit_field_rows 为空")
            return
        
        # 检查编辑面板是否处于活跃状态
        if not hasattr(self, 'right_panel_stack'):
            print(f"🔍 [自动保存] 跳过：没有 right_panel_stack")
            return
        
        # 获取编辑面板中的名称
        if not hasattr(self, 'edit_name_input'):
            print(f"🔍 [自动保存] 跳过：没有 edit_name_input")
            return
        
        name = self.edit_name_input.text().strip()
        if not name:
            print(f"🔍 [自动保存] 跳过：名称为空")
            return
        
        # ⚡️ 检查编辑的是否是当前名片（避免保存错误的数据）
        # 如果编辑面板的名称与当前名片不同，可能是残留的旧数据
        if name != self.current_card.name:
            # 检查是否在编辑页中（如果在编辑页，允许保存名称不同的情况，因为用户可能正在改名）
            if self.right_panel_stack.currentIndex() != 1:
                print(f"🔍 [自动保存] 跳过：编辑面板名称 '{name}' 与当前名片 '{self.current_card.name}' 不匹配，且不在编辑页")
                return
        
        # 使用当前名片的分类
        category = self.current_card.category if hasattr(self.current_card, 'category') and self.current_card.category else "默认分类"
        
        # 收集字段
        configs = []
        print(f"🔍 [自动保存] 收集字段，共 {len(self.edit_field_rows)} 行")
        for row_widget in self.edit_field_rows:
            key, value, fixed_template_id = row_widget.get_data()
            print(f"  - key={key}, value={value}")
            if key:  # 只添加有字段名的
                config = {"key": key, "value": value}
                if fixed_template_id:
                    config['fixed_template_id'] = fixed_template_id
                configs.append(config)
        
        if not configs:
            print(f"🔍 [自动保存] 跳过：没有有效配置")
            return
        
        print(f"🔍 [自动保存] 准备保存 {len(configs)} 个字段到名片 '{name}'")
        
        # 静默保存到数据库
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
            
            # ⚡️ 关键修复：清空该名片的 selected_values 缓存，确保使用最新数据
            card_id = str(self.current_card.id)
            if card_id in self.selected_values:
                del self.selected_values[card_id]
                print(f"🔄 [自动保存] 已清空名片 '{name}' 的选择值缓存")
            
            print(f"✅ [自动保存] 名片 '{name}' 已自动保存（一键全填前）")
            
        except Exception as e:
            print(f"⚠️ [自动保存] 保存失败: {e}")
    
    def _refresh_synced_cards_data(self, saved_configs):
        """刷新被同步的其他名片的内存数据
        
        当修改名片时，如果包含固定模板字段，会同步字段到其他名片。
        - 所有固定模板字段：同步字段名(key)
        - 特殊项(is_special=True)：同时同步字段值(value)
        """
        template_updates = {}  # {fixed_template_id: {'key': key, 'value': value}}
        for config in saved_configs:
            if isinstance(config, dict):
                template_id = config.get('fixed_template_id')
                if template_id:
                    template_updates[template_id] = {
                        'key': config.get('key', ''),
                        'value': config.get('value', '')
                    }
        
        if not template_updates:
            return
        
        special_map = DatabaseManager.get_fixed_templates_special_map(list(template_updates.keys()))
        special_template_ids = {tid for tid, is_sp in special_map.items() if is_sp}
        
        print(f"🔄 刷新被同步的名片内存数据，涉及 {len(template_updates)} 个固定模板，其中 {len(special_template_ids)} 个特殊项")
        
        current_card_id = str(self.current_card.id)
        updated_count = 0
        
        for card in self.selected_cards:
            if str(card.id) == current_card_id:
                continue
            
            if not hasattr(card, 'configs') or not card.configs:
                continue
            
            card_updated = False
            
            for config in card.configs:
                template_id = None
                if isinstance(config, dict):
                    template_id = config.get('fixed_template_id')
                elif hasattr(config, 'fixed_template_id'):
                    template_id = config.fixed_template_id
                
                if template_id and template_id in template_updates:
                    update_data = template_updates[template_id]
                    is_special = template_id in special_template_ids
                    
                    old_key = config['key'] if isinstance(config, dict) else config.key
                    new_key = update_data['key']
                    if old_key != new_key:
                        if isinstance(config, dict):
                            config['key'] = new_key
                        elif hasattr(config, 'key'):
                            config.key = new_key
                        card_updated = True
                    
                    if is_special:
                        old_value = config['value'] if isinstance(config, dict) else config.value
                        new_value = update_data['value']
                        if old_value != new_value:
                            if isinstance(config, dict):
                                config['value'] = new_value
                            elif hasattr(config, 'value'):
                                config.value = new_value
                            card_updated = True
            
            if card_updated:
                updated_count += 1
                print(f"  ✅ 已刷新名片「{card.name}」的内存数据")
        
        if updated_count > 0:
            print(f"🔄 共刷新 {updated_count} 个名片的内存数据")

    def add_edit_field_row(self, key="", value="", fixed_template_id=None, is_special=True):
        """添加编辑字段行"""
        row = EditFieldRow(key, value, self, fixed_template_id, is_special)
        self.edit_fields_layout.addWidget(row)
        self.edit_field_rows.append(row)
        
    def remove_edit_field_row(self, row):
        """删除编辑字段行"""
        if row in self.edit_field_rows:
            self.edit_field_rows.remove(row)
            row.deleteLater()

    def reimport_card(self):
        """一键填充：单开模式填充当前名片，多开模式填充当前tab链接下所有webview"""
        print("🔄 一键填充...")
        
        # ⚡️ 先自动保存当前编辑面板中的修改（如果有）
        self._auto_save_current_edit()
        
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
        
        # 多开模式：填充当前tab链接下所有webview（复用auto_fill_for_link逻辑）
        if self.fill_mode == "multi":
            print(f"📋 多开模式：填充链接 {link_id} 下所有webview")
            self.auto_fill_for_link(link_id)
            return
        
        # 单开模式：填充当前名片对应的webview
        if not self.current_card:
            QMessageBox.warning(self, "提示", "请先选择名片")
            return
        
        # 获取该链接下的所有 WebView 信息
        webview_infos = self.web_views_by_link.get(link_id, [])
        
        # 单开模式下，只有一个 WebView
        target_info = webview_infos[0] if webview_infos else None
        
        if target_info:
            if target_info.get('web_view'):
                # ⚡️ 从数据库获取最新的名片数据（确保修改后的数据被使用）
                latest_card = self.current_card
                try:
                    db_card = self.db_manager.get_card_by_id(self.current_card.id)
                    if db_card:
                        latest_card = db_card
                        # 更新缓存中的 card，以便下次使用
                        target_info['card'] = latest_card
                        # 更新 WebView 的属性
                        target_info['web_view'].setProperty("card_data", latest_card)
                        # 同时更新 self.current_card
                        self.current_card = latest_card
                        # ⚡️ 兼容处理：清空缓存前保存用户选择的格式索引，清空后重新应用
                        card_id = str(latest_card.id)
                        batch_format_index = self.batch_index_combo.currentIndex() if hasattr(self, 'batch_index_combo') else 0
                        if card_id in self.selected_values:
                            del self.selected_values[card_id]
                        # 重新应用用户选择的格式
                        if batch_format_index > 0:
                            self._apply_batch_format_for_card(latest_card, batch_format_index)
                        print(f"✅ 已刷新名片数据: {latest_card.name}")
                except Exception as e:
                    print(f"⚠️ 刷新名片失败: {e}")

                # ⚡️ 直接执行填充逻辑，不刷新页面
                print(f"⚡️ 直接执行填充（不刷新页面）: {latest_card.name}")
                
                # 设置状态为填充中
                target_info['web_view'].setProperty("status", "filling")
                target_info['web_view'].setProperty("is_auto_fill_active", True)
                
                # 直接调用填充函数
                self.execute_auto_fill_for_webview(target_info['web_view'], latest_card)
                return
            else:
                QMessageBox.warning(self, "提示", "页面尚未加载完成，请稍候")
                return
        
        QMessageBox.warning(self, "提示", "未找到该名片对应的表单")

    def select_card_by_id(self, target_card_id: str):
        """通过ID选中名片列表项"""
        target_card = None
        
        # 1. 更新列表项视觉状态（支持新的网格布局）
        if hasattr(self, 'cards_list_layout'):
            for i in range(self.cards_list_layout.count()):
                item = self.cards_list_layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if isinstance(widget, FillCardItemWidget):
                        if str(widget.card.id) == target_card_id:
                            widget.set_selected(True)
                            target_card = widget.card
                        else:
                            widget.set_selected(False)
        
        # 2. 触发业务逻辑
        if target_card:
            # 如果在单开模式下切换，才调用 switch_card_single_mode
            if self.fill_mode == "single" and self.current_card != target_card:
                 self.switch_card_single_mode(target_card)
            
            # 始终刷新右侧面板
            self.show_card_info(target_card)

    def eventFilter(self, obj, event):
        """事件过滤器：处理点击选中"""
        if event.type() == QEvent.Type.MouseButtonPress:
             # 点击容器或标题栏选中
             card_id = obj.property("card_id")
             if card_id:
                 self.select_card_by_id(card_id)
                 
        elif event.type() == QEvent.Type.FocusIn:
             # WebView获得焦点时选中
             card_id = obj.property("card_id")
             if card_id:
                 self.select_card_by_id(card_id)
        
        return super().eventFilter(obj, event)

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
        
        # ⚡️ 优化：切换名片时，使用新名片的 Profile，而不是清除旧名片的 cookie
        # 这样可以保持每个名片的登录状态独立，同时同一名片内共享登录状态
        if info['web_view']:
            web_view = info['web_view']
            
            # 获取新名片对应的 Profile
            form_type = self.detect_form_type(link.url)
            new_profile = self.get_or_create_profile(str(new_card.id), form_type)
            
            # ⚡️ 关键修复：如果是报名工具链接，必须清除旧的 filler 和相关属性
            # 防止复用旧名片的 filler（其 card_id 是错误的）
            if form_type == 'baominggongju':
                # 停止旧的登录轮询定时器
                login_timer = web_view.property("login_timer")
                if login_timer:
                    login_timer.stop()
                    web_view.setProperty("login_timer", None)
                
                # 停止旧的提交检查定时器
                submit_timer = web_view.property("submit_timer")
                if submit_timer:
                    submit_timer.stop()
                    web_view.setProperty("submit_timer", None)
                
                # 清除旧的 filler 及相关属性
                web_view.setProperty("baoming_filler", None)
                web_view.setProperty("baoming_card_config", None)
                web_view.setProperty("baoming_filled_data", None)
                web_view.setProperty("baoming_page_rendered", False)
                web_view.setProperty("baoming_card", None)
                print(f"🧹 [报名工具] 已清除旧名片的 filler，准备使用新名片 {new_card.name} 重新初始化")
            
            # 创建新的 Page（使用新名片的 Profile）
            class WebEnginePage(QWebEnginePage):
                def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
                    print(f"  [JS] {message}", flush=True)
                
                def javaScriptConfirm(self, securityOrigin, msg):
                    return True
            
            new_page = WebEnginePage(new_profile, web_view)
            web_view.setPage(new_page)
            
            # 加载空白页，视觉上重置
            web_view.load(QUrl("about:blank"))
            
            print(f"🔄 已切换到新名片 Profile: {new_card.id}_{form_type}")

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
                info['loaded'] = False
                
                # ⚡️ 关键修复：报名工具链接使用自定义登录页面，不加载原始URL
                if 'baominggongju.com' in link.url:
                    print(f"  📱 [报名工具] 切换名片后，直接显示登录页面（不加载原网页）")
                    self.init_baoming_tool_for_webview(info['web_view'], link.url, new_card)
                else:
                    # 其他链接正常加载原始URL
                    info['web_view'].setProperty("auto_fill_on_switch", True)
                    info['web_view'].load(QUrl(link.url))
             
             # 延迟 300ms 再加载目标页面
             QTimer.singleShot(300, reload_target)
             
        # 5. 手动触发填充（补救措施）- 仅对非报名工具链接有效
        # 目标加载启动后，再过 2000ms 检查 (总共 2300ms 后)
        if 'baominggongju.com' not in link.url:
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
        # ⚡️ 安全检查：窗口是否已关闭
        if not self._is_valid():
            return
        
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
        
        # ⚡️ 清理其他标签页的资源，减少内存占用和卡顿
        self.unload_inactive_tabs(link_id)
        
        # ⚡️ 检查标签页是否因分类切换需要重建（多开模式 + 多分类时）
        current_tab_widget = self.tab_widget.widget(index)
        built_category = getattr(current_tab_widget, 'built_category', None)
        if (self.fill_mode == "multi" and len(self.category_list) > 1
                and built_category is not None and built_category != self.current_category):
            print(f"🔄 检测到分类变更: {built_category} -> {self.current_category}，重建标签页 '{current_link.name}'")
            
            if link_id in self.web_views_by_link:
                for info in self.web_views_by_link[link_id]:
                    web_view = info.get('web_view')
                    if web_view:
                        try:
                            web_view.stop()
                            web_view.loadFinished.disconnect()
                        except:
                            pass
                del self.web_views_by_link[link_id]
            
            if hasattr(self, 'loading_queues') and link_id in self.loading_queues:
                del self.loading_queues[link_id]
            
            new_content = self.create_link_tab_content(current_link)
            
            self.tab_widget.currentChanged.disconnect(self.on_tab_changed)
            try:
                self.tab_widget.removeTab(index)
                self.tab_widget.insertTab(index, new_content, current_link.name or f"链接{index}")
                self.tab_widget.setCurrentIndex(index)
                if current_tab_widget:
                    current_tab_widget.deleteLater()
            finally:
                self.tab_widget.currentChanged.connect(self.on_tab_changed)
            
            webview_infos = self.web_views_by_link.get(link_id, [])
            if webview_infos:
                self.load_webviews_only(webview_infos)
            return
        
        # ⚡️ 强制刷新当前标签页的UI
        current_widget = self.tab_widget.currentWidget()
        if current_widget:
            current_widget.update()
            
        # 获取该链接的WebView信息
        webview_infos = self.web_views_by_link.get(link_id, [])
        
        # 检查是否需要加载（如果是首次访问，或之前被清理了）
        needs_load = False
        
        if not hasattr(self, 'loading_queues') or link_id not in self.loading_queues:
             needs_load = True
        else:
             # 检查是否有任何已加载的 view，如果没有（被unload了），也视为需要加载
             has_views = any(info.get('web_view') for info in webview_infos)
             if not has_views:
                 needs_load = True
        
        if needs_load:
             print(f"⚡️ 激活标签页，开始加载链接 '{current_link.name}' 的WebView...")
             # 重新初始化加载队列并开始加载
             self.load_webviews_only(webview_infos)
        else:
             # 如果已经初始化过，检查是否有挂起的加载任务（继续加载剩余的）
             # 或者只是单纯的切换显示（WebView已经创建）
             pass
             
    def unload_inactive_tabs(self, active_link_id: str):
        """销毁非当前标签页的 WebView 以释放资源"""
        # ⚡️ 安全检查
        if not self._is_valid():
            return
        
        print(f"🧹 正在清理非当前标签页资源，保留: {active_link_id}")
        
        try:
            from PyQt6 import sip
        except ImportError:
            import sip
        
        # 遍历所有链接的 WebView 信息
        for link_id, webview_infos in list(self.web_views_by_link.items()):  # 使用 list() 避免迭代时修改
            if link_id == active_link_id:
                continue
                
            # 清理该链接下的所有 WebView
            destroyed_count = 0
            for info in webview_infos:
                web_view = info.get('web_view')
                if web_view:
                    # 停止加载并销毁
                    try:
                        # 检查 WebView 是否已被销毁
                        if not sip.isdeleted(web_view):
                            # 先断开信号连接，防止回调触发
                            try:
                                web_view.loadFinished.disconnect()
                            except:
                                pass
                            web_view.stop()
                            web_view.setParent(None)
                            web_view.deleteLater()
                    except Exception as e:
                        print(f"⚠️ 销毁 WebView 失败: {e}")
                    
                    # 重置信息
                    info['web_view'] = None
                    info['loaded'] = False
                    destroyed_count += 1
            
            if destroyed_count > 0:
                print(f"  - 已销毁链接 {link_id} 的 {destroyed_count} 个 WebView")
            
            # 清理加载队列，防止后台继续加载
            if hasattr(self, 'loading_queues') and link_id in self.loading_queues:
                del self.loading_queues[link_id]
                
        # 强制垃圾回收
        import gc
        gc.collect()
        
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
        # ⚡️ 安全检查：窗口是否已关闭
        if not self._is_valid():
            print("🛑 [auto_fill_for_link] 窗口已关闭，跳过自动填充")
            return
        
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
        
        # 收集所有已加载的WebView（包括已填充的，支持覆盖填充）
        loaded_webviews = []
        for info in webview_infos:
            status = info['web_view'].property("status") if info['web_view'] else None
            # ⚡️ 关键修复：不仅收集 "loaded"，也收集 "filled" 状态的 WebView
            # 这样"一键全填"可以覆盖已填充的数据
            if info['web_view'] and status in ["loaded", "filled", "filling"]:
                loaded_webviews.append(info['web_view'])
        
        print(f"\n{'='*60}")
        print(f"🚀 开始填充链接 {link_id} 的 {len(loaded_webviews)} 个表单")
        print(f"{'='*60}\n")
        
        for index, web_view in enumerate(loaded_webviews):
            card_data = web_view.property("card_data")
            
            # ⚡️ 从数据库获取最新的名片数据
            try:
                latest_card = self.db_manager.get_card_by_id(card_data.id)
                if latest_card:
                    card_data = latest_card
                    # 更新 WebView 的属性
                    web_view.setProperty("card_data", latest_card)
                    # ⚡️ 兼容处理：清空缓存前保存用户选择的格式索引，清空后重新应用
                    card_id = str(latest_card.id)
                    batch_format_index = self.batch_index_combo.currentIndex() if hasattr(self, 'batch_index_combo') else 0
                    if card_id in self.selected_values:
                        del self.selected_values[card_id]
                    # 重新应用用户选择的格式
                    if batch_format_index > 0:
                        self._apply_batch_format_for_card(latest_card, batch_format_index)
                    print(f"✅ 已刷新名片数据: {latest_card.name}")
            except Exception as e:
                print(f"⚠️ 刷新名片失败: {e}")
            
            print(f"📝 填写 WebView #{index+1}: {card_data.name}")
            web_view.setProperty("status", "filling")
            # 设置 is_auto_fill_active 标记
            web_view.setProperty("is_auto_fill_active", True)
            
            # ⚡️ 直接执行填充逻辑，不刷新页面
            print(f"⚡️ 直接执行填充（不刷新页面）: {card_data.name}")
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
        
        # 创建WebView - 使用支持中文右键菜单的自定义类
        web_view = ChineseContextWebView()
        web_view.setMinimumHeight(450)
        
        # ⚡️ 确保WebView可以交互和实时渲染
        web_view.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        web_view.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # ⚡️ 禁用双缓冲优化，确保实时渲染
        # web_view.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        # web_view.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        web_view.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors, False)
        
        # ⚡️ 获取或创建 Profile（同一名片+同一平台共享登录状态）
        form_type = self.detect_form_type(link.url)
        profile = self.get_or_create_profile(str(card.id), form_type)
        
        class WebEnginePage(QWebEnginePage):
            def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
                """重写此方法以捕获JavaScript控制台消息"""
                print(f"  [JS] {message}", flush=True)
            
            def javaScriptConfirm(self, securityOrigin, msg):
                """自动接受离开页面的确认对话框（如登录跳转时的 beforeunload）"""
                return True
        
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
        # QApplication.processEvents()  # 处理挂起的事件，立即刷新UI
        
        return web_view
    
    def load_next_batch_for_link(self, link_id: str, batch_size: int):
        """为指定链接加载下一批WebView"""
        # ⚡️ 安全检查：窗口是否已关闭
        if not self._is_valid():
            print("🛑 [load_next_batch_for_link] 窗口已关闭，停止加载")
            return
        
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
        
        # ⚡️ 初始化加载超时定时器存储（如果不存在）
        if not hasattr(self, 'load_timeout_timers'):
            self.load_timeout_timers = {}
        
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
            # ⚡️ 记录加载开始时间，用于超时检测
            web_view.setProperty("load_start_time", time.time())
            
            # ⚡️ 设置加载超时定时器（30秒）
            webview_id = id(web_view)
            timeout_timer = QTimer()
            timeout_timer.setSingleShot(True)
            timeout_timer.timeout.connect(lambda wv=web_view, lid=link_id: self.on_webview_load_timeout(wv, lid))
            timeout_timer.start(30000)  # 30秒超时
            self.load_timeout_timers[webview_id] = timeout_timer
            
            # ⚡️ 强制刷新，确保加载立即可见
            web_view.show()
            # web_view.update()
    
    def on_webview_load_timeout(self, web_view: QWebEngineView, link_id: str):
        """WebView 加载超时处理"""
        # ⚡️ 安全检查
        if not self._is_valid():
            return
        
        try:
            from PyQt6 import sip
        except ImportError:
            import sip
        
        if sip.isdeleted(web_view):
            return
        
        # 检查是否已经加载完成（避免重复处理）
        status = web_view.property("status")
        if status != "loading":
            return
        
        card_data = web_view.property("card_data")
        card_name = card_data.name if card_data else "未知"
        
        print(f"⏰ WebView ({card_name}) 加载超时（30秒），强制标记为已加载")
        
        # 将状态设为 timeout，并触发后续流程
        web_view.setProperty("status", "timeout")
        
        # 清理超时定时器
        webview_id = id(web_view)
        if hasattr(self, 'load_timeout_timers') and webview_id in self.load_timeout_timers:
            del self.load_timeout_timers[webview_id]
        
        # 手动触发加载完成检查，继续加载下一批
        self.check_batch_load_complete(link_id, web_view)
    
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
        
        # ⚡️ 初始化加载超时定时器存储（如果不存在）
        if not hasattr(self, 'load_timeout_timers'):
            self.load_timeout_timers = {}
        
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
            # ⚡️ 记录加载开始时间
            web_view.setProperty("load_start_time", time.time())
            
            # ⚡️ 设置加载超时定时器（30秒）
            webview_id = id(web_view)
            link_id = str(link.id) if hasattr(link, 'id') else "unknown"
            timeout_timer = QTimer()
            timeout_timer.setSingleShot(True)
            timeout_timer.timeout.connect(lambda wv=web_view, lid=link_id: self.on_webview_load_timeout(wv, lid))
            timeout_timer.start(30000)  # 30秒超时
            self.load_timeout_timers[webview_id] = timeout_timer
            
            # ⚡️ 强制刷新，确保加载立即可见
            web_view.show()
            # web_view.update()
    
    def _safe_set_property(self, obj, prop_name, value):
        """安全地设置属性，防止对象已删除导致的crash"""
        try:
            from PyQt6 import sip
        except ImportError:
            import sip
        
        try:
            if not sip.isdeleted(obj):
                obj.setProperty(prop_name, value)
        except:
            pass

    def _safe_execute_auto_fill(self, web_view, card_data):
        """安全地执行自动填充"""
        try:
            from PyQt6 import sip
        except ImportError:
            import sip
        
        try:
            if not sip.isdeleted(web_view):
                self.execute_auto_fill_for_webview(web_view, card_data)
        except:
            pass

    def on_batch_webview_loaded(self, web_view: QWebEngineView, success: bool):
        """批量加载时的回调"""
        # ⚡️ 安全检查：窗口或 WebView 是否已销毁
        if not self._is_valid():
            print("🛑 [on_batch_webview_loaded] 窗口已关闭，跳过回调")
            return
        
        try:
            from PyQt6 import sip
        except ImportError:
            import sip
        
        if sip.isdeleted(web_view):
            print("🛑 [on_batch_webview_loaded] WebView 已销毁，跳过回调")
            return
        
        # ⚡️ 取消加载超时定时器
        webview_id = id(web_view)
        if hasattr(self, 'load_timeout_timers') and webview_id in self.load_timeout_timers:
            timer = self.load_timeout_timers[webview_id]
            if timer.isActive():
                timer.stop()
            del self.load_timeout_timers[webview_id]
        
        card_data = web_view.property("card_data")
        link_data = web_view.property("link_data")
        index = web_view.property("index")
        info = web_view.property("info")
        
        if not success:
            web_view.setProperty("status", "failed")
            print(f"❌ WebView #{index+1} ({card_data.name}) 加载失败")
            # ⚡️ 即使失败也要检查是否继续加载下一批
            link_id = str(link_data.id)
            self.check_batch_load_complete(link_id, web_view)
            return
        
        web_view.setProperty("status", "loaded")
        if info:
            info['loaded'] = True
        self.loaded_views.append(web_view)
        print(f"✅ WebView #{index+1} ({card_data.name}) 加载完成")
        
        # ⚡️ 加载完成后强制刷新UI
        web_view.update()
        # QApplication.processEvents()
        
        # ⚡️ 逻辑优化：如果是被手动禁用（如刷新）的自动填充，
        # 在页面加载完成2秒后，自动恢复自动填充能力（is_auto_fill_active -> True）
        # 这样下次如果页面发生跳转（如登录后），就能自动填充了
        if web_view.property("is_auto_fill_active") is False:
            print(f"⚡️ 检测到自动填充被临时禁用，将在2秒后恢复能力（但不执行填充）")
            QTimer.singleShot(2000, lambda: self._safe_set_property(web_view, "is_auto_fill_active", True))

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
            QTimer.singleShot(2000, lambda: self._safe_execute_auto_fill(web_view, card_data))
            return  # 不再继续执行后续的首次加载逻辑
        
        # ⚡️ 模式切换后自动填充：检查 info 中的 auto_fill_after_switch 标记
        if info and info.get('auto_fill_after_switch'):
            print(f"⚡️ 模式切换后加载完成，准备自动填充: {card_data.name}")
            info['auto_fill_after_switch'] = False  # 清除标记，避免重复填充
            # 设置 is_auto_fill_active，这样后续刷新也能自动填充
            web_view.setProperty("is_auto_fill_active", True)
            # 延迟执行填充，确保页面完全就绪
            QTimer.singleShot(1500, lambda: self._safe_execute_auto_fill(web_view, card_data))
            # 注意：不 return，继续执行后续逻辑以便处理批次加载
        
        # 获取当前WebView所属的链接
        link_id = str(link_data.id)
        
        # ⚡️ 检查批次加载是否完成，继续加载下一批
        self.check_batch_load_complete(link_id, web_view)
    
    def check_batch_load_complete(self, link_id: str, web_view: QWebEngineView):
        """检查当前批次是否加载完成，继续加载下一批"""
        # ⚡️ 安全检查
        if not self._is_valid():
            return
        
        webview_infos = self.web_views_by_link.get(link_id, [])
        link_data = web_view.property("link_data")
        
        # 统计该链接的加载状态（只统计 "loading" 状态的）
        loading_count = sum(1 for info in webview_infos 
                          if info['web_view'] and info['web_view'].property("status") == "loading")
        
        if loading_count == 0:
            # 当前链接的当前批次加载完成
            BATCH_SIZE = 2
            if hasattr(self, 'loading_queues') and link_id in self.loading_queues and self.loading_queues[link_id]:
                # 继续加载该链接的下一批
                print(f"\n⏭️  链接 {link_id} 继续加载下一批（剩余 {len(self.loading_queues[link_id])} 个）")
                # ⚡️ 优化：增加加载间隔，减轻卡顿
                QTimer.singleShot(800, lambda lid=link_id: self.load_next_batch_for_link(lid, BATCH_SIZE))
            else:
                # 该链接的所有WebView加载完成
                loaded_count = sum(1 for info in webview_infos if info.get('loaded', False))
                link_name = link_data.name if link_data else link_id
                print(f"\n🎉 链接 '{link_name}' 的所有WebView加载完成 ({loaded_count}/{len(webview_infos)})")
                
                # ⚡️ 自动填充模式：该链接加载完成后立即开始填充
                if hasattr(self, 'auto_fill_enabled') and self.auto_fill_enabled:
                    if link_id not in self.links_ready_for_fill:
                        self.links_ready_for_fill.add(link_id)
                        print(f"\n🚀 自动开始填充链接 '{link_name}' 的表单...")
                        # 使用默认参数捕获link_id的当前值，避免闭包问题
                        QTimer.singleShot(1000, lambda lid=link_id: self.auto_fill_for_link(lid))
    
    def on_webview_loaded(self, web_view: QWebEngineView, success: bool):
        """WebView加载完成"""
        # ⚡️ 安全检查：窗口或 WebView 是否已销毁
        if not self._is_valid():
            print("🛑 [on_webview_loaded] 窗口已关闭，跳过回调")
            return
        
        try:
            from PyQt6 import sip
        except ImportError:
            import sip
        
        if sip.isdeleted(web_view):
            print("🛑 [on_webview_loaded] WebView 已销毁，跳过回调")
            return
        
        # ⚡️ 取消加载超时定时器
        webview_id = id(web_view)
        if hasattr(self, 'load_timeout_timers') and webview_id in self.load_timeout_timers:
            timer = self.load_timeout_timers[webview_id]
            if timer.isActive():
                timer.stop()
            del self.load_timeout_timers[webview_id]
        
        card_data = web_view.property("card_data")
        link_data = web_view.property("link_data")
        index = web_view.property("index")
        
        if not success:
            web_view.setProperty("status", "failed")
            print(f"❌ WebView #{index+1} ({card_data.name}) 加载失败")
            return
        
        web_view.setProperty("status", "loaded")
        print(f"✅ WebView #{index+1} ({card_data.name}) 加载完成 - {link_data.name}")
        
        # ⚡️ 移动端适配：为特定平台注入响应式 CSS
        self._inject_mobile_responsive_css(web_view, link_data)
        
        # ⚡️ 逻辑优化：如果是被手动禁用（如刷新）的自动填充，
        # 在页面加载完成2秒后，自动恢复自动填充能力（is_auto_fill_active -> True）
        # 这样下次如果页面发生跳转（如登录后），就能自动填充了
        if web_view.property("is_auto_fill_active") is False:
            print(f"⚡️ 检测到自动填充被临时禁用，将在2秒后恢复能力（但不执行填充）")
            QTimer.singleShot(2000, lambda: self._safe_set_property(web_view, "is_auto_fill_active", True))

        # ⚡️ 智能重填逻辑：如果之前点击了"填充"，且页面重新加载了（可能是登录跳转回来），则自动再次填充
        if web_view.property("is_auto_fill_active"):
            # ⚡️ 报名工具特殊处理：如果已经渲染了自定义表单页面，不要重复触发填充
            # 因为报名工具的 setHtml() 会触发 loadFinished，导致无限循环
            if web_view.property("baoming_page_rendered"):
                print(f"⚡️ 报名工具页面已渲染，跳过自动重填: {card_data.name}")
                return  # 跳过，不触发填充
            
            print(f"⚡️ 检测到页面刷新且填充模式已激活，准备自动重填: {card_data.name}")
            # 延迟2秒执行，给予页面充分的初始化时间（特别是登录后的重定向）
            QTimer.singleShot(2000, lambda: self._safe_execute_auto_fill(web_view, card_data))
        
        # 检查是否是切换名片后的重新加载
        if web_view.property("auto_fill_on_switch"):
             print(f"⚡️ 切换名片后加载完成，准备自动填充: {card_data.name}")
             web_view.setProperty("auto_fill_on_switch", False) # 清除标记
             # 延迟执行填充，确保页面完全就绪
             QTimer.singleShot(1000, lambda: self._safe_execute_auto_fill(web_view, card_data))
        
        # 检查是否有自动填充标记（重新导入时使用）
        if web_view.property("auto_fill_after_load"):
            print(f"⚡️ 页面刷新完成，正在重新导入数据: {card_data.name}")
            web_view.setProperty("auto_fill_after_load", False)
            # 延迟执行填充，确保页面完全就绪
            QTimer.singleShot(1500, lambda: self._safe_execute_auto_fill(web_view, card_data))
        
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
    
    def _get_fill_data_for_card(self, card, as_dict=False):
        """获取名片的填充数据（使用用户选择的值）
        
        Args:
            card: 名片对象
            as_dict: 是否返回字典格式（某些平台需要）
            
        Returns:
            list 或 dict 格式的填充数据
        """
        import json
        card_id = str(card.id)
        selected = self.selected_values.get(card_id, {})
        
        print(f"🔍 [_get_fill_data_for_card] 名片: {card.name}, ID: {card_id}")
        print(f"🔍 [_get_fill_data_for_card] card.configs 类型: {type(card.configs)}, 数量: {len(card.configs) if card.configs else 0}")
        
        def parse_value(key, raw_value):
            """解析字段值：检测 JSON 数组格式，使用用户选择或默认第一个值"""
            # 优先使用用户已选择的值
            if key in selected:
                return selected[key]
            
            # 检测是否是 JSON 数组格式（兼容老数据）
            if isinstance(raw_value, str) and raw_value.startswith('[') and raw_value.endswith(']'):
                try:
                    values_list = json.loads(raw_value)
                    if isinstance(values_list, list) and values_list:
                        # 默认使用第一个值
                        return values_list[0]
                except json.JSONDecodeError:
                    pass
            
            # 普通字符串，直接返回
            return raw_value
        
        if as_dict:
            fill_data = {}
            for config in card.configs:
                if isinstance(config, dict):
                    key = config.get('key', '')
                    raw_value = config.get('value', '')
                else:
                    key = config.key
                    raw_value = getattr(config, 'value', '')
                
                final_value = parse_value(key, raw_value)
                fill_data[key] = final_value
                print(f"  📝 字段: {key} = {final_value} (原始值: {raw_value})")
            return fill_data
        else:
            fill_data = []
            for config in card.configs:
                if isinstance(config, dict):
                    key = config.get('key', '')
                    raw_value = config.get('value', '')
                else:
                    key = config.key
                    raw_value = getattr(config, 'value', '')
                
                final_value = parse_value(key, raw_value)
                fill_data.append({'key': key, 'value': final_value})
                print(f"  📝 字段: {key} = {final_value} (原始值: {raw_value})")
            return fill_data
    
    def execute_auto_fill_for_webview(self, web_view: QWebEngineView, card):
        """为单个WebView执行自动填写（参考 auto_fill_window.py）"""
        # ⚡️ 安全检查：窗口或 WebView 是否已销毁
        if not self._is_valid():
            print("🛑 [execute_auto_fill_for_webview] 窗口已关闭，跳过填充")
            return
        
        try:
            from PyQt6 import sip
        except ImportError:
            import sip
        
        if sip.isdeleted(web_view):
            print("🛑 [execute_auto_fill_for_webview] WebView 已销毁，跳过填充")
            return
        
        # ⚡️ 关键修复：每次填充前检查用户权限（防止多开模式绕过次数限制）
        if self.current_user:
            from core.auth import check_user_can_use
            can_use, message = check_user_can_use(self.current_user)
            if not can_use:
                print(f"❌ [权限检查] 用户无法继续填充: {message}")
                web_view.setProperty("status", "quota_exceeded")
                # 只弹出一次提示（使用实例标记防止重复弹窗）
                if not getattr(self, '_quota_exceeded_shown', False):
                    self._quota_exceeded_shown = True
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "使用受限", f"{message}\n\n请联系平台客服续费后继续使用。")
                return
        
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
        
        # 准备填写数据（使用辅助方法，支持多值选择）
        if form_type == 'tencent_docs':
            # 腾讯文档需要字典格式
            fill_data = self._get_fill_data_for_card(card, as_dict=True)
            
            # 使用腾讯文档填写引擎
            js_code = self.tencent_docs_engine.generate_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟3秒后获取结果
            def safe_get_result():
                try:
                    from PyQt6 import sip
                except ImportError:
                    import sip
                if not sip.isdeleted(web_view):
                    self.get_fill_result(web_view, card, 'tencent_docs')
            
            QTimer.singleShot(3000, safe_get_result)
            
        elif form_type == 'mikecrm':
            # 麦客CRM需要列表格式
            fill_data = self._get_fill_data_for_card(card)
            
            # 使用麦客CRM填写引擎
            js_code = self.auto_fill_engine.generate_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟3秒后获取结果
            def safe_get_result():
                try:
                    from PyQt6 import sip
                except ImportError:
                    import sip
                if not sip.isdeleted(web_view):
                    self.get_fill_result(web_view, card, 'mikecrm')

            QTimer.singleShot(3000, safe_get_result)
        
        elif form_type == 'wjx':
            # 问卷星需要列表格式
            fill_data = self._get_fill_data_for_card(card)
            
            # 打印名片字段
            print(f"\n{'='*60}")
            print(f"📇 [问卷星] 名片字段列表 ({len(fill_data)}个):")
            print(f"{'='*60}")
            for i, item in enumerate(fill_data, 1):
                key = item.get('key', '')
                value = str(item.get('value', ''))
                value_preview = value[:30] + '...' if len(value) > 30 else value
                print(f"  {i:2}. \"{key}\" = \"{value_preview}\"")
            print(f"{'='*60}\n")
            
            # 先获取表单字段，打印后再填充
            self._wjx_fill_with_field_log(web_view, card, fill_data)
        
        elif form_type == 'jinshuju':
            # 金数据需要列表格式
            fill_data = self._get_fill_data_for_card(card)
            
            # 打印名片字段
            print(f"\n{'='*60}")
            print(f"📇 [金数据] 名片字段列表 ({len(fill_data)}个):")
            print(f"{'='*60}")
            for i, item in enumerate(fill_data, 1):
                key = item.get('key', '')
                value = str(item.get('value', ''))
                value_preview = value[:30] + '...' if len(value) > 30 else value
                print(f"  {i:2}. \"{key}\" = \"{value_preview}\"")
            print(f"{'='*60}\n")
            
            # 先获取表单字段，打印后再填充
            self._jinshuju_fill_with_field_log(web_view, card, fill_data)
        
        elif form_type == 'shimo':
            # 石墨文档需要列表格式
            fill_data = self._get_fill_data_for_card(card)
            
            # 使用石墨文档专用填充脚本
            js_code = self.generate_shimo_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟3秒后获取结果
            def safe_get_result():
                try:
                    from PyQt6 import sip
                except ImportError:
                    import sip
                if not sip.isdeleted(web_view):
                    self.get_fill_result(web_view, card, 'shimo')
            
            QTimer.singleShot(3000, safe_get_result)
        
        elif form_type == 'credamo':
            # 见数平台需要列表格式
            fill_data = self._get_fill_data_for_card(card)
            
            # 使用见数专用填充脚本
            js_code = self.generate_credamo_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟3秒后获取结果
            def safe_get_result():
                try:
                    from PyQt6 import sip
                except ImportError:
                    import sip
                if not sip.isdeleted(web_view):
                    self.get_fill_result(web_view, card, 'credamo')
            
            QTimer.singleShot(3000, safe_get_result)
        
        elif form_type == 'wenjuan':
            # 问卷网需要列表格式
            fill_data = self._get_fill_data_for_card(card)
            
            # 使用问卷网专用填充脚本
            js_code = self.generate_wenjuan_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟3秒后获取结果
            def safe_get_result():
                try:
                    from PyQt6 import sip
                except ImportError:
                    import sip
                if not sip.isdeleted(web_view):
                    self.get_fill_result(web_view, card, 'wenjuan')
            
            QTimer.singleShot(3000, safe_get_result)
        
        elif form_type == 'fanqier':
            # 番茄表单需要列表格式
            fill_data = self._get_fill_data_for_card(card)
            
            # 先检测页面中的输入框数量
            debug_js = """
            (function() {
                const results = [];
                
                // 测试各种选择器
                const selectors = [
                    '.fq-input__inner',
                    '.fq-input input',
                    'input[type="text"]',
                    'input:not([type])',
                    'textarea'
                ];
                
                selectors.forEach(sel => {
                    const elements = document.querySelectorAll(sel);
                    results.push(`${sel}: ${elements.length}个`);
                });
                
                // 返回调试信息
                return {
                    url: window.location.href,
                    title: document.title,
                    readyState: document.readyState,
                    selectors: results,
                    bodyLength: document.body ? document.body.innerHTML.length : 0
                };
            })();
            """
            
            def debug_callback(result):
                print(f"  🔍 页面检测结果:")
                if result:
                    print(f"    URL: {result.get('url', 'N/A')}")
                    print(f"    标题: {result.get('title', 'N/A')}")
                    print(f"    状态: {result.get('readyState', 'N/A')}")
                    print(f"    Body长度: {result.get('bodyLength', 0)}")
                    print(f"    输入框检测:")
                    for sel_result in result.get('selectors', []):
                        print(f"      {sel_result}")
                else:
                    print(f"    ❌ 无法获取页面信息")
            
            # 先执行调试脚本
            web_view.page().runJavaScript(debug_js, debug_callback)
            
            # 延迟1秒后执行填充脚本
            QTimer.singleShot(1000, lambda: self.execute_fanqier_fill(web_view, fill_data, card))
            
            # 延迟6秒后获取最终结果（1秒调试+1秒执行+4秒等待）
            def safe_get_result():
                try:
                    from PyQt6 import sip
                except ImportError:
                    import sip
                if not sip.isdeleted(web_view):
                    self.get_fill_result(web_view, card, 'fanqier')
            
            QTimer.singleShot(6000, safe_get_result)
        
        elif form_type == 'feishu':
            # 飞书问卷需要列表格式
            fill_data = self._get_fill_data_for_card(card)
            
            # 使用飞书问卷专用填充脚本
            js_code = self.generate_feishu_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟3秒后获取结果
            def safe_get_result():
                try:
                    from PyQt6 import sip
                except ImportError:
                    import sip
                if not sip.isdeleted(web_view):
                    self.get_fill_result(web_view, card, 'feishu')
            
            QTimer.singleShot(3000, safe_get_result)
        
        elif form_type == 'kdocs':
            # WPS表单需要列表格式
            fill_data = self._get_fill_data_for_card(card)
            
            # 使用WPS表单专用填充脚本
            js_code = self.generate_kdocs_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟3秒后获取结果
            def safe_get_result():
                try:
                    from PyQt6 import sip
                except ImportError:
                    import sip
                if not sip.isdeleted(web_view):
                    self.get_fill_result(web_view, card, 'kdocs')
            
            QTimer.singleShot(3000, safe_get_result)
        
        elif form_type == 'tencent_wj':
            # 腾讯问卷需要列表格式
            fill_data = self._get_fill_data_for_card(card)
            
            # 使用腾讯问卷专用填充脚本
            js_code = self.generate_tencent_wj_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟3秒后获取结果
            def safe_get_result():
                try:
                    from PyQt6 import sip
                except ImportError:
                    import sip
                if not sip.isdeleted(web_view):
                    self.get_fill_result(web_view, card, 'tencent_wj')
            
            QTimer.singleShot(3000, safe_get_result)
        
        elif form_type == 'baominggongju':
            # 报名工具需要特殊处理
            print(f"  📱 报名工具处理...")
            
            # 准备名片配置数据（使用用户选择的值）
            fill_data = self._get_fill_data_for_card(card)
            # 转换为报名工具需要的格式（name 而不是 key）
            card_config = [{'name': item['key'], 'value': item['value']} for item in fill_data]
            
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
                    # ⚡️ 传递 form_short_info，确保使用新界面样式
                    form_short_info = getattr(existing_filler, 'form_short_info', None)
                    self.show_baoming_form_page(web_view, existing_filler, filled_data, card, form_short_info)
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
                    # 更新 WebView 的属性，以便 on_webview_loaded 能获取最新数据
                    web_view.setProperty("card_data", latest_card)
                    print(f"  🔄 [填充] 已获取最新名片数据: {card.name}")
                    # 打印第一个配置项的值用于调试
                    if card.configs:
                        print(f"  🔍 配置示例: {card.configs[0].key}={card.configs[0].value}")
        except Exception as e:
            print(f"  ⚠️ 获取最新名片失败: {e}")

        # ⚡️ 关键修复：刷新页面以重置网页状态，让 on_webview_loaded 自动触发填充
        # 这样可以覆盖已填充的数据，而不只是填充空白字段
        print(f"🔄 手动填充触发刷新并等待自动填充: {card.name}")
        web_view.setProperty("status", "loading")  # 重置状态
        web_view.reload()
    
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

        # ⚡️ 使用 _get_fill_data_for_card 处理多值字段（解析 JSON 数组，使用用户选择或默认第一个值）
        fill_data = self._get_fill_data_for_card(card)
        # 转换为报名工具需要的格式（name 而不是 key）
        card_config = [{'name': item['key'], 'value': item['value']} for item in fill_data]

        # 调试打印
        print(f"  📋 [初始化] 名片配置 ({len(card_config)}): {[c['name'] + '=' + str(c['value']) for c in card_config]}")
        
        # 调用设置方法
        self.setup_baoming_tool_in_webview(url, card_config, web_view, card)
    
    def setup_baoming_tool_in_webview(self, url: str, card_config: list, web_view: QWebEngineView, card):
        """在WebView中设置报名工具界面"""
        from core.baoming_tool_filler import BaomingToolFiller
        
        # ⚡️ 关键修复：立即显示加载中页面，防止显示原网页内容
        loading_html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    color: white;
                }
                .loading-container {
                    text-align: center;
                    padding: 40px;
                }
                .spinner {
                    width: 50px;
                    height: 50px;
                    border: 4px solid rgba(255,255,255,0.3);
                    border-top-color: white;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin: 0 auto 24px;
                }
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
                .loading-text {
                    font-size: 18px;
                    font-weight: 500;
                    opacity: 0.9;
                }
                .loading-sub {
                    font-size: 14px;
                    opacity: 0.7;
                    margin-top: 8px;
                }
            </style>
        </head>
        <body>
            <div class="loading-container">
                <div class="spinner"></div>
                <div class="loading-text">正在初始化报名工具...</div>
                <div class="loading-sub">请稍候</div>
            </div>
        </body>
        </html>
        '''
        web_view.setHtml(loading_html)
        
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
        success, msg = filler.initialize(url, card.id)
        if not success:
            print(f"  ❌ [报名工具] 初始化失败: {msg}")
            self.show_baoming_error_page(web_view, msg)
            return
        print(f"  ✅ [报名工具] 初始化成功")
        
        # 尝试恢复登录状态
        if filler.try_restore_login():
            print(f"  ✅ [报名工具] 已恢复登录状态，直接加载表单")
            self.load_baoming_form(web_view, filler, card_config, card)
            return

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
                .tip {{
                    color: #ff6b35;
                    font-size: 12px;
                    margin-top: 16px;
                    padding: 8px 12px;
                    background: #fff7e6;
                    border-radius: 8px;
                    border: 1px solid #ffd591;
                }}
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
                <div class="tip">⚠️ 请用不同微信扫码（因为发布者可能设置一个账号只能填写10份）</div>
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
            try:
                from PyQt6 import sip
            except ImportError:
                import sip
            
            # ⚡️ 安全检查：窗口是否已关闭
            if not self._is_valid():
                print("🛑 窗口已关闭，停止登录轮询")
                timer.stop()
                return
                
            # ⚡️ 安全检查：如果 WebView 已被删除，停止定时器并退出
            if sip.isdeleted(web_view):
                print("🛑 WebView 已销毁，停止登录轮询")
                timer.stop()
                timer.deleteLater()
                return

            try:
                # 再次检查 page 是否存在
                if not web_view.page():
                    timer.stop()
                    return

                poll_count = timer.property("poll_count") or 0
                timer.setProperty("poll_count", poll_count + 1)
                
                # 先检查是否需要刷新二维码
                def handle_refresh_check(need_refresh):
                    # 异步回调中的安全检查
                    if sip.isdeleted(web_view):
                        return
                        
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
            except RuntimeError:
                print("⚠️ WebView 运行时错误，停止轮询")
                timer.stop()
            except Exception as e:
                print(f"⚠️ 登录检查异常: {e}")
                timer.stop()
        
        def do_login_check():
            try:
                from PyQt6 import sip
            except ImportError:
                import sip
            
            # ⚡️ 安全检查：窗口是否已关闭
            if not self._is_valid():
                timer.stop()
                return
                
            # 安全检查
            if sip.isdeleted(web_view) or not web_view.page():
                timer.stop()
                return

            poll_count = timer.property("poll_count") or 0
            
            # 最多轮询120次（4分钟）
            if poll_count >= 120:
                timer.stop()
                try:
                    web_view.page().runJavaScript(
                        "document.getElementById('status').textContent = '登录超时，请点击刷新二维码';"
                        "document.getElementById('status').className = 'status error';"
                    )
                except Exception:
                    pass
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
        
        # 将定时器绑定到 WebView 上，方便销毁时查找（虽然已通过setProperty绑定，但这里是逻辑上的）
        web_view.setProperty("baoming_login_timer", timer)
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
            # 检测是否是 token 失效，如果是则重新显示登录页面
            if filler._is_token_invalid_error(msg):
                print(f"  🔄 [报名工具] Token 失效，重新获取二维码...")
                # 重新获取二维码
                qr_success, qr_data, code = filler.get_qr_code()
                if qr_success:
                    self.show_baoming_login_page(web_view, qr_data)
                    self.start_baoming_login_polling(web_view, filler, card_config, card)
                    return
            self.show_baoming_error_page(web_view, msg)
            return
        
        print(f"  ✅ [报名工具] 表单加载成功，开始匹配填充...")
        # 自动匹配填充
        filled_data = filler.match_and_fill(card_config)
        
        # ⚡️ 合并字段类型信息（已在 filler.match_and_fill 中处理，此处仅作为检查）
        form_fields = filler.form_fields
        print(f"  🔍 [调试] 字段数据检查：filled_data={len(filled_data)}个, form_fields={len(form_fields)}个")
        
        # ⚡️ 优化：直接使用 filled_data 中的 metadata，不再重新匹配（防止 duplicate key 导致匹配错误）
        # 之前的逻辑存在风险：如果 field_key 为空或重复，会导致错误的字段类型覆盖
        '''
        for item in filled_data:
            field_key = item.get('field_key')
            field_name = item.get('field_name', '')
            matched = False
            for field in form_fields:
                # ⚡️ 修复：支持字符串和整数类型的 field_key 比较
                form_field_key = field.get('field_key')
                if str(form_field_key) == str(field_key):
                    item['field_type'] = field.get('field_type', 0)
                    item['options'] = field.get('new_options', [])
                    item['require'] = field.get('require', 0)
                    item['field_desc'] = field.get('field_desc', '')
                    matched = True
                    print(f"     ✅ 字段 \"{field_name}\" -> field_type={item['field_type']}, require={item['require']}")
                    break
            if not matched:
                print(f"     ⚠️ 字段 \"{field_name}\" (key={field_key}) 未找到匹配的类型定义")
        '''
        
        # 生成表单HTML
        # ⚡️ 传递表单简要信息
        form_short_info = getattr(filler, 'form_short_info', None)
        self.show_baoming_form_page(web_view, filler, filled_data, card, form_short_info)
    
    def show_baoming_form_page(self, web_view: QWebEngineView, filler, filled_data: list, card, form_info: dict = None):
        """显示报名工具表单页面（新设计）"""
        import json
        import html as html_escape
        from datetime import datetime
        
        # 字段类型常量（与前端 JS 和后端 API 保持一致）
        FIELD_TYPE_TEXT = 0       # 单行文本
        FIELD_TYPE_NUMBER = 1     # 数字
        FIELD_TYPE_TEXTAREA = 2   # 多行文本
        FIELD_TYPE_DATE = 3       # 日期
        FIELD_TYPE_RADIO = 4      # 单选
        FIELD_TYPE_CHECKBOX = 5   # 多选
        FIELD_TYPE_IMAGE = 6      # 图片上传
        FIELD_TYPE_FILE = 7       # 文件上传
        FIELD_TYPE_ADDRESS = 8    # 地址
        FIELD_TYPE_ID_CARD = 9    # 身份证
        FIELD_TYPE_SELECT = 10    # 下拉选择
        FIELD_TYPE_REGION = 12    # 地区选择
        FIELD_TYPE_PHONE = 13     # 手机号
        FIELD_TYPE_RICH_TEXT = 14 # 富文本/图片上传
        
        # 构造头部 HTML
        header_html = ''
        if form_info:
            title = html_escape.escape(form_info.get('title', ''))
            status_code = form_info.get('status', 1)
            status_text = "进行中" if status_code == 1 else ("未开始" if status_code == 0 else "已结束")
            
            # 格式化时间
            start_ts = form_info.get('start_time', 0)
            end_ts = form_info.get('end_time', 0)
            try:
                start_str = datetime.fromtimestamp(start_ts).strftime('%m/%d %H:%M')
                end_str = datetime.fromtimestamp(end_ts).strftime('%m/%d %H:%M')
                time_range = f"{start_str} - {end_str}"
            except:
                time_range = ""
            
            count = form_info.get('count', 0)
            limit = form_info.get('limit', 0)
            
            owner_pic = form_info.get('owner_pic', '')
            sign_name = html_escape.escape(form_info.get('sign_name', ''))
            
            content_list = form_info.get('content', [])
            content_text = ""
            if content_list and isinstance(content_list, list):
                for item in content_list:
                    if item.get('type') == 'text':
                        val = item.get('value', '')
                        if val:
                            content_text += html_escape.escape(val).replace('\n', '<br>') + "<br>"
            
            header_html = f'''
            <div class="header-card">
                <div class="card-top">
                    <div class="card-title">{title}</div>
                    <div class="card-status">{status_text}</div>
                </div>
                <div class="card-info-row">
                    <div class="info-item" style="margin-right: 16px;">
                        <span class="icon">📝</span> 报名: {time_range}
                    </div>
                    <div class="info-item">
                        <span class="icon">👥</span> 提交: {count}/{limit}
                    </div>
                </div>
                <div class="owner-row">
                    <div class="owner-left">
                        <img src="{owner_pic}" class="owner-avatar">
                        <div class="owner-info">
                            <div class="owner-name">{sign_name}</div>
                        </div>
                    </div>
                </div>
                <div class="card-content">
                    {content_text}
                </div>
            </div>
            '''
        else:
            # 获取表单标题（旧逻辑）
            form_title = filler.get_form_title() if hasattr(filler, 'get_form_title') else ''
            form_title_escaped = html_escape.escape(form_title) if form_title else ''
            header_html = f'''
            <div class="header">
                <div class="title">{form_title_escaped or '📋 报名工具表单'}</div>
            </div>
            '''
        
        # 生成表单字段HTML
        fields_html = ''
        for i, field in enumerate(filled_data):
            field_name = field.get('field_name', '')
            field_key = field.get('field_key', '')
            field_value = field.get('field_value', '')
            field_type = field.get('field_type', 0)
            options = field.get('options', [])
            require = field.get('require', 0)
            field_desc = field.get('field_desc', '')
            
            # ⚡️ 修复：确保 field_value 是字符串（用于渲染）
            # 对于多选框，将数组转换为逗号分隔的字符串
            if isinstance(field_value, list):
                if field_type == FIELD_TYPE_CHECKBOX:
                    # 多选框：数组转逗号分隔字符串
                    field_value = ','.join(str(v) for v in field_value if v)
                else:
                    # 其他类型：取第一个值
                    field_value = field_value[0] if field_value else ''
            elif not isinstance(field_value, str):
                field_value = str(field_value) if field_value else ''
            
            # HTML 转义
            field_name_escaped = html_escape.escape(str(field_name))
            field_key_escaped = html_escape.escape(str(field_key))
            field_value_escaped = html_escape.escape(str(field_value))
            field_desc_escaped = html_escape.escape(str(field_desc)) if field_desc else ''
            
            # 必填标记
            require_mark = '<span class="require-mark">*</span>' if require else ''
            # 字段描述
            desc_html = f'<div class="field-desc">{field_desc_escaped}</div>' if field_desc_escaped else ''
            
            # ⚡️ 图片上传类型判断：严格根据 field_type 判断
            # 1. field_type == 6 (图片上传)
            # 2. field_type == 14 (富文本/图片上传)
            # 注意：不再根据字段名关键词匹配，因为会导致误判（如"图片更换"被识别为图片上传）
            is_image_field = field_type in [FIELD_TYPE_IMAGE, FIELD_TYPE_RICH_TEXT]
            
            # 根据字段类型生成不同的输入组件
            if field_type == FIELD_TYPE_CHECKBOX and options:
                # 多选框
                checkbox_html = ''
                selected_values = [v.strip() for v in field_value.split(',') if v.strip()]
                for opt in options:
                    opt_key = html_escape.escape(str(opt.get('key', '')))
                    opt_value = html_escape.escape(str(opt.get('value', '')))
                    # 检查是否已选中（匹配 key 或 value）
                    is_checked = opt.get('key', '') in selected_values or opt.get('value', '') in selected_values
                    checked_attr = 'checked' if is_checked else ''
                    checkbox_html += f'''
                        <label class="checkbox-item">
                            <input type="checkbox" name="field_{i}" value="{opt_key}" data-text="{opt_value}" {checked_attr}>
                            <span class="checkbox-label">{opt_value}</span>
                        </label>
                    '''
                fields_html += f'''
                <div class="field-group">
                    <div class="field-header">
                        <label>{require_mark}{field_name_escaped}</label>
                    </div>
                    {desc_html}
                    <div class="checkbox-group" id="field_{i}" data-key="{field_key_escaped}" data-name="{field_name_escaped}" data-type="checkbox">
                        {checkbox_html}
                    </div>
                </div>
                '''
            elif field_type == FIELD_TYPE_RADIO and options:
                # 单选框
                radio_html = ''
                for opt in options:
                    opt_key = html_escape.escape(str(opt.get('key', '')))
                    opt_value = html_escape.escape(str(opt.get('value', '')))
                    is_checked = opt.get('key', '') == field_value or opt.get('value', '') == field_value
                    checked_attr = 'checked' if is_checked else ''
                    radio_html += f'''
                        <label class="radio-item">
                            <input type="radio" name="field_{i}" value="{opt_key}" data-text="{opt_value}" {checked_attr}>
                            <span class="radio-label">{opt_value}</span>
                        </label>
                    '''
                fields_html += f'''
                <div class="field-group">
                    <div class="field-header">
                        <label>{require_mark}{field_name_escaped}</label>
                    </div>
                    {desc_html}
                    <div class="radio-group" id="field_{i}" data-key="{field_key_escaped}" data-name="{field_name_escaped}" data-type="radio">
                        {radio_html}
                    </div>
                </div>
                '''
            elif is_image_field:
                # 图片上传（根据 field_type 或字段名识别）
                preview_html = f'<img src="{field_value_escaped}" class="image-preview" id="preview_{i}">' if field_value else f'<div class="image-placeholder" id="preview_{i}">📷 点击上传图片</div>'
                fields_html += f'''
                <div class="field-group">
                    <div class="field-header">
                        <label>{require_mark}{field_name_escaped}</label>
                    </div>
                    {desc_html}
                    <div class="image-upload-container" id="field_{i}" data-key="{field_key_escaped}" data-name="{field_name_escaped}" data-type="image">
                        <input type="file" accept="image/*" id="file_{i}" class="file-input" onchange="handleImageUpload({i}, this)">
                        <div class="image-preview-box" onclick="document.getElementById('file_{i}').click()">
                            {preview_html}
                        </div>
                        <input type="hidden" id="url_{i}" value="{field_value_escaped}">
                        <div class="upload-status" id="status_{i}"></div>
                    </div>
                </div>
                '''
            else:
                # 默认：文本输入框
                input_type = 'tel' if field_type == FIELD_TYPE_PHONE else 'text'
                fields_html += f'''
                <div class="field-group">
                    <div class="field-header">
                        <label>{require_mark}{field_name_escaped}</label>
                    </div>
                    {desc_html}
                    <input type="{input_type}"
                           id="field_{i}"
                           data-key="{field_key_escaped}"
                           data-name="{field_name_escaped}"
                           data-type="text"
                           value="{field_value_escaped}"
                           placeholder="请输入{field_name_escaped}">
                </div>
                '''
        
        # 标题区域HTML（只在没有新header时显示）
        title_section = ''
        if not form_info:
            form_title = filler.get_form_title() if hasattr(filler, 'get_form_title') else ''
            form_title_escaped = html_escape.escape(form_title) if form_title else ''
            if form_title_escaped:
                title_section = f'''
                    <div class="form-title-section">
                        <div class="form-title-label">📝 表单标题</div>
                        <div class="form-title-text">{form_title_escaped}</div>
                    </div>
                '''
        
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
                /* Header Card Styles */
                .header-card {{
                    background: #fff;
                    border-radius: 16px;
                    padding: 24px;
                    margin-bottom: 24px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                }}
                .card-top {{
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 16px;
                }}
                .card-title {{
                    font-size: 20px;
                    font-weight: 700;
                    color: #1D1D1F;
                    line-height: 1.4;
                    flex: 1;
                    margin-right: 12px;
                }}
                .card-status {{
                    background: #E6F4FF;
                    color: #007AFF;
                    font-size: 13px;
                    padding: 4px 12px;
                    border-radius: 4px;
                    font-weight: 500;
                    white-space: nowrap;
                }}
                .card-info-row {{
                    display: flex;
                    align-items: center;
                    margin-bottom: 8px;
                    color: #666;
                    font-size: 14px;
                }}
                .info-item {{
                    display: flex;
                    align-items: center;
                }}
                .icon {{
                    margin-right: 8px;
                    font-size: 16px;
                }}
                .owner-row {{
                    display: flex;
                    align-items: center;
                    margin: 12px 0 16px 0;
                }}
                .owner-left {{
                    display: flex;
                    align-items: center;
                }}
                .owner-avatar {{
                    width: 32px;
                    height: 32px;
                    border-radius: 16px;
                    margin-right: 10px;
                    object-fit: cover;
                }}
                .owner-info {{
                    display: flex;
                    flex-direction: column;
                }}
                .owner-name {{
                    font-size: 14px;
                    font-weight: 600;
                    color: #333;
                }}
                .card-content {{
                    font-size: 14px;
                    color: #444;
                    line-height: 1.6;
                    margin-top: 16px;
                    padding-top: 16px;
                    border-top: 1px solid #F0F0F0;
                    white-space: pre-wrap;
                }}
                
                /* Old Header */
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
                .form-title-section {{
                    background: linear-gradient(135deg, #fff7e6 0%, #fffbe6 100%);
                    border: 1px solid #ffe58f;
                    border-radius: 12px;
                    padding: 16px 20px;
                    margin-bottom: 20px;
                }}
                .form-title-label {{
                    font-size: 12px;
                    color: #d48806;
                    font-weight: 600;
                    margin-bottom: 8px;
                }}
                .form-title-text {{
                    font-size: 16px;
                    font-weight: 600;
                    color: #ad6800;
                    line-height: 1.5;
                    word-break: break-all;
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
                input::placeholder {{
                    color: #bfbfbf;
                }}
                .require-mark {{
                    color: #f5222d;
                    margin-right: 4px;
                }}
                .field-desc {{
                    font-size: 12px;
                    color: #8c8c8c;
                    margin-bottom: 8px;
                    line-height: 1.4;
                }}
                /* 多选框样式 */
                .checkbox-group, .radio-group {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 12px;
                }}
                .checkbox-item, .radio-item {{
                    display: flex;
                    align-items: center;
                    cursor: pointer;
                    padding: 10px 16px;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    background: #fff;
                    transition: all 0.2s;
                    flex: 0 0 auto;
                    min-width: 100px;
                }}
                .checkbox-item:hover, .radio-item:hover {{
                    border-color: #1890ff;
                    background: #f0f7ff;
                }}
                .checkbox-item input, .radio-item input {{
                    width: 18px;
                    height: 18px;
                    margin-right: 8px;
                    cursor: pointer;
                    accent-color: #1890ff;
                }}
                .checkbox-item input:checked + .checkbox-label,
                .radio-item input:checked + .radio-label {{
                    color: #1890ff;
                    font-weight: 600;
                }}
                .checkbox-item:has(input:checked),
                .radio-item:has(input:checked) {{
                    border-color: #1890ff;
                    background: #e6f4ff;
                }}
                .checkbox-label, .radio-label {{
                    font-size: 14px;
                    color: #333;
                    user-select: none;
                }}
                /* 图片上传样式 */
                .image-upload-container {{
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }}
                .file-input {{
                    display: none;
                }}
                .image-preview-box {{
                    width: 100%;
                    min-height: 120px;
                    border: 2px dashed #d9d9d9;
                    border-radius: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    background: #fafafa;
                    transition: all 0.2s;
                    overflow: hidden;
                }}
                .image-preview-box:hover {{
                    border-color: #1890ff;
                    background: #f0f7ff;
                }}
                .image-placeholder {{
                    color: #8c8c8c;
                    font-size: 14px;
                    text-align: center;
                    padding: 20px;
                }}
                .image-preview {{
                    max-width: 100%;
                    max-height: 200px;
                    object-fit: contain;
                }}
                .upload-status {{
                    font-size: 12px;
                    color: #8c8c8c;
                }}
                .upload-status.uploading {{
                    color: #1890ff;
                }}
                .upload-status.success {{
                    color: #52c41a;
                }}
                .upload-status.error {{
                    color: #f5222d;
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
                .logout-btn {{
                    width: 100%;
                    padding: 12px;
                    background: #fff;
                    color: #666;
                    border: 1px solid #d9d9d9;
                    border-radius: 8px;
                    font-size: 14px;
                    cursor: pointer;
                    margin-top: 12px;
                    transition: all 0.2s;
                }}
                .logout-btn:hover {{
                    color: #ff4d4f;
                    border-color: #ff4d4f;
                    background: #fff1f0;
                }}
                .result-banner {{
                    position: fixed;
                    top: -80px;
                    left: 0;
                    right: 0;
                    z-index: 9999;
                    text-align: center;
                    font-size: 15px;
                    padding: 14px 20px;
                    font-weight: 600;
                    transition: top 0.35s cubic-bezier(0.4, 0, 0.2, 1);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                }}
                .result-banner.show {{
                    top: 0;
                }}
                .result-banner.success {{
                    background: linear-gradient(135deg, #52c41a, #73d13d);
                    color: #fff;
                }}
                .result-banner.error {{
                    background: linear-gradient(135deg, #f5222d, #ff4d4f);
                    color: #fff;
                }}
            </style>
        </head>
        <body>
            <div class="result-banner" id="resultBanner"></div>
            {header_html}
            <div class="form-container">
                {title_section}
                {fields_html}
                <button class="submit-btn" onclick="submitForm()">📤 立即提交表单</button>
                <button class="logout-btn" onclick="logoutAccount()">🔄 退出登录 / 切换账号</button>
            </div>
            
            <script>
                // 退出登录处理
                function logoutAccount() {{
                    if (confirm('确定要退出登录并切换账号吗？')) {{
                        window.__logoutRequest__ = true;
                    }}
                }}
                
                // 图片上传处理
                function handleImageUpload(index, input) {{
                    var file = input.files[0];
                    if (!file) return;
                    
                    var statusEl = document.getElementById('status_' + index);
                    var previewEl = document.getElementById('preview_' + index);
                    var urlInput = document.getElementById('url_' + index);
                    
                    // 显示预览
                    var reader = new FileReader();
                    reader.onload = function(e) {{
                        previewEl.outerHTML = '<img src="' + e.target.result + '" class="image-preview" id="preview_' + index + '">';
                    }};
                    reader.readAsDataURL(file);
                    
                    // 上传到 OSS
                    statusEl.textContent = '正在上传...';
                    statusEl.className = 'upload-status uploading';
                    
                    var formData = new FormData();
                    var timestamp = Date.now();
                    var filename = 'test/upload/' + timestamp + '_' + file.name;
                    
                    formData.append('key', filename);
                    formData.append('OSSAccessKeyId', 'LTAI5tHzG8jWeAZG2mP2MFvS');
                    formData.append('policy', 'eyJleHBpcmF0aW9uIjoiMjEwMC0wMS0wMVQxMjowMDowMC4wMDBaIiwiY29uZGl0aW9ucyI6W1siY29udGVudC1sZW5ndGgtcmFuZ2UiLDAsMTA0ODU3NjAwMF1dfQ==');
                    formData.append('signature', 'jdjUfw+5vYWYkzjyiQYXveiP1nA=');
                    formData.append('success_action_status', '200');
                    formData.append('file', file);
                    
                    fetch('https://taiguoossanmo.oss-accelerate.aliyuncs.com', {{
                        method: 'POST',
                        body: formData
                    }})
                    .then(function(response) {{
                        if (response.ok || response.status === 204) {{
                            var ossUrl = 'https://oss.fang-qingsong.com/' + filename;
                            urlInput.value = ossUrl;
                            statusEl.textContent = '上传成功';
                            statusEl.className = 'upload-status success';
                            console.log('图片上传成功:', ossUrl);
                        }} else {{
                            throw new Error('上传失败: ' + response.status);
                        }}
                    }})
                    .catch(function(error) {{
                        statusEl.textContent = '上传失败: ' + error.message;
                        statusEl.className = 'upload-status error';
                        console.error('图片上传失败:', error);
                    }});
                }}
                
                function submitForm() {{
                    var btn = document.querySelector('.submit-btn');
                    btn.disabled = true;
                    btn.textContent = '正在提交...';
                    
                    var data = [];
                    
                    // 处理文本输入框
                    var textInputs = document.querySelectorAll('input[data-type="text"]');
                    textInputs.forEach(function(input) {{
                        var key = input.getAttribute('data-key');
                        if (/^\d+$/.test(key)) key = parseInt(key, 10);
                        data.push({{
                            field_name: input.getAttribute('data-name'),
                            field_key: key,
                            field_value: input.value,
                            ignore: 0
                        }});
                    }});
                    
                    // 处理多选框（报名工具需要数组格式）
                    var checkboxGroups = document.querySelectorAll('.checkbox-group');
                    checkboxGroups.forEach(function(group) {{
                        var key = group.getAttribute('data-key');
                        if (/^\d+$/.test(key)) key = parseInt(key, 10);
                        
                        var checkedValues = []; // 文本值
                        var checkedKeys = [];   // Key值
                        
                        group.querySelectorAll('input:checked').forEach(function(cb) {{
                            checkedKeys.push(cb.value);
                            // 优先使用 data-text，降级使用 label
                            var text = cb.getAttribute('data-text');
                            if (!text && cb.nextElementSibling) {{
                                text = cb.nextElementSibling.textContent;
                            }}
                            checkedValues.push(text || '');
                        }});
                        
                        data.push({{
                            field_name: group.getAttribute('data-name'),
                            field_key: key,
                            field_value: checkedValues,
                            new_field_value: checkedKeys,
                            ignore: 0
                        }});
                    }});
                    
                    // 处理单选框（报名工具需要 new_field_value 字段）
                    var radioGroups = document.querySelectorAll('.radio-group');
                    radioGroups.forEach(function(group) {{
                        var key = group.getAttribute('data-key');
                        if (/^\d+$/.test(key)) key = parseInt(key, 10);
                        
                        var checkedRadio = group.querySelector('input:checked');
                        var valText = '';
                        var valKey = '';
                        
                        if (checkedRadio) {{
                            valKey = checkedRadio.value;
                            valText = checkedRadio.getAttribute('data-text');
                            if (!valText && checkedRadio.nextElementSibling) {{
                                valText = checkedRadio.nextElementSibling.textContent;
                            }}
                        }}
                        
                        data.push({{
                            field_name: group.getAttribute('data-name'),
                            field_key: key,
                            field_value: valText || '',
                            new_field_value: valKey || '',
                            ignore: 0
                        }});
                    }});
                    
                    // 处理图片上传
                    var imageContainers = document.querySelectorAll('.image-upload-container');
                    imageContainers.forEach(function(container) {{
                        var key = container.getAttribute('data-key');
                        if (/^\d+$/.test(key)) key = parseInt(key, 10);
                        var urlInput = container.querySelector('input[type="hidden"]');
                        data.push({{
                            field_name: container.getAttribute('data-name'),
                            field_key: key,
                            field_value: urlInput ? urlInput.value : '',
                            ignore: 0
                        }});
                    }});
                    
                    window.__submitData__ = data;
                    window.__submitReady__ = true;
                }}
                
                function showResult(success, message) {{
                    var banner = document.getElementById('resultBanner');
                    var btn = document.querySelector('.submit-btn');
                    banner.textContent = message;
                    banner.className = 'result-banner ' + (success ? 'success' : 'error');
                    // 触发重排后添加 show 类，实现滑入动画
                    void banner.offsetHeight;
                    banner.classList.add('show');
                    btn.disabled = false;
                    btn.textContent = '📤 立即提交表单';
                    // 5秒后自动收起
                    clearTimeout(window.__bannerTimer__);
                    window.__bannerTimer__ = setTimeout(function() {{
                        banner.classList.remove('show');
                    }}, 5000);
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
        web_view.setProperty("baoming_submit_timer", timer) # 绑定以便清理
        
        def check_submit():
            try:
                from PyQt6 import sip
            except ImportError:
                import sip
            
            # ⚡️ 安全检查：窗口是否已关闭
            if not self._is_valid():
                timer.stop()
                return
                
            if sip.isdeleted(web_view) or not web_view.page():
                timer.stop()
                timer.deleteLater()
                return

            try:
                # ⚡️ 先检查是否有退出登录请求
                def check_logout(logout_requested):
                    if sip.isdeleted(web_view) or not self._is_valid():
                        return
                    if logout_requested:
                        timer.stop()
                        self.handle_baoming_logout(web_view, card)
                    else:
                        # 再检查是否有提交请求
                        web_view.page().runJavaScript(
                            "window.__submitReady__ === true",
                            lambda ready: self.handle_baoming_submit(web_view, filler, card, timer) if ready and not sip.isdeleted(web_view) and self._is_valid() else None
                        )
                
                web_view.page().runJavaScript(
                    "window.__logoutRequest__ === true",
                    check_logout
                )
            except RuntimeError:
                timer.stop()
            except Exception as e:
                print(f"⚠️ 提交检查异常: {e}")
                timer.stop()
        
        timer.timeout.connect(check_submit)
        timer.start(500)  # 每500ms检查一次
        
        web_view.setProperty("submit_timer", timer)
    
    def handle_baoming_logout(self, web_view: QWebEngineView, card):
        """处理报名工具退出登录"""
        print(f"  🔄 [报名工具] 用户请求退出登录，准备切换账号...")
        
        # 1. 停止所有定时器
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
        
        # 2. 清除登录状态和持久化存储的Token
        filler = web_view.property("baoming_filler")
        if filler:
            # ⚡️ 关键：调用 _clear_token() 删除本地存储的token
            if hasattr(filler, '_clear_token'):
                filler._clear_token()
                print(f"  🗑️ [报名工具] 已清除本地存储的Token")
            # 清除内存中的登录状态
            if hasattr(filler, 'api') and hasattr(filler.api, 'access_token'):
                filler.api.access_token = None
            if hasattr(filler, 'api') and hasattr(filler.api, 'user_info'):
                filler.api.user_info = None
        
        web_view.setProperty("baoming_filler", None)
        web_view.setProperty("baoming_card_config", None)
        web_view.setProperty("baoming_filled_data", None)
        web_view.setProperty("baoming_page_rendered", False)
        
        # 3. 获取原始URL
        original_url = web_view.property("original_url")
        if not original_url:
            # 尝试从其他地方获取
            original_url = web_view.property("baoming_url")
        
        print(f"  🔄 [报名工具] 重新初始化，URL: {original_url}")
        
        # 4. 显示加载提示
        loading_html = """
        <!DOCTYPE html>
        <html>
        <body style="margin:0;padding:0;background:#f0f2f5;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;">
            <div style="text-align:center;color:#666;">
                <div style="font-size:32px;margin-bottom:16px;">🔄</div>
                <div>正在切换账号...</div>
            </div>
        </body>
        </html>
        """
        web_view.setHtml(loading_html)
        
        # 5. 延迟重新初始化
        QTimer.singleShot(500, lambda: self.init_baoming_tool_for_webview(web_view, original_url, card))
    
    def handle_baoming_submit(self, web_view: QWebEngineView, filler, card, timer):
        """处理报名工具提交"""
        # ⚡️ 安全检查
        if not self._is_valid():
            return
        
        try:
            from PyQt6 import sip
        except ImportError:
            import sip
        
        if sip.isdeleted(web_view):
            return
        
        # 停止检查
        timer.stop()
        
        # 重置标志
        web_view.page().runJavaScript("window.__submitReady__ = false;")
        
        # 获取提交数据
        def do_submit(data):
            # ⚡️ 安全检查
            if not self._is_valid() or sip.isdeleted(web_view):
                return
            
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
    
    def _inject_mobile_responsive_css(self, web_view: QWebEngineView, link_data):
        """为 WebView 注入移动端响应式 CSS，实现自适应布局"""
        url = link_data.url if link_data else ""
        form_type = self.detect_form_type(url)
        
        # 针对不同平台注入不同的适配样式
        if form_type == 'kdocs':
            # WPS / 金山文档表单适配 - 使用缩放和强制样式
            # 先设置 WebView 的缩放因子
            web_view.setZoomFactor(0.85)  # 缩小到 85%，适应小窗口
            
            inject_js = """
            (function() {
                // 设置 viewport
                var meta = document.querySelector('meta[name="viewport"]');
                if (!meta) {
                    meta = document.createElement('meta');
                    meta.name = 'viewport';
                    document.head.appendChild(meta);
                }
                meta.content = 'width=device-width, initial-scale=0.8, maximum-scale=2.0, user-scalable=yes';
                
                // 注入响应式 CSS
                var style = document.createElement('style');
                style.id = 'auto-fill-responsive';
                style.textContent = `
                    /* 移动端自适应 - WPS/KDocs 专用 */
                    html, body {
                        width: 100% !important;
                        max-width: 100vw !important;
                        overflow-x: hidden !important;
                        margin: 0 !important;
                        padding: 0 !important;
                    }
                    /* 主容器强制自适应 */
                    #app, #root, .app, .root, main, .main,
                    [class*="container"], [class*="wrapper"], [class*="content"] {
                        width: 100% !important;
                        max-width: 100% !important;
                        min-width: 0 !important;
                        box-sizing: border-box !important;
                        overflow-x: hidden !important;
                    }
                    /* 表单主体 */
                    [class*="form"], [class*="Form"], [class*="question"],
                    [class*="field"], [class*="Field"], [class*="item"] {
                        width: 100% !important;
                        max-width: 100% !important;
                        box-sizing: border-box !important;
                    }
                    /* 输入框自适应 */
                    input, textarea, select, [class*="input"], [class*="Input"] {
                        width: 100% !important;
                        max-width: 100% !important;
                        box-sizing: border-box !important;
                    }
                    /* 固定宽度元素处理 */
                    [style*="width: 6"], [style*="width: 7"], [style*="width: 8"],
                    [style*="width:6"], [style*="width:7"], [style*="width:8"] {
                        width: 100% !important;
                        max-width: 100% !important;
                    }
                `;
                
                // 移除旧的样式
                var oldStyle = document.getElementById('auto-fill-responsive');
                if (oldStyle) oldStyle.remove();
                
                document.head.appendChild(style);
                console.log('[AutoFill] WPS/KDocs 移动端适配 CSS 已注入');
            })();
            """
            web_view.page().runJavaScript(inject_js)
            print(f"  📱 已为 WPS/KDocs 设置缩放 0.85 并注入移动端适配 CSS")
            
        elif form_type in ['wjx', 'jinshuju', 'shimo', 'fanqier', 'feishu']:
            # 通用表单平台适配 - 这些平台本身已有响应式设计
            pass  # 不需要额外处理

    def detect_form_type(self, url: str) -> str:
        """检测表单类型"""
        if 'docs.qq.com/form' in url:
            return 'tencent_docs'
        elif 'mikecrm.com' in url or 'mike-x.com' in url:
            return 'mikecrm'
        elif 'wjx.cn' in url or 'wjx.top' in url:
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
        elif 'kdocs.cn' in url or 'wps.cn' in url or 'wps.com' in url:
            return 'kdocs'
        elif 'wj.qq.com' in url:
            return 'tencent_wj'
        else:
            return 'unknown'
    
    def get_or_create_profile(self, card_id: str, form_type: str) -> QWebEngineProfile:
        """
        获取或创建 Profile 实例
        
        同一个名片 + 同一个平台共享同一个 Profile 实例，
        这样同一名片访问同一平台的不同链接可以共享登录状态（cookie、token等）
        
        Args:
            card_id: 名片ID
            form_type: 平台类型（由 detect_form_type 返回）
            
        Returns:
            QWebEngineProfile: Profile 实例
        """
        cache_key = f"{card_id}_{form_type}"
        
        if cache_key in self.profile_cache:
            print(f"  🔄 复用已有 Profile: {cache_key}")
            return self.profile_cache[cache_key]
        
        # 创建新的 Profile
        storage_name = f"profile_store_{cache_key}"
        # 注意：这里不传入 parent，让 profile 的生命周期由 self.profile_cache 管理
        profile = QWebEngineProfile(storage_name, self)
        
        # 设置为磁盘缓存模式，允许持久化 Cookie
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
        
        # 设置中文语言
        profile.setHttpAcceptLanguage("zh-CN,zh;q=0.9,en;q=0.8")
        
        # 设置 User-Agent
        user_agent = profile.httpUserAgent()
        if 'zh-CN' not in user_agent:
            profile.setHttpUserAgent(user_agent + " Language/zh-CN")
        
        # 缓存 Profile
        self.profile_cache[cache_key] = profile
        print(f"  ✅ 创建新 Profile: {cache_key} (共 {len(self.profile_cache)} 个)")
        
        return profile
    
    def _jinshuju_fill_with_field_log(self, web_view, card, fill_data: list):
        """金数据填充：先获取表单字段打印日志，再执行填充"""
        import json
        
        try:
            from PyQt6 import sip
        except ImportError:
            import sip
        
        if not self._is_valid() or sip.isdeleted(web_view):
            return
        
        # 获取表单字段的 JavaScript（针对金数据结构优化）
        get_fields_js = """
(function() {
    var fields = [];
    var seenTitles = {};
    
    var allInputs = document.querySelectorAll('input, textarea');
    console.log('[日志] 找到 ' + allInputs.length + ' 个 input/textarea 元素');
    
    for (var i = 0; i < allInputs.length; i++) {
        var input = allInputs[i];
        if (input.type === 'hidden') continue;
        
        var title = '';
        
        // 【方法1】金数据专用：找 .field-container 或 [data-api-code] 容器
        var fieldContainer = input.closest('.field-container, [data-api-code]');
        if (fieldContainer) {
            // 在 .ant-form-item-label 里找标题
            var labelEl = fieldContainer.querySelector('.ant-form-item-label .label-item');
            if (labelEl) {
                title = (labelEl.innerText || labelEl.textContent || '').trim();
            }
            // 备选：直接找 label 标签
            if (!title) {
                var label = fieldContainer.querySelector('.ant-form-item-label label');
                if (label) {
                    title = (label.innerText || label.textContent || '').trim();
                }
            }
        }
        
        // 【方法2】通用：向上查找 ant-form-item
        if (!title) {
            var parent = input.parentElement;
            for (var depth = 0; depth < 10 && parent && !title; depth++) {
                if (parent.classList && parent.classList.contains('ant-form-item')) {
                    var labelEl = parent.querySelector('.ant-form-item-label');
                    if (labelEl) {
                        title = (labelEl.innerText || labelEl.textContent || '').trim();
                    }
                    break;
                }
                parent = parent.parentElement;
            }
        }
        
        // 清理标题并去重
        if (title) {
            title = title.replace(/[*？?！!。.]+$/g, '').trim();
            if (title && !seenTitles[title]) {
                seenTitles[title] = true;
                fields.push(title);
                console.log('[日志] 字段 ' + fields.length + ': ' + title);
            }
        }
    }
    return JSON.stringify(fields);
})();
"""
        
        def on_fields_received(result):
            try:
                from PyQt6 import sip
            except ImportError:
                import sip
            
            if not self._is_valid() or sip.isdeleted(web_view):
                return
            
            # 打印表单字段
            try:
                form_fields = json.loads(result) if result else []
            except:
                form_fields = []
            
            print(f"{'='*60}")
            print(f"📋 [金数据] 表单字段列表 ({len(form_fields)}个):")
            print(f"{'='*60}")
            for i, title in enumerate(form_fields, 1):
                print(f"  {i:2}. \"{title}\"")
            if not form_fields:
                print("  (未检测到表单字段，可能页面还在加载)")
            print(f"{'='*60}\n")
            
            # 执行填充
            js_code = self.generate_jinshuju_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟获取结果
            def safe_get_result():
                try:
                    from PyQt6 import sip
                except ImportError:
                    import sip
                if not sip.isdeleted(web_view) and self._is_valid():
                    self.get_fill_result(web_view, card, 'jinshuju')
            
            QTimer.singleShot(3000, safe_get_result)
        
        # 带重试的获取字段
        retry_count = [0]
        max_retries = 3
        
        def get_fields():
            if not self._is_valid() or sip.isdeleted(web_view):
                return
            web_view.page().runJavaScript(get_fields_js, handle_result)
        
        def handle_result(result):
            try:
                fields = json.loads(result) if result else []
            except:
                fields = []
            
            # 如果没获取到字段且还有重试次数，继续等待
            if len(fields) == 0 and retry_count[0] < max_retries:
                retry_count[0] += 1
                print(f"  ⏳ 等待表单加载... (重试 {retry_count[0]}/{max_retries})")
                QTimer.singleShot(1500, get_fields)
            else:
                on_fields_received(result)
        
        # 首次延迟 500ms 后获取字段
        QTimer.singleShot(500, get_fields)
    
    def _wjx_fill_with_field_log(self, web_view, card, fill_data: list):
        """问卷星填充：先获取表单字段打印日志，再执行填充"""
        import json
        
        try:
            from PyQt6 import sip
        except ImportError:
            import sip
        
        if not self._is_valid() or sip.isdeleted(web_view):
            return
        
        # 获取表单字段的 JavaScript（复用填充脚本的逻辑）
        get_fields_js = """
(function() {
    var fields = [];
    var seenTitles = {};
    
    // 辅助函数：从元素中提取标题
    function extractLabelText(el) {
        if (!el) return '';
        var fullText = (el.innerText || el.textContent || '').trim();
        var firstLine = fullText.split('\\n')[0].trim();
        if (firstLine && firstLine !== '.' && firstLine.length >= 2 && firstLine.length < 100) {
            return firstLine;
        }
        return '';
    }
    
    var allInputs = document.querySelectorAll('input, textarea');
    console.log('[日志] 找到 ' + allInputs.length + ' 个 input/textarea 元素');
    
    for (var i = 0; i < allInputs.length; i++) {
        var input = allInputs[i];
        // 宽松检测：只排除 hidden 类型
        if (input.type === 'hidden') continue;
        
        var title = '';
        
        // 方法1: aria-labelledby
        var ariaLabelledBy = input.getAttribute('aria-labelledby');
        if (ariaLabelledBy) {
            var ids = ariaLabelledBy.split(' ');
            for (var j = 0; j < ids.length && !title; j++) {
                var el = document.getElementById(ids[j]);
                if (el) title = extractLabelText(el);
            }
        }
        
        // 方法2: 向上查找问题容器的标题
        if (!title) {
            var parent = input.parentElement;
            for (var depth = 0; depth < 10 && parent && !title; depth++) {
                var cls = (parent.className || '').toLowerCase();
                if (cls.indexOf('field') >= 0 || cls.indexOf('question') >= 0 || cls.indexOf('topic') >= 0) {
                    var labelEl = parent.querySelector('.field-label, .topichtml, .topic-title, .q-title, .label:not(.note)');
                    if (!labelEl) labelEl = parent.querySelector('label');
                    if (labelEl) title = extractLabelText(labelEl);
                    break;
                }
                parent = parent.parentElement;
            }
        }
        
        // 方法3: 关联的 label 标签
        if (!title && input.id) {
            var label = document.querySelector('label[for="' + input.id + '"]');
            if (label) title = extractLabelText(label);
        }
        
        // 清理标题并去重
        if (title) {
            title = title.replace(/[*？?！!。.]+$/g, '').trim();
            if (title && !seenTitles[title]) {
                seenTitles[title] = true;
                fields.push(title);
            }
        }
    }
    return JSON.stringify(fields);
})();
"""
        
        def on_fields_received(result):
            try:
                from PyQt6 import sip
            except ImportError:
                import sip
            
            if not self._is_valid() or sip.isdeleted(web_view):
                return
            
            # 打印表单字段
            try:
                form_fields = json.loads(result) if result else []
            except:
                form_fields = []
            
            print(f"{'='*60}")
            print(f"📋 [问卷星] 表单字段列表 ({len(form_fields)}个):")
            print(f"{'='*60}")
            for i, title in enumerate(form_fields, 1):
                print(f"  {i:2}. \"{title}\"")
            if not form_fields:
                print("  (未检测到表单字段，可能页面还在加载)")
            print(f"{'='*60}\n")
            
            # 执行填充
            js_code = self.generate_wjx_fill_script(fill_data)
            web_view.page().runJavaScript(js_code)
            
            # 延迟获取结果
            def safe_get_result():
                try:
                    from PyQt6 import sip
                except ImportError:
                    import sip
                if not sip.isdeleted(web_view) and self._is_valid():
                    self.get_fill_result(web_view, card, 'wjx')
            
            QTimer.singleShot(3000, safe_get_result)
        
        # 带重试的获取字段
        retry_count = [0]
        max_retries = 3
        
        def get_fields():
            if not self._is_valid() or sip.isdeleted(web_view):
                return
            web_view.page().runJavaScript(get_fields_js, handle_result)
        
        def handle_result(result):
            try:
                fields = json.loads(result) if result else []
            except:
                fields = []
            
            # 如果没获取到字段且还有重试次数，继续等待
            if len(fields) == 0 and retry_count[0] < max_retries:
                retry_count[0] += 1
                print(f"  ⏳ 等待表单加载... (重试 {retry_count[0]}/{max_retries})")
                QTimer.singleShot(1500, get_fields)
            else:
                on_fields_received(result)
        
        # 首次延迟 500ms 后获取字段
        QTimer.singleShot(500, get_fields)
    
    def generate_wjx_fill_script(self, fill_data: list) -> str:
        """生成问卷星(wjx.cn/wjx.top)专用的填充脚本 - 使用共享匹配算法"""
        import json
        from core.tencent_docs_filler import TencentDocsFiller
        
        fill_data_json = json.dumps(fill_data, ensure_ascii=False)
        
        # 获取共享的匹配算法（cleanText, splitKeywords, matchKeyword）
        shared_algorithm = TencentDocsFiller.get_shared_match_algorithm()
        
        js_code = f"""
(function() {{
    console.log('🚀 开始填写问卷星表单（使用共享算法 v3.0）...');
    
    // ═══════════════════════════════════════════════════════════════
    // 共享匹配算法（来自 TencentDocsFiller.get_shared_match_algorithm()）
    // ═══════════════════════════════════════════════════════════════
{shared_algorithm}
    
    // 🔧 自动适配移动端视口
    (function adaptViewport() {{
        const existingViewport = document.querySelector('meta[name="viewport"]');
        if (existingViewport) {{
            existingViewport.remove();
        }}
        
        const viewport = document.createElement('meta');
        viewport.name = 'viewport';
        viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';
        document.head.appendChild(viewport);
        
        const style = document.createElement('style');
        style.textContent = `
            body {{
                width: 100% !important;
                min-width: 100% !important;
                max-width: 100% !important;
                overflow-x: hidden !important;
            }}
            #divContent, .div_question, .field {{
                width: 100% !important;
                max-width: 100% !important;
                padding: 10px !important;
                box-sizing: border-box !important;
            }}
            input, textarea, select {{
                width: 100% !important;
                box-sizing: border-box !important;
            }}
        `;
        document.head.appendChild(style);
        console.log('📱 已适配移动端视口');
    }})();
    
    const fillData = {fill_data_json};
    let fillCount = 0;
    const results = [];
    const usedCardKeys = new Set();
    
    // 寻找最佳匹配项 - 使用共享的 matchKeyword
    function findBestMatch(identifiers, formTitle = '') {{
        let bestMatch = {{ item: null, score: 0, identifier: null, matchedKey: null }};
        
        for (const item of fillData) {{
            // 跳过已使用的字段
            if (usedCardKeys.has(item.key)) continue;
            
            // 使用共享的 matchKeyword
            const matchResult = matchKeyword(identifiers, item.key);
            if (matchResult.matched && matchResult.score > bestMatch.score) {{
                bestMatch = {{ 
                    item: item, 
                    score: matchResult.score,
                    identifier: matchResult.identifier,
                    matchedKey: matchResult.matchedKey
                }};
            }}
        }}
        
        return bestMatch;
    }}
    
    // ═══════════════════════════════════════════════════════════════
    // 填充函数
    // ═══════════════════════════════════════════════════════════════
    
    // 填充输入框 - React/Vue 深度兼容
    function fillInput(input, value) {{
        if (!input || input.readOnly || input.disabled) return false;
        
        input.focus();
        input.click();
        
        const isTextArea = input.tagName === 'TEXTAREA';
        const proto = isTextArea ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
        
        try {{
            const nativeValueSetter = Object.getOwnPropertyDescriptor(proto, 'value').set;
            nativeValueSetter.call(input, value);
        }} catch (e) {{
            input.value = value;
        }}
        
        // 触发各种事件
        const inputEvent = new InputEvent('input', {{
            bubbles: true,
            cancelable: true,
            inputType: 'insertText',
            data: value
        }});
        input.dispatchEvent(inputEvent);
        
        const changeEvent = new Event('change', {{ bubbles: true, cancelable: true }});
        input.dispatchEvent(changeEvent);
        
        // 触发键盘事件
        ['keydown', 'keypress', 'keyup'].forEach(eventName => {{
            const keyEvent = new KeyboardEvent(eventName, {{
                bubbles: true,
                cancelable: true,
                key: value.slice(-1) || 'a',
                code: 'KeyA'
            }});
            input.dispatchEvent(keyEvent);
        }});
        
        // 确保值已设置
        if (input.value !== value) {{
            input.value = value;
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}
        
        input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
        
        return input.value === value;
    }}
    
    // 辅助函数：最长公共子串（用于模糊匹配）
    function longestCommonSubstring(s1, s2) {{
        const m = s1.length, n = s2.length;
        if (m === 0 || n === 0) return 0;
        let maxLen = 0;
        const dp = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0));
        for (let i = 1; i <= m; i++) {{
            for (let j = 1; j <= n; j++) {{
                if (s1[i-1] === s2[j-1]) {{
                    dp[i][j] = dp[i-1][j-1] + 1;
                    maxLen = Math.max(maxLen, dp[i][j]);
                }}
            }}
        }}
        return maxLen;
    }}
    
    // 处理多选题（checkbox）
    function handleCheckbox(fieldDiv, value, questionTitle) {{
        const checkboxes = fieldDiv.querySelectorAll('input[type="checkbox"]');
        if (checkboxes.length === 0) return false;
        
        // 值可能是逗号分隔的多选项
        const selectedValues = String(value).split(/[,，、;；|｜\\n]+/).map(v => cleanText(v)).filter(v => v);
        let filledCount = 0;
        
        checkboxes.forEach(checkbox => {{
            // 获取选项文本
            const wrapper = checkbox.closest('.ui-checkbox');
            let optionText = '';
            if (wrapper) {{
                const label = wrapper.querySelector('.label, label');
                optionText = label ? (label.innerText || label.textContent || '').trim() : '';
            }}
            // 也尝试从 dit 属性获取（URL编码）
            if (!optionText) {{
                const labelEl = wrapper?.querySelector('[dit]');
                if (labelEl) {{
                    try {{
                        optionText = decodeURIComponent(labelEl.getAttribute('dit') || '');
                    }} catch(e) {{}}
                }}
            }}
            
            const cleanOption = cleanText(optionText);
            
            // 检查是否匹配选中值
            const shouldSelect = selectedValues.some(v => {{
                return cleanOption === v || 
                       cleanOption.includes(v) || 
                       v.includes(cleanOption) ||
                       longestCommonSubstring(cleanOption, v) >= Math.min(cleanOption.length, v.length) * 0.6;
            }});
            
            if (shouldSelect && !checkbox.checked) {{
                // 点击关联的 a.jqcheck 元素（问卷星的自定义样式）
                const jqcheck = wrapper?.querySelector('a.jqcheck');
                if (jqcheck) {{
                    jqcheck.click();
                }} else {{
                    checkbox.click();
                }}
                filledCount++;
                console.log(`   ☑️  选中: "${{optionText}}"`);
            }}
        }});
        
        return filledCount > 0;
    }}
    
    // 处理下拉选择（select2）
    function handleSelect(fieldDiv, value, questionTitle) {{
        const select = fieldDiv.querySelector('select');
        if (!select) return false;
        
        const cleanValue = cleanText(value);
        let matchedOption = null;
        let bestScore = 0;
        
        // 遍历所有选项寻找最佳匹配
        Array.from(select.options).forEach(option => {{
            if (option.value === '-2') return; // 跳过"请选择"
            
            const optionText = cleanText(option.text || option.innerText || '');
            
            // 完全匹配
            if (optionText === cleanValue) {{
                matchedOption = option;
                bestScore = 100;
            }}
            // 包含匹配
            else if (bestScore < 80 && (optionText.includes(cleanValue) || cleanValue.includes(optionText))) {{
                matchedOption = option;
                bestScore = 80;
            }}
            // 部分匹配
            else if (bestScore < 60) {{
                const lcs = longestCommonSubstring(optionText, cleanValue);
                if (lcs >= 2 && lcs >= Math.min(optionText.length, cleanValue.length) * 0.5) {{
                    matchedOption = option;
                    bestScore = 60;
                }}
            }}
        }});
        
        if (matchedOption) {{
            select.value = matchedOption.value;
            select.dispatchEvent(new Event('change', {{ bubbles: true }}));
            
            // 触发 select2 更新（如果使用了 select2）
            if (window.jQuery && window.jQuery(select).data('select2')) {{
                window.jQuery(select).trigger('change.select2');
            }}
            
            // 更新 select2 显示
            const select2Container = fieldDiv.querySelector('.select2-selection__rendered');
            if (select2Container) {{
                select2Container.textContent = matchedOption.text;
                select2Container.setAttribute('title', matchedOption.text);
            }}
            
            console.log(`   📋 选择: "${{matchedOption.text}}"`);
            return true;
        }}
        
        return false;
    }}
    
    // ⚡️ 辅助函数：在所有名片字段中查找最佳匹配（不受 usedCardKeys 限制，允许重复使用）
    function findBestMatchAllowReuse(identifiers, formTitle = '') {{
        let bestMatch = {{ item: null, score: 0, identifier: null, matchedKey: null }};
        
        for (const item of fillData) {{
            // ⚡️ 关键：不跳过已使用的字段，允许重复使用
            const matchResult = matchKeyword(identifiers, item.key);
            if (matchResult.matched && matchResult.score > bestMatch.score) {{
                bestMatch = {{ 
                    item: item, 
                    score: matchResult.score,
                    identifier: matchResult.identifier,
                    matchedKey: matchResult.matchedKey
                }};
            }}
        }}
        
        return bestMatch;
    }}
    
    // 处理联系地址（type=9 矩阵表格）
    function handleAddressField(fieldDiv, questionTitle) {{
        const rows = fieldDiv.querySelectorAll('tr[id^="drv"]');
        let filledCount = 0;
        
        rows.forEach(row => {{
            // 获取子字段标题
            const titleSpan = row.querySelector('.itemTitleSpan');
            let subTitle = titleSpan ? (titleSpan.innerText || titleSpan.textContent || '').trim() : '';
            subTitle = subTitle.replace(/[：:]/g, '').trim();
            
            if (!subTitle) return;
            
            // 获取输入框
            const input = row.querySelector('input:not([readonly]), textarea');
            if (!input) return;
            
            // 构建标识符
            const identifiers = [
                subTitle,
                questionTitle + subTitle,
                subTitle.replace(/[或及和]/g, '|')
            ];
            
            // 特殊处理常见字段名
            if (subTitle.includes('姓名') || subTitle.includes('名字')) {{
                identifiers.push('姓名', '收货人', '收件人', '联系人');
            }}
            if (subTitle.includes('手机') || subTitle.includes('电话') || subTitle.includes('固话')) {{
                identifiers.push('手机', '电话', '手机号', '联系电话', '电话号码');
            }}
            if (subTitle.includes('地址') || subTitle.includes('街道')) {{
                identifiers.push('详细地址', '街道地址', '收货地址', '地址');
            }}
            if (subTitle.includes('地区') || subTitle.includes('省') || subTitle.includes('市')) {{
                identifiers.push('所在地', '所在地区', '省市区', '城市', '地区');
            }}
            
            // ⚡️ 关键修复：使用允许重复使用的匹配函数，只看匹配度最高
            const match = findBestMatchAllowReuse(identifiers, subTitle);
            
            if (match.item && match.score >= 50) {{
                const filled = fillInput(input, match.item.value);
                if (filled) {{
                    usedCardKeys.add(match.item.key);
                    filledCount++;
                    console.log(`   📍 地址字段 "${{subTitle}}": "${{match.item.value}}" (匹配: ${{match.item.key}}, 分数: ${{match.score}})`);
                    results.push({{
                        key: match.item.key,
                        value: match.item.value,
                        matched: subTitle,
                        score: match.score,
                        success: true
                    }});
                }}
            }}
        }});
        
        // 处理只读的地区选择器（需要特殊处理）
        const regionInput = fieldDiv.querySelector('input[readonly][onclick*="openCityBox"], input[verify="省市区"]');
        if (regionInput) {{
            const regionIdentifiers = ['所在地区', '省市区', '城市', '地区', '所在地'];
            const regionMatch = findBestMatch(regionIdentifiers, '所在地区');
            if (regionMatch.item && regionMatch.score >= 50) {{
                // 注意：地区选择器是只读的，需要通过点击触发
                // 这里先设置一个标记，后续可能需要人工选择
                console.log(`   ⚠️  地区字段需要手动选择: "${{regionMatch.item.value}}"`);
            }}
        }}
        
        return filledCount > 0;
    }}
    
    // ═══════════════════════════════════════════════════════════════
    // 解析问卷星表单结构
    // ═══════════════════════════════════════════════════════════════
    
    function parseWjxFields() {{
        const fields = [];
        
        // 问卷星的问题容器: .field[type] 或 div[id^="div"][topic]
        const fieldDivs = document.querySelectorAll('.field[type], div.field[topic], fieldset .field');
        
        console.log(`\\n📊 发现 ${{fieldDivs.length}} 个问题字段`);
        
        fieldDivs.forEach((fieldDiv, index) => {{
            const type = fieldDiv.getAttribute('type');
            const topic = fieldDiv.getAttribute('topic');
            
            // 获取问题标题
            const topicHtml = fieldDiv.querySelector('.topichtml');
            let questionTitle = '';
            if (topicHtml) {{
                questionTitle = (topicHtml.innerText || topicHtml.textContent || '').trim();
                // 去除【请选择...】这类提示
                questionTitle = questionTitle.replace(/【[^】]*】/g, '').trim();
            }}
            
            if (!questionTitle) {{
                const labelDiv = fieldDiv.querySelector('.field-label');
                if (labelDiv) {{
                    questionTitle = (labelDiv.innerText || labelDiv.textContent || '').trim();
                    // 去除序号和必填标记
                    questionTitle = questionTitle.replace(/^\\d+\\.\\s*\\*?\\s*/, '').replace(/\\*$/, '').trim();
                }}
            }}
            
            fields.push({{
                element: fieldDiv,
                type: type,
                topic: topic,
                title: questionTitle,
                index: index
            }});
            
            console.log(`  [${{index + 1}}] type=${{type}}, topic=${{topic}}: "${{questionTitle.substring(0, 30)}}${{questionTitle.length > 30 ? '...' : ''}}"`);
        }});
        
        return fields;
    }}
    
    // ═══════════════════════════════════════════════════════════════
    // 主执行函数
    // ═══════════════════════════════════════════════════════════════
    
    async function executeAutoFill() {{
        console.log('\\n═══════════════════════════════════════════════════════════════');
        console.log('🔍 [问卷星 v2.0] 页面结构分析');
        console.log('═══════════════════════════════════════════════════════════════');
        console.log(`页面URL: ${{window.location.href}}`);
        console.log(`页面标题: ${{document.title}}`);
        
        // 打印名片字段列表
        console.log('\\n📇 名片字段列表:');
        fillData.forEach((item, i) => {{
            const valuePreview = String(item.value).substring(0, 30) + (String(item.value).length > 30 ? '...' : '');
            console.log(`   ${{i + 1}}. "${{item.key}}" = "${{valuePreview}}"`);
        }});
        
        // 等待页面加载
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // 解析表单字段
        const fields = parseWjxFields();
        
        if (fields.length === 0) {{
            console.warn('⚠️ 未找到问卷星问题字段，尝试兼容模式...');
            // 兼容模式：直接扫描所有可编辑输入框
            await fallbackFill();
            return;
        }}
        
        console.log('\\n🎯 开始智能填写...');
        console.log('═══════════════════════════════════════════════════════════════');
        
        // 遍历每个问题字段
        for (const field of fields) {{
            const {{ element: fieldDiv, type, topic, title }} = field;
            
            console.log(`\\n📋 问题 #${{topic || field.index + 1}}: "${{title}}"`);
            console.log(`   类型: type=${{type}}`);
            
            let filled = false;
            
            switch (type) {{
                case '1': // 文本输入
                case '2': // 多行文本
                case '6': // 数字输入
                    // ⚡️ 扩展选择器：支持 text、tel、number 类型的输入框
                    const textInput = fieldDiv.querySelector('input[type="text"], input[type="tel"], input[type="number"], textarea');
                    if (textInput && !textInput.readOnly && !textInput.disabled) {{
                        // ⚡️【核心优化】智能提取核心标题，去除序号和说明文字
                        // 例如: "1、账号类型（科技、文创、亲子、情侣、萌宠、生活类）" -> "账号类型"
                        let coreTitle = title;
                        // 1. 去除开头的序号（如 "1、" "2." "*1" "Q1"）
                        coreTitle = coreTitle.replace(/^[\\*]*[\\dqQ]+[、.．:：\\s]*/g, '');
                        // 2. 提取括号前的核心内容
                        const bracketMatch = coreTitle.match(/^([^（(【\\[]+)/);
                        if (bracketMatch && bracketMatch[1].trim().length >= 2) {{
                            coreTitle = bracketMatch[1].trim();
                        }}
                        // 3. 如果核心部分太长，取第一个词组
                        if (coreTitle.length > 10) {{
                            const parts = coreTitle.split(/[，,、\\s]+/);
                            if (parts[0] && parts[0].length >= 2) {{
                                coreTitle = parts[0];
                            }}
                        }}
                        // 4. 去除尾部的数字和单位
                        coreTitle = coreTitle.replace(/\\d+[万wW以上以下以内左右]+.*$/, '');
                        // 5. 如果结果太短，回退到原标题
                        if (!coreTitle || coreTitle.length < 2) {{
                            coreTitle = title;
                        }}
                        
                        // 使用核心标题作为标识符，直接交给共享匹配算法
                        const identifiers = [coreTitle];
                        if (coreTitle !== title) {{
                            identifiers.push(title);
                        }}
                        
                        const match = findBestMatch(identifiers, title);
                        if (match.item && match.score >= 50) {{
                            filled = fillInput(textInput, match.item.value);
                            if (filled) {{
                                usedCardKeys.add(match.item.key);
                                console.log(`   ✅ 填入: "${{match.item.value}}" (匹配: ${{match.item.key}}, 分数: ${{match.score.toFixed(1)}})`);
                                fillCount++;
                                results.push({{
                                    key: match.item.key,
                                    value: match.item.value,
                                    matched: title,
                                    score: match.score,
                                    success: true
                                }});
                            }}
                        }} else {{
                            console.log(`   ❌ 未找到匹配 (最高分: ${{match.score ? match.score.toFixed(1) : 0}})`);
                        }}
                    }}
                    break;
                    
                case '3': // 单选题
                    // 单选题类似多选题但只选一个
                    const radios = fieldDiv.querySelectorAll('input[type="radio"]');
                    if (radios.length > 0) {{
                        const identifiers = [title];
                        const match = findBestMatch(identifiers, title);
                        if (match.item && match.score >= 50) {{
                            const cleanValue = cleanText(match.item.value);
                            radios.forEach(radio => {{
                                const wrapper = radio.closest('.ui-radio');
                                let optionText = '';
                                if (wrapper) {{
                                    const label = wrapper.querySelector('.label, label');
                                    optionText = cleanText(label ? (label.innerText || '') : '');
                                }}
                                
                                if (optionText === cleanValue || optionText.includes(cleanValue) || cleanValue.includes(optionText)) {{
                                    const jqradio = wrapper?.querySelector('a.jqradio');
                                    if (jqradio) {{
                                        jqradio.click();
                                    }} else {{
                                        radio.click();
                                    }}
                                    usedCardKeys.add(match.item.key);
                                    filled = true;
                                    fillCount++;
                                    console.log(`   ✅ 选择: "${{optionText}}" (匹配: ${{match.item.key}})`);
                                    results.push({{
                                        key: match.item.key,
                                        value: match.item.value,
                                        matched: title,
                                        score: match.score,
                                        success: true
                                    }});
                                }}
                            }});
                        }}
                    }}
                    break;
                    
                case '4': // 多选题
                    const identifiersCheckbox = [title];
                    if (title.includes('类型') || title.includes('类别')) {{
                        identifiersCheckbox.push('账号类型', '类型', '分类', '领域');
                    }}
                    const checkboxMatch = findBestMatch(identifiersCheckbox, title);
                    if (checkboxMatch.item && checkboxMatch.score >= 50) {{
                        filled = handleCheckbox(fieldDiv, checkboxMatch.item.value, title);
                        if (filled) {{
                            usedCardKeys.add(checkboxMatch.item.key);
                            fillCount++;
                            results.push({{
                                key: checkboxMatch.item.key,
                                value: checkboxMatch.item.value,
                                matched: title,
                                score: checkboxMatch.score,
                                success: true
                            }});
                        }}
                    }}
                    break;
                    
                case '7': // 下拉选择
                    const identifiersSelect = [title];
                    if (title.includes('返点')) {{
                        identifiersSelect.push('返点比例', '返点', '佣金比例');
                    }}
                    const selectMatch = findBestMatch(identifiersSelect, title);
                    if (selectMatch.item && selectMatch.score >= 50) {{
                        filled = handleSelect(fieldDiv, selectMatch.item.value, title);
                        if (filled) {{
                            usedCardKeys.add(selectMatch.item.key);
                            fillCount++;
                            results.push({{
                                key: selectMatch.item.key,
                                value: selectMatch.item.value,
                                matched: title,
                                score: selectMatch.score,
                                success: true
                            }});
                        }}
                    }}
                    break;
                    
                case '9': // 联系地址（矩阵表格）
                    filled = handleAddressField(fieldDiv, title);
                    break;
                    
                default:
                    console.log(`   ⚠️  暂不支持的题型: type=${{type}}`);
            }}
            
            if (!filled && type !== '9') {{
                console.log(`   ⏭️  跳过此字段`);
            }}
        }}
        
        // 汇总结果
        console.log('\\n═══════════════════════════════════════════════════════════════');
        console.log('📊 填写汇总:');
        console.log(`   成功填写: ${{fillCount}} 个字段`);
        
        const unusedFields = fillData.filter(item => !usedCardKeys.has(item.key));
        if (unusedFields.length > 0) {{
            console.log(`\\n⚠️  未使用的名片字段 (${{unusedFields.length}}个):`);
            unusedFields.forEach(item => {{
                console.log(`   - "${{item.key}}" = "${{String(item.value).substring(0, 30)}}..."`);
                results.push({{
                    key: item.key,
                    value: item.value,
                    matched: null,
                    score: 0,
                    success: false
                }});
            }});
        }}
        
        window.__autoFillResult__ = {{
            fillCount: fillCount,
            totalCount: fields.length,
            status: 'completed',
            results: results
        }};
        
        console.log(`\\n✅ 问卷星填写完成: ${{fillCount}}/${{fields.length}} 个字段`);
        console.log('═══════════════════════════════════════════════════════════════\\n');
    }}
    
    // 兼容模式：直接扫描所有输入框
    async function fallbackFill() {{
        console.log('\\n⚡ 启动兼容模式...');
        
        const allInputs = document.querySelectorAll('input[type="text"]:not([readonly]):not([disabled]), textarea:not([readonly]):not([disabled])');
        console.log(`找到 ${{allInputs.length}} 个可编辑输入框`);
        
        allInputs.forEach((input, index) => {{
            // 跳过同意条款等
            const parentText = (input.closest('.field, .question, .ui-field-contain')?.innerText || '').toLowerCase();
            if (parentText.includes('同意') || parentText.includes('协议') || parentText.includes('隐私')) {{
                return;
            }}
            
            // 尝试获取标签
            const identifiers = [];
            
            // 向上查找标题
            let parent = input.parentElement;
            for (let i = 0; i < 6 && parent; i++) {{
                const titleEl = parent.querySelector('.topichtml, .field-label, label, .title');
                if (titleEl) {{
                    const text = (titleEl.innerText || '').trim().replace(/^\\d+\\.\\s*\\*?/, '').replace(/\\*$/, '');
                    if (text && text.length < 50) {{
                        identifiers.push(text);
                        break;
                    }}
                }}
                parent = parent.parentElement;
            }}
            
            if (input.placeholder) identifiers.push(input.placeholder);
            if (input.name) identifiers.push(input.name);
            
            if (identifiers.length === 0) return;
            
            // 传入第一个标识符作为表单标题用于互斥检测
            const formTitle = identifiers[0] || '';
            const match = findBestMatch(identifiers, formTitle);
            if (match.item && match.score >= 50) {{
                const filled = fillInput(input, match.item.value);
                if (filled) {{
                    usedCardKeys.add(match.item.key);
                    fillCount++;
                    console.log(`   ✅ [${{index + 1}}] "${{identifiers[0]}}" → "${{match.item.value}}"`);
                    results.push({{
                        key: match.item.key,
                        value: match.item.value,
                        matched: identifiers[0],
                        score: match.score,
                        success: true
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
        
        console.log(`\\n✅ 兼容模式填写完成: ${{fillCount}} 个字段`);
    }}
    
    executeAutoFill();
    return '问卷星填写脚本(v2.0)已执行';
}})();
        """
        return js_code
    
    def generate_jinshuju_fill_script(self, fill_data: list) -> str:
        """生成金数据专用的填充脚本 - 使用共享匹配算法"""
        import json
        from core.tencent_docs_filler import TencentDocsFiller
        
        fill_data_json = json.dumps(fill_data, ensure_ascii=False)
        
        # 获取共享的匹配算法和执行逻辑
        shared_algorithm = TencentDocsFiller.get_shared_match_algorithm()
        shared_executor = TencentDocsFiller.get_shared_execution_logic()
        
        js_code = f"""
(function() {{
    console.log('🚀 开始填写金数据表单（使用共享算法）...');
    
    const fillData = {fill_data_json};
    
    // ═══════════════════════════════════════════════════════════════
    // 共享匹配算法（来自 TencentDocsFiller.get_shared_match_algorithm()）
    // ═══════════════════════════════════════════════════════════════
{shared_algorithm}
    
    // ═══════════════════════════════════════════════════════════════
    // 共享执行逻辑（来自 TencentDocsFiller.get_shared_execution_logic()）
    // ═══════════════════════════════════════════════════════════════
{shared_executor}
    
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
    
    // 【核心】获取输入框的所有可能标识（针对金数据结构优化）
    // 金数据结构：
    // div[data-api-code="field_xx"].field-container
    //   └─ .ant-form-item-label label .label-item div  → 标题
    //   └─ .field__description  → 灰色提示（排除）
    //   └─ input[name="field_xx"]  → 输入框
    function getInputIdentifiers(input) {{
        const identifiers = [];
        
        // 【方法1】金数据专用：向上找 .field-container 或 [data-api-code] 容器
        let fieldContainer = input.closest('.field-container, [data-api-code]');
        if (fieldContainer) {{
            // 在 .ant-form-item-label 里找标题（不是 .field__description）
            const labelEl = fieldContainer.querySelector('.ant-form-item-label .label-item');
            if (labelEl) {{
                const text = (labelEl.innerText || labelEl.textContent || '').trim();
                if (text && text.length >= 1 && !identifiers.includes(text)) {{
                    identifiers.push(text);
                }}
            }}
            
            // 备选：直接找 label 标签里的文本
            if (identifiers.length === 0) {{
                const label = fieldContainer.querySelector('.ant-form-item-label label');
                if (label) {{
                    const text = (label.innerText || label.textContent || '').trim();
                    if (text && text.length >= 1 && !identifiers.includes(text)) {{
                        identifiers.push(text);
                    }}
                }}
            }}
        }}
        
        // 【方法2】通用：向上查找包含 label 的父元素
        if (identifiers.length === 0) {{
            let parent = input.parentElement;
            for (let depth = 0; depth < 10 && parent; depth++) {{
                // 查找同级或父级的 label
                const label = parent.querySelector(':scope > label, :scope > .ant-form-item-label label');
                if (label) {{
                    const text = (label.innerText || label.textContent || '').trim();
                    if (text && text.length >= 1 && !identifiers.includes(text)) {{
                        identifiers.push(text);
                        break;
                    }}
                }}
                
                // 检查是否是 ant-form-item（金数据表单项容器）
                if (parent.classList && parent.classList.contains('ant-form-item')) {{
                    const labelEl = parent.querySelector('.ant-form-item-label');
                    if (labelEl) {{
                        const text = (labelEl.innerText || labelEl.textContent || '').trim();
                        if (text && text.length >= 1 && !identifiers.includes(text)) {{
                            identifiers.push(text);
                            break;
                        }}
                    }}
                }}
                
                parent = parent.parentElement;
            }}
        }}
        
        // 【方法3】基本属性作为备选标识
        if (input.name) identifiers.push(input.name.trim());
        if (input.id) identifiers.push(input.id.trim());
        if (input.title) identifiers.push(input.title.trim());
        if (input.getAttribute('aria-label')) identifiers.push(input.getAttribute('aria-label').trim());
        
        // 【调试】输出找到的标识
        if (identifiers.length > 0) {{
            console.log('[标识] input[name=' + input.name + '] → 找到标识:', identifiers.slice(0, 3).join(', '));
        }}
        
        return identifiers;
    }}
    
    // 填充输入框 - React/Ant Design 深度兼容（修复金数据表单验证问题）
    function fillInput(input, value) {{
        // 1. 聚焦输入框
        input.focus();
        input.click();
        
        // 2. 清空现有内容（触发 React 状态清除）
        input.value = '';
        
        // 3. 使用原生 setter 设置值（React 关键）
        const isTextArea = input.tagName === 'TEXTAREA';
        const proto = isTextArea ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
        
        try {{
            const nativeValueSetter = Object.getOwnPropertyDescriptor(proto, 'value').set;
            nativeValueSetter.call(input, value);
        }} catch (e) {{
            input.value = value;
        }}
        
        // 4. 触发 React 合成事件 - 使用 InputEvent（关键！）
        const inputEvent = new InputEvent('input', {{
            bubbles: true,
            cancelable: true,
            inputType: 'insertText',
            data: value
        }});
        input.dispatchEvent(inputEvent);
        
        // 5. 触发 change 事件
        const changeEvent = new Event('change', {{ bubbles: true, cancelable: true }});
        input.dispatchEvent(changeEvent);
        
        // 6. 模拟键盘事件序列（某些框架依赖这些事件）
        const keyboardEvents = ['keydown', 'keypress', 'keyup'];
        keyboardEvents.forEach(eventName => {{
            const keyEvent = new KeyboardEvent(eventName, {{
                bubbles: true,
                cancelable: true,
                key: value.slice(-1) || 'a',
                code: 'KeyA'
            }});
            input.dispatchEvent(keyEvent);
        }});
        
        // 7. 再次确认值已设置
        if (input.value !== value) {{
            input.value = value;
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}
        
        // 8. 触发 blur 完成编辑
        input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
        
        // 9. 尝试触发 React/Ant Design 内部状态更新
        try {{
            // React Fiber 节点查找
            const reactKey = Object.keys(input).find(key => 
                key.startsWith('__reactFiber$') || 
                key.startsWith('__reactInternalInstance$') ||
                key.startsWith('__reactProps$')
            );
            if (reactKey && input[reactKey]) {{
                const props = input[reactKey].memoizedProps || input[reactKey].pendingProps || {{}};
                if (props.onChange) {{
                    props.onChange({{ target: input, currentTarget: input }});
                }}
            }}
        }} catch (e) {{}}
        
        // 10. Ant Design 特殊处理：尝试触发 Form.Item 的 onFieldsChange
        try {{
            // 找到 ant-form-item 容器
            const formItem = input.closest('.ant-form-item');
            if (formItem) {{
                // 触发 input 的 compositionend 事件（某些输入法模式需要）
                input.dispatchEvent(new CompositionEvent('compositionend', {{
                    bubbles: true,
                    data: value
                }}));
            }}
        }} catch (e) {{}}
    }}
    
    // ═══════════════════════════════════════════════════════════════
    // 主执行函数 - 调用共享执行器（来自 TencentDocsFiller）
    // ═══════════════════════════════════════════════════════════════
    async function executeAutoFill() {{
        const hasInputs = await waitForInputs();
        
        if (!hasInputs) {{
            window.__autoFillResult__ = {{ fillCount: 0, totalCount: fillData.length, status: 'completed', results: [] }};
            return;
        }}
        
        const allInputs = getAllInputs();
        
        // 使用共享执行器
        const executor = createSharedExecutor({{
            fillData: fillData,
            allInputs: allInputs,
            getIdentifiers: getInputIdentifiers,
            fillInput: fillInput,
            onProgress: (msg) => console.log(msg)
        }});
        
        const result = await executor.execute();
        window.__autoFillResult__ = result;
        
        console.log(`\\n✅ 金数据填写完成: ${{result.fillCount}}/${{result.totalCount}} 个输入框`);
    }}
    
    executeAutoFill();
    return '金数据填写脚本已执行';
}})();
        """
        return js_code
    
    def generate_shimo_fill_script(self, fill_data: list) -> str:
        """生成石墨文档专用的填充脚本 - 使用共享匹配算法"""
        import json
        from core.tencent_docs_filler import TencentDocsFiller
        
        fill_data_json = json.dumps(fill_data, ensure_ascii=False)
        
        # 获取共享的匹配算法和执行逻辑
        shared_algorithm = TencentDocsFiller.get_shared_match_algorithm()
        shared_executor = TencentDocsFiller.get_shared_execution_logic()
        
        js_code = f"""
(function() {{
    console.log('🚀 开始填写石墨文档表单（使用共享算法）...');
    
    // 🔧 自动适配移动端视口
    (function adaptViewport() {{
        // 移除现有 viewport
        const existingViewport = document.querySelector('meta[name="viewport"]');
        if (existingViewport) {{
            existingViewport.remove();
        }}
        
        // 添加适配的 viewport
        const viewport = document.createElement('meta');
        viewport.name = 'viewport';
        viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';
        document.head.appendChild(viewport);
        
        // 注入移动端适配样式
        const style = document.createElement('style');
        style.textContent = `
            body {{
                width: 100% !important;
                min-width: 100% !important;
                max-width: 100% !important;
                overflow-x: hidden !important;
            }}
            main, .FormFillPageWrapper-sc-8cs2d7, form {{
                width: 100% !important;
                max-width: 100% !important;
                padding: 15px !important;
                box-sizing: border-box !important;
            }}
            input, textarea {{
                width: 100% !important;
                box-sizing: border-box !important;
            }}
        `;
        document.head.appendChild(style);
        console.log('📱 已适配移动端视口');
    }})();
    
    const fillData = {fill_data_json};
    
    // ═══════════════════════════════════════════════════════════════
    // 共享匹配算法（来自 TencentDocsFiller.get_shared_match_algorithm()）
    // ═══════════════════════════════════════════════════════════════
{shared_algorithm}
    
    // ═══════════════════════════════════════════════════════════════
    // 共享执行逻辑（来自 TencentDocsFiller.get_shared_execution_logic()）
    // ═══════════════════════════════════════════════════════════════
{shared_executor}
    
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
                // ⚡️ 排除不应该被填充的输入框
                // 1. 排除举报弹窗相关的输入框
                const fieldset = input.closest('fieldset');
                if (fieldset) {{
                    const fieldsetText = fieldset.innerText || '';
                    if (fieldsetText.includes('举报') || fieldsetText.includes('投诉')) {{
                        console.log('[石墨] 跳过举报/投诉相关输入框');
                        return;
                    }}
                }}
                // 2. 排除模态框/弹窗中的输入框
                const modal = input.closest('[class*="Modal"], [class*="Dialog"], [class*="Popup"], [role="dialog"]');
                if (modal) {{
                    const modalStyle = window.getComputedStyle(modal);
                    if (modalStyle.display === 'none' || modalStyle.visibility === 'hidden' || modalStyle.opacity === '0') {{
                        return;
                    }}
                }}
                // 3. 排除搜索框等非表单输入框
                if (input.type === 'search' || input.name === 'search' || input.id === 'search') {{
                    return;
                }}
                // 4. 确保输入框真正可见（有尺寸）
                const rect = input.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) {{
                    return;
                }}
                
                inputs.push(input);
            }}
        }});
        return inputs;
    }}
    
    // 【核心】石墨文档专用：精确提取输入框对应的问题标识
    // 石墨文档结构：
    // <fieldset id="xxx">
    //   <h2 class="QuestionTitle-sc-14d3crw">
    //     <div class="QuestionIndex-sc-todj01">01.*</div>
    //     <span class="Title-sc-ci5sac">探店时间20号-31号</span>
    //   </h2>
    //   <input class="InputStyled-sc-m8ror5" />
    // </fieldset>
    function getInputIdentifiers(input, inputIndex) {{
        const identifiers = [];
        const MAX_LABEL_LENGTH = 150;
        
        // 辅助函数：添加标识符（带去重和优先级）
        function addIdentifier(text, priority = 0) {{
            if (!text) return;
            let cleaned = text.trim();
            // 去除序号前缀（如 "01.*"、"02."等）
            cleaned = cleaned.replace(/^\\d{{1,2}}\\.\\s*\\*?\\s*/, '').trim();
            // 去除多余空白和特殊符号
            cleaned = cleaned.replace(/^[\\s*]+|[\\s*]+$/g, '').trim();
            // 去除末尾的附件标记（石墨文档特有）
            cleaned = cleaned.replace(/\\s*<span[^>]*InlineAttachment[^>]*>.*?<\\/span>\\s*$/gi, '').trim();
            
            if (cleaned && cleaned.length > 0 && cleaned.length <= MAX_LABEL_LENGTH) {{
                // 去重
                if (!identifiers.some(item => item.text === cleaned)) {{
                    identifiers.push({{ text: cleaned, priority: priority }});
                }}
            }}
        }}
        
        // 【方法1 - 最高优先级】石墨文档专用：向上找 fieldset 容器，精确提取标题
        let fieldset = input.closest('fieldset');
        if (fieldset) {{
            // 在 fieldset 中查找 .Title-sc-ci5sac（实际问题文本，不含序号）
            const titleSpan = fieldset.querySelector('.Title-sc-ci5sac, [class*="Title-sc-"]');
            if (titleSpan) {{
                const titleText = (titleSpan.innerText || titleSpan.textContent || '').trim();
                if (titleText) {{
                    addIdentifier(titleText, 100);
                    console.log(`[石墨] fieldset精确匹配: "${{titleText}}"`);
                }}
            }}
            
            // 备选：如果上面没找到，查找整个 QuestionTitle
            if (identifiers.length === 0) {{
                const questionTitle = fieldset.querySelector('.QuestionTitle-sc-14d3crw, [class*="QuestionTitle-sc-"], h2');
                if (questionTitle) {{
                    const fullText = (questionTitle.innerText || questionTitle.textContent || '').trim();
                    // 从完整文本中提取标题（去除序号部分）
                    const cleanedTitle = fullText.replace(/^\\d{{1,2}}\\.\\s*\\*?\\s*/, '').trim();
                    if (cleanedTitle) {{
                        addIdentifier(cleanedTitle, 95);
                        console.log(`[石墨] fieldset通用匹配: "${{cleanedTitle}}"`);
                    }}
                }}
            }}
        }}
        
        // 【方法2】向上查找包含问题标题的容器（通用方法）
        if (identifiers.length === 0) {{
            let parent = input.parentElement;
            for (let depth = 0; depth < 8 && parent; depth++) {{
                // 查找 h2, h3 等标题标签
                const titleEl = parent.querySelector(':scope > h2, :scope > h3, :scope [class*="QuestionTitle"], :scope [class*="Title-sc-"]');
                if (titleEl) {{
                    const text = (titleEl.innerText || titleEl.textContent || '').trim();
                    const cleanedText = text.replace(/^\\d{{1,2}}\\.\\s*\\*?\\s*/, '').trim();
                    if (cleanedText && cleanedText.length <= MAX_LABEL_LENGTH) {{
                        addIdentifier(cleanedText, 90);
                        console.log(`[石墨] 向上查找匹配: "${{cleanedText}}"`);
                        break;
                    }}
                }}
                parent = parent.parentElement;
            }}
        }}
        
        // 【方法3】aria-labelledby 属性
        const ariaLabelledBy = input.getAttribute('aria-labelledby');
        if (ariaLabelledBy) {{
            ariaLabelledBy.split(' ').forEach(id => {{
                const el = document.getElementById(id);
                if (el) {{
                    addIdentifier(el.innerText || el.textContent, 85);
                }}
            }});
        }}
        
        // 【方法4】Label 标签关联
        if (input.labels && input.labels.length > 0) {{
            input.labels.forEach(label => {{
                addIdentifier(label.innerText || label.textContent, 85);
            }});
        }}
        
        // 【方法5】placeholder、title、aria-label 基础属性
        if (input.placeholder) addIdentifier(input.placeholder, 70);
        if (input.title) addIdentifier(input.title, 70);
        if (input.getAttribute('aria-label')) addIdentifier(input.getAttribute('aria-label'), 70);
        
        // 【方法6】前置兄弟元素（作为兜底）
        let sibling = input.previousElementSibling;
        for (let i = 0; i < 3 && sibling; i++) {{
            if (sibling.tagName === 'H2' || sibling.tagName === 'H3' || 
                sibling.tagName === 'LABEL' || sibling.className.includes('Title')) {{
                const text = (sibling.innerText || sibling.textContent || '').trim();
                if (text && text.length <= MAX_LABEL_LENGTH) {{
                    addIdentifier(text, 60);
                    break;
                }}
            }}
            sibling = sibling.previousElementSibling;
        }}
        
        // 按优先级排序，优先级高的在前
        identifiers.sort((a, b) => {{
            if (b.priority !== a.priority) return b.priority - a.priority;
            // 优先级相同时，短标题优先（更精确）
            return a.text.length - b.text.length;
        }});
        
        const result = identifiers.map(item => item.text);
        if (result.length > 0) {{
            console.log(`[石墨] 输入框#${{inputIndex + 1}} 标识符: [${{result.slice(0, 3).join(' | ')}}]`);
        }} else {{
            console.warn(`[石墨] 输入框#${{inputIndex + 1}} 未找到标识符`);
        }}
        return result;
    }}
    
    // 填充输入框 - React 深度兼容（修复石墨文档提交问题）
    function fillInput(input, value) {{
        const stringValue = String(value);
        
        // ⚡️ 【关键修复】React 18+ 需要先重置 _valueTracker 才能正确触发更新
        // React 使用 _valueTracker 来追踪输入值变化，如果不重置，React 会认为值没有变化
        function resetReactValueTracker(element) {{
            const tracker = element._valueTracker;
            if (tracker) {{
                tracker.setValue('');
            }}
        }}
        
        // ⚡️ 【新增】检测是否是石墨数字输入框（带 # 号图标的）
        // 数字输入框的特征：被 InputWrapper-sc-pke9o8 包裹，有 # 号图标
        const isNumberInput = input.closest('.InputWrapper-sc-pke9o8') !== null || 
                              input.closest('[class*="InputWrapper-sc-"]') !== null ||
                              (input.placeholder && input.placeholder.includes('数字'));
        
        if (isNumberInput) {{
            console.log('[fillInput] 📊 检测到数字输入框，使用增强填充策略');
        }}
        
        // 1. 聚焦输入框
        input.focus();
        
        // 2. 使用原生 setter 设置值（React 关键）
        const isTextArea = input.tagName === 'TEXTAREA';
        const proto = isTextArea ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
        
        // ⚡️ 【新增】对于数字输入框，先尝试使用 execCommand 方法（更接近真实用户输入）
        if (isNumberInput) {{
            try {{
                // 先选中所有内容
                input.select();
                // 使用 execCommand 插入文本（这会触发真实的输入事件）
                const execResult = document.execCommand('insertText', false, stringValue);
                if (execResult && input.value === stringValue) {{
                    console.log('[fillInput] ✅ execCommand 成功');
                    // execCommand 成功，直接返回（跳过后续步骤）
                    console.log(`[fillInput] 填充: "${{stringValue.substring(0, 20)}}..." -> 实际值: "${{input.value.substring(0, 20)}}..."`);
                    return;
                }}
            }} catch (e) {{
                console.log('[fillInput] execCommand 失败，使用备用方案:', e.message);
            }}
        }}
        
        try {{
            // ⚡️ 【关键】先重置 React 的 valueTracker
            resetReactValueTracker(input);
            
            // 获取原生 setter
            const nativeValueSetter = Object.getOwnPropertyDescriptor(proto, 'value').set;
            
            // 先清空
            nativeValueSetter.call(input, '');
            
            // 再设置新值
            nativeValueSetter.call(input, stringValue);
        }} catch (e) {{
            console.warn('[fillInput] 原生setter失败，使用直接赋值:', e);
            input.value = stringValue;
        }}
        
        // 3. ⚡️ 【关键】使用 InputEvent 而非普通 Event（React 17+ 更好支持）
        const inputEvent = new InputEvent('input', {{
            bubbles: true,
            cancelable: true,
            inputType: 'insertText',
            data: stringValue
        }});
        // 手动设置 simulated 标记，让 React 识别为用户输入
        Object.defineProperty(inputEvent, 'simulated', {{ value: true }});
        input.dispatchEvent(inputEvent);
        
        // 4. 触发 change 事件（某些 React 组件监听这个）
        const changeEvent = new Event('change', {{ bubbles: true, cancelable: true }});
        input.dispatchEvent(changeEvent);
        
        // 5. ⚡️ 【新增】尝试直接调用 React 的 onChange 处理器
        try {{
            // 查找 React Fiber 或 Props 节点
            const reactPropsKey = Object.keys(input).find(key => 
                key.startsWith('__reactProps$')
            );
            if (reactPropsKey && input[reactPropsKey]) {{
                const props = input[reactPropsKey];
                if (props.onChange && typeof props.onChange === 'function') {{
                    // 构造 React 风格的事件对象
                    const syntheticEvent = {{
                        target: {{ ...input, value: stringValue }},
                        currentTarget: input,
                        type: 'change',
                        nativeEvent: inputEvent,
                        preventDefault: () => {{}},
                        stopPropagation: () => {{}},
                        persist: () => {{}}
                    }};
                    // ⚡️ 确保 target.value 返回正确的值
                    Object.defineProperty(syntheticEvent.target, 'value', {{
                        get: () => stringValue,
                        configurable: true
                    }});
                    props.onChange(syntheticEvent);
                    console.log('[fillInput] ✅ 已调用 React onChange');
                }}
            }}
        }} catch (e) {{
            console.log('[fillInput] React props 调用跳过:', e.message);
        }}
        
        // 6. ⚡️ 【新增】针对石墨特殊组件：模拟完整的输入过程
        // 石墨可能使用 onCompositionEnd 来处理中文输入
        try {{
            // 触发 compositionstart
            const compStartEvent = new CompositionEvent('compositionstart', {{
                bubbles: true,
                cancelable: true,
                data: ''
            }});
            input.dispatchEvent(compStartEvent);
            
            // 触发 compositionend
            const compEndEvent = new CompositionEvent('compositionend', {{
                bubbles: true,
                cancelable: true,
                data: stringValue
            }});
            input.dispatchEvent(compEndEvent);
        }} catch (e) {{}}
        
        // 7. 模拟键盘事件（某些组件需要）
        try {{
            const keydownEvent = new KeyboardEvent('keydown', {{
                bubbles: true,
                cancelable: true,
                key: stringValue.slice(-1) || 'a',
                keyCode: 65
            }});
            input.dispatchEvent(keydownEvent);
            
            const keyupEvent = new KeyboardEvent('keyup', {{
                bubbles: true,
                cancelable: true,
                key: stringValue.slice(-1) || 'a',
                keyCode: 65
            }});
            input.dispatchEvent(keyupEvent);
        }} catch (e) {{}}
        
        // 8. ⚡️ 【新增】针对数字输入框：通过 React Fiber 强制更新状态
        if (isNumberInput) {{
            try {{
                // 方法1：查找 React Fiber 节点并尝试更新
                const fiberKey = Object.keys(input).find(key => 
                    key.startsWith('__reactFiber$') || key.startsWith('__reactInternalInstance$')
                );
                if (fiberKey) {{
                    let fiber = input[fiberKey];
                    // 向上遍历 Fiber 树，找到状态组件
                    while (fiber) {{
                        if (fiber.stateNode && fiber.stateNode.setState) {{
                            // 找到有状态的组件
                            console.log('[fillInput] 🔧 找到 React 状态组件，尝试强制更新');
                            break;
                        }}
                        // 尝试找到 memoizedState
                        if (fiber.memoizedState && typeof fiber.memoizedState === 'object') {{
                            console.log('[fillInput] 🔧 找到 memoizedState');
                        }}
                        fiber = fiber.return;
                    }}
                }}
                
                // 方法2：再次重置 valueTracker 并重新设置值
                resetReactValueTracker(input);
                const nativeValueSetter = Object.getOwnPropertyDescriptor(proto, 'value').set;
                nativeValueSetter.call(input, stringValue);
                
                // 再次触发事件
                input.dispatchEvent(new InputEvent('input', {{
                    bubbles: true,
                    cancelable: true,
                    inputType: 'insertText',
                    data: stringValue
                }}));
            }} catch (e) {{
                console.log('[fillInput] Fiber 更新跳过:', e.message);
            }}
        }}
        
        // 9. 最终验证并补救
        if (input.value !== stringValue) {{
            console.warn('[fillInput] ⚠️ 值未正确设置，尝试最终补救');
            input.value = stringValue;
            // 再次重置 tracker 并触发事件
            resetReactValueTracker(input);
            input.dispatchEvent(new InputEvent('input', {{ bubbles: true, inputType: 'insertText', data: stringValue }}));
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }}
        
        // 10. ⚡️ 【重要修改】延迟触发 blur，给 React 足够时间处理状态更新
        // 对于数字输入框，不立即触发 blur，而是等待一小段时间
        if (isNumberInput) {{
            // 数字输入框：延迟 blur 或不触发（避免 React 重新渲染清空值）
            setTimeout(() => {{
                // 再次检查并确保值正确
                if (input.value !== stringValue) {{
                    resetReactValueTracker(input);
                    const nativeValueSetter = Object.getOwnPropertyDescriptor(proto, 'value').set;
                    try {{
                        nativeValueSetter.call(input, stringValue);
                    }} catch(e) {{
                        input.value = stringValue;
                    }}
                    input.dispatchEvent(new InputEvent('input', {{ bubbles: true, inputType: 'insertText', data: stringValue }}));
                }}
                // 最后触发 blur
                input.dispatchEvent(new FocusEvent('blur', {{ bubbles: true }}));
            }}, 50);
        }} else {{
            // 普通输入框：立即触发 blur
            input.dispatchEvent(new FocusEvent('blur', {{ bubbles: true }}));
        }}
        
        // 11. 打印调试信息
        console.log(`[fillInput] 填充: "${{stringValue.substring(0, 20)}}..." -> 实际值: "${{input.value.substring(0, 20)}}..."`);
    }}
    
    // ═══════════════════════════════════════════════════════════════
    // 主执行函数 - 调用共享执行器（来自 TencentDocsFiller）
    // ═══════════════════════════════════════════════════════════════
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
        
        const allInputs = getAllInputs();
        
        // 使用共享执行器
        const executor = createSharedExecutor({{
            fillData: fillData,
            allInputs: allInputs,
            getIdentifiers: getInputIdentifiers,
            fillInput: fillInput,
            onProgress: (msg) => console.log(msg)
        }});
        
        const result = await executor.execute();
        window.__autoFillResult__ = result;
        
        console.log(`\\n✅ 石墨文档填写完成: ${{result.fillCount}}/${{result.totalCount}} 个输入框`);
    }}
    
    executeAutoFill();
    return '石墨文档填写脚本已执行';
}})();
        """
        return js_code
    
    def generate_credamo_fill_script(self, fill_data: list) -> str:
        """生成见数(Credamo)专用的填充脚本 - 使用共享匹配算法 v2.0"""
        import json
        from core.tencent_docs_filler import TencentDocsFiller
        
        fill_data_json = json.dumps(fill_data, ensure_ascii=False)
        
        # 获取共享算法和执行逻辑
        shared_algorithm = TencentDocsFiller.get_shared_match_algorithm()
        shared_executor = TencentDocsFiller.get_shared_execution_logic()
        
        js_code = f"""
(function() {{
    console.log('🚀 开始填写见数(Credamo)表单（使用共享算法）...');
    
    const fillData = {fill_data_json};
    
    // ═══════════════════════════════════════════════════════════════
    // 共享匹配算法（来自 TencentDocsFiller）
    // ═══════════════════════════════════════════════════════════════
    {shared_algorithm}
    
    // ═══════════════════════════════════════════════════════════════
    // 共享执行逻辑（来自 TencentDocsFiller）
    // ═══════════════════════════════════════════════════════════════
    {shared_executor}
    
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
    function getInputIdentifiers(input, inputIndex) {{
        const identifiers = [];
        const MAX_LABEL_LENGTH = 100;
        
        function addIdentifier(text) {{
            if (!text) return;
            let cleaned = text.trim();
            cleaned = cleaned.replace(/^[\\d\\*\\.、]+\\s*/, '').trim();
            cleaned = cleaned.replace(/\\*/g, '').replace(/必填/g, '').trim();
            cleaned = cleaned.replace(/\\s+/g, ' ').trim();
            
            if (cleaned && cleaned.length > 0 && cleaned.length <= MAX_LABEL_LENGTH) {{
                if (!identifiers.includes(cleaned)) {{
                    identifiers.push(cleaned);
                }}
            }}
        }}

        // 1. 【见数特有】查找 regular-answer 容器
        const regularAnswer = input.closest('.regular-answer, .answer-wrapper, .input-wrapper, .question-wrapper');
        if (regularAnswer) {{
            let containerText = '';
            regularAnswer.childNodes.forEach(node => {{
                if (node.nodeType === Node.TEXT_NODE) {{
                    containerText += node.textContent + ' ';
                }} else if (node.nodeType === Node.ELEMENT_NODE && node !== input && !node.contains(input)) {{
                    containerText += node.innerText + ' ';
                }}
            }});
            addIdentifier(containerText);

            const prevEl = regularAnswer.previousElementSibling;
            if (prevEl) {{
                addIdentifier(prevEl.innerText || prevEl.textContent);
            }}
            
            const parentOfRegular = regularAnswer.parentElement;
            if (parentOfRegular) {{
                const titleEl = parentOfRegular.querySelector('.question-title, .title, h3, h4');
                if (titleEl) {{
                    addIdentifier(titleEl.innerText || titleEl.textContent);
                }}
            }}
        }}
        
        // 2. 【见数特有】查找问题容器中的标题
        let questionItem = input.closest('.question-item, .form-item, .el-form-item, .survey-question, [class*="question"], [class*="field"]');
        if (questionItem) {{
            const titleEl = questionItem.querySelector('.question-title, .el-form-item__label, .form-label, .title, label, [class*="title"], [class*="label"]');
            if (titleEl) {{
                addIdentifier(titleEl.innerText || titleEl.textContent);
            }}
        }}

        // 3. aria-labelledby
        const ariaLabelledBy = input.getAttribute('aria-labelledby');
        if (ariaLabelledBy) {{
            ariaLabelledBy.split(' ').forEach(id => {{
                const el = document.getElementById(id);
                if (el) addIdentifier(el.innerText || el.textContent);
            }});
        }}
        
        // 4. Label 标签
        if (input.labels && input.labels.length > 0) {{
            input.labels.forEach(label => addIdentifier(label.innerText || label.textContent));
        }}
        
        // 5. 通过 for 属性查找 label
        if (input.id) {{
            const label = document.querySelector(`label[for="${{input.id}}"]`);
            if (label) addIdentifier(label.innerText || label.textContent);
        }}
        
        // 6. 基本属性
        if (input.placeholder) addIdentifier(input.placeholder);
        if (input.name) addIdentifier(input.name);
        if (input.title) addIdentifier(input.title);
        if (input.getAttribute('aria-label')) addIdentifier(input.getAttribute('aria-label'));
        
        // 7. 父元素中的 label 和直接文本
        let parent = input.parentElement;
        for (let depth = 0; depth < 6 && parent; depth++) {{
            const labelEl = parent.querySelector('label, .label, [class*="label"]');
            if (labelEl && labelEl !== input && !labelEl.contains(input)) {{
                addIdentifier(labelEl.innerText || labelEl.textContent);
            }}
            
            let parentText = '';
            Array.from(parent.childNodes).forEach(node => {{
                if (node.nodeType === Node.TEXT_NODE) {{
                    parentText += node.textContent.trim() + ' ';
                }}
            }});
            addIdentifier(parentText);
            
            parent = parent.parentElement;
        }}
        
        // 8. 前置兄弟元素
        let sibling = input.previousElementSibling;
        let siblingCount = 0;
        while (sibling && siblingCount < 3) {{
            addIdentifier(sibling.innerText || sibling.textContent);
            sibling = sibling.previousElementSibling;
            siblingCount++;
        }}
        
        if (identifiers.length > 0) {{
            console.log(`[见数] 输入框#${{inputIndex + 1}} 标识: [${{identifiers.slice(0, 3).map(s => s.substring(0, 20)).join(' | ')}}]`);
        }}
        return identifiers;
    }}
    
    // 填充输入框 - Vue/Element-UI 兼容
    function fillInputCredamo(input, value) {{
        input.focus();
        input.value = '';
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
        return true;
    }}
    
    // 主执行函数 - 使用共享执行器
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
        
        // 使用共享执行器
        const executor = createSharedExecutor({{
            fillData: fillData,
            allInputs: allInputs,
            getIdentifiers: getInputIdentifiers,
            fillInput: fillInputCredamo,
            onProgress: (msg) => console.log(msg)
        }});
        
        const result = await executor.execute();
        window.__autoFillResult__ = result;
        
        console.log(`\\n✅ 见数表单填写完成: ${{result.fillCount}}/${{result.totalCount}} 个输入框`);
    }}
    
    executeAutoFill();
    return '见数(Credamo)填写脚本已执行';
}})();
        """
        return js_code
    
    def generate_wenjuan_fill_script(self, fill_data: list) -> str:
        """生成问卷网(wenjuan.com)专用的填充脚本 - 使用共享匹配算法"""
        import json
        from core.tencent_docs_filler import TencentDocsFiller
        
        fill_data_json = json.dumps(fill_data, ensure_ascii=False)
        
        # 获取共享的匹配算法和执行逻辑
        shared_algorithm = TencentDocsFiller.get_shared_match_algorithm()
        shared_executor = TencentDocsFiller.get_shared_execution_logic()
        
        js_code = f"""
(function() {{
    console.log('🚀 开始填写问卷网表单（使用共享算法）...');
    
    const fillData = {fill_data_json};
    
    // ═══════════════════════════════════════════════════════════════
    // 共享匹配算法（来自 TencentDocsFiller.get_shared_match_algorithm()）
    // ═══════════════════════════════════════════════════════════════
{shared_algorithm}
    
    // ═══════════════════════════════════════════════════════════════
    // 共享执行逻辑（来自 TencentDocsFiller.get_shared_execution_logic()）
    // ═══════════════════════════════════════════════════════════════
{shared_executor}
    
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
    
    // 【核心】获取输入框的所有可能标识 - 问卷网精确适配
    // 问卷网结构：
    // <div class="question-box">
    //   <div class="question-title-box">
    //     <div class="question-title-text">
    //       <div class="question-title">
    //         <div><span class="question-seq">*1.</span> 探店时间20号-31号</div>
    //       </div>
    //     </div>
    //   </div>
    //   <div class="question-content">
    //     <textarea class="ws-textarea__inner"></textarea>
    //   </div>
    // </div>
    function getInputIdentifiers(input) {{
        const identifiers = [];
        const MAX_LABEL_LENGTH = 150;
        
        // 辅助函数：添加标识符（带去重和清理）
        function addIdentifier(text, priority = 0) {{
            if (!text) return;
            let cleaned = text.trim();
            // 去除序号前缀（如 "*1."、"2."、"* 3."等）
            cleaned = cleaned.replace(/^[\\*\\s]*\\d+[\\. 、]+\\s*/, '').trim();
            // 去除必填标记
            cleaned = cleaned.replace(/\\*/g, '').replace(/必填/g, '').trim();
            // 去除多余空白
            cleaned = cleaned.replace(/\\s+/g, ' ').trim();
            
            if (cleaned && cleaned.length > 0 && cleaned.length <= MAX_LABEL_LENGTH) {{
                // 去重
                if (!identifiers.some(item => item.text === cleaned)) {{
                    identifiers.push({{ text: cleaned, priority: priority }});
                }}
            }}
        }}
        
        // 【方法1 - 最高优先级】问卷网专用：向上找 .question-box 容器
        let questionBox = input.closest('.question-box, [class*="question-box"]');
        if (questionBox) {{
            // 精确提取 .question-title 内的文本
            const titleDiv = questionBox.querySelector('.question-title, [class*="question-title"]');
            if (titleDiv) {{
                // 获取标题文本（排除序号span）
                const fullText = (titleDiv.innerText || titleDiv.textContent || '').trim();
                addIdentifier(fullText, 100);
                console.log(`[问卷网] question-box精确匹配: "${{fullText.replace(/^[\\*\\s]*\\d+[\\. 、]+\\s*/, '').trim()}}"`);
            }}
            
            // 备选：查找 .question-title-text
            if (identifiers.length === 0) {{
                const titleText = questionBox.querySelector('.question-title-text, [class*="title-text"]');
                if (titleText) {{
                    const text = (titleText.innerText || titleText.textContent || '').trim();
                    addIdentifier(text, 95);
                    console.log(`[问卷网] title-text匹配: "${{text}}"`);
                }}
            }}
        }}
        
        // 【方法2】通用方法：向上查找包含问题的容器
        if (identifiers.length === 0) {{
            let parent = input.closest('.survey-question, .question-item, .wj-question, .el-form-item, [class*="question"]');
            if (parent) {{
                const titleEl = parent.querySelector('.question-title, .wj-title, .el-form-item__label, .title, [class*="title"]:not([class*="title-box"])');
                if (titleEl) {{
                    const text = (titleEl.innerText || titleEl.textContent || '').trim();
                    addIdentifier(text, 90);
                    console.log(`[问卷网] 通用容器匹配: "${{text}}"`);
                }}
            }}
        }}
        
        // 【方法3】aria-labelledby 属性
        const ariaLabelledBy = input.getAttribute('aria-labelledby');
        if (ariaLabelledBy) {{
            ariaLabelledBy.split(' ').forEach(id => {{
                const el = document.getElementById(id);
                if (el) {{
                    const text = (el.innerText || el.textContent || '').trim();
                    if (text && text !== '.') {{
                        addIdentifier(text, 85);
                    }}
                }}
            }});
        }}
        
        // 【方法4】Label 标签关联
        if (input.labels && input.labels.length > 0) {{
            input.labels.forEach(label => {{
                const text = (label.innerText || label.textContent || '').trim();
                addIdentifier(text, 85);
            }});
        }}
        
        // 【方法5】通过 for 属性查找 label
        if (input.id) {{
            const label = document.querySelector(`label[for="${{input.id}}"]`);
            if (label) {{
                const text = (label.innerText || label.textContent || '').trim();
                addIdentifier(text, 85);
            }}
        }}
        
        // 【方法6】placeholder、title、aria-label 基础属性
        if (input.placeholder) addIdentifier(input.placeholder, 70);
        if (input.title) addIdentifier(input.title, 70);
        if (input.getAttribute('aria-label')) addIdentifier(input.getAttribute('aria-label'), 70);
        
        // 【方法7】前置兄弟元素（作为兜底）
        let sibling = input.previousElementSibling;
        for (let i = 0; i < 3 && sibling; i++) {{
            if (sibling.tagName === 'LABEL' || sibling.className.includes('label') || sibling.className.includes('title')) {{
                const text = (sibling.innerText || sibling.textContent || '').trim();
                if (text && text.length <= MAX_LABEL_LENGTH) {{
                    addIdentifier(text, 60);
                    break;
                }}
            }}
            sibling = sibling.previousElementSibling;
        }}
        
        // 按优先级排序，优先级高的在前
        identifiers.sort((a, b) => {{
            if (b.priority !== a.priority) return b.priority - a.priority;
            // 优先级相同时，短标题优先（更精确）
            return a.text.length - b.text.length;
        }});
        
        const result = identifiers.map(item => item.text);
        if (result.length > 0) {{
            console.log(`[问卷网] 输入框标识符: [${{result.slice(0, 3).join(' | ')}}]`);
        }} else {{
            console.warn(`[问卷网] 输入框未找到标识符`);
        }}
        return result;
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
    
    // ═══════════════════════════════════════════════════════════════
    // 主执行函数 - 调用共享执行器（来自 TencentDocsFiller）
    // ═══════════════════════════════════════════════════════════════
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
        
        const allInputs = getAllInputs();
        
        // 使用共享执行器
        const executor = createSharedExecutor({{
            fillData: fillData,
            allInputs: allInputs,
            getIdentifiers: getInputIdentifiers,
            fillInput: fillInput,
            onProgress: (msg) => console.log(msg)
        }});
        
        const result = await executor.execute();
        window.__autoFillResult__ = result;
        
        console.log(`\\n✅ 问卷网填写完成: ${{result.fillCount}}/${{result.totalCount}} 个输入框`);
    }}
    
    executeAutoFill();
    return '问卷网填写脚本已执行';
}})();
        """
        return js_code
    
    def generate_fanqier_fill_script(self, fill_data: list) -> str:
        """生成番茄表单(fanqier.cn)专用的填充脚本 - Vue框架适配 v3.0（使用共享算法）"""
        import json
        from core.tencent_docs_filler import TencentDocsFiller
        
        fill_data_json = json.dumps(fill_data, ensure_ascii=False)
        
        # 获取共享算法和执行逻辑
        shared_algorithm = TencentDocsFiller.get_shared_match_algorithm()
        shared_executor = TencentDocsFiller.get_shared_execution_logic()
        
        js_code = f"""
(function() {{
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('🍅 番茄表单填充脚本 v3.0（共享算法）');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('页面URL:', window.location.href);
    console.log('页面标题:', document.title);
    
    let fillData, fillCount, results;
    
    try {{
        fillData = {fill_data_json};
        fillCount = 0;
        results = [];
        console.log('📇 接收到名片数据:', fillData.length, '个字段');
    }} catch(err) {{
        console.error('❌ JSON解析出错:', err.message);
        return '数据解析失败: ' + err.message;
    }}
    
    // ═══════════════════════════════════════════════════════════════
    // 共享匹配算法（来自 TencentDocsFiller）
    // ═══════════════════════════════════════════════════════════════
    {shared_algorithm}
    
    // ═══════════════════════════════════════════════════════════════
    // 共享执行逻辑（来自 TencentDocsFiller）
    // ═══════════════════════════════════════════════════════════════
    {shared_executor}
    
    // ═══════════════════════════════════════════════════════════════
    // 填充函数 - Vue框架深度兼容
    // ═══════════════════════════════════════════════════════════════
    
    function fillInput(input, value) {{
        if (!input) return false;
        
        // 聚焦
        input.focus();
        input.click();
        
        // 清空
        input.value = '';
        
        // 使用原生setter设置值（绕过Vue的响应式）
        const isTextArea = input.tagName === 'TEXTAREA';
        const proto = isTextArea ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
        
        try {{
            const nativeValueSetter = Object.getOwnPropertyDescriptor(proto, 'value').set;
            nativeValueSetter.call(input, value);
        }} catch (e) {{
            input.value = value;
        }}
        
        // 触发Vue响应式更新
        const inputEvent = new InputEvent('input', {{
            bubbles: true,
            cancelable: true,
            inputType: 'insertText',
            data: value
        }});
        input.dispatchEvent(inputEvent);
        
        // 触发change事件
        input.dispatchEvent(new Event('change', {{ bubbles: true, cancelable: true }}));
        
        // 模拟键盘事件（某些Vue组件需要）
        ['keydown', 'keypress', 'keyup'].forEach(eventName => {{
            input.dispatchEvent(new KeyboardEvent(eventName, {{
                bubbles: true,
                cancelable: true,
                key: value.slice(-1) || 'a'
            }}));
        }});
        
        // 触发compositionend（中文输入法兼容）
        try {{
            input.dispatchEvent(new CompositionEvent('compositionend', {{ bubbles: true, data: value }}));
        }} catch (e) {{}}
        
        // 确保值已设置
        if (input.value !== value) {{
            input.value = value;
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}
        
        // 失焦触发验证
        input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
        
        return input.value === value;
    }}
    
    // 处理下拉选择
    function handleSelect(fieldDiv, value) {{
        // 番茄表单的下拉框使用 Element UI 的 el-select
        const selectTrigger = fieldDiv.querySelector('.el-select, .fq-select, [class*="select"]');
        if (!selectTrigger) return false;
        
        // 点击打开下拉框
        selectTrigger.click();
        
        setTimeout(() => {{
            // 查找下拉选项
            const options = document.querySelectorAll('.el-select-dropdown__item, .fq-select-dropdown__item, [class*="select-dropdown"] li');
            const cleanValue = cleanText(value);
            
            for (const option of options) {{
                const optionText = cleanText(option.innerText || option.textContent || '');
                if (optionText === cleanValue || optionText.includes(cleanValue) || cleanValue.includes(optionText)) {{
                    option.click();
                    console.log(`   📋 选择: "${{option.innerText}}"`);
                    return true;
                }}
            }}
        }}, 100);
        
        return false;
    }}
    
    // 处理单选/多选
    function handleRadioCheckbox(fieldDiv, value) {{
        const radios = fieldDiv.querySelectorAll('input[type="radio"], input[type="checkbox"], .el-radio, .el-checkbox, .fq-radio, .fq-checkbox');
        if (radios.length === 0) return false;
        
        const cleanValue = cleanText(value);
        const selectedValues = value.split(/[,，、;；|｜]+/).map(v => cleanText(v));
        let filled = false;
        
        radios.forEach(radio => {{
            const wrapper = radio.closest('.el-radio, .el-checkbox, .fq-radio, .fq-checkbox, label');
            const optionText = cleanText(wrapper ? (wrapper.innerText || '') : '');
            
            const shouldSelect = selectedValues.some(v => 
                optionText === v || optionText.includes(v) || v.includes(optionText)
            );
            
            if (shouldSelect) {{
                if (wrapper) wrapper.click();
                else radio.click();
                console.log(`   ☑️  选中: "${{wrapper?.innerText || ''}}"`)
                filled = true;
            }}
        }});
        
        return filled;
    }}
    
    // ═══════════════════════════════════════════════════════════════
    // 解析番茄表单结构
    // ═══════════════════════════════════════════════════════════════
    
    function parseFanqierFields() {{
        const fields = [];
        
        // 番茄表单的字段容器：div[data-type] 或 .fq-field
        const fieldDivs = document.querySelectorAll('[data-type]:not([data-type="title"]), .fq-field:not(.fq-field-title)');
        
        console.log(`\\n📊 发现 ${{fieldDivs.length}} 个表单字段`);
        
        fieldDivs.forEach((fieldDiv, index) => {{
            const dataType = fieldDiv.getAttribute('data-type') || 'unknown';
            const dataId = fieldDiv.getAttribute('data-id') || '';
            
            // 获取字段标题
            let title = '';
            const labelEl = fieldDiv.querySelector('.fq-field__label span, .fq-field__label, h3[class*="label"], [class*="field__label"]');
            if (labelEl) {{
                title = (labelEl.innerText || labelEl.textContent || '').trim();
                // 去除必填星号等
                title = title.replace(/^\\*\\s*/, '').replace(/\\s*\\*$/, '').trim();
            }}
            
            // 获取输入元素
            let inputEl = null;
            let inputType = 'text';
            
            // 番茄表单的 data-type 类型包括：
            const textTypes = ['text', 'textarea', 'number', 'email', 'phone', 'name', 'text-evaluation', 'mobile', 'address', 'link'];
            
            if (textTypes.includes(dataType)) {{
                inputEl = fieldDiv.querySelector('.fq-input__inner, input[type="text"], input:not([type]), textarea');
                inputType = 'text';
            }} else if (dataType === 'select' || dataType === 'dropdown' || dataType === 'single-select' || dataType === 'multi-select') {{
                inputEl = fieldDiv;
                inputType = 'select';
            }} else if (dataType === 'radio' || dataType === 'checkbox' || dataType === 'single-choice' || dataType === 'multi-choice') {{
                inputEl = fieldDiv;
                inputType = dataType.includes('radio') || dataType.includes('single') ? 'radio' : 'checkbox';
            }} else {{
                // 尝试通用查找输入框
                inputEl = fieldDiv.querySelector('.fq-input__inner, input[type="text"], input:not([type]), textarea');
                if (inputEl) {{
                    inputType = 'text';
                }}
            }}
            
            if (title || inputEl) {{
                fields.push({{
                    element: fieldDiv,
                    input: inputEl,
                    dataType: dataType,
                    inputType: inputType,
                    dataId: dataId,
                    title: title,
                    index: index
                }});
                
                console.log(`  [${{index + 1}}] type=${{dataType}}: "${{title.substring(0, 30)}}${{title.length > 30 ? '...' : ''}}"`);
            }}
        }});
        
        return fields;
    }}
    
    // ═══════════════════════════════════════════════════════════════
    // 获取输入框标识符（适配器函数）
    // ═══════════════════════════════════════════════════════════════
    function getInputIdentifiers(field, index) {{
        return [field.title];
    }}
    
    // ═══════════════════════════════════════════════════════════════
    // 填充输入框（适配器函数）
    // ═══════════════════════════════════════════════════════════════
    async function fillInputFanqier(field, value) {{
        const {{ element: fieldDiv, input: inputEl, inputType }} = field;
        
        switch (inputType) {{
            case 'text':
                if (inputEl && inputEl.tagName) {{
                    return fillInput(inputEl, value);
                }}
                return false;
            case 'select':
                return handleSelect(fieldDiv, value);
            case 'radio':
            case 'checkbox':
                return handleRadioCheckbox(fieldDiv, value);
            default:
                if (inputEl && inputEl.tagName) {{
                    return fillInput(inputEl, value);
                }}
                return false;
        }}
    }}
    
    // ═══════════════════════════════════════════════════════════════
    // 主执行函数 - 使用共享执行器
    // ═══════════════════════════════════════════════════════════════
    
    async function executeAutoFill() {{
        window.__fanqierFillStatus__ = {{ status: 'starting', message: '开始填充...' }};
        
        // 等待页面加载
        await new Promise(resolve => setTimeout(resolve, 800));
        
        // 打印名片字段
        console.log('\\n📇 名片字段列表:');
        fillData.forEach((item, i) => {{
            const valuePreview = String(item.value).substring(0, 30) + (String(item.value).length > 30 ? '...' : '');
            console.log(`   ${{i + 1}}. "${{item.key}}" = "${{valuePreview}}"`);
        }});
        
        // 解析表单结构
        const fields = parseFanqierFields();
        
        if (fields.length === 0) {{
            console.warn('⚠️ 未识别到番茄表单字段，尝试兼容模式...');
            await fallbackFill();
            return;
        }}
        
        // 使用共享执行器
        const executor = createSharedExecutor({{
            fillData: fillData,
            allInputs: fields,
            getIdentifiers: getInputIdentifiers,
            fillInput: fillInputFanqier,
            onProgress: (msg) => console.log(msg)
        }});
        
        const result = await executor.execute();
        
        window.__autoFillResult__ = result;
        window.__fanqierFillStatus__ = {{
            status: 'completed',
            message: `填写完成: ${{result.fillCount}}/${{result.totalCount}} 个字段`
        }};
        
        console.log(`\\n✅ 番茄表单填写完成: ${{result.fillCount}}/${{result.totalCount}} 个字段`);
        console.log('═══════════════════════════════════════════════════════════════\\n');
    }}
    
    // 兼容模式：直接扫描所有输入框
    async function fallbackFill() {{
        console.log('\\n⚡ 启动兼容模式...');
        
        const allInputs = document.querySelectorAll([
            '.fq-input__inner',
            'input[type="text"]:not([readonly]):not([disabled])',
            'input:not([type]):not([readonly]):not([disabled])',
            'textarea:not([readonly]):not([disabled])'
        ].join(', '));
        
        console.log(`找到 ${{allInputs.length}} 个可编辑输入框`);
        
        let fillCount = 0;
        const results = [];
        
        for (let index = 0; index < allInputs.length; index++) {{
            const input = allInputs[index];
            const style = window.getComputedStyle(input);
            if (style.display === 'none' || style.visibility === 'hidden') continue;
            
            // 获取标签
            const identifiers = [];
            
            // 向上查找字段容器
            const fieldDiv = input.closest('.fq-field, [data-type], [class*="field"]');
            if (fieldDiv) {{
                const labelEl = fieldDiv.querySelector('.fq-field__label span, .fq-field__label, h3, label');
                if (labelEl) {{
                    const text = (labelEl.innerText || '').trim().replace(/^\\*\\s*/, '');
                    if (text && text.length < 50) identifiers.push(text);
                }}
            }}
            
            if (input.placeholder && input.placeholder !== '请输入内容') {{
                identifiers.push(input.placeholder);
            }}
            
            if (identifiers.length === 0) continue;
            
            // 找最佳匹配
            let bestMatch = null;
            let bestScore = 0;
            for (const item of fillData) {{
                const matchResult = matchKeyword(identifiers, item.key);
                if (matchResult.matched && matchResult.score > bestScore) {{
                    bestMatch = item;
                    bestScore = matchResult.score;
                }}
            }}
            
            if (bestMatch && bestScore >= 50) {{
                const filled = fillInput(input, bestMatch.value);
                if (filled) {{
                    fillCount++;
                    console.log(`   ✅ [${{index + 1}}] "${{identifiers[0]}}" → "${{bestMatch.value}}"`);
                    results.push({{
                        key: bestMatch.key,
                        value: bestMatch.value,
                        matched: identifiers[0],
                        score: bestScore,
                        success: true
                    }});
                }}
            }}
        }}
        
        window.__autoFillResult__ = {{
            fillCount: fillCount,
            totalCount: allInputs.length,
            status: 'completed',
            results: results
        }};
        
        window.__fanqierFillStatus__ = {{
            status: 'completed',
            message: `兼容模式填写完成: ${{fillCount}} 个字段`
        }};
        
        console.log(`\\n✅ 兼容模式填写完成: ${{fillCount}} 个字段`);
    }}
    
    // 启动
    window.__fanqierFillStatus__ = {{
        status: 'starting',
        message: '脚本已启动',
        timestamp: Date.now()
    }};
    
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', () => executeAutoFill());
    }} else {{
        executeAutoFill();
    }}
    
    return '番茄表单填写脚本(v3.0)已启动';
}})();
        """
        return js_code
    
    def generate_feishu_fill_script(self, fill_data: list) -> str:
        """生成飞书问卷(feishu.cn)专用的填充脚本 - 使用共享匹配算法"""
        import json
        from core.tencent_docs_filler import TencentDocsFiller
        
        fill_data_json = json.dumps(fill_data, ensure_ascii=False)
        
        # 获取共享的匹配算法和执行逻辑
        shared_algorithm = TencentDocsFiller.get_shared_match_algorithm()
        shared_executor = TencentDocsFiller.get_shared_execution_logic()
        
        js_code = f"""
(function() {{
    console.log('🐦 开始填写飞书问卷（使用共享算法）...');
    
    const fillData = {fill_data_json};
    
    // ═══════════════════════════════════════════════════════════════
    // 共享匹配算法（来自 TencentDocsFiller.get_shared_match_algorithm()）
    // ═══════════════════════════════════════════════════════════════
{shared_algorithm}
    
    // ═══════════════════════════════════════════════════════════════
    // 共享执行逻辑（来自 TencentDocsFiller.get_shared_execution_logic()）
    // ═══════════════════════════════════════════════════════════════
{shared_executor}
    
    // 检测表单版本
    function detectFormVersion() {{
        // 新版/移动端: bitable-form-item
        const newVersionItems = document.querySelectorAll('.bitable-form-item[data-index]');
        // 旧版: base-form-container_card_item
        const oldVersionItems = document.querySelectorAll('.base-form-container_card_item');
        
        if (newVersionItems.length > 0) {{
            return 'new';
        }} else if (oldVersionItems.length > 0) {{
            return 'old';
        }}
        return null;
    }}
    
    // 等待飞书表单加载完成
    function waitForForm(maxAttempts = 25, interval = 400) {{
        return new Promise((resolve) => {{
            let attempts = 0;
            const checkForm = setInterval(() => {{
                attempts++;
                const version = detectFormVersion();
                
                // 新版表单
                const newItems = document.querySelectorAll('.bitable-form-item[data-index]');
                // 旧版表单
                const oldItems = document.querySelectorAll('.base-form-container_card_item');
                
                const totalItems = newItems.length + oldItems.length;
                console.log(`🔍 尝试 ${{attempts}}/${{maxAttempts}}: 找到 ${{totalItems}} 个字段 (新版:${{newItems.length}}, 旧版:${{oldItems.length}})`);
                
                if (totalItems > 0 || attempts >= maxAttempts) {{
                    clearInterval(checkForm);
                    resolve({{ found: totalItems > 0, version: version }});
                }}
            }}, interval);
        }});
    }}
    
    // 获取所有字段信息 - 新版表单
    function getAllFieldsNewVersion() {{
        const fields = [];
        
        // 新版飞书表单使用 .bitable-form-item[data-index] 作为字段容器
        document.querySelectorAll('.bitable-form-item[data-index]').forEach((item, index) => {{
            // 向上查找包含标题的父容器
            const fieldContainer = item.closest('[id^="field-item-"]') || item.closest('.ud__form__item');
            if (!fieldContainer) return;
            
            // 获取字段标题 - 新版在 label 元素中
            const labelEl = fieldContainer.querySelector('.ud__form__item__label label');
            const title = labelEl ? labelEl.innerText.trim() : '';
            
            // 获取可编辑的富文本区域
            const editor = item.querySelector('[contenteditable="true"].adit-container');
            
            // 获取选择器类型字段（支持移动端和桌面端两种结构）
            // 移动端: .bitable-selector-option-wrapper
            // 桌面端: .bitable-single-selector-editor, .b-select-dropdown-menu
            const selectorMobile = item.querySelector('.bitable-selector-option-wrapper');
            const selectorDesktop = item.querySelector('.bitable-single-selector-editor, .b-select-dropdown-menu');
            const selector = selectorMobile || selectorDesktop;
            const selectorType = selectorMobile ? 'mobile' : (selectorDesktop ? 'desktop' : null);
            
            if (title) {{
                fields.push({{
                    index: index,
                    title: title,
                    editor: editor,
                    selector: selector,
                    selectorType: selectorType,
                    container: item,
                    fieldType: selector ? 'select' : 'text'
                }});
                console.log(`  字段 ${{index + 1}}: "${{title}}" (${{selector ? '选择(' + selectorType + ')' : '文本'}})`);
            }}
        }});
        
        return fields;
    }}
    
    // 获取所有字段信息 - 旧版表单
    function getAllFieldsOldVersion() {{
        const fields = [];
        
        // 旧版飞书问卷使用 .base-form-container_card_item 作为字段容器
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
                    selector: null,
                    container: card,
                    fieldType: 'text'
                }});
                console.log(`  字段 ${{index + 1}}: "${{title}}"`);
            }}
        }});
        
        return fields;
    }}
    
    // 获取所有字段信息（自动识别版本）
    function getAllFields(version) {{
        if (version === 'new') {{
            return getAllFieldsNewVersion();
        }} else {{
            return getAllFieldsOldVersion();
        }}
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
    
    // 填充选择器类型字段（支持移动端和桌面端）
    async function fillSelector(field, value) {{
        try {{
            const selector = field.selector;
            const selectorType = field.selectorType;
            if (!selector) return false;
            
            console.log(`    尝试填充选择器 (类型: ${{selectorType}}), 值: "${{value}}"`);
            
            let options = [];
            let matched = false;
            
            if (selectorType === 'desktop') {{
                // 桌面端选择器处理
                // 点击下拉菜单打开选项
                const dropdownMenu = selector.querySelector('.b-select-dropdown-menu') || selector;
                dropdownMenu.click();
                await new Promise(r => setTimeout(r, 400));
                
                // 桌面端选项在 .b-select-option 内，文本在 .ud__tag__content
                options = field.container.querySelectorAll('.b-select-option');
                console.log(`    桌面端找到 ${{options.length}} 个选项`);
                
                for (const opt of options) {{
                    const contentEl = opt.querySelector('.ud__tag__content');
                    const optText = contentEl ? contentEl.innerText.trim() : opt.innerText.trim();
                    console.log(`      检查选项: "${{optText}}"`);
                    
                    if (optText.includes(value) || value.includes(optText)) {{
                        opt.click();
                        matched = true;
                        console.log(`    ✅ 桌面端选择: "${{optText}}"`);
                        break;
                    }}
                }}
                
                // 模糊匹配
                if (!matched) {{
                    for (const opt of options) {{
                        const contentEl = opt.querySelector('.ud__tag__content');
                        const optText = (contentEl ? contentEl.innerText.trim() : opt.innerText.trim()).toLowerCase();
                        const valLower = value.toLowerCase();
                        if (optText.includes(valLower) || valLower.includes(optText)) {{
                            opt.click();
                            matched = true;
                            console.log(`    ✅ 桌面端模糊选择: "${{opt.innerText.trim()}}"`);
                            break;
                        }}
                    }}
                }}
            }} else {{
                // 移动端选择器处理
                selector.click();
                await new Promise(r => setTimeout(r, 300));
                
                // 查找选项列表
                const optionList = document.querySelector('.bitable-selector-option-list, .ud__select__dropdown');
                if (!optionList) {{
                    console.warn('    未找到移动端选项列表');
                    return false;
                }}
                
                options = optionList.querySelectorAll('.bitable-selector-option, .ud__select__option');
                console.log(`    移动端找到 ${{options.length}} 个选项`);
                
                for (const opt of options) {{
                    const optText = opt.innerText.trim();
                    if (optText.includes(value) || value.includes(optText)) {{
                        opt.click();
                        matched = true;
                        console.log(`    ✅ 移动端选择: "${{optText}}"`);
                        break;
                    }}
                }}
                
                // 模糊匹配
                if (!matched) {{
                    for (const opt of options) {{
                        const optText = opt.innerText.trim().toLowerCase();
                        const valLower = value.toLowerCase();
                        if (optText.includes(valLower) || valLower.includes(optText)) {{
                            opt.click();
                            matched = true;
                            console.log(`    ✅ 移动端模糊选择: "${{opt.innerText.trim()}}"`);
                            break;
                        }}
                    }}
                }}
            }}
            
            // 关闭下拉（点击其他地方）
            if (!matched) {{
                console.warn(`    ⚠️ 未找到匹配选项: "${{value}}"`);
                document.body.click();
            }}
            
            await new Promise(r => setTimeout(r, 200));
            return matched;
        }} catch (e) {{
            console.error(`    ❌ 选择失败: ${{e.message}}`);
            return false;
        }}
    }}
    
    // ═══════════════════════════════════════════════════════════════
    // 飞书专用填充函数（包装器，用于适配共享执行器）
    // ═══════════════════════════════════════════════════════════════
    async function fillInputFeishu(field, value) {{
        // 根据字段类型选择填充方式
        if (field.fieldType === 'select' && field.selector) {{
            return await fillSelector(field, value);
        }} else if (field.editor) {{
            return fillEditor(field.editor, value);
        }}
        return false;
    }}
    
    // ═══════════════════════════════════════════════════════════════
    // 主执行函数 - 调用共享执行器（来自 TencentDocsFiller）
    // ═══════════════════════════════════════════════════════════════
    async function executeAutoFill() {{
        const formResult = await waitForForm();
        
        if (!formResult.found) {{
            console.warn('⚠️ 未找到飞书问卷表单');
            window.__autoFillResult__ = {{
                fillCount: 0,
                totalCount: fillData.length,
                status: 'completed',
                results: []
            }};
            return;
        }}
        
        console.log(`\\n📋 检测到飞书表单版本: ${{formResult.version === 'new' ? '新版/移动端' : '旧版'}}`);
        const allFields = getAllFields(formResult.version);
        
        // 使用共享执行器
        const executor = createSharedExecutor({{
            fillData: fillData,
            allInputs: allFields,
            getIdentifiers: (field, index) => [field.title],  // 飞书字段的标识符就是标题
            fillInput: fillInputFeishu,  // 飞书专用填充函数（支持选择器和编辑器）
            onProgress: (msg) => console.log(msg)
        }});
        
        const result = await executor.execute();
        window.__autoFillResult__ = result;
        
        console.log(`\\n✅ 飞书问卷填写完成: ${{result.fillCount}}/${{result.totalCount}} 个字段`);
    }}
    
    executeAutoFill();
    return '飞书问卷填写脚本已执行';
}})();
        """
        return js_code
    
    def generate_kdocs_fill_script(self, fill_data: list) -> str:
        """生成WPS表单(kdocs.cn/wps.cn)专用的填充脚本 - 使用腾讯文档的共享匹配算法和执行逻辑"""
        import json
        from core.tencent_docs_filler import TencentDocsFiller
        
        fill_data_json = json.dumps(fill_data, ensure_ascii=False)
        
        # 获取共享的匹配算法和执行逻辑
        shared_algorithm = TencentDocsFiller.get_shared_match_algorithm()
        shared_executor = TencentDocsFiller.get_shared_execution_logic()
        
        js_code = f"""
(function() {{
    console.log('🚀 开始填写WPS表单(优化版)...');
    
    // 🔧 自动适配移动端视口
    (function adaptViewport() {{
        const existingViewport = document.querySelector('meta[name="viewport"]');
        if (existingViewport) {{
            existingViewport.remove();
        }}
        
        const viewport = document.createElement('meta');
        viewport.name = 'viewport';
        viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';
        document.head.appendChild(viewport);
        
        const style = document.createElement('style');
        style.textContent = `
            body {{
                width: 100% !important;
                min-width: 100% !important;
                max-width: 100% !important;
                overflow-x: hidden !important;
            }}
            .ksapc-form-container-write, .ksapc-responsive-form-container-write {{
                width: 100% !important;
                max-width: 100% !important;
                padding: 15px !important;
                box-sizing: border-box !important;
            }}
            input, textarea {{
                width: 100% !important;
                box-sizing: border-box !important;
            }}
        `;
        document.head.appendChild(style);
        console.log('📱 已适配移动端视口');
    }})();
    
    const fillData = {fill_data_json};
    let fillCount = 0;
    const results = [];
    
    // ═══════════════════════════════════════════════════════════════
    // 共享匹配算法（来自 TencentDocsFiller.get_shared_match_algorithm()）
    // ═══════════════════════════════════════════════════════════════
{shared_algorithm}
    
    // ═══════════════════════════════════════════════════════════════
    // 共享执行逻辑（来自 TencentDocsFiller.get_shared_execution_logic()）
    // ═══════════════════════════════════════════════════════════════
{shared_executor}
    
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
    
    // 获取所有可见的输入框（优化：radio/checkbox 组去重）
    function getAllInputs() {{
        const inputs = [];
        const radioGroups = new Map(); // 记录已处理的 radio/checkbox 组
        
        document.querySelectorAll('input, textarea').forEach(input => {{
            const style = window.getComputedStyle(input);
            if (style.display === 'none' || style.visibility === 'hidden') {{
                return; // 跳过隐藏元素
            }}
            
            // 【优化】radio button 和 checkbox 去重
            // 使用多种方式识别同一组：name、容器、问题ID
            if (input.type === 'radio' || input.type === 'checkbox') {{
                // 方式1：使用 name 属性
                let groupKey = input.name;
                
                // 方式2：如果没有 name，使用最近的问题容器 ID
                if (!groupKey) {{
                    const container = input.closest('.ksapc-questions-write-container, [class*="question"]');
                    if (container) {{
                        groupKey = container.id || container.className;
                    }}
                }}
                
                // 方式3：兜底 - 使用问题标题
                if (!groupKey) {{
                    const titleEl = input.closest('.ksapc-questions-write-container')?.querySelector('.ksapc-question-title-title');
                    if (titleEl) {{
                        groupKey = 'title:' + (titleEl.textContent || '').trim();
                    }}
                }}
                
                if (groupKey) {{
                    if (radioGroups.has(groupKey)) {{
                        // 已经有这个组的代表了，跳过
                        console.log(`[WPS] 跳过重复的 ${{input.type}} 组成员: key="${{groupKey.substring(0, 30)}}..."`);
                        return;
                    }}
                    // 记录这个组，并使用第一个作为代表
                    radioGroups.set(groupKey, input);
                    console.log(`[WPS] 保留 ${{input.type}} 组代表: key="${{groupKey.substring(0, 30)}}..."`);
                }} else {{
                    console.warn(`[WPS] ⚠️ 无法确定 ${{input.type}} 的组标识，保留此元素`);
                }}
            }}
            
            inputs.push(input);
        }});
        
        console.log(`[WPS] ✅ 去重后共 ${{inputs.length}} 个输入框（原始查询: ${{document.querySelectorAll('input, textarea').length}} 个）`);
        return inputs;
    }}
    
    // 【核心】WPS表单专用：精确提取输入框对应的问题标识
    // WPS表单结构：
    // <div class="ksapc-form-container-write">
    //   <div class="ksapc-theme-back">
    //     问题标题文本
    //     <input />
    //   </div>
    // </div>
    function getInputIdentifiers(input, inputIndex) {{
        const identifiers = [];
        const MAX_LABEL_LENGTH = 150;
        
        // 【优化】检测输入框类型：radio/checkbox 只提取问题标题，不提取选项文本
        const isRadioOrCheckbox = input.type === 'radio' || input.type === 'checkbox';
        if (isRadioOrCheckbox) {{
            console.log(`[WPS] 检测到 ${{input.type}} 类型，只提取问题标题`);
        }}
        
        // 辅助函数：添加标识符（带去重和优先级）
        function addIdentifier(text, priority = 0) {{
            if (!text) return;
            let cleaned = text.trim();
            // 去除序号前缀（如 "01."、"1."等）
            cleaned = cleaned.replace(/^\\d{{1,2}}\\.\\s*\\*?\\s*/, '').trim();
            // 去除多余空白和特殊符号
            cleaned = cleaned.replace(/^[\\s*]+|[\\s*]+$/g, '').trim();
            // 去除必填标记
            cleaned = cleaned.replace(/\\*/g, '').replace(/必填/g, '').trim();
            
            if (cleaned && cleaned.length > 0 && cleaned.length <= MAX_LABEL_LENGTH) {{
                if (!identifiers.some(item => item.text === cleaned)) {{
                    identifiers.push({{ text: cleaned, priority: priority }});
                }}
            }}
        }}
        
        // 【方法1 - 最高优先级】WPS表单专用：查找问题容器
        // 注意：必须精确匹配问题容器，不能用 [class*="ksapc"] 因为会匹配到输入框本身的容器
        let container = input.closest('.ksapc-questions-write-container');
        if (!container) {{
            // 备用：尝试其他可能的容器
            container = input.closest('.ksapc-theme-back, [class*="form-item"], [class*="question-container"]');
        }}
        console.log(`[WPS DEBUG] 输入框#${{inputIndex + 1}} 容器: ${{container ? container.className : '未找到'}}`);
        if (container) {{
            // 【WPS专用】精确查找标题元素 - ksapc-question-title-title 是纯净标题
            const wpsTitleEl = container.querySelector('.ksapc-question-title-title, pre.ksapc-question-title-title');
            console.log(`[WPS DEBUG] 标题元素: ${{wpsTitleEl ? wpsTitleEl.className : '未找到'}}`);
            if (wpsTitleEl) {{
                let titleText = (wpsTitleEl.innerText || wpsTitleEl.textContent || '').trim();
                console.log(`[WPS DEBUG] 原始标题文本: "${{titleText}}"`);
                
                // 【优化】如果标题包含多个空格，说明有额外的说明文字，只取第一部分
                if (titleText.includes('   ') || titleText.includes('  ')) {{
                    titleText = titleText.split(/\s{{2,}}/)[0].trim();
                    console.log(`[WPS DEBUG] 清理后标题: "${{titleText}}"`);
                }}
                
                if (titleText && titleText.length <= MAX_LABEL_LENGTH) {{
                    addIdentifier(titleText, 100);  // WPS纯净标题最高优先级
                    console.log(`[WPS] ✅ 精确标题匹配: "${{titleText}}"`);
                }}
            }}
            
            // 【WPS专用】查找序号元素
            const indexEl = container.querySelector('.ksapc-question-title-index');
            if (indexEl && wpsTitleEl) {{
                const indexText = (indexEl.innerText || indexEl.textContent || '').trim();
                const titleText = (wpsTitleEl.innerText || wpsTitleEl.textContent || '').trim();
                const fullTitle = indexText + titleText;
                if (fullTitle && fullTitle.length <= MAX_LABEL_LENGTH) {{
                    addIdentifier(fullTitle, 95);  // 带序号的完整标题
                }}
            }}
            
            // 【通用备用】如果WPS专用选择器没找到，尝试通用选择器
            if (identifiers.length === 0) {{
                const titleEl = container.querySelector('[class*="title-title"], [class*="label"], label, h3, h4');
                if (titleEl) {{
                    let titleText = (titleEl.innerText || titleEl.textContent || '').trim();
                    // 如果标题包含换行，只取第一行
                    if (titleText.includes('\\n')) {{
                        titleText = titleText.split('\\n')[0].trim();
                    }}
                    const cleanTitle = titleText.replace(/^\\d{{1,2}}\\.\\s*\\*?\\s*/, '').trim();
                    if (cleanTitle && cleanTitle.length <= MAX_LABEL_LENGTH) {{
                        addIdentifier(cleanTitle, 90);
                        console.log(`[WPS] 通用标题匹配: "${{cleanTitle}}"`);
                    }}
                }}
            }}
            
            // 【兜底】提取容器中的直接文本节点
            if (identifiers.length === 0) {{
                const titleContainer = container.querySelector('.ksapc-question-title');
                if (titleContainer) {{
                    // 遍历直接子节点，找到包含标题的文本
                    for (const child of titleContainer.querySelectorAll('*')) {{
                        const text = (child.innerText || child.textContent || '').trim();
                        // 跳过备注（note）和过长文本
                        if (child.className && child.className.includes('note')) continue;
                        if (text && text.length > 0 && text.length <= 50 && !text.includes('[填')) {{
                            const cleanTitle = text.replace(/^\\d{{1,2}}\\.\\s*\\*?\\s*/, '').trim();
                            if (cleanTitle) {{
                                addIdentifier(cleanTitle, 85);
                                console.log(`[WPS] 兜底标题匹配: "${{cleanTitle}}"`);
                                break;
                            }}
                        }}
                    }}
                }}
            }}
        }}
        
        // 【方法2】向上查找包含问题标题的容器
        if (identifiers.length === 0) {{
            let parent = input.parentElement;
            for (let depth = 0; depth < 8 && parent; depth++) {{
                const titleEl = parent.querySelector(':scope > h2, :scope > h3, :scope > h4, :scope [class*="title"], :scope [class*="label"]');
                if (titleEl) {{
                    const text = (titleEl.innerText || titleEl.textContent || '').trim();
                    const cleanedText = text.replace(/^\\d{{1,2}}\\.\\s*\\*?\\s*/, '').trim();
                    if (cleanedText && cleanedText.length <= MAX_LABEL_LENGTH) {{
                        addIdentifier(cleanedText, 90);
                        console.log(`[WPS] 向上查找匹配: "${{cleanedText}}"`);
                        break;
                    }}
                }}
                parent = parent.parentElement;
            }}
        }}
        
        // 【方法3】aria-labelledby 属性（radio/checkbox 跳过）
        if (!isRadioOrCheckbox) {{
            const ariaLabelledBy = input.getAttribute('aria-labelledby');
            if (ariaLabelledBy) {{
                ariaLabelledBy.split(' ').forEach(id => {{
                    const el = document.getElementById(id);
                    if (el) {{
                        addIdentifier(el.innerText || el.textContent, 85);
                    }}
                }});
            }}
        }}
        
        // 【方法4】Label 标签关联（radio/checkbox 跳过，避免提取选项文本）
        if (!isRadioOrCheckbox && input.labels && input.labels.length > 0) {{
            input.labels.forEach(label => {{
                addIdentifier(label.innerText || label.textContent, 85);
            }});
        }}
        
        // 【方法5】placeholder、title、aria-label 基础属性（radio/checkbox 跳过）
        if (!isRadioOrCheckbox) {{
            // 【优化】过滤通用的、太短的 placeholder，避免干扰匹配
            if (input.placeholder) {{
                const ph = input.placeholder.trim();
                const genericPlaceholders = ['请输入', '请填写', '请选择', '输入', '填写', '选择', 
                                             '图文', '视频', '文本', '数字', '日期', '时间'];
                const isGeneric = genericPlaceholders.some(g => ph === g || ph.includes('请') && ph.length <= 4);
                
                if (!isGeneric && ph.length > 2) {{
                    addIdentifier(ph, 50);  // 降低优先级从70到50
                    console.log(`[WPS] 添加placeholder标识: "${{ph}}" (优先级:50)`);
                }} else {{
                    console.log(`[WPS] 跳过通用placeholder: "${{ph}}"`);
                }}
            }}
            if (input.title) addIdentifier(input.title, 70);
            if (input.getAttribute('aria-label')) addIdentifier(input.getAttribute('aria-label'), 70);
        }}
        
        // 【方法6】前置兄弟元素（作为兜底，radio/checkbox 跳过）
        if (!isRadioOrCheckbox) {{
            let sibling = input.previousElementSibling;
            for (let i = 0; i < 3 && sibling; i++) {{
                if (sibling.tagName === 'H2' || sibling.tagName === 'H3' || 
                    sibling.tagName === 'LABEL' || sibling.className.includes('title') || 
                    sibling.className.includes('label')) {{
                    const text = (sibling.innerText || sibling.textContent || '').trim();
                    if (text && text.length <= MAX_LABEL_LENGTH) {{
                        addIdentifier(text, 60);
                        break;
                    }}
                }}
                sibling = sibling.previousElementSibling;
            }}
        }}
        
        // 【最终过滤】如果是 radio/checkbox，移除可能的选项文本
        if (isRadioOrCheckbox) {{
            const optionTexts = ['图文', '视频', '是', '否', '确认', '取消', '同意', '不同意', '已知晓'];
            const filtered = identifiers.filter(item => {{
                const text = item.text.trim();
                // 保留较长的标识符（问题标题）
                if (text.length > 6) return true;
                // 移除短的通用选项文本
                if (optionTexts.includes(text)) {{
                    console.log(`[WPS] 过滤选项文本: "${{text}}"`);
                    return false;
                }}
                // 移除纯数字或百分比（如 "50%", "55%"）
                if (/^\\d+%?$/.test(text)) {{
                    console.log(`[WPS] 过滤数字选项: "${{text}}"`);
                    return false;
                }}
                return true;
            }});
            
            // 如果过滤后还有标识符，使用过滤后的
            if (filtered.length > 0) {{
                identifiers.length = 0;
                identifiers.push(...filtered);
                console.log(`[WPS] ✅ 过滤后保留 ${{filtered.length}} 个标识符（移除选项文本）`);
            }}
        }}
        
        // 按优先级排序
        identifiers.sort((a, b) => {{
            if (b.priority !== a.priority) return b.priority - a.priority;
            return a.text.length - b.text.length;
        }});
        
        const result = identifiers.map(item => item.text);
        if (result.length > 0) {{
            console.log(`[WPS] 输入框#${{inputIndex + 1}} 标识符: [${{result.slice(0, 3).join(' | ')}}]`);
        }} else {{
            console.warn(`[WPS] 输入框#${{inputIndex + 1}} 未找到标识符`);
        }}
        return result;
    }}
    
    // 填充输入框 - React 深度兼容
    function fillInput(input, value) {{
        input.focus();
        input.click();
        input.value = '';
        
        const isTextArea = input.tagName === 'TEXTAREA';
        const proto = isTextArea ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
        
        try {{
            const nativeValueSetter = Object.getOwnPropertyDescriptor(proto, 'value').set;
            nativeValueSetter.call(input, value);
        }} catch (e) {{
            input.value = value;
        }}
        
        const inputEvent = new InputEvent('input', {{
            bubbles: true,
            cancelable: true,
            inputType: 'insertText',
            data: value
        }});
        input.dispatchEvent(inputEvent);
        
        const changeEvent = new Event('change', {{ bubbles: true, cancelable: true }});
        input.dispatchEvent(changeEvent);
        
        const keyboardEvents = ['keydown', 'keypress', 'keyup'];
        keyboardEvents.forEach(eventName => {{
            const keyEvent = new KeyboardEvent(eventName, {{
                bubbles: true,
                cancelable: true,
                key: value.slice(-1) || 'a',
                code: 'KeyA'
            }});
            input.dispatchEvent(keyEvent);
        }});
        
        if (input.value !== value) {{
            input.value = value;
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}
        
        input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
        
        try {{
            const reactKey = Object.keys(input).find(key => 
                key.startsWith('__reactFiber$') || 
                key.startsWith('__reactInternalInstance$') ||
                key.startsWith('__reactProps$')
            );
            if (reactKey && input[reactKey]) {{
                const props = input[reactKey].memoizedProps || input[reactKey].pendingProps || {{}};
                if (props.onChange) {{
                    props.onChange({{ target: input, currentTarget: input }});
                }}
            }}
        }} catch (e) {{}}
    }}
    
    // ═══════════════════════════════════════════════════════════════
    // 主执行函数 - 调用共享执行器（来自 TencentDocsFiller）
    // ═══════════════════════════════════════════════════════════════
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
        
        const allInputs = getAllInputs();
        
        // 使用共享执行器
        const executor = createSharedExecutor({{
            fillData: fillData,
            allInputs: allInputs,
            getIdentifiers: getInputIdentifiers,
            fillInput: fillInput,
            onProgress: (msg) => console.log(msg)
        }});
        
        const result = await executor.execute();
        window.__autoFillResult__ = result;
    }}
    
    executeAutoFill();
    return 'WPS表单填写脚本已执行';
}})();
        """
        return js_code
    
    def generate_tencent_wj_fill_script(self, fill_data: list) -> str:
        """生成腾讯问卷(wj.qq.com)专用的填充脚本 - 使用共享匹配算法"""
        import json
        from core.tencent_docs_filler import TencentDocsFiller
        
        fill_data_json = json.dumps(fill_data, ensure_ascii=False)
        
        # 获取共享的匹配算法和执行逻辑
        shared_algorithm = TencentDocsFiller.get_shared_match_algorithm()
        shared_executor = TencentDocsFiller.get_shared_execution_logic()
        
        js_code = f"""
(function() {{
    console.log('🐧 开始填写腾讯问卷（使用共享算法）...');
    
    // 🔧 自动适配移动端视口
    (function adaptViewport() {{
        // 移除现有 viewport
        const existingViewport = document.querySelector('meta[name="viewport"]');
        if (existingViewport) {{
            existingViewport.remove();
        }}
        
        // 添加适配的 viewport
        const viewport = document.createElement('meta');
        viewport.name = 'viewport';
        viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';
        document.head.appendChild(viewport);
        
        // 注入移动端适配样式
        const style = document.createElement('style');
        style.textContent = `
            body {{
                width: 100% !important;
                min-width: 100% !important;
                max-width: 100% !important;
                overflow-x: hidden !important;
            }}
            .form-wrapper, .question-form, .survey-wrapper {{
                width: 100% !important;
                max-width: 100% !important;
                padding: 10px !important;
                box-sizing: border-box !important;
            }}
            .question {{
                width: 100% !important;
                box-sizing: border-box !important;
            }}
            .inputs-input {{
                width: 100% !important;
                box-sizing: border-box !important;
            }}
        `;
        document.head.appendChild(style);
        console.log('📱 已适配移动端视口');
    }})();
    
    const fillData = {fill_data_json};
    
    // ═══════════════════════════════════════════════════════════════
    // 共享匹配算法（来自 TencentDocsFiller.get_shared_match_algorithm()）
    // ═══════════════════════════════════════════════════════════════
{shared_algorithm}
    
    // ═══════════════════════════════════════════════════════════════
    // 共享执行逻辑（来自 TencentDocsFiller.get_shared_execution_logic()）
    // ═══════════════════════════════════════════════════════════════
{shared_executor}
    
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
    
    // 【腾讯文档专用】按DOM顺序提取问题标题
    let _questionLabelsCache = null;
    function getQuestionLabels() {{
        if (_questionLabelsCache) return _questionLabelsCache;
        
        const pageText = document.body.innerText || '';
        const labels = [];
        
        // 匹配腾讯文档格式: "0 1 * 小红书账号" 或 "01 * 小红书账号" 或 "1 * 小红书账号"
        // 也兼容: "01. * 标签" 或 "1. 标签" 格式
        const patterns = [
            // 格式1: "0 1 * 标签" (数字之间有空格)
            /(\\d)\\s+(\\d)\\s*\\*?\\s*([^\\d\\n*]{{1,30}})(?=\\d\\s+\\d|$|\\n)/g,
            // 格式2: "01 * 标签" (两位数字连在一起)
            /(\\d{{1,2}})\\s*\\*\\s*([^\\d\\n*]{{1,30}})(?=\\d{{1,2}}\\s*\\*|$|\\n)/g,
            // 格式3: "01. * 标签" (带点号)
            /(\\d{{1,2}})\\.\\s*\\*?\\s*([^\\d\\n]{{1,30}})(?=\\d{{1,2}}\\.|$|\\n)/g
        ];
        
        // 尝试所有格式
        for (const regex of patterns) {{
            let match;
            while ((match = regex.exec(pageText)) !== null) {{
                let num, label;
                if (match.length === 4) {{
                    // 格式1: 两个数字分开
                    num = parseInt(match[1] + match[2]);
                    label = match[3].trim();
                }} else {{
                    // 格式2/3: 数字连在一起
                    num = parseInt(match[1]);
                    label = match[2].trim();
                }}
                
                // 清理标签
                label = label.replace(/[\\s*]+$/, '').trim();
                label = label.split(/[\\n此题]/)[0].trim(); // 去掉"此题涉及隐私"等后缀
                
                if (label && label.length > 0 && label.length <= 30) {{
                    // 避免重复添加
                    if (!labels.some(l => l.num === num)) {{
                        labels.push({{ num: num, label: label }});
                    }}
                }}
            }}
            
            // 如果找到了问题，就不再尝试其他格式
            if (labels.length > 0) break;
        }}
        
        // 按序号排序
        labels.sort((a, b) => a.num - b.num);
        _questionLabelsCache = labels;
        console.log('📋 提取到的问题标题:', labels.map(l => `${{l.num}}.${{l.label}}`).join(', '));
        return labels;
    }}
    
    // 获取所有问题字段
    function getAllFields() {{
        const fields = [];
        const questionLabels = getQuestionLabels();
        
        // 方式1: 查找腾讯问卷标准结构 .question
        document.querySelectorAll('.question').forEach((question, index) => {{
            const titleEl = question.querySelector('.question-title .text .pe-line');
            const title = titleEl ? titleEl.innerText.trim() : '';
            const input = question.querySelector('.inputs-input, input, textarea');
            
            if (title && input) {{
                fields.push({{ index: index, title: title, input: input, question: question }});
                console.log(`  字段 ${{index + 1}}: "${{title}}"`);
            }}
        }});
        
        // 方式2: 如果没找到标准结构，使用通用查找
        if (fields.length === 0) {{
            const allInputs = [];
            document.querySelectorAll('input[type="text"], input:not([type]), textarea').forEach(input => {{
                const style = window.getComputedStyle(input);
                if (style.display !== 'none' && style.visibility !== 'hidden' && input.offsetParent !== null) {{
                    if (!input.disabled && !input.readOnly) {{
                        allInputs.push(input);
                    }}
                }}
            }});
            
            // 按索引与问题标题配对
            allInputs.forEach((input, index) => {{
                let title = '';
                if (index < questionLabels.length) {{
                    title = questionLabels[index].label;
                }}
                fields.push({{ index: index, title: title, input: input, question: null }});
                console.log(`  字段 ${{index + 1}}: "${{title}}"`);
            }});
        }}
        
        return fields;
    }}
    
    // 填充输入框 - React/Vue 深度兼容（修复提交问题）
    function fillInput(input, value) {{
        try {{
            // 1. 聚焦输入框
            input.focus();
            input.click();
            
            // 2. 清空现有内容
            input.value = '';
            
            // 3. 使用原生 setter 设置值（React 关键）
            const isTextArea = input.tagName === 'TEXTAREA';
            const proto = isTextArea ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
            
            try {{
                const nativeValueSetter = Object.getOwnPropertyDescriptor(proto, 'value').set;
                nativeValueSetter.call(input, value);
            }} catch (e) {{
                input.value = value;
            }}
            
            // 4. 触发 React 合成事件 - 使用 InputEvent（关键！）
            const inputEvent = new InputEvent('input', {{
                bubbles: true,
                cancelable: true,
                inputType: 'insertText',
                data: value
            }});
            input.dispatchEvent(inputEvent);
            
            // 5. 触发 change 事件
            const changeEvent = new Event('change', {{ bubbles: true, cancelable: true }});
            input.dispatchEvent(changeEvent);
            
            // 6. 模拟键盘事件序列
            ['keydown', 'keypress', 'keyup'].forEach(eventName => {{
                const keyEvent = new KeyboardEvent(eventName, {{
                    bubbles: true,
                    cancelable: true,
                    key: value.slice(-1) || 'a',
                    code: 'KeyA'
                }});
                input.dispatchEvent(keyEvent);
            }});
            
            // 7. 再次确认值已设置
            if (input.value !== value) {{
                input.value = value;
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
            
            // 8. 触发 blur 完成编辑
            input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
            
            // 9. 尝试触发 React/Vue 内部状态更新
            try {{
                const reactKey = Object.keys(input).find(key => 
                    key.startsWith('__reactFiber$') || 
                    key.startsWith('__reactInternalInstance$') ||
                    key.startsWith('__reactProps$')
                );
                if (reactKey && input[reactKey]) {{
                    const props = input[reactKey].memoizedProps || input[reactKey].pendingProps || {{}};
                    if (props.onChange) {{
                        props.onChange({{ target: input, currentTarget: input }});
                    }}
                }}
            }} catch (e) {{}}
            
            // 10. Vue 兼容 - 触发 v-model 更新
            try {{
                if (input.__vue__) {{
                    input.__vue__.$emit('input', value);
                }}
            }} catch (e) {{}}
            
            console.log(`    ✅ 已填入: "${{value}}"`);
            return true;
        }} catch (e) {{
            console.error(`    ❌ 填充失败: ${{e.message}}`);
            return false;
        }}
    }}
    
    // ═══════════════════════════════════════════════════════════════
    // 主执行函数 - 调用共享执行器（来自 TencentDocsFiller）
    // ═══════════════════════════════════════════════════════════════
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
        
        // 使用共享执行器
        const executor = createSharedExecutor({{
            fillData: fillData,
            allInputs: allFields,  // 传入字段对象数组
            getIdentifiers: (field, index) => {{
                // 返回字段标题作为标识符
                return field.title ? [field.title] : ['(无标题)'];
            }},
            fillInput: (field, value) => {{
                // 调用腾讯问卷专用的填充函数
                return fillInput(field.input, value);
            }},
            onProgress: (msg) => console.log(msg)
        }});
        
        const result = await executor.execute();
        window.__autoFillResult__ = result;
        
        console.log(`\\n✅ 腾讯问卷填写完成: ${{result.fillCount}}/${{result.totalCount}} 个字段`);
    }}
    
    executeAutoFill();
    return '腾讯问卷填写脚本已执行';
}})();
        """
        return js_code
    
    def execute_fanqier_fill(self, web_view: QWebEngineView, fill_data: list, card):
        """执行番茄表单填充"""
        print(f"  ⏰ 延迟后执行填充脚本...")
        self._fanqier_debug_printed = False  # 重置调试打印标志
        
        # 生成填充脚本
        js_code = self.generate_fanqier_fill_script(fill_data)
        print(f"  📝 生成番茄表单脚本，字段数量: {len(fill_data)}")
        print(f"  📄 脚本总长度: {len(js_code)} 字符")
        print(f"  🚀 执行番茄表单填充脚本...")
        
        def script_callback(result):
            print(f"  ✅ 脚本注入完成: {result}")
            # 等待500ms后开始轮询状态
            QTimer.singleShot(500, lambda: self.check_fill_result(web_view, 0))
        
        web_view.page().runJavaScript(js_code, script_callback)
    
    def check_fill_result(self, web_view: QWebEngineView, retry_count=0):
        """检查填充结果（带重试）"""
        result_js = """
        (function() {
            const status = window.__fanqierFillStatus__ || {status: 'unknown', message: '未知'};
            const result = window.__autoFillResult__ || null;
            const debug = window.__fanqierDebugInfo__ || null;
            
            return {
                status: status.status,
                message: status.message,
                hasResult: !!result,
                fillCount: result ? result.fillCount : 0,
                totalCount: result ? result.totalCount : 0,
                debugInfo: debug
            };
        })();
        """
        
        def result_callback(result):
            if not result:
                print(f"  ⚠️ 无法获取状态")
                return
            
            status = result.get('status', 'unknown')
            message = result.get('message', '')
            print(f"  📊 执行状态 [{retry_count+1}]: {status} - {message}")
            
            # 只要有调试信息，且尚未打印过（或填充失败），就打印
            debug = result.get('debugInfo')
            has_printed_debug = getattr(self, '_fanqier_debug_printed', False)
            
            if debug and (not has_printed_debug or (result.get('hasResult') and result.get('fillCount', 0) == 0)):
                self._fanqier_debug_printed = True
                print(f"  🔍 调试信息 (Input={debug.get('inputCount', 0)}):")
                print(f"    前3个输入框的识别情况:")
                for inp in debug.get('inputs', [])[:3]:
                    identifiers = inp.get('identifiers', [])
                    id_texts = [item.get('text') for item in identifiers]
                    print(f"      #{inp.get('index')}: 标识符={id_texts}")
                    if not id_texts and inp.get('structure'):
                        print(f"        ⚠️ 结构快照: {inp.get('structure')}")

            # 如果还在执行中，继续轮询
            if status in ['starting', 'waiting_dom', 'dom_loaded', 'dom_ready', 'waiting_inputs', 'scanning', 'found_inputs'] and retry_count < 20:
                QTimer.singleShot(500, lambda: self.check_fill_result(web_view, retry_count + 1))
            elif result.get('hasResult'):
                fillCount = result.get('fillCount', 0)
                totalCount = result.get('totalCount', 0)
                print(f"  ✅ 填充完成: {fillCount}/{totalCount} 个字段")
                if fillCount == 0 and totalCount > 0:
                    print(f"  ⚠️ 警告: 0个字段被填充，可能是匹配阈值太高或字段名称不匹配")
            elif status == 'no_inputs':
                print(f"  ❌ 未找到输入框")
            elif status == 'error':
                print(f"  ❌ 执行出错: {message}")
            else:
                print(f"  ⚠️ 状态异常，重试次数已达上限")
        
        web_view.page().runJavaScript(result_js, result_callback)
    
    def get_fill_result(self, web_view: QWebEngineView, card, form_type: str):
        """获取填写结果"""
        # ⚡️ 安全检查：窗口或 WebView 是否已销毁
        if not self._is_valid():
            print("🛑 [get_fill_result] 窗口已关闭，跳过结果获取")
            return
        
        try:
            from PyQt6 import sip
        except ImportError:
            import sip
        
        if sip.isdeleted(web_view):
            print("🛑 [get_fill_result] WebView 已销毁，跳过结果获取")
            return
        
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
            # ⚡️ 安全检查：窗口或 WebView 是否已销毁
            if not self._is_valid():
                return
            if sip.isdeleted(web_view):
                return
            
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
                
                # 填写成功后尝试增加使用次数（带权限检查）
                record_success = fill_count > 0
                if fill_count > 0 and self.current_user:
                    from core.auth import try_increment_usage_count
                    can_increment, msg = try_increment_usage_count(self.current_user)
                    if not can_increment:
                        # 额度已用尽，不记录为成功
                        print(f"⚠️ [额度检查] 无法增加使用次数: {msg}")
                        record_success = False
                        fill_count = 0  # 标记为未成功填充
                        # 只弹出一次提示（使用实例标记防止重复弹窗）
                        if not getattr(self, '_quota_exceeded_shown', False):
                            self._quota_exceeded_shown = True
                            from PyQt6.QtWidgets import QMessageBox
                            QMessageBox.warning(self, "使用受限", f"{msg}\n\n请联系平台客服续费后继续使用。")
                
                # 保存记录
                self.db_manager.create_fill_record(
                    card.id,
                    link_data.id,
                    fill_count,
                    total_count,
                    success=record_success
                )
                
                web_view.setProperty("status", "filled")
                print(f"✅ {card.name}: 填写 {fill_count}/{total_count} 个字段")
                
                # 检查是否所有填写完成
                self.check_all_fills_completed()
        
        web_view.page().runJavaScript(get_result_script, handle_result)
    
    def check_all_fills_completed(self):
        """检查是否所有填写完成"""
        # ⚡️ 安全检查
        if not self._is_valid():
            return
        
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
    def __init__(self, key="", value="", parent_window=None, fixed_template_id=None, is_special=True):
        super().__init__()
        self.parent_window = parent_window
        self.fixed_template_id = fixed_template_id  # 固定模板ID
        self.is_special = is_special
        self.init_ui(key, value)
        
    def init_ui(self, key, value):
        # 主容器 - 改回单行布局，符合设计图
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10) # 增加间距
        self.setLayout(layout)
        
        # 字段名输入容器（包含输入框和内嵌加号按钮）
        key_input_container = QWidget()
        key_input_container.setFixedHeight(36)
        key_input_container.setMinimumWidth(100)
        key_input_layout = QHBoxLayout(key_input_container)
        key_input_layout.setContentsMargins(0, 0, 0, 0)
        key_input_layout.setSpacing(0)
        
        # 字段名输入框
        self.key_input = QLineEdit(key)
        self.key_input.setPlaceholderText("昵称")
        self.key_input.setFixedHeight(36)
        self.key_input.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.key_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 0 32px 0 10px;
                font-size: 13px;
                background: white;
                color: #333;
            }}
            QLineEdit:focus {{
                border: 1px solid {COLORS['primary']};
                background: #FDFDFD;
            }}
        """)
        key_input_layout.addWidget(self.key_input)
        
        # 加号按钮（内嵌在输入框右侧）
        plus_btn = QPushButton()
        plus_btn.setIcon(Icons.plus_circle('primary'))
        plus_btn.setIconSize(QSize(16, 16))
        plus_btn.setFixedSize(24, 24)
        plus_btn.setToolTip("添加字段别名")
        plus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        plus_btn.setStyleSheet(f"""
            QPushButton {{
                border: none;
                background: transparent;
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background: #E8F4FD;
            }}
            QPushButton:pressed {{
                background: #D0E8F9;
            }}
        """)
        plus_btn.clicked.connect(self.append_key_segment)
        
        # 将加号按钮定位在输入框内部右侧
        plus_btn.setParent(key_input_container)
        plus_btn.raise_()
        
        # 监听容器大小变化，保持按钮位置
        def update_plus_btn_pos():
            plus_btn.move(key_input_container.width() - 28, (key_input_container.height() - 24) // 2)
        key_input_container.resizeEvent = lambda e: update_plus_btn_pos()
        
        layout.addWidget(key_input_container, 3)
        
        # 字段值输入框
        self.value_input = QLineEdit(value)
        self.value_input.setPlaceholderText("值")
        self.value_input.setFixedHeight(36)
        self.value_input.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        
        if self.fixed_template_id and not self.is_special:
            self.value_input.setEnabled(False)
            self.value_input.setStyleSheet(f"""
                QLineEdit {{
                    border: 1px solid #E0E0E0;
                    border-radius: 6px;
                    padding: 0 10px;
                    font-size: 13px;
                    background: #F5F5F5;
                    color: #999;
                }}
            """)
        else:
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
        layout.addWidget(self.value_input, 4)
        
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
        dialog = QDialog(self)
        dialog.setWindowTitle("新增字段别名")
        dialog.setFixedWidth(400)
        dialog.setStyleSheet("""
            QDialog { background: white; font-family: "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif; }
            QLabel { color: #333333; font-size: 13px; }
            QLineEdit {
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding: 8px;
                color: #333333;
                background-color: white;
                font-size: 14px;
            }
            QLineEdit:focus { border-color: #3B82F6; }
            QPushButton { font-family: "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif; }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        label = QLabel("请输入要追加的别名（将自动用顿号拼接）：")
        label.setWordWrap(True)
        layout.addWidget(label)
        
        input_field = QLineEdit()
        input_field.setPlaceholderText("输入别名")
        input_field.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        layout.addWidget(input_field)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        paste_btn = QPushButton("粘贴")
        paste_btn.setFixedHeight(36)
        paste_btn.setMinimumWidth(90)
        paste_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        paste_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #666;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                padding: 0 16px;
            }
            QPushButton:hover { background: #F5F5F5; border-color: #3B82F6; color: #3B82F6; }
        """)
        paste_btn.clicked.connect(lambda: input_field.insert(QApplication.clipboard().text()))
        
        save_btn = QPushButton("保存")
        save_btn.setFixedHeight(36)
        save_btn.setMinimumWidth(90)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background: #3B82F6;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 600;
                padding: 0 16px;
            }
            QPushButton:hover { background: #2563EB; }
        """)
        save_btn.clicked.connect(dialog.accept)
        
        btn_layout.addWidget(paste_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        
        input_field.setFocus()
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            text = input_field.text().strip()
            if text:
                current_val = self.key_input.text().strip()
                if current_val:
                    new_val = f"{current_val}、{text}"
                else:
                    new_val = text
                self.key_input.setText(new_val)
        
    def get_data(self):
        return self.key_input.text().strip(), self.value_input.text().strip(), self.fixed_template_id

