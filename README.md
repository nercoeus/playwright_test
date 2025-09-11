# Playwright Web Proxy

一个使用 Playwright 托管网页的系统，提供前端界面来展示和操作服务端托管的网页内容。

## 功能特性

- 🌐 使用 Playwright 在服务端托管任意网页
- 🖥️ 前端提供实时网页展示窗口
- 🖱️ 支持鼠标点击、滚动等交互操作
- ⌨️ 支持键盘输入操作
- 🔄 实时同步网页状态变化
- 📱 响应式设计，适配不同屏幕尺寸

## 安装和运行

1. 安装依赖：
```bash
npm install
```

2. 安装 Playwright 浏览器：
```bash
npm run install-browsers
```

3. 启动服务器：
```bash
npm start
```

4. 打开浏览器访问：`http://localhost:3000`

## 技术架构

- **后端**: Node.js + Express + Playwright
- **前端**: HTML + CSS + JavaScript
- **通信**: WebSocket (Socket.IO)
- **浏览器自动化**: Playwright

## 使用说明

1. 在前端界面输入要访问的网址
2. 系统会在服务端使用 Playwright 打开该网页
3. 前端实时显示网页内容
4. 可以通过前端界面进行点击、输入等操作
5. 所有操作会同步到服务端的实际网页中