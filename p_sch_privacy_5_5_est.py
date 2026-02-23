# Standard library imports
import os
import random
import sys
import openpyxl
import time
import subprocess
from datetime import datetime, timedelta, date
import warnings
import pyperclip

# Third-party imports
from playwright.sync_api import sync_playwright
from openpyxl.styles import Font

warnings.filterwarnings("ignore", category=UserWarning, module="playwright_stealth")
warnings.filterwarnings("ignore", category=DeprecationWarning)

def log_error_to_file(error_message, log_file_path="G:\Meu Drive\Privacy_free\p_sch_privacy_free_error_logs.txt"):
    """
    Logs an error message to a file with a timestamp.
    Creates the directory if it does not exist.
    """
    timestamp = datetime.now().strftime("%m/%d/%Y at %H:%M") # MM/DD/YYYY at HH:MM
    log_entry = f"Error in click_on_sair on {timestamp}: {error_message}\n"

    # Ensure the directory exists
    log_dir = os.path.dirname(log_file_path)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    try:
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
        print(f"✅ Error logged to {log_file_path}")
    except Exception as file_e:
        print(f"❌ Failed to write log to file: {str(file_e)}")

# region playwright-stealth (fork mais atualizado recomendado em 2025/2026)
try:
    from playwright_stealth import stealth_sync
except ImportError as e: # Catch the specific ImportError
    error_message = f"playwright-stealth not found. Please install with: pip install git+https://github.com/AtuboDad/playwright_stealth.git - {str(e)}"
    print(f"❌ {error_message}")
    log_error_to_file(error_message) # Log the error
    sys.exit(1)
except Exception as e: # Catch any other unexpected exceptions during import
    error_message = f"An unexpected error occurred during playwright-stealth import: {str(e)}"
    print(f"❌ {error_message}")
    log_error_to_file(error_message) # Log the error
    sys.exit(1)
# endregion

def cleanup(pw=None, context=None, browser_process=None):
    """Cleanup resources properly"""
    if context:
        try:
            context.close()
        except Exception as e:
            error_message = f"Error closing context: {str(e)}"
            print(f"❌ {error_message}")
            log_error_to_file(error_message)
    if pw:
        try:
            pw.stop()
        except Exception as e:
            error_message = f"Error stopping Playwright: {str(e)}"
            print(f"❌ {error_message}")
            log_error_to_file(error_message)
    if browser_process:
        try:
            browser_process.terminate()
            browser_process.wait(timeout=5)
        except Exception as e:
            error_message = f"Error terminating browser process: {str(e)}"
            print(f"❌ {error_message}")
            log_error_to_file(error_message)
    print("Recursos liberados")

def open_chrome_in_privacy_login_page():
    # 1. Paths
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    # We use a subfolder to avoid the 'default directory' security error
    user_data = os.path.join(os.environ['LOCALAPPDATA'], r"Google\Chrome\User Data\Automation")

    # 2. Kill any existing Chrome
    try:
        os.system("taskkill /f /im chrome.exe /t >nul 2>&1")
        time.sleep(2)
    except Exception as e:
        error_message = f"Error killing existing Chrome processes: {str(e)}"
        print(f"❌ {error_message}")
        log_error_to_file(error_message)
        # Decide if you want to exit or continue if killing fails
        # For now, we'll let it try to proceed.

    # 3. Launch Chrome as a SEPARATE process (Native Launch)
    # We open a 'Remote Debugging Port' that Playwright will use to connect
    print("Launching Native Chrome Process...")
    browser_process = None
    try:
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

    except Exception as e:
        error_message = f"Error launching native Chrome process: {str(e)}"
        print(f"❌ {error_message}")
        log_error_to_file(error_message)
        if browser_process:
            browser_process.kill()
        raise # Re-raise the exception as we cannot proceed without a browser

    # 4. Connect Playwright to the ALREADY OPENED Chrome
    pw = None
    try:
        print("Hooking Playwright into the running Chrome...")
        pw = sync_playwright().start()
        # Instead of launch_persistent_context, we CONNECT to the port
        browser = pw.chromium.connect_over_cdp("http://localhost:9222")

        # Access the already open context and page
        context = browser.contexts[0]
        page = context.pages[0]

        print("✅ Successfully hooked! Browser is now under automation control.")
        return pw, context, browser_process

    except Exception as e:
        error_message = f"Failed to hook Playwright into running Chrome: {str(e)}"
        print(f"❌ {error_message}")
        log_error_to_file(error_message)
        if pw:
            pw.stop()
        if browser_process:
            browser_process.kill()
        raise # Re-raise the exception as the core operation failed

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
                            console.error('❌ Error inserting username:', e);
                        }}
                        return false;
                    }}''', "milfelectra@gmail.com")
                    if input_inserted:
                        print("✅ Username inserted successfully with Shadow DOM selector")
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
                            print("✅ Username inserted successfully with XPath")
                            return True
                        except Exception as e:
                            print(f"❌ XPath insert failed: {str(e)}")

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
                            print("✅ Username inserted successfully with CSS selector")
                            return True
                        except Exception as e:
                            print(f"❌ CSS selector insert failed: {str(e)}")

            except Exception as e:
                print(f"❌ Failed with username input selector {selector}: {str(e)}")
                continue

        # Fallback JavaScript approach with comprehensive search (updated with new patterns)
        print("⏳ Trying JavaScript fallback approach for username input...")
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
            print("✅ Username successfully using JavaScript fallback!")
            return True

        print("❌ Could not find or insert into username input using any method.")
        return False

    except Exception as e:
        # This outer except block catches any unhandled exceptions from the entire function
        print(f"❌ Error in insert_username: {error_message}")
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
                            console.error('❌ Error inserting password:', e);
                        }}
                        return false;
                    }}''', "#Partiu14")
                    if input_inserted:
                        print("✅ Password inserted successfully with Shadow DOM selector")
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
                            print("✅ Password inserted successfully with XPath")
                            return True
                        except Exception as e:
                            print(f"❌ XPath insert failed: {str(e)}")

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
                            print("✅ Password inserted successfully with CSS selector")
                            return True
                        except Exception as e:
                            print(f"❌ CSS selector insert failed: {str(e)}")

            except Exception as e:
                print(f"❌ Failed with password input selector {selector}: {str(e)}")
                continue

        # Fallback JavaScript approach with comprehensive search (updated with new patterns)
        print("⏳ Trying JavaScript fallback approach for password input...")
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
            print("✅ Password inserted successfully using JavaScript fallback!")
            return True

        print("❌ Could not find or insert into password input using any method.")
        return False

    except Exception as e:
        # This outer except block catches any unhandled exceptions from the entire function
        print(f"❌ Error in insert_password: {error_message}")
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
                        print(f"✅ 'Entrar' button clicked successfully with JS selector: {approach['path']}")
                        return True

                elif approach["type"] == "xpath":
                    # Force click via Playwright locator
                    el = page.locator(f"xpath={approach['path']}")
                    if el.count() > 0:
                        el.first.click(force=True, timeout=2000)
                        print(f"✅ 'Entrar' button clicked successfully with XPath: {approach['path']}")
                        return True

                elif approach["type"] == "css":
                    # CSS selector (Playwright handles shadow DOM for simple cases, but JS is more robust for force-clicking)
                    el = page.locator(approach['path'])
                    if el.count() > 0:
                        # Attempt to remove disabled state via JS before Playwright click
                        page.evaluate(f'''(selector) => {{
                            const btn = document.querySelector(selector);
                            if (btn) {{
                                btn.disabled = false;
                                btn.classList.remove('is-disabled');
                            }}
                        }}''', approach['path'])
                        el.first.click(force=True, timeout=2000)
                        print(f"✅ 'Entrar' button clicked successfully with CSS selector: {approach['path']}")
                        return True

            except Exception as e:
                # Log specific selector failure, but continue trying other approaches
                print(f"⏳ Attempt to click 'Entrar' button failed with {approach['type']} selector {approach['path']}: {str(e)}")
                continue # Try the next approach

        # Final Fallback: Search for the button by text content "Entrar"
        print("⏳ Trying JavaScript fallback for 'Entrar' button by text content...")
        fallback = page.evaluate('''() => {
            const authRoot = document.querySelector("#privacy-web-auth")?.shadowRoot;
            if (authRoot) {
                const buttons = authRoot.querySelectorAll('button');
                for (const btn of buttons) {
                    if (btn.textContent.includes('Entrar')) {
                        btn.disabled = false; // Ensure it's not disabled
                        btn.classList.remove('is-disabled');
                        btn.scrollIntoView({behavior: 'instant', block: 'center'});
                        btn.click();
                        return true;
                    }
                }
            }
            // Also check main DOM if not found in shadow
            const mainButtons = document.querySelectorAll('button');
            for (const btn of mainButtons) {
                if (btn.textContent.includes('Entrar')) {
                    btn.disabled = false;
                    btn.classList.remove('is-disabled');
                    btn.scrollIntoView({behavior: 'instant', block: 'center'});
                    btn.click();
                    return true;
                }
            }
            return false;
        }''')

        if fallback:
            print("✅ 'Entrar' button clicked successfully using JavaScript text fallback!")
            return True
        else:
            print("❌ Could not find or click 'Entrar' button using any method.")
            return False

    except Exception as e:
        # This outer except block catches any unhandled exceptions from the entire function
        print(f"❌ Error in click_on_entrar_button: {error_message}")
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

def captions_operation():
    """
    Loads captions from Excel, filters out used ones based on the history file,
    and returns a randomized list. If all are used, it resets the history.
    """
    # Updated File paths
    excel_path = r"G:\Meu Drive\Privacy_free\privacy_captions.xlsx"
    history_path = r"G:\Meu Drive\Privacy_free\privacy_free_used_captions.txt"
    
    available_captions = []
    used_captions = []

    # 1. Load used captions from the history file
    if os.path.exists(history_path):
        with open(history_path, "r", encoding="utf-8") as f:
            used_captions = [line.strip() for line in f.readlines() if line.strip()]

    try:
        # 2. Load all captions from the Excel file
        workbook = openpyxl.load_workbook(excel_path)
        sheet = workbook.active
        all_excel_captions = []
        
        for row in sheet.iter_rows(values_only=True):
            for cell in row:
                if cell is not None:
                    clean_caption = str(cell).strip()
                    if clean_caption:
                        all_excel_captions.append(clean_caption)

        # 3. Filter: Keep only captions NOT found in the history file
        available_captions = [c for c in all_excel_captions if c not in used_captions]

        # 4. Logic: Reset if empty
        if not available_captions:
            print("All captions used. Resetting history file...")
            with open(history_path, "w", encoding="utf-8") as f:
                f.truncate(0)
                f.flush()
                os.fsync(f.fileno())
            available_captions = all_excel_captions

        # 5. Shuffle
        random.shuffle(available_captions)

    except FileNotFoundError:
        error_msg = f"Error: Excel file not found at {excel_path}"
        print(f"❌ Error: Excel file not found at {excel_path}")
        log_error_to_file(error_msg) # Log cleanup errors
    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        print(f"❌ An unexpected error occurred: {e}")
        log_error_to_file(error_msg) # Log cleanup errors

    return available_captions

def mark_caption_as_used(caption):
    """
    Appends the caption to the history file and forces an immediate save to disk.
    """
    history_path = r"G:\Meu Drive\Privacy_free\privacy_free_used_captions.txt"
    
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    
    # Using 'a' (append) mode to add the new caption at the end
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(caption + "\n")
        # Force the OS to write the data to the physical disk immediately
        f.flush()
        os.fsync(f.fileno())

def cleanup(pw=None, context=None, browser_process=None):
    """Cleanup resources properly"""
    if context:
        try:
            context.close()
        except Exception as e:
            print(f"❌ Error closing context: {e}")
            error_msg = f"❌ Error closing context: {e}"
            log_error_to_file(error_msg) # Log cleanup errors
    if pw:
        try:
            pw.stop()
        except Exception as e:
            print(f"❌ Error stopping Playwright: {e}")
            error_msg = f"❌ Error stopping Playwright: {e}"
            log_error_to_file(error_msg) # Log cleanup errors
    if browser_process:
        try:
            browser_process.terminate()
            browser_process.wait(timeout=5)
        except Exception as e:
            print(f"❌ Error terminating browser process: {e}")
            error_msg = f"❌ Error terminating browser process: {e}"
            log_error_to_file(error_msg) # Log cleanup errors
    print("Recursos liberados")

