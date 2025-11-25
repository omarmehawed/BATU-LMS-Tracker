import streamlit as st
import datetime
import os.path
import pickle
import re
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import time
import threading
# --- [كود الطوارئ] مسح التوكن القديم إجبارياً ---
if os.path.exists('token.pickle'):
    os.remove('token.pickle')
# --- إعدادات عامة (Constants) ---
SCOPES = ['https://www.googleapis.com/auth/calendar']
REDIRECT_URI = "https://batu-lms-tracker.streamlit.app" # تأكد إن الرابط ده مطابق للي في جوجل كونسول
MY_PORTFOLIO_URL = "https://www.linkedin.com/in/omar-mehawed-861098249/" # حط لينكك هنا
SESSIONS_FILE = "active_sessions.json"

# --- دوال إدارة الجلسات (Memory) ---
def load_sessions():
    if not os.path.exists(SESSIONS_FILE): return {}
    try:
        with open(SESSIONS_FILE, "r") as f: return json.load(f)
    except: return {}

def save_session(username, status_data):
    sessions = load_sessions()
    sessions[username] = status_data
    with open(SESSIONS_FILE, "w") as f: json.dump(sessions, f)

def remove_session(username):
    sessions = load_sessions()
    if username in sessions:
        del sessions[username]
        with open(SESSIONS_FILE, "w") as f: json.dump(sessions, f)

def is_user_active(username):
    sessions = load_sessions()
    return username in sessions

# --- دوال جوجل (Server Compatible) ---
def get_calendar_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # --- هنا التعديل والحل ---
            # 1. بنثبت الرابط الأساسي (من غير شرطة في الآخر)
            redirect_uri = "https://batu-lms-tracker.streamlit.app"
            
            # 2. (للتجربة) بنطبع الرابط عشان نتأكد
            st.error(f"⚠️ الرابط المرسل لجوجل هو: {redirect_uri}")
            st.info("تأكد أن هذا الرابط موجود تماماً في Google Console")

            flow = Flow.from_client_secrets_file(
                'credentials.json',
                scopes=SCOPES,
                redirect_uri=redirect_uri
            )

            auth_code = st.query_params.get("code")

            if not auth_code:
                auth_url, _ = flow.authorization_url(prompt='consent')
                st.markdown(f"""
                    <a href="{auth_url}" target="_self" style="
                        background-color: #4285F4; color: white; padding: 10px 20px; 
                        text-decoration: none; border-radius: 5px; font-weight: bold;
                        display: block; text-align: center; margin: 20px 0;">
                        👉 اضغط هنا لربط حساب جوجل
                    </a>
                    """, unsafe_allow_html=True)
                st.warning("يجب ربط حساب جوجل أولاً للمتابعة.")
                st.stop()
            else:
                flow.fetch_token(code=auth_code)
                creds = flow.credentials
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)
                st.query_params.clear()
                st.rerun()

    return build('calendar', 'v3', credentials=creds)

# --- دوال المعالجة والتحليل ---
def extract_date_regex(text):
    if not text: return None
    match = re.search(r'\d{4}-\d{2}-\d{2}', text)
    if match: return match.group(0)
    return None

def add_event_to_calendar(service, full_title, release_date, deadline_date, link):
    try:
        if not release_date or not deadline_date: return False, "تاريخ غير صالح"
        
        events_result = service.events().list(
            calendarId='primary', 
            timeMin=f"{release_date}T00:00:00Z", 
            timeMax=f"{release_date}T23:59:59Z", 
            singleEvents=True, q=full_title
        ).execute()
        
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

# --- دالة السكرابينج (Scraping) ---
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

# --- وظيفة المراقبة في الخلفية ---
def run_background_monitor(user, pw, interval_minutes):
    try:
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
            srv = build('calendar', 'v3', credentials=creds)
            
            while True:
                if not is_user_active(user): break
                try:
                    logs, data = check_lms_assignments(user, pw)
                    if data:
                        for d in data:
                            add_event_to_calendar(srv, d['title'], d['release_date'], d['deadline_date'], d['link'])
                except: pass
                time.sleep(interval_minutes * 60)
    except: pass

# --- واجهة المستخدم (UI) ---
st.set_page_config(page_title="BATU LMS", page_icon="🎓", layout="centered")

