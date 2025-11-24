import streamlit as st
import datetime
import os.path
import pickle
import re
import json # <--- عشان نحفظ حالة المستخدمين
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import time
import threading # <--- عشان نشغل البوت في الخلفية وميوقفش مع الريستارت

# --- إعدادات عامة ---
SCOPES = ['https://www.googleapis.com/auth/calendar']
MY_PORTFOLIO_URL = "https://your-portfolio-link.com" 
SESSIONS_FILE = "active_sessions.json" # ده الدفتر اللي بنسجل فيه مين شغال

# --- دوال إدارة الجلسات (الذاكرة الدائمة) ---
def load_sessions():
    if not os.path.exists(SESSIONS_FILE):
        return {}
    try:
        with open(SESSIONS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_session(username, status_data):
    sessions = load_sessions()
    sessions[username] = status_data
    with open(SESSIONS_FILE, "w") as f:
        json.dump(sessions, f)

def remove_session(username):
    sessions = load_sessions()
    if username in sessions:
        del sessions[username]
        with open(SESSIONS_FILE, "w") as f:
            json.dump(sessions, f)

def is_user_active(username):
    sessions = load_sessions()
    return username in sessions

# --- دوال جوجل والتحليل (الأساسية) ---
def get_calendar_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('calendar', 'v3', credentials=creds)

def extract_date_regex(text):
    if not text: return None
    match = re.search(r'\d{4}-\d{2}-\d{2}', text)
    if match: return match.group(0)
    return None

def add_event_to_calendar(service, full_title, release_date, deadline_date, link):
    try:
        if not release_date or not deadline_date: return False, "تاريخ غير صالح"
        events_result = service.events().list(calendarId='primary', timeMin=f"{release_date}T00:00:00Z", timeMax=f"{release_date}T23:59:59Z", singleEvents=True, q=full_title).execute()
        if events_result.get('items', []): return True, "موجود بالفعل"
        until_date = deadline_date.replace("-", "")
        event = {
            'summary': f'📘 {full_title}',
            'location': 'BATU LMS',
            'description': f'🚨 DEADLINE: {deadline_date}\n\nرابط التسليم: {link}\n\nAdded by BATU Bot 🤖',
            'start': {'date': release_date, 'timeZone': 'Africa/Cairo'},
            'end': {'date': release_date, 'timeZone': 'Africa/Cairo'},
            'recurrence': [f'RRULE:FREQ=DAILY;UNTIL={until_date}T235959Z'],
            'reminders': {'useDefault': False, 'overrides': [{'method': 'popup', 'minutes': 60}]}
        }
        service.events().insert(calendarId='primary', body=event).execute()
        return True, "تمت الإضافة"
    except Exception as e: return False, str(e)

def delete_old_events(service):
    try:
        events_result = service.events().list(calendarId='primary', q='BATU Bot', singleEvents=True).execute()
        events = events_result.get('items', [])
        if not events: return 0, "نظيف"
        for event in events:
            service.events().delete(calendarId='primary', eventId=event['id']).execute()
        return len(events), "تم الحذف"
    except: return 0, "خطأ"

def check_lms_assignments(username, password):
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument('--ignore-certificate-errors')
    driver = webdriver.Chrome(options=chrome_options)
    found_data = []
    logs = []

    try:
        driver.get("https://batechu.com/lms/login")
        driver.find_element(By.ID, "email").send_keys(username)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.XPATH, "//button[contains(., 'Log in')]").click()
        time.sleep(3) 

        if "login" in driver.current_url:
            page_src = driver.page_source
            if "The password you entered is incorrect" in page_src or "credentials" in page_src:
                return ["❌ الباسورد غلط يا هندسة."], []
            return ["🚫 الأكونت مقفول (مصاريف) أو فيه مشكلة تفعيل."], []

        driver.get("https://batechu.com/lms/assignments")
        logs.append("✅ تم الدخول (Online)")
        time.sleep(8)

        release_elements = driver.find_elements(By.XPATH, "//time[contains(text(), 'Released on')]")
        logs.append(f"🔍 فحص {len(release_elements)} عنصر...")

        for el in release_elements:
            try:
                raw_text = el.get_attribute("textContent")
                release_date = extract_date_regex(raw_text)
                if not release_date: continue
                box = el.find_element(By.XPATH, "./../..")
                try:
                    deadline_el = box.find_element(By.XPATH, ".//*[contains(@class, 'text-red-500') or contains(@class, 'text-green-500')]")
                    d_text = extract_date_regex(deadline_el.get_attribute("textContent"))
                    deadline_date = d_text if d_text else release_date
                except: deadline_date = release_date
                try:
                    header_h2 = box.find_element(By.XPATH, "./preceding-sibling::h2[1]")
                    assignment_name_el = header_h2.find_element(By.XPATH, ".//button/span")
                    assignment_name = assignment_name_el.get_attribute("textContent").strip()
                except: assignment_name = "Assignment"
                try:
                    course_body = el.find_element(By.XPATH, "./ancestor::div[contains(@class, 'dark:bg-gray-900')]")
                    subject_el = course_body.find_element(By.XPATH, ".//strong")
                    subject_name = subject_el.get_attribute("textContent").strip()
                except: subject_name = "Course"
                full_title = f"{subject_name} : {assignment_name}"
                try: link = box.find_element(By.XPATH, ".//a[contains(@href, 'files')]").get_attribute('href')
                except: link = "https://batechu.com/lms/assignments"
                if release_date and deadline_date:
                    found_data.append({"title": full_title, "release_date": release_date, "deadline_date": deadline_date, "link": link})
            except: continue
    except Exception as e: logs.append(f"Error: {e}")
    finally: driver.quit()
    return logs, found_data

