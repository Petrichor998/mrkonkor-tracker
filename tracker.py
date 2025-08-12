#
# این کد نهایی و کامل است. تمام محتوای این کادر را کپی کنید
#
import requests
import json
import os
import re
from bs4 import BeautifulSoup
import sys
import time

# --- کتابخانه‌های سلنیوم ---
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

# --- تنظیمات اصلی ---
LOGIN_URL = 'https://mrkonkor.com/login'
STATS_URL = 'https://mrkonkor.com/user'
LICENSE_KEY = 'BZ8PEXS4GR7DJHN4YQLF'
TELEGRAM_BOT_TOKEN = '8308117883:AAGt32gWXGp44-_fBpLBMSfKDRidiW_0_34'
TELEGRAM_CHAT_ID = '5858496632'
COOKIES_FILE = 'cookies.json'
DATA_FILE = 'data.json'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'

# --- توابع ---

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print("پیام تلگرام با موفقیت ارسال شد.")
    except requests.exceptions.RequestException as e:
        print(f"خطا در ارسال پیام تلگرام: {e}")

def get_data_with_selenium():
    """
    یک مرورگر کامل را باز کرده، لاگین می‌کند، به صفحه آمار می‌رود،
    صبر می‌کند تا محتوا لود شود و سپس محتوای صفحه و کوکی‌ها را برمی‌گرداند.
    """
    print("در حال اجرای مرورگر مجازی برای ورود و دریافت اطلاعات...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f"user-agent={USER_AGENT}")

    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # مرحله لاگین
        driver.get(LOGIN_URL)
        wait = WebDriverWait(driver, 20)
        license_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[wire\\:model='license']")))
        license_input.send_keys(LICENSE_KEY)
        time.sleep(1)
        login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()
        wait.until(EC.url_to_be(STATS_URL))
        print("لاگین موفقیت‌آمیز بود.")

        # حالا که در صفحه آمار هستیم، کمی صبر می‌کنیم تا جاوا اسکریپت کارش را بکند
        print("منتظر لود شدن کامل اطلاعات صفحه...")
        time.sleep(7) # <<<<<<<< نکته کلیدی: اینجا صبر می‌کنیم

        # محتوای صفحه را استخراج می‌کنیم
        page_content = driver.page_source
        
        # کوکی‌ها را برای اجراهای بعدی ذخیره می‌کنیم
        selenium_cookies = driver.get_cookies()
        requests_cookies = {cookie['name']: cookie['value'] for cookie in selenium_cookies}

        return page_content, requests_cookies

    except TimeoutException as e:
        print(f"خطا: زمان انتظار تمام شد. جزئیات: {e}")
        send_telegram_message("ربات نتوانست وارد سایت شود یا صفحه آمار را لود کند (خطای Timeout).")
        driver.save_screenshot('error_screenshot.png')
        return None, None
    except Exception as e:
        print(f"خطایی هنگام کار با مرورگر رخ داد: {e}")
        send_telegram_message(f"ربات با خطای غیرمنتظره مواجه شد: {e}")
        driver.save_screenshot('error_screenshot.png')
        return None, None
    finally:
        driver.quit()

def get_data_with_cookies(session):
    """با استفاده از کوکی‌های موجود، صفحه آمار را دریافت می‌کند."""
    print("در حال دریافت صفحه آمار با استفاده از کوکی‌های ذخیره شده...")
    try:
        response = session.get(STATS_URL, allow_redirects=True, timeout=20)
        response.raise_for_status()
        
        # اگر به صفحه لاگین هدایت شدیم، یعنی کوکی‌ها نامعتبرند
        if 'ورود کاربر' in response.text or "login" in response.url:
            print("کوکی‌ها نامعتبر هستند.")
            return None
        
        print("صفحه آمار با کوکی دریافت شد.")
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"خطا در دریافت صفحه با کوکی: {e}")
        return None


