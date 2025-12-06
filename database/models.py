"""
数据库模型定义
使用 MongoEngine ODM
"""
from mongoengine import (
    Document, EmbeddedDocument, 
    StringField, IntField, BooleanField, DateTimeField, 
    EmbeddedDocumentListField, ReferenceField,
    connect
)
from datetime import datetime
import hashlib
import config


# 连接 MongoDB
def init_database():
    """初始化数据库连接"""
    try:
        print("🔧 正在连接 MongoDB...")
        
        # 连接配置
        connection_config = {
            'db': config.MONGODB_DB_NAME,
            'host': config.MONGODB_URI,
            'serverSelectionTimeoutMS': 5000,  # 5秒超时
            'connectTimeoutMS': 10000,  # 10秒连接超时
        }
        
        # 连接数据库
        conn = connect(**connection_config)
        
        # 禁用自动创建索引（因为权限限制）
        # 索引需要在 MongoDB 控制台手动创建
        import mongoengine
        mongoengine.connection.get_db().command({'buildInfo': 1})  # 测试连接
        
        print(f"✅ MongoDB 连接成功！数据库: {config.MONGODB_DB_NAME}")
        
        # 创建默认管理员账号
        if User.objects.count() == 0:
            print("🔧 创建默认管理员账号...")
            create_default_admin()
        
        # 数据迁移：处理没有 user 字段的旧名片
        try:
            admin_user = User.objects(username='admin').first()
            if admin_user:
                # 尝试修复没有 user 字段的名片
                from pymongo.errors import OperationFailure
                try:
                    orphan_cards = Card.objects(user__exists=False)
                    if orphan_cards.count() > 0:
                        print(f"🔧 发现 {orphan_cards.count()} 个孤立名片，正在分配给 admin 用户...")
                        for card in orphan_cards:
                            card.user = admin_user
                            card.save()
                        print(f"✅ 已修复孤立名片")
                except:
                    # 如果查询失败，可能是旧数据有问题，删除所有名片重新创建
                    print("⚠️ 检测到旧版本数据结构，正在清理...")
                    try:
                        Card.drop_collection()
                        print("✅ 已清理旧数据")
                    except:
                        pass
                
                # 尝试修复没有 user 字段的链接
                try:
                    orphan_links = Link.objects(user__exists=False)
                    if orphan_links.count() > 0:
                        print(f"🔧 发现 {orphan_links.count()} 个孤立链接，正在分配给 admin 用户...")
                        for link in orphan_links:
                            link.user = admin_user
                            link.save()
                        print(f"✅ 已修复孤立链接")
                except Exception as e:
                    print(f"⚠️ 链接迁移警告: {e}")
                
                # 创建默认分类
                if Category.objects(user=admin_user).count() == 0:
                    print("🔧 创建默认分类...")
                    create_default_categories(admin_user)
        except Exception as e:
            print(f"⚠️ 数据迁移警告: {e}")
        
        # 创建默认测试数据
        if Card.objects.count() == 0:
            print("🔧 创建默认测试数据...")
            create_default_data()
        
        return True
    except Exception as e:
        print(f"❌ MongoDB 连接失败: {e}")
        return False


class User(Document):
    """用户模型"""
    username = StringField(required=True, unique=True, max_length=50, verbose_name="用户名")
    password_hash = StringField(required=True, verbose_name="密码哈希")
    role = StringField(required=True, choices=['admin', 'user'], default='user', verbose_name="角色")
    is_active = BooleanField(default=True, verbose_name="是否激活")
    expire_time = DateTimeField(verbose_name="过期时间")
    usage_count = IntField(default=0, verbose_name="已使用次数")
    max_usage_count = IntField(default=-1, verbose_name="最大使用次数")  # -1 表示不限制
    created_at = DateTimeField(default=datetime.now, verbose_name="创建时间")
    last_login = DateTimeField(verbose_name="最后登录时间")
    
    meta = {
        'collection': 'users',
        'ordering': ['-created_at'],
        'auto_create_index': False,  # 禁用自动创建索引（权限限制）
        'indexes': [
            'username',
            'role'
        ]
    }
    
    def set_password(self, password: str):
        """设置密码（SHA256加密）"""
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    def check_password(self, password: str) -> bool:
        """验证密码"""
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()
    
    def is_admin(self) -> bool:
        """是否为管理员"""
        return self.role == 'admin'
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': str(self.id),
            'username': self.username,
            'role': self.role,
            'is_active': self.is_active,
            'expire_time': self.expire_time.strftime('%Y-%m-%d %H:%M:%S') if self.expire_time else None,
            'usage_count': self.usage_count,
            'max_usage_count': self.max_usage_count,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M:%S') if self.last_login else None
        }


class Device(Document):
    """设备模型 - 用于设备管理和限制"""
    user = ReferenceField(User, required=True, verbose_name="所属用户")
    device_id = StringField(required=True, max_length=200, verbose_name="设备ID")
    device_name = StringField(required=True, max_length=100, verbose_name="设备名称")
    device_type = StringField(max_length=50, verbose_name="设备类型")  # macOS, Windows, Linux
    last_ip = StringField(max_length=50, verbose_name="最后登录IP")
    last_login = DateTimeField(default=datetime.now, verbose_name="最后登录时间")
    created_at = DateTimeField(default=datetime.now, verbose_name="首次绑定时间")
    is_active = BooleanField(default=True, verbose_name="是否激活")
    
    meta = {
        'collection': 'devices',
        'ordering': ['-last_login'],
        'auto_create_index': False,
        'indexes': [
            'user',
            'device_id',
            ('user', 'device_id')  # 组合索引
        ]
    }
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': str(self.id),
            'user_id': str(self.user.id) if self.user else None,
            'username': self.user.username if self.user else None,
            'device_id': self.device_id,
            'device_name': self.device_name,
            'device_type': self.device_type,
            'last_ip': self.last_ip,
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M:%S') if self.last_login else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'is_active': self.is_active
        }


