# Standard library imports
import os
import sys
from openpyxl import load_workbook, Workbook
import time
import subprocess
from datetime import datetime, timedelta
import warnings
from transformers import pipeline, Conversation
import pandas as pd
from openpyxl.styles import Font, Border, Side, PatternFill, Alignment

# Third-party imports
from playwright.sync_api import sync_playwright
from openpyxl.styles import Font

warnings.filterwarnings("ignore", category=UserWarning, module="playwright_stealth")
warnings.filterwarnings("ignore", category=DeprecationWarning)

last_messages = []

# region playwright-stealth (fork mais atualizado recomendado em 2025/2026)
try:
    from playwright_stealth import stealth_sync
except ImportError:
    print("playwright-stealth não encontrado.")
    print("Instale com: pip install git+https://github.com/AtuboDad/playwright_stealth.git")
    sys.exit(1)
# endregion

def cleanup(pw=None, context=None, browser_process=None):
    """Cleanup resources properly"""
    if context:
        try:
            context.close()
        except Exception as e:
            print(f"Error closing context: {e}")
    if pw:
        try:
            pw.stop()
        except Exception as e:
            print(f"Error stopping Playwright: {e}")
    if browser_process:
        try:
            browser_process.terminate()
            browser_process.wait(timeout=5)
        except Exception as e:
            print(f"Error terminating browser process: {e}")
    print("Recursos liberados")

def open_chrome_in_privacy_login_page():
    # 1. Paths
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    # We use a subfolder to avoid the 'default directory' security error
    user_data = os.path.join(os.environ['LOCALAPPDATA'], r"Google\Chrome\User Data\Automation")

    # 2. Kill any existing Chrome
    os.system("taskkill /f /im chrome.exe /t >nul 2>&1")
    time.sleep(2)

    # 3. Launch Chrome as a SEPARATE process (Native Launch)
    # We open a 'Remote Debugging Port' that Playwright will use to connect
    print("Launching Native Chrome Process...")
    browser_process = subprocess.Popen([
        chrome_path,
        f"--user-data-dir={user_data}",
        "--remote-debugging-port=9222",
        "--start-maximized",
        "--no-first-run",
        "--no-default-browser-check",
        "https://privacy.com.br/board"
    ])

    # Give the browser 5 seconds to fully open and start the debugging server
    time.sleep(5)

    # 4. Connect Playwright to the ALREADY OPENED Chrome
    pw = sync_playwright().start()
    try:
        print("Hooking Playwright into the running Chrome...")
        # Instead of launch_persistent_context, we CONNECT to the port
        browser = pw.chromium.connect_over_cdp("http://localhost:9222")

        # Access the already open context and page
        context = browser.contexts[0]
        page = context.pages[0]

        print("Successfully hooked! Browser is now under automation control.")
        return pw, context, browser_process

    except Exception as e:
        print(f"Hook failed: {e}")
        pw.stop()
        browser_process.kill()
        raise

def insert_username(page):
    """
    Attempt to find the username input field and insert 'milfelectra@gmail.com'.
    Handles Shadow DOM and multiple selector strategies.
    """
    try:
        # List of selectors to try (updated with new ID and paths)
        selectors = [
            # Shadow DOM JavaScript selector (most reliable for this page, updated with new ID)
            'document.querySelector("#privacy-web-auth").shadowRoot.querySelector("#floating-input-jnygnm9")',
            'document.querySelector("#privacy-web-auth").shadowRoot.querySelector("input[type=\'email\']")',
            'document.querySelector("#privacy-web-auth").shadowRoot.querySelector("input.el-input__inner[type=\'email\']")',
            'document.querySelector("#privacy-web-auth").shadowRoot.querySelector("div > div > div:nth-child(1) > div > form > div:nth-child(1) input")',
            # Direct CSS selectors (if Shadow DOM is not present, updated with new ID)
            "#floating-input-jnygnm9",
            "input#floating-input-jnygnm9",
            "input.el-input__inner[type='email']",
            "input[type='email'][autocomplete='off']",
            "input[placeholder=' '][type='email']",
            # Generalized for dynamic IDs
            'document.querySelector("#privacy-web-auth").shadowRoot.querySelector("input[id^=\'floating-input-\']")',
            # XPath (may not work with Shadow DOM, updated with new ID)
            "//*[@id='floating-input-jnygnm9']",
            "//*[@id='privacy-web-auth']//div/div/div[1]/div/form/div[1]//input",
            "//input[@type='email' and contains(@id, 'floating-input')]",
            "//input[@class='el-input__inner' and @type='email']"
        ]

        # Try each selector
        for selector in selectors:
            try:
                # Handle different selector types
                if selector.startswith("document.querySelector"):
                    # JavaScript selector (handles shadow DOM)
                    input_inserted = page.evaluate(f'''(text) => {{
                        try {{
                            const input = {selector};
                            if (input) {{
                                input.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                                input.focus();
                                input.value = text;
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                                return true;
                            }}
                        }} catch(e) {{
                            console.error('Error inserting username:', e);
                        }}
                        return false;
                    }}''', "milfelectra@gmail.com")
                    if input_inserted:
                        print("✓ Username inserted successfully with Shadow DOM selector")
                        return True

                elif selector.startswith('/'):
                    # XPath selector
                    xpath_elements = page.locator(f"xpath={selector}")
                    if xpath_elements.count() > 0:
                        try:
                            # Force visibility
                            page.evaluate(f'''(selector) => {{
                                const element = document.evaluate(
                                    `{selector}`,
                                    document,
                                    null,
                                    XPathResult.FIRST_ORDERED_NODE_TYPE,
                                    null
                                ).singleNodeValue;
                                if (element) {{
                                    element.style.opacity = '1';
                                    element.style.visibility = 'visible';
                                    element.style.display = 'block';
                                }}
                            }}''', selector)
                            # Scroll, focus, and fill
                            xpath_elements.first.scroll_into_view_if_needed()
                            xpath_elements.first.focus()
                            xpath_elements.first.fill("milfelectra@gmail.com")
                            print("✓ Username inserted successfully with XPath")
                            return True
                        except Exception as e:
                            print(f"XPath insert failed: {str(e)}")

                else:
                    # CSS selector
                    css_elements = page.locator(selector)
                    if css_elements.count() > 0:
                        try:
                            # Force visibility
                            page.evaluate(f'''(selector) => {{
                                const element = document.querySelector(selector);
                                if (element) {{
                                    element.style.opacity = '1';
                                    element.style.visibility = 'visible';
                                    element.style.display = 'block';
                                }}
                            }}''', selector)
                            # Scroll, focus, and fill
                            css_elements.first.scroll_into_view_if_needed()
                            css_elements.first.focus()
                            css_elements.first.fill("milfelectra@gmail.com")
                            print("✓ Username inserted successfully with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector insert failed: {str(e)}")

            except Exception as e:
                print(f"Failed with username input selector {selector}: {str(e)}")
                continue

        # Fallback JavaScript approach with comprehensive search (updated with new patterns)
        print("Trying JavaScript fallback approach for username input...")
        fallback_inserted = page.evaluate('''(text) => {
            // Try Shadow DOM first
            const shadowHost = document.querySelector("#privacy-web-auth");
            if (shadowHost && shadowHost.shadowRoot) {
                // Try multiple selectors inside shadow DOM (updated with new ID)
                const shadowSelectors = [
                    '#floating-input-jnygnm9',
                    'input[id^="floating-input-"]',
                    'input[type="email"]',
                    'input.el-input__inner[type="email"]',
                    'input[autocomplete="off"][type="email"]',
                    'input[placeholder=" "][type="email"]',
                    'div > div > div:nth-child(1) > div > form > div:nth-child(1) input'
                ];

                for (const selector of shadowSelectors) {
                    const shadowInput = shadowHost.shadowRoot.querySelector(selector);
                    if (shadowInput) {
                        shadowInput.scrollIntoView({behavior: 'smooth', block: 'center'});
                        shadowInput.focus();
                        shadowInput.value = text;
                        shadowInput.dispatchEvent(new Event('input', { bubbles: true }));
                        shadowInput.dispatchEvent(new Event('change', { bubbles: true }));
                        shadowInput.dispatchEvent(new Event('blur', { bubbles: true }));
                        return true;
                    }
                }
            }

            // Try regular DOM as fallback
            const inputSelectors = [
                '#floating-input-jnygnm9',
                'input[id^="floating-input-"]',
                'input[type="email"]',
                'input.el-input__inner[type="email"]',
                'input[autocomplete="off"][type="email"]',
                'input[tabindex="0"][type="email"]',
                'input[placeholder=" "][type="email"]'
            ];

            for (const selector of inputSelectors) {
                const inputs = document.querySelectorAll(selector);
                for (const input of inputs) {
                    if (input && input.offsetParent !== null) {
                        input.scrollIntoView({behavior: 'smooth', block: 'center'});
                        input.focus();
                        input.value = text;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                        input.dispatchEvent(new Event('blur', { bubbles: true }));
                        return true;
                    }
                }
            }

            return false;
        }''', "milfelectra@gmail.com")

        if fallback_inserted:
            print("✓ Username inserted successfully using JavaScript fallback!")
            return True

        print("❌ Could not find or insert into username input using any method.")
        return False

    except Exception as e:
        print(f"❌ Error in insert_username: {str(e)}")
        return False

