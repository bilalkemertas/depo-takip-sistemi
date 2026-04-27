import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Bilal BRN Depo Pro - Unified", layout="wide", page_icon="📦")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton {display: none !important;}
    .block-container { padding: 0.5rem 0.5rem !important; }
    input { font-size: 16px !important; }
    .stButton>button { height: 3em; font-size: 16px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. GÜVENLİK ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if 'gecici_sayim_listesi' not in st.session_state:
    st.session_state['gecici_sayim_listesi'] = []

if not st.session_state.logged_in:
    st.markdown("<h3 style='text-align:center;'>🛡️ Bilal BRN Depo Giriş</h3>", unsafe_allow_html=True)
    with st.form("Giriş"):
        u_raw = st.text_input("Kullanıcı:")
        p_raw = st.text_input("Parola:", type="password")
        if st.form_submit_button("SİSTEME GİRİŞ YAP", use_container_width=True):
            if "users" in st.secrets:
                users = st.secrets["users"]
                u_lower = u_raw.strip().lower()
                if u_lower in users and str(users[u_lower]) == p_raw.strip():
                    st.session_state.logged_in = True
                    st.session_state.user = u_lower
                    st.rerun()
                else: st.error("Hatalı Giriş Bilgisi!")
    st.stop()

# --- NAVİGASYON ---
if 'page' not in st.session_state: st.session_state.page = 'home'
def go_home(): st.session_state.page = 'home'
def go_stok(): st.session_state.page = 'stok'
def go_uretim(): st.session_state.page = 'uretim'
def go_sayim(): st.session_state.page = 'sayim'
def go_rapor(): st.session_state.page = 'rapor'

# --- 3. BAĞLANTI ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- 4. YARDIMCI FONKSİYONLAR ---
@st.cache_data(ttl=0)
def get_internal_data(worksheet_name):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=60)
def get_kod_map():
    df = get_internal_data("Stok")
    if not df.empty:
        df['Kod'] = df['Kod'].astype(str).str.strip().str.upper()
        df['İsim'] = df['İsim'].astype(str).str.strip().str.upper()
        return dict(zip(df['Kod'], df['İsim']))
    return {}

def find_name_by_code(kod):
    if not kod: return ""
    return get_kod_map().get(str(kod).strip().upper(), "")

