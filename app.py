import streamlit as st
import pandas as pd  # <-- Hata burada düzeltildi!
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import os
import streamlit.components.v1 as components

# --- 1. MODER TASARIM VE GİZLEME ---
st.set_page_config(page_title="Bilal BRN Depo", layout="centered", page_icon="brn_logo.webp")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton {display: none !important; visibility: hidden !important;}
    [data-testid="stStatusWidget"], [data-testid="stToolbar"], [data-testid="stDecoration"] {display: none !important;}
    div[class*="viewerBadge"], div[class*="StreamlitFrameBadge"], button[title*="Manage"] {
        display: none !important; height: 0px !important; width: 0px !important;
    }
    .block-container { padding: 0.5rem 1rem !important; max-width: 100% !important; }
    input { font-size: 16px !important; }
    </style>
""", unsafe_allow_html=True)

# Manage App Butonunu JavaScript ile imha et
components.html(
    """
    <script>
    const cleanSystemUI = () => {
        const selectors = ['div[class*="viewerBadge"]', 'button[title*="Manage app"]', 'header', 'footer', '.stAppDeployButton'];
        selectors.forEach(selector => {
            try { window.parent.document.querySelectorAll(selector).forEach(el => el.remove()); } catch (e) {}
        });
    };
    setInterval(cleanSystemUI, 300);
    </script>
    """,
    height=0,
)

# --- 2. GÜVENLİK (HARF DUYARSIZ KULLANICI ADI) ---
try:
    USERS = st.secrets["users"]
except Exception:
    USERS = {"admin": "1234"}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h3 style='text-align:center;'>🔒 Güvenli Erişim</h3>", unsafe_allow_html=True)
    with st.form("Giriş"):
        u_in = st.text_input("Kullanıcı:")
        p_in = st.text_input("Parola:", type="password")
        if st.form_submit_button("GİRİŞ", use_container_width=True):
            matching_user = next((u for u in USERS if u.lower() == u_in.lower()), None)
            if matching_user and str(USERS[matching_user]) == p_in:
                st.session_state.logged_in = True
                st.session_state.user = matching_user
                st.rerun()
            else: st.error("Bilgiler hatalı!")
    st.stop()

# --- 3. VERİ BAĞLANTISI ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(ws):
    st.cache_data.clear()
    try:
        df = conn.read(ttl=0, worksheet=ws)
        if not df.empty:
            df.columns = df.columns.str.strip()
        return df
    except: return pd.DataFrame()

df_u = get_data("Urun_Listesi")
df_h_raw = get_data("Sayfa1")

# --- 4. ARAYÜZ ---
c1, c2, c3 = st.columns([1, 3, 1])
with c1:
    if os.path.exists("brn_logo.webp"): st.image("brn_logo.webp", width=45)
with c2: st.write(f"**Operatör:** {st.session_state.user.upper()}")
with c3:
    if st.button("Çık"):
        st.session_state.logged_in = False
        st.rerun()

st.markdown("<hr style='margin:0'>", unsafe_allow_html=True)

t1, t2, t3 = st.tabs(["📥 İşlem", "🔄 Transfer", "📊 Stok"])

with t1:
    col_a, col_b = st.columns(2)
    tip = col_a.selectbox("İşlem:", ["GİRİŞ", "ÇIKIŞ"])
    adr = col_b.text_input("Adres:", "GENEL")
    kod = st.text_input("📦 Barkod Okut:", key="main_scan")
    
    if kod:
        match = df_u[df_u['Malzeme Kodu'].astype(str).str.upper() == str(kod).upper()]
        if not match.empty:
            ad, brm = match.iloc[0]['Malzeme Adı'], match.iloc[0]['Birim']
            st.success(f"**{ad}** ({brm})")
            step = 0.001 if str(brm).upper() not in ["ADET", "ADT"] else 1.0
            mik = st.number_input("Miktar:", min_value=0.0, step=step)
            if st.button("KAYDI TAMAMLA", use_container_width=True):
                if mik > 0:
                    yeni = pd.DataFrame({"Tarih": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")], "İşlem": [tip], "Adres": [adr.upper()], "Malzeme Kodu": [kod.upper()], "Malzeme Adı": [ad.upper()], "Birim": [str(brm).upper()], "Miktar": [float(mik)], "Kullanıcı": [st.session_state.user.upper()]})
                    conn.update(data=pd.concat([df_h_raw, yeni], ignore_index=True), worksheet="Sayfa1")
                    st.toast("Kaydedildi!")
                    st.rerun()
        else: st.error("Ürün Tanımsız!")

with t2:
    tr_k = st.text_input("Transfer Barkodu:", key="tr_scan")
    if tr_k and not df_u.empty:
        m_tr = df_u[df_u['Malzeme Kodu'].astype(str).str.upper() == str(tr_k).upper()]
        if not m_tr.empty:
            st.info(f"Ürün: {m_tr.iloc[0]['Malzeme Adı']}")
            ca, cb = st.columns(2)
            n_d, n_y = ca.text_input("Nerden:"), cb.text_input("Nereye:")
            tr_m = st.number_input("Miktar:", min_value=0.0, key="tr_qty")
            if st.button("TRANSFERİ ONAYLA", use_container_width=True):
                if n_y and tr_m > 0:
                    y1 = pd.DataFrame({"Tarih": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")], "İşlem": ["ÇIKIŞ"], "Adres": [n_d.upper()], "Malzeme Kodu": [tr_k.upper()], "Malzeme Adı": [m_tr.iloc[0]['Malzeme Adı'].upper()], "Birim": [str(m_tr.iloc[0]['Birim']).upper()], "Miktar": [float(tr_m)], "Kullanıcı": [st.session_state.user.upper()]})
                    y2 = pd.DataFrame({"Tarih": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")], "İşlem": ["GİRİŞ"], "Adres": [n_y.upper()], "Malzeme Kodu": [tr_k.upper()], "Malzeme Adı": [m_tr.iloc[0]['Malzeme Adı'].upper()], "Birim": [str(m_tr.iloc[0]['Birim']).upper()], "Miktar": [float(tr_m)], "Kullanıcı": [st.session_state.user.upper()]})
                    conn.update(data=pd.concat([df_h_raw, y1, y2], ignore_index=True), worksheet="Sayfa1")
                    st.toast("Transfer Tamam!"); st.rerun()

with t3:
    if st.button("🔄 Veriyi Güncelle"): st.rerun()
    ara = st.text_input("🔍 Filtre:").upper()
    if not df_h_raw.empty:
        df_h = df_h_raw.copy()
        df_h['Birim'] = df_h['Birim'].fillna('-')
        df_h['Miktar'] = pd.to_numeric(df_h['Miktar'], errors='coerce').fillna(0)
        df_h['Net'] = df_h.apply(lambda r: r['Miktar'] if str(r['İşlem']).upper() == 'GİRİŞ' else -r['Miktar'], axis=1)
        stok = df_h.groupby(['Adres', 'Malzeme Kodu', 'Malzeme Adı', 'Birim'])['Net'].sum().reset_index()
        stok = stok[stok['Net'] > 0]
        stok.columns = ["Adres", "Kod", "Ürün", "Brm", "Miktar"]
        if ara:
            stok = stok[(stok['Adres'].str.contains(ara, na=False)) | (stok['Kod'].str.contains(ara, na=False)) | (stok['Ürün'].str.contains(ara, na=False))]
        st.dataframe(stok, use_container_width=True, hide_index=True)

st.markdown("<p style='text-align:center; font-size:10px; color:gray;'>BRN SLEEP PRODUCTS | "BİLAL KEMERTAŞ", unsafe_allow_html=True)
