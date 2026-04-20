import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components

# --- 1. SAYFA AYARLARI VE GİZLEME ---
st.set_page_config(page_title="BRN X-Ray Pro", layout="centered", page_icon="📦")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton {display: none !important; visibility: hidden !important;}
    [data-testid="stStatusWidget"], [data-testid="stToolbar"], [data-testid="stDecoration"] {display: none !important;}
    .block-container { padding: 0.5rem 0.5rem !important; max-width: 100% !important; }
    input { font-size: 16px !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] { padding: 8px 12px; font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

components.html(
    """<script>
    const cleanUI = () => {
        const selectors = ['div[class*="viewerBadge"]', 'button[title*="Manage app"]', 'header', 'footer'];
        selectors.forEach(s => {
            try { window.parent.document.querySelectorAll(s).forEach(el => el.remove()); } catch (e) {}
        });
    };
    setInterval(cleanUI, 300);
    </script>""", height=0
)

# --- 2. GÜVENLİK VE GİRİŞ ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h3 style='text-align:center;'>🛡️ BRN Güvenli Erişim</h3>", unsafe_allow_html=True)
    with st.form("Giriş"):
        u_raw = st.text_input("Kullanıcı:")
        p_raw = st.text_input("Parola:", type="password")
        if st.form_submit_button("SİSTEME GİRİŞ YAP", use_container_width=True):
            try:
                USERS = st.secrets["users"]
                u_in = u_raw.strip().lower()
                p_in = p_raw.strip()
                match = next((u for u in USERS if u.lower() == u_in), None)
                if match and str(USERS[match]) == p_in:
                    st.session_state.logged_in = True
                    st.session_state.user = match
                    st.rerun()
                else: st.error("Hatalı Giriş!")
            except: st.error("Secrets (Şifreler) yapılandırılmamış!")
    st.stop()

# --- 3. VERİ BAĞLANTISI ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 4. KOMPAKT HEADER (LOGO + İSİM + ÇIKIŞ) ---
h_col1, h_col2, h_col3 = st.columns([0.8, 2, 0.8], vertical_alignment="center")
with h_col1:
    st.image("brn_logo.webp", width=55)
with h_col2:
    st.markdown(f"<p style='margin:0; font-size:13px; font-weight:bold; color:gray;'>👤 {st.session_state.user.upper()}</p>", unsafe_allow_html=True)
with h_col3:
    if st.button("Çık", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

st.markdown("---")

# --- 5. ANA MENÜ (TABS) ---
t1, t2, t3 = st.tabs(["📥 İşlem", "🔄 Transfer", "📊 Stok"])

# --- KAYIT MODÜLÜ ---
with t1:
    with st.container(border=True):
        islem = st.selectbox("İşlem Tipi:", ["GİRİŞ", "ÇIKIŞ"])
        adres = st.text_input("Adres:", value="GENEL", key="adr1").strip().upper()
        barkod = st.text_input("Barkod Okut:", key="bk1").strip().upper()
        
        if st.button("KAYDI TAMAMLA", use_container_width=True, type="primary"):
            if barkod:
                yeni_veri = pd.DataFrame([{
                    "Tarih": datetime.now().strftime("%d.%m.%Y %H:%M"),
                    "İşlem": islem,
                    "Adres": adres,
                    "Barkod": barkod,
                    "Operatör": st.session_state.user
                }])
                mevcut = conn.read(worksheet="Sayfa1")
                guncel = pd.concat([mevcut, yeni_veri], ignore_index=True)
                conn.update(worksheet="Sayfa1", data=guncel)
                st.success(f"✅ {islem} Kaydedildi!")
            else: st.warning("Barkod boş olamaz!")

# --- TRANSFER MODÜLÜ (YENİDEN AKTİF) ---
with t2:
    with st.container(border=True):
        st.subheader("Ürün Transferi")
        yeni_adres = st.text_input("Yeni Adres (Hedef):", key="adr2").strip().upper()
        tr_barkod = st.text_input("Barkod Okut:", key="bk2").strip().upper()
        
        if st.button("TRANSFERİ GERÇEKLEŞTİR", use_container_width=True, type="primary"):
            if tr_barkod and yeni_adres:
                tr_veri = pd.DataFrame([{
                    "Tarih": datetime.now().strftime("%d.%m.%Y %H:%M"),
                    "İşlem": "TRANSFER",
                    "Adres": yeni_adres,
                    "Barkod": tr_barkod,
                    "Operatör": st.session_state.user
                }])
                mevcut = conn.read(worksheet="Sayfa1")
                guncel = pd.concat([mevcut, tr_veri], ignore_index=True)
                conn.update(worksheet="Sayfa1", data=guncel)
                st.success(f"📦 {tr_barkod} -> {yeni_adres} Adresine Taşındı!")
            else: st.error("Lütfen hem yeni adresi hem de barkodu girin!")

# --- STOK MODÜLÜ ---
with t3:
    if st.button("Güncel Stok Listesini Getir"):
        st.dataframe(conn.read(worksheet="Sayfa1").tail(15), use_container_width=True)
