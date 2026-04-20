import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Sayfa Ayarları
st.set_page_config(page_title="Hızlı Depo", layout="centered")
st.title("📦 Hızlı Depo Takip (V2)")

# Google Sheets Bağlantısı
conn = st.connection("gsheets", type=GSheetsConnection)

def veri_getir():
    df = conn.read() 
    if not df.empty:
        df.columns = df.columns.str.strip()
    return df

def kayit_ekle(islem, adres, malzeme_kodu, malzeme_adi, miktar):
    df = veri_getir()
    # Boş olan alanları "BİLİNMİYOR" yerine temiz birer tire (-) veya boşluk yapalım
    yeni_kayit = pd.DataFrame({
        "Tarih": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "İşlem": [islem],
        "Adres": [str(adres).upper() if adres else "GENEL"],
        "Malzeme Kodu": [str(malzeme_kodu).upper() if malzeme_kodu else "-"],
        "Malzeme Adı": [str(malzeme_adi).upper() if malzeme_adi else "-"],
        "Miktar": [miktar]
    })
    guncel_df = pd.concat([df, yeni_kayit], ignore_index=True)
    conn.update(data=guncel_df)

# Sekmeler
tab1, tab2, tab3 = st.tabs(["📥 Hızlı Giriş", "📤 Hızlı Çıkış", "🔍 Stok Sorgula"])

with tab1:
    st.subheader("Malzeme Girişi")
    g_adr = st.text_input("Adres:", value="GENEL", key="g_adr")
    g_kod = st.text_input("Ürün Kodu (Veya İsim):", key="g_k")
    g_ad = st.text_input("Ürün Adı (Veya Kod):", key="g_a")
    g_mik = st.number_input("Miktar:", min_value=1, step=1, key="g_m")
    
    # MANTIK: Kod VEYA Ad doluysa kaydet
    if st.button("Girişi Tamamla", use_container_width=True):
        if g_kod or g_ad:
            kayit_ekle("GİRİŞ", g_adr, g_kod, g_ad, g_mik)
            st.success("İşlem Başarıyla Kaydedildi!")
        else:
            st.error("HATA: Lütfen Ürün Kodu veya Ürün Adı alanlarından en az birini doldurun!")

with tab2:
    st.subheader("Malzeme Çıkışı")
    c_adr = st.text_input("Adres:", value="GENEL", key="c_adr")
    c_kod = st.text_input("Ürün Kodu:", key="c_k")
    c_ad = st.text_input("Ürün Adı:", key="c_a")
    c_mik = st.number_input("Miktar:", min_value=1, step=1, key="c_m")
    
    if st.button("Çıkışı Tamamla", use_container_width=True):
        if c_kod or c_ad:
            kayit_ekle("ÇIKIŞ", c_adr, c_kod, c_ad, c_mik)
            st.success("Çıkış İşlemi Tamamlandı!")
        else:
            st.error("HATA: Çıkış yapmak için ürün bilgisi girmelisiniz!")

with tab3:
    st.subheader("🔍 Stok Sorgula")
    search = st.text_input("Herhangi bir şey yazın (Kod, Ad, Adres):")
    
    if search:
        df = veri_getir()
        if not df.empty:
            df['Miktar'] = pd.to_numeric(df['Miktar'], errors='coerce').fillna(0)
            df['Net'] = df.apply(lambda r: r['Miktar'] if str(r['İşlem']).upper() == 'GİRİŞ' else -r['Miktar'], axis=1)
            
            stok = df.groupby(['Adres', 'Malzeme Kodu', 'Malzeme Adı'])['Net'].sum().reset_index()
            stok = stok[stok['Net'] > 0]
            
            term = search.upper()
            mask = (stok['Adres'].str.upper().str.contains(term, na=False) | 
                    stok['Malzeme Kodu'].str.upper().str.contains(term, na=False) | 
                    stok['Malzeme Adı'].str.upper().str.contains(term, na=False))
            sonuc = stok[mask]
            
            if not sonuc.empty:
                st.dataframe(sonuc[["Adres", "Malzeme Kodu", "Malzeme Adı", "Net"]], use_container_width=True, hide_index=True)
            else:
                st.warning("Eşleşen ürün bulunamadı.")
