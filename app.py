# import streamlit as st

# # --- إعدادات الصفحة ---
# st.set_page_config(page_title="Maintenance | BATU LMS", page_icon="🚧", layout="centered")

# # --- إخفاء عناصر التحكم ---
# st.markdown("""
# <style>
#     #MainMenu {visibility: hidden;}
#     footer {visibility: hidden;}
#     header {visibility: hidden;}
#     .stAppDeployButton {display: none !important;}
#     [data-testid="stToolbar"] {display: none !important;}
# </style>
# """, unsafe_allow_html=True)

# # --- رسالة الصيانة ---
# st.warning("⚠️ تنبيه هام")
# st.title("🚧 الموقع تحت الصيانة")
# st.markdown("""
# ### عذراً يا شباب، الخدمة متوقفة مؤقتاً 🛑

#  .(LMS) تم إيقاف البوت مؤقتاً لمنع حدوث أخطاء في.


# **شكراً لتفهمكم ❤️**
# """)

# # --- الفوتر ---
# st.markdown(f"""
# <div style="position: fixed; left: 0; bottom: 0; width: 100%; background-color: #0e1117; color: white; text-align: center; padding: 10px; border-top: 1px solid #333;">
#     Developed with ❤️ by Omar Mehawed
# </div>
# """, unsafe_allow_html=True)
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
import json
from google.oauth2.credentials import Credentials
from maintenance import show_maintenance_mode  # استدعاء ملف الصيانة
# --- إخفاء علامة GitHub والفوتر والقائمة ---
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stAppDeployButton {display:none;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
# --- إعدادات عامة (Constants) ---
SCOPES = ['https://www.googleapis.com/auth/calendar']
REDIRECT_URI = "https://batu-lms-tracker.streamlit.app" # تأكد إن الرابط ده مطابق للي في جوجل كونسول
MY_PORTFOLIO_URL = "https://www.linkedin.com/in/omar-mehawed-861098249/" # حط لينكك هنا
SESSIONS_FILE = "active_sessions.json"
TOKENS_DB = "user_tokens.json"
# 🔴 1. تعديل الأدمن (ضفت إيميل الجيميل بتاعك)
ADMIN_USERS = ["2420823@batechu.com", "omarmehawed4@gmail.com"]

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
    # --- دوال قاعدة البيانات (DB Functions) ---
def load_tokens_db():
    if not os.path.exists(TOKENS_DB): return {}
    try:
        with open(TOKENS_DB, "r") as f: return json.load(f)
    except: return {}

def save_token_to_db(username, creds):
    db = load_tokens_db()
    db[username] = json.loads(creds.to_json())
    with open(TOKENS_DB, "w") as f:
        json.dump(db, f)

def get_token_from_db(username):
    db = load_tokens_db()
    if username in db:
        info = db[username]
        try:
            # بنحاول نقرا التوكن
            return Credentials.from_authorized_user_info(info, SCOPES)
        except ValueError:
            # لو بايظ (زي حالتك دلوقتي) امسحه عشان ميعملش Error
            delete_token_from_db(username)
            return None
    return None

def delete_token_from_db(username):
    db = load_tokens_db()
    if username in db:
        del db[username]
        with open(TOKENS_DB, "w") as f:
            json.dump(db, f)

# --- دوال جوجل (Server Compatible) ---
# --- التعديل النهائي (Clean Version without Debug) ---
# --- التعديل الجديد: الاعتماد على session_state بدلاً من الملفات ---
def get_calendar_service(username_key=None):
    creds = None
    # 1. لو معانا اسم مستخدم، ندور في الداتا بيز الأول
    if username_key:
        creds = get_token_from_db(username_key)

    # 2. التحقق والتجديد
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                if username_key: save_token_to_db(username_key, creds)
            except:
                creds = None 

        # 3. لو مفيش توكن، نطلب إذن جديد
        if not creds:
            flow = Flow.from_client_secrets_file(
                'credentials.json',
                scopes=SCOPES,
                redirect_uri=REDIRECT_URI
            )

            auth_code = st.query_params.get("code")

            if not auth_code:
                # هنا التعديل: شيلنا prompt='consent' عشان ميسألكش كل مرة
                auth_url, _ = flow.authorization_url(access_type='offline', prompt='consent')
                # كود أيقونة جوجل (Base64) عشان تظهر علطول ومتقطعش
                # رابط صورة الزرار
                google_btn_img = "https://raw.githubusercontent.com/omarmehawed/BATU-LMS-Tracker/main/google_logo.png"
                
                # --- كود HTML المصحح ---
                st.markdown(f"""
                    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin-top: 20px;">
                        <p style="color: #ccc; font-size: 14px; margin-bottom: 15px;">اضغط أدناه لربط التقويم</p>
                        <a href="{auth_url}" target="_blank">
                            <img src="{google_btn_img}" style="width: 200px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: transform 0.2s; cursor: pointer;">
                        </a>
                        <p style="color: #666; font-size: 11px; margin-top: 15px;">(سيفتح نافذة جديدة)</p>
                    </div>
                    """, unsafe_allow_html=True)
                st.stop()
            else:
                try:
                    flow.fetch_token(code=auth_code)
                    creds = flow.credentials
                    
                    if username_key:
                        save_token_to_db(username_key, creds)
                        st.toast(f"تم ربط حساب جوجل بنجاح لـ {username_key}!", icon="✅")
                    
                    st.query_params.clear()
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"خطأ في المصادقة: {e}")
                    st.stop()

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

