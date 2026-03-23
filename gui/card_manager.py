"""
名片管理对话框 - 分类视图
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMessageBox, QInputDialog, QLineEdit, QWidget, QScrollArea,
    QGroupBox, QFormLayout, QFrame, QRadioButton, QComboBox, QListWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from .icons import safe_qta_icon as qta_icon
from database import DatabaseManager, Card, Category, CardEditRequest
from database.models import CardConfigItem


# 颜色主题
COLORS = {
    'primary': '#34C759',
    'danger': '#FF3B30',
    'warning': '#FF9500',
    'info': '#007AFF',
    'background': '#F5F5F7',
    'surface': '#FFFFFF',
    'border': '#E5E5EA',
    'text_primary': '#000000',
    'text_secondary': '#8E8E93',
}


class CardManagerDialog(QDialog):
    """名片管理对话框 - 分类视图"""
    
    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.current_user = current_user  # 当前登录用户
        self.current_category = None
        self.expanded_categories = None  # None 表示首次加载，会自动展开所有分类
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("名片管理")
        self.setGeometry(150, 150, 1200, 700)
        self.setStyleSheet(f"background-color: {COLORS['background']};")
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        self.setLayout(main_layout)
        
        # 顶部标题和按钮区域
        header_layout = QHBoxLayout()
        
        title_label = QLabel("名片管理")
        title_label.setStyleSheet("""
            font-size: 24px; 
            font-weight: bold; 
            color: #1D1D1F;
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # 新增按钮组
        btn_add_card = QPushButton(" 新增名片")
        btn_add_card.setIcon(qta_icon('fa5s.plus', color='white'))
        btn_add_card.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #28A745;
            }}
        """)
        btn_add_card.clicked.connect(self.add_card)
        header_layout.addWidget(btn_add_card)
        
        btn_add_category = QPushButton(" 新增分类")
        btn_add_category.setIcon(qta_icon('fa5s.folder-plus', color='white'))
        btn_add_category.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['info']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #0051D5;
            }}
        """)
        btn_add_category.clicked.connect(self.add_category)
        header_layout.addWidget(btn_add_category)
        
        btn_add_template = QPushButton(" 新增官方模版")
        btn_add_template.setIcon(qta_icon('fa5s.clipboard-list', color='white'))
        btn_add_template.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['warning']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #E68A00;
            }}
        """)
        btn_add_template.clicked.connect(self.add_template)
        header_layout.addWidget(btn_add_template)
        
        # 待审批按钮（如果有待审批请求）
        self.pending_btn = QPushButton()
        self.pending_btn.setIcon(qta_icon('fa5s.bell', color='white'))
        self.pending_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pending_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['danger']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #E62E25;
            }}
        """)
        self.pending_btn.clicked.connect(self.show_pending_requests)
        self.pending_btn.hide()  # 默认隐藏
        header_layout.addWidget(self.pending_btn)
        
        # 检查是否有待审批请求
        self.check_pending_requests()
        
        main_layout.addLayout(header_layout)
        
        # 名片列表区域（滚动）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
        """)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(10)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_widget.setLayout(self.content_layout)
        scroll.setWidget(self.content_widget)
        
        main_layout.addWidget(scroll)
        
        # 底部按钮
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        btn_close = QPushButton("关闭")
        btn_close.setFixedWidth(100)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['border']};
                color: {COLORS['text_primary']};
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #D0D0D5;
            }}
        """)
        btn_close.clicked.connect(self.accept)
        bottom_layout.addWidget(btn_close)
        
        main_layout.addLayout(bottom_layout)
        
        # 加载数据
        self.load_data()
    
    def showEvent(self, event):
        super().showEvent(event)
        
        # 强制设置全局 ToolTip 样式（防止被覆盖）
        self.setStyleSheet(self.styleSheet() + """
            QToolTip {
                color: #1D1D1F;
                background-color: #FFFFFF;
                border: 1px solid #E5E5EA;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
        """)

    def load_data(self):
        """加载数据 - 按分类分组显示"""
        # 清空现有内容
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # 获取当前用户的所有名片并按分类分组
        cards = self.db_manager.get_all_cards(user=self.current_user)
        
        # 按分类分组
        categories = {}
        for card in cards:
            category = card.category or '默认分类'
            if category not in categories:
                categories[category] = []
            categories[category].append(card)
        
        # 添加数据库中存在的分类（即使没有名片）
        if self.current_user:
            for category_obj in Category.objects(user=self.current_user).order_by('order', 'name'):
                if category_obj.name not in categories:
                    categories[category_obj.name] = []
        
        # 如果没有任何分类，显示提示
        if not categories:
            empty_label = QLabel("暂无分类和名片\n\n点击「新增分类」创建分类，或点击「新增名片」添加名片")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet(f"""
                color: {COLORS['text_secondary']};
                font-size: 16px;
                padding: 40px;
            """)
            self.content_layout.addWidget(empty_label)
            return
        
        # 首次加载时，展开所有分类
        if self.expanded_categories is None:
            self.expanded_categories = set(categories.keys())
        
        # 显示每个分类
        for category_name in sorted(categories.keys()):
            category_widget = self.create_category_widget(category_name, categories[category_name])
            self.content_layout.addWidget(category_widget)
        
        # 添加底部间距
        self.content_layout.addStretch()
    
    def create_category_widget(self, category_name: str, cards: list):
        """创建分类组件"""
        # 分类容器
        category_frame = QFrame()
        category_frame.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        
        category_layout = QVBoxLayout()
        category_layout.setSpacing(0)
        category_layout.setContentsMargins(0, 0, 0, 0)
        category_frame.setLayout(category_layout)
        
        # 分类头部（可点击展开/折叠）
        header_widget = QWidget()
        header_widget.setStyleSheet(f"""
            QWidget {{
                background: {COLORS['surface']};
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                padding: 15px;
            }}
            QWidget:hover {{
                background: #F8F9FA;
            }}
        """)
        header_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        header_widget.mousePressEvent = lambda e: self.toggle_category(category_name)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(15, 10, 15, 10)
        header_widget.setLayout(header_layout)
        
        # 展开/折叠图标
        is_expanded = category_name in self.expanded_categories
        arrow_btn = QPushButton()
        arrow_btn.setIcon(qta_icon('fa5s.chevron-down' if is_expanded else 'fa5s.chevron-right', color='#667eea'))
        arrow_btn.setFixedSize(24, 24)
        arrow_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
        """)
        header_layout.addWidget(arrow_btn)
        
        # 分类图标（如果有的话）
        category_obj = Category.objects(user=self.current_user, name=category_name).first()
        if category_obj and category_obj.icon:
            category_icon_btn = QPushButton()
            try:
                category_icon_btn.setIcon(qta_icon(category_obj.icon, color=category_obj.color or '#667eea'))
            except:
                # 如果图标名称无效，使用默认图标
                category_icon_btn.setIcon(qta_icon('fa5s.folder', color=category_obj.color or '#667eea'))
            category_icon_btn.setFixedSize(28, 28)
            category_icon_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                }
            """)
            header_layout.addWidget(category_icon_btn)
        
        # 分类名称
        category_label = QLabel(f"{category_name}")
        category_label.setStyleSheet("""
            font-size: 16px;
            font-weight: 600;
            color: #1D1D1F;
        """)
        header_layout.addWidget(category_label)
        
        # 卡片数量
        count_label = QLabel(f"({len(cards)})")
        count_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px;")
        header_layout.addWidget(count_label)
        
        header_layout.addStretch()
        
        # 操作按钮
        btn_rename = QPushButton()
        btn_rename.setIcon(qta_icon('fa5s.edit', color='white'))
        btn_rename.setToolTip("重命名分类")
        btn_rename.setFixedSize(32, 32)
        btn_rename.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['info']};
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: #0051D5;
            }}
        """)
        btn_rename.clicked.connect(lambda: self.rename_category(category_name))
        header_layout.addWidget(btn_rename)
        
        btn_delete_category = QPushButton()
        btn_delete_category.setIcon(qta_icon('fa5s.trash', color='white'))
        btn_delete_category.setToolTip("删除分类")
        btn_delete_category.setFixedSize(32, 32)
        btn_delete_category.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['danger']};
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: #CC0000;
            }}
        """)
        btn_delete_category.clicked.connect(lambda: self.delete_category(category_name))
        header_layout.addWidget(btn_delete_category)
        
        category_layout.addWidget(header_widget)
        
        # 名片列表（可展开/折叠）
        if is_expanded:
            cards_container = QWidget()
            cards_container.setStyleSheet(f"background: {COLORS['surface']}; padding: 10px;")
            cards_layout = QVBoxLayout()
            cards_layout.setSpacing(8)
            cards_layout.setContentsMargins(15, 5, 15, 15)
            cards_container.setLayout(cards_layout)
            
            if cards:
                # 有名片，显示名片列表
                for card in cards:
                    card_widget = self.create_card_widget(card)
                    cards_layout.addWidget(card_widget)
            else:
                # 空分类，显示提示
                empty_label = QLabel(f"该分类暂无名片\n\n点击「新增名片」并选择「{category_name}」分类")
                empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                empty_label.setStyleSheet(f"""
                    color: {COLORS['text_secondary']};
                    font-size: 13px;
                    padding: 30px;
                """)
                cards_layout.addWidget(empty_label)
            
            category_layout.addWidget(cards_container)
        
        return category_frame
    
    def create_card_widget(self, card: Card):
        """创建名片组件"""
        card_frame = QFrame()
        card_frame.setStyleSheet(f"""
            QFrame {{
                background: #F8F9FA;
                border-radius: 8px;
                border: 1px solid {COLORS['border']};
                padding: 8px;
            }}
            QFrame:hover {{
                background: #E9ECEF;
                border: 1px solid {COLORS['info']};
            }}
        """)
        
        card_layout = QHBoxLayout()
        card_layout.setContentsMargins(12, 8, 12, 8)
        card_frame.setLayout(card_layout)
        
        # 名片名称
        name_label = QLabel(card.name)
        name_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 600;
            color: #1D1D1F;
        """)
        card_layout.addWidget(name_label)
        
        # 配置项数量
        config_count_label = QLabel(f"{len(card.configs)} 项")
        config_count_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        card_layout.addWidget(config_count_label)
        
        card_layout.addStretch()
            
            # 操作按钮
        btn_view = QPushButton()
        btn_view.setIcon(qta_icon('fa5s.eye', color='white'))
        btn_view.setToolTip("查看")
        btn_view.setFixedSize(32, 32)
        btn_view.setStyleSheet("""
            QPushButton {
                background: #667eea;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #5568d3;
            }
        """)
        btn_view.clicked.connect(lambda: self.view_card(card))
        card_layout.addWidget(btn_view)
        
        btn_edit = QPushButton()
        btn_edit.setIcon(qta_icon('fa5s.edit', color='white'))
        btn_edit.setToolTip("编辑")
        btn_edit.setFixedSize(32, 32)
        btn_edit.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['info']};
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: #0051D5;
            }}
        """)
        btn_edit.clicked.connect(lambda: self.edit_card(card))
        card_layout.addWidget(btn_edit)
        
        btn_copy = QPushButton()
        btn_copy.setIcon(qta_icon('fa5s.copy', color='white'))
        btn_copy.setToolTip("复制")
        btn_copy.setFixedSize(32, 32)
        btn_copy.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['warning']};
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: #E68A00;
            }}
        """)
        btn_copy.clicked.connect(lambda: self.copy_card(card))
        card_layout.addWidget(btn_copy)
        
        btn_delete = QPushButton()
        btn_delete.setIcon(qta_icon('fa5s.trash', color='white'))
        btn_delete.setToolTip("删除")
        btn_delete.setFixedSize(32, 32)
        btn_delete.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['danger']};
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: #CC0000;
            }}
        """)
        btn_delete.clicked.connect(lambda: self.delete_card(card))
        card_layout.addWidget(btn_delete)
        
        return card_frame
    
    def toggle_category(self, category_name: str):
        """展开/折叠分类"""
        if category_name in self.expanded_categories:
            self.expanded_categories.remove(category_name)
        else:
            self.expanded_categories.add(category_name)
        self.load_data()
    
    def check_pending_requests(self):
        """检查是否有未读消息"""
        if not self.current_user:
            return
        
        count = DatabaseManager.get_unread_notifications_count(self.current_user)
        if count > 0:
            self.pending_btn.setText(f" 消息 ({count})")
            self.pending_btn.show()
        else:
            self.pending_btn.hide()
    
    def show_pending_requests(self):
        """显示消息中心"""
        from .card_edit_approval import MessageCenterDialog
        
        dialog = MessageCenterDialog(self.current_user, self)
        dialog.exec()
        
        # 刷新未读数量和名片列表
        self.check_pending_requests()
        self.load_data()
    
    def add_card(self):
        """新增名片"""
        dialog = CardEditDialog(self, current_user=self.current_user)
        if dialog.exec():
            self.load_data()
    
    def add_category(self):
        """新增分类"""
        if not self.current_user:
            QMessageBox.warning(self, "错误", "未找到当前用户信息")
            return
        
        category_name, ok = QInputDialog.getText(
            self,
            "新增分类",
            "请输入分类名称:",
            QLineEdit.EchoMode.Normal,
            ""
        )
        
        if ok and category_name.strip():
            # 检查分类是否已存在
            existing = Category.objects(user=self.current_user, name=category_name.strip()).first()
            if existing:
                QMessageBox.warning(self, "提示", f"分类 '{category_name}' 已存在")
                return
            
            try:
                # 创建新分类
                category = Category(
                    user=self.current_user,
                    name=category_name.strip(),
                    description=f"{category_name} 分类",
                    color='#667eea',
                    icon='fa5s.folder',
                    order=Category.objects(user=self.current_user).count()
                )
                category.save()
                
                # 将新分类添加到展开列表中（确保新分类自动展开显示）
                if self.expanded_categories is None:
                    self.expanded_categories = set()
                self.expanded_categories.add(category_name.strip())
                
                # 刷新界面显示新分类
                self.load_data()
                
                QMessageBox.information(
                    self,
                    "成功",
                    f"分类 '{category_name}' 已创建！✅\n\n您可以在新增/编辑名片时选择这个分类。"
                )
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建分类失败: {str(e)}")
    
    def add_template(self):
        """新增官方模版"""
        QMessageBox.information(
            self,
            "提示",
            "官方模版功能开发中...\n您可以先手动创建名片模版。"
        )
    
    def rename_category(self, old_name: str):
        """重命名分类"""
        new_name, ok = QInputDialog.getText(
            self,
            "重命名分类",
            "请输入新的分类名称:",
            QLineEdit.EchoMode.Normal,
            old_name
        )
        
        if ok and new_name.strip() and new_name != old_name:
            # 更新该分类下所有名片（仅当前用户的）
            cards = Card.objects(user=self.current_user, category=old_name)
            count = 0
            for card in cards:
                card.category = new_name
                card.save()
                count += 1
            
            QMessageBox.information(self, "成功", f"已将 {count} 个名片从 '{old_name}' 移动到 '{new_name}'")
            self.load_data()
    
    def delete_category(self, category_name: str):
        """删除分类"""
        # 检查该分类下是否有名片（仅当前用户的）
        cards_count = Card.objects(user=self.current_user, category=category_name).count()
        
        if cards_count > 0:
            # 自定义删除确认对话框
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("确认删除")
            msg_box.setText(f"分类 '{category_name}' 下有 {cards_count} 个名片")
            msg_box.setInformativeText("删除后这些名片将移动到「默认分类」。是否继续？")
            msg_box.setIcon(QMessageBox.Icon.Warning)
            
            # 自定义按钮
            btn_yes = msg_box.addButton("确定删除", QMessageBox.ButtonRole.YesRole)
            btn_yes.setIcon(qta_icon('fa5s.check', color='#FF3B30'))
            btn_no = msg_box.addButton("取消", QMessageBox.ButtonRole.NoRole)
            btn_no.setIcon(qta_icon('fa5s.times', color='#666'))
            
            msg_box.setDefaultButton(btn_no)
            
            # 设置样式
            msg_box.setStyleSheet(f"""
                QMessageBox {{
                    background: white;
                }}
                QPushButton {{
                    min-width: 90px;
                    padding: 8px 16px;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: 600;
                }}
            """)
            
            msg_box.exec()
            
            if msg_box.clickedButton() == btn_yes:
                # 将名片移动到默认分类（仅当前用户的）
                cards = Card.objects(user=self.current_user, category=category_name)
                for card in cards:
                    card.category = '默认分类'
                    card.save()
                
                # 删除数据库中的分类记录
                try:
                    category_obj = Category.objects(user=self.current_user, name=category_name).first()
                    if category_obj:
                        category_obj.delete()
                except:
                    pass
                
                QMessageBox.information(self, "成功", f"已将 {cards_count} 个名片移动到「默认分类」")
                self.load_data()
        else:
            # 空分类，直接删除
            try:
                category_obj = Category.objects(user=self.current_user, name=category_name).first()
                if category_obj:
                    category_obj.delete()
                QMessageBox.information(self, "提示", f"分类 '{category_name}' 已删除")
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")
    
    def view_card(self, card: Card):
        """查看名片"""
        dialog = CardViewDialog(card, self)
        dialog.exec()
    
    def edit_card(self, card: Card):
        """编辑名片"""
        # 检查权限
        if self.current_user and card.user.id != self.current_user.id:
            QMessageBox.warning(self, "权限不足", "您只能编辑自己的名片")
            return
        
        dialog = CardEditDialog(self, card, current_user=self.current_user)
        if dialog.exec():
            self.load_data()
    
    def copy_card(self, card: Card):
        """复制名片"""
        if not self.current_user:
            QMessageBox.warning(self, "错误", "未找到当前用户信息")
            return
        
        new_name = f"{card.name} - 副本"
        
        # 创建配置项列表
        configs = []
        for config in card.configs:
            configs.append({
                'key': config.key,
                'value': config.value
            })
        
        try:
            self.db_manager.create_card(
                name=new_name,
                configs=configs,
                user=self.current_user,
                description=card.description,
                category=card.category
            )
            QMessageBox.information(self, "成功", f"已复制名片: {new_name}")
            self.load_data()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"复制失败: {str(e)}")
    
    def delete_card(self, card: Card):
        """删除名片"""
        # 检查权限
        if self.current_user and card.user.id != self.current_user.id:
            QMessageBox.warning(self, "权限不足", "您只能删除自己的名片")
            return
        
        # 自定义删除确认对话框
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("确认删除")
        msg_box.setText(f"确定要删除名片 '{card.name}' 吗？")
        msg_box.setInformativeText("此操作不可撤销！")
        msg_box.setIcon(QMessageBox.Icon.Warning)
        
        # 自定义按钮
        btn_yes = msg_box.addButton("删除", QMessageBox.ButtonRole.YesRole)
        btn_yes.setIcon(qta_icon('fa5s.trash', color='#FF3B30'))
        btn_no = msg_box.addButton("取消", QMessageBox.ButtonRole.NoRole)
        btn_no.setIcon(qta_icon('fa5s.times', color='#666'))
        
        msg_box.setDefaultButton(btn_no)
        
        # 设置样式
        msg_box.setStyleSheet(f"""
            QMessageBox {{
                background: white;
            }}
            QPushButton {{
                min-width: 80px;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 600;
            }}
        """)
        
        msg_box.exec()
        
        if msg_box.clickedButton() == btn_yes:
            if self.db_manager.delete_card(card.id):
                QMessageBox.information(self, "成功", "名片已删除")
                self.load_data()
            else:
                QMessageBox.critical(self, "错误", "删除失败")