def insert_password(page):
    """
    Attempt to find the password input field and insert '#Partiu14'.
    Handles Shadow DOM and multiple selector strategies.
    """
    try:
        # List of selectors to try (updated with new ID and paths)
        selectors = [
            # Shadow DOM JavaScript selectors (most reliable for this page, updated with new ID)
            'document.querySelector("#privacy-web-auth").shadowRoot.querySelector("#floating-input-sekcpj1")',
            'document.querySelector("#privacy-web-auth").shadowRoot.querySelector("input[type=\'password\']")',
            'document.querySelector("#privacy-web-auth").shadowRoot.querySelector("input.el-input__inner[type=\'password\']")',
            'document.querySelector("#privacy-web-auth").shadowRoot.querySelector("div > div > div:nth-child(1) > div > form > div.el-form-item.is-required.asterisk-left input")',
            'document.querySelector("#privacy-web-auth").shadowRoot.querySelector("div > div > div:nth-child(1) > div > form > div:nth-child(2) input")',
            # Direct CSS selectors (if Shadow DOM is not present, updated with new ID)
            "#floating-input-sekcpj1",
            "input#floating-input-sekcpj1",
            "input.el-input__inner[type='password']",
            "input[type='password'][autocomplete='off']",
            "input[placeholder=' '][type='password']",
            "div.el-form-item.is-required input[type='password']",
            # Generalized for dynamic IDs
            'document.querySelector("#privacy-web-auth").shadowRoot.querySelector("input[id^=\'floating-input-\']")',
            # XPath (may not work with Shadow DOM, updated with new ID)
            "//*[@id='floating-input-sekcpj1']",
            "//*[@id='privacy-web-auth']//div/div/div[1]/div/form/div[2]//input",
            "//input[@type='password' and contains(@id, 'floating-input')]",
            "//input[@class='el-input__inner' and @type='password']",
            "//div[contains(@class, 'is-required')]//input[@type='password']"
        ]

        # Try each selector
        for selector in selectors:
            try:
                # Handle different selector types
                if selector.startswith("document.querySelector"):
                    # JavaScript selector (handles shadow DOM)
                    input_inserted = page.evaluate(f'''(text) => {{
                        try {{
                            const input = {selector};
                            if (input) {{
                                input.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                                input.focus();
                                input.value = text;
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                                return true;
                            }}
                        }} catch(e) {{
                            console.error('Error inserting password:', e);
                        }}
                        return false;
                    }}''', "#Partiu14")
                    if input_inserted:
                        print("✓ Password inserted successfully with Shadow DOM selector")
                        return True

                elif selector.startswith('/'):
                    # XPath selector
                    xpath_elements = page.locator(f"xpath={selector}")
                    if xpath_elements.count() > 0:
                        try:
                            # Force visibility
                            page.evaluate(f'''(selector) => {{
                                const element = document.evaluate(
                                    `{selector}`,
                                    document,
                                    null,
                                    XPathResult.FIRST_ORDERED_NODE_TYPE,
                                    null
                                ).singleNodeValue;
                                if (element) {{
                                    element.style.opacity = '1';
                                    element.style.visibility = 'visible';
                                    element.style.display = 'block';
                                }}
                            }}''', selector)
                            # Scroll, focus, and fill
                            xpath_elements.first.scroll_into_view_if_needed()
                            xpath_elements.first.focus()
                            xpath_elements.first.fill("#Partiu14")
                            print("✓ Password inserted successfully with XPath")
                            return True
                        except Exception as e:
                            print(f"XPath insert failed: {str(e)}")

                else:
                    # CSS selector
                    css_elements = page.locator(selector)
                    if css_elements.count() > 0:
                        try:
                            # Force visibility
                            page.evaluate(f'''(selector) => {{
                                const element = document.querySelector(selector);
                                if (element) {{
                                    element.style.opacity = '1';
                                    element.style.visibility = 'visible';
                                    element.style.display = 'block';
                                }}
                            }}''', selector)
                            # Scroll, focus, and fill
                            css_elements.first.scroll_into_view_if_needed()
                            css_elements.first.focus()
                            css_elements.first.fill("#Partiu14")
                            print("✓ Password inserted successfully with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector insert failed: {str(e)}")

            except Exception as e:
                print(f"Failed with password input selector {selector}: {str(e)}")
                continue

        # Fallback JavaScript approach with comprehensive search (updated with new patterns)
        print("Trying JavaScript fallback approach for password input...")
        fallback_inserted = page.evaluate('''(text) => {
            // Try Shadow DOM first
            const shadowHost = document.querySelector("#privacy-web-auth");
            if (shadowHost && shadowHost.shadowRoot) {
                // Try multiple selectors inside shadow DOM (updated with new ID)
                const shadowSelectors = [
                    '#floating-input-sekcpj1',
                    'input[id^="floating-input-"]',
                    'input[type="password"]',
                    'input.el-input__inner[type="password"]',
                    'input[autocomplete="off"][type="password"]',
                    'input[placeholder=" "][type="password"]',
                    'div.el-form-item.is-required input[type="password"]',
                    'div > div > div:nth-child(1) > div > form > div:nth-child(2) input',
                    'div.el-form-item.is-required.asterisk-left input'
                ];

                for (const selector of shadowSelectors) {
                    const shadowInput = shadowHost.shadowRoot.querySelector(selector);
                    if (shadowInput) {
                        shadowInput.scrollIntoView({behavior: 'smooth', block: 'center'});
                        shadowInput.focus();
                        shadowInput.value = text;
                        shadowInput.dispatchEvent(new Event('input', { bubbles: true }));
                        shadowInput.dispatchEvent(new Event('change', { bubbles: true }));
                        shadowInput.dispatchEvent(new Event('blur', { bubbles: true }));
                        return true;
                    }
                }
            }

            // Try regular DOM as fallback
            const inputSelectors = [
                '#floating-input-sekcpj1',
                'input[id^="floating-input-"]',
                'input[type="password"]',
                'input.el-input__inner[type="password"]',
                'input[autocomplete="off"][type="password"]',
                'input[tabindex="0"][type="password"]',
                'input[placeholder=" "][type="password"]',
                'div.el-form-item.is-required input[type="password"]'
            ];

            for (const selector of inputSelectors) {
                const inputs = document.querySelectorAll(selector);
                for (const input of inputs) {
                    if (input && input.offsetParent !== null) {
                        input.scrollIntoView({behavior: 'smooth', block: 'center'});
                        input.focus();
                        input.value = text;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                        input.dispatchEvent(new Event('blur', { bubbles: true }));
                        return true;
                    }
                }
            }

            return false;
        }''', "#Partiu14")

        if fallback_inserted:
            print("✓ Password inserted successfully using JavaScript fallback!")
            return True

        print("❌ Could not find or insert into password input using any method.")
        return False

    except Exception as e:
        print(f"❌ Error in insert_password: {str(e)}")
        return False

def click_on_entrar_button(page):
    """
    Finds and clicks the 'Entrar' button, bypassing Shadow DOM and disabled states.
    """
    try:
        # 1. Define the specific selectors provided
        js_path = 'document.querySelector("#privacy-web-auth").shadowRoot.querySelector("div > div > div:nth-child(1) > div > form > button")'
        css_selector = "div > div > div:nth-child(1) > div > form > button"
        xpath_selector = "//*[@id='privacy-web-auth']//div/div/div[1]/div/form/button"

        # List of approaches
        approaches = [
            {"type": "js", "path": js_path},
            {"type": "xpath", "path": xpath_selector},
            {"type": "css", "path": css_selector}
        ]

        for approach in approaches:
            try:
                if approach["type"] == "js":
                    # FORCE CLICK via JavaScript (Works even if disabled or inside shadow root)
                    clicked = page.evaluate(f'''() => {{
                        const btn = {approach["path"]};
                        if (btn) {{
                            btn.disabled = false; // Remove disabled attribute
                            btn.classList.remove('is-disabled');
                            btn.scrollIntoView({{behavior: 'instant', block: 'center'}});
                            btn.click();
                            return true;
                        }}
                        return false;
                    }}''')
                    if clicked:
                        return True

                elif approach["type"] == "xpath":
                    # Force click via Playwright locator
                    el = page.locator(f"xpath={approach['path']}")
                    if el.count() > 0:
                        el.first.click(force=True, timeout=2000)
                        return True

            except Exception:
                continue

        # Final Fallback: Search for the button by text content "Entrar"
        fallback = page.evaluate('''() => {
            const authRoot = document.querySelector("#privacy-web-auth")?.shadowRoot;
            if (authRoot) {
                const buttons = authRoot.querySelectorAll('button');
                for (const btn of buttons) {
                    if (btn.textContent.includes('Entrar')) {
                        btn.disabled = false;
                        btn.click();
                        return true;
                    }
                }
            }
            return false;
        }''')
        return fallback

    except Exception as e:
        print(f"Error in click_on_entrar_button: {e}")
        return False

