"""
AI 解析器
使用 DeepSeek API 解析文本中的链接和标题
"""
import json
import urllib.request
import urllib.error
import config

class AIParser:
    """AI 解析器类"""
    
    @staticmethod
    def parse_links(text: str):
        """
        调用 DeepSeek API 解析文本中的链接
        
        Args:
            text: 包含链接的文本
            
        Returns:
            list: 解析后的链接列表 [{'name': '标题', 'url': '链接', 'category': '分类'}]
        """
        if not text or not text.strip():
            return []
            
        api_key = config.DEEPSEEK_CONFIG["apiKey"]
        api_url = config.DEEPSEEK_CONFIG["apiUrl"]
        model = config.DEEPSEEK_CONFIG["model"]
        
        # 构造 Prompt
        prompt = f"""
请分析以下文本，提取其中所有的URL链接。
对于每个链接，请提取其对应的完整描述作为标题（name）。
注意：
1. 标题必须尽可能完整，保留原文中该链接前后的所有描述性文字（如项目名称、活动详情、要求等），不要简写或自行概括。
2. 如果链接前后有一段长文本描述，请将整段描述作为标题，不要截断。
3. 根据URL的域名推断分类（参考：问卷星、麦客、金数据、石墨文档、见数、问卷网、番茄表单、飞书问卷、WPS表单、报名工具、腾讯文档、腾讯问卷等）。

文本内容：
{text}

请直接返回 JSON 数组格式，不要包含 markdown 标记或其他废话。
格式要求：
[
    {{
        "name": "完整的原文描述（不要简写）",
        "url": "URL地址",
        "category": "推断的分类"
    }}
]
"""
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是一个专业的文本信息提取助手，擅长从混乱的文本中提取结构化的链接信息。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": config.DEEPSEEK_CONFIG["temperature"],
            "max_tokens": config.DEEPSEEK_CONFIG["maxTokens"],
            "stream": False
        }
        
        try:
            req = urllib.request.Request(
                api_url, 
                data=json.dumps(data).encode('utf-8'), 
                headers=headers, 
                method='POST'
            )
            
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content'].strip()
                    
                    # 清理可能的 markdown 标记
                    if content.startswith("```json"):
                        content = content[7:]
                    if content.endswith("```"):
                        content = content[:-3]
                    
                    try:
                        parsed_data = json.loads(content.strip())
                        if isinstance(parsed_data, list):
                            return parsed_data
                    except json.JSONDecodeError:
                        print(f"AI 返回格式错误: {content}")
                        
        except Exception as e:
            print(f"AI 解析请求失败: {e}")
            
        return []
