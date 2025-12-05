"""
macOS 风格样式定义
扁平化设计 + Big Sur 风格
"""

# macOS 配色方案 - 升级版
COLORS = {
    # 主色调 - 现代渐变蓝
    'primary': '#007AFF',  # 系统蓝
    'primary_light': '#4DA3FF',  # 浅蓝
    'primary_dark': '#0051D5',   # 深蓝
    
    # 状态色
    'success': '#34C759',  # 系统绿
    'success_light': '#5FD87F',
    'warning': '#FF9500',  # 系统橙
    'warning_light': '#FFB340',
    'danger': '#FF3B30',   # 系统红
    'danger_light': '#FF6259',
    'info': '#5856D6',     # 系统紫
    'info_light': '#7B79DC',
    
    # 中性色
    'background': '#F5F7FA',  # 浅灰背景
    'background_dark': '#E8EAED',
    'surface': '#FFFFFF',      # 卡片白色
    'surface_hover': '#FAFBFC',
    'card': '#FFFFFF',
    'card_shadow': 'rgba(0, 0, 0, 0.08)',
    
    # 文字色
    'text_primary': '#1D1D1F',
    'text_secondary': '#6E6E73',
    'text_tertiary': '#9E9E9E',
    'text_light': '#FFFFFF',
    
    # 边框和分割线
    'border': '#E5E5EA',
    'border_light': '#F0F0F5',
    'divider': '#E8E8ED',
    
    # 强调色
    'accent_blue': '#007AFF',
    'accent_purple': '#AF52DE',
    'accent_pink': '#FF2D55',
    'accent_green': '#34C759',
    'accent_orange': '#FF9500',
    'accent_yellow': '#FFCC00',
    'accent_teal': '#64D2FF',
    'accent_indigo': '#5E5CE6',
}

# 全局样式 - 现代化设计
GLOBAL_STYLE = f"""
QWidget {{
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", "PingFang SC", "Microsoft YaHei", sans-serif;
    font-size: 14px;
    color: {COLORS['text_primary']};
    letter-spacing: -0.2px;
}}

QMainWindow, QDialog {{
    background-color: {COLORS['background']};
}}

/* 按钮样式 - 现代化渐变 */
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 {COLORS['primary']}, 
                                stop:1 {COLORS['primary_dark']});
    color: white;
    border: none;
    border-radius: 10px;
    padding: 12px 24px;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.3px;
}}

QPushButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 {COLORS['primary_light']}, 
                                stop:1 {COLORS['primary']});
}}

QPushButton:pressed {{
    background: {COLORS['primary_dark']};
    padding-top: 13px;
    padding-bottom: 11px;
}}

QPushButton:disabled {{
    background: {COLORS['border']};
    color: {COLORS['text_tertiary']};
}}

/* 列表样式 - 卡片式设计 */
QListWidget {{
    background-color: {COLORS['surface']};
    border: none;
    border-radius: 12px;
    padding: 6px;
    outline: none;
}}

QListWidget::item {{
    border-radius: 8px;
    padding: 12px 14px;
    margin: 3px 0;
    color: {COLORS['text_primary']};
    background-color: {COLORS['surface_hover']};
    font-size: 13px;
    font-weight: 500;
}}

QListWidget::item:selected {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 {COLORS['primary']}, 
                                stop:1 {COLORS['primary_light']});
    color: white;
    font-weight: 600;
}}

QListWidget::item:hover {{
    background-color: {COLORS['border_light']};
}}

QListWidget::item:selected:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 {COLORS['primary_light']}, 
                                stop:1 {COLORS['primary']});
    color: white;
}}

/* 表格样式 - 现代化 */
QTableWidget {{
    background-color: {COLORS['surface']};
    border: none;
    border-radius: 12px;
    gridline-color: {COLORS['border_light']};
}}

QTableWidget::item {{
    padding: 12px 10px;
    color: {COLORS['text_primary']};
}}

QTableWidget::item:selected {{
    background-color: {COLORS['primary_light']};
    color: white;
}}

QTableWidget::item:hover {{
    background-color: {COLORS['surface_hover']};
}}

QHeaderView::section {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 {COLORS['background']}, 
                                stop:1 {COLORS['background_dark']});
    color: {COLORS['text_secondary']};
    border: none;
    border-bottom: 2px solid {COLORS['border']};
    padding: 14px 10px;
    font-weight: 700;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* 滚动条样式 - macOS 风格 */
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 12px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {COLORS['text_tertiary']};
    border-radius: 6px;
    min-height: 30px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLORS['text_secondary']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    border: none;
    background: transparent;
    height: 12px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background: {COLORS['text_tertiary']};
    border-radius: 6px;
    min-width: 30px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {COLORS['text_secondary']};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

/* 输入框样式 - 现代化 */
QLineEdit, QTextEdit {{
    background-color: {COLORS['surface']};
    border: 2px solid {COLORS['border']};
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 14px;
    color: {COLORS['text_primary']};
    selection-background-color: {COLORS['primary_light']};
}}

QLineEdit:focus, QTextEdit:focus {{
    border: 2px solid {COLORS['primary']};
    background-color: {COLORS['surface_hover']};
}}

QLineEdit:hover, QTextEdit:hover {{
    border: 2px solid {COLORS['border_light']};
}}

/* 标签样式 */
QLabel {{
    color: {COLORS['text_primary']};
    background: transparent;
}}

/* 分组框样式 - 卡片化 */
QGroupBox {{
    background-color: {COLORS['surface']};
    border: none;
    border-radius: 12px;
    margin-top: 16px;
    padding: 16px;
    font-weight: 600;
    color: {COLORS['text_primary']};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 12px;
    background: transparent;
    color: {COLORS['text_primary']};
    font-size: 15px;
    font-weight: 700;
}}

/* Frame 样式 - 卡片阴影 */
QFrame {{
    background-color: {COLORS['surface']};
    border-radius: 12px;
    border: none;
}}

/* 消息框样式 */
QMessageBox {{
    background-color: {COLORS['surface']};
}}

QMessageBox QPushButton {{
    min-width: 80px;
}}
"""