from playwright.sync_api import sync_playwright

def click_to_filter_messages_by(page):
    """
    Attempt to find and click the 'Filter Messages' button using multiple approaches.
    This method handles elements within a shadow DOM automatically with Playwright.
    """
    try:
        # List of selectors to try for the filter button
        selectors = [
            # Primary CSS selector provided
            "div > div > div > div.vac-rooms-container.vac-rooms-container-full > div.vac-wrapper-header-actions > div.vac-header-actions > div.vac-header-actions-buttons > button:nth-child(4) > svg",
            # XPath selector provided
            "//*[@id='privacy-web-chat']//div/div/div/div[2]/div[1]/div[1]/div[2]/button[4]/svg",
            # More generic CSS selector for the SVG icon if the nth-child changes
            "button:has(svg.fa-bars-filter)",
            # CSS selector targeting the button directly, assuming the SVG is inside
            "div.vac-header-actions-buttons > button:nth-child(4)",
        ]

        # Try each selector
        for selector in selectors:
            try:
                # Playwright's locator can handle CSS and XPath directly.
                # It also automatically pierces shadow DOMs.
                locator = page.locator(selector)

                # Check if the element exists and is visible/enabled
                if locator.is_visible() and locator.is_enabled():
                    # Scroll into view and click, forcing the click if necessary
                    locator.scroll_into_view_if_needed()
                    locator.click(force=True)
                    print(f"Successfully clicked filter button with selector: {selector}")
                    return True
                else:
                    print(f"Locator found for '{selector}' but element not visible or enabled. Trying next selector.")

            except Exception as e:
                print(f"Failed with selector '{selector}': {str(e)}. Trying next selector.")
                continue

        # Fallback JavaScript approach if Playwright's direct click fails
        print("Could not click using Playwright locators. Trying JavaScript fallback...")
        js_selector = "document.querySelector(\"#privacy-web-chat\").shadowRoot.querySelector(\"div > div > div > div.vac-rooms-container.vac-rooms-container-full > div.vac-wrapper-header-actions > div.vac-header-actions > div.vac-header-actions-buttons > button:nth-child(4) > svg\")"

        fallback_clicked = page.evaluate(f'''() => {{
            const element = {js_selector};
            if (element) {{
                // Force visibility and click using JavaScript
                element.style.opacity = '1';
                element.style.visibility = 'visible';
                element.style.display = 'block';
                element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                element.click();
                return true;
            }}
            return false;
        }}''')

        if fallback_clicked:
            print("Successfully clicked filter button using JavaScript fallback!")
            return True

        print("Could not find or click the filter messages button using any method.")
        return False

    except Exception as e:
        print(f"Error in click_to_filter_messages_by: {str(e)}")
        return False

def click_to_filter_by_non_read_messages(page):
    """
    Attempt to find and click the 'Não lidas' (Unread) filter option.
    """
    try:
        # List of selectors to try for the 'Não lidas' span
        selectors = [
            # Direct CSS selector for the span element
            "#el-id-2096-34 > div > div:nth-child(1) > div > swiper-container > swiper-slide.swiper-slide.swiper-slide-active > span > span > div > span",
            # JavaScript path for the span element (within shadowRoot)
            "document.querySelector(\"#privacy-web-chat\").shadowRoot.querySelector(\"#el-id-2096-34 > div > div:nth-child(1) > div > swiper-container > swiper-slide.swiper-slide.swiper-slide-active > span > span > div > span\")",
            # XPath for the span element (within shadowRoot context)
            "//*[@id=\"el-id-2096-34\"]/div/div[1]/div/swiper-container/swiper-slide[1]/span/span/div/span",
            # Alternative: locate by text content if direct selectors fail
            "text=Não lidas"
        ]

        # Try each selector
        for selector in selectors:
            try:
                # Handle different selector types
                if selector.startswith("document.querySelector"):
                    # JavaScript selector (handles shadow DOM)
                    element_clicked = page.evaluate(f'''() => {{
                        const element = {selector};
                        if (element) {{
                            element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            element.click();
                            return true;
                        }}
                        return false;
                    }}''')

                    if element_clicked:
                        return True

                elif selector.startswith('/'):
                    # XPath selector
                    # For XPath within shadow DOM, Playwright's locator might need the full path
                    # or you might need to evaluate JS to get the shadowRoot first.
                    xpath_elements = page.locator(f"xpath={selector}")
                    if xpath_elements.count() > 0:
                        try:
                            # Force visibility (using the shadowRoot context for evaluation)
                            page.evaluate(f'''(selector) => {{
                                const shadowHost = document.querySelector("#privacy-web-chat");
                                if (shadowHost && shadowHost.shadowRoot) {{
                                    const element = shadowHost.shadowRoot.evaluate(
                                        `{selector}`, 
                                        shadowHost.shadowRoot, 
                                        null, 
                                        XPathResult.FIRST_ORDERED_NODE_TYPE, 
                                        null
                                    ).singleNodeValue;
                                    if (element) {{
                                        element.style.opacity = '1';
                                        element.style.visibility = 'visible';
                                        element.style.display = 'block';
                                    }}
                                }}
                            }}''', selector)

                            # Scroll and click
                            xpath_elements.first.scroll_into_view_if_needed()
                            xpath_elements.first.click(force=True)
                            return True
                        except Exception as e:
                            print(f"XPath click failed: {str(e)}")

                elif selector.startswith('text='):
                    # Playwright's text locator
                    text_elements = page.locator(selector)
                    if text_elements.count() > 0:
                        try:
                            text_elements.first.scroll_into_view_if_needed()
                            text_elements.first.click(force=True)
                            return True
                        except Exception as e:
                            print(f"Text locator click failed: {str(e)}")

                else:
                    # CSS selector (assumes it's directly accessible or Playwright handles shadow DOM)
                    css_elements = page.locator(selector)
                    if css_elements.count() > 0:
                        try:
                            # Force visibility (using the shadowRoot context for evaluation)
                            page.evaluate(f'''(selector) => {{
                                const shadowHost = document.querySelector("#privacy-web-chat");
                                if (shadowHost && shadowHost.shadowRoot) {{
                                    const element = shadowHost.shadowRoot.querySelector(selector);
                                    if (element) {{
                                        element.style.opacity = '1';
                                        element.style.visibility = 'visible';
                                        element.style.display = 'block';
                                    }}
                                }}
                            }}''', selector)

                            # Scroll and click
                            css_elements.first.scroll_into_view_if_needed()
                            css_elements.first.click(force=True)
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")

            except Exception as e:
                print(f"Failed with 'Não lidas' selector {selector}: {str(e)}")
                continue

        print("Could not find or click the 'Não lidas' filter option using any method.")
        return False

    except Exception as e:
        print(f"Error in click_to_filter_by_non_read_messages: {str(e)}")
        return False

def click_to_filter_by_older_messages(page):
    """
    Attempt to find and click the 'Mais antigas' (Older messages) filter option.
    """
    try:
        # List of selectors to try for the 'Mais antigas' span
        selectors = [
            # Direct CSS selector for the span element
            "#el-id-2096-34 > div > div:nth-child(3) > div > div > swiper-container > swiper-slide.swiper-slide.swiper-slide-next > span > span > div > span",
            # JavaScript path for the span element (within shadowRoot)
            "document.querySelector(\"#privacy-web-chat\").shadowRoot.querySelector(\"#el-id-2096-34 > div > div:nth-child(3) > div > div > swiper-container > swiper-slide.swiper-slide.swiper-slide-next > span > span > div > span\")",
            # XPath for the span element (within shadowRoot context)
            "//*[@id=\"el-id-2096-34\"]/div/div[3]/div/div/swiper-container/swiper-slide[2]/span/span/div/span",
            # Alternative: locate by text content if direct selectors fail
            "text=Mais antigas"
        ]

        # Try each selector
        for selector in selectors:
            try:
                # Handle different selector types
                if selector.startswith("document.querySelector"):
                    # JavaScript selector (handles shadow DOM)
                    # The selector string is already a valid JS expression here
                    element_clicked = page.evaluate(f'''() => {{
                        const element = {selector};
                        if (element) {{
                            element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            element.click();
                            return true;
                        }}
                        return false;
                    }}''')

                    if element_clicked:
                        return True

                elif selector.startswith('/'):
                    # XPath selector
                    xpath_elements = page.locator(f"xpath={selector}")
                    if xpath_elements.count() > 0:
                        try:
                            # Force visibility (using the shadowRoot context for evaluation)
                            page.evaluate(f'''(xpathSelector) => {{
                                const shadowHost = document.querySelector("#privacy-web-chat");
                                if (shadowHost && shadowHost.shadowRoot) {{
                                    const element = shadowHost.shadowRoot.ownerDocument.evaluate(
                                        xpathSelector, 
                                        shadowHost.shadowRoot, 
                                        null, 
                                        XPathResult.FIRST_ORDERED_NODE_TYPE, 
                                        null
                                    ).singleNodeValue;
                                    if (element) {{
                                        element.style.opacity = '1';
                                        element.style.visibility = 'visible';
                                        element.style.display = 'block';
                                    }}
                                }}
                            }}''', selector) # Pass selector as an argument to the JS function

                            # Scroll and click
                            xpath_elements.first.scroll_into_view_if_needed()
                            xpath_elements.first.click(force=True)
                            return True
                        except Exception as e:
                            print(f"XPath click failed: {str(e)}")

                elif selector.startswith('text='):
                    # Playwright's text locator
                    text_elements = page.locator(selector)
                    if text_elements.count() > 0:
                        try:
                            text_elements.first.scroll_into_view_if_needed()
                            text_elements.first.click(force=True)
                            return True
                        except Exception as e:
                            print(f"Text locator click failed: {str(e)}")

                else:
                    # CSS selector (assumes it's directly accessible or Playwright handles shadow DOM)
                    css_elements = page.locator(selector)
                    if css_elements.count() > 0:
                        try:
                            # Force visibility (using the shadowRoot context for evaluation)
                            page.evaluate(f'''(cssSelector) => {{
                                const shadowHost = document.querySelector("#privacy-web-chat");
                                if (shadowHost && shadowHost.shadowRoot) {{
                                    const element = shadowHost.shadowRoot.querySelector(cssSelector);
                                    if (element) {{
                                        element.style.opacity = '1';
                                        element.style.visibility = 'visible';
                                        element.style.display = 'block';
                                    }}
                                }}
                            }}''', selector) # Pass selector as an argument to the JS function

                            # Scroll and click
                            css_elements.first.scroll_into_view_if_needed()
                            css_elements.first.click(force=True)
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")

            except Exception as e:
                print(f"Failed with 'Mais antigas' selector {selector}: {str(e)}")
                continue

        print("Could not find or click the 'Mais antigas' filter option using any method.")
        return False

    except Exception as e:
        print(f"Error in click_to_filter_by_older_messages: {str(e)}")
        return False