# --- دالة الحذف المحسنة (مع شريط التقدم) ---
# --- دالة الحذف المحسنة (تعد الواجبات الأصلية فقط) ---
def delete_old_events(service):
    try:
        unique_assignments = set() # قائمة لتخزين أسماء الواجبات الفريدة
        page_token = None
        
        status_text = st.empty()
        progress_bar = st.progress(0, text="جاري البحث...")

        # 1. تجميع كل الايفنتات الأول
        all_events = []
        while True:
            events_result = service.events().list(
                calendarId='primary',
                q='BATU Bot', 
                singleEvents=True, # لازم دي عشان يجيب كل التكرارات ويمسحها
                pageToken=page_token
            ).execute()

            batch = events_result.get('items', [])
            all_events.extend(batch)
            
            page_token = events_result.get('nextPageToken')
            if not page_token: break
        
        if not all_events:
            progress_bar.empty()
            return 0, "الكاليندر نظيفة تماماً! ✨"

        # 2. الحذف والعد الذكي
        total_items = len(all_events)
        
        for i, event in enumerate(all_events):
            try:
                # الحذف الفعلي
                service.events().delete(calendarId='primary', eventId=event['id']).execute()
                
                # --- هنا التعديل: بناخد الاسم عشان نعده مرة واحدة بس ---
                # اسم الايفنت بيكون: "📘 Course : Assignment Name"
                # هناخد الاسم كامل كبصمة
                assignment_title = event.get('summary', 'Unknown')
                unique_assignments.add(assignment_title)
                
                # تحديث الشريط
                prog = int(((i + 1) / total_items) * 100)
                status_text.info(f"جاري تنظيف: {assignment_title}...")
                progress_bar.progress(prog, text=f"تم مسح {len(unique_assignments)} واجب أساسي...")
                
            except:
                pass

        status_text.empty()
        progress_bar.empty()
        
        # الرقم النهائي هو عدد الأسماء الفريدة في القائمة
        real_count = len(unique_assignments)
        
        return real_count, f"تم تنظيف الكاليندر! حذفتلك {real_count} واجب (بكل أيام تكرارهم) بنجاح 🧹"

    except Exception as e:
        return -1, f"حدث خطأ في الاتصال: {str(e)}"

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
        # بنجيب التوكن الخاص باليوزر ده من الداتا بيز
        creds = get_token_from_db(user)
        if creds:
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
    