def click_On_Pular_Tutorial_btn(page):
    """
    Attempt to find and click the "Pular tutorial" button using multiple approaches.
    """
    try:
        # List of selectors to try
        selectors = [
            # Direct CSS selector
            "#onboarding-container > div > header > button",
            # Shadow DOM JavaScript path
            "document.querySelector('#privacy-web-board').shadowRoot.querySelector('div > privacy-web-onboarding').shadowRoot.querySelector('#onboarding-container > div > header > button')",
            # XPath
            "//*[@id='onboarding-container']/div/header/button"
        ]

        # Try each selector
        for selector in selectors:
            try:
                print(f"⏳ Trying Pular tutorial button selector: {selector}")
                
                # Handle different selector types
                if selector.startswith("document.querySelector"):
                    # JavaScript selector
                    button_clicked = page.evaluate(f'''() => {{
                        const button = {selector};
                        if (button) {{
                            button.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            button.click();
                            return true;
                        }}
                        return false;
                    }}''')
                    
                    if button_clicked:
                        print(f"✅ Successfully clicked Pular tutorial button with JS selector")
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
                            xpath_elements.first.click(force=True)
                            print(f"✅ Successfully clicked Pular tutorial button with XPath")
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
                            css_elements.first.click(force=True)
                            print(f"✅ Successfully clicked Pular tutorial button with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"❌ Failed with Pular tutorial button selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("⏳ Trying JavaScript fallback approach for Pular tutorial button...")
        fallback_clicked = page.evaluate('''() => {
            // Try finding button elements with "Pular tutorial" text
            const buttonSelectors = [
                'button.skip-button',
                'button.el-button--secondary',
                'button[aria-disabled="false"]'
            ];
            
            for (const selector of buttonSelectors) {
                const buttons = document.querySelectorAll(selector);
                for (const button of buttons) {
                    if (button && button.textContent.includes('Pular tutorial')) {
                        button.scrollIntoView({behavior: 'smooth', block: 'center'});
                        button.click();
                        return true;
                    }
                }
            }
            return false;
        }''')
        
        if fallback_clicked:
            print("✅ Successfully clicked Pular tutorial button using JavaScript fallback!")
            return True
        
        print("Could not find or click Pular tutorial button using any method.")
        return False
    
    except Exception as e:
        print(f"❌ Error in click_On_Pular_Tutorial_btn: {str(e)}")
        return False

def click_to_close_pop_up(page):
    """
    Attempt to find and click the 'X' (close) button inside the Shadow DOM pop-up.
    """
    try:
        # List of selectors specifically for this X mark
        selectors = [
            # 1. Shadow DOM CSS Selector (Playwright handles '>>' as shadow boundary)
            "#privacy-web-stories >> div.privacy-wrapped__dialog >> button >> svg.fa-xmark",
            
            # 2. JavaScript Path (Direct from your parameters)
            'document.querySelector("#privacy-web-stories").shadowRoot.querySelector("div > div.privacy-wrapped__dialog > div > div > div > header > div > button > svg")',
            
            # 3. XPath (Note: Standard XPath doesn't penetrate Shadow DOM well, but we keep it for structure)
            '//*[@id="privacy-web-stories"]//div/div[2]/div/div/div/header/div/button/svg'
        ]

        for selector in selectors:
            try:
                # Handle JavaScript Path approach
                if selector.startswith("document.querySelector"):
                    clicked = page.evaluate(f'''() => {{
                        const element = {selector};
                        if (element) {{
                            element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            // We click the parent button as it's a better target than the SVG path
                            const btn = element.closest('button') || element;
                            btn.click();
                            return true;
                        }}
                        return false;
                    }}''')
                    if clicked: return True

                # Handle Playwright Shadow DOM CSS
                elif ">>" in selector:
                    target = page.locator(selector).first
                    if target.count() > 0:
                        target.scroll_into_view_if_needed()
                        target.click(force=True)
                        return True

                # Handle Standard Selectors
                else:
                    target = page.locator(selector).first
                    if target.count() > 0:
                        target.click(force=True)
                        return True

            except Exception:
                continue

        # Fallback: Broad JavaScript search inside the shadow root
        fallback_clicked = page.evaluate('''() => {
            const host = document.querySelector("#privacy-web-stories");
            if (!host || !host.shadowRoot) return false;
            
            // Look for any button with a close icon/class inside the shadow
            const closeBtn = host.shadowRoot.querySelector('button[aria-label*="close" i]') || 
                             host.shadowRoot.querySelector('.fa-xmark')?.closest('button');
            
            if (closeBtn) {
                closeBtn.click();
                return true;
            }
            return false;
        }''')

        return fallback_clicked

    except Exception as e:
        print(f"❌ Error in click_to_close_pop_up: {str(e)}")
        return False

def click_on_postar_btn(page):
    """
    Attempt to find and click the 'Postar' button using multiple approaches.
    """
    try:
        # List of selectors to try
        selectors = [
            # Direct CSS selector
            "div > nav > div:nth-child(3) > svg",
            # Alternative CSS selectors
            "nav.menu div.menu__item:nth-child(3)",
            "div.menu__item svg[data-icon='plus']",
            "svg.fa-plus",
            # JavaScript path (from shadow root)
            "document.querySelector(\"#privacy-web-floatmenu\").shadowRoot.querySelector(\"div > nav > div:nth-child(3) > svg\")",
            # XPath
            "//*[@id=\"privacy-web-floatmenu\"]//div/nav/div[3]/svg",
            # Alternative XPath
            "//nav[@class='menu']/div[3]",
            "//svg[@data-icon='plus']"
        ]

        # Try each selector
        for selector in selectors:
            try:
                # Handle different selector types
                if selector.startswith("document.querySelector"):
                    # JavaScript selector (handles shadow DOM)
                    button_clicked = page.evaluate(f'''() => {{
                        const button = {selector};
                        if (button) {{
                            button.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            button.click();
                            return true;
                        }}
                        return false;
                    }}''')
                    if button_clicked:
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
                            xpath_elements.first.click(force=True)
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
                            css_elements.first.click(force=True)
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")

            except Exception as e:
                print(f"❌ Failed with Postar button selector {selector}: {str(e)}")
                continue

        # Fallback JavaScript approach for shadow DOM
        fallback_clicked = page.evaluate('''() => {
            // Try to access shadow root
            const floatMenu = document.querySelector('#privacy-web-floatmenu');
            if (floatMenu && floatMenu.shadowRoot) {
                const postarBtn = floatMenu.shadowRoot.querySelector('div > nav > div:nth-child(3)');
                if (postarBtn) {
                    postarBtn.scrollIntoView({behavior: 'smooth', block: 'center'});
                    postarBtn.click();
                    return true;
                }
            }

            // Try finding by data-icon attribute
            const plusIcons = document.querySelectorAll('svg[data-icon="plus"]');
            for (const icon of plusIcons) {
                const parentDiv = icon.closest('div.menu__item');
                if (parentDiv) {
                    parentDiv.scrollIntoView({behavior: 'smooth', block: 'center'});
                    parentDiv.click();
                    return true;
                }
            }

            // Try finding by text content "Postar"
            const menuItems = document.querySelectorAll('div.menu__item');
            for (const item of menuItems) {
                const textSpan = item.querySelector('span.text-menu');
                if (textSpan && textSpan.textContent.trim() === 'Postar') {
                    item.scrollIntoView({behavior: 'smooth', block: 'center'});
                    item.click();
                    return true;
                }
            }

            return false;
        }''')

        if fallback_clicked:
            return True

        print("Could not find or click Postar button using any method.")
        return False

    except Exception as e:
        print(f"❌ Error in click_on_postar_btn: {str(e)}")
        return False

def click_On_Feed_btn(page):
    """
    Attempt to find and click the Feed option in the Postar modal window.
    """
    try:
        # List of selectors (prioritized: attribute-based)
        selectors = [
            # Attribute-based CSS
            {"selector": 'div.options__option:has(svg[data-icon="feed"])', "options": {}},
            # Stable XPath
            {"selector": "//div[contains(@class, 'options__option') and .//svg[@data-icon='feed']]", "options": {"is_xpath": True}},
            # Text-based fallback
            {"selector": 'div.options__option:has-text("Feed")', "options": {}},
        ]

        for sel in selectors:
            if safe_click(page, sel["selector"], sel["options"]):
                return True

        # Fallback JavaScript (with null checks)
        fallback_clicked = page.evaluate('''() => {
            const options = document.querySelectorAll('div.options__option');
            for (const option of options) {
                if (option.querySelector('svg[data-icon="feed"]')) {
                    option.scrollIntoView({behavior: 'smooth', block: 'center'});
                    option.click();
                    return true;
                }
            }
            return false;
        }''')

        if fallback_clicked:
            print("✅ Successfully clicked Feed button using JavaScript fallback!")
            return True

        print("Could not find or click Feed button using any method.")
        return False

    except Exception as e:
        print(f"❌ Error in click_On_Feed_btn: {str(e)}")
        return False

def click_On_Selecionar_Foto_ou_Video_btn(page):
    """
    Attempt to find and click the "Select Photo or Video" button in the media upload modal.
    """
    try:
        # First ensure the modal is visible
        modal_visible = page.locator("div.post-upload.el-drawer.rtl.open").is_visible()
        if not modal_visible:
            print("Media upload modal is not visible")
            return False

        # List of selectors to try (all within the modal context)
        selectors = [
            # CSS selector for the button div
            "div.post-upload__content-button",
            # More specific CSS selector
            "div.post-upload__content-media > div.post-upload__content-button",
            # XPath for the button
            "//div[contains(@class, 'post-upload__content-button')]",
            # Full path XPath
            "//div[@class='post-upload el-drawer rtl open']//div[contains(@class, 'post-upload__content-button')]"
        ]

        # Try each selector
        for selector in selectors:
            try:
                print(f"⏳ Trying Select Photo/Video button selector: {selector}")
                
                if selector.startswith('/'):
                    # XPath selector
                    xpath_elements = page.locator(f"xpath={selector}")
                    if xpath_elements.count() > 0:
                        try:
                            # Wait for element to be visible and enabled
                            xpath_elements.first.wait_for(state="visible")
                            xpath_elements.first.wait_for(state="enabled")
                            
                            # Scroll and click
                            xpath_elements.first.scroll_into_view_if_needed()
                            xpath_elements.first.click(force=True)
                            print(f"✅ Successfully clicked Select Photo/Video button with XPath")
                            return True
                        except Exception as e:
                            print(f"XPath click failed: {str(e)}")
                else:
                    # CSS selector
                    css_elements = page.locator(selector)
                    if css_elements.count() > 0:
                        try:
                            # Wait for element to be visible and enabled
                            css_elements.first.wait_for(state="visible")
                            css_elements.first.wait_for(state="enabled")
                            
                            # Scroll and click
                            css_elements.first.scroll_into_view_if_needed()
                            css_elements.first.click(force=True)
                            print(f"✅ Successfully clicked Select Photo/Video button with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"❌ Failed with Select Photo/Video button selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach specifically for the modal
        print("⏳ Trying JavaScript fallback approach for Select Photo/Video button...")
        fallback_clicked = page.evaluate('''() => {
            // Find the modal first
            const modal = document.querySelector('div.post-upload.el-drawer.rtl.open');
            if (!modal) return false;
            
            // Try finding the button within the modal
            const buttons = modal.querySelectorAll('div.post-upload__content-button');
            for (const button of buttons) {
                if (button) {
                    // Verify it contains the plus icon and correct text
                    const hasPlusIcon = button.querySelector('svg[data-icon="plus"]');
                    const hasCorrectText = button.textContent.toLowerCase().includes('selecionar foto ou vídeo');
                    
                    if (hasPlusIcon && hasCorrectText) {
                        button.scrollIntoView({behavior: 'smooth', block: 'center'});
                        button.click();
                        return true;
                    }
                }
            }
            return false;
        }''')
        
        if fallback_clicked:
            print("✅ Successfully clicked Select Photo/Video button using JavaScript fallback!")
            return True
        
        print("Could not find or click Select Photo/Video button using any method.")
        return False
    
    except Exception as e:
        print(f"❌ Error in click_On_Selecionar_Foto_ou_Video_btn: {str(e)}")
        return False

def click_to_send_file_url(page, filename):
    """
    Directly uploads a file to the browser without using PyAutoGUI.
    """
    # 1. Define the full path
    folder_path = r'G:\Meu Drive\SFS'
    full_file_path = os.path.join(folder_path, filename)

    print(f"Directly uploading: {full_file_path}")

    try:
        # 2. Playwright 'expect_file_chooser' handles the hidden input trigger
        with page.expect_file_chooser() as fc_info:
            # Click the "+" icon or the button that triggers the upload
            # We use the SVG structure or the text to find it
            page.locator("text=selecionar foto ou vídeo").click()
            
        file_chooser = fc_info.value
        
        # 3. Send the URL/Path directly to the browser
        file_chooser.set_files(full_file_path)
        
        print("File sent ✅ Successfully via browser URL.")
        return True

    except Exception as e:
        print(f"❌ Error sending file directly: {e}")
        return False

def click_On_Text_Area(page):
    """
    Attempt to find and click the text area using multiple approaches.
    """
    try:
        # List of selectors to try
        selectors = [
            # Direct CSS selector
            "textarea.el-textarea__inner",
            # ID selector
            "#el-id-6502-40",
            # Shadow DOM JavaScript path
            "document.querySelector(\"#privacy-web-publisher\").shadowRoot.querySelector(\"#el-id-6502-40\")",
            # XPath
            "//textarea[@class='el-textarea__inner']",
            "//*[@id=\"el-id-6502-40\"]"
        ]

        # Try each selector
        for selector in selectors:
            try:
                print(f"⏳ Trying text area selector: {selector}")
                
                # Handle different selector types
                if selector.startswith("document.querySelector"):
                    # JavaScript selector
                    clicked = page.evaluate(f'''() => {{
                        const textarea = {selector};
                        if (textarea) {{
                            textarea.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            textarea.click();
                            return true;
                        }}
                        return false;
                    }}''')
                    
                    if clicked:
                        print(f"✅ Successfully clicked text area with JS selector")
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
                            xpath_elements.first.click(force=True)
                            print(f"✅ Successfully clicked text area with XPath")
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
                            css_elements.first.click(force=True)
                            print(f"✅ Successfully clicked text area with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"❌ Failed with text area selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("⏳ Trying JavaScript fallback approach for text area...")
        fallback_clicked = page.evaluate('''() => {
            // Try finding textarea elements
            const textareaSelectors = [
                'textarea[placeholder="Escreva uma legenda..."]',
                'textarea[maxlength="2200"]',
                'textarea.el-textarea__inner'
            ];
            
            for (const selector of textareaSelectors) {
                const textareas = document.querySelectorAll(selector);
                for (const textarea of textareas) {
                    if (textarea) {
                        textarea.scrollIntoView({behavior: 'smooth', block: 'center'});
                        textarea.click();
                        return true;
                    }
                }
            }
            return false;
        }''')
        
        if fallback_clicked:
            print("✅ Successfully clicked text area using JavaScript fallback!")
            return True
        
        print("Could not find or click text area using any method.")
        return False
    
    except Exception as e:
        print(f"❌ Error in click_On_Text_Area: {str(e)}")
        return False

def select_media():
    folder_path = r'G:\Meu Drive\SFS'
    history_path = r"G:\Meu Drive\Privacy_free\privacy_free_used_media.txt"
    
    # 1. Define allowed extensions (ignores desktop.ini and Google Drive shortcuts)
    valid_extensions = ('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.avi', '.webp')
    
    used_media = []
    # 2. Load already used media from the text file
    if os.path.exists(history_path):
        with open(history_path, "r", encoding="utf-8") as f:
            used_media = [line.strip() for line in f.readlines() if line.strip()]

    try:
        # 3. List all files and filter by extensions
        all_files = os.listdir(folder_path)
        files_only = [
            f for f in all_files 
            if f.lower().endswith(valid_extensions) and os.path.isfile(os.path.join(folder_path, f))
        ]
        
        # 4. Create list of media NOT in the history file
        available_media = [f for f in files_only if f not in used_media]

        # 5. CRITICAL CHECK: If everything has been used, clear the history and restart
        if not available_media:
            print("All media used. Clearing history file and restarting...")
            with open(history_path, "w", encoding="utf-8") as f:
                f.truncate(0)  # Deletes everything inside the TXT
            available_media = files_only # The list becomes full again

        # 6. Shuffle for randomness
        random.shuffle(available_media)
        return available_media

    except Exception as e:
        print(f"❌ Error selecting media: {e}")
        return []

def mark_media_as_used(media_name):
    history_path = r"G:\Meu Drive\Privacy_free\privacy_free_used_media.txt"
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(media_name + "\n")
        
def click_to_schedule_post(page):
    """
    Attempt to find and click the 'Agendar publicação' (Schedule post) switch using multiple approaches.
    """
    try:
        # List of selectors to try
        selectors = [
            # Direct CSS selector
            "#el-id-5287-17 > form > div.post-attributes > div.post-attributes__switchs.d-flex.flex-column.gap-3.mt-4 > div:nth-child(1) > div:nth-child(2) > div",
            # Alternative CSS selectors
            "div.post-attributes__switchs-item:nth-child(1) div.el-switch",
            "div.el-switch input[id^='el-id'][type='checkbox']",
            ".post-attributes__switchs .el-switch",
            # Input directly
            "input.el-switch__input[role='switch'][id^='el-id']",
            # JavaScript path (from shadow root)
            "document.querySelector(\"#privacy-web-publisher\").shadowRoot.querySelector(\"#el-id-5287-17 > form > div.post-attributes > div.post-attributes__switchs.d-flex.flex-column.gap-3.mt-4 > div:nth-child(1) > div:nth-child(2) > div\")",
            # XPath
            "//*[@id=\"el-id-5287-17\"]/form/div[4]/div[2]/div[1]/div[2]/div",
            # Alternative XPath
            "//span[contains(text(), 'Agendar publicação')]/ancestor::div[@class='post-attributes__switchs-item']//div[@class='el-switch']",
            "//input[@class='el-switch__input' and @type='checkbox']"
        ]

        # Try each selector
        for selector in selectors:
            try:
                # Handle different selector types
                if selector.startswith("document.querySelector"):
                    # JavaScript selector (handles shadow DOM)
                    button_clicked = page.evaluate(f'''() => {{
                        try {{
                            const element = {selector};
                            if (element) {{
                                element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                                element.click();
                                return true;
                            }}
                            // Try clicking the input inside
                            const input = element?.querySelector('input.el-switch__input');
                            if (input) {{
                                input.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                                input.click();
                                return true;
                            }}
                        }} catch(e) {{
                            console.error(e);
                        }}
                        return false;
                    }}''')
                    if button_clicked:
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
                            xpath_elements.first.click(force=True)
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
                            css_elements.first.click(force=True)
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")

            except Exception as e:
                print(f"❌ Failed with schedule switch selector {selector}: {str(e)}")
                continue

        # Fallback JavaScript approach for shadow DOM and dynamic IDs
        fallback_clicked = page.evaluate('''() => {
            // Try to access shadow root
            const publisher = document.querySelector('#privacy-web-publisher');
            if (publisher && publisher.shadowRoot) {
                // Find by text content "Agendar publicação"
                const switchItems = publisher.shadowRoot.querySelectorAll('.post-attributes__switchs-item');
                for (const item of switchItems) {
                    const text = item.querySelector('span.font-sm');
                    if (text && text.textContent.includes('Agendar publicação')) {
                        const switchEl = item.querySelector('.el-switch');
                        if (switchEl) {
                            switchEl.scrollIntoView({behavior: 'smooth', block: 'center'});
                            switchEl.click();
                            return true;
                        }
                        // Try clicking input directly
                        const input = item.querySelector('input.el-switch__input');
                        if (input) {
                            input.scrollIntoView({behavior: 'smooth', block: 'center'});
                            input.click();
                            return true;
                        }
                    }
                }
            }

            // Try finding by calendar icon + switch combination
            const calendarIcons = document.querySelectorAll('svg[data-icon="calendar"]');
            for (const icon of calendarIcons) {
                const switchItem = icon.closest('.post-attributes__switchs-item');
                if (switchItem) {
                    const switchEl = switchItem.querySelector('.el-switch');
                    if (switchEl) {
                        switchEl.scrollIntoView({behavior: 'smooth', block: 'center'});
                        switchEl.click();
                        return true;
                    }
                }
            }

            // Try finding first switch in post-attributes
            const firstSwitch = document.querySelector('.post-attributes__switchs .el-switch');
            if (firstSwitch) {
                firstSwitch.scrollIntoView({behavior: 'smooth', block: 'center'});
                firstSwitch.click();
                return true;
            }

            return false;
        }''')

        if fallback_clicked:
            return True

        print("Could not find or click schedule switch using any method.")
        return False

    except Exception as e:
        print(f"❌ Error in click_to_schedule_post: {str(e)}")
        return False

def insert_new_media(page):
    """
    Attempt to find and click the media/image insertion button using multiple approaches.
    """
    try:
        # List of selectors to try
        selectors = [
            # Direct CSS selector
            "div > div.ce-actions.ce-actions-many-items > div.ce-actions-icon > div:nth-child(1) > svg",
            # Shadow DOM JavaScript path
            "document.querySelector(\"#privacy-web-publication\").shadowRoot.querySelector(\"div > div > privacy-web-contenteditor\").shadowRoot.querySelector(\"div > div.ce-actions.ce-actions-many-items > div.ce-actions-icon > div:nth-child(1) > svg\")",
            # XPath
            "//*[@id=\"privacy-web-publication\"]//div/div/privacy-web-contenteditor//div/div[2]/div[1]/div[1]/svg"
        ]

        # Try each selector
        for selector in selectors:
            try:
                print(f"⏳ Trying media insertion selector: {selector}")
                
                # Handle different selector types
                if selector.startswith("document.querySelector"):
                    # JavaScript selector
                    button_clicked = page.evaluate(f'''() => {{
                        const svgElement = {selector};
                        if (svgElement) {{
                            svgElement.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            svgElement.closest('div').click();
                            return true;
                        }}
                        return false;
                    }}''')
                    
                    if button_clicked:
                        print(f"✅ Successfully clicked media insertion button with JS selector")
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
                            xpath_elements.first.click(force=True)
                            print(f"✅ Successfully clicked media insertion button with XPath")
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
                            css_elements.first.click(force=True)
                            print(f"✅ Successfully clicked media insertion button with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"❌ Failed with media insertion selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("⏳ Trying JavaScript fallback approach for media insertion...")
        fallback_clicked = page.evaluate('''() => {
            // Try finding SVG elements related to image/media insertion
            const svgSelectors = [
                'svg.svg-inline--fa[data-icon="image"]',
                'svg[role="img"][data-icon="image"]',
                'svg[data-prefix="fal"][data-icon="image"]'
            ];
            
            for (const selector of svgSelectors) {
                const svgElements = document.querySelectorAll(selector);
                for (const svg of svgElements) {
                    if (svg) {
                        svg.scrollIntoView({behavior: 'smooth', block: 'center'});
                        // Try clicking the SVG or its closest clickable parent
                        const clickableParent = svg.closest('div[clickable], div.ce-actions-icon');
                        if (clickableParent) {
                            clickableParent.click();
                            return true;
                        }
                        svg.click();
                        return true;
                    }
                }
            }
            return false;
        }''')
        
        if fallback_clicked:
            print("✅ Successfully clicked media insertion button using JavaScript fallback!")
            return True
        
        print("Could not find or click media insertion button using any method.")
        return False
    
    except Exception as e:
        print(f"❌ Error in insert_new_media: {str(e)}")
        return False

def click_tomorrow(page):
    """
    Finds and clicks tomorrow's date in the calendar picker.
    """
    try:
        # Calculate target date (Tomorrow)
        tomorrow = date.today() + timedelta(days=1)
        target_day = tomorrow.day
        print(f"Targeting tomorrow's date: {target_day}")

        # Primary selectors: CSS and XPath
        approaches = [
            f"css=.dp__cell_inner:not(.dp__cell_disabled):text-is('{target_day}')",
            f"xpath=//div[contains(@class, 'dp__cell_inner') and not(contains(@class, 'dp__cell_disabled')) and text()='{target_day}']"
        ]

        for selector in approaches:
            try:
                locator = page.locator(selector)
                if locator.count() > 0:
                    locator.first.scroll_into_view_if_needed()
                    locator.first.click(force=True)
                    print(f"Success: Day {target_day} clicked using browser locator.")
                    return True
            except:
                continue

        # Fallback: JavaScript execution (for Shadow DOM or hidden elements)
        js_success = page.evaluate(f'''(day) => {{
            const elements = Array.from(document.querySelectorAll('.dp__cell_inner:not(.dp__cell_disabled)'));
            const target = elements.find(el => el.textContent.trim() === day.toString());
            if (target) {{
                target.scrollIntoView({{behavior: 'instant', block: 'center'}});
                target.click();
                return true;
            }}
            return false;
        }}''', target_day)

        if js_success:
            print(f"Success: Day {target_day} clicked via JavaScript.")
        
        return js_success

    except Exception as e:
        print(f"❌ Error while trying to click tomorrow's date: {str(e)}")
        return False

def click_time(page):
    """
    Attempt to find and click the time/timer element using multiple approaches.
    """
    try:
        # List of selectors to try
        selectors = [
            # Direct CSS selector
            "#tab-timer",
            # Shadow DOM JavaScript path
            "document.querySelector(\"#privacy-web-publication\").shadowRoot.querySelector(\"div > div > privacy-web-contenteditor\").shadowRoot.querySelector(\"#tab-timer\")",
            # XPath
            "//*[@id=\"tab-timer\"]"
        ]

        # Try each selector
        for selector in selectors:
            try:
                print(f"⏳ Trying time element selector: {selector}")
                
                # Handle different selector types
                if selector.startswith("document.querySelector"):
                    # JavaScript selector
                    time_clicked = page.evaluate(f'''() => {{
                        const timeElement = {selector};
                        if (timeElement) {{
                            timeElement.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            timeElement.click();
                            return true;
                        }}
                        return false;
                    }}''')
                    
                    if time_clicked:
                        print(f"✅ Successfully clicked time element with JS selector")
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
                            xpath_elements.first.click(force=True)
                            print(f"✅ Successfully clicked time element with XPath")
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
                            css_elements.first.click(force=True)
                            print(f"✅ Successfully clicked time element with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"❌ Failed with time element selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("⏳ Trying JavaScript fallback approach for time element...")
        fallback_clicked = page.evaluate('''() => {
            // Try finding time-related elements
            const timeSelectors = [
                '#tab-timer',
                '.el-tabs__item.is-top[aria-controls="pane-timer"]',
                'div[aria-selected="false"][role="tab"][id="tab-timer"]'
            ];
            
            for (const selector of timeSelectors) {
                const timeElements = document.querySelectorAll(selector);
                for (const timeEl of timeElements) {
                    if (timeEl) {
                        timeEl.scrollIntoView({behavior: 'smooth', block: 'center'});
                        timeEl.click();
                        return true;
                    }
                }
            }
            return false;
        }''')
        
        if fallback_clicked:
            print("✅ Successfully clicked time element using JavaScript fallback!")
            return True
        
        print("Could not find or click time element using any method.")
        return False
    
    except Exception as e:
        print(f"❌ Error in click_time: {str(e)}")
        return False

def click_hour(page):
    """
    Attempt to find and click the hour selection button using multiple approaches.
    """
    try:
        # List of selectors to try
        selectors = [
            # Direct CSS selector
            "#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div:nth-child(1) > button.dp__time_display.dp__time_display_block.dp--time-overlay-btn",
            # Shadow DOM JavaScript path
            "document.querySelector(\"#privacy-web-publication\").shadowRoot.querySelector(\"div > div > privacy-web-contenteditor\").shadowRoot.querySelector(\"#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div:nth-child(1) > button.dp__time_display.dp__time_display_block.dp--time-overlay-btn\")",
            # XPath
            "//*[@id=\"pane-timer\"]/div/div[2]/div/div/div/div/div/div/div/div/div/div/div[1]/button[2]"
        ]

        # Try each selector
        for selector in selectors:
            try:
                print(f"⏳ Trying hour selection selector: {selector}")
                
                # Handle different selector types
                if selector.startswith("document.querySelector"):
                    # JavaScript selector
                    button_clicked = page.evaluate(f'''() => {{
                        const hourElement = {selector};
                        if (hourElement) {{
                            hourElement.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            hourElement.click();
                            return true;
                        }}
                        return false;
                    }}''')
                    
                    if button_clicked:
                        print(f"✅ Successfully clicked hour selection button with JS selector")
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
                            xpath_elements.first.click(force=True)
                            print(f"✅ Successfully clicked hour selection button with XPath")
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
                            css_elements.first.click(force=True)
                            print(f"✅ Successfully clicked hour selection button with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"❌ Failed with hour selection selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("⏳ Trying JavaScript fallback approach for hour selection...")
        fallback_clicked = page.evaluate('''() => {
            // Try finding hour selection buttons
            const hourSelectors = [
                'button.dp__time_display.dp__time_display_block.dp--time-overlay-btn',
                '#pane-timer button[aria-label="Open hours overlay"]',
                'button[type="button"][tabindex="0"][class*="dp__time_display"]'
            ];
            
            for (const selector of hourSelectors) {
                const hourElements = document.querySelectorAll(selector);
                for (const hourEl of hourElements) {
                    if (hourEl) {
                        hourEl.scrollIntoView({behavior: 'smooth', block: 'center'});
                        hourEl.click();
                        return true;
                    }
                }
            }
            return false;
        }''')
        
        if fallback_clicked:
            print("✅ Successfully clicked hour selection button using JavaScript fallback!")
            return True
        
        print("Could not find or click hour selection button using any method.")
        return False
    
    except Exception as e:
        print(f"❌ Error in click_hour: {str(e)}")
        return False

def click_00_hour(page):
    """
    Attempt to find and click the '00' time selection using multiple approaches.
    """
    try:
        # List of selectors to try
        selectors = [
            # Direct CSS selector
            "#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(2) > div:nth-child(1) > div",
            # Shadow DOM JavaScript path
            "document.querySelector(\"#privacy-web-publication\").shadowRoot.querySelector(\"div > div > privacy-web-contenteditor\").shadowRoot.querySelector(\"#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(2) > div:nth-child(1) > div\")",
            # XPath
            "//*[@id=\"pane-timer\"]/div/div[2]/div/div/div/div/div/div/div/div/div/div/div[4]/div/div[2]/div[1]/div"
        ]

        # Try each selector
        for selector in selectors:
            try:
                print(f"⏳ Trying '00' time selection selector: {selector}")
                
                # Handle different selector types
                if selector.startswith("document.querySelector"):
                    # JavaScript selector
                    button_clicked = page.evaluate(f'''() => {{
                        const timeElement = {selector};
                        if (timeElement) {{
                            timeElement.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            timeElement.click();
                            return true;
                        }}
                        return false;
                    }}''')
                    
                    if button_clicked:
                        print(f"✅ Successfully clicked '00' time selection with JS selector")
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
                            xpath_elements.first.click(force=True)
                            print(f"✅ Successfully clicked '00' time selection with XPath")
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
                            css_elements.first.click(force=True)
                            print(f"✅ Successfully clicked '00' time selection with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"❌ Failed with '00' time selection selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("⏳ Trying JavaScript fallback approach for '00' time selection...")
        fallback_clicked = page.evaluate('''() => {
            // Try finding '00' time selection elements
            const timeSelectors = [
                '.dp__overlay_cell.dp__overlay_cell_pad:contains("00")',
                'div[class*="dp__overlay_cell"]:contains("00")',
                '.dp--overlay-absolute div div:contains("00")'
            ];
            
            for (const selector of timeSelectors) {
                const timeElements = document.querySelectorAll(selector);
                for (const timeEl of timeElements) {
                    if (timeEl) {
                        timeEl.scrollIntoView({behavior: 'smooth', block: 'center'});
                        timeEl.click();
                        return true;
                    }
                }
            }
            return false;
        }''')
        
        if fallback_clicked:
            print("✅ Successfully clicked '00' time selection using JavaScript fallback!")
            return True
        
        print("Could not find or click '00' time selection using any method.")
        return False
    
    except Exception as e:
        print(f"❌ Error in click_00: {str(e)}")
        return False

def click_hour_up(page):
    """
    Attempt to find and click the hour up button using multiple approaches.
    """
    try:
        # List of selectors to try
        selectors = [
            # Direct CSS selector
            "#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div:nth-child(1) > button:nth-child(1) > svg",
            # Shadow DOM JavaScript path
            "document.querySelector(\"#privacy-web-publication\").shadowRoot.querySelector(\"div > div > privacy-web-contenteditor\").shadowRoot.querySelector(\"#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div:nth-child(1) > button:nth-child(1) > svg\")",
            # XPath
            "//*[@id=\"pane-timer\"]/div/div[2]/div/div/div/div/div/div/div/div/div/div/div[1]/button[1]/svg"
        ]

        # Try each selector
        for selector in selectors:
            try:
                print(f"⏳ Trying hour up button selector: {selector}")
                
                # Handle different selector types
                if selector.startswith("document.querySelector"):
                    # JavaScript selector
                    button_clicked = page.evaluate(f'''() => {{
                        const svgElement = {selector};
                        if (svgElement) {{
                            svgElement.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            svgElement.closest('button').click();
                            return true;
                        }}
                        return false;
                    }}''')
                    
                    if button_clicked:
                        print(f"✅ Successfully clicked hour up button with JS selector")
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
                            xpath_elements.first.click(force=True)
                            print(f"✅ Successfully clicked hour up button with XPath")
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
                            css_elements.first.click(force=True)
                            print(f"✅ Successfully clicked hour up button with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"❌ Failed with hour up button selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("⏳ Trying JavaScript fallback approach for hour up button...")
        fallback_clicked = page.evaluate('''() => {
            // Try finding the specific SVG for the hour up button
            const svgPath = "M24.943 19.057l-8-8c-0.521-0.521-1.365-0.521-1.885 0l-8 8c-0.52 0.52-0.52 1.365 0 1.885s1.365 0.52 1.885 0l7.057-7.057c0 0 7.057 7.057 7.057 7.057 0.52 0.52 1.365 0.52 1.885 0s0.52-1.365 0-1.885z";
            const svgs = document.querySelectorAll('svg');
            for (const svg of svgs) {
                const paths = svg.querySelectorAll('path');
                for (const path of paths) {
                    if (path.getAttribute('d') === svgPath) {
                        svg.closest('button').click();
                        return true;
                    }
                }
            }
            return false;
        }''')
        
        if fallback_clicked:
            print("✅ Successfully clicked hour up button using JavaScript fallback!")
            return True
        
        print("Could not find or click hour up button using any method.")
        return False
    
    except Exception as e:
        print(f"❌ Error in click_hour_up: {str(e)}")
        return False

def click_minute(page):
    """
    Attempt to find and click the minute selection button using multiple approaches.
    """
    try:
        # List of selectors to try
        selectors = [
            # Direct CSS selector
            "#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div:nth-child(3) > button.dp__time_display.dp__time_display_block.dp--time-overlay-btn",
            # Shadow DOM JavaScript path
            "document.querySelector(\"#privacy-web-publication\").shadowRoot.querySelector(\"div > div > privacy-web-contenteditor\").shadowRoot.querySelector(\"#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div:nth-child(3) > button.dp__time_display.dp__time_display_block.dp--time-overlay-btn\")",
            # XPath
            "//*[@id=\"pane-timer\"]/div/div[2]/div/div/div/div/div/div/div/div/div/div/div[3]/button[2]"
        ]

        # Try each selector
        for selector in selectors:
            try:
                print(f"⏳ Trying minute selection selector: {selector}")
                
                # Handle different selector types
                if selector.startswith("document.querySelector"):
                    # JavaScript selector
                    button_clicked = page.evaluate(f'''() => {{
                        const minuteElement = {selector};
                        if (minuteElement) {{
                            minuteElement.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            minuteElement.click();
                            return true;
                        }}
                        return false;
                    }}''')
                    
                    if button_clicked:
                        print(f"✅ Successfully clicked minute selection button with JS selector")
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
                            xpath_elements.first.click(force=True)
                            print(f"✅ Successfully clicked minute selection button with XPath")
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
                            css_elements.first.click(force=True)
                            print(f"✅ Successfully clicked minute selection button with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"❌ Failed with minute selection selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("⏳ Trying JavaScript fallback approach for minute selection...")
        fallback_clicked = page.evaluate('''() => {
            // Try finding minute selection buttons
            const minuteSelectors = [
                'button.dp__time_display.dp__time_display_block.dp--time-overlay-btn[aria-label="Open minutes overlay"]',
                '#pane-timer button[tabindex="0"]:contains("01")',
                'button[type="button"][class*="dp__time_display"]:contains("01")'
            ];
            
            for (const selector of minuteSelectors) {
                const minuteElements = document.querySelectorAll(selector);
                for (const minuteEl of minuteElements) {
                    if (minuteEl) {
                        minuteEl.scrollIntoView({behavior: 'smooth', block: 'center'});
                        minuteEl.click();
                        return true;
                    }
                }
            }
            return false;
        }''')
        
        if fallback_clicked:
            print("✅ Successfully clicked minute selection button using JavaScript fallback!")
            return True
        
        print("Could not find or click minute selection button using any method.")
        return False
    
    except Exception as e:
        print(f"❌ Error in click_minute: {str(e)}")
        return False

def click_00_minute(page):
    """
    Attempt to find and click the 00 minute button using multiple approaches.
    """
    try:
        # List of selectors to try
        selectors = [
            # Direct CSS selector
            "#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(2) > div:nth-child(1) > div",
            # Shadow DOM JavaScript path
            "document.querySelector(\"#privacy-web-publication\").shadowRoot.querySelector(\"div > div > privacy-web-contenteditor\").shadowRoot.querySelector(\"#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(2) > div:nth-child(1) > div\")",
            # XPath
            "//*[@id=\"pane-timer\"]/div/div[2]/div/div/div/div/div/div/div/div/div/div/div[4]/div/div[2]/div[1]/div"
        ]

        # Try each selector
        for selector in selectors:
            try:
                print(f"⏳ Trying 00 minute selector: {selector}")
                
                # Handle different selector types
                if selector.startswith("document.querySelector"):
                    # JavaScript selector
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
                        print(f"✅ Successfully clicked 00 minute button with JS selector")
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
                            xpath_elements.first.click(force=True)
                            print(f"✅ Successfully clicked 00 minute button with XPath")
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
                            css_elements.first.click(force=True)
                            print(f"✅ Successfully clicked 00 minute button with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"❌ Failed with 00 minute selector {selector}: {str(e)}")
                continue
        
        print("Could not find or click 00 minute button using any method.")
        return False
    
    except Exception as e:
        print(f"❌ Error in click_00_minute: {str(e)}")
        return False

def click_On_Minute_Up_btn(page):
    """
    Attempt to find and click the 'Minute Up' button using multiple approaches.
    """
    try:
        # List of selectors to try
        selectors = [
            # Direct CSS selector
            "#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div:nth-child(3) > button:nth-child(1)",
            # Alternative CSS selectors
            "button[aria-label='Increment minutes']",
            "button.dp__btn.dp__inc_dec_button",
            "button:has(svg[viewBox='0 0 32 32'])",
            # JavaScript path
            "document.querySelector(\"#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div:nth-child(3) > button:nth-child(1)\")",
            # XPath
            "//*[@id=\"pane-timer\"]/div/div[2]/div/div/div/div/div/div/div/div/div/div/div[3]/button[1]",
            # Alternative XPaths
            "//button[@aria-label='Increment minutes']",
            "//button[contains(@class, 'dp__inc_dec_button')]",
            "//button[svg[@viewBox='0 0 32 32']]"
        ]

        # Try each selector
        for selector in selectors:
            try:
                print(f"⏳ Trying Minute Up button selector: {selector}")
                
                # Handle different selector types
                if selector.startswith("document.querySelector"):
                    # JavaScript selector
                    button_clicked = page.evaluate(f'''() => {{
                        const button = {selector};
                        if (button) {{
                            button.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            button.click();
                            return true;
                        }}
                        return false;
                    }}''')
                    
                    if button_clicked:
                        print(f"✅ Successfully clicked Minute Up button with JS selector")
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
                            xpath_elements.first.click(force=True)
                            print(f"✅ Successfully clicked Minute Up button with XPath")
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
                            css_elements.first.click(force=True)
                            print(f"✅ Successfully clicked Minute Up button with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"❌ Failed with Minute Up button selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("⏳ Trying JavaScript fallback approach for Minute Up button...")
        fallback_clicked = page.evaluate('''() => {
            // Try finding button elements with minute increment attributes
            const buttonSelectors = [
                'button[aria-label*="Increment minute"]',
                'button[aria-label*="minute"]',
                'button.dp__inc_dec_button',
                'button:has(svg)'
            ];
            
            for (const selector of buttonSelectors) {
                const buttons = document.querySelectorAll(selector);
                for (const button of buttons) {
                    // Check if it's likely the minute up button by position or context
                    const ariaLabel = button.getAttribute('aria-label') || '';
                    if (ariaLabel.includes('minute') || ariaLabel.includes('Minute')) {
                        button.scrollIntoView({behavior: 'smooth', block: 'center'});
                        button.click();
                        return true;
                    }
                    
                    // Check if it contains the specific SVG path
                    const svgPath = button.querySelector('path[d*="24.943 19.057"]');
                    if (svgPath) {
                        button.scrollIntoView({behavior: 'smooth', block: 'center'});
                        button.click();
                        return true;
                    }
                }
            }
            
            return false;
        }''')
        
        if fallback_clicked:
            print("✅ Successfully clicked Minute Up button using JavaScript fallback!")
            return True
        
        print("Could not find or click Minute Up button using any method.")
        return False
    
    except Exception as e:
        print(f"❌ Error in click_On_Minute_Up_btn: {str(e)}")
        return False

def click_00_minute(page):
    """
    Attempt to find and click the 00 minute button using multiple approaches.
    """
    try:
        # List of selectors to try
        selectors = [
            # Direct CSS selector
            "#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(2) > div:nth-child(1) > div",
            
            # Shadow DOM JavaScript path
            "document.querySelector('#privacy-web-publisher').shadowRoot.querySelector('#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(2) > div:nth-child(1) > div')",
            
            # XPath
            "//*[@id='pane-timer']/div/div[2]/div/div/div/div/div/div/div/div/div/div/div[4]/div/div[2]/div[1]/div"
        ]
        
        for selector in selectors:
            try:
                if selector.startswith("document.querySelector"):
                    # JavaScript selector (Shadow DOM)
                    button_clicked = page.evaluate(f'''() => {{
                        const element = {selector};
                        if (element) {{
                            element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            element.click();
                            return true;
                        }}
                        return false;
                    }}''')
                    if button_clicked: return True
                
                elif selector.startswith('/'):
                    # XPath selector
                    xpath_elements = page.locator(f"xpath={selector}")
                    if xpath_elements.count() > 0:
                        # Force visibility via JS
                        page.evaluate(f'''(xpath) => {{
                            const element = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                            if (element) {{
                                element.style.opacity = '1';
                                element.style.visibility = 'visible';
                                element.style.display = 'block';
                            }}
                        }}''', selector)
                        xpath_elements.first.scroll_into_view_if_needed()
                        xpath_elements.first.click(force=True)
                        return True
                else:
                    # CSS selector
                    css_elements = page.locator(selector)
                    if css_elements.count() > 0:
                        page.evaluate(f'''(css) => {{
                            const element = document.querySelector(css);
                            if (element) {{
                                element.style.opacity = '1';
                                element.style.visibility = 'visible';
                                element.style.display = 'block';
                            }}
                        }}''', selector)
                        css_elements.first.scroll_into_view_if_needed()
                        css_elements.first.click(force=True)
                        return True
            except Exception as e:
                continue
        return False
    except Exception as e:
        print(f"❌ Error in click_00_minute: {str(e)}")
        return False

def click_05_minute(page):
    """
    Attempt to find and click the 05 minute button using multiple approaches.
    """
    try:
        selectors = [
            "#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(2) > div:nth-child(2) > div",
            "document.querySelector('#privacy-web-publisher').shadowRoot.querySelector('#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(2) > div:nth-child(2) > div')",
            "//*[@id='pane-timer']/div/div[2]/div/div/div/div/div/div/div/div/div/div/div[4]/div/div[2]/div[2]/div"
        ]
        for selector in selectors:
            try:
                if selector.startswith("document.querySelector"):
                    button_clicked = page.evaluate(f"() => {{ const el = {selector}; if(el) {{ el.scrollIntoView(); el.click(); return true; }} return false; }}")
                    if button_clicked: return True
                elif selector.startswith('/'):
                    elements = page.locator(f"xpath={selector}")
                    if elements.count() > 0:
                        elements.first.click(force=True)
                        return True
                else:
                    elements = page.locator(selector)
                    if elements.count() > 0:
                        elements.first.click(force=True)
                        return True
            except: continue
        return False
    except Exception as e:
        print(f"❌ Error in click_05_minute: {str(e)}")
        return False

def click_10_minute(page):
    """
    Attempt to find and click the 10 minute button using multiple approaches.
    """
    try:
        selectors = [
            "#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(2) > div:nth-child(3) > div",
            "document.querySelector('#privacy-web-publisher').shadowRoot.querySelector('#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(2) > div:nth-child(3) > div')",
            "//*[@id='pane-timer']/div/div[2]/div/div/div/div/div/div/div/div/div/div/div[4]/div/div[2]/div[3]/div"
        ]
        for selector in selectors:
            try:
                if selector.startswith("document.querySelector"):
                    if page.evaluate(f"() => {{ const el = {selector}; if(el) {{ el.click(); return true; }} return false; }}"): return True
                else:
                    el = page.locator(f"xpath={selector}" if selector.startswith('/') else selector)
                    if el.count() > 0:
                        el.first.click(force=True)
                        return True
            except: continue
        return False
    except Exception as e:
        print(f"❌ Error in click_10_minute: {str(e)}")
        return False

def click_15_minute(page):
    """ Attempt to click 15 min """
    try:
        selectors = [
            "#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(3) > div:nth-child(1) > div",
            "document.querySelector('#privacy-web-publisher').shadowRoot.querySelector('#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(3) > div:nth-child(1) > div')",
            "//*[@id='pane-timer']/div/div[2]/div/div/div/div/div/div/div/div/div/div/div[4]/div/div[3]/div[1]/div"
        ]
        for s in selectors:
            try:
                if s.startswith("document"):
                    if page.evaluate(f"() => {{ const e = {s}; if(e) {{ e.click(); return true; }} return false; }}"): return True
                else:
                    loc = page.locator(f"xpath={s}" if s.startswith('/') else s)
                    if loc.count() > 0:
                        loc.first.click(force=True)
                        return True
            except: continue
        return False
    except Exception as e:
        print(f"❌ Error in click_15_minute: {str(e)}")
        return False

def click_20_minute(page):
    """ Attempt to click 20 min """
    try:
        selectors = [
            "#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(3) > div:nth-child(2) > div",
            "document.querySelector('#privacy-web-publisher').shadowRoot.querySelector('#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(3) > div:nth-child(2) > div')",
            "//*[@id='pane-timer']/div/div[2]/div/div/div/div/div/div/div/div/div/div/div[4]/div/div[3]/div[2]/div"
        ]
        for s in selectors:
            try:
                if s.startswith("document"):
                    if page.evaluate(f"() => {{ const e = {s}; if(e) {{ e.click(); return true; }} return false; }}"): return True
                else:
                    loc = page.locator(f"xpath={s}" if s.startswith('/') else s)
                    if loc.count() > 0:
                        loc.first.click(force=True)
                        return True
            except: continue
        return False
    except Exception as e:
        print(f"❌ Error in click_20_minute: {str(e)}")
        return False

def click_25_minute(page):
    """ Attempt to click 25 min """
    try:
        selectors = [
            "#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(3) > div:nth-child(3) > div",
            "document.querySelector('#privacy-web-publisher').shadowRoot.querySelector('#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(3) > div:nth-child(3) > div')",
            "//*[@id='pane-timer']/div/div[2]/div/div/div/div/div/div/div/div/div/div/div[4]/div/div[3]/div[3]/div"
        ]
        for s in selectors:
            try:
                if s.startswith("document"):
                    if page.evaluate(f"() => {{ const e = {s}; if(e) {{ e.click(); return true; }} return false; }}"): return True
                else:
                    loc = page.locator(f"xpath={s}" if s.startswith('/') else s)
                    if loc.count() > 0:
                        loc.first.click(force=True)
                        return True
            except: continue
        return False
    except Exception as e:
        print(f"❌ Error in click_25_minute: {str(e)}")
        return False

def click_30_minute(page):
    """ Attempt to click 30 min """
    try:
        selectors = [
            "#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(4) > div:nth-child(1) > div",
            "document.querySelector('#privacy-web-publisher').shadowRoot.querySelector('#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(4) > div:nth-child(1) > div')",
            "//*[@id='pane-timer']/div/div[2]/div/div/div/div/div/div/div/div/div/div/div[4]/div/div[4]/div[1]/div"
        ]
        for s in selectors:
            try:
                if s.startswith("document"):
                    if page.evaluate(f"() => {{ const e = {s}; if(e) {{ e.click(); return true; }} return false; }}"): return True
                else:
                    loc = page.locator(f"xpath={s}" if s.startswith('/') else s)
                    if loc.count() > 0:
                        loc.first.click(force=True)
                        return True
            except: continue
        return False
    except Exception as e:
        print(f"❌ Error in click_30_minute: {str(e)}")
        return False

def click_35_minute(page):
    """ Attempt to click 35 min """
    try:
        selectors = [
            "#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(4) > div:nth-child(2) > div",
            "document.querySelector('#privacy-web-publisher').shadowRoot.querySelector('#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(4) > div:nth-child(2) > div')",
            "//*[@id='pane-timer']/div/div[2]/div/div/div/div/div/div/div/div/div/div/div[4]/div/div[4]/div[2]/div"
        ]
        for s in selectors:
            try:
                if s.startswith("document"):
                    if page.evaluate(f"() => {{ const e = {s}; if(e) {{ e.click(); return true; }} return false; }}"): return True
                else:
                    loc = page.locator(f"xpath={s}" if s.startswith('/') else s)
                    if loc.count() > 0:
                        loc.first.click(force=True)
                        return True
            except: continue
        return False
    except Exception as e:
        print(f"❌ Error in click_35_minute: {str(e)}")
        return False

def click_40_minute(page):
    """ Attempt to click 40 min """
    try:
        selectors = [
            "#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(4) > div:nth-child(3) > div",
            "document.querySelector('#privacy-web-publisher').shadowRoot.querySelector('#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(4) > div:nth-child(3) > div')",
            "//*[@id='pane-timer']/div/div[2]/div/div/div/div/div/div/div/div/div/div/div[4]/div/div[4]/div[3]/div"
        ]
        for s in selectors:
            try:
                if s.startswith("document"):
                    if page.evaluate(f"() => {{ const e = {s}; if(e) {{ e.click(); return true; }} return false; }}"): return True
                else:
                    loc = page.locator(f"xpath={s}" if s.startswith('/') else s)
                    if loc.count() > 0:
                        loc.first.click(force=True)
                        return True
            except: continue
        return False
    except Exception as e:
        print(f"❌ Error in click_40_minute: {str(e)}")
        return False

def click_45_minute(page):
    """ Attempt to click 45 min """
    try:
        selectors = [
            "#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(5) > div:nth-child(1) > div",
            "document.querySelector('#privacy-web-publisher').shadowRoot.querySelector('#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(5) > div:nth-child(1) > div')",
            "//*[@id='pane-timer']/div/div[2]/div/div/div/div/div/div/div/div/div/div/div[4]/div/div[5]/div[1]/div"
        ]
        for s in selectors:
            try:
                if s.startswith("document"):
                    if page.evaluate(f"() => {{ const e = {s}; if(e) {{ e.click(); return true; }} return false; }}"): return True
                else:
                    loc = page.locator(f"xpath={s}" if s.startswith('/') else s)
                    if loc.count() > 0:
                        loc.first.click(force=True)
                        return True
            except: continue
        return False
    except Exception as e:
        print(f"❌ Error in click_45_minute: {str(e)}")
        return False

def click_50_minute(page):
    """ Attempt to click 50 min """
    try:
        selectors = [
            "#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(5) > div:nth-child(2) > div",
            "document.querySelector('#privacy-web-publisher').shadowRoot.querySelector('#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(5) > div:nth-child(2) > div')",
            "//*[@id='pane-timer']/div/div[2]/div/div/div/div/div/div/div/div/div/div/div[4]/div/div[5]/div[2]/div"
        ]
        for s in selectors:
            try:
                if s.startswith("document"):
                    if page.evaluate(f"() => {{ const e = {s}; if(e) {{ e.click(); return true; }} return false; }}"): return True
                else:
                    loc = page.locator(f"xpath={s}" if s.startswith('/') else s)
                    if loc.count() > 0:
                        loc.first.click(force=True)
                        return True
            except: continue
        return False
    except Exception as e:
        print(f"❌ Error in click_50_minute: {str(e)}")
        return False

def click_55_minute(page):
    """ Attempt to click 55 min """
    try:
        selectors = [
            "#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(5) > div:nth-child(3) > div",
            "document.querySelector('#privacy-web-publisher').shadowRoot.querySelector('#pane-timer > div > div.dp__outer_menu_wrap > div > div > div > div > div > div > div > div > div > div > div.dp__overlay.dp--overlay-absolute > div > div:nth-child(5) > div:nth-child(3) > div')",
            "//*[@id='pane-timer']/div/div[2]/div/div/div/div/div/div/div/div/div/div/div[4]/div/div[5]/div[3]/div"
        ]
        for s in selectors:
            try:
                if s.startswith("document"):
                    if page.evaluate(f"() => {{ const e = {s}; if(e) {{ e.click(); return true; }} return false; }}"): return True
                else:
                    loc = page.locator(f"xpath={s}" if s.startswith('/') else s)
                    if loc.count() > 0:
                        loc.first.click(force=True)
                        return True
            except: continue
        return False
    except Exception as e:
        print(f"❌ Error in click_55_minute: {str(e)}")
        return False

def click_On_Aplicar_btn(page):
    """
    Attempt to find and click the 'Aplicar' button using multiple approaches.
    """
    try:
        # List of selectors to try - updated for Aplicar button
        selectors = [
            # Direct CSS selector
            "#el-id-9023-109 > div > div.component-button > button",
            # Shadow DOM JavaScript path
            "document.querySelector(\"#privacy-web-publisher\").shadowRoot.querySelector(\"#el-id-9023-109 > div > div.component-button > button\")",
            # XPath
            "//*[@id=\"el-id-9023-109\"]/div/div[2]/button",
            # Alternative XPath by button text
            "//button[contains(@class, 'el-button--gradient') and contains(span/span, 'Aplicar')]"
        ]

        # Try each selector
        for selector in selectors:
            try:
                print(f"⏳ Trying Aplicar button selector: {selector}")
                
                # Handle different selector types
                if selector.startswith("document.querySelector"):
                    # JavaScript selector
                    button_clicked = page.evaluate(f'''() => {{
                        const button = {selector};
                        if (button && !button.getAttribute('aria-disabled')) {{
                            button.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            button.click();
                            return true;
                        }}
                        return false;
                    }}''')
                    
                    if button_clicked:
                        print(f"✅ Successfully clicked Aplicar button with JS selector")
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
                            xpath_elements.first.click(force=True)
                            print(f"✅ Successfully clicked Aplicar button with XPath")
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
                            css_elements.first.click(force=True)
                            print(f"✅ Successfully clicked Aplicar button with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"❌ Failed with Aplicar button selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("⏳ Trying JavaScript fallback approach for Aplicar button...")
        fallback_clicked = page.evaluate('''() => {
            // Try finding button elements with 'Aplicar' text
            const buttonSelectors = [
                'button.el-button--gradient',
                'button[type="button"]',
                'button span span'
            ];
            
            for (const selector of buttonSelectors) {
                const buttons = document.querySelectorAll(selector);
                for (const button of buttons) {
                    const buttonText = button.innerText || button.textContent;
                    if (buttonText && buttonText.includes('Aplicar') && 
                        !button.getAttribute('aria-disabled')) {
                        button.scrollIntoView({behavior: 'smooth', block: 'center'});
                        button.click();
                        return true;
                    }
                }
            }
            return false;
        }''')
        
        if fallback_clicked:
            print("✅ Successfully clicked Aplicar button using JavaScript fallback!")
            return True
        
        print("Could not find or click Aplicar button using any method.")
        return False
    
    except Exception as e:
        print(f"❌ Error in click_On_Aplicar_btn: {str(e)}")
        return False

def click_aplicar_in_modal(page):
    """
    Attempt to find and click the 'Aplicar' button within the scheduling modal.
    Returns True if successful, False otherwise.
    """
    try:
        # Wait for modal to be visible
        modal = page.locator(".calendar.min-drawer.el-drawer.open")
        modal.wait_for(state="visible", timeout=10000)
        
        # Define multiple selectors to try
        selectors = [
            ".el-drawer__body .component-button button",  # Specific path
            "button:has-text('Aplicar')",  # Text-based
            "button.el-button--gradient"  # Class-based
        ]
        
        for selector in selectors:
            try:
                button = page.locator(selector)
                button.wait_for(state="visible", timeout=3000)
                
                # Check if enabled
                is_disabled = button.evaluate("el => el.getAttribute('aria-disabled') === 'true'")
                if is_disabled:
                    continue
                    
                button.scroll_into_view_if_needed()
                button.click(timeout=3000)
                return True
                
            except Exception as e:
                print(f"⏳ Attempt with selector '{selector}' failed: {str(e)}")
                continue
                
        print("All selector attempts failed")
        return False
        
    except Exception as e:
        print(f"❌ Error in click_aplicar_in_modal: {str(e)}")
        return False

def click_on_aplicar_button(page):
    """
    Attempt to find and click the 'Aplicar' (Apply) button using multiple approaches,
    specifically handling Shadow DOM and dynamic IDs.
    """
    try:
        # List of selectors based on your provided parameters
        selectors = [
            # 1. Your JSPath (Handles Shadow Root - Most likely to work)
            'document.querySelector("#privacy-web-publisher").shadowRoot.querySelector("#el-id-2923-31 > div > div.component-button button")',
            
            # 2. Direct CSS Selector from your parameters
            "#el-id-2923-31 > div > div.component-button",
            
            # 3. XPath from your parameters
            "xpath=//*[@id='el-id-2923-31']/div/div[2]",
            
            # 4. Playwright Text-based selector (Highly stable)
            "button:has-text('Aplicar')",
            
            # 5. Class-based selector (Ignores dynamic IDs)
            "div.component-button button.el-button--gradient"
        ]

        for selector in selectors:
            try:
                # Handle JavaScript/Shadow Root selectors
                if selector.startswith("document.querySelector"):
                    clicked = page.evaluate(f'''() => {{
                        const element = {selector};
                        if (element) {{
                            element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            element.click();
                            return true;
                        }}
                        return false;
                    }}''')
                    if clicked: return True

                # Handle XPath selectors
                elif selector.startswith("xpath="):
                    loc = page.locator(selector)
                    if loc.count() > 0:
                        loc.first.scroll_into_view_if_needed()
                        loc.first.click(force=True)
                        return True

                # Handle Standard CSS selectors
                else:
                    loc = page.locator(selector)
                    if loc.count() > 0:
                        # Ensure visibility via JS before clicking
                        page.evaluate(f'''(sel) => {{
                            const el = document.querySelector(sel);
                            if (el) {{
                                el.style.display = 'block';
                                el.style.visibility = 'visible';
                                el.style.opacity = '1';
                            }}
                        }}''', selector)
                        loc.first.click(force=True)
                        return True

            except Exception:
                continue

        # Final Fallback: Search for any button containing the text 'Aplicar'
        fallback_clicked = page.evaluate('''() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const target = buttons.find(b => b.textContent.includes('Aplicar'));
            if (target) {
                target.scrollIntoView({behavior: 'smooth', block: 'center'});
                target.click();
                return true;
            }
            return false;
        }''')
        
        return fallback_clicked

    except Exception as e:
        print(f"❌ Error in click_on_aplicar_button: {str(e)}")
        return False

def click_On_Avancar_btn(page):
    """
    Fast version - uses known working selector first with safe_click.
    """
    try:
        selectors = [
            {"selector": 'button.el-button--gradient.is-block', "options": {"timeout": 3000}},
            {"selector": 'button.el-button--gradient', "options": {}},
            {"selector": 'div.component-button > button', "options": {}},
            {"selector": 'button:has-text("Avançar")', "options": {}},
        ]

        for sel in selectors:
            if safe_click(page, sel["selector"], sel["options"]):
                return True

        return False

    except Exception as e:
        print(f"❌ Error clicking Avançar button: {str(e)}")
        return False

def click_On_Agendar_btn(page):
    """
    Simple method to click the Agendar button in shadow DOM
    """
    try:
        # Use JavaScript to find and click the button in shadow DOM
        result = page.evaluate('''() => {
            const shadowRoot = document.querySelector("#privacy-web-publisher").shadowRoot;
            const buttons = shadowRoot.querySelectorAll("button");
            for (const button of buttons) {
                if (button.textContent.includes('Agendar')) {
                    button.click();
                    return true;
                }
            }
            return false;
        }''')
        
        if result:
            print("Agendar button clicked successfully")
            return True
        else:
            print("Agendar button not found")
            return False
            
    except Exception as e:
        print(f"❌ Error clicking Agendar button: {e}")
        return False

def click_On_Concluido_btn(page):
    """
    Click on the 'Concluido' button inside the shadow DOM.
    """
    try:
        # List of selectors (prioritized: text-based)
        selectors = [
            # Text-based
            {"selector": 'button:has-text("Concluido"), button:has-text("Concluído")', "options": {}},
            # Shadow DOM with Playwright
            {"selector": '#privacy-web-publisher >> button.el-button--gradient:has-text("Concluido")', "options": {}},
            # Component structure
            {"selector": 'div.component-button button:has-text("Concluido")', "options": {}},
        ]

        for sel in selectors:
            if safe_click(page, sel["selector"], sel["options"]):
                return True

        # Fallback JavaScript (with null checks)
        fallback_clicked = page.evaluate('''() => {
            const host = document.querySelector('#privacy-web-publisher');
            if (!host || !host.shadowRoot) return false;
            const shadowRoot = host.shadowRoot;
            const buttons = shadowRoot.querySelectorAll('button');
            for (const button of buttons) {
                const text = button.textContent;
                if (text.includes('Concluido') || text.includes('Concluído')) {
                    button.click();
                    return true;
                }
            }
            return false;
        }''')

        if fallback_clicked:
            print("✅ Successfully clicked Concluido button via JavaScript")
            return True

        print("Could not find or click Concluido button")
        return False

    except Exception as e:
        print(f"❌ Error in click_On_Concluido_btn: {str(e)}")
        return False

def click_on_Confirmar_btn(page):
    """
    Attempt to find and click the Confirmar button using multiple approaches.
    """
    try:
        # List of selectors to try
        selectors = [
            # Direct CSS selector
            "button.el-button.el-button--primary.is-plain.btn-primary",
            # More specific CSS selector
            "div > div.ce-actions.ce-actions-many-items > div.ce-actions-icon > div:nth-child(7) > div.el-overlay > div > div > footer > span > button.el-button.el-button--primary.is-plain.btn-primary",
            # XPath
            "//button[contains(@class, 'el-button--primary') and contains(span/span, 'Confirmar')]",
            # Alternative XPath
            "//*[@id='privacy-web-publication']//div/div/privacy-web-contenteditor//div/div[2]/div[1]/div[6]/div[2]/div/div/footer/span/button[1]"
        ]

        # Try each selector
        for selector in selectors:
            try:
                print(f"⏳ Trying Confirmar button selector: {selector}")
                
                if selector.startswith('/'):
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
                            xpath_elements.first.click(force=True)
                            print(f"✅ Successfully clicked Confirmar button with XPath")
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
                            css_elements.first.click(force=True)
                            print(f"✅ Successfully clicked Confirmar button with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"❌ Failed with Confirmar button selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("⏳ Trying JavaScript fallback approach for Confirmar button...")
        fallback_clicked = page.evaluate('''() => {
            // Try finding button elements with Confirmar text
            const buttonSelectors = [
                'button.el-button.el-button--primary',
                'button.btn-primary',
                'button[type="button"]'
            ];
            
            for (const selector of buttonSelectors) {
                const buttons = document.querySelectorAll(selector);
                for (const button of buttons) {
                    if (button && button.textContent.includes('Confirmar')) {
                        button.scrollIntoView({behavior: 'smooth', block: 'center'});
                        button.click();
                        return true;
                    }
                }
            }
            return false;
        }''')
        
        if fallback_clicked:
            print("✅ Successfully clicked Confirmar button using JavaScript fallback!")
            return True
        
        print("Could not find or click Confirmar button using any method.")
        return False
    
    except Exception as e:
        print(f"❌ Error in click_on_Confirmar_btn: {str(e)}")
        return False

def set_expiration(page):
    """
    Attempt to find and interact with the expiration element using multiple approaches.
    """
    try:
        # List of selectors to try
        selectors = [
            # Direct CSS selector
            "div.ce-actions-icon > div:nth-child(5)",
            # Shadow DOM JavaScript path
            'document.querySelector("#privacy-web-publication").shadowRoot.querySelector("div > div > privacy-web-contenteditor").shadowRoot.querySelector("div > div.ce-actions.ce-actions-many-items > div.ce-actions-icon > div:nth-child(5)")',
            # XPath
            '//*[@id="privacy-web-publication"]//div/div/privacy-web-contenteditor//div/div[2]/div[1]/div[4]'
        ]

        # Try each selector
        for selector in selectors:
            try:
                print(f"⏳ Trying expiration element selector: {selector}")
                
                # Handle different selector types
                if selector.startswith("document.querySelector"):
                    # JavaScript selector
                    element_found = page.evaluate(f'''() => {{
                        const element = {selector};
                        if (element) {{
                            element.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            element.click();
                            return true;
                        }}
                        return false;
                    }}''')
                    
                    if element_found:
                        print(f"✅ Successfully interacted with expiration element using JS selector")
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
                            xpath_elements.first.click(force=True)
                            print(f"✅ Successfully interacted with expiration element using XPath")
                            return True
                        except Exception as e:
                            print(f"XPath interaction failed: {str(e)}")
                
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
                            css_elements.first.click(force=True)
                            print(f"✅ Successfully interacted with expiration element using CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector interaction failed: {str(e)}")
                
            except Exception as e:
                print(f"❌ Failed with expiration element selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("⏳ Trying JavaScript fallback approach for expiration element...")
        fallback_found = page.evaluate('''() => {
            // Try finding elements related to expiration
            const expirationSelectors = [
                'div.ce-button-svg.el-tooltip__trigger',
                'div.ce-actions-icon > div:nth-child(5)',
                'div[role="button"]'
            ];
            
            for (const selector of expirationSelectors) {
                const elements = document.querySelectorAll(selector);
                for (const element of elements) {
                    if (element) {
                        element.scrollIntoView({behavior: 'smooth', block: 'center'});
                        element.click();
                        return true;
                    }
                }
            }
            return false;
        }''')
        
        if fallback_found:
            print("✅ Successfully interacted with expiration element using JavaScript fallback!")
            return True
        
        print("Could not find or interact with expiration element using any method.")
        return False
    
    except Exception as e:
        print(f"❌ Error in set_expiration: {str(e)}")
        return False

def get_textarea_coordinates(page):
    coordinates = page.evaluate('''() => {
        const textarea = document.querySelector("textarea.ce-textarea");
        if (textarea) {
            const rect = textarea.getBoundingClientRect();
            return {
                x: rect.left + rect.width / 2, 
                y: rect.top + rect.height / 2
            };
        }
        return null;
    }''')
    return coordinates

def click_on_text_area(page):
    """
    Attempt to find and click the text area using the provided selectors.
    Retrieves and returns the coordinates (X, Y) of the text area element.
    """
    try:
        # List of selectors to try
        selectors = [
            # CSS selector
            "div > textarea",
            # JavaScript path
            "document.querySelector(\"#privacy-web-publication\").shadowRoot.querySelector(\"div > div > privacy-web-contenteditor\").shadowRoot.querySelector(\"div > textarea\")",
            # XPath
            "//*[@id=\"privacy-web-publication\"]//div/div/privacy-web-contenteditor//div/textarea"
        ]

        for selector in selectors:
            try:
                print(f"⏳ Trying text area selector: {selector}")
                
                if selector.startswith("document.querySelector"):
                    # Handle JavaScript path
                    coords = page.evaluate(f'''() => {{
                        const textarea = {selector};
                        if (textarea) {{
                            const rect = textarea.getBoundingClientRect();
                            textarea.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                            textarea.focus();
                            textarea.click();
                            return {{ x: rect.left + window.scrollX, y: rect.top + window.scrollY }};
                        }}
                        return null;
                    }}''')
                    
                    if coords:
                        print(f"Text area coordinates (JS path): X = {coords['x']}, Y = {coords['y']}")
                        return coords

                elif selector.startswith('/'):
                    # Handle XPath
                    xpath_elements = page.locator(f"xpath={selector}")
                    if xpath_elements.count() > 0:
                        element = xpath_elements.first
                        bounding_box = element.bounding_box()
                        if bounding_box:
                            # Click and log coordinates
                            element.scroll_into_view_if_needed()
                            element.click()
                            coords = {"x": bounding_box["x"], "y": bounding_box["y"]}
                            print(f"Text area coordinates (XPath): X = {coords['x']}, Y = {coords['y']}")
                            return coords

                else:
                    # Handle CSS selector
                    css_elements = page.locator(selector)
                    if css_elements.count() > 0:
                        element = css_elements.first
                        bounding_box = element.bounding_box()
                        if bounding_box:
                            # Click and log coordinates
                            element.scroll_into_view_if_needed()
                            element.click()
                            coords = {"x": bounding_box["x"], "y": bounding_box["y"]}
                            print(f"Text area coordinates (CSS): X = {coords['x']}, Y = {coords['y']}")
                            return coords

            except Exception as e:
                print(f"❌ Failed with selector {selector}: {str(e)}")
                continue

        print("Failed to locate or interact with the text area using all selectors.")
        return None

    except Exception as e:
        print(f"❌ Error in click_on_text_area: {str(e)}")
        return None

def click_on_text_area_2(page):
    """
    Attempt to find and click the text area using multiple selectors.
    """
    try:
        # List of selectors to try
        selectors = [
            # CSS selector
            "div > textarea",
            # Shadow DOM JavaScript path
            "document.querySelector(\"#privacy-web-publication\").shadowRoot.querySelector(\"div > div > privacy-web-contenteditor\").shadowRoot.querySelector(\"div > textarea\")",
            # XPath
            "//*[@id=\"privacy-web-publication\"]//div/div/privacy-web-contenteditor//div/textarea"
        ]

        # Try each selector
        for selector in selectors:
            try:
                print(f"⏳ Trying text area selector: {selector}")
                
                # Handle JavaScript path
                if selector.startswith("document.querySelector"):
                    clicked = page.evaluate(f'''() => {{
                        const textarea = {selector};
                        if (textarea) {{
                            textarea.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                            textarea.focus();
                            textarea.click();
                            return true;
                        }}
                        return false;
                    }}''')
                    
                    if clicked:
                        print(f"✅ Successfully clicked text area with JS path selector.")
                        return True

                # Handle XPath
                elif selector.startswith('/'):
                    xpath_elements = page.locator(f"xpath={selector}")
                    if xpath_elements.count() > 0:
                        element = xpath_elements.first
                        element.scroll_into_view_if_needed()
                        element.click()
                        print(f"✅ Successfully clicked text area with XPath.")
                        return True

                # Handle CSS selector
                else:
                    css_elements = page.locator(selector)
                    if css_elements.count() > 0:
                        element = css_elements.first
                        element.scroll_into_view_if_needed()
                        element.click()
                        print(f"✅ Successfully clicked text area with CSS selector.")
                        return True

            except Exception as e:
                print(f"❌ Failed with selector {selector}: {str(e)}")
                continue

        print("Failed to locate or interact with the text area using all selectors.")
        return False

    except Exception as e:
        print(f"❌ Error in click_on_text_area_2: {str(e)}")
        return False

def safe_click(page, selector, options=None):
    """
    Reusable helper to safely click an element with retries, waits, and visibility forcing.
    Options: is_xpath (bool), is_js (bool), timeout (int), retries (int), is_switch (bool).
    """
    options = options or {}
    is_xpath = options.get('is_xpath', False)
    is_js = options.get('is_js', False)
    timeout = options.get('timeout', 5000)
    retries = options.get('retries', 3)
    is_switch = options.get('is_switch', False)

    for attempt in range(retries):
        try:
            if is_js:
                # Execute JS selector
                clicked = page.evaluate(selector)
                if clicked:
                    return True
            else:
                locator_str = f"xpath={selector}" if is_xpath else selector
                elements = page.locator(locator_str)

                if elements.count() == 0:
                    raise Exception("Element not found")

                element = elements.first
                # Wait for visibility/attachment
                element.wait_for(state="visible", timeout=timeout)

                # Force visibility via JS
                page.evaluate('''(el) => {
                    el.style.opacity = '1';
                    el.style.visibility = 'visible';
                    el.style.display = 'block';
                    el.style.pointerEvents = 'auto';
                }''', element.element_handle())

                # Scroll and click
                element.scroll_into_view_if_needed()
                if is_switch:
                    # Handle switch toggle
                    page.evaluate('''(el) => {
                        if (el.tagName === 'INPUT') {
                            el.checked = !el.checked;
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                        } else {
                            el.click();
                        }
                    }''', element.element_handle())
                else:
                    element.click(force=True, timeout=timeout)
                return True
        except Exception as e:
            print(f"⏳ Attempt {attempt + 1} failed for selector '{selector}': {str(e)}")
            # Log HTML snippet for debugging
            try:
                html_snippet = page.inner_html('body')[:500]  # Truncate for brevity
                print(f"HTML snippet: {html_snippet}")
            except:
                pass
            time.sleep(1)  # Short delay before retry
    return False

def click_on_menu(page):
    """
    Attempt to find and click the 'Menu' button (avatar) using multiple approaches.
    Prioritizes the specific avatar button identified and handles Shadow DOM if present.
    """
    print("⏳ Attempting to click the 'Menu' button...")
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
                print(f"⏳ Trying avatar selector: {selector}")
                # Playwright's locator handles CSS and XPath automatically if prefixed
                locator = page.locator(selector)
                if locator.count() > 0:
                    # Use Playwright's built-in waiting and clicking capabilities
                    # force=True can help if Playwright thinks it's not interactable,
                    # but it's often better to ensure proper waits.
                    locator.first.scroll_into_view_if_needed()
                    locator.first.click(timeout=5000) # Add a timeout for the click operation
                    print(f"✅ Successfully clicked avatar button with selector: {selector}")
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
                    print(f"⏳ Trying Shadow DOM internal selector: {internal_selector}")
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
                        print(f"✅ Successfully clicked Shadow DOM menu button with internal selector: {internal_selector}")
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
            print("✅ Successfully clicked Menu button using generic JavaScript fallback.")
            return True

        print("Could not find or click Menu button using any method.")
        return False

    except Exception as e:
        print(f"❌ An unexpected error occurred in click_on_menu: {str(e)}")
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
                            console.error('❌ Error clicking sair:', e);
                        }}
                        return false;
                    }}''')
                    if clicked:
                        print("✅ Sair clicked successfully with Shadow DOM selector")
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
                            print("✅ Sair clicked successfully with XPath")
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
                            print("✅ Sair clicked successfully with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")

            except Exception as e:
                print(f"❌ Failed with sair selector {selector}: {str(e)}")
                continue

        # Fallback JavaScript approach with comprehensive search
        print("⏳ Trying JavaScript fallback approach for sair click...")
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
            print("✅ Sair clicked successfully using JavaScript fallback!")
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

    # ADDITION: Define user_data here to access it in finally (for cleanup)
    user_data = os.path.join(os.environ['LOCALAPPDATA'], r"Google\Chrome\User Data\Automation")

    # 2. Launch Browser via the Native Hook method
    try:
        pw, context, browser_process = open_chrome_in_privacy_login_page()
        page = context.pages[0]  # Grab the active Privacy board page
        print("✅ Browser launched successfully")
    except Exception as e:
        error_msg = f"❌ Failed to launch or hook browser: {e}"
        print(error_msg)
        log_error_to_file(error_msg) # Log the error
        cleanup(pw, context, browser_process)
        sys.exit(1) # Exit with an error code

    # 3. Automation and Interaction
    try:
        print("⏳ Waiting for page load...")
        page.wait_for_load_state("domcontentloaded")

        # Fullscreen Mode
        try:
            import pyautogui
            pyautogui.press('f11')
            page.wait_for_timeout(3000)
        except ImportError:
            warning_msg = "Warning: pyautogui not installed, skipping fullscreen."
            print(warning_msg)
            log_error_to_file(warning_msg) # Log the warning

        # region LOGIN OPERATION

        # region Try to insert username with retries
        max_retries = 3
        username_inserted = False # Flag to track if username was inserted

        for attempt in range(max_retries):
            print(f"\nAttempt {attempt + 1} to insert username...")
            if insert_username(page):
                print("✅ Username inserted successfully!")
                username_inserted = True
                break
            else:
                print(f"⏳ Attempt {attempt + 1} failed.")
                if attempt < max_retries - 1:
                    print("⏳ Waiting before next attempt...")
                    page.wait_for_timeout(2000)

        if not username_inserted:
            error_msg = "❌ Maybe you are already logged in or username insertion failed permanently!"
            print(error_msg)

        page.wait_for_timeout(3000)
        # endregion Try to insert username with retries

        # region Try to insert password with retries
        max_retries = 3
        password_inserted = False # Flag to track if password was inserted

        for attempt in range(max_retries):
            print(f"\nAttempt {attempt + 1} to insert password...")
            if insert_password(page):
                print("✅ Password inserted successfully!")
                password_inserted = True
                break
            else:
                print(f"⏳ Attempt {attempt + 1} failed.")
                if attempt < max_retries - 1:
                    print("⏳ Waiting before next attempt...")
                    page.wait_for_timeout(2000)

        if not password_inserted:
            error_msg = "❌ Maybe you are already logged in or password insertion failed permanently!"
            print(error_msg)

        page.wait_for_timeout(3000)
        # endregion Try to insert password with retries

        # region Try to click the Entrar button with retries
        max_retries = 3
        entrar_button_clicked = False # Flag to track if the button was clicked

        for attempt in range(max_retries):
            print(f"\nAttempt {attempt + 1} to click Entrar button...")
            if click_on_entrar_button(page):
                print("✅ ✅ Successfully clicked Entrar button!")
                entrar_button_clicked = True
                break
            else:
                print(f"⏳ Attempt {attempt + 1} failed.")
                if attempt < max_retries - 1:
                    print("⏳ Waiting before next attempt...")
                    page.wait_for_timeout(2000)

        if not entrar_button_clicked:
            error_msg = "❌ Failed to click Entrar button after all attempts."
            print(error_msg)

        page.wait_for_timeout(7000)
        # endregion Try to click the Entrar button with retries

        # endregion LOGIN OPERATION

        # region POST-LOGIN CHECK AND RETRY LOGIC
        print("Checking if logon screen still persists...")
        # Assuming functions like 'insert_username', 'insert_password', 'click_on_entrar_button' exist
        if insert_username(page) and insert_password(page) and click_on_entrar_button(page):
            print("Logon elements still available, trying to execute LOGIN OPERATION flow again.")
            # Re-execute the LOGIN OPERATION flow (you'd likely wrap the above "LOGIN OPERATION" region in a function or loop)
            # For demonstration, I'll repeat the core logic here. In a real script, refactor this into a function.

            # --- Start of repeated LOGIN OPERATION flow ---
            # Try to insert username with retries
            max_retries = 3
            username_inserted = False 
            for attempt in range(max_retries):
                if insert_username(page):
                    print("✅ Username inserted successfully (retry)!")
                    username_inserted = True
                    break
                else:
                    print(f"⏳ Attempt {attempt + 1} failed (retry).")
                    if attempt < max_retries - 1:
                        page.wait_for_timeout(2000)
            if not username_inserted:
                error_msg = "❌ Username insertion failed permanently on retry!"
                print(error_msg)
                 
            page.wait_for_timeout(3000)

            # Try to insert password with retries
            max_retries = 3
            password_inserted = False 
            for attempt in range(max_retries):
                if insert_password(page):
                    print("✅ Password inserted successfully (retry)!")
                    password_inserted = True
                    break
                else:
                    print(f"⏳ Attempt {attempt + 1} failed (retry).")
                    if attempt < max_retries - 1:
                        page.wait_for_timeout(2000)
            if not password_inserted:
                error_msg = "❌ Password insertion failed permanently on retry!"
                print(error_msg)
                
            page.wait_for_timeout(3000)

            # Try to click the Entrar button with retries
            max_retries = 3
            entrar_button_clicked = False 
            for attempt in range(max_retries):
                if click_on_entrar_button(page):
                    print("✅ ✅ Successfully clicked Entrar button (retry)!")
                    entrar_button_clicked = True
                    break
                else:
                    print(f"⏳ Attempt {attempt + 1} failed (retry).")
                    if attempt < max_retries - 1:
                        page.wait_for_timeout(2000)
            if not entrar_button_clicked:
                error_msg = "❌ Failed to click Entrar button after all attempts on retry."
                print(error_msg)
                 
            page.wait_for_timeout(7000)
            # --- End of repeated LOGIN OPERATION flow ---

            print("Checking if logon screen still persists after retry...")
            if insert_username(page) and insert_password(page) and click_on_entrar_button(page):
                error_msg = "Unable to login in Privacy VIP, aborting process to avoid account locking."
                print(error_msg)
                log_error_to_file(error_msg)
            else:
                # Navigate to Mural page after successful retry
                print("\nNavigating to Mural page after successful retry...")
                page.goto("https://privacy.com.br/board")
                page.wait_for_timeout(5000)
                print(f"✅ Navigated to: {page.url}")
        else:
            # Navigate to Mural page after successful retry
            print("\nNavigating to Mural page after successful retry...")
            page.goto("https://privacy.com.br/board")
            page.wait_for_timeout(5000)
            print(f"✅ Navigated to: {page.url}")
        
        # endregion POST-LOGIN CHECK AND RETRY LOGIC
        
        # region try to clear any pop-ups blocking the view
        print("Checking for pop-ups to close...")
        if click_to_close_pop_up(page):
            print("Pop-up closed.")
            time.sleep(1) # Wait for animation to finish
        # endregion

        # Initialize counters OUTSIDE the loop
        i = j = k = 0

        # region Map each minute to its corresponding function (Now synchronous)
        minute_functions = {
            "00": click_00_minute, "05": click_05_minute, "10": click_10_minute,
            "15": click_15_minute, "20": click_20_minute, "25": click_25_minute,
            "30": click_30_minute, "35": click_35_minute, "40": click_40_minute,
            "45": click_45_minute, "50": click_50_minute, "55": click_55_minute
        }
        # endregion

        available_captions = captions_operation()
        available_media = select_media()

        # Loop for increment hours
        for hora in range(24):
            hora_str = f"{hora:02d}"
            print(f"\n=== PROCESSING HOUR {hora_str}:00 (Loop {hora + 1}/24) ===")
                                
            # Loop for increment minutes
            for minute_str, click_func in minute_functions.items():
                max_retries = 3
                                
                # region Try to click the Postar button with retries
                max_retries = 3
                for attempt in range(max_retries):
                    if click_on_postar_btn(page):
                        print("✅ Successfully clicked Postar button!")
                        break
                    else:
                        print(f"⏳ Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            print("⏳ Waiting before next attempt...")
                            page.wait_for_timeout(1000)  # Wait 1 second before retrying
                else:
                    print("❌ Failed to click Postar button after all attempts.")
                    error_msg = "❌ Error in click_on_postar_btn: {str(e)}"
                    print(error_msg)
                    log_error_to_file(error_msg)

                page.wait_for_timeout(3000)
                # endregion Try to click the Postar button with retries

                # region Try to click on Feed button with retries
                for attempt in range(max_retries):
                    if click_On_Feed_btn(page):
                        print(f"[{minute_str}] Feed button clicked.")
                        break
                    else:
                        print(f"[{minute_str}] Feed Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(3)
                else:
                    print("❌ CRITICAL: Failed Feed at {minute_str}. Refreshing and skipping...")
                    error_msg = f"❌ Error in click_On_Feed_btn: {str(e)}"
                    print(error_msg)
                    log_error_to_file(error_msg)
                    page.reload()
                    time.sleep(5)
                    continue # Skips to the next minute iteration

                page.wait_for_timeout(3000)
                # endregion Try to Click on Feed button with retries

                # region direct upload operation
                # 1. Safety check to ensure the list is not empty before popping
                if not available_media:
                    print(f"WARNING: No media available for {minute_str}. Skipping...")
                    continue

                # 2. Get the filename from your pre-filtered list
                current_media_filename = available_media.pop(0) 

                # 3. Call the new direct method and handle failure using the Critical Strategy
                if click_to_send_file_url(page, current_media_filename):
                    # Success: Small buffer to let the UI register the action
                    time.sleep(2)
                else:
                    # STRATEGY: This runs only if click_to_send_file_url fails
                    print(f"❌ CRITICAL: Failed Direct Upload at {minute_str}. Refreshing and skipping...")
                    error_msg = f"❌ Error in click_to_send_file_url: {str(e)}"
                    print(error_msg)
                    log_error_to_file(error_msg)
                    page.reload()
                    time.sleep(5)
                    continue # Skips to the next minute iteration

                # 4. Final cooldown after successful upload
                page.wait_for_timeout(3000)
                # endregion Direct upload operation

                # region Try to click the text area with retries
                for attempt in range(max_retries):
                    if click_On_Text_Area(page): 
                        print(f"[{minute_str}] Text Area clicked.")
                        break
                    else:
                        print(f"[{minute_str}] Text Area Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(5)
                else:
                    # If the loop finishes all attempts without a 'break'
                    print(f"❌ CRITICAL: Failed Text Area at {minute_str}. Refreshing and skipping...")
                    error_msg = f"❌ Failed to accesss Text Area at {minute_str}"
                    print(error_msg)
                    log_error_to_file(error_msg)
                    page.reload()
                    page.wait_for_timeout(4000)
                    continue # Skips to the next minute iteration

                # endregion Try to click the text area with retries

                # region Pastes random phrases
                current_caption = available_captions[j % len(available_captions)]
                pyperclip.copy(current_caption)
                time.sleep(2)
                page.keyboard.press('Control+V')
                time.sleep(2)
                # endregion

                # region Try to click on Post 24 horas button
                try:
                    # Attempt to click the button with a short timeout to avoid long hangs
                    page.locator('.swiper-slide:has-text("Post 24 horas")').click(timeout=10000)
                    time.sleep(2) # Small buffer for the UI to respond
                except Exception as e:
                    # STRATEGY: This runs if the button cannot be found or clicked
                    print(f"❌ CRITICAL: Failed to click Post 24 horas at {minute_str}. Refreshing and skipping...")
                    error_msg = f"❌ Failed to click Post 24 horas at {minute_str}"
                    print(error_msg)
                    log_error_to_file(error_msg)
                    page.reload()
                    page.wait_for_timeout(4000)
                    continue # Skips to the next minute iteration

                page.wait_for_timeout(5000)

                # endregion Try to click on Post 24 horas button

                # region Try to click the Schedule switch with retries
                max_retries = 3
                for attempt in range(max_retries):
                    if click_to_schedule_post(page):
                        print("✅ Successfully clicked Schedule switch!")
                        break
                    else:
                        print(f"⏳ Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            print("⏳ Waiting before next attempt...")
                            page.wait_for_timeout(1000)  # Wait 1 second before retrying
                else:
                    print("❌ Failed to click the Schedule switch after all attempts.")
                    error_msg = f"❌ Error in to click the Schedule switch: {str(e)}"
                    print(error_msg)
                    log_error_to_file(error_msg)

                page.wait_for_timeout(3000)
                # endregion Try to click the Schedule switch with retries

                # region Try to click tomorrow's day with retries
                
                for attempt in range(max_retries):
                    if click_tomorrow(page):
                        print(f"[{minute_str}] Tomorrow's date selected successfully.")
                        break
                    else:
                        print(f"[{minute_str}] Date Selection Attempt {attempt + 1} failed. Retrying...")
                        if attempt < max_retries - 1:
                            time.sleep(3)
                else:
                    error_msg = f"❌ Failed to click Date Selection at {minute_str}"
                    print(error_msg)
                    log_error_to_file(error_msg)
                    page.reload()
                    page.wait_for_timeout(4000)
                    continue # Skips to the next minute iteration

                page.wait_for_timeout(5000)

                # endregion Try to click tomorrow's day with retries

                # region Try to click time element with retries
                for attempt in range(max_retries):
                    if click_time(page): 
                        print(f"[{minute_str}] Time element opened.")
                        break
                    else:
                        print(f"[{minute_str}] Time Element Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(5)
                else:
                    # Failure handling for the time element
                    print(f"❌ CRITICAL: Could not open time picker at {minute_str}. Refreshing...")
                    error_msg = f"❌ Failed to click open time picker at {minute_str}"
                    print(error_msg)
                    log_error_to_file(error_msg)
                    page.reload()
                    time.sleep(5)
                    continue # Skip to next minute iteration

                page.wait_for_timeout(2000)
                # endregion Try to click time element with retries

                # region Try to click hour selection with retries
                for attempt in range(max_retries):
                    if click_hour(page): 
                        print(f"[{minute_str}] Hour selection successful.")
                        break
                    else:
                        print(f"[{minute_str}] Hour Selection Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(5)
                else:
                    # Failure handling for the hour selection
                    print(f"❌ CRITICAL: Could not select hour at {minute_str}. Refreshing...")
                    error_msg = f"❌ Failed to select hour at {minute_str}"
                    print(error_msg)
                    log_error_to_file(error_msg)
                    page.reload()
                    time.sleep(5)
                    continue # Skip to next minute iteration

                page.wait_for_timeout(3000)
                # endregion Try to click hour selection with retries

                # region select hour accordingly to the current loop for hora
                for attempt in range(max_retries):
                    try:
                        # Use 'text=' with quotes to force an exact match on the hour
                        hour_selector = page.locator(f".dp__overlay_cell >> text='{hora_str}'")
                        
                        # Wait for and click the element
                        hour_selector.wait_for(state="visible", timeout=3000)
                        hour_selector.click()
                        
                        print(f"[{minute_str}] ✅ Successfully clicked hour: {hora_str}")
                        break  # Exit the retry loop on success
                        
                    except Exception as e:
                        print(f"[{minute_str}] Attempt {attempt + 1} to select hour {hora_str} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(3)
                else:
                    # This block executes if all 3 attempts in the 'for' loop fail
                    print(f"❌ CRITICAL: Failed to select hour {hora_str} after all retries. Refreshing...")
                    error_msg = f"❌ Failed to select hour {hora_str}"
                    print(error_msg)
                    log_error_to_file(error_msg)
                    page.reload()
                    page.wait_for_timeout(4000)
                    continue  # Skip the rest of this minute loop and go to the next minute

                # Short sleep to allow the UI to transition
                page.wait_for_timeout(3000)
                # endregion select hour accordingly to the current loop for hora
                    
                # region Try to click minute selection
                for attempt in range(max_retries):
                    if click_minute(page): 
                        print(f"[{minute_str}] Minute selection successful.")
                        break
                    else:
                        print(f"[{minute_str}] Minute Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            page.wait_for_timeout(5000)
                else:
                    # If all attempts fail, reset the browser state
                    print(f"❌ CRITICAL: Failed to select minute at {minute_str}. Refreshing...")
                    error_msg = f"❌ Failed to select minute at {minute_str}"
                    print(error_msg)
                    log_error_to_file(error_msg)
                    page.reload()
                    page.wait_for_timeout(3000)
                    continue  # Jumps to the next minute_str in the main loop

                page.wait_for_timeout(3000)
                # endregion Try to click minute selection

                # region Select the specific minute using the dictionary
                for attempt in range(max_retries):
                    print(f"[{minute_str}] Attempt {attempt + 1} to select minute...")
                    
                    try:
                        # 1. Trigger the specific function from your dictionary
                        if click_func(page):
                            print(f"✅ Successfully clicked {minute_str} via dictionary function!")
                            break # Success! Exit the retry loop
                        
                        # 2. Targeted fallback if function returned False
                        else:
                            print(f"Dictionary function failed, trying direct locator for {minute_str}...")
                            if not page.locator(".dp__overlay").is_visible():
                                # Triggering the overlay visibility
                                page.locator(".dp__action_row").click() 
                            
                            target = page.locator(".dp__overlay_cell").filter(has_text=f"^{minute_str}$")
                            if target.count() > 0:
                                target.first.click()
                                print(f"Direct locator success for minute {minute_str}!")
                                break # Success! Exit the retry loop
                                
                    except Exception as e:
                        print(f"⏳ Attempt {attempt + 1} failed with error: {e}")
                    
                    # If we reached here, it failed. Sleep before retrying.
                    if attempt < max_retries - 1:
                        time.sleep(2)
                else:
                    # This block triggers ONLY if 'break' was never called (total failure)
                    print(f"❌ CRITICAL: All attempts for minute {minute_str} failed. Refreshing and skipping...")
                    error_msg = f"❌ Failed to select minute at {minute_str}"
                    print(error_msg)
                    log_error_to_file(error_msg)
                    page.reload()
                    page.wait_for_timeout(3000)
                    continue # Skip the rest of this minute loop iteration

                page.wait_for_timeout(3000)
                # endregion Select the specific minute using the dictionary

                # region Try to click the Minute Up button with retries
                for attempt in range(max_retries):
                    if click_On_Minute_Up_btn(page):
                        break
                    else:
                        print(f"[{minute_str}] Minute Up Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(2)
                else:
                    print(f"❌ CRITICAL: Failed Minute Up at {minute_str}. Refreshing...")
                    error_msg = f"❌ Failed to set Minute Up at {minute_str}"
                    print(error_msg)
                    log_error_to_file(error_msg)
                    page.reload()
                    page.wait_for_timeout(3000)
                    continue

                page.wait_for_timeout(3000)
                # endregion Try to click the Minute Up button with retries

                # region Try to click Aplicar button in modal with retries
                max_retries = 3
                for attempt in range(max_retries):
                    print(f"⏳ Attempt {attempt + 1} to click Aplicar button...")
                    if click_on_aplicar_button(page):
                        print("✅ Successfully clicked Aplicar button!")
                        break
                    else:
                        print(f"⏳ Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(1)
                else:
                    print("❌ Failed to click Aplicar button after all attempts.")
                    error_msg = f"❌ Error to click on Aplicar button: {str(e)}"
                    print(error_msg)
                    log_error_to_file(error_msg)

                page.wait_for_timeout(3000)
                # endregion Try to click Aplicar button in modal with retries

                # region Try to click the Avançar button with retries
                for attempt in range(max_retries):
                    if click_On_Avancar_btn(page):
                        break
                    else:
                        print(f"[{minute_str}] Avançar Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(1)
                else:
                    print(f"❌ CRITICAL: Failed Avançar at {minute_str}. Refreshing...")
                    error_msg = f"❌ Failed to click on avançar at {minute_str}"
                    print(error_msg)
                    log_error_to_file(error_msg)
                    page.reload()
                    page.wait_for_timeout(3000)
                    continue

                page.wait_for_timeout(3000)
                # endregion Try to click the Avançar button with retries

                # region Try to click on Agendar button
                for attempt in range(max_retries):
                    if click_On_Agendar_btn(page):
                        break
                    else:
                        print(f"[{minute_str}] Agendar Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(3)
                else:
                    print(f"❌ CRITICAL: Failed Agendar at {minute_str}. Refreshing...")
                    error_msg = f"❌ Failed to click on Agendar at {minute_str}"
                    print(error_msg)
                    log_error_to_file(error_msg)
                    page.reload()
                    page.wait_for_timeout(3000)
                    continue

                page.wait_for_timeout(3000)
                # endregion Try to click on Agendar button       

                # region Try to click the Concluído button with retries
                concluido_clicked_successfully = False # 🚀 New variable to track success
                for attempt in range(max_retries):
                    if click_On_Concluido_btn(page): # Assuming 'click_On_Concluido_btn' is a function that clicks the "Concluído" button
                        print(f"✅ 'Concluído' button clicked successfully on attempt {attempt + 1} at {minute_str}.")
                        concluido_clicked_successfully = True
                        break
                    else:
                        print(f"[{minute_str}] 'Concluído' Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(3)
                else:
                    print(f"❌ CRITICAL: Failed to click 'Concluído' at {minute_str}. Refreshing...")
                    error_msg = f"❌ Failed to click on 'Concluído' at {minute_str}"
                    print(error_msg)
                    log_error_to_file(error_msg)
                    page.reload()
                    page.wait_for_timeout(3000)
                    continue

                if concluido_clicked_successfully: # 🎉 Logs success if the button was clicked
                    log_error_to_file(f"'Concluído' button clicked successfully at {minute_str}")

                page.wait_for_timeout(3000)
                # endregion Try to click the Concluído button with retries
                
                # Increment counters for next iteration
                i += 1  # Media file counter
                j += 1  # Phrase counter
                k += 1  # General counter
            
                mark_caption_as_used(current_caption)
                mark_media_as_used(current_media_filename)

        page.evaluate("window.scrollTo(0, 0);")

        # region Try to click the Menu button with retries
        max_retries = 3
        print(f"Starting attempts to click the Menu button (avatar). Max retries: {max_retries}")
        for attempt in range(max_retries):
            print(f"\n--- Attempt {attempt + 1} of {max_retries} ---")
            if click_on_menu(page):
                print("✅ Successfully clicked Menu button after one or more attempts!")
                break # Exit the loop if successful
            else:
                print(f"⏳ Attempt {attempt + 1} failed to click the Menu button.")
                if attempt < max_retries - 1:
                    print("⏳ Waiting 1 second before the next attempt...")
                    page.wait_for_timeout(1000)  # Wait 1 second before retrying
                else:
                    print("This was the last attempt.")
        else:
            # This 'else' block executes if the loop completes without a 'break'
            print("❌ Failed to click Menu button after all attempts.")
            error_msg = f"❌ Failed to click on Menu button"
            print(error_msg)
            log_error_to_file(error_msg)

        print("⏳ Waiting for 3 seconds after menu interaction (or failure)...")
        page.wait_for_timeout(3000)
        # region Try to click the Menu button with retries

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
                    print("⏳ Waiting before next attempt...")
                    time.sleep(2)

        if not sair_clicked:
            print("❌ Failed to click on sair after all attempts.")
            error_msg = f"❌ Failed to click on Sair button"
            print(error_msg)
            log_error_to_file(error_msg)

        page.wait_for_timeout(5000)
        # endregion Try to click on sair with retries

    except Exception as e:
        error_msg = f"An unexpected error occurred during automation!"
        print(f"❌ {error_msg}")
        log_error_to_file(error_msg) # Log the unexpected error
        sys.exit(1) # Exit with an error code

    finally:
        # Cleanup: Close browser and resources (adjust based on your Playwright setup)
        try:
            if 'page' in locals() and page:
                page.close()
            if 'context' in locals() and context:
                context.close()
            # The 'browser' variable might not be directly available if using browser_process
            # if 'browser' in locals() and browser: # This line might be redundant or incorrect depending on Playwright setup
            #     browser.close()
            if browser_process: # Use the browser_process variable
                browser_process.kill() # Ensure the browser process is terminated
            print("Browser closed successfully.")
        except Exception as close_err:
            error_msg = f"Error during browser cleanup: {close_err}"
            print(f"❌ {error_msg}")
            log_error_to_file(error_msg) # Log cleanup errors

        file_path = r"G:\Meu Drive\Privacy_free\p_sch_privacy_free_error_logs.txt"
        text_to_insert = "\n====== END OF THIS ITERATION LOGGING =======\n"

        with open(file_path, 'a') as file:
            file.write(text_to_insert)

        # Exit the script (0 for success, 1 for error)
        sys.exit(0)

if __name__ == "__main__":
    main()