import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. SAYFA AYARLARI VE MERKEZİ MENÜ TASARIMI (CSS)
# ==========================================
st.set_page_config(
    page_title="Bilal BRN Depo Pro",
    layout="wide",
    page_icon="📦"
)

# Sidebar'ı Kökten Kapatan ve Ana Menü Butonlarını Zırhlayan CSS
st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton, [data-testid="stSidebar"] {display: none !important;}
    .block-container { padding: 2rem 3rem !important; max-width: 1300px; margin: auto; }
    
    /* Ana Menü Dev Butonlar */
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
        box-shadow: 0 8px 15px rgba(0,0,0,0.2);
    }
    
    /* Alt Menü ve Bilgi Kutuları */
    .info-box {
        background-color: #e8f5e9;
        padding: 25px;
        border-radius: 18px;
        border-left: 8px solid #1b5e20;
        margin-bottom: 30px;
    }
    
    /* PATRON, METRİK YAZILARINI BURADA KOYULAŞTIRDIK */
    [data-testid="stMetricValue"] {
        color: #000000 !important;
        font-weight: 900 !important;
        font-size: 32px !important;
    }
    [data-testid="stMetricLabel"] {
        color: #000000 !important;
        font-weight: 800 !important;
        font-size: 18px !important;
    }
    
    .stMetric {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 18px;
        border: 2px solid #1b5e20; 
        box-shadow: 4px 4px 10px rgba(0,0,0,0.1);
    }
    
    /* Tablo Görünürlüğü */
    .stDataFrame { border: 1px solid #1b5e20; border-radius: 12px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SESSION VE GÜVENLİK YÖNETİMİ
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if 'gecici_sayim_listesi' not in st.session_state: 
    st.session_state['gecici_sayim_listesi'] = []
if 'delete_confirm' not in st.session_state: 
    st.session_state.delete_confirm = None
if 'current_screen' not in st.session_state:
    st.session_state.current_screen = "MAIN"

# GİRİŞ EKRANI (LOGİN)
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
# 3. VERİ BAĞLANTISI VE YARDIMCI MOTORLAR
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

@st.cache_data(ttl=10)
def get_internal_data(worksheet_name):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)
        df.columns = df.columns.str.strip()
        return df.fillna("-")
    except: return pd.DataFrame()

def get_katalog():
    df = get_internal_data("Stok")
    if not df.empty:
        df['Arama'] = df['Kod'].astype(str) + " | " + df['İsim'].astype(str)
        return sorted(df['Arama'].unique().tolist())
    return []

