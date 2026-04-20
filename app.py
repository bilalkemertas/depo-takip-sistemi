import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import os

# --- 1. SAYFA AYARLARI VE AGRESİF GİZLEME (CSS) ---
st.set_page_config(page_title="Depo X-Ray v9.5", layout="centered", page_icon="brn_logo.webp")

# "Manage app" butonu ve diğer araç çubuklarını tamamen kapatan güncel CSS
# viewerBadge ile başlayan sınıflar Streamlit'in sağ alt butonunu hedefler.
hide_style = """
    <style>
    /* Streamlit öğelerini gizle */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Sağ üstteki Deploy butonu ve araç çubuğu */
    .stDeployButton {display:none !important;}
    div[data-testid="stToolbar"] {display: none !important;}
    div[data-testid="stDecoration"] {display: none !important;}
    
    /* SAĞ ALTTAKİ MANAGE APP BUTONU İÇİN KRİTİK BÖLÜM */
    div[class^="viewerBadge_container"] {display: none !important;}
    button[title="Manage app"] {display: none !important;}
    
    /* Sayfa paddinglerini el terminali için optimize et */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
    }
    </style>
    """
st.markdown(hide_style, unsafe_allow_html=True)

# --- 2. KULLANICI DOĞRULAMA ---
try:
    USERS = st.secrets["users"]
except:
    USERS = {"admin": "1234"}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🔒 Giriş Yapın</h2>", unsafe_allow_html=True)
    with st.form("Login"):
        u = st.text_input("Kullanıcı:")
        p = st.text_input("Parola:", type="password")
        if st.form_submit_button("GİRİŞ", use_container_width=True):
            if u in USERS and str(USERS[u]) == p:
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else: st.error("Hatalı!")
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

df_urunler = taze_veri_getir("Urun_Listesi")
df_hareketler = taze_veri_getir("Sayfa1")

def urun_bilgisi_cek(kod):
    if not df_urunler.empty and kod:
        match = df_urunler[df_urunler['Malzeme Kodu'].astype(str).str.upper() == str(kod).upper()]
        if not match.empty:
            return match.iloc[0]['Malzeme Adı'], match.iloc[0]['Birim']
    return None, None

def kayit_ekle(islem, adr, kod, ad, brm, mik):
    df_t = taze_veri_getir("Sayfa1")
    yeni = pd.DataFrame({
        "Tarih": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "İşlem": [islem], "Adres": [str(adr).upper()],
        "Malzeme Kodu": [str(kod).upper()], "Malzeme Adı": [str(ad).upper()],
        "Birim": [str(brm).upper()], "Miktar": [float(mik)],
        "Kullanıcı": [st.session_state.user.upper()]
    })
    conn.update(data=pd.concat([df_t, yeni], ignore_index=True), worksheet="Sayfa1")

# --- 4. ARAYÜZ (LOGO VE ÇIKIŞ) ---
c_l, c_u, c_o = st.columns([1, 3, 1])
with c_l:
    if os.path.exists("brn_logo.webp"): st.image("brn_logo.webp", width=45)
with c_u: st.write(f"**{st.session_state.user.upper()}**")
with c_o:
    if st.button("Çık"):
        st.session_state.logged_in = False
        st.rerun()

st.markdown("<hr style='margin:0'>", unsafe_allow_html=True)

# --- 5. SEKMELER ---
t1, t2, t3 = st.tabs(["📥 Kayıt", "🔄 Trans", "🔍 Rapor"])

with t1:
    c1, c2 = st.columns(2)
    i_tip = c1.selectbox("İşlem:", ["GİRİŞ", "ÇIKIŞ"])
    adr_v = c2.text_input("Adres:", "GENEL")
    k_v = st.text_input("📦 Barkod Okutun:", key="barkod_kayit")
    
    ad_b, brm_b = urun_bilgisi_cek(k_v)
    if k_v and ad_b:
        st.success(f"{ad_b}")
        step = 0.001 if str(brm_b).upper() not in ["ADET", "ADT", "AD"] else 1.0
        m_v = st.number_input("Miktar:", min_value=0.0, step=step)
        if st.button(f"{i_tip} KAYDET", use_container_width=True):
            if m_v > 0:
                kayit_ekle(i_tip, adr_v, k_v, ad_b, brm_b, m_v)
                st.toast("Kayıt Başarılı!")
                st.rerun()
    elif k_v: st.error("Tanımsız!")

with t2:
    tr_k = st.text_input("Transfer Kod:", key="tr_barkod")
    tr_ad, tr_b = urun_bilgisi_cek(tr_k)
    if tr_k and tr_ad:
        st.info(f"{tr_ad}")
        c_a, c_b = st.columns(2)
        n_d = c_a.text_input("Nerden:", "GENEL")
        n_y = c_b.text_input("Nereye:")
        tr_m = st.number_input("Miktar:", min_value=0.0, key="tr_m_v")
        if st.button("TRANSFER ET", use_container_width=True):
            if n_y and tr_m > 0:
                kayit_ekle("ÇIKIŞ", n_d, tr_k, tr_ad, tr_b, tr_m)
                kayit_ekle("GİRİŞ", n_y, tr_k, tr_ad, tr_b, tr_m)
                st.toast("Transfer Tamam!")
                st.rerun()

with t3:
    if st.button("🔄 Veriyi Yenile"): st.rerun()
    ara = st.text_input("🔍 Ara:").upper()
    if not df_hareketler.empty:
        df_h = df_hareketler.copy()
        df_h['Miktar'] = pd.to_numeric(df_h['Miktar'], errors='coerce').fillna(0)
        df_h['Net'] = df_h.apply(lambda r: r['Miktar'] if str(r['İşlem']).upper() == 'GİRİŞ' else -r['Miktar'], axis=1)
        stok = df_h.groupby(['Adres', 'Malzeme Kodu', 'Malzeme Adı', 'Birim'])['Net'].sum().reset_index()
        stok = stok[stok['Net'] > 0]
        stok.columns = ["Adres", "Kod", "Ürün", "Brm", "Miktar"]
        if ara:
            stok = stok[(stok['Adres'].str.contains(ara)) | (stok['Kod'].str.contains(ara)) | (stok['Ürün'].str.contains(ara))]
        st.dataframe(stok, use_container_width=True, hide_index=True)

st.markdown("<div style='text-align:center; color:gray; font-size:10px;'>BRN X-Ray v9.5</div>", unsafe_allow_html=True)
