import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Sayfa Ayarları
st.set_page_config(page_title="Adresli Depo", layout="centered")
st.title("📦 Akıllı Depo Sorgu Sistemi")

# Google Sheets Bağlantısı
conn = st.connection("gsheets", type=GSheetsConnection)

def veri_getir():
    df = conn.read() 
    if not df.empty:
        df.columns = df.columns.str.strip()
    return df

def kayit_ekle(islem, adres, malzeme_kodu, malzeme_adi, miktar):
    df = veri_getir()
    yeni_kayit = pd.DataFrame({
        "Tarih": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "İşlem": [islem],
        "Adres": [str(adres).upper()],
        "Malzeme Kodu": [str(malzeme_kodu).upper()],
        "Malzeme Adı": [str(malzeme_adi).upper()],
        "Miktar": [miktar]
    })
    guncel_df = pd.concat([df, yeni_kayit], ignore_index=True)
    conn.update(data=guncel_df)

# Sekmeler
tab1, tab2, tab3 = st.tabs(["📥 Giriş", "📤 Çıkış", "🔍 Stok Sorgula"])

with tab1:
    st.subheader("Malzeme Girişi")
    g_adres = st.text_input("Adres (Opsiyonel):", value="GENEL", key="g_adr")
    g_kod = st.text_input("Malzeme Kodu:", key="g_k")
    g_ad = st.text_input("Malzeme Adı:", key="g_a")
    g_mik = st.number_input("Miktar:", min_value=1, step=1, key="g_m")
    if st.button("Girişi Kaydet", use_container_width=True):
        if g_kod:
            kayit_ekle("GİRİŞ", g_adres, g_kod, g_ad, g_mik)
            st.success("Kayıt Başarılı!")
        else: st.error("Kod zorunludur!")

with tab2:
    st.subheader("Malzeme Çıkışı")
    c_adres = st.text_input("Adres:", value="GENEL", key="c_adr")
    c_kod = st.text_input("Malzeme Kodu:", key="c_k")
    c_ad = st.text_input("Malzeme Adı:", key="c_a")
    c_mik = st.number_input("Miktar:", min_value=1, step=1, key="c_m")
    if st.button("Çıkışı Kaydet", use_container_width=True):
        if c_kod:
            kayit_ekle("ÇIKIŞ", c_adres, c_kod, c_ad, c_mik)
            st.success("Çıkış Kaydedildi!")
        else: st.error("Kod zorunludur!")

with tab3:
    st.subheader("🔍 Akıllı Arama")
    # Arama kutusu - her şeyi buradan arayacağız
    search = st.text_input("Adres, Kod veya Ürün Adı Yazın:", placeholder="Örn: A-01, Rulman, 102...")
    
    if st.button("Sorgula", use_container_width=True) or search:
        df = veri_getir()
        if not df.empty:
            # Net stok hesabı
            df['Miktar'] = pd.to_numeric(df['Miktar'], errors='coerce').fillna(0)
            df['Net'] = df.apply(lambda r: r['Miktar'] if str(r['İşlem']).upper() == 'GİRİŞ' else -r['Miktar'], axis=1)
            
            stok = df.groupby(['Adres', 'Malzeme Kodu', 'Malzeme Adı'])['Net'].sum().reset_index()
            stok = stok[stok['Net'] > 0]
            
            if search:
                # Üç sütunda birden arama yapma mantığı
                term = search.upper()
                mask = (stok['Adres'].str.upper().str.contains(term, na=False) | 
                        stok['Malzeme Kodu'].str.upper().str.contains(term, na=False) | 
                        stok['Malzeme Adı'].str.upper().str.contains(term, na=False))
                stok = stok[mask]
            
            stok.columns = ["Adres", "Kod", "Ürün Adı", "Miktar"]
            if not stok.empty:
                st.dataframe(stok, use_container_width=True, hide_index=True)
            else:
                st.warning("Aranan kriterlere uygun stok bulunamadı.")
