import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Depo X-Ray v8.0", layout="centered", page_icon="🛡️")
st.title("🛡️ Depo X-Ray: Master Data Kontrollü")

conn = st.connection("gsheets", type=GSheetsConnection)

def taze_veri_getir(worksheet="Sayfa1"):
    st.cache_data.clear()
    # Hem hareketleri hem de ürün listesini çekiyoruz
    df = conn.read(ttl=0, worksheet=worksheet)
    if not df.empty:
        df.columns = df.columns.str.strip()
    return df

# --- MASTER DATA KONTROLÜ ---
df_urunler = taze_veri_getir(worksheet="Urun_Listesi") # Ürün kartlarının olduğu sayfa
df_hareketler = taze_veri_getir(worksheet="Sayfa1")    # Hareketlerin olduğu sayfa

def urun_bilgisi_cek(kod):
    if not df_urunler.empty and kod:
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
        "Birim": [str(birim).upper()], # Artık birim de kaydediliyor
        "Miktar": [float(miktar)]
    })
    conn.update(data=pd.concat([df_temp, yeni_kayit], ignore_index=True), worksheet="Sayfa1")

# Sekmeler
t1, t2, t3 = st.tabs(["📥 Hareket Kaydı (Giriş/Çıkış)", "🔄 Transfer", "🔍 Stok Sorgula"])

with t1:
    col_islem, col_adr = st.columns(2)
    islem_tipi = col_islem.selectbox("İşlem Tipi:", ["GİRİŞ", "ÇIKIŞ"])
    adr = col_adr.text_input("Adres:", value="GENEL")
    
    kod = st.text_input("📦 Ürün Kodunu Okutun/Yazın:")
    
    # MASTER DATA SORGUSU
    ad_bulunan, birim_bulunan = urun_bilgisi_cek(kod)
    
    if kod:
        if ad_bulunan:
            st.info(f"✅ Ürün: **{ad_bulunan}** | Birim: **{birim_bulunan}**")
            
            # KÜSÜRAT KISITI: Birim 'Adet' ise küsüratı engelle
            is_decimal = False if str(birim_bulunan).upper() in ["ADET", "ADT", "AD"] else True
            step_val = 0.001 if is_decimal else 1.0
            
            mik = st.number_input(f"Miktar ({birim_bulunan}):", min_value=0.0, step=step_val)
            
            if st.button(f"{islem_tipi} Kaydet", use_container_width=True):
                if mik > 0:
                    kayit_ekle(islem_tipi, adr, kod, ad_bulunan, birim_bulunan, mik)
                    st.success("İşlem Başarılı!")
                    st.rerun()
        else:
            st.error("⚠️ Bu ürün kodu 'Urun_Listesi' sayfasında tanımlı değil! Lütfen önce tanımlayın.")

with t2:
    st.subheader("🔄 Adres Transferi")
    tr_kod = st.text_input("Transfer Ürün Kodu:", key="tr_k")
    tr_ad, tr_birim = urun_bilgisi_cek(tr_kod)
    
    if tr_kod and tr_ad:
        st.info(f"Ürün: {tr_ad} ({tr_birim})")
        c1, c2 = st.columns(2)
        n_den = c1.text_input("Nereden:", value="GENEL")
        n_ye = c2.text_input("Nereye:")
        
        tr_step = 0.001 if str(tr_birim).upper() not in ["ADET", "ADT"] else 1.0
        tr_mik = st.number_input("Miktar:", min_value=0.0, step=tr_step)
        
        if st.button("Transferi Onayla"):
            if n_ye and tr_mik > 0:
                kayit_ekle("ÇIKIŞ", n_den, tr_kod, tr_ad, tr_birim, tr_mik)
                kayit_ekle("GİRİŞ", n_ye, tr_kod, tr_ad, tr_birim, tr_mik)
                st.success("Transfer Tamamlandı.")
                st.rerun()
    elif tr_kod:
        st.warning("Ürün bulunamadı.")

with t3:
    c1, c2 = st.columns([3, 1])
    c1.subheader("📊 Anlık Stok Durumu")
    if c2.button("🔄 Verileri Yenile"): st.rerun()
    
    if not df_hareketler.empty:
        df_h = df_hareketler.copy()
        df_h['Miktar'] = pd.to_numeric(df_h['Miktar'], errors='coerce').fillna(0)
        df_h['Net'] = df_h.apply(lambda r: r['Miktar'] if str(r['İşlem']).upper() == 'GİRİŞ' else -r['Miktar'], axis=1)
        
        # PİVOT - Birim bazlı net stok
        stok = df_h.groupby(['Adres', 'Malzeme Kodu', 'Malzeme Adı', 'Birim'])['Net'].sum().reset_index()
        stok = stok[stok['Net'] > 0]
        stok.columns = ["Adres", "Kod", "Ürün Adı", "Birim", "Miktar"]
        st.dataframe(stok, use_container_width=True, hide_index=True)

# --- İMZA ---
st.markdown("---")
st.markdown(f'<div style="text-align: center; color: gray;"><b>[BİLAL KEMERTAŞ]</b></div>', unsafe_allow_html=True)
