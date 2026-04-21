import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Bilal BRN Depo Pro", layout="centered", page_icon="📦")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton {display: none !important;}
    .block-container { padding: 0.5rem 0.5rem !important; }
    .stButton>button { height: 3em; font-size: 16px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. GÜVENLİK ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h3 style='text-align:center;'>🛡️ Bilal BRN Depo Giriş</h3>", unsafe_allow_html=True)
    with st.form("Giriş"):
        u_raw = st.text_input("Kullanıcı:")
        p_raw = st.text_input("Parola:", type="password")
        if st.form_submit_button("SİSTEME GİRİŞ YAP", use_container_width=True):
            if "users" not in st.secrets:
                st.error("Secrets ayarlarında [users] bloğu bulunamadı!")
            else:
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
def go_rapor(): st.session_state.page = 'rapor'

# --- 3. BAĞLANTI ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- 4. YARDIMCI FONKSİYONLAR ---
@st.cache_data(ttl=5)
def get_stok_data():
    return conn.read(spreadsheet=SHEET_URL, worksheet="Stok", ttl=0)

def urun_katalogu_getir():
    try:
        df = get_stok_data()
        if not df.empty:
            df['Arama'] = df['Kod'].astype(str) + " | " + df['İsim'].astype(str)
            return ["+ MANUEL GİRİŞ"] + sorted(df['Arama'].unique().tolist())
        return ["+ MANUEL GİRİŞ"]
    except: return ["+ MANUEL GİRİŞ"]

def check_address_stock(kod, adres, miktar):
    df = get_stok_data()
    df['Miktar'] = pd.to_numeric(df['Miktar'], errors='coerce').fillna(0)
    current = df[(df['Kod'] == kod) & (df['Adres'] == adres)]['Miktar'].sum()
    return current >= miktar, current

def update_stock_record(kod, isim, adres, birim, miktar, is_increase=True):
    try: stok_df = get_stok_data()
    except: stok_df = pd.DataFrame(columns=['Adres', 'Kod', 'İsim', 'Birim', 'Miktar'])
    
    miktar = float(miktar)
    stok_df['Miktar'] = pd.to_numeric(stok_df['Miktar'], errors='coerce').fillna(0)
    mask = (stok_df['Kod'] == kod) & (stok_df['Adres'] == adres) & (stok_df['Birim'] == birim)
    
    if mask.any():
        if is_increase: stok_df.loc[mask, 'Miktar'] += miktar
        else: stok_df.loc[mask, 'Miktar'] -= miktar
    elif is_increase:
        new_row = pd.DataFrame([{"Adres": adres, "Kod": kod, "İsim": isim, "Birim": birim, "Miktar": miktar}])
        stok_df = pd.concat([stok_df, new_row], ignore_index=True)
    
    conn.update(spreadsheet=SHEET_URL, worksheet="Stok", data=stok_df[stok_df['Miktar'] >= 0])

# --- 5. ANA EKRAN ---
if st.session_state.page == 'home':
    st.markdown("<h3 style='text-align:center;'>📦 Depo Kontrol Merkezi</h3>", unsafe_allow_html=True)
    st.button("📊 STOK İŞLEMLERİ", use_container_width=True, type="primary", on_click=go_stok)
    st.button("🏭 ÜRETİM HAZIRLIK", use_container_width=True, type="primary", on_click=go_uretim)
    st.button("📈 RAPORLAR", use_container_width=True, type="primary", on_click=go_rapor)

# --- 6. STOK İŞLEMLERİ (Önceki Fonksiyonellik Korundu) ---
elif st.session_state.page == 'stok':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    t1, t2 = st.tabs(["📥 Giriş/Çıkış", "🔄 Transfer"])
    katalog = urun_katalogu_getir()
    
    with t1:
        is_type = st.selectbox("İşlem:", ["GİRİŞ", "ÇIKIŞ"])
        secim = st.selectbox("Ürün Seç:", katalog)
        init_kod = secim.split(" | ")[0] if secim != "+ MANUEL GİRİŞ" else ""
        init_isim = secim.split(" | ")[1] if secim != "+ MANUEL GİRİŞ" else ""
        
        kod = st.text_input("Stok Kodu:", value=init_kod).strip().upper()
        isim = st.text_input("Stok Adı:", value=init_isim).strip().upper()
        adr = st.text_input("Adres:", value="GENEL").strip().upper()
        qty = st.number_input("Miktar:", min_value=0.1, value=1.0)
        
        if st.button("KAYDET", use_container_width=True, type="primary"):
            if is_type == "ÇIKIŞ":
                ok, mevcut = check_address_stock(kod, adr, qty)
                if not ok: st.error(f"Stok Yetersiz! Mevcut: {mevcut}"); st.stop()
            update_stock_record(kod, isim, adr, "ADET", qty, is_increase=(is_type == "GİRİŞ"))
            st.success("Başarılı!"); st.cache_data.clear()

    with t2:
        e_adr = st.text_input("Nereden:").strip().upper()
        y_adr = st.text_input("Nereye:").strip().upper()
        t_sec = st.selectbox("Ürün:", katalog, key="tr_sec")
        t_kod = t_sec.split(" | ")[0] if t_sec != "+ MANUEL GİRİŞ" else ""
        t_isim = t_sec.split(" | ")[1] if t_sec != "+ MANUEL GİRİŞ" else ""
        t_qty = st.number_input("Transfer Miktarı:", min_value=0.1)
        
        if st.button("TRANSFER ET", use_container_width=True, type="primary"):
            ok, mevcut = check_address_stock(t_kod, e_adr, t_qty)
            if ok:
                update_stock_record(t_kod, t_isim, e_adr, "ADET", t_qty, is_increase=False)
                update_stock_record(t_kod, t_isim, y_adr, "ADET", t_qty, is_increase=True)
                st.success("Transfer Edildi!"); st.cache_data.clear()
            else: st.error(f"Kaynakta stok yok! Mevcut: {mevcut}")

# --- 7. ÜRETİM HAZIRLIK (Gelişmiş Satır Bazlı Adresleme) ---
elif st.session_state.page == 'uretim':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("🏭 Üretim Malzeme Hazırlama")
    
    try:
        df_all = conn.read(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", ttl=0)
        emirler = ["Seçiniz..."] + sorted(df_all["İş Emri"].unique().tolist())
    except: emirler = ["Seçiniz..."]

    secim = st.selectbox("Hazırlanacak İş Emri:", emirler)
    
    if secim != "Seçiniz...":
        df_sub = df_all[df_all["İş Emri"] == secim].copy()
        
        # Eğer tabloda 'Alınan Adres' sütunu yoksa geçici olarak ekle
        if "Alınan Adres" not in df_sub.columns:
            df_sub["Alınan Adres"] = "GENEL"
        
        st.info("Her satırın 'Alınan Adres' ve 'Hazırlanan Adet' kısmını doldurup kaydedin.")
        
        edited = st.data_editor(
            df_sub, 
            disabled=["İş Emri", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı"], 
            hide_index=True,
            column_config={
                "Alınan Ades": st.column_config.TextColumn("Alınan Adres", help="Ürünü hangi raftan aldınız?"),
                "Hazırlanan Adet": st.column_config.NumberColumn("Hazırlanan", min_value=0)
            }
        )
        
        if st.button("TÜM LİSTEYİ KAYDET VE STOKLARI GÜNCELLE", use_container_width=True, type="primary"):
            hata_var = False
            islem_listesi = []

            for idx, row in edited.iterrows():
                # Sadece artan hazırlık miktarı kadar stoktan düşeceğiz
                eski_hazirlanan = float(df_sub.loc[idx, "Hazırlanan Adet"])
                yeni_hazirlanan = float(row["Hazırlanan Adet"])
                fark = yeni_hazirlanan - eski_hazirlanan
                
                if fark > 0:
                    adr = str(row["Alınan Adres"]).strip().upper()
                    kod = row["Stok Kodu"]
                    isim = row["Stok Adı"]
                    
                    ok, mevcut = check_address_stock(kod, adr, fark)
                    if not ok:
                        st.error(f"❌ DURDURULDU: {isim} için {adr} adresinde yeterli stok yok! (İstenen: {fark}, Mevcut: {mevcut})")
                        hata_var = True
                        break
                    islem_listesi.append((kod, isim, adr, fark))
            
            if not hata_var:
                # Stokları düş
                for k, i, a, f in islem_listesi:
                    update_stock_record(k, i, a, "ADET", f, is_increase=False)
                
                # İş emri tablosunu (Alınan Adres sütunu hariç) güncelle
                final_df = edited.drop(columns=["Alınan Adres"]) if "Alınan Adres" in edited.columns else edited
                df_all.update(final_df)
                conn.update(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", data=df_all)
                st.success("✅ Tüm liste başarıyla işlendi ve stoklar düşüldü!"); st.cache_data.clear()
                st.rerun()

# --- 8. RAPORLAR ---
elif st.session_state.page == 'rapor':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.subheader("📊 Depo & Üretim Raporu")
    
    t_s, t_e = st.tabs(["🏠 Stok Durumu", "🏭 İş Emirleri"])
    with t_s: st.dataframe(get_stok_data(), use_container_width=True, hide_index=True)
    with t_e:
        df_emir = conn.read(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", ttl=0)
        if not df_emir.empty:
            df_emir['%'] = (pd.to_numeric(df_emir['Hazırlanan Adet']) / pd.to_numeric(df_emir['İhtiyaç Miktarı']) * 100).round(1)
            st.dataframe(df_emir, hide_index=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
