import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import os
import streamlit.components.v1 as components

# --- 1. MODERN ARAYÜZ VE AGRESİF GİZLEME ---
st.set_page_config(page_title="BRN X-Ray Pro", layout="centered", page_icon="brn_logo.webp")

hide_all_style = """
    <style>
    #MainMenu, footer, header, .stDeployButton {display: none !important; visibility: hidden !important;}
    [data-testid="stStatusWidget"], [data-testid="stToolbar"], [data-testid="stDecoration"] {display: none !important;}
    div[class*="viewerBadge"], div[class*="StreamlitFrameBadge"], button[title*="Manage"] {
        display: none !important; height: 0px !important; width: 0px !important;
    }
    .block-container { padding-top: 0.5rem !important; padding-bottom: 0rem !important; max-width: 98% !important; }
    input { font-size: 16px !important; }
    </style>
"""
st.markdown(hide_all_style, unsafe_allow_html=True)

# 2026 Agresif JavaScript Temizlik
components.html(
    """
    <script>
    const cleanSystemUI = () => {
        const selectors = ['div[class*="viewerBadge"]', 'button[title*="Manage app"]', '[data-testid="bundle-viewer-button"]', 'footer', '.stAppDeployButton', 'header'];
        selectors.forEach(selector => {
            try { window.parent.document.querySelectorAll(selector).forEach(el => el.remove()); } catch (e) {}
        });
    };
    setInterval(cleanSystemUI, 300);
    </script>
    """,
    height=0,
)

# --- 2. GÜVENLİK (Kullanıcı Adı Harf Duyarsız, Parola Duyarlı) ---
try:
    USERS = st.secrets["users"]
except Exception:
    USERS = {"admin": "1234"} # Settings > Secrets kısmına eklenmeli

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h3 style='text-align:center;'>🛡️ BRN Giriş</h3>", unsafe_allow_html=True)
    with st.form("Giriş"):
        u_input = st.text_input("Kullanıcı Adı:")
        p_input = st.text_input("Parola:", type="password")
        if st.form_submit_button("SİSTEME GİRİŞ", use_container_width=True):
            # KULLANICI ADI KONTROLÜ: Girdiyi ve listedekileri küçültüp kıyaslıyoruz
            found_user = next((u for u in USERS if u.lower() == u_input.lower()), None)
            
            if found_user:
                # PAROLA KONTROLÜ: Harf duyarlılığını korumak için doğrudan kıyaslıyoruz
                if str(USERS[found_user]) == p_input:
                    st.session_state.logged_in = True
                    st.session_state.user = found_user
                    st.rerun()
                else: st.error("Hatalı Parola!")
            else: st.error("Kullanıcı Bulunamadı!")
    st.stop()

# --- 3. VERİ BAĞLANTISI ---
conn = st.connection("gsheets", type=GSheetsConnection)

def taze_veri_getir(ws="Sayfa1"):
    st.cache_data.clear()
    try:
        df = conn.read(ttl=0, worksheet=ws)
        if not df.empty: df.columns = df.columns.str.strip()
        return df
    except: return pd.DataFrame()

df_u = taze_veri_getir("Urun_Listesi")
df_h_raw = taze_veri_getir("Sayfa1")

# --- 4. ARAYÜZ ---
c1, c2, c3 = st.columns([1, 3, 1])
with c1:
    if os.path.exists("brn_logo.webp"): st.image("brn_logo.webp", width=45)
with c2: st.write(f"**Operatör:** {st.session_state.user.upper()}")
with c3:
    if st.button("Çıkış"):
        st.session_state.logged_in = False
        st.rerun()

st.markdown("<hr style='margin:0'>", unsafe_allow_html=True)
t1, t2, t3 = st.tabs(["📥 İşlem", "🔄 Transfer", "🔍 Stok"])