class Category(Document):
    """分类模型"""
    user = ReferenceField(User, required=True, verbose_name="所属用户")
    name = StringField(required=True, max_length=100, verbose_name="分类名称")
    description = StringField(verbose_name="描述")
    color = StringField(default='#667eea', max_length=20, verbose_name="颜色标识")
    icon = StringField(max_length=50, verbose_name="图标")  # 增加长度以支持图标库名称
    order = IntField(default=0, verbose_name="排序")
    created_at = DateTimeField(default=datetime.now, verbose_name="创建时间")
    updated_at = DateTimeField(default=datetime.now, verbose_name="更新时间")
    
    meta = {
        'collection': 'categories',
        'ordering': ['order', 'name'],
        'auto_create_index': False,
        'indexes': [
            'user',
            ('user', 'name'),  # 组合唯一索引
            'order'
        ]
    }
    
    def save(self, *args, **kwargs):
        """保存时更新时间"""
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': str(self.id),
            'user_id': str(self.user.id) if self.user else None,
            'username': self.user.username if self.user else None,
            'name': self.name,
            'description': self.description,
            'color': self.color,
            'icon': self.icon,
            'order': self.order,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class CardConfigItem(EmbeddedDocument):
    """名片配置项（嵌入式文档）"""
    key = StringField(required=True, max_length=100, verbose_name="字段名")
    value = StringField(required=True, verbose_name="字段值")
    order = IntField(default=0, verbose_name="排序")
    fixed_template_id = StringField(verbose_name="固定模板ID")  # 来源模板ID，用户自己添加的为空
    
    meta = {
        'ordering': ['order']
    }
    
    def to_dict(self):
        """转换为字典"""
        return {
            'key': self.key,
            'value': self.value,
            'order': self.order,
            'fixed_template_id': self.fixed_template_id
        }


class Card(Document):
    """名片模型"""
    user = ReferenceField(User, required=True, verbose_name="所属用户")
    name = StringField(required=True, max_length=100, verbose_name="名片名称")
    description = StringField(verbose_name="描述")
    category = StringField(default='默认分类', max_length=100, verbose_name="分类")
    configs = EmbeddedDocumentListField(CardConfigItem, verbose_name="配置项列表")
    order = IntField(default=0, verbose_name="排序顺序")  # 排序字段，数值越小越靠前
    created_at = DateTimeField(default=datetime.now, verbose_name="创建时间")
    updated_at = DateTimeField(default=datetime.now, verbose_name="更新时间")
    
    meta = {
        'collection': 'cards',
        'ordering': ['order', '-created_at'],  # 优先按 order 排序
        'auto_create_index': False,  # 禁用自动创建索引（权限限制）
        'indexes': [
            'user',
            'name',
            'category',
            'order',
            '-created_at',
            ('user', 'category'),  # 组合索引：用户+分类
            ('user', 'category', 'order')  # 用户+分类+排序
        ]
    }
    
    def save(self, *args, **kwargs):
        """保存时更新时间"""
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': str(self.id),
            'user_id': str(self.user.id) if self.user else None,
            'username': self.user.username if self.user else None,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'config': [c.to_dict() for c in self.configs]
        }


class Link(Document):
    """通告链接模型"""
    user = ReferenceField(User, required=True, verbose_name="所属用户")
    name = StringField(required=True, max_length=200, verbose_name="链接名称")
    url = StringField(required=True, verbose_name="链接地址")
    status = StringField(default='active', max_length=50, verbose_name="状态")  # active, archived, deleted
    category = StringField(max_length=100, verbose_name="分类")
    description = StringField(verbose_name="描述")
    created_at = DateTimeField(default=datetime.now, verbose_name="创建时间")
    updated_at = DateTimeField(default=datetime.now, verbose_name="更新时间")
    
    meta = {
        'collection': 'links',
        'ordering': ['-created_at'],
        'auto_create_index': False,  # 禁用自动创建索引（权限限制）
        'indexes': [
            'user',
            'status',
            '-created_at',
            ('user', 'status')
        ]
    }
    
    def save(self, *args, **kwargs):
        """保存时更新时间"""
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': str(self.id),
            'name': self.name,
            'url': self.url,
            'status': self.status,
            'category': self.category,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class FillRecord(Document):
    """填写记录模型"""
    card = ReferenceField(Card, required=True, verbose_name="使用的名片")
    link = ReferenceField(Link, required=True, verbose_name="填写的链接")
    fill_count = IntField(default=0, verbose_name="成功填写字段数")
    total_count = IntField(default=0, verbose_name="总配置项数")
    success = BooleanField(default=True, verbose_name="是否成功")
    error_message = StringField(verbose_name="错误信息")
    created_at = DateTimeField(default=datetime.now, verbose_name="填写时间")
    
    meta = {
        'collection': 'fill_records',
        'ordering': ['-created_at'],
        'auto_create_index': False,  # 禁用自动创建索引（权限限制）
        'indexes': [
            '-created_at',
            'card',
            'link'
        ]
    }
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': str(self.id),
            'card_id': str(self.card.id) if self.card else None,
            'card_name': self.card.name if self.card else '',
            'link_id': str(self.link.id) if self.link else None,
            'link_name': self.link.name if self.link else '',
            'fill_count': self.fill_count,
            'total_count': self.total_count,
            'success': self.success,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat()
        }


