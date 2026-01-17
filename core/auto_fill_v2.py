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
    
    // 获取输入框的所有可能标识 - 麦客CRM增强版
    function getInputIdentifiers(input) {{
        const identifiers = [];
        const MAX_LABEL_LENGTH = 100;
        
        // 辅助函数：添加标识符（带去重和清理）
        function addIdentifier(text, priority = 0) {{
            if (!text) return;
            let cleaned = text.trim();
            // 去除序号前缀
            cleaned = cleaned.replace(/^[\\d\\*\\.、]+\\s*/, '').trim();
            // 去除必填标记
            cleaned = cleaned.replace(/[\\*必填]/g, '').trim();
            // 去除图标占位符（麦客CRM特有的 "." 占位）
            if (cleaned === '.') return;
            // 去除多余空白
            cleaned = cleaned.replace(/\\s+/g, ' ').trim();
            
            if (cleaned && cleaned.length > 0 && cleaned.length <= MAX_LABEL_LENGTH) {{
                // 去重
                if (!identifiers.some(item => item.text === cleaned)) {{
                    identifiers.push({{ text: cleaned, priority: priority }});
                }}
            }}
        }}
        
        // 0. 【最高优先级】麦客CRM特殊处理：通过 aria-labelledby 查找
        const ariaLabelledBy = input.getAttribute('aria-labelledby');
        if (ariaLabelledBy) {{
            const ids = ariaLabelledBy.split(' ');
            ids.forEach(id => {{
                const el = document.getElementById(id);
                if (el) {{
                    const text = (el.innerText || el.textContent || '').trim();
                    addIdentifier(text, 100);
                    console.log(`[麦客] aria-labelledby找到: "${{text}}" (id: ${{id}})`);
                }}
            }});
        }}
        
        // 1. 【麦客CRM增强】查找 .ReactModalPortal 或 .formMiddle 容器中的标签
        let formContainer = input.closest('.formMiddle, .handleForm, .wrapper, [class*="form-item"], [class*="field"]');
        if (formContainer) {{
            // 查找标签元素（麦客CRM可能使用多种class名称）
            const labelSelectors = [
                'label',
                '.form-label',
                '[class*="label"]',
                '[class*="title"]',
                'div[role="heading"]',
                'h3',
                'h4'
            ];
            
            for (const selector of labelSelectors) {{
                const labelEl = formContainer.querySelector(selector);
                if (labelEl && labelEl !== input && !labelEl.contains(input)) {{
                    const text = (labelEl.innerText || labelEl.textContent || '').trim();
                    addIdentifier(text, 95);
                    console.log(`[麦客] 容器标签找到: "${{text}}" (选择器: ${{selector}})`);
                    break;
                }}
            }}
            
            // 【关键】查找带图标的输入框结构：图标 + 文本可能在同一个父容器中
            // 麦客CRM结构：<div class="xxx"><i class="icon"></i><span>标签文本</span><input></div>
            const iconSiblings = formContainer.querySelectorAll('i + span, i + div, svg + span, svg + div, [class*="icon"] + span, [class*="icon"] + div');
            iconSiblings.forEach(el => {{
                const text = (el.innerText || el.textContent || '').trim();
                addIdentifier(text, 90);
                console.log(`[麦客] 图标后文本找到: "${{text}}"`);
            }});
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
        
        // 6. 【麦客CRM增强】向上查找包含标签的父元素（扩大搜索范围）
        let parent = input.parentElement;
        let depth = 0;
        while (parent && depth < 8) {{  // 增加深度到8层
            // 查找父元素中的 label 或标题元素
            const labelEl = parent.querySelector(':scope > label, :scope > div > label, :scope [class*="label"]:not(input), :scope [class*="title"]:not(input)');
            if (labelEl && labelEl !== input && !labelEl.contains(input)) {{
                const text = (labelEl.innerText || labelEl.textContent || '').trim();
                addIdentifier(text, 75 - depth * 5);
                console.log(`[麦客] 父元素[${{depth}}]标签找到: "${{text}}"`);
            }}
            
            // 【关键优化】获取父元素的直接文本内容（排除子元素的文本）
            let directText = '';
            Array.from(parent.childNodes).forEach(node => {{
                if (node.nodeType === Node.TEXT_NODE) {{
                    const txt = node.textContent.trim();
                    if (txt && txt.length > 0 && txt.length < 100) {{
                        directText += txt + ' ';
                    }}
                }} else if (node.nodeType === Node.ELEMENT_NODE && node !== input && !node.contains(input)) {{
                    // 获取不包含input的兄弟元素的文本（可能是图标后的标签）
                    const tagName = node.tagName.toLowerCase();
                    if (tagName === 'span' || tagName === 'div' || tagName === 'label') {{
                        const txt = (node.innerText || node.textContent || '').trim();
                        if (txt && txt.length > 0 && txt.length < 100) {{
                            directText += txt + ' ';
                        }}
                    }}
                }}
            }});
            
            if (directText.trim()) {{
                addIdentifier(directText.trim(), 70 - depth * 5);
                console.log(`[麦客] 父元素[${{depth}}]直接文本: "${{directText.trim()}}"`);
            }}
            
            parent = parent.parentElement;
            depth++;
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
    
    // 清理文本用于匹配
    function cleanText(text) {{
        if (!text) return '';
        return String(text)
            .toLowerCase()
            .replace(/[：:：*？?！!。.、，,\\s\\-_\\(\\)（）【】\\[\\]\\n\\r\\t\\/／\\\\|｜;；\\u0027\\u0022\\u2795+《》<>""'']/g, '')
            .trim();
    }}
    
    // 去除数字前缀
    function cleanTextNoPrefix(text) {{
        if (!text) return '';
        let cleaned = cleanText(text);
        cleaned = cleaned.replace(/^\\d+\\.?\\*?/, '');
        return cleaned.trim();
    }}
    
    // 分割关键词为子关键词数组
    function splitKeywords(keyword) {{
        if (!keyword) return [];
        return keyword
            .split(/[|,;，；、\\n\\r\\t/／\\\\｜\\u2795+]+/)
            .map(k => k.trim())
            .filter(k => k.length > 0);
    }}
    
    // 提取核心词
    function extractCoreWords(text) {{
        const cleaned = cleanText(text);
        const corePatterns = [
            '小红书', '蒲公英', '微信', '微博', '抖音', '快手', 'b站', '哔哩哔哩',
            'id', '账号', '昵称', '主页', '名字', '名称', '姓名', '用户名',
            '粉丝', '点赞', '赞藏', '互动', '阅读', '播放', '曝光', '收藏', '评论', '转发',
            '中位数', '均赞', 'cpm', 'cpe', 'cpc',
            '价格', '报价', '报备', '返点', '裸价', '预算', '费用', '单价',
            '视频', '图文', '链接', '笔记', '直播',
            '手机', '电话', '地址', '联系', '方式', '街道', '地区', '省', '市', '区', '邮编',
            '年龄', '性别', '城市', 'ip', '所在',
            '档期', '类别', '类型', '领域', '备注', '授权', '分发', '排竞', '分类',
            '平台', '健康', '等级', '保价', '配合', '时间', '探店', '日期',
            '护肤', '美妆', '好物', '分享', '时尚', '旅行', '母婴', '美食'
        ];
        const found = [];
        for (const pattern of corePatterns) {{
            if (cleaned.includes(pattern)) {{
                found.push(pattern);
            }}
        }}
        return found;
    }}
    
    // 计算最长连续公共子串长度
    function longestCommonSubstring(s1, s2) {{
        const m = s1.length, n = s2.length;
        if (m === 0 || n === 0) return 0;
        let maxLen = 0;
        const dp = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0));
        for (let i = 1; i <= m; i++) {{
            for (let j = 1; j <= n; j++) {{
                if (s1[i-1] === s2[j-1]) {{
                    dp[i][j] = dp[i-1][j-1] + 1;
                    maxLen = Math.max(maxLen, dp[i][j]);
                }}
            }}
        }}
        return maxLen;
    }}
    
    // 匹配关键词（增强版：动态覆盖率评分系统）
    function matchKeyword(identifiers, keyword) {{
        if (!keyword) return {{ matched: false, identifier: null, score: 0 }};
        
        const cleanKeyword = cleanText(keyword);
        if (!cleanKeyword) return {{ matched: false, identifier: null, score: 0 }};
        
        const cleanKeywordNoPrefix = cleanTextNoPrefix(keyword);
        
        // 分割成子关键词
        const subKeywords = splitKeywords(keyword).map(k => cleanText(k)).filter(k => k);
        if (subKeywords.length === 0) subKeywords.push(cleanKeyword);
        
        const subKeywordsNoPrefix = splitKeywords(keyword).map(k => cleanTextNoPrefix(k)).filter(k => k);
        if (subKeywordsNoPrefix.length === 0) subKeywordsNoPrefix.push(cleanKeywordNoPrefix);
        
        let bestScore = 0;
        let bestIdentifier = null;
        let bestSubKey = null;
        
        for (let i = 0; i < subKeywords.length; i++) {{
            const subKey = subKeywords[i];
            const subKeyNoPrefix = subKeywordsNoPrefix[i] || subKey;
            const subKeyCoreWords = extractCoreWords(subKey);
            
            for (const identifier of identifiers) {{
                const cleanIdentifier = cleanText(identifier);
                const cleanIdentifierNoPrefix = cleanTextNoPrefix(identifier);
                if (!cleanIdentifier) continue;
                
                const identifierCoreWords = extractCoreWords(identifier);
                let currentScore = 0;
                
                // 1. 完全匹配（100分）
                if (cleanIdentifier === subKey) {{
                    currentScore = 100;
                }}
                // 2. 去前缀后完全匹配（98分）
                else if (subKeyNoPrefix && cleanIdentifier === subKeyNoPrefix) {{
                    currentScore = 98;
                }}
                // 3. 表单标签包含名片key（50-95分）
                else if (cleanIdentifier.includes(subKey) && subKey.length >= 2) {{
                    const coverage = subKey.length / cleanIdentifier.length;
                    if (coverage >= 0.8) {{
                        currentScore = 95;
                    }} else if (coverage >= 0.5) {{
                        currentScore = 50 + (coverage * 45);
                    }} else {{
                        currentScore = 50 + (coverage * 40);
                    }}
                }}
                // 4. 去前缀后的包含匹配
                else if (subKeyNoPrefix && cleanIdentifier.includes(subKeyNoPrefix) && subKeyNoPrefix.length >= 2) {{
                    const coverage = subKeyNoPrefix.length / cleanIdentifier.length;
                    if (coverage >= 0.8) {{
                        currentScore = 93;
                    }} else {{
                        currentScore = 48 + (coverage * 40);
                    }}
                }}
                // 5. 名片key包含表单标签（反向包含）
                else if (subKey.includes(cleanIdentifier) && cleanIdentifier.length >= 2) {{
                    if (subKeyNoPrefix === cleanIdentifier) {{
                        currentScore = 96;
                    }} else {{
                        const coverage = cleanIdentifier.length / (subKeyNoPrefix.length || subKey.length);
                        currentScore = 55 + (coverage * 35);
                    }}
                }}
                // 6. 去前缀版本的反向包含
                else if (subKeyNoPrefix && subKeyNoPrefix.includes(cleanIdentifierNoPrefix) && cleanIdentifierNoPrefix.length >= 2) {{
                    const coverage = cleanIdentifierNoPrefix.length / subKeyNoPrefix.length;
                    currentScore = 53 + (coverage * 35);
                }}
                // 7. 核心词匹配
                else if (subKeyCoreWords.length > 0 && identifierCoreWords.length > 0) {{
                    const commonCoreWords = subKeyCoreWords.filter(w => identifierCoreWords.includes(w));
                    if (commonCoreWords.length > 0) {{
                        const coreMatchRatio = commonCoreWords.length / Math.max(subKeyCoreWords.length, identifierCoreWords.length);
                        
                        if (commonCoreWords.length === subKeyCoreWords.length && 
                            commonCoreWords.length === identifierCoreWords.length) {{
                            currentScore = 88;
                        }} else if (subKeyCoreWords.length === 1 && identifierCoreWords.length === 1) {{
                            currentScore = 80;
                        }} else {{
                            currentScore = 55 + Math.floor(coreMatchRatio * 25);
                        }}
                    }}
                }}
                // 8. 最长公共子串匹配（兜底）
                else if (subKey.length >= 2 && cleanIdentifier.length >= 2) {{
                    const lcs = longestCommonSubstring(subKey, cleanIdentifier);
                    const maxLen = Math.max(subKey.length, cleanIdentifier.length);
                    const minLen = Math.min(subKey.length, cleanIdentifier.length);
                    
                    if (lcs >= 2) {{
                        const coverage = lcs / maxLen;
                        const matchRate = lcs / minLen;
                        
                        if (matchRate >= 0.6 && lcs >= 3) {{
                            currentScore = 30 + (coverage * 20) + (matchRate * 15);
                        }} else if (matchRate >= 0.5 && lcs >= 2) {{
                            currentScore = 25 + (coverage * 15) + (matchRate * 10);
                        }}
                    }}
                }}
                
                if (currentScore > bestScore) {{
                    bestScore = currentScore;
                    bestIdentifier = identifier;
                    bestSubKey = subKey;
                }}
            }}
        }}
        
        const threshold = 50;
        return {{ 
            matched: bestScore >= threshold, 
            identifier: bestIdentifier, 
            score: bestScore,
            matchedKey: bestSubKey
        }};
    }}
    
    // 填充输入框 - React 深度兼容（麦客CRM使用React）
    function fillInput(input, value) {{
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
    
    // 主执行函数（异步） - 麦客CRM优化版
    async function executeAutoFill() {{
        console.log('\\n═══════════════════════════════════════════════════════════════');
        console.log('🎯 [麦客CRM v2.0] 开始自动填充');
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
        
        // 打印名片字段列表
        console.log('\\n📇 名片字段列表:');
        fillData.forEach((item, i) => {{
            const valuePreview = String(item.value).substring(0, 30) + (String(item.value).length > 30 ? '...' : '');
            console.log(`   ${{i + 1}}. "${{item.key}}" = "${{valuePreview}}"`);
        }});
        
        console.log('\\n🎯 开始匹配和填写...');
        
        const usedCardKeys = new Set();
        
        // 以输入框为主体遍历，为每个输入框找最佳匹配的名片字段
        allInputs.forEach((input, index) => {{
            const identifiers = getInputIdentifiers(input);
            let bestMatch = {{ item: null, score: 0, identifier: null, matchedKey: null }};
            
            // 打印表单字段标题
            const mainTitle = identifiers[0] || '(无标题)';
            console.log(`\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
            console.log(`📋 表单字段 #${{index + 1}}: "${{mainTitle}}"`);
            if (identifiers.length > 1) {{
                console.log(`   其他标识: [${{identifiers.slice(1, 4).map(i => '"' + i + '"').join(', ')}}${{identifiers.length > 4 ? '...' : ''}}]`);
            }}
            console.log(`   🔍 匹配过程:`);
            
            // 收集所有匹配结果用于排序显示
            const allMatches = [];
            
            // 在所有名片字段中找最佳匹配
            fillData.forEach(item => {{
                // 跳过已使用的名片字段（避免重复使用）
                if (usedCardKeys.has(item.key)) return;
                
                const matchResult = matchKeyword(identifiers, item.key);
                allMatches.push({{
                    key: item.key,
                    value: item.value,
                    score: matchResult.score,
                    matched: matchResult.matched,
                    identifier: matchResult.identifier,
                    matchedKey: matchResult.matchedKey
                }});
                
                if (matchResult.matched && matchResult.score > bestMatch.score) {{
                    bestMatch = {{ 
                        item: item, 
                        score: matchResult.score,
                        identifier: matchResult.identifier,
                        matchedKey: matchResult.matchedKey
                    }};
                }}
            }});
            
            // 按分数排序，只打印分数>0的匹配（最多显示前5个）
            allMatches.sort((a, b) => b.score - a.score);
            const validMatches = allMatches.filter(m => m.score > 0);
            if (validMatches.length > 0) {{
                validMatches.slice(0, 5).forEach((m, i) => {{
                    const scoreBar = '█'.repeat(Math.floor(m.score / 10)) + '░'.repeat(10 - Math.floor(m.score / 10));
                    const status = m.score >= 50 ? (i === 0 ? '🏆' : '✓') : '✗';
                    const valuePreview = String(m.value).substring(0, 15) + (String(m.value).length > 15 ? '...' : '');
                    console.log(`      ${{status}} "${{m.key}}" → ${{m.score.toFixed(1)}}分 [${{scoreBar}}] ${{m.identifier ? '(标识:"' + m.identifier + '")' : ''}} 值="${{valuePreview}}"`);
                }});
                if (validMatches.length > 5) {{
                    console.log(`      ... 还有 ${{validMatches.length - 5}} 个候选 ...`);
                }}
            }} else {{
                console.log(`      (无匹配候选)`);
            }}
            
            // 如果找到匹配且分数足够高，填写（阈值 50）
            if (bestMatch.item && bestMatch.score >= 50) {{
                const filled = fillInput(input, bestMatch.item.value);
                if (filled) {{
                    usedCardKeys.add(bestMatch.item.key);
                    console.log(`   ✅ 选中: "${{bestMatch.item.key}}" = "${{bestMatch.item.value}}" (分数: ${{bestMatch.score.toFixed(1)}})`);
                    fillCount++;
                    results.push({{
                        key: bestMatch.item.key,
                        value: bestMatch.item.value,
                        matched: bestMatch.identifier,
                        matchedKey: bestMatch.matchedKey,
                        score: bestMatch.score,
                        success: true
                    }});
                }} else {{
                    console.warn(`   ⚠️ 填充失败（输入框可能是只读）`);
                }}
            }} else {{
                console.log(`   ❌ 未匹配 (最高分: ${{bestMatch.score ? bestMatch.score.toFixed(1) : '0'}}, 需要>=50)`);
            }}
        }});
        
        // 记录未匹配的名片字段
        console.log('\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.log('📊 匹配汇总:');
        const filledKeys = new Set(results.filter(r => r.success).map(r => r.key));
        const unusedFields = fillData.filter(item => !filledKeys.has(item.key));
        if (unusedFields.length > 0) {{
            console.log(`⚠️ 未使用的名片字段 (${{unusedFields.length}}个):`);
            unusedFields.forEach(item => {{
                console.warn(`   - "${{item.key}}" = "${{String(item.value).substring(0, 20)}}..."`);
                results.push({{
                    key: item.key,
                    value: item.value,
                    matched: null,
                    score: 0,
                    success: false
                }});
            }});
        }} else {{
            console.log(`✅ 所有名片字段都已使用`);
        }}
        
        // 返回结果
        const result = {{
            fillCount: fillCount,
            totalCount: allInputs.length,
            success: fillCount > 0,
            results: results
        }};
        
        console.log('\\n═══════════════════════════════════════════════════════════════');
        console.log(`📊 填充完成: ${{fillCount}}/${{allInputs.length}} 个输入框`);
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

