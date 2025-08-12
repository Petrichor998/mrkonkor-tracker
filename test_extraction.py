#
# این اسکریپت فقط برای تست استخراج داده است
#
import time
import re
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import requests

# --- تنظیمات ---
LOGIN_URL = 'https://mrkonkor.com/login'
STATS_URL = 'https://mrkonkor.com/user'
LICENSE_KEY = 'BZ8PEXS4GR7DJHN4YQLF'
TELEGRAM_BOT_TOKEN = '8308117883:AAGt32gWXGp44-_fBpLBMSfKDRidiW_0_34'
TELEGRAM_CHAT_ID = '5858496632'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    try:
        requests.post(url, json=payload, timeout=10).raise_for_status()
        print("پیام تست با موفقیت ارسال شد.")
    except requests.exceptions.RequestException as e:
        print(f"خطا در ارسال پیام تلگرام: {e}")

def extract_data_with_selenium(driver):
    print("شروع استخراج داده...")
    sources_data = []
    try:
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "g.highcharts-series-group .highcharts-point")))
        scripts = driver.execute_script("return document.getElementsByTagName('script');")
        for script in scripts:
            content = driver.execute_script("return arguments[0].innerHTML;", script)
            if content and "Highcharts.chart('container'" in content:
                pattern = re.compile(r"'name':'(.*?)','y':[\d.]+,'z':(\d+)")
                matches = pattern.findall(content)
                for match in matches:
                    sources_data.append({"name": match[0], "z": int(match[1])})
                if sources_data:
                    print(f"اطلاعات منابع استخراج شد: {len(sources_data)} منبع")
                break
    except Exception as e:
        print(f"خطا در استخراج اطلاعات منابع: {e}")

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
            print(f"اطلاعات دروس استخراج شد: {len(responses_data)} درس")
    except Exception as e:
        print(f"خطا در استخراج اطلاعات دروس: {e}")

    if not sources_data or not responses_data:
        return None
    return {'sources': sources_data, 'responses': responses_data}

def main():
    print("--- شروع اسکریپت تست ---")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(f"user-agent={USER_AGENT}")
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        driver.get(LOGIN_URL)
        wait = WebDriverWait(driver, 30)
        license_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[wire\\:model='license']")))
        license_input.send_keys(LICENSE_KEY)
        time.sleep(1)
        login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
        driver.execute_script("arguments[0].click();", login_button)
        wait.until(EC.url_to_be(STATS_URL))
        print("ورود موفقیت‌آمیز بود.")
        time.sleep(10)

        extracted_data = extract_data_with_selenium(driver)

        if extracted_data:
            message = "📊 گزارش تست استخراج داده:\n\n"
            message += "📚 **منابع:**\n"
            for item in extracted_data['sources']:
                message += f"- {item['name']}: {item['z']} سوال\n"
            
            message += "\n"
            message += "📖 **دروس:**\n"
            for item in extracted_data['responses']:
                message += f"- {item['name']}: {item['total']} سوال\n"
            
            send_telegram_message(message)
        else:
            send_telegram_message("❌ تست ناموفق بود. داده‌ای استخراج نشد.")

    except Exception as e:
        print(f"خطایی در اسکریپت تست رخ داد: {e}")
        send_telegram_message(f"❌ اسکریپت تست با خطا مواجه شد: {e}")
    finally:
        driver.quit()
        print("--- پایان اسکریپت تست ---")

if __name__ == "__main__":
    main()
