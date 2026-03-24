"""
报名工具专用填充器
https://p.baominggongju.com

由于报名工具需要扫码登录并通过API提交表单，无法使用常规的JavaScript注入方式，
因此需要专门的处理模块来：
1. 获取登录二维码
2. 轮询登录状态
3. 获取表单结构
4. 渲染表单界面
5. 提交表单数据
"""

import re
import json
import time
import base64
import requests
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Callable
from urllib.parse import urlparse, parse_qs

# RSA 签名生成
def generate_baoming_signature(eid: str) -> str:
    """
    生成报名工具的 _a 签名参数
    
    JSEncrypt 库的 encrypt() 方法返回的是 Base64 编码字符串
    
    Args:
        eid: 报名活动ID
        
    Returns:
        str: Base64 编码的 RSA 加密签名（与 JSEncrypt 一致）
    """
    try:
        from Crypto.PublicKey import RSA
        from Crypto.Cipher import PKCS1_v1_5
        
        public_key_pem = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCjI8E8LT0fwFekelMMuTWuaIfo
fK69lyNIo+Vz0CGdfE3rLSIH94S2A3Q+bg+9/VnImvfXzcDVmqwHwC4hHPHs6hc6
ufq0gfivTPms3kwX74F5qLMr70j4iZLt/PCkU+uyQ56KmRW4foCV4RPX8o8QZVss
6eifHaeUeJxKM556ewIDAQAB
-----END PUBLIC KEY-----"""
        
        # 使用秒级时间戳（与 JS 代码一致: Math.round(Date.now() / 1e3)）
        timestamp = round(time.time())
        plain_text = f"{eid}{timestamp}"
        print(f"  🔐 [签名] plain_text: {plain_text}")
        
        public_key = RSA.import_key(public_key_pem)
        cipher = PKCS1_v1_5.new(public_key)
        encrypted = cipher.encrypt(plain_text.encode('utf-8'))
        
        # JSEncrypt 的 encrypt() 返回 Base64 编码字符串
        signature = base64.b64encode(encrypted).decode('utf-8')
        print(f"  🔐 [签名] 生成 Base64 签名，长度: {len(signature)}")
        return signature
    except ImportError:
        print("  ⚠️ [报名工具] 缺少 pycryptodome 库，无法生成签名")
        return ""
    except Exception as e:
        print(f"  ⚠️ [报名工具] 生成签名失败: {e}")
        return ""


class BaomingToolAPI:
    """报名工具API封装"""
    
    BASE_URL = "https://api-xcx-qunsou.weiyoubot.cn/xcx"
    
    def __init__(self):
        self.access_token: Optional[str] = None
        self.eid: Optional[str] = None
        self.info_id: Optional[str] = None
        self.user_info: Optional[Dict] = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
            'Referer': 'https://p.baominggongju.com/'
        })
        
    def extract_eid(self, url: str) -> Optional[str]:
        """从URL中提取eid"""
        # 尝试从查询参数中提取
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        if 'eid' in params:
            self.eid = params['eid'][0]
            return self.eid
        
        # 尝试从路径中提取
        match = re.search(r'eid=([a-f0-9]+)', url)
        if match:
            self.eid = match.group(1)
            return self.eid
            
        return None
    
    def get_qr_code(self) -> Tuple[bool, str, Optional[str]]:
        """
        获取登录二维码
        
        Returns:
            Tuple[bool, str, Optional[str]]: (成功标志, 消息/二维码数据, 登录code)
        """
        try:
            url = f"{self.BASE_URL}/enroll_web/v1/pc_code"
            print(f"  📡 [API] GET {url}")
            response = self.session.get(url, timeout=10)
            print(f"  📡 [API] 响应状态码: {response.status_code}")
            data = response.json()
            print(f"  📡 [API] 响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            if data.get('sta') == 0:
                qr_data = data.get('data', {})
                qrcode = qr_data.get('qrcode', '')
                code = qr_data.get('code', '')
                print(f"  📡 [API] 获取二维码成功, code={code[:20]}...")
                return True, qrcode, code
            else:
                print(f"  📡 [API] 获取二维码失败: {data.get('msg')}")
                return False, data.get('msg', '获取二维码失败'), None
                
        except Exception as e:
            print(f"  📡 [API] 请求异常: {e}")
            return False, f"请求失败: {str(e)}", None
    
    def poll_login_status(self, code: str) -> Tuple[int, str, Optional[Dict]]:
        """
        轮询登录状态
        
        Args:
            code: 二维码对应的code
            
        Returns:
            Tuple[int, str, Optional[Dict]]: 
                (状态码, 消息, 用户信息)
                状态码: 0=成功, -1=等待中, 其他=失败
        """
        try:
            url = f"{self.BASE_URL}/enroll_web/v1/pc_login"
            params = {
                'code': code,
                'source': 'h5'
            }
            print(f"  📡 [API] GET {url}?code={code[:20]}...&source=h5")
            response = self.session.get(url, params=params, timeout=10)
            print(f"  📡 [API] 响应状态码: {response.status_code}")
            data = response.json()
            print(f"  📡 [API] 响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            sta = data.get('sta', -99)
            msg = data.get('msg', '')
            
            if sta == 0:
                user_data = data.get('data', {})
                self.access_token = user_data.get('access_token')
                self.user_info = user_data
                print(f"  📡 [API] 登录成功, 用户: {user_data.get('uname', '未知')}, token={self.access_token[:20] if self.access_token else 'None'}...")
                return 0, '登录成功', user_data
            elif sta == -1:
                return -1, '等待扫码...', None
            else:
                print(f"  📡 [API] 登录失败: {msg}")
                return sta, msg, None
                
        except Exception as e:
            print(f"  📡 [API] 请求异常: {e}")
            return -99, f"请求失败: {str(e)}", None
    
    def get_short_detail(self) -> Tuple[bool, str, Optional[Dict]]:
        """
        获取表单简要信息（包含标题sign_name）
        
        Returns:
            Tuple[bool, str, Optional[Dict]]: (成功标志, 消息, 详情数据)
        """
        if not self.eid:
            print(f"  📡 [API] get_short_detail 缺少eid")
            return False, '缺少eid', None
            
        try:
            url = f"{self.BASE_URL}/enroll/v1/short_detail"
            params = {
                'eid': self.eid
            }
            print(f"  📡 [API] GET {url}?eid={self.eid}")
            response = self.session.get(url, params=params, timeout=10)
            print(f"  📡 [API] 响应状态码: {response.status_code}")
            data = response.json()
            print(f"  📡 [API] 响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            if data.get('msg') == 'ok' or data.get('sta') == 0:
                detail = data.get('data', {})
                print(f"  📡 [API] 获取简要信息成功, 标题: {detail.get('title', detail.get('sign_name', ''))[:30]}")
                return True, '获取成功', detail
            else:
                print(f"  📡 [API] 获取简要信息失败: {data.get('msg')}")
                return False, data.get('msg', '获取简要信息失败'), None
                
        except Exception as e:
            print(f"  📡 [API] 请求异常: {e}")
            return False, f"请求失败: {str(e)}", None
    
    def get_enroll_detail(self) -> Tuple[bool, str, Optional[str]]:
        """
        获取报名详情，提取 info_id
        
        Returns:
            Tuple[bool, str, Optional[str]]: (成功标志, 消息, info_id)
        """
        if not self.eid or not self.access_token:
            print(f"  📡 [API] get_enroll_detail 缺少eid或access_token")
            return False, '缺少eid或access_token', None
            
        try:
            url = f"{self.BASE_URL}/enroll/v3/detail"
            params = {
                'eid': self.eid,
                'access_token': self.access_token,
                'referer': '',
                'spider': 'h5'
            }
            print(f"  📡 [API] GET {url}?eid={self.eid}&access_token={self.access_token[:20]}...")
            response = self.session.get(url, params=params, timeout=10)
            print(f"  📡 [API] 响应状态码: {response.status_code}")
            data = response.json()
            print(f"  📡 [API] 响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            if data.get('sta') == 0:
                detail = data.get('data', {})
                info_id = detail.get('info_id')
                if info_id:
                    self.info_id = info_id
                    print(f"  📡 [API] 获取报名详情成功, info_id={info_id}")
                    return True, '获取成功', self.info_id
                else:
                    # API 返回成功但没有 info_id，说明用户未报名过
                    print(f"  📡 [API] detail 中没有 info_id，用户可能未报名过")
                    return False, '未找到已有报名记录', None
            else:
                print(f"  📡 [API] 获取报名详情失败: {data.get('msg')}")
                return False, data.get('msg', '获取详情失败'), None
                
        except Exception as e:
            print(f"  📡 [API] 请求异常: {e}")
            return False, f"请求失败: {str(e)}", None
    
    def get_form_fields(self) -> Tuple[bool, str, Optional[List[Dict]]]:
        """
        获取表单字段信息
        
        Returns:
            Tuple[bool, str, Optional[List[Dict]]]: (成功标志, 消息, 字段列表)
        """
        if not self.eid or not self.access_token:
            print(f"  📡 [API] get_form_fields 缺少eid或access_token")
            return False, '缺少eid或access_token', None
            
        try:
            url = f"{self.BASE_URL}/enroll/v1/req_detail"
            params = {
                'access_token': self.access_token,
                'eid': self.eid
            }
            print(f"  📡 [API] GET {url}?eid={self.eid}&access_token={self.access_token[:20]}...")
            response = self.session.get(url, params=params, timeout=10)
            print(f"  📡 [API] 响应状态码: {response.status_code}")
            data = response.json()
            print(f"  📡 [API] 响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
            
            if data.get('sta') == 0:
                form_data = data.get('data', {})
                req_info = form_data.get('req_info', [])
                print(f"  📡 [API] 获取表单字段成功, 共 {len(req_info)} 个字段")
                # 打印每个字段名
                for i, field in enumerate(req_info):
                    print(f"       字段{i+1}: {field.get('field_name', '未知')}")
                return True, '获取成功', req_info
            else:
                print(f"  📡 [API] 获取表单字段失败: {data.get('msg')}")
                return False, data.get('msg', '获取表单字段失败'), None
                
        except Exception as e:
            print(f"  📡 [API] 请求异常: {e}")
            return False, f"请求失败: {str(e)}", None
    
    def submit_form(self, form_data: List[Dict]) -> Tuple[bool, str]:
        """
        提交表单（先新增再更新）
        
        Args:
            form_data: 表单数据列表，每项包含 field_name, field_key, field_value, ignore
            
        Returns:
            Tuple[bool, str]: (成功标志, 消息)
        """
        if not self.eid or not self.access_token:
            return False, '缺少eid或access_token'
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        # 调用新增接口 enroll/v5/enroll
        try:
            # 生成签名
            signature = generate_baoming_signature(self.eid)
            print(f"  🔐 [报名工具] 生成签名: eid={self.eid}, _a={signature[:50] if signature else 'None'}...")
            if not signature:
                print(f"  ❌ [报名工具] 签名生成失败")
                return False, '签名生成失败，请检查 pycryptodome 库是否安装'
            
            enroll_url = f"{self.BASE_URL}/enroll/v5/enroll"
            enroll_payload = {
                'eid': self.eid,
                'info': form_data,
                'on_behalf': 1,
                'items': [],
                'access_token': self.access_token,
                'referer': '',
                'from': 'h5',
                '_a': signature
            }
            
            print(f"  📤 [报名工具] 调用新增接口: {enroll_url}")
            print(f"  📤 [报名工具] 完整请求参数:")
            import json as json_module
            print(json_module.dumps(enroll_payload, ensure_ascii=False, indent=2))
            response = self.session.post(enroll_url, json=enroll_payload, headers=headers, timeout=15)
            print(f"  📥 [报名工具] 新增接口状态码: {response.status_code}")
            print(f"  📥 [报名工具] 新增接口原始响应: {response.text[:500] if response.text else '空响应'}")
            
            if not response.text:
                print(f"  ⚠️ [报名工具] 新增接口返回空响应，跳过")
                data = {'sta': -1, 'msg': '空响应'}
            else:
                try:
                    data = response.json()
                except Exception as json_err:
                    print(f"  ⚠️ [报名工具] JSON解析失败: {json_err}")
                    data = {'sta': -1, 'msg': f'响应解析失败: {response.text[:100]}'}
            
            print(f"  📥 [报名工具] 新增接口响应: {data}")
            
            if data.get('sta') != 0:
                error_msg = data.get('msg', '提交失败')
                print(f"  ❌ [报名工具] 新增接口报错: {error_msg}")
                return False, f'提交失败: {error_msg}'
            else:
                print(f"  ✅ [报名工具] 新增接口调用成功")
                # 新增成功后，更新 info_id
                new_info_id = data.get('data', {}).get('info_id')
                if new_info_id:
                    self.info_id = new_info_id
                    print(f"  ✅ [报名工具] 获取到新 info_id: {new_info_id}")
                return True, '提交成功'
                    
        except Exception as e:
            print(f"  ❌ [报名工具] 新增接口异常: {e}")
            return False, f'提交失败: {str(e)}'


class BaomingToolFiller:
    """报名工具填充器，处理整个填充流程"""
    
    def __init__(self):
        self.api = BaomingToolAPI()
        self.form_fields: List[Dict] = []
        self.login_code: Optional[str] = None
        self.card_id: Optional[str] = None
        self.eid: Optional[str] = None
        self.form_title: Optional[str] = None  # 表单标题（sign_name）
        self.form_short_info: Optional[Dict] = None  # 表单简要信息
        
    def initialize(self, url: str, card_id: Optional[str] = None) -> Tuple[bool, str]:
        """
        初始化填充器
        
        Args:
            url: 报名工具链接
            card_id: 名片ID（可选，用于区分不同用户的登录状态）
            
        Returns:
            Tuple[bool, str]: (成功标志, 消息)
        """
        self.card_id = str(card_id) if card_id else "default"
        
        eid = self.api.extract_eid(url)
        if not eid:
            return False, '无法从链接中提取eid'
            
        self.eid = eid
        return True, f'已提取eid: {eid}'
    
    def get_qr_code(self) -> Tuple[bool, str, Optional[str]]:
        """获取登录二维码"""
        success, data, code = self.api.get_qr_code()
        if success:
            self.login_code = code
        return success, data, code
    
    def check_login(self) -> Tuple[int, str, Optional[Dict]]:
        """检查登录状态"""
        if not self.login_code:
            return -99, '未获取登录二维码', None
        status, msg, user_data = self.api.poll_login_status(self.login_code)
        
        # 登录成功后，保存 Token
        if status == 0 and user_data:
            self._save_token(user_data)
            
        return status, msg, user_data
    
    def try_restore_login(self) -> bool:
        """
        尝试恢复登录状态
        
        ⚡️ 优化：同一名片的所有报名工具链接共享 token
        只要该名片之前登录过任意一个报名工具活动，其他活动也自动登录
        """
        if not self.card_id:
            return False
            
        token_data = self._load_token()
        if not token_data:
            return False
            
        access_token = token_data.get('access_token')
        if not access_token:
            return False
            
        # 验证 Token 是否有效
        self.api.access_token = access_token
        self.api.user_info = token_data # 恢复用户信息
        
        print(f"  ✅ [报名工具] 恢复登录状态: {token_data.get('uname', '用户')} (名片ID: {self.card_id})")
        return True

    def _save_token(self, user_data: Dict):
        """保存 Token 到数据库"""
        try:
            from database.models import BaomingToken, Card
            
            if not self.card_id:
                print(f"  ⚠️ [报名工具] 保存 Token 失败: 缺少 card_id")
                return
            
            # 查找名片
            try:
                card = Card.objects(id=self.card_id).first()
                if not card:
                    print(f"  ⚠️ [报名工具] 保存 Token 失败: 名片不存在 (ID: {self.card_id})")
                    return
            except Exception as e:
                print(f"  ⚠️ [报名工具] 保存 Token 失败: 名片查询异常 - {e}")
                return
            
            # 查找或创建 Token 记录
            token_record = BaomingToken.objects(card=card).first()
            
            if token_record:
                # 更新现有记录
                token_record.access_token = user_data.get('access_token', '')
                token_record.uname = user_data.get('uname', '')
                token_record.pic = user_data.get('pic', '')
                token_record.unionid = user_data.get('unionid', '')
                token_record.last_used = datetime.now()
                token_record.save()
                print(f"  💾 [报名工具] Token 已更新: 名片 '{card.name}' (ID: {self.card_id})")
            else:
                # 创建新记录
                token_record = BaomingToken(
                    card=card,
                    access_token=user_data.get('access_token', ''),
                    uname=user_data.get('uname', ''),
                    pic=user_data.get('pic', ''),
                    unionid=user_data.get('unionid', '')
                )
                token_record.save()
                print(f"  💾 [报名工具] Token 已保存: 名片 '{card.name}' (ID: {self.card_id})")
                
        except Exception as e:
            print(f"  ⚠️ [报名工具] 保存 Token 失败: {e}")
            import traceback
            traceback.print_exc()

    def _load_token(self) -> Optional[Dict]:
        """从数据库加载 Token"""
        try:
            from database.models import BaomingToken, Card

            if not self.card_id:
                return None
            
            # 查找名片
            try:
                card = Card.objects(id=self.card_id).first()
                if not card:
                    return None
            except:
                return None
            
            # 查找 Token 记录
            token_record = BaomingToken.objects(card=card).first()
            
            if token_record:
                # 更新最后使用时间
                token_record.last_used = datetime.now()
                token_record.save()
                
                return {
                    'access_token': token_record.access_token,
                    'uname': token_record.uname,
                    'pic': token_record.pic,
                    'unionid': token_record.unionid
                }
            
            return None
            
        except Exception as e:
            print(f"  ⚠️ [报名工具] 加载 Token 失败: {e}")
            return None
    
    def _clear_token(self):
        """清空数据库中的 Token（token 失效时调用）"""
        try:
            from database.models import BaomingToken, Card
            
            if not self.card_id:
                return
            
            # 查找名片
            try:
                card = Card.objects(id=self.card_id).first()
                if not card:
                    return
            except:
                return
            
            # 删除 Token 记录
            token_record = BaomingToken.objects(card=card).first()
            if token_record:
                token_record.delete()
                print(f"  🗑️ [报名工具] Token 已清空: 名片 '{card.name}' (ID: {self.card_id})")
                
        except Exception as e:
            print(f"  ⚠️ [报名工具] 清空 Token 失败: {e}")
    
    def _is_token_invalid_error(self, msg: str) -> bool:
        """检查错误消息是否表示 token 失效"""
        invalid_keywords = ['invalid access_token', 'access_token', 'token', '登录', '过期', '失效', '无效']
        msg_lower = msg.lower()
        return any(keyword.lower() in msg_lower for keyword in invalid_keywords)
            
    def load_form(self) -> Tuple[bool, str]:
        """加载表单数据"""
        # 先获取简要信息（包含表单标题）
        success, msg, short_info = self.api.get_short_detail()
        if success and short_info:
            self.form_short_info = short_info
            # 从 short_detail 接口的 title 字段获取标题
            self.form_title = short_info.get('title', '')
            # 如果 title 为空，回退到 sign_name
            if not self.form_title:
                self.form_title = short_info.get('sign_name', '')
            print(f"  📋 [报名工具] 表单标题: {self.form_title[:50]}..." if len(self.form_title) > 50 else f"  📋 [报名工具] 表单标题: {self.form_title}")
        
        # 获取详情（尝试获取已有的 info_id，首次报名时可能没有）
        success, msg, info_id = self.api.get_enroll_detail()
        if not success:
            # 检测 token 是否失效
            if self._is_token_invalid_error(msg):
                print(f"  ⚠️ [报名工具] Token 已失效，清空本地缓存: {msg}")
                self._clear_token()
                self.api.access_token = None
                self.api.user_info = None
                return False, msg
            # 未找到已有报名记录是正常的（首次报名），继续获取表单字段
            if '未找到已有报名记录' in msg:
                print(f"  ℹ️ [报名工具] 首次报名，继续加载表单字段...")
            else:
                # 其他错误则返回
                return False, msg
            
        # 再获取表单字段
        success, msg, fields = self.api.get_form_fields()
        if not success:
            # 检测 token 是否失效
            if self._is_token_invalid_error(msg):
                print(f"  ⚠️ [报名工具] Token 已失效，清空本地缓存: {msg}")
                self._clear_token()
                self.api.access_token = None
                self.api.user_info = None
            return False, msg
            
        self.form_fields = fields or []
        return True, f'已加载 {len(self.form_fields)} 个字段'
    
    def get_form_title(self) -> str:
        """获取表单标题"""
        return self.form_title or ""
    
    def match_and_fill(self, card_config: List[Dict]) -> List[Dict]:
        """
        匹配名片配置并填充表单（使用共享匹配算法）
        
        Args:
            card_config: 名片配置项列表，每项包含 name(字段名) 和 value(值)
            
        Returns:
            List[Dict]: 填充后的表单数据
        """
        from core.tencent_docs_filler import SharedMatchAlgorithm
        
        result = []
        
        print(f"  🎯 [报名工具] 开始智能匹配（使用共享算法），共有 {len(self.form_fields)} 个字段，{len(card_config)} 个名片项")
        
        for index, field in enumerate(self.form_fields):
            field_name = field.get('field_name', '')
            field_key = field.get('field_key', '')
            ignore = field.get('ignore', 0)
            
            best_match = {
                'value': '',
                'score': 0,
                'matched_key': None
            }
            
            print(f"  📋 字段 #{index+1}: \"{field_name}\"")
            
            # 遍历所有名片配置找最佳匹配
            for config in card_config:
                config_name = config.get('name', '')  # 名片上的key
                config_value = config.get('value', '')
                
                # 使用共享匹配算法
                score_result = SharedMatchAlgorithm.match_keyword(field_name, config_name)

                if score_result['matched'] and score_result['score'] > best_match['score']:
                    best_match = {
                        'value': config_value,
                        'score': score_result['score'],
                        'matched_key': config_name
                    }
            
            matched_value = ''
            if best_match['score'] >= 50:  # 阈值50
                matched_value = best_match['value']
                val_preview = str(matched_value)[:20] + "..." if len(str(matched_value)) > 20 else str(matched_value)
                print(f"     ✅ 选中: \"{best_match['matched_key']}\" = \"{val_preview}\" (分数: {best_match['score']})")
            else:
                print(f"     ❌ 未匹配 (最高分: {best_match['score']})")

            # ⚡️ 核心修复：处理选择题的 Key 映射
            # 报名工具 API 对于选择题（单选/下拉），要求提交 new_field_value=key
            new_field_value = None
            options = field.get('new_options', [])
            field_type = field.get('field_type', 0)
            
            if options and matched_value:
                print(f"     🔄 [调试] 尝试匹配选项 Key，当前值: {matched_value}")
                matched_option = None
                
                # 1. 精确匹配
                for opt in options:
                    if str(opt.get('value', '')).strip() == str(matched_value).strip():
                        matched_option = opt
                        break
                
                # 2. 如果没精确匹配，尝试模糊匹配
                if not matched_option:
                    for opt in options:
                        opt_val = str(opt.get('value', '')).strip()
                        # 选项值包含名片值，或名片值包含选项值
                        if opt_val and (str(matched_value) in opt_val or opt_val in str(matched_value)):
                            matched_option = opt
                            print(f"     ⚠️ [调试] 模糊匹配成功: {matched_value} -> {opt_val}")
                            break
                            
                if matched_option:
                    new_field_value = matched_option.get('key')
                    # 将 field_value 更新为标准选项文本，确保提交数据一致性
                    # 注意：抓包数据显示 field_value 是文本，new_field_value 是 Key
                    matched_value = matched_option.get('value', matched_value)
                    print(f"     ✅ [调试] 匹配到选项 Key: {new_field_value} ({matched_value})")
                else:
                    print(f"     ❌ [调试] 未能在选项中找到匹配项")

            item = {
                'field_name': field_name,
                'field_key': field_key,
                'field_value': matched_value,
                'ignore': ignore,
                # ⚡️ 传递元数据，防止 GUI 匹配失败导致字段类型丢失
                'field_type': field_type,
                'options': options,
                'require': field.get('require', 0),
                'field_desc': field.get('field_desc', '')
            }
            
            # 只有匹配到 Key 才添加 new_field_value
            if new_field_value:
                item['new_field_value'] = new_field_value
                
            result.append(item)
        
        return result

    def _match_field_name(self, form_field: str, config_name: str) -> bool:
        """保留旧方法接口，使用共享算法（为了兼容性）"""
        from core.tencent_docs_filler import SharedMatchAlgorithm
        result = SharedMatchAlgorithm.match_keyword(form_field, config_name)
        return result['matched']
    
    def submit(self, form_data: List[Dict]) -> Tuple[bool, str]:
        """提交表单"""
        return self.api.submit_form(form_data)
    
    def get_field_names(self) -> List[str]:
        """获取所有字段名称"""
        return [f.get('field_name', '') for f in self.form_fields]

