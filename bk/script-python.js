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
        
        navigateBtn.addEventListener('click', () => this.navigate());
        urlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.navigate();
            }
        });

        // 控制按钮
        document.getElementById('refreshBtn').addEventListener('click', () => this.refresh());
        document.getElementById('backBtn').addEventListener('click', () => this.goBack());
        document.getElementById('forwardBtn').addEventListener('click', () => this.goForward());
        document.getElementById('screenshotBtn').addEventListener('click', () => this.takeScreenshot());

        // 页面交互
        const frame = document.getElementById('webFrame');
        frame.addEventListener('click', (e) => this.handleFrameClick(e));
        frame.addEventListener('scroll', (e) => this.handleFrameScroll(e));
        
        // 键盘事件
        document.addEventListener('keydown', (e) => {
            if (document.activeElement === document.getElementById('urlInput')) {
                return; // 如果焦点在 URL 输入框，不处理
            }
            this.handleKeyDown(e);
        });
    }

    navigate() {
        const url = document.getElementById('urlInput').value.trim();
        if (!url) {
            alert('请输入有效的 URL');
            return;
        }
        
        // 如果 URL 不包含协议，添加 https://
        const finalUrl = url.includes('://') ? url : `https://${url}`;
        
        this.showLoading();
        this.sendMessage('navigate', { url: finalUrl });
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
        e.preventDefault();
        
        if (!this.isConnected) {
            return;
        }
        
        const rect = e.target.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // 根据图片的实际尺寸和显示尺寸计算比例
        const img = e.target;
        const scaleX = img.naturalWidth / img.clientWidth;
        const scaleY = img.naturalHeight / img.clientHeight;
        
        const actualX = Math.round(x * scaleX);
        const actualY = Math.round(y * scaleY);
        
        this.showLoading();
        this.sendMessage('click', { x: actualX, y: actualY });
    }

    handleFrameScroll(e) {
        const scrollX = e.target.scrollLeft;
        const scrollY = e.target.scrollTop;
        
        this.sendMessage('scroll', { x: scrollX, y: scrollY });
    }

    handleKeyDown(e) {
        if (!this.isConnected) {
            return;
        }
        
        // 阻止某些默认行为
        if (e.key === 'F5' || (e.ctrlKey && e.key === 'r')) {
            e.preventDefault();
        }
        
        this.showLoading();
        this.sendMessage('keydown', {
            key: e.key,
            ctrlKey: e.ctrlKey,
            shiftKey: e.shiftKey,
            altKey: e.altKey,
            metaKey: e.metaKey
        });
    }

    displayScreenshot(screenshotBase64) {
        const img = document.getElementById('webFrame');
        img.src = `data:image/png;base64,${screenshotBase64}`;
    }

    showLoading() {
        document.getElementById('loading').style.display = 'block';
    }

    hideLoading() {
        document.getElementById('loading').style.display = 'none';
    }

    updateConnectionStatus() {
        const statusElement = document.getElementById('connectionStatus');
        if (this.isConnected) {
            statusElement.textContent = '已连接';
            statusElement.className = 'status connected';
            document.getElementById('controls').style.display = 'block';
        } else {
            statusElement.textContent = '未连接';
            statusElement.className = 'status disconnected';
            document.getElementById('controls').style.display = 'none';
        }
    }

    updateCurrentUrl() {
        document.getElementById('currentUrl').textContent = this.currentUrl;
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