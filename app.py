import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="BRN Depo Pro", layout="centered", page_icon="📦")

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
                u_lower = u_raw.strip().lower()
                if u_lower in users and str(users[u_lower]) == p_raw.strip():
                    st.session_state.logged_in = True
                    st.session_state.user = u_lower
                    st.rerun()
                else: st.error("Hatalı Giriş!")
            except: st.error("Secrets bulunamadı!")
    st.stop()

# --- 3. BAĞLANTI ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- 4. ENVANTER GÜNCELLEME FONKSİYONU (AYNI KALDI) ---
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
    
    stok_df = stok_df[stok_df['Miktar'] > 0]
    conn.update(spreadsheet=SHEET_URL, worksheet="Stok", data=stok_df)

# --- 5. HEADER ---
h1, h2, h3 = st.columns([0.8, 2, 0.8], vertical_alignment="center")
with h1: st.image("brn_logo.webp", width=55)
with h2: st.markdown(f"**👤 {st.session_state.user.upper()}**")
with h3: 
    if st.button("Çık"):
        st.session_state.logged_in = False
        st.rerun()

st.divider()

# --- 6. MODÜLLER ---
t1, t2, t3 = st.tabs(["📥 İşlem", "🔄 Transfer", "📊 Stok"])

with t1:
    with st.container(border=True):
        is_type = st.selectbox("İşlem:", ["GİRİŞ", "ÇIKIŞ"])
        adr = st.text_input("Adres:", value="GENEL", key="a1").strip().upper()
        kod = st.text_input("Kod:", key="b1").strip().upper()
        isim = st.text_input("İsim:", key="n1").strip().upper()
        c1, c2 = st.columns(2)
        with c1: unit = st.selectbox("Birim:", ["ADET", "METRE", "KG", "RULO"], key="u1")
        with c2: qty = st.number_input("Miktar:", min_value=0.1, value=1.0, key="m1")
        if st.button("KAYDI TAMAMLA", use_container_width=True, type="primary"):
            log_df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1")
            new_log = pd.DataFrame([{"Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "İşlem": is_type, "Adres": adr, "Malzeme Kodu": kod, "Malzeme Adı": isim, "Birim": unit, "Miktar": qty, "Operatör": st.session_state.user}])
            conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([log_df, new_log]))
            update_stock_record(kod, isim, adr, unit, qty, is_increase=(is_type == "GİRİŞ"))
            st.success("Kaydedildi!")

with t2:
    with st.container(border=True):
        st.subheader("Transfer")
        e_adr = st.text_input("Nereden:", key="ea2").strip().upper()
        y_adr = st.text_input("Nereye:", key="ya2").strip().upper()
        t_kod = st.text_input("Kod:", key="b2").strip().upper()
        t_qty = st.number_input("Miktar:", min_value=0.1, value=1.0, key="tm2")
        t_unit = st.selectbox("Birim:", ["ADET", "METRE", "KG", "RULO"], key="tu2")
        if st.button("TRANSFERİ ONAYLA", use_container_width=True, type="primary"):
            log_df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1")
            c_log = pd.DataFrame([{"Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "İşlem": "ÇIKIŞ", "Adres": e_adr, "Malzeme Kodu": t_kod, "Malzeme Adı": "TRANSFER", "Birim": t_unit, "Miktar": t_qty, "Operatör": st.session_state.user}])
            g_log = pd.DataFrame([{"Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "İşlem": "GİRİŞ", "Adres": y_adr, "Malzeme Kodu": t_kod, "Malzeme Adı": "TRANSFER", "Birim": t_unit, "Miktar": t_qty, "Operatör": st.session_state.user}])
            conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([log_df, c_log, g_log]))
            update_stock_record(t_kod, "TRANSFER", e_adr, t_unit, t_qty, is_increase=False)
            update_stock_record(t_kod, "TRANSFER", y_adr, t_unit, t_qty, is_increase=True)
            st.success("Transfer yapıldı.")

# --- 📊 STOK SEKİMESİ (YENİ MOCKUP - SADECE GÖRSEL GÜNCELLEME) ---
with t3:
    # Başlık ve Senkronizasyon Butonu Yan Yana
    st_col1, st_col2 = st.columns([1.4, 1], vertical_alignment="bottom")
    with st_col1:
        st.subheader("🔍 Mevcut Stok")
    with st_col2:
        sync_trigger = st.button("🔄 SENKRONİZE ET", use_container_width=True)

    # Filtreleme (Full Width)
    ara = st.text_input("Kod, İsim veya Adres Ara:", key="f_search").strip().upper()
    
    # Görüntüleme Butonu (Full Width)
    refresh_trigger = st.button("LİSTEYİ GÖRÜNTÜLE / YENİLE", use_container_width=True, type="primary")

    st.divider()
    
    # 1. SENKRONİZE ETME MANTIĞI
    if sync_trigger:
        with st.spinner("Geçmiş veriler hesaplanıyor..."):
            st.cache_data.clear()
            raw = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1", ttl=0)
            if not raw.empty:
                raw['Miktar'] = pd.to_numeric(raw['Miktar'], errors='coerce').fillna(0)
                raw['Net'] = raw.apply(lambda x: x['Miktar'] if x['İşlem'] == 'GİRİŞ' else (-x['Miktar'] if x['İşlem'] == 'ÇIKIŞ' else 0), axis=1)
                
                # Malzeme isimlerini eşleştirme (TRANSFER yazanları düzeltme)
                lookup_names = raw[raw['Malzeme Adı'] != 'TRANSFER'].sort_values('Tarih').groupby('Malzeme Kodu')['Malzeme Adı'].last().to_dict()
                raw['Malzeme Adı'] = raw['Malzeme Kodu'].map(lookup_names).fillna(raw['Malzeme Adı'])
                
                # Gruplandırma
                summary = raw.groupby(['Adres', 'Malzeme Kodu', 'Malzeme Adı', 'Birim'])['Net'].sum().reset_index()
                summary.columns = ['Adres', 'Kod', 'İsim', 'Birim', 'Miktar']
                summary = summary[summary['Miktar'] > 0]
                conn.update(spreadsheet=SHEET_URL, worksheet="Stok", data=summary)
                st.success("Senkronizasyon Başarılı!")

    # 2. GÖRÜNTÜLEME MANTIĞI (TAM GENİŞLİK)
    if refresh_trigger or ara:
        st.cache_data.clear()
        try:
            stok_data = conn.read(spreadsheet=SHEET_URL, worksheet="Stok", ttl=0)
            if not stok_data.empty:
                if ara:
                    stok_data = stok_data[(stok_data['Kod'].str.contains(ara, na=False)) | (stok_data['Adres'].str.contains(ara, na=False)) | (stok_data['İsim'].str.contains(ara, na=False))]
                # Filtrenin altındaki tüm alanı kullanır
                st.dataframe(stok_data, use_container_width=True, hide_index=True)
            else:
                st.warning("Stok sekmesi boş.")
        except:
            st.error("Stok sekmesine erişilemedi.")
