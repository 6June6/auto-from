"""
登录窗口 - Enterprise Modern UI
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFrame, QMessageBox,
    QGraphicsDropShadowEffect, QApplication, QWidget,
    QCheckBox, QGridLayout, QSizePolicy, QGraphicsOpacityEffect
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QPoint, QRectF,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QVariantAnimation
)
from PyQt6.QtGui import QFont, QColor, QCursor, QLinearGradient, QPalette, QBrush, QPainter, QPen
from database import User
from core.auth import login_with_password, get_device_id
from pathlib import Path


class ModernSpinner(QWidget):
    """现代风格加载动画组件 - 双环科技感设计"""
    
    def __init__(self, parent=None, size=80, color="#3B82F6"):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._color = QColor(color)
        
        # 动画参数
        self._angle_outer = 0
        self._angle_inner = 0
        self._scale = 1.0
        self._scale_direction = 1
        
        # 呼吸动画定时器
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        
    def start(self):
        self._timer.start(16)  # ~60fps
        
    def stop(self):
        self._timer.stop()
        
    def _animate(self):
        # 外环顺时针
        self._angle_outer = (self._angle_outer + 4) % 360
        # 内环逆时针
        self._angle_inner = (self._angle_inner - 6) % 360
        
        # 中心呼吸效果
        if self._scale > 1.2:
            self._scale_direction = -1
        elif self._scale < 0.8:
            self._scale_direction = 1
        self._scale += 0.01 * self._scale_direction
        
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = self.rect().center()
        w, h = self.width(), self.height()
        
        # --- 1. 绘制外环 (动态断开的弧线) ---
        radius_outer = min(w, h) / 2 - 4
        rect_outer = QRectF(center.x() - radius_outer, center.y() - radius_outer, 
                           radius_outer * 2, radius_outer * 2)
        
        pen_outer = QPen(self._color, 4)
        pen_outer.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_outer)
        
        # 两条追逐的弧线
        start_angle = self._angle_outer * 16
        painter.drawArc(rect_outer, start_angle, 100 * 16)
        painter.drawArc(rect_outer, start_angle + 180 * 16, 60 * 16)
        
        # --- 2. 绘制内环 (半透明虚线) ---
        radius_inner = radius_outer - 12
        rect_inner = QRectF(center.x() - radius_inner, center.y() - radius_inner,
                           radius_inner * 2, radius_inner * 2)
                           
        pen_inner = QPen(self._color)
        pen_inner.setWidth(3)
        pen_inner.setCapStyle(Qt.PenCapStyle.RoundCap)
        # 降低不透明度
        c = QColor(self._color)
        c.setAlpha(120)
        pen_inner.setColor(c)
        painter.setPen(pen_inner)
        
        start_angle_in = self._angle_inner * 16
        painter.drawArc(rect_inner, start_angle_in, 280 * 16)
        
        # --- 3. 绘制中心呼吸点 ---
        radius_center = 6 * self._scale
        painter.setPen(Qt.PenStyle.NoPen)
        c.setAlpha(255) # 恢复不透明
        painter.setBrush(QBrush(c))
        painter.drawEllipse(QPoint(int(center.x()), int(center.y())), int(radius_center), int(radius_center))
        
        # --- 4. 绘制外部微弱光晕 (可选) ---
        c.setAlpha(30)
        painter.setBrush(QBrush(c))
        painter.drawEllipse(center, radius_outer + 2, radius_outer + 2)

# -----------------------------------------------------------------------------
# Design System
# -----------------------------------------------------------------------------

class DesignToken:
    """高级 UI 设计系统"""
    # 品牌色系 - 深邃科技蓝
    BRAND_DARK = '#0F172A'     # 深蓝黑背景
    BRAND_PRIMARY = '#3B82F6'  # 亮蓝色主色
    BRAND_ACCENT = '#60A5FA'   # 浅蓝点缀
    
    # 渐变背景
    SIDEBAR_GRADIENT = "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1E293B, stop:1 #0F172A)"
    
    # 文本颜色
    TEXT_WHITE = '#FFFFFF'
    TEXT_TITLE = '#1E293B'
    TEXT_BODY = '#64748B'
    TEXT_HINT = '#94A3B8'
    
    # 组件颜色
    INPUT_BG = '#F8FAFC'
    INPUT_BORDER = '#E2E8F0'
    
    FONT_FAMILY = "Microsoft YaHei UI, Segoe UI, sans-serif"

# -----------------------------------------------------------------------------
# Components
# -----------------------------------------------------------------------------

class InputGroup(QWidget):
    """带标签和图标的输入框组合"""
    def __init__(self, label_text, placeholder, is_password=False, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        
        # 标签
        self.label = QLabel(label_text)
        self.label.setFont(QFont(DesignToken.FONT_FAMILY, 9, QFont.Weight.Bold))
        self.label.setStyleSheet(f"color: {DesignToken.TEXT_BODY};")
        layout.addWidget(self.label)
        
        # 输入框
        self.input = QLineEdit()
        self.input.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.input.setPlaceholderText(placeholder)
        if is_password:
            self.input.setEchoMode(QLineEdit.EchoMode.Password)
        self.input.setMinimumHeight(45)
        self.input.setFont(QFont(DesignToken.FONT_FAMILY, 10))
        self.input.setStyleSheet(f"""
            QLineEdit {{
                padding: 0 12px;
                background-color: {DesignToken.INPUT_BG};
                border: 1px solid {DesignToken.INPUT_BORDER};
                border-radius: 8px;
                color: {DesignToken.TEXT_TITLE};
            }}
            QLineEdit:hover {{
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
            }}
            QLineEdit:focus {{
                background-color: #FFFFFF;
                border: 1px solid {DesignToken.BRAND_PRIMARY};
            }}
        """)
        layout.addWidget(self.input)

    def text(self):
        return self.input.text()

    def setFocus(self):
        self.input.setFocus()

    def set_return_pressed_callback(self, callback):
        self.input.returnPressed.connect(callback)

# -----------------------------------------------------------------------------
# Main Window
# -----------------------------------------------------------------------------

class LoginWindow(QDialog):
    """登录窗口 - 左右分栏高端布局"""
    login_success = pyqtSignal(object)
    ready_to_show_main = pyqtSignal(object)
    
    def __init__(self, parent=None, auto_login=True):
        super().__init__(parent)
        self.current_user = None
        self.main_window_ready = False
        self._is_closing = False
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._animations = []
        
        self.init_ui()
        self._load_saved_credentials()
        
        self.dragging = False
        self.drag_position = QPoint()
        
        self.start_entrance_animation()
        
    def init_ui(self):
        self.setFixedSize(850, 560) # 增加尺寸以容纳更多内容，防止显示不全
        
        # 主容器（用于圆角切割）
        self.main_frame = QFrame(self)
        self.main_frame.setGeometry(0, 0, 850, 560)
        self.main_frame.setStyleSheet(f"""
            QFrame#MainFrame {{
                background-color: #FFFFFF;
                border-radius: 16px;
            }}
        """)
        self.main_frame.setObjectName("MainFrame")
        
        # 添加窗口阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 0)
        self.main_frame.setGraphicsEffect(shadow)
        
        # 主布局：水平排列
        h_layout = QHBoxLayout(self.main_frame)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)
        
        # ---------------------------------------------------------------------
        # 左侧：品牌视觉区 (40%)
        # ---------------------------------------------------------------------
        left_panel = QFrame()
        left_panel.setStyleSheet(f"""
            QFrame {{
                background: {DesignToken.SIDEBAR_GRADIENT};
                border-top-left-radius: 16px;
                border-bottom-left-radius: 16px;
            }}
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(40, 60, 40, 40)
        
        # 装饰 Logo
        logo_icon = QLabel("💠")
        logo_icon.setFont(QFont("Segoe UI Emoji", 48))
        logo_icon.setStyleSheet("color: transparent; background: transparent;") # 这里只是占位，实际可以是图片
        # 为了好看，用文字模拟一个图形 Logo
        logo_text = QLabel("AUTO\nFILLER")
        logo_text.setFont(QFont("Impact", 28))
        logo_text.setStyleSheet(f"color: {DesignToken.BRAND_ACCENT}; line-height: 100%;")
        
        left_layout.addWidget(logo_icon)
        left_layout.addWidget(logo_text)
        
        left_layout.addSpacing(30)
        
        # 宣传语
        slogan_title = QLabel("简单 · 快捷 · 高效")
        slogan_title.setFont(QFont(DesignToken.FONT_FAMILY, 14, QFont.Weight.Bold))
        slogan_title.setStyleSheet("color: #FFFFFF;")
        left_layout.addWidget(slogan_title)
        
        slogan_desc = QLabel("新一代自动表单填写工具\n智能多开处理，抢占订单快人一步！")
        slogan_desc.setWordWrap(True)
        slogan_desc.setFont(QFont(DesignToken.FONT_FAMILY, 10))
        slogan_desc.setStyleSheet("color: #94A3B8; line-height: 150%;")
        left_layout.addWidget(slogan_desc)
        
        left_layout.addStretch()
        
        # 底部版本信息
        version_label = QLabel("Version 2.0.1 Enterprise")
        version_label.setStyleSheet("color: #475569; font-size: 10px;")
        left_layout.addWidget(version_label)
        
        h_layout.addWidget(left_panel, 38) # 占比 38%
        
        # ---------------------------------------------------------------------
        # 右侧：登录表单区 (60%)
        # ---------------------------------------------------------------------
        right_panel = QFrame()
        right_panel.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-top-right-radius: 16px;
                border-bottom-right-radius: 16px;
            }
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(50, 45, 50, 35)
        right_layout.setSpacing(10)
        
        # 顶部操作栏 (关闭按钮)
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet("""
            QPushButton {
                border: none;
                font-size: 20px;
                color: #94A3B8;
                background: transparent;
            }
            QPushButton:hover { color: #EF4444; }
        """)
        close_btn.clicked.connect(self.reject)
        top_bar.addWidget(close_btn)
        right_layout.addLayout(top_bar)
        
        # 标题
        welcome_title = QLabel("欢迎登录")
        welcome_title.setFont(QFont(DesignToken.FONT_FAMILY, 22, QFont.Weight.Bold))
        welcome_title.setStyleSheet(f"color: {DesignToken.TEXT_TITLE};")
        right_layout.addWidget(welcome_title)
        
        sub_title = QLabel("请输入您的管理员账号信息")
        sub_title.setFont(QFont(DesignToken.FONT_FAMILY, 10))
        sub_title.setStyleSheet(f"color: {DesignToken.TEXT_BODY};")
        right_layout.addWidget(sub_title)
        
        right_layout.addSpacing(30)
        
        # 表单
        self.username_input = InputGroup("账号", "请输入用户名 / 手机号")
        right_layout.addWidget(self.username_input)
        
        right_layout.addSpacing(15)
        
        self.password_input = InputGroup("密码", "请输入密码", is_password=True)
        self.password_input.set_return_pressed_callback(self.do_login)
        right_layout.addWidget(self.password_input)
        
        right_layout.addSpacing(15)
        
        # 辅助选项
        options_layout = QHBoxLayout()
        self.remember_me = QCheckBox("记住我")
        self.remember_me.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.remember_me.setStyleSheet(f"""
            QCheckBox {{ color: {DesignToken.TEXT_BODY}; font-size: 12px; }}
            QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid #CBD5E1; }}
            QCheckBox::indicator:checked {{ background-color: {DesignToken.BRAND_PRIMARY}; border-color: {DesignToken.BRAND_PRIMARY}; }}
        """)
        options_layout.addWidget(self.remember_me)
        
        options_layout.addStretch()
        
        forget_btn = QPushButton("忘记密码?")
        forget_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        forget_btn.setStyleSheet(f"border: none; color: {DesignToken.BRAND_PRIMARY}; font-size: 12px;")
        forget_btn.clicked.connect(lambda: QMessageBox.information(self, "提示", "请联系系统管理员重置密码。"))
        options_layout.addWidget(forget_btn)
        
        right_layout.addLayout(options_layout)
        
        right_layout.addSpacing(30)
        
        # 登录按钮
        self.login_btn = QPushButton("登  录")
        self.login_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.login_btn.setMinimumHeight(48)
        self.login_btn.setFont(QFont(DesignToken.FONT_FAMILY, 11, QFont.Weight.Bold))
        self.login_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {DesignToken.BRAND_PRIMARY};
                color: white;
                border: none;
                border-radius: 8px;
                letter-spacing: 4px;
            }}
            QPushButton:hover {{
                background-color: {DesignToken.BRAND_ACCENT};
            }}
            QPushButton:pressed {{
                background-color: #2563EB;
            }}
        """)
        self.login_btn.clicked.connect(self.do_login)
        
        # 按钮光晕效果
        btn_shadow = QGraphicsDropShadowEffect(self)
        btn_shadow.setBlurRadius(20)
        btn_shadow.setColor(QColor(59, 130, 246, 80))
        btn_shadow.setOffset(0, 5)
        self.login_btn.setGraphicsEffect(btn_shadow)
        
        right_layout.addWidget(self.login_btn)
        
        right_layout.addStretch()
        
        # 底部机器码
        try:
            device_id = get_device_id()
            # 稍微增加显示的长度，或者调整字体大小
            short_id = device_id[-12:] if len(device_id) > 12 else device_id
            dev_text = f"设备号: {short_id}"
        except:
            device_id = "Unknown"
            dev_text = "设备号: N/A"
            
        self.device_label = QPushButton(dev_text)
        self.device_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.device_label.setStyleSheet("border: none; color: #CBD5E1; font-size: 11px; text-align: right;")
        self.device_label.clicked.connect(lambda: self.copy_machine_code(device_id))
        
        dev_layout = QHBoxLayout()
        dev_layout.addStretch()
        dev_layout.addWidget(self.device_label)
        right_layout.addLayout(dev_layout)
        
        h_layout.addWidget(right_panel, 62) # 占比 62%
        
        # 动画结束后再聚焦，避免闪烁

    def start_entrance_animation(self):
        """启动高质感入场动画"""
        import sys
        is_windows = sys.platform == 'win32'
        
        # 确保 main_frame 已经创建
        if not hasattr(self, 'main_frame'):
            return
        
        # Windows 上只使用透明度动画，避免位置动画导致的重影问题
        if is_windows:
            self.setWindowOpacity(0)
            
            # 仅透明度动画
            self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
            self.opacity_anim.setDuration(400)
            self.opacity_anim.setStartValue(0)
            self.opacity_anim.setEndValue(1)
            self.opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._animations.append(self.opacity_anim)
            
            # 动画结束后强制重绘并聚焦
            self.opacity_anim.finished.connect(self._on_animation_finished)
            self.opacity_anim.start()
        else:
            # macOS/Linux 使用完整动画效果
            self.setWindowOpacity(0)
            original_rect = self.main_frame.geometry()
            
            # 1. 透明度动画 (Fade In)
            self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
            self.opacity_anim.setDuration(700)
            self.opacity_anim.setStartValue(0)
            self.opacity_anim.setEndValue(1)
            self.opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._animations.append(self.opacity_anim)
            
            # 2. 位置上浮动画 (Slide Up)
            start_rect = original_rect.translated(0, 50)
            
            self.pos_anim = QPropertyAnimation(self.main_frame, b"geometry")
            self.pos_anim.setDuration(700)
            self.pos_anim.setStartValue(start_rect)
            self.pos_anim.setEndValue(original_rect)
            self.pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._animations.append(self.pos_anim)
            
            # 3. 组合并启动
            self.anim_group = QParallelAnimationGroup()
            self.anim_group.addAnimation(self.opacity_anim)
            self.anim_group.addAnimation(self.pos_anim)
            
            # 动画结束后聚焦输入框
            self.anim_group.finished.connect(self._on_animation_finished)
            self.anim_group.start()
    
    def _on_animation_finished(self):
        """动画结束后的清理工作"""
        self.main_frame.update()
        self.update()
        self.repaint()
        self.username_input.setFocus()
    
    def _load_saved_credentials(self):
        """加载已保存的账号密码并自动填充"""
        try:
            import json
            cred_file = Path.home() / '.auto-form-filler' / '.credentials'
            if not cred_file.exists():
                return
            data = json.loads(cred_file.read_text(encoding='utf-8'))
            username = data.get('username', '')
            password = data.get('password', '')
            if username:
                self.username_input.input.setText(username)
            if password:
                self.password_input.input.setText(password)
            self.remember_me.setChecked(True)
        except Exception:
            pass

    def _save_credentials(self, username: str, password: str):
        """保存账号密码到本地"""
        try:
            import json
            auth_dir = Path.home() / '.auto-form-filler'
            auth_dir.mkdir(exist_ok=True)
            cred_file = auth_dir / '.credentials'
            cred_file.write_text(
                json.dumps({'username': username, 'password': password}, ensure_ascii=False),
                encoding='utf-8'
            )
        except Exception:
            pass

    def _clear_credentials(self):
        """清除已保存的账号密码"""
        try:
            cred_file = Path.home() / '.auto-form-filler' / '.credentials'
            if cred_file.exists():
                cred_file.unlink()
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Window Drag Logic
    # -------------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.dragging = False

    # -------------------------------------------------------------------------
    # Logic
    # -------------------------------------------------------------------------
    def copy_machine_code(self, code):
        clipboard = QApplication.clipboard()
        clipboard.setText(code)
        
        original = self.device_label.text()
        self.device_label.setText("Copied!")
        self.device_label.setStyleSheet(f"border: none; color: {DesignToken.BRAND_PRIMARY}; font-size: 11px;")
        QTimer.singleShot(1500, lambda: self.restore_device_label(original))
        
    def restore_device_label(self, text):
        try:
            self.device_label.setText(text)
            self.device_label.setStyleSheet("border: none; color: #CBD5E1; font-size: 11px;")
        except: pass
    
    def do_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username:
            self.shake_window()
            self.username_input.setFocus()
            return
        
        if not password:
            self.shake_window()
            self.password_input.setFocus()
            return
        
        # 显示加载状态
        self.show_loading_state()
        
        # 使用定时器延迟执行登录，让UI有时间更新
        QTimer.singleShot(100, lambda: self._perform_login(username, password))
    
    def _perform_login(self, username, password):
        """实际执行登录逻辑"""
        try:
            success, message, token, user = login_with_password(username, password)
            if not success:
                self.hide_loading_state()
                QMessageBox.warning(self, "验证失败", message)
                return
            if token:
                self.save_token(token)
            
            if self.remember_me.isChecked():
                self._save_credentials(username, password)
            else:
                self._clear_credentials()
            
            self.current_user = user
            
            self.loading_text.setText("登录成功！")
            if hasattr(self, 'sub_loading_text'):
                self.sub_loading_text.setText("即将进入...")
            
            QTimer.singleShot(300, self._finish_login)
            
        except Exception as e:
            self.hide_loading_state()
            QMessageBox.critical(self, "错误", str(e))
    
    def _finish_login(self):
        """完成登录，关闭窗口"""
        # 发出信号通知登录成功
        self.login_success.emit(self.current_user)
    
    def close_after_ready(self):
        """主窗口准备好后调用此方法关闭登录窗口"""
        if self._is_closing:
            return
        self._is_closing = True
        self.main_window_ready = True
        # 先清理动画，再关闭
        self._cleanup_animations()
        # 短暂延迟后关闭，让过渡更平滑
        QTimer.singleShot(100, self.accept)
    
    def _safe_close(self):
        """兜底关闭（如果主窗口创建失败等情况）"""
        if not self.main_window_ready and not self._is_closing:
            self._is_closing = True
            self._cleanup_animations()
            self.accept()
    
    def _cleanup_animations(self):
        """清理所有动画对象，防止 Windows 闪退"""
        # 停止 spinner 定时器
        if hasattr(self, 'spinner') and self.spinner:
            try:
                self.spinner.stop()
            except:
                pass
        
        # 停止所有记录的动画
        for anim in self._animations:
            try:
                if anim and anim.state() == QPropertyAnimation.State.Running:
                    anim.stop()
            except:
                pass
        self._animations.clear()
        
        # 停止入场动画
        if hasattr(self, 'opacity_anim') and self.opacity_anim:
            try:
                self.opacity_anim.stop()
            except:
                pass
        
        if hasattr(self, 'pos_anim') and self.pos_anim:
            try:
                self.pos_anim.stop()
            except:
                pass
        
        if hasattr(self, 'anim_group') and self.anim_group:
            try:
                self.anim_group.stop()
            except:
                pass
        
        # 停止 fade 动画
        if hasattr(self, 'fade_anim') and self.fade_anim:
            try:
                self.fade_anim.stop()
            except:
                pass
    
    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        self._cleanup_animations()
        super().closeEvent(event)
    
    def show_loading_state(self, message="正在验证..."):
        """显示加载遮罩 - 增强设计感"""
        # 禁用输入
        self.login_btn.setEnabled(False)
        self.username_input.input.setEnabled(False)
        self.password_input.input.setEnabled(False)
        
        # 创建遮罩层
        self.loading_overlay = QFrame(self.main_frame)
        self.loading_overlay.setGeometry(0, 0, self.main_frame.width(), self.main_frame.height())
        # 使用渐变背景，营造现代感
        self.loading_overlay.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(255, 255, 255, 0.98), 
                    stop:1 rgba(240, 249, 255, 0.95));
                border-radius: 16px;
            }
        """)
        
        # 初始透明度为0，用于渐入动画
        opacity_effect = QGraphicsOpacityEffect(self.loading_overlay)
        opacity_effect.setOpacity(0)
        self.loading_overlay.setGraphicsEffect(opacity_effect)
        
        # 遮罩内容布局
        overlay_layout = QVBoxLayout(self.loading_overlay)
        overlay_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        
        # 内容容器
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.setSpacing(25) # 增加间距
        
        # 1. 现代 Loading 动画
        self.spinner = ModernSpinner(
            size=72, 
            color=DesignToken.BRAND_PRIMARY
        )
        self.spinner.start()
        vbox.addWidget(self.spinner, 0, Qt.AlignmentFlag.AlignCenter)
        
        # 文字区域
        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setSpacing(8)
        text_layout.setContentsMargins(0, 0, 0, 0)
        
        # 2. 主标题
        self.loading_text = QLabel(message)
        self.loading_text.setFont(QFont(DesignToken.FONT_FAMILY, 15, QFont.Weight.Bold))
        self.loading_text.setStyleSheet(f"color: {DesignToken.TEXT_TITLE};")
        self.loading_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_layout.addWidget(self.loading_text)
        
        # 3. 副标题 (提示语)
        self.sub_loading_text = QLabel("正在连接安全服务器...")
        self.sub_loading_text.setFont(QFont(DesignToken.FONT_FAMILY, 11))
        self.sub_loading_text.setStyleSheet(f"color: {DesignToken.TEXT_BODY};")
        self.sub_loading_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_layout.addWidget(self.sub_loading_text)
        
        vbox.addWidget(text_container)
        
        overlay_layout.addWidget(container)
        
        self.loading_overlay.show()
        self.loading_overlay.raise_()
        
        # 启动渐入动画
        self.fade_anim = QPropertyAnimation(opacity_effect, b"opacity")
        self.fade_anim.setDuration(250)
        self.fade_anim.setStartValue(0)
        self.fade_anim.setEndValue(1)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animations.append(self.fade_anim)
        self.fade_anim.start()
    
    def hide_loading_state(self):
        """隐藏加载遮罩"""
        # 停止 spinner
        if hasattr(self, 'spinner') and self.spinner:
            try:
                self.spinner.stop()
            except:
                pass
        
        # 停止 fade 动画
        if hasattr(self, 'fade_anim') and self.fade_anim:
            try:
                self.fade_anim.stop()
            except:
                pass
        
        # 渐出动画
        if hasattr(self, 'loading_overlay') and self.loading_overlay:
            try:
                self.loading_overlay.hide()
                self.loading_overlay.deleteLater()
            except:
                pass
        
        # 恢复输入
        try:
            self.login_btn.setEnabled(True)
            self.username_input.input.setEnabled(True)
            self.password_input.input.setEnabled(True)
        except:
            pass

    def shake_window(self):
        original_pos = self.pos()
        x = original_pos.x()
        y = original_pos.y()
        for i in range(3):
            QTimer.singleShot(i * 50, lambda: self.move(x + 5, y))
            QTimer.singleShot(i * 50 + 25, lambda: self.move(x - 5, y))
        QTimer.singleShot(150, lambda: self.move(x, y))
    
    def save_token(self, token: str):
        try:
            auth_dir = Path.home() / '.auto-form-filler'
            auth_dir.mkdir(exist_ok=True)
            (auth_dir / '.token').write_text(token)
        except: pass
    
    def get_current_user(self):
        return self.current_user
