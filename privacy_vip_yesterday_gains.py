# Standard library imports
import os
import sys
from openpyxl import load_workbook, Workbook
import traceback
import time
import subprocess
from datetime import datetime, timedelta
import warnings

# Third-party imports
from playwright.sync_api import sync_playwright
from openpyxl.styles import Font

warnings.filterwarnings("ignore", category=UserWarning, module="playwright_stealth")
warnings.filterwarnings("ignore", category=DeprecationWarning)

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
    Attempt to find the username input field and insert 'hacksimone29@gmail.com'.
    Handles Shadow DOM and multiple selector strategies.
    """
    try:
        # List of selectors to try
        selectors = [
            # Shadow DOM JavaScript selector (most reliable for this page)
            'document.querySelector("#privacy-web-auth").shadowRoot.querySelector("input#floating-input-i4nch77")',
            'document.querySelector("#privacy-web-auth").shadowRoot.querySelector("input[type=\'email\']")',
            'document.querySelector("#privacy-web-auth").shadowRoot.querySelector("div > div > div:nth-child(1) > div > form > div:nth-child(1) input")',
            # Direct CSS selectors (if Shadow DOM is not present)
            "input#floating-input-i4nch77",
            "input.el-input__inner[type='email']",
            "input[type='email'][autocomplete='off']",
            "input[placeholder=' '][type='email']",
            # XPath (may not work with Shadow DOM)
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
                    }}''', "hacksimone29@gmail.com")
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
                            xpath_elements.first.fill("hacksimone29@gmail.com")
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
                            css_elements.first.fill("hacksimone29@gmail.com")
                            print("✓ Username inserted successfully with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector insert failed: {str(e)}")

            except Exception as e:
                print(f"Failed with username input selector {selector}: {str(e)}")
                continue

        # Fallback JavaScript approach with comprehensive search
        print("Trying JavaScript fallback approach for username input...")
        fallback_inserted = page.evaluate('''(text) => {
            // Try Shadow DOM first
            const shadowHost = document.querySelector("#privacy-web-auth");
            if (shadowHost && shadowHost.shadowRoot) {
                // Try multiple selectors inside shadow DOM
                const shadowSelectors = [
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
        }''', "hacksimone29@gmail.com")

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
    Attempt to find the password input field and insert '#Partiu15'.
    Handles Shadow DOM and multiple selector strategies.
    """
    try:
        # List of selectors to try
        selectors = [
            # Shadow DOM JavaScript selectors (most reliable for this page)
            'document.querySelector("#privacy-web-auth").shadowRoot.querySelector("input#floating-input-ue2x7hk")',
            'document.querySelector("#privacy-web-auth").shadowRoot.querySelector("input[type=\'password\']")',
            'document.querySelector("#privacy-web-auth").shadowRoot.querySelector("div > div > div:nth-child(1) > div > form > div.el-form-item.is-required.asterisk-left input")',
            'document.querySelector("#privacy-web-auth").shadowRoot.querySelector("div > div > div:nth-child(1) > div > form > div:nth-child(2) input")',
            # Direct CSS selectors (if Shadow DOM is not present)
            "input#floating-input-ue2x7hk",
            "input.el-input__inner[type='password']",
            "input[type='password'][autocomplete='off']",
            "input[placeholder=' '][type='password']",
            "div.el-form-item.is-required input[type='password']",
            # XPath (may not work with Shadow DOM)
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
                    }}''', "#Partiu15")
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
                            xpath_elements.first.fill("#Partiu15")
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
                            css_elements.first.fill("#Partiu15")
                            print("✓ Password inserted successfully with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector insert failed: {str(e)}")

            except Exception as e:
                print(f"Failed with password input selector {selector}: {str(e)}")
                continue

        # Fallback JavaScript approach with comprehensive search
        print("Trying JavaScript fallback approach for password input...")
        fallback_inserted = page.evaluate('''(text) => {
            // Try Shadow DOM first
            const shadowHost = document.querySelector("#privacy-web-auth");
            if (shadowHost && shadowHost.shadowRoot) {
                // Try multiple selectors inside shadow DOM
                const shadowSelectors = [
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
        }''', "#Partiu15")

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

def try_close_popup(page):
    selectors = [
        'button:has-text("Fechar")',
        'button[aria-label*="fechar" i]',
        ".close-icon",
        "#privacy-web-stories >> button",
        'button:has(.fa-xmark)',
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=2000):
                loc.click(timeout=5000)
                print("Popup fechado:", sel)
                time.sleep(1)
                return True
        except:
            continue
    return False

def click_extrato_tab(page):
    selectors = [
        '#tab-statement',
        '.el-tabs__item#tab-statement',
        'div[aria-controls="pane-statement"]',
        '//*[contains(text(),"Extrato")]',
        'button:has-text("Extrato")',
        '#privacy-web-myprivacy >> #tab-statement',
    ]
    for selector in selectors:
        try:
            if selector.startswith('//'):
                loc = page.locator(f"xpath={selector}")
            else:
                loc = page.locator(selector)
            if loc.count() > 0 and loc.is_visible(timeout=4000):
                loc.first.click(timeout=8000)
                print(f"Aba 'Extrato' clicada usando: {selector}")
                return True
        except:
            continue
    print("Não conseguiu localizar a aba Extrato")
    return False

def click_on_calendar(page):
    """
    Attempt to find and click the Calendar icon using multiple approaches,
    specifically handling elements inside Shadow DOM.
    """
    try:
        # List of selectors to try
        selectors = [
            # Direct CSS selector (Playwright usually pierces shadow roots with this)
            "i.el-icon.el-input__icon.el-range__icon",

            # Specific Path CSS
            "#pane-statement i.el-range__icon",

            # XPath
            "//*[@id='pane-statement']//i[contains(@class, 'el-range__icon')]",

            # The full JS Path provided (Direct Shadow DOM access)
            'document.querySelector("#privacy-web-myprivacy").shadowRoot.querySelector("#pane-statement > div > div:nth-child(1) > div > div.card-body > div.border-0 > div > div > div:nth-child(1) > div > i.el-icon.el-input__icon.el-range__icon")'
        ]

        for selector in selectors:
            try:
                # Handle the explicit Shadow Root JS selector
                if selector.startswith("document.querySelector"):
                    button_clicked = page.evaluate(f'''() => {{
                        const element = {selector};
                        if (element) {{
                            element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            element.click();
                            return true;
                        }}
                        return false;
                    }}''')
                    if button_clicked:
                        return True

                # Handle XPath
                elif selector.startswith('//') or selector.startswith('(*'):
                    xpath_elements = page.locator(f"xpath={selector}")
                    if xpath_elements.count() > 0:
                        xpath_elements.first.click(force=True)
                        return True

                # Handle Standard CSS (Playwright auto-pierces Shadow DOM)
                else:
                    css_elements = page.locator(selector)
                    if css_elements.count() > 0:
                        css_elements.first.click(force=True)
                        return True

            except Exception:
                continue

        # Fallback JavaScript approach specifically for Element UI / Shadow DOM
        fallback_clicked = page.evaluate('''() => {
            // Helper to find element inside shadow roots recursively
            const findInShadow = (selector) => {
                let result = null;
                const search = (root) => {
                    if (root.querySelector(selector)) {
                        result = root.querySelector(selector);
                        return;
                    }
                    const shadows = Array.from(root.querySelectorAll('*')).filter(el => el.shadowRoot);
                    for (let s of shadows) {
                        search(s.shadowRoot);
                        if (result) return;
                    }
                };
                search(document);
                return result;
            };

            const calendarIcon = findInShadow('i.el-range__icon') || findInShadow('.el-icon-date');
            if (calendarIcon) {
                calendarIcon.scrollIntoView({behavior: 'auto', block: 'center'});
                calendarIcon.click();
                return true;
            }
            return false;
        }''')

        return fallback_clicked

    except Exception as e:
        print(f"Error in click_on_calendar: {str(e)}")
        return False

def click_on_yesterday(page):
    """
    Calculates yesterday's date and clicks it twice in the Element calendar.
    Handles Shadow DOM and dynamic date selection.
    """
    try:
        # 1. Calculate Yesterday's Day Number
        yesterday = datetime.now() - timedelta(days=1)
        day_to_click = str(yesterday.day)

        # 2. JavaScript to find and click the specific day inside Shadow DOM
        click_script = f'''() => {{
            const findInShadow = (selector, root = document) => {{
                const el = root.querySelector(selector);
                if (el) return el;
                const shadows = Array.from(root.querySelectorAll('*')).filter(e => e.shadowRoot);
                for (let s of shadows) {{
                    const result = findInShadow(selector, s.shadowRoot);
                    if (result) return result;
                }}
                return null;
            }};

            // Find all available date cells
            const cells = Array.from(document.querySelectorAll('.el-date-table td.available'))
                          .concat(Array.from(findInShadow('.el-date-table') ?
                                  findInShadow('.el-date-table').querySelectorAll('td.available') : []));

            // Filter for the cell that matches yesterday's date
            const targetCell = cells.find(cell => {{
                const text = cell.innerText.trim();
                return text === "{day_to_click}";
            }});

            if (targetCell) {{
                targetCell.scrollIntoView({{behavior: 'auto', block: 'center'}});
                // Click twice for range selection (Start and End)
                targetCell.click();
                setTimeout(() => targetCell.click(), 200);
                return true;
            }}
            return false;
        }}'''

        success = page.evaluate(click_script)
        return success

    except Exception as e:
        print(f"Error in click_on_yesterday: {str(e)}")
        return False

def click_on_extrato_de_venda_next_page_button(page):
    """
    Finds and clicks the 'Next Page' button in the sales statement pagination.
    Handles Shadow DOM, checks for disabled states, and waits for UI transition.
    """
    try:
        # 1. Advanced JavaScript Evaluation for Shadow DOM and State
        js_click_script = '''() => {
            const findElementInShadows = (selector, root = document) => {
                const el = root.querySelector(selector);
                if (el) return el;
                const shadows = Array.from(root.querySelectorAll('*')).filter(e => e.shadowRoot);
                for (let s of shadows) {
                    const found = findElementInShadows(selector, s.shadowRoot);
                    if (found) return found;
                }
                return null;
            };

            const btn = findElementInShadows('button.btn-next');

            if (!btn) return "not_found";

            // Check if button is disabled via attribute, property, or CSS class
            const isReadonly = btn.disabled ||
                               btn.getAttribute('aria-disabled') === 'true' ||
                               btn.classList.contains('disabled');

            if (isReadonly) return "disabled";

            btn.scrollIntoView({behavior: 'auto', block: 'center'});
            btn.click();
            return "clicked";
        }'''

        result = page.evaluate(js_click_script)

        if result == "clicked":
            # Mandatory wait for the table to begin refreshing
            page.wait_for_timeout(2000)
            return True
        elif result == "disabled":
            print("Pagination: Reached the last page (Next button is disabled).")
            return False
        else:
            # Fallback to Playwright's native locators if JS didn't find it
            native_btn = page.locator("#pane-statement button.btn-next").first
            if native_btn.is_visible() and native_btn.is_enabled():
                native_btn.click(force=True)
                page.wait_for_timeout(2000)
                return True

            print("Pagination: Next page button not found.")
            return False

    except Exception as e:
        print(f"Error in click_on_extrato_de_venda_next_page_button: {str(e)}")
        return False

def click_on_gerar_relatorio_button(page):
    """
    Finds and clicks the 'Gerar Relatório' button in the sales statement.
    Handles Shadow DOM and checks for disabled state.
    """
    try:
        # List of selectors specific to the Gerar Relatório button
        selectors = [
            # 1. Direct CSS (Playwright automatically pierces Shadow DOM for CSS)
            "#pane-statement button.btn-primary:has-text('Gerar Relatório')",

            # 2. Your provided CSS Selector
            "#pane-statement > div > div:nth-child(1) > div > div.card-buttons > button",

            # 3. Text-based locator
            "button:has-text('Gerar Relatório')",

            # 4. Provided XPath
            "xpath=//*[@id='pane-statement']/div/div[1]/div/div[3]/button",

            # 5. Provided JS Path for Shadow DOM
            'document.querySelector("#privacy-web-myprivacy").shadowRoot.querySelector("#pane-statement > div > div:nth-child(1) > div > div.card-buttons > button")'
        ]

        for selector in selectors:
            try:
                # Handle JS Path specifically
                if selector.startswith("document.querySelector"):
                    clicked = page.evaluate(f'''() => {{
                        const btn = {selector};
                        if (btn && btn.getAttribute('aria-disabled') !== 'true') {{
                            btn.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            btn.click();
                            return true;
                        }}
                        return false;
                    }}''')
                    if clicked:
                        return True

                # Handle Standard Locators (CSS/XPath)
                else:
                    loc = page.locator(selector).first
                    if loc.count() > 0 and loc.is_visible():
                        # Force visibility and click
                        loc.scroll_into_view_if_needed()
                        loc.click(force=True)
                        return True
            except:
                continue

        # Global Shadow DOM Fallback
        fallback_clicked = page.evaluate('''() => {
            const findInShadow = (root = document) => {
                const buttons = Array.from(root.querySelectorAll('button'));
                const target = buttons.find(b => b.innerText.includes('Gerar Relatório'));
                if (target && target.getAttribute('aria-disabled') !== 'true') return target;

                const shadows = Array.from(root.querySelectorAll('*')).filter(e => e.shadowRoot);
                for (let s of shadows) {
                    const found = findInShadow(s.shadowRoot);
                    if (found) return found;
                }
                return null;
            };
            const btn = findInShadow();
            if (btn) {
                btn.click();
                return true;
            }
            return false;
        }''')

        return fallback_clicked

    except Exception as e:
        print(f"Error in click_on_gerar_relatorio_button: {str(e)}")
        return False

def click_on_confirmar_button(page):
    """
    Finds and clicks the 'Confirmar' button inside the 'Gerar Relatório' overlay dialog.
    Handles the el-overlay-dialog structure specifically.
    """
    try:
        # JavaScript to find and click the Confirmar button
        js_click_script = '''() => {
            const findButtonInDialog = (root = document) => {
                // 1. Find the dialog container by aria-label
                const dialog = root.querySelector('div[role="dialog"][aria-label="Gerar Relatório"]');

                if (dialog) {
                    // 2. Find the Confirmar button within that dialog's footer
                    const buttons = Array.from(dialog.querySelectorAll('button.btn-primary'));
                    const confirmBtn = buttons.find(b => b.innerText.includes('Confirmar'));

                    if (confirmBtn && confirmBtn.getAttribute('aria-disabled') !== 'true') {
                        confirmBtn.click();
                        return "clicked";
                    }
                    return confirmBtn ? "disabled" : "button_not_found";
                }

                // 2. If not found, recurse into shadow roots
                const shadows = Array.from(root.querySelectorAll('*')).filter(e => e.shadowRoot);
                for (let s of shadows) {
                    const result = findButtonInDialog(s.shadowRoot);
                    if (result !== "not_found") return result;
                }
                return "not_found";
            };

            return findButtonInDialog();
        }'''

        result = page.evaluate(js_click_script)

        if result == "clicked":
            return True
        elif result == "disabled":
            print("Confirmar button is disabled (check if form fields are filled).")
            return False

        # 3. Native Playwright Fallback
        try:
            confirm_loc = page.get_by_role("dialog", name="Gerar Relatório").get_by_role("button", name="Confirmar")
            if confirm_loc.is_visible():
                confirm_loc.click(force=True)
                return True
        except:
            pass

        print("Could not find the 'Gerar Relatório' confirmation dialog.")
        return False

    except Exception as e:
        print(f"Error in click_on_confirmar_button: {str(e)}")
        return False

def click_on_menu(page):
    """
    Click the menu button (avatar/profile image) using multiple approaches.
    Handles shadow DOM and tries various selector strategies.
    Uses Playwright synchronous API.
    """
    try:
        # List of selectors to try in order of preference
        selectors = [
            # Shadow DOM JavaScript path (most reliable for this case)
            {
                'type': 'shadow_js',
                'selector': 'document.querySelector("#privacy-web-floatmenu").shadowRoot.querySelector("div > nav > div:nth-child(5) > div > img")'
            },
            # XPath
            {
                'type': 'xpath',
                'selector': '//*[@id="privacy-web-floatmenu"]//div/nav/div[5]/div/img'
            },
            # CSS selectors (alternative approaches)
            {
                'type': 'css',
                'selector': 'img.el-image__inner[src*="avatar"]'
            },
            {
                'type': 'css',
                'selector': 'nav div:nth-child(5) img'
            }
        ]

        # Try each selector approach
        for selector_config in selectors:
            try:
                selector_type = selector_config['type']
                selector = selector_config['selector']

                if selector_type == 'shadow_js':
                    # JavaScript approach for Shadow DOM
                    button_clicked = page.evaluate(f'''() => {{
                        try {{
                            const element = {selector};
                            if (element) {{
                                element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                                element.click();
                                return true;
                            }}
                        }} catch (e) {{
                            console.error('Shadow DOM click error:', e);
                        }}
                        return false;
                    }}''')

                    if button_clicked:
                        print(f"✓ Successfully clicked menu using Shadow DOM JS")
                        return True

                elif selector_type == 'xpath':
                    # XPath approach
                    try:
                        xpath_locator = page.locator(f"xpath={selector}")
                        count = xpath_locator.count()
                        if count > 0:
                            xpath_locator.first.scroll_into_view_if_needed()
                            xpath_locator.first.click(force=True, timeout=3000)
                            print(f"✓ Successfully clicked menu using XPath")
                            return True
                    except Exception as xpath_error:
                        print(f"✗ XPath click failed: {str(xpath_error)}")

                elif selector_type == 'css':
                    # CSS selector approach
                    try:
                        css_locator = page.locator(selector)
                        count = css_locator.count()
                        if count > 0:
                            css_locator.first.scroll_into_view_if_needed()
                            css_locator.first.click(force=True, timeout=3000)
                            print(f"✓ Successfully clicked menu using CSS: {selector}")
                            return True
                    except Exception as css_error:
                        print(f"✗ CSS click failed: {str(css_error)}")

            except Exception as e:
                print(f"✗ Failed with selector {selector}: {str(e)}")
                continue

        # Fallback: comprehensive JavaScript approach
        print("Trying JavaScript fallback methods...")
        fallback_clicked = page.evaluate('''() => {
            // Strategy 1: Shadow DOM access
            try {
                const floatMenu = document.querySelector('#privacy-web-floatmenu');
                if (floatMenu && floatMenu.shadowRoot) {
                    const menuImg = floatMenu.shadowRoot.querySelector('div > nav > div:nth-child(5) > div > img');
                    if (menuImg) {
                        menuImg.scrollIntoView({behavior: 'smooth', block: 'center'});
                        menuImg.click();
                        return true;
                    }

                    // Try clicking parent div instead
                    const menuDiv = floatMenu.shadowRoot.querySelector('div > nav > div:nth-child(5)');
                    if (menuDiv) {
                        menuDiv.scrollIntoView({behavior: 'smooth', block: 'center'});
                        menuDiv.click();
                        return true;
                    }
                }
            } catch (e) {
                console.error('Shadow DOM fallback error:', e);
            }

            // Strategy 2: Find by avatar image source
            try {
                const avatarImages = document.querySelectorAll('img[src*="avatar"]');
                for (const img of avatarImages) {
                    if (img.classList.contains('el-image__inner')) {
                        img.scrollIntoView({behavior: 'smooth', block: 'center'});
                        img.click();
                        return true;
                    }
                }
            } catch (e) {
                console.error('Avatar image search error:', e);
            }

            // Strategy 3: Find menu items and click the 5th one
            try {
                const menuItems = document.querySelectorAll('nav div');
                if (menuItems.length >= 5) {
                    const fifthItem = Array.from(menuItems).filter(item => 
                        item.querySelector('img')
                    )[4];
                    if (fifthItem) {
                        fifthItem.scrollIntoView({behavior: 'smooth', block: 'center'});
                        fifthItem.click();
                        return true;
                    }
                }
            } catch (e) {
                console.error('Menu items search error:', e);
            }

            // Strategy 4: Direct click on any avatar image
            try {
                const allImages = document.querySelectorAll('img');
                for (const img of allImages) {
                    if (img.src && img.src.includes('avatar')) {
                        img.scrollIntoView({behavior: 'smooth', block: 'center'});
                        img.click();
                        return true;
                    }
                }
            } catch (e) {
                console.error('Direct avatar click error:', e);
            }

            return false;
        }''')

        if fallback_clicked:
            print("✓ Successfully clicked menu using JavaScript fallback")
            return True

        print("✗ Could not find or click menu button using any method")
        return False

    except Exception as e:
        print(f"✗ Error in click_on_menu: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def click_to_logoff(page):
    """
    Click the logout button (Sair) using multiple approaches.
    Handles shadow DOM and tries various selector strategies.
    Uses Playwright synchronous API.
    """
    try:
        # List of selectors to try in order of preference
        selectors = [
            # Shadow DOM JavaScript path (most reliable for this case)
            {
                'type': 'shadow_js',
                'selector': 'document.querySelector("#privacy-web-floatmenu").shadowRoot.querySelector("#el-id-9525-20 > div > div > div.submenu__options > div:nth-child(3) > div > section > div.others-options > div:nth-child(4) > div.font-medium.text-sm.option-header.d-flex.align-items-center.gap-2.mb-2 > span")'
            },
            # Simplified Shadow DOM path (clicking parent div)
            {
                'type': 'shadow_js',
                'selector': 'document.querySelector("#privacy-web-floatmenu").shadowRoot.querySelector("div.others-options > div:nth-child(4)")'
            },
            # XPath
            {
                'type': 'xpath',
                'selector': '//*[@id="el-id-9525-20"]/div/div/div[1]/div[2]/div/section/div[2]/div[4]/div[1]/span'
            },
            # Alternative XPath (parent div)
            {
                'type': 'xpath',
                'selector': '//*[@id="el-id-9525-20"]/div/div/div[1]/div[2]/div/section/div[2]/div[4]'
            },
            # CSS selectors (alternative approaches)
            {
                'type': 'css',
                'selector': 'div.others-options div:nth-child(4) span'
            },
            {
                'type': 'css',
                'selector': 'div.font-medium.option-header span'
            }
        ]

        # Try each selector approach
        for selector_config in selectors:
            try:
                selector_type = selector_config['type']
                selector = selector_config['selector']

                if selector_type == 'shadow_js':
                    # JavaScript approach for Shadow DOM
                    button_clicked = page.evaluate(f'''() => {{
                        try {{
                            const element = {selector};
                            if (element) {{
                                element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                                element.click();
                                return true;
                            }}
                        }} catch (e) {{
                            console.error('Shadow DOM click error:', e);
                        }}
                        return false;
                    }}''')

                    if button_clicked:
                        print(f"✓ Successfully clicked logout using Shadow DOM JS")
                        return True

                elif selector_type == 'xpath':
                    # XPath approach
                    try:
                        xpath_locator = page.locator(f"xpath={selector}")
                        count = xpath_locator.count()
                        if count > 0:
                            xpath_locator.first.scroll_into_view_if_needed()
                            xpath_locator.first.click(force=True, timeout=3000)
                            print(f"✓ Successfully clicked logout using XPath")
                            return True
                    except Exception as xpath_error:
                        print(f"✗ XPath click failed: {str(xpath_error)}")

                elif selector_type == 'css':
                    # CSS selector approach
                    try:
                        css_locator = page.locator(selector)
                        count = css_locator.count()
                        if count > 0:
                            css_locator.first.scroll_into_view_if_needed()
                            css_locator.first.click(force=True, timeout=3000)
                            print(f"✓ Successfully clicked logout using CSS: {selector}")
                            return True
                    except Exception as css_error:
                        print(f"✗ CSS click failed: {str(css_error)}")

            except Exception as e:
                print(f"✗ Failed with selector {selector}: {str(e)}")
                continue

        # Fallback: comprehensive JavaScript approach
        print("Trying JavaScript fallback methods...")
        fallback_clicked = page.evaluate('''() => {
            // Strategy 1: Shadow DOM access - exact path
            try {
                const floatMenu = document.querySelector('#privacy-web-floatmenu');
                if (floatMenu && floatMenu.shadowRoot) {
                    const sairSpan = floatMenu.shadowRoot.querySelector('#el-id-9525-20 > div > div > div.submenu__options > div:nth-child(3) > div > section > div.others-options > div:nth-child(4) > div.font-medium.text-sm.option-header.d-flex.align-items-center.gap-2.mb-2 > span');
                    if (sairSpan) {
                        sairSpan.scrollIntoView({behavior: 'smooth', block: 'center'});
                        sairSpan.click();
                        return true;
                    }

                    // Try clicking parent div
                    const sairDiv = floatMenu.shadowRoot.querySelector('div.others-options > div:nth-child(4)');
                    if (sairDiv) {
                        sairDiv.scrollIntoView({behavior: 'smooth', block: 'center'});
                        sairDiv.click();
                        return true;
                    }
                }
            } catch (e) {
                console.error('Shadow DOM fallback error:', e);
            }

            // Strategy 2: Find by text content "Sair"
            try {
                const floatMenu = document.querySelector('#privacy-web-floatmenu');
                if (floatMenu && floatMenu.shadowRoot) {
                    const allSpans = floatMenu.shadowRoot.querySelectorAll('span');
                    for (const span of allSpans) {
                        if (span.textContent.trim() === 'Sair') {
                            span.scrollIntoView({behavior: 'smooth', block: 'center'});
                            span.click();
                            return true;
                        }
                    }
                }
            } catch (e) {
                console.error('Text search error:', e);
            }

            // Strategy 3: Find by class combination
            try {
                const floatMenu = document.querySelector('#privacy-web-floatmenu');
                if (floatMenu && floatMenu.shadowRoot) {
                    const optionHeaders = floatMenu.shadowRoot.querySelectorAll('div.option-header');
                    for (const header of optionHeaders) {
                        const span = header.querySelector('span');
                        if (span && span.textContent.trim() === 'Sair') {
                            header.scrollIntoView({behavior: 'smooth', block: 'center'});
                            header.click();
                            return true;
                        }
                    }
                }
            } catch (e) {
                console.error('Class search error:', e);
            }

            // Strategy 4: Find in others-options section
            try {
                const floatMenu = document.querySelector('#privacy-web-floatmenu');
                if (floatMenu && floatMenu.shadowRoot) {
                    const othersOptions = floatMenu.shadowRoot.querySelector('div.others-options');
                    if (othersOptions) {
                        const fourthDiv = othersOptions.querySelector('div:nth-child(4)');
                        if (fourthDiv) {
                            fourthDiv.scrollIntoView({behavior: 'smooth', block: 'center'});
                            fourthDiv.click();
                            return true;
                        }
                    }
                }
            } catch (e) {
                console.error('Others-options search error:', e);
            }

            return false;
        }''')

        if fallback_clicked:
            print("✓ Successfully clicked logout using JavaScript fallback")
            return True

        print("✗ Could not find or click logout button using any method")
        return False

    except Exception as e:
        print(f"✗ Error in click_to_logoff: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    pw, context, browser_process = None, None, None

    try:
        # Open browser and navigate to login page
        pw, context, browser_process = open_chrome_in_privacy_login_page()
        page = context.pages[0]

        print("\n" + "="*60)
        print("STARTING AUTOMATION PROCESS")
        print("="*60)

        # Wait for page load
        print("\nWaiting for page to load...")
        page.wait_for_timeout(5000)

        # Insert credentials and login
        print("\nInserting username...")
        if not insert_username(page):
            print("⚠ Failed to insert username, continuing...")
        page.wait_for_timeout(1000)

        print("Inserting password...")
        if not insert_password(page):
            print("⚠ Failed to insert password, continuing...")
        page.wait_for_timeout(1000)

        print("Clicking 'Entrar' button...")
        if not click_on_entrar_button(page):
            print("⚠ Failed to click 'Entrar' button, continuing...")
        page.wait_for_timeout(1000)

        # Wait for login to complete
        print("Waiting for login to complete...")
        page.wait_for_timeout(8000)

        # Try to close any popup
        print("\nChecking for popups...")
        try_close_popup(page)
        page.wait_for_timeout(2000)

        # Click Extrato tab
        print("\nAttempting to click Extrato tab...")
        if not click_extrato_tab(page):
        print("✓ Success: Extrato tab clicked.")
        page.wait_for_timeout(3000)

        # Open calendar
        print("\nOpening calendar...")
        if not click_on_calendar(page):
            raise Exception("Failed to open calendar")
        page.wait_for_timeout(2000)

        # Select yesterday
        print("Selecting yesterday's date...")
        if not click_on_yesterday(page):
            raise Exception("Failed to select yesterday")
        page.wait_for_timeout(1000)

        # Click yesterday again to set both start and end date
        if not click_on_yesterday(page):
            raise Exception("Failed to select yesterday (end date)")
        print("Successfully selected Yesterday (Range Start & End).")
        page.wait_for_timeout(2000)

        # Click Gerar Relatório button
        print("\nClicking 'Gerar Relatório' button...")
        if not click_on_gerar_relatorio_button(page):
            raise Exception("Failed to click Gerar Relatório")
        print("Dialog 'Gerar Relatório' opened.")
        page.wait_for_timeout(2000)

        # Download the report
        print("\nAttempt 1: Waiting for download event...")

        try:
            with page.expect_download(timeout=30000) as download_info:
                print("Confirm button clicked. Processing file...")
                if not click_on_confirmar_button(page):
                    raise Exception("Failed to click Confirmar button")

            download = download_info.value
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest_filename = f"SalesStatement_{timestamp}.xlsx"
            save_path = os.path.join(r"G:\Meu Drive\Financeiro", dest_filename)

            # Verifique se o diretório existe
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            download.save_as(save_path)
            print(f"✓ File successfully saved to: {save_path}")

        except Exception as download_error:
            print(f"❌ Error during download/save: {download_error}")
            raise  # Re-levanta para o except principal

        # IMPORTANTE: NÃO RETORNE AQUI! Continue para o logout!

        # Wait for download dialog to close
        print("\nWaiting for download confirmation dialog to close...")
        page.wait_for_timeout(5000)

        # Close any remaining dialogs
        print("Checking for open dialogs...")
        try:
            dialog_closed = page.evaluate('''() => {
                try {
                    const overlays = document.querySelectorAll('.el-overlay');
                    overlays.forEach(overlay => {
                        const dialog = overlay.querySelector('[role="dialog"]');
                        if (dialog) {
                            const closeBtn = dialog.querySelector('button.el-dialog__headerbtn');
                            if (closeBtn) closeBtn.click();
                        }
                    });
                    document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape'}));
                    return true;
                } catch (e) {
                    console.error('Error closing dialogs:', e);
                    return false;
                }
            }''')

            if dialog_closed:
                print("✓ Dialogs closed")
            else:
                print("⚠ Dialogs not closed - continuing anyway")
            page.wait_for_timeout(2000)
        except Exception as dialog_error:
            print(f"⚠ Error closing dialogs: {dialog_error} - Continuing to logout")

        # Screenshot before logout
        try:
            print("\nTaking screenshot before logout...")
            page.screenshot(path="before_logout.png")
        except Exception as screenshot_error:
            print(f"⚠ Error taking screenshot: {screenshot_error}")

        # LOGOUT PROCESS
        print("\n" + "="*60)
        print("STARTING LOGOUT PROCESS")
        print("="*60)

        # Step 1: Click menu
        print("\nStep 1: Opening user menu...")

        max_retries = 3
        menu_clicked = False

        for attempt in range(max_retries):
            print(f"Menu click attempt {attempt + 1}/{max_retries}")
            page.screenshot(path=f"menu_attempt_{attempt + 1}.png")

            if click_on_menu(page):
                print("✓ Menu clicked successfully!")
                menu_clicked = True
                break
            else:
                print(f"✗ Attempt {attempt + 1} failed")
                if attempt < max_retries - 1:
                    print("Waiting 2 seconds before retry...")
                    page.wait_for_timeout(2000)

        if not menu_clicked:
            print("\n✗ FAILED: Could not open menu")
            page.screenshot(path="menu_click_failed_final.png")

            # Try ESC workaround
            print("Trying ESC workaround...")
            page.keyboard.press("Escape")
            page.wait_for_timeout(1000)

            if click_on_menu(page):
                print("✓ Menu opened after ESC!")
                menu_clicked = True
            else:
                print("❌ Could not open menu - skipping logout")

        if menu_clicked:
            # Wait for menu animation
            print("Waiting for menu animation...")
            page.wait_for_timeout(2500)
            page.screenshot(path="menu_opened.png")

            # Step 2: Click logout
            print("\nStep 2: Clicking logout button (Sair)...")

            logout_clicked = False

            for attempt in range(max_retries):
                print(f"Logout click attempt {attempt + 1}/{max_retries}")
                page.screenshot(path=f"logout_attempt_{attempt + 1}.png")

                if click_to_logoff(page):
                    print("✓ Logout clicked successfully!")
                    logout_clicked = True
                    break
                else:
                    print(f"✗ Attempt {attempt + 1} failed")
                    if attempt < max_retries - 1:
                        print("Waiting 2 seconds before retry...")
                        page.wait_for_timeout(2000)

            if not logout_clicked:
                print("\n✗ FAILED: Could not click logout button")
                page.screenshot(path="logout_click_failed_final.png")
                print("⚠ Warning: Logout incomplete")
            else:
                # Wait for logout
                print("Waiting for logout to complete...")
                page.wait_for_timeout(4000)

                # Verify logout
                current_url = page.url
                print(f"Current URL: {current_url}")

                if "login" in current_url.lower() or "auth" in current_url.lower():
                    print("✓ Logout confirmed - redirected to login page")
                else:
                    print("⚠ URL doesn't indicate logout completion")

                page.screenshot(path="after_logout.png")
                print("✓ Logout process completed!")

        print("\n" + "="*60)
        print("✓ AUTOMATION COMPLETED SUCCESSFULLY")
        print("="*60)
        print("\n✓ Download and logout process completed.")

    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        traceback.print_exc()

        # Error screenshot
        try:
            page.screenshot(path="error_screenshot.png")
            print("Error screenshot saved")
        except:
            pass

    finally:
        print("\n" + "="*60)
        print("CLEANING UP RESOURCES")
        print("="*60)
        cleanup(pw, context, browser_process)
        print("✓ Cleanup completed. Program finished.")

if __name__ == "__main__":
    main()