# --- وظيفة الإنذار (Alarm) لكل الأدمنز ---
def send_admin_alarm(error_msg):
    # نلف على كل الأدمنز ونبعت
    for admin in ADMIN_USERS:
        try:
            creds = get_token_from_db(admin)
            if not creds: continue # لو مش رابط، عدي

            service = build('calendar', 'v3', credentials=creds)
            
            now = datetime.datetime.now()
            end = now + datetime.timedelta(minutes=10)
            
            event = {
                'summary': '🚨🚨 الموقع وقع!! 🚨🚨',
                'location': 'BATU Server',
                'description': f'رسالة الخطأ:\n{error_msg}\n\nادخل اعمل ريستارت بسرعة!',
                'start': {'dateTime': now.isoformat(), 'timeZone': 'Africa/Cairo'},
                'end': {'dateTime': end.isoformat(), 'timeZone': 'Africa/Cairo'},
                'colorId': '11', # لون أحمر للطوارئ
                'reminders': {'useDefault': False, 'overrides': [{'method': 'popup', 'minutes': 0}]},
            }
            service.events().insert(calendarId='primary', body=event).execute()
        except: pass
        
# --- واجهة المستخدم (UI) ---
st.set_page_config(page_title="BATU-NOTIF-LMS", page_icon="logo.png", layout="centered")

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
# 1. Live Tracker
with tab_live:
    st.info("أدخل بياناتك لمرة واحدة، وسيقوم النظام بالمتابعة تلقائياً.")
    col_a, col_b = st.columns(2)
    with col_a: live_user = st.text_input("Username", placeholder="24xxxx@batechu.com", key="live_u")
    with col_b: live_pass = st.text_input("Password", type="password", key="live_p")
    
    refresh_rate = st.slider("افحص الموقع كل (دقائق):", 60, 180, 60, step=60)
    
    if live_user:
        # هل اليوزر ده ليه توكن متخزن؟
        has_token = get_token_from_db(live_user) is not None
        # هل اليوزر ده مشغل مراقبة؟
        is_running = is_user_active(live_user)

        if has_token:
            st.success(f"✅ الحساب ({live_user}) مربوط بجوجل وجاهز.")
            # ضفنا key هنا
            if st.button("🔄 فك الارتباط (Re-link Google)", key="relink_btn_unique"):
                delete_token_from_db(live_user)
                st.rerun()
        else:
            st.info("ℹ️ هذا الحساب غير مربوط بجوجل. سيتم طلب الربط عند البدء.")

        if is_running:
            sessions = load_sessions()
            start_time = sessions.get(live_user, {}).get("start_time", "Unknown")
            st.warning(f"📡 المراقبة تعمل حالياً منذ: {start_time}")
            # ضفنا key هنا
            if st.button(f"🛑 إيقاف المراقبة", key="stop_btn_unique"):
                remove_session(live_user)
                st.rerun()
        else:
            # ضفنا key هنا (وده اللي كان مطلع الايرور عندك)
            if st.button("ابدأ المراقبة الآن 🚀", key="start_btn_unique"):
                if live_user and live_pass:
                    try:
                        # هنا بنبعت اليوزر عشان الدالة تدور على التوكن بتاعه أو تنشئه
                        srv = get_calendar_service(username_key=live_user)
                        
                        now_str = datetime.datetime.now().strftime("%I:%M %p")
                        save_session(live_user, {"start_time": now_str})
                        t = threading.Thread(target=run_background_monitor, args=(live_user, live_pass, refresh_rate))
                        t.daemon = True 
                        t.start()
                        st.toast(f"تم التفعيل لـ {live_user}!", icon="📡")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"خطأ: {e}")
                else: st.error("دخل الباسورد!")
    else:
        st.caption("👈 اكتب اليوزر عشان نشوف حالتك.")

