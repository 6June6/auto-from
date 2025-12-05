import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QScrollArea, QFrame, 
                             QGridLayout, QComboBox, QLineEdit, QCheckBox,
                             QButtonGroup, QDateEdit, QApplication, QMessageBox,
                             QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QDate, QEvent
from PyQt6.QtGui import QColor, QFont, QIcon, QCursor

from database.db_manager import DatabaseManager
from .styles import COLORS, GLOBAL_STYLE
from .icons import Icons

class TagButton(QPushButton):
    """标签按钮 - 胶囊样式"""
    def __init__(self, text, parent=None, is_active=False):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setChecked(is_active)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(32)
        self.update_style()
        self.toggled.connect(self.update_style)
    
    def update_style(self):
        if self.isChecked():
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                              stop:0 {COLORS['primary']}, 
                                              stop:1 {COLORS['primary_light']});
                    color: white;
                    border: none;
                    border-radius: 16px;
                    padding: 0 18px;
                    font-weight: 600;
                    font-size: 13px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: #F3F4F6;
                    color: {COLORS['text_secondary']};
                    border: 1px solid transparent;
                    border-radius: 16px;
                    padding: 0 18px;
                    font-size: 13px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: #E5E7EB;
                    color: {COLORS['text_primary']};
                }}
            """)

class NoticeCardWidget(QFrame):
    """通告卡片组件 - 现代悬浮卡片"""
    
    join_clicked = pyqtSignal(object)  # 链接信号，传递整个 notice 对象
    
    def __init__(self, notice, parent=None):
        super().__init__(parent)
        self.notice = notice
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.init_ui()
        
    def init_ui(self):
        self.setFixedWidth(280) # 固定宽度使排版更整齐
        
        # 阴影效果
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(15)
        self.shadow.setColor(QColor(0, 0, 0, 20))
        self.shadow.setOffset(0, 4)
        self.setGraphicsEffect(self.shadow)
        
        # 卡片基础样式
        self.setStyleSheet(f"""
            NoticeCardWidget {{
                background-color: white;
                border-radius: 16px;
                border: 1px solid {COLORS['border_light']};
            }}
            NoticeCardWidget:hover {{
                border: 1px solid {COLORS['primary_light']};
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        self.setLayout(layout)
        
        # 1. 头部：徽标信息
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        # 平台标签
        platform_tag = QLabel(self.notice.platform)
        platform_tag.setStyleSheet(f"""
            background-color: #EEF2FF;
            color: {COLORS['primary']};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
            font-weight: 600;
        """)
        header_layout.addWidget(platform_tag)
        
        header_layout.addStretch()
        
        # 状态标签（如果是 active 就不显示，显示日期）
        date_label = QLabel(self.notice.publish_date.strftime('%m-%d') if self.notice.publish_date else "")
        date_label.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 12px;")
        header_layout.addWidget(date_label)
        
        layout.addLayout(header_layout)
        
        # 2. 标题与品牌
        title_label = QLabel(self.notice.title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 700;
            color: {COLORS['text_primary']};
            line-height: 1.4;
        """)
        layout.addWidget(title_label)
        
        brand_layout = QHBoxLayout()
        brand_icon = QLabel("🏢") # 临时图标
        brand_label = QLabel(self.notice.brand)
        brand_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; font-weight: 500;")
        brand_layout.addWidget(brand_icon)
        brand_layout.addWidget(brand_label)
        brand_layout.addStretch()
        layout.addLayout(brand_layout)
        
        # 3. 关键数据卡片
        data_container = QWidget()
        data_container.setStyleSheet(f"""
            background-color: #F9FAFB;
            border-radius: 8px;
        """)
        data_layout = QHBoxLayout(data_container)
        data_layout.setContentsMargins(12, 12, 12, 12)
        
        # 粉丝要求
        fans_layout = QVBoxLayout()
        fans_layout.setSpacing(2)
        fans_val = QLabel(f"{self.notice.min_fans}")
        fans_val.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 700; font-size: 14px;")
        fans_lbl = QLabel("粉丝要求")
        fans_lbl.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 11px;")
        fans_layout.addWidget(fans_val)
        fans_layout.addWidget(fans_lbl)
        
        # 报酬
        reward_layout = QVBoxLayout()
        reward_layout.setSpacing(2)
        reward_val = QLabel(self.notice.reward)
        reward_val.setStyleSheet(f"color: {COLORS['danger']}; font-weight: 700; font-size: 14px;")
        reward_lbl = QLabel("预估报酬")
        reward_lbl.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 11px;")
        reward_layout.addWidget(reward_val)
        reward_layout.addWidget(reward_lbl)
        
        data_layout.addLayout(fans_layout)
        # 分割线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet(f"background-color: {COLORS['border']}; max-width: 1px;")
        data_layout.addWidget(line)
        data_layout.addLayout(reward_layout)
        
        layout.addWidget(data_container)
        
        # 4. 产品信息摘要
        product_info = self.notice.product_info or ""
        if len(product_info) > 35:
            product_info = product_info[:33] + "..."
        info_label = QLabel(product_info)
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; margin-top: 4px;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        # 5. 底部按钮
        join_btn = QPushButton("加入链接")
        join_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        join_btn.setFixedHeight(36)
        join_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {COLORS['primary_light']};
            }}
            QPushButton:pressed {{
                background: {COLORS['primary_dark']};
            }}
        """)
        join_btn.clicked.connect(lambda: self.join_clicked.emit(self.notice))
        layout.addWidget(join_btn)

    def enterEvent(self, event):
        # 鼠标悬停效果
        self.shadow.setBlurRadius(25)
        self.shadow.setColor(QColor(0, 0, 0, 30))
        self.shadow.setOffset(0, 8)
        super().enterEvent(event)

    def leaveEvent(self, event):
        # 鼠标移开恢复
        self.shadow.setBlurRadius(15)
        self.shadow.setColor(QColor(0, 0, 0, 20))
        self.shadow.setOffset(0, 4)
        super().leaveEvent(event)


class NoticePlazaWindow(QMainWindow):
    """通告广场窗口"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.current_category = None
        self.current_platform = None
        self.page = 1
        self.page_size = 12  # 3x4 或 4x3
        
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        self.setWindowTitle("通告广场")
        self.setGeometry(100, 100, 1280, 850)
        self.setStyleSheet(GLOBAL_STYLE)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        central_widget.setLayout(main_layout)
        
        # 顶部：筛选区
        filter_container = QWidget()
        filter_container.setStyleSheet(f"background-color: white; border-bottom: 1px solid {COLORS['border']};")
        filter_layout = QVBoxLayout()
        filter_layout.setContentsMargins(24, 24, 24, 24)
        filter_layout.setSpacing(16)
        filter_container.setLayout(filter_layout)
        
        # 1. 类目筛选
        category_layout = QHBoxLayout()
        cat_label = QLabel("类目：")
        cat_label.setFixedWidth(60)
        cat_label.setStyleSheet(f"font-weight: 600; color: {COLORS['text_primary']};")
        category_layout.addWidget(cat_label)
        
        self.category_group = QButtonGroup(self)
        self.category_group.setExclusive(True)
        self.category_layout_container = QHBoxLayout()
        self.category_layout_container.setSpacing(10)
        
        # 包装在一个 ScrollArea 里防止类目太多
        cat_scroll = QScrollArea()
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setFixedHeight(50)
        cat_scroll.setFrameShape(QFrame.Shape.NoFrame)
        cat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cat_scroll.setStyleSheet("background: transparent;")
        
        cat_content = QWidget()
        cat_content.setLayout(self.category_layout_container)
        cat_scroll.setWidget(cat_content)
        
        category_layout.addWidget(cat_scroll)
        filter_layout.addLayout(category_layout)
        
        # 2. 平台筛选
        platform_layout = QHBoxLayout()
        plat_label = QLabel("平台：")
        plat_label.setFixedWidth(60)
        plat_label.setStyleSheet(f"font-weight: 600; color: {COLORS['text_primary']};")
        platform_layout.addWidget(plat_label)
        
        self.platform_group = QButtonGroup(self)
        self.platform_group.setExclusive(True)
        self.platform_layout_container = QHBoxLayout()
        self.platform_layout_container.setSpacing(10)
        
        platform_layout.addLayout(self.platform_layout_container)
        platform_layout.addStretch()
        filter_layout.addLayout(platform_layout)
        
        # 3. 高级筛选 (时间、粉丝、报酬)
        advanced_layout = QHBoxLayout()
        advanced_layout.setSpacing(20)
        
        # 样式化输入框
        input_style = f"""
            background: #F3F4F6;
            border: 1px solid transparent;
            border-radius: 8px;
            padding: 6px 10px;
            color: {COLORS['text_primary']};
        """
        
        # 有效时间
        time_label = QLabel("有效时间")
        time_label.setStyleSheet(f"font-weight: 600; color: {COLORS['text_secondary']};")
        advanced_layout.addWidget(time_label)
        
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setDate(QDate.currentDate())
        self.start_date.setFixedWidth(130)
        self.start_date.setStyleSheet(f"""
            QDateEdit {{ {input_style} }}
            QDateEdit::drop-down {{ border: none; width: 20px; }}
        """)
        
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setDate(QDate.currentDate().addDays(30))
        self.end_date.setFixedWidth(130)
        self.end_date.setStyleSheet(f"""
            QDateEdit {{ {input_style} }}
            QDateEdit::drop-down {{ border: none; width: 20px; }}
        """)
        
        advanced_layout.addWidget(self.start_date)
        advanced_layout.addWidget(QLabel("-"))
        advanced_layout.addWidget(self.end_date)
        
        # 粉丝要求
        fans_label = QLabel("粉丝要求")
        fans_label.setStyleSheet(f"font-weight: 600; color: {COLORS['text_secondary']}; margin-left: 10px;")
        advanced_layout.addWidget(fans_label)
        self.fans_combo = QComboBox()
        self.fans_combo.addItems(["不限", "1000+", "5000+", "1w+", "5w+", "10w+"])
        self.fans_combo.setFixedWidth(130)
        self.fans_combo.setStyleSheet(f"""
            QComboBox {{ {input_style} }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
        """)
        advanced_layout.addWidget(self.fans_combo)
        
        # 最高报酬
        reward_label = QLabel("最高报酬")
        reward_label.setStyleSheet(f"font-weight: 600; color: {COLORS['text_secondary']}; margin-left: 10px;")
        advanced_layout.addWidget(reward_label)
        self.reward_combo = QComboBox()
        self.reward_combo.addItems(["不限", "500以下", "500-1000", "1000-3000", "3000以上"])
        self.reward_combo.setFixedWidth(130)
        self.reward_combo.setStyleSheet(f"""
            QComboBox {{ {input_style} }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
        """)
        advanced_layout.addWidget(self.reward_combo)
        
        advanced_layout.addStretch()
        
        # 搜索按钮
        search_btn = QPushButton("筛选")
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.setFixedSize(100, 36)
        search_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['primary']};
                color: white;
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: {COLORS['primary_light']};
            }}
            QPushButton:pressed {{
                background: {COLORS['primary_dark']};
            }}
        """)
        search_btn.clicked.connect(self.refresh_notices)
        advanced_layout.addWidget(search_btn)
        
        filter_layout.addLayout(advanced_layout)
        
        main_layout.addWidget(filter_container)
        
        # 中间：内容区
        content_area = QScrollArea()
        content_area.setWidgetResizable(True)
        content_area.setFrameShape(QFrame.Shape.NoFrame)
        content_area.setStyleSheet(f"background-color: {COLORS['background']};")
        
        self.cards_container = QWidget()
        self.cards_grid = QGridLayout()
        self.cards_grid.setSpacing(20)
        self.cards_grid.setContentsMargins(24, 24, 24, 24)
        self.cards_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.cards_container.setLayout(self.cards_grid)
        
        content_area.setWidget(self.cards_container)
        main_layout.addWidget(content_area)
        
        # 底部：分页
        footer_container = QWidget()
        footer_container.setStyleSheet("background-color: white; border-top: 1px solid #E5E5EA;")
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(24, 16, 24, 16)
        
        # 分页按钮样式
        page_btn_style = f"""
            QPushButton {{
                background: white;
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                color: {COLORS['text_primary']};
                font-weight: 600;
            }}
            QPushButton:hover {{
                border-color: {COLORS['primary']};
                color: {COLORS['primary']};
            }}
            QPushButton:disabled {{
                background: #F3F4F6;
                border-color: transparent;
                color: {COLORS['text_tertiary']};
            }}
        """
        
        self.prev_btn = QPushButton("<")
        self.prev_btn.setFixedSize(40, 40)
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.setStyleSheet(page_btn_style)
        self.prev_btn.clicked.connect(self.prev_page)
        
        self.page_label = QLabel("1 / 1")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setFixedWidth(80)
        self.page_label.setStyleSheet(f"font-weight: 600; color: {COLORS['text_secondary']};")
        
        self.next_btn = QPushButton(">")
        self.next_btn.setFixedSize(40, 40)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setStyleSheet(page_btn_style)
        self.next_btn.clicked.connect(self.next_page)
        
        footer_layout.addStretch()
        footer_layout.addWidget(self.prev_btn)
        footer_layout.addWidget(self.page_label)
        footer_layout.addWidget(self.next_btn)
        footer_layout.addStretch()
        
        footer_container.setLayout(footer_layout)
        main_layout.addWidget(footer_container)
    
    def load_data(self):
        """加载初始化数据"""
        # 加载类目
        categories = self.db_manager.get_all_notice_categories()
        # 添加"全部"选项
        all_cat_btn = TagButton("全部", is_active=True)
        all_cat_btn.clicked.connect(lambda: self.on_category_changed(None))
        self.category_group.addButton(all_cat_btn)
        self.category_layout_container.addWidget(all_cat_btn)
        
        for cat in categories:
            btn = TagButton(cat.name)
            btn.clicked.connect(lambda checked, c=cat.name: self.on_category_changed(c))
            self.category_group.addButton(btn)
            self.category_layout_container.addWidget(btn)
        
        self.category_layout_container.addStretch()
            
        # 加载平台
        platforms = self.db_manager.get_all_platforms()
        all_plat_btn = TagButton("全部", is_active=True)
        all_plat_btn.clicked.connect(lambda: self.on_platform_changed(None))
        self.platform_group.addButton(all_plat_btn)
        self.platform_layout_container.addWidget(all_plat_btn)
        
        for plat in platforms:
            btn = TagButton(plat.name)
            btn.clicked.connect(lambda checked, p=plat.name: self.on_platform_changed(p))
            self.platform_group.addButton(btn)
            self.platform_layout_container.addWidget(btn)
            
        self.platform_layout_container.addStretch()
        
        # 加载通告
        self.refresh_notices()
        
    def on_category_changed(self, category):
        self.current_category = category
        self.page = 1
        self.refresh_notices()
        
    def on_platform_changed(self, platform):
        self.current_platform = platform
        self.page = 1
        self.refresh_notices()
        
    def refresh_notices(self):
        """刷新通告列表"""
        # 清空现有的
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 获取筛选条件
        min_fans = None
        fans_text = self.fans_combo.currentText()
        if "1000+" in fans_text: min_fans = 1000
        elif "5000+" in fans_text: min_fans = 5000
        elif "1w+" in fans_text: min_fans = 10000
        elif "5w+" in fans_text: min_fans = 50000
        elif "10w+" in fans_text: min_fans = 100000
        
        # 获取数据
        notices = self.db_manager.get_all_notices(
            category=self.current_category,
            platform=self.current_platform,
            min_fans=min_fans
        )
        
        # 简单的分页逻辑
        total = len(notices)
        total_pages = (total + self.page_size - 1) // self.page_size
        if total_pages == 0: total_pages = 1
        
        self.page_label.setText(f"{self.page} / {total_pages}")
        self.prev_btn.setEnabled(self.page > 1)
        self.next_btn.setEnabled(self.page < total_pages)
        
        start = (self.page - 1) * self.page_size
        end = start + self.page_size
        current_notices = notices[start:end]
        
        # 渲染卡片
        cols = 4 # 固定4列
        for i, notice in enumerate(current_notices):
            card = NoticeCardWidget(notice)
            card.join_clicked.connect(self.add_to_my_links)
            row = i // cols
            col = i % cols
            self.cards_grid.addWidget(card, row, col)
            
    def prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.refresh_notices()
            
    def next_page(self):
        self.page += 1
        self.refresh_notices()
        
    def add_to_my_links(self, notice):
        """将通告添加到我的链接"""
        try:
            # 获取当前用户
            user = self.parent().current_user if self.parent() else None
            
            # 检查链接是否已存在（按用户筛选）
            existing_link = self.db_manager.get_link_by_url(notice.link, user=user)
            if existing_link:
                QMessageBox.information(self, "提示", "该链接已存在于您的链接库中！")
                return

            # 创建新链接
            # 链接名称格式：【平台】标题
            link_name = f"【{notice.platform}】{notice.title}"
            
            self.db_manager.create_link(
                name=link_name,
                url=notice.link,
                user=user,
                status='active',
                category=notice.category,  # 使用通告的分类
                description=f"来自通告广场：{notice.brand} - {notice.product_info}"
            )
            
            QMessageBox.information(self, "成功", "已成功添加到“我的链接”！")
            
            # 尝试刷新主窗口的数据
            if self.parent():
                if hasattr(self.parent(), 'refresh_data'):
                    self.parent().refresh_data()
                    
        except Exception as e:
            QMessageBox.warning(self, "失败", f"添加链接失败：{str(e)}")

    def copy_link(self, link):
        QApplication.clipboard().setText(link)
        QMessageBox.information(self, "成功", "报名链接已复制到剪贴板！")

if __name__ == "__main__":
    # 测试代码
    from database.models import init_database
    init_database()
    
    app = QApplication(sys.argv)
    window = NoticePlazaWindow()
    window.show()
    sys.exit(app.exec())

