"""
管理员消息发送模块
用于管理员向用户主动发送系统消息
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QFrame, QLineEdit, QTextEdit, QCheckBox,
    QScrollArea, QMessageBox, QComboBox, QGraphicsDropShadowEffect,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QDateTime
from PyQt6.QtGui import QColor, QFont

from database.models import User, Notification
from gui.icons import Icons
from gui.styles import COLORS

class UserRowWidget(QFrame):
    """用户行组件 - 带复选框"""
    
    selection_changed = pyqtSignal(bool, object)  # selected, user_obj
    
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.is_selected = False
        self._setup_ui()
        
    def _setup_ui(self):
        self.setFixedHeight(60)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-radius: 10px;
                border: 1px solid transparent;
            }}
            QFrame:hover {{
                background-color: {COLORS['surface_hover']};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(15)
        
        # 1. 复选框
        self.checkbox = QCheckBox()
        self.checkbox.setFixedSize(20, 20)
        self.checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.checkbox.stateChanged.connect(self._on_check_changed)
        layout.addWidget(self.checkbox)
        
        # 2. 头像
        avatar_lbl = QLabel(self.user.username[0].upper() if self.user.username else "?")
        avatar_lbl.setFixedSize(36, 36)
        avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_lbl.setStyleSheet(f"""
            background-color: {COLORS['primary']}20;
            color: {COLORS['primary']};
            border-radius: 18px;
            font-weight: bold;
            font-size: 16px;
        """)
        layout.addWidget(avatar_lbl)
        
        # 3. 用户信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        name_lbl = QLabel(self.user.username)
        name_lbl.setStyleSheet(f"font-weight: 600; color: {COLORS['text_primary']}; font-size: 14px;")
        
        role_text = "管理员" if self.user.is_admin() else "普通用户"
        role_lbl = QLabel(role_text)
        role_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        
        info_layout.addWidget(name_lbl)
        info_layout.addWidget(role_lbl)
        layout.addLayout(info_layout)
        
        layout.addStretch()
        
        # 4. 状态
        status_text = "激活" if self.user.is_active else "禁用"
        status_color = COLORS['success'] if self.user.is_active else COLORS['danger']
        status_lbl = QLabel(status_text)
        status_lbl.setStyleSheet(f"""
            color: {status_color};
            background-color: {status_color}15;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        """)
        layout.addWidget(status_lbl)

    def _on_check_changed(self, state):
        self.is_selected = (state == 2)  # 2 is Checked
        self.update_style()
        self.selection_changed.emit(self.is_selected, self.user)
        
    def set_checked(self, checked):
        self.checkbox.setChecked(checked)
        
    def update_style(self):
        if self.is_selected:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['primary']}10;
                    border: 1px solid {COLORS['primary']}40;
                    border-radius: 10px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['surface']};
                    border-radius: 10px;
                    border: 1px solid transparent;
                }}
                QFrame:hover {{
                    background-color: {COLORS['surface_hover']};
                }}
            """)

