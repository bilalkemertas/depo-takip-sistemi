import streamlit as st
from streamlit_gsheets import GSheetsConnection
from modules import stok_islemleri, uretim_hazirlik, sayim_modulu

# Sayfa Ayarları
st.set_page_config(page_title="Depo Otomasyon v2.0", layout="wide", initial_sidebar_state="expanded")

# Veritabanı Bağlantısı (Tek Seferlik)
conn = st.connection("gsheets", type=GSheetsConnection)

# Navigasyon Menüsü
st.sidebar.title("📦 DEPO KONTROL MERKEZİ")
st.sidebar.markdown("---")
page = st.sidebar.radio("İşlem Seçiniz:", 
    ["🏠 Ana Sayfa", "📊 Stok Giriş/Çıkış", "↔️ Depo İçi Transfer", "🏗️ Üretim Hazırlık", "📝 Sayım Modülü"])

if page == "🏠 Ana Sayfa":
    st.title("Depo Yönetim Paneli")
    st.info("Lütfen işlem yapmak için sol taraftaki menüyü kullanın.")
    # Buraya genel stok durum grafikleri eklenebilir

elif page == "📊 Stok Giriş/Çıkış":
    stok_islemleri.run_islem(conn)

elif page == "↔️ Depo İçi Transfer":
    stok_islemleri.run_transfer(conn)

elif page == "🏗️ Üretim Hazırlık":
    uretim_hazirlik.run(conn)

elif page == "📝 Sayım Modülü":
    sayim_modulu.run(conn)