def click_on_aplicar_button(page):
    """
    Attempt to find and click the 'Aplicar' (Apply) button.
    """
    try:
        # List of selectors to try for the 'Aplicar' span/button
        selectors = [
            # Direct CSS selector for the span element within the button
            "#el-id-2096-34 > div > span > button > span",
            # JavaScript path for the span element (within shadowRoot)
            "document.querySelector(\"#privacy-web-chat\").shadowRoot.querySelector(\"#el-id-2096-34 > div > span > button > span\")",
            # XPath for the span element (within shadowRoot context)
            "//*[@id=\"el-id-2096-34\"]/div/span/button/span",
            # Alternative: locate the button by its text content
            "text=Aplicar"
        ]

        # Try each selector
        for selector in selectors:
            try:
                # Handle different selector types
                if selector.startswith("document.querySelector"):
                    # JavaScript selector (handles shadow DOM)
                    # The selector string is already a valid JS expression here
                    element_clicked = page.evaluate(f'''() => {{
                        const element = {selector};
                        if (element) {{
                            // Click the parent button if the span itself is not directly clickable
                            const clickableParent = element.closest('button');
                            const targetElement = clickableParent || element;
                            targetElement.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            targetElement.click();
                            return true;
                        }}
                        return false;
                    }}''')

                    if element_clicked:
                        return True

                elif selector.startswith('/'):
                    # XPath selector
                    xpath_elements = page.locator(f"xpath={selector}")
                    if xpath_elements.count() > 0:
                        try:
                            # Force visibility (using the shadowRoot context for evaluation)
                            page.evaluate(f'''(xpathSelector) => {{
                                const shadowHost = document.querySelector("#privacy-web-chat");
                                if (shadowHost && shadowHost.shadowRoot) {{
                                    const element = shadowHost.shadowRoot.ownerDocument.evaluate(
                                        xpathSelector, 
                                        shadowHost.shadowRoot, 
                                        null, 
                                        XPathResult.FIRST_ORDERED_NODE_TYPE, 
                                        null
                                    ).singleNodeValue;
                                    if (element) {{
                                        element.style.opacity = '1';
                                        element.style.visibility = 'visible';
                                        element.style.display = 'block';
                                    }}
                                }}
                            }}''', selector) # Pass selector as an argument to the JS function

                            # Scroll and click the parent button if the span itself is not directly clickable
                            parent_button = xpath_elements.first.locator("xpath=..") # Get parent element (the button)
                            if parent_button.count() > 0:
                                parent_button.first.scroll_into_view_if_needed()
                                parent_button.first.click(force=True)
                            else: # Fallback to clicking the span directly
                                xpath_elements.first.scroll_into_view_if_needed()
                                xpath_elements.first.click(force=True)
                            return True
                        except Exception as e:
                            print(f"XPath click failed: {str(e)}")

                elif selector.startswith('text='):
                    # Playwright's text locator
                    text_elements = page.locator(selector)
                    if text_elements.count() > 0:
                        try:
                            text_elements.first.scroll_into_view_if_needed()
                            text_elements.first.click(force=True)
                            return True
                        except Exception as e:
                            print(f"Text locator click failed: {str(e)}")

                else:
                    # CSS selector (assumes it's directly accessible or Playwright handles shadow DOM)
                    css_elements = page.locator(selector)
                    if css_elements.count() > 0:
                        try:
                            # Force visibility (using the shadowRoot context for evaluation)
                            page.evaluate(f'''(cssSelector) => {{
                                const shadowHost = document.querySelector("#privacy-web-chat");
                                if (shadowHost && shadowHost.shadowRoot) {{
                                    const element = shadowHost.shadowRoot.querySelector(cssSelector);
                                    if (element) {{
                                        element.style.opacity = '1';
                                        element.style.visibility = 'visible';
                                        element.style.display = 'block';
                                    }}
                                }}
                            }}''', selector) # Pass selector as an argument to the JS function

                            # Scroll and click the parent button if the span itself is not directly clickable
                            parent_button = css_elements.first.locator("xpath=..") # Get parent element (the button)
                            if parent_button.count() > 0:
                                parent_button.first.scroll_into_view_if_needed()
                                parent_button.first.click(force=True)
                            else: # Fallback to clicking the span directly
                                css_elements.first.scroll_into_view_if_needed()
                                css_elements.first.click(force=True)
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")

            except Exception as e:
                print(f"Failed with 'Aplicar' selector {selector}: {str(e)}")
                continue

        print("Could not find or click the 'Aplicar' button using any method.")
        return False

    except Exception as e:
        print(f"Error in click_on_aplicar_button: {str(e)}")
        return False

def click_on_unread_messages(page):
    """
    Attempt to find and click the 'Unread Messages' counter,
    but only if the count is 1 or more.
    This method handles elements within a shadow DOM automatically with Playwright.
    """
    try:
        # List of selectors to try for the unread messages counter
        # The ID #\36 543dd61aed8fcd345c858cf is dynamic, so we'll prioritize more stable selectors
        # if available, but will include the provided ones.
        selectors = [
            # Primary CSS selector provided, targeting the span directly
            "#\\36 543dd61aed8fcd345c858cf > div > div.wrapper-content-and-options > div.wrapper-options > div.d-flex.align-items-center.gap-1 > div > span.vac-text-unread-msg-counter",
            # XPath selector provided
            "//*[@id='6543dd61aed8fcd345c858cf']/div/div[2]/div[2]/div[2]/div/span",
            # More generic CSS selector for the span with the specific class
            "span.vac-text-unread-msg-counter",
            # CSS selector targeting the parent div of the span, then the span
            "div.d-flex.align-items-center.gap-1 > div > span.vac-text-unread-msg-counter",
        ]

        # Try each selector
        for selector in selectors:
            try:
                locator = page.locator(selector)

                # Check if the element exists and is visible
                if locator.is_visible():
                    # Get the text content and convert to integer
                    unread_count_text = locator.text_content()
                    if unread_count_text:
                        unread_count = int(unread_count_text)

                        if unread_count >= 1:
                            # Scroll into view and click, forcing the click if necessary
                            locator.scroll_into_view_if_needed()
                            locator.click(force=True)
                            print(f"Successfully clicked unread messages counter (count: {unread_count}) with selector: {selector}")
                            return True
                        else:
                            print(f"Unread messages counter found with count {unread_count}, which is less than 1. Not clicking.")
                            return False # Found the element, but condition not met
                    else:
                        print(f"Unread messages counter found for '{selector}' but text content is empty. Trying next selector.")
                else:
                    print(f"Locator found for '{selector}' but element not visible. Trying next selector.")

            except ValueError:
                print(f"Unread messages counter found for '{selector}' but text content '{unread_count_text}' is not a valid number. Trying next selector.")
            except Exception as e:
                print(f"Failed with selector '{selector}': {str(e)}. Trying next selector.")
                continue

        # Fallback JavaScript approach if Playwright's direct click fails
        print("Could not click using Playwright locators. Trying JavaScript fallback...")
        # Note: The JS path provided includes a dynamic ID. For robustness, consider a more generic JS selector
        # if the ID changes frequently. For now, using the provided one.
        js_selector = "document.querySelector(\"#privacy-web-chat\").shadowRoot.querySelector(\"#\\36 543dd61aed8fcd345c858cf > div > div.wrapper-content-and-options > div.wrapper-options > div.d-flex.align-items-center.gap-1 > div > span\")"

        fallback_clicked = page.evaluate(f'''() => {{
            const shadowHost = document.querySelector("#privacy-web-chat");
            if (!shadowHost || !shadowHost.shadowRoot) return false;

            const element = shadowHost.shadowRoot.querySelector("{js_selector.split('shadowRoot.querySelector(')[1].replace('")', '')}");
            if (element) {{
                const unreadCountText = element.textContent;
                if (unreadCountText && parseInt(unreadCountText) >= 1) {{
                    // Force visibility and click using JavaScript
                    element.style.opacity = '1';
                    element.style.visibility = 'visible';
                    element.style.display = 'block';
                    element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                    element.click();
                    return true;
                }}
            }}
            return false;
        }}''')

        if fallback_clicked:
            print("Successfully clicked unread messages counter using JavaScript fallback!")
            return True

        print("Could not find or click the unread messages counter using any method, or count was less than 1.")
        return False

    except Exception as e:
        print(f"Error in click_on_unread_messages: {str(e)}")
        return False

