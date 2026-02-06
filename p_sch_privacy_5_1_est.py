# Standard library imports
import os
import random
import sys
import time
from datetime import timedelta, date
from pathlib import Path

# Third-party imports
import openpyxl
import pyperclip
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
        print(f"Error: Excel file not found at {excel_path}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

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
                #print(f"Trying Pular tutorial button selector: {selector}")
                
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
                        #print(f"Successfully clicked Pular tutorial button with JS selector")
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
                            #print(f"Successfully clicked Pular tutorial button with XPath")
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
                            #print(f"Successfully clicked Pular tutorial button with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"Failed with Pular tutorial button selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("Trying JavaScript fallback approach for Pular tutorial button...")
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
            print("Successfully clicked Pular tutorial button using JavaScript fallback!")
            return True
        
        print("Could not find or click Pular tutorial button using any method.")
        return False
    
    except Exception as e:
        print(f"Error in click_On_Pular_Tutorial_btn: {str(e)}")
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
        print(f"Error in click_to_close_pop_up: {str(e)}")
        return False

def click_On_Postar_btn(page):
    """
    Attempt to find and click the "Postar" button using multiple approaches.
    """
    try:
        # List of selectors to try (reordered to prioritize the working approach)
        selectors = [
            # Shadow DOM JavaScript path (moved first as it succeeds)
            "document.querySelector('#privacy-web-floatmenu').shadowRoot.querySelector('div > nav > div:nth-child(3)')",
            # XPath
            "//*[@id='privacy-web-floatmenu']//div/nav/div[3]",
            # Direct CSS selector (moved last as it often fails)
            "div > nav > div:nth-child(3)"
        ]
        # Try each selector
        for selector in selectors:
            try:
                #print(f"Trying Postar button selector: {selector}")
                
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
                        #print(f"Successfully clicked Postar button with JS selector")
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
                            #print(f"Successfully clicked Postar button with XPath")
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
                            #print(f"Successfully clicked Postar button with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"Failed with Postar button selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("Trying JavaScript fallback approach for Postar button...")
        fallback_clicked = page.evaluate('''() => {
            // Try finding elements with "Postar" text
            const buttonSelectors = [
                'div.menu__item',
                'nav > div',
                'div[tabindex="0"]'
            ];
            
            for (const selector of buttonSelectors) {
                const elements = document.querySelectorAll(selector);
                for (const element of elements) {
                    if (element && element.textContent.includes('Postar')) {
                        element.scrollIntoView({behavior: 'smooth', block: 'center'});
                        element.click();
                        return true;
                    }
                }
            }
            
            // Try finding the plus icon
            const svgSelectors = [
                'svg.svg-inline--fa[data-icon="plus"]',
                'svg[data-prefix="fak"][data-icon="plus"]'
            ];
            
            for (const selector of svgSelectors) {
                const svgElements = document.querySelectorAll(selector);
                for (const svg of svgElements) {
                    if (svg) {
                        const parent = svg.closest('div.menu__item');
                        if (parent) {
                            parent.scrollIntoView({behavior: 'smooth', block: 'center'});
                            parent.click();
                            return true;
                        }
                    }
                }
            }
            return false;
        }''')
        
        if fallback_clicked:
            print("Successfully clicked Postar button using JavaScript fallback!")
            return True
        
        print("Could not find or click Postar button using any method.")
        return False
    
    except Exception as e:
        print(f"Error in click_On_Postar_btn: {str(e)}")
        return False

def click_On_Feed_btn(page):
    """
    Attempt to find and click the Feed option in the Postar modal window.
    """
    try:
        # List of selectors to try
        selectors = [
            # CSS selector for the Feed option
            "div.options__option:has(svg.svg-inline--fa-feed)",
            # More specific CSS selector
            "div.options__option:has(> svg[data-icon='feed'])",
            # XPath for the Feed option
            "//div[contains(@class, 'options__option')][.//svg[@data-icon='feed']]",
            # Full path XPath
            "//div[@class='options min-drawer el-drawer btt open']//div[@class='options__option'][.//svg[@data-icon='feed']]"
        ]

        # Try each selector
        for selector in selectors:
            try:
                #print(f"Trying Feed button selector: {selector}")
                
                if selector.startswith('/'):
                    # XPath selector
                    xpath_elements = page.locator(f"xpath={selector}")
                    if xpath_elements.count() > 0:
                        try:
                            # Wait for element to be visible
                            xpath_elements.first.wait_for(state="visible")
                            
                            # Scroll and click
                            xpath_elements.first.scroll_into_view_if_needed()
                            xpath_elements.first.click(force=True)
                            #print(f"Successfully clicked Feed button with XPath")
                            return True
                        except Exception as e:
                            print(f"XPath click failed: {str(e)}")
                else:
                    # CSS selector
                    css_elements = page.locator(selector)
                    if css_elements.count() > 0:
                        try:
                            # Wait for element to be visible
                            css_elements.first.wait_for(state="visible")
                            
                            # Scroll and click
                            css_elements.first.scroll_into_view_if_needed()
                            css_elements.first.click(force=True)
                            #print(f"Successfully clicked Feed button with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"Failed with Feed button selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("Trying JavaScript fallback approach for Feed button...")
        fallback_clicked = page.evaluate('''() => {
            // Find all options in the modal
            const options = document.querySelectorAll('div.options__option');
            for (const option of options) {
                // Check if this is the Feed option
                const feedIcon = option.querySelector('svg[data-icon="feed"]');
                if (feedIcon) {
                    // Scroll and click
                    option.scrollIntoView({behavior: 'smooth', block: 'center'});
                    option.click();
                    return true;
                }
            }
            return false;
        }''')
        
        if fallback_clicked:
            print("Successfully clicked Feed button using JavaScript fallback!")
            return True
        
        print("Could not find or click Feed button using any method.")
        return False
    
    except Exception as e:
        print(f"Error in click_On_Feed_btn: {str(e)}")
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
                #print(f"Trying Select Photo/Video button selector: {selector}")
                
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
                            #print(f"Successfully clicked Select Photo/Video button with XPath")
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
                            #print(f"Successfully clicked Select Photo/Video button with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"Failed with Select Photo/Video button selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach specifically for the modal
        print("Trying JavaScript fallback approach for Select Photo/Video button...")
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
            print("Successfully clicked Select Photo/Video button using JavaScript fallback!")
            return True
        
        print("Could not find or click Select Photo/Video button using any method.")
        return False
    
    except Exception as e:
        print(f"Error in click_On_Selecionar_Foto_ou_Video_btn: {str(e)}")
        return False

def click_to_send_file_url(page, filename):
    """
    Directly uploads a file to the browser without using PyAutoGUI.
    """
    # 1. Define the full path
    folder_path = r'G:\Meu Drive\SFS'
    full_file_path = os.path.join(folder_path, filename)

    #print(f"Directly uploading: {full_file_path}")

    try:
        # 2. Playwright 'expect_file_chooser' handles the hidden input trigger
        with page.expect_file_chooser() as fc_info:
            # Click the "+" icon or the button that triggers the upload
            # We use the SVG structure or the text to find it
            page.locator("text=selecionar foto ou vídeo").click()
            
        file_chooser = fc_info.value
        
        # 3. Send the URL/Path directly to the browser
        file_chooser.set_files(full_file_path)
        
        #print("File sent successfully via browser URL.")
        return True

    except Exception as e:
        print(f"Error sending file directly: {e}")
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
                #print(f"Trying text area selector: {selector}")
                
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
                        #print(f"Successfully clicked text area with JS selector")
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
                            #print(f"Successfully clicked text area with XPath")
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
                            #print(f"Successfully clicked text area with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"Failed with text area selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("Trying JavaScript fallback approach for text area...")
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
            print("Successfully clicked text area using JavaScript fallback!")
            return True
        
        print("Could not find or click text area using any method.")
        return False
    
    except Exception as e:
        print(f"Error in click_On_Text_Area: {str(e)}")
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
        print(f"Error selecting media: {e}")
        return []

def mark_media_as_used(media_name):
    history_path = r"G:\Meu Drive\Privacy_free\privacy_free_used_media.txt"
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(media_name + "\n")
        
def click_On_Agendar_publicacao_btn(page):
    """
    Attempt to find and click the 'Agendar Publicação' switch using multiple approaches.
    """
    try:
        # List of selectors to try for the switch element
        selectors = [
            # CSS selector
            "#el-id-4154-90 > form > div.post-attributes > div.post-attributes__switchs.d-flex.flex-column.gap-3.mt-4 > div:nth-child(1) > div:nth-child(2) > div",
            # Shadow DOM JavaScript path
            "document.querySelector(\"#privacy-web-publisher\").shadowRoot.querySelector(\"#el-id-4154-90 > form > div.post-attributes > div.post-attributes__switchs.d-flex.flex-column.gap-3.mt-4 > div:nth-child(1) > div:nth-child(2) > div\")",
            # XPath
            "//*[@id=\"el-id-4154-90\"]/form/div[4]/div[2]/div[1]/div[2]/div",
            # Alternative selector targeting the switch class
            ".el-switch",
            # Input checkbox within the switch
            ".el-switch__input[type='checkbox']"
        ]

        # Try each selector
        for selector in selectors:
            try:
                #print(f"Trying Agendar Publicação selector: {selector}")
                
                # Handle different selector types
                if selector.startswith("document.querySelector"):
                    # JavaScript selector for shadow DOM
                    switch_clicked = page.evaluate(f'''() => {{
                        try {{
                            const switchElement = {selector};
                            if (switchElement) {{
                                switchElement.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                                
                                // Check if it's a checkbox input or div element
                                if (switchElement.tagName === 'INPUT') {{
                                    switchElement.checked = !switchElement.checked;
                                    switchElement.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                }} else {{
                                    switchElement.click();
                                }}
                                return true;
                            }}
                            return false;
                        }} catch (e) {{
                            console.error('Shadow DOM access error:', e);
                            return false;
                        }}
                    }}''')
                    
                    if switch_clicked:
                        #print(f"Successfully clicked Agendar Publicação switch with JS selector")
                        return True
                
                elif selector.startswith('/'):
                    # XPath selector
                    xpath_elements = page.locator(f"xpath={selector}")
                    if xpath_elements.count() > 0:
                        try:
                            # Force visibility and ensure it's clickable
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
                                    element.style.pointerEvents = 'auto';
                                }}
                            }}''', selector)
                            
                            # Scroll and click
                            xpath_elements.first.scroll_into_view_if_needed()
                            xpath_elements.first.click(force=True)
                            #print(f"Successfully clicked Agendar Publicação switch with XPath")
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
                                    element.style.pointerEvents = 'auto';
                                }}
                            }}''', selector)
                            
                            # Scroll and click
                            css_elements.first.scroll_into_view_if_needed()
                            css_elements.first.click(force=True)
                            #print(f"Successfully clicked Agendar Publicação switch with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"Failed with Agendar Publicação selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach for finding the switch
        print("Trying JavaScript fallback approach for Agendar Publicação switch...")
        fallback_clicked = page.evaluate('''() => {
            // Try finding switch elements
            const switchSelectors = [
                '.el-switch',
                '[role="switch"]',
                'input[type="checkbox"][role="switch"]',
                '.post-attributes__switchs .el-switch'
            ];
            
            for (const selector of switchSelectors) {
                const switches = document.querySelectorAll(selector);
                for (const switchElement of switches) {
                    // Look for elements that might be related to scheduling/publication
                    const parentText = switchElement.parentElement?.innerText || '';
                    const surroundingText = switchElement.closest('div')?.innerText || '';
                    
                    if (parentText.includes('Agendar') || 
                        parentText.includes('Publicação') || 
                        surroundingText.includes('Agendar') || 
                        surroundingText.includes('Publicação') ||
                        switchElement.getAttribute('aria-label')?.includes('Agendar')) {
                        
                        switchElement.scrollIntoView({behavior: 'smooth', block: 'center'});
                        
                        // Handle different element types
                        if (switchElement.tagName === 'INPUT') {
                            switchElement.checked = !switchElement.checked;
                            switchElement.dispatchEvent(new Event('change', { bubbles: true }));
                        } else {
                            switchElement.click();
                        }
                        return true;
                    }
                }
            }
            return false;
        }''')
        
        if fallback_clicked:
            print("Successfully clicked Agendar Publicação switch using JavaScript fallback!")
            return True
        
        print("Could not find or click Agendar Publicação switch using any method.")
        return False
    
    except Exception as e:
        print(f"Error in click_On_Agendar_publicacao_btn: {str(e)}")
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
                #print(f"Trying media insertion selector: {selector}")
                
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
                        #print(f"Successfully clicked media insertion button with JS selector")
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
                            #print(f"Successfully clicked media insertion button with XPath")
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
                            #print(f"Successfully clicked media insertion button with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"Failed with media insertion selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("Trying JavaScript fallback approach for media insertion...")
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
            print("Successfully clicked media insertion button using JavaScript fallback!")
            return True
        
        print("Could not find or click media insertion button using any method.")
        return False
    
    except Exception as e:
        print(f"Error in insert_new_media: {str(e)}")
        return False

