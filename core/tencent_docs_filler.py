"""
腾讯文档表单填写引擎
专门针对腾讯文档（docs.qq.com）表单的自动填写
"""
import re
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class SharedMatchAlgorithm:
    """
    共享的匹配算法（Python 版本）
    可被多个平台复用：报名工具等需要 Python 端匹配的平台
    """
    
    @staticmethod
    def clean_text(text: str) -> str:
        """清理文本用于匹配"""
        if not text:
            return ''
        text = str(text).lower()
        # 去除特殊字符
        text = re.sub(r'[：:*？?！!。.、，,\s\-_\(\)（）【】\[\]]+', '', text)
        return text.strip()
    
    @staticmethod
    def split_keywords(keyword: str) -> List[str]:
        """分割关键词为子关键词数组"""
        if not keyword:
            return []
        parts = re.split(r'[|,;，；、\n\r\t/／\\｜\u2795+]+', keyword)
        return [SharedMatchAlgorithm.clean_text(p) for p in parts if p.strip()]
    
    @staticmethod
    def match_keyword(identifiers, keyword: str) -> Dict:
        """
        匹配关键词 - 评分系统（与 JavaScript 版本保持一致）
        
        Args:
            identifiers: 标识符列表或单个标题字符串
            keyword: 关键词（支持 |,;，；、 分隔的多个关键词）
            
        Returns:
            Dict: { matched: bool, score: int, identifier: str, matchedKey: str }
        """
        if not keyword:
            return {'matched': False, 'identifier': None, 'score': 0, 'matchedKey': None}
        
        # 支持传入标题字符串或标识符数组
        if isinstance(identifiers, str):
            identifiers = [identifiers]
        
        clean_keyword = SharedMatchAlgorithm.clean_text(keyword)
        if not clean_keyword:
            return {'matched': False, 'identifier': None, 'score': 0, 'matchedKey': None}
        
        # 分割子关键词
        sub_keywords = SharedMatchAlgorithm.split_keywords(keyword)
        if not sub_keywords:
            sub_keywords = [clean_keyword]
        
        best_score = 0
        best_identifier = None
        best_sub_key = None
        
        for sub_key in sub_keywords:
            if not sub_key:
                continue
                
            for identifier in identifiers:
                clean_identifier = SharedMatchAlgorithm.clean_text(identifier)
                if not clean_identifier:
                    continue
                
                current_score = 0
                
                # 1. 完全匹配（100分）
                if clean_identifier == sub_key:
                    current_score = 100
                # 2. 包含匹配（80-90分）
                elif sub_key in clean_identifier:
                    ratio = len(sub_key) / len(clean_identifier)
                    current_score = 80 + (ratio * 10)
                elif clean_identifier in sub_key:
                    current_score = 70
                # 3. 字符相似度匹配（30-60分）
                else:
                    common = sum(1 for c in sub_key if c in clean_identifier)
                    similarity = common / len(sub_key) if sub_key else 0
                    if similarity >= 0.5:
                        current_score = int(similarity * 60)
                
                if current_score > best_score:
                    best_score = current_score
                    best_identifier = identifier
                    best_sub_key = sub_key
        
        threshold = 50
        return {
            'matched': best_score >= threshold,
            'identifier': best_identifier,
            'score': best_score,
            'matchedKey': best_sub_key
        }