def right_click_on_first_message_and_scroll_down(page, num_page_downs=4, key_press_pause_time=2):
    """
    Right-clicks the first visible message/conversation item and then performs
    a specified number of 'PageDown' key presses to scroll down.
    It also handles closing a filter drawer if detected.
    Returns True if the action was successful, False otherwise.
    """
    try:
        # Selector for the chat rooms list container
        rooms_list_selector = "#rooms-list"
        # Selector for each room item within the list
        room_item_selector = f"{rooms_list_selector} > div.vac-room-item"
        # Selector for the filter drawer overlay that might be covering the screen
        filter_drawer_overlay_selector = "div.el-overlay[style*='display: block'] > div.vac-float-filter"
        filter_drawer_close_button_selector = "button.el-button.is-circle.vac-float-filter-close"

        # Check and close the filter drawer if it's visible
        filter_drawer_overlay = page.locator(filter_drawer_overlay_selector)
        if filter_drawer_overlay.is_visible():
            print("Filter drawer detected and visible. Attempting to close...")
            close_button = page.locator(filter_drawer_close_button_selector)
            if close_button.is_visible() and close_button.is_enabled():
                close_button.click(force=True)
                page.wait_for_selector(filter_drawer_overlay_selector, state='hidden', timeout=5000)
                print("Filter drawer closed successfully.")
            else:
                print("Filter drawer close button not found or not clickable.")
                page.keyboard.press("Escape")
                page.wait_for_timeout(1000)
                if filter_drawer_overlay.is_visible():
                    print("Failed to close filter drawer. Proceeding with caution.")

        # Find the first message item
        first_message_item = page.locator(room_item_selector).first

        # Wait for the first message item to be visible
        first_message_item.wait_for(state='visible', timeout=10000)

        if not first_message_item.is_visible():
            print("No message items found to right-click.")
            return False

        print("Right-clicking the first message item...")
        first_message_item.click(button="right", force=True)
        page.wait_for_timeout(500) # Small pause after right-click

        print(f"Performing {num_page_downs} 'PageDown' key presses...")
        for i in range(num_page_downs):
            page.keyboard.press("PageDown")
            print(f"PageDown press {i + 1}/{num_page_downs} completed.")
            time.sleep(key_press_pause_time) # Wait between key presses

        # After scrolling, count the total messages found
        total_messages_found = page.locator(room_item_selector).count()
        print(f"After right-click and {num_page_downs} PageDown presses, found a total of {total_messages_found} messages/conversations.")

        return True

    except Exception as e:
        print(f"An error occurred during right-click and PageDown presses: {e}")
        return False

def messages_found_counter(page):
    """
    Counts and prints the number of visible "room items" (messages/conversations)
    in the chat rooms list and returns this number.
    """
    messages_found = 0
    try:
        # Selector for the rooms list (the parent container)
        rooms_list_selector = "#rooms-list"

        # Selector for each room item within the list
        room_item_selector = f"{rooms_list_selector} > div.vac-room-item"

        # Try to find the rooms list container first
        rooms_list_locator = page.locator(rooms_list_selector)
        if not rooms_list_locator.is_visible():
            print(f"The chat rooms list container '{rooms_list_selector}' is not visible.")
            return 0

        # Find all visible room items within the container
        room_items = page.locator(room_item_selector)
        messages_found = room_items.count()

        if messages_found > 0:
            print(f"Found {messages_found} messages/conversations in the list.")
        else:
            print("No messages/conversations were found in the list.")

        return messages_found

    except Exception as e:
        print(f"An error occurred while trying to count messages/conversations: {e}")
        return 0

from playwright.sync_api import sync_playwright
import time

from playwright.sync_api import sync_playwright
import time

from playwright.sync_api import sync_playwright
import time

from playwright.sync_api import sync_playwright
import time

from playwright.sync_api import sync_playwright
import time

from playwright.sync_api import sync_playwright
import time

def access_and_get_the_last_unread_messages(page):
    """
    Accesses the first message item with unread messages, extracts the unread count,
    clicks the message to open the conversation, then retrieves the specified
    number of latest messages by scrolling up the chat container within the Shadow DOM.
    This method performs the operation once.
    Returns a list of the collected messages or an empty list if unsuccessful.
    """
    messages_list = []
    number_of_last_messages_to_get = 0

    try:
        # Selectors for the chat rooms list and individual items
        rooms_list_selector = "#rooms-list"
        room_item_selector = f"{rooms_list_selector} > div.vac-room-item"

        # Selector for the unread message counter within a room item
        unread_counter_selector = "span.vac-text-unread-msg-counter"

        # --- UPDATED SELECTORS FOR OPEN CHAT WITHIN SHADOW DOM ---
        # Host element for the Shadow DOM
        shadow_host_selector = "#privacy-web-chat"

        # The main container for all messages in an open chat, now inside Shadow DOM
        # Playwright can chain locators to pierce shadow DOMs implicitly if the parent is correctly located.
        chat_messages_container_selector_in_shadow = "#messages-list" 

        # Selector for a single message wrapper, which contains the text.
        message_wrapper_selector = "div.vac-message-wrapper-msg"

        # Selector for the actual message text span within the message wrapper.
        message_text_span_selector_in_shadow = f"{message_wrapper_selector} div.vac-format-container.quote-adjustment > span"
        # --- END UPDATED SELECTORS ---

        # Check and close the filter drawer if it's visible (reusing logic)
        filter_drawer_overlay_selector = "div.el-overlay[style*='display: block'] > div.vac-float-filter"
        filter_drawer_close_button_selector = "button.el-button.is-circle.vac-float-filter-close"
        filter_drawer_overlay = page.locator(filter_drawer_overlay_selector)
        if filter_drawer_overlay.is_visible():
            print("Filter drawer detected and visible. Attempting to close...")
            close_button = page.locator(filter_drawer_close_button_selector)
            if close_button.is_visible() and close_button.is_enabled():
                close_button.click(force=True)
                page.wait_for_selector(filter_drawer_overlay_selector, state='hidden', timeout=5000)
                print("Filter drawer closed successfully.")
            else:
                print("Filter drawer close button not found or not clickable. Trying ESC.")
                page.keyboard.press("Escape")
                page.wait_for_timeout(1000)
                if filter_drawer_overlay.is_visible():
                    print("Failed to close filter drawer. Proceeding with caution.")

        # Find all room items
        all_room_items = page.locator(room_item_selector)
        num_room_items = all_room_items.count()

        if num_room_items == 0:
            print("No chat room items found.")
            return []

        first_unread_message_item = None
        for i in range(num_room_items):
            room_item = all_room_items.nth(i)
            unread_counter = room_item.locator(unread_counter_selector)

            if unread_counter.is_visible():
                unread_count_text = unread_counter.text_content()
                if unread_count_text and int(unread_count_text) >= 1:
                    number_of_last_messages_to_get = int(unread_count_text)
                    first_unread_message_item = room_item
                    print(f"Found first unread message item with {number_of_last_messages_to_get} unread messages.")
                    break

        if not first_unread_message_item:
            print("No unread message items found or counter is zero.")
            return []

        print("Clicking on the first unread message item...")
        first_unread_message_item.click()
        page.wait_for_timeout(3000) # Wait for conversation to load

        # Now, locate the chat container within the Shadow DOM
        # This locator will pierce the shadow DOM to find #messages-list
        chat_container = page.locator(shadow_host_selector).locator(chat_messages_container_selector_in_shadow)

        # Wait for the chat container to be visible
        chat_container.wait_for(state='visible', timeout=10000)
        print(f"Chat messages container '{chat_messages_container_selector_in_shadow}' is visible within Shadow DOM.")

        print(f"Attempting to retrieve the last {number_of_last_messages_to_get} messages...")

        # Get all message text elements initially
        # These are also within the shadow DOM, so we chain locators
        all_message_text_elements = chat_container.locator(message_text_span_selector_in_shadow)

        # If there are fewer messages than requested, adjust the count
        current_visible_messages_count = all_message_text_elements.count()
        if number_of_last_messages_to_get > current_visible_messages_count:
            print(f"Requested {number_of_last_messages_to_get} messages, but only {current_visible_messages_count} are initially visible. Adjusting to {current_visible_messages_count}.")
            number_of_last_messages_to_get = current_visible_messages_count

        # Retrieve messages starting from the latest (bottom of the chat)
        for i in range(number_of_last_messages_to_get):
            # Re-locate all message text elements in case the DOM changes or new messages load
            all_message_text_elements = chat_container.locator(message_text_span_selector_in_shadow)

            if all_message_text_elements.count() > 0:
                # Get the message text element from the end (latest message)
                # We need to adjust index for reverse iteration
                message_index = all_message_text_elements.count() - 1 - i
                if message_index < 0:
                    print(f"No more message text elements to process after collecting {len(messages_list)} messages.")
                    break

                current_message_element = all_message_text_elements.nth(message_index)

                message_text = current_message_element.text_content()
                if message_text:
                    messages_list.insert(0, message_text.strip()) # Insert at the beginning to keep chronological order
                    print(f"Collected message {i+1}: '{message_text.strip()}'")
                else:
                    print(f"Could not get text for message {i+1} from element at index {message_index}.")
            else:
                print(f"No more message text elements found to collect after {i} messages.")
                break

            # Scroll up the chat container to reveal older messages if more are needed
            if i < number_of_last_messages_to_get - 1:
                # Corrected page.evaluate call: pass arguments as a single dictionary or list
                page.evaluate('''(args) => {
                    const host = document.querySelector(args.hostSelector);
                    if (host && host.shadowRoot) {
                        const element = host.shadowRoot.querySelector(args.containerSelector);
                        if (element) {
                            element.scrollTop -= 500; // Scroll up by 500 pixels
                            if (element.scrollTop < 0) element.scrollTop = 0; // Don't scroll past top
                        }
                    }
                }''', {'hostSelector': shadow_host_selector, 'containerSelector': chat_messages_container_selector_in_shadow})
                page.wait_for_timeout(1000) # Small pause for scroll and content load

        print(f"Finished collecting messages. Total collected: {len(messages_list)}")
        print("Collected messages:", messages_list)
        return messages_list

    except Exception as e:
        print(f"An error occurred in access_and_get_the_last_unread_messages: {e}")
        return []