with t1:
    col_a, col_b = st.columns(2)
    i_tip = col_a.selectbox("İşlem:", ["GİRİŞ", "ÇIKIŞ"])
    adr_v = col_b.text_input("Adres:", "GENEL")
    k_v = st.text_input("📦 Barkod Okutun:", key="reg_scan")
    
    if k_v and not df_u.empty:
        match = df_u[df_u['Malzeme Kodu'].astype(str).str.upper() == str(k_v).upper()]
        if not match.empty:
            ad_b, brm_b = match.iloc[0]['Malzeme Adı'], match.iloc[0]['Birim']
            st.success(f"{ad_b} ({brm_b})")
            step = 0.001 if str(brm_b).upper() not in ["ADET", "ADT"] else 1.0
            m_v = st.number_input("Miktar:", min_value=0.0, step=step)
            if st.button("KAYDI TAMAMLA", use_container_width=True):
                if m_v > 0:
                    yeni = pd.DataFrame({"Tarih": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")], "İşlem": [i_tip], "Adres": [adr_v.upper()], "Malzeme Kodu": [k_v.upper()], "Malzeme Adı": [ad_b.upper()], "Birim": [brm_b.upper()], "Miktar": [float(m_v)], "Kullanıcı": [st.session_state.user.upper()]})
                    conn.update(data=pd.concat([df_h_raw, yeni], ignore_index=True), worksheet="Sayfa1")
                    st.toast("Kaydedildi!")
                    st.rerun()
        else: st.error("Ürün Tanımsız!")

with t2:
    tr_k = st.text_input("Transfer Barkod:", key="tr_scan")
    if tr_k and not df_u.empty:
        m_tr = df_u[df_u['Malzeme Kodu'].astype(str).str.upper() == str(tr_k).upper()]
        if not m_tr.empty:
            st.info(f"Ürün: {m_tr.iloc[0]['Malzeme Adı']}")
            ca, cb = st.columns(2)
            n_d, n_y = ca.text_input("Nerden:"), cb.text_input("Nereye:")
            tr_m = st.number_input("Miktar:", min_value=0.0, key="tr_qty")
            if st.button("TRANSFERİ ONAYLA", use_container_width=True):
                if n_y and tr_m > 0:
                    # Çıkış ve Giriş
                    y1 = pd.DataFrame({"Tarih": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")], "İşlem": ["ÇIKIŞ"], "Adres": [n_d.upper()], "Malzeme Kodu": [tr_k.upper()], "Malzeme Adı": [m_tr.iloc[0]['Malzeme Adı'].upper()], "Birim": [m_tr.iloc[0]['Birim'].upper()], "Miktar": [float(tr_m)], "Kullanıcı": [st.session_state.user.upper()]})
                    y2 = pd.DataFrame({"Tarih": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")], "İşlem": ["GİRİŞ"], "Adres": [n_y.upper()], "Malzeme Kodu": [tr_k.upper()], "Malzeme Adı": [m_tr.iloc[0]['Malzeme Adı'].upper()], "Birim": [m_tr.iloc[0]['Birim'].upper()], "Miktar": [float(tr_m)], "Kullanıcı": [st.session_state.user.upper()]})
                    conn.update(data=pd.concat([df_h_raw, y1, y2], ignore_index=True), worksheet="Sayfa1")
                    st.toast("Transfer Tamam!")
                    st.rerun()

with t3:
    if st.button("🔄 Veriyi Yenile"): st.rerun()
    ara = st.text_input("🔍 Filtre (Kod/Adres/İsim):").upper()
    if not df_h_raw.empty:
        df_h = df_h_raw.copy()
        # --- NaN TEMİZLİĞİ ---
        df_h['Birim'] = df_h['Birim'].fillna('-')
        df_h['Malzeme Adı'] = df_h['Malzeme Adı'].fillna('İsimsiz')
        df_h['Miktar'] = pd.to_numeric(df_h['Miktar'], errors='coerce').fillna(0)
        
        df_h['Net'] = df_h.apply(lambda r: r['Miktar'] if str(r['İşlem']).upper() == 'GİRİŞ' else -r['Miktar'], axis=1)
        stok = df_h.groupby(['Adres', 'Malzeme Kodu', 'Malzeme Adı', 'Birim'])['Net'].sum().reset_index()
        stok = stok[stok['Net'] > 0]
        stok.columns = ["Adres", "Kod", "Ürün", "Brm", "Miktar"]
        if ara:
            stok = stok[(stok['Adres'].str.contains(ara, na=False)) | (stok['Kod'].str.contains(ara, na=False)) | (stok['Ürün'].str.contains(ara, na=False))]
        st.dataframe(stok, use_container_width=True, hide_index=True)

st.markdown("<div style='text-align:center; color:gray; font-size:10px; margin-top:20px;'>BRN X-Ray Pro v10.1 | 2026 Enterprise</div>", unsafe_allow_html=True)
