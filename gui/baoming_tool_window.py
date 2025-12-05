"""
报名工具专用窗口
处理扫码登录、表单渲染和提交
"""

import base64
from typing import Optional, List, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QLineEdit, QFormLayout, QFrame, QMessageBox,
    QGroupBox, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont, QImage

from core.baoming_tool_filler import BaomingToolFiller


class BaomingToolWindow(QWidget):
    """报名工具专用填充窗口"""
    
    # 信号
    fill_completed = pyqtSignal(bool, str)  # 填充完成信号
    
    def __init__(self, url: str, card_config: List[Dict], parent=None):
        """
        初始化窗口
        
        Args:
            url: 报名工具链接
            card_config: 名片配置，每项包含 name 和 value
            parent: 父窗口
        """
        super().__init__(parent)
        self.url = url
        self.card_config = card_config
        self.filler = BaomingToolFiller()
        self.login_timer: Optional[QTimer] = None
        self.form_inputs: Dict[str, QLineEdit] = {}
        self.filled_data: List[Dict] = []
        
        self.init_ui()
        self.start_login_flow()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle('报名工具 - 扫码登录')
        self.setMinimumSize(500, 600)
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a2e;
                color: #eaeaea;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
            }
            QLabel {
                color: #eaeaea;
            }
            QLineEdit {
                background-color: #16213e;
                border: 1px solid #0f3460;
                border-radius: 6px;
                padding: 10px 12px;
                color: #eaeaea;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #e94560;
            }
            QPushButton {
                background-color: #e94560;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff6b6b;
            }
            QPushButton:pressed {
                background-color: #c23a51;
            }
            QPushButton:disabled {
                background-color: #444;
                color: #888;
            }
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #0f3460;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: #e94560;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)
        
        # 标题
        title_label = QLabel('📱 报名工具')
        title_label.setStyleSheet('font-size: 24px; font-weight: bold; color: #e94560;')
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 状态标签
        self.status_label = QLabel('正在初始化...')
        self.status_label.setStyleSheet('font-size: 14px; color: #888;')
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # 二维码容器
        self.qr_container = QFrame()
        self.qr_container.setStyleSheet("""
            QFrame {
                background-color: #16213e;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        qr_layout = QVBoxLayout(self.qr_container)
        qr_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.qr_label = QLabel()
        self.qr_label.setFixedSize(250, 250)
        self.qr_label.setStyleSheet('background-color: white; border-radius: 8px;')
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_layout.addWidget(self.qr_label)
        
        qr_hint = QLabel('请使用微信扫描二维码登录')
        qr_hint.setStyleSheet('color: #888; font-size: 13px; margin-top: 12px;')
        qr_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_layout.addWidget(qr_hint)
        
        main_layout.addWidget(self.qr_container)
        
        # 表单容器（初始隐藏）
        self.form_container = QScrollArea()
        self.form_container.setWidgetResizable(True)
        self.form_container.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.form_container.hide()
        
        self.form_widget = QWidget()
        self.form_layout = QVBoxLayout(self.form_widget)
        self.form_layout.setSpacing(16)
        self.form_container.setWidget(self.form_widget)
        
        main_layout.addWidget(self.form_container)
        
        # 用户信息
        self.user_info_label = QLabel()
        self.user_info_label.setStyleSheet('font-size: 13px; color: #4ade80;')
        self.user_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.user_info_label.hide()
        main_layout.addWidget(self.user_info_label)
        
        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.refresh_btn = QPushButton('🔄 刷新二维码')
        self.refresh_btn.clicked.connect(self.refresh_qr_code)
        btn_layout.addWidget(self.refresh_btn)
        
        self.submit_btn = QPushButton('📤 提交表单')
        self.submit_btn.clicked.connect(self.submit_form)
        self.submit_btn.hide()
        btn_layout.addWidget(self.submit_btn)
        
        self.close_btn = QPushButton('关闭')
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #444;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(btn_layout)
    
    def start_login_flow(self):
        """开始登录流程"""
        # 初始化
        success, msg = self.filler.initialize(self.url)
        if not success:
            self.status_label.setText(f'❌ {msg}')
            return
        
        self.status_label.setText(msg)
        
        # 获取二维码
        self.fetch_qr_code()
    
    def fetch_qr_code(self):
        """获取二维码"""
        self.status_label.setText('正在获取二维码...')
        
        success, data, code = self.filler.get_qr_code()
        
        if success:
            # 显示二维码
            self.display_qr_code(data)
            self.status_label.setText('请扫描二维码登录')
            
            # 开始轮询登录状态
            self.start_login_polling()
        else:
            self.status_label.setText(f'❌ {data}')
    
    def display_qr_code(self, qr_data: str):
        """显示二维码"""
        try:
            # 解析 base64 数据
            if qr_data.startswith('data:image'):
                # 移除前缀
                base64_data = qr_data.split(',')[1]
            else:
                base64_data = qr_data
            
            # 解码
            image_data = base64.b64decode(base64_data)
            
            # 创建 QPixmap
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            
            # 缩放并显示
            scaled = pixmap.scaled(
                230, 230,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.qr_label.setPixmap(scaled)
            
        except Exception as e:
            self.status_label.setText(f'❌ 显示二维码失败: {str(e)}')
    
    def start_login_polling(self):
        """开始轮询登录状态"""
        if self.login_timer:
            self.login_timer.stop()
        
        self.login_timer = QTimer(self)
        self.login_timer.timeout.connect(self.check_login_status)
        self.login_timer.start(2000)  # 每2秒检查一次
    
    def check_login_status(self):
        """检查登录状态"""
        status, msg, user_info = self.filler.check_login()
        
        if status == 0:
            # 登录成功
            self.login_timer.stop()
            self.on_login_success(user_info)
        elif status == -1:
            # 等待中
            pass
        else:
            # 失败
            self.login_timer.stop()
            self.status_label.setText(f'❌ 登录失败: {msg}')
    
    def on_login_success(self, user_info: Dict):
        """登录成功处理"""
        self.status_label.setText('✅ 登录成功，正在加载表单...')
        
        # 显示用户信息
        uname = user_info.get('uname', '用户')
        self.user_info_label.setText(f'👤 已登录: {uname}')
        self.user_info_label.show()
        
        # 隐藏二维码，显示表单
        self.qr_container.hide()
        self.refresh_btn.hide()
        
        # 加载表单
        self.load_form()
    
    def load_form(self):
        """加载表单"""
        success, msg = self.filler.load_form()
        
        if not success:
            self.status_label.setText(f'❌ {msg}')
            return
        
        self.status_label.setText(msg)
        
        # 自动填充
        self.filled_data = self.filler.match_and_fill(self.card_config)
        
        # 渲染表单
        self.render_form()
    
    def render_form(self):
        """渲染表单"""
        # 清除旧内容
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.form_inputs.clear()
        
        # 创建表单组
        form_group = QGroupBox('📋 表单字段')
        form_inner_layout = QVBoxLayout(form_group)
        form_inner_layout.setSpacing(12)
        
        for field_data in self.filled_data:
            field_name = field_data.get('field_name', '')
            field_key = field_data.get('field_key', '')
            field_value = field_data.get('field_value', '')
            
            # 字段容器
            field_container = QWidget()
            field_layout = QVBoxLayout(field_container)
            field_layout.setContentsMargins(0, 0, 0, 0)
            field_layout.setSpacing(4)
            
            # 标签
            label = QLabel(field_name)
            label.setStyleSheet('font-size: 13px; color: #888;')
            field_layout.addWidget(label)
            
            # 输入框
            input_field = QLineEdit()
            input_field.setText(field_value)
            input_field.setPlaceholderText(f'请输入{field_name}')
            field_layout.addWidget(input_field)
            
            # 保存引用
            self.form_inputs[field_key] = input_field
            
            form_inner_layout.addWidget(field_container)
        
        self.form_layout.addWidget(form_group)
        
        # 添加弹性空间
        self.form_layout.addStretch()
        
        # 显示表单容器和提交按钮
        self.form_container.show()
        self.submit_btn.show()
        
        # 更新状态
        matched_count = sum(1 for d in self.filled_data if d.get('field_value'))
        self.status_label.setText(f'✅ 已自动填充 {matched_count}/{len(self.filled_data)} 个字段')
    
    def refresh_qr_code(self):
        """刷新二维码"""
        if self.login_timer:
            self.login_timer.stop()
        self.fetch_qr_code()
    
    def submit_form(self):
        """提交表单"""
        # 收集表单数据
        submit_data = []
        for field_data in self.filled_data:
            field_key = field_data.get('field_key', '')
            input_field = self.form_inputs.get(field_key)
            
            if input_field:
                submit_data.append({
                    'field_name': field_data.get('field_name', ''),
                    'field_key': field_key,
                    'field_value': input_field.text(),
                    'ignore': field_data.get('ignore', 0)
                })
        
        # 提交
        self.status_label.setText('正在提交...')
        self.submit_btn.setEnabled(False)
        
        success, msg = self.filler.submit(submit_data)
        
        if success:
            self.status_label.setText('✅ 提交成功！')
            QMessageBox.information(self, '成功', '表单提交成功！')
            self.fill_completed.emit(True, '提交成功')
        else:
            self.status_label.setText(f'❌ {msg}')
            QMessageBox.warning(self, '失败', f'提交失败: {msg}')
            self.fill_completed.emit(False, msg)
        
        self.submit_btn.setEnabled(True)
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.login_timer:
            self.login_timer.stop()
        super().closeEvent(event)