def click_on_menu(page):
    """
    Attempt to find and click the 'Menu' button (avatar) using multiple approaches.
    Prioritizes the specific avatar button identified and handles Shadow DOM if present.
    """
    print("Attempting to click the 'Menu' button...")
    try:
        # Define specific selectors for the avatar button you identified
        # These are for the parent button or the image itself, which Playwright can often click
        avatar_selectors = [
            # 1. Direct CSS selector for the parent button of the avatar image
            "#privacy-header--avatar-button",
            # 2. CSS selector for the image itself (Playwright can often click images)
            "#privacy-header--avatar-button > img",
            # 3. XPath for the parent button
            "//*[@id='privacy-header--avatar-button']",
            # 4. XPath for the image itself
            "//*[@id='privacy-header--avatar-button']/img",
            # 5. More generic CSS for the image based on attributes
            "img.privacy-header--avatar-img[src*='media/avatar/']",
            # 6. More generic XPath for the image based on attributes
            "//img[contains(@src, 'media/avatar/') and @class='privacy-header--avatar-img']"
        ]

        # Define selectors for a potential Shadow DOM menu button, if it's a separate element
        # These are for the 'div > nav > div:nth-child(5)' inside a shadow root
        shadow_dom_menu_selectors = [
            "div > nav > div:nth-child(5)", # This is the internal selector for the shadow root
            "nav.menu div.menu__item:nth-child(5)",
            "nav.menu div.menu__item:last-child",
            "div.menu__item:has(span:text-is('Menu'))",
        ]

        # --- Phase 1: Try clicking the identified avatar button directly ---
        for selector in avatar_selectors:
            try:
                print(f"Trying avatar selector: {selector}")
                # Playwright's locator handles CSS and XPath automatically if prefixed
                locator = page.locator(selector)
                if locator.count() > 0:
                    # Use Playwright's built-in waiting and clicking capabilities
                    # force=True can help if Playwright thinks it's not interactable,
                    # but it's often better to ensure proper waits.
                    locator.first.scroll_into_view_if_needed()
                    locator.first.click(timeout=5000) # Add a timeout for the click operation
                    print(f"Successfully clicked avatar button with selector: {selector}")
                    return True
            except Exception as e:
                print(f"Failed to click avatar button with selector '{selector}': {str(e)}")
                # Continue to the next selector

        # --- Phase 2: Handle potential Shadow DOM menu if the avatar click didn't work ---
        # This assumes '#privacy-web-floatmenu' is the shadow host for a *different* menu
        print("Avatar button not found or clickable. Checking for Shadow DOM menu...")
        float_menu_host = page.locator("#privacy-web-floatmenu")
        if float_menu_host.count() > 0:
            print("Found potential shadow host: #privacy-web-floatmenu")
            # Execute JavaScript to access the shadowRoot and find the element within it
            # This is the most robust way to interact with Shadow DOM in Playwright/Selenium
            for internal_selector in shadow_dom_menu_selectors:
                try:
                    print(f"Trying Shadow DOM internal selector: {internal_selector}")
                    button_clicked = page.evaluate(f'''(host, selector) => {{
                        const shadowHost = host;
                        if (shadowHost && shadowHost.shadowRoot) {{
                            const button = shadowHost.shadowRoot.querySelector(selector);
                            if (button) {{
                                button.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                                button.click();
                                return true;
                            }}
                        }}
                        return false;
                    }}''', float_menu_host.element_handle(), internal_selector) # Pass element_handle for JS context

                    if button_clicked:
                        print(f"Successfully clicked Shadow DOM menu button with internal selector: {internal_selector}")
                        return True
                except Exception as e:
                    print(f"Failed to click Shadow DOM menu button with internal selector '{internal_selector}': {str(e)}")
                    # Continue to the next internal selector

        # --- Phase 3: Fallback for other generic "Menu" elements (less specific) ---
        print("Shadow DOM menu not found or clickable. Trying generic text/image based fallbacks...")
        fallback_clicked = page.evaluate('''() => {
            // Try finding by img src/class (if not already covered by avatar_selectors)
            const avatarImgs = document.querySelectorAll('img.el-image__inner[src*="media/avatar/"]');
            for (const img of avatarImgs) {
                const parentDiv = img.closest('div.menu__item') || img.parentElement; // Get parent div or immediate parent
                if (parentDiv) {
                    parentDiv.scrollIntoView({behavior: 'smooth', block: 'center'});
                    parentDiv.click();
                    return true;
                }
            }

            // Try finding by text content "Menu"
            const menuItems = document.querySelectorAll('div.menu__item, span.text-menu');
            for (const item of menuItems) {
                if (item.textContent.trim() === 'Menu') {
                    item.scrollIntoView({behavior: 'smooth', block: 'center'});
                    item.click();
                    return true;
                }
            }
            return false;
        }''')

        if fallback_clicked:
            print("Successfully clicked Menu button using generic JavaScript fallback.")
            return True

        print("Could not find or click Menu button using any method.")
        return False

    except Exception as e:
        print(f"An unexpected error occurred in click_on_menu: {str(e)}")
        return False

