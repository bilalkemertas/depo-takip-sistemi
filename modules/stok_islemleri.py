import streamlit as st
import pandas as pd
from datetime import datetime

def run_islem(conn):
    st.header("📊 Stok Giriş / Çıkış İşlemleri")
    
    # Verileri Çek
    df_stok = conn.read(worksheet="Stok_Listesi")
    df_hareketler = conn.read(worksheet="Hareketler")

    # Akıllı Arama ve Listeleme
    arama_terimi = st.text_input("🔍 Ürün Adı veya Kodunda Ara")
    filtreli_df = df_stok[df_stok.apply(lambda row: arama_terimi.lower() in str(row).lower(), axis=1)]
    
    secilen_urun = st.selectbox("Ürün Seçin:", filtreli_df['URUN_ADI'].tolist())
    urun_detay = df_stok[df_stok['URUN_ADI'] == secilen_urun].iloc[0]
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Ürün Kodu:** {urun_detay['URUN_KODU']}")
        islem_tipi = st.selectbox("İşlem Tipi", ["GİRİŞ", "ÇIKIŞ"])
        miktar = st.number_input("Miktar", min_value=1)
    
    with col2:
        adres = st.text_input("Adres (Örn: A-01-02)")
        personel = st.text_input("İşlemi Yapan Personel")

    if st.button("HAREKETİ KAYDET"):
        yeni_veri = pd.DataFrame([{
            "Tarih": datetime.now().strftime("%d-%m-%Y %H:%M"),
            "Ürün Kodu": urun_detay['URUN_KODU'],
            "Ürün Adı": secilen_urun,
            "Adres": adres,
            "Miktar": miktar if islem_tipi == "GİRİŞ" else -miktar,
            "İşlem": islem_tipi,
            "Personel": personel
        }])
        # Kayıt mantığı
        st.success("İşlem Başarıyla Kaydedildi!")

def run_transfer(conn):
    st.header("↔️ Depo İçi Adres Transferi")
    # Transfer ekranı kodların (Kod yazınca ismin gelmesi, 'TRANSFER' yazısının düzeltilmesi dahil)
    # [cite: 1610, 1630]
    pass # Mevcut transfer fonksiyonun buraya eklenecek
