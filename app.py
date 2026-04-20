import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Sayfa Ayarları
st.set_page_config(page_title="Akıllı Depo v4", layout="centered")
st.title("📦 Profesyonel Depo Takip Sistemi")

# Google Sheets Bağlantısı
conn = st.connection("gsheets", type=GSheetsConnection)

def veri_getir():
    df = conn.read() 
    if not df.empty:
        df.columns = df.columns.str.strip()
    return df

# Ürün koduna göre en güncel ismi bulan fonksiyon
def isim_dogrula(kod, ad, mevcut_df):
    kod_str = str(kod).strip().upper()
    ad_str = str(ad).strip().upper() if ad else ""
    
    # Eğer ad girilmemişse geçmişten bulalım
    if not ad_str and not mevcut_df.empty:
        gecmis_kayit = mevcut_df[mevcut_df['Malzeme Kodu'].astype(str).str.upper() == kod_str]
        if not gecmis_kayit.empty:
            # En son girilen geçerli (tire olmayan) ismi alalım
            gecerli_isimler = gecmis_kayit[gecmis_kayit['Malzeme Adı'] != "-"]
            if not gecerli_isimler.empty:
                return gecerli_isimler.iloc[-1]['Malzeme Adı']
    
    return ad_str if ad_str else "-"

def kayit_ekle(islem, adres, kod, ad, miktar):
    df = veri_getir()
    # Kayıt anında ismi otomatik tamamla/doğrula
    tam_ad = isim_dogrula(kod, ad, df)
    
    yeni_kayit = pd.DataFrame({
        "Tarih": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "İşlem": [islem],
        "Adres": [str(adres).upper() if adres else "GENEL"],
        "Malzeme Kodu": [str(kod).upper()],
        "Malzeme Adı": [tam_ad.upper()],
        "Miktar": [miktar]
    })
    guncel_df = pd.concat([df, yeni_kayit], ignore_index=True)
    conn.update(data=guncel_df)
    return tam_ad

# Veriyi oku
df_ana = veri_getir()

tab1, tab2, tab3 = st.tabs(["📥 Giriş", "📤 Çıkış", "🔍 Akıllı Stok Sorgu"])

with tab1:
    st.subheader("Malzeme Girişi")
    g_adr = st.text_input("Adres:", value="GENEL", key="g_adr")
    g_kod = st.text_input("Ürün Kodu:", key="g_k")
    g_ad = st.text_input("Ürün Adı (Boş bırakılabilir):", key="g_a")
    g_mik = st.number_input("Miktar:", min_value=1, step=1, key="g_m")
    
    if st.button("Girişi Kaydet", use_container_width=True):
        if g_kod:
            kaydedilen_ad = kayit_ekle("GİRİŞ", g_adr, g_kod, g_ad, g_mik)
            st.success(f"Kaydedildi: {g_kod} - {kaydedilen_ad}")
            st.rerun()
        else: st.error("Ürün kodu girmelisiniz!")

with tab2:
    st.subheader("Malzeme Çıkışı")
    c_adr = st.text_input("Adres:", value="GENEL", key="c_adr")
    c_kod = st.text_input("Ürün Kodu:", key="c_k")
    c_ad = st.text_input("Ürün Adı (Boş bırakılabilir):", key="c_a")
    c_mik = st.number_input("Miktar:", min_value=1, step=1, key="c_m")
    
    if st.button("Çıkışı Kaydet", use_container_width=True):
        if c_kod:
            kaydedilen_ad = kayit_ekle("ÇIKIŞ", c_adr, c_kod, c_ad, c_mik)
            st.success(f"Çıkış Yapıldı: {c_kod} - {kaydedilen_ad}")
            st.rerun()
        else: st.error("Ürün kodu girmelisiniz!")

with tab3:
    st.subheader("🔍 Mevcut Stoklar")
    search = st.text_input("Ara (Kod, İsim veya Adres):")
    
    if not df_ana.empty:
        # Veriyi temizle ve sayıya çevir
        df_ana['Miktar'] = pd.to_numeric(df_ana['Miktar'], errors='coerce').fillna(0)
        df_ana['Net'] = df_ana.apply(lambda r: r['Miktar'] if str(r['İşlem']).upper() == 'GİRİŞ' else -r['Miktar'], axis=1)
        
        # PİVOT MANTIĞI: Önce her kodun en güncel ismini belirleyelim
        islem_df = df_ana.sort_values('Tarih')
        # Her kod için en son girilen ve "-" olmayan ismi bulma
        isim_map = islem_df[islem_df['Malzeme Adı'] != "-"].groupby('Malzeme Kodu')['Malzeme Adı'].last().to_dict()
        
        # Tüm satırlara bu güncel isimleri bas (Konsolidasyon)
        df_ana['Guncel_Ad'] = df_ana['Malzeme Kodu'].map(isim_map).fillna(df_ana['Malzeme Adı'])
        
        # Şimdi pivot yapalım
        stok = df_ana.groupby(['Adres', 'Malzeme Kodu', 'Guncel_Ad'])['Net'].sum().reset_index()
        stok = stok[stok['Net'] > 0]
        stok.columns = ["Adres", "Kod", "Ürün Adı", "Miktar"]

        if search:
            term = search.upper()
            mask = (stok['Adres'].str.upper().str.contains(term, na=False) | 
                    stok['Kod'].str.upper().str.contains(term, na=False) | 
                    stok['Ürün Adı'].str.upper().str.contains(term, na=False))
            stok = stok[mask]
        
        st.dataframe(stok, use_container_width=True, hide_index=True)
    else:
        st.info("Henüz hareket kaydı bulunmuyor.")