def click_on_sair(page):
    """
    Attempt to find and click on the 'Sair' (logout) element.
    Handles Shadow DOM and multiple selector strategies.
    """
    try:
        # List of selectors to try (based on provided details)
        selectors = [
            # Shadow DOM JavaScript selector (most reliable for this page)
            'document.querySelector("#privacy-web-floatmenu").shadowRoot.querySelector("#el-id-1595-11 > div > div > div.submenu__options > div:nth-child(3) > div > section > div.others-options > div:nth-child(4) > div.font-medium.text-sm.option-header.d-flex.align-items-center.gap-2.mb-2 > span")',
            'document.querySelector("#privacy-web-floatmenu").shadowRoot.querySelector("span:contains(\'Sair\')")',  # Text-based
            'document.querySelector("#privacy-web-floatmenu").shadowRoot.querySelector("div.submenu__options > div:nth-child(3) > div > section > div.others-options > div:nth-child(4) > div > span")',
            # Direct CSS selectors (if Shadow DOM is not present)
            "#el-id-1595-11 > div > div > div.submenu__options > div:nth-child(3) > div > section > div.others-options > div:nth-child(4) > div.font-medium.text-sm.option-header.d-flex.align-items-center.gap-2.mb-2 > span",
            "span:contains('Sair')",  # Text-based (may need library support or JS for :contains)
            "div.font-medium.text-sm.option-header.d-flex.align-items-center.gap-2.mb-2 > span",
            # Generalized for dynamic IDs and classes
            "[id^='el-id-'] > div > div > div.submenu__options > div:nth-child(3) > div > section > div.others-options > div:nth-child(4) > div > span",
            # XPath (may not work with Shadow DOM)
            "//*[@id='el-id-1595-11']/div/div/div[1]/div[2]/div/section/div[2]/div[4]/div[1]/span",
            "//span[contains(text(), 'Sair')]",
            "//div[contains(@class, 'submenu__options')]//span[contains(text(), 'Sair')]"
        ]

        # Try each selector
        for selector in selectors:
            try:
                # Handle different selector types
                if selector.startswith("document.querySelector"):
                    # JavaScript selector (handles shadow DOM)
                    clicked = page.evaluate(f'''() => {{
                        try {{
                            const element = {selector};
                            if (element) {{
                                element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                                element.focus();
                                element.click();
                                element.dispatchEvent(new Event('click', {{ bubbles: true }}));
                                return true;
                            }}
                        }} catch(e) {{
                            console.error('Error clicking sair:', e);
                        }}
                        return false;
                    }}''')
                    if clicked:
                        print("✓ Sair clicked successfully with Shadow DOM selector")
                        return True

                elif selector.startswith('/'):
                    # XPath selector
                    xpath_elements = page.locator(f"xpath={selector}")
                    if xpath_elements.count() > 0:
                        try:
                            # Force visibility
                            page.evaluate(f'''(selector) => {{
                                const element = document.evaluate(
                                    `{selector}`,
                                    document,
                                    null,
                                    XPathResult.FIRST_ORDERED_NODE_TYPE,
                                    null
                                ).singleNodeValue;
                                if (element) {{
                                    element.style.opacity = '1';
                                    element.style.visibility = 'visible';
                                    element.style.display = 'block';
                                }}
                            }}''', selector)
                            # Scroll and click
                            xpath_elements.first.scroll_into_view_if_needed()
                            xpath_elements.first.click()
                            print("✓ Sair clicked successfully with XPath")
                            return True
                        except Exception as e:
                            print(f"XPath click failed: {str(e)}")

                else:
                    # CSS selector
                    css_elements = page.locator(selector)
                    if css_elements.count() > 0:
                        try:
                            # Force visibility
                            page.evaluate(f'''(selector) => {{
                                const element = document.querySelector(selector);
                                if (element) {{
                                    element.style.opacity = '1';
                                    element.style.visibility = 'visible';
                                    element.style.display = 'block';
                                }}
                            }}''', selector)
                            # Scroll and click
                            css_elements.first.scroll_into_view_if_needed()
                            css_elements.first.click()
                            print("✓ Sair clicked successfully with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")

            except Exception as e:
                print(f"Failed with sair selector {selector}: {str(e)}")
                continue

        # Fallback JavaScript approach with comprehensive search
        print("Trying JavaScript fallback approach for sair click...")
        fallback_clicked = page.evaluate('''() => {
            // Try Shadow DOM first
            const shadowHost = document.querySelector("#privacy-web-floatmenu");
            if (shadowHost && shadowHost.shadowRoot) {
                // Try multiple selectors inside shadow DOM
                const shadowSelectors = [
                    '#el-id-1595-11 > div > div > div.submenu__options > div:nth-child(3) > div > section > div.others-options > div:nth-child(4) > div.font-medium.text-sm.option-header.d-flex.align-items-center.gap-2.mb-2 > span',
                    'span:contains("Sair")',
                    'div.submenu__options > div:nth-child(3) > div > section > div.others-options > div:nth-child(4) > div > span',
                    '[id^="el-id-"] > div > div > div.submenu__options > div:nth-child(3) > div > section > div.others-options > div:nth-child(4) > div > span'
                ];

                for (const selector of shadowSelectors) {
                    const shadowElement = shadowHost.shadowRoot.querySelector(selector);
                    if (shadowElement) {
                        shadowElement.scrollIntoView({behavior: 'smooth', block: 'center'});
                        shadowElement.focus();
                        shadowElement.click();
                        shadowElement.dispatchEvent(new Event('click', { bubbles: true }));
                        return true;
                    }
                }
            }

            // Try regular DOM as fallback
            const elementSelectors = [
                '#el-id-1595-11 > div > div > div.submenu__options > div:nth-child(3) > div > section > div.others-options > div:nth-child(4) > div.font-medium.text-sm.option-header.d-flex.align-items-center.gap-2.mb-2 > span',
                'span:contains("Sair")',
                'div.submenu__options > div:nth-child(3) > div > section > div.others-options > div:nth-child(4) > div > span',
                '[id^="el-id-"] > div > div > div.submenu__options > div:nth-child(3) > div > section > div.others-options > div:nth-child(4) > div > span'
            ];

            for (const selector of elementSelectors) {
                const elements = document.querySelectorAll(selector);
                for (const element of elements) {
                    if (element && element.offsetParent !== null) {
                        element.scrollIntoView({behavior: 'smooth', block: 'center'});
                        element.focus();
                        element.click();
                        element.dispatchEvent(new Event('click', { bubbles: true }));
                        return true;
                    }
                }
            }

            return false;
        }''')

        if fallback_clicked:
            print("✓ Sair clicked successfully using JavaScript fallback!")
            return True

        print("❌ Could not find or click on sair using any method.")
        return False

    except Exception as e:
        print(f"❌ Error in click_on_sair: {str(e)}")
        return False

def main():
    pw = None
    context = None
    page = None
    browser_process = None

    # ADIÇÃO: Definir user_data aqui para acessá-lo no finally (para limpeza)
    user_data = os.path.join(os.environ['LOCALAPPDATA'], r"Google\Chrome\User Data\Automation")

    # 2. Launch Browser via the Native Hook method
    try:
        pw, context, browser_process = open_chrome_in_privacy_login_page()
        page = context.pages[0]  # Grab the active Privacy board page
        print("✓ Browser launched successfully")
    except Exception as e:
        print(f"❌ Failed to launch or hook browser: {e}")
        cleanup(pw, context, browser_process)
        return

    # 3. Automation and Interaction
    try:
        print("Waiting for page load...")
        page.wait_for_load_state("domcontentloaded")

        # Fullscreen Mode
        try:
            import pyautogui
            pyautogui.press('f11')
            page.wait_for_timeout(3000)
        except ImportError:
            print("Warning: pyautogui not installed, skipping fullscreen")

        # region Try to insert username with retries
        print("\nAttempting to insert username...")
        max_retries = 3
        username_inserted = False

        for attempt in range(max_retries):
            print(f"Username attempt {attempt + 1}/{max_retries}")
            if insert_username(page):
                username_inserted = True
                break
            else:
                print(f"✗ Username attempt {attempt + 1} failed.")
                if attempt < max_retries - 1:
                    print("Waiting before next attempt...")
                    time.sleep(2)

        if not username_inserted:
            print("❌ Maybe you are already logged in!")

        time.sleep(2)
        # endregion

        # region Try to insert password with retries
        print("\nAttempting to insert password...")
        max_retries = 3
        password_inserted = False

        for attempt in range(max_retries):
            print(f"Password attempt {attempt + 1}/{max_retries}")
            if insert_password(page):
                password_inserted = True
                break
            else:
                print(f"✗ Password attempt {attempt + 1} failed.")
                if attempt < max_retries - 1:
                    print("Waiting before next attempt...")
                    time.sleep(2)

        if not password_inserted:
            print("❌ Maybe you are already logged in!")

        time.sleep(2)
        # endregion

        # region Try to click the Entrar button with retries
        print("\nAttempting to click Entrar button...")
        max_retries = 3
        login_successful = False

        for attempt in range(max_retries):
            print(f"Attempt {attempt + 1}: Clicking Entrar...")
            if click_on_entrar_button(page):
                print("✓ Success: Entrar button clicked.")
                login_successful = True
                break
            else:
                print(f"✗ Attempt {attempt + 1} failed. Maybe you are already logged in!")
                if attempt < max_retries - 1:
                    time.sleep(2)

        # Wait for login to complete
        if login_successful:
            print("\nWaiting for login to complete...")
            page.wait_for_timeout(10000)
            print(f"Current URL: {page.url}")
            print("✓ Login process completed!")
        # endregion

        # Navigate to MyPrivacy chat page
        print("\nNavigating to MyPrivacy chat page...")
        page.goto("https://privacy.com.br/chat")
        page.wait_for_timeout(5000)
        print(f"✓ Navigated to: {page.url}")

        # region Try to click the filter messages button with retries
        max_retries = 3
        for attempt in range(max_retries):
            #print(f"\nAttempt {attempt + 1} to click filter messages button...")
            if click_to_filter_messages_by(page):
                #print("Successfully clicked filter messages button!")
                break
            else:
                print(f"Attempt {attempt + 1} failed.")
                if attempt < max_retries - 1:
                    print("Waiting before next attempt...")
                    page.wait_for_timeout(2000) # Wait for 2 seconds
        else:
            print("Failed to click filter messages button after all attempts.")

        page.wait_for_timeout(3000) # Wait for 3 seconds before closing
        # endregion Try to click the filter messages button with retries

        # region Try to click the 'Não lidas' filter option with retries
        max_retries = 3
        for attempt in range(max_retries):
            #print(f"\nAttempt {attempt + 1} to click 'Não lidas' filter option...")
            if click_to_filter_by_non_read_messages(page):
                #print("Successfully clicked 'Não lidas' filter option!")
                break
            else:
                print(f"Attempt {attempt + 1} failed.")
                if attempt < max_retries - 1:
                    print("Waiting before next attempt...")
                    page.wait_for_timeout(2000)
        else:
            print("Failed to click 'Não lidas' filter option after all attempts.")

        page.wait_for_timeout(3000)
        # endregion Try to click the 'Não lidas' filter option with retries

        # region Try to click the 'Mais antigas' filter option with retries
        max_retries = 3
        for attempt in range(max_retries):
            #print(f"\nAttempt {attempt + 1} to click 'Mais antigas' filter option...")
            if click_to_filter_by_older_messages(page):
                #print("Successfully clicked 'Mais antigas' filter option!")
                break
            else:
                print(f"Attempt {attempt + 1} failed.")
                if attempt < max_retries - 1:
                    print("Waiting before next attempt...")
                    page.wait_for_timeout(2000)
        else:
            print("Failed to click 'Mais antigas' filter option after all attempts.")

        page.wait_for_timeout(3000)
        # endregion Try to click the 'Mais antigas' filter option with retries

        # region Try to click the 'Aplicar' button with retries
        max_retries = 3
        for attempt in range(max_retries):
            #print(f"\nAttempt {attempt + 1} to click 'Aplicar' button...")
            if click_on_aplicar_button(page):
                #print("Successfully clicked 'Aplicar' button!")
                break
            else:
                print(f"Attempt {attempt + 1} failed.")
                if attempt < max_retries - 1:
                    print("Waiting before next attempt...")
                    page.wait_for_timeout(2000)
        else:
            print("Failed to click 'Aplicar' button after all attempts.")

        page.wait_for_timeout(7000)
        # endregion Try to click the 'Aplicar' button with retries

        # region Attempt to right-click first message and scroll down with retries
        max_retries = 3
        action_successful = False
        for attempt in range(max_retries):
            print(f"\nAttempt {attempt + 1} to right-click first message and scroll down...")
            # Perform 4 'PageDown' key presses with a 2-second pause between each
            action_successful = right_click_on_first_message_and_scroll_down(page, num_page_downs=4, key_press_pause_time=2) 
            if action_successful:
                print("Successfully performed right-click and PageDown presses!")
                break
            else:
                print(f"Attempt {attempt + 1} failed.")
                if attempt < max_retries - 1:
                    print("Waiting before next attempt...")
                    page.wait_for_timeout(2000) # Wait for 2 seconds
        else:
            print("Failed to right-click first message and scroll down after all attempts.")

        page.wait_for_timeout(3000) # Wait for 3 seconds before closing
        # endregion Attempt to right-click first message and scroll down with retries

        # region Attempt to count messages with retries
        max_retries = 3
        messages_found = 0
        for attempt in range(max_retries):
            print(f"\nAttempt {attempt + 1} to count messages...")
            messages_found = messages_found_counter(page)
            if messages_found > 0:
                print(f"Message count successful: {messages_found} messages found!")
                break
            else:
                print(f"Attempt {attempt + 1} failed or no messages were found.")
                if attempt < max_retries - 1:
                    print("Waiting before next attempt...")
                    page.wait_for_timeout(2000) # Wait for 2 seconds
        else:
            print("Failed to count messages after all attempts.")

        page.wait_for_timeout(3000) # Wait for 3 seconds before closing
        # endregion Attempt to count messages with retries