class MessageHistoryWidget(QWidget):
    """历史消息记录组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 顶部工具栏
        toolbar = QHBoxLayout()
        title = QLabel("已发送记录")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {COLORS['text_primary']};")
        toolbar.addWidget(title)
        
        toolbar.addStretch()
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.setIcon(Icons.refresh(COLORS['primary']))
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: white;
                color: {COLORS['primary']};
                border: 1px solid {COLORS['primary']};
                border-radius: 6px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background: {COLORS['primary']}10;
            }}
        """)
        refresh_btn.clicked.connect(self.load_history)
        toolbar.addWidget(refresh_btn)
        
        layout.addLayout(toolbar)
        
        # 表格容器
        table_frame = QFrame()
        table_frame.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 16px;
                border: none;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 15))
        shadow.setOffset(0, 5)
        table_frame.setGraphicsEffect(shadow)
        
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(0, 0, 0, 0)
        
        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["发送时间", "类型", "标题", "内容摘要", "接收人数"])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background: transparent;
                border: none;
                gridline-color: {COLORS['border_light']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['background']};
                border: none;
                border-bottom: 2px solid {COLORS['border_light']};
                padding: 12px;
                font-weight: 600;
                color: {COLORS['text_secondary']};
            }}
            QTableWidget::item {{
                padding: 12px;
                border-bottom: 1px solid {COLORS['border_light']};
            }}
        """)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # 时间
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # 类型
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # 标题
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # 内容
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents) # 人数
        
        table_layout.addWidget(self.table)
        layout.addWidget(table_frame)
        
        self.load_history()
        
    def load_history(self):
        """加载并聚合历史记录"""
        self.table.setRowCount(0)
        
        try:
            # 1. 获取最近的系统通知
            notifications = Notification.objects(
                type__in=['system', 'other']
            ).order_by('-created_at').limit(1000)
            
            # 2. 内存聚合
            # Key: (title, content, time_minute_str)
            grouped = {}
            
            for note in notifications:
                time_str = note.created_at.strftime("%Y-%m-%d %H:%M")
                key = (note.title, note.content, time_str)
                
                if key not in grouped:
                    grouped[key] = {
                        'count': 0,
                        'record': note,
                        'time': note.created_at
                    }
                grouped[key]['count'] += 1
                
            # 3. 排序 (按时间倒序)
            sorted_groups = sorted(
                grouped.values(), 
                key=lambda x: x['time'], 
                reverse=True
            )
            
            # 4. 显示
            for item in sorted_groups:
                note = item['record']
                count = item['count']
                
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # 时间
                time_item = QTableWidgetItem(note.created_at.strftime("%Y-%m-%d %H:%M"))
                self.table.setItem(row, 0, time_item)
                
                # 类型
                type_map = {'system': '系统通知', 'other': '其他消息'}
                type_text = type_map.get(note.type, note.type)
                type_item = QTableWidgetItem(type_text)
                self.table.setItem(row, 1, type_item)
                
                # 标题
                title_item = QTableWidgetItem(note.title)
                title_item.setFont(QFont("System", 13, QFont.Weight.Bold))
                self.table.setItem(row, 2, title_item)
                
                # 内容 (截断)
                content_text = note.content
                if len(content_text) > 50:
                    content_text = content_text[:50] + "..."
                content_item = QTableWidgetItem(content_text)
                content_item.setToolTip(note.content)
                self.table.setItem(row, 3, content_item)
                
                # 人数
                count_item = QTableWidgetItem(f"{count} 人")
                count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                count_item.setForeground(QColor(COLORS['primary']))
                self.table.setItem(row, 4, count_item)
                
        except Exception as e:
            print(f"Error loading history: {e}")

class AdminMessageManager(QWidget):
    """管理员消息管理主界面 (包含发送和历史)"""
    
    def __init__(self, parent=None, current_admin=None):
        super().__init__(parent)
        self.current_admin = current_admin
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建 Tab
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {COLORS['text_secondary']};
                padding: 12px 24px;
                font-size: 15px;
                font-weight: 600;
                border-bottom: 3px solid transparent;
            }}
            QTabBar::tab:selected {{
                color: {COLORS['primary']};
                border-bottom: 3px solid {COLORS['primary']};
            }}
            QTabBar::tab:hover {{
                color: {COLORS['text_primary']};
                background: rgba(0,0,0,0.02);
            }}
        """)
        
        # Tab 1: 发送消息
        self.send_tab = MessageSendWidget(current_admin=self.current_admin)
        self.tabs.addTab(self.send_tab, "发送新消息")
        
        # Tab 2: 历史记录
        self.history_tab = MessageHistoryWidget()
        self.tabs.addTab(self.history_tab, "发送记录")
        
        # 关联刷新：切换到历史记录时自动刷新
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        layout.addWidget(self.tabs)
        
    def on_tab_changed(self, index):
        if index == 1: # 历史记录页
            self.history_tab.load_history()

