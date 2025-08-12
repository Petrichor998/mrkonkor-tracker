#
# نسخه نهایی با استخراج مستقیم داده توسط سلنیوم
#
import requests
import json
import os
import re
from bs4 import BeautifulSoup
import sys
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
TELEGRAM_BOT_TOKEN = '8308117883:AAGt32gWXGp44-_fBpLBMSfKDRidiW_0_34'
TELEGRAM_CHAT_ID = '5858496632'
COOKIES_FILE = 'cookies.json'
DATA_FILE = 'data.json'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    try:
        requests.post(url, json=payload, timeout=10).raise_for_status()
        print("پیام تلگرام با موفقیت ارسال شد.")
    except requests.exceptions.RequestException as e:
        print(f"خطا در ارسال پیام تلگرام: {e}")

def extract_data_with_selenium(driver):
    """مستقیماً با استفاده از درایور سلنیوم داده‌ها را استخراج می‌کند."""
    print("شروع استخراج داده با سلنیوم...")
    
    # 1. استخراج اطلاعات منابع (نمودار دایره‌ای)
    sources_data = []
    try:
        wait = WebDriverWait(driver, 15)
        # انتظار برای اینکه نمودار کاملا ساخته شود
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "g.highcharts-series-group .highcharts-point")))
        
        # پیدا کردن اسکریپت حاوی داده‌ها
        scripts = driver.execute_script("return document.getElementsByTagName('script');")
        for script in scripts:
            content = driver.execute_script("return arguments[0].innerHTML;", script)
            if content and "Highcharts.chart('container'" in content:
                match = re.search(r"data:\s*(\[.*?\])", content, re.DOTALL)
                if match:
                    json_string = match.group(1).replace("'", '"')
                    json_string = re.sub(r'(\w+):', r'"\1":', json_string)
                    json_string = re.sub(r',\s*([}\]])', r'\1', json_string)
                    sources_data = json.loads(json_string)
                    print(f"اطلاعات منابع با موفقیت استخراج شد: {len(sources_data)} منبع")
                    break
    except Exception as e:
        print(f"خطا در استخراج اطلاعات منابع: {e}")

    # 2. استخراج اطلاعات پاسخگویی (میله‌های پیشرفت)
    responses_data = []
    try:
        persian_to_english = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
        response_elements = driver.find_elements(By.CSS_SELECTOR, "div.flex.w-\\[80\\%\\]")
        for el in response_elements:
            subject = el.find_element(By.CSS_SELECTOR, "span.basis-1\\/4").text
            numbers_text = el.find_element(By.CSS_SELECTOR, "span[class^='absolute right-1']").text
            match = re.search(r'از\s*([\d۰-۹]+)', numbers_text)
            if match:
                total_str = match.group(1).translate(persian_to_english)
                responses_data.append({'name': subject, 'total': int(total_str)})
        if responses_data:
            print(f"اطلاعات دروس با موفقیت استخراج شد: {len(responses_data)} درس")
    except Exception as e:
        print(f"خطا در استخراج اطلاعات دروس: {e}")

    if not sources_data or not responses_data:
        send_telegram_message("اسکریپت نتوانست داده‌ها را استخراج کند. ممکن است ساختار سایت تغییر کرده باشد.")
        return None
        
    return {'sources': sources_data, 'responses': responses_data}

def process_data(new_data):
    if not os.path.exists(DATA_FILE):
        print(f"اجرای اول. در حال ذخیره داده‌های اولیه...")
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, ensure_ascii=False, indent=4)
        send_telegram_message("اسکریپت رهگیر سوالات با موفقیت راه‌اندازی شد. داده‌های اولیه ذخیره شدند.")
    else:
        print("در حال مقایسه با داده‌های قبلی...")
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
        
        # تابع مقایسه
        changes = []
        old_sources_map = {item.get('name'): item.get('z', 0) for item in old_data.get('sources', [])}
        new_sources_map = {item.get('name'): item.get('z', 0) for item in new_data.get('sources', [])}
        all_source_names = sorted(list(set(old_sources_map.keys()) | set(new_sources_map.keys())))

        for name in all_source_names:
            old_val = old_sources_map.get(name, 0)
            new_val = new_sources_map.get(name, 0)
            if old_val != new_val:
                change = new_val - old_val
                changes.append(f"- {name} (منبع): {change:+} سوال")

        old_responses_map = {item.get('name'): item.get('total', 0) for item in old_data.get('responses', [])}
        new_responses_map = {item.get('name'): item.get('total', 0) for item in new_data.get('responses', [])}
        all_response_names = sorted(list(set(old_responses_map.keys()) | set(new_responses_map.keys())))

        for name in all_response_names:
            old_val = old_responses_map.get(name, 0)
            new_val = new_responses_map.get(name, 0)
            if old_val != new_val:
                change = new_val - old_val
                changes.append(f"- {name} (درس): {change:+} سوال")
        
        if changes:
            message = "تغییرات جدید در داشبورد مستر کنکور:\n" + "\n".join(changes)
            print("تغییرات شناسایی شد!")
            print(message)
            send_telegram_message(message)
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, ensure_ascii=False, indent=4)
            print("فایل داده‌ها با مقادیر جدید به‌روزرسانی شد.")
        else:
            print("هیچ تغییری شناسایی نشد.")

def main():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(f"user-agent={USER_AGENT}")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # همیشه ابتدا با کوکی‌ها امتحان کن
        if os.path.exists(COOKIES_FILE):
            print("در حال تلاش برای ورود با کوکی...")
            # برای استفاده از کوکی، باید ابتدا به دامنه سایت برویم
            driver.get(LOGIN_URL) 
            with open(COOKIES_FILE, 'r') as f:
                cookies = json.load(f)
            for cookie in cookies:
                driver.add_cookie(cookie)
            
            driver.get(STATS_URL)
            time.sleep(5) # صبر برای ریدایرکت احتمالی
            
            if "login" not in driver.current_url:
                print("ورود با کوکی موفق بود.")
                new_data = extract_data_with_selenium(driver)
                if new_data:
                    process_data(new_data)
                    return
                else:
                    print("استخراج داده با کوکی ناموفق بود. تلاش برای لاگین کامل...")
            else:
                print("کوکی‌ها نامعتبر بودند.")

        # اگر ورود با کوکی موفق نبود، لاگین کامل انجام بده
        print("شروع فرآیند لاگین کامل با مرورگر...")
        driver.get(LOGIN_URL)
        wait = WebDriverWait(driver, 30)
        
        license_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[wire\\:model='license']")))
        license_input.send_keys(LICENSE_KEY)
        time.sleep(1)

        login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
        driver.execute_script("arguments[0].click();", login_button)

        print("در انتظار لود شدن صفحه آمار...")
        wait.until(EC.url_to_be(STATS_URL))
        
        new_data = extract_data_with_selenium(driver)
        if new_data:
            # ذخیره کوکی‌های جدید
            with open(COOKIES_FILE, 'w') as f:
                json.dump(driver.get_cookies(), f)
            print("کوکی‌های جدید ذخیره شدند.")
            process_data(new_data)
        else:
            print("استخراج داده پس از لاگین کامل نیز ناموفق بود.")
            sys.exit(1)

    except Exception as e:
        print(f"یک خطای بزرگ در فرآیند اصلی رخ داد: {e}")
        send_telegram_message(f"ربات با خطای بحرانی مواجه شد: {e}")
        driver.save_screenshot('critical_error.png')
        sys.exit(1)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
