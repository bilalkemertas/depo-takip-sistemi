import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Sayfa Ayarları
st.set_page_config(page_title="Adresli Depo", layout="centered")
st.title("📦 Bulut Adresli Depo Takip")

# Google Sheets Bağlantısını Kurma
conn = st.connection("gsheets", type=GSheetsConnection)

# Veriyi getiren fonksiyon
def veri_getir():
    # 'Depo_Veritabani' tablosunu okur
    df = conn.read() 
    # Başlıklardaki olası gizli boşlukları otomatik temizler (Hayat kurtarır!)
    if not df.empty:
        df.columns = df.columns.str.strip()
    return df

# Veriyi kaydeden fonksiyon
def kayit_ekle(islem, adres, malzeme_kodu, malzeme_adi, miktar):
    df = veri_getir()
    yeni_kayit = pd.DataFrame({
        "Tarih": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "İşlem": [islem],
        "Adres": [adres.upper()],
        "Malzeme Kodu": [malzeme_kodu.upper()],
        "Malzeme Adı": [malzeme_adi.upper()],
        "Miktar": [miktar]
    })
    
    # Eski veriyle yeni veriyi birleştirip yazar
    guncel_df = pd.concat([df, yeni_kayit], ignore_index=True)
    conn.update(data=guncel_df)

# Sekmeler (Giriş, Çıkış, Stok)
tab1, tab2, tab3 = st.tabs(["📥 Giriş", "📤 Çıkış", "📊 Stok Raporu"])

with tab1:
    st.subheader("Depoya Malzeme Ekle")
    g_adres = st.text_input("Adres (Giriş):", key="g_adres")
    g_malzeme_kodu = st.text_input("Malzeme Kodu:", key="g_malz_kod")
    g_malzeme_adi = st.text_input("Malzeme Adı:", key="g_malz_adi")
    g_miktar = st.number_input("Miktar:", min_value=1, step=1, key="g_miktar")
    
    if st.button("Girişi Kaydet", use_container_width=True):
        if g_adres and g_malzeme_kodu:
            kayit_ekle("GİRİŞ", g_adres, g_malzeme_kodu, g_malzeme_adi, g_miktar)
            st.success(f"{g_miktar} adet {g_malzeme_kodu}, {g_adres} adresine eklendi!")
        else:
            st.warning("Lütfen Adres ve Malzeme Kodu alanlarını doldurun.")

with tab2:
    st.subheader("Depodan Malzeme Çıkar")
    c_adres = st.text_input("Adres (Çıkış):", key="c_adres")
    c_malzeme_kodu = st.text_input("Malzeme Kodu:", key="c_malz_kod")
    c_malzeme_adi = st.text_input("Malzeme Adı:", key="c_malz_adi")
    c_miktar = st.number_input("Miktar:", min_value=1, step=1, key="c_miktar")
    
    if st.button("Çıkışı Kaydet", use_container_width=True):
        if c_adres and c_malzeme_kodu:
            kayit_ekle("ÇIKIŞ", c_adres, c_malzeme_kodu, c_malzeme_adi, c_miktar)
            st.success(f"{c_miktar} adet {c_malzeme_kodu}, {c_adres} adresinden düşüldü!")
        else:
            st.warning("Lütfen Adres ve Malzeme Kodu alanlarını doldurun.")

with tab3:
    st.subheader("Mevcut Stok Raporu")
    if st.button("Stokları Yenile", use_container_width=True):
        df = veri_getir()
        if not df.empty and len(df) > 0:
            
            # Gerekli başlıkların kontrolü
            gerekli_sutunlar = ['İşlem', 'Adres', 'Malzeme Kodu', 'Malzeme Adı', 'Miktar']
            eksik = [col for col in gerekli_sutunlar if col not in df.columns]
            
            if eksik:
                st.error(f"Google Sheets'te şu başlıklar eksik: {', '.join(eksik)}")
            else:
                # Sayısal olmayan miktarları 0 yap ve net stoğu hesapla
                df['Miktar'] = pd.to_numeric(df['Miktar'], errors='coerce').fillna(0)
                df['Net_Miktar'] = df.apply(lambda row: row['Miktar'] if str(row['İşlem']).strip().upper() == 'GİRİŞ' else -row['Miktar'], axis=1)
                
                # Yeni başlıklara göre gruplama (Özet Tablo)
                stok_ozet = df.groupby(['Adres', 'Malzeme Kodu', 'Malzeme Adı'])['Net_Miktar'].sum().reset_index()
                
                # Stoğu 0'dan büyük olanları filtrele
                guncel_stok = stok_ozet[stok_ozet['Net_Miktar'] > 0].sort_values(by="Adres")
                guncel_stok.columns = ["Adres", "Malzeme Kodu", "Malzeme Adı", "Mevcut Miktar"]
                
                st.dataframe(guncel_stok, use_container_width=True)
        else:
            st.info("Sistemde henüz hareket yok veya veriler okunamıyor.")
