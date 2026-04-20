import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import streamlit.components.v1 as components

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="BRN Depo Yönetimi", layout="centered", page_icon="📦")

# Mobil Kompakt Görünüm
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
                else: st.error("Hatalı Giriş Bilgisi!")
            except: st.error("Giriş ayarları (Secrets) eksik!")
    st.stop()

# --- 3. BAĞLANTI ---
conn = st.connection("gsheets", type=GSheetsConnection)
# Senin secrets ayarlarındaki linki otomatik çeker
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
t1, t2, t3 = st.tabs(["📥 İşlem", "🔄 Transfer", "📊 Anlık Stok"])

with t1:
    with st.container(border=True):
        islem = st.selectbox("İşlem Tipi:", ["GİRİŞ", "ÇIKIŞ"])
        adres = st.text_input("Adres:", value="GENEL", key="a1").strip().upper()
        barkod = st.text_input("Barkod Okut:", key="b1").strip().upper()
        if st.button("KAYDI TAMAMLA", use_container_width=True, type="primary"):
            if barkod:
                df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1")
                yeni = pd.DataFrame([{"Tarih": datetime.now().strftime("%d.%m.%Y %H:%M"), "İşlem": islem, "Adres": adres, "Barkod": barkod, "Operatör": st.session_state.user}])
                conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([df, yeni]))
                st.success(f"{barkod} {islem} yapıldı!")
            else: st.warning("Barkod boş!")

with t2:
    with st.container(border=True):
        st.subheader("Adres Transferi")
        y_adres = st.text_input("Hedef Adres:", key="a2").strip().upper()
        tr_barkod = st.text_input("Ürün Barkodu:", key="b2").strip().upper()
        if st.button("TRANSFERİ ONAYLA", use_container_width=True, type="primary"):
            if tr_barkod and y_adres:
                df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1")
                yeni = pd.DataFrame([{"Tarih": datetime.now().strftime("%d.%m.%Y %H:%M"), "İşlem": "TRANSFER", "Adres": y_adres, "Barkod": tr_barkod, "Operatör": st.session_state.user}])
                conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([df, yeni]))
                st.success(f"{tr_barkod} -> {y_adres} adresine taşındı.")
            else: st.error("Eksik bilgi!")

with t3:
    st.subheader("🔎 Stok Durumu")
    
    # --- FİLTRELEME KUTUSU (Geri Geldi) ---
    search = st.text_input("Barkod veya Adres ile Filtrele:", key="stok_ara").strip().upper()
    
    if st.button("Listeyi Yenile"):
        # Veriyi çek
        raw_df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1")
        
        if not raw_df.empty:
            # ANLIK STOK HESAPLAMA MANTIĞI:
            # Her barkodun en son hareketini buluyoruz. 
            # Eğer son hareketi ÇIKIŞ değilse, o ürün deponun o adresindedir.
            
            # Tarihe göre sırala (en güncel en sonda kalacak şekilde)
            raw_df['Tarih_dt'] = pd.to_datetime(raw_df['Tarih'], format='%d.%m.%Y %H:%M', errors='coerce')
            stok_durumu = raw_df.sort_values('Tarih_dt').drop_duplicates('Barkod', keep='last')
            
            # ÇIKIŞ yapılmış olanları listeden çıkar (çünkü artık stokta değiller)
            stok_durumu = stok_durumu[stok_durumu['İşlem'] != 'ÇIKIŞ']
            
            # Filtreleme Uygula
            if search:
                stok_durumu = stok_durumu[
                    (stok_durumu['Barkod'].str.contains(search, na=False)) | 
                    (stok_durumu['Adres'].str.contains(search, na=False))
                ]
            
            # Gereksiz sütunları temizle ve göster
            gosterilecek = stok_durumu[['Barkod', 'Adres', 'Tarih', 'Operatör']]
            st.write(f"**Bulunan Kayıt Sayısı:** {len(gosterilecek)}")
            st.dataframe(gosterilecek, use_container_width=True)
        else:
            st.info("Henüz kayıt bulunamadı.")
