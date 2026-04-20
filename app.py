import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import os

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Bilal Depo", layout="centered", page_icon="🛡️")

# --- LOGO VE BAŞLIK ---
# Logonun varlığını kontrol et ve göster
if os.path.exists("brn_logo.webp"):
    st.image("brn_logo.webp", width=150)

st.title("🛡️ Bilal BRN Depo Simülasyonu")
st.markdown("---")

conn = st.connection("gsheets", type=GSheetsConnection)

def taze_veri_getir(worksheet="Sayfa1"):
    st.cache_data.clear()
    try:
        df = conn.read(ttl=0, worksheet=worksheet)
        if not df.empty:
            df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame()

# Master Data ve Hareketleri Yükle
df_urunler = taze_veri_getir(worksheet="Urun_Listesi")
df_hareketler = taze_veri_getir(worksheet="Sayfa1")

def urun_bilgisi_cek(kod):
    if not df_urunler.empty and kod:
        if 'Malzeme Kodu' in df_urunler.columns:
            match = df_urunler[df_urunler['Malzeme Kodu'].astype(str).str.upper() == str(kod).upper()]
            if not match.empty:
                return match.iloc[0]['Malzeme Adı'], match.iloc[0]['Birim']
    return None, None

def kayit_ekle(islem, adres, kod, ad, birim, miktar):
    df_temp = taze_veri_getir(worksheet="Sayfa1")
    yeni_kayit = pd.DataFrame({
        "Tarih": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "İşlem": [islem],
        "Adres": [str(adres).upper()],
        "Malzeme Kodu": [str(kod).upper()],
        "Malzeme Adı": [str(ad).upper()],
        "Birim": [str(birim).upper()],
        "Miktar": [float(miktar)]
    })
    conn.update(data=pd.concat([df_temp, yeni_kayit], ignore_index=True), worksheet="Sayfa1")

# Sekmeler
t1, t2, t3 = st.tabs(["📥 Kayıt İşlemleri", "🔄 Transfer", "🔍 Stok Raporu"])

with t1:
    col_islem, col_adr = st.columns(2)
    islem_tipi = col_islem.selectbox("İşlem Tipi:", ["GİRİŞ", "ÇIKIŞ"])
    adr = col_adr.text_input("Adres:", value="GENEL")
    
    kod = st.text_input("📦 Ürün Kodunu Okutun:")
    
    ad_bulunan, birim_bulunan = urun_bilgisi_cek(kod)
    
    if kod:
        if ad_bulunan:
            st.info(f"✅ **{ad_bulunan}** ({birim_bulunan})")
            is_decimal = False if str(birim_bulunan).upper() in ["ADET", "ADT", "AD"] else True
            step_val = 0.001 if is_decimal else 1.0
            mik = st.number_input(f"Miktar:", min_value=0.0, step=step_val)
            
            if st.button(f"{islem_tipi} Onayla", use_container_width=True):
                if mik > 0:
                    kayit_ekle(islem_tipi, adr, kod, ad_bulunan, birim_bulunan, mik)
                    st.success("İşlem Kaydedildi!")
                    st.rerun()
        else:
            st.error("⚠️ Kod 'Urun_Listesi' sayfasında bulunamadı!")

with t2:
    st.subheader("🔄 Adres Transferi")
    tr_kod = st.text_input("Transfer Ürün Kodu:", key="tr_k")
    tr_ad, tr_birim = urun_bilgisi_cek(tr_kod)
    
    if tr_kod and tr_ad:
        st.info(f"Ürün: {tr_ad}")
        c1, c2 = st.columns(2)
        n_den = c1.text_input("Nereden:", value="GENEL")
        n_ye = c2.text_input("Nereye:")
        tr_step = 0.001 if str(tr_birim).upper() not in ["ADET", "ADT"] else 1.0
        tr_mik = st.number_input("Miktar:", min_value=0.0, step=tr_step)
        
        if st.button("Transferi Başlat", use_container_width=True):
            if n_ye and tr_mik > 0:
                kayit_ekle("ÇIKIŞ", n_den, tr_kod, tr_ad, tr_birim, tr_mik)
                kayit_ekle("GİRİŞ", n_ye, tr_kod, tr_ad, tr_birim, tr_mik)
                st.success("Transfer Başarılı.")
                st.rerun()

with t3:
    col_t, col_b = st.columns([3, 1])
    col_t.subheader("📊 Stok Durumu")
    if col_b.button("🔄 Yenile"): st.rerun()
    
    if not df_hareketler.empty:
        # Sütun kontrolü (KeyError önleyici)
        gerekli = ['Adres', 'Malzeme Kodu', 'Malzeme Adı', 'Birim', 'İşlem', 'Miktar']
        mevcut = df_hareketler.columns.tolist()
        eksik = [c for c in gerekli if c not in mevcut]
        
        if eksik:
            st.warning(f"Google Sheets 'Sayfa1' içerisinde şu başlıklar eksik: {eksik}")
        else:
            df_h = df_hareketler.copy()
            df_h['Miktar'] = pd.to_numeric(df_h['Miktar'], errors='coerce').fillna(0)
            df_h['Net'] = df_h.apply(lambda r: r['Miktar'] if str(r['İşlem']).upper() == 'GİRİŞ' else -r['Miktar'], axis=1)
            stok = df_h.groupby(['Adres', 'Malzeme Kodu', 'Malzeme Adı', 'Birim'])['Net'].sum().reset_index()
            stok = stok[stok['Net'] > 0]
            stok.columns = ["Adres", "Kod", "Ürün Adı", "Birim", "Miktar"]
            st.dataframe(stok, use_container_width=True, hide_index=True)

# --- İMZA ---
st.markdown("---")
st.markdown(f'<div style="text-align: center; color: gray; font-size: 0.8em;">Geliştiren: <b>[BİLAL KEMERTAŞ]</b><br>🛡️ Depo X-Ray v8.1</div>', unsafe_allow_html=True)