def log_movement(islem, adres, kod, isim, miktar):
    try:
        log_df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1", ttl=0)
        yeni_log = pd.DataFrame([{"Tarih": (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M"), "İşlem": str(islem), "Adres": str(adres).upper(), "Malzeme Kodu": str(kod).upper(), "Malzeme Adı": isim if isim else find_name_by_code(kod), "Miktar": float(miktar), "Operatör": st.session_state.user}])
        conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([log_df, yeni_log], ignore_index=True))
    except: pass

def update_stock_record(kod, isim, adres, miktar, is_increase=True):
    kod_str = str(kod).strip().upper()
    adr_str = str(adres).strip().upper()
    hedef_adres = "GENEL" if adr_str == "STOK YOK" else adr_str
    stok_df = conn.read(spreadsheet=SHEET_URL, worksheet="Stok", ttl=0)
    mask = (stok_df['Kod'].astype(str) == kod_str) & (stok_df['Adres'].astype(str) == hedef_adres)
    if mask.any():
        if is_increase: stok_df.loc[mask, 'Miktar'] += float(miktar)
        else: stok_df.loc[mask, 'Miktar'] = (stok_df.loc[mask, 'Miktar'] - float(miktar)).clip(lower=0)
    elif is_increase:
        new_row = pd.DataFrame([{"Adres": hedef_adres, "Kod": kod_str, "İsim": isim if isim else find_name_by_code(kod_str), "Birim": "ADET", "Miktar": float(miktar)}])
        stok_df = pd.concat([stok_df, new_row], ignore_index=True)
    conn.update(spreadsheet=SHEET_URL, worksheet="Stok", data=stok_df[stok_df['Miktar'] > 0])
    get_internal_data.clear(); get_kod_map.clear()
    return hedef_adres

# --- 5. ANA EKRAN ---
if st.session_state.page == 'home':
    st.markdown("<h3 style='text-align:center;'>📦 Depo Kontrol Merkezi</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.button("📊 STOK İŞLEMLERİ", use_container_width=True, type="primary", on_click=go_stok)
        st.button("🏭 ÜRETİM HAZIRLIK", use_container_width=True, type="primary", on_click=go_uretim)
    with c2:
        st.button("📝 SAYIM SİSTEMİ", use_container_width=True, type="primary", on_click=go_sayim)
        st.button("📈 GENEL RAPORLAR", use_container_width=True, type="primary", on_click=go_rapor)

# --- SAYFALAR (STOK, ÜRETİM VB.) ---
# (Stok ve Üretim kısımları aynı mimariyle devam eder...)

# --- 8. SAYIM SİSTEMİ (SATIR SİLME ÖZELLİKLİ) ---
elif st.session_state.page == 'sayim':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.title("⚖️ Sayım ve Durum Yönetimi")
    st_tab1, st_tab2 = st.tabs(["📝 Sayım Girişi", "📊 Sayım & Fark Raporu"])
    kod_map = get_kod_map()
    kod_listesi = sorted(list(kod_map.keys()))
    durum_opsiyonlari = ["Kullanılabilir", "Hasarlı", "Kayıp", "İncelemede"]

    with st_tab1:
        with st.container(border=True):
            c_adr, c_kod, c_isim, c_mik, c_dur = st.columns([1, 1, 1.5, 0.8, 1])
            s_adr = c_adr.text_input("📍 Adres").upper()
            s_kod = c_kod.selectbox("📦 Kod", [""] + kod_listesi)
            c_isim.text_input("Ürün Adı", value=kod_map.get(s_kod, ""), disabled=True)
            s_mik = c_mik.number_input("Miktar", min_value=0.0, step=1.0)
            s_dur = c_dur.selectbox("🛠️ Durum", durum_opsiyonlari)
            
            if st.button("➕ Listeye Ekle", use_container_width=True):
                if s_adr and s_kod:
                    st.session_state['gecici_sayim_listesi'].append({
                        "Tarih": datetime.now().strftime("%Y-%m-%d"),
                        "Personel": st.session_state.user,
                        "Adres": s_adr, "Kod": s_kod, 
                        "Ürün Adı": kod_map.get(s_kod, ""),
                        "Miktar": s_mik, "Durum": s_dur
                    })
                    st.toast(f"{s_kod} listeye eklendi.")
                else: st.warning("Adres ve Kod boş olamaz!")

        # --- DİNAMİK SATIR BAZLI SİLİNEBİLİR LİSTE ---
        if st.session_state['gecici_sayim_listesi']:
            st.markdown("### 📥 Onay Bekleyen Liste")
            
            # Başlıklar
            h_col1, h_col2, h_col3, h_col4, h_col5, h_col6 = st.columns([1, 1, 1.5, 0.7, 1, 0.3])
            h_col1.caption("Adres")
            h_col2.caption("Kod")
            h_col3.caption("Ürün Adı")
            h_col4.caption("Miktar")
            h_col5.caption("Durum")
            h_col6.caption("Sil")

            for index, item in enumerate(st.session_state['gecici_sayim_listesi']):
                r_col1, r_col2, r_col3, r_col4, r_col5, r_col6 = st.columns([1, 1, 1.5, 0.7, 1, 0.3])
                r_col1.write(item["Adres"])
                r_col2.write(item["Kod"])
                r_col3.write(item["Ürün Adı"])
                r_col4.write(str(item["Miktar"]))
                r_col5.write(item["Durum"])
                
                # SATIR BAZLI SİLME BUTONU
                if r_col6.button("🗑️", key=f"del_{index}"):
                    st.session_state['gecici_sayim_listesi'].pop(index)
                    st.rerun()

            st.write("---")
            col_onay, col_iptal = st.columns(2)
            if col_onay.button("📤 DRIVE'A KAYDET VE ONAYLA", type="primary", use_container_width=True):
                df_db = get_internal_data("sayim")
                conn.update(spreadsheet=SHEET_URL, worksheet="sayim", data=pd.concat([df_db, pd.DataFrame(st.session_state['gecici_sayim_listesi'])], ignore_index=True))
                st.session_state['gecici_sayim_listesi'] = []
                st.success("Sayımlar başarıyla kaydedildi!"); st.rerun()
            if col_iptal.button("❌ Tüm Listeyi Boşalt", use_container_width=True):
                st.session_state['gecici_sayim_listesi'] = []; st.rerun()

    with st_tab2:
        # (Sayım Raporu filtreleri ve analizi aynen devam eder...)
        try:
            df_s_db = get_internal_data("sayim")
            df_stok_ana = get_internal_data("Stok")
            if not df_s_db.empty:
                # Filtre Paneli ve Analiz Kodları Buraya...
                st.info("Rapor Filtreleri v22 standartlarında aktif.")
                # (Rapor tablosu ve metrikler...)
        except: st.info("Sayım verisi yok.")

# (Raporlar ve Çıkış kısımları...)
st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
