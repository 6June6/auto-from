# 匹配算法重构说明

## 📋 重构目标

将 WPS 表单的匹配算法统一为使用腾讯文档的简洁匹配算法，避免代码重复，方便维护。

## 🎯 遵循原则

- **DRY 原则**（Don't Repeat Yourself）：避免代码重复
- **KISS 原则**（Keep It Simple, Stupid）：保持算法简洁
- **单一职责原则**：匹配算法独立管理，易于维护

## 📊 重构内容

### 1. **创建共享匹配算法模块**

在 `core/tencent_docs_filler.py` 中添加静态方法 `get_shared_match_algorithm()`：

```python
@staticmethod
def get_shared_match_algorithm() -> str:
    """获取共享的匹配算法 JavaScript 代码"""
    return """
    // 清理文本
    function cleanText(text) { ... }

    // 分割关键词
    function splitKeywords(keyword) { ... }

    // 匹配关键词（评分系统）
    function matchKeyword(titleOrIdentifiers, keyword) { ... }
    """
```

**算法特点**：

- ✅ 支持多关键词匹配（用 `|,;，；、` 分隔）
- ✅ 评分系统：完全匹配100分、包含匹配80-90分、字符相似度30-60分
- ✅ 阈值：50分以上才匹配
- ✅ 简洁清晰，易于维护

### 2. **腾讯文档使用共享算法**

修改 `TencentDocsFiller.generate_fill_script()` 方法：

```python
def generate_fill_script(self, field_data: Dict[str, str]) -> str:
    # 获取共享的匹配算法
    shared_algorithm = self.get_shared_match_algorithm()

    js_code = f"""
    (async function() {{
        const fieldData = {self._dict_to_js_object(field_data)};

        {shared_algorithm}  // 插入共享算法

        // ... 其他腾讯文档特定代码
    }})();
    """
```

### 3. **WPS 表单使用共享算法**

修改 `gui/new_fill_window.py` 中的 `generate_kdocs_fill_script()` 方法：

```python
def generate_kdocs_fill_script(self, fill_data: list) -> str:
    """生成WPS表单专用的填充脚本 - 使用腾讯文档的共享匹配算法"""
    from core.tencent_docs_filler import TencentDocsFiller

    # 获取共享的匹配算法
    shared_algorithm = TencentDocsFiller.get_shared_match_algorithm()

    js_code = f"""
    (function() {{
        const fillData = {fill_data_json};

        // 共享匹配算法
        {shared_algorithm}

        // ... WPS 特定的表单解析和填充代码
    }})();
    """
```

**删除的 WPS 重复代码**：

- ❌ `cleanText()` - 已由共享算法提供
- ❌ `splitKeywords()` - 已由共享算法提供
- ❌ `matchKeyword()` - 已由共享算法提供
- ❌ `cleanTextNoPrefix()` - 不再需要
- ❌ `extractCoreIdentifier()` - 不再需要
- ❌ `extractCoreWords()` - 不再需要
- ❌ `hasNegationConflict()` - 不再需要
- ❌ `hasKeyConflictWithForm()` - 不再需要
- ❌ `areFieldsIncompatible()` - 不再需要
- ❌ `longestCommonSubstring()` - 不再需要
- ❌ `isPlaceholderIdentifier()` - 不再需要

## 📈 重构优势

### 代码质量提升

- **代码行数减少**：WPS 匹配相关代码从 ~250行 减少到 ~50行
- **逻辑清晰**：匹配算法集中在一个地方，易于理解
- **可维护性强**：只需要维护一份匹配算法代码

### 一致性保证

- **行为统一**：腾讯文档和 WPS 使用完全相同的匹配逻辑
- **测试简化**：只需测试一个匹配算法
- **bug修复容易**：修复一处，所有平台受益

### 扩展性好

- **易于添加新平台**：新的表单平台可以直接复用匹配算法
- **参数化配置**：可以轻松调整阈值等参数

## 🔄 迁移路径

如果将来需要为不同平台定制匹配算法，可以：

1. 添加参数化配置：

```python
@staticmethod
def get_shared_match_algorithm(threshold=50, scoring_config=None) -> str:
    # 根据参数生成不同的匹配算法
```

2. 创建算法变体：

```python
@staticmethod
def get_strict_match_algorithm() -> str:
    # 更严格的匹配（阈值更高）

@staticmethod
def get_fuzzy_match_algorithm() -> str:
    # 更模糊的匹配（阈值更低）
```

## 📝 使用示例

### 腾讯文档填充

```python
filler = TencentDocsFiller()
script = filler.generate_fill_script({"姓名": "张三", "电话": "13800138000"})
# 自动使用共享匹配算法
```

### WPS 表单填充

```python
script = self.generate_kdocs_fill_script([
    {"key": "姓名", "value": "张三"},
    {"key": "电话", "value": "13800138000"}
])
# 自动使用与腾讯文档相同的共享匹配算法
```

## ✅ 验证清单

- [x] 腾讯文档填充正常工作
- [x] WPS 表单填充正常工作
- [x] 匹配算法代码只在一处定义
- [x] 无 linter 错误
- [x] 代码符合 DRY、KISS、SOLID 原则

## 🎉 总结

通过这次重构，我们成功地：

1. ✅ 消除了代码重复（DRY原则）
2. ✅ 简化了匹配算法（KISS原则）
3. ✅ 提高了代码可维护性
4. ✅ 保证了不同平台的一致性
5. ✅ 为未来扩展留下了空间

**代码更简洁，维护更容易！** 🚀
