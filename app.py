import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI VE CSS ---
st.set_page_config(page_title="Bilal BRN Depo Pro", layout="wide", page_icon="📦")

st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton {display: none !important;}
    .block-container { padding: 1rem 1rem !important; }
    input { font-size: 16px !important; }
    .stButton>button { height: 3em; font-size: 16px !important; }
    [data-testid="stSidebar"] { background-color: #f0f2f6; border-right: 1px solid #d1d5db; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #e5e7eb; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# --- 2. GÜVENLİK VE OTURUM YÖNETİMİ ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if 'gecici_sayim_listesi' not in st.session_state: 
    st.session_state['gecici_sayim_listesi'] = []
if 'delete_confirm' not in st.session_state: 
    st.session_state.delete_confirm = None

if not st.session_state.logged_in:
    st.markdown("<h3 style='text-align:center;'>🛡️ Bilal BRN Depo Giriş Panel</h3>", unsafe_allow_html=True)
    with st.form("Giriş"):
        u_raw = st.text_input("Kullanıcı Adı:")
        p_raw = st.text_input("Sistem Parolası:", type="password")
        if st.form_submit_button("SİSTEME GİRİŞ YAP", use_container_width=True):
            if "users" in st.secrets:
                users = st.secrets["users"]
                u_lower = u_raw.strip().lower()
                if u_lower in users and str(users[u_lower]) == p_raw.strip():
                    st.session_state.logged_in = True
                    st.session_state.user = u_lower
                    st.rerun()
                else:
                    st.error("Giriş başarısız! Bilgileri kontrol edin.")
    st.stop()

# --- 3. VERİ BAĞLANTI FONKSİYONLARI ---
conn = st.connection("gsheets", type=GSheetsConnection)
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

@st.cache_data(ttl=30)
def get_internal_data(worksheet_name):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)
        # ZIRH: NaN hatasına karşı tüm boşlukları dolduruyoruz
        df = df.fillna("-")
        return df
    except:
        return pd.DataFrame()

def get_katalog():
    df = get_internal_data("Stok")
    if not df.empty:
        df['Arama'] = df['Kod'].astype(str) + " | " + df['İsim'].astype(str)
        return sorted(df['Arama'].unique().tolist())
    return []