class CardEditRequest(Document):
    """名片修改请求模型 - 管理员修改用户名片需要用户审批"""
    card = ReferenceField('Card', required=True, verbose_name="目标名片")
    user = ReferenceField(User, required=True, verbose_name="名片所属用户")
    admin = ReferenceField(User, required=True, verbose_name="发起修改的管理员")
    
    # 修改前后的数据（JSON格式存储）
    original_name = StringField(verbose_name="原名片名称")
    original_description = StringField(verbose_name="原描述")
    original_category = StringField(verbose_name="原分类")
    original_configs = StringField(verbose_name="原配置项JSON")
    
    modified_name = StringField(verbose_name="修改后名称")
    modified_description = StringField(verbose_name="修改后描述")
    modified_category = StringField(verbose_name="修改后分类")
    modified_configs = StringField(verbose_name="修改后配置项JSON")
    
    # 状态和备注
    status = StringField(default='pending', choices=['pending', 'approved', 'rejected'], verbose_name="状态")
    admin_comment = StringField(verbose_name="管理员备注")
    user_comment = StringField(verbose_name="用户备注/拒绝理由")
    
    # 时间戳
    created_at = DateTimeField(default=datetime.now, verbose_name="创建时间")
    processed_at = DateTimeField(verbose_name="处理时间")
    
    meta = {
        'collection': 'card_edit_requests',
        'ordering': ['-created_at'],
        'auto_create_index': False,
        'indexes': [
            'card',
            'user',
            'admin',
            'status',
            '-created_at',
            ('user', 'status'),  # 用户+状态索引，用于查询用户的待处理请求
        ]
    }
    
    def to_dict(self):
        """转换为字典"""
        import json
        return {
            'id': str(self.id),
            'card_id': str(self.card.id) if self.card else None,
            'card_name': self.card.name if self.card else '',
            'user_id': str(self.user.id) if self.user else None,
            'username': self.user.username if self.user else '',
            'admin_id': str(self.admin.id) if self.admin else None,
            'admin_name': self.admin.username if self.admin else '',
            'original_name': self.original_name,
            'original_description': self.original_description,
            'original_category': self.original_category,
            'original_configs': json.loads(self.original_configs) if self.original_configs else [],
            'modified_name': self.modified_name,
            'modified_description': self.modified_description,
            'modified_category': self.modified_category,
            'modified_configs': json.loads(self.modified_configs) if self.modified_configs else [],
            'status': self.status,
            'admin_comment': self.admin_comment,
            'user_comment': self.user_comment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
        }


class Notification(Document):
    """系统通知/消息模型"""
    user = ReferenceField(User, required=True, verbose_name="接收用户")
    type = StringField(required=True, choices=['card_edit', 'system', 'other', 'field_push'], default='system', verbose_name="消息类型")
    title = StringField(required=True, max_length=200, verbose_name="标题")
    content = StringField(verbose_name="内容")
    
    # 关联对象（可选）
    related_id = StringField(verbose_name="关联对象ID") # 比如 CardEditRequest 的 ID
    
    is_read = BooleanField(default=False, verbose_name="是否已读")
    created_at = DateTimeField(default=datetime.now, verbose_name="创建时间")
    
    meta = {
        'collection': 'notifications',
        'ordering': ['-created_at'],
        'auto_create_index': False,
        'indexes': [
            'user',
            'is_read',
            '-created_at'
        ]
    }
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'user_id': str(self.user.id) if self.user else None,
            'type': self.type,
            'title': self.title,
            'content': self.content,
            'related_id': self.related_id,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Notice(Document):
    """通告广场-通告模型"""
    title = StringField(required=True, max_length=200, verbose_name="标题")
    platform = StringField(required=True, max_length=50, verbose_name="平台")
    category = StringField(max_length=50, verbose_name="类目")
    brand = StringField(max_length=100, verbose_name="品牌")
    
    # 详情信息
    product_info = StringField(verbose_name="产品情况")
    requirements = StringField(verbose_name="粉丝要求")
    min_fans = IntField(default=0, verbose_name="最低粉丝数")
    reward = StringField(max_length=100, verbose_name="报酬")
    
    # 链接
    link = StringField(verbose_name="报名链接")
    
    # 时间
    publish_date = DateTimeField(default=datetime.now, verbose_name="发布日期")
    start_date = DateTimeField(verbose_name="开始时间")
    end_date = DateTimeField(verbose_name="结束时间")
    
    # 状态
    status = StringField(default='active', choices=['active', 'expired', 'closed'], verbose_name="状态")
    
    # 系统字段
    created_by = ReferenceField(User, verbose_name="创建人")
    created_at = DateTimeField(default=datetime.now, verbose_name="创建时间")
    updated_at = DateTimeField(default=datetime.now, verbose_name="更新时间")
    
    meta = {
        'collection': 'notices',
        'ordering': ['-publish_date', '-created_at'],
        'auto_create_index': False,
        'indexes': [
            'platform',
            'category',
            'status',
            '-publish_date',
            'min_fans'
        ]
    }
    
    def save(self, *args, **kwargs):
        """保存时更新时间"""
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': str(self.id),
            'title': self.title,
            'platform': self.platform,
            'category': self.category,
            'brand': self.brand,
            'product_info': self.product_info,
            'requirements': self.requirements,
            'min_fans': self.min_fans,
            'reward': self.reward,
            'link': self.link,
            'publish_date': self.publish_date.strftime('%Y-%m-%d') if self.publish_date else None,
            'start_date': self.start_date.strftime('%Y-%m-%d') if self.start_date else None,
            'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else None,
            'status': self.status,
            'created_by': self.created_by.username if self.created_by else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class NoticeCategory(Document):
    """通告类目模型（系统级）"""
    name = StringField(required=True, unique=True, max_length=50, verbose_name="类目名称")
    order = IntField(default=0, verbose_name="排序")
    is_active = BooleanField(default=True, verbose_name="是否启用")
    created_at = DateTimeField(default=datetime.now, verbose_name="创建时间")
    
    meta = {
        'collection': 'notice_categories',
        'ordering': ['order', '-created_at'],
        'auto_create_index': False
    }
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'order': self.order,
            'is_active': self.is_active
        }


