"""
自动填写引擎 V2 - 增强版（使用共享匹配算法）
支持麦客CRM（mikecrm.com）和麦客企业版（mike-x.com）
"""
import json
from typing import List, Dict


class AutoFillEngineV2:
    """自动填写引擎 V2 - 麦客CRM/企业版"""
    
    @staticmethod
    def generate_fill_script(fill_data: List[Dict[str, str]]) -> str:
        """
        生成自动填写的 JavaScript 脚本（使用共享算法）
        """
        from core.tencent_docs_filler import TencentDocsFiller
        
        fill_data_json = json.dumps(fill_data, ensure_ascii=False)
        
        # 获取共享算法和执行逻辑
        shared_algorithm = TencentDocsFiller.get_shared_match_algorithm()
        shared_executor = TencentDocsFiller.get_shared_execution_logic()
        
        js_code = f"""
(function() {{
    console.log('🚀 开始自动填写 麦客CRM（共享算法版）...');
    console.log('⏳ 等待表单元素加载...');
    
    const fillData = {fill_data_json};
    
    // ═══════════════════════════════════════════════════════════════
    // 共享匹配算法（来自 TencentDocsFiller）
    // ═══════════════════════════════════════════════════════════════
    {shared_algorithm}
    
    // ═══════════════════════════════════════════════════════════════
    // 共享执行逻辑（来自 TencentDocsFiller）
    // ═══════════════════════════════════════════════════════════════
    {shared_executor}
    
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
    
    // 获取输入框的所有可能标识 - 麦客CRM增强版
    function getInputIdentifiers(input) {{
        const identifiers = [];
        // 普通标识符的最大长度（防止多字段连接）
        const MAX_LABEL_LENGTH = 50;
        // ⚡️ 主标题的最大长度（麦客的 t- 开头的 ID，允许更长）
        const MAX_TITLE_LENGTH = 150;
        
        // 辅助函数：添加标识符（带去重和清理）
        function addIdentifier(text, priority = 0, isMainTitle = false) {{
            if (!text) return;
            let cleaned = text.trim();
            // 去除序号前缀
            cleaned = cleaned.replace(/^[\\d\\*\\.、]+\\s*/, '').trim();
            // 去除必填标记（注意：只去除 * 和 "必填" 整词，不能用字符类误删"填"字）
            cleaned = cleaned.replace(/\\*/g, '').replace(/必填/g, '').trim();
            // 去除图标占位符（麦客CRM特有的 "." 占位）
            if (cleaned === '.') return;
            // 去除多余空白
            cleaned = cleaned.replace(/\\s+/g, ' ').trim();
            
            // 根据是否是主标题决定长度限制
            const maxLen = isMainTitle ? MAX_TITLE_LENGTH : MAX_LABEL_LENGTH;
            
            // 对于非主标题，过滤掉包含多个空格的标识符（可能是多个字段名连接）
            if (!isMainTitle) {{
                const spaceCount = (cleaned.match(/\\s/g) || []).length;
                if (spaceCount > 2) {{
                    return;
                }}
            }}
            
            if (cleaned && cleaned.length > 0 && cleaned.length <= maxLen) {{
                // 去重
                if (!identifiers.some(item => item.text === cleaned)) {{
                    identifiers.push({{ text: cleaned, priority: priority }});
                }}
            }}
        }}
        
        // 0. 【最高优先级】麦客CRM特殊处理：通过 aria-labelledby 查找
        // ⚡️ 优先处理 t- 开头的 ID（主标题），给予最高优先级和更长的长度限制
        const ariaLabelledBy = input.getAttribute('aria-labelledby');
        if (ariaLabelledBy) {{
            const ids = ariaLabelledBy.split(' ');
            // 先处理 t- 开头的主标题
            ids.forEach(id => {{
                if (id.startsWith('t-')) {{
                    const el = document.getElementById(id);
                    if (el) {{
                        const text = (el.innerText || el.textContent || '').trim();
                        // 主标题使用更高的优先级和更长的长度限制
                        addIdentifier(text, 110, true);
                        console.log(`[麦客] 主标题(t-): "${{text.substring(0, 50)}}${{text.length > 50 ? '...' : ''}}" (id: ${{id}})`);
                    }}
                }}
            }});
            // 再处理其他 ID（sub- 副标题等）
            ids.forEach(id => {{
                if (!id.startsWith('t-')) {{
                    const el = document.getElementById(id);
                    if (el) {{
                        const text = (el.innerText || el.textContent || '').trim();
                        addIdentifier(text, 90);
                        if (text && text.length > 0) {{
                            console.log(`[麦客] 副标题: "${{text}}" (id: ${{id}})`);
                        }}
                    }}
                }}
            }});
        }}
        
        // 1. 【麦客CRM增强】查找直接包含该输入框的最小容器中的标签
        // ⚡️ 关键修复：只查找只包含当前输入框（不包含其他输入框）的容器
        let formItemContainer = null;
        let parent = input.parentElement;
        let depth = 0;
        while (parent && depth < 6) {{
            // 检查这个容器是否只包含当前这一个输入框
            const inputsInParent = parent.querySelectorAll('input, textarea');
            if (inputsInParent.length === 1 && inputsInParent[0] === input) {{
                // 这是直接包含该输入框的容器
                formItemContainer = parent;
            }} else if (inputsInParent.length > 1) {{
                // 包含多个输入框，停止向上查找
                break;
            }}
            parent = parent.parentElement;
            depth++;
        }}
        
        if (formItemContainer) {{
            // 查找标签元素（麦客CRM可能使用多种class名称）
            const labelSelectors = [
                ':scope > label',
                ':scope > .form-label',
                ':scope > [class*="label"]',
                ':scope > p > span',
                ':scope > p',
                ':scope > div > label'
            ];
            
            for (const selector of labelSelectors) {{
                const labelEl = formItemContainer.querySelector(selector);
                if (labelEl && labelEl !== input && !labelEl.contains(input)) {{
                    const text = (labelEl.innerText || labelEl.textContent || '').trim();
                    // 过滤掉太长的文本（可能是多个字段的组合）
                    if (text && text.length > 0 && text.length <= 20) {{
                        addIdentifier(text, 95);
                        console.log(`[麦客] 容器标签找到: "${{text}}" (选择器: ${{selector}})`);
                        break;
                    }}
                }}
            }}
        }}
        
        // 2. Label 标签
        if (input.labels && input.labels.length > 0) {{
            input.labels.forEach(label => {{
                const text = (label.innerText || label.textContent || '').trim();
                addIdentifier(text, 85);
            }});
        }}
        
        // 3. 通过 for 属性查找 label
        if (input.id) {{
            const label = document.querySelector(`label[for="${{input.id}}"]`);
            if (label) {{
                const text = (label.innerText || label.textContent || '').trim();
                addIdentifier(text, 85);
            }}
        }}
        
        // 4. aria-label 属性
        if (input.getAttribute('aria-label')) {{
            addIdentifier(input.getAttribute('aria-label'), 80);
        }}
        
        // 5. placeholder
        if (input.placeholder) {{
            addIdentifier(input.placeholder, 70);
        }}
        
        // 6. 【麦客CRM增强】向上查找包含标签的父元素
        // ⚡️ 关键修复：如果已经找到了有效的主标识符，就不再向上遍历
        // 这样可以避免找到整个表单容器中其他字段的标签（如"主页名称"）
        if (identifiers.length === 0) {{
            let parent = input.parentElement;
            let depth = 0;
            while (parent && depth < 5) {{  // 减少深度到5层，避免遍历到表单容器
                // 检查是否已经遍历到了表单级别的容器，如果是就停止
                const parentClasses = parent.className || '';
                if (parentClasses.includes('form') || parentClasses.includes('wrapper') || 
                    parent.tagName === 'FORM' || parent.querySelectorAll('input, textarea').length > 1) {{
                    // 这是表单容器，停止遍历
                    console.log(`[麦客] 到达表单容器，停止向上遍历`);
                    break;
                }}
                
                // 查找父元素中的 label 或标题元素
                const labelEl = parent.querySelector(':scope > label, :scope > div > label, :scope [class*="label"]:not(input), :scope [class*="title"]:not(input)');
                if (labelEl && labelEl !== input && !labelEl.contains(input)) {{
                    const text = (labelEl.innerText || labelEl.textContent || '').trim();
                    addIdentifier(text, 75 - depth * 5);
                    console.log(`[麦客] 父元素[${{depth}}]标签找到: "${{text}}"`);
                    // ⚡️ 找到一个有效标签后就停止
                    break;
                }}
                
                // 获取父元素的直接文本内容（排除子元素的文本）
                let directText = '';
                Array.from(parent.childNodes).forEach(node => {{
                    if (node.nodeType === Node.TEXT_NODE) {{
                        const txt = node.textContent.trim();
                        if (txt && txt.length > 0 && txt.length < 50) {{
                            directText += txt + ' ';
                        }}
                    }} else if (node.nodeType === Node.ELEMENT_NODE && node !== input && !node.contains(input)) {{
                        const tagName = node.tagName.toLowerCase();
                        if (tagName === 'span' || tagName === 'div' || tagName === 'label') {{
                            const txt = (node.innerText || node.textContent || '').trim();
                            if (txt && txt.length > 0 && txt.length < 50) {{
                                directText += txt + ' ';
                            }}
                        }}
                    }}
                }});
                
                if (directText.trim()) {{
                    addIdentifier(directText.trim(), 70 - depth * 5);
                    console.log(`[麦客] 父元素[${{depth}}]直接文本: "${{directText.trim()}}"`);
                    // ⚡️ 找到有效文本后就停止
                    break;
                }}
                
                parent = parent.parentElement;
                depth++;
            }}
        }}
        
        // 7. 前置兄弟元素（包括图标和文本）
        let sibling = input.previousElementSibling;
        let siblingCount = 0;
        while (sibling && siblingCount < 5) {{  // 增加搜索数量
            // 提取兄弟元素的文本（过滤掉纯图标元素）
            const text = (sibling.innerText || sibling.textContent || '').trim();
            const tagName = sibling.tagName.toLowerCase();
            
            // 跳过纯图标元素（i, svg等），但要获取它们后面的文本
            if (tagName === 'i' || tagName === 'svg' || sibling.className.includes('icon')) {{
                // 检查图标后是否有文本
                const nextSibling = sibling.previousElementSibling;
                if (nextSibling) {{
                    const nextText = (nextSibling.innerText || nextSibling.textContent || '').trim();
                    addIdentifier(nextText, 60 - siblingCount * 5);
                }}
            }} else if (text && text.length > 0 && text.length < 100) {{
                addIdentifier(text, 65 - siblingCount * 5);
            }}
            
            sibling = sibling.previousElementSibling;
            siblingCount++;
        }}
        
        // 8. name/id/title 属性（降低优先级）
        if (input.name) addIdentifier(input.name, 50);
        if (input.id) addIdentifier(input.id, 50);
        if (input.title) addIdentifier(input.title, 50);
        
        // ⚡️ 9. 【麦客CRM特殊处理】如果仍未找到标识符，尝试查找输入框所在表单项的标签
        // 麦客CRM的某些字段（如微信昵称、微信号）使用特殊的DOM结构
        if (identifiers.length === 0) {{
            // 方法1: 查找包含当前输入框的最近的 form-item 类元素
            let formItem = input.closest('[class*="form-item"], [class*="field"], [class*="question"]');
            if (formItem) {{
                // 在这个表单项中查找标签
                const labelEl = formItem.querySelector('[class*="label"], [class*="title"], label, p > span');
                if (labelEl && !labelEl.contains(input)) {{
                    const text = (labelEl.innerText || labelEl.textContent || '').trim();
                    if (text && text.length > 0 && text.length <= MAX_LABEL_LENGTH) {{
                        addIdentifier(text, 65);
                        console.log(`[麦客] form-item标签找到: "${{text}}"`);
                    }}
                }}
            }}
            
            // 方法2: 根据输入框在DOM中的位置，查找前面最近的标签文本
            // 遍历所有前面的兄弟节点和父节点的前面兄弟
            let currentNode = input;
            let searchDepth = 0;
            while (identifiers.length === 0 && searchDepth < 10) {{
                // 检查当前节点的前一个兄弟
                let prevSibling = currentNode.previousElementSibling;
                while (prevSibling && identifiers.length === 0) {{
                    // 检查这个兄弟节点是否是标签
                    const text = (prevSibling.innerText || prevSibling.textContent || '').trim();
                    // 麦客CRM的标签通常包含 "*" 必填标记
                    if (text && text.includes('*') && text.length <= MAX_LABEL_LENGTH) {{
                        // 去掉 "*" 后添加
                        const cleanLabel = text.replace(/\\*/g, '').trim();
                        if (cleanLabel.length > 0 && cleanLabel.length <= MAX_LABEL_LENGTH) {{
                            addIdentifier(cleanLabel, 60);
                            console.log(`[麦客] 前兄弟标签找到: "${{cleanLabel}}"`);
                            break;
                        }}
                    }}
                    // 如果是包含输入框的容器，跳过
                    if (prevSibling.querySelector && prevSibling.querySelector('input, textarea')) {{
                        break;
                    }}
                    prevSibling = prevSibling.previousElementSibling;
                }}
                // 向上移动到父元素
                currentNode = currentNode.parentElement;
                if (!currentNode || currentNode.tagName === 'FORM' || currentNode.tagName === 'BODY') break;
                searchDepth++;
            }}
        }}
        
        // 按优先级排序，优先级高的在前
        identifiers.sort((a, b) => {{
            if (b.priority !== a.priority) return b.priority - a.priority;
            // 优先级相同时，短标题优先（更精确）
            return a.text.length - b.text.length;
        }});
        
        const result = identifiers.map(item => item.text);
        if (result.length > 0) {{
            console.log(`[麦客] 输入框标识符: [${{result.slice(0, 3).join(' | ')}}]`);
        }} else {{
            console.warn(`[麦客] ⚠️ 输入框未找到标识符`);
        }}
        return result;
    }}
    
    // 填充输入框 - React 深度兼容（麦客CRM使用React）
    function fillInputMike(input, value) {{
        if (!input || input.readOnly || input.disabled) return false;
        
        // 1. 聚焦输入框
        input.focus();
        input.click();
        
        // 2. 清空现有内容（触发 React 状态清除）
        input.value = '';
        
        // 3. 使用原生 setter 设置值（React 关键）
        const isTextArea = input.tagName === 'TEXTAREA';
        const proto = isTextArea ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
        
        try {{
            const nativeValueSetter = Object.getOwnPropertyDescriptor(proto, 'value').set;
            nativeValueSetter.call(input, value);
        }} catch (e) {{
            input.value = value;
        }}
        
        // 4. 触发 React 合成事件 - 使用 InputEvent（关键！）
        const inputEvent = new InputEvent('input', {{
            bubbles: true,
            cancelable: true,
            inputType: 'insertText',
            data: value
        }});
        input.dispatchEvent(inputEvent);
        
        // 5. 触发 change 事件
        const changeEvent = new Event('change', {{ bubbles: true, cancelable: true }});
        input.dispatchEvent(changeEvent);
        
        // 6. 模拟键盘事件序列（某些框架依赖这些事件）
        const keyboardEvents = ['keydown', 'keypress', 'keyup'];
        keyboardEvents.forEach(eventName => {{
            const keyEvent = new KeyboardEvent(eventName, {{
                bubbles: true,
                cancelable: true,
                key: value.slice(-1) || 'a',
                code: 'KeyA'
            }});
            input.dispatchEvent(keyEvent);
        }});
        
        // 7. 再次确认值已设置
        if (input.value !== value) {{
            input.value = value;
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}
        
        // 8. 触发 blur 完成编辑
        input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
        
        // 9. 尝试触发 React 内部状态更新
        try {{
            // React Fiber 节点查找
            const reactKey = Object.keys(input).find(key => 
                key.startsWith('__reactFiber$') || 
                key.startsWith('__reactInternalInstance$') ||
                key.startsWith('__reactProps$')
            );
            if (reactKey && input[reactKey]) {{
                const props = input[reactKey].memoizedProps || input[reactKey].pendingProps || {{}};
                if (props.onChange) {{
                    props.onChange({{ target: input, currentTarget: input }});
                }}
            }}
        }} catch (e) {{}}
        
        return input.value === value;
    }}
    
    // 主执行函数（异步） - 使用共享执行器
    async function executeAutoFill() {{
        console.log('\\n═══════════════════════════════════════════════════════════════');
        console.log('🎯 [麦客CRM v3.0 共享算法] 开始自动填充');
        console.log('═══════════════════════════════════════════════════════════════');
        console.log(`页面URL: ${{window.location.href}}`);
        console.log(`页面标题: ${{document.title}}`);
        
        // 等待输入框加载
        const hasInputs = await waitForInputs();
        
        if (!hasInputs) {{
            console.error('❌ 未找到任何输入框');
            return {{
                fillCount: 0,
                totalCount: fillData.length,
                success: false,
                error: '未找到任何输入框',
                results: []
            }};
        }}
        
        // 获取所有输入框
        console.log('\\n📋 扫描页面输入框...');
        const allInputs = getAllInputs();
        console.log(`找到 ${{allInputs.length}} 个输入框`);
        
        // 使用共享执行器
        const executor = createSharedExecutor({{
            fillData: fillData,
            allInputs: allInputs,
            getIdentifiers: getInputIdentifiers,
            fillInput: fillInputMike,
            onProgress: (msg) => console.log(msg)
        }});
        
        const result = await executor.execute();
        
        console.log('\\n═══════════════════════════════════════════════════════════════');
        console.log(`📊 填充完成: ${{result.fillCount}}/${{result.totalCount}} 个输入框`);
        console.log('═══════════════════════════════════════════════════════════════\\n');
        
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

