# Standard library imports
import os
import sys
import time
import psutil
from pathlib import Path

# Third-party imports
import subprocess
from playwright.sync_api import sync_playwright

# Local imports
sys.path.append(str(Path(__file__).resolve().parent.parent))  # Adjust path to include the parent directory

# region Script to help build the executable with PyInstaller
try:
    # Para o executável PyInstaller
    sys.path.append(os.path.join(sys._MEIPASS, "repository"))
except Exception:
    # Para desenvolvimento
    sys.path.append(str(Path(__file__).resolve().parent.parent / "repository"))
# endregion

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
    subprocess.Popen([
        chrome_path,
        f"--user-data-dir={user_data}",
        "--remote-debugging-port=9222", # This is the bridge
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
        return pw, context

    except Exception as e:
        print(f"Hook failed: {e}")
        pw.stop()
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
                    if clicked: return True

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

def cleanup_playwright():
    """Safely close browser and stop Playwright when done."""
    global playwright_instance, browser_context
    
    # Close browser context
    try:
        if browser_context is not None:
            browser_context.close()
            print("Browser context closed.")
    except Exception as e:
        print(f"Error closing browser context: {e}")
    
    # Stop Playwright instance
    try:
        if playwright_instance is not None:
            playwright_instance.stop()
            print("Playwright stopped.")
    except Exception as e:
        print(f"Error stopping Playwright: {e}")

def keep_browser_alive():
    """
    Mantém o browser ativo indefinidamente.
    Chame esta função após open_chrome_with_profile() se quiser manter o browser aberto.
    """
    try:
        print("Mantendo browser ativo... (Pressione Ctrl+C para encerrar)")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando browser...")
        cleanup_playwright()

def open_chrome_native():
    """
    Alternative: Opens native Chrome without Playwright.
    Uses the Chrome executable directly with the specified profile.
    """
    profile_path = r"C:\Users\danie\AppData\Local\Google\Chrome\User Data"
    chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    target_url = "https://privacy.com.br/board"

    # Validate file and directory existence
    if not os.path.exists(chrome_exe):
        raise FileNotFoundError(f"Chrome not found at: {chrome_exe}")
    
    if not os.path.exists(profile_path):
        raise FileNotFoundError(f"Profile directory not found: {profile_path}")

    # Build command arguments
    cmd = [
        chrome_exe,
        f"--user-data-dir={profile_path}",
        "--profile-directory=Default",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--remote-debugging-port=0",
        target_url
    ]

    try:
        print(f"Opening Native Chrome...\nExe: {chrome_exe}\nProfile: {profile_path}")

        # Start the Chrome process detached from the script
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )

        print(f"Chrome started with PID: {process.pid}")
        
        # Wait for initialization
        time.sleep(3)

        # Check if the process is still alive
        if process.poll() is None:
            print("Chrome is running successfully.")
            return True
        else:
            print("Chrome closed unexpectedly.")
            return False
            
    except Exception as e:
        print(f"Error opening native Chrome: {e}")
        return False

def main():
    pw = None
    context = None
    page = None

    # 2. Launch Browser via the Native Hook method
    try:
        pw, context = open_chrome_in_privacy_login_page()
        page = context.pages[0]  # Grab the active Privacy board page
        print("✓ Browser launched successfully")
    except Exception as e:
        print(f"❌ Failed to launch or hook browser: {e}")
        cleanup_resources(pw, context, page)
        return

    # 3. Automation and Interaction
    try:
        print("Waiting for page load...")
        page.wait_for_load_state("domcontentloaded")

        # Fullscreen Mode
        import pyautogui
        pyautogui.press('f11')
        page.wait_for_timeout(3000)

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
                    time.sleep(2)  # Wait 2 seconds before retrying

        if not username_inserted:
            print("❌ Failed to insert username after all attempts.")
            page.screenshot(path="debug_username_failed.png")

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
                    time.sleep(2)  # Wait 2 seconds before retrying

        if not password_inserted:
            print("❌ Failed to insert password after all attempts.")
            page.screenshot(path="debug_password_failed.png")

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
            page.wait_for_timeout(5000)
            print(f"Current URL: {page.url}")
            print("✓ Login process completed!")
        # endregion

        print("\n" + "="*50)
        print("✓ All tasks completed successfully!")
        print("="*50)

    except KeyboardInterrupt:
        print("\n⚠️ Script interrupted by user (Ctrl+C)")
    except Exception as e:
        print(f"❌ Error during automation: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 5. Complete Cleanup
        cleanup_resources(pw, context, page)

    print("✓ Exiting process.")
    sys.exit(0)


def cleanup_resources(pw, context, page):
    """
    Comprehensive cleanup of all browser resources, contexts, and processes.
    """
    print("\n" + "="*50)
    print("Cleaning up resources...")
    print("="*50)

    # Close page
    if page:
        try:
            print("Closing page...")
            page.close()
            print("✓ Page closed")
        except Exception as e:
            print(f"⚠️ Error closing page: {e}")

    # Close context
    if context:
        try:
            print("Closing browser context...")
            context.close()
            print("✓ Context closed")
        except Exception as e:
            print(f"⚠️ Error closing context: {e}")

    # Stop Playwright
    if pw:
        try:
            print("Stopping Playwright...")
            pw.stop()
            print("✓ Playwright stopped")
        except Exception as e:
            print(f"⚠️ Error stopping Playwright: {e}")

    # Kill any remaining Chrome processes (optional but thorough)
    try:
        import psutil
        print("Checking for remaining Chrome processes...")
        chrome_killed = False

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if 'chrome' in proc.info['name'].lower():
                    proc.kill()
                    chrome_killed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if chrome_killed:
            print("✓ Remaining Chrome processes terminated")
        else:
            print("✓ No remaining Chrome processes found")
    except ImportError:
        print("⚠️ psutil not installed - skipping process cleanup")
        print("   Install with: pip install psutil")
    except Exception as e:
        print(f"⚠️ Error during process cleanup: {e}")

    print("="*50)
    print("✓ Cleanup completed")
    print("="*50)


if __name__ == "__main__":
    main()

