const express = require('express');
const http = require('http');
const socketIo = require('socket.io');
const { chromium } = require('playwright');
const path = require('path');
const cors = require('cors');
const fs = require('fs');

class PlaywrightWebProxyServer {
    constructor() {
        this.app = express();
        this.server = http.createServer(this.app);
        this.io = socketIo(this.server, {
            cors: {
                origin: "*",
                methods: ["GET", "POST"]
            }
        });
        
        this.browser = null;
        this.page = null;
        this.clients = new Map();
        
        // 初始化日志文件
        this.logFile = path.join(__dirname, 'playwright-logs.txt');
        this.initLogFile();
        
        this.init();
    }

    initLogFile() {
        // 创建日志文件，如果不存在的话
        const logHeader = `=== Playwright Web Proxy 日志 ===\n启动时间: ${new Date().toLocaleString()}\n\n`;
        if (!fs.existsSync(this.logFile)) {
            fs.writeFileSync(this.logFile, logHeader);
        } else {
            fs.appendFileSync(this.logFile, `\n\n=== 新会话开始 ===\n启动时间: ${new Date().toLocaleString()}\n\n`);
        }
    }

    writeLog(message) {
        const timestamp = new Date().toLocaleString();
        const logMessage = `[${timestamp}] ${message}\n`;
        
        // 同时输出到控制台和文件
        console.log(message);
        fs.appendFileSync(this.logFile, logMessage);
    }

    async init() {
        this.setupExpress();
        this.setupSocketIO();
        await this.initBrowser();
        this.startServer();
    }

    setupExpress() {
        // 中间件
        this.app.use(cors());
        this.app.use(express.json());
        this.app.use(express.static(path.join(__dirname, 'public')));

        // 路由
        this.app.get('/', (req, res) => {
            res.sendFile(path.join(__dirname, 'public', 'index.html'));
        });

        this.app.get('/health', (req, res) => {
            res.json({ 
                status: 'ok', 
                browser: this.browser ? 'connected' : 'disconnected',
                clients: this.clients.size
            });
        });
    }

    setupSocketIO() {
        this.io.on('connection', (socket) => {
            this.writeLog(`客户端连接: ${socket.id}`);
            this.clients.set(socket.id, { socket, lastActivity: Date.now() });

            // 导航到新页面
            socket.on('navigate', async (data) => {
                try {
                    this.writeLog(`导航到: ${data.url}`);
                    await this.navigateToUrl(data.url);
                    const screenshot = await this.takeScreenshot();
                    socket.emit('navigation-complete', { url: data.url });
                    socket.emit('screenshot', { screenshot });
                } catch (error) {
                    console.error('导航错误:', error);
                    socket.emit('error', { message: error.message });
                }
            });

            // 刷新页面
            socket.on('refresh', async () => {
                try {
                    this.writeLog('刷新页面');
                    await this.page.reload();
                    const screenshot = await this.takeScreenshot();
                    socket.emit('screenshot', { screenshot });
                } catch (error) {
                    console.error('刷新错误:', error);
                    socket.emit('error', { message: error.message });
                }
            });

            // 后退
            socket.on('go-back', async () => {
                try {
                    await this.page.goBack();
                    const screenshot = await this.takeScreenshot();
                    socket.emit('screenshot', { screenshot });
                } catch (error) {
                    console.error('后退错误:', error);
                    socket.emit('error', { message: error.message });
                }
            });

            // 前进
            socket.on('go-forward', async () => {
                try {
                    await this.page.goForward();
                    const screenshot = await this.takeScreenshot();
                    socket.emit('screenshot', { screenshot });
                } catch (error) {
                    console.error('前进错误:', error);
                    socket.emit('error', { message: error.message });
                }
            });

            // 截图
            socket.on('screenshot', async () => {
                try {
                    const screenshot = await this.takeScreenshot();
                    socket.emit('screenshot', { screenshot });
                } catch (error) {
                    console.error('截图错误:', error);
                    socket.emit('error', { message: error.message });
                }
            });

            // 点击事件
            socket.on('click', async (data) => {
                try {
                    this.writeLog(`点击坐标: (${data.x}, ${data.y})`);
                    await this.page.mouse.click(data.x, data.y);
                    
                    // 等待页面可能的变化
                    await this.page.waitForTimeout(500);
                    
                    const screenshot = await this.takeScreenshot();
                    socket.emit('screenshot', { screenshot });
                } catch (error) {
                    console.error('点击错误:', error);
                    socket.emit('error', { message: error.message });
                }
            });

            // 滚动事件
            socket.on('scroll', async (data) => {
                try {
                    await this.page.evaluate((scrollData) => {
                        window.scrollTo(scrollData.x, scrollData.y);
                    }, data);
                } catch (error) {
                    console.error('滚动错误:', error);
                }
            });

            // 键盘事件
            socket.on('keydown', async (data) => {
                try {
                    this.writeLog(`按键: ${data.key}`);
                    
                    // 处理特殊按键
                    if (data.key.length === 1) {
                        // 普通字符
                        await this.page.keyboard.type(data.key);
                    } else {
                        // 特殊按键
                        const modifiers = [];
                        if (data.ctrlKey) modifiers.push('Control');
                        if (data.shiftKey) modifiers.push('Shift');
                        if (data.altKey) modifiers.push('Alt');
                        if (data.metaKey) modifiers.push('Meta');
                        
                        await this.page.keyboard.press(data.key, { modifiers });
                    }
                    
                    // 等待可能的页面变化
                    await this.page.waitForTimeout(300);
                    
                    const screenshot = await this.takeScreenshot();
                    socket.emit('screenshot', { screenshot });
                } catch (error) {
                    console.error('键盘事件错误:', error);
                    socket.emit('error', { message: error.message });
                }
            });

            // 客户端断开连接
            socket.on('disconnect', () => {
                this.writeLog(`客户端断开连接: ${socket.id}`);
                this.clients.delete(socket.id);
            });

            // 更新客户端活动时间
            socket.onAny(() => {
                const client = this.clients.get(socket.id);
                if (client) {
                    client.lastActivity = Date.now();
                }
            });
        });
    }

