import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ======================
# SAYFA AYARLARI
# ======================
st.set_page_config(page_title="Depo Sistemi", layout="centered")

# ======================
# LOGIN
# ======================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    with st.form("login"):
        user = st.text_input("Kullanıcı").lower().strip()
        passw = st.text_input("Şifre", type="password")

        if st.form_submit_button("Giriş"):
            if user in st.secrets["users"] and st.secrets["users"][user] == passw:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Hatalı giriş")
    st.stop()

# ======================
# GSHEET BAĞLANTI (DOĞRU YAPI)
# ======================
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["connections"]["gsheets"],
    scopes=scope
)

client = gspread.authorize(creds)

SHEET_ID = st.secrets["connections"]["gsheets"]["spreadsheet"]

# ⚠️ KRİTİK: Sheet adı değil ID olmalı
sheet = client.open_by_key(SHEET_ID).worksheet("Sayfa1")

# ======================
# HEADER
# ======================
st.title("📦 Depo Yönetim Sistemi")

col1, col2 = st.columns([3,1])
with col1:
    st.write(f"Kullanıcı: **{st.session_state.user.upper()}**")
with col2:
    if st.button("Çıkış"):
        st.session_state.logged_in = False
        st.rerun()

st.divider()

# ======================
# TABLAR
# ======================
tab1, tab2, tab3 = st.tabs(["📥 İşlem", "🔄 Transfer", "📊 Stok"])

# ======================
# VERİ OKUMA (CACHE)
# ======================
@st.cache_data(ttl=10)
def load_data():
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# ======================
# İŞLEM (GİRİŞ / ÇIKIŞ)
# ======================
with tab1:
    islem = st.selectbox("İşlem", ["GİRİŞ", "ÇIKIŞ"])
    adres = st.text_input("Adres").upper()
    kod = st.text_input("Malzeme Kodu").upper()
    ad = st.text_input("Malzeme Adı").upper()
    birim = st.selectbox("Birim", ["ADET","KG","METRE","RULO"])
    miktar = st.number_input("Miktar", min_value=0.1, step=0.1)

    if st.button("Kaydet"):
        if kod:
            sheet.append_row([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                islem,
                adres,
                kod,
                ad,
                birim,
                miktar,
                st.session_state.user
            ])
            st.success("Kayıt eklendi")
        else:
            st.warning("Kod boş olamaz")

# ======================
# TRANSFER
# ======================
with tab2:
    eski = st.text_input("Eski Lokasyon").upper()
    yeni = st.text_input("Yeni Lokasyon").upper()
    kod = st.text_input("Malzeme Kodu", key="tr_kod").upper()
    birim = st.selectbox("Birim", ["ADET","KG","METRE","RULO"], key="tr_birim")
    miktar = st.number_input("Miktar", min_value=0.1, key="tr_miktar")

    if st.button("Transfer Et"):
        if eski and yeni and kod:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # ÇIKIŞ
            sheet.append_row([
                now,"ÇIKIŞ",eski,kod,"TRANSFER",birim,miktar,st.session_state.user
            ])

            # GİRİŞ
            sheet.append_row([
                now,"GİRİŞ",yeni,kod,"TRANSFER",birim,miktar,st.session_state.user
            ])

            st.success("Transfer tamamlandı")
        else:
            st.error("Eksik bilgi")

# ======================
# STOK (NET HESAP)
# ======================
with tab3:

    if st.button("🔄 Refresh"):
        st.cache_data.clear()

    df = load_data()

    if not df.empty:

        df["Miktar"] = pd.to_numeric(df["Miktar"], errors="coerce").fillna(0)

        # NET HESAP
        df["Net"] = df.apply(
            lambda x: x["Miktar"] if x["İşlem"] == "GİRİŞ"
            else -x["Miktar"], axis=1
        )

        stok = df.groupby(
            ["Adres","Malzeme Kodu","Malzeme Adı","Birim"]
        )["Net"].sum().reset_index()

        stok.columns = ["Adres","Kod","Ad","Birim","Bakiye"]

        # sadece mevcut stok
        stok = stok[stok["Bakiye"] > 0]

        st.dataframe(stok, use_container_width=True, hide_index=True)

    else:
        st.info("Veri yok")
