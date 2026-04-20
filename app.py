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
    # 'Depo_Veritabani' tablosundaki verileri okur
    df = conn.read() 
    return df

# Veriyi kaydeden fonksiyon
def kayit_ekle(islem, adres, malzeme, adet):
    df = veri_getir()
    yeni_kayit = pd.DataFrame({
        "Tarih": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "İşlem": [islem],
        "Adres": [adres.upper()],
        "Malzeme": [malzeme.upper()],
        "Adet": [adet]
    })
    
    # Eski veriyle yeni veriyi birleştirip Google Sheets'e yazar
    guncel_df = pd.concat([df, yeni_kayit], ignore_index=True)
    conn.update(data=guncel_df)

# Sekmeler (Giriş, Çıkış, Stok)
tab1, tab2, tab3 = st.tabs(["📥 Malzeme Girişi", "📤 Malzeme Çıkışı", "📊 Stok Durumu"])

with tab1:
    st.subheader("Depoya Malzeme Ekle")
    g_adres = st.text_input("Adres Barkodu (Giriş):", key="g_adres")
    g_malzeme = st.text_input("Malzeme Barkodu (Giriş):", key="g_malz")
    g_adet = st.number_input("Adet:", min_value=1, step=1, key="g_adet")
    
    if st.button("Girişi Kaydet", use_container_width=True):
        if g_adres and g_malzeme:
            kayit_ekle("GİRİŞ", g_adres, g_malzeme, g_adet)
            st.success(f"{g_adet} adet {g_malzeme}, {g_adres} adresine eklendi!")
        else:
            st.warning("Lütfen adres ve malzeme alanlarını doldurun.")

with tab2:
    st.subheader("Depodan Malzeme Çıkar")
    c_adres = st.text_input("Adres Barkodu (Çıkış):", key="c_adres")
    c_malzeme = st.text_input("Malzeme Barkodu (Çıkış):", key="c_malz")
    c_adet = st.number_input("Adet:", min_value=1, step=1, key="c_adet")
    
    if st.button("Çıkışı Kaydet", use_container_width=True):
        if c_adres and c_malzeme:
            kayit_ekle("ÇIKIŞ", c_adres, c_malzeme, c_adet)
            st.success(f"{c_adet} adet {c_malzeme}, {c_adres} adresinden düşüldü!")
        else:
            st.warning("Lütfen adres ve malzeme alanlarını doldurun.")

with tab3:
    st.subheader("Mevcut Stok Raporu")
    if st.button("Stokları Yenile", use_container_width=True):
        df = veri_getir()
        if not df.empty and len(df) > 0:
            # İşlem tipine göre net stoğu hesaplama
            df['Net_Adet'] = df.apply(lambda row: row['Adet'] if row['İşlem'] == 'GİRİŞ' else -row['Adet'], axis=1)
            
            # Adres ve Malzemeye göre özetleme
            stok_ozet = df.groupby(['Adres', 'Malzeme'])['Net_Adet'].sum().reset_index()
            guncel_stok = stok_ozet[stok_ozet['Net_Adet'] > 0].sort_values(by="Adres")
            guncel_stok.columns = ["Adres", "Malzeme", "Mevcut Miktar"]
            
            st.dataframe(guncel_stok, use_container_width=True)
        else:
            st.info("Henüz sistemde hareket bulunmuyor.")
