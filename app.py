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

# --- 7. SAYIM SİSTEMİ ---
elif st.session_state.page == 'sayim':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.title("⚖️ Sayım ve Durum Yönetimi")
    
    st_tab1, st_tab2 = st.tabs(["📝 Sayım Girişi", "📊 Sayım & Fark Raporu"])
    kod_map = get_kod_map()
    durum_opsiyonlari = ["Kullanılabilir", "Hasarlı", "Kayıp", "İncelemede"]

    with st_tab1:
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

        if st.session_state['gecici_sayim_listesi']:
            st.markdown("### 📥 Onay Bekleyenler")
            for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
                col_txt, col_del = st.columns([0.85, 0.15])
                col_txt.write(f"**{item['Adres']}** | {item['Kod']} | {item['Miktar']} ad.")
                if col_del.button("🗑️", key=f"del_{idx}"):
                    st.session_state['gecici_sayim_listesi'].pop(idx); st.rerun()
            
            if st.button("📤 DRIVE'A KAYDET", type="primary", use_container_width=True):
                df_db = get_internal_data("sayim")
                conn.update(spreadsheet=SHEET_URL, worksheet="sayim", data=pd.concat([df_db, pd.DataFrame(st.session_state['gecici_sayim_listesi'])], ignore_index=True))
                st.session_state['gecici_sayim_listesi'] = []; st.success("Kaydedildi!"); st.rerun()

    with st_tab2:
        try:
            df_s_db = get_internal_data("sayim")
            df_stok_ana = get_internal_data("Stok")
            if not df_s_db.empty:
                df_s_db['Miktar'] = pd.to_numeric(df_s_db['Miktar'], errors='coerce').fillna(0)
                df_stok_ana['Miktar'] = pd.to_numeric(df_stok_ana['Miktar'], errors='coerce').fillna(0)
                
                with st.expander("🔍 Rapor Filtreleri", expanded=True):
                    f_tarih = st.selectbox("📅 Tarih Seç:", ["Tümü"] + sorted(df_s_db["Tarih"].astype(str).unique().tolist(), reverse=True))
                    c1, c2 = st.columns(2)
                    sel_k = c1.multiselect("📦 Kod:", sorted(df_s_db["Kod"].unique().tolist()))
                    sel_a = c2.multiselect("📍 Adres:", sorted(df_s_db["Adres"].unique().tolist()))

                act = df_s_db.copy()
                if f_tarih != "Tümü": act = act[act["Tarih"] == f_tarih]
                if sel_k: act = act[act["Kod"].isin(sel_k)]
                if sel_a: act = act[act["Adres"].isin(sel_a)]

                if not act.empty:
                    say_ozet = act.groupby(['Adres', 'Kod', 'Ürün Adı'])['Miktar'].sum().reset_index()
                    sis_ozet = df_stok_ana.groupby(['Adres', 'Kod'])['Miktar'].sum().reset_index()
                    res = pd.merge(say_ozet, sis_ozet, on=['Adres', 'Kod'], how='left').fillna(0)
                    res.columns = ["Adres", "Kod", "Ürün Adı", "Sayılan", "Sistem"]
                    res['FARK'] = res['Sayılan'] - res['Sistem']
                    
                    m1, m2 = st.columns(2)
                    m1.metric("Sayılan", f"{res['Sayılan'].sum():,.0f}")
                    m2.metric("Fark", f"{res['FARK'].sum():,.0f}", delta=int(res['FARK'].sum()))
                    st.dataframe(res, use_container_width=True, hide_index=True)
            else: st.info("Veri yok.")
        except Exception as e: st.error(f"Hata: {e}")

# --- 8. GENEL RAPORLAR ---
elif st.session_state.page == 'rapor':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    rt1, rt2 = st.tabs(["🏠 Stok Durumu", "📜 Hareket Arşivi"])
    with rt1: st.dataframe(get_internal_data("Stok"), use_container_width=True, hide_index=True)
    with rt2: st.dataframe(get_internal_data("Sayfa1").iloc[::-1], use_container_width=True, hide_index=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