def click_tomorrow(page):
    """
    Finds and clicks tomorrow's date in the calendar picker.
    """
    try:
        # Calculate target date (Tomorrow)
        tomorrow = date.today() + timedelta(days=1)
        target_day = tomorrow.day
        #print(f"Targeting tomorrow's date: {target_day}")

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
                    #print(f"Success: Day {target_day} clicked using browser locator.")
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
        print(f"Error while trying to click tomorrow's date: {str(e)}")
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
                #print(f"Trying time element selector: {selector}")
                
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
                        #print(f"Successfully clicked time element with JS selector")
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
                            #print(f"Successfully clicked time element with XPath")
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
                            #print(f"Successfully clicked time element with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"Failed with time element selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("Trying JavaScript fallback approach for time element...")
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
            print("Successfully clicked time element using JavaScript fallback!")
            return True
        
        print("Could not find or click time element using any method.")
        return False
    
    except Exception as e:
        print(f"Error in click_time: {str(e)}")
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
                #print(f"Trying hour selection selector: {selector}")
                
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
                        #print(f"Successfully clicked hour selection button with JS selector")
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
                            #print(f"Successfully clicked hour selection button with XPath")
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
                            #print(f"Successfully clicked hour selection button with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"Failed with hour selection selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("Trying JavaScript fallback approach for hour selection...")
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
            print("Successfully clicked hour selection button using JavaScript fallback!")
            return True
        
        print("Could not find or click hour selection button using any method.")
        return False
    
    except Exception as e:
        print(f"Error in click_hour: {str(e)}")
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
                #print(f"Trying '00' time selection selector: {selector}")
                
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
                        #print(f"Successfully clicked '00' time selection with JS selector")
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
                            #print(f"Successfully clicked '00' time selection with XPath")
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
                            #print(f"Successfully clicked '00' time selection with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"Failed with '00' time selection selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("Trying JavaScript fallback approach for '00' time selection...")
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
            print("Successfully clicked '00' time selection using JavaScript fallback!")
            return True
        
        print("Could not find or click '00' time selection using any method.")
        return False
    
    except Exception as e:
        print(f"Error in click_00: {str(e)}")
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
                #print(f"Trying hour up button selector: {selector}")
                
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
                        #print(f"Successfully clicked hour up button with JS selector")
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
                            #print(f"Successfully clicked hour up button with XPath")
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
                            #print(f"Successfully clicked hour up button with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"Failed with hour up button selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("Trying JavaScript fallback approach for hour up button...")
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
            print("Successfully clicked hour up button using JavaScript fallback!")
            return True
        
        print("Could not find or click hour up button using any method.")
        return False
    
    except Exception as e:
        print(f"Error in click_hour_up: {str(e)}")
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
                #print(f"Trying minute selection selector: {selector}")
                
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
                        #print(f"Successfully clicked minute selection button with JS selector")
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
                            #print(f"Successfully clicked minute selection button with XPath")
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
                            #print(f"Successfully clicked minute selection button with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"Failed with minute selection selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("Trying JavaScript fallback approach for minute selection...")
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
            print("Successfully clicked minute selection button using JavaScript fallback!")
            return True
        
        print("Could not find or click minute selection button using any method.")
        return False
    
    except Exception as e:
        print(f"Error in click_minute: {str(e)}")
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
                #print(f"Trying 00 minute selector: {selector}")
                
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
                        #print(f"Successfully clicked 00 minute button with JS selector")
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
                            #print(f"Successfully clicked 00 minute button with XPath")
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
                            #print(f"Successfully clicked 00 minute button with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"Failed with 00 minute selector {selector}: {str(e)}")
                continue
        
        print("Could not find or click 00 minute button using any method.")
        return False
    
    except Exception as e:
        print(f"Error in click_00_minute: {str(e)}")
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
                #print(f"Trying Minute Up button selector: {selector}")
                
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
                        #print(f"Successfully clicked Minute Up button with JS selector")
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
                            #print(f"Successfully clicked Minute Up button with XPath")
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
                            #print(f"Successfully clicked Minute Up button with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"Failed with Minute Up button selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("Trying JavaScript fallback approach for Minute Up button...")
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
            print("Successfully clicked Minute Up button using JavaScript fallback!")
            return True
        
        print("Could not find or click Minute Up button using any method.")
        return False
    
    except Exception as e:
        print(f"Error in click_On_Minute_Up_btn: {str(e)}")
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
    except: return False

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
    except: return False

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
    except: return False

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
    except: return False

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
    except: return False

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
    except: return False

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
    except: return False

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
    except: return False

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
    except: return False

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
    except: return False

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
    except: return False

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
                #print(f"Trying Aplicar button selector: {selector}")
                
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
                        #print(f"Successfully clicked Aplicar button with JS selector")
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
                            #print(f"Successfully clicked Aplicar button with XPath")
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
                            #print(f"Successfully clicked Aplicar button with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"Failed with Aplicar button selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("Trying JavaScript fallback approach for Aplicar button...")
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
            print("Successfully clicked Aplicar button using JavaScript fallback!")
            return True
        
        print("Could not find or click Aplicar button using any method.")
        return False
    
    except Exception as e:
        print(f"Error in click_On_Aplicar_btn: {str(e)}")
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
                print(f"Attempt with selector '{selector}' failed: {str(e)}")
                continue
                
        print("All selector attempts failed")
        return False
        
    except Exception as e:
        print(f"Error in click_aplicar_in_modal: {str(e)}")
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
        print(f"Error in click_on_aplicar_button: {str(e)}")
        return False