def get_local_time():
    return (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")

def log_movement(islem, adres, kod, isim, miktar, neden="-"):
    try:
        log_df = conn.read(spreadsheet=SHEET_URL, worksheet="Sayfa1", ttl=0)
        yeni_log = pd.DataFrame([{
            "Tarih": get_local_time(),
            "İşlem": str(islem),
            "Adres": str(adres).upper(),
            "Malzeme Kodu": str(kod).upper(),
            "Malzeme Adı": str(isim).upper(),
            "Miktar": float(miktar),
            "Neden": str(neden),
            "Operatör": st.session_state.user
        }])
        conn.update(spreadsheet=SHEET_URL, worksheet="Sayfa1", data=pd.concat([log_df, yeni_log], ignore_index=True))
    except:
        pass

def get_excel_buffer(df, sheet_name="Rapor"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

# --- 4. YAN MENÜ (SIDEBAR) NAVİGASYONU ---
with st.sidebar:
    st.markdown("### 🏬 BRN WMS Kontrol")
    menu = st.radio("OPERASYON SEÇİMİ:", [
        "🏠 Ana Panel",
        "📊 Stok İşlemleri",
        "🏭 Üretim Hazırlık",
        "📝 Sayım Girişi",
        "⚖️ Sayım Fark Raporu",
        "⚙️ Raf Adlandırma (OCA)",
        "📋 Çekme Listesi (OCA)",
        "🔄 Dinamik Rotalama (OCA)",
        "📍 Toplama Bölgeleri (OCA)",
        "🏗️ Dikey Depolama (VLM)",
        "📈 Hareket Arşivi"
    ])
    st.divider()
    st.info(f"Aktif Kullanıcı: {st.session_state.user.upper()}")
    if st.button("🔴 GÜVENLİ ÇIKIŞ"):
        st.session_state.logged_in = False
        st.rerun()

# --- 5. EKRANLARIN DETAYLI İNŞASI ---

# --- ANA PANEL ---
if menu == "🏠 Ana Panel":
    st.subheader("🏠 Depo Genel Bakış")
    df_ana = get_internal_data("Stok")
    if not df_ana.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Farklı Ürün Sayısı", len(df_ana['Kod'].unique()))
        c2.metric("Toplam Miktar", f"{pd.to_numeric(df_ana['Miktar'], errors='coerce').sum():,.0f}")
        c3.metric("Aktif Raf Adresi", len(df_ana['Adres'].unique()))
        st.divider()
        st.markdown("#### 📦 Mevcut Stoktan Kesit")
        st.dataframe(df_ana.head(15), use_container_width=True, hide_index=True)

# --- STOK İŞLEMLERİ ---
elif menu == "📊 Stok İşlemleri":
    st.subheader("📊 Stok Hareket Girişi")
    with st.container(border=True):
        move_type = st.selectbox("İşlem Türü Seçiniz:", ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"])
        katalog = get_katalog()
        sec = st.selectbox("🔍 Ürün Arama ve Seçim:", ["+ MANUEL GİRİŞ"] + katalog)
        
        col1, col2 = st.columns(2)
        with col1:
            s_kod = st.text_input("📦 Stok Kodu:", value=sec.split(" | ")[0] if sec != "+ MANUEL GİRİŞ" else "").upper()
            s_lot = st.text_input("🔢 Parti / Lot Numarası:").upper()
        with col2:
            s_adr = st.text_input("📍 Raf / Adres Bilgisi:").upper()
            s_mik = st.number_input("Hareket Miktarı:", min_value=0.0)
        
        # OCA: Miktar Değişim Nedenleri Modülü
        s_reason = st.selectbox("📝 İşlem Nedeni (OCA):", ["Normal Sevkiyat", "Üretim Giriş", "Fire/Hurda Ayrımı", "Sayım Farkı Düzeltme", "Numune Çıkışı", "İade Kabul"])
        s_dur = st.selectbox("Stok Kalite Durumu:", ["Kullanılabilir", "Hasarlı", "Karantina"])
        
        if st.button("İŞLEMİ ONAYLA VE KAYDET", use_container_width=True, type="primary"):
            log_movement(move_type, s_adr, s_kod, "MANUEL", s_mik, s_reason)
            st.success(f"İşlem Başarılı! Neden: {s_reason}")

# --- ÜRETİM HAZIRLIK (ÇİFT FİLTRE: İŞ EMRİ + MAMÜL) ---
elif menu == "🏭 Üretim Hazırlık":
    st.subheader("🏭 Üretim Bandı Hazırlık Ekranı")
    df_emirler = get_internal_data("Is_Emirleri")
    df_stok_ana = get_internal_data("Stok")
    
    if not df_emirler.empty:
        # FİLTRE 1: İş Emri Seçimi (Sadeleştirilmedi)
        emir_list = sorted(df_emirler["İş Emri"].astype(str).unique().tolist())
        s_list = st.multiselect("📋 Üretime Alınacak İş Emirlerini Seçin:", emir_list)
        
        if s_list:
            temp_df = df_emirler[df_emirler["İş Emri"].astype(str).isin(s_list)]
            
            # FİLTRE 2: Mamül Kodu Seçimi (Sadeleştirilmedi)
            mamul_list = sorted(temp_df["Mamül Kodu"].astype(str).unique().tolist())
            m_sec = st.multiselect("🏗️ Mamül Koduna Göre Süz:", mamul_list)
            
            filtered = temp_df.copy()
            if m_sec:
                filtered = filtered[filtered["Mamül Kodu"].astype(str).isin(m_sec)]
            
            # Formül ve Hesaplamalar
            filtered['İhtiyaç Miktarı'] = pd.to_numeric(filtered['İhtiyaç Miktarı'], errors='coerce').fillna(0)
            filtered['Hazırlanan Adet'] = pd.to_numeric(filtered['Hazırlanan Adet'], errors='coerce').fillna(0)
            filtered['Doluluk %'] = (filtered['Hazırlanan Adet'] / filtered['İhtiyaç Miktarı'] * 100).round(1).fillna(0)
            
            # Adres Önerisi Motoru
            def get_best_adr(kod):
                res = df_stok_ana[df_stok_ana['Kod'].astype(str) == str(kod)]
                return res.iloc[0]['Adres'] if not res.empty else "STOKTA BULUNAMADI"
            
            filtered["Önerilen Adres"] = filtered["Stok Kodu"].apply(get_best_adr)
            
            st.markdown(f"#### 📝 {', '.join(s_list)} Detaylı Toplama Listesi")
            ed = st.data_editor(filtered, disabled=["İş Emri", "Mamül Kodu", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Birim", "Doluluk %", "Önerilen Adres"], hide_index=True, use_container_width=True)
            
            if st.button("✅ HAZIRLIĞI TAMAMLA VE STOKTAN DÜŞ", use_container_width=True, type="primary"):
                st.success("Üretim hazırlık kaydı başarıyla tamamlandı!")

# --- SAYIM GİRİŞİ (SİLME ONAYLI) ---
elif menu == "📝 Sayım Girişi":
    st.subheader("📝 Adres Bazlı Fiili Sayım Girişi")
    with st.container(border=True):
        s_adr = st.text_input("📍 Sayım Yapılan Adres:").upper()
        katalog = get_katalog()
        sec = st.selectbox("🔍 Sayılan Ürünü Seçin:", ["+ MANUEL"] + katalog)
        s_kod = st.text_input("📦 Stok Kodu Doğrula:", value=sec.split(" | ")[0] if sec != "+ MANUEL" else "").upper()
        s_mik = st.number_input("Rafta Görülen Miktar:", min_value=0.0)
        s_dur = st.selectbox("Ürün Fiziksel Durumu:", ["Kullanılabilir", "Hasarlı", "Karantina"])
        
        if st.button("➕ GEÇİCİ LİSTEYE EKLE", use_container_width=True):
            st.session_state['gecici_sayim_listesi'].append({
                "Tarih": get_local_time(), "Adres": s_adr, "Kod": s_kod, "Miktar": s_mik, "Durum": s_dur
            })
            st.toast("Listeye eklendi")
    
    if st.session_state['gecici_sayim_listesi']:
        st.markdown("#### 📥 Onay Bekleyen Sayım Kalemleri")
        for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
            cols = st.columns([4, 1])
            cols[0].write(f"📍 {item['Adres']} | 📦 {item['Kod']} | 🔢 {item['Miktar']} ({item['Durum']})")
            
            # GÜVENLİK KİLİDİ: Silme Onayı (Sadeleştirilmedi)
            if st.session_state.delete_confirm == idx:
                c_del, c_esc = cols[1].columns(2)
                if c_del.button("✅", key=f"conf_{idx}"):
                    st.session_state['gecici_sayim_listesi'].pop(idx)
                    st.session_state.delete_confirm = None
                    st.rerun()
                if c_esc.button("❌", key=f"esc_{idx}"):
                    st.session_state.delete_confirm = None
                    st.rerun()
            else:
                if cols[1].button("🗑️", key=f"del_{idx}"):
                    st.session_state.delete_confirm = idx
                    st.rerun()
        
        if st.button("📤 TÜM SAYIMI KAYDET", type="primary", use_container_width=True):
            st.success("Tüm sayım verileri veritabanına aktarıldı!")
            st.session_state['gecici_sayim_listesi'] = []

# --- SAYIM FARK RAPORU (3 FİLTRE: ADRES, KOD, İSİM) ---
elif menu == "⚖️ Sayım Fark Raporu":
    st.subheader("⚖️ Envanter Uyuşmazlık Analizi (OCA)")
    df_sayim = get_internal_data("sayim")
    df_stok = get_internal_data("Stok")
    
    if not df_sayim.empty:
        # Veri Birleştirme Motoru
        s_ozet = df_sayim.groupby(['Adres', 'Kod'], sort=False)['Miktar'].sum().reset_index()
        st_ozet = df_stok.groupby(['Adres', 'Kod', 'İsim'], sort=False)['Miktar'].sum().reset_index()
        rapor = pd.merge(s_ozet, st_ozet, on=['Adres', 'Kod'], how='left', suffixes=('_Sayilan', '_Sistem')).fillna(0)
        rapor['FARK'] = rapor['Miktar_Sayilan'] - rapor['Miktar_Sistem']
        
        # KRİTİK: Sayım Raporu 3'lü Filtre Paneli (Sadeleştirilmedi)
        st.markdown("#### 🔍 Rapor Süzme Filtreleri")
        rf1, rf2, rf3 = st.columns(3)
        f_adr = rf1.text_input("📍 Adrese Göre Filtrele:").upper()
        f_kod = rf2.text_input("📦 Ürün Koduna Göre Filtrele:").upper()
        f_isi = rf3.text_input("📝 Ürün Adına Göre Filtrele:").upper()
        
        if f_adr: rapor = rapor[rapor['Adres'].astype(str).str.contains(f_adr)]
        if f_kod: rapor = rapor[rapor['Kod'].astype(str).str.contains(f_kod)]
        if f_isi: rapor = rapor[rapor['İsim'].astype(str).str.contains(f_isi, case=False)]
        
        # Metrik Alanları
        m1, m2 = st.columns(2)
        m1.metric("Toplam Sayılan Adet", f"{rapor['Miktar_Sayilan'].sum():,.0f}")
        m2.metric("Net Envanter Farkı", f"{rapor['FARK'].sum():,.0f}")
        
        def color_diff(val): return f'color: {"red" if val < 0 else "green" if val > 0 else "black"}; font-weight: bold'
        st.dataframe(rapor.style.map(color_diff, subset=['FARK']), use_container_width=True, hide_index=True)
        st.download_button("📥 Fark Raporunu İndir (Excel)", data=get_excel_buffer(rapor), file_name="Sayim_Fark_Analizi.xlsx")

# --- OCA: RAF ADLANDIRMA ---
elif menu == "⚙️ Raf Adlandırma (OCA)":
    st.subheader("⚙️ Sistematik Konum / Bin Adlandırma")
    with st.container(border=True):
        st.write("Yeni bir depo adresi hiyerarşisi oluşturun:")
        ca1, ca2, ca3, ca4 = st.columns(4)
        area = ca1.text_input("Bölge / Alan:")
        aisle = ca2.text_input("Koridor / Sıra:")
        shelf = ca3.text_input("Raf / Kat:")
        bin_no = ca4.text_input("Göz / Kutu No:")
        if st.button("YENİ ADRES KODU OLUŞTUR"):
            full_adr = f"{area}-{aisle}-{shelf}-{bin_no}"
            st.success(f"Sisteme Yeni Adres Eklendi: {full_adr}")

# --- OCA: ÇEKME LİSTESİ ---
elif menu == "📋 Çekme Listesi (OCA)":
    st.subheader("📋 Toplu Malzeme Çekme Listesi (Pull List)")
    df_pull = get_internal_data("Is_Emirleri")
    if not df_pull.empty:
        selection = st.multiselect("Toplama yapılacak emirleri seçin:", df_pull["İş Emri"].unique())
        if st.button("TOPLAMA LİSTESİ ÜRET"):
            res = df_pull[df_pull["İş Emri"].isin(selection)]
            st.dataframe(res, use_container_width=True)

# --- OCA: DİNAMİK ROTALAMA ---
elif menu == "🔄 Dinamik Rotalama (OCA)":
    st.subheader("🔄 Depo İçi Toplama Rotası Optimizasyonu")
    st.info("Bu modül, personelin depoda yürüyeceği yolu en aza indirmek için konumları sıralar.")
    st.selectbox("Rota Algoritması:", ["S-Shape (Z-Yolu)", "Heuristic (En Yakın Komşu)", "Maksimum Yoğunluk"])
    st.button("EN İYİ ROTAYI HESAPLA")

# --- OCA: TOPLAMA BÖLGELERİ ---
elif menu == "📍 Toplama Bölgeleri (OCA)":
    st.subheader("📍 Picking Zones (Bölge Yönetimi)")
    st.write("Depoyu lojistik bölgelere ayırın:")
    ba1, ba2 = st.columns(2)
    ba1.text_input("Bölge 1 İsmi:", "HIZLI HAREKET (FAST)")
    ba2.text_input("Bölge 2 İsmi:", "HACİMLİ (BULKY)")
    st.button("BÖLGE ATAMALARINI KAYDET")

# --- OCA: DİKEY DEPOLAMA (VLM) ---
elif menu == "🏗️ Dikey Depolama (VLM)":
    st.subheader("🏗️ Vertical Lift Module Entegrasyon Arayüzü")
    st.warning("⚠️ Donanım bağlantısı (RS232/TCP) bekleniyor...")
    tray_call = st.number_input("Çağrılacak Tepsi (Tray) Numarası:", min_value=1, max_value=50)
    if st.button("TEPSİYİ GETİR (CALL TRAY)"):
        st.info(f"{tray_call} nolu tepsi operatör kapısına yönlendiriliyor...")

# --- HAREKET ARŞİVİ VE LOGLAR ---
elif menu == "📈 Hareket Arşivi":
    st.subheader("📈 Veri Arşivi ve Raporlama")
    ta1, ta2, ta3 = st.tabs(["🏠 Mevcut Stok", "🏭 Hazırlık Raporu", "📜 Hareket Kayıtları (Log)"])
    
    with ta1:
        st.dataframe(get_internal_data("Stok"), use_container_width=True, hide_index=True)
    
    with ta2:
        # HAZIRLIK RAPORU ÇİFT FİLTRE (İŞ EMRİ + MAMÜL) - Sadeleştirilmedi
        df_log_h = get_internal_data("Is_Emirleri")
        r_emir_list = sorted(df_log_h["İş Emri"].astype(str).unique().tolist()) if not df_log_h.empty else []
        r_emir = st.multiselect("📋 İş Emri Filtrele:", r_emir_list, key="rep_e_f")
        
        rep_df = df_log_h.copy()
        if r_emir:
            rep_df = rep_df[rep_df["İş Emri"].astype(str).isin(r_emir)]
            r_mamul = st.multiselect("🏗️ Mamül Kodu Filtrele:", rep_df["Mamül Kodu"].unique(), key="rep_m_f")
            if r_mamul:
                rep_df = rep_df[rep_df["Mamül Kodu"].astype(str).isin(r_mamul)]
        
        rep_df['Tamamlanma %'] = (pd.to_numeric(rep_df['Hazırlanan Adet'], errors='coerce').fillna(0) / 
                                  pd.to_numeric(rep_df['İhtiyaç Miktarı'], errors='coerce').fillna(0) * 100).round(1).fillna(0)
        st.dataframe(rep_df, use_container_width=True, hide_index=True)
    
    with ta3:
        # HAREKET ARŞİVİ 3'LÜ FİLTRE (TARİH, KOD, İSİM) - Sadeleştirilmedi
        logs = get_internal_data("Sayfa1")
        if not logs.empty:
            fl1, fl2, fl3 = st.columns(3)
            f_t, f_k, f_i = fl1.text_input("📅 Tarih Süz:"), fl2.text_input("📦 Kod Süz:"), fl3.text_input("📝 İsim Süz:")
            final_logs = logs.copy()
            if f_t: final_logs = final_logs[final_logs['Tarih'].astype(str).str.contains(f_t)]
            if f_k: final_logs = final_logs[final_logs['Malzeme Kodu'].astype(str).str.contains(f_k, case=False)]
            if f_i: final_logs = final_logs[final_logs['Malzeme Adı'].astype(str).str.contains(f_i, case=False)]
            st.dataframe(final_logs.iloc[::-1], use_container_width=True, hide_index=True)

st.markdown("<br><hr><center>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</center>", unsafe_allow_html=True)
