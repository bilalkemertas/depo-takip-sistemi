import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import os

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Bilal BRN Depo", layout="centered", page_icon="brn_logo.webp")

# --- KULLANICI LİSTESİ (Burayı dilediğin gibi çoğaltabilirsin) ---
USERS = {
    "admin": "506413",
    "depo1": "brn2026",
    "depo2": "brn2026."
    "depo3": "brn.2026"
}

# --- LOGIN KONTROLÜ ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = ""

def login_ekrani():
    st.markdown("<h2 style='text-align: center;'>🔒 Depo Giriş</h2>", unsafe_allow_html=True)
    with st.form("Login"):
        u_name = st.text_input("Kullanıcı Adı:")
        u_pass = st.text_input("Parola:", type="password")
        submit = st.form_submit_button("GİRİŞ YAP", use_container_width=True)
        
        if submit:
            if u_name in USERS and USERS[u_name] == u_pass:
                st.session_state.logged_in = True
                st.session_state.user = u_name
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya parola!")

if not st.session_state.logged_in:
    login_ekrani()
    st.stop() # Giriş yapılmadıysa uygulamanın geri kalanını çalıştırma

# --- BAĞLANTI VE FONKSİYONLAR ---
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
        "Kullanıcı": [st.session_state.user.upper()] # KİMİN YAPTIĞI BURADA TUTULUYOR
    })
    conn.update(data=pd.concat([df_temp, yeni_kayit], ignore_index=True), worksheet="Sayfa1")

# --- ÜST PANEL (Logo & Çıkış) ---
c1, c2, c3 = st.columns([1, 3, 1])
with c1:
    if os.path.exists("brn_logo.webp"): st.image("brn_logo.webp", width=50)
with c2:
    st.markdown(f"**Hoş geldin, {st.session_state.user.upper()}**")
with c3:
    if st.button("Çıkış"):
        st.session_state.logged_in = False
        st.rerun()
st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)

# --- SEKMELER ---
t1, t2, t3 = st.tabs(["📥 Kayıt", "🔄 Transfer", "🔍 Rapor"])

with t1:
    c_isl, c_adr = st.columns(2)
    islem_tipi = c_isl.selectbox("İşlem:", ["GİRİŞ", "ÇIKIŞ"])
    adr = c_adr.text_input("Adres:", value="GENEL")
    kod = st.text_input("📦 Ürün Kodu:")
    ad_bulunan, birim_bulunan = urun_bilgisi_cek(kod)
    if kod and ad_bulunan:
        st.success(f"{ad_bulunan} ({birim_bulunan})")
        step_val = 0.001 if str(birim_bulunan).upper() not in ["ADET", "ADT"] else 1.0
        mik = st.number_input(f"Miktar:", min_value=0.0, step=step_val)
        if st.button(f"{islem_tipi} KAYDET", use_container_width=True):
            if mik > 0:
                kayit_ekle(islem_tipi, adr, kod, ad_bulunan, birim_bulunan, mik)
                st.success("İşlem kaydedildi.")
                st.rerun()

with t2:
    tr_kod = st.text_input("Transfer Ürün Kodu:", key="tr_k")
    tr_ad, tr_birim = urun_bilgisi_cek(tr_kod)
    if tr_kod and tr_ad:
        st.info(f"{tr_ad}")
        ca, cb = st.columns(2)
        n_den = ca.text_input("Nereden:", value="GENEL")
        n_ye = cb.text_input("Nereye:")
        tr_mik = st.number_input("Miktar:", min_value=0.0, key="tr_mik")
        if st.button("TRANSFERİ TAMAMLA", use_container_width=True):
            if n_ye and tr_mik > 0:
                kayit_ekle("ÇIKIŞ", n_den, tr_kod, tr_ad, tr_birim, tr_mik)
                kayit_ekle("GİRİŞ", n_ye, tr_kod, tr_ad, tr_birim, tr_mik)
                st.success("Transfer tamamlandı.")
                st.rerun()

with t3:
    search = st.text_input("🔍 Ara (Kod, Ad veya Adres):")
    if not df_hareketler.empty:
        df_h = df_hareketler.copy()
        df_h['Miktar'] = pd.to_numeric(df_h['Miktar'], errors='coerce').fillna(0)
        df_h['Net'] = df_h.apply(lambda r: r['Miktar'] if str(r['İşlem']).upper() == 'GİRİŞ' else -r['Miktar'], axis=1)
        
        stok = df_h.groupby(['Adres', 'Malzeme Kodu', 'Malzeme Adı', 'Birim'])['Net'].sum().reset_index()
        stok = stok[stok['Net'] > 0]
        stok.columns = ["Adr", "Kod", "Ad", "Brm", "Miktar"]
        
        if search:
            s = search.upper()
            stok = stok[(stok['Adr'].str.upper().str.contains(s, na=False)) | (stok['Kod'].str.upper().str.contains(s, na=False)) | (stok['Ad'].str.upper().str.contains(s, na=False))]
        
        st.dataframe(stok, use_container_width=True, hide_index=True)
