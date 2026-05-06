import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- VERİTABANI BAĞLANTISI ---
def get_db_connection():
    return sqlite3.connect('depo.db', check_same_thread=False)

def get_katalog():
    db = get_db_connection()
    try:
        df = pd.read_sql("SELECT kod, isim FROM Urun_Listesi", db)
        if not df.empty:
            return df.apply(lambda x: f"{x['kod']} | {x['isim']}", axis=1).tolist()
        return []
    except:
        return []
    finally:
        db.close()

# --- ÜRÜN SEÇİLİNCE KODU OTOMATİK DOLDUR ---
def teslim_urun_secildi():
    sec = st.session_state.get("teslim_sec")
    if sec and sec != "+ MANUEL GİRİŞ":
        st.session_state.teslim_kod = sec.split(" | ")[0]

def run():
    st.subheader("📥 Mal Kabul / Teslim Alma Formu")
    st.markdown("Tedarikçi üzerinden depoya giren ürünlerin kayıt ekranı.")
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            tedarikci = st.text_input("🏢 Tedarikçi Firma:", placeholder="Örn: ABC Lojistik")
            siparis_no = st.text_input("📄 Satınalma Sipariş (PO) No:", placeholder="Örn: PO-20260515")
        with col2:
            irsaliye_no = st.text_input("📝 İrsaliye Numarası:", placeholder="Örn: IRS-98765")
            tarih_secim = st.date_input("📅 Teslim Tarihi:")

        st.markdown("---")
        
        katalog = get_katalog()
        sec = st.selectbox(
            "🔍 Kabul Edilen Ürün:", 
            ["+ MANUEL GİRİŞ"] + katalog, 
            key="teslim_sec",
            on_change=teslim_urun_secildi
        )
        
        c3, c4 = st.columns(2)
        with c3:
            s_kod = st.text_input("📦 Malzeme Kodu:", key="teslim_kod").upper().strip()
            s_mik = st.number_input("Miktar:", min_value=0.0, step=1.0)
        with c4:
            s_adr = st.text_input("📍 Yerleştirilecek Hedef Adres:").upper().strip()
            s_dur = st.selectbox("Kalite Durumu:", ["Kullanılabilir", "Karantina (Test Bekliyor)", "Hasarlı Red"])

        if st.button("📥 SİSTEME KABUL ET", use_container_width=True, type="primary"):
            if not s_kod or s_mik <= 0 or not irsaliye_no or not tedarikci:
                st.error("Lütfen Tedarikçi, İrsaliye No, Ürün Kodu ve Miktar alanlarını eksiksiz doldurun!")
            else:
                db = get_db_connection()
                try:
                    df_stok = pd.read_sql("SELECT * FROM Stok", db)
                    df_hareketler = pd.read_sql("SELECT * FROM Hareketler", db)
                    
                    islem_zamani = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    personel = st.session_state.user if 'user' in st.session_state else "Sistem"
                    urun_isim = sec.split(" | ")[1] if sec != "+ MANUEL GİRİŞ" and len(sec.split(" | ")) > 1 else "MANUEL KABUL"
                    
                    # 1. Mal Kabul Tablosuna Özel Detaylı Kayıt
                    cursor = db.cursor()
                    cursor.execute("""
                        INSERT INTO Mal_Kabul (Tarih, Irsaliye_No, Siparis_No, Tedarikci, Kod, Isim, Miktar, Adres, Personel)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (islem_zamani, irsaliye_no, siparis_no, tedarikci, s_kod, urun_isim, s_mik, s_adr, personel))

                    # 2. Genel Hareketler Tablosuna Kayıt (Stok Ekstresi İçin)
                    yeni_hareket = {
                        "Tarih": islem_zamani, "İşlem": f"MAL KABUL ({irsaliye_no})", "Kod": s_kod,
                        "İsim": urun_isim, "Adres": s_adr, "Miktar": s_mik, "Personel": personel
                    }
                    df_hareketler = pd.concat([df_hareketler, pd.DataFrame([yeni_hareket])], ignore_index=True)
                    df_hareketler.to_sql("Hareketler", db, if_exists="replace", index=False)

                    # 3. Canlı Stok Tablosunu Güncelleme
                    mask = (df_stok['Kod'] == s_kod) & (df_stok['Adres'] == s_adr)
                    if mask.any():
                        df_stok.loc[mask, 'Miktar'] += s_mik
                    else:
                        new_row = pd.DataFrame([{"Adres": s_adr, "Kod": s_kod, "İsim": urun_isim, "Birim": "-", "Miktar": s_mik, "Durum": s_dur}])
                        df_stok = pd.concat([df_stok, new_row], ignore_index=True)
                    
                    df_stok.to_sql("Stok", db, if_exists="replace", index=False)
                    
                    db.commit()
                    st.success(f"✅ {s_kod} kodlu ürün (İrsaliye: {irsaliye_no}) başarıyla depoya kabul edildi!")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"Veritabanı kayıt hatası: {e}")
                finally:
                    db.close()
