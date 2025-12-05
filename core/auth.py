"""
JWT 认证模块
处理 Token 生成、验证和设备管理
"""
import jwt
import uuid
import platform
import socket
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from database.models import User, Device, SystemConfig
import config


# JWT 配置
JWT_SECRET_KEY = config.JWT_SECRET_KEY if hasattr(config, 'JWT_SECRET_KEY') else 'your-secret-key-change-in-production'
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_DAYS = 30  # Token 过期时间：30天
# MAX_DEVICES_PER_USER = 2  # 每个用户最多绑定设备数 - 已移至 SystemConfig 动态获取


def get_device_id() -> str:
    """
    获取设备唯一标识
    基于MAC地址生成设备ID
    """
    try:
        # 获取MAC地址
        mac = uuid.getnode()
        # 生成设备ID
        device_id = f"{platform.system()}_{hex(mac)}"
        return device_id
    except:
        # 如果获取失败，使用随机UUID
        return str(uuid.uuid4())


def get_device_info() -> Dict:
    """获取设备信息"""
    return {
        'device_id': get_device_id(),
        'device_name': platform.node() or socket.gethostname(),
        'device_type': platform.system(),  # macOS, Windows, Linux
    }


def generate_token(user: User, device_info: Dict) -> str:
    """
    生成 JWT Token
    
    Args:
        user: 用户对象
        device_info: 设备信息
        
    Returns:
        JWT token 字符串
    """
    payload = {
        'user_id': str(user.id),
        'username': user.username,
        'role': user.role,
        'device_id': device_info['device_id'],
        'exp': datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS),
        'iat': datetime.utcnow()
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token: str) -> Optional[Dict]:
    """
    验证 JWT Token
    
    Args:
        token: JWT token 字符串
        
    Returns:
        解码后的 payload，如果验证失败返回 None
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        print("❌ Token 已过期")
        return None
    except jwt.InvalidTokenError as e:
        print(f"❌ Token 无效: {e}")
        return None


def check_device_limit(user: User, device_id: str) -> Tuple[bool, str]:
    """
    检查设备数量限制
    
    Args:
        user: 用户对象
        device_id: 设备ID
        
    Returns:
        (是否允许登录, 消息)
    """
    # 查询用户的所有激活设备
    active_devices = Device.objects(user=user, is_active=True)
    
    # 检查当前设备是否已绑定
    current_device = Device.objects(user=user, device_id=device_id, is_active=True).first()
    if current_device:
        # 当前设备已绑定，允许登录
        return True, "设备已绑定"
    
    # 检查是否超过设备数量限制
    max_devices = int(SystemConfig.get('MAX_DEVICES_PER_USER', '2'))
    if active_devices.count() >= max_devices:
        return False, f"该账号已达到最大设备数量限制（{max_devices}台），请在后台解绑其他设备后重试"
    
    return True, "可以绑定新设备"


def bind_device(user: User, device_info: Dict, ip_address: str = None) -> Device:
    """
    绑定设备
    
    Args:
        user: 用户对象
        device_info: 设备信息
        ip_address: IP地址
        
    Returns:
        Device 对象
    """
    device_id = device_info['device_id']
    
    # 检查设备是否已存在
    device = Device.objects(user=user, device_id=device_id).first()
    
    if device:
        # 更新设备信息
        device.device_name = device_info.get('device_name', device.device_name)
        device.device_type = device_info.get('device_type', device.device_type)
        device.last_ip = ip_address or device.last_ip
        device.last_login = datetime.now()
        device.is_active = True
        device.save()
    else:
        # 创建新设备
        device = Device(
            user=user,
            device_id=device_id,
            device_name=device_info.get('device_name', 'Unknown Device'),
            device_type=device_info.get('device_type', 'Unknown'),
            last_ip=ip_address,
            last_login=datetime.now(),
            is_active=True
        )
        device.save()
    
    return device


def unbind_device(device_id: str) -> bool:
    """
    解绑设备
    
    Args:
        device_id: 设备ID（MongoDB ObjectId）
        
    Returns:
        是否成功
    """
    try:
        device = Device.objects(id=device_id).first()
        if device:
            device.is_active = False
            device.save()
            return True
        return False
    except Exception as e:
        print(f"❌ 解绑设备失败: {e}")
        return False


def login_with_password(username: str, password: str) -> Tuple[bool, str, Optional[str], Optional[User]]:
    """
    使用用户名密码登录
    
    Args:
        username: 用户名
        password: 密码
        
    Returns:
        (是否成功, 消息, token, 用户对象)
    """
    try:
        # 查找用户
        user = User.objects(username=username).first()
        if not user:
            return False, "用户名或密码错误", None, None
        
        # 验证密码
        if not user.check_password(password):
            return False, "用户名或密码错误", None, None
        
        # 检查用户是否被禁用
        if not user.is_active:
            return False, "账号已被禁用，请联系管理员", None, None
        
        # 检查账号是否过期（管理员除外）
        if user.role != 'admin' and user.expire_time:
            if datetime.now() > user.expire_time:
                expire_str = user.expire_time.strftime('%Y-%m-%d %H:%M')
                return False, f"您的账号已于 {expire_str} 过期，请联系平台续费", None, None
        
        # 检查使用次数是否超限（管理员除外）
        if user.role != 'admin' and user.max_usage_count > -1:
            if user.usage_count >= user.max_usage_count:
                return False, f"您的使用次数已用尽（{user.usage_count}/{user.max_usage_count}次），请联系平台续费", None, None
        
        # 获取设备信息
        device_info = get_device_info()
        
        # 检查设备限制
        can_login, message = check_device_limit(user, device_info['device_id'])
        if not can_login:
            return False, message, None, None
        
        # 绑定设备
        bind_device(user, device_info)
        
        # 生成 Token
        token = generate_token(user, device_info)
        
        # 更新最后登录时间
        user.last_login = datetime.now()
        user.save()
        
        return True, "登录成功", token, user
        
    except Exception as e:
        return False, f"登录失败: {str(e)}", None, None


def login_with_token(token: str) -> Tuple[bool, str, Optional[User]]:
    """
    使用 Token 登录（自动登录）
    
    Args:
        token: JWT token
        
    Returns:
        (是否成功, 消息, 用户对象)
    """
    try:
        # 验证 Token
        payload = verify_token(token)
        if not payload:
            return False, "Token 无效或已过期", None
        
        # 获取用户
        user_id = payload.get('user_id')
        device_id = payload.get('device_id')
        
        user = User.objects(id=user_id).first()
        if not user:
            return False, "用户不存在", None
        
        # 检查用户是否被禁用
        if not user.is_active:
            return False, "账号已被禁用", None
        
        # 检查账号是否过期（管理员除外）
        if user.role != 'admin' and user.expire_time:
            if datetime.now() > user.expire_time:
                expire_str = user.expire_time.strftime('%Y-%m-%d %H:%M')
                return False, f"您的账号已于 {expire_str} 过期，请联系平台续费", None
        
        # 检查使用次数是否超限（管理员除外）
        if user.role != 'admin' and user.max_usage_count > -1:
            if user.usage_count >= user.max_usage_count:
                return False, f"您的使用次数已用尽（{user.usage_count}/{user.max_usage_count}次），请联系平台续费", None
        
        # 检查设备是否仍然绑定
        device = Device.objects(user=user, device_id=device_id, is_active=True).first()
        if not device:
            return False, "设备已解绑，请重新登录", None
        
        # 更新设备最后登录时间
        device.last_login = datetime.now()
        device.save()
        
        # 更新用户最后登录时间
        user.last_login = datetime.now()
        user.save()
        
        return True, "自动登录成功", user
        
    except Exception as e:
        return False, f"自动登录失败: {str(e)}", None


def check_user_can_use(user: User) -> Tuple[bool, str]:
    """
    检查用户是否可以继续使用软件（用于填写表单前的检查）
    
    Args:
        user: 用户对象
        
    Returns:
        (是否可用, 消息)
    """
    # 管理员无限制
    if user.role == 'admin':
        return True, "管理员无限制"
    
    # 检查账号是否过期
    if user.expire_time and datetime.now() > user.expire_time:
        expire_str = user.expire_time.strftime('%Y-%m-%d %H:%M')
        return False, f"您的账号已于 {expire_str} 过期，请联系平台续费"
    
    # 检查使用次数
    if user.max_usage_count > -1 and user.usage_count >= user.max_usage_count:
        return False, f"您的使用次数已用尽（{user.usage_count}/{user.max_usage_count}次），请联系平台续费"
    
    return True, "可以使用"


def increment_usage_count(user: User) -> bool:
    """
    增加用户使用次数
    
    Args:
        user: 用户对象
        
    Returns:
        是否成功
    """
    try:
        user.reload()  # 重新加载确保数据最新
        user.usage_count = (user.usage_count or 0) + 1
        user.save()
        return True
    except Exception as e:
        print(f"❌ 增加使用次数失败: {e}")
        return False


def get_user_status_info(user: User) -> dict:
    """
    获取用户状态信息（用于前端展示）
    
    Args:
        user: 用户对象
        
    Returns:
        状态信息字典
    """
    info = {
        'username': user.username,
        'role': user.role,
        'is_admin': user.role == 'admin',
        'expire_time': None,
        'expire_time_str': '永不过期',
        'is_expired': False,
        'days_remaining': None,
        'usage_count': user.usage_count or 0,
        'max_usage_count': user.max_usage_count or -1,
        'usage_unlimited': (user.max_usage_count or -1) == -1,
        'usage_exhausted': False
    }
    
    # 管理员特殊处理
    if user.role == 'admin':
        info['expire_time_str'] = '永不过期'
        info['usage_unlimited'] = True
        return info
    
    # 过期时间
    if user.expire_time:
        info['expire_time'] = user.expire_time
        info['expire_time_str'] = user.expire_time.strftime('%Y-%m-%d %H:%M')
        
        if datetime.now() > user.expire_time:
            info['is_expired'] = True
            info['days_remaining'] = 0
        else:
            delta = user.expire_time - datetime.now()
            info['days_remaining'] = delta.days
    
    # 使用次数
    if user.max_usage_count and user.max_usage_count > -1:
        info['usage_unlimited'] = False
        if user.usage_count >= user.max_usage_count:
            info['usage_exhausted'] = True
    
    return info


def get_user_devices(user: User) -> list:
    """
    获取用户的所有设备
    
    Args:
        user: 用户对象
        
    Returns:
        设备列表
    """
    devices = Device.objects(user=user).order_by('-last_login')
    return [device.to_dict() for device in devices]


def clear_token() -> bool:
    """
    清除本地保存的 Token（用于退出登录/切换账号）
    
    Returns:
        是否成功清除
    """
    try:
        from pathlib import Path
        
        # 获取 token 文件路径
        auth_dir = Path.home() / '.auto-form-filler'
        token_file = auth_dir / '.token'
        
        # 如果文件存在，则删除
        if token_file.exists():
            token_file.unlink()
            print("✅ Token 已清除")
            return True
        else:
            print("ℹ️ Token 文件不存在")
            return True
            
    except Exception as e:
        print(f"⚠️ 清除 Token 失败: {e}")
        return False