# توابع extract_data و compare_data بدون تغییر باقی می‌مانند
def extract_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    sources_data = []
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string and "'name':'قلمچی'" in script.string:
            match = re.search(r"data:\s*(\[.*?\])", script.string, re.DOTALL)
            if match:
                json_string = match.group(1).replace("'", '"').replace('name', '"name"').replace('y', '"y"').replace('z', '"z"')
                json_string = re.sub(r'(,)\s*([}\]])', r'\2', json_string)
                try:
                    sources_data = json.loads(json_string)
                    print("اطلاعات منابع با موفقیت استخراج شد.")
                except json.JSONDecodeError as e:
                    print(f"خطا در پارس کردن اطلاعات منابع: {e} | رشته: {json_string[:200]}")
                break
    responses_data = []
    response_elements = soup.find_all('div', class_='flex w-[80%]')
    persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
    for el in response_elements:
        subject_el = el.find('span', class_='basis-1/4')
        numbers_el = el.find('span', class_=re.compile(r"absolute right-1"))
        if subject_el and numbers_el:
            subject = subject_el.get_text(strip=True)
            numbers_text = numbers_el.get_text(strip=True)
            match = re.search(r'از\s*([\d۰-۹]+)', numbers_text)
            if match:
                total_str = match.group(1).translate(persian_to_english)
                responses_data.append({'name': subject, 'total': int(total_str)})
    if responses_data:
        print("اطلاعات پاسخگویی دروس با موفقیت استخراج شد.")
    if not sources_data or not responses_data:
        send_telegram_message("اسکریپت نتوانست داده‌ها را از صفحه استخراج کند. ممکن است ساختار سایت تغییر کرده باشد.")
        with open('failed_extraction.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        return None
    return {'sources': sources_data, 'responses': responses_data}

def compare_data(old_data, new_data):
    changes = []
    old_sources_map = {item['name']: item['z'] for item in old_data['sources']}
    for new_item in new_data['sources']:
        name = new_item['name']
        if name in old_sources_map and old_sources_map[name] != new_item['z']:
            change = new_item['z'] - old_sources_map[name]
            changes.append(f"- {name} (منبع): {change:+} سوال")
    old_responses_map = {item['name']: item['total'] for item in old_data['responses']}
    for new_item in new_data['responses']:
        name = new_item['name']
        if name in old_responses_map and old_responses_map[name] != new_item['total']:
            change = new_item['total'] - old_responses_map[name]
            changes.append(f"- {name} (درس): {change:+} سوال")
    if not changes:
        return None
    message = "تغییرات جدید در داشبورد مستر کنکور:\n" + "\n".join(changes)
    return message

def main():
    page_html = None
    
    # 1. تلاش برای استفاده از کوکی‌های موجود
    if os.path.exists(COOKIES_FILE):
        session = requests.Session()
        session.headers.update({'User-Agent': USER_AGENT})
        with open(COOKIES_FILE, 'r') as f:
            cookies = json.load(f)
            session.cookies.update(cookies)
        page_html = get_data_with_cookies(session)

    # 2. اگر کوکی‌ها کار نکردند یا وجود نداشتند، از سلنیوم استفاده کن
    if not page_html:
        print("اجرای کامل با مرورگر...")
        page_html, new_cookies = get_data_with_selenium()
        if page_html and new_cookies:
            with open(COOKIES_FILE, 'w') as f:
                json.dump(new_cookies, f)
            print(f"کوکی‌ها در فایل {COOKIES_FILE} ذخیره/به‌روز شدند.")
        else:
            print("دریافت اطلاعات با مرورگر ناموفق بود. خروج.")
            sys.exit(1) # خروج با خطا
    
    # 3. استخراج و مقایسه داده‌ها
    new_data = extract_data(page_html)
    if not new_data:
        print("استخراج داده ناموفق بود. خروج از برنامه.")
        return

    if not os.path.exists(DATA_FILE):
        print(f"اجرای اول. در حال ذخیره داده‌های اولیه در {DATA_FILE}...")
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, ensure_ascii=False, indent=4)
        send_telegram_message("اسکریپت رهگیر سوالات با موفقیت راه‌اندازی شد. داده‌های اولیه ذخیره شدند.")
    else:
        print("در حال مقایسه با داده‌های قبلی...")
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
        
        change_message = compare_data(old_data, new_data)
        
        if change_message:
            print("تغییرات شناسایی شد!")
            print(change_message)
            send_telegram_message(change_message)
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, ensure_ascii=False, indent=4)
            print("فایل داده‌ها با مقادیر جدید به‌روزرسانی شد.")
        else:
            print("هیچ تغییری شناسایی نشد.")

if __name__ == "__main__":
    main()