# --- وظيفة المراقبة في الخلفية (Background Worker) ---
def run_background_monitor(user, pw, interval_minutes):
    """
    دي الوظيفة اللي هتشتغل في الخلفية وتفضل تلف وتدور
    """
    try:
        # إنشاء اتصال منفصل بجوجل داخل الثريد
        srv = get_calendar_service()
        
        while True:
            # 1. هل المستخدم لسه موجود في ملف الذاكرة؟
            if not is_user_active(user):
                print(f"Stopping monitor for {user}...")
                break # وقف المراقبة لو الاسم اتمسح

            print(f"Checking for {user}...")
            
            # 2. تنفيذ الفحص
            try:
                logs, data = check_lms_assignments(user, pw)
                if data:
                    for d in data:
                        add_event_to_calendar(srv, d['title'], d['release_date'], d['deadline_date'], d['link'])
            except:
                pass
            
            # 3. الانتظار
            time.sleep(interval_minutes * 60)
            
    except Exception as e:
        print(f"Thread Error: {e}")

# --- UI Design ---
st.set_page_config(page_title="BATU Notification LMS", page_icon="🎓")
st.markdown("""
<style>
    .footer {position: fixed; left: 0; bottom: 0; width: 100%; background-color: #0e1117; color: white; text-align: center; padding: 10px; border-top: 1px solid #333; z-index: 100;}
    .footer a {color: #4ea4f9; text-decoration: none; font-weight: bold;}
    [data-testid="stImage"] {display: flex; justify-content: center;}
</style>
""", unsafe_allow_html=True)

c1, c2, c3 = st.columns([1, 2, 1])
with c1:
    if os.path.exists("uni_logo.png"): st.image("uni_logo.png", width=90)
with c3:
    if os.path.exists("it_logo.png"): st.image("it_logo.png", width=90)
with c2:
    st.title("BATU Notification LMS")
    st.caption("نظام إشعارات تلقائي للجامعة")

tab_live, tab_manual, tab_clean = st.tabs(["🔴 Live Tracker", "🔄 Insert Past Assignment", "🗑️ Clean"])

# --- 1. Live Tracker (الذكي) ---
with tab_live:
    st.markdown("### نظام المراقبة الحية")
    st.info("أدخل بياناتك لمرة واحدة، وسيقوم النظام بالمتابعة تلقائياً.")

    # الخانات ظاهرة دائماً
    col_a, col_b = st.columns(2)
    with col_a:
        live_user = st.text_input("Username", placeholder="24xxxx@batechu.com", key="live_u")
    with col_b:
        live_pass = st.text_input("Password", type="password", key="live_p")
    
    refresh_rate = st.slider("افحص الموقع كل (دقائق):", 10, 180, 60)

    # فحص الحالة من "الدفتر" (الملف)
    # لو اليوزر كاتب اسمه، نشوف حالته هو
    # لو مش كاتب، مش هنعرف نعرض حالة
    
    if live_user:
        is_active = is_user_active(live_user)
        
        if is_active:
            # نجيب وقت البدء
            sessions = load_sessions()
            start_time = sessions.get(live_user, {}).get("start_time", "Unknown")
            
            st.success(f"✅ يا هندسة، نظام المراقبة بتاعك مُفعل وشغال بالفعل منذ: {start_time}")
            
            if st.button(f"🛑 إلغاء المراقبة لـ {live_user}"):
                remove_session(live_user)
                st.warning("تم إلغاء المراقبة بنجاح! سيتوقف البوت قريباً.")
                time.sleep(1)
                st.rerun()
        else:
            if st.button("ابدأ المراقبة الآن 🚀"):
                if live_user and live_pass:
                    # 1. حفظ الحالة في الملف
                    now_str = datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p")
                    save_session(live_user, {"start_time": now_str, "rate": refresh_rate})
                    
                    # 2. تشغيل البوت في ثريد منفصل (عشان يفضل شغال حتى لو قفلت الصفحة)
                    t = threading.Thread(target=run_background_monitor, args=(live_user, live_pass, refresh_rate))
                    t.daemon = True # عشان يقفل لما السيرفر الرئيسي يقفل
                    t.start()
                    
                    st.toast(f"تم تفعيل البوت لـ {live_user}!", icon="📡")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("دخل الباسورد يا هندسة!")
    else:
        st.caption("👈 اكتب اليوزر نيم عشان نشوف حالتك.")

# --- 2. Manual ---
with tab_manual:
    with st.form("sync_manual"):
        m_user = st.text_input("Username")
        m_pw = st.text_input("Password", type="password")
        m_sub = st.form_submit_button("Insert Past Assignments")
    if m_sub and m_user and m_pw:
        with st.status("Working...", expanded=True):
            logs, data = check_lms_assignments(m_user, m_pw)
            for l in logs: 
                if "❌" in l or "🚫" in l: st.error(l)
                else: st.text(l)
            if data:
                srv = get_calendar_service()
                for d in data:
                    s, m = add_event_to_calendar(srv, d['title'], d['release_date'], d['deadline_date'], d['link'])
                    if s: st.success(f"✅ {d['title']}")
                    else: st.error(f"❌ {d['title']} -> {m}")
            else: st.warning("No data.")

# --- 3. Clean ---
with tab_clean:
    if st.button("Clean All Events"):
        srv = get_calendar_service()
        c, m = delete_old_events(srv)
        st.success(m)

st.markdown(f"""<div class="footer">Developed with ❤️ by <a href="{MY_PORTFOLIO_URL}" target="_blank">Omar Mehawed</a></div>""", unsafe_allow_html=True)