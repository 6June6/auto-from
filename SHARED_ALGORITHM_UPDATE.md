# 共享算法升级文档

## 📅 更新时间

2026-01-30

## 🎯 目标

实现 WPS 和腾讯文档使用完全相同的匹配算法和执行逻辑，方便维护。

## ✅ 已完成的改动

### 1. 共享匹配算法（已有）

**位置**: `core/tencent_docs_filler.py::get_shared_match_algorithm()`

- ✅ `cleanText()` - 文本清理
- ✅ `splitKeywords()` - 关键词分割
- ✅ `matchKeyword()` - 匹配评分系统（完全匹配 100 分、包含 80-90 分、相似度 30-60 分）

### 2. 共享执行逻辑（新增）

**位置**: `core/tencent_docs_filler.py::get_shared_execution_logic()`

- ✅ `createSharedExecutor(config)` - 创建执行器

  - 配置参数：
    - `fillData`: 名片数据数组
    - `allInputs`: 所有输入框数组
    - `getIdentifiers`: 获取输入框标识符的函数
    - `fillInput`: 填充函数
    - `onProgress`: 进度回调

- ✅ **执行逻辑**（腾讯文档算法）：
  1. 扫描页面输入框
  2. 逐个遍历输入框
  3. 对每个输入框独立查找最高分的名片数据
  4. **名片数据可以被多次使用**（不会被"消耗"）
  5. 只接受分数>=50 的匹配
  6. 执行填充

### 3. WPS 表单填充脚本

**位置**: `gui/new_fill_window.py::generate_kdocs_fill_script()`

**改动**：

```python
# 之前
shared_algorithm = TencentDocsFiller.get_shared_match_algorithm()

# 现在
shared_algorithm = TencentDocsFiller.get_shared_match_algorithm()
shared_executor = TencentDocsFiller.get_shared_execution_logic()  # 新增
```

**JavaScript 改动**：

```javascript
// 之前：自己实现执行逻辑（全局贪心分配，名片数据会被消耗）
async function executeAutoFill() {
  // 第一阶段：扫描
  // 第二阶段：计算全局匹配矩阵
  // 第三阶段：贪心分配（名片数据被消耗）
  // 第四阶段：执行填充
}

// 现在：调用共享执行器
async function executeAutoFill() {
  const hasInputs = await waitForInputs();
  if (!hasInputs) return;

  const allInputs = getAllInputs();

  // 使用共享执行器
  const executor = createSharedExecutor({
    fillData: fillData,
    allInputs: allInputs,
    getIdentifiers: getInputIdentifiers,
    fillInput: fillInput,
    onProgress: (msg) => console.log(msg),
  });

  const result = await executor.execute();
  window.__autoFillResult__ = result;
}
```

### 4. Radio/Checkbox 优化（额外修复）

**位置**: `gui/new_fill_window.py`

**问题**：WPS 的 radio/checkbox 可能没有 `name` 属性，导致去重失败

**解决方案**：

```javascript
// 使用多种方式识别同一组
function getAllInputs() {
  // 方式1：使用 name 属性
  // 方式2：使用容器 ID/className
  // 方式3：使用问题标题
  if (radioGroups.has(groupKey)) {
    return; // 跳过重复
  }
}
```

**过滤选项文本**：

```javascript
// 移除 "图文"、"视频"、"是"、"否"、"50%"  等选项文本
const optionTexts = ['图文', '视频', '是', '否', ...];
identifiers = identifiers.filter(item => {
    if (text.length > 6) return true;
    if (optionTexts.includes(text)) return false;
    if (/^\d+%?$/.test(text)) return false;  // 移除纯数字
    return true;
});
```

## 🔄 腾讯文档状态

**保持原样**，因为：

1. 腾讯文档的执行逻辑已经很好
2. DOM 结构与 WPS 差异大（使用 `.question[data-qid]` 而不是 `input, textarea`）
3. 匹配算法已经统一（核心需求已满足）

## 📊 效果对比

### 之前（WPS 贪心算法）

```
❌ 表单#14 "分发平台ID" 匹配 "ID、平台ID..." (分数: 90)
   ↓ 名片被消耗
❌ 表单#2 "博主ID" 找不到匹配

❌ 表单#8 "合作形式[视频]" 匹配 "视频、后台视频价格..." (分数: 100)
   ↓ 名片被消耗
❌ 表单#10 "后台视频价格" 找不到匹配
```

### 现在（腾讯文档算法）

```
✅ 输入框#2 "博主ID" 独立查找
   → 找到 "ID、平台ID、博主ID..." (分数: 100) ✅

✅ 输入框#14 "分发平台ID" 独立查找
   → 也可以找到 "ID、平台ID..." (分数: 90) ✅

✅ 输入框#8 "合作形式" 独立查找
   → 找到 "合作形式、合作方式..." (分数: 100) ✅

✅ 输入框#10 "后台视频价格" 独立查找
   → 找到 "后台视频价格、视频价格..." (分数: 100) ✅
```

## 🎯 核心优势

1. **代码复用**：匹配算法和执行逻辑统一管理
2. **易于维护**：修改一处，多个平台生效
3. **逻辑一致**：WPS 和腾讯文档行为完全相同
4. **更好的匹配**：名片数据可以被多次使用，不会因为被"消耗"而导致匹配失败

## 📝 使用方法

### 添加新的表单平台

```python
# 1. 在填充脚本中导入
from core.tencent_docs_filler import TencentDocsFiller

# 2. 获取共享算法和执行器
shared_algorithm = TencentDocsFiller.get_shared_match_algorithm()
shared_executor = TencentDocsFiller.get_shared_execution_logic()

# 3. 注入到 JavaScript
js_code = f"""
{shared_algorithm}
{shared_executor}

// 4. 调用执行器
const executor = createSharedExecutor({{
    fillData: [...],           // 名片数据
    allInputs: [...],          // 输入框
    getIdentifiers: (input) => [...],  // 提取标识符
    fillInput: (input, value) => {{}},  // 填充逻辑
    onProgress: console.log    // 日志输出
}});

await executor.execute();
"""
```

## 🔧 测试建议

1. 重新运行 WPS 表单填充，验证匹配效果
2. 检查日志是否显示"腾讯文档算法"
3. 验证 "博主 ID"、"后台视频价格" 等字段是否正确匹配
4. 确认 radio/checkbox 去重是否生效

## 📌 注意事项

- 共享执行器返回的结果格式统一：
  ```javascript
  {
      fillCount: number,
      totalCount: number,
      status: 'completed',
      results: [...]
  }
  ```
- 每个平台需要提供自己的 `getIdentifiers` 和 `fillInput` 适配函数
- 延迟参数 (50ms) 在共享执行器中固定，可以根据需要调整
