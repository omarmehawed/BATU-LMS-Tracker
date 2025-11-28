import streamlit as st

def show_maintenance_mode():
    # 1. إخفاء عناصر التحكم
    st.markdown("""
    <style>
        div.stButton > button:first-child {display: none;}
        div[data-testid="stVerticalBlock"] > div {display: none;}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stAppDeployButton {display: none !important;}
        [data-testid="stToolbar"] {display: none !important;}
        [data-testid="stDecoration"] {display: none !important;}
        [data-testid="stStatusWidget"] {display: none !important;}
        div[class*="viewerBadge"] {display: none !important;}
    </style>
    """, unsafe_allow_html=True)

    # 2. رسالة الصيانة
    st.warning("⚠️ تنبيه هام")
    st.title("🚧 الموقع تحت الصيانة")
    st.markdown("""
    ### عذراً يا شباب، الخدمة متوقفة مؤقتاً 🛑

    نظراً لتوقف موقع الجامعة (LMS) حالياً، تم إيقاف البوت مؤقتاً لمنع حدوث أخطاء.
    سيتم إعادة التشغيل فور عودة النظام للعمل.
    """)
    
    # 3. الفوتر (عشان يفضل ظاهر)
    st.markdown(f"""
    <div style="position: fixed; left: 0; bottom: 0; width: 100%; background-color: #0e1117; color: white; text-align: center; padding: 10px; border-top: 1px solid #333; z-index: 99999;">
        Developed with ❤️ by Omar Mehawed
    </div>
    """, unsafe_allow_html=True)
    
    st.stop() # وقف باقي الكود
