import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Sayfa Ayarları
st.set_page_config(page_title="Akıllı Depo v7", layout="centered")
st.title("📦 Profesyonel Adresli Depo Takip")

# Google Sheets Bağlantısı
conn = st.connection("gsheets", type=GSheetsConnection)

def taze_veri_getir():
    st.cache_data.clear()
    df = conn.read(ttl=0)
    if not df.empty:
        df.columns = df.columns.str.strip()
    return df

def isim_dogrula(kod, ad, mevcut_df):
    kod_str = str(kod).strip().upper()
    ad_str = str(ad).strip().upper() if ad and str(ad).strip() != "" else ""
    if (not ad_str or ad_str == "-") and not mevcut_df.empty:
        gecmis = mevcut_df[mevcut_df['Malzeme Kodu'].astype(str).str.upper() == kod_str]
        if not gecmis.empty:
            gecerli_isimler = gecmis[(gecmis['Malzeme Adı'].notna()) & (gecmis['Malzeme Adı'].astype(str) != "-")]
            if not gecerli_isimler.empty:
                return gecerli_isimler.iloc[-1]['Malzeme Adı']
    return ad_str if ad_str else "-"

def kayit_ekle(islem, adres, kod, ad, miktar, taze_df):
    tam_ad = isim_dogrula(kod, ad, taze_df)
    yeni_kayit = pd.DataFrame({
        "Tarih": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "İşlem": [islem],
        "Adres": [str(adres).upper()],
        "Malzeme Kodu": [str(kod).upper()],
        "Malzeme Adı": [tam_ad.upper()],
        "Miktar": [float(miktar)]
    })
    return yeni_kayit

# Başlangıç Verisi
if 'df' not in st.session_state:
    st.session_state.df = taze_veri_getir()

t1, t2, t3, t4 = st.tabs(["📥 Giriş", "📤 Çıkış", "🔄 Transfer", "🔍 Stok Sorgula"])

with t1:
    st.subheader("Malzeme Girişi")
    g_adr = st.text_input("Adres:", value="GENEL", key="g_adr")
    g_kod = st.text_input("Ürün Kodu:", key="g_k")
    g_ad = st.text_input("Ürün Adı (Otomatik):", key="g_a")
    g_mik = st.number_input("Miktar:", min_value=0.0, step=1.0, key="g_m")
    if st.button("📥 Kaydet", use_container_width=True):
        if g_kod and g_mik > 0:
            df_curr = taze_veri_getir()
            yeni = kayit_ekle("GİRİŞ", g_adr, g_kod, g_ad, g_mik, df_curr)
            conn.update(data=pd.concat([df_curr, yeni], ignore_index=True))
            st.success("Kaydedildi!")
            st.session_state.df = taze_veri_getir()
            st.rerun()

with t2:
    st.subheader("Malzeme Çıkışı")
    c_adr = st.text_input("Adres:", value="GENEL", key="c_adr")
    c_kod = st.text_input("Ürün Kodu:", key="c_k")
    c_ad = st.text_input("Ürün Adı (Otomatik):", key="c_a")
    c_mik = st.number_input("Miktar:", min_value=0.0, step=1.0, key="c_m")
    if st.button("📤 Çıkış Yap", use_container_width=True):
        if c_kod and c_mik > 0:
            df_curr = taze_veri_getir()
            yeni = kayit_ekle("ÇIKIŞ", c_adr, c_kod, c_ad, c_mik, df_curr)
            conn.update(data=pd.concat([df_curr, yeni], ignore_index=True))
            st.success("Çıkış Yapıldı!")
            st.session_state.df = taze_veri_getir()
            st.rerun()

with t3:
    st.subheader("🔄 Adresler Arası Transfer")
    tr_kod = st.text_input("Transfer Edilecek Ürün Kodu:", key="tr_k")
    col_a, col_b = st.columns(2)
    tr_nereden = col_a.text_input("Kaynak Adres (Nereden):", value="GENEL")
    tr_nereye = col_b.text_input("Hedef Adres (Nereye):", placeholder="Örn: P0001")
    tr_mik = st.number_input("Transfer Miktarı:", min_value=0.0, step=1.0, key="tr_m")
    
    if st.button("🔄 Transferi Onayla", use_container_width=True):
        if tr_kod and tr_nereye and tr_mik > 0:
            df_curr = taze_veri_getir()
            # 1. Kaynak adresten ÇIKIŞ
            cikis_satir = kayit_ekle("ÇIKIŞ", tr_nereden, tr_kod, "", tr_mik, df_curr)
            # 2. Hedef adrese GİRİŞ
            giris_satir = kayit_ekle("GİRİŞ", tr_nereye, tr_kod, "", tr_mik, df_curr)
            
            # İki satırı da ekle
            guncel_df = pd.concat([df_curr, cikis_satir, giris_satir], ignore_index=True)
            conn.update(data=guncel_df)
            st.success(f"{tr_kod} ürünü {tr_nereden} -> {tr_nereye} adresine taşındı!")
            st.session_state.df = taze_veri_getir()
            st.rerun()
        else: st.error("Lütfen tüm alanları doldurun!")

with t4:
    c1, c2 = st.columns([3, 1])
    c1.subheader("🔍 Mevcut Stoklar")
    if c2.button("🔄 Yenile"):
        st.session_state.df = taze_veri_getir()
        st.rerun()
    
    search = st.text_input("Sorgula (Kod, Ad veya Adres):")
    df_ana = st.session_state.df
    if not df_ana.empty:
        df_ana['Miktar'] = pd.to_numeric(df_ana['Miktar'], errors='coerce').fillna(0)
        df_ana['Net'] = df_ana.apply(lambda r: r['Miktar'] if str(r['İşlem']).upper() == 'GİRİŞ' else -r['Miktar'], axis=1)
        
        valid_names = df_ana[df_ana['Malzeme Adı'] != "-"].sort_values('Tarih')
        isim_map = valid_names.groupby('Malzeme Kodu')['Malzeme Adı'].last().to_dict()
        df_ana['Ürün Adı'] = df_ana['Malzeme Kodu'].map(isim_map).fillna(df_ana['Malzeme Adı'])
        
        stok = df_ana.groupby(['Adres', 'Malzeme Kodu', 'Ürün Adı'])['Net'].sum().reset_index()
        stok = stok[stok['Net'] > 0]
        stok.columns = ["Adres", "Kod", "Ürün Adı", "Miktar"]
        if search:
            t = search.upper()
            stok = stok[(stok['Adres'].str.upper().contains(t)) | (stok['Kod'].str.upper().contains(t)) | (stok['Ürün Adı'].str.upper().contains(t))]
        st.dataframe(stok, use_container_width=True, hide_index=True)
