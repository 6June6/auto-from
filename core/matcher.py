"""
字段匹配算法
实现智能模糊匹配
"""
import re
from typing import Optional


class FieldMatcher:
    """字段匹配器"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        清理文本
        移除标点符号、空格，转小写
        """
        if not text:
            return ""
        
        # 转小写 
        text = str(text).lower().strip()
        
        # 移除常见标点符号和空格
        text = re.sub(r'[：:：*？?！!。.、，,\s\*\-_/\\]+', '', text)
        
        return text
    
    @staticmethod
    def match_keyword(text: str, keyword: str) -> bool:
        """
        关键词匹配（模糊匹配）
        :param text: 待匹配文本
        :param keyword: 关键词
        :return: 是否匹配
        """
        if not text or not keyword:
            return False
        
        # 清理文本
        clean_text_str = FieldMatcher.clean_text(text)
        clean_keyword = FieldMatcher.clean_text(keyword)
        
        if not clean_text_str or not clean_keyword:
            return False
        
        # 双向包含匹配
        return clean_keyword in clean_text_str or clean_text_str in clean_keyword
    
    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """
        计算相似度（简单版本）
        :return: 0-1 之间的相似度
        """
        if not text1 or not text2:
            return 0.0
        
        clean_text1 = FieldMatcher.clean_text(text1)
        clean_text2 = FieldMatcher.clean_text(text2)
        
        if clean_text1 == clean_text2:
            return 1.0
        
        # 双向包含检查
        if clean_text1 in clean_text2:
            return len(clean_text1) / len(clean_text2)
        elif clean_text2 in clean_text1:
            return len(clean_text2) / len(clean_text1)
        
        # 字符级别相似度
        common_chars = set(clean_text1) & set(clean_text2)
        if not common_chars:
            return 0.0
        
        total_chars = set(clean_text1) | set(clean_text2)
        return len(common_chars) / len(total_chars)


