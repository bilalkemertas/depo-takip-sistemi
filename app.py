import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import os

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Bilal Depo", layout="centered", page_icon="brn_logo.webp")

# --- KOMPAKT LOGO VE BAŞLIK TASARIMI ---
col_logo, col_baslik = st.columns([1, 4])

with col_logo:
    if os.path.exists("brn_logo.webp"):
        st.image("brn_logo.webp", width=50) # Logo %50 küçük

with col_baslik:
    st.markdown("<h3 style='margin: 0; padding-top: 5px;'>Bilal BRN Adresli Depo Simülasyonu</h3>", unsafe_allow_html=True)

st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)

# --- BAĞLANTI VE FONKSİYONLAR ---
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

# --- SEKMELER ---
t1, t2, t3 = st.tabs(["📥 Kayıt", "🔄 Transfer", "🔍 Rapor"])

with t1:
    c_isl, c_adr = st.columns(2)
    islem_tipi = c_isl.selectbox("İşlem:", ["GİRİŞ", "ÇIKIŞ"])
    adr = c_adr.text_input("Adres:", value="GENEL")
    
    kod = st.text_input("📦 Ürün Kodu:")
    ad_bulunan, birim_bulunan = urun_bilgisi_cek(kod)
    
    if kod:
        if ad_bulunan:
            st.success(f"{ad_bulunan} ({birim_bulunan})")
            is_decimal = False if str(birim_bulunan).upper() in ["ADET", "ADT", "AD"] else True
            step_val = 0.001 if is_decimal else 1.0
            mik = st.number_input(f"Miktar:", min_value=0.0, step=step_val)
            
            if st.button(f"{islem_tipi} KAYDET", use_container_width=True):
                if mik > 0:
                    kayit_ekle(islem_tipi, adr, kod, ad_bulunan, birim_bulunan, mik)
                    st.success("İşlem Başarılı!")
                    st.rerun()
        else:
            st.error("Ürün Tanımlı Değil!")

with t2:
    st.subheader("Adres Transferi")
    tr_kod = st.text_input("Ürün Kodu:", key="tr_k")
    tr_ad, tr_birim = urun_bilgisi_cek(tr_kod)
    
    if tr_kod and tr_ad:
        st.info(f"{tr_ad}")
        ca, cb = st.columns(2)
        n_den = ca.text_input("Nereden:", value="GENEL")
        n_ye = cb.text_input("Nereye:")
        tr_step = 0.001 if str(tr_birim).upper() not in ["ADET", "ADT"] else 1.0
        tr_mik = st.number_input("Mik:", min_value=0.0, step=tr_step, key="tr_mik")
        
        if st.button("TRANSFERİ TAMAMLA", use_container_width=True):
            if n_ye and tr_mik > 0:
                kayit_ekle("ÇIKIŞ", n_den, tr_kod, tr_ad, tr_birim, tr_mik)
                kayit_ekle("GİRİŞ", n_ye, tr_kod, tr_ad, tr_birim, tr_mik)
                st.success("Taşındı.")
                st.rerun()

with t3:
    col_t, col_b = st.columns([2, 1])
    col_t.caption("📊 Mevcut Stoklar")
    # HATA DÜZELTİLDİ: size="small" kaldırıldı
    if col_b.button("🔄 Yenile"): 
        st.rerun()
    
    if not df_hareketler.empty:
        df_h = df_hareketler.copy()
        if 'Birim' in df_h.columns:
            df_h['Miktar'] = pd.to_numeric(df_h['Miktar'], errors='coerce').fillna(0)
            df_h['Net'] = df_h.apply(lambda r: r['Miktar'] if str(r['İşlem']).upper() == 'GİRİŞ' else -r['Miktar'], axis=1)
            stok = df_h.groupby(['Adres', 'Malzeme Kodu', 'Malzeme Adı', 'Birim'])['Net'].sum().reset_index()
            stok = stok[stok['Net'] > 0]
            stok.columns = ["Adr", "Kod", "Ad", "Brm", "Miktar"]
            st.dataframe(stok, use_container_width=True, hide_index=True)
        else:
            st.warning("Eksik Sütun: Birim!")

# --- İMZA ---
st.markdown("<div style='text-align: center; color: gray; font-size: 0.7em; margin-top: 20px;'>Bilal BRN Depo  | Geliştiren: [BİLAL KEMERTAŞ]</div>", unsafe_allow_html=True)
