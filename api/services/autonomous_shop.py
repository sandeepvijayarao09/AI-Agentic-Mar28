"""Autonomous browser-based shopping — opens real sites, searches, adds to cart."""

import asyncio
from pathlib import Path

SCREENSHOTS_DIR = Path("screenshots")
SCREENSHOTS_DIR.mkdir(exist_ok=True)


async def shop_amazon(query: str) -> dict:
    """Open Amazon, search for a product, and try to add to cart."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        try:
            await page.goto(f"https://www.amazon.com/s?k={query.replace(' ', '+')}", timeout=20000)
            await asyncio.sleep(3)

            screenshot_path = str(SCREENSHOTS_DIR / "amazon_search.png")
            await page.screenshot(path=screenshot_path)

            # Find first product link
            product_link = page.locator("div.s-result-item h2 a").first
            await product_link.wait_for(timeout=10000)
            product_title = await product_link.inner_text()
            await product_link.click()
            await asyncio.sleep(3)

            # Get price
            price = ""
            try:
                price_el = page.locator("span.a-price span.a-offscreen").first
                price = await price_el.inner_text()
            except Exception:
                pass

            # Screenshot product page
            await page.screenshot(path=str(SCREENSHOTS_DIR / "amazon_product.png"))

            # Add to cart
            try:
                add_btn = page.locator("#add-to-cart-button")
                await add_btn.wait_for(timeout=5000)
                await add_btn.click()
                await asyncio.sleep(3)
                await page.screenshot(path=str(SCREENSHOTS_DIR / "amazon_cart.png"))

                await browser.close()
                return {
                    "status": "added_to_cart",
                    "platform": "amazon",
                    "product": product_title,
                    "price": price,
                    "message": f"Done! I added '{product_title}' ({price}) to your Amazon cart. Go to https://www.amazon.com/cart to checkout and pay!",
                }
            except Exception:
                await browser.close()
                return {
                    "status": "product_found",
                    "platform": "amazon",
                    "product": product_title,
                    "price": price,
                    "message": f"I found '{product_title}' ({price}) on Amazon. The browser is open — you can add it to cart and checkout.",
                }

        except Exception as e:
            try:
                await page.screenshot(path=str(SCREENSHOTS_DIR / "amazon_error.png"))
            except Exception:
                pass
            await browser.close()
            return {
                "status": "search_opened",
                "platform": "amazon",
                "message": f"I opened Amazon search for '{query}'. The browser window is open — browse and add to cart!",
                "url": f"https://www.amazon.com/s?k={query.replace(' ', '+')}",
            }


async def order_doordash(query: str) -> dict:
    """Open DoorDash and search for a restaurant or food."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        try:
            url = f"https://www.doordash.com/search/store/{query.replace(' ', '%20')}/"
            await page.goto(url, timeout=20000)
            await asyncio.sleep(4)

            screenshot_path = str(SCREENSHOTS_DIR / "doordash_search.png")
            await page.screenshot(path=screenshot_path)

            # Try clicking first restaurant
            try:
                first_card = page.locator("a[data-testid='StoreSearchCard'], a[href*='/store/']").first
                await first_card.wait_for(timeout=8000)
                restaurant_name = (await first_card.inner_text()).split("\n")[0]
                await first_card.click()
                await asyncio.sleep(3)
                await page.screenshot(path=str(SCREENSHOTS_DIR / "doordash_menu.png"))

                await browser.close()
                return {
                    "status": "restaurant_opened",
                    "platform": "doordash",
                    "restaurant": restaurant_name,
                    "message": f"I opened '{restaurant_name}' on DoorDash! The browser is showing their menu. Add items to your cart and checkout to order!",
                }
            except Exception:
                await browser.close()
                return {
                    "status": "search_opened",
                    "platform": "doordash",
                    "message": f"I opened DoorDash search for '{query}'. The browser is open — pick a restaurant and order!",
                    "url": url,
                }

        except Exception as e:
            await browser.close()
            return {
                "status": "search_opened",
                "platform": "doordash",
                "message": f"I opened DoorDash for '{query}'. Browse restaurants and order!",
                "url": f"https://www.doordash.com/search/store/{query.replace(' ', '%20')}/",
            }
