import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Bilal BRN Depo Pro", layout="wide", page_icon="📦")

# Mobil Görüntü Fixleme İçin Özel CSS
st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton {display: none !important;}
    .block-container { padding: 0.5rem 0.5rem !important; }
    input { font-size: 16px !important; }
    .stButton>button { height: 3em; font-size: 16px !important; }
    [data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 10px; }
    .stDataFrame { width: 100% !important; overflow-x: auto !important; }
    @media (max-width: 640px) {
        .stMetric { padding: 5px !important; border: 1px solid #eee; margin-bottom: 5px; }
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. GÜVENLİK ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if 'gecici_sayim_listesi' not in st.session_state: st.session_state['gecici_sayim_listesi'] = []

if not st.session_state.logged_in:
    st.markdown("<h3 style='text-align:center;'>🛡️ Bilal BRN Depo Giriş</h3>", unsafe_allow_html=True)
    with st.form("Giriş"):
        u_raw = st.text_input("Kullanıcı:")
        p_raw = st.text_input("Parola:", type="password")
        if st.form_submit_button("SİSTEME GİRİŞ YAP", use_container_width=True):
            if "users" in st.secrets:
                users = st.secrets["users"]
                if u_raw.strip().lower() in users and str(users[u_raw.strip().lower()]) == p_raw.strip():
                    st.session_state.logged_in = True
                    st.session_state.user = u_raw.lower()
                    st.rerun()
                else: st.error("Hatalı Giriş!")
    st.stop()

# Navigasyon
if 'page' not in st.session_state: st.session_state.page = 'home'
def go_home(): st.session_state.page = 'home'
def go_stok(): st.session_state.page = 'stok'
def go_uretim(): st.session_state.page = 'uretim'
def go_sayim(): st.session_state.page = 'sayim'
def go_rapor(): st.session_state.page = 'rapor'

# --- 3. BAĞLANTI & YARDIMCI FONKSİYONLAR ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

@st.cache_data(ttl=0)
def get_internal_data(worksheet_name):
    try: return conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)
    except: return pd.DataFrame()

@st.cache_data(ttl=60)
def get_kod_map():
    df = get_internal_data("Stok")
    if not df.empty: return dict(zip(df['Kod'].astype(str), df['İsim'].astype(str)))
    return {}

def log_movement(islem, adres, kod, isim, miktar):
    try:
        log_df = get_internal_data("Sayfa1")
        yeni_log = pd.DataFrame([{"Tarih": (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M"), "İşlem": str(islem), "Adres": str(adres).upper(), "Malzeme Kodu": str(kod).upper(), "Malzeme Adı": isim, "Miktar": float(miktar), "Operatör": st.session_state.user}])
        conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([log_df, yeni_log], ignore_index=True))
    except: pass

# --- 4. ANA EKRAN ---
if st.session_state.page == 'home':
    st.markdown("<h3 style='text-align:center;'>📦 Depo Kontrol Merkezi</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.button("📊 STOK İŞLEMLERİ", use_container_width=True, type="primary", on_click=go_stok)
        st.button("🏭 ÜRETİM HAZIRLIK", use_container_width=True, type="primary", on_click=go_uretim)
    with c2:
        st.button("📝 SAYIM SİSTEMİ", use_container_width=True, type="primary", on_click=go_sayim)
        st.button("📈 GENEL RAPORLAR", use_container_width=True, type="primary", on_click=go_rapor)
    if st.sidebar.button("Güvenli Çıkış"): st.session_state.clear(); st.rerun()

# --- 5. STOK İŞLEMLERİ ---
elif st.session_state.page == 'stok':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("İşlem Ekranı")
    # Stok kodları buraya (v21 standartları)...

# --- 6. ÜRETİM HAZIRLIK ---
elif st.session_state.page == 'uretim':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("Üretim Hazırlık")
    # Üretim kodları buraya...

# --- 7. SAYIM SİSTEMİ (TABLO GÖRÜNÜMLÜ ONAY LİSTESİ) ---
elif st.session_state.page == 'sayim':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.title("⚖️ Sayım ve Durum Yönetimi")
    
    st_tab1, st_tab2 = st.tabs(["📝 Sayım Girişi", "📊 Sayım & Fark Raporu"])
    kod_map = get_kod_map()
    durum_opsiyonlari = ["Kullanılabilir", "Hasarlı", "Kayıp", "İncelemede"]

    with st_tab1:
        # Veri Giriş Formu
        with st.container(border=True):
            s_adr = st.text_input("📍 Adres").upper()
            s_kod = st.selectbox("📦 Kod", [""] + sorted(list(kod_map.keys())))
            st.caption(f"Ürün Adı: {kod_map.get(s_kod, '')}")
            s_mik = st.number_input("Miktar", min_value=0.0, step=1.0)
            s_dur = st.selectbox("🛠️ Durum", durum_opsiyonlari)
            
            if st.button("➕ Listeye Ekle", use_container_width=True):
                if s_adr and s_kod:
                    st.session_state['gecici_sayim_listesi'].append({
                        "Tarih": datetime.now().strftime("%Y-%m-%d"),
                        "Personel": st.session_state.user, "Adres": s_adr, "Kod": s_kod, 
                        "Ürün Adı": kod_map.get(s_kod, ""), "Miktar": s_mik, "Durum": s_dur
                    })
                    st.toast("Eklendi")
                else: st.warning("Eksik Bilgi")

        # --- ONAY BEKLEYENLER TABLO GÖRÜNÜMÜ ---
        if st.session_state['gecici_sayim_listesi']:
            st.markdown("### 📥 Onay Bekleyen Sayımlar")
            
            # Tablo Başlıkları (Header)
            h_cols = st.columns([1, 1.2, 1.5, 0.8, 1, 0.4])
            h_cols[0].write("**Adres**")
            h_cols[1].write("**Kod**")
            h_cols[2].write("**Ürün Adı**")
            h_cols[3].write("**Mik.**")
            h_cols[4].write("**Durum**")
            h_cols[5].write("**Sil**")
            st.markdown("---")

            # Tablo Satırları (Rows)
            for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
                r_cols = st.columns([1, 1.2, 1.5, 0.8, 1, 0.4])
                r_cols[0].write(item['Adres'])
                r_cols[1].write(item['Kod'])
                r_cols[2].write(f"<small>{item['Ürün Adı']}</small>", unsafe_allow_html=True) # Uzun isimler için küçük font
                r_cols[3].write(str(item['Miktar']))
                r_cols[4].write(item['Durum'])
                if r_cols[5].button("🗑️", key=f"del_final_{idx}"):
                    st.session_state['gecici_sayim_listesi'].pop(idx)
                    st.rerun()
            
            st.write("---")
            if st.button("📤 DRIVE'A KAYDET VE ONAYLA", type="primary", use_container_width=True):
                df_db = get_internal_data("sayim")
                conn.update(spreadsheet=SHEET_URL, worksheet="sayim", data=pd.concat([df_db, pd.DataFrame(st.session_state['gecici_sayim_listesi'])], ignore_index=True))
                st.session_state['gecici_sayim_listesi'] = []
                st.success("Tüm sayımlar Drive'a işlendi!"); st.rerun()

    # Rapor ekranı (v23'teki fixli mobil haliyle devam ediyor)
    with st_tab2:
        # ... (Önceki fixli rapor kodların burada kalmalı) ...
# --- 8. GENEL RAPORLAR ---
elif st.session_state.page == 'rapor':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    rt1, rt2 = st.tabs(["🏠 Stok Durumu", "📜 Hareket Arşivi"])
    with rt1: st.dataframe(get_internal_data("Stok"), use_container_width=True, hide_index=True)
    with rt2: st.dataframe(get_internal_data("Sayfa1").iloc[::-1], use_container_width=True, hide_index=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
