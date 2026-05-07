import streamlit as st
import sqlite3
import pandas as pd
from modules import stok_islemleri, uretim_hazirlik, sayim_modulu, blok_kesim, teslim_alma

# --- VERİTABANI BAŞLATICI ---
def init_db():
    conn = sqlite3.connect('depo.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS Urun_Listesi (kod TEXT PRIMARY KEY, isim TEXT, BIRIM TEXT, ADRES TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Stok (Adres TEXT, Kod TEXT, İsim TEXT, Birim TEXT, Miktar REAL, Durum TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Hareketler (Tarih TEXT, İşlem TEXT, Kod TEXT, İsim TEXT, Adres TEXT, Miktar REAL, Personel TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Is_Emirleri ("İş Emri" TEXT, "Ürün Kodu" TEXT, "Mamül Adı" TEXT, "Stok Kodu" TEXT, "Stok Adı" TEXT, "İhtiyaç Miktarı" REAL, "Hazırlanan Adet" REAL, Birim TEXT)''')
    # Mal Kabul işlemleri için yeni tablo (İrsaliye ve Sipariş detaylarını tutmak için)
    cursor.execute('''CREATE TABLE IF NOT EXISTS Mal_Kabul (Tarih TEXT, Irsaliye_No TEXT, Siparis_No TEXT, Tedarikci TEXT, Kod TEXT, Isim TEXT, Miktar REAL, Adres TEXT, Personel TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- SAYFA AYARLARI VE KURUMSAL TEMA ---
st.set_page_config(page_title="WMS Enterprise", page_icon="🏢", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        /* Kurumsal ERP (SAP Fiori / Oracle) Hissiyatı İçin CSS */
        .block-container { padding: 1rem !important; max-width: 800px; margin: 0 auto; }
        header { visibility: hidden; }
        footer { visibility: hidden; }
        
        /* Genel Font ve Arka Plan */
        html, body, [class*="css"] {
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f4f5f7;
        }
        
        /* Ana Menü Karo (Tile) Tasarımı */
        button[kind="primary"] {
            width: 100%;
            height: 110px;
            border-radius: 10px;
            background-color: #ffffff;
            color: #0b3c5d;
            border: 1px solid #dcdcdc;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            font-size: 16px;
            font-weight: bold;
            transition: all 0.2s ease;
            white-space: pre-wrap;
        }
        button[kind="primary"]:hover {
            border-color: #328cc1;
            box-shadow: 0 6px 12px rgba(0,0,0,0.1);
            transform: translateY(-2px);
            color: #328cc1;
        }
        button[kind="primary"]:active {
            transform: translateY(0);
        }
        
        /* Kurumsal Header */
        .erp-header {
            background-color: #0b3c5d;
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .erp-title { margin: 0; font-size: 20px; font-weight: 600; letter-spacing: 1px; }
        .erp-user { margin: 0; font-size: 14px; opacity: 0.9; }
        
        /* Çıkış Butonu Özel Ayarı */
        .logout-box {
            display: flex;
            justify-content: flex-end;
            align-items: center;
            height: 100%;
        }
    </style>
""", unsafe_allow_html=True)

# --- STATE YÖNETİMİ ---
if 'user' not in st.session_state: st.session_state.user = None
if 'current_module' not in st.session_state: st.session_state.current_module = "home"

# --- LOGİN EKRANI ---
if st.session_state.user is None:
    st.markdown("<div style='text-align: center; margin-top: 40px; margin-bottom: 20px;'><h2 style='color: #0b3c5d;'>WMS Enterprise</h2><p style='color: #666;'>Sistem Girişi</p></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            u = st.text_input("Kullanıcı ID")
            p = st.text_input("Şifre", type="password")
            if st.form_submit_button("OTURUM AÇ", use_container_width=True):
                if u in st.secrets["users"] and st.secrets["users"][u] == p:
                    st.session_state.user = u
                    st.rerun()
                else: 
                    st.error("Yetki Reddedildi.")
else:
    # --- KURUMSAL HEADER ---
    c_title, c_user, c_logout = st.columns([5, 3, 1])
    with c_title:
        st.markdown("<h3 style='color: #0b3c5d; margin-top: 5px;'>🏢 WMS Enterprise</h3>", unsafe_allow_html=True)
    with c_user:
        st.markdown(f"<p style='text-align: right; margin-top: 15px; color: #666; font-weight: 500;'>👤 {st.session_state.user}</p>", unsafe_allow_html=True)
    with c_logout:
        st.markdown("<div class='logout-box'>", unsafe_allow_html=True)
        if st.button("⏻", help="Oturumu Kapat"):
            st.session_state.user = None
            st.session_state.current_module = "home"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='margin-top: 5px; margin-bottom: 20px;'>", unsafe_allow_html=True)

    # --- YÖNLENDİRME MOTORU (DASHBOARD) ---
    if st.session_state.current_module == "home":
        
        c1, c2 = st.columns(2)
        
        with c1:
            if st.button("📦\nStok İşlemleri", type="primary"):
                st.session_state.current_module = "stok"
                st.rerun()
            if st.button("🏗️\nÜretim Hazırlık", type="primary"):
                st.session_state.current_module = "uretim"
                st.rerun()
            if st.button("✂️\nBlok Kesim", type="primary"):
                st.session_state.current_module = "blok"
                st.rerun()
             if st.button("✂️\nBBağlantı Test", type="primary"):
                st.session_state.current_module = "test"
                st.rerun()
                
        with c2:
            # Depo Transfer yerine Teslim Alma eklendi
            if st.button("📥\nTeslim Alma", type="primary"):
                st.session_state.current_module = "teslim"
                st.rerun()
            if st.button("📋\nSayım Modülü", type="primary"):
                st.session_state.current_module = "sayim"
                st.rerun()

    else:
        # Seçili Modülü Çalıştır
        if st.session_state.current_module == "stok":
            stok_islemleri.run_islem()
        elif st.session_state.current_module == "teslim":
            teslim_alma.run()
        elif st.session_state.current_module == "uretim":
            uretim_hazirlik.run()
        elif st.session_state.current_module == "sayim":
            sayim_modulu.run()
        elif st.session_state.current_module == "blok":
            blok_kesim.run()
            
        # Alt Kısımda Küçük Ana Ekran Butonu
        st.markdown("<br><hr style='margin-bottom: 10px;'>", unsafe_allow_html=True)
        if st.button("⬅️ Ana Ekran"):
            st.session_state.current_module = "home"
            st.rerun()
