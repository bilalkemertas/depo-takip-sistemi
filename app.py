import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- SAYFA ---
st.set_page_config(page_title="BRN Depo", layout="centered")

# --- GÜVENLİK ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    with st.form("login"):
        u = st.text_input("Kullanıcı").lower().strip()
        p = st.text_input("Parola", type="password")
        if st.form_submit_button("Giriş"):
            if u in st.secrets["users"] and st.secrets["users"][u] == p:
                st.session_state.logged_in = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Hatalı giriş")
    st.stop()

# --- GSHEET BAĞLANTI (APPEND FIX) ---
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
sheet = client.open_by_key(SHEET_ID).worksheet("Sayfa1")

# --- HEADER ---
st.write(f"👤 {st.session_state.user.upper()}")
if st.button("Çık"):
    st.session_state.logged_in = False
    st.rerun()

st.divider()

# --- TABLAR ---
t1, t2, t3 = st.tabs(["📥 İşlem", "🔄 Transfer", "📊 Stok"])

# --- İŞLEM ---
with t1:
    islem = st.selectbox("İşlem", ["GİRİŞ", "ÇIKIŞ"])
    adres = st.text_input("Adres").upper()
    kod = st.text_input("Kod").upper()
    ad = st.text_input("Ad").upper()
    birim = st.selectbox("Birim", ["ADET","KG","METRE","RULO"])
    miktar = st.number_input("Miktar", min_value=0.1)

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
            st.success("Kaydedildi")
        else:
            st.warning("Kod gir")

# --- TRANSFER ---
with t2:
    eski = st.text_input("Eski Raf").upper()
    yeni = st.text_input("Yeni Raf").upper()
    kod = st.text_input("Kod", key="t_kod").upper()
    birim = st.selectbox("Birim", ["ADET","KG","METRE","RULO"], key="t_birim")
    miktar = st.number_input("Miktar", min_value=0.1, key="t_miktar")

    if st.button("Transfer"):
        if eski and yeni and kod:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            sheet.append_row([now,"ÇIKIŞ",eski,kod,"TRANSFER",birim,miktar,st.session_state.user])
            sheet.append_row([now,"GİRİŞ",yeni,kod,"TRANSFER",birim,miktar,st.session_state.user])

            st.success("Transfer yapıldı")
        else:
            st.error("Eksik alan")

# --- CACHE OKUMA ---
@st.cache_data(ttl=10)
def load_data():
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# --- STOK ---
with t3:
    if "refresh" not in st.session_state:
        st.session_state.refresh = 0

    if st.button("Stok Listesini Hesapla"):
        st.session_state.refresh += 1

    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.session_state.refresh += 1

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

        # SADECE NET STOK
        stok = stok[stok["Bakiye"] > 0]

        st.dataframe(stok, use_container_width=True, hide_index=True)
    else:
        st.info("Veri yok")
