import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="BRN Depo Pro", layout="centered", page_icon="📦")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton {display: none !important;}
    .block-container { padding: 0.5rem 0.5rem !important; }
    input { font-size: 16px !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 5px; }
    .stTabs [data-baseweb="tab"] { padding: 10px; font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. GÜVENLİK ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h3 style='text-align:center;'>🛡️ BRN Güvenli Erişim</h3>", unsafe_allow_html=True)
    with st.form("Giriş"):
        u_raw = st.text_input("Kullanıcı:")
        p_raw = st.text_input("Parola:", type="password")
        if st.form_submit_button("SİSTEME GİRİŞ YAP", use_container_width=True):
            try:
                users = st.secrets["users"]
                u_in = u_raw.strip().lower()
                p_in = p_raw.strip()
                if u_in in users and str(users[u_in]) == p_in:
                    st.session_state.logged_in = True
                    st.session_state.user = u_in
                    st.rerun()
                else: st.error("Hatalı Giriş!")
            except: st.error("Secrets ayarları eksik!")
    st.stop()

# --- 3. BAĞLANTI ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- 4. HEADER ---
h1, h2, h3 = st.columns([0.8, 2, 0.8], vertical_alignment="center")
with h1: st.image("brn_logo.webp", width=55)
with h2: st.markdown(f"**👤 {st.session_state.user.upper()}**")
with h3: 
    if st.button("Çık"):
        st.session_state.logged_in = False
        st.rerun()

st.divider()

# --- 5. ANA MODÜLLER ---
t1, t2, t3 = st.tabs(["📥 İşlem", "🔄 Transfer", "📊 Stok Sorgu"])

with t1:
    with st.container(border=True):
        islem = st.selectbox("İşlem Tipi:", ["GİRİŞ", "ÇIKIŞ"])
        adres = st.text_input("Adres (Raf):", value="GENEL", key="a1").strip().upper()
        m_kodu = st.text_input("Malzeme Kodu:", key="b1").strip().upper()
        m_adi = st.text_input("Malzeme Adı:", key="n1").strip().upper()
        c1, c2 = st.columns(2)
        with c1: birim = st.selectbox("Birim:", ["ADET", "METRE", "KG", "RULO"], key="u1")
        with c2: miktar = st.number_input("Miktar:", min_value=0.1, value=1.0, step=0.1, key="m1")
        
        if st.button("KAYDI TAMAMLA", use_container_width=True, type="primary"):
            if m_kodu:
                df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1")
                yeni = pd.DataFrame([{"Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "İşlem": islem, "Adres": adres, "Malzeme Kodu": m_kodu, "Malzeme Adı": m_adi, "Birim": birim, "Miktar": miktar, "Operatör": st.session_state.user}])
                conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([df, yeni]))
                st.success(f"{miktar} {birim} {islem} kaydedildi!")
            else: st.warning("Kod boş!")

with t2:
    with st.container(border=True):
        st.subheader("Transfer")
        e_adres = st.text_input("Nereden (Eski Raf):", key="ea2").strip().upper()
        y_adres = st.text_input("Nereye (Yeni Raf):", key="ya2").strip().upper()
        tr_kodu = st.text_input("Malzeme Kodu:", key="b2").strip().upper()
        tr_miktar = st.number_input("Miktar:", min_value=0.1, value=1.0, key="tm2")
        tr_birim = st.selectbox("Birim:", ["ADET", "METRE", "KG", "RULO"], key="tu2")
        
        if st.button("TRANSFERİ GERÇEKLEŞTİR", use_container_width=True, type="primary"):
            if tr_kodu and y_adres and e_adres:
                df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1")
                cikis = pd.DataFrame([{"Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "İşlem": "ÇIKIŞ", "Adres": e_adres, "Malzeme Kodu": tr_kodu, "Malzeme Adı": "TRANSFER", "Birim": tr_birim, "Miktar": tr_miktar, "Operatör": st.session_state.user}])
                giris = pd.DataFrame([{"Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "İşlem": "GİRİŞ", "Adres": y_adres, "Malzeme Kodu": tr_kodu, "Malzeme Adı": "TRANSFER", "Birim": tr_birim, "Miktar": tr_miktar, "Operatör": st.session_state.user}])
                conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([df, cikis, giris]))
                st.success("Transfer tamamlandı.")
            else: st.error("Alanları doldurun!")

# --- 📊 STOK SORGULAMA (FİLTRELİ VE TEMİZLİKLİ) ---
with t3:
    st.subheader("🔍 Mevcut Envanter")
    ara = st.text_input("Kod, Ad veya Adres Ara:", key="f_search").strip().upper()
    
    if st.button("Stok Listesini Hesapla / Yenile", use_container_width=True):
        # 1. CATCH (ÖNBELLEK) TEMİZLİĞİ
        st.cache_data.clear() 
        
        # 2. VERİYİ SIFIRDAN ÇEK
        data = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1", ttl=0)
        
        if not data.empty:
            # Sayısal veri dönüşümü
            data['Miktar'] = pd.to_numeric(data['Miktar'], errors='coerce').fillna(0)
            
            # GİRİŞ (+) / ÇIKIŞ (-) Hesaplaması
            data['Net_Miktar'] = data.apply(
                lambda x: x['Miktar'] if x['İşlem'] == 'GİRİŞ' else (-x['Miktar'] if x['İşlem'] == 'ÇIKIŞ' else 0), 
                axis=1
            )
            
            # GRUPLANDIRMA (Hareket listesini gerçek stok listesine çeviren sihirli satır)
            stok_listesi = data.groupby(['Adres', 'Malzeme Kodu', 'Malzeme Adı', 'Birim'])['Net_Miktar'].sum().reset_index()
            stok_listesi.columns = ['Adres', 'Malzeme Kodu', 'Malzeme Adı', 'Birim', 'Bakiye']
            
            # Sadece eldeki bakiyesi olanları (0 olmayanları) göster
            stok_listesi = stok_listesi[stok_listesi['Bakiye'] != 0]
            
            # Arama filtresi
            if ara:
                stok_listesi = stok_listesi[
                    (stok_listesi['Malzeme Kodu'].str.contains(ara, na=False)) | 
                    (stok_listesi['Malzeme Adı'].str.contains(ara, na=False)) |
                    (stok_listesi['Adres'].str.contains(ara, na=False))
                ]
            
            # Tabloyu bas
            st.write(f"📊 Toplam {len(stok_listesi)} kalem ürün bulundu.")
            st.dataframe(stok_listesi, use_container_width=True, hide_index=True)
        else:
            st.info("Hesaplanacak veri bulunamadı.")
