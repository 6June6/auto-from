"""
自动填写引擎
负责生成和执行自动填写的 JavaScript 代码
"""
import json
from typing import List, Dict


class AutoFillEngine:
    """自动填写引擎"""
    
    @staticmethod
    def generate_fill_script(fill_data: List[Dict[str, str]]) -> str:
        """
        生成自动填写的 JavaScript 脚本
        :param fill_data: 填写数据 [{'key': '字段名', 'value': '值'}, ...]
        :return: JavaScript 代码字符串
        """
        fill_data_json = json.dumps(fill_data, ensure_ascii=False)
        
        js_code = f"""
(function() {{
    console.log('🚀 开始自动填写...');
    
    const fillData = {fill_data_json};
    let fillCount = 0;
    const results = [];
    
    // 首先打印所有找到的输入框信息（调试用）
    console.log('📋 扫描页面中的所有输入框:');
    const allInputs = document.querySelectorAll('input[type="text"], input:not([type]), textarea, input[type="tel"], input[type="email"], input[type="number"]');
    allInputs.forEach((input, index) => {{
        const label = findLabelDebug(input);
        const placeholder = input.placeholder || '';
        const name = input.name || '';
        const id = input.id || '';
        console.log(`输入框 ${{index + 1}}: label="${{label}}", placeholder="${{placeholder}}", name="${{name}}", id="${{id}}"`);
    }});
    
    // 调试版本的findLabel
    function findLabelDebug(input) {{
        let label = '';
        if (input.labels && input.labels.length > 0) {{
            label = input.labels[0].innerText || input.labels[0].textContent;
        }} else if (input.id) {{
            const labelEl = document.querySelector(`label[for="${{input.id}}"]`);
            if (labelEl) label = labelEl.innerText || labelEl.textContent;
        }}
        if (!label) {{
            let parent = input.parentElement;
            let depth = 0;
            while (parent && depth < 5) {{
                const labelElement = parent.querySelector('label');
                if (labelElement) {{
                    label = labelElement.innerText || labelElement.textContent;
                    break;
                }}
                const text = Array.from(parent.childNodes)
                    .filter(node => node.nodeType === Node.TEXT_NODE)
                    .map(node => node.textContent.trim())
                    .join(' ');
                if (text && text.length < 100 && text.length > 0) {{
                    label = text;
                    break;
                }}
                parent = parent.parentElement;
                depth++;
            }}
        }}
        if (!label) {{
            let sibling = input.previousElementSibling;
            let count = 0;
            while (sibling && count < 3) {{
                if (sibling.tagName === 'LABEL' || sibling.tagName === 'SPAN' || sibling.tagName === 'DIV') {{
                    const text = (sibling.innerText || sibling.textContent || '').trim();
                    if (text && text.length < 100) {{
                        label = text;
                        break;
                    }}
                }}
                sibling = sibling.previousElementSibling;
                count++;
            }}
        }}
        return (label || '').trim();
    }}
    
    // 查找输入框关联的 label
    function findLabel(input, doc) {{
        // 1. 通过 labels 属性
        if (input.labels && input.labels.length > 0) {{
            return input.labels[0].innerText || input.labels[0].textContent;
        }}
        
        // 2. 通过 for 属性
        const id = input.id;
        if (id) {{
            const label = doc.querySelector(`label[for="${{id}}"]`);
            if (label) return label.innerText || label.textContent;
        }}
        
        // 3. 查找父元素中的文本
        let parent = input.parentElement;
        let depth = 0;
        while (parent && depth < 3) {{
            const labelElement = parent.querySelector('label');
            if (labelElement) {{
                return labelElement.innerText || labelElement.textContent;
            }}
            
            // 获取父元素的直接文本（不包括子元素）
            const text = Array.from(parent.childNodes)
                .filter(node => node.nodeType === Node.TEXT_NODE)
                .map(node => node.textContent.trim())
                .join(' ');
            
            if (text && text.length < 50 && text.length > 0) {{
                return text;
            }}
            
            parent = parent.parentElement;
            depth++;
        }}
        
        // 4. 查找前面的兄弟节点
        let sibling = input.previousElementSibling;
        while (sibling) {{
            if (sibling.tagName === 'LABEL' || sibling.tagName === 'SPAN' || sibling.tagName === 'DIV') {{
                const text = (sibling.innerText || sibling.textContent || '').trim();
                if (text && text.length < 50) {{
                    return text;
                }}
            }}
            sibling = sibling.previousElementSibling;
        }}
        
        return '';
    }}
    
    // 关键词匹配（模糊匹配）
    function matchKeyword(text, keyword) {{
        if (!text || !keyword) return false;
        
        text = String(text).toLowerCase().trim();
        keyword = String(keyword).toLowerCase().trim();
        
        // 移除常见的符号
        text = text.replace(/[：:：*？?！!。.、，,\\s]/g, '');
        keyword = keyword.replace(/[：:：*？?！!。.、，,\\s]/g, '');
        
        // 双向包含匹配
        return text.includes(keyword) || keyword.includes(text);
    }}
    
    // 填写输入框
    function fillInput(input, value) {{
        // 设置值
        input.value = value;
        
        // 触发各种事件以确保值被识别
        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
        input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
        
        // 对于某些框架（如 Vue、React），需要设置原生值
        try {{
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype,
                'value'
            ).set;
            nativeInputValueSetter.call(input, value);
        }} catch (e) {{
            console.warn('设置原生值失败:', e);
        }}
    }}
    
    // 以输入框为主体遍历，为每个输入框找最佳匹配的名片字段
    const inputs = document.querySelectorAll(
        'input[type="text"], input:not([type]), textarea, input[type="tel"], input[type="email"], input[type="number"]'
    );
    
    inputs.forEach((input, index) => {{
        const label = findLabel(input, document);
        const placeholder = input.placeholder || '';
        const name = input.name || '';
        const id = input.id || '';
        
        let bestMatch = {{ item: null, score: 0, matched: null }};
        
        // 在所有名片字段中找最佳匹配
        fillData.forEach(item => {{
            const keyword = item.key;
            let score = 0;
            let matched = null;
            
            if (matchKeyword(label, keyword)) {{
                score = 100;
                matched = label;
            }} else if (matchKeyword(placeholder, keyword)) {{
                score = 80;
                matched = placeholder;
            }} else if (matchKeyword(name, keyword)) {{
                score = 70;
                matched = name;
            }} else if (matchKeyword(id, keyword)) {{
                score = 60;
                matched = id;
            }}
            
            if (score > bestMatch.score) {{
                bestMatch = {{ item: item, score: score, matched: matched }};
            }}
        }});
        
        // 如果找到匹配，填写
        if (bestMatch.item && bestMatch.score >= 50) {{
            fillInput(input, bestMatch.item.value);
            console.log('✅ 填写字段:', bestMatch.item.key, '=', bestMatch.item.value, '(匹配:', bestMatch.matched, ')');
            fillCount++;
            results.push({{
                key: bestMatch.item.key,
                value: bestMatch.item.value,
                matched: bestMatch.matched,
                success: true
            }});
        }}
    }});
    
    // 处理下拉框
    const selects = document.querySelectorAll('select');
    selects.forEach((select, index) => {{
        const label = findLabel(select, document);
        let bestMatch = {{ item: null, score: 0 }};
        
        fillData.forEach(item => {{
            if (matchKeyword(label, item.key)) {{
                bestMatch = {{ item: item, score: 100 }};
            }}
        }});
        
        if (bestMatch.item) {{
            for (let option of select.options) {{
                if (matchKeyword(option.text, bestMatch.item.value) || matchKeyword(option.value, bestMatch.item.value)) {{
                    select.value = option.value;
                    select.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    console.log('✅ 选择下拉:', bestMatch.item.key, '=', bestMatch.item.value);
                    fillCount++;
                    results.push({{
                        key: bestMatch.item.key,
                        value: bestMatch.item.value,
                        matched: label,
                        success: true
                    }});
                    break;
                }}
            }}
        }}
    }});
    
    // 记录未匹配的名片字段
    const filledKeys = new Set(results.filter(r => r.success).map(r => r.key));
    fillData.forEach(item => {{
        if (!filledKeys.has(item.key)) {{
            const hasResult = results.some(r => r.key === item.key);
            if (!hasResult) {{
                console.warn('⚠️ 名片字段未使用:', item.key);
                results.push({{
                    key: item.key,
                    value: item.value,
                    matched: null,
                    success: false
                }});
            }}
        }}
    }});
    
    // 返回结果
    const result = {{
        fillCount: fillCount,
        totalCount: fillData.length,
        success: fillCount > 0,
        results: results
    }};
    
    console.log('📊 填写完成:', result);
    
    // 返回结果给 Python
    return result;
}})();
"""
        return js_code
    
    @staticmethod
    def generate_notification_script(fill_count: int, total_count: int) -> str:
        """
        生成显示通知的脚本
        :param fill_count: 成功填写数量
        :param total_count: 总配置项数量
        :return: JavaScript 代码
        """
        js_code = f"""
(function() {{
    const successMsg = document.createElement('div');
    successMsg.style.cssText = 'position:fixed;top:20px;right:20px;background:#28a745;color:white;padding:20px 30px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.3);z-index:999999;font-size:16px;font-family:sans-serif;';
    successMsg.innerHTML = '<strong>✅ 自动填写完成！</strong><br>成功填写 {fill_count} 个字段，共 {total_count} 个配置项。';
    document.body.appendChild(successMsg);
    
    setTimeout(() => {{
        successMsg.style.transition = 'opacity 0.5s';
        successMsg.style.opacity = '0';
        setTimeout(() => document.body.removeChild(successMsg), 500);
    }}, 3000);
}})();
"""
        return js_code



