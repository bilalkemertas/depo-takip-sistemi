import streamlit as st
from streamlit_gsheets import GSheetsConnection
# blok_kesim modülü import listesine eklendi
from modules import stok_islemleri, uretim_hazirlik, sayim_modulu, blok_kesim 

# Sayfa Ayarları
st.set_page_config(page_title="Depo Otomasyon v2.0", layout="wide", initial_sidebar_state="expanded")

# Veritabanı Bağlantısı (Tek Seferlik)
conn = st.connection("gsheets", type=GSheetsConnection)

# Navigasyon Menüsü
st.sidebar.title("📦 DEPO KONTROL MERKEZİ")
st.sidebar.markdown("---")
page = st.sidebar.radio("İşlem Seçiniz:", 
    ["🏠 Ana Sayfa", "📊 Stok Giriş/Çıkış", "↔️ Depo İçi Transfer", "🏗️ Üretim Hazırlık", "📝 Sayım Modülü", "✂️ BLOK KESİM"]) # <-- Menüye eklendi

if page == "🏠 Ana Sayfa":
    st.title("Depo Yönetim Paneli")
    st.info("Lütfen işlem yapmak için sol taraftaki menüyü kullanın.")
    # Buraya genel stok durum grafikleri eklenebilir

elif page == "📊 Stok Giriş/Çıkış":
    st.run_islem(conn)

elif page == "↔️ Depo İçi Transfer":
    stok_islemleri.run_transfer(conn)

elif page == "🏗️ Üretim Hazırlık":
    uretim_hazirlik.run(conn)

elif page == "📝 Sayım Modülü":
    sayim_modulu.run(conn)

elif page == "✂️ BLOK KESİM": # <-- Yeni sayfa yönlendirmesi
    blok_kesim.run_blok_kesim(conn)
