import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Sayfa Ayarları
st.set_page_config(page_title="Akıllı Depo v3", layout="centered")
st.title("📦 Akıllı Depo Takip Sistemi")

# Google Sheets Bağlantısı
conn = st.connection("gsheets", type=GSheetsConnection)

# Veriyi getiren fonksiyon
def veri_getir():
    df = conn.read() 
    if not df.empty:
        df.columns = df.columns.str.strip()
    return df

# Kayıt ekleme fonksiyonu
def kayit_ekle(islem, adres, malzeme_kodu, malzeme_adi, miktar):
    df = veri_getir()
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

# Veritabanından ürün koduna göre isim bulan yardımcı fonksiyon (VLOOKUP Mantığı)
def urun_adi_bul(kod, mevcut_df):
    if kod and not mevcut_df.empty:
        kod_arama = str(kod).upper().strip()
        # En güncel ismi getirmek için listeyi tersten tarıyoruz
        match = mevcut_df[mevcut_df['Malzeme Kodu'].str.upper() == kod_arama]
        if not match.empty:
            return match.iloc[-1]['Malzeme Adı']
    return ""

# Verileri bir kez çekelim
df_ana = veri_getir()

# Sekmeler
tab1, tab2, tab3 = st.tabs(["📥 Giriş", "📤 Çıkış", "🔍 Stok Sorgula"])

with tab1:
    st.subheader("Malzeme Girişi")
    g_adr = st.text_input("Adres:", value="GENEL", key="g_adr")
    g_kod = st.text_input("Ürün Kodu:", key="g_k")
    
    # Otomatik Tamamlama Mantığı
    otomatik_ad = urun_adi_bul(g_kod, df_ana)
    g_ad = st.text_input("Ürün Adı:", value=otomatik_ad, help="Kod girildiğinde sistem otomatik getirir.", key="g_a")
    
    g_mik = st.number_input("Miktar:", min_value=1, step=1, key="g_m")
    
    if st.button("Girişi Kaydet", use_container_width=True):
        if g_kod or g_ad:
            kayit_ekle("GİRİŞ", g_adr, g_kod, g_ad, g_mik)
            st.success(f"Başarılı! Ürün: {g_ad if g_ad else g_kod}")
            st.rerun() # Sayfayı yenileyerek hafızayı günceller
        else:
            st.error("HATA: En az bir ürün bilgisi girilmeli!")

with tab2:
    st.subheader("Malzeme Çıkışı")
    c_adr = st.text_input("Adres:", value="GENEL", key="c_adr")
    c_kod = st.text_input("Ürün Kodu:", key="c_k")
    
    # Otomatik Tamamlama Mantığı
    otomatik_ad_c = urun_adi_bul(c_kod, df_ana)
    c_ad = st.text_input("Ürün Adı:", value=otomatik_ad_c, key="c_a")
    
    c_mik = st.number_input("Miktar:", min_value=1, step=1, key="c_m")
    
    if st.button("Çıkışı Kaydet", use_container_width=True):
        if c_kod or c_ad:
            kayit_ekle("ÇIKIŞ", c_adr, c_kod, c_ad, c_mik)
            st.success("Çıkış İşlemi Tamamlandı!")
            st.rerun()
        else:
            st.error("HATA: Ürün bilgisi eksik!")

with tab3:
    st.subheader("🔍 Stok Sorgula")
    search = st.text_input("Arama (Kod, Ad, Adres):")
    
    if search:
        if not df_ana.empty:
            df_ana['Miktar'] = pd.to_numeric(df_ana['Miktar'], errors='coerce').fillna(0)
            df_ana['Net'] = df_ana.apply(lambda r: r['Miktar'] if str(r['İşlem']).upper() == 'GİRİŞ' else -r['Miktar'], axis=1)
            
            stok = df_ana.groupby(['Adres', 'Malzeme Kodu', 'Malzeme Adı'])['Net'].sum().reset_index()
            stok = stok[stok['Net'] > 0]
            
            term = search.upper()
            mask = (stok['Adres'].str.upper().str.contains(term, na=False) | 
                    stok['Malzeme Kodu'].str.upper().str.contains(term, na=False) | 
                    stok['Malzeme Adı'].str.upper().str.contains(term, na=False))
            sonuc = stok[mask]
            
            if not sonuc.empty:
                st.dataframe(sonuc, use_container_width=True, hide_index=True)
            else:
                st.warning("Eşleşen ürün bulunamadı.")