class Platform(Document):
    """平台模型（系统级）"""
    name = StringField(required=True, unique=True, max_length=50, verbose_name="平台名称")
    icon = StringField(max_length=50, verbose_name="图标")
    order = IntField(default=0, verbose_name="排序")
    is_active = BooleanField(default=True, verbose_name="是否启用")
    created_at = DateTimeField(default=datetime.now, verbose_name="创建时间")
    
    meta = {
        'collection': 'platforms',
        'ordering': ['order', '-created_at'],
        'auto_create_index': False
    }

    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'icon': self.icon,
            'order': self.order,
            'is_active': self.is_active
        }


class FieldLibrary(Document):
    """平台字段库模型（系统级，管理员维护）
    
    用于存储预定义的字段模板，用户可以从中选择添加到自己的名片中。
    字段名支持多个别名（用顿号分隔），方便匹配不同表单的字段。
    """
    name = StringField(required=True, max_length=100, verbose_name="字段名称（支持别名，用顿号分隔）")
    description = StringField(verbose_name="字段说明")
    category = StringField(default='通用', max_length=50, verbose_name="字段分类")  # 如：基本信息、社交账号、平台数据等
    default_value = StringField(verbose_name="默认值示例")
    placeholder = StringField(verbose_name="占位提示")
    order = IntField(default=0, verbose_name="排序")
    is_active = BooleanField(default=True, verbose_name="是否启用")
    created_by = ReferenceField(User, verbose_name="创建人")
    created_at = DateTimeField(default=datetime.now, verbose_name="创建时间")
    updated_at = DateTimeField(default=datetime.now, verbose_name="更新时间")
    
    meta = {
        'collection': 'field_library',
        'ordering': ['category', 'order', '-created_at'],
        'auto_create_index': False,
        'indexes': [
            'category',
            'is_active',
            'order'
        ]
    }
    
    def save(self, *args, **kwargs):
        """保存时更新时间"""
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'default_value': self.default_value,
            'placeholder': self.placeholder,
            'order': self.order,
            'is_active': self.is_active,
            'created_by': self.created_by.username if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class SystemConfig(Document):
    """系统配置字典模型"""
    key = StringField(required=True, unique=True, max_length=100, verbose_name="配置键")
    value = StringField(required=True, verbose_name="配置值")
    description = StringField(verbose_name="说明")
    updated_at = DateTimeField(default=datetime.now, verbose_name="更新时间")
    
    meta = {
        'collection': 'system_config',
        'auto_create_index': False,
        'indexes': ['key']
    }
    
    def save(self, *args, **kwargs):
        """保存时更新时间"""
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)
    
    @classmethod
    def get(cls, key, default=None):
        """获取配置值"""
        try:
            config = cls.objects(key=key).first()
            return config.value if config else default
        except:
            return default
            
    @classmethod
    def set(cls, key, value, description=None):
        """设置配置值"""
        config = cls.objects(key=key).first()
        if not config:
            config = cls(key=key)
        config.value = str(value)
        if description:
            config.description = description
        config.save()


class FixedTemplate(Document):
    """固定模板模型（系统级，管理员维护）
    
    用于存储固定的字段名-字段值模板，用户填表时可以直接使用这些预设值。
    与字段库不同的是，这里存储的是完整的字段名和对应的固定值。
    """
    field_name = StringField(required=True, max_length=200, verbose_name="字段名（支持别名，用顿号分隔）")
    field_value = StringField(required=True, verbose_name="字段值")
    category = StringField(default='通用', max_length=50, verbose_name="分类")
    description = StringField(verbose_name="说明")
    order = IntField(default=0, verbose_name="排序")
    is_active = BooleanField(default=True, verbose_name="是否启用")
    created_by = ReferenceField(User, verbose_name="创建人")
    created_at = DateTimeField(default=datetime.now, verbose_name="创建时间")
    updated_at = DateTimeField(default=datetime.now, verbose_name="更新时间")
    
    meta = {
        'collection': 'fixed_templates',
        'ordering': ['category', 'order', '-created_at'],
        'auto_create_index': False,
        'indexes': [
            'category',
            'is_active',
            'order'
        ]
    }
    
    def save(self, *args, **kwargs):
        """保存时更新时间"""
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': str(self.id),
            'field_name': self.field_name,
            'field_value': self.field_value,
            'category': self.category,
            'description': self.description,
            'order': self.order,
            'is_active': self.is_active,
            'created_by': self.created_by.username if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


