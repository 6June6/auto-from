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
import requests
from typing import Optional, Dict, List, Tuple, Callable
from urllib.parse import urlparse, parse_qs


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
                self.info_id = detail.get('info_id')
                return True, '获取成功', self.info_id
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
        提交表单
        
        Args:
            form_data: 表单数据列表，每项包含 field_name, field_key, field_value, ignore
            
        Returns:
            Tuple[bool, str]: (成功标志, 消息)
        """
        if not self.info_id or not self.access_token:
            return False, '缺少info_id或access_token'
            
        try:
            url = f"{self.BASE_URL}/enroll/v1/user_update"
            payload = {
                'info_id': self.info_id,
                'info': form_data,
                'anon': 0,
                'access_token': self.access_token,
                'from': 'xcx'
            }
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = self.session.post(url, json=payload, headers=headers, timeout=15)
            data = response.json()
            
            if data.get('sta') == 0:
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
        
    def initialize(self, url: str) -> Tuple[bool, str]:
        """
        初始化填充器
        
        Args:
            url: 报名工具链接
            
        Returns:
            Tuple[bool, str]: (成功标志, 消息)
        """
        eid = self.api.extract_eid(url)
        if not eid:
            return False, '无法从链接中提取eid'
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
        return self.api.poll_login_status(self.login_code)
    
    def load_form(self) -> Tuple[bool, str]:
        """加载表单数据"""
        # 先获取详情
        success, msg, info_id = self.api.get_enroll_detail()
        if not success:
            return False, msg
            
        # 再获取表单字段
        success, msg, fields = self.api.get_form_fields()
        if not success:
            return False, msg
            
        self.form_fields = fields or []
        return True, f'已加载 {len(self.form_fields)} 个字段'
    
    def match_and_fill(self, card_config: List[Dict]) -> List[Dict]:
        """
        匹配名片配置并填充表单
        
        Args:
            card_config: 名片配置项列表，每项包含 name(字段名) 和 value(值)
            
        Returns:
            List[Dict]: 填充后的表单数据
        """
        result = []
        
        for field in self.form_fields:
            field_name = field.get('field_name', '')
            field_key = field.get('field_key', '')
            ignore = field.get('ignore', 0)
            
            # 查找匹配的名片配置
            matched_value = ''
            for config in card_config:
                config_name = config.get('name', '')
                config_value = config.get('value', '')
                
                # 使用评分匹配
                if self._match_field_name(field_name, config_name):
                    matched_value = config_value
                    break
            
            result.append({
                'field_name': field_name,
                'field_key': field_key,
                'field_value': matched_value,
                'ignore': ignore
            })
        
        return result
    
    def _match_field_name(self, form_field: str, config_name: str) -> bool:
        """
        匹配字段名称
        
        支持多种匹配方式：
        1. 完全匹配
        2. 包含匹配
        3. 别名匹配（使用、分隔）
        """
        if not form_field or not config_name:
            return False
            
        form_field = form_field.lower().strip()
        config_name = config_name.lower().strip()
        
        # 完全匹配
        if form_field == config_name:
            return True
        
        # 支持别名（用、分隔）
        aliases = config_name.split('、')
        for alias in aliases:
            alias = alias.strip()
            if not alias:
                continue
            # 完全匹配
            if form_field == alias:
                return True
            # 包含匹配
            if alias in form_field or form_field in alias:
                return True
        
        return False
    
    def submit(self, form_data: List[Dict]) -> Tuple[bool, str]:
        """提交表单"""
        return self.api.submit_form(form_data)
    
    def get_field_names(self) -> List[str]:
        """获取所有字段名称"""
        return [f.get('field_name', '') for f in self.form_fields]

