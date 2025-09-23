#!/usr/bin/env python3
"""
TikTok Shop 商品评分筛选完整流程
完成如下步骤的完整的 playwright 代码：
1. 进入 TikTok Shop 商品评分页面
2. 点击侧边栏商品、商品评分
3. 点击1星和2星按钮，点击已回复按钮
4. 点击日期选择器弹出弹窗
5. 选择7天前到今天的日期范围（动态计算）
"""
import asyncio
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

async def complete_tiktok_shop_rating_filter():
    """完整的TikTok Shop商品评分筛选流程"""
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        # 读取cookies文件
        with open('./cookies.json', 'r') as f:
            cookies = json.load(f)

        # 添加cookies到浏览器上下文
        await context.add_cookies(cookies)

        # 创建新页面
        page = await context.new_page()

        # 设置shop_region参数
        shop_region = 'PH'

        try:
            print("=== 第一步：进入TikTok Shop页面 ===")
            # 访问TikTok Shop卖家中心首页
            url = f'https://seller.tiktokshopglobalselling.com/homepage?shop_region={shop_region}'
            await page.goto(url)
            print("-----------1")
            await page.wait_for_load_state('networkidle')
            print("-----------2")
            await page.wait_for_timeout(30000)
            print("-----------3")
            print(f"✓ 成功访问TikTok Shop卖家中心，shop_region: {shop_region}")
            print(f"✓ 当前页面标题: {await page.title()}")

            print("\\n=== 第二步：导航到商品评分页面 ===")
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
                        print(f"✓ 成功点击商品菜单: {selector}")
                        product_clicked = True
                        break
                    except:
                        continue

                if not product_clicked:
                    print("尝试通过悬停展开商品菜单")
                    await page.hover('text=商品', timeout=5000)
                    await page.wait_for_timeout(1000)

                # 等待商品子菜单展开
                await page.wait_for_timeout(2000)

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
                        print(f"✓ 成功点击商品评分: {selector}")
                        rating_clicked = True
                        break
                    except:
                        continue

                if not rating_clicked:
                    print("无法找到商品评分菜单，直接访问URL")
                    rating_url = f'https://seller.tiktokshopglobalselling.com/product/rating?shop_region={shop_region}'
                    await page.goto(rating_url)

            except Exception as e:
                print(f"通过菜单导航失败: {e}")
                # 直接访问商品评分页面
                rating_url = f'https://seller.tiktokshopglobalselling.com/product/rating?shop_region={shop_region}'
                await page.goto(rating_url)

            # 等待商品评分页面加载完成
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(3000)
            print(f"✓ 成功进入商品评分页面")

            print("\\n=== 第三步：筛选1星2星和已回复评价 ===")
            # 点击1星按钮
            try:
                one_star_selector = '[data-id="product.rating.filter_one_star"]'
                await page.click(one_star_selector, timeout=5000)
                print("✓ 成功点击1星按钮")
                await page.wait_for_timeout(1000)
            except Exception as e:
                print(f"点击1星按钮失败: {e}")
                try:
                    await page.click('button:has([class*="star-fill"]):nth-of-type(1)', timeout=3000)
                    print("✓ 使用备用方式点击1星按钮")
                except:
                    print("✗ 无法点击1星按钮")

            # 点击2星按钮
            try:
                two_star_selector = '[data-id="product.rating.filter_two_stars"]'
                await page.click(two_star_selector, timeout=5000)
                print("✓ 成功点击2星按钮")
                await page.wait_for_timeout(1000)
            except Exception as e:
                print(f"点击2星按钮失败: {e}")
                try:
                    await page.click('button:has([class*="star-fill"]):nth-of-type(2)', timeout=3000)
                    print("✓ 使用备用方式点击2星按钮")
                except:
                    print("✗ 无法点击2星按钮")

            # 点击已回复按钮
            try:
                replied_selector = '[data-id="product.rating.filter_replied"]'
                await page.click(replied_selector, timeout=5000)
                print("✓ 成功点击已回复按钮")
                await page.wait_for_timeout(2000)
            except Exception as e:
                print(f"点击已回复按钮失败: {e}")
                try:
                    await page.click('text=已回复', timeout=3000)
                    print("✓ 使用备用方式点击已回复按钮")
                except:
                    print("✗ 无法点击已回复按钮")

            print("\\n=== 第四步：打开日期选择器 ===")
            # 计算日期
            today = datetime.now()
            seven_days_ago = today - timedelta(days=7)
            today_day = today.day
            seven_days_ago_day = seven_days_ago.day

            print(f"今天是: {today.strftime('%Y年%m月%d日')} (日期: {today_day})")
            print(f"7天前是: {seven_days_ago.strftime('%Y年%m月%d日')} (日期: {seven_days_ago_day})")

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
                        print(f"✓ 成功点击日期选择器: {selector}")
                        date_picker_clicked = True
                        break
                    except:
                        continue

                if not date_picker_clicked:
                    # 尝试点击包含"从"或"到"的输入框
                    try:
                        await page.click('input[placeholder="从"]', timeout=3000)
                        print("✓ 成功点击'从'输入框")
                        date_picker_clicked = True
                    except:
                        try:
                            await page.click('input[placeholder="到"]', timeout=3000)
                            print("✓ 成功点击'到'输入框")
                            date_picker_clicked = True
                        except:
                            try:
                                await page.click('.theme-arco-icon-calendar', timeout=3000)
                                print("✓ 成功点击日历图标")
                                date_picker_clicked = True
                            except:
                                print("✗ 无法点击任何日期选择器元素")

                if date_picker_clicked:
                    # 等待日期选择弹窗完全显示
                    await page.wait_for_timeout(3000)

                    # 检查是否有日期选择弹窗出现
                    try:
                        await page.wait_for_selector('.core-picker-body', timeout=5000)
                        print("✓ 日期选择器弹窗已显示")
                    except:
                        try:
                            await page.wait_for_selector('[class*="calendar"]', timeout=3000)
                            print("✓ 日历组件已显示")
                        except:
                            print("⚠ 未检测到日期选择器弹窗，但继续执行...")

                    print("\\n=== 第五步：选择7天前到今天的日期范围 ===")

                    # 点击7天前的日期
                    try:
                        seven_days_ago_selector = f'.core-picker-cell-in-view:has-text("{seven_days_ago_day:02d}")'
                        await page.click(seven_days_ago_selector, timeout=3000)
                        print(f"✓ 成功点击7天前的日期: {seven_days_ago_day}号")
                    except:
                        try:
                            # 如果两位数格式失败，尝试一位数格式
                            seven_days_ago_selector = f'.core-picker-cell-in-view:has-text("{seven_days_ago_day}")'
                            await page.click(seven_days_ago_selector, timeout=3000)
                            print(f"✓ 成功点击7天前的日期: {seven_days_ago_day}号")
                        except Exception as e:
                            print(f"✗ 点击7天前日期失败: {e}")

                    await page.wait_for_timeout(1000)

                    # 点击今天的日期
                    try:
                        today_selector = f'.core-picker-cell-in-view:has-text("{today_day:02d}")'
                        await page.click(today_selector, timeout=3000)
                        print(f"✓ 成功点击今天的日期: {today_day}号")
                    except:
                        try:
                            # 如果两位数格式失败，尝试一位数格式
                            today_selector = f'.core-picker-cell-in-view:has-text("{today_day}")'
                            await page.click(today_selector, timeout=3000)
                            print(f"✓ 成功点击今天的日期: {today_day}号")
                        except Exception as e:
                            print(f"✗ 点击今天日期失败: {e}")

                    await page.wait_for_timeout(2000)
                    print("✓ 日期范围选择完成，等待页面更新...")

                    # 等待页面加载筛选结果
                    await page.wait_for_timeout(3000)
                    await page.wait_for_load_state('networkidle')

            except Exception as e:
                print(f"日期选择过程出错: {e}")

            print("\\n=== 流程完成 ===")
            print(f"✓ 当前页面URL: {page.url}")
            print("✓ 已完成以下筛选:")
            print("  - 评分：1星和2星")
            print("  - 回复状态：已回复")
            print(f"  - 日期范围：{seven_days_ago.strftime('%Y年%m月%d日')} 到 {today.strftime('%Y年%m月%d日')}")

            # 保持页面打开一段时间以便观察结果
            await asyncio.sleep(10)

        except Exception as e:
            print(f"执行过程中出错: {e}")

        finally:
            # 关闭浏览器
            await browser.close()

if __name__ == "__main__":
    asyncio.run(complete_tiktok_shop_rating_filter())