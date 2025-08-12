#
# این کد کامل است. تمام محتوای این کادر را کپی کنید
#
import requests
import json
import os
import re
from bs4 import BeautifulSoup
import sys

# --- تنظیمات اصلی ---
LOGIN_URL = 'https://mrkonkor.com/login'
STATS_URL = 'https://mrkonkor.com/user'
LICENSE_KEY = 'BZ8PEXS4GR7DJHN4YQLF'
TELEGRAM_BOT_TOKEN = '8308117883:AAGt32gWXGp44-_fBpLBMSfKDRidiW_0_34'
TELEGRAM_CHAT_ID = '5858496632'
COOKIES_FILE = 'cookies.json'
DATA_FILE = 'data.json'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

# --- توابع برنامه ---

def send_telegram_message(message):
    """یک پیام به کاربر تلگرام ارسال می‌کند."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("پیام تلگرام با موفقیت ارسال شد.")
    except requests.exceptions.RequestException as e:
        print(f"خطا در ارسال پیام تلگرام: {e}")

def perform_login(session):
    """وارد سایت شده و کوکی‌ها را ذخیره می‌کند."""
    print("در حال ورود به سایت برای اولین بار...")
    try:
        # درخواست اولیه برای گرفتن کوکی‌های لازم
        login_page_res = session.get(LOGIN_URL, headers={'User-Agent': USER_AGENT})
        login_page_res.raise_for_status()
        soup = BeautifulSoup(login_page_res.text, 'html.parser')
        
        # پیدا کردن توکن CSRF
        token_element = soup.find('input', {'name': '_token'})
        if not token_element:
             print("توکن CSRF پیدا نشد. ممکن است لاگین با مشکل مواجه شود.")
             # در صورت نبود توکن استاندارد، با یک فرم ساده تلاش می‌کنیم
             payload = {'license': LICENSE_KEY}
        else:
             payload = {'_token': token_element['value'], 'license': LICENSE_KEY}

        # ارسال درخواست لاگین
        login_response = session.post(LOGIN_URL, data=payload, headers={'User-Agent': USER_AGENT, 'Referer': LOGIN_URL})
        login_response.raise_for_status()

        # بررسی موفقیت لاگین با مراجعه به صفحه آمار
        test_res = session.get(STATS_URL, headers={'User-Agent': USER_AGENT})
        if 'ورود کاربر' in test_res.text or "login" in test_res.url:
             raise Exception("لاگین ناموفق بود. لایسنس یا ساختار صفحه لاگین را بررسی کنید.")

        print("لاگین موفقیت‌آمیز بود.")
        with open(COOKIES_FILE, 'w') as f:
            json.dump(session.cookies.get_dict(), f)
        print(f"کوکی‌ها در فایل {COOKIES_FILE} ذخیره شدند.")
        return session

    except Exception as e:
        print(f"خطایی هنگام لاگین رخ داد: {e}")
        send_telegram_message(f"ربات نتوانست وارد سایت شود. خطا: {e}")
        sys.exit(1)


def get_session():
    """یک سشن جدید می‌سازد یا کوکی‌های قبلی را بارگذاری می‌کند."""
    session = requests.Session()
    if os.path.exists(COOKIES_FILE):
        print(f"فایل {COOKIES_FILE} پیدا شد، در حال بارگذاری کوکی‌ها...")
        with open(COOKIES_FILE, 'r') as f:
            cookies = json.load(f)
            session.cookies.update(cookies)
    else:
        print(f"فایل {COOKIES_FILE} پیدا نشد.")
        session = perform_login(session)
    return session

def extract_data(html_content):
    """اطلاعات سوالات را از صفحه استخراج می‌کند."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # استخراج اطلاعات منابع (نمودار دایره‌ای)
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
                    print(f"خطا در پارس کردن اطلاعات منابع: {e}")
                break

    # استخراج اطلاعات پاسخگویی (میله‌های پیشرفت)
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
        return None

    return {'sources': sources_data, 'responses': responses_data}

def compare_data(old_data, new_data):
    """داده‌های جدید و قدیم را مقایسه کرده و پیام تغییرات را برمی‌گرداند."""
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

# --- منطق اصلی برنامه ---
def main():
    session = get_session()
    
    print("در حال دریافت صفحه آمار...")
    try:
        response = session.get(STATS_URL, headers={'User-Agent': USER_AGENT}, allow_redirects=True)
        response.raise_for_status()
        
        if 'ورود کاربر' in response.text or "login" in response.url:
            print("کوکی نامعتبر است. در حال تلاش برای لاگین مجدد...")
            if os.path.exists(COOKIES_FILE):
                os.remove(COOKIES_FILE)
            session = perform_login(requests.Session())
            response = session.get(STATS_URL, headers={'User-Agent': USER_AGENT})
            response.raise_for_status()
            if 'ورود کاربر' in response.text:
                 raise Exception("لاگین مجدد ناموفق بود. برنامه متوقف می‌شود.")
        
        print("صفحه آمار با موفقیت دریافت شد.")
    except requests.exceptions.RequestException as e:
        print(f"خطا در دریافت صفحه آمار: {e}")
        send_telegram_message(f"خطا در دسترسی به صفحه آمار: {e}")
        return

    new_data = extract_data(response.text)
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