st.markdown("""
<style>
    [data-testid="stImage"] {display: flex; justify-content: center; align-items: center;}
    [data-testid="stImage"] img {max-width: 100%; height: auto;}
    .footer {position: fixed; left: 0; bottom: 0; width: 100%; background-color: #0e1117; color: white; text-align: center; padding: 10px; z-index: 999; font-size: 14px; border-top: 1px solid #333;}
    .footer a {color: #4ea4f9; text-decoration: none;}
    @media (max-width: 768px) {
        [data-testid="stImage"] img {max-width: 80px !important; height: auto !important; margin-bottom: 10px;}
        h1 { font-size: 1.4rem !important; }
        .block-container { padding-top: 1rem !important; padding-bottom: 4rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# Header
col1, col2, col3 = st.columns([1, 3, 1])
with col1:
    if os.path.exists("uni_logo.png"): st.image("uni_logo.png", use_container_width=True)
with col3:
    if os.path.exists("it_logo.png"): st.image("it_logo.png", use_container_width=True)
with col2:
    st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>BATU Notification LMS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray; margin-top: 0;'>نظام إشعارات تلقائي للجامعة</p>", unsafe_allow_html=True)

# Tabs
tab_live, tab_manual, tab_clean = st.tabs(["🔴 Live Tracker", "🔄 Insert Past", "🗑️ Clean"])

# Tab 1: Live Tracker
with tab_live:
    st.info("أدخل بياناتك لمرة واحدة، وسيقوم النظام بالمتابعة تلقائياً.")
    col_a, col_b = st.columns(2)
    with col_a: live_user = st.text_input("Username", placeholder="2xxxxx@batechu.com", key="live_u")
    with col_b: live_pass = st.text_input("Password", type="password", key="live_p")
    
    refresh_rate = st.slider("افحص الموقع كل (دقائق):", 10, 180, 60)

    if live_user:
        if is_user_active(live_user):
            sessions = load_sessions()
            start_time = sessions.get(live_user, {}).get("start_time", "Unknown")
            st.success(f"✅ يا هندسة، المراقبة شغالة ليك من الساعة: {start_time}")
            if st.button(f"🛑 إلغاء المراقبة"):
                remove_session(live_user)
                st.warning("تم الإلغاء.")
                time.sleep(1)
                st.rerun()
        else:
            if st.button("ابدأ المراقبة الآن 🚀"):
                if live_user and live_pass:
                    try:
                        # التأكد من الاتصال بجوجل أولاً
                        srv = get_calendar_service()
                        now_str = datetime.datetime.now().strftime("%I:%M %p")
                        save_session(live_user, {"start_time": now_str})
                        t = threading.Thread(target=run_background_monitor, args=(live_user, live_pass, refresh_rate))
                        t.daemon = True 
                        t.start()
                        st.toast(f"تم التفعيل لـ {live_user}!", icon="📡")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"خطأ في الاتصال: {e}")
                else: st.error("دخل الباسورد!")
    else:
        st.caption("👈 اكتب اليوزر عشان نشوف حالتك.")

# Tab 2: Manual Check
with tab_manual:
    with st.form("sync_manual"):
        m_user = st.text_input("Username",placeholder="2xxxxx@batechu.com")
        m_pw = st.text_input("Password", type="password")
        m_sub = st.form_submit_button("Insert Past Assignments")
    if m_sub and m_user and m_pw:
        with st.status("Working...", expanded=True):
            logs, data = check_lms_assignments(m_user, m_pw)
            for l in logs: 
                if "❌" in l or "🚫" in l: st.error(l)
                else: st.text(l)
            if data:
                try:
                    srv = get_calendar_service()
                    for d in data:
                        s, m = add_event_to_calendar(srv, d['title'], d['release_date'], d['deadline_date'], d['link'])
                        if s: st.success(f"✅ {d['title']}")
                        else: st.error(f"❌ {d['title']} -> {m}")
                except: st.error("جوجل مش متصل")
            else: st.warning("No data.")

# Tab 3: Clean
with tab_clean:
    if st.button("Clean All Events"):
        try:
            srv = get_calendar_service()
            c, m = delete_old_events(srv)
            st.success(m)
        except Exception as e:
            st.error(f"حدث خطأ: {e}")

# Footer
st.markdown(f"""<div class="footer">Developed with ❤️ by <a href="{MY_PORTFOLIO_URL}" target="_blank">Omar Mehawed</a></div>""", unsafe_allow_html=True)


