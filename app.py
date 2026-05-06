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

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Depo Kontrol v2.0", page_icon="📦", layout="wide")

if 'user' not in st.session_state: st.session_state.user = None

# --- LOGİN VE MENÜ ---
if st.session_state.user is None:
    st.title("🔐 Depo Giriş")
    with st.form("login"):
        u = st.text_input("Kullanıcı")
        p = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş"):
            if u in st.secrets["users"] and st.secrets["users"][u] == p:
                st.session_state.user = u
                st.rerun()
            else: st.error("Hatalı Giriş!")
else:
    menu = st.sidebar.radio("İşlem:", ["🏠 Ana Sayfa", "📊 Stok Giriş/Çıkış", "↔️ Depo İçi Transfer", "🏗️ Üretim Hazırlık", "📝 Sayım Modülü"])
    
    if st.sidebar.button("🚪 Çıkış"):
        st.session_state.user = None
        st.rerun()

    # --- MODÜL ÇAĞRILARI (Parametresiz) ---
    if menu == "🏠 Ana Sayfa":
        st.title("📦 Depo Kontrol Merkezi")
        st.success(f"Hoş geldin {st.session_state.user}")
    
    elif menu == "📊 Stok Giriş/Çıkış":
        stok_islemleri.run_islem()

    elif menu == "↔️ Depo İçi Transfer":
        stok_islemleri.run_transfer()

    elif menu == "🏗️ Üretim Hazırlık":
        uretim_hazirlik.run()

    elif menu == "📝 Sayım Modülü":
        sayim_modulu.run()
