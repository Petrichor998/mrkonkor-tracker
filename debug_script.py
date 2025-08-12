import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# --- تنظیمات ---
LOGIN_URL = 'https://mrkonkor.com/login'
STATS_URL = 'https://mrkonkor.com/user'
LICENSE_KEY = 'BZ8PEXS4GR7DJHN4YQLF'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'

print("--- شروع اسکریپت عیب‌یابی ---")

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument(f"user-agent={USER_AGENT}")

driver = webdriver.Chrome(options=chrome_options)

try:
    print("در حال باز کردن صفحه لاگین...")
    driver.get(LOGIN_URL)
    wait = WebDriverWait(driver, 20)

    print("در انتظار فیلد لایسنس...")
    license_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[wire\\:model='license']")))
    license_input.send_keys(LICENSE_KEY)
    print("لایسنس وارد شد.")
    time.sleep(1)

    print("در حال کلیک روی دکمه ورود...")
    login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    login_button.click()

    print("در انتظار ریدایرکت شدن به صفحه آمار...")
    wait.until(EC.url_to_be(STATS_URL))
    print("ورود موفقیت‌آمیز بود. در حال حاضر در صفحه آمار هستیم.")

    print("۱۵ ثانیه صبر برای لود کامل محتوای صفحه...")
    time.sleep(15)

    print("صبر به پایان رسید.")

except Exception as e:
    print(f"!!! یک خطا در حین اجرای اسکریپت رخ داد: {e}")

finally:
    print("در حال ذخیره فایل‌های خروجی برای عیب‌یابی...")
    # ذخیره محتوای صفحه
    with open('debug_page.html', 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    print("محتوای صفحه در debug_page.html ذخیره شد.")

    # ذخیره اسکرین‌شات
    driver.save_screenshot('debug_screenshot.png')
    print("اسکرین‌شات در debug_screenshot.png ذخیره شد.")
    
    driver.quit()
    print("--- پایان اسکریپت عیب‌یابی ---")
