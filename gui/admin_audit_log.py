"""
审核记录管理模块
用于管理员查看和处理名片修改请求
采用现代化玻璃拟态设计风格
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QMessageBox, QLineEdit, QFrame, 
    QGraphicsDropShadowEffect, QDialog, QScrollArea, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from database import DatabaseManager, CardEditRequest
from gui.admin_base_components import (
    PREMIUM_COLORS, GlassFrame, GradientButton, CompactStatWidget, create_action_button
)
import datetime
import json


# ========== 审核记录列表自定义组件 ==========

# 列宽配置
AUDIT_LIST_COLUMNS = {
    'card': 180,
    'user': 100,
    'admin': 100,
    'status': 100,
    'created': 130,
    'processed': 130,
    'actions': 70,
}


class AuditListHeader(QFrame):
    """审核记录列表表头"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(f"""
            AuditListHeader {{
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
            ('目标名片', AUDIT_LIST_COLUMNS['card']),
            ('所属用户', AUDIT_LIST_COLUMNS['user']),
            ('申请人', AUDIT_LIST_COLUMNS['admin']),
            ('状态', AUDIT_LIST_COLUMNS['status']),
            ('提交时间', AUDIT_LIST_COLUMNS['created']),
            ('处理时间', AUDIT_LIST_COLUMNS['processed']),
            ('操作', AUDIT_LIST_COLUMNS['actions']),
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


class AuditRowWidget(QFrame):
    """审核记录行组件"""
    
    view_clicked = pyqtSignal(object)
    
    def __init__(self, req, parent=None):
        super().__init__(parent)
        self.req = req
        self.setFixedHeight(60)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet(f"""
            AuditRowWidget {{
                background: white;
                border: none;
                border-bottom: 1px solid {PREMIUM_COLORS['border_light']};
            }}
            AuditRowWidget:hover {{
                background: #fafbfc;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(0)
        
        # 1. 目标名片
        self._add_card(layout)
        # 2. 所属用户
        self._add_user(layout)
        # 3. 申请人
        self._add_admin(layout)
        # 4. 状态
        self._add_status(layout)
        # 5. 提交时间
        self._add_created(layout)
        # 6. 处理时间
        self._add_processed(layout)
        # 7. 操作
        self._add_actions(layout)
        
        layout.addStretch()
    
    def _add_card(self, layout):
        container = QWidget()
        container.setFixedWidth(AUDIT_LIST_COLUMNS['card'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 8, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # 安全地获取名片名称，处理已删除的名片引用
        try:
            card_name = self.req.card.name if self.req.card else (self.req.original_name or "未知名片")
        except Exception:
            # 名片已被删除，使用备用名称
            card_name = self.req.original_name or "已删除的名片"
        
        lbl = QLabel(card_name)
        lbl.setStyleSheet(f"font-weight: 600; color: {PREMIUM_COLORS['text_heading']}; font-size: 13px;")
        lbl.setToolTip(card_name)
        c_layout.addWidget(lbl)
        layout.addWidget(container)
    
    def _add_user(self, layout):
        container = QWidget()
        container.setFixedWidth(AUDIT_LIST_COLUMNS['user'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 安全地获取用户名，处理已删除的用户引用
        try:
            user_name = self.req.user.username if self.req.user else "未知"
        except Exception:
            user_name = "已删除"
        
        lbl = QLabel(user_name)
        lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-size: 12px;")
        c_layout.addWidget(lbl)
        layout.addWidget(container)
    
    def _add_admin(self, layout):
        container = QWidget()
        container.setFixedWidth(AUDIT_LIST_COLUMNS['admin'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 安全地获取管理员名，处理已删除的管理员引用
        try:
            admin_name = self.req.admin.username if self.req.admin else "未知"
        except Exception:
            admin_name = "已删除"
        
        lbl = QLabel(admin_name)
        lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-size: 12px;")
        c_layout.addWidget(lbl)
        layout.addWidget(container)
    
    def _add_status(self, layout):
        container = QWidget()
        container.setFixedWidth(AUDIT_LIST_COLUMNS['status'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        s_lbl = QLabel()
        if self.req.status == 'pending':
            s_lbl.setText("⏳ 待审批")
            s_lbl.setStyleSheet("color: #d97706; background: #fff7ed; padding: 4px 10px; border-radius: 10px; font-size: 11px; font-weight: 600;")
        elif self.req.status == 'approved':
            s_lbl.setText("✅ 已通过")
            s_lbl.setStyleSheet("color: #059669; background: #ecfdf5; padding: 4px 10px; border-radius: 10px; font-size: 11px; font-weight: 600;")
        else:
            s_lbl.setText("❌ 已拒绝")
            s_lbl.setStyleSheet("color: #dc2626; background: #fef2f2; padding: 4px 10px; border-radius: 10px; font-size: 11px; font-weight: 600;")
        
        c_layout.addWidget(s_lbl)
        layout.addWidget(container)
    
    def _add_created(self, layout):
        container = QWidget()
        container.setFixedWidth(AUDIT_LIST_COLUMNS['created'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        c_time = self.req.created_at.strftime('%Y-%m-%d %H:%M') if self.req.created_at else "-"
        lbl = QLabel(c_time)
        lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-size: 12px;")
        c_layout.addWidget(lbl)
        layout.addWidget(container)
    
    def _add_processed(self, layout):
        container = QWidget()
        container.setFixedWidth(AUDIT_LIST_COLUMNS['processed'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 4, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        p_time = self.req.processed_at.strftime('%Y-%m-%d %H:%M') if self.req.processed_at else "-"
        lbl = QLabel(p_time)
        lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_hint']}; font-size: 12px;")
        c_layout.addWidget(lbl)
        layout.addWidget(container)
    
    def _add_actions(self, layout):
        container = QWidget()
        container.setFixedWidth(AUDIT_LIST_COLUMNS['actions'])
        c_layout = QHBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_view = create_action_button("查看", PREMIUM_COLORS['gradient_blue_start'])
        btn_view.clicked.connect(lambda: self.view_clicked.emit(self.req))
        c_layout.addWidget(btn_view)
        layout.addWidget(container)


class AuditListWidget(QWidget):
    """审核记录列表组件"""
    
    view_request = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.row_widgets = []
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.header = AuditListHeader()
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
    
    def set_requests(self, requests):
        for widget in self.row_widgets:
            widget.deleteLater()
        self.row_widgets.clear()
        
        if not requests:
            empty_label = QLabel("暂无审核记录")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet(f"""
                color: {PREMIUM_COLORS['text_hint']};
                font-size: 14px;
                padding: 60px;
            """)
            self.content_layout.addWidget(empty_label)
            self.row_widgets.append(empty_label)
            return
        
        for req in requests:
            row = AuditRowWidget(req)
            row.view_clicked.connect(self.view_request.emit)
            
            self.content_layout.addWidget(row)
            self.row_widgets.append(row)

class AdminAuditLogDetailDialog(QDialog):
    """审核记录详情对话框"""
    
    def __init__(self, request: CardEditRequest, parent=None):
        super().__init__(parent)
        self.request = request
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("审核记录详情")
        self.setFixedSize(500, 650)
        self.setStyleSheet("QDialog { background-color: #f8fafc; }")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setFixedHeight(100)
        
        # 根据状态设置不同的Header背景色
        if self.request.status == 'approved':
            bg_start, bg_end = PREMIUM_COLORS['gradient_green_start'], PREMIUM_COLORS['gradient_green_end']
            status_text = "已通过"
            icon = "✅"
        elif self.request.status == 'rejected':
            bg_start, bg_end = PREMIUM_COLORS['coral'], '#ff8787'
            status_text = "已拒绝"
            icon = "❌"
        else:
            bg_start, bg_end = PREMIUM_COLORS['gradient_orange_start'], PREMIUM_COLORS['gradient_orange_end']
            status_text = "待审批"
            icon = "⏳"
            
        header.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {bg_start}, stop:1 {bg_end});
            }}
        """)
        
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(30, 20, 30, 20)
        
        title_row = QHBoxLayout()
        title_lbl = QLabel(f"{icon} {status_text}")
        title_lbl.setStyleSheet("color: white; font-size: 22px; font-weight: 800;")
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        header_layout.addLayout(title_row)
        
        sub_lbl = QLabel(f"申请ID: {self.request.id}")
        sub_lbl.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 12px;")
        header_layout.addWidget(sub_lbl)
        
        layout.addWidget(header)
        
        # Content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(16)
        
        # 基本信息卡片
        info_card = self._create_section("基本信息")
        info_layout = info_card.layout()
        
        # 安全地获取名片名称
        try:
            card_name = self.request.card.name if self.request.card else self.request.original_name
        except Exception:
            card_name = self.request.original_name or "已删除的名片"
        
        # 安全地获取用户名
        try:
            user_name = self.request.user.username if self.request.user else "未知"
        except Exception:
            user_name = "已删除"
        
        # 安全地获取管理员名
        try:
            admin_name = self.request.admin.username if self.request.admin else "未知"
        except Exception:
            admin_name = "已删除"
        
        info_layout.addWidget(self._create_info_row("目标名片", card_name))
        info_layout.addWidget(self._create_info_row("所属用户", user_name))
        info_layout.addWidget(self._create_info_row("申请管理员", admin_name))
        info_layout.addWidget(self._create_info_row("提交时间", self.request.created_at))
        if self.request.processed_at:
            info_layout.addWidget(self._create_info_row("处理时间", self.request.processed_at))
            
        content_layout.addWidget(info_card)
        
        # 备注信息
        if self.request.admin_comment or self.request.user_comment:
            comment_card = self._create_section("备注信息")
            c_layout = comment_card.layout()
            if self.request.admin_comment:
                c_layout.addWidget(self._create_info_row("管理员备注", self.request.admin_comment))
            if self.request.user_comment:
                c_layout.addWidget(self._create_info_row("用户反馈", self.request.user_comment))
            content_layout.addWidget(comment_card)
            
        # 变更内容
        change_card = self._create_section("变更摘要")
        ch_layout = change_card.layout()
        
        if self.request.original_name != self.request.modified_name:
            ch_layout.addWidget(self._create_change_row("名片名称", self.request.original_name, self.request.modified_name))
            
        if self.request.original_category != self.request.modified_category:
            ch_layout.addWidget(self._create_change_row("分类", self.request.original_category, self.request.modified_category))
            
        ch_layout.addWidget(QLabel("详细配置变更请在名片详情中查看"))
        content_layout.addWidget(change_card)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # Footer
        footer = QFrame()
        footer.setStyleSheet("background: white; border-top: 1px solid #e2e8f0;")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 16, 20, 16)
        
        if self.request.status == 'pending':
            del_btn = QPushButton("撤销申请")
            del_btn.setStyleSheet(f"color: {PREMIUM_COLORS['coral']}; background: transparent; font-weight: 600; border: none;")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(self.delete_request)
            footer_layout.addWidget(del_btn)
            
        footer_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.setFixedSize(80, 36)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PREMIUM_COLORS['surface']};
                border: 1px solid {PREMIUM_COLORS['border']};
                border-radius: 18px;
                color: {PREMIUM_COLORS['text_body']};
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {PREMIUM_COLORS['background']}; }}
        """)
        close_btn.clicked.connect(self.accept)
        footer_layout.addWidget(close_btn)
        
        layout.addWidget(footer)
        
    def _create_section(self, title):
        frame = QFrame()
        frame.setStyleSheet("background: white; border-radius: 12px; border: 1px solid #e2e8f0;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_heading']}; font-weight: 700; font-size: 14px;")
        layout.addWidget(title_lbl)
        
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: #f1f5f9;")
        layout.addWidget(line)
        
        return frame
        
    def _create_info_row(self, label, value):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        l_lbl = QLabel(label)
        l_lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_hint']}; font-size: 13px;")
        l_lbl.setFixedWidth(80)
        
        v_lbl = QLabel(str(value) if value else "-")
        v_lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_body']}; font-size: 13px; font-weight: 500;")
        v_lbl.setWordWrap(True)
        
        layout.addWidget(l_lbl)
        layout.addWidget(v_lbl)
        return container
        
    def _create_change_row(self, label, old, new):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        l_lbl = QLabel(label)
        l_lbl.setStyleSheet(f"color: {PREMIUM_COLORS['text_heading']}; font-weight: 600; font-size: 12px;")
        layout.addWidget(l_lbl)
        
        row = QHBoxLayout()
        old_lbl = QLabel(old)
        old_lbl.setStyleSheet("color: #9ca3af; text-decoration: line-through;")
        
        arrow = QLabel("→")
        arrow.setStyleSheet("color: #cbd5e1;")
        
        new_lbl = QLabel(new)
        new_lbl.setStyleSheet(f"color: {PREMIUM_COLORS['gradient_blue_start']}; font-weight: 600;")
        
        row.addWidget(old_lbl)
        row.addWidget(arrow)
        row.addWidget(new_lbl)
        row.addStretch()
        
        layout.addLayout(row)
        return container

    def delete_request(self):
        confirm = QMessageBox.question(
            self, "确认撤销",
            "确定要撤销此修改申请吗？\n撤销后用户将不再看到此请求。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            if DatabaseManager.delete_card_edit_request(self.request.id):
                QMessageBox.information(self, "成功", "已撤销申请")
                self.accept()
            else:
                QMessageBox.critical(self, "错误", "操作失败")

class AdminAuditLogManager(QWidget):
    """管理员审核记录页面"""
    
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
        
        # === Main Content ===
        self._create_main_card(main_layout)
        
        self.load_data()
        
    def _create_header(self, layout):
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)
        
        title_label = QLabel("审核记录中心")
        title_label.setStyleSheet(f"""
            font-size: 24px; 
            font-weight: 800; 
            color: {PREMIUM_COLORS['text_heading']};
            background: transparent;
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addSpacing(16)
        
        # Stats
        stats_data = [
            ("待审批", 0, "⏳", PREMIUM_COLORS['gradient_orange_start'], PREMIUM_COLORS['gradient_orange_end']),
            ("已通过", 0, "✅", PREMIUM_COLORS['gradient_green_start'], PREMIUM_COLORS['gradient_green_end']),
            ("已拒绝", 0, "❌", PREMIUM_COLORS['coral'], '#ff8787'),
        ]
        
        for title, value, icon, start, end in stats_data:
            widget = CompactStatWidget(title, value, icon, start, end)
            self.stat_widgets[title] = widget
            header_layout.addWidget(widget)
            
        header_layout.addStretch()
        
        refresh_btn = GradientButton(
            "刷新数据",
            PREMIUM_COLORS['gradient_blue_start'],
            PREMIUM_COLORS['gradient_blue_end']
        )
        refresh_btn.setFixedSize(120, 40)
        refresh_btn.clicked.connect(self.load_data)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
    def _create_main_card(self, layout):
        card = GlassFrame(opacity=1.0, radius=16)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        
        # Toolbar
        toolbar = QFrame()
        toolbar.setFixedHeight(56)
        toolbar.setStyleSheet(f"border-bottom: 1px solid {PREMIUM_COLORS['border_light']}; background: transparent;")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 0, 16, 0)
        
        # Filter
        self.status_filter = QComboBox()
        self.status_filter.blockSignals(True)
        self.status_filter.model().blockSignals(True)
        self.status_filter.addItems(["全部状态", "待审批", "已通过", "已拒绝"])
        self.status_filter.model().blockSignals(False)
        self.status_filter.blockSignals(False)
        self.status_filter.setFixedSize(100, 32)
        self.status_filter.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid {PREMIUM_COLORS['border_light']};
                border-radius: 6px;
                padding: 0 10px;
                background: white;
            }}
        """)
        self.status_filter.currentTextChanged.connect(self.on_search)
        toolbar_layout.addWidget(self.status_filter)
        
        # Search
        search_container = QFrame()
        search_container.setFixedSize(260, 32)
        search_container.setStyleSheet(f"""
            QFrame {{
                background: {PREMIUM_COLORS['background']};
                border-radius: 16px;
            }}
        """)
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(10, 0, 10, 0)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索名片名称或用户名...")
        self.search_input.setStyleSheet("border: none; background: transparent;")
        self.search_input.textChanged.connect(self.on_search)
        search_layout.addWidget(QLabel("🔍"))
        search_layout.addWidget(self.search_input)
        toolbar_layout.addWidget(search_container)
        
        toolbar_layout.addStretch()
        card_layout.addWidget(toolbar)
        
        # 自定义审核记录列表
        self.audit_list = AuditListWidget()
        self.audit_list.view_request.connect(self.view_detail)
        card_layout.addWidget(self.audit_list, 1)
        
        # Pagination
        pagination = QFrame()
        pagination.setFixedHeight(50)
        pagination.setStyleSheet(f"background: white; border-top: 1px solid {PREMIUM_COLORS['border_light']}; border-bottom-left-radius: 16px; border-bottom-right-radius: 16px;")
        p_layout = QHBoxLayout(pagination)
        p_layout.setContentsMargins(16, 0, 16, 0)
        
        self.page_info = QLabel("0 / 0")
        p_layout.addWidget(self.page_info)
        p_layout.addStretch()
        
        self.prev_btn = QPushButton("‹")
        self.next_btn = QPushButton("›")
        for btn in [self.prev_btn, self.next_btn]:
            btn.setFixedSize(28, 28)
            btn.clicked.connect(self.change_page)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {PREMIUM_COLORS['surface']};
                    border: 1px solid {PREMIUM_COLORS['border']};
                    border-radius: 14px;
                }}
                QPushButton:hover {{ background: {PREMIUM_COLORS['primary']}15; border-color: {PREMIUM_COLORS['primary']}; }}
            """)
            
        p_layout.addWidget(self.prev_btn)
        p_layout.addWidget(self.next_btn)
        
        card_layout.addWidget(pagination)
        layout.addWidget(card, 1)
        
    def change_page(self):
        sender = self.sender()
        if sender == self.prev_btn:
            self.current_page -= 1
        else:
            self.current_page += 1
        self.load_data()
        
    def on_search(self):
        self.current_page = 1
        self.load_data()
        
    def load_data(self):
        keyword = self.search_input.text().strip().lower()
        status_map = {"待审批": "pending", "已通过": "approved", "已拒绝": "rejected"}
        status = status_map.get(self.status_filter.currentText())
        
        # Get all requests
        requests = DatabaseManager.get_card_edit_requests(status=status)
        
        # Client-side filter
        if keyword:
            filtered = []
            for r in requests:
                c_name = r.card.name if r.card else r.original_name or ""
                u_name = r.user.username if r.user else ""
                if keyword in c_name.lower() or keyword in u_name.lower():
                    filtered.append(r)
            requests = filtered
            
        # Update Stats
        pending = sum(1 for r in requests if r.status == 'pending')
        approved = sum(1 for r in requests if r.status == 'approved')
        rejected = sum(1 for r in requests if r.status == 'rejected')
        
        if "待审批" in self.stat_widgets: self.stat_widgets["待审批"].update_value(pending)
        if "已通过" in self.stat_widgets: self.stat_widgets["已通过"].update_value(approved)
        if "已拒绝" in self.stat_widgets: self.stat_widgets["已拒绝"].update_value(rejected)
        
        # Pagination
        self.total_records = len(requests)
        self.total_pages = max(1, (self.total_records + self.page_size - 1) // self.page_size)
        self.current_page = max(1, min(self.current_page, self.total_pages))
        
        start = (self.current_page - 1) * self.page_size
        page_data = requests[start:start+self.page_size]
        
        self.audit_list.set_requests(page_data)
        
        self.page_info.setText(f"显示 {start+1}-{min(start+self.page_size, self.total_records)} 条，共 {self.total_records} 条")
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < self.total_pages)
            
    def view_detail(self, req):
        dialog = AdminAuditLogDetailDialog(req, self)
        if dialog.exec():
            self.load_data()

