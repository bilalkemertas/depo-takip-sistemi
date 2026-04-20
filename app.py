import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Sayfa Ayarları
st.set_page_config(page_title="Hızlı Depo v6", layout="centered")
st.title("📦 Profesyonel Akıllı Depo")

# Google Sheets Bağlantısı
conn = st.connection("gsheets", type=GSheetsConnection)

# Önbelleği temizleyen ve veriyi taze çeken fonksiyon
def taze_veri_getir():
    st.cache_data.clear() # Zorla temizleme
    df = conn.read(ttl=0) # TTL 0 ile anlık veri çekme
    if not df.empty:
        df.columns = df.columns.str.strip()
    return df

# Ürün koduna göre geçmişteki en geçerli ismi bulan fonksiyon (Arka Plan VLOOKUP)
def isim_dogrula(kod, ad, mevcut_df):
    kod_str = str(kod).strip().upper()
    ad_str = str(ad).strip().upper() if ad and str(ad).strip() != "" else ""
    
    # Eğer ad girilmemişse veya tireyse geçmişten bulalım
    if (not ad_str or ad_str == "-") and not mevcut_df.empty:
        gecmis = mevcut_df[mevcut_df['Malzeme Kodu'].astype(str).str.upper() == kod_str]
        if not gecmis.empty:
            # Gerçek bir isim içeren en son kaydı bul
            gecerli_isimler = gecmis[(gecmis['Malzeme Adı'].notna()) & (gecmis['Malzeme Adı'].astype(str) != "-")]
            if not gecerli_isimler.empty:
                return gecerli_isimler.iloc[-1]['Malzeme Adı']
    return ad_str if ad_str else "-"

def kayit_ekle(islem, adres, kod, ad, miktar):
    # Veriyi en taze haliyle çekip kontrol ediyoruz
    df_temp = taze_veri_getir()
    # Kayıt anında ismi otomatik tamamla/doğrula
    tam_ad = isim_dogrula(kod, ad, df_temp)
    
    yeni_kayit = pd.DataFrame({
        "Tarih": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "İşlem": [islem],
        "Adres": [str(adres).upper() if adres else "GENEL"],
        "Malzeme Kodu": [str(kod).upper()],
        "Malzeme Adı": [tam_ad.upper()],
        "Miktar": [miktar]
    })
    guncel_df = pd.concat([df_temp, yeni_kayit], ignore_index=True)
    conn.update(data=guncel_df)
    return tam_ad

# Uygulama başladığında veriyi session state'e al
if 'df' not in st.session_state:
    st.session_state.df = taze_veri_getir()

tab1, tab2, tab3 = st.tabs(["📥 Giriş", "📤 Çıkış", "🔍 Stok Sorgula"])

with tab1:
    st.subheader("Malzeme Girişi")
    g_adr = st.text_input("Adres:", value="GENEL", key="g_adr")
    g_kod = st.text_input("Ürün Kodu:", key="g_k")
    g_ad = st.text_input("Ürün Adı (Sistem otomatik tamamlar):", key="g_a")
    g_mik = st.number_input("Miktar:", min_value=1, step=1, key="g_m")
    
    if st.button("📥 Kaydı Tamamla", use_container_width=True):
        if g_kod:
            kaydedilen_ad = kayit_ekle("GİRİŞ", g_adr, g_kod, g_ad, g_mik)
            st.success(f"Kaydedildi: {g_kod} - {kaydedilen_ad}")
            st.session_state.df = taze_veri_getir() # İşlem sonrası taze veri
            st.rerun()
        else: st.error("Ürün kodu girmelisiniz!")

with tab2:
    st.subheader("Malzeme Çıkışı")
    c_adr = st.text_input("Adres:", value="GENEL", key="c_adr")
    c_kod = st.text_input("Ürün Kodu:", key="c_k")
    c_ad = st.text_input("Ürün Adı (Sistem otomatik tamamlar):", key="c_a")
    c_mik = st.number_input("Miktar:", min_value=1, step=1, key="c_m")
    
    if st.button("📤 Çıkışı Tamamla", use_container_width=True):
        if c_kod:
            kaydedilen_ad = kayit_ekle("ÇIKIŞ", c_adr, c_kod, c_ad, c_mik)
            st.success(f"Çıkış Yapıldı: {c_kod} - {kaydedilen_ad}")
            st.session_state.df = taze_veri_getir()
            st.rerun()
        else: st.error("Ürün kodu girmelisiniz!")

with tab3:
    # Başlık ve İstediğin Yenileme Butonu Yan Yana
    c1, c2 = st.columns([3, 1])
    with c1:
        st.subheader("🔍 Mevcut Stoklar")
    with c2:
        if st.button("🔄 Yenile"):
            st.session_state.df = taze_veri_getir()
            st.rerun()

    search = st.text_input("Ara (Kod, Ad veya Adres):")
    
    df_ana = st.session_state.df
    if not df_ana.empty:
        # Veriyi temizle ve sayıya çevir
        df_ana['Miktar'] = pd.to_numeric(df_ana['Miktar'], errors='coerce').fillna(0)
        df_ana['Net'] = df_ana.apply(lambda r: r['Miktar'] if str(r['İşlem']).upper() == 'GİRİŞ' else -r['Miktar'], axis=1)
        
        # --- PİVOT VE KONSOLİDASYON MANTIĞI ---
        # Her kodun en güncel geçerli ismini bul (Hafıza)
        valid_names = df_ana[df_ana['Malzeme Adı'] != "-"].sort_values('Tarih')
        isim_map = valid_names.groupby('Malzeme Kodu')['Malzeme Adı'].last().to_dict()
        
        # Tüm satırları bu isimle güncelle (İsimsizler isimlilerle birleşsin diye)
        df_ana['Malzeme Adı'] = df_ana['Malzeme Kodu'].map(isim_map).fillna(df_ana['Malzeme Adı'])
        
        # Gruplama yap (Aynı Adres + Kod + İsim olanları topla)
        stok = df_ana.groupby(['Adres', 'Malzeme Kodu', 'Malzeme Adı'])['Net'].sum().reset_index()
        stok = stok[stok['Net'] > 0]
        stok.columns = ["Adres", "Kod", "Ürün Adı", "Miktar"]

        if search:
            t = search.upper()
            mask = (stok['Adres'].str.upper().str.contains(t, na=False) | 
                    stok['Kod'].str.upper().str.contains(t, na=False) | 
                    stok['Ürün Adı'].str.upper().str.contains(t, na=False))
            stok = stok[mask]
        
        st.dataframe(stok, use_container_width=True, hide_index=True)
    else:
        st.info("Sistemde henüz hareket bulunmuyor.")
