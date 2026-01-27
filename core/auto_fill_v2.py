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
    
    // ═══════════════════════════════════════════════════════════════
    // 匹配关键词（优化版 - 直接比较字符串匹配度，优先完全匹配）
    // ═══════════════════════════════════════════════════════════════
    function matchKeyword(identifiers, cardKey) {{
        if (!cardKey) return {{ matched: false, identifier: null, score: 0 }};
        
        let bestScore = 0;
        let bestIdentifier = null;
        let bestSubKey = null;
        
        // ⚡️ 平台关键词识别与互斥检测（提前到函数开头，全局应用）
        const platformKeywordsMap = {{
            'wechat': ['微信', 'wx', 'vx', '微信号', '微信名', '微信昵称', '微信id'],
            'xiaohongshu': ['小红书', '红书', '小红薯', '红薯', 'xhs', '蒲公英', '平台昵称', '账号昵称', '账号名', '主页'],
            'douyin': ['抖音', 'dy', '抖音号'],
            'weibo': ['微博', 'wb', '微博号'],
            'bilibili': ['b站', 'bilibili', '哔哩哔哩', 'up主']
        }};
        
        const detectPlatform = (text) => {{
            if (!text) return 'unknown';
            const textLower = text.toLowerCase();
            for (const [platform, keywords] of Object.entries(platformKeywordsMap)) {{
                for (const keyword of keywords) {{
                    if (textLower.includes(keyword)) {{
                        return platform;
                    }}
                }}
            }}
            return 'unknown';
        }};
        
        // 检测名片字段的平台归属（全局检测一次）
        const configPlatform = detectPlatform(cardKey.toLowerCase());
        
        // 遍历每个表单标识符
        for (const identifier of identifiers) {{
            const cleanId = cleanText(identifier);
            if (!cleanId || cleanId.length < 1) continue;
            
            // 检测表单字段的平台归属
            const fieldPlatform = detectPlatform(cleanId);
            
            // 计算平台惩罚/加分因子（全局应用）
            let platformFactor = 1.0;
            if (fieldPlatform !== 'unknown' && configPlatform !== 'unknown') {{
                if (fieldPlatform !== configPlatform) {{
                    // 不同平台，大幅惩罚
                    platformFactor = 0.05;
                    console.log(`[平台互斥] 表单"${{cleanId}}"(${{fieldPlatform}}) vs 名片"${{cardKey}}"(${{configPlatform}}) → 惩罚0.05`);
                }} else {{
                    // 同一平台，加分
                    platformFactor = 1.2;
                }}
            }}
            
            // ⚡️【关键优化】第一步：检查表单标识是否在整个名片key中找到完全匹配
            // 这样即使名片key中有逗号，也不会被分割导致匹配失败
            const fullCleanCardKey = cleanText(cardKey);
            if (fullCleanCardKey.includes(cleanId) && cleanId.length >= 4) {{
                // 表单标识完全包含在名片key中，计算覆盖率
                const coverage = cleanId.length / fullCleanCardKey.length;
                let directScore = 0;
                
                // 检查是否是作为独立别名存在（通过原始文本中的分隔符判断）
                // 如果表单标识正好是原始key中用顿号/逗号分隔的某个别名
                const originalParts = cardKey.split(/[、，,;；|｜\\/／]/);
                const isExactAlias = originalParts.some(part => cleanText(part) === cleanId);
                
                // ⚡️【优先级优化】检查是否是独立字段（名片key整体等于表单标识）
                const isExactKeyMatch = fullCleanCardKey === cleanId;
                
                if (isExactKeyMatch) {{
                    // 名片key整体完全等于表单标识 → 105分（最高优先级）
                    directScore = 105;
                    console.log(`[精确匹配] "${{cleanId}}" 名片key完全匹配 → 105分`);
                }} else if (isExactAlias) {{
                    // 完全匹配原始key中的某个别名 → 100分
                    directScore = 100;
                    console.log(`[直接匹配] "${{cleanId}}" 完全匹配名片别名 → 100分`);
                }} else if (coverage >= 0.8) {{
                    // 高覆盖率包含 → 95分
                    directScore = 95;
                }} else if (coverage >= 0.5) {{
                    // 中等覆盖率包含 → 85分
                    directScore = 85;
                }} else {{
                    // 低覆盖率包含 → 70-80分
                    directScore = 70 + Math.floor(coverage * 20);
                }}
                
                // ⚡️ 应用平台惩罚/加分因子（新增）
                if (platformFactor !== 1.0) {{
                    directScore = Math.floor(directScore * platformFactor);
                }}
                
                if (directScore > bestScore) {{
                    bestScore = directScore;
                    bestIdentifier = identifier;
                    bestSubKey = cleanId;
                }}
            }}
            
            // 如果已经找到最高优先级匹配（105分=独立字段精确匹配），直接返回
            if (bestScore >= 105) break;
        }}
        
        // 如果直接匹配已经得到较高分数（>=80），不再做子关键词匹配，避免干扰
        if (bestScore >= 80) {{
            return {{ 
                matched: bestScore >= 50, 
                identifier: bestIdentifier, 
                score: bestScore,
                matchedKey: bestSubKey
            }};
        }}
        
        // 分割名片key为子关键词（用于处理没有直接匹配的情况）
        const cardKeywords = splitKeywords(cardKey).map(k => cleanText(k)).filter(k => k);
        if (cardKeywords.length === 0) {{
            return {{ matched: bestScore >= 50, identifier: bestIdentifier, score: bestScore, matchedKey: bestSubKey }};
        }}
        
        // 遍历每个表单标识符
        for (const identifier of identifiers) {{
            const cleanId = cleanText(identifier);
            if (!cleanId || cleanId.length < 1) continue;
            
            // 检测表单字段的平台归属
            const fieldPlatform = detectPlatform(cleanId);
            
            // 计算平台惩罚/加分因子
            let platformFactor = 1.0;
            if (fieldPlatform !== 'unknown' && configPlatform !== 'unknown') {{
                if (fieldPlatform !== configPlatform) {{
                    // 不同平台，大幅惩罚
                    platformFactor = 0.05;
                }} else {{
                    // 同一平台，加分
                    platformFactor = 1.2;
                }}
            }}
            
            // 遍历每个名片子关键词，计算匹配分数
            for (const ckw of cardKeywords) {{
                if (!ckw || ckw.length < 1) continue;
                
                let currentScore = 0;
                
                // 1. 完全匹配（100分）
                if (cleanId === ckw) {{
                    currentScore = 100;
                }}
                // 2. 表单标签包含名片子关键词（60-95分）
                else if (ckw.length >= 2 && cleanId.includes(ckw)) {{
                    const coverage = ckw.length / cleanId.length;
                    currentScore = 60 + Math.floor(coverage * 35);
                }}
                // 3. 名片子关键词包含表单标签（60-95分）
                else if (cleanId.length >= 2 && ckw.includes(cleanId)) {{
                    const coverage = cleanId.length / ckw.length;
                    currentScore = 60 + Math.floor(coverage * 35);
                }}
                // 4. 核心词匹配 - ⚡️降低分数，避免单核心词干扰
                else {{
                    const idCoreWords = extractCoreWords(cleanId);
                    const ckwCoreWords = extractCoreWords(ckw);
                    
                    if (idCoreWords.length > 0 && ckwCoreWords.length > 0) {{
                        const commonCore = idCoreWords.filter(w => ckwCoreWords.includes(w));
                        
                        if (commonCore.length > 0) {{
                            const matchRatio = commonCore.length / Math.max(idCoreWords.length, ckwCoreWords.length);
                            
                            // 核心词完全相同且至少2个
                            if (commonCore.length === idCoreWords.length && 
                                commonCore.length === ckwCoreWords.length &&
                                commonCore.length >= 2) {{
                                currentScore = 70;
                            }}
                            // 多个核心词部分匹配
                            else if (commonCore.length >= 2) {{
                                currentScore = 55 + Math.floor(matchRatio * 15);
                            }}
                            // 单核心词匹配 - ⚡️大幅降低分数（从85降到40）
                            else if (idCoreWords.length === 1 || ckwCoreWords.length === 1) {{
                                currentScore = 40;
                            }}
                        }}
                    }}
                }}
                
                // 5. LCS匹配（兜底，30-60分）
                if (currentScore === 0 && ckw.length >= 2 && cleanId.length >= 2) {{
                    const lcs = longestCommonSubstring(cleanId, ckw);
                    if (lcs >= 2) {{
                        const maxLen = Math.max(cleanId.length, ckw.length);
                        const coverage = lcs / maxLen;
                        if (coverage >= 0.5) {{
                            currentScore = 30 + Math.floor(coverage * 30);
                        }}
                    }}
                }}
                
                // ⚡️ 否定词不匹配惩罚：
                // 更精确的检测：检测否定词是否直接修饰业务关键词（如"非报备"、"不报备"）
                // 而不是简单检测字符串中是否存在否定词
                if (currentScore > 0) {{
                    const negationPatterns = ['非', '不', '无', '否', '未'];
                    const businessKeywords = ['报备', '报价', '返点', '授权', '挂车', '置顶', '分发'];
                    
                    // 检测否定词+业务关键词的组合
                    const hasNegatedBusinessKeyword = (text) => {{
                        for (const neg of negationPatterns) {{
                            for (const bk of businessKeywords) {{
                                if (text.includes(neg + bk)) return true;
                            }}
                        }}
                        return false;
                    }};
                    
                    const idHasNegation = hasNegatedBusinessKeyword(cleanId);
                    const ckwHasNegation = hasNegatedBusinessKeyword(ckw);
                    const hasBusinessKeyword = businessKeywords.some(bk => cleanId.includes(bk) || ckw.includes(bk));
                    
                    if (hasBusinessKeyword && idHasNegation !== ckwHasNegation) {{
                        console.log(`[否定词惩罚] "${{cleanId}}" vs "${{ckw}}": 否定状态不一致，分数从${{currentScore}}降为0`);
                        currentScore = 0;
                    }}
                }}
                
                // ⚡️ 应用平台惩罚/加分因子（新增）
                if (currentScore > 0 && platformFactor !== 1.0) {{
                    currentScore = Math.floor(currentScore * platformFactor);
                }}
                
                if (currentScore > bestScore) {{
                    bestScore = currentScore;
                    bestIdentifier = identifier;
                    bestSubKey = ckw;
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
        
        // ⚡️ 添加详细日志收集
        const matchLogs = [];
        
        // 等待输入框加载
        const hasInputs = await waitForInputs();
        
        if (!hasInputs) {{
            console.error('❌ 未找到任何输入框');
            return {{
                fillCount: 0,
                totalCount: fillData.length,
                success: false,
                error: '未找到任何输入框',
                results: [],
                matchLogs: []
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
        
        // ═══════════════════════════════════════════════════════════════
        // ⚡️【关键优化】两阶段匹配：先预扫描建立全局最优匹配，再按优先级填充
        // 解决问题：当名片字段包含多个别名时，应该优先匹配最精确的表单字段
        // ═══════════════════════════════════════════════════════════════
        
        // 第一阶段：预扫描所有表单字段和名片字段的匹配关系
        console.log('\\n📊 第一阶段：预扫描匹配关系...');
        const inputInfos = allInputs.map((input, index) => {{
            const identifiers = getInputIdentifiers(input);
            return {{ input, index, identifiers, mainTitle: identifiers[0] || '(无标题)' }};
        }});
        
        // 计算所有表单字段与名片字段的匹配分数矩阵
        const matchMatrix = [];
        inputInfos.forEach((inputInfo, inputIndex) => {{
            fillData.forEach((item, cardIndex) => {{
                const matchResult = matchKeyword(inputInfo.identifiers, item.key);
                if (matchResult.score > 0) {{
                    matchMatrix.push({{
                        inputIndex,
                        cardIndex,
                        input: inputInfo.input,
                        identifiers: inputInfo.identifiers,
                        mainTitle: inputInfo.mainTitle,
                        cardKey: item.key,
                        cardValue: item.value,
                        score: matchResult.score,
                        matched: matchResult.matched,
                        identifier: matchResult.identifier,
                        matchedKey: matchResult.matchedKey
                    }});
                }}
            }});
        }});
        
        // 按分数降序排序，高分优先
        matchMatrix.sort((a, b) => b.score - a.score);
        
        console.log(`   找到 ${{matchMatrix.length}} 个潜在匹配`);
        if (matchMatrix.length > 0) {{
            console.log(`   最高分: ${{matchMatrix[0].score.toFixed(1)}} (表单:"${{matchMatrix[0].mainTitle}}" ↔ 名片:"${{matchMatrix[0].cardKey.substring(0, 30)}}...")`);
        }}
        
        // 第二阶段：按分数优先级分配匹配（贪心算法）
        console.log('\\n📊 第二阶段：按优先级分配匹配...');
        const usedCardKeys = new Set();
        const usedInputIndices = new Set();
        const finalMatches = new Map(); // inputIndex -> matchInfo
        
        for (const match of matchMatrix) {{
            // 跳过已使用的表单字段或名片字段
            if (usedInputIndices.has(match.inputIndex) || usedCardKeys.has(match.cardKey)) {{
                continue;
            }}
            
            // 只接受分数>=50的匹配
            if (match.score >= 50) {{
                finalMatches.set(match.inputIndex, match);
                usedInputIndices.add(match.inputIndex);
                usedCardKeys.add(match.cardKey);
                console.log(`   ✅ 分配: 表单#${{match.inputIndex + 1}}"${{match.mainTitle}}" ← 名片"${{match.cardKey.substring(0, 25)}}..." (分数:${{match.score.toFixed(1)}})`);
            }}
        }}
        
        console.log(`\\n   共分配 ${{finalMatches.size}} 个匹配`);
        
        // 第三阶段：按表单字段顺序执行填充并打印日志
        console.log('\\n🎯 第三阶段：执行填充...');
        
        // 重置已使用集合（用于日志显示）
        const usedCardKeysForLog = new Set();
        
        inputInfos.forEach((inputInfo, index) => {{
            const {{ input, identifiers, mainTitle }} = inputInfo;
            
            // 打印表单字段标题
            console.log(`\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
            console.log(`📋 表单字段 #${{index + 1}}: "${{mainTitle}}"`);
            if (identifiers.length > 1) {{
                console.log(`   其他标识: [${{identifiers.slice(1, 4).map(i => '"' + i + '"').join(', ')}}${{identifiers.length > 4 ? '...' : ''}}]`);
            }}
            console.log(`   🔍 匹配过程:`);
            
            // ⚡️ 为每个表单字段创建日志条目
            const fieldLog = {{
                formField: mainTitle,
                identifiers: identifiers.slice(0, 5),
                candidates: []
            }};
            
            // 收集所有匹配结果用于排序显示（排除已使用的名片字段）
            const allMatches = [];
            fillData.forEach(item => {{
                if (usedCardKeysForLog.has(item.key)) return;
                const matchResult = matchKeyword(identifiers, item.key);
                allMatches.push({{
                    key: item.key,
                    value: item.value,
                    score: matchResult.score,
                    matched: matchResult.matched,
                    identifier: matchResult.identifier,
                    matchedKey: matchResult.matchedKey
                }});
                if (matchResult.score > 0) {{
                    fieldLog.candidates.push({{
                        cardKey: item.key.substring(0, 40),
                        score: matchResult.score,
                        matchedSubKey: matchResult.matchedKey,
                        matchedIdentifier: matchResult.identifier
                    }});
                }}
            }});
            
            // ⚡️ 按分数排序候选
            fieldLog.candidates.sort((a, b) => b.score - a.score);
            allMatches.sort((a, b) => b.score - a.score);
            
            // 打印候选列表
            const validMatches = allMatches.filter(m => m.score > 0);
            if (validMatches.length > 0) {{
                validMatches.slice(0, 5).forEach((m, i) => {{
                    const scoreBar = '█'.repeat(Math.max(0, Math.min(10, Math.floor(m.score / 10)))) + '░'.repeat(Math.max(0, 10 - Math.floor(m.score / 10)));
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
            
            // 检查是否有预分配的匹配
            const preMatch = finalMatches.get(index);
            if (preMatch) {{
                const filled = fillInput(input, preMatch.cardValue);
                if (filled) {{
                    usedCardKeysForLog.add(preMatch.cardKey);
                    console.log(`   ✅ 选中: "${{preMatch.cardKey}}" = "${{preMatch.cardValue}}" (分数: ${{preMatch.score.toFixed(1)}})`);
                    fillCount++;
                    results.push({{
                        key: preMatch.cardKey,
                        value: preMatch.cardValue,
                        matched: preMatch.identifier,
                        matchedKey: preMatch.matchedKey,
                        score: preMatch.score,
                        success: true
                    }});
                    fieldLog.selected = {{
                        cardKey: preMatch.cardKey.substring(0, 40),
                        value: String(preMatch.cardValue).substring(0, 30),
                        score: preMatch.score
                    }};
                }} else {{
                    console.warn(`   ⚠️ 填充失败（输入框可能是只读）`);
                    fieldLog.selected = null;
                    fieldLog.error = '填充失败（输入框可能是只读）';
                }}
            }} else {{
                console.log(`   ❌ 未匹配 (无预分配匹配或分数不足)`);
                fieldLog.selected = null;
            }}
            
            // ⚡️ 添加到日志
            matchLogs.push(fieldLog);
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
        
        // 返回结果（包含详细匹配日志）
        const result = {{
            fillCount: fillCount,
            totalCount: allInputs.length,
            success: fillCount > 0,
            results: results,
            matchLogs: matchLogs
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

