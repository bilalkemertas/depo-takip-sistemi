import streamlit as st
from streamlit_gsheets import GSheetsConnection

from modules import stok_islemleri, uretim_hazirlik, sayim_modulu, blok_kesim

# ---------------------------
# SAYFA AYARLARI
# ---------------------------
st.set_page_config(
    page_title="Depo Otomasyon v2.0",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------
# GOOGLE SHEETS BAĞLANTISI
# ---------------------------
conn = st.connection("gsheets", type=GSheetsConnection)

# ---------------------------
# MENU
# ---------------------------
st.sidebar.title("📦 DEPO KONTROL MERKEZİ")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "İşlem Seçiniz:",
    [
        "🏠 Ana Sayfa",
        "📊 Stok Giriş/Çıkış",
        "↔️ Depo İçi Transfer",
        "🏗️ Üretim Hazırlık",
        "📝 Sayım Modülü",
        "✂️ BLOK KESİM"
    ]
)

# ---------------------------
# ROUTER
# ---------------------------
if page == "🏠 Ana Sayfa":
    st.title("Depo Yönetim Paneli")
    st.info("İşlem için sol menüyü kullanın.")

elif page == "📊 Stok Giriş/Çıkış":
    stok_islemleri.run_islem(conn)

elif page == "↔️ Depo İçi Transfer":
    stok_islemleri.run_transfer(conn)

elif page == "🏗️ Üretim Hazırlık":
    uretim_hazirlik.run(conn)

elif page == "📝 Sayım Modülü":
    sayim_modulu.run(conn)

elif page == "✂️ BLOK KESİM":
    blok_kesim.run_blok_kesim(conn)
