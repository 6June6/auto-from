"""
数据库管理器
提供高级数据操作接口
适配 MongoDB + MongoEngine
"""
from typing import List, Optional, Dict
from .models import Card, CardConfigItem, Link, FillRecord, User, Notice, NoticeCategory, Platform, FieldLibrary, Category, CardEditRequest, Notification, FixedTemplate
from bson import ObjectId
from mongoengine.errors import DoesNotExist, ValidationError
from mongoengine import Q


class DatabaseManager:
    """数据库管理器"""
    
    # ==================== 名片相关 ====================
    
    @staticmethod
    def get_all_cards(user=None) -> List[Card]:
        """
        获取所有名片
        
        Args:
            user: 用户对象，如果提供则只返回该用户的名片
        
        Returns:
            名片列表
        """
        if user:
            return list(Card.objects(user=user).order_by('-created_at'))
        return list(Card.objects.order_by('-created_at'))
    
    @staticmethod
    def get_card_by_id(card_id: str) -> Optional[Card]:
        """
        根据ID获取名片
        
        Args:
            card_id: 名片ID（字符串或ObjectId）
        
        Returns:
            Card对象或None
        """
        try:
            # MongoDB 使用 ObjectId 作为主键
            if isinstance(card_id, int):
                # 如果传入的是整数，尝试转换
                # 这是为了兼容旧的 SQLite 代码
                cards = Card.objects.order_by('created_at')
                if 0 < card_id <= len(cards):
                    return cards[card_id - 1]
                return None
            
            return Card.objects.get(id=card_id)
        except (DoesNotExist, ValidationError):
            return None
    
    @staticmethod
    def create_card(name: str, configs: List[Dict[str, str]], user, description: str = "", category: str = "默认分类") -> Card:
        """
        创建名片
        
        Args:
            name: 名片名称
            configs: 配置项列表 [{'key': '字段名', 'value': '值'}, ...]
            user: 所属用户对象或用户ID
            description: 描述
            category: 分类
        
        Returns:
            创建的名片对象
        """
        try:
            # 如果传入的是用户ID字符串，转换为User对象
            if isinstance(user, str):
                user = User.objects.get(id=user)
            
            # 创建配置项对象
            config_items = []
            for i, config in enumerate(configs):
                config_item = CardConfigItem(
                    key=config['key'],
                    value=config['value'],
                    order=i
                )
                config_items.append(config_item)
            
            # 创建名片
            card = Card(
                user=user,
                name=name,
                description=description,
                category=category,
                configs=config_items
            )
            card.save()
            
            return card
            
        except Exception as e:
            print(f"❌ 创建名片失败: {e}")
            raise
    
    @staticmethod
    def update_card(card_id: str, name: str = None, configs: List[Dict[str, str]] = None, 
                   description: str = None, category: str = None) -> bool:
        """
        更新名片
        
        Args:
            card_id: 名片ID
            name: 新名称
            configs: 新配置项列表
            description: 新描述
            category: 分类
        
        Returns:
            是否成功
        """
        try:
            card = DatabaseManager.get_card_by_id(card_id)
            if not card:
                return False
            
            # 更新字段
            if name is not None:
                card.name = name
            
            if description is not None:
                card.description = description
            
            if category is not None:
                card.category = category
            
            # 更新配置项
            if configs is not None:
                config_items = []
                for i, config in enumerate(configs):
                    config_item = CardConfigItem(
                        key=config['key'],
                        value=config['value'],
                        order=i
                    )
                    config_items.append(config_item)
                card.configs = config_items
            
            card.save()
            return True
            
        except Exception as e:
            print(f"❌ 更新名片失败: {e}")
            return False
    
    @staticmethod
    def update_cards_order(card_orders: List[Dict[str, any]]) -> bool:
        """
        批量更新名片排序
        
        Args:
            card_orders: 名片排序列表 [{'id': card_id, 'order': order}, ...]
        
        Returns:
            是否成功
        """
        try:
            for item in card_orders:
                card = DatabaseManager.get_card_by_id(item['id'])
                if card:
                    card.order = item['order']
                    card.save()
            return True
        except Exception as e:
            print(f"❌ 更新名片排序失败: {e}")
            return False
    
    @staticmethod
    def delete_card(card_id: str) -> bool:
        """
        删除名片
        
        Args:
            card_id: 名片ID
        
        Returns:
            是否成功
        """
        try:
            card = DatabaseManager.get_card_by_id(card_id)
            if not card:
                return False
            
            # 删除关联的填写记录
            FillRecord.objects(card=card).delete()
            
            # 删除名片
            card.delete()
            return True
            
        except Exception as e:
            print(f"❌ 删除名片失败: {e}")
            return False
    
    # ==================== 用户分类相关 ====================
    
    @staticmethod
    def get_user_categories(user) -> List[Category]:
        """
        获取用户的所有分类
        
        Args:
            user: 用户对象
        
        Returns:
            分类列表
        """
        try:
            if user:
                return list(Category.objects(user=user).order_by('order', 'name'))
            return []
        except Exception as e:
            print(f"❌ 获取用户分类失败: {e}")
            return []
    
    @staticmethod
    def create_user_category(user, name: str, description: str = "", color: str = "#667eea", icon: str = "fa5s.folder") -> Category:
        """
        创建用户分类
        
        Args:
            user: 用户对象
            name: 分类名称
            description: 描述
            color: 颜色
            icon: 图标
        
        Returns:
            创建的分类对象
        """
        try:
            # 检查是否已存在同名分类
            existing = Category.objects(user=user, name=name).first()
            if existing:
                return existing
            
            # 获取当前最大 order
            max_order = 0
            categories = Category.objects(user=user)
            if categories.count() > 0:
                max_order = max([c.order for c in categories]) + 1
            
            category = Category(
                user=user,
                name=name,
                description=description,
                color=color,
                icon=icon,
                order=max_order
            )
            category.save()
            return category
        except Exception as e:
            print(f"❌ 创建用户分类失败: {e}")
            return None
    
    # ==================== 链接相关 ====================
    
    @staticmethod
    def get_all_links(status: str = None, user=None) -> List[Link]:
        """
        获取所有链接
        
        Args:
            status: 筛选状态，None表示全部
            user: 用户对象，如果提供则只返回该用户的链接
        
        Returns:
            链接列表
        """
        try:
            query = Link.objects
            
            if user:
                query = query.filter(user=user)
                
            if status:
                query = query.filter(status=status)
                
            return list(query.order_by('-created_at'))
        except Exception as e:
            print(f"❌ 获取链接列表失败: {e}")
            return []
    
    @staticmethod
    def get_link_by_id(link_id: str) -> Optional[Link]:
        """
        根据ID获取链接
        
        Args:
            link_id: 链接ID
        
        Returns:
            Link对象或None
        """
        try:
            # MongoDB 使用 ObjectId 作为主键
            if isinstance(link_id, int):
                # 兼容旧的整数ID
                links = Link.objects.order_by('created_at')
                if 0 < link_id <= len(links):
                    return links[link_id - 1]
                return None
            
            return Link.objects.get(id=link_id)
        except (DoesNotExist, ValidationError):
            return None
    
    @staticmethod
    def get_all_links_admin(keyword: str = None, limit: int = 20, offset: int = 0) -> Dict:
        """
        获取所有链接（管理员用，支持搜索和分页）
        
        Args:
            keyword: 搜索关键词
            limit: 数量限制
            offset: 偏移量
            
        Returns:
            Dict: {'links': List[Link], 'total': int}
        """
        try:
            query = Link.objects
            
            if keyword:
                # 搜索链接名、URL、用户名
                users = User.objects(username__icontains=keyword)
                query = query.filter(Q(name__icontains=keyword) | Q(url__icontains=keyword) | Q(user__in=users))
            
            total = query.count()
            links = list(query.order_by('-created_at').skip(offset).limit(limit))
            
            return {
                'links': links,
                'total': total
            }
        except Exception as e:
            print(f"❌ 获取所有链接失败: {e}")
            return {'links': [], 'total': 0}

    @staticmethod
    def get_link_by_url(url: str, user=None) -> Optional[Link]:
        """
        根据URL获取链接
        
        Args:
            url: 链接地址
            user: 用户对象，如果提供则只查询该用户的链接
        
        Returns:
            Link对象或None
        """
        try:
            if user:
                return Link.objects(url=url, user=user).first()
            return Link.objects(url=url).first()
        except Exception:
            return None

    @staticmethod
    def create_link(name: str, url: str, user, status: str = 'active', 
                   category: str = None, description: str = None) -> Link:
        """
        创建链接
        
        Args:
            name: 链接名称
            url: 链接地址
            user: 所属用户
            status: 状态
            category: 分类
            description: 描述
        
        Returns:
            创建的链接对象
        """
        try:
            # 如果传入的是用户ID字符串，转换为User对象
            if isinstance(user, str):
                user = User.objects.get(id=user)
                
            link = Link(
                user=user,
                name=name,
                url=url,
                status=status,
                category=category,
                description=description
            )
            link.save()
            return link
            
        except Exception as e:
            print(f"❌ 创建链接失败: {e}")
            raise
    
    @staticmethod
    def update_link(link_id: str, **kwargs) -> bool:
        """
        更新链接
        
        Args:
            link_id: 链接ID
            **kwargs: 要更新的字段
        
        Returns:
            是否成功
        """
        try:
            link = DatabaseManager.get_link_by_id(link_id)
            if not link:
                return False
            
            # 更新字段
            for key, value in kwargs.items():
                if hasattr(link, key) and value is not None:
                    setattr(link, key, value)
            
            link.save()
            return True
            
        except Exception as e:
            print(f"❌ 更新链接失败: {e}")
            return False
    
    @staticmethod
    def delete_link(link_id: str) -> bool:
        """
        删除链接
        
        Args:
            link_id: 链接ID
        
        Returns:
            是否成功
        """
        try:
            link = DatabaseManager.get_link_by_id(link_id)
            if not link:
                return False
            
            # 删除关联的填写记录
            FillRecord.objects(link=link).delete()
            
            # 删除链接
            link.delete()
            return True
            
        except Exception as e:
            print(f"❌ 删除链接失败: {e}")
            return False
    
    # ==================== 用户管理相关 ====================
    
    @staticmethod
    def get_all_users(keyword: str = None) -> List[User]:
        """
        获取所有用户
        
        Args:
            keyword: 搜索关键词（用户名）
        
        Returns:
            用户列表
        """
        try:
            query = User.objects
            if keyword:
                query = query.filter(username__icontains=keyword)
            return list(query.order_by('-created_at'))
        except Exception as e:
            print(f"❌ 获取用户列表失败: {e}")
            return []

    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[User]:
        """根据ID获取用户"""
        try:
            return User.objects.get(id=user_id)
        except (DoesNotExist, ValidationError):
            return None

    @staticmethod
    def create_user(username: str, password: str, role: str = 'user', is_active: bool = True, 
                    expire_time=None, max_usage_count: int = -1) -> User:
        """
        创建用户
        
        Args:
            username: 用户名
            password: 密码
            role: 角色 (admin/user)
            is_active: 是否激活
            expire_time: 过期时间
            max_usage_count: 最大使用次数
        
        Returns:
            创建的用户对象
        """
        try:
            # 检查用户名是否存在
            if User.objects(username=username).first():
                raise ValueError(f"用户名 '{username}' 已存在")
            
            user = User(
                username=username,
                role=role,
                is_active=is_active,
                expire_time=expire_time,
                max_usage_count=max_usage_count
            )
            user.set_password(password)
            user.save()
            return user
        except Exception as e:
            print(f"❌ 创建用户失败: {e}")
            raise

    @staticmethod
    def update_user(user_id: str, password: str = None, role: str = None, 
                   is_active: bool = None, expire_time=None, max_usage_count: int = None) -> bool:
        """
        更新用户
        
        Args:
            user_id: 用户ID
            password: 新密码（如果为None则不修改）
            role: 新角色
            is_active: 新状态
            expire_time: 过期时间
            max_usage_count: 最大使用次数
        
        Returns:
            是否成功
        """
        try:
            user = DatabaseManager.get_user_by_id(user_id)
            if not user:
                return False
            
            if password:
                user.set_password(password)
            
            if role:
                user.role = role
                
            if is_active is not None:
                user.is_active = is_active
                
            if expire_time is not None:
                user.expire_time = expire_time
                
            if max_usage_count is not None:
                user.max_usage_count = max_usage_count
            
            user.save()
            return True
        except Exception as e:
            print(f"❌ 更新用户失败: {e}")
            return False

    @staticmethod
    def delete_user(user_id: str) -> bool:
        """
        删除用户
        注意：这会级联删除用户的所有数据（名片、链接等）
        """
        try:
            user = DatabaseManager.get_user_by_id(user_id)
            if not user:
                return False
            
            # 级联删除关联数据
            # 1. 删除设备
            from .models import Device
            Device.objects(user=user).delete()
            
            # 2. 删除填写记录
            user_cards = Card.objects(user=user)
            FillRecord.objects(card__in=user_cards).delete()
            
            # 3. 删除名片
            user_cards.delete()
            
            # 4. 删除链接
            Link.objects(user=user).delete()
            
            # 5. 删除分类
            Category.objects(user=user).delete()
            
            # 最后删除用户
            user.delete()
            return True
        except Exception as e:
            print(f"❌ 删除用户失败: {e}")
            return False

    # ==================== 通告广场相关 ====================
    
    @staticmethod
    def get_all_notices(category: str = None, platform: str = None, 
                       status: str = 'active', min_fans: int = None,
                       keyword: str = None, limit: int = 100) -> List[Notice]:
        """
        获取通告列表
        
        Args:
            category: 类目筛选
            platform: 平台筛选
            status: 状态筛选
            min_fans: 最低粉丝要求筛选 (<= min_fans)
            keyword: 关键词搜索 (标题/品牌)
            limit: 限制数量
        
        Returns:
            通告列表
        """
        try:
            query = Notice.objects
            
            if status:
                query = query.filter(status=status)
            
            if category and category != '全部':
                query = query.filter(category=category)
                
            if platform and platform != '全部':
                query = query.filter(platform=platform)
                
            if min_fans is not None:
                # 筛选粉丝要求小于等于用户粉丝数的通告，或者是筛选要求粉丝数大于等于某个值的通告？
                # 通常用户想看自己能报名的，所以这里假设 min_fans 是用户的粉丝数
                # 或者是筛选通告的门槛，比如筛选门槛 > 10000 的通告
                # 这里假设是筛选器，筛选 min_fans 字段
                # 比如 min_fans=5000，找出所有 min_fans <= 5000 的通告？还是 >= 5000？
                # 假设用户想找粉丝要求 <= 自己的粉丝数的通告
                query = query.filter(min_fans__lte=min_fans)
                
            if keyword:
                from mongoengine.queryset.visitor import Q
                query = query.filter(Q(title__icontains=keyword) | Q(brand__icontains=keyword))
            
            return list(query.order_by('-publish_date', '-created_at').limit(limit))
            
        except Exception as e:
            print(f"❌ 获取通告列表失败: {e}")
            return []

    @staticmethod
    def get_notice_by_id(notice_id: str) -> Optional[Notice]:
        """根据ID获取通告"""
        try:
            return Notice.objects.get(id=notice_id)
        except (DoesNotExist, ValidationError):
            return None

    @staticmethod
    def create_notice(title: str, platform: str, link: str, **kwargs) -> Notice:
        """
        创建通告
        
        Args:
            title: 标题
            platform: 平台
            link: 链接
            **kwargs: 其他字段 (category, brand, product_info, requirements, min_fans, reward, 
                             publish_date, start_date, end_date, created_by)
        
        Returns:
            创建的通告对象
        """
        try:
            notice = Notice(
                title=title,
                platform=platform,
                link=link,
                **kwargs
            )
            notice.save()
            return notice
        except Exception as e:
            print(f"❌ 创建通告失败: {e}")
            raise

    @staticmethod
    def update_notice(notice_id: str, **kwargs) -> bool:
        """
        更新通告
        
        Args:
            notice_id: 通告ID
            **kwargs: 要更新的字段
        
        Returns:
            是否成功
        """
        try:
            notice = DatabaseManager.get_notice_by_id(notice_id)
            if not notice:
                return False
            
            for key, value in kwargs.items():
                if hasattr(notice, key) and value is not None:
                    setattr(notice, key, value)
            
            notice.save()
            return True
        except Exception as e:
            print(f"❌ 更新通告失败: {e}")
            return False

    @staticmethod
    def delete_notice(notice_id: str) -> bool:
        """删除通告"""
        try:
            notice = DatabaseManager.get_notice_by_id(notice_id)
            if not notice:
                return False
            
            notice.delete()
            return True
        except Exception as e:
            print(f"❌ 删除通告失败: {e}")
            return False

    # ==================== 字典表管理 ====================
    
    @staticmethod
    def get_all_platforms() -> List[Platform]:
        """获取所有平台"""
        return list(Platform.objects(is_active=True).order_by('order'))
        
    @staticmethod
    def get_all_notice_categories() -> List[NoticeCategory]:
        """获取所有通告分类"""
        return list(NoticeCategory.objects(is_active=True).order_by('order'))

    @staticmethod
    def create_platform(name: str, icon: str = None, order: int = 0) -> Platform:
        """创建平台"""
        try:
            p = Platform(name=name, icon=icon, order=order)
            p.save()
            return p
        except Exception as e:
            print(f"❌ 创建平台失败: {e}")
            raise

    @staticmethod
    def update_platform(platform_id: str, name: str = None, icon: str = None, 
                       order: int = None, is_active: bool = None) -> bool:
        """更新平台"""
        try:
            p = Platform.objects.get(id=platform_id)
            if name: p.name = name
            if icon: p.icon = icon
            if order is not None: p.order = order
            if is_active is not None: p.is_active = is_active
            p.save()
            return True
        except Exception as e:
            print(f"❌ 更新平台失败: {e}")
            return False

    @staticmethod
    def delete_platform(platform_id: str) -> bool:
        """删除平台"""
        try:
            Platform.objects.get(id=platform_id).delete()
            return True
        except Exception as e:
            print(f"❌ 删除平台失败: {e}")
            return False

    @staticmethod
    def create_notice_category(name: str, order: int = 0) -> NoticeCategory:
        """创建通告分类"""
        try:
            c = NoticeCategory(name=name, order=order)
            c.save()
            return c
        except Exception as e:
            print(f"❌ 创建通告分类失败: {e}")
            raise

    @staticmethod
    def update_notice_category(category_id: str, name: str = None, 
                             order: int = None, is_active: bool = None) -> bool:
        """更新通告分类"""
        try:
            c = NoticeCategory.objects.get(id=category_id)
            if name: c.name = name
            if order is not None: c.order = order
            if is_active is not None: c.is_active = is_active
            c.save()
            return True
        except Exception as e:
            print(f"❌ 更新通告分类失败: {e}")
            return False

    @staticmethod
    def delete_notice_category(category_id: str) -> bool:
        """删除通告分类"""
        try:
            NoticeCategory.objects.get(id=category_id).delete()
            return True
        except Exception as e:
            print(f"❌ 删除通告分类失败: {e}")
            return False
    
    # ==================== 字段库相关 ====================
    
    @staticmethod
    def get_all_field_library(category: str = None, is_active: bool = True) -> List[FieldLibrary]:
        """
        获取字段库列表
        
        Args:
            category: 字段分类筛选
            is_active: 是否只获取启用的字段
        
        Returns:
            字段库列表
        """
        try:
            query = FieldLibrary.objects
            
            if is_active is not None:
                query = query.filter(is_active=is_active)
            
            if category and category != '全部':
                query = query.filter(category=category)
            
            return list(query.order_by('category', 'order', '-created_at'))
        except Exception as e:
            print(f"❌ 获取字段库失败: {e}")
            return []
    
    @staticmethod
    def get_field_library_categories() -> List[str]:
        """
        获取字段库所有分类
        
        Returns:
            分类列表
        """
        try:
            fields = FieldLibrary.objects(is_active=True).only('category')
            categories = list(set([f.category for f in fields if f.category]))
            return sorted(categories)
        except Exception as e:
            print(f"❌ 获取字段库分类失败: {e}")
            return []
    
    @staticmethod
    def get_field_library_by_id(field_id: str) -> Optional[FieldLibrary]:
        """根据ID获取字段"""
        try:
            return FieldLibrary.objects.get(id=field_id)
        except Exception:
            return None
    
    @staticmethod
    def create_field_library(name: str, category: str = '通用', description: str = None,
                            default_value: str = None, placeholder: str = None,
                            order: int = 0, created_by=None) -> FieldLibrary:
        """
        创建字段库条目
        
        Args:
            name: 字段名称（支持别名，用顿号分隔）
            category: 字段分类
            description: 字段说明
            default_value: 默认值示例
            placeholder: 占位提示
            order: 排序
            created_by: 创建人
        
        Returns:
            创建的字段对象
        """
        try:
            field = FieldLibrary(
                name=name,
                category=category,
                description=description,
                default_value=default_value,
                placeholder=placeholder,
                order=order,
                is_active=True,
                created_by=created_by
            )
            field.save()
            return field
        except Exception as e:
            print(f"❌ 创建字段库条目失败: {e}")
            raise
    
    @staticmethod
    def update_field_library(field_id: str, **kwargs) -> bool:
        """
        更新字段库条目
        
        Args:
            field_id: 字段ID
            **kwargs: 要更新的字段
        
        Returns:
            是否成功
        """
        try:
            field = DatabaseManager.get_field_library_by_id(field_id)
            if not field:
                return False
            
            for key, value in kwargs.items():
                if hasattr(field, key) and value is not None:
                    setattr(field, key, value)
            
            field.save()
            return True
        except Exception as e:
            print(f"❌ 更新字段库条目失败: {e}")
            return False
    
    @staticmethod
    def delete_field_library(field_id: str) -> bool:
        """
        删除字段库条目
        
        Args:
            field_id: 字段ID
        
        Returns:
            是否成功
        """
        try:
            field = DatabaseManager.get_field_library_by_id(field_id)
            if not field:
                return False
            
            field.delete()
            return True
        except Exception as e:
            print(f"❌ 删除字段库条目失败: {e}")
            return False
    
    # ==================== 固定模板相关 ====================
    
    @staticmethod
    def get_all_fixed_templates(category: str = None, is_active: bool = True) -> List[FixedTemplate]:
        """
        获取固定模板列表
        
        Args:
            category: 分类筛选
            is_active: 是否只获取启用的模板
        
        Returns:
            模板列表
        """
        try:
            query = FixedTemplate.objects
            
            if is_active is not None:
                query = query.filter(is_active=is_active)
            
            if category and category != '全部':
                query = query.filter(category=category)
            
            return list(query.order_by('category', 'order', '-created_at'))
        except Exception as e:
            print(f"❌ 获取固定模板失败: {e}")
            return []
            
    @staticmethod
    def get_fixed_template_categories() -> List[str]:
        """
        获取固定模板所有分类
        
        Returns:
            分类列表
        """
        try:
            templates = FixedTemplate.objects(is_active=True).only('category')
            categories = list(set([t.category for t in templates if t.category]))
            return sorted(categories)
        except Exception as e:
            print(f"❌ 获取固定模板分类失败: {e}")
            return []

    @staticmethod
    def get_fixed_template_by_id(template_id: str) -> Optional[FixedTemplate]:
        """根据ID获取固定模板"""
        try:
            return FixedTemplate.objects.get(id=template_id)
        except Exception:
            return None

    @staticmethod
    def create_fixed_template(field_name: str, field_value: str, category: str = '通用',
                             description: str = None, order: int = 0, 
                             created_by=None) -> FixedTemplate:
        """
        创建固定模板
        
        Args:
            field_name: 字段名（支持别名，用顿号分隔）
            field_value: 字段值
            category: 分类
            description: 说明
            order: 排序
            created_by: 创建人
        
        Returns:
            创建的模板对象
        """
        try:
            template = FixedTemplate(
                field_name=field_name,
                field_value=field_value,
                category=category,
                description=description,
                order=order,
                is_active=True,
                created_by=created_by
            )
            template.save()
            return template
        except Exception as e:
            print(f"❌ 创建固定模板失败: {e}")
            raise

    @staticmethod
    def update_fixed_template(template_id: str, **kwargs) -> bool:
        """
        更新固定模板
        
        Args:
            template_id: 模板ID
            **kwargs: 要更新的字段
        
        Returns:
            是否成功
        """
        try:
            template = DatabaseManager.get_fixed_template_by_id(template_id)
            if not template:
                return False
            
            for key, value in kwargs.items():
                if hasattr(template, key) and value is not None:
                    setattr(template, key, value)
            
            template.save()
            return True
        except Exception as e:
            print(f"❌ 更新固定模板失败: {e}")
            return False

    @staticmethod
    def delete_fixed_template(template_id: str) -> bool:
        """
        删除固定模板
        
        Args:
            template_id: 模板ID
        
        Returns:
            是否成功
        """
        try:
            template = DatabaseManager.get_fixed_template_by_id(template_id)
            if not template:
                return False
            
            template.delete()
            return True
        except Exception as e:
            print(f"❌ 删除固定模板失败: {e}")
            return False
    
    # ==================== 填写记录相关 ====================
    
    @staticmethod
    def create_fill_record(card_id: str, link_id: str, fill_count: int, 
                          total_count: int, success: bool = True, 
                          error_message: str = None) -> FillRecord:
        """
        创建填写记录
        
        Args:
            card_id: 名片ID
            link_id: 链接ID
            fill_count: 成功填写字段数
            total_count: 总配置项数
            success: 是否成功
            error_message: 错误信息
        
        Returns:
            创建的记录对象
        """
        try:
            card = DatabaseManager.get_card_by_id(card_id)
            link = DatabaseManager.get_link_by_id(link_id)
            
            if not card or not link:
                raise ValueError("名片或链接不存在")
            
            record = FillRecord(
                card=card,
                link=link,
                fill_count=fill_count,
                total_count=total_count,
                success=success,
                error_message=error_message
            )
            record.save()
            return record
            
        except Exception as e:
            print(f"❌ 创建填写记录失败: {e}")
            raise
    
    @staticmethod
    def get_all_fill_records(keyword: str = None, limit: int = 20, offset: int = 0) -> Dict:
        """
        获取所有填写记录（支持搜索）
        
        Args:
            keyword: 搜索关键词（用户名、名片名、链接名）
            limit: 数量限制
            offset: 偏移量
            
        Returns:
            Dict: {'records': List[FillRecord], 'total': int}
        """
        try:
            query = FillRecord.objects
            
            if keyword:
                # 1. 查找匹配的用户
                users = User.objects(username__icontains=keyword)
                
                # 2. 查找匹配的名片 (名字匹配 OR 用户匹配)
                cards = Card.objects(Q(name__icontains=keyword) | Q(user__in=users))
                
                # 3. 查找匹配的链接 (名字匹配 OR 用户匹配)
                links = Link.objects(Q(name__icontains=keyword) | Q(user__in=users))
                
                # 4. 组合查询
                query = query.filter(Q(card__in=cards) | Q(link__in=links))
            
            total = query.count()
            records = list(query.order_by('-created_at').skip(offset).limit(limit))
            
            return {
                'records': records,
                'total': total
            }
        except Exception as e:
            print(f"❌ 获取所有填写记录失败: {e}")
            return {'records': [], 'total': 0}

    @staticmethod
    def get_fill_records(card_id: str = None, link_id: str = None, limit: int = 100, offset: int = 0, user=None) -> List[FillRecord]:
        """
        获取填写记录
        
        Args:
            card_id: 筛选名片ID
            link_id: 筛选链接ID
            limit: 限制数量
            offset: 偏移量（用于分页）
            user: 用户对象，如果提供则只获取该用户的记录
        
        Returns:
            记录列表
        """
        try:
            query = FillRecord.objects
            
            # 按用户筛选（通过名片关联）
            if user:
                user_cards = Card.objects(user=user)
                query = query.filter(card__in=user_cards)
            
            # 筛选条件
            if card_id:
                card = DatabaseManager.get_card_by_id(card_id)
                if card:
                    query = query.filter(card=card)
            
            if link_id:
                link = DatabaseManager.get_link_by_id(link_id)
                if link:
                    query = query.filter(link=link)
            
            # 排序、偏移和限制
            return list(query.order_by('-created_at').skip(offset).limit(limit))
            
        except Exception as e:
            print(f"❌ 获取填写记录失败: {e}")
            return []
    
    @staticmethod
    def get_statistics(user=None) -> Dict:
        """
        获取统计信息
        
        Args:
            user: 用户对象，如果提供则只统计该用户的数据
        
        Returns:
            统计数据字典
        """
        from datetime import datetime, timedelta
        
        try:
            # 今日开始时间
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            if user:
                # 获取用户相关的统计
                user_cards = Card.objects(user=user)
                card_ids = [card.id for card in user_cards]
                
                total_records = FillRecord.objects(card__in=card_ids).count()
                success_records = FillRecord.objects(card__in=card_ids, success=True).count()
                today_records = FillRecord.objects(card__in=card_ids, created_at__gte=today_start).count()
                
                return {
                    'total_cards': user_cards.count(),
                    'total_links': Link.objects(user=user).count(),
                    'total_notices': Notice.objects(status='active').count(),
                    'total_records': total_records,
                    'success_records': success_records,
                    'active_links': Link.objects(user=user, status='active').count(),
                    'today_records': today_records,
                    'success_rate': round(success_records / total_records * 100) if total_records > 0 else 0
                }
            else:
                # 全局统计（管理员）
                total_records = FillRecord.objects.count()
                success_records = FillRecord.objects(success=True).count()
                today_records = FillRecord.objects(created_at__gte=today_start).count()
                
                # 计算昨日数据，用于环比
                yesterday_start = today_start - timedelta(days=1)
                yesterday_end = today_start
                yesterday_records = FillRecord.objects(created_at__gte=yesterday_start, created_at__lt=yesterday_end).count()
                
                # 累计填充环比增长 (假设 total 是累积的，环比意义不大，通常看日增量。这里计算日增量的环比)
                # 假设 trend 是指 今日 vs 昨日
                
                return {
                    'total_cards': Card.objects.count(),
                    'total_links': Link.objects.count(),
                    'total_notices': Notice.objects.count(),
                    'total_records': total_records,
                    'success_records': success_records,
                    'active_links': Link.objects(status='active').count(),
                    'today_records': today_records,
                    'yesterday_records': yesterday_records,
                    'success_rate': round(success_records / total_records * 100) if total_records > 0 else 0
                }
        except Exception as e:
            print(f"❌ 获取统计信息失败: {e}")
            return {
                'total_cards': 0,
                'total_links': 0,
                'total_notices': 0,
                'total_records': 0,
                'success_records': 0,
                'active_links': 0,
                'today_records': 0,
                'success_rate': 0
            }
    
    @staticmethod
    def get_daily_fill_stats(days: int = 7) -> List[int]:
        """
        获取过去N天的每日填充数量（包含今天）
        返回: [day1_count, day2_count, ..., today_count]
        """
        from datetime import datetime, timedelta
        stats = []
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        try:
            for i in range(days - 1, -1, -1):
                start_date = today - timedelta(days=i)
                end_date = start_date + timedelta(days=1)
                count = FillRecord.objects(created_at__gte=start_date, created_at__lt=end_date).count()
                stats.append(count)
            return stats
        except Exception as e:
            print(f"❌ 获取每日填充统计失败: {e}")
            return [0] * days

    @staticmethod
    def get_platform_distribution() -> List[Dict]:
        """
        获取平台活跃度分布（基于表单类型识别）
        """
        try:
            # 表单平台规则匹配
            patterns = {
                '腾讯文档': ['docs.qq.com/form'],
                '麦客CRM': ['mikecrm.com'],
                '问卷星': ['wjx.cn'],
                '金数据': ['jsj.top', 'jinshuju.net'],
                '石墨文档': ['shimo.im'],
                '报名工具': ['baominggongju.com'],
                'Credamo见数': ['credamo.com'],
                '问卷网': ['wenjuan.com'],
                '番茄表单': ['fanqier.cn'],
                '飞书问卷': ['feishu.cn'],
                '金山文档': ['kdocs.cn'],
                '腾讯问卷': ['wj.qq.com']
            }
            
            # 获取最近的 1000 条记录进行分析
            recent_links = Link.objects.limit(1000).only('url')
            total = 0
            counts = {k: 0 for k in patterns.keys()}
            counts['其他'] = 0
            
            for link in recent_links:
                matched = False
                url = link.url.lower() if link.url else ""
                for platform, domains in patterns.items():
                    if any(d in url for d in domains):
                        counts[platform] += 1
                        matched = True
                        break
                if not matched:
                    counts['其他'] += 1
                total += 1
            
            if total == 0:
                return []
                
            # 转换为百分比并排序
            result = []
            # 为常见平台分配颜色
            colors = {
                '腾讯文档': '#0052D9',
                '麦客CRM': '#2B3648',
                '问卷星': '#F08800',
                '金数据': '#F5A623',
                '石墨文档': '#3C4043',
                '报名工具': '#E64A19',
                'Credamo见数': '#5B77AF',
                '问卷网': '#FF6A00',
                '番茄表单': '#FF4D4F',
                '飞书问卷': '#3370FF',
                '金山文档': '#CB2D3E',
                '腾讯问卷': '#0052D9',
                '其他': '#9CA3AF'
            }
            
            for name, count in counts.items():
                if count > 0:
                    pct = round(count / total * 100)
                    result.append({'name': name, 'value': pct, 'color': colors.get(name, '#9CA3AF')})
            
            # 按比例降序
            return sorted(result, key=lambda x: x['value'], reverse=True)
            
        except Exception as e:
            print(f"❌ 获取平台分布失败: {e}")
            return []

    @staticmethod
    def get_active_user_count(days: int = 1) -> int:
        """获取活跃用户数（过去 N 天有登录或操作）"""
        from datetime import datetime, timedelta
        from .models import Device
        try:
            start_date = datetime.now() - timedelta(days=days)
            # 1. 登录活跃
            login_users = Device.objects(last_login__gte=start_date).distinct('user')
            # 2. 填充活跃 (可选，如果 device 更新不及时)
            # fill_users = FillRecord.objects(created_at__gte=start_date).distinct('card.user') # 这种关联查询mongoengine不支持直接distinct跨表
            # 简单起见，只查 Device
            return len(login_users)
        except Exception:
            return 0

    # ==================== 通知消息相关 ====================
    
    @staticmethod
    def create_notification(user, title: str, content: str, type: str = 'system', related_id: str = None) -> Notification:
        """创建通知"""
        try:
            notification = Notification(
                user=user,
                type=type,
                title=title,
                content=content,
                related_id=related_id
            )
            notification.save()
            return notification
        except Exception as e:
            print(f"❌ 创建通知失败: {e}")
            return None
            
    @staticmethod
    def get_user_notifications(user, limit: int = 50, only_unread: bool = False) -> List[Notification]:
        """获取用户通知列表"""
        try:
            query = Notification.objects(user=user)
            if only_unread:
                query = query.filter(is_read=False)
            return list(query.order_by('-created_at').limit(limit))
        except Exception as e:
            print(f"❌ 获取通知列表失败: {e}")
            return []
            
    @staticmethod
    def get_unread_notifications_count(user) -> int:
        """获取未读通知数量"""
        try:
            return Notification.objects(user=user, is_read=False).count()
        except Exception:
            return 0
            
    @staticmethod
    def mark_notification_read(notification_id: str) -> bool:
        """标记通知为已读"""
        try:
            n = Notification.objects.get(id=notification_id)
            n.is_read = True
            n.save()
            return True
        except Exception:
            return False
            
    @staticmethod
    def mark_all_notifications_read(user) -> bool:
        """标记所有通知为已读"""
        try:
            Notification.objects(user=user, is_read=False).update(set__is_read=True)
            return True
        except Exception:
            return False
    
    @staticmethod
    def push_field_to_users(field_id: str, user_ids: List[str], admin_user) -> int:
        """
        推送字段给指定用户
        
        Args:
            field_id: 字段ID
            user_ids: 用户ID列表
            admin_user: 操作管理员
            
        Returns:
            成功推送的用户数
        """
        count = 0
        try:
            field = DatabaseManager.get_field_library_by_id(field_id)
            if not field:
                return 0
                
            for uid in user_ids:
                user = DatabaseManager.get_user_by_id(uid)
                if user:
                    DatabaseManager.create_notification(
                        user=user,
                        type='field_push',
                        title='新字段推荐',
                        content=f"管理员向您推荐了新字段：【{field.name}】\n说明：{field.description or '无'}",
                        related_id=str(field.id)
                    )
                    count += 1
            return count
        except Exception as e:
            print(f"❌ 推送字段失败: {e}")
            return 0
    
    # ==================== 名片修改请求相关 ====================
    
    @staticmethod
    def create_card_edit_request(card_id: str, admin, modified_name: str = None,
                                  modified_description: str = None, modified_category: str = None,
                                  modified_configs: List[Dict] = None, admin_comment: str = None) -> CardEditRequest:
        """
        创建名片修改请求
        
        Args:
            card_id: 目标名片ID
            admin: 发起修改的管理员用户对象
            modified_name: 修改后的名称
            modified_description: 修改后的描述
            modified_category: 修改后的分类
            modified_configs: 修改后的配置项列表
            admin_comment: 管理员备注
        
        Returns:
            创建的请求对象
        """
        import json
        try:
            card = DatabaseManager.get_card_by_id(card_id)
            if not card:
                raise ValueError("名片不存在")
            
            # 保存原始数据
            original_configs = [{'key': c.key, 'value': c.value, 'order': c.order} for c in card.configs]
            
            request = CardEditRequest(
                card=card,
                user=card.user,
                admin=admin,
                # 原始数据
                original_name=card.name,
                original_description=card.description,
                original_category=card.category,
                original_configs=json.dumps(original_configs, ensure_ascii=False),
                # 修改后数据
                modified_name=modified_name or card.name,
                modified_description=modified_description if modified_description is not None else card.description,
                modified_category=modified_category or card.category,
                modified_configs=json.dumps(modified_configs, ensure_ascii=False) if modified_configs else json.dumps(original_configs, ensure_ascii=False),
                # 备注
                admin_comment=admin_comment,
                status='pending'
            )
            request.save()
            
            # 创建通知
            DatabaseManager.create_notification(
                user=card.user,
                type='card_edit',
                title='名片修改请求',
                content=f"管理员 {admin.username} 请求修改您的名片【{card.name}】",
                related_id=str(request.id)
            )
            
            return request
        except Exception as e:
            print(f"❌ 创建名片修改请求失败: {e}")
            raise
    
    @staticmethod
    def get_card_edit_requests(user=None, status: str = None, card_id: str = None) -> List[CardEditRequest]:
        """
        获取名片修改请求列表
        
        Args:
            user: 用户对象（获取该用户收到的请求）
            status: 状态筛选 (pending/approved/rejected)
            card_id: 名片ID筛选
        
        Returns:
            请求列表
        """
        try:
            query = CardEditRequest.objects
            
            if user:
                query = query.filter(user=user)
            
            if status:
                query = query.filter(status=status)
                
            if card_id:
                card = DatabaseManager.get_card_by_id(card_id)
                if card:
                    query = query.filter(card=card)
            
            return list(query.order_by('-created_at'))
        except Exception as e:
            print(f"❌ 获取名片修改请求列表失败: {e}")
            return []
    
    @staticmethod
    def get_card_edit_request_by_id(request_id: str) -> Optional[CardEditRequest]:
        """根据ID获取修改请求"""
        try:
            return CardEditRequest.objects.get(id=request_id)
        except (DoesNotExist, ValidationError):
            return None
    
    @staticmethod
    def get_pending_edit_requests_count(user) -> int:
        """获取用户待处理的修改请求数量"""
        try:
            return CardEditRequest.objects(user=user, status='pending').count()
        except Exception:
            return 0
    
    @staticmethod
    def approve_card_edit_request(request_id: str, user_comment: str = None) -> bool:
        """
        同意名片修改请求
        
        Args:
            request_id: 请求ID
            user_comment: 用户备注
        
        Returns:
            是否成功
        """
        import json
        from datetime import datetime
        try:
            request = DatabaseManager.get_card_edit_request_by_id(request_id)
            if not request or request.status != 'pending':
                return False
            
            # 应用修改到名片
            card = request.card
            card.name = request.modified_name
            card.description = request.modified_description
            card.category = request.modified_category
            
            # 更新配置项
            modified_configs = json.loads(request.modified_configs) if request.modified_configs else []
            config_items = []
            for i, config in enumerate(modified_configs):
                config_item = CardConfigItem(
                    key=config['key'],
                    value=config['value'],
                    order=config.get('order', i)
                )
                config_items.append(config_item)
            card.configs = config_items
            card.save()
            
            # 更新请求状态
            request.status = 'approved'
            request.user_comment = user_comment
            request.processed_at = datetime.now()
            request.save()
            
            # 更新通知状态（如果有关联的未读通知）
            # 这里比较简单，就不特意去找通知了，用户点击处理时通常已经看到了通知
            
            return True
        except Exception as e:
            print(f"❌ 同意名片修改请求失败: {e}")
            return False
    
    @staticmethod
    def reject_card_edit_request(request_id: str, user_comment: str = None) -> bool:
        """
        拒绝名片修改请求
        
        Args:
            request_id: 请求ID
            user_comment: 拒绝理由
        
        Returns:
            是否成功
        """
        from datetime import datetime
        try:
            request = DatabaseManager.get_card_edit_request_by_id(request_id)
            if not request or request.status != 'pending':
                return False
            
            request.status = 'rejected'
            request.user_comment = user_comment
            request.processed_at = datetime.now()
            request.save()
            
            return True
        except Exception as e:
            print(f"❌ 拒绝名片修改请求失败: {e}")
            return False
    
    @staticmethod
    def delete_card_edit_request(request_id: str) -> bool:
        """删除名片修改请求"""
        try:
            request = DatabaseManager.get_card_edit_request_by_id(request_id)
            if not request:
                return False
            request.delete()
            return True
        except Exception as e:
            print(f"❌ 删除名片修改请求失败: {e}")
            return False
