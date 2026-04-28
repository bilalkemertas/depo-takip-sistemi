import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Bilal BRN Depo Pro", layout="centered", page_icon="📦")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton {display: none !important;}
    .block-container { padding: 0.5rem 0.5rem !important; }
    input { font-size: 16px !important; }
    .stButton>button { height: 3em; font-size: 16px !important; }
    [data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 10px; }
    @media (max-width: 640px) {
        .stMetric { padding: 5px !important; border: 1px solid #eee; margin-bottom: 5px; }
        .row-font { font-size: 12px !important; }
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. GÜVENLİK VE SESSION DURUMU ---
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
@st.cache_data(ttl=30)
def get_internal_data(worksheet_name):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)
        # BOŞ HÜCRE ZIRHI: Tüm boşlukları "-" yaparak tip hatalarını önler
        df = df.fillna("-")
        return df
    except:
        return pd.DataFrame()

def get_kod_map():
    df = get_internal_data("Stok")
    if not df.empty:
        df['Kod'] = df['Kod'].astype(str).str.strip().str.upper()
        df['İsim'] = df['İsim'].astype(str).str.strip().str.upper()
        return dict(zip(df['Kod'], df['İsim']))
    return {}

def get_katalog():
    df = get_internal_data("Stok")
    if not df.empty:
        df['Arama'] = df['Kod'].astype(str) + " | " + df['İsim'].astype(str)
        return sorted(df['Arama'].unique().tolist())
    return []

def get_local_time():
    return (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")

def get_excel_buffer(df, sheet_name="Rapor"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

# --- 5. ANA EKRAN ---
if st.session_state.page == 'home':
    st.markdown("<h3 style='text-align:center;'>📦 Depo Kontrol Merkezi</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.button("📊 STOK İŞLEMLERİ", use_container_width=True, type="primary", on_click=go_stok)
        st.button("🏭 ÜRETİM HAZIRLIK", use_container_width=True, type="primary", on_click=go_uretim)
    with c2:
        st.button("📝 SAYIM SİSTEMİ", use_container_width=True, type="primary", on_click=go_sayim)
        st.button("📈 RAPORLAR", use_container_width=True, type="primary", on_click=go_rapor)

# --- 6. STOK İŞLEMLERİ (Özet) ---
elif st.session_state.page == 'stok':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.info("Bu ekran giriş/çıkış ve transfer için hazır.")

# --- 7. ÜRETİM HAZIRLIK ---
elif st.session_state.page == 'uretim':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.info("İş emri hazırlık ekranı aktif.")

# --- 8. SAYIM SİSTEMİ (DÜZELTİLMİŞ) ---
elif st.session_state.page == 'sayim':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("⚖️ Sayım ve Fark Analizi")
    t1, t2 = st.tabs(["📝 Sayım Girişi", "📊 Fark Raporu"])

    with t1:
        with st.container(border=True):
            s_adr = st.text_input("📍 Adres:").upper()
            katalog = get_katalog()
            sec = st.selectbox("🔍 Ürün Seç:", ["+ MANUEL"] + katalog)
            k_i = sec.split(" | ")[0] if sec != "+ MANUEL" else ""
            s_kod = st.text_input("📦 Kod:", value=k_i).upper()
            s_mik = st.number_input("Miktar:", min_value=0.0, step=1.0)
            if st.button("➕ Listeye Ekle", use_container_width=True):
                st.session_state['gecici_sayim_listesi'].append({
                    "Tarih": get_local_time(), "Personel": st.session_state.user,
                    "Adres": s_adr, "Kod": s_kod, "Miktar": s_mik
                })
                st.toast("Listeye eklendi")
        
        if st.session_state['gecici_sayim_listesi']:
            st.dataframe(pd.DataFrame(st.session_state['gecici_sayim_listesi']), use_container_width=True)
            if st.button("📤 VERİTABANINA KAYDET", type="primary", use_container_width=True):
                eski = get_internal_data("sayim")
                yeni = pd.DataFrame(st.session_state['gecici_sayim_listesi'])
                conn.update(spreadsheet=SHEET_URL, worksheet="sayim", data=pd.concat([eski, yeni], ignore_index=True))
                st.session_state['gecici_sayim_listesi'] = []
                st.success("Başarıyla kaydedildi!"); st.rerun()

    with t2:
        df_sayim = get_internal_data("sayim")
        df_stok = get_internal_data("Stok")
        if not df_sayim.empty and not df_stok.empty:
            # SIRALAMA DÜZELTMESİ: Verileri string'e çevirip düzgünce grupluyoruz
            df_sayim['Kod'] = df_sayim['Kod'].astype(str)
            df_stok['Kod'] = df_stok['Kod'].astype(str)
            
            s_ozet = df_sayim.groupby(['Adres', 'Kod'])['Miktar'].sum().reset_index()
            st_ozet = df_stok.groupby(['Adres', 'Kod'])['Miktar'].sum().reset_index()
            
            rapor = pd.merge(s_ozet, st_ozet, on=['Adres', 'Kod'], how='outer', suffixes=('_Sayilan', '_Sistem')).fillna(0)
            rapor['FARK'] = rapor['Miktar_Sayilan'] - rapor['Miktar_Sistem']
            
            # RAPORU ADRESE GÖRE SIRALIYORUZ
            rapor = rapor.sort_values(by=['Adres', 'Kod'])
            
            st.metric("Toplam Sayım Farkı", f"{rapor['FARK'].sum():,.0f}")
            st.dataframe(rapor, use_container_width=True, hide_index=True)
            st.download_button("📥 Raporu İndir", data=get_excel_buffer(rapor), file_name="Sayim_Fark.xlsx")

# --- 9. RAPORLAR ---
elif st.session_state.page == 'rapor':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("📈 Genel Stok Raporu")
    st.dataframe(get_internal_data("Stok"), use_container_width=True, hide_index=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
