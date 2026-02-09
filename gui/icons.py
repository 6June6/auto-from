"""
图标管理器
使用 QtAwesome 提供现代化图标
Windows 字体加载失败时自动降级为 emoji 图标
"""
import qtawesome as qta
from PyQt6.QtGui import QIcon, QColor, QPixmap, QPainter, QFont
from PyQt6.QtCore import QSize, Qt, QRect

# FontAwesome 图标名 → emoji 降级映射
_EMOJI_FALLBACK = {
    'fa5s.plus': '+', 'fa5s.plus-circle': '⊕',
    'fa5s.edit': '✎', 'fa5s.trash': '✕', 'fa5s.trash-alt': '✕',
    'fa5s.check': '✓', 'fa5s.check-circle': '✓',
    'fa5s.times': '✕', 'fa5s.times-circle': '✕',
    'fa5s.search': '⌕', 'fa5s.sync-alt': '↻', 'fa5s.sync': '↻',
    'fa5s.cog': '⚙', 'fa5s.magic': '★',
    'fa5s.home': '⌂', 'fa5s.user': '☺', 'fa5s.users': '☺',
    'fa5s.link': '🔗', 'fa5s.unlink': '⊘',
    'fa5s.bell': '♪', 'fa5s.bullhorn': '♪',
    'fa5s.fire': '✦',
    'fa5s.info-circle': 'ℹ', 'fa5s.exclamation-triangle': '⚠',
    'fa5s.exclamation-circle': '!', 'fa5s.question-circle': '?',
    'fa5s.chevron-down': '▾', 'fa5s.chevron-up': '▴',
    'fa5s.chevron-left': '◂', 'fa5s.chevron-right': '▸',
    'fa5s.arrow-up': '↑', 'fa5s.arrow-down': '↓',
    'fa5s.arrow-left': '←', 'fa5s.arrow-right': '→',
    'fa5s.folder': '📁', 'fa5s.folder-open': '📂', 'fa5s.folder-plus': '📁',
    'fa5s.file': '📄', 'fa5s.file-alt': '📄',
    'fa5s.copy': '⧉', 'fa5s.paste': '⎗',
    'fa5s.save': '💾', 'fa5s.download': '↓', 'fa5s.upload': '↑',
    'fa5s.play': '▶', 'fa5s.stop': '■', 'fa5s.pause': '❚❚',
    'fa5s.id-card': '☐', 'fa5s.address-card': '☐',
    'fa5s.bars': '☰', 'fa5s.list': '≡', 'fa5s.th': '⊞', 'fa5s.th-large': '⊞',
    'fa5s.ellipsis-h': '⋯', 'fa5s.ellipsis-v': '⋮',
    'fa5s.external-link-alt': '↗',
    'fa5s.eye': '◉', 'fa5s.eye-slash': '◎',
    'fa5s.lock': '🔒', 'fa5s.unlock': '🔓',
    'fa5s.sign-out-alt': '→', 'fa5s.sign-in-alt': '←',
    'fa5s.spinner': '◌', 'fa5s.tag': '⚑', 'fa5s.tags': '⚑',
    'fa5s.calendar': '📅', 'fa5s.clock': '◷',
    'fa5s.robot': '⚙', 'fa5s.database': '⊟',
    'fa5s.plug': '⚡', 'fa5s.toggle-on': '●', 'fa5s.toggle-off': '○',
    'fa5s.broadcast-tower': '📡', 'fa5s.clipboard-check': '☑',
    'fa5s.clipboard-list': '☐', 'fa5s.circle': '●',
    'fa5s.chart-bar': '▊', 'fa5s.grip-vertical': '⋮', 'fa5s.arrows-alt': '⇔',
}


def _create_emoji_icon(name, color='#666666'):
    """用 emoji/符号创建降级图标"""
    text = _EMOJI_FALLBACK.get(name, '•')
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setFont(QFont('Segoe UI Symbol', 28))
    if color:
        c = color if isinstance(color, str) else color.name() if isinstance(color, QColor) else '#666666'
        painter.setPen(QColor(c))
    painter.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, text)
    painter.end()
    return QIcon(pixmap)


def safe_qta_icon(name, **kwargs):
    """安全的 qtawesome 图标调用，字体加载失败时用 emoji 降级"""
    try:
        return qta.icon(name, **kwargs)
    except Exception:
        color = kwargs.get('color', '#666666')
        return _create_emoji_icon(name, color)