class TencentDocsFiller:
    """腾讯文档表单填写引擎"""
    
    def __init__(self):
        self.logger = logger
    
    @staticmethod
    def get_shared_match_algorithm() -> str:
        """
        获取共享的匹配算法 JavaScript 代码
        这个算法可以被多个表单平台复用（腾讯文档、WPS 等）
        
        Returns:
            JavaScript 函数代码字符串，包含：
            - cleanText(): 清理文本
            - splitKeywords(): 分割关键词
            - matchKeyword(): 匹配关键词（评分系统）
        """
        return """
    /**
     * 清理文本用于匹配
     */
    function cleanText(text) {
        if (!text) return '';
        return String(text).toLowerCase().replace(/[：:*？?！!。.、，,\\s\\-_\\(\\)（）【】\\[\\]]/g, '').trim();
    }
    
    /**
     * 分割关键词为子关键词数组
     */
    function splitKeywords(keyword) {
        if (!keyword) return [];
        return keyword
            .split(/[|,;，；、\\n\\r\\t/／\\\\｜\\u2795+]+/)
            .map(k => k.trim())
            .filter(k => k.length > 0);
    }
    
    /**
     * 匹配关键词 - 评分系统（支持多关键词）
     * @param {string|Array<string>} titleOrIdentifiers - 标题字符串或标识符数组
     * @param {string} keyword - 关键词（支持 |,;，；、 分隔的多个关键词）
     * @returns {Object} { matched: boolean, score: number, identifier: string, matchedKey: string }
     */
    function matchKeyword(titleOrIdentifiers, keyword) {
        if (!keyword) return { matched: false, identifier: null, score: 0 };
        
        // 支持传入标题字符串或标识符数组
        const identifiers = Array.isArray(titleOrIdentifiers) ? titleOrIdentifiers : [titleOrIdentifiers];
        
        const cleanKeyword = cleanText(keyword);
        if (!cleanKeyword) return { matched: false, identifier: null, score: 0 };
        
        // 支持顿号、逗号、竖线分隔的多个关键词
        const subKeywords = splitKeywords(keyword).map(k => cleanText(k)).filter(k => k);
        if (subKeywords.length === 0) subKeywords.push(cleanKeyword);
        
        let bestScore = 0;
        let bestIdentifier = null;
        let bestSubKey = null;
        
        for (const subKey of subKeywords) {
            for (const identifier of identifiers) {
                const cleanIdentifier = cleanText(identifier);
                if (!cleanIdentifier) continue;
                
                let currentScore = 0;
                
                // 1. 完全匹配（100分）
                if (cleanIdentifier === subKey) {
                    currentScore = 100;
                }
                // 2. 包含匹配（80-90分）
                else if (cleanIdentifier.includes(subKey)) {
                    const ratio = subKey.length / cleanIdentifier.length;
                    currentScore = 80 + (ratio * 10);
                }
                else if (subKey.includes(cleanIdentifier)) {
                    currentScore = 70;
                }
                // 3. 字符相似度匹配（30-60分）
                else {
                    let common = 0;
                    for (const c of subKey) {
                        if (cleanIdentifier.includes(c)) common++;
                    }
                    const similarity = common / subKey.length;
                    if (similarity >= 0.5) {
                        currentScore = Math.floor(similarity * 60);
                    }
                }
                
                if (currentScore > bestScore) {
                    bestScore = currentScore;
                    bestIdentifier = identifier;
                    bestSubKey = subKey;
                }
            }
        }
        
        const threshold = 50;
        return { 
            matched: bestScore >= threshold, 
            identifier: bestIdentifier, 
            score: bestScore,
            matchedKey: bestSubKey
        };
    }
"""
    
    @staticmethod
    def get_shared_execution_logic() -> str:
        """
        获取共享的执行逻辑 JavaScript 代码
        这个函数可以被多个表单平台复用（腾讯文档、WPS 等）
        
        核心逻辑：逐个遍历输入框 + 独立匹配（名片数据可以被多次使用）
        
        Returns:
            JavaScript 函数代码字符串：createSharedExecutor(config)
            
        使用方法：
            const executor = createSharedExecutor({
                fillData: [...],              // 名片数据数组
                allInputs: [...],             // 所有输入框数组
                getIdentifiers: (input, i) => [...],  // 获取输入框标识符的函数
                fillInput: (input, value) => {},      // 填充函数
                onProgress: (msg) => {}       // 进度回调（可选）
            });
            await executor.execute();
        """
        return """
    /**
     * 创建共享的表单填充执行器（腾讯文档算法）
     * @param {Object} config - 配置对象
     * @returns {Object} - 执行器对象，包含 execute() 方法
     */
    function createSharedExecutor(config) {
        const {
            fillData,           // 名片数据数组 [{ key: '...', value: '...' }, ...]
            allInputs,          // 所有输入框数组
            getIdentifiers,     // 函数：(input, index) => [标识符数组]
            fillInput,          // 函数：(input, value) => {} 执行填充
            onProgress          // 可选回调：(message) => {} 进度信息
        } = config;
        
        const log = onProgress || console.log;
        
        return {
            async execute() {
                log('\\n═══════════════════════════════════════════════════════════════');
                log('📋 扫描页面输入框...');
                log('═══════════════════════════════════════════════════════════════');
                log(`找到 ${allInputs.length} 个输入框`);
                
                // 打印名片字段列表
                log('\\n📇 名片字段列表:');
                fillData.forEach((item, i) => {
                    const valuePreview = String(item.value).substring(0, 20) + 
                                        (String(item.value).length > 20 ? '...' : '');
                    log(`   ${i + 1}. "${item.key}" = "${valuePreview}"`);
                });
                
                log('\\n═══════════════════════════════════════════════════════════════');
                log('📝 开始逐个匹配并填充（腾讯文档算法）...');
                log('═══════════════════════════════════════════════════════════════');
                
                let fillCount = 0;
                const results = [];
                const usedCardKeys = new Set();
                
                // 遍历每个输入框（类似腾讯文档的 fillQuestion）
                for (let i = 0; i < allInputs.length; i++) {
                    const input = allInputs[i];
                    const identifiers = getIdentifiers(input, i);
                    const mainTitle = identifiers.length > 0 ? identifiers[0] : '(无标题)';
                    
                    log(`\\n--- 输入框 ${i + 1}/${allInputs.length} ---`);
                    log(`  📝 标题: "${mainTitle}"`);
                    if (identifiers.length > 1) {
                        log(`  🏷️  备选标识: [${identifiers.slice(1, 3).join(', ')}]`);
                    }
                    
                    // 对当前输入框，查找最高分的名片数据（独立匹配）
                    let matchedKey = null;
                    let matchedValue = null;
                    let maxScore = 0;
                    let matchedCardItem = null;
                    
                    for (const cardItem of fillData) {
                        const result = matchKeyword(identifiers, cardItem.key);
                        if (result.matched && result.score > maxScore) {
                            maxScore = result.score;
                            matchedKey = cardItem.key;
                            matchedValue = cardItem.value;
                            matchedCardItem = cardItem;
                        }
                    }
                    
                    // 只接受分数>=50的匹配
                    if (!matchedKey || maxScore < 50) {
                        log(`  ⚠️  未找到匹配 (最高分: ${maxScore.toFixed(1)})`);
                        continue;
                    }
                    
                    log(`  ✅ 匹配成功: "${mainTitle}" ← "${matchedKey}" (分数: ${maxScore.toFixed(1)})`);
                    
                    // 执行填充
                    try {
                        fillInput(input, matchedValue);
                        usedCardKeys.add(matchedKey);
                        fillCount++;
                        const valuePreview = String(matchedValue).substring(0, 30) + 
                                            (String(matchedValue).length > 30 ? '...' : '');
                        log(`  ✅ 填写成功: "${mainTitle}" = "${valuePreview}"`);
                        
                        results.push({
                            key: matchedKey,
                            value: matchedValue,
                            matched: mainTitle,
                            score: maxScore,
                            success: true
                        });
                    } catch (error) {
                        log(`  ❌ 填写失败: ${error.message}`);
                        results.push({
                            key: matchedKey,
                            value: matchedValue,
                            matched: mainTitle,
                            score: maxScore,
                            success: false,
                            error: error.message
                        });
                    }
                    
                    // 延迟，避免操作过快
                    await new Promise(resolve => setTimeout(resolve, 50));
                }
                
                // 汇总结果
                log('\\n═══════════════════════════════════════════════════════════════');
                log('📊 填写汇总:');
                log(`   成功填写: ${fillCount} 个字段`);
                
                const unusedFields = fillData.filter(item => !usedCardKeys.has(item.key));
                if (unusedFields.length > 0) {
                    log(`\\n⚠️  未使用的名片字段 (${unusedFields.length}个):`);
                    unusedFields.forEach(item => {
                        const valuePreview = String(item.value).substring(0, 20) + 
                                            (String(item.value).length > 20 ? '...' : '');
                        log(`   - "${item.key}" = "${valuePreview}..."`);
                    });
                } else {
                    log(`✅ 所有名片字段都已使用`);
                }
                
                log(`\\n✅ 表单填写完成: ${fillCount}/${allInputs.length} 个输入框`);
                log('═══════════════════════════════════════════════════════════════\\n');
                
                return {
                    fillCount,
                    totalCount: allInputs.length,
                    status: 'completed',
                    results
                };
            }
        };
    }
"""
    
    def generate_fill_script(self, field_data: Dict[str, str]) -> str:
        """
        生成填写腾讯文档表单的 JavaScript 脚本（使用共享匹配算法和执行逻辑）
        
        Args:
            field_data: 字段数据，格式 {字段名: 值}
        
        Returns:
            JavaScript 代码字符串
        """
        # 获取共享的匹配算法和执行逻辑
        shared_algorithm = self.get_shared_match_algorithm()
        shared_executor = self.get_shared_execution_logic()
        
        js_code = f"""
(async function() {{
    console.log('====== 🚀 开始填写腾讯文档表单（共享算法）======');
    
    // 存储结果
    window.__autoFillResult__ = {{
        status: 'waiting',
        message: '正在填写...',
        filled: [],
        failed: []
    }};
    
    const fieldData = {self._dict_to_js_object(field_data)};
    
{shared_algorithm}
    
{shared_executor}
    
    /**
     * 等待页面加载完成
     */
    async function waitForPageReady() {{
        console.log('⏳ 等待页面加载...');
        const maxAttempts = 10;
        let attempts = 0;
        
        while (attempts < maxAttempts) {{
            const questions = document.querySelectorAll('.question[data-qid]');
            if (questions.length > 0) {{
                console.log(`✅ 页面已加载，找到 ${{questions.length}} 个问题`);
                return true;
            }}
            await new Promise(resolve => setTimeout(resolve, 500));
            attempts++;
        }}
        
        console.error('❌ 页面加载超时');
        return false;
    }}
    
    /**
     * 获取问题标题
     */
    function getQuestionTitle(questionElement) {{
        const titleElement = questionElement.querySelector('.question-title .form-auto-ellipsis');
        if (!titleElement) return '';
        
        const titleText = (titleElement.textContent || titleElement.innerText || '').trim();
        console.log('  📝 问题标题:', titleText);
        return titleText;
    }}
    
    /**
     * 获取输入框
     */
    function getInputElement(questionElement) {{
        // 腾讯文档使用 textarea 作为输入框
        const textarea = questionElement.querySelector('textarea');
        if (textarea) {{
            console.log('  📋 找到输入框:', textarea.tagName, textarea.disabled ? '(禁用)' : '(启用)');
            return textarea;
        }}
        
        console.log('  ❌ 未找到输入框');
        return null;
    }}
    
    /**
     * 填写单个问题
     */
    async function fillQuestion(questionElement) {{
        try {{
            const title = getQuestionTitle(questionElement);
            if (!title) {{
                console.log('  ⚠️ 无法获取问题标题，跳过');
                return null;
            }}
            
            // 查找匹配的字段数据 - 使用评分系统
            let matchedKey = null;
            let matchedValue = null;
            let maxScore = 0;
            
            for (const [key, value] of Object.entries(fieldData)) {{
                const result = matchKeyword(title, key);
                if (result.matched && result.score > maxScore) {{
                    maxScore = result.score;
                    matchedKey = key;
                    matchedValue = value;
                }}
            }}
            
            if (!matchedKey) {{
                console.log(`  ⚠️ 未找到匹配的数据: "${{title}}" (最高分: ${{maxScore}})`);
                return null;
            }}
            
            console.log(`  ✅ 匹配成功: "${{title}}" ← "${{matchedKey}}" (分: ${{maxScore}})`);
            
            // 获取输入框
            const input = getInputElement(questionElement);
            if (!input) {{
                console.log(`  ❌ 问题 "${{title}}" 没有找到输入框`);
                return {{ field: title, status: 'failed', reason: '未找到输入框' }};
            }}
            
            // 移除 disabled 属性
            if (input.disabled) {{
                input.removeAttribute('disabled');
                input.disabled = false;
                console.log('  🔓 已启用输入框');
            }}
            
            // 移除 readonly 属性
            if (input.readOnly) {{
                input.removeAttribute('readonly');
                input.readOnly = false;
                console.log('  🔓 已移除只读属性');
            }}
            
            // 聚焦输入框
            input.focus();
            await new Promise(resolve => setTimeout(resolve, 50));
            
            // 设置值
            input.value = matchedValue;
            
            // 触发事件
            const events = ['input', 'change', 'blur'];
            events.forEach(eventType => {{
                const event = new Event(eventType, {{ bubbles: true, cancelable: true }});
                input.dispatchEvent(event);
            }});
            
            // 再次失焦
            input.blur();
            
            console.log(`  ✅ 填写成功: "${{title}}" = "${{matchedValue}}"`);
            return {{ field: title, status: 'success', value: matchedValue }};
            
        }} catch (error) {{
            console.error('  ❌ 填写失败:', error);
            return {{ field: title || 'unknown', status: 'failed', reason: error.message }};
        }}
    }}
    
    /**
     * 主填写流程
     */
    async function executeAutoFill() {{
        try {{
            // 等待页面加载
            const isReady = await waitForPageReady();
            if (!isReady) {{
                window.__autoFillResult__ = {{
                    status: 'failed',
                    message: '页面加载超时',
                    filled: [],
                    failed: []
                }};
                return;
            }}
            
            // 获取所有问题
            const questions = document.querySelectorAll('.question[data-qid]');
            console.log(`\\n📋 共找到 ${{questions.length}} 个问题`);
            console.log(`📊 待填写字段数: ${{Object.keys(fieldData).length}}`);
            console.log('');
            
            const results = [];
            
            // 遍历所有问题
            for (let i = 0; i < questions.length; i++) {{
                const question = questions[i];
                const qid = question.getAttribute('data-qid');
                const qtype = question.getAttribute('data-type');
                
                console.log(`\\n--- 问题 ${{i + 1}}/${{questions.length}} ---`);
                console.log(`  ID: ${{qid}}`);
                console.log(`  类型: ${{qtype}}`);
                
                const result = await fillQuestion(question);
                if (result) {{
                    results.push(result);
                }}
                
                // 延迟，避免操作过快
                await new Promise(resolve => setTimeout(resolve, 100));
            }}
            
            // 统计结果
            const filled = results.filter(r => r.status === 'success');
            const failed = results.filter(r => r.status === 'failed');
            
            console.log('\\n====== 📊 填写统计 ======');
            console.log(`✅ 成功: ${{filled.length}} 个`);
            console.log(`❌ 失败: ${{failed.length}} 个`);
            console.log('');
            
            if (filled.length > 0) {{
                console.log('成功填写的字段:');
                filled.forEach(f => {{
                    console.log(`  ✓ ${{f.field}} = ${{f.value}}`);
                }});
            }}
            
            if (failed.length > 0) {{
                console.log('\\n失败的字段:');
                failed.forEach(f => {{
                    console.log(`  ✗ ${{f.field}} - ${{f.reason || '未知原因'}}`);
                }});
            }}
            
            console.log('\\n====== 填写完成 ======');
            
            // 更新结果
            window.__autoFillResult__ = {{
                status: filled.length > 0 ? 'success' : 'failed',
                message: `成功填写 ${{filled.length}} 个字段，失败 ${{failed.length}} 个`,
                filled: filled,
                failed: failed,
                total: results.length
            }};
            
        }} catch (error) {{
            console.error('❌ 填写过程出错:', error);
            window.__autoFillResult__ = {{
                status: 'failed',
                message: error.message || '未知错误',
                filled: [],
                failed: []
            }};
        }}
    }}
    
    // 执行填写
    await executeAutoFill();
    
}})();
        """
        return js_code
    
    def generate_get_result_script(self) -> str:
        """生成获取填写结果的脚本"""
        return """
(function() {
    return window.__autoFillResult__ || {
        status: 'failed',
        message: '未找到填写结果',
        filled: [],
        failed: []
    };
})();
        """
    
    def _dict_to_js_object(self, data: Dict[str, str]) -> str:
        """将 Python 字典转换为 JavaScript 对象字符串"""
        import json
        return json.dumps(data, ensure_ascii=False)
    
    def generate_diagnostic_script(self) -> str:
        """生成腾讯文档表单诊断脚本"""
        js_code = """
(function() {
    console.log('====== 🔍 腾讯文档表单诊断 ======');
    
    const results = {
        title: document.title,
        url: window.location.href,
        platform: '腾讯文档',
        questions: []
    };
    
    // 查找所有问题
    const questions = document.querySelectorAll('.question[data-qid]');
    console.log(`\\n📋 共找到 ${questions.length} 个问题\\n`);
    
    questions.forEach((question, index) => {
        const qid = question.getAttribute('data-qid');
        const qtype = question.getAttribute('data-type');
        const titleElement = question.querySelector('.question-title .form-auto-ellipsis');
        const title = titleElement ? titleElement.textContent.trim() : '';
        const textarea = question.querySelector('textarea');
        const isRequired = question.querySelector('.required-span') !== null;
        
        console.log(`--- 问题 ${index + 1} ---`);
        console.log(`  ID: ${qid}`);
        console.log(`  类型: ${qtype}`);
        console.log(`  标题: ${title}`);
        console.log(`  必填: ${isRequired ? '是' : '否'}`);
        console.log(`  输入框: ${textarea ? 'textarea' : '无'}`);
        if (textarea) {
            console.log(`    - disabled: ${textarea.disabled}`);
            console.log(`    - readOnly: ${textarea.readOnly}`);
            console.log(`    - placeholder: ${textarea.placeholder || '无'}`);
            console.log(`    - value: ${textarea.value || '空'}`);
        }
        console.log('');
        
        results.questions.push({
            index: index + 1,
            qid: qid,
            qtype: qtype,
            title: title,
            required: isRequired,
            hasTextarea: !!textarea,
            disabled: textarea ? textarea.disabled : null,
            readOnly: textarea ? textarea.readOnly : null,
            placeholder: textarea ? textarea.placeholder : null,
            value: textarea ? textarea.value : null
        });
    });
    
    console.log('====== 诊断完成 ======');
    return results;
})();
        """
        return js_code

