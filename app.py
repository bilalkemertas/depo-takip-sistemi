import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="BRN Depo Pro", layout="centered", page_icon="📦")

# Sabit Link (Hata almamak için buraya ekledik)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1FkrwprfhJc0UlflZFWTskSyukHmBPW7yunPULN5pR8A/edit"

# Mobil Kompakt Görünüm CSS
st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton {display: none !important;}
    .block-container { padding: 0.5rem 0.5rem !important; }
    input { font-size: 16px !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 5px; }
    .stTabs [data-baseweb="tab"] { padding: 10px; font-size: 14px; }
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
                u_in = u_raw.strip().lower()
                p_in = p_raw.strip()
                if u_in in users and str(users[u_in]) == p_in:
                    st.session_state.logged_in = True
                    st.session_state.user = u_in
                    st.rerun()
                else: st.error("Hatalı Giriş Bilgisi!")
            except: st.error("Secrets bulunamadı!")
    st.stop()

# --- 3. BAĞLANTI ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 4. KOMPAKT HEADER (Logo, İsim, Çıkış Tek Satırda) ---
h1, h2, h3 = st.columns([0.8, 2, 0.8], vertical_alignment="center")
with h1:
    st.image("brn_logo.webp", width=55) # Logo isminin doğru olduğundan emin ol
with h2:
    st.markdown(f"<p style='margin:0; font-size:14px;'>👤 <b>{st.session_state.user.upper()}</b></p>", unsafe_allow_html=True)
with h3: 
    if st.button("Çık", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

st.markdown("---")

# --- 5. ANA MODÜLLER ---
t1, t2, t3 = st.tabs(["📥 İşlem", "🔄 Transfer", "📊 Stok"])

with t1:
    with st.container(border=True):
        islem = st.selectbox("İşlem:", ["GİRİŞ", "ÇIKIŞ"])
        adres = st.text_input("Adres:", value="GENEL", key="a1").strip().upper()
        barkod = st.text_input("Barkod Okut:", key="b1").strip().upper()
        if st.button("KAYDET", use_container_width=True, type="primary"):
            if barkod:
                df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1")
                yeni = pd.DataFrame([{"Tarih": datetime.now().strftime("%d.%m.%Y %H:%M"), "İşlem": islem, "Adres": adres, "Barkod": barkod, "Operatör": st.session_state.user}])
                conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([df, yeni]))
                st.success("Kaydedildi!")
            else: st.warning("Barkod okutun!")

with t2:
    with st.container(border=True):
        st.subheader("Transfer")
        y_adres = st.text_input("Hedef Adres:", key="a2").strip().upper()
        tr_barkod = st.text_input("Ürün Barkodu:", key="b2").strip().upper()
        if st.button("TRANSFERİ TAMAMLA", use_container_width=True, type="primary"):
            if tr_barkod and y_adres:
                df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1")
                yeni = pd.DataFrame([{"Tarih": datetime.now().strftime("%d.%m.%Y %H:%M"), "İşlem": "TRANSFER", "Adres": y_adres, "Barkod": tr_barkod, "Operatör": st.session_state.user}])
                conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([df, yeni]))
                st.success("Ürün taşındı!")
            else: st.error("Bilgileri doldurun!")

with t3:
    if st.button("Listeyi Güncelle"):
        st.dataframe(conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1").tail(15), use_container_width=True)