def create_default_data():
    """创建默认测试数据"""
    try:
        # 获取默认用户（admin）
        admin_user = User.objects(username='admin').first()
        if not admin_user:
            print("  ⚠️ 未找到管理员用户，跳过创建默认名片")
            return False
            
        # 创建默认系统配置
        if SystemConfig.objects.count() == 0:
            default_configs = {
                'MAX_DEVICES_PER_USER': {'value': '2', 'desc': '每个用户最大允许登录设备数'},
                'CONTACT_WECHAT': {'value': 'your_wechat_id', 'desc': '客服微信号'},
                'CONTACT_EMAIL': {'value': 'your_email@example.com', 'desc': '客服邮箱'},
                'CONTACT_PHONE': {'value': '138-0000-0000', 'desc': '客服电话'},
                'CONTACT_WORK_HOURS': {'value': '周一至周五 9:00-18:00', 'desc': '客服工作时间'}
            }
            for key, data in default_configs.items():
                SystemConfig(key=key, value=data['value'], description=data['desc']).save()
            print(f"  ✅ 创建默认系统配置: {len(default_configs)}项")
        
        # 创建默认通告分类
        if NoticeCategory.objects.count() == 0:
            default_notice_cats = [
                '美妆', '护肤', '个人护理', '兴趣爱好', '时尚', '美食', '家居家装', 
                '母婴', '亲子', '出行', '影视综资讯', '生活记录', '宠物', '运动健身', 
                '游戏', '摄影', '文化艺术', '情感', '科技数码', '婚嫁', '探店', '其他'
            ]
            for i, name in enumerate(default_notice_cats):
                NoticeCategory(name=name, order=i).save()
            print(f"  ✅ 创建默认通告分类: {len(default_notice_cats)}个")
            
        # 创建默认平台
        if Platform.objects.count() == 0:
            default_platforms = [
                {'name': '小红书', 'icon': 'xiaohongshu'},
                {'name': '抖音', 'icon': 'douyin'},
                {'name': '微博', 'icon': 'weibo'},
                {'name': '视频号', 'icon': 'channels'},
                {'name': '西瓜视频', 'icon': 'xigua'},
                {'name': '快手', 'icon': 'kuaishou'}
            ]
            for i, p in enumerate(default_platforms):
                Platform(name=p['name'], icon=p['icon'], order=i).save()
            print(f"  ✅ 创建默认平台: {len(default_platforms)}个")
        
        # 创建默认字段库
        if FieldLibrary.objects.count() == 0:
            default_fields = [
                # 基本信息
                {'name': 'ID、id、账号', 'category': '基本信息', 'description': '平台账号ID', 'default_value': '', 'order': 0},
                {'name': '微信昵称、昵称', 'category': '基本信息', 'description': '微信昵称', 'default_value': '', 'order': 1},
                {'name': '微信号、微信', 'category': '基本信息', 'description': '微信号', 'default_value': '', 'order': 2},
                {'name': '昵称1', 'category': '基本信息', 'description': '备用昵称1', 'default_value': '', 'order': 3},
                {'name': '昵称2', 'category': '基本信息', 'description': '备用昵称2', 'default_value': '', 'order': 4},
                {'name': '昵称23', 'category': '基本信息', 'description': '备用昵称', 'default_value': '', 'order': 5},
                {'name': '手机号、电话、联系方式', 'category': '基本信息', 'description': '联系电话', 'default_value': '', 'order': 6},
                {'name': '姓名、名字', 'category': '基本信息', 'description': '真实姓名', 'default_value': '', 'order': 7},
                {'name': '年龄、年纪', 'category': '基本信息', 'description': '年龄', 'default_value': '', 'order': 8},
                {'name': '性别', 'category': '基本信息', 'description': '性别', 'default_value': '', 'order': 9},
                {'name': '所在地、城市、地区', 'category': '基本信息', 'description': '所在城市', 'default_value': '', 'order': 10},
                
                # 平台数据
                {'name': '粉丝数、粉丝、粉丝量', 'category': '平台数据', 'description': '粉丝数量', 'default_value': '', 'order': 0},
                {'name': '赞藏量、赞藏、点赞收藏', 'category': '平台数据', 'description': '点赞收藏数', 'default_value': '', 'order': 1},
                {'name': '主页链接、主页、链接', 'category': '平台数据', 'description': '个人主页链接', 'default_value': '', 'order': 2},
                {'name': '账号类型、类型、领域', 'category': '平台数据', 'description': '账号类型/领域', 'default_value': '', 'order': 3},
                {'name': '播放量、平均播放', 'category': '平台数据', 'description': '平均播放量', 'default_value': '', 'order': 4},
                
                # 报价相关
                {'name': '报价、自报价、价格', 'category': '报价相关', 'description': '报价金额', 'default_value': '', 'order': 0},
                {'name': '300内自报价', 'category': '报价相关', 'description': '300元内报价', 'default_value': '', 'order': 1},
                {'name': '500内自报价', 'category': '报价相关', 'description': '500元内报价', 'default_value': '', 'order': 2},
                {'name': '1000内自报价', 'category': '报价相关', 'description': '1000元内报价', 'default_value': '', 'order': 3},
                
                # 小红书专用
                {'name': '小红书账号、小红书id', 'category': '小红书', 'description': '小红书账号', 'default_value': '', 'order': 0},
                {'name': '小红书昵称', 'category': '小红书', 'description': '小红书昵称', 'default_value': '', 'order': 1},
                {'name': '小红书链接', 'category': '小红书', 'description': '小红书主页链接', 'default_value': '', 'order': 2},
                {'name': '小红书粉丝', 'category': '小红书', 'description': '小红书粉丝数', 'default_value': '', 'order': 3},
                {'name': '小红书视频报价', 'category': '小红书', 'description': '小红书视频报价', 'default_value': '', 'order': 4},
                {'name': '小红书图文报价', 'category': '小红书', 'description': '小红书图文报价', 'default_value': '', 'order': 5},
                
                # 抖音专用
                {'name': '抖音账号、抖音id', 'category': '抖音', 'description': '抖音账号', 'default_value': '', 'order': 0},
                {'name': '抖音昵称', 'category': '抖音', 'description': '抖音昵称', 'default_value': '', 'order': 1},
                {'name': '抖音链接', 'category': '抖音', 'description': '抖音主页链接', 'default_value': '', 'order': 2},
                {'name': '抖音粉丝', 'category': '抖音', 'description': '抖音粉丝数', 'default_value': '', 'order': 3},
                {'name': '抖音报价', 'category': '抖音', 'description': '抖音视频报价', 'default_value': '', 'order': 4},
                {'name': '抖音赞藏', 'category': '抖音', 'description': '抖音点赞收藏数', 'default_value': '', 'order': 5},
                {'name': '抖音播放量', 'category': '抖音', 'description': '抖音平均播放量', 'default_value': '', 'order': 6},
                
                # 微博专用
                {'name': '微博账号、微博id', 'category': '微博', 'description': '微博账号', 'default_value': '', 'order': 0},
                {'name': '微博昵称', 'category': '微博', 'description': '微博昵称', 'default_value': '', 'order': 1},
                {'name': '微博链接', 'category': '微博', 'description': '微博主页链接', 'default_value': '', 'order': 2},
                {'name': '微博粉丝', 'category': '微博', 'description': '微博粉丝数', 'default_value': '', 'order': 3},
                {'name': '微博报价', 'category': '微博', 'description': '微博发布报价', 'default_value': '', 'order': 4},
                {'name': '微博转评赞', 'category': '微博', 'description': '微博互动数据', 'default_value': '', 'order': 5},
                
                # 快手专用
                {'name': '快手账号、快手id', 'category': '快手', 'description': '快手账号', 'default_value': '', 'order': 0},
                {'name': '快手昵称', 'category': '快手', 'description': '快手昵称', 'default_value': '', 'order': 1},
                {'name': '快手链接', 'category': '快手', 'description': '快手主页链接', 'default_value': '', 'order': 2},
                {'name': '快手粉丝', 'category': '快手', 'description': '快手粉丝数', 'default_value': '', 'order': 3},
                {'name': '快手报价', 'category': '快手', 'description': '快手视频报价', 'default_value': '', 'order': 4},
                {'name': '快手播放量', 'category': '快手', 'description': '快手平均播放量', 'default_value': '', 'order': 5},
                
                # B站专用
                {'name': 'B站账号、B站id、哔哩哔哩账号', 'category': 'B站', 'description': 'B站账号', 'default_value': '', 'order': 0},
                {'name': 'B站昵称、哔哩哔哩昵称', 'category': 'B站', 'description': 'B站昵称', 'default_value': '', 'order': 1},
                {'name': 'B站链接', 'category': 'B站', 'description': 'B站主页链接', 'default_value': '', 'order': 2},
                {'name': 'B站粉丝', 'category': 'B站', 'description': 'B站粉丝数', 'default_value': '', 'order': 3},
                {'name': 'B站报价', 'category': 'B站', 'description': 'B站视频报价', 'default_value': '', 'order': 4},
                {'name': 'B站播放量', 'category': 'B站', 'description': 'B站平均播放量', 'default_value': '', 'order': 5},
                
                # 视频号专用
                {'name': '视频号账号、视频号id', 'category': '视频号', 'description': '视频号账号', 'default_value': '', 'order': 0},
                {'name': '视频号昵称', 'category': '视频号', 'description': '视频号昵称', 'default_value': '', 'order': 1},
                {'name': '视频号链接', 'category': '视频号', 'description': '视频号主页链接', 'default_value': '', 'order': 2},
                {'name': '视频号粉丝', 'category': '视频号', 'description': '视频号粉丝数', 'default_value': '', 'order': 3},
                {'name': '视频号报价', 'category': '视频号', 'description': '视频号视频报价', 'default_value': '', 'order': 4},
                
                # 公众号专用
                {'name': '公众号名称', 'category': '公众号', 'description': '公众号名称', 'default_value': '', 'order': 0},
                {'name': '公众号id', 'category': '公众号', 'description': '公众号ID', 'default_value': '', 'order': 1},
                {'name': '公众号粉丝', 'category': '公众号', 'description': '公众号粉丝数', 'default_value': '', 'order': 2},
                {'name': '公众号头条报价', 'category': '公众号', 'description': '公众号头条报价', 'default_value': '', 'order': 3},
                {'name': '公众号次条报价', 'category': '公众号', 'description': '公众号次条报价', 'default_value': '', 'order': 4},
                {'name': '公众号阅读量', 'category': '公众号', 'description': '公众号平均阅读量', 'default_value': '', 'order': 5},
                
                # 知乎专用
                {'name': '知乎账号、知乎id', 'category': '知乎', 'description': '知乎账号', 'default_value': '', 'order': 0},
                {'name': '知乎昵称', 'category': '知乎', 'description': '知乎昵称', 'default_value': '', 'order': 1},
                {'name': '知乎链接', 'category': '知乎', 'description': '知乎主页链接', 'default_value': '', 'order': 2},
                {'name': '知乎粉丝', 'category': '知乎', 'description': '知乎粉丝数', 'default_value': '', 'order': 3},
                {'name': '知乎报价', 'category': '知乎', 'description': '知乎回答/文章报价', 'default_value': '', 'order': 4},
                
                # 西瓜视频专用
                {'name': '西瓜账号、西瓜id', 'category': '西瓜视频', 'description': '西瓜视频账号', 'default_value': '', 'order': 0},
                {'name': '西瓜昵称', 'category': '西瓜视频', 'description': '西瓜视频昵称', 'default_value': '', 'order': 1},
                {'name': '西瓜链接', 'category': '西瓜视频', 'description': '西瓜视频主页链接', 'default_value': '', 'order': 2},
                {'name': '西瓜粉丝', 'category': '西瓜视频', 'description': '西瓜视频粉丝数', 'default_value': '', 'order': 3},
                {'name': '西瓜报价', 'category': '西瓜视频', 'description': '西瓜视频报价', 'default_value': '', 'order': 4},
                
                # 收货信息
                {'name': '收货人、收件人', 'category': '收货信息', 'description': '收货人姓名', 'default_value': '', 'order': 0},
                {'name': '收货电话、收件电话', 'category': '收货信息', 'description': '收货电话', 'default_value': '', 'order': 1},
                {'name': '收货地址、收件地址、详细地址', 'category': '收货信息', 'description': '收货详细地址', 'default_value': '', 'order': 2},
                {'name': '省份', 'category': '收货信息', 'description': '省份', 'default_value': '', 'order': 3},
                {'name': '城市', 'category': '收货信息', 'description': '城市', 'default_value': '', 'order': 4},
                {'name': '区县', 'category': '收货信息', 'description': '区/县', 'default_value': '', 'order': 5},
                {'name': '邮编', 'category': '收货信息', 'description': '邮政编码', 'default_value': '', 'order': 6},
                
                # 其他常用
                {'name': '身份证号', 'category': '其他', 'description': '身份证号码', 'default_value': '', 'order': 0},
                {'name': '银行卡号', 'category': '其他', 'description': '银行卡号', 'default_value': '', 'order': 1},
                {'name': '开户行', 'category': '其他', 'description': '开户银行', 'default_value': '', 'order': 2},
                {'name': '支付宝账号', 'category': '其他', 'description': '支付宝账号', 'default_value': '', 'order': 3},
                {'name': '邮箱、电子邮箱、email', 'category': '其他', 'description': '电子邮箱', 'default_value': '', 'order': 4},
                {'name': 'QQ号、QQ', 'category': '其他', 'description': 'QQ号码', 'default_value': '', 'order': 5},
                {'name': '职业、工作', 'category': '其他', 'description': '职业/工作', 'default_value': '', 'order': 6},
                {'name': '备注、其他说明', 'category': '其他', 'description': '备注信息', 'default_value': '', 'order': 7},
            ]
            for field_data in default_fields:
                FieldLibrary(
                    name=field_data['name'],
                    category=field_data['category'],
                    description=field_data['description'],
                    default_value=field_data.get('default_value', ''),
                    order=field_data['order'],
                    is_active=True,
                    created_by=admin_user
                ).save()
            print(f"  ✅ 创建默认字段库: {len(default_fields)}个")

        # 创建默认通告
        if Notice.objects.count() == 0:
            notices_data = [
                {
                    'title': '安踏儿童探店打卡',
                    'platform': '小红书',
                    'category': '母婴',
                    'brand': '安踏儿童',
                    'product_info': '安踏儿童冰甲羽绒服，预估寄拍，样品需回寄\n(寄60元内需自费)',
                    'requirements': '6000',
                    'min_fans': 6000,
                    'reward': '8000',
                    'link': 'https://docs.qq.com/form/page/DV0JwTG9BTmJIZWNr',
                    'publish_date': datetime(2025, 10, 22),
                    'start_date': datetime(2025, 10, 22),
                    'end_date': datetime(2025, 11, 22),
                    'created_by': admin_user
                },
                {
                    'title': '美妆新品试色',
                    'platform': '抖音',
                    'category': '美妆',
                    'brand': '花西子',
                    'product_info': '新品口红套盒，无需寄回',
                    'requirements': '10000',
                    'min_fans': 10000,
                    'reward': '500-1000',
                    'link': 'https://docs.qq.com/form/page/DV0JwTG9BTmJIZWNr',
                    'publish_date': datetime(2025, 10, 23),
                    'start_date': datetime(2025, 10, 23),
                    'end_date': datetime(2025, 11, 23),
                    'created_by': admin_user
                },
                {
                    'title': '数码测评-蓝牙耳机',
                    'platform': 'B站',
                    'category': '科技数码',
                    'brand': 'Sony',
                    'product_info': '新款降噪耳机测评，需产出3分钟以上视频',
                    'requirements': '50000',
                    'min_fans': 50000,
                    'reward': '2000',
                    'link': 'https://docs.qq.com/form/page/DV0JwTG9BTmJIZWNr',
                    'publish_date': datetime(2025, 10, 24),
                    'start_date': datetime(2025, 10, 24),
                    'end_date': datetime(2025, 11, 24),
                    'created_by': admin_user
                }
            ]
            
            # 复制多份以模拟列表效果
            for i in range(4):
                for n in notices_data:
                    # 稍微修改一下标题防止完全重复
                    new_notice = n.copy()
                    if i > 0:
                        new_notice['title'] = f"{new_notice['title']} #{i}"
                    Notice(**new_notice).save()
                    
            print(f"  ✅ 创建默认通告: {len(notices_data) * 4}个")

        # 创建默认名片
        default_card = Card(
            user=admin_user,
            name="名片1",
            description="默认测试名片",
            category="默认分类"
        )
        
        # 创建默认配置项（同时支持腾讯文档和麦客CRM表单）
        default_configs = [
            # 腾讯文档表单字段
            CardConfigItem(key='手机号【着急时联系】', value='13800138000', order=0),
            CardConfigItem(key='微信', value='weixin123', order=1),
            CardConfigItem(key='抖音昵称', value='美妆达人小红', order=2),
            CardConfigItem(key='抖音账号', value='douyin_xiaohong', order=3),
            CardConfigItem(key='粉丝数量', value='150000', order=4),
            CardConfigItem(key='主页链接', value='https://www.douyin.com/user/xiaohong', order=5),
            CardConfigItem(key='赞藏量', value='80000', order=6),
            CardConfigItem(key='所在地', value='北京', order=7),
            CardConfigItem(key='（自行报价）', value='450', order=8),
            CardConfigItem(key='账号类型', value='母婴', order=9),
            
            # 麦客CRM表单字段（兼容）
            CardConfigItem(key='名称', value='美妆达人小红', order=10),
            CardConfigItem(key='ID号', value='douyin_xiaohong', order=11),
            CardConfigItem(key='链接', value='https://www.douyin.com/user/xiaohong', order=12),
            CardConfigItem(key='粉丝', value='150000', order=13),
            CardConfigItem(key='赞藏', value='80000', order=14),
            CardConfigItem(key='类型', value='母婴', order=15),
            CardConfigItem(key='300内自报价', value='450', order=16),
            CardConfigItem(key='电话', value='13800138000', order=17),
        ]
        
        default_card.configs = default_configs
        default_card.save()
        print(f"  ✅ 创建默认名片: {default_card.name}")
        
        # 创建默认链接
        link1 = Link(
            user=admin_user,
            name="抖音招募表单-麦客CRM",
            url="https://mu2ukf52t27s5d3a.mikecrm.com/xIQzSHo",
            status="active",
            category="麦客CRM",
            description="麦客CRM测试表单"
        )
        link1.save()
        print(f"  ✅ 创建默认链接1: {link1.name}")
        
        link2 = Link(
            user=admin_user,
            name="抖音-Vitavea白加黑胶囊-腾讯文档",
            url="https://docs.qq.com/form/page/DV0JwTG9BTmJIZWNr",
            status="active",
            category="腾讯文档",
            description="腾讯文档测试表单"
        )
        link2.save()
        print(f"  ✅ 创建默认链接2: {link2.name}")
        
        print("✅ 默认数据创建成功")
        return True
        
    except Exception as e:
        print(f"❌ 创建默认数据失败: {e}")
        return False


