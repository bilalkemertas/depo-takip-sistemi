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

# --- 4. YARDIMCI FONKSİYONLAR & PERFORMANS MOTORU ---
@st.cache_data(ttl=0)
def get_internal_data(worksheet_name):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)
        if worksheet_name == "Is_Emirleri" and not df.empty:
            for col in ["Birim", "Mamül Kodu", "Mamül Adı"]:
                if col not in df.columns: df[col] = "ADET" if col == "Birim" else "-"
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60)
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
        df['Kod'] = df['Kod'].astype(str).str.strip().str.upper()
        df['İsim'] = df['İsim'].astype(str).str.strip().str.upper()
        df['Arama'] = df['Kod'] + " | " + df['İsim']
        liste = [x for x in df['Arama'].unique() if "|" in str(x) and "NAN" not in str(x)]
        return df, sorted(liste)
    return pd.DataFrame(), []

def find_name_by_code(kod):
    if not kod: return ""
    kod_str = str(kod).strip().upper()
    return get_kod_map().get(kod_str, "")

def get_local_time():
    return (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")

def check_address_stock(kod, adres, miktar):
    df = get_internal_data("Stok")
    if adres == "STOK YOK" or df.empty: return False, 0
    df['Kod'] = df['Kod'].astype(str).str.strip().str.upper()
    df['Adres'] = df['Adres'].astype(str).str.strip().str.upper()
    df['Miktar'] = pd.to_numeric(df['Miktar'], errors='coerce').fillna(0)
    
    kod_str = str(kod).strip().upper()
    adr_str = str(adres).strip().upper()
    current = df[(df['Kod'] == kod_str) & (df['Adres'] == adr_str)]['Miktar'].sum()
    return current >= miktar, current

def log_movement(islem, adres, kod, isim, miktar):
    try:
        log_df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1", ttl=0)
        yeni_log = pd.DataFrame([{
            "Tarih": get_local_time(),
            "İşlem": str(islem),
            "Adres": str(adres).upper(),
            "Malzeme Kodu": str(kod).upper(),
            "Malzeme Adı": isim if isim else find_name_by_code(kod),
            "Miktar": float(miktar),
            "Operatör": st.session_state.user
        }])
        conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([log_df, yeni_log], ignore_index=True))
    except Exception as e:
        st.error(f"Sisteme Log Yazılamadı: {e}")

def update_stock_record(kod, isim, adres, miktar, is_increase=True):
    kod_str = str(kod).strip().upper()
    adr_str = str(adres).strip().upper()
    hedef_adres = "GENEL" if adr_str == "STOK YOK" else adr_str
    
    stok_df = conn.read(spreadsheet=SHEET_URL, worksheet="Stok", ttl=0)
    stok_df['Kod'] = stok_df['Kod'].astype(str).str.strip().str.upper()
    stok_df['Adres'] = stok_df['Adres'].astype(str).str.strip().str.upper()
    stok_df['Miktar'] = pd.to_numeric(stok_df['Miktar'], errors='coerce').fillna(0)
    
    mask = (stok_df['Kod'] == kod_str) & (stok_df['Adres'] == hedef_adres)
    
    if mask.any():
        if is_increase: 
            stok_df.loc[mask, 'Miktar'] += float(miktar)
        else: 
            stok_df.loc[mask, 'Miktar'] = (stok_df.loc[mask, 'Miktar'] - float(miktar)).clip(lower=0)
    elif is_increase:
        gercek_isim = isim if isim else find_name_by_code(kod_str)
        new_row = pd.DataFrame([{"Adres": hedef_adres, "Kod": kod_str, "İsim": gercek_isim, "Birim": "ADET", "Miktar": float(miktar)}])
        stok_df = pd.concat([stok_df, new_row], ignore_index=True)
    
    stok_df = stok_df[stok_df['Miktar'] > 0]
    conn.update(spreadsheet=SHEET_URL, worksheet="Stok", data=stok_df)
    get_internal_data.clear(); get_kod_map.clear()
    return hedef_adres

# --- 5. ANA EKRAN ---
if st.session_state.page == 'home':
    st.markdown("<h3 style='text-align:center;'>📦 Depo Kontrol Merkezi</h3>", unsafe_allow_html=True)
    st.sidebar.info(f"👤 Personel: {st.session_state.user}")
    if st.sidebar.button("Güvenli Çıkış"): st.session_state.clear(); st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        st.button("📊 STOK İŞLEMLERİ", use_container_width=True, type="primary", on_click=go_stok)
        st.button("🏭 ÜRETİM HAZIRLIK", use_container_width=True, type="primary", on_click=go_uretim)
    with c2:
        st.button("📝 SAYIM SİSTEMİ", use_container_width=True, type="primary", on_click=go_sayim)
        st.button("📈 GENEL RAPORLAR", use_container_width=True, type="primary", on_click=go_rapor)

