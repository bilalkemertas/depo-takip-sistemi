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
    /* Mobilde tabloların taşmasını önlemek için */
    .stDataFrame { width: 100% !important; overflow-x: auto !important; }
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

# Navigasyon Ayarları
if 'page' not in st.session_state: st.session_state.page = 'home'
def go_home(): st.session_state.page = 'home'
def go_sayim(): st.session_state.page = 'sayim'

# --- 3. BAĞLANTI & VERİ ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

@st.cache_data(ttl=0)
def get_internal_data(worksheet_name):
    try:
        return conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)
    except: return pd.DataFrame()

@st.cache_data(ttl=60)
def get_kod_map():
    df = get_internal_data("Stok")
    if not df.empty:
        return dict(zip(df['Kod'].astype(str), df['İsim'].astype(str)))
    return {}

# --- 4. ANA SAYFA ---
if st.session_state.page == 'home':
    st.title("📦 Kontrol Paneli")
    c1, c2 = st.columns(2)
    with c1: st.button("📝 SAYIM SİSTEMİ", use_container_width=True, type="primary", on_click=go_sayim)
    with c2: 
        if st.button("🚪 ÇIKIŞ YAP", use_container_width=True):
            st.session_state.clear()
            st.rerun()

# --- 5. SAYIM SİSTEMİ (HATASIZ VE MOBİL UYUMLU) ---
elif st.session_state.page == 'sayim':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.title("⚖️ Sayım ve Durum Yönetimi")
    
    # KRİTİK: st_tab2 değişkeninin tanımlandığı yer burasıdır!
    st_tab1, st_tab2 = st.tabs(["📝 Sayım Girişi", "📊 Sayım & Fark Raporu"])
    
    kod_map = get_kod_map()
    durum_opsiyonlari = ["Kullanılabilir", "Hasarlı", "Kayıp", "İncelemede"]

    with st_tab1:
        with st.container(border=True):
            s_adr = st.text_input("📍 Adres").upper()
            s_kod = st.selectbox("📦 Ürün Seçin", [""] + sorted(list(kod_map.keys())))
            st.info(f"Ürün Adı: {kod_map.get(s_kod, 'Seçilmedi')}")
            s_mik = st.number_input("Miktar", min_value=0.0, step=1.0)
            s_dur = st.selectbox("🛠️ Durum", durum_opsiyonlari)
            
            if st.button("➕ Listeye Ekle", use_container_width=True):
                if s_adr and s_kod:
                    st.session_state['gecici_sayim_listesi'].append({
                        "Tarih": (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d"),
                        "Personel": st.session_state.user,
                        "Adres": s_adr, "Kod": s_kod, 
                        "Ürün Adı": kod_map.get(s_kod, ""),
                        "Miktar": s_mik, "Durum": s_dur
                    })
                    st.toast("Eklendi!")
                else: st.warning("Eksik bilgi!")

        if st.session_state['gecici_sayim_listesi']:
            st.markdown("### 📥 Onay Bekleyenler")
            for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
                col_text, col_del = st.columns([0.8, 0.2])
                col_text.write(f"{item['Adres']} | {item['Kod']} | {item['Miktar']} Adet")
                if col_del.button("🗑️", key=f"del_{idx}"):
                    st.session_state['gecici_sayim_listesi'].pop(idx)
                    st.rerun()
            
            if st.button("📤 DRIVE'A KAYDET", type="primary", use_container_width=True):
                df_db = get_internal_data("sayim")
                yeni_df = pd.concat([df_db, pd.DataFrame(st.session_state['gecici_sayim_listesi'])], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet="sayim", data=yeni_df)
                st.session_state['gecici_sayim_listesi'] = []
                st.success("Kaydedildi!")
                st.rerun()

    with st_tab2:
        try:
            df_s_db = get_internal_data("sayim")
            df_stok_ana = get_internal_data("Stok")
            
            if not df_s_db.empty:
                df_s_db['Miktar'] = pd.to_numeric(df_s_db['Miktar'], errors='coerce').fillna(0)
                df_stok_ana['Miktar'] = pd.to_numeric(df_stok_ana['Miktar'], errors='coerce').fillna(0)
                
                with st.expander("🔍 Rapor Filtreleri", expanded=True):
                    f_t = st.selectbox("Tarih", ["Tümü"] + sorted(df_s_db["Tarih"].astype(str).unique().tolist(), reverse=True))
                    f_a = st.multiselect("Adres", sorted(df_s_db["Adres"].unique().tolist()))
                
                # Filtreleme
                act = df_s_db.copy()
                if f_t != "Tümü": act = act[act["Tarih"] == f_t]
                if f_a: act = act[act["Adres"].isin(f_a)]
                
                # Raporlama Mantığı
                say_ozet = act.groupby(['Adres', 'Kod', 'Ürün Adı'])['Miktar'].sum().reset_index()
                say_ozet.columns = ["Adres", "Kod", "Ürün Adı", "Sayılan"]
                
                sis_ozet = df_stok_ana.groupby(['Adres', 'Kod'])['Miktar'].sum().reset_index()
                sis_ozet.columns = ["Adres", "Kod", "Sistem"]
                
                res = pd.merge(say_ozet, sis_ozet, on=['Adres', 'Kod'], how='left').fillna(0)
                res['FARK'] = res['Sayılan'] - res['Sistem']
                
                # Mobilde Tabloyu Göster
                st.dataframe(res, use_container_width=True, hide_index=True)
                
                c_m1, c_m2 = st.columns(2)
                c_m1.metric("Toplam Sayılan", f"{res['Sayılan'].sum():,.0f}")
                c_m2.metric("Net Fark", f"{res['FARK'].sum():,.0f}", delta=int(res['FARK'].sum()))
            else:
                st.info("Veri yok.")
        except Exception as e: st.error(f"Hata: {e}")

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS</center>", unsafe_allow_html=True)
