"""
腾讯文档表单填写引擎
专门针对腾讯文档（docs.qq.com）表单的自动填写
"""
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


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
    
    def generate_fill_script(self, field_data: Dict[str, str]) -> str:
        """
        生成填写腾讯文档表单的 JavaScript 脚本
        
        Args:
            field_data: 字段数据，格式 {字段名: 值}
        
        Returns:
            JavaScript 代码字符串
        """
        # 获取共享的匹配算法
        shared_algorithm = self.get_shared_match_algorithm()
        
        js_code = f"""
(async function() {{
    console.log('====== 🚀 开始填写腾讯文档表单 ======');
    
    // 存储结果
    window.__autoFillResult__ = {{
        status: 'waiting',
        message: '正在填写...',
        filled: [],
        failed: []
    }};
    
    const fieldData = {self._dict_to_js_object(field_data)};
    
{shared_algorithm}
    
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

