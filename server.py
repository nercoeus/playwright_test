import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from playwright.async_api import async_playwright, Browser, Page
import uvicorn

# 导入脚本模块
sys.path.append('/Users/bytedance/Desktop/demo/bk')
from final_complete_script import complete_tiktok_shop_rating_filter
from tiktok_script_integrated import complete_tiktok_shop_rating_filter_integrated
from util import low_quality

cookies_global = ''

class PlaywrightWebProxyServer:
    def __init__(self):
        self.app = FastAPI()
        self.browser: Browser = None
        self.page: Page = None
        self.clients: Dict[str, WebSocket] = {}
        self.log_file = Path(__file__).parent / "playwright-logs.txt"
        self.script_running = False
        self.script_task = None
        
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
            if msg_type == 'start-script':
                await self.start_tiktok_script(websocket)
            
            elif msg_type == 'navigate':
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
            
            elif msg_type == 'clear-cookies':
                await self.clear_cookies(websocket)
            
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
            headless=True,  # 改回无头模式，在托管界面中显示
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
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
        """截图（智能完整截图版本）"""
        if not self.page:
            raise Exception('浏览器未初始化')
        
        try:
            # 获取页面实际尺寸
            viewport_size = await self.page.evaluate("""() => {
                return {
                    width: Math.max(document.documentElement.scrollWidth, window.innerWidth),
                    height: Math.max(document.documentElement.scrollHeight, window.innerHeight)
                };
            }""")
            
            # 如果页面内容超出视窗，使用完整页面截图
            current_viewport = await self.page.evaluate("() => ({width: window.innerWidth, height: window.innerHeight})")
            
            if (viewport_size['width'] > current_viewport['width'] or 
                viewport_size['height'] > current_viewport['height']):
                # 页面有滚动内容，使用完整页面截图
                screenshot = await self.page.screenshot(type='png', full_page=False)
            else:
                # 页面内容在视窗内，使用视窗截图
                screenshot = await self.page.screenshot(type='png', full_page=False)
                
        except Exception as e:
            # 备用方案：使用完整页面截图
            screenshot = await self.page.screenshot(type='png', full_page=False)
        screenshot = low_quality(screenshot)
        import base64
        return base64.b64encode(screenshot).decode('utf-8')
    
    async def clear_cookies(self, websocket: WebSocket):
        """清空浏览器cookies"""
        if not self.page:
            await self.safe_send_message(websocket, {
                'type': 'cookie-clear-result',
                'data': {'success': False, 'message': '浏览器未初始化'}
            })
            return
        
        try:
            # 清空当前页面的所有cookies
            context = self.page.context
            await context.clear_cookies()
            
            self.write_log('已清空浏览器cookies')
            await self.safe_send_message(websocket, {
                'type': 'cookie-clear-result',
                'data': {'success': True, 'message': '已清空cookies'}
            })
            
        except Exception as e:
            error_msg = f'清空cookies失败: {str(e)}'
            self.write_log(error_msg)
            await self.safe_send_message(websocket, {
                'type': 'cookie-clear-result',
                'data': {'success': False, 'message': error_msg}
            })
    
    async def load_cookies_for_script(self, websocket: WebSocket):
        """为脚本加载cookies"""
        try:
            cookies_file = './bk/cookies.json'
            if os.path.exists(cookies_file):
                with open(cookies_file, 'r') as f:
                    cookies = json.load(f)
                
                # 添加cookies到浏览器上下文
                await self.page.context.add_cookies(cookies)
                
                await self.safe_send_message(websocket, {
                    'type': 'script-status',
                    'data': {'status': 'running', 'message': '已加载 cookies'}
                })
                self.write_log('脚本启动时已加载 cookies')
            else:
                await self.safe_send_message(websocket, {
                    'type': 'script-status',
                    'data': {'status': 'running', 'message': 'cookies文件不存在，继续执行...'}
                })
                self.write_log('cookies文件不存在，脚本将在无cookies状态下执行')
                
        except Exception as e:
            error_msg = f'加载 cookies 失败: {str(e)}，继续执行...'
            await self.safe_send_message(websocket, {
                'type': 'script-status',
                'data': {'status': 'running', 'message': error_msg}
            })
            self.write_log(error_msg)
    
    async def cleanup(self):
        """清理资源"""
        self.write_log('清理资源...')
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
        self.write_log('服务器已关闭')

    async def start_tiktok_script(self, websocket: WebSocket):
        """启动TikTok脚本"""
        if self.script_running:
            await self.safe_send_message(websocket, {
                'type': 'script-status',
                'data': {'status': 'error', 'message': '脚本已在运行中'}
            })
            return
        
        self.script_running = True
        await self.safe_send_message(websocket, {
            'type': 'script-status',
            'data': {'status': 'starting', 'message': '正在启动TikTok脚本...'}
        })
        
        try:
            # 在后台运行脚本
            self.script_task = asyncio.create_task(self.run_tiktok_script_with_updates(websocket))
        except Exception as e:
            self.script_running = False
            await self.safe_send_message(websocket, {
                'type': 'script-status',
                'data': {'status': 'error', 'message': f'启动脚本失败: {str(e)}'}
            })
    
    async def run_tiktok_script_with_updates(self, websocket: WebSocket):
        """运行TikTok脚本并发送状态更新"""
        try:
            await self.safe_send_message(websocket, {
                'type': 'script-status',
                'data': {'status': 'running', 'message': '脚本正在执行中...'}
            })
            
            # 使用现有的页面实例执行脚本
            if not self.page:
                raise Exception('浏览器页面未初始化')
            
            # 在启动脚本前先加载cookies
            await self.load_cookies_for_script(websocket)
            
            # 创建回调函数来发送状态更新
            async def status_callback(message):
                await self.safe_send_message(websocket, message)
            
            # 执行适配版本的脚本
            await complete_tiktok_shop_rating_filter_integrated(self.page, status_callback)
            
            await self.safe_send_message(websocket, {
                'type': 'script-status',
                'data': {'status': 'completed', 'message': '脚本执行完成'}
            })
            
        except Exception as e:
            await self.safe_send_message(websocket, {
                'type': 'script-status',
                'data': {'status': 'error', 'message': f'脚本执行失败: {str(e)}'}
            })
        finally:
            self.script_running = False
            self.script_task = None

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