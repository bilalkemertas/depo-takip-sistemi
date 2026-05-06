import streamlit as st
import sqlite3
import pandas as pd
from modules import stok_islemleri, uretim_hazirlik, sayim_modulu

# --- SAYFA AYARLARI ---
st.set_page_config(
    page_title="Depo Kontrol Merkezi v2.0",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- OTURUM YÖNETİMİ ---
# Kullanıcı giriş yapmamışsa login ekranına yönlendir
if 'user' not in st.session_state:
    st.session_state.user = None

if 'page' not in st.session_state:
    st.session_state.page = "Ana Sayfa"

# --- LOGİN SİSTEMİ (Basit) ---
def login():
    st.title("🔐 Depo Giriş")
    with st.form("login_form"):
        username = st.text_input("Kullanıcı Adı")
        password = st.text_input("Şifre", type="password")
        submit = st.form_submit_button("Giriş Yap")
        
        if submit:
            # Secrets içindeki kullanıcı bilgilerini kontrol et
            if username in st.secrets["users"] and st.secrets["users"][username] == password:
                st.session_state.user = username
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre!")

# --- ANA UYGULAMA ---
if st.session_state.user is None:
    login()
else:
    # --- YAN MENÜ (SIDEBAR) ---
    st.sidebar.title(f"👤 Merhaba, {st.session_state.user}")
    st.sidebar.markdown("---")
    
    menu = st.sidebar.radio(
        "İşlem Seçiniz:",
        [
            "🏠 Ana Sayfa", 
            "📊 Stok Giriş/Çıkış", 
            "↔️ Depo İçi Transfer", 
            "🏗️ Üretim Hazırlık", 
            "📝 Sayım Modülü"
        ]
    )
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Çıkış Yap"):
        st.session_state.user = None
        st.rerun()

    # --- MODÜL YÖNLENDİRMELERİ ---
    # SQLite yapısına geçtiğimiz için artık 'conn' parametresi göndermiyoruz
    
    if menu == "🏠 Ana Sayfa":
        st.title("📦 Depo Kontrol Merkezi")
        st.info(f"Hoş geldin Patron! Bugün depo operasyonlarını yönetmeye hazırsın.")
        
        # Hızlı istatistikler buraya eklenebilir
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Aktif Oturum", st.session_state.get('aktif_sayim_adi', 'Yok'))
        with col2:
            st.write("Depo doluluk oranı ve kritik stok uyarıları yakında burada olacak.")

    elif menu == "📊 Stok Giriş/Çıkış":
        stok_islemleri.run_islem()

    elif menu == "↔️ Depo İçi Transfer":
        stok_islemleri.run_transfer()

    elif menu == "🏗️ Üretim Hazırlık":
        uretim_hazirlik.run()

    elif menu == "📝 Sayım Modülü":
        sayim_modulu.run()

# --- ALT BİLGİ ---
st.sidebar.caption("v2.0.1 - SQLite Edition")