def click_On_Avancar_btn(page):
    """
    Fast version - uses known working selector first
    """
    try:
        # Try the known working selector first
        try:
            page.locator("button.el-button--gradient.is-block").click(timeout=3000)
            print("Successfully clicked Avançar button with known selector!")
            return True
        except:
            pass
        
        # Fallback to other selectors
        selectors = [
            "button.el-button--gradient",
            "div.component-button > button",
            "button:has-text('Avançar')"
        ]
        
        for selector in selectors:
            try:
                page.locator(selector).first.click(timeout=2000)
                #print(f"Successfully clicked Avançar button with: {selector}")
                return True
            except:
                continue
        
        return False
        
    except Exception as e:
        print(f"Error clicking Avançar button: {str(e)}")
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
            #print("Agendar button clicked successfully")
            return True
        else:
            print("Agendar button not found")
            return False
            
    except Exception as e:
        print(f"Error clicking Agendar button: {e}")
        return False

def click_On_Concluido_btn(page):
    """
    Click on the 'Concluido' button inside the shadow DOM
    """
    try:
        # Method 1: Use JavaScript to access the shadow DOM and click the button
        click_success = page.evaluate('''() => {
            try {
                // Get the shadow root
                const shadowHost = document.querySelector("#privacy-web-publisher");
                if (!shadowHost) return false;
                
                const shadowRoot = shadowHost.shadowRoot;
                if (!shadowRoot) return false;
                
                // Find the button by text content
                const buttons = shadowRoot.querySelectorAll("button");
                for (const button of buttons) {
                    if (button.textContent.includes('Concluido') || button.textContent.includes('Concluído')) {
                        button.click();
                        return true;
                    }
                }
                
                // Alternative: Find by specific selector if text search fails
                const concluidoButton = shadowRoot.querySelector("button.el-button--gradient");
                if (concluidoButton && (concluidoButton.textContent.includes('Concluido') || concluidoButton.textContent.includes('Concluído'))) {
                    concluidoButton.click();
                    return true;
                }
                
                return false;
            } catch (e) {
                console.error('Error clicking Concluido button:', e);
                return false;
            }
        }''')
        
        if click_success:
            #print("Successfully clicked Concluido button via JavaScript")
            return True
        
        # Method 2: Try using Playwright's text locator (might work despite shadow DOM)
        try:
            concluido_button = page.locator("button:has-text('Concluido'), button:has-text('Concluído')")
            if concluido_button.count() > 0:
                concluido_button.first.click(force=True, timeout=5000)
                #print("Successfully clicked Concluido button using text locator")
                return True
        except:
            pass
            
        # Method 3: Use the specific component structure
        try:
            component_button = page.locator("div.component-button button")
            if component_button.count() > 0:
                for i in range(component_button.count()):
                    button_text = component_button.nth(i).text_content()
                    if 'Concluido' in button_text or 'Concluído' in button_text:
                        component_button.nth(i).click(force=True, timeout=5000)
                        #print("Successfully clicked Concluido button via component structure")
                        return True
        except:
            pass
            
        print("Could not find or click Concluido button")
        return False
        
    except Exception as e:
        print(f"Error in click_On_Concluido_btn: {str(e)}")
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
                #print(f"Trying Confirmar button selector: {selector}")
                
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
                            #print(f"Successfully clicked Confirmar button with XPath")
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
                            #print(f"Successfully clicked Confirmar button with CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector click failed: {str(e)}")
                
            except Exception as e:
                print(f"Failed with Confirmar button selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("Trying JavaScript fallback approach for Confirmar button...")
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
            print("Successfully clicked Confirmar button using JavaScript fallback!")
            return True
        
        print("Could not find or click Confirmar button using any method.")
        return False
    
    except Exception as e:
        print(f"Error in click_on_Confirmar_btn: {str(e)}")
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
                #print(f"Trying expiration element selector: {selector}")
                
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
                        #print(f"Successfully interacted with expiration element using JS selector")
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
                            #print(f"Successfully interacted with expiration element using XPath")
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
                            #print(f"Successfully interacted with expiration element using CSS selector")
                            return True
                        except Exception as e:
                            print(f"CSS selector interaction failed: {str(e)}")
                
            except Exception as e:
                print(f"Failed with expiration element selector {selector}: {str(e)}")
                continue
        
        # Fallback JavaScript approach
        print("Trying JavaScript fallback approach for expiration element...")
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
            print("Successfully interacted with expiration element using JavaScript fallback!")
            return True
        
        print("Could not find or interact with expiration element using any method.")
        return False
    
    except Exception as e:
        print(f"Error in set_expiration: {str(e)}")
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
                #print(f"Trying text area selector: {selector}")
                
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
                print(f"Failed with selector {selector}: {str(e)}")
                continue

        print("Failed to locate or interact with the text area using all selectors.")
        return None

    except Exception as e:
        print(f"Error in click_on_text_area: {str(e)}")
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
                #print(f"Trying text area selector: {selector}")
                
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
                        #print(f"Successfully clicked text area with JS path selector.")
                        return True

                # Handle XPath
                elif selector.startswith('/'):
                    xpath_elements = page.locator(f"xpath={selector}")
                    if xpath_elements.count() > 0:
                        element = xpath_elements.first
                        element.scroll_into_view_if_needed()
                        element.click()
                        #print(f"Successfully clicked text area with XPath.")
                        return True

                # Handle CSS selector
                else:
                    css_elements = page.locator(selector)
                    if css_elements.count() > 0:
                        element = css_elements.first
                        element.scroll_into_view_if_needed()
                        element.click()
                        #print(f"Successfully clicked text area with CSS selector.")
                        return True

            except Exception as e:
                print(f"Failed with selector {selector}: {str(e)}")
                continue

        print("Failed to locate or interact with the text area using all selectors.")
        return False

    except Exception as e:
        print(f"Error in click_on_text_area_2: {str(e)}")
        return False

def main():
    
    # 2. Launch Browser via the Native Hook method
    try:
        pw, context = open_chrome_in_privacy_login_page()
        page = context.pages[0] # Grab the active Privacy board page
    except Exception as e:
        print(f"Failed to launch or hook browser: {e}")
        return

    # 3. Automation and Interaction
    try:
        print("Waiting for page load...")
        page.wait_for_load_state("domcontentloaded")
        
        # Fullscreen Mode
        import pyautogui
        pyautogui.press('f11')
        
        time.sleep(3)
        
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

        # region Try to click the Entrar button with retries
        max_retries = 3
        for attempt in range(max_retries):
            print(f"Attempt {attempt + 1}: Clicking Entrar...")
            if click_on_entrar_button(page):
                print("Success: Entrar button clicked.")
                break
            else:
                print(f"Attempt {attempt + 1} failed. Maybe you are already logged in!")
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        # endregion

        # Loop for increment hours
        for hora in range(24):
            hora_str = f"{hora:02d}"
            #print(f"\n=== PROCESSING HOUR {hora_str}:00 (Loop {hora + 1}/24) ===")
                                
            # Loop for increment minutes
            for minute_str, click_func in minute_functions.items():
                max_retries = 3
                                
                # region Click on Postar button with retries
                for attempt in range(max_retries):
                    if click_On_Postar_btn(page):
                        #print(f"[{minute_str}] Postar button clicked.")
                        break
                    else:
                        print(f"[{minute_str}] Postar Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(5) 
                else:
                    # This runs only if all retries for Postar failed
                    print(f"CRITICAL: Failed Postar at {minute_str}. Refreshing and skipping...")
                    page.reload()
                    time.sleep(5)
                    continue # Skips to the next minute iteration

                time.sleep(3)

                # endregion

                # region Click on Feed button with retries
                for attempt in range(max_retries):
                    if click_On_Feed_btn(page):
                        #print(f"[{minute_str}] Feed button clicked.")
                        break
                    else:
                        print(f"[{minute_str}] Feed Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(3)
                else:
                    # This runs only if all retries for Feed failed
                    print(f"CRITICAL: Failed Feed at {minute_str}. Refreshing and skipping...")
                    page.reload()
                    time.sleep(5)
                    continue # Skips to the next minute iteration

                # endregion

                # region NEW DIRECT UPLOAD OPERATION
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
                    print(f"CRITICAL: Failed Direct Upload at {minute_str}. Refreshing and skipping...")
                    page.reload()
                    time.sleep(5)
                    continue # Skips to the next minute iteration

                # 4. Final cooldown after successful upload
                time.sleep(3)
                # endregion

                # region Try to click the text area with retries
                for attempt in range(max_retries):
                    if click_On_Text_Area(page): 
                        #print(f"[{minute_str}] Text Area clicked.")
                        break
                    else:
                        print(f"[{minute_str}] Text Area Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(5)
                else:
                    # If the loop finishes all attempts without a 'break'
                    print(f"CRITICAL: Failed Text Area at {minute_str}. Refreshing and skipping...")
                    page.reload()
                    time.sleep(5)
                    continue # Exit current minute iteration and move to next minute_str

                time.sleep(5)
                # endregion

                # region Pastes random phrases
                current_caption = available_captions[j % len(available_captions)]
                pyperclip.copy(current_caption)
                time.sleep(2)
                page.keyboard.press('Control+V')
                time.sleep(2)
                # endregion

                # region Click on Post 24 horas button
                try:
                    # Attempt to click the button with a short timeout to avoid long hangs
                    page.locator('.swiper-slide:has-text("Post 24 horas")').click(timeout=10000)
                    time.sleep(2) # Small buffer for the UI to respond
                except Exception as e:
                    # STRATEGY: This runs if the button cannot be found or clicked
                    print(f"CRITICAL: Failed to click Post 24 horas at {minute_str}. Refreshing and skipping...")
                    page.reload()
                    time.sleep(5)
                    continue # Skips to the next minute iteration
                # endregion

                # region Try to click the Agendar Publicação switch with retries
                for attempt in range(max_retries):
                    if click_On_Agendar_publicacao_btn(page): 
                        #print(f"[{minute_str}] Agendar Publicação switch enabled.")
                        break
                    else:
                        print(f"[{minute_str}] Agendar Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(3)
                else:
                    # Failure handling: Refresh, wait, and skip to next minute loop iteration
                    print(f"CRITICAL: Could not toggle Agendar at {minute_str}. Refreshing...")
                    page.reload()
                    time.sleep(5)
                    continue # Jumps to the next minute in minute_functions.items()

                time.sleep(2)
                # endregion

                # region Try to click tomorrow's day with retries
                #print("Starting date selection for tomorrow...")

                for attempt in range(max_retries):
                    if click_tomorrow(page):
                        #print(f"[{minute_str}] Tomorrow's date selected successfully.")
                        break
                    else:
                        print(f"[{minute_str}] Date Selection Attempt {attempt + 1} failed. Retrying...")
                        if attempt < max_retries - 1:
                            time.sleep(3)
                else:
                    # This triggers if 'break' was never hit (all 3 attempts failed)
                    print("CRITICAL: Could not select the date. Refreshing and skipping...")
                    page.reload()
                    time.sleep(5)
                    continue  # Jumps to the next iteration of the minute loop

                # This part only runs if click_tomorrow was successful
                time.sleep(2)
                #print("Proceeding with posting instructions.")
                # endregion

                time.sleep(3)

                # region Try to click time element with retries
                for attempt in range(max_retries):
                    if click_time(page): 
                        #print(f"[{minute_str}] Time element opened.")
                        break
                    else:
                        print(f"[{minute_str}] Time Element Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(5)
                else:
                    # Failure handling for the time element
                    print(f"CRITICAL: Could not open time picker at {minute_str}. Refreshing...")
                    page.reload()
                    time.sleep(5)
                    continue # Skip to next minute iteration

                time.sleep(2)
                # endregion

                # region Try to click hour selection with retries
                for attempt in range(max_retries):
                    if click_hour(page): 
                        #print(f"[{minute_str}] Hour selection successful.")
                        break
                    else:
                        print(f"[{minute_str}] Hour Selection Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(5)
                else:
                    # Failure handling for the hour selection
                    print(f"CRITICAL: Could not select hour at {minute_str}. Refreshing...")
                    page.reload()
                    time.sleep(5)
                    continue # Skip to next minute iteration

                time.sleep(2)
                # endregion

                # region select hour accordingly to the current loop for hora
                for attempt in range(max_retries):
                    try:
                        # Use 'text=' with quotes to force an exact match on the hour
                        hour_selector = page.locator(f".dp__overlay_cell >> text='{hora_str}'")
                        
                        # Wait for and click the element
                        hour_selector.wait_for(state="visible", timeout=3000)
                        hour_selector.click()
                        
                        #print(f"[{minute_str}] Successfully clicked hour: {hora_str}")
                        break  # Exit the retry loop on success
                        
                    except Exception as e:
                        print(f"[{minute_str}] Attempt {attempt + 1} to select hour {hora_str} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(3)
                else:
                    # This block executes if all 3 attempts in the 'for' loop fail
                    print(f"CRITICAL: Failed to select hour {hora_str} after all retries. Refreshing...")
                    page.reload()
                    time.sleep(5)
                    continue  # Skip the rest of this minute loop and go to the next minute

                # Short sleep to allow the UI to transition
                time.sleep(2)
                # endregion
                    
                # region Try to click minute selection
                for attempt in range(max_retries):
                    if click_minute(page): 
                        #print(f"[{minute_str}] Minute selection successful.")
                        break
                    else:
                        print(f"[{minute_str}] Minute Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(5)
                else:
                    # If all attempts fail, reset the browser state
                    print(f"CRITICAL: Failed to select minute at {minute_str}. Refreshing...")
                    page.reload()
                    time.sleep(5)
                    continue  # Jumps to the next minute_str in the main loop

                time.sleep(2)
                # endregion

                # region Select the specific minute using the dictionary
                for attempt in range(max_retries):
                    #print(f"[{minute_str}] Attempt {attempt + 1} to select minute...")
                    
                    try:
                        # 1. Trigger the specific function from your dictionary
                        if click_func(page):
                            #print(f"Successfully clicked {minute_str} via dictionary function!")
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
                        print(f"Attempt {attempt + 1} failed with error: {e}")
                    
                    # If we reached here, it failed. Sleep before retrying.
                    if attempt < max_retries - 1:
                        time.sleep(2)
                else:
                    # This block triggers ONLY if 'break' was never called (total failure)
                    print(f"CRITICAL: All attempts for minute {minute_str} failed. Refreshing and skipping...")
                    page.reload()
                    time.sleep(5)
                    continue # Skip the rest of this minute loop iteration

                time.sleep(2)
                # endregion

                # region Try to click the Minute Up button with retries
                for attempt in range(max_retries):
                    if click_On_Minute_Up_btn(page):
                        break
                    else:
                        print(f"[{minute_str}] Minute Up Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(2)
                else:
                    print(f"CRITICAL: Failed Minute Up at {minute_str}. Refreshing...")
                    page.reload()
                    time.sleep(5)
                    continue

                time.sleep(2)
                # endregion

                # region Try to click Aplicar button in modal with retries
                max_retries = 3
                for attempt in range(max_retries):
                    # print(f"Attempt {attempt + 1} to click Aplicar button...")
                    if click_on_aplicar_button(page):
                        #print("Successfully clicked Aplicar button!")
                        break
                    else:
                        print(f"Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(1)
                else:
                    print("Failed to click Aplicar button after all attempts.")

                time.sleep(3)
                # endregion

                # region Try to click the Avançar button with retries
                for attempt in range(max_retries):
                    if click_On_Avancar_btn(page):
                        break
                    else:
                        print(f"[{minute_str}] Avançar Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(1)
                else:
                    print(f"CRITICAL: Failed Avançar at {minute_str}. Refreshing...")
                    page.reload()
                    time.sleep(5)
                    continue

                time.sleep(5)
                # endregion

                # region Try to click on Agendar button
                for attempt in range(max_retries):
                    if click_On_Agendar_btn(page):
                        break
                    else:
                        print(f"[{minute_str}] Agendar Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(3)
                else:
                    print(f"CRITICAL: Failed Agendar at {minute_str}. Refreshing...")
                    page.reload()
                    time.sleep(5)
                    continue

                time.sleep(2)
                # endregion       

                # region Try to click the Concluído button with retries
                for attempt in range(max_retries):
                    if click_On_Concluido_btn(page):
                        break
                    else:
                        print(f"[{minute_str}] Concluído Attempt {attempt + 1} failed.")
                        if attempt < max_retries - 1:
                            time.sleep(3)
                else:
                    print(f"CRITICAL: Failed Concluído at {minute_str}. Refreshing...")
                    page.reload()
                    time.sleep(5)
                    continue

                time.sleep(2)
                # endregion
                
                # Increment counters for next iteration
                i += 1  # Media file counter
                j += 1  # Phrase counter
                k += 1  # General counter
            
                mark_caption_as_used(current_caption)
                mark_media_as_used(current_media_filename)

        # region Persistence Loop
        print("\n=== Browser is ready ===")
        print("Script active. Close the Chrome window to exit.")
        # endregion

        while True:
            # For CDP connection, we check if the browser object is still connected
            if not context.browser or not context.browser.is_connected():
                print("Browser disconnected/closed by user. Shutting down...")
                break
            
            # Additional safety: check if all pages were closed
            if len(context.pages) == 0:
                print("All tabs closed. Shutting down...")
                break

            time.sleep(1)
        # endregion

    except Exception as e:
        print(f"Error during automation: {e}")
    finally:
        # 5. Cleanup
        print("Cleaning up Playwright resources...")
        try:
            pw.stop()
        except:
            pass
    
        print("Exiting process.")
        sys.exit(0)

if __name__ == "__main__":
    main()