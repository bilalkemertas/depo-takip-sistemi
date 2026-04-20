import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import os

# --- 1. SAYFA AYARLARI VE TAM GİZLEME (CSS) ---
st.set_page_config(page_title="Depo X-Ray v9.4", layout="centered", page_icon="brn_logo.webp")

# Sağ alttaki 'Manage app', 'Made with Streamlit' ve üst bannerları tamamen yok eden kod
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
    # Secrets ayarlanmamışsa yedek giriş
    USERS = {"admin": "1234"}

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
    is_tip = c1.selectbox("İşlem:", ["GİRİŞ", "ÇIKIŞ"])
    adr_val = c2.text_input("Adres:", value="GENEL")
    kod_val = st.text_input("📦 Ürün Kodu:")
    
    ad_bul, birim_bul = urun_bilgisi_cek(kod_val)
    if kod_val:
        if ad_bul:
            st.success(f"{ad_bul} ({birim_bul})")
            step_v = 0.001 if str(birim_bul).upper() not in ["ADET", "ADT", "AD"] else 1.0
            mik_val = st.number_input("Miktar:", min_value=0.0, step=step_v)
            if st.button(f"{is_tip} KAYDET", use_container_width=True):
                if mik_val > 0:
                    kayit_ekle(is_tip, adr_val, kod_val, ad_bul, birim_bul, mik_val)
                    st.success("Kaydedildi!")
                    st.rerun()
        else: st.error("Ürün Tanımsız!")

with t2:
    tr_kod = st.text_input("Transfer Ürün Kod:", key="tr_k")
    tr_ad, tr_birim = urun_bilgisi_cek(tr_kod)
    if tr_kod and tr_ad:
        st.info(f"Ürün: {tr_ad}")
        ca, cb = st.columns(2)
        n_den = ca.text_input("Nereden:", value="GENEL")
        n_ye = cb.text_input("Nereye:")
        tr_mik = st.number_input("Miktar:", min_value=0.0, key="tr_mik_val")
        if st.button("TRANSFERİ TAMAMLA", use_container_width=True):
            if n_ye and tr_mik > 0: # Hata buradaydı, düzeltildi.
                kayit_ekle("ÇIKIŞ", n_den, tr_kod, tr_ad, tr_birim, tr_mik)
                kayit_ekle("GİRİŞ", n_ye, tr_kod, tr_ad, tr_birim, tr_mik)
                st.success("Başarıyla Taşındı.")
                st.rerun()

with t3:
    col_t, col_b = st.columns([2, 1])
    col_t.caption("📊 Mevcut Stoklar")
    if col_b.button("🔄 Yenile"): st.rerun()
    
    search = st.text_input("🔍 Ara:", placeholder="Kod, İsim veya Adres...")
    
    if not df_hareketler.empty:
        df_h = df_hareketler.copy()
        if 'Birim' in df_h.columns:
            df_h['Miktar'] = pd.to_numeric(df_h['Miktar'], errors='coerce').fillna(0)
            df_h['Net'] = df_h.apply(lambda r: r['Miktar'] if str(r['İşlem']).upper() == 'GİRİŞ' else -r['Miktar'], axis=1)
            stok = df_h.groupby(['Adres', 'Malzeme Kodu', 'Malzeme Adı', 'Birim'])['Net'].sum().reset_index()
            stok = stok[stok['Net'] > 0]
            stok.columns = ["Adr", "Kod", "Ad", "Brm", "Miktar"]
            if search:
                s = search.upper()
                stok = stok[(stok['Adr'].str.upper().str.contains(s, na=False)) | 
                            (stok['Kod'].str.upper().str.contains(s, na=False)) | 
                            (stok['Ad'].str.upper().str.contains(s, na=False))]
            st.dataframe(stok, use_container_width=True, hide_index=True)

# --- 6. İMZA ---
st.markdown(f"<div style='text-align: center; color: gray; font-size: 0.7em; margin-top: 30px;'>🛡️ BRN Depo X-Ray v9.4 | Tasarlayan: [SENİN ADIN]</div>", unsafe_allow_html=True)
