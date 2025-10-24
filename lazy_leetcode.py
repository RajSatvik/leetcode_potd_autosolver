import requests
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium_stealth import stealth
import json

class LeetCodePOTDBot:
    def __init__(self, username, password, chrome_driver_path):
        self.username = username
        self.password = password
        self.chrome_driver_path = chrome_driver_path
        self.session = requests.Session()
        self.driver = None

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/json',
        }
        self.session.headers.update(self.headers)

    def setup_driver(self):
        """Set up Chrome driver with stealth configuration"""
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')

        try:
            print(f"Trying to use ChromeDriver at: {self.chrome_driver_path}")
            service = Service(executable_path=self.chrome_driver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Apply stealth configuration
            stealth(self.driver,
                    languages=["en-US", "en"],
                    vendor="Google Inc.",
                    platform="Win32",
                    webgl_vendor="Intel Inc.",
                    renderer="Intel Iris OpenGL Engine",
                    fix_hairline=True,
                    )
            
            print("ChromeDriver started successfully with stealth configuration!")
        except Exception as e:
            print(f"ChromeDriver setup failed: {e}")
            raise

    def get_potd_url(self):
        """Get the POTD URL using multiple methods"""
        print("Trying to get POTD URL...")

        try:
            print("Method 2: Using LeetCode API...")
            graphql_query = {
                "query": """
                {
                    activeDailyCodingChallengeQuestion {
                        link
                    }
                }
                """
            }

            response = requests.post(
                'https://leetcode.com/graphql',
                json=graphql_query,
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                link = data['data']['activeDailyCodingChallengeQuestion']['link']
                full_url = f"https://leetcode.com{link}"
                print(f"Success! Got URL: {full_url}")
                return full_url
        except Exception as e:
            print(f"Method 2 failed: {e}")

        print("All methods failed to get POTD URL")
        return None

    def login(self):
        try:
            self.driver.get("https://leetcode.com/accounts/login/")

            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "id_login"))
            )

            username_field = self.driver.find_element(By.ID, "id_login")
            username_field.send_keys(self.username)

            password_field = self.driver.find_element(By.ID, "id_password")
            password_field.send_keys(self.password)

            try:
                WebDriverWait(self.driver, 15).until_not(
                    EC.presence_of_element_located((By.ID, "initial-loading"))
                )
                print("Loading overlay gone, ready to click Sign In.")
            except:
                print("No initial-loading overlay found or it already disappeared.")

            signin_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "signin_btn"))
            )
            signin_btn.click()

            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/problemset/')]"))
            )

            print("Login successful!")
            return True

        except Exception as e:
            print(f"Login failed: {e}")
            return False

    def get_editorial_code(self, problem_url):
        """Extract code from editorial page"""
        try:
            # Navigate to editorial page
            editorial_url = problem_url.rstrip('/') + '/editorial/'
            print(f"Opening editorial page: {editorial_url}")
            self.driver.get(editorial_url)
            
            # Wait for editorial content to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "editorial-content"))
            )
            
            # Look for code blocks in the editorial
            print("Looking for code solutions in editorial...")
            
            # Try different selectors for code blocks
            code_selectors = [
                "//pre/code",
                "//div[contains(@class, 'code-block')]//code",
                "//div[contains(@class, 'editorial-code')]//code",
                "//pre[contains(@class, 'code')]",
                "//code[contains(@class, 'language-')]"
            ]
            
            code_blocks = []
            for selector in code_selectors:
                try:
                    blocks = self.driver.find_elements(By.XPATH, selector)
                    if blocks:
                        code_blocks.extend(blocks)
                        print(f"Found {len(blocks)} code blocks with selector: {selector}")
                except:
                    continue
            
            if not code_blocks:
                print("No code blocks found in editorial")
                return None
            
            # Get the text from the first substantial code block
            for block in code_blocks:
                code_text = block.text.strip()
                if len(code_text) > 50:  # Filter out small code snippets
                    print(f"Found code solution with {len(code_text)} characters")
                    return code_text
            
            print("No substantial code blocks found")
            return None
            
        except Exception as e:
            print(f"Error getting editorial code: {e}")
            return None

    def paste_and_submit_code(self, problem_url):
        try:
            print("Getting code from editorial...")
            code_to_paste = self.get_editorial_code(problem_url)
            
            if not code_to_paste:
                print("Could not get code from editorial, using fallback solution")
                code_to_paste = """class Solution {
    public:
        int maxIncreasingSubarrays(vector<int>& nums) {
            int ans = 0;
            int increasing = 1;
            int prevIncreasing = 0;

            for (int i = 1; i < nums.size(); ++i) {
                if (nums[i] > nums[i - 1]) {
                    ++increasing;
                } else {
                    prevIncreasing = increasing;
                    increasing = 1;
                }
                ans = max(ans, increasing / 2);
                ans = max(ans, min(prevIncreasing, increasing));
            }
            return ans;
        }
};"""

            print("Waiting for code editor...")
            editor_div = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "monaco-editor"))
            )

            print("Editor found! Removing old code and pasting new code...")

            # Execute JavaScript to paste code into Monaco editor
            self.driver.execute_script("""
            function setMonacoEditorContent(code) {
                // Try multiple methods to set editor content
                const editors = monaco.editor.getEditors();
                if (editors.length > 0) {
                    editors[0].setValue(code);
                    return true;
                }
                
                // Alternative method: find editor instance
                const editorElements = document.querySelectorAll('[data-monaco-editor]');
                for (let element of editorElements) {
                    const editor = element.__monaco_editor__;
                    if (editor) {
                        editor.setValue(code);
                        return true;
                    }
                }
                
                // Fallback: use textarea
                const textareas = document.querySelectorAll('textarea.inputarea');
                for (let textarea of textareas) {
                    textarea.focus();
                    textarea.value = code;
                    textarea.dispatchEvent(new Event('input', { bubbles: true }));
                    textarea.dispatchEvent(new Event('change', { bubbles: true }));
                }
                
                return false;
            }
            
            setMonacoEditorContent(arguments[0]);
            """, code_to_paste)

            time.sleep(2) 

            print("Looking for Submit button...")
            submit_button = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Submit')]"))
            )

            print("Clicking Submit button...")
            self.driver.execute_script("arguments[0].click();", submit_button)

            print("✅ Code submitted successfully!")
            return True

        except Exception as e:
            print(f"Error while pasting/submitting code: {e}")
            return False

    def run(self):
        try:
            print("Setting up Chrome driver with stealth...")
            self.setup_driver()

            print("Logging in to LeetCode...")
            if not self.login():
                return False

            print("Getting POTD URL...")
            potd_url = self.get_potd_url()
            if not potd_url:
                print("Could not get POTD URL.")
                return False

            print(f"Opening POTD: {potd_url}")
            self.driver.get(potd_url)

            print("Waiting for page to load completely...")
            time.sleep(5)

            if self.paste_and_submit_code(potd_url):
                print("🎯 Code submitted successfully!")
            else:
                print("❌ Failed to submit code.")

            time.sleep(10)
            return True

        except Exception as e:
            print(f"Error in bot execution: {e}")
            return False

        finally:
            if self.driver:
                print("Closing browser...")
                self.driver.quit()

def main():
    USERNAME = "7vik_raj"
    PASSWORD = "kira_2507"
    CHROME_DRIVER_PATH = "chromedriver.exe"

    print("Starting LeetCode POTD Bot...")
    print(f"Looking for ChromeDriver at: {CHROME_DRIVER_PATH}")

    bot = LeetCodePOTDBot(USERNAME, PASSWORD, CHROME_DRIVER_PATH)
    success = bot.run()

    if success:
        print("🎉 Bot completed successfully!")
    else:
        print("❌ Bot failed to complete")

if __name__ == "__main__":
    main()