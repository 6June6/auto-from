#!/usr/bin/env python3
"""
演示 WPS 表单匹配效果
展示优化后的匹配算法如何工作
"""

import re


class WPSMatchingDemo:
    """WPS 表单匹配演示"""
    
    def __init__(self):
        self.core_patterns = [
            '小红书', '蒲公英', '微信', '微博', '抖音', '快手',
            'id', '账号', '昵称', '主页', '名字', '名称',
            '粉丝', '点赞', '赞藏', '互动', '阅读', '播放', '曝光', '收藏',
            '中位数', '均赞', 'cpm', 'cpe',
            '价格', '报价', '报备', '返点', '裸价', '预算',
            '视频', '图文', '链接',
            '手机', '电话', '地址',
            '姓名', '年龄', '性别', '城市', '地区', 'ip',
            '档期', '类别', '类型', '领域', '备注', '授权', '分发', '排竞',
            '平台', '健康', '等级', '保价', '配合', '时间', '探店'
        ]
    
    def clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ''
        text = str(text).lower()
        text = re.sub(r'[：:*？?！!。.、，,\s\-_()（）【】\[\]\n\r\t/／\\|｜;；\'"\u2795+《》<>""'']+', '', text)
        return text.strip()
    
    def clean_text_no_prefix(self, text: str) -> str:
        """去除数字前缀"""
        if not text:
            return ''
        cleaned = self.clean_text(text)
        cleaned = re.sub(r'^\d+\.?\*?', '', cleaned)
        return cleaned.strip()
    
    def split_keywords(self, keyword: str) -> list:
        """分割关键词"""
        if not keyword:
            return []
        parts = re.split(r'[|,;，；、\n\r\t/／\\｜\u2795+]+', keyword)
        return [self.clean_text(p) for p in parts if p.strip()]
    
    def extract_core_words(self, text: str) -> list:
        """提取核心词"""
        cleaned = self.clean_text(text)
        found = []
        for pattern in self.core_patterns:
            if pattern in cleaned:
                found.append(pattern)
        return found
    
    def longest_common_substring(self, s1: str, s2: str) -> int:
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
    
    def calculate_match_score(self, field_name: str, config_name: str) -> dict:
        """计算匹配分数"""
        if not config_name:
            return {'matched': False, 'score': 0, 'reason': '空关键词'}
        
        clean_identifier = self.clean_text(field_name)
        if not clean_identifier:
            return {'matched': False, 'score': 0, 'reason': '空标识符'}
        
        clean_identifier_no_prefix = self.clean_text_no_prefix(field_name)
        identifier_core_words = self.extract_core_words(field_name)
        
        sub_keywords = self.split_keywords(config_name)
        if not sub_keywords:
            sub_keywords = [self.clean_text(config_name)]
        
        sub_keywords_no_prefix = [self.clean_text_no_prefix(k) for k in config_name.split('|')]
        if not sub_keywords_no_prefix:
            sub_keywords_no_prefix = [self.clean_text_no_prefix(config_name)]
        
        best_score = 0
        best_reason = ''
        
        for i, sub_key in enumerate(sub_keywords):
            if not sub_key:
                continue
            
            sub_key_no_prefix = sub_keywords_no_prefix[i] if i < len(sub_keywords_no_prefix) else sub_key
            sub_key_core_words = self.extract_core_words(sub_key)
            
            current_score = 0
            reason = ''
            
            # 1. 完全匹配 (100分)
            if clean_identifier == sub_key:
                current_score = 100
                reason = '完全匹配'
            
            # 2. 去前缀后完全匹配 (98分)
            elif sub_key_no_prefix and clean_identifier == sub_key_no_prefix:
                current_score = 98
                reason = '去前缀后完全匹配'
            
            # 3. 表单标签包含名片key
            elif sub_key in clean_identifier and len(sub_key) >= 2:
                coverage = len(sub_key) / len(clean_identifier)
                if coverage >= 0.8:
                    current_score = 95
                elif coverage >= 0.5:
                    current_score = 50 + (coverage * 45)
                else:
                    current_score = 50 + (coverage * 40)
                reason = f'包含匹配(覆盖率{coverage*100:.1f}%)'
            
            # 4. 去前缀后的包含匹配
            elif sub_key_no_prefix and sub_key_no_prefix in clean_identifier and len(sub_key_no_prefix) >= 2:
                coverage = len(sub_key_no_prefix) / len(clean_identifier)
                if coverage >= 0.8:
                    current_score = 93
                else:
                    current_score = 48 + (coverage * 40)
                reason = f'去前缀包含匹配(覆盖率{coverage*100:.1f}%)'
            
            # 5. 名片key包含表单标签
            elif clean_identifier in sub_key and len(clean_identifier) >= 2:
                if sub_key_no_prefix == clean_identifier:
                    current_score = 96
                    reason = '反向完全匹配'
                else:
                    base_len = len(sub_key_no_prefix) if sub_key_no_prefix else len(sub_key)
                    coverage = len(clean_identifier) / base_len
                    current_score = 55 + (coverage * 35)
                    reason = f'反向包含匹配(覆盖率{coverage*100:.1f}%)'
            
            # 6. 去前缀版本的反向包含
            elif sub_key_no_prefix and clean_identifier_no_prefix in sub_key_no_prefix and len(clean_identifier_no_prefix) >= 2:
                coverage = len(clean_identifier_no_prefix) / len(sub_key_no_prefix)
                current_score = 53 + (coverage * 35)
                reason = f'去前缀反向包含(覆盖率{coverage*100:.1f}%)'
            
            # 7. 核心词匹配
            elif len(sub_key_core_words) > 0 and len(identifier_core_words) > 0:
                common_core_words = [w for w in sub_key_core_words if w in identifier_core_words]
                if common_core_words:
                    max_core_len = max(len(sub_key_core_words), len(identifier_core_words))
                    core_match_ratio = len(common_core_words) / max_core_len
                    
                    if len(common_core_words) == len(sub_key_core_words) and len(common_core_words) == len(identifier_core_words):
                        current_score = 88
                        reason = f'核心词完全匹配({",".join(common_core_words)})'
                    elif len(sub_key_core_words) == 1 and len(identifier_core_words) == 1:
                        current_score = 80
                        reason = f'单核心词匹配({common_core_words[0]})'
                    else:
                        current_score = 55 + int(core_match_ratio * 25)
                        reason = f'多核心词匹配({",".join(common_core_words)})'
            
            # 8. 最长公共子串匹配
            elif len(sub_key) >= 2 and len(clean_identifier) >= 2:
                lcs = self.longest_common_substring(sub_key, clean_identifier)
                max_len = max(len(sub_key), len(clean_identifier))
                min_len = min(len(sub_key), len(clean_identifier))
                
                if lcs >= 2:
                    coverage = lcs / max_len
                    match_rate = lcs / min_len
                    
                    if match_rate >= 0.6 and lcs >= 3:
                        current_score = 30 + (coverage * 20) + (match_rate * 15)
                        reason = f'公共子串匹配(LCS={lcs})'
                    elif match_rate >= 0.5 and lcs >= 2:
                        current_score = 25 + (coverage * 15) + (match_rate * 10)
                        reason = f'公共子串匹配(LCS={lcs})'
            
            if current_score > best_score:
                best_score = current_score
                best_reason = reason
        
        return {
            'matched': best_score >= 50,
            'score': best_score,
            'reason': best_reason if best_reason else '无匹配'
        }
    
    def demo_matching(self):
        """演示匹配效果"""
        print("🎯 WPS 表单匹配算法演示")
        print("=" * 80)
        print()
        
        # 测试用例
        test_cases = [
            # (表单字段, 名片配置, 期望结果)
            ("探店时间20号-31号之间", "探店时间", "应该匹配"),
            ("探店时间20号-31号之间", "01.探店时间", "应该匹配"),
            ("小红书账号", "小红书账号", "应该匹配"),
            ("小红书账号昵称", "小红书昵称", "应该匹配"),
            ("粉丝数量", "粉丝", "应该匹配"),
            ("联系方式", "手机", "应该匹配"),
            ("报价", "价格", "应该匹配"),
            ("账号链接", "主页链接", "应该匹配"),
            ("姓名", "名字", "应该匹配"),
            ("微信号", "微信", "应该匹配"),
            ("探店时间", "小红书账号", "不应该匹配"),
        ]
        
        for field_name, config_name, expected in test_cases:
            result = self.calculate_match_score(field_name, config_name)
            
            # 判断是否符合期望
            is_expected = (result['matched'] and "应该匹配" in expected) or \
                         (not result['matched'] and "不应该匹配" in expected)
            
            status = "✅" if is_expected else "❌"
            match_status = "✓ 匹配" if result['matched'] else "✗ 不匹配"
            
            # 生成分数条
            score_bar = '█' * int(result['score'] / 10) + '░' * (10 - int(result['score'] / 10))
            
            print(f"{status} 表单字段: \"{field_name}\"")
            print(f"   名片配置: \"{config_name}\"")
            print(f"   {match_status} | 分数: {result['score']:.1f} [{score_bar}]")
            print(f"   匹配原因: {result['reason']}")
            print(f"   期望结果: {expected}")
            print()
        
        print("=" * 80)
        print("📊 演示完成")
        print()
        print("💡 说明:")
        print("   - 分数 ≥ 50 认为匹配成功")
        print("   - 分数越高，匹配越精确")
        print("   - 支持多种匹配策略：完全匹配、包含匹配、核心词匹配、公共子串匹配")


if __name__ == '__main__':
    demo = WPSMatchingDemo()
    demo.demo_matching()

