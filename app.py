import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title=" Bilal BRN Depo", layout="centered", page_icon="📦")

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
    st.markdown("<h3 style='text-align:center;'>🛡️ Bilal BRN Depo Girşi</h3>", unsafe_allow_html=True)
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
                else: st.error("Hatalı Giriş!")
            except: st.error("Secrets bulunamadı!")
    st.stop()

# --- 3. BAĞLANTI ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- 4. AKILLI KATALOG VE ENVANTER FONKSİYONLARI ---
@st.cache_data(ttl=60)
def urun_katalogu_getir():
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Stok", ttl=0)
        if not df.empty:
            # Kod ve İsimdeki boşlukları (NaN) temizleyip birleştiriyoruz
            df['Kod'] = df['Kod'].fillna("KODSUZ").astype(str)
            df['İsim'] = df['İsim'].fillna("İSİMSİZ").astype(str)
            df['Arama'] = df['Kod'] + " | " + df['İsim']
            return ["+ YENİ / MANUEL GİRİŞ"] + sorted(df['Arama'].unique().tolist())
        return ["+ YENİ / MANUEL GİRİŞ"]
    except:
        return ["+ YENİ / MANUEL GİRİŞ"]

def update_stock_record(kod, isim, adres, birim, miktar, is_increase=True):
    try:
        stok_df = conn.read(spreadsheet=SHEET_URL, worksheet="Stok", ttl=0)
    except:
        stok_df = pd.DataFrame(columns=['Adres', 'Kod', 'İsim', 'Birim', 'Miktar'])
    
    miktar = float(miktar)
    if not stok_df.empty:
        stok_df['Miktar'] = pd.to_numeric(stok_df['Miktar'], errors='coerce').fillna(0)
        mask = (stok_df['Kod'] == kod) & (stok_df['Adres'] == adres) & (stok_df['Birim'] == birim)
        if mask.any():
            if is_increase: stok_df.loc[mask, 'Miktar'] += miktar
            else: stok_df.loc[mask, 'Miktar'] -= miktar
        else:
            if is_increase:
                new_row = pd.DataFrame([{"Adres": adres, "Kod": kod, "İsim": isim, "Birim": birim, "Miktar": miktar}])
                stok_df = pd.concat([stok_df, new_row], ignore_index=True)
    else:
        if is_increase:
            stok_df = pd.DataFrame([{"Adres": adres, "Kod": kod, "İsim": isim, "Birim": birim, "Miktar": miktar}])
    
    stok_df = stok_df[stok_df['Miktar'] > 0]
    conn.update(spreadsheet=SHEET_URL, worksheet="Stok", data=stok_df)

# --- 5. HEADER ---
h1, h2, h3 = st.columns([0.8, 2, 0.8], vertical_alignment="center")
with h1: st.image("brn_logo.webp", width=55)
with h2: st.markdown(f"**👤 {st.session_state.user.upper()}**")
with h3: 
    if st.button("Çık"):
        st.session_state.logged_in = False
        st.rerun()

st.divider()

# --- 6. MODÜLLER ---
t1, t2, t3 = st.tabs(["📥 İşlem", "🔄 Transfer", "📊 Stok"])
arama_listesi = urun_katalogu_getir()

with t1:
    with st.container(border=True):
        is_type = st.selectbox("İşlem:", ["GİRİŞ", "ÇIKIŞ"])
        adr = st.text_input("Adres:", value="GENEL", key="a1").strip().upper()
        
        secim = st.selectbox("🔍 Kayıtlı Ürün Ara (Ad veya Kod):", arama_listesi, key="sec1")
        
        if secim == "+ ÜRÜN ADI ARA":
            kod = st.text_input("Kod:", key="

                                # --- İMZA SATIRI ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align: center; color: #888888; font-size: 12px; padding-top: 10px; border-top: 1px solid #e0e0e0;'>"
    "<b>BRN SLEEP PRODUCTS</b><br>BİLAL KEMERTAŞ"
    "</div>", 
    unsafe_allow_html=True
)