    async initBrowser() {
        try {
            this.writeLog('初始化 Playwright 浏览器...');
            this.browser = await chromium.launch({
                headless: true,
                args: [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu'
                ]
            });
            
            this.page = await this.browser.newPage();
            
            // 监听请求事件，记录 header 信息到文件
            this.page.on('request', request => {
                let logMessage = '\n=== 请求信息 ===';
                logMessage += `\nURL: ${request.url()}`;
                logMessage += `\n方法: ${request.method()}`;
                logMessage += '\n请求头:';
                const headers = request.headers();
                Object.keys(headers).forEach(key => {
                    logMessage += `\n  ${key}: ${headers[key]}`;
                });
                logMessage += '\n==================\n';
                this.writeLog(logMessage);
            });
            
            // 监听响应事件，记录响应信息到文件
            this.page.on('response', response => {
                let logMessage = '\n=== 响应信息 ===';
                logMessage += `\nURL: ${response.url()}`;
                logMessage += `\n状态码: ${response.status()}`;
                logMessage += `\n状态文本: ${response.statusText()}`;
                logMessage += '\n响应头:';
                const headers = response.headers();
                Object.keys(headers).forEach(key => {
                    logMessage += `\n  ${key}: ${headers[key]}`;
                });
                logMessage += '\n==================\n';
                this.writeLog(logMessage);
            });
            
            // 设置视口大小
            await this.page.setViewportSize({ width: 1280, height: 720 });
            
            // 设置用户代理
            await this.page.setExtraHTTPHeaders({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            });
            
            this.writeLog('浏览器初始化完成');
        } catch (error) {
            console.error('浏览器初始化失败:', error);
            throw error;
        }
    }

    async navigateToUrl(url) {
        if (!this.page) {
            throw new Error('浏览器未初始化');
        }
        
        try {
            await this.page.goto(url, { 
                waitUntil: 'networkidle',
                timeout: 30000 
            });
        } catch (error) {
            // 如果网络空闲等待失败，尝试等待加载完成
            await this.page.goto(url, { 
                waitUntil: 'load',
                timeout: 30000 
            });
        }
    }

    async takeScreenshot() {
        if (!this.page) {
            throw new Error('浏览器未初始化');
        }
        
        const screenshot = await this.page.screenshot({ 
            type: 'png',
            fullPage: true
        });
        
        return screenshot.toString('base64');
    }

    startServer() {
        const PORT = process.env.PORT || 3000;
        this.server.listen(PORT, () => {
            this.writeLog(`🚀 服务器运行在 http://localhost:${PORT}`);
            this.writeLog(`📱 打开浏览器访问上述地址开始使用`);
            this.writeLog(`📝 日志文件位置: ${this.logFile}`);
        });
    }

    async cleanup() {
        this.writeLog('清理资源...');
        if (this.browser) {
            await this.browser.close();
        }
        this.server.close();
        this.writeLog('服务器已关闭');
    }
}

// 创建服务器实例
const server = new PlaywrightWebProxyServer();

// 优雅关闭
process.on('SIGINT', async () => {
    console.log('\n收到 SIGINT 信号，正在关闭服务器...');
    await server.cleanup();
    process.exit(0);
});

process.on('SIGTERM', async () => {
    console.log('收到 SIGTERM 信号，正在关闭服务器...');
    await server.cleanup();
    process.exit(0);
});

// 未捕获的异常处理
process.on('uncaughtException', async (error) => {
    console.error('未捕获的异常:', error);
    await server.cleanup();
    process.exit(1);
});

process.on('unhandledRejection', async (reason, promise) => {
    console.error('未处理的 Promise 拒绝:', reason);
    await server.cleanup();
    process.exit(1);
});