# ... (seu código existente até a linha onde collected_messages é preenchido) ...

        # region Attempt to access and get the last unread messages with retries
        max_retries = 3
        collected_messages = []
        for attempt in range(max_retries):
            print(f"\nAttempt {attempt + 1} to access and get the last unread messages...")
            collected_messages = access_and_get_the_last_unread_messages(page)
            if collected_messages: # If the list is not empty, it means messages were collected
                print(f"Successfully collected {len(collected_messages)} messages!")
                break
            else:
                print(f"Attempt {attempt + 1} failed or no unread messages were found/collected.")
                if attempt < max_retries - 1:
                    print("Waiting before next attempt...")
                    page.wait_for_timeout(2000) # Wait for 2 seconds
        else:
            print("Failed to access and get the last unread messages after all attempts.")

        page.wait_for_timeout(3000) # Wait for 3 seconds before closing
        # endregion Attempt to access and get the last unread messages with retries

        # --- NOVO CÓDIGO A PARTIR DAQUI ---

        # 1. Importar o pipeline de conversação do transformers
        

        # 2. Carregar o modelo de chatbot (se ainda não foi carregado)
        # É uma boa prática carregar o modelo uma vez no início do script se ele for usado várias vezes.
        # Para este exemplo, vamos carregá-lo aqui para demonstrar a integração.
        print("\nCarregando o modelo de chatbot...")
        try:
            chatbot_pipeline = pipeline("conversational", model="facebook/blenderbot-400M-distill")
            print("Modelo de chatbot carregado com sucesso.")
        except Exception as e:
            print(f"Erro ao carregar o modelo de chatbot: {e}")
            chatbot_pipeline = None # Garante que o pipeline não seja usado se houver erro

        if chatbot_pipeline and collected_messages:
            print("\nProcessando mensagens coletadas com o chatbot...")

            # Combine as mensagens coletadas em uma única string para o contexto inicial do chatbot
            # Ou processe cada mensagem individualmente, dependendo da sua necessidade.
            # Para um chat, geralmente queremos o contexto da conversa.
            full_conversation_context = "\n".join(collected_messages)

            # Crie um objeto Conversation com o contexto das mensagens
            # O BlenderBot é treinado para responder a uma entrada, então a última mensagem
            # ou um resumo pode ser mais eficaz como "pergunta" inicial.
            # Vamos usar a última mensagem como a entrada principal para o chatbot.
            initial_user_input = collected_messages[-1] if collected_messages else "Olá!"

            # Crie uma nova conversa para o chatbot
            # Você pode pré-preencher o histórico se quiser que o chatbot tenha mais contexto
            # além da última mensagem. Para BlenderBot, uma única entrada é comum.
            conversation = Conversation(initial_user_input)

            # Adicione as mensagens anteriores como parte do histórico se o modelo suportar
            # e se você quiser que ele considere mais do que apenas a última.
            # Para BlenderBot, a entrada principal é mais importante.
            # Se você quiser que o chatbot "leia" todas as mensagens, pode passá-las como uma única string.
            # Exemplo: conversation = Conversation("As mensagens são: " + full_conversation_context + "\nMinha resposta?")

            # Gerar uma resposta do chatbot
            try:
                chatbot_pipeline(conversation)
                chatbot_response = conversation.generated_responses[-1]
                print(f"\nResposta do Chatbot: {chatbot_response}")
                last_messages.append(chatbot_response) # Adiciona a resposta à lista global, se necessário
            except Exception as e:
                print(f"Erro ao gerar resposta do chatbot: {e}")
                chatbot_response = "Não consegui gerar uma resposta no momento."
        elif not chatbot_pipeline:
            print("Chatbot não foi carregado, pulando a geração de resposta.")
        else:
            print("Nenhuma mensagem coletada para o chatbot processar.")

        # --- FIM DO NOVO CÓDIGO ---

        page.wait_for_timeout(90000)

# ... (restante do seu código) ...


        # region Try to click the Menu button with retries
        max_retries = 3
        print(f"Starting attempts to click the Menu button (avatar). Max retries: {max_retries}")
        for attempt in range(max_retries):
            print(f"\n--- Attempt {attempt + 1} of {max_retries} ---")
            if click_on_menu(page):
                print("Successfully clicked Menu button after one or more attempts!")
                break # Exit the loop if successful
            else:
                print(f"Attempt {attempt + 1} failed to click the Menu button.")
                if attempt < max_retries - 1:
                    print("Waiting 1 second before the next attempt...")
                    page.wait_for_timeout(1000)  # Wait 1 second before retrying
                else:
                    print("This was the last attempt.")
        else:
            # This 'else' block executes if the loop completes without a 'break'
            print("Failed to click Menu button after all attempts.")

        print("Waiting for 3 seconds after menu interaction (or failure)...")
        page.wait_for_timeout(3000)
        # endregion

        # region Try to click on sair with retries
        print("\nAttempting to click on sair...")
        max_retries = 3
        sair_clicked = False

        for attempt in range(max_retries):
            print(f"Sair click attempt {attempt + 1}/{max_retries}")
            if click_on_sair(page):
                sair_clicked = True
                break
            else:
                print(f"✗ Sair click attempt {attempt + 1} failed.")
                if attempt < max_retries - 1:
                    print("Waiting before next attempt...")
                    time.sleep(2)

        if not sair_clicked:
            print("❌ Failed to click on sair after all attempts.")

        page.wait_for_timeout(5000)
        # endregion

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Cleanup: Close browser and resources (adjust based on your Playwright setup)
        try:
            if 'page' in locals() and page:
                page.close()
            if 'context' in locals() and context:
                context.close()
            if 'browser' in locals() and page:
                page.close()
            if 'browser' in locals() and browser_process:
                browser_process.close()
            print("Browser closed successfully.")
        except Exception as close_err:
            print(f"Error closing browser: {close_err}")

        # Exit the script (0 for success, as per search recommendations)
        sys.exit(0)    

if __name__ == "__main__":
    main()
