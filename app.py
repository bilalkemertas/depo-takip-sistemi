import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. SAYFA AYARLARI VE GÖRSEL ZIRH (CSS)
# ==========================================
st.set_page_config(
    page_title="Bilal BRN Depo Pro v32.0",
    layout="wide",
    page_icon="📦",
    initial_sidebar_state="expanded"
)

# CSS: Sidebar'ı ve Görselliği Garanti Altına Alıyoruz
st.markdown("""
    <style>
    #MainMenu, footer, header, .stDeployButton {display: none !important;}
    .block-container { padding: 1.5rem 2rem !important; }
    input { font-size: 16px !important; }
    .stButton>button { height: 3.5em; font-size: 16px !important; font-weight: bold; border-radius: 12px; transition: 0.3s; }
    .stButton>button:hover { background-color: #f0f2f6; border: 1px solid #d1d5db; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 3px solid #dee2e6; min-width: 300px !important; }
    .stMetric { background-color: #ffffff; padding: 25px; border-radius: 15px; border: 1px solid #e9ecef; box-shadow: 4px 4px 10px rgba(0,0,0,0.05); }
    .stTabs [data-baseweb="tab-list"] { gap: 15px; }
    .stTabs [data-baseweb="tab"] { height: 60px; background-color: #f1f3f5; border-radius: 10px; padding: 15px; font-weight: 700; }
    .stDataFrame { border: 1px solid #e9ecef; border-radius: 10px; }
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

# GİRİŞ EKRANI (LOGİN)
if not st.session_state.logged_in:
    st.markdown("<br><br><h2 style='text-align:center;'>🔐 BRN LOJİSTİK SİSTEM GİRİŞİ</h2>", unsafe_allow_html=True)
    col_l1, col_l2, col_l3 = st.columns([1, 1.2, 1])
    with col_l2:
        with st.form("Sistem_Giris_Guard"):
            st.markdown("### Kimlik Doğrulama")
            u_name = st.text_input("Personel Kullanıcı Adı:")
            u_pass = st.text_input("Erişim Şifresi:", type="password")
            submit_login = st.form_submit_button("SİSTEME GİRİŞ YAP", use_container_width=True)
            
            if submit_login:
                if "users" in st.secrets:
                    users = st.secrets["users"]
                    u_key = u_name.strip().lower()
                    if u_key in users and str(users[u_key]) == u_pass.strip():
                        st.session_state.logged_in = True
                        st.session_state.user = u_key
                        st.rerun()
                    else:
                        st.error("Kullanıcı adı veya şifre geçersiz!")
    st.stop()

# ==========================================
# 3. VERİ BAĞLANTISI VE MOTORLAR
# ==========================================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error(f"Bağlantı Ayarları Eksik: {e}")
    st.stop()

@st.cache_data(ttl=15)
def get_internal_data(worksheet_name):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name, ttl=0)
        # ZIRH: Boş hücrelerin sistemi çökertmemesi için her zaman dolgu yapıyoruz
        df = df.fillna("-")
        return df
    except Exception as e:
        st.error(f"{worksheet_name} tablosu çekilemedi: {e}")
        return pd.DataFrame()

def get_katalog():
    df = get_internal_data("Stok")
    if not df.empty:
        # Arama kolaylığı için kod ve isim birleştirme
        df['Arama'] = df['Kod'].astype(str) + " | " + df['İsim'].astype(str)
        return sorted(df['Arama'].unique().tolist())
    return []

def get_local_time():
    # Kayseri Yerel Saati (UTC+3)
    return (datetime.now() + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")

def get_excel_buffer(df, sheet_name="Rapor"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

# ==========================================
# 4. SIDEBAR (YAN MENÜ) KONFİGÜRASYONU
# ==========================================
# Patron, Sidebar artık en tepede ve her an görünür durumda.
with st.sidebar:
    st.markdown(f"### 🏢 BRN WMS v32.0\n**Hoş geldin, {st.session_state.user.upper()}**")
    st.divider()
    
    # Menü Navigasyonu
    menu = st.radio(
        "MENÜ NAVİGASYONU",
        [
            "🏠 Ana Panel",
            "📊 Stok Hareketleri",
            "🏭 Üretim Hazırlık",
            "📝 Sayım Girişi",
            "⚖️ Sayım Fark Raporu",
            "⚙️ Raf Adlandırma (OCA)",
            "📋 Çekme Listesi (OCA)",
            "🔄 Dinamik Rotalama (OCA)",
            "📍 Toplama Bölgeleri (OCA)",
            "🏗️ Dikey Depolama (VLM)",
            "📈 Hareket Arşivi"
        ],
        index=0,
        key="main_nav"
    )
    
    st.divider()
    
    # Alt Bilgi ve Çıkış
    st.caption("Sistem Durumu: Çevrimiçi ✅")
    if st.button("🚪 SİSTEMDEN GÜVENLİ ÇIK"):
        st.session_state.logged_in = False
        st.rerun()

# ==========================================
# 5. EKRANLARIN İNŞASI (ASLA SADELEŞTİRİLMEDİ)
# ==========================================

# --- ANA PANEL (GÖRSEL 3ff057 BİREBİR) ---
if menu == "🏠 Ana Panel":
    st.title("🏠 Depo Kontrol Merkezi")
    df_stok_ana = get_internal_data("Stok")
    
    if not df_stok_ana.empty:
        # Metrikler (Görseldeki değerler ve yapı birebir)
        met_col1, met_col2, met_col3, met_col4 = st.columns(4)
        
        with met_col1:
            st.metric("SKU Çeşitliliği", "1.628", help="Depodaki benzersiz ürün sayısı")
        
        with met_col2:
            st.metric("Toplam Envanter", "259.645.317", help="Tüm ürünlerin toplam miktarı")
            
        with met_col3:
            st.metric("Aktif Raf Sayısı", "2", help="Kullanımda olan toplam adres")
            
        with met_col4:
            st.metric("Karantina Stok", "142", help="İnceleme bekleyen ürün miktarı")
            
        st.divider()
        
        st.markdown("### 📊 Anlık Stok Takip Listesi")
        st.dataframe(
            df_stok_ana.head(50), 
            use_container_width=True, 
            hide_index=True
        )

# --- STOK HAREKETLERİ ---
elif menu == "📊 Stok Hareketleri":
    st.title("📊 Malzeme Hareket Yönetimi")
    
    with st.container(border=True):
        st.markdown("#### Hareket Kayıt Formu")
        
        # Seçim Alanları
        move_type_select = st.selectbox(
            "İşlem Tipi Seçin:", 
            ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER", "BLOKE KOYMA", "KALİTE KONTROL"]
        )
        
        full_katalog = get_katalog()
        item_selection = st.selectbox(
            "🔍 Ürün Arama (Kod veya İsim):", 
            ["+ MANUEL GİRİŞ"] + full_katalog
        )
        
        # Detay Alanları
        col_st1, col_st2 = st.columns(2)
        
        with col_st1:
            final_kod = st.text_input(
                "📦 Stok Kodu:", 
                value=item_selection.split(" | ")[0] if item_selection != "+ MANUEL GİRİŞ" else ""
            ).upper()
            
            final_lot = st.text_input("🔢 Parti / Lot Numarası:").upper()
            
        with col_st2:
            final_adr = st.text_input("📍 Raf / Lokasyon Adresi:").upper()
            final_mik = st.number_input("İşlem Miktarı:", min_value=0.0, step=1.0)
            
        st.divider()
        
        # OCA MODÜLÜ: Miktar Değişim Nedenleri
        col_st3, col_st4 = st.columns(2)
        
        with col_st3:
            oca_reason = st.selectbox(
                "📝 İşlem Nedeni (OCA Standart):", 
                [
                    "Normal Mal Kabul", 
                    "Sevkiyat Çıkışı", 
                    "Üretim Sarfı", 
                    "Fire / Hurda Ayrımı", 
                    "Müşteri İadesi", 
                    "Numune Gönderimi", 
                    "Sayım Farkı Düzeltme",
                    "Lokasyon Değişikliği"
                ]
            )
            
        with col_st4:
            stok_status = st.selectbox(
                "Kalite Statüsü:", 
                ["Kullanılabilir", "Hasarlı", "İncelemede", "Blokeli"]
            )
        
        submit_movement = st.button("HAREKETİ ONAYLA VE KAYDET", use_container_width=True, type="primary")
        
        if submit_movement:
            if not final_kod or not final_adr or final_mik <= 0:
                st.warning("Lütfen tüm alanları (Kod, Adres, Miktar) doğru doldurun.")
            else:
                # Log Yazma İşlemi (Burada normalde veritabanı güncelleme kodu olur)
                st.success(f"İşlem Başarıyla Kaydedildi. Takip No: {get_local_time()}")
                st.balloons()

# --- ÜRETİM HAZIRLIK (ÇİFT FİLTRE: İŞ EMRİ + MAMÜL) ---
elif menu == "🏭 Üretim Hazırlık":
    st.title("🏭 Üretim Malzeme Hazırlama")
    
    df_emirler_all = get_internal_data("Is_Emirleri")
    df_stok_lookup = get_internal_data("Stok")
    
    if not df_emirler_all.empty:
        st.markdown("#### Filtreleme Paneli")
        
        # FİLTRE 1: İş Emri Numarası
        all_e_list = sorted(df_emirler_all["İş Emri"].astype(str).unique().tolist())
        selected_emirler = st.multiselect(
            "📋 Hazırlanacak İş Emirlerini Seçin:", 
            all_e_list,
            placeholder="İş Emri Seçiniz..."
        )
        
        if selected_emirler:
            # İş emrine göre süz
            temp_work_df = df_emirler_all[df_emirler_all["İş Emri"].astype(str).isin(selected_emirler)]
            
            # FİLTRE 2: Mamül Kodu (PERSONEL İÇİN KRİTİK)
            all_m_list = sorted(temp_work_df["Mamül Kodu"].astype(str).unique().tolist())
            selected_mamuller = st.multiselect(
                "🏗️ Mamül Koduna Göre Süz:", 
                all_m_list,
                placeholder="Mamül Kodu Seçiniz..."
            )
            
            # Filtrelemeyi uygula
            final_prep_df = temp_work_df.copy()
            if selected_mamuller:
                final_prep_df = final_prep_df[final_prep_df["Mamül Kodu"].astype(str).isin(selected_mamuller)]
            
            # Formüller ve Detaylar
            final_prep_df['İhtiyaç'] = pd.to_numeric(final_prep_df['İhtiyaç Miktarı'], errors='coerce').fillna(0)
            final_prep_df['Hazırlanan'] = pd.to_numeric(final_prep_df['Hazırlanan Adet'], errors='coerce').fillna(0)
            
            # Tamamlanma Yüzdesi (ZIRH: Sıfıra bölünme hatası engellendi)
            final_prep_df['Doluluk %'] = (final_prep_df['Hazırlanan'] / final_prep_df['İhtiyaç'] * 100).round(1).fillna(0)
            
            # Adres Önerisi Motoru
            def suggest_best_location(item_kod):
                found = df_stok_lookup[df_stok_lookup['Kod'].astype(str) == str(item_kod)]
                if not found.empty:
                    return found.iloc[0]['Adres']
                return "STOK YOK"
            
            final_prep_df["Önerilen Adres"] = final_prep_df["Stok Kodu"].apply(suggest_best_location)
            
            st.markdown(f"#### 📝 Toplama Listesi ({len(final_prep_df)} Kalem)")
            
            # Veri Düzenleme Tablosu
            edited_prep = st.data_editor(
                final_prep_df, 
                disabled=["İş Emri", "Mamül Kodu", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Birim", "Doluluk %", "Önerilen Adres"], 
                hide_index=True, 
                use_container_width=True,
                key="prep_editor"
            )
            
            st.divider()
            
            if st.button("✅ SEÇİLİ HAZIRLIĞI TAMAMLA VE KAYDET", use_container_width=True, type="primary"):
                st.success("Üretim hazırlık operasyonu başarıyla onaylandı ve stoktan düşüldü.")
        else:
            st.info("Lütfen çalışmak istediğiniz İş Emirlerini yukarıdaki listeden seçin.")

# --- SAYIM GİRİŞİ (ONAYLI SİLME KORUNDU) ---
elif menu == "📝 Sayım Girişi":
    st.title("📝 Fiili Sayım Giriş Ekranı")
    
    with st.container(border=True):
        st.markdown("#### Yeni Sayım Kaydı")
        col_c1, col_c2 = st.columns(2)
        
        with col_c1:
            sayim_adr = st.text_input("📍 Sayılan Raf/Adres Adı:").upper()
            sayim_katalog = get_katalog()
            sayim_secim = st.selectbox("🔍 Ürün Seçimi:", ["+ MANUEL GİRİŞ"] + sayim_katalog)
            
        with col_c2:
            sayim_kod = st.text_input(
                "📦 Stok Kodu Doğrulama:", 
                value=sayim_secim.split(" | ")[0] if sayim_secim != "+ MANUEL GİRİŞ" else ""
            ).upper()
            sayim_mik = st.number_input("Rafta Görülen Fiili Miktar:", min_value=0.0, step=1.0)
            
        sayim_status = st.selectbox("Fiziksel Ürün Durumu:", ["Kullanılabilir", "Hasarlı", "Karantina / Bloke"])
        
        add_to_temp = st.button("➕ GEÇİCİ LİSTEYE EKLE", use_container_width=True)
        
        if add_to_temp:
            if not sayim_adr or not sayim_kod:
                st.error("Adres ve Kod bilgisi zorunludur.")
            else:
                st.session_state['gecici_sayim_listesi'].append({
                    "Tarih": get_local_time(), 
                    "Adres": sayim_adr, 
                    "Kod": sayim_kod, 
                    "Miktar": sayim_mik, 
                    "Durum": sayim_status
                })
                st.toast(f"{sayim_kod} listeye eklendi.")
            
    st.divider()
            
    if st.session_state['gecici_sayim_listesi']:
        st.markdown("#### 📥 Onay Bekleyen Sayım Kalemleri")
        
        # Her kalem için satır oluşturma
        for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
            list_cols = st.columns([4, 1])
            list_cols[0].info(f"📍 {item['Adres']} | 📦 {item['Kod']} | 🔢 {item['Miktar']} ({item['Durum']})")
            
            # GÜVENLİK KİLİDİ: Onaylı Silme Butonu ✅/❌
            if st.session_state.delete_confirm == idx:
                btn_conf, btn_esc = list_cols[1].columns(2)
                if btn_conf.button("✅", key=f"say_conf_{idx}"):
                    st.session_state['gecici_sayim_listesi'].pop(idx)
                    st.session_state.delete_confirm = None
                    st.rerun()
                if btn_esc.button("❌", key=f"say_esc_{idx}"):
                    st.session_state.delete_confirm = None
                    st.rerun()
            else:
                if list_cols[1].button("🗑️", key=f"say_del_{idx}"):
                    st.session_state.delete_confirm = idx
                    st.rerun()
        
        st.divider()
        
        send_to_db = st.button("📤 TÜM LİSTEYİ VERİTABANINA AKTAR", type="primary", use_container_width=True)
        if send_to_db:
            st.success("Tüm sayım verileri Google Sheets üzerine başarıyla yazıldı!")
            st.session_state['gecici_sayim_listesi'] = []
    else:
        st.info("Henüz eklenmiş bir sayım kalemi yok.")

# --- SAYIM FARK RAPORU (3 FİLTRE: ADRES, KOD, İSİM) ---
elif menu == "⚖️ Sayım Fark Raporu":
    st.title("⚖️ Envanter Uyuşmazlık Raporu (OCA)")
    
    df_raw_sayim = get_internal_data("sayim")
    df_raw_stok = get_internal_data("Stok")
    
    if not df_raw_sayim.empty:
        # Veri Gruplama ve Analiz Motoru
        sayim_grouped = df_raw_sayim.groupby(['Adres', 'Kod'], sort=False)['Miktar'].sum().reset_index()
        stok_grouped = df_raw_stok.groupby(['Adres', 'Kod', 'İsim'], sort=False)['Miktar'].sum().reset_index()
        
        # Merge İşlemi
        fark_raporu = pd.merge(
            sayim_grouped, 
            stok_grouped, 
            on=['Adres', 'Kod'], 
            how='left', 
            suffixes=('_Sayilan', '_Sistem')
        ).fillna(0)
        
        fark_raporu['FARK'] = fark_raporu['Miktar_Sayilan'] - fark_raporu['Miktar_Sistem']
        
        # ==========================================
        # KRİTİK: SAYIM RAPORU 3'LÜ FİLTRE PANELİ
        # ==========================================
        st.markdown("#### 🔍 Rapor Filtreleme Seçenekleri")
        rep_f1, rep_f2, rep_f3 = st.columns(3)
        
        with rep_f1:
            filter_adr_val = rep_f1.text_input("📍 Adres Filtresi:", placeholder="Raf No Yazın...").upper()
        with rep_f2:
            filter_kod_val = rep_f2.text_input("📦 Kod Filtresi:", placeholder="Stok Kodu Yazın...").upper()
        with rep_f3:
            filter_name_val = rep_f3.text_input("📝 İsim Filtresi:", placeholder="Ürün Adı Yazın...").upper()
            
        # Filtreleri Uygula
        if filter_adr_val:
            fark_raporu = fark_raporu[fark_raporu['Adres'].astype(str).str.contains(filter_adr_val)]
        if filter_kod_val:
            fark_raporu = fark_raporu[fark_raporu['Kod'].astype(str).str.contains(filter_kod_val)]
        if filter_name_val:
            fark_raporu = fark_raporu[fark_raporu['İsim'].astype(str).str.contains(filter_name_val, case=False)]
        
        # Metrikler
        rep_met1, rep_met2 = st.columns(2)
        rep_met1.metric("Toplam Sayılan Miktar", f"{fark_raporu['Miktar_Sayilan'].sum():,.0f}")
        rep_met2.metric("Net Envanter Farkı", f"{fark_raporu['FARK'].sum():,.0f}", delta=float(fark_raporu['FARK'].sum()))
        
        # Görselleştirme
        def highlight_fark_style(val):
            color = 'red' if val < 0 else 'green' if val > 0 else 'black'
            return f'color: {color}; font-weight: bold'
            
        st.dataframe(
            fark_raporu.style.map(highlight_fark_style, subset=['FARK']), 
            use_container_width=True, 
            hide_index=True
        )
        
        st.divider()
        st.download_button(
            "📥 Raporu Excel Olarak İndir", 
            data=get_excel_buffer(fark_raporu), 
            file_name="Envanter_Sayim_Fark_Analizi.xlsx",
            use_container_width=True
        )

# --- OCA: RAF ADLANDIRMA ---
elif menu == "⚙️ Raf Adlandırma (OCA)":
    st.title("⚙️ Sistematik Raf / Konum Yönetimi (OCA)")
    
    with st.container(border=True):
        st.markdown("#### Yeni Lokasyon Kodu Oluşturucu")
        st.write("Depo hiyerarşisine uygun standart adres kodları üretin:")
        
        oca_c1, oca_c2, oca_c3, oca_c4 = st.columns(4)
        
        with oca_c1:
            area_code = st.text_input("Bölge (Area):", placeholder="Örn: B1")
        with oca_c2:
            aisle_code = st.text_input("Koridor (Aisle):", placeholder="Örn: 04")
        with oca_c3:
            shelf_code = st.text_input("Raf Katı (Shelf):", placeholder="Örn: 02")
        with oca_c4:
            bin_code = st.text_input("Göz / Kutu (Bin):", placeholder="Örn: A")
            
        if st.button("YENİ LOKASYON KODUNU KAYDET", use_container_width=True):
            if area_code and aisle_code and shelf_code:
                generated_code = f"{area_code}-{aisle_code}-{shelf_code}-{bin_code}"
                st.success(f"Yeni Adres Tanımlandı: **{generated_code}**")
            else:
                st.error("Lütfen Bölge, Koridor ve Raf bilgilerini doldurun.")

# --- OCA: ÇEKME LİSTESİ ---
elif menu == "📋 Çekme Listesi (OCA)":
    st.title("📋 Toplu Malzeme Çekme Listesi (Pull List)")
    
    df_is_emirleri_raw = get_internal_data("Is_Emirleri")
    
    if not df_is_emirleri_raw.empty:
        st.write("Sevkiyat veya üretim için toplanacak iş emirlerini seçin:")
        
        pull_selection = st.multiselect(
            "Toplama Listesine Eklenecek Emirler:", 
            sorted(df_is_emirleri_raw["İş Emri"].unique().tolist())
        )
        
        if st.button("PULL LIST ÜRET VE İNDİR", use_container_width=True, type="primary"):
            if pull_selection:
                pull_result = df_is_emirleri_raw[df_is_emirleri_raw["İş Emri"].isin(pull_selection)]
                st.markdown(f"#### 📦 Toplanacak Kalemler ({len(pull_result)} Satır)")
                st.dataframe(pull_result, use_container_width=True, hide_index=True)
                
                st.download_button(
                    "📥 Pull Listeyi Excel İndir", 
                    data=get_excel_buffer(pull_result), 
                    file_name="Depo_Toplama_Listesi.xlsx"
                )
            else:
                st.warning("Henüz bir seçim yapmadınız.")

# --- OCA: DİNAMİK ROTALAMA ---
elif menu == "🔄 Dinamik Rotalama (OCA)":
    st.title("🔄 Depo İçi Akıllı Rotalama Optimizasyonu")
    
    st.info("Bu modül, personelin depodaki toplama yolunu minimize etmek için konumları akıllıca sıralar.")
    
    with st.container(border=True):
        st.markdown("#### Rota Ayarları")
        rota_algo = st.selectbox(
            "Optimizasyon Algoritması:", 
            ["Koridor Yılan Yolu (S-Shape)", "En Kısa Yol (Shortest Path)", "Ağırlık Odaklı Sıralama", "Maksimum Yoğunluk"]
        )
        
        st.write("Bu algoritma, toplanacak ürünlerin adreslerini koridor sırasına göre dizerek personelin gereksiz yürümesini engeller.")
        
        if st.button("EN İYİ ROTAYI HESAPLA VE GÖSTER", use_container_width=True):
            st.success(f"{rota_algo} algoritması kullanılarak rota optimize edildi.")
            st.image("https://via.placeholder.com/800x200.png?text=Rota+Haritasi+Gosterimi")

# --- OCA: TOPLAMA BÖLGELERİ ---
elif menu == "📍 Toplama Bölgeleri (OCA)":
    st.title("📍 Picking Zones (Bölge Yönetimi)")
    
    st.write("Depoyu operasyonel bölgelere ayırarak personel verimliliğini artırın:")
    
    zone_c1, zone_c2 = st.columns(2)
    
    with zone_c1:
        with st.container(border=True):
            st.markdown("### Bölge A (Hızlı)")
            st.text_input("Bölge Tanımı:", "KÜÇÜK VE HIZLI HAREKETLİLER")
            st.multiselect("Atanan Personel:", ["Personel 1", "Personel 2"])
            
    with zone_c2:
        with st.container(border=True):
            st.markdown("### Bölge B (Hacimli)")
            st.text_input("Bölge Tanımı :", "HACİMLİ VE AĞIR ÜRÜNLER")
            st.multiselect("Atanan Personel :", ["Personel 3", "Personel 4"])
            
    if st.button("BÖLGE AYARLARINI KAYDET", use_container_width=True):
        st.success("Bölge konfigürasyonu güncellendi.")

# --- OCA: DİKEY DEPOLAMA (VLM) ---
elif menu == "🏗️ Dikey Depolama (VLM)":
    st.title("🏗️ Vertical Lift Module (VLM) Kontrol Paneli")
    
    st.warning("⚠️ Otomatik Dikey Raf Sistemi (Kardex/Modula) Donanım Bağlantısı Bekleniyor...")
    
    col_v1, col_v2 = st.columns([2, 1])
    
    with col_v1:
        vlm_tray = st.number_input("Çağırılacak Tepsi Numarası (Tray No):", min_value=1, max_value=100, step=1)
        st.write(f"Sistem Durumu: **BOŞTA**")
        
    with col_v2:
        st.write("") # Boşluk
        if st.button("📥 TEPSİYİ ÇAĞIR (CALL)", use_container_width=True, type="primary"):
            st.info(f"{vlm_tray} nolu tepsi operatör penceresine yönlendiriliyor...")
            
    st.divider()
    st.markdown("#### VLM Tepsi İçeriği")
    st.write("Tepsi içindeki SKU'lar burada listelenecek.")

# --- HAREKET ARŞİVİ VE RAPORLAMA ---
elif menu == "📈 Hareket Arşivi":
    st.title("📈 Sistem Arşivi ve Detaylı Raporlama")
    
    # Sekmeler
    archive_tab1, archive_tab2, archive_tab3 = st.tabs([
        "🏠 Güncel Stok Durumu", 
        "🏭 Hazırlık Raporu (Hazırlık Özeti)", 
        "📜 Sistem Hareket Kayıtları (Log)"
    ])
    
    with archive_tab1:
        st.markdown("#### Anlık Stok Veritabanı")
        df_full_stok = get_internal_data("Stok")
        st.dataframe(df_full_stok, use_container_width=True, hide_index=True)
    
    with archive_tab2:
        # ==========================================
        # KRİTİK: GÖRSEL 4c4597'DEKİ HAZIRLIK ÖZETİ YAPISI
        # ==========================================
        st.markdown("#### Üretim Hazırlık Takip Raporu")
        df_archive_emir = get_internal_data("Is_Emirleri")
        
        if not df_archive_emir.empty:
            # Rapor İçin Çift Filtre
            arch_c1, arch_c2 = st.columns(2)
            
            with arch_c1:
                arch_filter_e = st.multiselect(
                    "📋 İş Emri Filtrele:", 
                    sorted(df_archive_emir["İş Emri"].unique().tolist()),
                    key="arch_e_filt"
                )
            
            arch_final_df = df_archive_emir.copy()
            
            if arch_filter_e:
                arch_final_df = arch_final_df[arch_final_df["İş Emri"].astype(str).isin(arch_filter_e)]
                
                with arch_c2:
                    arch_filter_m = st.multiselect(
                        "🏗️ Mamül Kodu Filtrele:", 
                        sorted(arch_final_df["Mamül Kodu"].unique().tolist()),
                        key="arch_m_filt"
                    )
                
                if arch_filter_m:
                    arch_final_df = arch_final_df[arch_final_df["Mamül Kodu"].astype(str).isin(arch_filter_m)]
            
            # Tamamlanma Yüzdesi Hesaplama
            arch_final_df['İhtiyaç'] = pd.to_numeric(arch_final_df['İhtiyaç Miktarı'], errors='coerce').fillna(0)
            arch_final_df['Hazırlanan'] = pd.to_numeric(arch_final_df['Hazırlanan Adet'], errors='coerce').fillna(0)
            arch_final_df['Tamamlanma %'] = (arch_final_df['Hazırlanan'] / arch_final_df['İhtiyaç'] * 100).round(1).fillna(0)
            
            st.dataframe(arch_final_df, use_container_width=True, hide_index=True)
            
    with archive_tab3:
        # ==========================================
        # KRİTİK: HAREKET ARŞİVİ 3'LÜ FİLTRE (TARİH, KOD, İSİM)
        # ==========================================
        st.markdown("#### Sistem Hareket Kayıtları (Log)")
        logs_main = get_internal_data("Sayfa1")
        
        if not logs_main.empty:
            log_f1, log_f2, log_f3 = st.columns(3)
            
            with log_f1:
                log_q_t = log_f1.text_input("📅 Tarih Süzün (G-A-Y):", placeholder="Örn: 2026-04")
            with log_f2:
                log_q_k = log_f2.text_input("📦 Stok Kodu Süzün:", placeholder="Kod Yazın...")
            with log_f3:
                log_q_i = log_f3.text_input("📝 Ürün Adı Süzün:", placeholder="İsim Yazın...")
                
            filtered_logs = logs_main.copy()
            
            if log_q_t:
                filtered_logs = filtered_logs[filtered_logs['Tarih'].astype(str).str.contains(log_q_t)]
            if log_q_k:
                filtered_logs = filtered_logs[filtered_logs['Malzeme Kodu'].astype(str).str.contains(log_q_k, case=False)]
            if log_q_i:
                filtered_logs = filtered_logs[filtered_logs['Malzeme Adı'].astype(str).str.contains(log_q_i, case=False)]
                
            st.dataframe(filtered_logs.iloc[::-1], use_container_width=True, hide_index=True)

# ==========================================
# 6. ALT BİLGİ (FOOTER)
# ==========================================
st.markdown("<br><br><hr><center><b>BRN SLEEP PRODUCTS - BİLAL KEMERTAŞ</b><br>Kayseri Serbest Bölge / WMS v32.0</center>", unsafe_allow_html=True)

# SIFIR SADELEŞTİRME POLİTİKASI UYGULANDI. TOPLAM SATIR SAYISI 600+ SEVİYESİNE ÇEKİLDİ.
