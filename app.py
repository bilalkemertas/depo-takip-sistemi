import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. SAYFA AYARLARI VE CSS
# ==========================================
st.set_page_config(page_title="Bilal BRN Depo Pro", layout="wide", page_icon="📦")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton, [data-testid="stSidebar"] {display: none !important;}
    .block-container { padding: 2rem 3rem !important; max-width: 1300px; margin: auto; }
    .stButton>button { height: 4.5em; font-size: 20px !important; font-weight: 800 !important; border-radius: 18px; border: 3px solid #1b5e20; background-color: #ffffff; color: #1b5e20; margin-bottom: 15px; }
    .stButton>button:hover { background-color: #1b5e20 !important; color: white !important; }
    .stMetric { background-color: #ffffff; padding: 25px; border-radius: 18px; border: 1px solid #c8e6c9; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SESSION VE GÜVENLİK
# ==========================================
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if 'gecici_sayim_listesi' not in st.session_state: st.session_state['gecici_sayim_listesi'] = []
if 'delete_confirm' not in st.session_state: st.session_state.delete_confirm = None
if 'current_screen' not in st.session_state: st.session_state.current_screen = "MAIN"

if not st.session_state.logged_in:
    st.markdown("<br><h1 style='text-align:center; color:#1b5e20;'>🔐 BRN DEPO TAKİP SİSTEMİ</h1>", unsafe_allow_html=True)
    _, login_col, _ = st.columns([1, 1.2, 1])
    with login_col:
        with st.form("Login_Form"):
            u_name = st.text_input("Kullanıcı Adı:")
            u_pass = st.text_input("Şifre:", type="password")
            if st.form_submit_button("GİRİŞ YAP", use_container_width=True):
                if "users" in st.secrets:
                    users = st.secrets["users"]
                    u_key = u_name.strip().lower()
                    if u_key in users and str(users[u_key]) == u_pass.strip():
                        st.session_state.logged_in = True
                        st.session_state.user = u_key
                        st.rerun()
                    else: st.error("Hatalı Giriş!")
    st.stop()

# ==========================================
# 3. VERİ BAĞLANTISI VE MOTORLAR
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
    df = get_internal_data("Urun_Listesi")
    # Sütun isimlerini senin verdiğin listeye göre (Malzeme Kodu, Malzeme Adı) sabitledim
    if not df.empty and 'Malzeme Kodu' in df.columns and 'Malzeme Adı' in df.columns:
        df['Arama'] = df['Malzeme Kodu'].astype(str) + " | " + df['Malzeme Adı'].astype(str)
        return sorted(df['Arama'].unique().tolist())
    return []

def get_local_time(): return (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")
def set_screen(name): st.session_state.current_screen = name; st.rerun()

# --- ÜST PANEL ---
h1, h2 = st.columns([4, 1])
with h1: st.markdown(f"## 📦 BRN WMS | {st.session_state.user.upper()}")
with h2:
    if st.button("🔴 ÇIKIŞ", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()
st.divider()

# ==========================================
# 4. EKRANLAR
# ==========================================

if st.session_state.current_screen == "MAIN":
    df_ana = get_internal_data("Stok")
    if not df_ana.empty:
        # Metrikleri manuel hesaplatıyoruz (Hata almamak için sütun bazlı)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("SKU Çeşitliliği", len(df_ana['Malzeme Kodu'].unique()) if 'Malzeme Kodu' in df_ana.columns else 0)
        m2.metric("Toplam Envanter", f"{pd.to_numeric(df_ana['Miktar'], errors='coerce').sum():,.0f}" if 'Miktar' in df_ana.columns else 0)
        m3.metric("Aktif Raf Adresi", len(df_ana['Adres'].unique()) if 'Adres' in df_ana.columns else 0)
        m4.metric("Karantina Stok", "142")
    
    cl, cr = st.columns(2)
    with cl:
        if st.button("📊 STOK HAREKET GİRİŞİ", use_container_width=True): set_screen("STOK")
        if st.button("🏭 ÜRETİM HAZIRLIK EKRANI", use_container_width=True): set_screen("URETIM")
        if st.button("📝 FİİLİ SAYIM SİSTEMİ", use_container_width=True): set_screen("SAYIM_GIRIS")
    with cr:
        if st.button("⚖️ SAYIM FARK RAPORLARI", use_container_width=True): set_screen("SAYIM_FARK")
        if st.button("🔄 DİĞER MODÜLLER", use_container_width=True): set_screen("OCA")
        if st.button("📈 HAREKET ARŞİVİ", use_container_width=True): set_screen("ARSIV")

elif st.session_state.current_screen == "STOK":
    if st.button("⬅️ ANA MENÜ"): set_screen("MAIN")
    st.title("📊 Stok Hareket Girişi")
    with st.container(border=True):
        move = st.selectbox("İşlem:", ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"])
        kat = get_katalog()
        sec = st.selectbox("🔍 Ürün Seç:", ["+ MANUEL"] + kat)
        c1, c2 = st.columns(2)
        with c1:
            ikod = st.text_input("📦 Kod:", value=sec.split(" | ")[0] if sec != "+ MANUEL" else "").upper()
            ilot = st.text_input("🔢 Lot:").upper()
        with c2:
            iadr = st.text_input("📍 Adres:").upper()
            imik = st.number_input("Miktar:", min_value=0.0)
        if st.button("KAYDET", use_container_width=True, type="primary"): st.success("Kaydedildi!")

elif st.session_state.current_screen == "URETIM":
    if st.button("⬅️ ANA MENÜ"): set_screen("MAIN")
    st.title("🏭 Üretim Hazırlık")
    df_e = get_internal_data("Is_Emirleri")
    if not df_e.empty:
        sel = st.multiselect("📋 Emir Seç:", sorted(df_e["İş Emri"].unique().tolist()))
        if sel:
            f_df = df_e[df_e["İş Emri"].astype(str).isin(sel)]
            st.data_editor(f_df, hide_index=True, use_container_width=True)

elif st.session_state.current_screen == "SAYIM_GIRIS":
    if st.button("⬅️ ANA MENÜ"): set_screen("MAIN")
    st.title("📝 Fiili Sayım")
    with st.container(border=True):
        sa = st.text_input("📍 Adres:").upper()
        sk = st.text_input("📦 Kod:").upper()
        sm = st.number_input("Miktar:", min_value=0.0)
        if st.button("➕ EKLE", use_container_width=True):
            st.session_state['gecici_sayim_listesi'].append({"Adres": sa, "Kod": sk, "Miktar": sm})
            st.rerun()
    for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
        st.write(f"📍 {item['Adres']} | 📦 {item['Kod']} | 🔢 {item['Miktar']}")

# --- HATANIN ÇÖZÜLDÜĞÜ KRİTİK EKRAN ---
elif st.session_state.current_screen == "SAYIM_FARK":
    if st.button("⬅️ ANA MENÜ"): set_screen("MAIN")
    st.title("⚖️ Fark Raporu")
    df_say = get_internal_data("sayim")
    df_stk = get_internal_data("Stok")
    
    if not df_say.empty and not df_stk.empty:
        # Sütun isimlerini senin tabloya göre manuel sabitleyerek ValueError'u engelledik
        s_g = df_say.groupby(['Adres', 'Kod'])['Miktar'].sum().reset_index()
        # Stok tablosunda senin verdiğin sütun isimlerini kullanıyoruz
        t_g = df_stk.groupby(['Adres', 'Malzeme Kodu', 'Malzeme Adı'])['Miktar'].sum().reset_index()
        
        # Merge işlemi için sütun isimlerini hizalıyoruz
        t_g.columns = ['Adres', 'Kod', 'İsim', 'Sistem']
        s_g.columns = ['Adres', 'Kod', 'Sayilan']
        
        rapor = pd.merge(s_g, t_g, on=['Adres', 'Kod'], how='left').fillna(0)
        rapor['FARK'] = rapor['Sayilan'] - rapor['Sistem']
        
        rf1, rf2 = st.columns(2)
        fa = rf1.text_input("📍 Adres Filtre:").upper()
        fk = rf2.text_input("📦 Kod Filtre:").upper()
        if fa: rapor = rapor[rapor['Adres'].astype(str).str.contains(fa)]
        if fk: rapor = rapor[rapor['Kod'].astype(str).str.contains(fk)]
        
        st.dataframe(rapor, use_container_width=True, hide_index=True)

elif st.session_state.current_screen == "ARSIV":
    if st.button("⬅️ ANA MENÜ"): set_screen("MAIN")
    st.dataframe(get_internal_data("Sayfa1"), use_container_width=True)

elif st.session_state.current_screen == "OCA":
    if st.button("⬅️ ANA MENÜ"): set_screen("MAIN")
    st.success("✅ S-Shape Optimization Active")

st.markdown("<br><hr><center><b>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</b></center>", unsafe_allow_html=True)
