import streamlit as st
from core import db
from modules import stok_islemleri, uretim_hazirlik, sayim_modulu, blok_kesim, teslim_alma

# --- INIT ---
db.init_db()

st.set_page_config(
    page_title="Depo Otomasyon v2.0",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- MENU ---
st.sidebar.title("📦 DEPO KONTROL MERKEZİ")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "İşlem Seçiniz:",
    [
        "🏠 Ana Sayfa",
        "📊 Stok Giriş/Çıkış",
        "↔️ Depo İçi Transfer",
        "📥 Mal Kabul",
        "🏗️ Üretim Hazırlık",
        "📝 Sayım Modülü",
        "✂️ BLOK KESİM"
    ]
)

# --- PAGES ---
if page == "🏠 Ana Sayfa":
    st.title("Depo Yönetim Paneli")

elif page == "📊 Stok Giriş/Çıkış":
    stok_islemleri.run_islem()

elif page == "↔️ Depo İçi Transfer":
    stok_islemleri.run_transfer()

elif page == "📥 Mal Kabul":
    teslim_alma.run()

elif page == "🏗️ Üretim Hazırlık":
    uretim_hazirlik.run()

elif page == "📝 Sayım Modülü":
    sayim_modulu.run()

elif page == "✂️ BLOK KESİM":
    blok_kesim.run_blok_kesim(db.get_drive_conn())
