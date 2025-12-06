# 官网部署指南

这是一个为 `Auto Form Filler` 项目生成的静态官网，设计风格现代、高大上（High-end），使用了 Tailwind CSS 和 AOS 动画库。

## 📂 目录结构

```
website/
├── index.html        # 主页文件
├── assets/           # (需手动创建) 存放图片资源
│   ├── screenshot-main.png       # 主界面截图
│   └── screenshot-platforms.png  # 多平台展示图
└── README.md         # 本说明文件
```

## 🚀 如何使用

1.  **创建资源目录**:
    在 `website` 目录下创建一个名为 `assets` 的文件夹。

2.  **添加图片**:
    请截图你的软件界面，并保存为以下文件名放入 `assets` 文件夹中（或者修改 `index.html` 中的图片路径）：
    *   `screenshot-main.png` (建议尺寸: 1920x1080 或 1200x675) - 用于首屏展示
    *   `screenshot-platforms.png` (建议尺寸: 800x600) - 用于多平台介绍部分

3.  **配置下载链接**:
    打开 `index.html`，搜索 "下载安装包"，找到对应的 `<a href="#">` 标签，将 `#` 替换为实际的文件下载地址（例如 GitHub Release 链接或云存储链接）。

    *   macOS Apple Silicon 链接
    *   macOS Intel 链接
    *   Windows 链接

4.  **本地预览**:
    直接双击打开 `index.html` 即可在浏览器中查看效果。

5.  **部署**:
    你可以将整个 `website` 文件夹的内容上传 to GitHub Pages, Vercel, Netlify 或任何静态网页服务器。

## 🎨 技术栈

*   **HTML5**: 语义化标签
*   **Tailwind CSS (CDN)**: 无需编译，直接引入的原子化 CSS 框架
*   **FontAwesome (CDN)**: 图标库
*   **AOS (CDN)**: 滚动动画库
*   **Google Fonts**: Inter 和 Noto Sans SC 字体

无需安装 `node_modules` 或运行构建命令，这是一个纯静态页面，随处可用。

