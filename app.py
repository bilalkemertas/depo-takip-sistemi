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
    /* Header'ı mobilde tek satıra zorla */
    div[data-testid="stHorizontalBlock"]:first-of-type {
        flex-wrap: nowrap !important;
        align-items: center !important;
    }
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
                u_lower = u_raw.strip().lower()
                if u_lower in users and str(users[u_lower]) == p_raw.strip():
                    st.session_state.logged_in = True
                    st.session_state.user = u_lower
                    st.rerun()
                else: st.error("Hatalı Giriş Bilgisi!")
            except: st.error("Secrets ayarları eksik!")
    st.stop()

# --- 3. BAĞLANTI ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- 4. AKILLI KATALOG FONKSİYONLARI ---
@st.cache_data(ttl=60)
def urun_katalogu_getir():
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet="Stok", ttl=0)
        if not df.empty:
            df['Kod'] = df['Kod'].fillna("KODSUZ").astype(str)
            df['İsim'] = df['İsim'].fillna("İSİMSİZ").astype(str)
            df['Arama'] = df['Kod'] + " | " + df['İsim']
            return ["+ YENİ / MANUEL GİRİŞ"] + sorted(df['Arama'].unique().tolist())
        return ["+ YENİ / MANUEL GİRİŞ"]
    except:
        return ["+ YENİ / MANUEL GİRİŞ"]

def update_stock_record(kod, isim, adres, birim, miktar, is_increase=True):
    try:
        stok_df = conn.read(spreadsheet=SHEET_URL, worksheet="Stok", ttl=0)
    except:
        stok_df = pd.DataFrame(columns=['Adres', 'Kod', 'İsim', 'Birim', 'Miktar'])
    
    miktar = float(miktar)
    if not stok_df.empty:
        stok_df['Miktar'] = pd.to_numeric(stok_df['Miktar'], errors='coerce').fillna(0)
        mask = (stok_df['Kod'] == kod) & (stok_df['Adres'] == adres) & (stok_df['Birim'] == birim)
        if mask.any():
            if is_increase: stok_df.loc[mask, 'Miktar'] += miktar
            else: stok_df.loc[mask, 'Miktar'] -= miktar
        else:
            if is_increase:
                new_row = pd.DataFrame([{"Adres": adres, "Kod": kod, "İsim": isim, "Birim": birim, "Miktar": miktar}])
                stok_df = pd.concat([stok_df, new_row], ignore_index=True)
    else:
        if is_increase:
            stok_df = pd.DataFrame([{"Adres": adres, "Kod": kod, "İsim": isim, "Birim": birim, "Miktar": miktar}])
    
    stok_df = stok_df[stok_df['Miktar'] >= 0]
    conn.update(spreadsheet=SHEET_URL, worksheet="Stok", data=stok_df)

# --- 5. HEADER (TEK SATIR) ---
h1, h2, h3 = st.columns([0.8, 2, 0.8], vertical_alignment="center")
with h1: st.image("brn_logo.webp", width=55)
with h2: st.markdown(f"<p style='text-align: center; margin: 0; font-size: 14px;'><b>👤 {st.session_state.user.upper()}</b></p>", unsafe_allow_html=True)
with h3: 
    if st.button("Çık", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

st.divider()

# --- 6. MODÜLLER ---
t1, t2, t3 = st.tabs(["📥 İşlem", "🔄 Transfer", "📊 Stok"])
arama_listesi = urun_katalogu_getir()

# --- TAB 1: GİRİŞ / ÇIKIŞ ---
with t1:
    with st.container(border=True):
        is_type = st.selectbox("İşlem:", ["GİRİŞ", "ÇIKIŞ"])
        adr = st.text_input("Adres:", value="GENEL", key="a1").strip().upper()
        
        secim = st.selectbox("🔍 Kayıtlı Ürün Ara:", arama_listesi, key="sec1")
        
        # Seçime göre UI ve Mantık ayrımı
        if secim == "+ YENİ / MANUEL GİRİŞ":
            kod = st.text_input("Kod:", key="b1", placeholder="KOD GİRİN...").strip().upper()
            isim = st.text_input("İsim:", key="n1", placeholder="ÜRÜN ADI GİRİN...").strip().upper()
        else:
            # Kutuları kilitler ve veriyi arkadan direkt alır, hata şansı bırakmaz.
            bolunmus = str(secim).split(" | ")
            kod = bolunmus[0].strip() if len(bolunmus) > 0 else ""
            isim = bolunmus[1].strip() if len(bolunmus) > 1 else ""
            
            st.text_input("Kod:", value=kod, disabled=True, key="b1_locked")
            st.text_input("İsim:", value=isim, disabled=True, key="n1_locked")
            
        c1, c2 = st.columns(2)
        with c1: unit = st.selectbox("Birim:", ["ADET", "METRE", "KG", "RULO"], key="u1")
        with c2: qty = st.number_input("Miktar:", min_value=0.1, value=1.0, key="m1")
        
        if st.button("KAYDI TAMAMLA", use_container_width=True, type="primary"):
            if kod and isim:
                log_df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1")
                new_log = pd.DataFrame([{"Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "İşlem": is_type, "Adres": adr, "Malzeme Kodu": kod, "Malzeme Adı": isim, "Birim": unit, "Miktar": qty, "Operatör": st.session_state.user}])
                conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([log_df, new_log]))
                update_stock_record(kod, isim, adr, unit, qty, is_increase=(is_type == "GİRİŞ"))
                st.success(f"{kod} başarıyla kaydedildi!")
                st.cache_data.clear()
            else: st.error("Lütfen Kod ve İsim girin!")

# --- TAB 2: TRANSFER ---
with t2:
    with st.container(border=True):
        st.subheader("Transfer")
        e_adr = st.text_input("Nereden:", key="ea2").strip().upper()
        y_adr = st.text_input("Nereye:", key="ya2").strip().upper()
        
        t_secim = st.selectbox("🔍 Ürün Ara:", arama_listesi, key="t_sec1")
        
        if t_secim == "+ YENİ / MANUEL GİRİŞ":
            t_kod = st.text_input("Kod:", key="b2", placeholder="KOD GİRİN...").strip().upper()
            t_isim = "TRANSFER"
        else:
            t_bolunmus = str(t_secim).split(" | ")
            t_kod = t_bolunmus[0].strip() if len(t_bolunmus) > 0 else ""
            t_isim = t_bolunmus[1].strip() if len(t_bolunmus) > 1 else "TRANSFER"
            
            st.text_input("Kod:", value=t_kod, disabled=True, key="b2_locked")
            
        t_qty = st.number_input("Miktar:", min_value=0.1, value=1.0, key="tm2")
        t_unit = st.selectbox("Birim:", ["ADET", "METRE", "KG", "RULO"], key="tu2")
        
        if st.button("TRANSFERİ ONAYLA", use_container_width=True, type="primary"):
            if t_kod and y_adr and e_adr:
                log_df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1")
                c_log = pd.DataFrame([{"Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "İşlem": "ÇIKIŞ", "Adres": e_adr, "Mal
