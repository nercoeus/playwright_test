import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from playwright.async_api import async_playwright, Browser, Page
import uvicorn

cookies_global = ''

class PlaywrightWebProxyServer:
    def __init__(self):
        self.app = FastAPI()
        self.browser: Browser = None
        self.page: Page = None
        self.clients: Dict[str, WebSocket] = {}
        self.log_file = Path(__file__).parent / "playwright-logs.txt"
        
        self.init_log_file()
        self.setup_routes()
    
    def init_log_file(self):
        """初始化日志文件"""
        log_header = f"=== Playwright Web Proxy 日志 ===\n启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        if not self.log_file.exists():
            self.log_file.write_text(log_header, encoding='utf-8')
        else:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n\n=== 新会话开始 ===\n启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    def write_log(self, message: str):
        """写入日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {message}\n"
        
        print(message)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_message)
    
    def setup_routes(self):
        """设置路由"""
        # 静态文件
        self.app.mount("/static", StaticFiles(directory="public"), name="static")
        
        @self.app.get("/")
        async def read_root():
            return FileResponse("public/index.html")
        
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "ok",
                "browser": "connected" if self.browser else "disconnected",
                "clients": len(self.clients)
            }
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.handle_websocket(websocket)
    
    async def safe_send_message(self, websocket: WebSocket, message: dict):
        """安全发送WebSocket消息"""
        try:
            if websocket.client_state.name == 'CONNECTED':
                await websocket.send_text(json.dumps(message))
        except Exception as e:
            self.write_log(f"发送消息失败: {str(e)}")
    
    async def handle_websocket(self, websocket: WebSocket):
        """处理WebSocket连接"""
        await websocket.accept()
        client_id = id(websocket)
        self.clients[client_id] = websocket
        self.write_log(f"客户端连接: {client_id}")
        
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                await self.handle_message(websocket, message)
        except WebSocketDisconnect:
            self.write_log(f"客户端断开连接: {client_id}")
            if client_id in self.clients:
                del self.clients[client_id]
        except Exception as e:
            self.write_log(f"WebSocket错误: {str(e)}")
            if client_id in self.clients:
                del self.clients[client_id]
    
    async def handle_message(self, websocket: WebSocket, message: dict):
        """处理WebSocket消息"""
        msg_type = message.get('type')
        data = message.get('data', {})
        
        try:
            if msg_type == 'navigate':
                url = data.get('url')
                self.write_log(f"导航到: {url}")
                await self.navigate_to_url(url)
                screenshot = await self.take_screenshot()
                await self.safe_send_message(websocket, {
                    'type': 'navigation-complete',
                    'data': {'url': url}
                })
                await self.safe_send_message(websocket, {
                    'type': 'screenshot',
                    'data': {'screenshot': screenshot}
                })
            
            elif msg_type == 'refresh':
                self.write_log('刷新页面')
                await self.page.reload()
                screenshot = await self.take_screenshot()
                await self.safe_send_message(websocket, {
                    'type': 'screenshot',
                    'data': {'screenshot': screenshot}
                })
            
            elif msg_type == 'go-back':
                await self.page.go_back()
                screenshot = await self.take_screenshot()
                await self.safe_send_message(websocket, {
                    'type': 'screenshot',
                    'data': {'screenshot': screenshot}
                })
            
            elif msg_type == 'go-forward':
                await self.page.go_forward()
                screenshot = await self.take_screenshot()
                await self.safe_send_message(websocket, {
                    'type': 'screenshot',
                    'data': {'screenshot': screenshot}
                })
            
            elif msg_type == 'screenshot':
                screenshot = await self.take_screenshot()
                await self.safe_send_message(websocket, {
                    'type': 'screenshot',
                    'data': {'screenshot': screenshot}
                })
            
            elif msg_type == 'click':
                x, y = data.get('x', 0), data.get('y', 0)
                self.write_log(f"点击坐标: ({x}, {y})")
                await self.page.mouse.click(x, y)
                await self.page.wait_for_timeout(500)
                screenshot = await self.take_screenshot()
                await websocket.send_text(json.dumps({
                    'type': 'screenshot',
                    'data': {'screenshot': screenshot}
                }))
            
            elif msg_type == 'scroll':
                x, y = data.get('x', 0), data.get('y', 0)
                await self.page.evaluate(f"window.scrollTo({x}, {y})")
            
            elif msg_type == 'keydown':
                key = data.get('key', '')
                self.write_log(f"按键: {key} (长度: {len(key)})")
                
                modifiers = []
                if data.get('ctrlKey'): modifiers.append('Control')
                if data.get('shiftKey'): modifiers.append('Shift')
                if data.get('altKey'): modifiers.append('Alt')
                if data.get('metaKey'): modifiers.append('Meta')
                
                # 特殊字符处理：对于@等特殊字符，直接使用type方法
                if key == '@':
                    await self.page.keyboard.type('@')
                # 对于大写字母，直接使用type方法（浏览器已经处理了Shift）
                elif len(key) == 1 and key.isupper():
                    await self.page.keyboard.type(key)
                # 删除键特殊处理
                elif key in ['Backspace', 'Delete']:
                    self.write_log(f"处理删除键: {key}")
                    await self.page.keyboard.press(key)
                # 如果有修饰键，需要先按下修饰键，再按主键
                elif modifiers:
                    # 按下所有修饰键
                    for modifier in modifiers:
                        await self.page.keyboard.down(modifier)
                    
                    # 按下主键
                    await self.page.keyboard.press(key)
                    
                    # 释放所有修饰键
                    for modifier in reversed(modifiers):
                        await self.page.keyboard.up(modifier)
                # 特殊按键（如Enter、Tab等）
                elif len(key) > 1:
                    self.write_log(f"处理特殊按键: {key}")
                    await self.page.keyboard.press(key)
                else:
                    # 普通单字符输入使用type方法
                    await self.page.keyboard.type(key)
                
                await self.page.wait_for_timeout(300)
                screenshot = await self.take_screenshot()
                await websocket.send_text(json.dumps({
                    'type': 'screenshot',
                    'data': {'screenshot': screenshot}
                }))
        
        except Exception as e:
            await websocket.send_text(json.dumps({
                'type': 'error',
                'data': {'message': str(e)}
            }))
    
    async def init_browser(self):
        """初始化浏览器"""
        self.write_log('初始化 Playwright 浏览器...')
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu'
            ]
        )
        
        self.page = await self.browser.new_page()
        
        # 设置视口大小
        await self.page.set_viewport_size({"width": 1280, "height": 720})
        
        # 设置用户代理
        await self.page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # 监听请求和响应
        self.page.on('request', self.log_request)
        self.page.on('response', self.log_response)
        
        self.write_log('浏览器初始化完成')
    
    def log_request(self, request):
        """记录请求信息"""
        return
        log_message = f"\n=== 请求信息 ===\nURL: {request.url}\n方法: {request.method}\n请求头:\n"
        for key, value in request.headers.items():
            log_message += f"  {key}: {value}\n"
        log_message += "==================\n"
        self.write_log(log_message)
    
    async def log_response(self, response):
        """记录响应信息"""
        # log_message = f"\n=== 响应信息 ===\nURL: {response.url}\n状态码: {response.status}\n状态文本: {response.status_text}\n响应头:\n"
        # for key, value in response.headers.items():
        #     log_message += f"  {key}: {value}\n"
        log_message = f""
        # 打印浏览器上下文的storage_state
        if self.browser and hasattr(self, 'page') and self.page:
            try:
                context = self.page.context
                storage_state = await context.storage_state()
                if 'cookies' not in storage_state:
                    return
                cookies = storage_state['cookies']
                global cookies_global
                if cookies == cookies_global:
                    return
                cookies_global = cookies
                log_message += f"\n=== Storage Cookie ===\n{json.dumps(cookies, indent=2, ensure_ascii=False)}\n"
            except Exception as e:
                log_message += f"\n=== Storage Cookie Error ===\n{str(e)}\n"
        
        log_message += "==================\n"
        self.write_log(log_message)
    
    async def navigate_to_url(self, url: str):
        """导航到指定URL"""
        if not self.page:
            raise Exception('浏览器未初始化')
        
        try:
            await self.page.goto(url, wait_until='networkidle', timeout=30000)
        except:
            await self.page.goto(url, wait_until='load', timeout=30000)
    
    async def take_screenshot(self) -> str:
        """截图"""
        if not self.page:
            raise Exception('浏览器未初始化')
        
        screenshot = await self.page.screenshot(type='png', full_page=True)
        import base64
        return base64.b64encode(screenshot).decode('utf-8')
    
    async def cleanup(self):
        """清理资源"""
        self.write_log('清理资源...')
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
        self.write_log('服务器已关闭')

# 创建服务器实例
server = PlaywrightWebProxyServer()

@server.app.on_event("startup")
async def startup_event():
    await server.init_browser()
    server.write_log('🚀 服务器运行在 http://localhost:9098')
    server.write_log('📱 打开浏览器访问上述地址开始使用')
    server.write_log(f'📝 日志文件位置: {server.log_file}')

@server.app.on_event("shutdown")
async def shutdown_event():
    await server.cleanup()

if __name__ == "__main__":
    uvicorn.run(server.app, host="0.0.0.0", port=9098)