class PlaywrightWebProxy {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.currentUrl = '';
        this.init();
    }

    init() {
        this.initSocket();
        this.bindEvents();
        this.updateUI();
    }

    initSocket() {
        // 连接到 Python 服务器的 WebSocket
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
            console.log('Connected to server');
            this.isConnected = true;
            this.updateConnectionStatus();
        };

        this.socket.onclose = () => {
            console.log('Disconnected from server');
            this.isConnected = false;
            this.updateConnectionStatus();
        };

        this.socket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.hideLoading();
            alert('连接错误，请刷新页面重试');
        };
    }

    handleMessage(message) {
        const { type, data } = message;
        
        switch (type) {
            case 'screenshot':
                this.displayScreenshot(data.screenshot);
                this.hideLoading();
                break;
            case 'navigation-complete':
                this.currentUrl = data.url;
                this.updateCurrentUrl();
                this.hideLoading();
                break;
            case 'error':
                console.error('Server error:', data);
                this.hideLoading();
                alert('发生错误: ' + data.message);
                break;
        }
    }

    sendMessage(type, data = {}) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({ type, data }));
        }
    }

    bindEvents() {
        // URL 导航
        const urlInput = document.getElementById('urlInput');
        const navigateBtn = document.getElementById('navigateBtn');
        const refreshBtn = document.getElementById('refreshBtn');
        
        navigateBtn.addEventListener('click', () => this.navigate());
        refreshBtn.addEventListener('click', () => this.refresh());
        
        urlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.navigate();
            }
        });

        // 浏览器控制
        const backBtn = document.getElementById('backBtn');
        const forwardBtn = document.getElementById('forwardBtn');
        const screenshotBtn = document.getElementById('screenshotBtn');
        
        backBtn.addEventListener('click', () => this.goBack());
        forwardBtn.addEventListener('click', () => this.goForward());
        screenshotBtn.addEventListener('click', () => this.takeScreenshot());

        // 浏览器框架交互
        const browserFrame = document.getElementById('browserFrame');
        browserFrame.addEventListener('click', (e) => this.handleFrameClick(e));
        browserFrame.addEventListener('scroll', (e) => this.handleFrameScroll(e));
        
        // 键盘事件
        document.addEventListener('keydown', (e) => this.handleKeyDown(e));
    }

    navigate() {
        const url = document.getElementById('urlInput').value.trim();
        if (!url) {
            alert('请输入有效的网址');
            return;
        }
        
        // 确保 URL 有协议
        let fullUrl = url;
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
            fullUrl = 'https://' + url;
        }
        
        this.showLoading();
        this.sendMessage('navigate', { url: fullUrl });
    }

    refresh() {
        if (!this.isConnected) {
            alert('未连接到服务器');
            return;
        }
        this.showLoading();
        this.sendMessage('refresh');
    }

    goBack() {
        this.sendMessage('go-back');
    }

    goForward() {
        this.sendMessage('go-forward');
    }

    takeScreenshot() {
        this.showLoading();
        this.sendMessage('screenshot');
    }

    handleFrameClick(e) {
        if (!this.isConnected || !this.currentUrl) return;
        
        const rect = e.currentTarget.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // 获取图片的实际尺寸和显示尺寸
        const img = e.currentTarget.querySelector('img');
        if (img) {
            const scaleX = img.naturalWidth / img.clientWidth;
            const scaleY = img.naturalHeight / img.clientHeight;
            
            const actualX = x * scaleX;
            const actualY = y * scaleY;
            
            this.sendMessage('click', { x: actualX, y: actualY });
        }
    }

    handleFrameScroll(e) {
        if (!this.isConnected || !this.currentUrl) return;
        
        const scrollTop = e.target.scrollTop;
        const scrollLeft = e.target.scrollLeft;
        
        this.sendMessage('scroll', { x: scrollLeft, y: scrollTop });
    }

    handleKeyDown(e) {
        if (!this.isConnected || !this.currentUrl) return;
        
        // 避免在输入框中触发
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }
        
        // 发送按键事件到服务端
        this.sendMessage('keydown', { 
            key: e.key, 
            code: e.code,
            ctrlKey: e.ctrlKey,
            shiftKey: e.shiftKey,
            altKey: e.altKey,
            metaKey: e.metaKey
        });
    }

    displayScreenshot(screenshotBase64) {
        const browserFrame = document.getElementById('browserFrame');
        browserFrame.innerHTML = `<img src="data:image/png;base64,${screenshotBase64}" alt="网页截图" />`;
    }

    showLoading() {
        document.getElementById('loadingOverlay').classList.add('show');
    }

    hideLoading() {
        document.getElementById('loadingOverlay').classList.remove('show');
    }

    updateConnectionStatus() {
        const statusElement = document.getElementById('connectionStatus');
        if (this.isConnected) {
            statusElement.textContent = '已连接';
            statusElement.className = 'status connected';
        } else {
            statusElement.textContent = '未连接';
            statusElement.className = 'status disconnected';
        }
    }

    updateCurrentUrl() {
        document.getElementById('currentUrl').textContent = this.currentUrl || '-';
        document.getElementById('urlInput').value = this.currentUrl || '';
    }

    updateUI() {
        this.updateConnectionStatus();
        this.updateCurrentUrl();
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new PlaywrightWebProxy();
});