# 2. Manual Check (تعديل: إضافة حالة الربط)
with tab_manual:
    st.info("هنا يمكنك جلب الواجبات القديمة يدوياً.")
    
    # 1. الخانات (خليناها بره الفورم عشان تظهر الحالة فوراً)
    col_m1, col_m2 = st.columns(2)
    with col_m1: 
        m_user = st.text_input("Username", placeholder="2xxxxx@batechu.com", key="manual_u")
    with col_m2: 
        m_pw = st.text_input("Password", type="password", key="manual_p")

    # 2. (الجزء الجديد) إظهار حالة الربط زي التبويب الأول بالظبط
    if m_user:
        # هل اليوزر ده ليه توكن في الداتا بيز؟
        if get_token_from_db(m_user):
             st.success(f"✅ الحساب ({m_user}) مربوط بجوجل وجاهز.")
             # زرار فك الربط لو حبيت تضيفه هنا كمان (اختياري)
             # if st.button("فك الارتباط", key="unlink_manual"):
             #    delete_token_from_db(m_user)
             #    st.rerun()
        else:
             st.warning("⚠️ هذا الحساب غير مربوط بجوجل.")

    # 3. زرار التشغيل
    if st.button("Insert Past Assignments", key="manual_btn"):
        if m_user and m_pw:
            with st.status("Working...", expanded=True):
                logs, data = check_lms_assignments(m_user, m_pw)
                for l in logs: 
                    if "❌" in l or "🚫" in l: st.error(l)
                    else: st.text(l)
                
                if data:
                    try:
                        # بنبعت اليوزر عشان يجيب التوكن
                        srv = get_calendar_service(username_key=m_user)
                        count = 0
                        for d in data:
                            s, m = add_event_to_calendar(srv, d['title'], d['release_date'], d['deadline_date'], d['link'])
                            if s: 
                                st.success(f"✅ {d['title']}")
                                count += 1
                            else: st.error(f"❌ {d['title']} -> {m}")
                        
                        if count > 0: st.balloons()
                    except Exception as e:
                        st.error(f"حدث خطأ (تأكد من الربط): {e}")
                else:
                    st.warning("No data found.")
        else:
            st.error("اكتب البيانات الأول!")

# 3. Clean Tab (الواجهة)
with tab_clean:
    c_user = st.text_input("Username للتنظيف", placeholder="2xxxxx@batechu.com")
    
    if st.button("Clean All Events", key="clean_btn"):
        if c_user:
            try:
                # لازم نبعت اليوزر عشان يجيب التوكن بتاعه ويمسح من الكاليندر بتاعته هو
                srv = get_calendar_service(username_key=c_user)
                
                c, m = delete_old_events(srv)
                
                if c > 0:
                    st.success(m)
                    st.balloons()
                elif c == 0:
                    st.info(m)
                else:
                    st.error(m)
            except Exception as e:
                st.error(f"حدث خطأ: {e}")
        else:
            st.error("اكتب اليوزر الأول عشان أعرف أمسح من عند مين!")

# --- إعدادات الفوتر ومعلومات التواصل ---
# 1. حط رقمك هنا (كود الدولة 20 + رقمك من غير صفر في الأول)
MY_WHATSAPP = "+201009489979"  # <--- امسح x واكتب رقمك الحقيقي هنا

# 2. الفوتر الجديد
st.markdown(f"""
<div class="footer">
    <p style="margin: 0; padding: 0;">Developed with ❤️ by <a href="{MY_PORTFOLIO_URL}" target="_blank">Omar Mehawed</a></p>
    <p style="margin: 5px 0 0 0; font-size: 12px;">
        Need Help? 
        <a href="https://wa.me/{MY_WHATSAPP}" target="_blank" style="color: #25D366; font-weight: bold; text-decoration: none;">
             Contact Me on WhatsApp 💬
        </a>
    </p>
</div>
""", unsafe_allow_html=True)


#________________________________________________________________________________________________________________________________________________
# ... (آخر حتة في الملف)
except Exception as e:
    # نبعتلك إنذار الأول
    send_admin_alarm(str(e))
    # وبعدين نستدعي صفحة الصيانة
    show_maintenance_mode()

