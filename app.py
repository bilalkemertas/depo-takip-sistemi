import streamlit as st
import pd as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import os
import streamlit.components.v1 as components

# --- 1. RADİKAL ARAYÜZ TEMİZLİĞİ ---
st.set_page_config(page_title="BRN X-Ray Pro", layout="centered", page_icon="brn_logo.webp")

# CSS ile tüm görünür Streamlit elementlerini yok et
st.markdown("""
    <style>
    /* Streamlit Cloud Butonları ve Toolbar */
    #MainMenu, footer, header {display: none !important;}
    .stDeployButton {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    
    /* Manage App butonunun tüm varyasyonlarını hedefle */
    div[class*="viewerBadge"], 
    div[class*="StreamlitFrameBadge"], 
    button[title*="Manage app"],
    div[data-testid="stConnectionStatus"] {
        display: none !important;
        visibility: hidden !important;
        height: 0px !important;
        width: 0px !important;
    }

    /* El terminali için tam ekran ve input optimizasyonu */
    .block-container { padding: 0.5rem 1rem !important; max-width: 100% !important; }
    input { font-size: 16px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. JAVASCRIPT İLE KOD VE BUTON KORUMASI ---
# Bu script sağ tıkı engeller, F12'yi zorlaştırır ve Manage App butonunu sürekli siler
components.html(
    """
    <script>
    // 1. Sağ tıkı engelle (Kodun kopyalanmasını zorlaştırır)
    window.parent.document.addEventListener('contextmenu', e => e.preventDefault());
    
    // 2. Manage App ve Frame Badge'i sürekli silen fonksiyon
    const killManageButton = () => {
        const selectors = [
            'div[class*="viewerBadge"]', 
            'button[title*="Manage app"]', 
            'header', 
            'footer',
            '.stAppDeployButton'
        ];
        selectors.forEach(s => {
            const el = window.parent.document.querySelector(s);
            if (el) el.remove();
        });
    };
    
    // Her 200ms'de bir kontrol et (Streamlit yeniden çizse bile siler)
    setInterval(killManageButton, 200);
    </script>
    """,
    height=0,
)

# --- 3. GÜVENLİ GİRİŞ (HARF DUYARSIZ) ---
try:
    USERS = st.secrets["users"]
except:
    USERS = {"admin": "1234"}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h3 style='text-align:center;'>🔒 Güvenli Erişim</h3>", unsafe_allow_html=True)
    with st.form("Login"):
        u_in = st.text_input("Kullanıcı:")
        p_in = st.text_input("Parola:", type="password")
        if st.form_submit_button("Sisteme Giriş", use_container_width=True):
            # Kullanıcı adında büyük-küçük harf ayrımı yok
            matching_user = next((u for u in USERS if u.lower() == u_in.lower()), None)
            if matching_user and str(USERS[matching_user]) == p_in:
                st.session_state.logged_in = True
                st.session_state.user = matching_user
                st.rerun()
            else: st.error("Bilgiler hatalı!")
    st.stop()

# --- 4. VERİ VE ANA UYGULAMA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(ws):
    st.cache_data.clear()
    try:
        df = conn.read(ttl=0, worksheet=ws)
        df.columns = df.columns.str.strip()
        return df
    except: return pd.DataFrame()

df_u = get_data("Urun_Listesi")
df_h = get_data("Sayfa1")

# Arayüz Üst Bölüm
c1, c2 = st.columns([1, 4])
with c1: st.write("👤")
with c2: st.write(f"**Hoş geldin, {st.session_state.user.upper()}**")

st.markdown("<hr style='margin:10px 0'>", unsafe_allow_html=True)

# Sekmeler ve İşlemler
t1, t2, t3 = st.tabs(["📦 İşlem", "🔄 Transfer", "📊 Rapor"])

with t1:
    col_a, col_b = st.columns(2)
    tip = col_a.selectbox("Tip:", ["GİRİŞ", "ÇIKIŞ"])
    adr = col_b.text_input("Adres:", "GENEL")
    kod = st.text_input("Barkod Okut:", key="scan_main")
    
    if kod:
        match = df_u[df_u['Malzeme Kodu'].astype(str).str.upper() == str(kod).upper()]
        if not match.empty:
            ad, brm = match.iloc[0]['Malzeme Adı'], match.iloc[0]['Birim']
            st.info(f"**Ürün:** {ad} ({brm})")
            mik = st.number_input("Miktar:", min_value=0.0, step=1.0)
            if st.button("KAYDET", use_container_width=True):
                yeni = pd.DataFrame({
                    "Tarih": [datetime.now().strftime("%Y-%m-%d %H:%M")],
                    "İşlem": [tip], "Adres": [adr.upper()], 
                    "Malzeme Kodu": [kod.upper()], "Malzeme Adı": [ad.upper()],
                    "Birim": [str(brm).upper()], "Miktar": [mik], 
                    "Kullanıcı": [st.session_state.user.upper()]
                })
                conn.update(data=pd.concat([df_h, yeni], ignore_index=True), worksheet="Sayfa1")
                st.toast("İşlem Başarılı!"); st.rerun()
        else: st.warning("Bu kod ürün listesinde yok!")

with t3:
    if st.button("🔄 Güncelle"): st.rerun()
    # NaN temizliği yapılmış rapor
    if not df_h.empty:
        df_clean = df_h.copy()
        df_clean['Birim'] = df_clean['Birim'].fillna('-')
        df_clean['Miktar'] = pd.to_numeric(df_clean['Miktar'], errors='coerce').fillna(0)
        df_clean['Net'] = df_clean.apply(lambda r: r['Miktar'] if r['İşlem'] == 'GİRİŞ' else -r['Miktar'], axis=1)
        
        ozet = df_clean.groupby(['Adres', 'Malzeme Kodu', 'Malzeme Adı', 'Birim'])['Net'].sum().reset_index()
        ozet = ozet[ozet['Net'] > 0]
        st.dataframe(ozet, hide_index=True, use_container_width=True)

st.markdown("<p style='text-align:center; font-size:9px; color:silver;'>v10.2 Secure Edition</p>", unsafe_allow_html=True)
