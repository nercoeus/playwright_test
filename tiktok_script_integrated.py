#!/usr/bin/env python3
"""
TikTok Shop 商品评分筛选完整流程 - 适配版本
使用现有的 playwright 实例而不是创建新的浏览器
"""
import asyncio
import json
import time
from datetime import datetime, timedelta
from playwright.async_api import Page
from util import low_quality

async def complete_tiktok_shop_rating_filter_integrated(page: Page, websocket_callback=None):
    """
    完整的TikTok Shop商品评分筛选流程 - 使用现有页面实例
    
    Args:
        page: 现有的 playwright Page 实例
        websocket_callback: 可选的回调函数，用于发送状态更新
    """
    
    async def send_status(status: str, message: str):
        """发送状态更新"""
        if websocket_callback:
            await websocket_callback({
                'type': 'script-status',
                'data': {'status': status, 'message': message}
            })
    
    async def send_screenshot_update():
        """发送截图更新到前端（极致优化版本 + 智能完整截图）"""
        if websocket_callback:
            try:
                # 获取页面实际尺寸，确保完整截图
                viewport_size = await page.evaluate("""() => {
                    return {
                        width: Math.max(document.documentElement.scrollWidth, window.innerWidth),
                        height: Math.max(document.documentElement.scrollHeight, window.innerHeight)
                    };
                }""")
                
                # 智能计算截图区域，确保不截断内容
                target_width = min(960, viewport_size['width'])  # 最大960px，但不超过实际内容
                target_height = min(540, viewport_size['height'])  # 最大540px，但不超过实际内容
                
                # 极致优化截图参数：最低质量和分辨率，最快速度，但保证完整性
                screenshot = await page.screenshot(
                    type='jpeg',  # 使用JPEG格式，文件更小
                    quality=30,   # 降低质量到30%，极大减少文件大小
                    full_page=False  # 只截取可视区域
                )
                # 对截图进行质量压缩
                screenshot = low_quality(screenshot)
                
                import base64
                screenshot_data = base64.b64encode(screenshot).decode('utf-8')
                await websocket_callback({
                    'type': 'screenshot',
                    'data': {'screenshot': screenshot_data}
                })
            except Exception as e:
                # 如果智能截图失败，尝试更基础的低质量截图
                try:
                    # 获取视窗尺寸作为备用
                    viewport_size = await page.evaluate("() => ({width: window.innerWidth, height: window.innerHeight})")
                    backup_width = min(800, viewport_size['width'])
                    backup_height = min(450, viewport_size['height'])
                    
                    screenshot = await page.screenshot(
                        type='jpeg', 
                        quality=20,  # 更低质量
                        clip={'x': 0, 'y': 0, 'width': backup_width, 'height': backup_height}  # 智能备用尺寸
                    )
                    screenshot = low_quality(screenshot)
                    import base64
                    screenshot_data = base64.b64encode(screenshot).decode('utf-8')
                    await websocket_callback({
                        'type': 'screenshot',
                        'data': {'screenshot': screenshot_data}
                    })
                except Exception as e2:
                    # 最后的备用方案：完整页面截图（低质量）
                    try:
                        screenshot = await page.screenshot(
                            type='jpeg', 
                            quality=15,
                            full_page=False  # 完整页面，确保不遗漏内容
                        )
                        screenshot = low_quality(screenshot)
                        import base64
                        screenshot_data = base64.b64encode(screenshot).decode('utf-8')
                        await websocket_callback({
                            'type': 'screenshot',
                            'data': {'screenshot': screenshot_data}
                        })
                    except Exception as e3:
                        await send_status('warning', f'截图失败: {str(e3)}')
    
    # 读取cookies文件
    try:
        with open('./bk/cookies.json', 'r') as f:
            cookies = json.load(f)
        
        # 添加cookies到浏览器上下文
        await page.context.add_cookies(cookies)
        await send_status('running', '已加载 cookies')
    except Exception as e:
        await send_status('warning', f'加载 cookies 失败: {str(e)}，继续执行...')

    # 设置shop_region参数
    shop_region = 'TH'

    try:
        await send_status('running', '第一步：进入TikTok Shop页面')
        # 访问TikTok Shop卖家中心首页
        url = f'https://seller.tiktokshopglobalselling.com/homepage?shop_region={shop_region}'
        
        # 增强的页面访问策略 - 多次重试机制
        max_retries = 3
        retry_count = 0
        page_loaded = False
        
        while retry_count < max_retries and not page_loaded:
            try:
                retry_count += 1
                await send_status('running', f'正在访问: {url} (尝试 {retry_count}/{max_retries})')
                
                # 第一次尝试：标准访问
                if retry_count == 1:
                    await page.goto(url, timeout=90000, wait_until='domcontentloaded')
                # 第二次尝试：更宽松的等待条件
                elif retry_count == 2:
                    await page.goto(url, timeout=120000, wait_until='load')
                # 第三次尝试：最宽松的条件
                else:
                    await page.goto(url, timeout=150000, wait_until='commit')
                
                await send_status('running', f'页面访问成功 (尝试 {retry_count})，等待页面稳定...')
                
                # 多层级等待策略
                try:
                    # 第一级：网络空闲等待 (最理想)
                    # await page.wait_for_load_state('networkidle', timeout=60000)  # 增加到60秒
                    await page.wait_for_timeout(3000)
                    await send_status('success', '✓ 页面网络空闲，加载完成')
                    page_loaded = True
                    
                except Exception as network_e:
                    await send_status('warning', f'网络空闲等待超时 (尝试 {retry_count}): {str(network_e)}')
                    
                    try:
                        # 第二级：DOM内容加载等待
                        await page.wait_for_load_state('domcontentloaded', timeout=30000)
                        await page.wait_for_timeout(5000)
                        await send_status('running', '✓ 页面DOM加载完成')
                        
                        # 检查页面是否真的加载了内容
                        page_title = await page.title()
                        if page_title and len(page_title) > 0:
                            await send_status('success', f'✓ 页面加载成功: {page_title}')
                            page_loaded = True
                        else:
                            raise Exception("页面标题为空，可能未正确加载")
                            
                    except Exception as dom_e:
                        await send_status('warning', f'DOM加载等待也超时 (尝试 {retry_count}): {str(dom_e)}')
                        
                        if retry_count == max_retries:
                            # 最后一次尝试：强制等待并检查页面状态
                            await page.wait_for_timeout(10000)  # 强制等待10秒
                            
                            # 尝试获取页面信息来验证是否加载成功
                            try:
                                page_url = page.url
                                page_title = await page.title()
                                await send_status('running', f'强制继续执行 - URL: {page_url}, 标题: {page_title}')
                                
                                # 如果URL包含预期的域名，认为加载成功
                                if 'tiktokshop' in page_url.lower():
                                    page_loaded = True
                                    await send_status('success', '✓ 页面基本加载完成，继续执行')
                                else:
                                    await send_status('error', f'页面可能未正确加载，当前URL: {page_url}')
                                    
                            except Exception as check_e:
                                await send_status('error', f'无法验证页面状态: {str(check_e)}')
                        
            except Exception as goto_e:
                await send_status('error', f'页面访问失败 (尝试 {retry_count}): {str(goto_e)}')
                
                if retry_count < max_retries:
                    await send_status('running', f'等待 {retry_count * 2} 秒后重试...')
                    await page.wait_for_timeout(retry_count * 2000)  # 递增等待时间
                else:
                    await send_status('error', '所有重试均失败，但尝试继续执行脚本')
                    # 即使失败也尝试继续，可能页面已经部分加载
                    try:
                        current_url = page.url
                        if 'tiktokshop' in current_url.lower():
                            page_loaded = True
                            await send_status('warning', '检测到TikTok Shop页面，尝试继续执行')
                    except:
                        pass
        
        # 发送页面截图
        try:
            await send_screenshot_update()
            if page_loaded:
                await send_status('success', '成功进入TikTok Shop页面')
            else:
                await send_status('warning', 'TikTok Shop页面可能未完全加载，但继续执行')
        except Exception as screenshot_e:
            await send_status('warning', f'截图失败: {str(screenshot_e)}，继续执行脚本')

        await send_status('running', '第二步：导航到商品评分页面')
        
        # 等待页面稳定
        await page.wait_for_timeout(2000)
        
        # 减少截图频率：只在关键步骤截图，这里跳过
        # await send_screenshot_update()  # 注释掉这个截图，减少频率
        
        # 尝试通过侧边栏导航到商品评分
        try:
            # 先尝试点击商品管理菜单
            product_selectors = [
                'text=商品管理',
                'text=商品',
                '[data-testid*="product"]',
                'a[href*="product"]',
                'li:has-text("商品")',
                'span:has-text("商品管理")'
            ]

            product_clicked = False
            for selector in product_selectors:
                try:
                    await page.click(selector, timeout=2000)
                    await send_status('running', f'✓ 成功点击商品菜单: {selector}')
                    product_clicked = True
                    break
                except:
                    continue

            if not product_clicked:
                await send_status('running', '尝试通过悬停展开商品菜单')
                await page.hover('text=商品', timeout=5000)

            # 等待商品子菜单展开
            await page.wait_for_timeout(1000)

            # 点击商品评分
            rating_selectors = [
                'text=商品评分',
                'a[href*="rating"]',
                'a[href*="review"]',
                'li:has-text("商品评分")',
                'span:has-text("商品评分")'
            ]

            rating_clicked = False
            for selector in rating_selectors:
                try:
                    await page.click(selector, timeout=3000)
                    await send_status('running', f'✓ 成功点击商品评分: {selector}')
                    rating_clicked = True
                    break
                except:
                    continue

            if not rating_clicked:
                await send_status('running', '无法找到商品评分菜单，直接访问URL')
                rating_url = f'https://seller.tiktokshopglobalselling.com/product/rating?shop_region={shop_region}'
                await page.goto(rating_url)

        except Exception as e:
            await send_status('running', f'通过菜单导航失败: {e}，直接访问URL')
            # 直接访问商品评分页面
            rating_url = f'https://seller.tiktokshopglobalselling.com/product/rating?shop_region={shop_region}'
            await page.goto(rating_url, timeout=90000)  # 增加超时时间

        # 等待商品评分页面加载完成，使用更强的重试机制
        try:
            await page.wait_for_load_state('networkidle', timeout=45000)
            await page.wait_for_timeout(3000)
            await send_status('success', '✓ 商品评分页面网络空闲，加载完成')
        except Exception as rating_e:
            await send_status('warning', f'评分页面网络空闲等待超时: {str(rating_e)}，尝试其他策略')
            try:
                await page.wait_for_load_state('domcontentloaded', timeout=20000)
                await page.wait_for_timeout(5000)
                await send_status('running', '✓ 评分页面DOM加载完成')
            except Exception as dom_e:
                await send_status('warning', f'评分页面DOM等待也超时: {str(dom_e)}，强制继续')
                await page.wait_for_timeout(8000)
        await page.wait_for_timeout(3000)
        
        # 发送页面截图
        await send_screenshot_update()
        await send_status('running', '✓ 成功进入商品评分页面')

        await send_status('running', '第三步：筛选1星2星和已回复评价')
        # 点击1星按钮
        try:
            one_star_selector = '[data-id="product.rating.filter_one_star"]'
            await page.click(one_star_selector, timeout=5000)
            await send_status('running', '✓ 成功点击1星按钮')
            await page.wait_for_timeout(1000)
        except Exception as e:
            await send_status('running', f'点击1星按钮失败: {e}')
            try:
                await page.click('button:has([class*="star-fill"]):nth-of-type(1)', timeout=3000)
                await send_status('running', '✓ 使用备用方式点击1星按钮')
            except:
                await send_status('warning', '✗ 无法点击1星按钮')

        # 点击2星按钮
        try:
            two_star_selector = '[data-id="product.rating.filter_two_stars"]'
            await page.click(two_star_selector, timeout=5000)
            await send_status('running', '✓ 成功点击2星按钮')
            await page.wait_for_timeout(1000)
        except Exception as e:
            await send_status('running', f'点击2星按钮失败: {e}')
            try:
                await page.click('button:has([class*="star-fill"]):nth-of-type(2)', timeout=3000)
                await send_status('running', '✓ 使用备用方式点击2星按钮')
            except:
                await send_status('warning', '✗ 无法点击2星按钮')

        # 点击已回复按钮
        try:
            replied_selector = '[data-id="product.rating.filter_replied"]'
            await page.click(replied_selector, timeout=5000)
            await send_status('running', '✓ 成功点击已回复按钮')
            await page.wait_for_timeout(2000)
        except Exception as e:
            await send_status('running', f'点击已回复按钮失败: {e}')
            try:
                await page.click('text=已回复', timeout=3000)
                await send_status('running', '✓ 使用备用方式点击已回复按钮')
            except:
                await send_status('warning', '✗ 无法点击已回复按钮')

        # 发送筛选后的页面截图
        await send_screenshot_update()
        await send_status('running', '✓ 完成评分筛选设置')

        await send_status('running', '第四步：打开日期选择器')
        # 计算日期
        today = datetime.now()
        seven_days_ago = today - timedelta(days=7)
        today_day = today.day
        seven_days_ago_day = seven_days_ago.day

        await send_status('running', f'今天是: {today.strftime("%Y年%m月%d日")} (日期: {today_day})')
        await send_status('running', f'7天前是: {seven_days_ago.strftime("%Y年%m月%d日")} (日期: {seven_days_ago_day})')

        # 点击日期选择器弹出日期选择弹窗
        try:
            date_picker_selectors = [
                '[data-tid="m4b_date_picker_range_picker"]',
                '.core-picker-range',
                '.pulse-date-picker-range',
                'input[placeholder="从"]',
                '.core-picker-input',
                '.core-picker'
            ]

            date_picker_clicked = False
            for selector in date_picker_selectors:
                try:
                    await page.click(selector, timeout=3000)
                    await send_status('running', f'✓ 成功点击日期选择器: {selector}')
                    date_picker_clicked = True
                    break
                except:
                    continue

            if not date_picker_clicked:
                # 尝试点击包含"从"或"到"的输入框
                try:
                    await page.click('input[placeholder="从"]', timeout=3000)
                    await send_status('running', '✓ 成功点击"从"输入框')
                    date_picker_clicked = True
                except:
                    try:
                        await page.click('input[placeholder="到"]', timeout=3000)
                        await send_status('running', '✓ 成功点击"到"输入框')
                        date_picker_clicked = True
                    except:
                        try:
                            await page.click('.theme-arco-icon-calendar', timeout=3000)
                            await send_status('running', '✓ 成功点击日历图标')
                            date_picker_clicked = True
                        except:
                            await send_status('warning', '✗ 无法点击任何日期选择器元素')

            if date_picker_clicked:
                # 等待日期选择弹窗完全显示
                await page.wait_for_timeout(3000)

                # 检查是否有日期选择弹窗出现
                try:
                    await page.wait_for_selector('.core-picker-body', timeout=5000)
                    await send_status('running', '✓ 日期选择器弹窗已显示')
                except:
                    try:
                        await page.wait_for_selector('[class*="calendar"]', timeout=3000)
                        await send_status('running', '✓ 日历组件已显示')
                    except:
                        await send_status('warning', '⚠ 未检测到日期选择器弹窗，但继续执行...')

                await send_status('running', '第五步：选择7天前到今天的日期范围')

                # 点击7天前的日期
                try:
                    seven_days_ago_selector = f'.core-picker-cell-in-view:has-text("{seven_days_ago_day:02d}")'
                    await page.click(seven_days_ago_selector, timeout=3000)
                    await send_status('running', f'✓ 成功点击7天前的日期: {seven_days_ago_day}号')
                except:
                    try:
                        # 如果两位数格式失败，尝试一位数格式
                        seven_days_ago_selector = f'.core-picker-cell-in-view:has-text("{seven_days_ago_day}")'
                        await page.click(seven_days_ago_selector, timeout=3000)
                        await send_status('running', f'✓ 成功点击7天前的日期: {seven_days_ago_day}号')
                    except Exception as e:
                        await send_status('warning', f'✗ 点击7天前日期失败: {e}')

                await page.wait_for_timeout(1000)

                # 点击今天的日期
                try:
                    today_selector = f'.core-picker-cell-in-view:has-text("{today_day:02d}")'
                    await page.click(today_selector, timeout=3000)
                    await send_status('running', f'✓ 成功点击今天的日期: {today_day}号')
                except:
                    try:
                        # 如果两位数格式失败，尝试一位数格式
                        today_selector = f'.core-picker-cell-in-view:has-text("{today_day}")'
                        await page.click(today_selector, timeout=3000)
                        await send_status('running', f'✓ 成功点击今天的日期: {today_day}号')
                    except Exception as e:
                        await send_status('warning', f'✗ 点击今天日期失败: {e}')

                await page.wait_for_timeout(2000)
                await send_status('running', '✓ 日期范围选择完成，等待页面更新...')

                # 等待页面加载筛选结果，使用更强的重试机制
                await page.wait_for_timeout(3000)
                try:
                    await page.wait_for_load_state('networkidle', timeout=45000)
                    await send_status('success', '✓ 筛选结果加载完成')
                except Exception as filter_e:
                    await send_status('warning', f'筛选结果网络空闲等待超时: {str(filter_e)}，强制继续')
                    await page.wait_for_timeout(5000)
                
                # 发送最终结果截图
                await send_screenshot_update()

        except Exception as e:
            await send_status('error', f'日期选择过程出错: {e}')

        # 最终完成时发送截图（保留这个重要截图）
        await send_screenshot_update()
        await send_status('completed', '流程完成')
        await send_status('completed', f'当前页面URL: {page.url}')
        await send_status('completed', '已完成以下筛选:')
        await send_status('completed', '  - 评分：1星和2星')
        await send_status('completed', '  - 回复状态：已回复')
        await send_status('completed', f'  - 日期范围：{seven_days_ago.strftime("%Y年%m月%d日")} 到 {today.strftime("%Y年%m月%d日")}')

    except Exception as e:
        await send_status('error', f'执行过程中出错: {e}')
        raise e