def create_default_categories(user):
    """创建默认分类"""
    try:
        default_categories = [
            {'name': '默认分类', 'description': '默认分类', 'color': '#667eea', 'icon': 'fa5s.folder', 'order': 0},
            {'name': '工作', 'description': '工作相关名片', 'color': '#4299e1', 'icon': 'fa5s.briefcase', 'order': 1},
            {'name': '个人', 'description': '个人名片', 'color': '#48bb78', 'icon': 'fa5s.user', 'order': 2},
            {'name': '测试', 'description': '测试用名片', 'color': '#ed8936', 'icon': 'fa5s.flask', 'order': 3},
        ]
        
        for cat_data in default_categories:
            category = Category(
                user=user,
                name=cat_data['name'],
                description=cat_data['description'],
                color=cat_data['color'],
                icon=cat_data.get('icon', '📁'),
                order=cat_data['order']
            )
            category.save()
            print(f"  ✅ 创建分类: {cat_data['icon']} {cat_data['name']}")
        
        print("✅ 默认分类创建成功")
        return True
    except Exception as e:
        print(f"❌ 创建默认分类失败: {e}")
        return False


def create_default_admin():
    """创建默认管理员账号"""
    try:
        # 创建管理员账号
        admin = User(
            username='admin',
            role='admin',
            is_active=True
        )
        admin.set_password('admin123')  # 默认密码
        admin.save()
        print(f"  ✅ 创建管理员账号: admin / admin123")
        
        # 创建普通测试用户
        user = User(
            username='user',
            role='user',
            is_active=True
        )
        user.set_password('user123')  # 默认密码
        user.save()
        print(f"  ✅ 创建测试用户: user / user123")
        
        print("✅ 默认用户创建成功")
        return True
    except Exception as e:
        print(f"❌ 创建默认用户失败: {e}")
        return False
