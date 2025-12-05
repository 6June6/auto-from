"""
页面诊断工具 - 用于分析表单结构
"""

class PageDiagnostic:
    """页面诊断类"""
    
    @staticmethod
    def generate_diagnostic_script() -> str:
        """生成诊断脚本 - 分析页面结构"""
        return """
(function() {
    console.log('====== 🔍 页面诊断开始 ======');
    
    // 1. 检查页面基本信息
    console.log('\\n📄 页面信息:');
    console.log('  标题:', document.title);
    console.log('  URL:', window.location.href);
    console.log('  就绪状态:', document.readyState);
    
    // 2. 检查所有输入元素
    console.log('\\n📝 输入元素统计:');
    const allInputs = document.querySelectorAll('input');
    const allTextareas = document.querySelectorAll('textarea');
    const allSelects = document.querySelectorAll('select');
    console.log('  input元素:', allInputs.length, '个');
    console.log('  textarea元素:', allTextareas.length, '个');
    console.log('  select元素:', allSelects.length, '个');
    
    // 3. 详细分析每个input
    console.log('\\n🔎 详细分析 input 元素:');
    allInputs.forEach((input, index) => {
        console.log(`\\n  Input ${index + 1}:`);
        console.log('    类型:', input.type || '无');
        console.log('    name:', input.name || '无');
        console.log('    id:', input.id || '无');
        console.log('    placeholder:', input.placeholder || '无');
        console.log('    class:', input.className || '无');
        console.log('    value:', input.value || '空');
        console.log('    可见:', input.offsetParent !== null);
        
        // 尝试找label
        let labelText = '';
        if (input.labels && input.labels.length > 0) {
            labelText = input.labels[0].textContent;
        } else if (input.id) {
            const label = document.querySelector(`label[for="${input.id}"]`);
            if (label) labelText = label.textContent;
        }
        if (!labelText) {
            const parent = input.parentElement;
            if (parent) {
                const label = parent.querySelector('label');
                if (label) labelText = label.textContent;
            }
        }
        console.log('    关联Label:', labelText.trim() || '无');
    });
    
    // 4. 详细分析textarea
    if (allTextareas.length > 0) {
        console.log('\\n📝 详细分析 textarea 元素:');
        allTextareas.forEach((textarea, index) => {
            console.log(`\\n  Textarea ${index + 1}:`);
            console.log('    name:', textarea.name || '无');
            console.log('    id:', textarea.id || '无');
            console.log('    placeholder:', textarea.placeholder || '无');
            console.log('    可见:', textarea.offsetParent !== null);
        });
    }
    
    // 5. 检查iframe
    const iframes = document.querySelectorAll('iframe');
    console.log('\\n🖼️  iframe 数量:', iframes.length);
    iframes.forEach((iframe, index) => {
        console.log(`  iframe ${index + 1}:`, iframe.src || '无src');
    });
    
    // 6. 检查form
    const forms = document.querySelectorAll('form');
    console.log('\\n📋 表单数量:', forms.length);
    forms.forEach((form, index) => {
        console.log(`  form ${index + 1}:`);
        console.log('    action:', form.action || '无');
        console.log('    method:', form.method || '无');
        console.log('    内部input:', form.querySelectorAll('input').length);
    });
    
    // 7. 检查常见的表单容器
    console.log('\\n📦 表单容器:');
    const commonContainers = [
        '.form', '.form-group', '.form-item', '.input-group',
        '[class*="form"]', '[class*="input"]', '[class*="field"]'
    ];
    commonContainers.forEach(selector => {
        try {
            const elements = document.querySelectorAll(selector);
            if (elements.length > 0) {
                console.log(`  ${selector}:`, elements.length, '个');
            }
        } catch(e) {}
    });
    
    console.log('\\n====== ✅ 页面诊断完成 ======\\n');
    
    return {
        inputs: allInputs.length,
        textareas: allTextareas.length,
        selects: allSelects.length,
        iframes: iframes.length,
        forms: forms.length,
        readyState: document.readyState
    };
})();
"""

