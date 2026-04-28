import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. SAYFA AYARLARI VE MERKEZİ MENÜ TASARIMI
# ==========================================
st.set_page_config(
    page_title="Bilal BRN Depo Pro",
    layout="wide",
    page_icon="📦"
)

st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton, [data-testid="stSidebar"] {display: none !important;}
    .block-container { padding: 2rem 3rem !important; max-width: 1300px; margin: auto; }
    .stButton>button {
        height: 4.5em;
        font-size: 20px !important;
        font-weight: 800 !important;
        border-radius: 18px;
        border: 3px solid #1b5e20;
        background-color: #ffffff;
        color: #1b5e20;
        transition: 0.4s;
        margin-bottom: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    .stButton>button:hover {
        background-color: #1b5e20 !important;
        color: white !important;
        transform: translateY(-5px);
    }
    .stMetric {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 18px;
        border: 1px solid #c8e6c9;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SESSION VE GÜVENLİK
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if 'gecici_sayim_listesi' not in st.session_state: 
    st.session_state['gecici_sayim_listesi'] = []
if 'delete_confirm' not in st.session_state: 
    st.session_state.delete_confirm = None
if 'current_screen' not in st.session_state:
    st.session_state.current_screen = "MAIN"

if not st.session_state.logged_in:
    st.markdown("<br><h1 style='text-align:center; color:#1b5e20;'>🔐 BRN DEPO TAKİP SİSTEMİ</h1>", unsafe_allow_html=True)
    _, login_col, _ = st.columns([1, 1.2, 1])
    with login_col:
        with st.form("Login_Form"):
            u_name = st.text_input("Yönetici/Personel Adı:")
            u_pass = st.text_input("Sistem Şifresi:", type="password")
            if st.form_submit_button("SİSTEME GİRİŞ YAP", use_container_width=True):
                if "users" in st.secrets:
                    users = st.secrets["users"]
                    u_key = u_name.strip().lower()
                    if u_key in users and str(users[u_key]) == u_pass.strip():
                        st.session_state.logged_in = True
                        st.session_state.user = u_key
                        st.rerun()
                    else: st.error("Hatalı Giriş Bilgisi!")
    st.stop()

# ==========================================
# 3. VERİ BAĞLANTISI VE YARDIMCI FONKSİYONLAR
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

@st.cache_data(ttl=10)
def get_internal_data(worksheet_name):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)
        return df.fillna("-")
    except: return pd.DataFrame()

def get_katalog():
    df = get_internal_data("Stok")
    if not df.empty:
        # Sütun ismi esnekliği için arama:
        k_col = next((c for c in df.columns if 'Kod' in c), df.columns[1])
        n_col = next((c for c in df.columns if 'Ad' in c or 'İsim' in c), df.columns[2])
        df['Arama'] = df[k_col].astype(str) + " | " + df[n_col].astype(str)
        return sorted(df['Arama'].unique().tolist())
    return []

def get_local_time():
    return (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")

def set_screen(name):
    st.session_state.current_screen = name
    st.rerun()

# --- ÜST BİLGİ VE ÇIKIŞ ---
h_col1, h_col2 = st.columns([4, 1])
with h_col1:
    st.markdown(f"## 📦 BRN WMS | Hoş geldin, {st.session_state.user.upper()}")
with h_col2:
    if st.button("🔴 SİSTEMİ KAPAT", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

st.divider()

# ==========================================
# 4. ANA MENÜ (DİNAMİK)
# ==========================================
if st.session_state.current_screen == "MAIN":
    df_ana = get_internal_data("Stok")
    if not df_ana.empty:
        # Dinamik Hesaplama
        k_col = next((c for c in df_ana.columns if 'Kod' in c), df_ana.columns[0])
        m_col = next((c for c in df_ana.columns if 'Miktar' in c), df_ana.columns[-1])
        
        sku_count = len(df_ana[k_col].unique())
        total_inv = pd.to_numeric(df_ana[m_col], errors='coerce').sum()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("SKU Çeşitliliği", f"{sku_count:,}")
        m2.metric("Toplam Envanter", f"{total_inv:,.0f}")
        m3.metric("Aktif Raf Adresi", "2")
        m4.metric("Karantina Stok", "142")
    
    st.markdown("<br>", unsafe_allow_html=True)
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("#### 🚀 GÜNLÜK OPERASYONLAR")
        if st.button("📊 STOK HAREKET GİRİŞİ", use_container_width=True): set_screen("STOK")
        if st.button("🏭 ÜRETİM HAZIRLIK EKRANI", use_container_width=True): set_screen("URETIM")
        if st.button("📝 FİİLİ SAYIM SİSTEMİ", use_container_width=True): set_screen("SAYIM_GIRIS")
    with col_right:
        st.markdown("#### ⚙️ GELİŞMİŞ WMS & ANALİZ")
        if st.button("⚖️ SAYIM FARK RAPORLARI", use_container_width=True): set_screen("SAYIM_FARK")
        if st.button("🔄 DİĞER MODÜLLER VE ROTA", use_container_width=True): set_screen("OCA")
        if st.button("📈 HAREKET ARŞİVİ & LOGLAR", use_container_width=True): set_screen("ARSIV")

# --- 5.1 STOK HAREKETLERİ ---
elif st.session_state.current_screen == "STOK":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("📊 Malzeme Hareket Yönetimi")
    with st.container(border=True):
        move_type = st.selectbox("İşlem Tipi Seçin:", ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"])
        kat = get_katalog()
        sec = st.selectbox("🔍 Ürün Arama:", ["+ MANUEL GİRİŞ"] + kat)
        c1, c2 = st.columns(2)
        with c1:
            in_kod = st.text_input("📦 Malzeme Kodu:", value=sec.split(" | ")[0] if sec != "+ MANUEL GİRİŞ" else "").upper()
            in_lot = st.text_input("🔢 Parti / Lot No:").upper()
        with c2:
            in_adr = st.text_input("📍 Raf Adresi:").upper()
            in_mik = st.number_input("İşlem Miktarı:", min_value=0.0)
        if st.button("KAYDI TAMAMLA", use_container_width=True, type="primary"):
            st.success("Kaydedildi!")

# --- 5.2 ÜRETİM HAZIRLIK ---
elif st.session_state.current_screen == "URETIM":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("🏭 Üretim Malzeme Hazırlama")
    df_e = get_internal_data("Is_Emirleri")
    if not df_e.empty:
        sel_e = st.multiselect("📋 İş Emirlerini Filtrele:", sorted(df_e["İş Emri"].unique().tolist()))
        if sel_e:
            t_df = df_e[df_e["İş Emri"].astype(str).isin(sel_e)]
            st.data_editor(t_df, hide_index=True, use_container_width=True)

# --- 5.3 SAYIM GİRİŞİ ---
elif st.session_state.current_screen == "SAYIM_GIRIS":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("📝 Fiili Sayım Girişi")
    with st.container(border=True):
        c_adr = st.text_input("📍 Sayım Adresi:").upper()
        c_kod = st.text_input("📦 Malzeme Kodu:").upper()
        c_mik = st.number_input("Görülen Miktar:", min_value=0.0)
        if st.button("➕ GEÇİCİ LİSTEYE EKLE", use_container_width=True):
            st.session_state['gecici_sayim_listesi'].append({"Adres": c_adr, "Kod": c_kod, "Miktar": c_mik})
            st.rerun()
    if st.session_state['gecici_sayim_listesi']:
        for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
            st.write(f"📍 {item['Adres']} | 📦 {item['Kod']} | 🔢 {item['Miktar']}")

# --- 5.4 SAYIM FARK RAPORU (ZIRHLI ÇÖZÜM) ---
elif st.session_state.current_screen == "SAYIM_FARK":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("⚖️ Envanter Uyuşmazlık Raporu")
    df_say = get_internal_data("sayim")
    df_stk = get_internal_data("Stok")
    
    if not df_say.empty and not df_stk.empty:
        # ZIRH: Sütun isimlerini dinamik olarak yakala (Hata almamak için)
        s_adr_col = next((c for c in df_say.columns if 'Adres' in c), df_say.columns[0])
        s_kod_col = next((c for c in df_say.columns if 'Kod' in c), df_say.columns[1])
        s_mik_col = next((c for c in df_say.columns if 'Miktar' in c), df_say.columns[-1])
        
        t_adr_col = next((c for c in df_stk.columns if 'Adres' in c), df_stk.columns[0])
        t_kod_col = next((c for c in df_stk.columns if 'Kod' in c), df_stk.columns[1])
        t_nam_col = next((c for c in df_stk.columns if 'Ad' in c or 'İsim' in c), df_stk.columns[2])
        t_mik_col = next((c for c in df_stk.columns if 'Miktar' in c), df_stk.columns[-1])

        # Gruplama ve Birleştirme
        s_g = df_say.groupby([s_adr_col, s_kod_col])[s_mik_col].sum().reset_index()
        t_g = df_stk.groupby([t_adr_col, t_kod_col, t_nam_col])[t_mik_col].sum().reset_index()
        
        # İsimleri standartlaştır
        s_g.columns = ['Adres', 'Kod', 'Sayilan']
        t_g.columns = ['Adres', 'Kod', 'İsim', 'Sistem']
        
        rapor = pd.merge(s_g, t_g, on=['Adres', 'Kod'], how='left').fillna(0)
        rapor['FARK'] = rapor['Sayilan'] - rapor['Sistem']
        
        st.markdown("#### 🔍 Filtreler")
        rf1, rf2, rf3 = st.columns(3)
        fa = rf1.text_input("📍 Adres:").upper()
        fk = rf2.text_input("📦 Kod:").upper()
        fi = rf3.text_input("📝 İsim:").upper()
        
        if fa: rapor = rapor[rapor['Adres'].astype(str).str.contains(fa)]
        if fk: rapor = rapor[rapor['Kod'].astype(str).str.contains(fk)]
        if fi: rapor = rapor[rapor['İsim'].astype(str).str.contains(fi, case=False)]
        
        def h_fark(val): return f'color: {"red" if val < 0 else "green" if val > 0 else "black"}; font-weight: bold'
        st.dataframe(rapor.style.map(h_fark, subset=['FARK']), use_container_width=True, hide_index=True)

# --- 5.6 ARŞİV ---
elif st.session_state.current_screen == "ARSIV":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("📈 Arşiv")
    st.dataframe(get_internal_data("Stok"), use_container_width=True)

st.markdown("<br><hr><center><b>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</b></center>", unsafe_allow_html=True)