# 特殊按钮样式
def get_card_button_style(color):
    """卡片式按钮"""
    return f"""
    QPushButton {{
        background-color: {COLORS['card']};
        color: {COLORS['text_primary']};
        border: 2px solid {color};
        border-radius: 12px;
        padding: 20px;
        text-align: left;
        font-size: 16px;
        font-weight: 600;
    }}
    
    QPushButton:hover {{
        background-color: {color};
        color: white;
    }}
    
    QPushButton:pressed {{
        background-color: {color};
    }}
    """

def get_toolbar_button_style():
    """工具栏按钮样式"""
    return f"""
    QPushButton {{
        background-color: {COLORS['card']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 13px;
        font-weight: 500;
    }}
    
    QPushButton:hover {{
        background-color: {COLORS['surface']};
        border-color: {COLORS['primary']};
    }}
    
    QPushButton:pressed {{
        background-color: {COLORS['divider']};
    }}
    """

def get_stats_card_style():
    """统计卡片样式 - 带阴影的现代卡片"""
    return f"""
    QFrame {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 {COLORS['surface']}, 
                                    stop:1 {COLORS['surface_hover']});
        border: none;
        border-radius: 16px;
        padding: 24px;
    }}
    """

def get_title_style(size=24):
    """标题样式"""
    return f"""
    QLabel {{
        color: {COLORS['text_primary']};
        font-size: {size}px;
        font-weight: 700;
        letter-spacing: -0.5px;
    }}
    """

def get_subtitle_style():
    """副标题样式"""
    return f"""
    QLabel {{
        color: {COLORS['text_secondary']};
        font-size: 12px;
        font-weight: 400;
    }}
    """

def get_panel_style():
    """面板样式"""
    return f"""
    QWidget {{
        background-color: {COLORS['card']};
        border-radius: 12px;
    }}
    """

def get_config_panel_style():
    """配置面板样式 - 温暖色调"""
    return f"""
    QFrame {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #FFFBF0, 
                                    stop:1 #FFF9E6);
        border: none;
        border-radius: 14px;
    }}
    """

def get_modern_card_style(color=None):
    """现代卡片样式 - 带渐变和圆角"""
    bg_color = color if color else COLORS['surface']
    return f"""
    QFrame {{
        background-color: {bg_color};
        border: none;
        border-radius: 16px;
        padding: 20px;
    }}
    """

def get_icon_button_style(color):
    """图标按钮样式 - 圆形或方形"""
    return f"""
    QPushButton {{
        background-color: {color};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 12px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        opacity: 0.9;
    }}
    QPushButton:pressed {{
        opacity: 0.7;
    }}
    """

