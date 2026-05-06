import streamlit as st
import sqlite3
import pandas as pd
from modules import stok_islemleri, uretim_hazirlik, sayim_modulu

# --- VERİTABANI BAŞLATICI ---
def init_db():
    conn = sqlite3.connect('depo.db')
    cursor = conn.cursor()
    # Urun_Listesi Tablosu
    cursor.execute('''CREATE TABLE IF NOT EXISTS Urun_Listesi 
                      (kod TEXT PRIMARY KEY, isim TEXT, BIRIM TEXT, ADRES TEXT)''')
    # Stok Tablosu
    cursor.execute('''CREATE TABLE IF NOT EXISTS Stok 
                      (Adres TEXT, Kod TEXT, İsim TEXT, Birim TEXT, Miktar REAL, Durum TEXT)''')
    # Hareketler Tablosu
    cursor.execute('''CREATE TABLE IF NOT EXISTS Hareketler 
                      (Tarih TEXT, İşlem TEXT, Kod TEXT, İsim TEXT, Adres TEXT, Miktar REAL, Personel TEXT)''')
    # İş Emirleri Tablosu
    cursor.execute('''CREATE TABLE IF NOT EXISTS Is_Emirleri 
                      ("İş Emri" TEXT, "Ürün Kodu" TEXT, "Mamül Adı" TEXT, "Stok Kodu" TEXT, "Stok Adı" TEXT, "İhtiyaç Miktarı" REAL, "Hazırlanan Adet" REAL, Birim TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- SAYFA AYARLARI VE CSS TEMA ---
st.set_page_config(page_title="Depo Kontrol v2.0", page_icon="📦", layout="wide", initial_sidebar_state="collapsed")

# Arayüzü profesyonelleştiren ve terminal ekranına uyduran CSS
st.markdown("""
    <style>
        /* Terminal ekranı için kenar boşluklarını daralt */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
        /* Genel font ayarı */
        html, body, [class*="css"] {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        /* Dokunmatik ekran için butonları büyüt ve köşeleri yuvarlat */
        div.stButton > button {
            border-radius: 8px;
            font-weight: 600;
            height: 3rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: all 0.2s ease;
        }
        div.stButton > button:active {
            transform: scale(0.98);
        }
        /* Varsayılan header ve footer gizle */
        header {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

if 'user' not in st.session_state: st.session_state.user = None

# --- LOGİN VE MENÜ ---
if st.session_state.user is None:
    st.markdown("<h3 style='text-align: center;'>🔐 Depo Giriş</h3>", unsafe_allow_html=True)
    with st.form("login"):
        u = st.text_input("Kullanıcı")
        p = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş Yap", use_container_width=True):
            if u in st.secrets["users"] and st.secrets["users"][u] == p:
                st.session_state.user = u
                st.rerun()
            else: 
                st.error("Hatalı Giriş!")
else:
    # --- EL TERMİNALİ İÇİN ÜST MENÜ ---
    col1, col2 = st.columns([3, 1])
    with col1:
        menu = st.selectbox("Modül Seçiniz:", ["🏠 Ana Sayfa", "📊 Stok Giriş/Çıkış", "↔️ Depo İçi Transfer", "🏗️ Üretim Hazırlık", "📝 Sayım Modülü"], label_visibility="collapsed")
    with col2:
        if st.button("🚪 Çıkış", use_container_width=True):
            st.session_state.user = None
            st.rerun()

    st.markdown("---")

    # --- MODÜL ÇAĞRILARI (Parametresiz) ---
    if menu == "🏠 Ana Sayfa":
        st.markdown("#### 📦 Depo Kontrol Merkezi")
        st.success(f"Hoş geldin, {st.session_state.user}")
        st.info("İşlem yapmak için üstteki menüyü kullanabilirsiniz.")
    
    elif menu == "📊 Stok Giriş/Çıkış":
        stok_islemleri.run_islem()

    elif menu == "↔️ Depo İçi Transfer":
        stok_islemleri.run_transfer()

    elif menu == "🏗️ Üretim Hazırlık":
        uretim_hazirlik.run()

    elif menu == "📝 Sayım Modülü":
        sayim_modulu.run()
