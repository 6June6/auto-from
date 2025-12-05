"""
自动填写引擎 V2 - 增强版
支持更多表单类型和更灵活的匹配
"""
import json
from typing import List, Dict


class AutoFillEngineV2:
    """自动填写引擎 V2"""
    
    @staticmethod
    def generate_fill_script(fill_data: List[Dict[str, str]]) -> str:
        """
        生成自动填写的 JavaScript 脚本（增强版）
        """
        fill_data_json = json.dumps(fill_data, ensure_ascii=False)
        
        js_code = f"""
(function() {{
    console.log('🚀 开始自动填写 V2...');
    console.log('⏳ 等待表单元素加载...');
    
    const fillData = {fill_data_json};
    let fillCount = 0;
    const results = [];
    
    // 等待输入框加载完成（优化速度：减少等待时间）
    function waitForInputs(maxAttempts = 5, interval = 300) {{
        return new Promise((resolve) => {{
            let attempts = 0;
            const checkInputs = setInterval(() => {{
                const inputs = document.querySelectorAll('input, textarea');
                attempts++;
                console.log(`🔍 尝试 ${{attempts}}/${{maxAttempts}}: 找到 ${{inputs.length}} 个输入框`);
                
                if (inputs.length > 0 || attempts >= maxAttempts) {{
                    clearInterval(checkInputs);
                    console.log(inputs.length > 0 ? '✅ 表单已加载' : '⚠️ 未找到输入框');
                    resolve(inputs.length > 0);
                }}
            }}, interval);
        }});
    }}
    
    // 获取所有可能的输入框（简化版，直接获取所有input和textarea）
    function getAllInputs() {{
        const inputs = [];
        
        // 【简化】直接获取所有input和textarea，不限制type
        document.querySelectorAll('input, textarea').forEach(input => {{
            // 只跳过明确隐藏的元素
            const style = window.getComputedStyle(input);
            if (style.display !== 'none' && style.visibility !== 'hidden') {{
                inputs.push(input);
            }}
        }});
        
        console.log(`📝 getAllInputs找到 ${{inputs.length}} 个输入框`);
        
        return inputs;
    }}
    
    // 获取输入框的所有可能标识
    function getInputIdentifiers(input) {{
        const identifiers = [];
        
        // 0. 【重要】麦客CRM特殊处理：通过 aria-labelledby 查找
        const ariaLabelledBy = input.getAttribute('aria-labelledby');
        if (ariaLabelledBy) {{
            // aria-labelledby 可能包含多个id，用空格分隔
            const ids = ariaLabelledBy.split(' ');
            ids.forEach(id => {{
                const el = document.getElementById(id);
                if (el) {{
                    const text = (el.innerText || el.textContent || '').trim();
                    if (text && text !== '.') {{  // 麦客CRM有些占位符是 "."
                        identifiers.push(text);
                        console.log(`通过aria-labelledby找到标识: "${{text}}" (id: ${{id}})`);
                    }}
                }}
            }});
        }}
        
        // 1. Label 标签
        if (input.labels && input.labels.length > 0) {{
            input.labels.forEach(label => {{
                const text = (label.innerText || label.textContent || '').trim();
                if (text) identifiers.push(text);
            }});
        }}
        
        // 2. 通过 for 属性查找 label
        if (input.id) {{
            const label = document.querySelector(`label[for="${{input.id}}"]`);
            if (label) {{
                const text = (label.innerText || label.textContent || '').trim();
                if (text) identifiers.push(text);
            }}
        }}
        
        // 3. placeholder
        if (input.placeholder) {{
            identifiers.push(input.placeholder.trim());
        }}
        
        // 4. name 属性
        if (input.name) {{
            identifiers.push(input.name.trim());
        }}
        
        // 5. id 属性
        if (input.id) {{
            identifiers.push(input.id.trim());
        }}
        
        // 6. title 属性
        if (input.title) {{
            identifiers.push(input.title.trim());
        }}
        
        // 7. aria-label 属性
        if (input.getAttribute('aria-label')) {{
            identifiers.push(input.getAttribute('aria-label').trim());
        }}
        
        // 8. 父元素中的 label
        let parent = input.parentElement;
        let depth = 0;
        while (parent && depth < 5) {{
            const labelEl = parent.querySelector('label');
            if (labelEl) {{
                const text = (labelEl.innerText || labelEl.textContent || '').trim();
                if (text && !identifiers.includes(text)) {{
                    identifiers.push(text);
                }}
            }}
            
            // 获取父元素的直接文本内容
            const directText = Array.from(parent.childNodes)
                .filter(node => node.nodeType === Node.TEXT_NODE)
                .map(node => node.textContent.trim())
                .filter(text => text.length > 0 && text.length < 50)
                .join(' ');
            
            if (directText && !identifiers.includes(directText)) {{
                identifiers.push(directText);
            }}
            
            parent = parent.parentElement;
            depth++;
        }}
        
        // 9. 前置兄弟元素
        let sibling = input.previousElementSibling;
        let siblingCount = 0;
        while (sibling && siblingCount < 3) {{
            const text = (sibling.innerText || sibling.textContent || '').trim();
            if (text && text.length < 50 && !identifiers.includes(text)) {{
                identifiers.push(text);
            }}
            sibling = sibling.previousElementSibling;
            siblingCount++;
        }}
        
        return identifiers;
    }}
    
    // 清理文本用于匹配
    function cleanText(text) {{
        if (!text) return '';
        return String(text)
            .toLowerCase()
            .replace(/[：:：*？?！!。.、，,\\s\\-_\\(\\)（）【】\\[\\]]/g, '')
            .trim();
    }}
    
    // 匹配关键词（增强版：支持多关键词）
    function matchKeyword(identifiers, keyword) {{
        const cleanKeyword = cleanText(keyword);
        if (!cleanKeyword) return {{ matched: false, identifier: null, score: 0 }};
        
        // 支持用逗号、竖线或分号分隔的多个关键词
        const subKeywords = keyword.split(/[|,;，；、]/).map(k => cleanText(k)).filter(k => k);
        
        // 如果没有分隔符，就只有一个关键词
        if (subKeywords.length === 0) subKeywords.push(cleanKeyword);
        
        let bestScore = 0;
        let bestIdentifier = null;
        
        for (const subKey of subKeywords) {{
            for (const identifier of identifiers) {{
                const cleanIdentifier = cleanText(identifier);
                if (!cleanIdentifier) continue;
                
                let currentScore = 0;
                
                // 1. 完全匹配 (最高优先级)
                if (cleanIdentifier === subKey) {{
                    currentScore = 100;
                }} 
                // 2. 包含匹配 (次高优先级)
                else if (cleanIdentifier.includes(subKey)) {{
                    // 如果标识符很短且包含关键词，分数高；如果标识符很长，分数低
                    const ratio = subKey.length / cleanIdentifier.length;
                    currentScore = 80 + (ratio * 10); 
                }}
                else if (subKey.includes(cleanIdentifier)) {{
                    currentScore = 70;
                }}
                // 3. 部分字符匹配
                else {{
                    let commonChars = 0;
                    for (const char of subKey) {{
                        if (cleanIdentifier.includes(char)) commonChars++;
                    }}
                    const similarity = commonChars / subKey.length;
                    if (similarity >= 0.5) {{
                        currentScore = Math.floor(similarity * 60);
                    }}
                }}
                
                if (currentScore > bestScore) {{
                    bestScore = currentScore;
                    bestIdentifier = identifier;
                }}
            }}
        }}
        
        return {{ matched: bestScore > 0, identifier: bestIdentifier, score: bestScore }};
    }}
    
    // 填写输入框
    function fillInput(input, value) {{
        // 先聚焦
        input.focus();
        
        // 设置值
        input.value = value;
        
        // 触发所有可能的事件
        const events = ['input', 'change', 'blur', 'keyup', 'keydown'];
        events.forEach(eventName => {{
            input.dispatchEvent(new Event(eventName, {{ bubbles: true, cancelable: true }}));
        }});
        
        // 对于某些框架（Vue/React），需要设置原生值
        try {{
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype,
                'value'
            ).set;
            if (nativeInputValueSetter) {{
                nativeInputValueSetter.call(input, value);
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }} catch (e) {{
            // 忽略错误
        }}
        
        // 对于 textarea
        try {{
            const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype,
                'value'
            ).set;
            if (nativeTextAreaValueSetter && input.tagName === 'TEXTAREA') {{
                nativeTextAreaValueSetter.call(input, value);
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            }}
        }} catch (e) {{
            // 忽略错误
        }}
        
        // 失去焦点
        input.blur();
    }}
    
    // 主执行函数（异步）
    async function executeAutoFill() {{
        // 等待输入框加载
        const hasInputs = await waitForInputs();
        
        if (!hasInputs) {{
            return {{
                fillCount: 0,
                totalCount: fillData.length,
                success: false,
                error: '未找到任何输入框',
                results: []
            }};
        }}
        
        // 开始填写
        console.log('\\n📋 扫描页面输入框...');
        const allInputs = getAllInputs();
        console.log(`找到 ${{allInputs.length}} 个输入框`);
        
        // 打印所有输入框的信息
        allInputs.forEach((input, index) => {{
            const identifiers = getInputIdentifiers(input);
            console.log(`\\n输入框 ${{index + 1}}:`);
            console.log(`  标识符: ${{identifiers.join(' | ')}}`);
            console.log(`  类型: ${{input.type || input.tagName}}`);
        }});
        
        console.log('\\n🎯 开始匹配和填写...');
        
        // 以输入框为主体遍历，为每个输入框找最佳匹配的名片字段
        allInputs.forEach((input, index) => {{
            const identifiers = getInputIdentifiers(input);
            let bestMatch = {{ item: null, score: 0, identifier: null }};
            
            // 在所有名片字段中找最佳匹配
            fillData.forEach(item => {{
                const matchResult = matchKeyword(identifiers, item.key);
                if (matchResult.matched && matchResult.score > bestMatch.score) {{
                    bestMatch = {{ item: item, score: matchResult.score, identifier: matchResult.identifier }};
                }}
            }});
            
            // 如果找到匹配且分数足够高，填写
            if (bestMatch.item && bestMatch.score >= 50) {{
                fillInput(input, bestMatch.item.value);
                console.log(`✅ 填写输入框${{index + 1}}: "${{bestMatch.item.key}}" = "${{bestMatch.item.value}}" (匹配: "${{bestMatch.identifier}}", 分数: ${{bestMatch.score}})`);
                fillCount++;
                results.push({{
                    key: bestMatch.item.key,
                    value: bestMatch.item.value,
                    matched: bestMatch.identifier,
                    score: bestMatch.score,
                    success: true
                }});
            }}
        }});
        
        // 记录未匹配的名片字段
        const filledKeys = new Set(results.filter(r => r.success).map(r => r.key));
        fillData.forEach(item => {{
            if (!filledKeys.has(item.key)) {{
                const hasResult = results.some(r => r.key === item.key);
                if (!hasResult) {{
                    console.warn(`⚠️ 名片字段未使用: "${{item.key}}"`);
                    results.push({{
                        key: item.key,
                        value: item.value,
                        matched: null,
                        score: 0,
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
        
        console.log('\\n📊 填写完成:', result);
        return result;
    }}
    
    // 执行异步函数并将结果存储到全局变量
    executeAutoFill().then(result => {{
        window.__autoFillResult__ = result;
        console.log('✅ 结果已保存到 window.__autoFillResult__');
    }}).catch(error => {{
        console.error('❌ 执行出错:', error);
        window.__autoFillResult__ = {{
            fillCount: 0,
            totalCount: fillData.length,
            success: false,
            error: error.message || '未知错误',
            results: []
        }};
    }});
    
    // 立即返回一个临时结果
    return {{ status: 'executing', message: '正在异步执行...' }};
}})();
"""
        return js_code
    
    @staticmethod
    def generate_get_result_script() -> str:
        """生成获取填写结果的脚本"""
        return """
(function() {
    if (window.__autoFillResult__) {
        return window.__autoFillResult__;
    } else {
        return { status: 'waiting', message: '等待结果...' };
    }
})();
"""
    
    @staticmethod
    def generate_notification_script(fill_count: int, total_count: int) -> str:
        """生成显示通知的脚本"""
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

