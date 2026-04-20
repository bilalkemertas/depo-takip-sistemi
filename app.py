import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import os

# --- 1. SAYFA AYARLARI VE GİZLEME (CSS) ---
st.set_page_config(page_title="Depo X-Ray v9.3", layout="centered", page_icon="brn_logo.webp")

# Sağ alttaki "Manage app", üstteki banner ve menüleri tamamen gizleyen profesyonel CSS
hide_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    div[data-testid="stToolbar"] {display: none;}
    div[data-testid="stDecoration"] {display: none;}
    .stDeployButton {display:none;}
    .viewerBadge_container__1QS1n {display: none !important;}
    </style>
    """
st.markdown(hide_style, unsafe_allow_html=True)

# --- 2. KULLANICI DOĞRULAMA (Secrets) ---
try:
    USERS = st.secrets["users"]
except Exception:
    # Eğer Secrets ayarlanmamışsa hata vermemesi için varsayılan
    USERS = {"admin": "1234"}

# Giriş Durumu Kontrolü
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = ""

def login_ekrani():
    st.markdown("<h2 style='text-align: center;'>🔒 Depo Giriş</h2>", unsafe_allow_html=True)
    with st.form("Login"):
        u_name = st.text_input("Kullanıcı Adı:")
        u_pass = st.text_input("Parola:", type="password")
        submit = st.form_submit_button("SİSTEME GİRİŞ", use_container_width=True)
        if submit:
            if u_name in USERS and str(USERS[u_name]) == u_pass:
                st.session_state.logged_in = True
                st.session_state.user = u_name
                st.rerun()
            else:
                st.error("Hatalı Giriş Bilgisi!")

if not st.session_state.logged_in:
    login_ekrani()
    st.stop()

# --- 3. BAĞLANTI VE VERİ FONKSİYONLARI ---
conn = st.connection("gsheets", type=GSheetsConnection)

def taze_veri_getir(worksheet="Sayfa1"):
    st.cache_data.clear()
    try:
        df = conn.read(ttl=0, worksheet=worksheet)
        if not df.empty:
            df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame()

# Verileri çek
df_urunler = taze_veri_getir(worksheet="Urun_Listesi")
df_hareketler = taze_veri_getir(worksheet="Sayfa1")

def urun_bilgisi_cek(kod):
    if not df_urunler.empty and kod:
        if 'Malzeme Kodu' in df_urunler.columns:
            match = df_urunler[df_urunler['Malzeme Kodu'].astype(str).str.upper() == str(kod).upper()]
            if not match.empty:
                return match.iloc[0]['Malzeme Adı'], match.iloc[0]['Birim']
    return None, None

def kayit_ekle(islem, adres, kod, ad, birim, miktar):
    df_temp = taze_veri_getir(worksheet="Sayfa1")
    yeni_kayit = pd.DataFrame({
        "Tarih": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "İşlem": [islem],
        "Adres": [str(adres).upper()],
        "Malzeme Kodu": [str(kod).upper()],
        "Malzeme Adı": [str(ad).upper()],
        "Birim": [str(birim).upper()],
        "Miktar": [float(miktar)],
        "Kullanıcı": [st.session_state.user.upper()]
    })
    conn.update(data=pd.concat([df_temp, yeni_kayit], ignore_index=True), worksheet="Sayfa1")

# --- 4. ÜST PANEL (Logo ve Kullanıcı Bilgisi) ---
col_logo, col_user, col_out = st.columns([1, 3, 1])
with col_logo:
    if os.path.exists("brn_logo.webp"):
        st.image("brn_logo.webp", width=50)
with col_user:
    st.markdown(f"<p style='margin-top:10px;'><b>{st.session_state.user.upper()}</b></p>", unsafe_allow_html=True)
with col_out:
    if st.button("Çıkış"):
        st.session_state.logged_in = False
        st.rerun()

st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)

# --- 5. ANA SEKMELER ---
t1, t2, t3 = st.tabs(["📥 Kayıt", "🔄 Transfer", "🔍 Rapor"])

with t1:
    c1, c2 = st.columns(2)
    islem_tipi = c1.selectbox("İşlem:", ["GİRİŞ", "ÇIKIŞ"])
    adr = c2.text_input("Adres:", value="GENEL")
    kod = st.text_input("📦 Ürün Kodunu Okutun:")
    ad_bulunan, birim_bulunan = urun_bilgisi_cek(kod)
    
    if kod:
        if ad_bulunan:
            st.success(f"{ad_bulunan} ({birim_bulunan})")
            # Birim Adet değilse küsürat aç
            step_val = 0.001 if str(birim_bulunan).upper() not in ["ADET", "ADT", "AD"] else 1.0
            mik = st.number_input(f"Miktar:", min_value=0.0, step=step_val)
            if st.button(f"{islem_tipi} KAYDET", use_container_width=True):
                if mik > 0:
                    kayit_ekle(islem_tipi, adr, kod, ad_bulunan, birim_bulunan, mik)
                    st.success("Kaydedildi!")
                    st.rerun()
        else: st.error("Ürün Tanımsız!")

with t2:
    tr_kod = st.text_input("Transfer Ürün Kod:", key="tr_k")
    tr_ad, tr_birim = urun_bilgisi_cek(tr_kod)
    if tr_kod and tr_ad:
        st.info(f"Transfer: {tr_ad}")
        ca, cb = st.columns(2)
        n_den = ca.text_input("Nereden:", value="GENEL")
        n_ye = cb.text_input("Nereye:")
        tr_mik = st.number_input("Miktar:", min_value=0.0, key="tr_mik")
        if st.button("TRANSFERİ TAMAMLA", use_container_width=True):
            if n_ye and tr_mik >
