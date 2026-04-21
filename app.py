import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="BRN Depo Yönetimi", layout="centered", page_icon="📦")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton {display: none !important;}
    .block-container { padding: 0.5rem 0.5rem !important; }
    input { font-size: 16px !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 5px; }
    .stTabs [data-baseweb="tab"] { padding: 10px; font-size: 14px; }
    div[data-testid="stHorizontalBlock"]:first-of-type {
        flex-wrap: nowrap !important;
        align-items: center !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. GÜVENLİK ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h3 style='text-align:center;'>🛡️ BRN Güvenli Erişim</h3>", unsafe_allow_html=True)
    with st.form("Giriş"):
        u_raw = st.text_input("Kullanıcı:")
        p_raw = st.text_input("Parola:", type="password")
        if st.form_submit_button("SİSTEME GİRİŞ YAP", use_container_width=True):
            try:
                users = st.secrets["users"]
                u_lower = u_raw.strip().lower()
                if u_lower in users and str(users[u_lower]) == p_raw.strip():
                    st.session_state.logged_in = True
                    st.session_state.user = u_lower
                    st.rerun()
                else: st.error("Hatalı Giriş Bilgisi!")
            except: st.error("Secrets ayarları eksik!")
    st.stop()

# --- 3. BAĞLANTI ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- 4. AKILLI KATALOG FONKSİYONLARI ---
@st.cache_data(ttl=60)
def urun_katalogu_getir():
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Stok", ttl=0)
        if not df.empty:
            df['Kod'] = df['Kod'].fillna("KODSUZ").astype(str)
            df['İsim'] = df['İsim'].fillna("İSİMSİZ").astype(str)
            df['Arama'] = df['Kod'] + " | " + df['İsim']
            return ["+ YENİ / MANUEL GİRİŞ"] + sorted(df['Arama'].unique