class Icons:
    """图标管理类 - 集中管理所有图标"""
    
    # 默认图标大小
    DEFAULT_SIZE = 16
    
    # 颜色定义
    COLORS = {
        'primary': '#007AFF',
        'success': '#34C759',
        'warning': '#FF9500',
        'danger': '#FF3B30',
        'info': '#5856D6',
        'dark': '#1D1D1F',
        'gray': '#6E6E73',
        'light': '#FFFFFF',
    }
    
    @staticmethod
    def get(name: str, color: str = None, size: int = None) -> QIcon:
        """
        获取图标
        
        Args:
            name: 图标名称（使用 FontAwesome 5 图标名）
            color: 图标颜色（可选）
            size: 图标大小（可选）
        
        Returns:
            QIcon 对象
        """
        if size is None:
            size = Icons.DEFAULT_SIZE
            
        options = {'scale_factor': 1.0}
        
        if color:
            # 如果是预定义颜色名，转换为实际颜色值
            if color in Icons.COLORS:
                color = Icons.COLORS[color]
            options['color'] = QColor(color)
        
        try:
            return safe_qta_icon(name, **options)
        except Exception as e:
            print(f"⚠️ 图标加载失败: {name}, 错误: {e}")
            # 返回空图标
            return QIcon()
    
    # ===== 常用图标快捷方法 =====
    
    @staticmethod
    def add(color: str = 'primary') -> QIcon:
        """添加/加号图标"""
        return Icons.get('fa5s.plus', color)
    
    @staticmethod
    def plus_circle(color: str = 'primary') -> QIcon:
        """圆形加号图标"""
        return Icons.get('fa5s.plus-circle', color)
    
    @staticmethod
    def edit(color: str = 'primary') -> QIcon:
        """编辑图标"""
        return Icons.get('fa5s.edit', color)
    
    @staticmethod
    def delete(color: str = 'danger') -> QIcon:
        """删除/垃圾桶图标"""
        return Icons.get('fa5s.trash-alt', color)
    
    @staticmethod
    def trash(color: str = 'danger') -> QIcon:
        """垃圾桶图标（别名）"""
        return Icons.delete(color)
    
    @staticmethod
    def drag(color: str = 'gray') -> QIcon:
        """拖拽排序图标"""
        return Icons.get('fa5s.grip-vertical', color)
    
    @staticmethod
    def move(color: str = 'gray') -> QIcon:
        """移动图标"""
        return Icons.get('fa5s.arrows-alt', color)
    
    @staticmethod
    def check(color: str = 'success') -> QIcon:
        """勾选/确认图标"""
        return Icons.get('fa5s.check', color)
    
    @staticmethod
    def check_circle(color: str = 'success') -> QIcon:
        """圆形勾选图标"""
        return Icons.get('fa5s.check-circle', color)
    
    @staticmethod
    def close(color: str = 'gray') -> QIcon:
        """关闭图标"""
        return Icons.get('fa5s.times', color)
    
    @staticmethod
    def close_circle(color: str = 'danger') -> QIcon:
        """圆形关闭图标"""
        return Icons.get('fa5s.times-circle', color)
    
    @staticmethod
    def search(color: str = 'gray') -> QIcon:
        """搜索图标"""
        return Icons.get('fa5s.search', color)
    
    @staticmethod
    def refresh(color: str = 'primary') -> QIcon:
        """刷新图标"""
        return Icons.get('fa5s.sync-alt', color)
    
    @staticmethod
    def settings(color: str = 'gray') -> QIcon:
        """设置图标"""
        return Icons.get('fa5s.cog', color)
    
    @staticmethod
    def user(color: str = 'gray') -> QIcon:
        """用户图标"""
        return Icons.get('fa5s.user', color)
    
    @staticmethod
    def users(color: str = 'gray') -> QIcon:
        """多用户图标"""
        return Icons.get('fa5s.users', color)
    
    @staticmethod
    def link(color: str = 'primary') -> QIcon:
        """链接图标"""
        return Icons.get('fa5s.link', color)
    
    @staticmethod
    def unlink(color: str = 'gray') -> QIcon:
        """断开链接图标"""
        return Icons.get('fa5s.unlink', color)
    
    @staticmethod
    def card(color: str = 'primary') -> QIcon:
        """名片/卡片图标"""
        return Icons.get('fa5s.id-card', color)
    
    @staticmethod
    def folder(color: str = 'warning') -> QIcon:
        """文件夹图标"""
        return Icons.get('fa5s.folder', color)
    
    @staticmethod
    def folder_open(color: str = 'warning') -> QIcon:
        """打开的文件夹图标"""
        return Icons.get('fa5s.folder-open', color)
    
    @staticmethod
    def file(color: str = 'gray') -> QIcon:
        """文件图标"""
        return Icons.get('fa5s.file', color)
    
    @staticmethod
    def copy(color: str = 'gray') -> QIcon:
        """复制图标"""
        return Icons.get('fa5s.copy', color)
    
    @staticmethod
    def paste(color: str = 'gray') -> QIcon:
        """粘贴图标"""
        return Icons.get('fa5s.paste', color)
    
    @staticmethod
    def save(color: str = 'primary') -> QIcon:
        """保存图标"""
        return Icons.get('fa5s.save', color)
    
    @staticmethod
    def download(color: str = 'primary') -> QIcon:
        """下载图标"""
        return Icons.get('fa5s.download', color)
    
    @staticmethod
    def upload(color: str = 'primary') -> QIcon:
        """上传图标"""
        return Icons.get('fa5s.upload', color)
    
    @staticmethod
    def play(color: str = 'success') -> QIcon:
        """播放/开始图标"""
        return Icons.get('fa5s.play', color)
    
    @staticmethod
    def stop(color: str = 'danger') -> QIcon:
        """停止图标"""
        return Icons.get('fa5s.stop', color)
    
    @staticmethod
    def pause(color: str = 'warning') -> QIcon:
        """暂停图标"""
        return Icons.get('fa5s.pause', color)
    
    @staticmethod
    def arrow_up(color: str = 'gray') -> QIcon:
        """向上箭头"""
        return Icons.get('fa5s.arrow-up', color)
    
    @staticmethod
    def arrow_down(color: str = 'gray') -> QIcon:
        """向下箭头"""
        return Icons.get('fa5s.arrow-down', color)
    
    @staticmethod
    def arrow_left(color: str = 'gray') -> QIcon:
        """向左箭头"""
        return Icons.get('fa5s.arrow-left', color)
    
    @staticmethod
    def arrow_right(color: str = 'gray') -> QIcon:
        """向右箭头"""
        return Icons.get('fa5s.arrow-right', color)
    
    @staticmethod
    def chevron_up(color: str = 'gray') -> QIcon:
        """向上尖角"""
        return Icons.get('fa5s.chevron-up', color)
    
    @staticmethod
    def chevron_down(color: str = 'gray') -> QIcon:
        """向下尖角"""
        return Icons.get('fa5s.chevron-down', color)
    
    @staticmethod
    def chevron_left(color: str = 'gray') -> QIcon:
        """向左尖角"""
        return Icons.get('fa5s.chevron-left', color)
    
    @staticmethod
    def chevron_right(color: str = 'gray') -> QIcon:
        """向右尖角"""
        return Icons.get('fa5s.chevron-right', color)
    
    @staticmethod
    def bell(color: str = 'warning') -> QIcon:
        """铃铛/通知图标"""
        return Icons.get('fa5s.bell', color)
    
    @staticmethod
    def info(color: str = 'info') -> QIcon:
        """信息图标"""
        return Icons.get('fa5s.info-circle', color)
    
    @staticmethod
    def warning(color: str = 'warning') -> QIcon:
        """警告图标"""
        return Icons.get('fa5s.exclamation-triangle', color)
    
    @staticmethod
    def error(color: str = 'danger') -> QIcon:
        """错误图标"""
        return Icons.get('fa5s.exclamation-circle', color)
    
    @staticmethod
    def question(color: str = 'info') -> QIcon:
        """问号图标"""
        return Icons.get('fa5s.question-circle', color)
    
    @staticmethod
    def home(color: str = 'gray') -> QIcon:
        """首页图标"""
        return Icons.get('fa5s.home', color)
    
    @staticmethod
    def chart(color: str = 'info') -> QIcon:
        """图表图标"""
        return Icons.get('fa5s.chart-bar', color)
    
    @staticmethod
    def list(color: str = 'gray') -> QIcon:
        """列表图标"""
        return Icons.get('fa5s.list', color)
    
    @staticmethod
    def grid(color: str = 'gray') -> QIcon:
        """网格图标"""
        return Icons.get('fa5s.th', color)
    
    @staticmethod
    def menu(color: str = 'gray') -> QIcon:
        """菜单图标"""
        return Icons.get('fa5s.bars', color)
    
    @staticmethod
    def ellipsis_h(color: str = 'gray') -> QIcon:
        """水平省略号图标"""
        return Icons.get('fa5s.ellipsis-h', color)
    
    @staticmethod
    def ellipsis_v(color: str = 'gray') -> QIcon:
        """垂直省略号图标"""
        return Icons.get('fa5s.ellipsis-v', color)
    
    @staticmethod
    def external_link(color: str = 'primary') -> QIcon:
        """外部链接图标"""
        return Icons.get('fa5s.external-link-alt', color)
    
    @staticmethod
    def eye(color: str = 'gray') -> QIcon:
        """眼睛/查看图标"""
        return Icons.get('fa5s.eye', color)
    
    @staticmethod
    def eye_slash(color: str = 'gray') -> QIcon:
        """隐藏图标"""
        return Icons.get('fa5s.eye-slash', color)
    
    @staticmethod
    def lock(color: str = 'gray') -> QIcon:
        """锁定图标"""
        return Icons.get('fa5s.lock', color)
    
    @staticmethod
    def unlock(color: str = 'success') -> QIcon:
        """解锁图标"""
        return Icons.get('fa5s.unlock', color)
    
    @staticmethod
    def sign_out(color: str = 'gray') -> QIcon:
        """登出图标"""
        return Icons.get('fa5s.sign-out-alt', color)
    
    @staticmethod
    def sign_in(color: str = 'primary') -> QIcon:
        """登入图标"""
        return Icons.get('fa5s.sign-in-alt', color)
    
    @staticmethod
    def spinner(color: str = 'primary') -> QIcon:
        """加载中图标"""
        return Icons.get('fa5s.spinner', color)
    
    @staticmethod
    def sync(color: str = 'primary') -> QIcon:
        """同步图标"""
        return Icons.get('fa5s.sync', color)
    
    @staticmethod
    def tag(color: str = 'info') -> QIcon:
        """标签图标"""
        return Icons.get('fa5s.tag', color)
    
    @staticmethod
    def tags(color: str = 'info') -> QIcon:
        """多标签图标"""
        return Icons.get('fa5s.tags', color)
    
    @staticmethod
    def calendar(color: str = 'gray') -> QIcon:
        """日历图标"""
        return Icons.get('fa5s.calendar', color)
    
    @staticmethod
    def clock(color: str = 'gray') -> QIcon:
        """时钟图标"""
        return Icons.get('fa5s.clock', color)
    
    @staticmethod
    def magic(color: str = 'info') -> QIcon:
        """魔法棒图标"""
        return Icons.get('fa5s.magic', color)
    
    @staticmethod
    def robot(color: str = 'primary') -> QIcon:
        """机器人图标"""
        return Icons.get('fa5s.robot', color)
    
    @staticmethod
    def form(color: str = 'primary') -> QIcon:
        """表单图标"""
        return Icons.get('fa5s.file-alt', color)
    
    @staticmethod
    def database(color: str = 'gray') -> QIcon:
        """数据库图标"""
        return Icons.get('fa5s.database', color)
    
    @staticmethod
    def plug(color: str = 'success') -> QIcon:
        """插件/连接图标"""
        return Icons.get('fa5s.plug', color)
    
    @staticmethod
    def toggle_on(color: str = 'success') -> QIcon:
        """开关开启图标"""
        return Icons.get('fa5s.toggle-on', color)
    
    @staticmethod
    def toggle_off(color: str = 'gray') -> QIcon:
        """开关关闭图标"""
        return Icons.get('fa5s.toggle-off', color)

    @staticmethod
    def broadcast(color: str = 'primary') -> QIcon:
        """广播/通告图标"""
        return Icons.get('fa5s.broadcast-tower', color)
    
    @staticmethod
    def verify(color: str = 'primary') -> QIcon:
        """审核/验证图标"""
        return Icons.get('fa5s.clipboard-check', color)
        
    @staticmethod
    def circle(color: str = 'gray') -> QIcon:
        """圆形图标"""
        return Icons.get('fa5s.circle', color)


# 创建全局图标实例，方便直接使用
icons = Icons()
