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
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            if data.get('sta') == 0:
                qr_data = data.get('data', {})
                qrcode = qr_data.get('qrcode', '')
                code = qr_data.get('code', '')
                return True, qrcode, code
            else:
                return False, data.get('msg', '获取二维码失败'), None
                
        except Exception as e:
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
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            sta = data.get('sta', -99)
            msg = data.get('msg', '')
            
            if sta == 0:
                user_data = data.get('data', {})
                self.access_token = user_data.get('access_token')
                self.user_info = user_data
                return 0, '登录成功', user_data
            elif sta == -1:
                return -1, '等待扫码...', None
            else:
                return sta, msg, None
                
        except Exception as e:
            return -99, f"请求失败: {str(e)}", None
    
    def get_short_detail(self) -> Tuple[bool, str, Optional[Dict]]:
        """
        获取表单简要信息（包含标题sign_name）
        
        Returns:
            Tuple[bool, str, Optional[Dict]]: (成功标志, 消息, 详情数据)
        """
        if not self.eid:
            return False, '缺少eid', None
            
        try:
            url = f"{self.BASE_URL}/enroll/v1/short_detail"
            params = {
                'eid': self.eid
            }
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('msg') == 'ok' or data.get('sta') == 0:
                detail = data.get('data', {})
                return True, '获取成功', detail
            else:
                return False, data.get('msg', '获取简要信息失败'), None
                
        except Exception as e:
            return False, f"请求失败: {str(e)}", None
    
    def get_enroll_detail(self) -> Tuple[bool, str, Optional[str]]:
        """
        获取报名详情，提取 info_id
        
        Returns:
            Tuple[bool, str, Optional[str]]: (成功标志, 消息, info_id)
        """
        if not self.eid or not self.access_token:
            return False, '缺少eid或access_token', None
            
        try:
            url = f"{self.BASE_URL}/enroll/v3/detail"
            params = {
                'eid': self.eid,
                'access_token': self.access_token,
                'referer': '',
                'spider': 'h5'
            }
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('sta') == 0:
                detail = data.get('data', {})
                info_id = detail.get('info_id')
                if info_id:
                    self.info_id = info_id
                    return True, '获取成功', self.info_id
                else:
                    # API 返回成功但没有 info_id，说明用户未报名过
                    print(f"  ⚠️ [报名工具] detail 中没有 info_id，用户可能未报名过")
                    return False, '未找到已有报名记录', None
            else:
                return False, data.get('msg', '获取详情失败'), None
                
        except Exception as e:
            return False, f"请求失败: {str(e)}", None
    
    def get_form_fields(self) -> Tuple[bool, str, Optional[List[Dict]]]:
        """
        获取表单字段信息
        
        Returns:
            Tuple[bool, str, Optional[List[Dict]]]: (成功标志, 消息, 字段列表)
        """
        if not self.eid or not self.access_token:
            return False, '缺少eid或access_token', None
            
        try:
            url = f"{self.BASE_URL}/enroll/v1/req_detail"
            params = {
                'access_token': self.access_token,
                'eid': self.eid
            }
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('sta') == 0:
                form_data = data.get('data', {})
                req_info = form_data.get('req_info', [])
                return True, '获取成功', req_info
            else:
                return False, data.get('msg', '获取表单字段失败'), None
                
        except Exception as e:
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
        
        # 第一步：调用新增接口 enroll/v5/enroll
        try:
            # 生成签名
            signature = generate_baoming_signature(self.eid)
            print(f"  🔐 [报名工具] 生成签名: eid={self.eid}, _a={signature[:50] if signature else 'None'}...")
            if not signature:
                print(f"  ⚠️ [报名工具] 签名生成失败，尝试直接获取已有记录...")
                # 签名失败时，尝试获取已有的 info_id
                success, msg, info_id = self.get_enroll_detail()
                if success and info_id:
                    self.info_id = info_id  # 确保赋值
                    print(f"  ✅ [报名工具] 获取到已有 info_id: {info_id}")
                # 跳过新增接口，直接走更新
                raise Exception("签名生成失败")
            
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
                error_msg = data.get('msg', '')
                
                # 如果返回限制提交次数的消息，直接返回给用户
                if '只允许提交' in error_msg or '提交次数' in error_msg:
                    print(f"  ⚠️ [报名工具] 提交受限: {error_msg}")
                    return False, error_msg
                
                # 如果返回 "您已报名过" 等错误，说明之前报过名，直接走更新接口
                if '已报名' in error_msg or '已经报名' in error_msg:
                    print(f"  ⚡️ [报名工具] 已报名过，直接更新...")
                    # 已报名过的情况下，需要先获取 info_id
                    if not self.info_id:
                        success, msg, info_id = self.get_enroll_detail()
                        if success and info_id:
                            self.info_id = info_id  # 确保赋值
                            print(f"  ✅ [报名工具] 获取到已有 info_id: {info_id}")
                        else:
                            print(f"  ⚠️ [报名工具] 获取已有 info_id 失败: {msg}")
                else:
                    print(f"  ⚠️ [报名工具] 新增接口返回: {error_msg}")
                    # 尝试获取 info_id（可能是已经报过名但接口返回其他错误）
                    if not self.info_id:
                        success, msg, info_id = self.get_enroll_detail()
                        if success and info_id:
                            self.info_id = info_id  # 确保赋值
                            print(f"  ✅ [报名工具] 获取到已有 info_id: {info_id}")
                        else:
                            print(f"  ⚠️ [报名工具] 获取已有 info_id 失败: {msg}")
            else:
                print(f"  ✅ [报名工具] 新增接口调用成功")
                # 新增成功后，更新 info_id
                new_info_id = data.get('data', {}).get('info_id')
                if new_info_id:
                    self.info_id = new_info_id
                    print(f"  ✅ [报名工具] 获取到新 info_id: {new_info_id}")
                    
        except Exception as e:
            print(f"  ⚠️ [报名工具] 新增接口异常: {e}，尝试直接更新...")
            # 尝试获取已有的 info_id
            if not self.info_id:
                try:
                    success, msg, info_id = self.get_enroll_detail()
                    if success and info_id:
                        self.info_id = info_id  # 确保赋值
                        print(f"  ✅ [报名工具] 获取到已有 info_id: {info_id}")
                    else:
                        print(f"  ⚠️ [报名工具] 获取已有 info_id 失败: {msg}")
                except Exception as detail_err:
                    print(f"  ⚠️ [报名工具] 获取 info_id 异常: {detail_err}")
        
        # 第二步：调用更新接口 enroll/v1/user_update
        if not self.info_id:
            print(f"  ❌ [报名工具] 无法获取 info_id，可能原因：")
            print(f"     1. 新增接口调用失败且用户未报名过（无历史记录）")
            print(f"     2. 服务器返回异常")
            print(f"     3. 签名验证失败")
            return False, '缺少info_id，无法更新。请检查：1.签名是否正确 2.是否为首次报名但新增接口失败'
            
        try:
            update_url = f"{self.BASE_URL}/enroll/v1/user_update"
            update_payload = {
                'info_id': self.info_id,
                'info': form_data,
                'anon': 0,
                'access_token': self.access_token,
                'from': 'xcx'
            }
            
            print(f"  📤 [报名工具] 调用更新接口...")
            response = self.session.post(update_url, json=update_payload, headers=headers, timeout=15)
            data = response.json()
            
            if data.get('sta') == 0:
                print(f"  ✅ [报名工具] 更新接口调用成功")
                return True, '提交成功'
            else:
                return False, data.get('msg', '提交失败')
                
        except Exception as e:
            return False, f"请求失败: {str(e)}"


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

    def _get_token_file_path(self):
        """获取 Token 存储路径"""
        import os
        from pathlib import Path
        # 存放在用户目录的 .auto-form-filler 文件夹下
        home = Path.home()
        config_dir = home / '.auto-form-filler'
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / 'baoming_tokens.json'

    def _get_storage_key(self) -> str:
        """
        生成存储 Key: card_{card_id}
        
        ⚡️ 优化：只使用 card_id 作为 key，这样同一名片的所有报名工具链接共享 token
        （之前是 card_{card_id}_eid_{eid}，每个活动都需要单独登录）
        """
        return f"card_{self.card_id}"

    def _save_token(self, user_data: Dict):
        """保存 Token 到本地文件（支持多账号）"""
        try:
            file_path = self._get_token_file_path()
            key = self._get_storage_key()
            
            # 读取现有数据
            all_tokens = {}
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        all_tokens = json.load(f)
                except:
                    all_tokens = {}
            
            # 更新特定 Key 的数据
            # 添加保存时间
            user_data['_save_time'] = time.time()
            all_tokens[key] = user_data
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(all_tokens, f, ensure_ascii=False, indent=2)
            print(f"  💾 [报名工具] Token 已保存: {key}")
        except Exception as e:
            print(f"  ⚠️ [报名工具] 保存 Token 失败: {e}")

    def _load_token(self) -> Optional[Dict]:
        """从本地文件加载特定 Key 的 Token"""
        try:
            file_path = self._get_token_file_path()
            if not file_path.exists():
                return None
            
            key = self._get_storage_key()
            
            with open(file_path, 'r', encoding='utf-8') as f:
                all_tokens = json.load(f)
                return all_tokens.get(key)
        except Exception as e:
            print(f"  ⚠️ [报名工具] 加载 Token 失败: {e}")
            return None
    
    def _clear_token(self):
        """清空当前 Key 的 Token（token 失效时调用）"""
        try:
            file_path = self._get_token_file_path()
            if not file_path.exists():
                return
            
            key = self._get_storage_key()
            
            with open(file_path, 'r', encoding='utf-8') as f:
                all_tokens = json.load(f)
            
            if key in all_tokens:
                del all_tokens[key]
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(all_tokens, f, ensure_ascii=False, indent=2)
                print(f"  🗑️ [报名工具] Token 已清空: {key}")
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
        匹配名片配置并填充表单（优化版 - 复用石墨文档/见数算法）
        
        Args:
            card_config: 名片配置项列表，每项包含 name(字段名) 和 value(值)
            
        Returns:
            List[Dict]: 填充后的表单数据
        """
        result = []
        
        print(f"  🎯 [报名工具] 开始智能匹配，共有 {len(self.form_fields)} 个字段，{len(card_config)} 个名片项")
        
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
                config_name = config.get('name', '') # 名片上的key
                config_value = config.get('value', '')
                
                # 计算匹配分数
                score_result = self._calculate_match_score(field_name, config_name)
                
                # 记录详细日志（调试用）
                # if score_result['score'] > 0:
                #    print(f"     - 候选: \"{config_name}\" -> {score_result['score']}分")

                if score_result['matched'] and score_result['score'] > best_match['score']:
                    best_match = {
                        'value': config_value,
                        'score': score_result['score'],
                        'matched_key': config_name
                    }
            
            matched_value = ''
            if best_match['score'] >= 50: # 阈值50
                matched_value = best_match['value']
                val_preview = str(matched_value)[:20] + "..." if len(str(matched_value)) > 20 else str(matched_value)
                print(f"     ✅ 选中: \"{best_match['matched_key']}\" = \"{val_preview}\" (分数: {best_match['score']})")
            else:
                print(f"     ❌ 未匹配 (最高分: {best_match['score']})")

            result.append({
                'field_name': field_name,
                'field_key': field_key,
                'field_value': matched_value,
                'ignore': ignore
            })
        
        return result
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ''
        text = str(text).lower()
        
        # 1. 先去除括号及其内容（通常是提示信息，如"(必填)", "(不要填错)"）
        # 支持中文括号（）和英文括号()
        text = re.sub(r'[\(（][^\)）]*[\)）]', '', text)
        
        # 2. 去除特殊字符
        text = re.sub(r'[：:*？?！!。.、，,\s\-_()（）【】\[\]\n\r\t/／\\|｜;；\'\"\u2795+《》<>""'']+', '', text)
        return text.strip()

    def _clean_text_no_prefix(self, text: str) -> str:
        """去除数字前缀"""
        if not text:
            return ''
        cleaned = self._clean_text(text)
        # 去除开头的数字和点号
        cleaned = re.sub(r'^\d+\.?\*?', '', cleaned)
        return cleaned.strip()

    def _split_keywords(self, keyword: str) -> List[str]:
        """分割关键词"""
        if not keyword:
            return []
        # 支持多种分隔符
        parts = re.split(r'[|,;，；、\n\r\t/／\\｜\u2795+]+', keyword)
        return [self._clean_text(p) for p in parts if p.strip()]
        
    def _split_keywords_no_prefix(self, keyword: str) -> List[str]:
        """分割关键词并去前缀"""
        if not keyword:
            return []
        parts = re.split(r'[|,;，；、\n\r\t/／\\｜\u2795+]+', keyword)
        return [self._clean_text_no_prefix(p) for p in parts if p.strip()]

    def _extract_core_words(self, text: str) -> List[str]:
        """提取核心词"""
        cleaned = self._clean_text(text)
        # 核心词库（与前端 JS 保持一致）
        core_patterns = [
            '小红书', '蒲公英', '微信', '微博', '抖音', '快手', 'b站', '哔哩哔哩',
            'id', '账号', '昵称', '主页', '名字', '名称',
            '粉丝', '点赞', '赞藏', '互动', '阅读', '播放', '曝光', '收藏',
            '中位数', '均赞', 'cpm', 'cpe',
            '价格', '报价', '报备', '返点', '裸价', '预算', '后台',
            '视频', '图文', '链接', '作品', '笔记',
            '手机', '电话', '地址',
            '姓名', '年龄', '性别', '城市', '地区', 'ip',
            '档期', '类别', '类型', '领域', '备注', '授权', '分发', '排竞',
            '平台', '健康', '等级', '保价', '配合', '时间', '探店',
            '收货', '寄送', '快递',
            '出镜', '人物', '保底'
        ]
        found = []
        for pattern in core_patterns:
            if pattern in cleaned:
                found.append(pattern)
        return found
        
    def _longest_common_substring(self, s1: str, s2: str) -> int:
        """最长公共子串长度"""
        m, n = len(s1), len(s2)
        if m == 0 or n == 0:
            return 0
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        max_len = 0
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                    max_len = max(max_len, dp[i][j])
                else:
                    dp[i][j] = 0
        return max_len

    def _has_negation_conflict(self, text1: str, text2: str) -> bool:
        """检测反义词冲突（如"非报备" vs "报备"）"""
        clean1 = self._clean_text(text1)
        clean2 = self._clean_text(text2)
        
        # 定义反义词对
        negation_pairs = [
            ['非报备', '报备'],
            ['非授权', '授权'],
            ['非视频', '视频'],
            ['非图文', '图文'],
            ['不报备', '报备'],
            ['无授权', '授权'],
            ['非独家', '独家'],
            ['税前', '税后'],
            ['含税', '不含税']
        ]
        
        for negative, positive in negation_pairs:
            # 检测：一方包含"非X"，另一方包含"X"但不包含"非X"
            has1_negative = negative in clean1
            has2_negative = negative in clean2
            has1_positive = positive in clean1 and not has1_negative
            has2_positive = positive in clean2 and not has2_negative
            
            # 如果一方是否定形式，另一方是肯定形式，则存在冲突
            if (has1_negative and has2_positive) or (has2_negative and has1_positive):
                # print(f"     🚫 [冲突] \"{text1}\" vs \"{text2}\" ({negative}/{positive})")
                return True
        return False

    def _are_fields_compatible(self, form_field: str, card_field: str) -> bool:
        """互斥字段检测"""
        clean_form = self._clean_text(form_field)
        clean_card = self._clean_text(card_field)
        
        # --- 1. 微信相关特殊处理 (优先处理) ---
        # 解决 微信名 vs 微信号、微信ID vs 微信昵称 等复杂情况
        is_form_wechat = any(k in clean_form for k in ['微信', 'wx', 'vx'])
        
        if is_form_wechat:
            # A. 表单是 微信名/昵称 类
            if any(k in clean_form for k in ['名', '昵称']):
                # 互斥：ID类 (号, id, 账号)
                # 但要注意：如果名片也是 Name 类 (如 "微信名")，则不互斥
                # 只有当名片是纯 ID 类时才互斥
                # ⚡️ 修正：将 "微信", "wx", "vx" 也视为 ID 特征，除非它包含 "名/昵称"
                is_card_id = any(k in clean_card for k in ['号', 'id', '账号', 'wx', 'vx']) or clean_card == '微信'
                is_card_name = any(k in clean_card for k in ['名', '昵称'])
                
                if is_card_id and not is_card_name:
                    return False
                    
                # 互斥：明显非微信的字段
                if any(k in clean_card for k in ['地址', '电话', '手机', '邮箱', '链接', '主页']):
                    return False
                    
                return True
                
            # B. 表单是 微信ID/账号 类 (默认为此)
            else:
                # 互斥：Name 类 (名, 昵称)
                # 只有当名片明确是 Name 类时才互斥
                is_card_name = any(k in clean_card for k in ['名', '昵称'])
                if is_card_name:
                    return False
                    
                # 互斥：明显非微信的字段
                if any(k in clean_card for k in ['地址', '电话', '手机', '邮箱', '链接', '主页']):
                    return False
                    
                return True

        # --- 2. 通用互斥组 (非微信字段) ---
        incompatible_pairs = [
            # 电话 vs 地址/姓名/其他
            (['电话', '手机', '联系方式', '固话'], 
             ['地址', '收货', '街道', '姓名', '昵称', '名字', '省', '市', '区', '微信', '账号', 'id', '邮箱']),
            # 地址 vs 电话
            (['地址', '收货', '街道', '所在地', '地区'], 
             ['电话', '手机', '固话', '微信', '账号', 'id', '粉丝', '价格', '邮箱']),
            # 姓名 vs 地址/电话
            (['姓名', '名字', '收货人'], 
             ['地址', '街道', '电话', '手机', '微信', '账号', 'id', '邮箱']),
            # 昵称 vs 微信/地址/电话
            (['昵称', '名称', '用户名'], 
             ['微信', '微信号', '地址', '电话', '手机', '邮箱']),
            # ID/账号 vs 地址/电话/昵称
            (['id', '账号'], 
             ['地址', '电话', '手机', '昵称', '名字', '名称', '微信', '微信号']),
            # 价格 vs 地址/电话
            (['价格', '报价', '费用', '预算'], 
             ['地址', '电话', '手机', '微信', '账号', 'id', '粉丝', '阅读', '点赞']),
            # 粉丝 vs 地址/电话
            (['粉丝'], 
             ['地址', '电话', '手机', '微信', '账号', 'id', '价格', '报价'])
        ]
        
        for form_keywords, card_keywords in incompatible_pairs:
            # 检查表单字段是否包含组1关键词
            form_match = any(kw in clean_form for kw in form_keywords)
            
            if form_match:
                # 检查名片字段是否包含组2关键词
                card_match = any(kw in clean_card for kw in card_keywords)
                if card_match:
                    # print(f"     🚫 [互斥] 表单:\"{form_field}\" vs 名片:\"{card_field}\"")
                    return False
                
        return True

    def _calculate_match_score(self, field_name: str, config_name: str) -> Dict:
        """
        计算匹配分数（核心算法）
        
        Args:
            field_name: 表单字段名 (Identifier)
            config_name: 名片配置项名 (Keyword)
        """
        if not config_name:
            return {'matched': False, 'score': 0}
            
        clean_identifier = self._clean_text(field_name)
        if not clean_identifier:
            return {'matched': False, 'score': 0}
            
        # 1. 兼容性预检
        if not self._are_fields_compatible(field_name, config_name):
            return {'matched': False, 'score': 0}
            
        clean_identifier_no_prefix = self._clean_text_no_prefix(field_name)
        identifier_core_words = self._extract_core_words(field_name)
        
        # 分割名片关键词
        sub_keywords = self._split_keywords(config_name)
        if not sub_keywords:
            sub_keywords = [self._clean_text(config_name)]
            
        sub_keywords_no_prefix = self._split_keywords_no_prefix(config_name)
        if not sub_keywords_no_prefix:
            sub_keywords_no_prefix = [self._clean_text_no_prefix(config_name)]
            
        best_score = 0
        
        for i, sub_key in enumerate(sub_keywords):
            if not sub_key: continue
            
            # 2. 反义词冲突检测
            if self._has_negation_conflict(field_name, sub_key):
                continue
            
            sub_key_no_prefix = sub_keywords_no_prefix[i] if i < len(sub_keywords_no_prefix) else sub_key
            sub_key_core_words = self._extract_core_words(sub_key) # 注意这里是子关键词的核心词
            
            current_score = 0
            
            # 1. 完全匹配 (100分)
            if clean_identifier == sub_key:
                current_score = 100
                
            # 2. 去前缀后完全匹配 (98分)
            elif sub_key_no_prefix and clean_identifier == sub_key_no_prefix:
                current_score = 98
                
            # 3. 表单标签包含名片key (包含匹配)
            elif sub_key in clean_identifier and len(sub_key) >= 2:
                coverage = len(sub_key) / len(clean_identifier)
                if coverage >= 0.8:
                    current_score = 95
                elif coverage >= 0.5:
                    current_score = 50 + (coverage * 45)
                else:
                    # ⚡️ 优化：低覆盖率时大幅降低分数 (原: 50 + coverage * 40)
                    # 例如 "视频" (2) in "视频出镜人物" (6), coverage=0.33 -> 30 + 13.2 = 43.2 (不匹配)
                    current_score = 30 + (coverage * 40)
                    
            # 4. 去前缀后的包含匹配
            elif sub_key_no_prefix and sub_key_no_prefix in clean_identifier and len(sub_key_no_prefix) >= 2:
                coverage = len(sub_key_no_prefix) / len(clean_identifier)
                if coverage >= 0.8:
                    current_score = 93
                else:
                    # ⚡️ 优化：同上
                    current_score = 28 + (coverage * 40)
                    
            # 5. 名片key包含表单标签 (反向包含)
            elif clean_identifier in sub_key and len(clean_identifier) >= 2:
                if sub_key_no_prefix == clean_identifier:
                    current_score = 96
                else:
                    base_len = len(sub_key_no_prefix) if sub_key_no_prefix else len(sub_key)
                    coverage = len(clean_identifier) / base_len
                    # ⚡️ 优化：反向包含时也降低低覆盖率的分数 (原: 55 + coverage * 35)
                    # 例如 "视频" (2) in "非报备视频报价" (7), coverage=0.28 -> 30 + 16.8 = 46.8 (不匹配)
                    current_score = 30 + (coverage * 60)
                    
            # 6. 去前缀版本的反向包含
            elif sub_key_no_prefix and clean_identifier_no_prefix in sub_key_no_prefix and len(clean_identifier_no_prefix) >= 2:
                 coverage = len(clean_identifier_no_prefix) / len(sub_key_no_prefix)
                 # ⚡️ 优化：同上
                 current_score = 28 + (coverage * 60)

            # 7. 核心词匹配
            elif len(sub_key_core_words) > 0 and len(identifier_core_words) > 0:
                common_core_words = [w for w in sub_key_core_words if w in identifier_core_words]
                if common_core_words:
                    max_core_len = max(len(sub_key_core_words), len(identifier_core_words))
                    core_match_ratio = len(common_core_words) / max_core_len
                    
                    if len(common_core_words) == len(sub_key_core_words) and len(common_core_words) == len(identifier_core_words):
                        current_score = 88
                    elif len(sub_key_core_words) == 1 and len(identifier_core_words) == 1:
                        # ⚡️ 优化：单核心词匹配时，如果不是完全相同（已被前面逻辑捕获），说明有其他干扰词
                        # 例如 "视频" vs "视频出镜人物"，ratio=0.33
                        current_score = 60 # 稍微降低
                    else:
                        # ⚡️ 优化：严格按照核心词比例打分 (原: 55 + ratio * 25)
                        # ratio=0.33 -> 25 + 21 = 46 (不匹配)
                        # ratio=0.5 -> 25 + 32 = 57 (匹配)
                        current_score = 25 + int(core_match_ratio * 65)
            
            # 8. 最长公共子串匹配 (兜底)
            elif len(sub_key) >= 2 and len(clean_identifier) >= 2:
                lcs = self._longest_common_substring(sub_key, clean_identifier)
                max_len = max(len(sub_key), len(clean_identifier))
                min_len = min(len(sub_key), len(clean_identifier))
                
                if lcs >= 2:
                    coverage = lcs / max_len
                    match_rate = lcs / min_len
                    
                    if match_rate >= 0.6 and lcs >= 3:
                        current_score = 30 + (coverage * 20) + (match_rate * 15)
                    elif match_rate >= 0.5 and lcs >= 2:
                        current_score = 25 + (coverage * 15) + (match_rate * 10)
            
            if current_score > best_score:
                best_score = current_score
                
        return {'matched': best_score >= 50, 'score': best_score}

    def _match_field_name(self, form_field: str, config_name: str) -> bool:
        """保留旧方法接口，但在内部调用新逻辑（为了兼容性）"""
        result = self._calculate_match_score(form_field, config_name)
        return result['matched']
    
    def submit(self, form_data: List[Dict]) -> Tuple[bool, str]:
        """提交表单"""
        return self.api.submit_form(form_data)
    
    def get_field_names(self) -> List[str]:
        """获取所有字段名称"""
        return [f.get('field_name', '') for f in self.form_fields]

