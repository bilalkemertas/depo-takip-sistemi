import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="BRN Depo Yönetimi", layout="centered", page_icon="📦")

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
t1, t2, t3 = st.tabs(["📥 İşlem", "🔄 Transfer", "📊 Mevcut Stok"])

with t1:
    with st.container(border=True):
        islem = st.selectbox("İşlem Tipi:", ["GİRİŞ", "ÇIKIŞ"])
        adres = st.text_input("Adres:", value="GENEL", key="a1").strip().upper()
        m_kodu = st.text_input("Malzeme Kodu / Barkod:", key="b1").strip().upper()
        m_adi = st.text_input("Malzeme Adı:", key="n1").strip().upper()
        miktar = st.number_input("Miktar:", min_value=1.0, value=1.0, step=1.0, key="m1")
        
        if st.button("KAYDI TAMAMLA", use_container_width=True, type="primary"):
            if m_kodu:
                df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1")
                yeni = pd.DataFrame([{
                    "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "İşlem": islem,
                    "Adres": adres,
                    "Malzeme Kodu": m_kodu,
                    "Malzeme Adı": m_adi,
                    "Miktar": miktar,
                    "Operatör": st.session_state.user
                }])
                conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([df, yeni]))
                st.success(f"✅ {miktar} Adet {islem} Kaydedildi!")
            else: st.warning("Barkod okutun!")

with t2:
    with st.container(border=True):
        st.subheader("Adres Transferi")
        e_adres = st.text_input("Nereden (Eski Adres):", key="ea2").strip().upper()
        y_adres = st.text_input("Nereye (Yeni Adres):", key="ya2").strip().upper()
        tr_kodu = st.text_input("Malzeme Kodu:", key="b2").strip().upper()
        tr_miktar = st.number_input("Miktar:", min_value=1.0, value=1.0, key="m2")
        
        if st.button("TRANSFERİ ONAYLA", use_container_width=True, type="primary"):
            if tr_kodu and y_adres and e_adres:
                df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1")
                # İki kayıt oluşturuyoruz: Eskiden çıkış, yeniye giriş
                cikis = pd.DataFrame([{"Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "İşlem": "ÇIKIŞ", "Adres": e_adres, "Malzeme Kodu": tr_kodu, "Malzeme Adı": "TRANSFER ÇIKIŞ", "Miktar": tr_miktar, "Operatör": st.session_state.user}])
                giris = pd.DataFrame([{"Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "İşlem": "GİRİŞ", "Adres": y_adres, "Malzeme Kodu": tr_kodu, "Malzeme Adı": "TRANSFER GİRİŞ", "Miktar": tr_miktar, "Operatör": st.session_state.user}])
                conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([df, cikis, giris]))
                st.success(f"📦 {tr_miktar} Adet {e_adres} -> {y_adres} Taşındı!")
            else: st.error("Lütfen tüm adres bilgilerini doldurun!")

with t3:
    st.subheader("🔍 Anlık Stok Sorgulama")
    filtre = st.text_input("Filtrele (Malzeme veya Adres):", key="f1").strip().upper()
    
    if st.button("Listeyi Hesapla", use_container_width=True):
        data = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1")
        
        if not data.empty:
            # Eski kayıtlarda miktar yoksa 1 kabul et
            if 'Miktar' not in data.columns:
                data['Miktar'] = 1
            
            # Bakiye hesapla
            data['Bakiye'] = data.apply(lambda x: x['Miktar'] if x['İşlem'] == 'GİRİŞ' else (-x['Miktar'] if x['İşlem'] == 'ÇIKIŞ' else 0), axis=1)
            
            # Filtrele
            if filtre:
                data = data[(data['Malzeme Kodu'].str.contains(filtre, na=False)) | 
                            (data['Malzeme Adı'].str.contains(filtre, na=False)) |
                            (data['Adres'].str.contains(filtre, na=False))]
            
            # Grupla ve Topla
            stok_ozet = data.groupby(['Adres', 'Malzeme Kodu', 'Malzeme Adı'])['Bakiye'].sum().reset_index()
            stok_ozet.columns = ['Adres', 'Kod', 'İsim', 'Adet']
            
            # Sıfır stokları gösterme (opsiyonel)
            stok_ozet = stok_ozet[stok_ozet['Adet'] != 0]
            
            st.dataframe(stok_ozet, use_container_width=True, hide_index=True)
            st.info(f"Filtreye uygun toplam {stok_ozet['Adet'].sum()} adet ürün bulundu.")
        else:
            st.info("Veri bulunamadı.")
