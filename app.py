import streamlit as st

# ---------------- CORE ----------------
from core import db

# ---------------- MODULES ----------------
from modules import (
    stok_islemleri,
    uretim_hazirlik,
    sayim_modulu,
    blok_kesim
)

# ---------------- INIT DB ----------------
db.init_db()

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Depo Otomasyon v3 - SQLite",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- SESSION INIT ----------------
if "user" not in st.session_state:
    st.session_state.user = "admin"  # şimdilik basit auth

if "page" not in st.session_state:
    st.session_state.page = "home"


# ---------------- SIDEBAR MENU ----------------
st.sidebar.title("📦 WMS CONTROL CENTER")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "İşlem Seçiniz",
    [
        "🏠 Ana Sayfa",
        "📊 Stok Giriş / Çıkış",
        "↔️ Depo Transfer",
        "🏗️ Üretim Hazırlık",
        "📝 Sayım Modülü",
        "✂️ Blok Kesim"
    ]
)

st.sidebar.markdown("---")
st.sidebar.info(f"Kullanıcı: {st.session_state.user}")


# ---------------- ROUTER ----------------
if page == "🏠 Ana Sayfa":
    st.title("📦 SQLite WMS Sistemine Hoş Geldiniz")
    st.write("Modül seçerek işlemlere başlayabilirsiniz.")

    # hızlı özet
    df = db.read("stok")
    st.metric("Toplam Stok Kalemi", len(df))

elif page == "📊 Stok Giriş / Çıkış":
    stok_islemleri.run()

elif page == "↔️ Depo Transfer":
    stok_islemleri.run_transfer()

elif page == "🏗️ Üretim Hazırlık":
    uretim_hazirlik.run()

elif page == "📝 Sayım Modülü":
    sayim_modulu.run()

elif page == "✂️ Blok Kesim":
    blok_kesim.run()
