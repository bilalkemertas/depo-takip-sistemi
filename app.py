import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="BRN Kesin Stok", layout="centered", page_icon="📦")

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
                if u_raw.strip().lower() in users and str(users[u_raw.strip().lower()]) == p_raw.strip():
                    st.session_state.logged_in = True
                    st.session_state.user = u_raw.strip().lower()
                    st.rerun()
                else: st.error("Hatalı Giriş!")
            except: st.error("Secrets bulunamadı!")
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
t1, t2, t3 = st.tabs(["📥 İşlem", "🔄 Transfer", "📊 ANLIK STOK"])

with t1:
    with st.container(border=True):
        islem = st.selectbox("İşlem:", ["GİRİŞ", "ÇIKIŞ"])
        adres = st.text_input("Adres:", value="GENEL", key="a1").strip().upper()
        m_kodu = st.text_input("Malzeme Kodu:", key="b1").strip().upper()
        m_adi = st.text_input("Malzeme Adı:", key="n1").strip().upper()
        c1, c2 = st.columns(2)
        with c1: birim = st.selectbox("Birim:", ["ADET", "METRE", "KG", "RULO"], key="u1")
        with c2: miktar = st.number_input("Miktar:", min_value=0.1, value=1.0, key="m1")
        if st.button("KAYDI TAMAMLA", use_container_width=True, type="primary"):
            df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1")
            yeni = pd.DataFrame([{"Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "İşlem": islem, "Adres": adres, "Malzeme Kodu": m_kodu, "Malzeme Adı": m_adi, "Birim": birim, "Miktar": miktar, "Operatör": st.session_state.user}])
            conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([df, yeni]))
            st.success("Kaydedildi!")

with t2:
    with st.container(border=True):
        st.subheader("Transfer")
        e_adr = st.text_input("Nereden (Eski):", key="ea2").strip().upper()
        y_adr = st.text_input("Nereye (Yeni):", key="ya2").strip().upper()
        t_kod = st.text_input("Malzeme Kodu:", key="b2").strip().upper()
        t_mik = st.number_input("Miktar:", min_value=0.1, value=1.0, key="tm2")
        t_bir = st.selectbox("Birim:", ["ADET", "METRE", "KG", "RULO"], key="tu2")
        if st.button("TRANSFER ET", use_container_width=True, type="primary"):
            df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1")
            # Transfer Satırları: Eski adresten düş, yeniye ekle
            cikis = pd.DataFrame([{"Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "İşlem": "ÇIKIŞ", "Adres": e_adr, "Malzeme Kodu": t_kod, "Malzeme Adı": "TRANSFER", "Birim": t_bir, "Miktar": t_mik, "Operatör": st.session_state.user}])
            giris = pd.DataFrame([{"Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "İşlem": "GİRİŞ", "Adres": y_adr, "Malzeme Kodu": t_kod, "Malzeme Adı": "TRANSFER", "Birim": t_bir, "Miktar": t_mik, "Operatör": st.session_state.user}])
            conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([df, cikis, giris]))
            st.success("Transfer yapıldı.")

# --- 📊 ANLIK STOK (GERÇEK MİZAN) ---
with t3:
    st.subheader("🔍 Mevcut Envanter Durumu")
    filtre = st.text_input("Kod veya Adres Ara:", key="f_search").strip().upper()
    
    if st.button("STOK LİSTESİNİ HESAPLA", use_container_width=True):
        st.cache_data.clear() # ÖNCE TEMİZLİK
        data = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1", ttl=0) # SONRA TAZE VERİ
        
        if not data.empty:
            # 1. Sayısal dönüşüm
            data['Miktar'] = pd.to_numeric(data['Miktar'], errors='coerce').fillna(0)
            
            # 2. Giriş/Çıkış Matematikselleştirme
            data['Net'] = data.apply(lambda x: x['Miktar'] if x['İşlem'] == 'GİRİŞ' else (-x['Miktar'] if x['İşlem'] == 'ÇIKIŞ' else 0), axis=1)
            
            # 3. Malzeme Adı temizliği (Sistem "TRANSFER" yazan isimleri en son gerçek isimle değiştirir)
            # Malzeme koduna göre en güncel (ve TRANSFER olmayan) ismi bulalım
            isimler = data[data['Malzeme Adı'] != 'TRANSFER'].sort_values('Tarih').groupby('Malzeme Kodu')['Malzeme Adı'].last().to_dict()
            data['Malzeme Adı'] = data['Malzeme Kodu'].map(isimler).fillna(data['Malzeme Adı'])

            # 4. GRUPLANDIRMA (Asıl Stok Raporu)
            stok = data.groupby(['Adres', 'Malzeme Kodu', 'Malzeme Adı', 'Birim'])['Net'].sum().reset_index()
            stok.columns = ['Adres', 'Kod', 'Malzeme Tanımı', 'Birim', 'Mevcut Bakiye']
            
            # 5. Sıfır olanları gizle
            stok = stok[stok['Mevcut Bakiye'] != 0]
            
            # 6. Arama Filtresi
            if filtre:
                stok = stok[(stok['Kod'].str.contains(filtre, na=False)) | (stok['Adres'].str.contains(filtre, na=False))]
            
            st.write(f"✅ **Güncel Veri Çekildi.** Toplam {len(stok)} kalem stokta.")
            st.dataframe(stok, use_container_width=True, hide_index=True)
        else:
            st.info("Hesaplanacak hareket bulunamadı.")