class MessageSendWidget(QWidget):
    """发送消息界面 (原 AdminMessageManager 内容)"""
    
    def __init__(self, parent=None, current_admin=None):
        super().__init__(parent)
        self.current_admin = current_admin
        self.selected_users = set() # Store user IDs
        self.user_widgets = []
        self.init_ui()
        
    def init_ui(self):
        # 主背景
        self.setStyleSheet(f"background-color: {COLORS['background']};")
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(25)
        
        # 左侧：用户选择列表 (40%)
        left_panel = self._create_user_list_panel()
        main_layout.addWidget(left_panel, 4)
        
        # 右侧：消息编辑发送 (60%)
        right_panel = self._create_message_panel()
        main_layout.addWidget(right_panel, 6)
        
        # 加载用户数据
        self.load_users()
        
    def _create_user_list_panel(self):
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 16px;
                border: none;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 15))
        shadow.setOffset(0, 5)
        panel.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题栏
        header = QHBoxLayout()
        title = QLabel("选择接收用户")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {COLORS['text_primary']};")
        header.addWidget(title)
        
        self.user_count_lbl = QLabel("0 位用户")
        self.user_count_lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        header.addWidget(self.user_count_lbl)
        header.addStretch()
        layout.addLayout(header)
        
        # 搜索框
        search_container = QFrame()
        search_container.setFixedHeight(40)
        search_container.setStyleSheet(f"""
            background-color: {COLORS['background']};
            border-radius: 8px;
        """)
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(10, 0, 10, 0)
        
        search_icon = QLabel()
        search_icon.setPixmap(Icons.search(COLORS['text_secondary']).pixmap(16, 16))
        search_layout.addWidget(search_icon)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索用户名...")
        self.search_input.setStyleSheet("border: none; background: transparent;")
        self.search_input.textChanged.connect(self.filter_users)
        search_layout.addWidget(self.search_input)
        
        layout.addWidget(search_container)
        
        # 全选控制
        action_layout = QHBoxLayout()
        self.select_all_cb = QCheckBox("全选")
        self.select_all_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_all_cb.stateChanged.connect(self.toggle_select_all)
        action_layout.addWidget(self.select_all_cb)
        action_layout.addStretch()
        layout.addLayout(action_layout)
        
        # 用户列表区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        self.users_container = QWidget()
        self.users_layout = QVBoxLayout(self.users_container)
        self.users_layout.setContentsMargins(0, 0, 0, 0)
        self.users_layout.setSpacing(10)
        self.users_layout.addStretch()
        
        scroll.setWidget(self.users_container)
        layout.addWidget(scroll)
        
        return panel
        
    def _create_message_panel(self):
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 16px;
                border: none;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 15))
        shadow.setOffset(0, 5)
        panel.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 标题
        title = QLabel("发送新消息")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {COLORS['text_primary']};")
        layout.addWidget(title)
        
        # 接收者预览
        self.recipient_info = QLabel("未选择用户")
        self.recipient_info.setStyleSheet(f"""
            color: {COLORS['primary']}; 
            background-color: {COLORS['primary']}10; 
            padding: 10px; 
            border-radius: 8px;
            font-weight: 500;
        """)
        layout.addWidget(self.recipient_info)
        
        # 消息类型
        type_layout = QHBoxLayout()
        type_lbl = QLabel("消息类型")
        type_lbl.setStyleSheet(f"font-weight: 600; color: {COLORS['text_primary']};")
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["系统通知", "维护公告", "活动推广", "其他"])
        self.type_combo.setFixedWidth(200)
        self.type_combo.setFixedHeight(36)
        
        type_layout.addWidget(type_lbl)
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)
        
        # 消息标题
        title_lbl = QLabel("标题")
        title_lbl.setStyleSheet(f"font-weight: 600; color: {COLORS['text_primary']}; margin-top: 10px;")
        layout.addWidget(title_lbl)
        
        self.msg_title_input = QLineEdit()
        self.msg_title_input.setPlaceholderText("请输入消息标题...")
        self.msg_title_input.setFixedHeight(45)
        layout.addWidget(self.msg_title_input)
        
        # 消息内容
        content_lbl = QLabel("内容")
        content_lbl.setStyleSheet(f"font-weight: 600; color: {COLORS['text_primary']}; margin-top: 10px;")
        layout.addWidget(content_lbl)
        
        self.msg_content_input = QTextEdit()
        self.msg_content_input.setPlaceholderText("请输入消息详细内容...")
        self.msg_content_input.setStyleSheet("""
            QTextEdit {
                padding: 15px;
                line-height: 1.5;
            }
        """)
        layout.addWidget(self.msg_content_input)
        
        layout.addStretch()
        
        # 发送按钮
        self.send_btn = QPushButton("发送消息")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setIcon(Icons.broadcast('white'))
        self.send_btn.setFixedHeight(50)
        self.send_btn.clicked.connect(self.send_message)
        layout.addWidget(self.send_btn)
        
        return panel

    def load_users(self):
        """加载用户列表"""
        # 清除现有列表
        for widget in self.user_widgets:
            widget.deleteLater()
        self.user_widgets.clear()
        self.selected_users.clear()
        
        try:
            users = User.objects.all().order_by('-created_at')
            self.user_count_lbl.setText(f"{len(users)} 位用户")
            
            for user in users:
                row = UserRowWidget(user)
                row.selection_changed.connect(self.on_user_selection_changed)
                self.users_layout.insertWidget(self.users_layout.count() - 1, row)
                self.user_widgets.append(row)
                
        except Exception as e:
            print(f"Error loading users: {e}")
            
    def filter_users(self, text):
        """过滤用户列表"""
        text = text.lower()
        visible_count = 0
        
        for widget in self.user_widgets:
            username = widget.user.username.lower()
            if text in username:
                widget.show()
                visible_count += 1
            else:
                widget.hide()
                
        # 更新全选状态（如果正在搜索，全选应该只针对可见项吗？通常逻辑比较复杂，这里简化处理）
        # 这里暂时不改变全选框状态，保持简单
        
    def toggle_select_all(self, state):
        """全选/取消全选"""
        is_checked = (state == 2)
        
        # 阻塞信号以防止触发大量回调
        for widget in self.user_widgets:
            if not widget.isHidden(): # 只选择可见的
                widget.blockSignals(True)
                widget.set_checked(is_checked)
                widget.is_selected = is_checked
                widget.update_style()
                
                if is_checked:
                    self.selected_users.add(str(widget.user.id))
                else:
                    uid = str(widget.user.id)
                    if uid in self.selected_users:
                        self.selected_users.remove(uid)
                        
                widget.blockSignals(False)
                
        self.update_recipient_info()

    def on_user_selection_changed(self, is_selected, user):
        """处理单个用户选择变化"""
        uid = str(user.id)
        if is_selected:
            self.selected_users.add(uid)
        else:
            if uid in self.selected_users:
                self.selected_users.remove(uid)
                
        # 更新全选框状态（可选：检测是否所有可见的都选中了）
        self.update_recipient_info()
        
    def update_recipient_info(self):
        """更新接收者信息显示"""
        count = len(self.selected_users)
        if count == 0:
            self.recipient_info.setText("未选择用户")
            self.recipient_info.setStyleSheet(f"""
                color: {COLORS['text_secondary']}; 
                background-color: {COLORS['border_light']}; 
                padding: 10px; 
                border-radius: 8px;
            """)
            self.send_btn.setEnabled(False)
            self.send_btn.setText("发送消息")
        else:
            self.recipient_info.setText(f"已选择 {count} 位接收用户")
            self.recipient_info.setStyleSheet(f"""
                color: {COLORS['primary']}; 
                background-color: {COLORS['primary']}10; 
                padding: 10px; 
                border-radius: 8px;
                font-weight: 600;
            """)
            self.send_btn.setEnabled(True)
            self.send_btn.setText(f"向 {count} 位用户发送")

    def send_message(self):
        """发送消息"""
        title = self.msg_title_input.text().strip()
        content = self.msg_content_input.toPlainText().strip()
        msg_type_text = self.type_combo.currentText()
        
        # 映射类型值
        type_map = {
            "系统通知": "system",
            "维护公告": "system",
            "活动推广": "other",
            "其他": "other"
        }
        msg_type = type_map.get(msg_type_text, "system")
        
        if not self.selected_users:
            QMessageBox.warning(self, "提示", "请先选择接收用户")
            return
            
        if not title or not content:
            QMessageBox.warning(self, "提示", "请输入标题和内容")
            return
            
        reply = QMessageBox.question(
            self, "确认发送",
            f"确定要向 {len(self.selected_users)} 位用户发送此消息吗？\n\n标题：{title}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 批量创建通知
                success_count = 0
                for uid in self.selected_users:
                    # 找到用户对象（可以优化为批量查询，但这里简单处理）
                    try:
                        user = User.objects.get(id=uid)
                        Notification(
                            user=user,
                            type=msg_type,
                            title=title,
                            content=content,
                            is_read=False
                        ).save()
                        success_count += 1
                    except Exception as e:
                        print(f"Failed to send to user {uid}: {e}")
                        
                QMessageBox.information(self, "成功", f"消息已发送给 {success_count} 位用户")
                
                # 重置表单
                self.msg_title_input.clear()
                self.msg_content_input.clear()
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"发送失败：{str(e)}")