class CardViewDialog(QDialog):
    """名片查看对话框"""
    
    def __init__(self, card: Card, parent=None):
        super().__init__(parent)
        self.card = card
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f"查看名片 - {self.card.name}")
        self.setGeometry(200, 200, 700, 600)
        self.setStyleSheet(f"background-color: {COLORS['background']};")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        self.setLayout(layout)
        
        # 名片信息
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface']};
                border-radius: 12px;
                padding: 20px;
            }}
        """)
        info_layout = QVBoxLayout()
        info_frame.setLayout(info_layout)
        
        name_label = QLabel(f"📇 {self.card.name}")
        name_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #1D1D1F;")
        info_layout.addWidget(name_label)
        
        if self.card.category:
            category_label = QLabel(f"分类: {self.card.category}")
            category_label.setStyleSheet(f"color: {COLORS['info']}; font-size: 14px; padding: 5px 0;")
            info_layout.addWidget(category_label)
        
        if self.card.description:
            desc_label = QLabel(f"描述: {self.card.description}")
            desc_label.setStyleSheet(f"color: {COLORS['text_secondary']}; padding: 5px 0;")
            info_layout.addWidget(desc_label)
        
        layout.addWidget(info_frame)
        
        # 配置列表
        config_label = QLabel("配置项:")
        config_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #1D1D1F;")
        layout.addWidget(config_label)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(10)
        content_widget.setLayout(content_layout)
        
        for config in self.card.configs:
            config_frame = QFrame()
            config_frame.setStyleSheet(f"""
                QFrame {{
                    background: {COLORS['surface']};
                    border-radius: 8px;
                    padding: 15px;
                    border-left: 4px solid {COLORS['info']};
                }}
            """)
            
            config_layout = QHBoxLayout()
            config_frame.setLayout(config_layout)
            
            key_label = QLabel(f"{config.key}:")
            key_label.setStyleSheet("color: #667eea; font-size: 14px; font-weight: 600;")
            key_label.setMinimumWidth(150)
            config_layout.addWidget(key_label)
            
            value_label = QLabel(config.value)
            value_label.setStyleSheet("color: #333; font-size: 14px;")
            value_label.setWordWrap(True)
            config_layout.addWidget(value_label, 1)
            
            content_layout.addWidget(config_frame)
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # 关闭按钮
        btn_close = QPushButton("关闭")
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['border']};
                color: {COLORS['text_primary']};
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #D0D0D5;
            }}
        """)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)