# --- 6. STOK İŞLEMLERİ (GİRİŞ/ÇIKIŞ/TRANSFER) ---
elif st.session_state.page == 'stok':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    t1, t2, t3 = st.tabs(["📥 Giriş/Çıkış", "🔄 Transfer", "🔍 Hızlı Sorgu"])
    stok_df_all, katalog_list = get_katalog()
    
    with t1:
        is_t = st.selectbox("İşlem:", ["GİRİŞ", "ÇIKIŞ"])
        sec = st.selectbox("Ürün Seçin:", ["+ MANUEL"] + katalog_list)
        kod = st.text_input("Kod:", value=sec.split(" | ")[0] if sec != "+ MANUEL" else "").strip().upper()
        isim = st.text_input("Ad:", value=find_name_by_code(kod)).strip().upper()
        adr = st.text_input("Adres:", value="GENEL").strip().upper()
        qty = st.number_input("Miktar:", min_value=0.1, step=1.0)
        if st.button("KAYDET"):
            if is_t == "ÇIKIŞ":
                ok, mev = check_address_stock(kod, adr, qty)
                if not ok: st.error(f"Yetersiz Stok! Mevcut: {mev}"); st.stop()
            update_stock_record(kod, isim, adr, qty, is_increase=(is_t == "GİRİŞ"))
            log_movement(is_t, adr, kod, isim, qty)
            st.success("Kaydedildi!")

    with t2:
        e_adr = st.text_input("Nereden (Adres):").strip().upper()
        y_adr = st.text_input("Nereye (Adres):").strip().upper()
        t_sec = st.selectbox("Ürün:", ["+ MANUEL"] + katalog_list, key="tr_s")
        t_kod = st.text_input("Ürün Kodu:", value=t_sec.split(" | ")[0] if t_sec != "+ MANUEL" else "").strip().upper()
        t_qty = st.number_input("Transfer Miktarı:", min_value=0.1, step=1.0)
        if st.button("TRANSFERİ ONAYLA"):
            ok, mev = check_address_stock(t_kod, e_adr, t_qty)
            if ok:
                ti = find_name_by_code(t_kod)
                update_stock_record(t_kod, ti, e_adr, t_qty, is_increase=False)
                update_stock_record(t_kod, ti, y_adr, t_qty, is_increase=True)
                log_movement("TRANSFER ÇIKIŞ", e_adr, t_kod, ti, t_qty)
                log_movement("TRANSFER GİRİŞ", y_adr, t_kod, ti, t_qty)
                st.success("Transfer Başarılı!")
            else: st.error(f"Stok Yok! Mevcut: {mev}")

    with t3:
        search = st.text_input("🔍 Kod veya İsim Ara:").strip().upper()
        if not stok_df_all.empty:
            df_v = stok_df_all.copy()
            if search: df_v = df_v[df_v['Kod'].str.contains(search, na=False) | df_v['İsim'].str.contains(search, na=False)]
            st.dataframe(df_v[["Adres", "Kod", "İsim", "Miktar"]], use_container_width=True, hide_index=True)