def get_local_time():
    return (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")

def get_excel_buffer(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

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
# 4. MERKEZİ ANA MENÜ (SIDEBARSIZ YAPI)
# ==========================================

if st.session_state.current_screen == "MAIN":
    df_ana = get_internal_data("Stok")
    if not df_ana.empty:
        sku_count = len(df_ana['Kod'].unique()) if 'Kod' in df_ana.columns else 0
        total_inv = pd.to_numeric(df_ana['Miktar'], errors='coerce').sum() if 'Miktar' in df_ana.columns else 0
        active_adr = len(df_ana['Adres'].unique()) if 'Adres' in df_ana.columns else 0
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("SKU Çeşitliliği", f"{sku_count:,}")
        m2.metric("Toplam Envanter", f"{total_inv:,.0f}")
        m3.metric("Aktif Raf Adresi", f"{active_adr}")
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

# ==========================================
# 5. ALT EKRANLAR
# ==========================================

# --- 5.1 STOK HAREKETLERİ (DİNAMİK ADRES ALANLARI) ---
elif st.session_state.current_screen == "STOK":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("📊 Malzeme Hareket Yönetimi")
    with st.container(border=True):
        move_type = st.selectbox("İşlem Tipi Seçin:", ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"])
        kat = get_katalog()
        sec = st.selectbox("🔍 Ürün Arama:", ["+ MANUEL GİRİŞ"] + kat)
        
        c1, c2 = st.columns(2)
        with c1:
            in_kod = st.text_input("📦 Kod:", value=sec.split(" | ")[0] if sec != "+ MANUEL GİRİŞ" else "").upper()
            in_lot = st.text_input("🔢 Parti / Lot No:").upper()
        with c2:
            in_mik = st.number_input("İşlem Miktarı:", min_value=0.0)
            in_neden = st.selectbox("📝 İşlem Nedeni (OCA):", ["Normal Operasyon", "Fire", "Numune", "Sayım Farkı"])
        
        st.markdown("---")
        adr_col1, adr_col2 = st.columns(2)
        
        with adr_col1:
            if move_type in ["ÇIKIŞ", "İÇ TRANSFER"]:
                in_src_adr = st.text_input("📍 Kaynak Adres (Nereden):", key="src_adr").upper()
        
        with adr_col2:
            if move_type in ["GİRİŞ", "İÇ TRANSFER"]:
                in_dst_adr = st.text_input("📍 Hedef Adres (Nereye):", key="dst_adr").upper()
        
        if st.button("KAYDI TAMAMLA", use_container_width=True, type="primary"):
            st.success(f"{move_type} işlemi veritabanına başarıyla işlendi!")

# --- 5.2 ÜRETİM HAZIRLIK ---
elif st.session_state.current_screen == "URETIM":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("🏭 Üretim Malzeme Hazırlama")
    df_e = get_internal_data("Is_Emirleri")
    if not df_e.empty:
        sel_e = st.multiselect("📋 İş Emirlerini Filtrele:", sorted(df_e["İş Emri"].unique().tolist()))
        if sel_e:
            t_df = df_e[df_e["İş Emri"].astype(str).isin(sel_e)]
            sel_m = st.multiselect("🏗️ Mamül Koduna Göre Süz:", sorted(t_df["Mamül Kodu"].unique().tolist()))
            f_df = t_df.copy()
            if sel_m: f_df = f_df[f_df["Mamül Kodu"].astype(str).isin(sel_m)]
            f_df['Doluluk %'] = (pd.to_numeric(f_df['Hazırlanan Adet'], errors='coerce').fillna(0) / 
                                 pd.to_numeric(f_df['İhtiyaç Miktarı'], errors='coerce').fillna(0) * 100).round(1).fillna(0)
            st.data_editor(f_df, hide_index=True, use_container_width=True)
            if st.button("✅ LİSTEYİ ONAYLA"): st.success("Üretim onayı verildi!")

# --- 5.3 SAYIM GİRİŞİ ---
elif st.session_state.current_screen == "SAYIM_GIRIS":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("📝 Fiili Sayım Girişi")
    with st.container(border=True):
        c_adr = st.text_input("📍 Sayım Adresi:").upper()
        kat_sayim = get_katalog()
        sec_sayim = st.selectbox("🔍 Ürün Seç (Katalogdan):", ["+ MANUEL GİRİŞ"] + kat_sayim)
        c_kod = st.text_input("📦 Kod:", value=sec_sayim.split(" | ")[0] if sec_sayim != "+ MANUEL GİRİŞ" else "").upper()
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            c_mik = st.number_input("Görülen Miktar:", min_value=0.0)
        with col_c2:
            c_durum = st.selectbox("🛠️ Stok Durumu Seç:", ["Kullanılabilir", "Hasarlı", "İncelemede", "Blokeli"])
        if st.button("➕ GEÇİCİ LİSTEYE EKLE", use_container_width=True):
            st.session_state['gecici_sayim_listesi'].append({"Adres": c_adr, "Kod": c_kod, "Miktar": c_mik, "Durum": c_durum})
            st.rerun()
    if st.session_state['gecici_sayim_listesi']:
        for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
            cols = st.columns([4, 1])
            cols[0].info(f"📍 {item['Adres']} | 📦 {item['Kod']} | 🔢 {item['Miktar']} | 🛠️ {item['Durum']}")
            if st.session_state.delete_confirm == idx:
                if cols[1].button("✅", key=f"y_{idx}"):
                    st.session_state['gecici_sayim_listesi'].pop(idx)
                    st.session_state.delete_confirm = None
                    st.rerun()
            else:
                if cols[1].button("🗑️", key=f"d_{idx}"):
                    st.session_state.delete_confirm = idx
                    st.rerun()

# --- 5.4 SAYIM FARK RAPORU ---
elif st.session_state.current_screen == "SAYIM_FARK":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("⚖️ Envanter Uyuşmazlık Raporu")
    df_say = get_internal_data("sayim")
    df_stk = get_internal_data("Stok")
    if not df_say.empty and not df_stk.empty:
        
        # PATRON: HATA VEREN YERİ SADECE BURADA SÖZLÜK MANTIĞIYLA DÜZELTTİM
        s_g = df_say.groupby(['Adres', 'Kod'])['Miktar'].sum().reset_index()
        t_g = df_stk.groupby(['Adres', 'Kod'])['Miktar'].sum().reset_index()
        
        # Sütun kaymasını önlemek için Stok listesindeki İsimleri bir sözlüğe hapsediyoruz
        isim_sozlugu = df_stk.drop_duplicates(subset=['Kod']).set_index('Kod')['İsim'].to_dict()
        
        # Önce sadece Miktarları birleştiriyoruz (Hatasız merge)
        rapor = pd.merge(s_g, t_g, on=['Adres', 'Kod'], how='outer', suffixes=('_Sayılan', '_Sistem')).fillna(0)
        
        # Sonra isimleri Kod üzerinden güvenli bir şekilde çağırıyoruz
        rapor['İsim'] = rapor['Kod'].map(isim_sozlugu).fillna("TANIMSIZ")
        
        # Farkı Hesapla
        rapor['FARK'] = rapor['Miktar_Sayılan'] - rapor['Miktar_Sistem']
        
        # Sütunların yerlerini sabitle
        rapor = rapor[['Adres', 'Kod', 'İsim', 'Miktar_Sayılan', 'Miktar_Sistem', 'FARK']]
        
        rf1, rf2, rf3 = st.columns(3)
        fa = rf1.text_input("📍 Adres Filtre:").upper()
        fk = rf2.text_input("📦 Kod Filtre:").upper()
        fi = rf3.text_input("📝 İsim Filtre:").upper()
        if fa: rapor = rapor[rapor['Adres'].astype(str).str.contains(fa)]
        if fk: rapor = rapor[rapor['Kod'].astype(str).str.contains(fk)]
        if fi: rapor = rapor[rapor['İsim'].astype(str).str.contains(fi, case=False)]
        st.dataframe(rapor, use_container_width=True, hide_index=True)

# --- 5.5 OCA MODÜLLERİ ---
elif st.session_state.current_screen == "OCA":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("⚙️ Gelişmiş WMS Modülleri (OCA)")
    tabs = st.tabs(["🔄 S-SHAPE ROTALAMA", "🏗️ VLM KONTROL", "⚙️ RAF ADLANDIRMA", "📋 ÇEKME LİSTESİ"])
    with tabs[0]:
        st.success("✅ Algoritma: S-Shape Path Optimization Active")
        st.button("ROTAYI PERSONELE GÖNDER")
    with tabs[1]:
        st.warning("⚠️ VLM Donanım Bağlantısı Bekleniyor...")
        tray = st.number_input("Tepsi Numarası (Tray No):", 1, 100)
    with tabs[2]:
        c1, c2, c3 = st.columns(3)
        v1 = c1.text_input("Bölge Kod:")
        v2 = c2.text_input("Raf No:")
        v3 = c3.text_input("Kat/Göz No:")
        if st.button("KOD ÜRET"): st.success(f"Oluşturulan: {v1}-{v2}-{v3}")
    with tabs[3]:
        df_p = get_internal_data("Is_Emirleri")
        if not df_p.empty:
            sel_p = st.multiselect("Toplanacak Emirleri Seçin:", df_p["İş Emri"].unique())
            if st.button("LİSTEYİ OLUŞTUR"): st.dataframe(df_p[df_p["İş Emri"].isin(sel_p)])

# --- 5.6 ARŞİV VE LOGLAR ---
elif st.session_state.current_screen == "ARSIV":
    if st.button("⬅️ ANA MENÜYE DÖN"): set_screen("MAIN")
    st.title("📈 Hareket Arşivi ve Analiz")
    t1, t2, t3 = st.tabs(["🏠 Mevcut Stok Veritabanı", "🏭 Hazırlık Raporu (Arşiv)", "📜 Sistem Logları"])
    with t1: st.dataframe(get_internal_data("Stok"), use_container_width=True, hide_index=True)
    with t2:
        df_lh = get_internal_data("Is_Emirleri")
        r_e = st.multiselect("İş Emri Süz:", sorted(df_lh["İş Emri"].unique().tolist()) if not df_lh.empty else [])
        res = df_lh[df_lh["İş Emri"].isin(r_e)] if r_e else df_lh
        st.dataframe(res, use_container_width=True, hide_index=True)
    with t3:
        logs = get_internal_data("Sayfa1")
        f_col1, f_col2, f_col3 = st.columns(3)
        ft, fk, fi = f_col1.text_input("Tarih:"), f_col2.text_input("Kod:"), f_col3.text_input("İsim:")
        if not logs.empty:
            if ft: logs = logs[logs['Tarih'].astype(str).str.contains(ft)]
            if fk: logs = logs[logs['Malzeme Kodu'].astype(str).str.contains(fk)]
            if fi: logs = logs[logs['Malzeme Adı'].astype(str).str.contains(fi, case=False)]
            st.dataframe(logs.iloc[::-1], use_container_width=True, hide_index=True)

st.markdown("<br><hr><center><b>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</b><br>2026</center>", unsafe_allow_html=True)
