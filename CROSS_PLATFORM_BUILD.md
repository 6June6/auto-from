# 🌍 跨平台打包指南

## ❌ 不可行的方法

在 macOS 上**无法直接**打包 Windows exe 文件，因为：

- PyInstaller 依赖目标平台的系统库
- Windows exe 需要 Windows 特定的二进制文件
- 即使使用交叉编译工具也无法完美支持 PyQt6

## ✅ 可行的解决方案

### 方案 1：GitHub Actions 自动化打包（最推荐）⭐⭐⭐⭐⭐

**优点：**

- ✅ 完全免费（GitHub 提供免费 CI/CD）
- ✅ 同时打包 macOS、Windows、Linux
- ✅ 自动化，无需手动操作
- ✅ 可以创建 Release 发布

**使用步骤：**

1. **推送代码到 GitHub**

```bash
cd /Users/chenchen/Desktop/开发项目/auto-form-filler-py
git init
git add .
git commit -m "初始提交"
git remote add origin https://github.com/your-username/auto-form-filler.git
git push -u origin main
```

2. **创建 Tag 触发打包**

```bash
git tag v1.0.0
git push origin v1.0.0
```

3. **等待自动打包完成**

- 访问 GitHub 仓库的 Actions 页面
- 等待约 10-15 分钟
- 在 Releases 页面下载打包好的文件

**或者手动触发：**

- 访问 GitHub 仓库
- 点击 Actions > 跨平台打包 > Run workflow

---

### 方案 2：Parallels Desktop / VMware（推荐）⭐⭐⭐⭐

在 macOS 上运行 Windows 虚拟机

**步骤：**

1. **安装虚拟机软件**

   - Parallels Desktop（商业，$99/年，最流畅）
   - VMware Fusion（免费，性能不错）
   - VirtualBox（免费，性能一般）

2. **安装 Windows 10/11**

   - 下载 Windows ISO
   - 创建虚拟机
   - 分配至少 4GB 内存、50GB 磁盘

3. **在 Windows 中打包**

```cmd
# 1. 复制项目到 Windows（通过共享文件夹）
# 2. 安装 Python 3.9+
# 3. 打开 PowerShell
cd C:\path\to\auto-form-filler-py
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller

# 4. 运行打包脚本
.\build_windows.bat

# 5. 复制 dist 文件夹到 macOS
```

---

### 方案 3：Boot Camp（适合有空间的用户）⭐⭐⭐

在 Mac 上安装双系统

**优点：**

- 原生 Windows 性能
- 完全免费

**缺点：**

- 需要重启切换系统
- 需要至少 64GB 空间
- Apple Silicon Mac 不支持

---

### 方案 4：云端 Windows 服务器 ⭐⭐⭐

**选项 A：使用现有的 Windows 电脑**

```bash
# 通过远程桌面连接
# macOS 自带 Microsoft Remote Desktop
# 连接到 Windows 电脑进行打包
```

**选项 B：租用云服务器**

- Azure / AWS / 腾讯云 Windows 服务器
- 按小时计费，打包完成后释放
- 成本约 ￥ 1-5 元/小时

---

### 方案 5：找 Windows 用户帮忙 ⭐⭐

1. 将项目打包发给 Windows 用户
2. 让他们运行 `build_windows.bat`
3. 返回 dist 文件夹

---

## 🚀 推荐流程

### 对于个人项目：

```
方案 1 (GitHub Actions)
  ↓ 如果不想用 GitHub
方案 2 (虚拟机)
  ↓ 如果没有虚拟机软件
方案 5 (找人帮忙)
```

### 对于团队项目：

```
方案 1 (GitHub Actions) - 必选
配合 方案 2 (虚拟机) - 用于本地测试
```

---

## 📝 GitHub Actions 详细说明

### 文件位置

已创建：`.github/workflows/build.yml`

### 触发方式

**方式 1：创建 Tag（推荐）**

```bash
git tag v1.0.0
git push origin v1.0.0
# 自动触发打包，并创建 Release
```

**方式 2：手动触发**

1. 访问 GitHub 仓库
2. 点击 "Actions" 标签
3. 选择 "跨平台打包"
4. 点击 "Run workflow"
5. 点击 "Run workflow" 按钮

### 下载打包文件

**如果使用 Tag 触发：**

- 访问仓库的 Releases 页面
- 下载对应平台的 zip 文件

**如果手动触发：**

- 访问 Actions 页面
- 点击对应的工作流运行
- 在 Artifacts 部分下载

---

## 🔧 本地测试 GitHub Actions

使用 [act](https://github.com/nektos/act) 在本地模拟 GitHub Actions：

```bash
# 安装 act
brew install act

# 本地运行工作流
cd /Users/chenchen/Desktop/开发项目/auto-form-filler-py
act workflow_dispatch

# 注意：act 只能测试流程，无法真正跨平台打包
```

---

## 📊 方案对比

| 方案           | 成本      | 难度   | 自动化 | 推荐度     |
| -------------- | --------- | ------ | ------ | ---------- |
| GitHub Actions | 免费      | ⭐     | ✅     | ⭐⭐⭐⭐⭐ |
| Parallels      | $99/年    | ⭐⭐   | ❌     | ⭐⭐⭐⭐   |
| VMware Fusion  | 免费      | ⭐⭐   | ❌     | ⭐⭐⭐⭐   |
| Boot Camp      | 免费      | ⭐⭐⭐ | ❌     | ⭐⭐⭐     |
| 云服务器       | ￥ 1-5/时 | ⭐⭐   | ❌     | ⭐⭐⭐     |
| 找人帮忙       | 免费      | ⭐     | ❌     | ⭐⭐       |

---

## 🎯 我的建议

### 对于您的情况：

**最佳方案：GitHub Actions**

1. **立即可用**

   ```bash
   cd /Users/chenchen/Desktop/开发项目/auto-form-filler-py

   # 如果还没有 git 仓库
   git init
   git add .
   git commit -m "添加 GitHub Actions 自动打包"

   # 创建 GitHub 仓库（在 GitHub 网站上）
   # 然后推送
   git remote add origin https://github.com/your-username/auto-form-filler.git
   git push -u origin main

   # 创建 tag 触发打包
   git tag v1.0.0
   git push origin v1.0.0

   # 10-15 分钟后在 Releases 下载
   ```

2. **长期方案**
   - 如果经常需要打包测试：购买 Parallels Desktop
   - 如果预算有限：使用免费的 VMware Fusion
   - 如果只是偶尔打包：继续使用 GitHub Actions

---

## ❓ 常见问题

### Q: 为什么不能用 Wine？

A: Wine 只能运行 Windows 程序，不能用来打包。PyInstaller 需要真实的 Windows 环境。

### Q: Docker 可以吗？

A: Docker for Mac 不支持 Windows 容器，无法使用。

### Q: 交叉编译工具呢？

A: 对于 C/C++ 项目可行，但 Python + PyQt6 太复杂，不支持交叉编译。

### Q: GitHub Actions 有次数限制吗？

A: 公开仓库无限制免费，私有仓库每月 2000 分钟免费（足够用）。

### Q: 打包的文件能在所有 Windows 上运行吗？

A: 可以，支持 Windows 7/8/10/11（32 位和 64 位），但建议在 Windows 10+ 上使用。

---

## 📞 需要帮助？

如果您选择了某个方案但遇到问题，请告诉我具体是哪个步骤，我会详细指导！