class CardEditDialog(QDialog):
    """名片编辑对话框"""
    
    def __init__(self, parent=None, card: Card = None, current_user=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.card = card  # None 表示新增
        self.current_user = current_user
        self.config_widgets = []
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        title = "编辑名片" if self.card else "新增名片"
        self.setWindowTitle(title)
        self.setGeometry(200, 200, 750, 600)
        self.setStyleSheet(f"background-color: {COLORS['background']};")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        self.setLayout(layout)
        
        # 基本信息
        form_frame = QFrame()
        form_frame.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface']};
                border-radius: 10px;
                padding: 16px;
            }}
        """)
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setVerticalSpacing(10)
        form_layout.setHorizontalSpacing(12)
        form_frame.setLayout(form_layout)
        
        # 名称输入
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入名片名称")
        self.name_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 2px solid #E5E5EA;
                border-radius: 6px;
                font-size: 14px;
                background: white;
            }
            QLineEdit:focus {
                border: 2px solid #007AFF;
            }
        """)
        if self.card:
            self.name_input.setText(self.card.name)
        
        # 创建带图标的标签
        name_label_widget = QWidget()
        name_label_layout = QHBoxLayout()
        name_label_layout.setContentsMargins(0, 0, 0, 0)
        name_label_layout.setSpacing(6)
        name_label_widget.setLayout(name_label_layout)
        
        name_icon_label = QLabel()
        name_icon_label.setPixmap(qta_icon('fa5s.id-card', color='#667eea').pixmap(16, 16))
        name_label_layout.addWidget(name_icon_label)
        
        name_text_label = QLabel("名片名称:")
        name_text_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #333;")
        name_label_layout.addWidget(name_text_label)
        name_label_layout.addStretch()
        
        form_layout.addRow(name_label_widget, self.name_input)
        
        # 分类选择
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.setStyleSheet("""
            QComboBox {
                padding: 8px 12px;
                border: 2px solid #E5E5EA;
                border-radius: 6px;
                font-size: 14px;
                background: white;
            }
            QComboBox:focus {
                border: 2px solid #007AFF;
            }
        """)
        
        # 加载现有分类（从 Category 表加载）
        categories = set()
        if self.current_user:
            # 优先加载用户创建的分类
            for category in Category.objects(user=self.current_user).order_by('order', 'name'):
                categories.add(category.name)
            
            # 也加载名片中使用的分类（兼容旧数据）
            for card in Card.objects(user=self.current_user):
                if card.category:
                    categories.add(card.category)
        
        # 确保有默认分类
        if not categories:
            categories.add('默认分类')
        
        self.category_combo.blockSignals(True)
        self.category_combo.model().blockSignals(True)
        self.category_combo.addItems(sorted(categories))
        self.category_combo.model().blockSignals(False)
        self.category_combo.blockSignals(False)
        
        if self.card and self.card.category:
            self.category_combo.setCurrentText(self.card.category)
        else:
            self.category_combo.setCurrentText('默认分类')
        
        # 创建带图标的分类标签
        category_label_widget = QWidget()
        category_label_layout = QHBoxLayout()
        category_label_layout.setContentsMargins(0, 0, 0, 0)
        category_label_layout.setSpacing(6)
        category_label_widget.setLayout(category_label_layout)
        
        category_icon_label = QLabel()
        category_icon_label.setPixmap(qta_icon('fa5s.folder', color='#667eea').pixmap(16, 16))
        category_label_layout.addWidget(category_icon_label)
        
        category_text_label = QLabel("所属分类:")
        category_text_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #333;")
        category_label_layout.addWidget(category_text_label)
        category_label_layout.addStretch()
        
        form_layout.addRow(category_label_widget, self.category_combo)
        
        # 描述输入
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("输入描述（可选）")
        self.desc_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 2px solid #E5E5EA;
                border-radius: 6px;
                font-size: 14px;
                background: white;
            }
            QLineEdit:focus {
                border: 2px solid #007AFF;
            }
        """)
        if self.card:
            self.desc_input.setText(self.card.description or "")
        
        # 创建带图标的描述标签
        desc_label_widget = QWidget()
        desc_label_layout = QHBoxLayout()
        desc_label_layout.setContentsMargins(0, 0, 0, 0)
        desc_label_layout.setSpacing(6)
        desc_label_widget.setLayout(desc_label_layout)
        
        desc_icon_label = QLabel()
        desc_icon_label.setPixmap(qta_icon('fa5s.align-left', color='#667eea').pixmap(16, 16))
        desc_label_layout.addWidget(desc_icon_label)
        
        desc_text_label = QLabel("描述:")
        desc_text_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #333;")
        desc_label_layout.addWidget(desc_text_label)
        desc_label_layout.addStretch()
        
        form_layout.addRow(desc_label_widget, self.desc_input)
        
        layout.addWidget(form_frame)
        
        # 配置项标题和添加按钮
        config_header = QHBoxLayout()
        config_header.setSpacing(8)
        
        config_label = QLabel("配置项:")
        config_label.setStyleSheet("font-weight: 600; font-size: 14px; color: #333;")
        config_header.addWidget(config_label)
        config_header.addStretch()
        
        btn_add_config = QPushButton(" 添加配置项")
        btn_add_config.setIcon(qta_icon('fa5s.plus', color='white'))
        btn_add_config.clicked.connect(lambda: self.add_config_row())
        btn_add_config.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #28A745;
            }}
        """)
        config_header.addWidget(btn_add_config)
        
        layout.addLayout(config_header)
        
        # 配置项滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        
        self.config_container = QWidget()
        self.config_layout = QVBoxLayout()
        self.config_layout.setSpacing(10)
        self.config_container.setLayout(self.config_layout)
        scroll.setWidget(self.config_container)
        
        layout.addWidget(scroll, 1)
        
        # 加载现有配置
        if self.card:
            # 编辑模式：加载名片已有配置
            for config in self.card.configs:
                self.add_config_row(config.key, config.value, getattr(config, 'fixed_template_id', None))
        else:
            # 新增模式：加载所有启用的固定模板
            self.load_fixed_templates()
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        btn_save = QPushButton(" 保存")
        btn_save.setIcon(qta_icon('fa5s.save', color='white'))
        btn_save.clicked.connect(self.save)
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['info']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #0051D5;
            }}
        """)
        button_layout.addWidget(btn_save)
        
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['border']};
                color: {COLORS['text_primary']};
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #D0D0D5;
            }}
        """)
        button_layout.addWidget(btn_cancel)
        
        layout.addLayout(button_layout)
    
    def load_fixed_templates(self):
        """加载固定模板到配置项"""
        try:
            templates = self.db_manager.get_all_fixed_templates(is_active=True)
            if templates:
                for template in templates:
                    self.add_config_row(
                        template.field_name,
                        template.field_value,
                        str(template.id)  # 固定模板ID
                    )
            else:
                # 如果没有固定模板，添加一个空行
                self.add_config_row()
        except Exception as e:
            print(f"加载固定模板失败: {e}")
            # 加载失败时添加一个空行
            self.add_config_row()
    
    def add_config_row(self, key: str = "", value: str = "", fixed_template_id: str = None):
        """添加配置行
        
        Args:
            key: 字段名
            value: 字段值
            fixed_template_id: 固定模板ID，用户自己添加的为None
        """
        row_frame = QFrame()
        row_frame.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface']};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        # 存储固定模板ID到frame的属性中
        row_frame.fixed_template_id = fixed_template_id
        
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(5, 5, 5, 5)
        row_layout.setSpacing(8)
        row_frame.setLayout(row_layout)
        
        key_input = QLineEdit()
        key_input.setPlaceholderText("字段名（如：平台、账号、微信）")
        key_input.setText(key)
        key_input.setStyleSheet("""
            QLineEdit {
                padding: 7px 10px;
                border: 2px solid #E5E5EA;
                border-radius: 5px;
                font-size: 13px;
                background: white;
            }
            QLineEdit:focus {
                border: 2px solid #007AFF;
            }
        """)
        row_layout.addWidget(key_input, 1)
        
        value_input = QLineEdit()
        value_input.setPlaceholderText("填写值")
        value_input.setText(value)
        value_input.setStyleSheet("""
            QLineEdit {
                padding: 7px 10px;
                border: 2px solid #E5E5EA;
                border-radius: 5px;
                font-size: 13px;
                background: white;
            }
            QLineEdit:focus {
                border: 2px solid #007AFF;
            }
        """)
        row_layout.addWidget(value_input, 2)
        
        btn_remove = QPushButton()
        btn_remove.setIcon(qta_icon('fa5s.trash-alt', color='white'))
        btn_remove.setToolTip("删除")
        btn_remove.setFixedSize(34, 34)
        btn_remove.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['danger']};
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: #CC0000;
            }}
        """)
        btn_remove.clicked.connect(lambda: self.remove_config_row(row_frame))
        row_layout.addWidget(btn_remove)
        
        self.config_widgets.append((key_input, value_input, row_frame))
        self.config_layout.addWidget(row_frame)
    
    def remove_config_row(self, row_frame):
        """删除配置行"""
        self.config_widgets = [(k, v, w) for k, v, w in self.config_widgets if w != row_frame]
        row_frame.deleteLater()
    
    def save(self):
        """保存"""
        if not self.current_user:
            QMessageBox.warning(self, "错误", "未找到当前用户信息")
            return
        
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "警告", "请输入名片名称")
            return
        
        category = self.category_combo.currentText().strip() or '默认分类'
        
        # 收集配置项
        configs = []
        for key_input, value_input, row_frame in self.config_widgets:
            key = key_input.text().strip()
            value = value_input.text().strip()
            if key and value:  # 只保存非空的配置
                config = {'key': key, 'value': value}
                # 获取固定模板ID（如果有）
                fixed_template_id = getattr(row_frame, 'fixed_template_id', None)
                if fixed_template_id:
                    config['fixed_template_id'] = fixed_template_id
                configs.append(config)
        
        if not configs:
            QMessageBox.warning(self, "警告", "请至少添加一个配置项")
            return
        
        description = self.desc_input.text().strip()
        
        try:
            if self.card:
                # 更新
                self.db_manager.update_card(
                    self.card.id,
                    name=name,
                    configs=configs,
                    description=description,
                    category=category
                )
                QMessageBox.information(self, "成功", "名片已更新")
            else:
                # 新增
                self.db_manager.create_card(
                    name=name,
                    configs=configs,
                    user=self.current_user,
                    description=description,
                    category=category
                )
                QMessageBox.information(self, "成功", "名片已创建")
            
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
