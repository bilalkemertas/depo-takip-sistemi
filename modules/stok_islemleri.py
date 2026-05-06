import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

def get_db_connection():
    """SQLite veritabanı bağlantısını kurar."""
    conn = sqlite3.connect('depo.db', check_same_thread=False)
    return conn

def run_islem():
    st.subheader("📊 Stok Giriş / Çıkış Paneli")
    db = get_db_connection()
    
    try:
        # SQLite'dan veri çekme mantığı
        df_stok = pd.read_sql("SELECT * FROM Urun_Listesi", db)
        df_hareketler = pd.read_sql("SELECT * FROM Hareketler", db)
        
        search = st.text_input("🔍 Ürün Ara (Ad/Kod)", "", key="stok_search_sql")
        
        if search:
            mask = df_stok['isim'].astype(str).str.contains(search, case=False, na=False) | \
                   df_stok['kod'].astype(str).str.contains(search, case=False, na=False)
            filtered = df_stok[mask]
        else:
            filtered = df_stok

        if not filtered.empty:
            options = filtered.apply(lambda x: f"{x['kod']} | {x['isim']}", axis=1).tolist()
            selected_option = st.selectbox("Ürünü Onaylayın:", options)
            
            sel_kodu = selected_option.split(" | ")[0]
            urun_bilgi = df_stok[df_stok['kod'] == sel_kodu].iloc[0]
            
            # Canlı stok miktarını 'Stok' tablosundan çek
            df_canli = pd.read_sql(f"SELECT SUM(Miktar) as toplam FROM Stok WHERE Kod = '{sel_kodu}'", db)
            mevcut_miktar = df_canli['toplam'].iloc[0] if not df_canli.empty else 0
            st.info(f"📦 Mevcut Toplam Stok: {mevcut_miktar}")
            
            with st.form("islem_form_sql"):
                islem = st.selectbox("İşlem Türü", ["GİRİŞ", "ÇIKIŞ"])
                miktar = st.number_input("İşlem Miktarı", min_value=0.1, step=1.0)
                adres = st.text_input("Depo Adresi", value=str(urun_bilgi.get('ADRES', '')))
                
                if st.form_submit_button("KAYDET"):
                    personel = st.session_state.get('user', 'Patron')
                    final_miktar = miktar if islem == "GİRİŞ" else -miktar
                    
                    # SQLite'a Kayıt
                    cursor = db.cursor()
                    cursor.execute("""
                        INSERT INTO Hareketler (Tarih, İşlem, Kod, İsim, Adres, Miktar, Personel)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), islem, sel_kodu, urun_bilgi['isim'], adres, final_miktar, personel))
                    db.commit()
                    st.success("✅ Kayıt SQLite'a işlendi!")
                    st.rerun()
    except Exception as e:
        st.error(f"Veri işleme hatası: {e}")
    finally:
        db.close()

def run_transfer():
    st.subheader("↔️ Depo İçi Transfer (Adres Değişimi)")
    db = get_db_connection()
    
    try:
        # SQLite sorgusuyla stok tablosunu al
        df_stok = pd.read_sql("SELECT * FROM Stok", db)
        
        search_transfer = st.text_input("🔍 Transfer Edilecek Ürünü Ara", key="trans_search_sql")
        
        if search_transfer:
            mask = df_stok['İsim'].astype(str).str.contains(search_transfer, case=False, na=False) | \
                   df_stok['Kod'].astype(str).str.contains(search_transfer, case=False, na=False)
            filtered_df = df_stok[mask]
        else:
            filtered_df = df_stok

        if not filtered_df.empty:
            options = filtered_df.apply(lambda x: f"{x['Kod']} | {x['İsim']} | {x['Adres']}", axis=1).tolist()
            selected_option = st.selectbox("Ürün Seçin:", options, key="trans_sel_sql")
            
            sel_kodu = selected_option.split(" | ")[0]
            eski_adres = selected_option.split(" | ")[2]
            urun_bilgi = df_stok[(df_stok['Kod'] == sel_kodu) & (df_stok['Adres'] == eski_adres)].iloc[0]
            
            with st.form("transfer_form_sql"):
                yeni_adres = st.text_input("Hedef (Yeni) Adres")
                transfer_miktar = st.number_input("Miktar", min_value=0.1, max_value=float(urun_bilgi['Miktar']))
                
                if st.form_submit_button("TRANSFERİ TAMAMLA"):
                    tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    personel = st.session_state.get('user', 'Patron')
                    
                    cursor = db.cursor()
                    # Çıkış ve Giriş hareketlerini ekle
                    cursor.execute("INSERT INTO Hareketler (Tarih, İşlem, Kod, İsim, Adres, Miktar, Personel) VALUES (?,?,?,?,?,?,?)",
                                 (tarih, "TRANSFER ÇIKIŞ", sel_kodu, urun_bilgi['İsim'], eski_adres, -transfer_miktar, personel))
                    cursor.execute("INSERT INTO Hareketler (Tarih, İşlem, Kod, İsim, Adres, Miktar, Personel) VALUES (?,?,?,?,?,?,?)",
                                 (tarih, "TRANSFER GİRİŞ", sel_kodu, urun_bilgi['İsim'], yeni_adres, transfer_miktar, personel))
                    db.commit()
                    st.success(f"✅ {sel_kodu} başarıyla {yeni_adres} adresine taşındı.")
                    st.rerun()
    except Exception as e:
        st.error(f"Transfer hatası: {e}")
    finally:
        db.close()