# --- 7. ÜRETİM HAZIRLIK ---
elif st.session_state.page == 'uretim':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    with st.expander("📥 İş Emri Yükle (Excel)"):
        f = st.file_uploader("Dosya Seç:", type=["xlsx"])
        if f:
            eno = f.name.split('.')[0]
            df_r = pd.read_excel(f, sheet_name="HAZIRLIK", skiprows=3)
            kc = next((c for c in df_r.columns if "STOK KOD" in str(c).upper()), None)
            ac = next((c for c in df_r.columns if "STOK AD" in str(c).upper()), None)
            mc = next((c for c in df_r.columns if "TOTAL" in str(c).upper()), None)
            if kc and ac and mc:
                df_r = df_r.dropna(subset=[kc])
                df_f = df_r[[kc, ac, mc]].copy()
                df_f.columns = ["Stok Kodu", "Stok Adı", "İhtiyaç Miktarı"]
                df_f.insert(0, "İş Emri", eno); df_f["Hazırlanan Adet"] = 0; df_f["Birim"] = "ADET"
                if st.button(f"{eno} Kaydet"):
                    old = get_internal_data("Is_Emirleri")
                    if not old.empty: old = old[old["İş Emri"] != eno]
                    conn.update(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", data=pd.concat([old, df_f], ignore_index=True))
                    st.success("Yüklendi!"); st.rerun()

    df_emirler = get_internal_data("Is_Emirleri")
    if not df_emirler.empty:
        s = st.selectbox("İş Emri Seç:", ["Seçiniz..."] + sorted(df_emirler["İş Emri"].unique().tolist()))
        if s != "Seçiniz...":
            df_is_emri = df_emirler[df_emirler["İş Emri"] == s].copy()
            df_prep = df_is_emri.groupby(['Stok Kodu', 'Stok Adı', 'Birim']).agg({'İhtiyaç Miktarı': 'sum', 'Hazırlanan Adet': 'sum'}).reset_index()
            ed = st.data_editor(df_prep, use_container_width=True, hide_index=True)
            if st.button("HAZIRLIĞI TAMAMLA"):
                for idx, row in ed.iterrows():
                    fark = float(row["Hazırlanan Adet"]) - float(df_prep.loc[idx, "Hazırlanan Adet"])
                    if fark > 0:
                        update_stock_record(row["Stok Kodu"], row["Stok Adı"], "GENEL", fark, is_increase=False)
                        log_movement(f"{s} ÜRETİM", "GENEL", row["Stok Kodu"], row["Stok Adı"], fark)
                st.success("İşlem Tamam!"); st.rerun()

# --- 8. SAYIM SİSTEMİ (YENİ ENTEGRE) ---
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
                        "Tarih": datetime.now().strftime("%d.%m.%Y"),
                        "Personel": st.session_state.user,
                        "Adres": s_adr, "Kod": s_kod, "Ürün Adı": kod_map.get(s_kod, ""),
                        "Miktar": s_mik, "Durum": s_dur
                    })
                    st.toast(f"{s_kod} eklendi.")
                else: st.warning("Eksik bilgi!")

        if st.session_state['gecici_sayim_listesi']:
            st.dataframe(pd.DataFrame(st.session_state['gecici_sayim_listesi']), use_container_width=True)
            col_onay, col_iptal = st.columns(2)
            if col_onay.button("📤 DRIVE'A KAYDET", type="primary", use_container_width=True):
                try:
                    df_gecici = pd.DataFrame(st.session_state['gecici_sayim_listesi'])
                    df_db = get_internal_data("sayim")
                    conn.update(spreadsheet=SHEET_URL, worksheet="sayim", data=pd.concat([df_db, df_gecici], ignore_index=True))
                    st.session_state['gecici_sayim_listesi'] = []
                    st.success("Kaydedildi!"); st.rerun()
                except Exception as e: st.error(f"Hata: {e}")
            if col_iptal.button("❌ Listeyi Temizle", use_container_width=True):
                st.session_state['gecici_sayim_listesi'] = []; st.rerun()

    with st_tab2:
        try:
            df_s_db = get_internal_data("sayim")
            df_stok_ana = get_internal_data("Stok")
            if not df_s_db.empty:
                df_stok_ana['Miktar'] = pd.to_numeric(df_stok_ana['Miktar'], errors='coerce').fillna(0)
                df_s_db['Miktar'] = pd.to_numeric(df_s_db['Miktar'], errors='coerce').fillna(0)
                
                sistem_ozet = df_stok_ana.groupby(['Adres', 'Kod', 'İsim'])['Miktar'].sum().reset_index()
                sistem_ozet.columns = ["Adres", "Kod", "Ürün Adı", "Sistem_Miktarı"]
                
                sayim_ozet = df_s_db.groupby(['Adres', 'Kod', 'Durum'])['Miktar'].sum().reset_index()
                sayim_ozet.columns = ["Adres", "Kod", "Durum", "Sayılan_Miktar"]
                
                f_df = pd.merge(sistem_ozet, sayim_ozet, on=['Adres', 'Kod'], how='outer').fillna(0)
                f_df['FARK'] = f_df['Sayılan_Miktar'] - f_df['Sistem_Miktarı']
                
                st.dataframe(f_df, use_container_width=True, hide_index=True)
                m1, m2, m3 = st.columns(3)
                m1.metric("Sistem Toplam", f"{f_df['Sistem_Miktarı'].sum():,.0f}")
                m2.metric("Sayılan Toplam", f"{f_df['Sayılan_Miktar'].sum():,.0f}")
                m3.metric("Net Fark", f"{f_df['FARK'].sum():,.0f}")
        except: st.info("Henüz sayım verisi bulunmuyor.")

# --- 9. RAPORLAR ---
elif st.session_state.page == 'rapor':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    rt1, rt2, rt3 = st.tabs(["🏠 Stok Durumu", "🏭 Hazırlık Takibi", "📜 Hareket Arşivi"])
    with rt1: st.dataframe(get_internal_data("Stok"), use_container_width=True, hide_index=True)
    with rt2:
        df_h = get_internal_data("Is_Emirleri")
        if not df_h.empty:
            summary = df_h.groupby('İş Emri')[['İhtiyaç Miktarı', 'Hazırlanan Adet']].sum().reset_index()
            summary['%'] = (summary['Hazırlanan Adet'] / summary['İhtiyaç Miktarı'] * 100).round(1)
            st.dataframe(summary, column_config={"%": st.column_config.ProgressColumn("İlerleme", format="%.1f%%", min_value=0, max_value=100)}, use_container_width=True, hide_index=True)
            st.divider()
            s_iş = st.selectbox("İş Emri Detay:", ["Seçiniz..."] + sorted(summary['İş Emri'].unique().tolist()))
            if s_iş != "Seçiniz...":
                detay = df_h[df_h['İş Emri'] == s_iş].copy()
                m_filtre = st.selectbox("Mamül Filtresi:", ["TÜMÜ"] + sorted(detay['Mamül Adı'].unique().tolist()))
                if m_filtre != "TÜMÜ": detay = detay[detay['Mamül Adı'] == m_filtre]
                st.dataframe(detay[["Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet"]], use_container_width=True, hide_index=True)
    with rt3:
        st.dataframe(get_internal_data("Sayfa1").iloc[::-1], use_container_width=True, hide_index=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
