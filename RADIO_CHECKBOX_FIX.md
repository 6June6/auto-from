# Radio/Checkbox 表单字段优化说明

## 📋 问题描述

在 WPS 表单填充时，单选按钮组（radio buttons）和复选框组（checkboxes）被错误地识别为**多个独立字段**，导致：

### 问题1：字段重复识别 ❌

```
表单#7: "合作形式" [图文]  ← radio 选项1
表单#8: "合作形式" [视频]  ← radio 选项2（重复！）
```

### 问题2：选项文本干扰匹配 ❌

```
输入框#7 标识符: [合作形式 | 图文]   ← "图文"是选项，不是字段名
输入框#8 标识符: [合作形式 | 视频]   ← "视频"是选项，不是字段名
```

导致匹配算法被选项文本（"图文"、"视频"）误导，匹配到错误的名片数据。

---

## 🔧 解决方案

### 修改1：`getAllInputs()` - Radio/Checkbox 组去重

```javascript
function getAllInputs() {
  const inputs = [];
  const radioGroups = new Map(); // 记录已处理的 radio/checkbox 组

  document.querySelectorAll("input, textarea").forEach((input) => {
    // 跳过隐藏元素
    if (style.display === "none" || style.visibility === "hidden") {
      return;
    }

    // 【核心】radio/checkbox 去重：同一个 name 的组只保留第一个
    if (input.type === "radio" || input.type === "checkbox") {
      const name = input.name;
      if (name) {
        if (radioGroups.has(name)) {
          console.log(`[WPS] 跳过重复的 ${input.type} 组成员: name="${name}"`);
          return; // 跳过
        }
        radioGroups.set(name, input);
        console.log(`[WPS] 保留 ${input.type} 组代表: name="${name}"`);
      }
    }

    inputs.push(input);
  });

  return inputs;
}
```

**效果**：

- ✅ "合作形式"的两个选项（图文/视频）只保留第一个
- ✅ 每个 radio/checkbox 组只会被识别为 1 个字段

---

### 修改2：`getInputIdentifiers()` - 过滤选项文本

```javascript
function getInputIdentifiers(input, inputIndex) {
  // 【新增】检测输入框类型
  const isRadioOrCheckbox = input.type === "radio" || input.type === "checkbox";
  if (isRadioOrCheckbox) {
    console.log(`[WPS] 检测到 ${input.type} 类型，只提取问题标题`);
  }

  // 【方法1】只提取问题容器的标题（优先级最高）
  // WPS 表单的标题在 .ksapc-question-title-title
  // ✅ 对所有类型都提取

  // 【方法3-6】跳过这些方法（避免提取选项文本）
  if (!isRadioOrCheckbox) {
    // aria-labelledby
    // Label 标签
    // placeholder
    // 前置兄弟元素
  }
}
```

**效果**：

- ✅ Radio/Checkbox 只提取问题标题："合作形式"
- ✅ 不提取选项文本："图文"、"视频"
- ✅ 不提取 label、placeholder 等可能包含选项信息的属性

---

### 修改3：过滤通用 Placeholder

```javascript
// 过滤通用的 placeholder
const genericPlaceholders = [
  "请输入",
  "请填写",
  "请选择",
  "输入",
  "填写",
  "选择",
  "图文",
  "视频",
  "文本",
  "数字",
  "日期",
  "时间",
];

const isGeneric = genericPlaceholders.some(
  (g) => ph === g || (ph.includes("请") && ph.length <= 4),
);

if (!isGeneric && ph.length > 2) {
  addIdentifier(ph, 50); // 降低优先级从70→50
} else {
  console.log(`[WPS] 跳过通用placeholder: "${ph}"`);
}
```

**效果**：

- ✅ "图文"、"视频"等通用词被过滤
- ✅ Placeholder 优先级降低（70 → 50）

---

## 📊 效果对比

### 修改前 ❌

```javascript
原始查询: 18 个输入框
处理后: 18 个输入框

输入框列表：
  #7: "合作形式" [图文]
  #8: "合作形式" [视频]     ← 重复！
  #9: "后台图文价格"
  #10: "后台视频价格"

匹配结果：
  表单#7"合作形式" ← 名片"视频还是图文、合作方式..." (分数:100.0)
  表单#8"合作形式" ← 名片"报备视频价格、视频..." (分数:100.0) ← 错误匹配！
  表单#10"后台视频价格" ← 未匹配 ❌
```

### 修改后 ✅

```javascript
原始查询: 18 个输入框
去重后: 16 个输入框  ← 减少2个

输入框列表：
  #7: "合作形式"           ← 只保留一个，无选项文本
  #8: "后台图文价格"       ← 编号前移
  #9: "后台视频价格"       ← 编号前移

匹配结果：
  表单#7"合作形式" ← 名片"视频还是图文、合作方式..." (分数:100.0) ✅
  表单#9"后台视频价格" ← 名片"报备视频价格、后台视频价格..." (分数:100.0) ✅
```

---

## 🎯 适用场景

此优化适用于所有包含以下元素的表单：

### 1. 单选按钮组（Radio Buttons）

```html
<input type="radio" name="合作形式" value="图文" />
<input type="radio" name="合作形式" value="视频" />
```

### 2. 复选框组（Checkboxes）

```html
<input type="checkbox" name="权益" value="授权" />
<input type="checkbox" name="权益" value="保价" />
```

### 3. WPS 表单特有结构

```html
<div class="ksapc-questions-write-container">
  <pre class="ksapc-question-title-title">合作形式</pre>
  <div class="ksapc-select-write">
    <label><input type="radio" />图文</label>
    <label><input type="radio" />视频</label>
  </div>
</div>
```

---

## 🔄 验证步骤

1. **重新加载应用**
2. **填充 WPS 表单**
3. **查看控制台日志**：

应该看到：

```
[WPS] 保留 radio 组代表: name="合作形式"
[WPS] 跳过重复的 radio 组成员: name="合作形式"
[WPS] 检测到 radio 类型，只提取问题标题
[WPS] 跳过通用placeholder: "图文"
[WPS] 跳过通用placeholder: "视频"
[WPS] ✅ 去重后共 16 个输入框（原始查询: 18 个）

输入框 #7: "合作形式" []  ← 无选项文本
```

---

## ✅ 总结

通过这两个优化：

1. **去重**：同名 radio/checkbox 组只保留一个代表
2. **过滤**：radio/checkbox 不提取选项文本和 placeholder

成功解决了：

- ✅ 字段重复识别问题
- ✅ 选项文本干扰匹配问题
- ✅ "后台视频价格"无法匹配的问题

**代码更精准，匹配更准确！** 🎉
