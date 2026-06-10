import streamlit as st
import pandas as pd
import veritabani
import re
import math
import os
from datetime import datetime

# --- ZIRHLI EŞLEŞTİRME MATRİSİ SÜTUN AYRIŞTIRICI MOTORU ---
def find_eslesme_columns(columns):
    plaka_col = None
    plaka_adi_col = None
    blok_col = None
    blok_adi_col = None
    
    # 1. Öncelikli ve spesifik aramalar (Tam eşleşmeye yakın)
    # Blok Kodu (Bağlı Blok Stok Kodu)
    for c in columns:
        cu = str(c).upper().strip()
        if any(x in cu for x in ["BAĞLI BLOK STOK KODU", "BAĞLI BLOK KODU", "BAĞLI KOD", "BLOK KODU", "PARENT KOD"]):
            blok_col = c
            break
            
    # Blok Adı (Bağlı Blok Stok Adı)
    for c in columns:
        cu = str(c).upper().strip()
        if any(x in cu for x in ["BAĞLI BLOK STOK ADI", "BAĞLI BLOK ADI", "BAĞLI AD", "BLOK ADI", "PARENT AD"]):
            blok_adi_col = c
            break

    # Plaka Kodu (Semi-finished plate code / hammadde kodu)
    for c in columns:
        cu = str(c).upper().strip()
        if c == blok_col or c == blok_adi_col:
            continue
        if any(x in cu for x in ["HAMMADDE KODU", "HAMMADDE KOD", "YARI MAMUL KODU", "YARI MAMUL KOD", "YARIMAMUL KODU", "PLAKA KODU"]):
            plaka_col = c
            break
            
    # Plaka Adı (Semi-finished plate name / YARI MAMUL ADI)
    for c in columns:
        cu = str(c).upper().strip()
        if c == blok_col or c == blok_adi_col or c == plaka_col:
            continue
        if any(x in cu for x in ["YARI MAMUL ADI", "YARIMAMUL ADI", "PLAKA ADI"]):
            plaka_adi_col = c
            break

    # 2. Geniş aramalı ikincil öncelikli aramalar (Eğer hala bulunamadıysa)
    if not plaka_col:
        for c in columns:
            cu = str(c).upper().strip()
            if c == blok_col or c == blok_adi_col:
                continue
            if any(x in cu for x in ["STOK KODU", "STOK_KODU", "MALZEME KODU", "KOD", "CODE"]):
                plaka_col = c
                break
                
    if not plaka_adi_col:
        for c in columns:
            cu = str(c).upper().strip()
            if c == blok_col or c == blok_adi_col or c == plaka_col:
                continue
            if any(x in cu for x in ["STOK ADI", "STOK_ADI", "MALZEME ADI", "ADI", "NAME", "TANIM", "AÇIKLAMA", "ACIKLAMA"]):
                plaka_adi_col = c
                break

    # 3. Kalan boş sütunları güvenli ve benzersiz şekilde doldurma (Çakışma Koruması)
    all_cols = list(columns)
    assigned = [plaka_col, plaka_adi_col, blok_col, blok_adi_col]
    unused = [c for c in all_cols if c not in assigned]
    
    if not plaka_col and unused:
        plaka_col = unused.pop(0)
    if not plaka_adi_col and unused:
        plaka_adi_col = unused.pop(0)
    if not blok_col and unused:
        blok_col = unused.pop(0)
    if not blok_adi_col and unused:
        blok_adi_col = unused.pop(0)
        
    return plaka_col, plaka_adi_col, blok_col, blok_adi_col


# --- ZIRHLI İŞ EMRİ EXCEL SÜTUN AYRIŞTIRICI MOTORU ---
def find_work_order_columns(columns):
    col_sip_no = None
    col_plaka_kodu = None
    col_plaka_adi = None
    col_plaka_adet = None
    
    # 1. Sipariş No tespiti
    for c in columns:
        cu = str(c).upper().strip()
        if any(x in cu for x in ['SİPARİŞ NO', 'SIPARIS NO', 'SİPARİŞ_NO', 'ORDER NO', 'ORDER_NO']):
            col_sip_no = c
            break
            
    # 2. Plaka Kodu (Stok Kodu) tespiti
    for c in columns:
        cu = str(c).upper().strip()
        if cu in ['STOK KODU', 'STOK_KODU', 'PLAKA KODU', 'PLAKA_KODU']:
            col_plaka_kodu = c
            break
    if not col_plaka_kodu:
        for c in columns:
            cu = str(c).upper().strip()
            if any(x in cu for x in ['MALZEME KODU', 'ÜRÜN KODU', 'URUN KODU', 'KOD', 'CODE']):
                col_plaka_kodu = c
                break

    # 3. Plaka Adı (Stok Adı / Açıklama) tespiti
    for c in columns:
        cu = str(c).upper().strip()
        if cu in ['STOK ADI', 'STOK_ADI', 'PLAKA ADI', 'PLAKA_ADI']:
            col_plaka_adi = c
            break
    if not col_plaka_adi:
        for c in columns:
            cu = str(c).upper().strip()
            if any(x in cu for x in ['MALZEME ADI', 'ÜRÜN ADI', 'URUN_ADI', 'ADI', 'NAME', 'TANIM', 'AÇIKLAMA', 'ACIKLAMA']):
                col_plaka_adi = c
                break

    # 4. Plaka Adet (Miktar / Sipariş Miktarı) tespiti
    for c in columns:
        cu = str(c).upper().strip()
        if cu in ['SİPARİŞ MİKTARI', 'SIPARIS MIKTARI', 'MİKTAR', 'MIKTAR', 'ADET', 'PLAKA ADET', 'PLAKA_ADET']:
            col_plaka_adet = c
            break
    if not col_plaka_adet:
        for c in columns:
            cu = str(c).upper().strip()
            if any(x in cu for x in ['MİKTAR', 'MIKTAR', 'ADET', 'QTY', 'GELEN MİKTAR', 'GELEN_MIKTAR']):
                col_plaka_adet = c
                break

    # 5. Kalan boşlukları benzersiz şekilde doldurma
    all_cols = list(columns)
    assigned = [col_sip_no, col_plaka_kodu, col_plaka_adi, col_plaka_adet]
    unused = [c for c in all_cols if c not in assigned]
    
    if not col_sip_no and unused:
        col_sip_no = unused.pop(0)
    if not col_plaka_kodu and unused:
        col_plaka_kodu = unused.pop(0)
    if not col_plaka_adi and unused:
        col_plaka_adi = unused.pop(0)
    if not col_plaka_adet and unused:
        col_plaka_adet = unused.pop(0)
        
    return col_sip_no, col_plaka_kodu, col_plaka_adi, col_plaka_adet


def run_blok_kesim(conn):
    st.markdown("""
        <style>
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: #f0f2f6;
            border-radius: 4px;
            color: #31333F;
            font-weight: bold;
        }
        .stTabs [aria-selected="true"] {
            background-color: #ff4b4b !important;
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- MASTER DATA YÜKLEME (TÜRKÇE KARAKTER ZIRHLI & CACHED) ---
    if 'eslesme_df' not in st.session_state:
        df_eslesme = pd.DataFrame()
        
        # Önce XLSX desteği (Kullanıcı için en kolayı)
        if os.path.exists("eslesme_matrisi.xlsx"):
            try:
                df_eslesme = pd.read_excel("eslesme_matrisi.xlsx", dtype=str)
            except:
                pass
        
        # XLSX yoksa veya boşsa CSV dene (Noktalı virgül korumalı)
        if df_eslesme.empty and os.path.exists("eslesme_matrisi.csv"):
            encodings = ['utf-8', 'windows-1254', 'iso-8859-9', 'cp1254', 'utf-8-sig']
            separators = [';', ',', '\t']
            success = False
            for sep in separators:
                for enc in encodings:
                    try:
                        temp_df = pd.read_csv("eslesme_matrisi.csv", dtype=str, encoding=enc, sep=sep)
                        if len(temp_df.columns) > 1: # Doğru ayrıştırıldı!
                            df_eslesme = temp_df
                            success = True
                            break
                    except:
                        continue
                if success:
                    break
            
            # Eğer tek sütunlu bile olsa son çare oku
            if df_eslesme.empty:
                try:
                    df_eslesme = pd.read_csv("eslesme_matrisi.csv", dtype=str, encoding='utf-8')
                except:
                    pass

        if not df_eslesme.empty:
            df_eslesme.columns = [str(c).strip() for c in df_eslesme.columns]
            st.session_state.eslesme_df = df_eslesme
        else:
            st.warning("⚠️ 'eslesme_matrisi.xlsx' veya 'eslesme_matrisi.csv' dosyası bulunamadı ya da okunamadı! Eşleştirme devre dışı.")
            st.session_state.eslesme_df = pd.DataFrame()

    # --- PANDAS ONDALIK (.0) VE BARKOD KOD NORMALİZASYON MOTORU ---
    def normalize_code(val):
        if pd.isna(val) or str(val).strip() == "":
            return ""
        s = str(val).strip().upper()
        if s.endswith(".0"):
            s = s[:-2]
        return s

    # --- ZIRHLI AYIKLAMA MOTORU (ASLA NONE DÖNMEZ) ---
    def ayikla_karakter_ve_olcu(text):
        default_return = {"boy": 0.0, "en": 0.0, "kalinlik": 0.0, "karakter": str(text) if text else ""}
        if pd.isna(text) or str(text).strip() == "":
            return default_return
        
        t = str(text).upper().replace(",", ".").strip()
        olcu_uzun = re.search(r'(\d+(?:\.\d+)?)\s*[Xx]\s*(\d+(?:\.\d+)?)\s*[Xx]\s*(\d+(?:\.\d+)?)', t)
        if olcu_uzun:
            try:
                boy = float(olcu_uzun.group(1))
                en = float(olcu_uzun.group(2))
                kalinlik = float(olcu_uzun.group(3))
                start_idx = olcu_uzun.start()
                karakter = t[:start_idx].strip()
                karakter = re.sub(r'[^A-Z0-9\sĞÜŞİÖÇ]+$', '', karakter).strip()
                return {"boy": boy, "en": en, "kalinlik": kalinlik, "karakter": karakter}
            except:
                pass
        return default_return

    # --- VERİTABANI YÜKLEME VE KORUMALI KAYDETME MOTORLARI ---
    def load_sheet(sheet_name):
        try:
            df = veritabani.get_internal_data(sheet_name)
        except AttributeError:
            try:
                df = veritabani.get_data(sheet_name, conn)
            except Exception as e:
                df = None
        
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
        else:
            if sheet_name == "Sunger_Kesim":
                df = pd.DataFrame(columns=[
                    'Sipariş No', 'Plaka Kodu', 'Plaka Adı', 'Blok Kodu', 'Blok Adı', 
                    'Plaka Adet', 'Blok Adet', 'Üretilen Plaka Miktarı', 'Kesilen Blok Miktarı'
                ])
            else:
                df = pd.DataFrame()
        return df

    def save_sheet(sheet_name, df):
        # NaN / JSON Serialization Kalkanı
        df_clean = df.copy()
        for col in df_clean.columns:
            if df_clean[col].dtype == 'object':
                df_clean[col] = df_clean[col].fillna("")
            else:
                df_clean[col] = df_clean[col].fillna(0.0)
        df_clean = df_clean.replace([math.inf, -math.inf], 0.0)
        
        success = False
        try:
            veritabani.update_data(sheet_name, df_clean)
            success = True
        except TypeError:
            try:
                veritabani.update_data(sheet_name, df_clean, conn)
                success = True
            except Exception as e:
                st.error(f"❌ '{sheet_name}' kaydedilirken hata oluştu: {e}")
        except Exception as e:
            st.error(f"❌ '{sheet_name}' kaydedilirken hata oluştu: {e}")
        return success

    # --- CANLI BULUT VERİLERİNİ ÇEKELİM ---
    stok_df = load_sheet("Stok")
    har_df = load_sheet("Hareketler")
    sunger_kesim_df = load_sheet("Sunger_Kesim")

    # Stok tablosunu normalize etme ve başlıkları eşleme
    if not stok_df.empty:
        renames = {}
        for col in stok_df.columns:
            col_upper = col.upper()
            if col_upper in ['KOD', 'STOK KODU', 'STOK_KODU', 'MALZEME KODU', 'URUN KODU', 'ÜRÜN KODU']:
                renames[col] = 'Kod'
            elif col_upper in ['MİKTAR', 'MIKTAR', 'ADET', 'STOK ADET', 'STOK_MİKTARI']:
                renames[col] = 'Miktar'
            elif col_upper in ['ADRES', 'STOK ADRES', 'YER', 'DEPO_ADRES']:
                renames[col] = 'Adres'
            elif col_upper in ['MALZEME ADI', 'MALZEME_ADI', 'STOK ADI', 'STOK_ADI', 'İSİM', 'ISIM', 'ÜRÜN ADI', 'URUN_ADI']:
                renames[col] = 'Malzeme_Adi'
        if renames:
            stok_df = stok_df.rename(columns=renames)

    # Dinamik stok barkod sütunu tespiti
    stok_barkod_col = None
    for c in ['Barkod', 'BARKOD', 'Barkod No', 'Stok Barkodu', 'Tedarikçi Barkodu', 'Tedarikçi_Barkodu']:
        if c in stok_df.columns:
            stok_barkod_col = c
            break
    if stok_barkod_col is None and not stok_df.empty:
        for c in stok_df.columns:
            if 'barkod' in str(c).lower() or 'barcode' in str(c).lower():
                stok_barkod_col = c
                break
        if stok_barkod_col is None:
            stok_barkod_col = stok_df.columns[0]

    # --- BAĞIMSIZ PENCERE STATE TANIMI ---
    if 'blok_kesim_page' not in st.session_state:
        st.session_state.blok_kesim_page = 'menu'
    
    if 'operator_work_orders' not in st.session_state:
        st.session_state.operator_work_orders = []
    
    if 'current_work_order_idx' not in st.session_state:
        st.session_state.current_work_order_idx = None

    # =========================================================================
    # 0. ANA PANEL / BAĞIMSIZ MENÜ
    # =========================================================================
    if st.session_state.blok_kesim_page == 'menu':
        st.title("🧱 Blok ve Rulo Sünger Kesim Otomasyonu")
        st.write("Yönetmek istediğiniz bağımsız ekranı seçiniz:")
        st.markdown("---")

        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info("📋 **Planlama Penceresi**")
            st.write("Drive'da kayıtlı kesim planını inceleyin, yeni Excel planı yükleyip doğrudan buluta kaydedin.")
            if st.button("📋 PLAN & İŞ EMRİ YÜKLE", use_container_width=True):
                st.session_state.blok_kesim_page = 'plan'
                st.rerun()

        with col2:
            st.success("🧱 **Operatör Kesim Terminali**")
            st.write("Eşleşen plakalardan iş emri oluşturun, barkod okuyucu ile kesim yapın ve stokları güncelleyin.")
            if st.button("🧱 KESİM OPERASYONU", use_container_width=True, type="primary"):
                st.session_state.blok_kesim_page = 'kesim_menu'
                st.rerun()

        with col3:
            st.warning("📊 **Kesim Analiz Raporu**")
            st.write("İş emri bazlı üretim/kesim tamamlama yüzdelerini ve stok hareket geçmişini izleyin.")
            if st.button("📊 KESİM RAPORLARI", use_container_width=True):
                st.session_state.blok_kesim_page = 'rapor'
                st.rerun()

    # =========================================================================
    # EKRAN 1: PLAN & İŞ EMRİ YÜKLEME (DRIVE SENKRONİZE)
    # =========================================================================
    elif st.session_state.blok_kesim_page == 'plan':
        c_nav1, c_nav2 = st.columns([2.5, 7.5])
        with c_nav1:
            if st.button("⬅️ GERİ (ANA MENÜ)", use_container_width=True, key="back_from_plan"):
                st.session_state.blok_kesim_page = 'menu'
                st.rerun()
        with c_nav2:
            st.subheader("📋 Drive Sünger Kesim Planı Yönetimi")
        
        st.markdown("---")

        tab_view, tab_upload = st.tabs(["👁️ Aktif Kesim Planı (Drive)", "📤 Yeni İş Emri Yükle (Excel)"])

        # TAB 1: MEVCUT PLANI GÖRÜNTÜLEME
        with tab_view:
            if sunger_kesim_df.empty:
                st.info("ℹ️ Google Drive'da kayıtlı aktif bir kesim planı bulunamadı. Başlamak için 'Yeni İş Emri Yükle' sekmesini kullanın.")
            else:
                st.success("🔄 **Canlı Veri:** Google Drive'daki güncel 'Sunger_Kesim' planı listeleniyor.")
                
                # Sayısal sütunların dönüştürülmesi
                for col in ['Plaka Adet', 'Blok Adet', 'Üretilen Plaka Miktarı', 'Kesilen Blok Miktarı']:
                    if col in sunger_kesim_df.columns:
                        sunger_kesim_df[col] = pd.to_numeric(sunger_kesim_df[col], errors='coerce').fillna(0.0)

                # Kalan ihtiyaçların hesaplanması
                sunger_kesim_df['Kalan Plaka Adet'] = sunger_kesim_df['Plaka Adet'] - sunger_kesim_df['Üretilen Plaka Miktarı']
                sunger_kesim_df['Kalan Plaka Adet'] = sunger_kesim_df['Kalan Plaka Adet'].apply(lambda x: max(0.0, x))

                sunger_kesim_df['Kalan Blok Adet'] = sunger_kesim_df['Blok Adet'] - sunger_kesim_df['Kesilen Blok Miktarı']
                sunger_kesim_df['Kalan Blok Adet'] = sunger_kesim_df['Kalan Blok Adet'].apply(lambda x: max(0.0, x))

                # Üretim Tamamlanma Yüzdesi Hesaplama
                sunger_kesim_df['Tamamlanma %'] = (sunger_kesim_df['Üretilen Plaka Miktarı'] / sunger_kesim_df['Plaka Adet'] * 100).fillna(0.0)
                sunger_kesim_df['Tamamlanma %'] = sunger_kesim_df['Tamamlanma %'].apply(lambda x: f"% {min(100.0, round(x, 1))}")

                # 1. Hammadde İhtiyaç Özeti
                st.subheader("📊 Gerekli Toplam Hammadde (Blok / Rulo) Özeti")
                pivot_df = sunger_kesim_df.groupby(["Blok Kodu", "Blok Adı"]).agg({
                    "Blok Adet": "sum",
                    "Kesilen Blok Miktarı": "sum",
                    "Kalan Blok Adet": "sum"
                }).reset_index()
                pivot_df.columns = ["Blok Kodu", "Blok Adı", "Gerekli Toplam (Adet)", "Kesilen (Adet)", "Kalan İhtiyaç (Adet)"]
                st.dataframe(pivot_df, use_container_width=True, hide_index=True)

                # 2. Tüm Kalemlerin Gösterimi
                st.markdown("---")
                st.subheader("📋 Aktif Plan Detay Satırları")
                gosterilecek_cols = [
                    'Sipariş No', 'Plaka Kodu', 'Plaka Adı', 'Blok Kodu', 'Blok Adı', 
                    'Plaka Adet', 'Üretilen Plaka Miktarı', 'Tamamlanma %', 'Blok Adet', 'Kesilen Blok Miktarı'
                ]
                st.dataframe(sunger_kesim_df[gosterilecek_cols], use_container_width=True, hide_index=True)

                # Plan Sıfırlama Butonu
                st.markdown("---")
                confirm_delete = st.checkbox("⚠️ Aktif planı silmek ve Drive'daki sayfayı sıfırlamak istiyorum.")
                if st.button("🗑️ AKTİF PLANI SİL (DRIVE'DAN TEMİZLE)", type="secondary", disabled=not confirm_delete):
                    empty_df = pd.DataFrame(columns=[
                        'Sipariş No', 'Plaka Kodu', 'Plaka Adı', 'Blok Kodu', 'Blok Adı', 
                        'Plaka Adet', 'Blok Adet', 'Üretilen Plaka Miktarı', 'Kesilen Blok Miktarı'
                    ])
                    if save_sheet("Sunger_Kesim", empty_df):
                        st.success("🧹 Google Drive 'Sunger_Kesim' sayfası tamamen sıfırlandı!")
                        st.rerun()

        # TAB 2: YENİ EXCEL PLANI YÜKLEME VE DRIVE'A YAZMA
        with tab_upload:
            st.subheader("📤 Yeni Kesim Listesi Yükleme")
            st.write("Elinizdeki yeni sipariş kesim planını içeren Excel dosyasını yükleyin. Sistem otomatik olarak eşleme matrisiyle Blok ve Rulo ihtiyaçlarını hesaplayacaktır.")
            
            is_emri_file = st.file_uploader("Sipariş/Kesim Planı Excel Dosyasını Sürükleyin ve Bırakın", type=['xlsx', 'xls'], key="new_plan_excel_uploader")

            if is_emri_file is not None:
                try:
                    excel_sheets = pd.ExcelFile(is_emri_file)
                    sheet_name = None
                    for s in excel_sheets.sheet_names:
                        if any(x in s.upper() for x in ["HAZIRLIK", "PLAN", "KESIM", "KESİM", "SÜNGER", "SUNG_KES"]):
                            sheet_name = s
                            break
                    if sheet_name is None:
                        sheet_name = excel_sheets.sheet_names[0]
                    
                    # --- DİNAMİK BAŞLIK AVCISI BAŞLANGIÇ ---
                    raw_df = pd.read_excel(is_emri_file, sheet_name=sheet_name, header=None)
                    header_idx = 0
                    
                    for i in range(min(20, len(raw_df))):
                        row_str = " ".join(str(val).upper() for val in raw_df.iloc[i].values if pd.notna(val))
                        if any(k in row_str for k in ['SİPARİŞ', 'SIPARIS', 'STOK', 'PLAKA', 'KOD', 'ÜRÜN', 'URUN', 'TANIM', 'MALZEME']) and \
                           any(k in row_str for k in ['MİKTAR', 'MIKTAR', 'ADET', 'QTY']):
                            header_idx = i
                            break
                            
                    df_raw = pd.read_excel(is_emri_file, sheet_name=sheet_name, header=header_idx)
                    df_raw.columns = [str(c).strip() for c in df_raw.columns]
                    st.write(f"📝 Okunan Sekme: **{sheet_name}** ({len(df_raw)} satır) | Algılanan Başlık Satırı: {header_idx + 1}")
                    # --- DİNAMİK BAŞLIK AVCISI BİTİŞ ---

                    # Sütun analizleri ve haritalama (Kurşun Geçirmez Ayrıştırıcı Motoru)
                    col_sip_no, col_plaka_kodu, col_plaka_adi, col_plaka_adet = find_work_order_columns(df_raw.columns)

                    st.info(f"📋 **Yüklenen İş Emri Sütunları Başarıyla Eşleşti:** \n"
                            f"• Sipariş No: **{col_sip_no}** \n"
                            f"• Plaka Kodu (Stok Kodu): **{col_plaka_kodu}** \n"
                            f"• Plaka Adı (Stok Adı): **{col_plaka_adi}** \n"
                            f"• Plaka Adet (Miktar): **{col_plaka_adet}**")

                    # Eşleştirme matrisinden blok karşılıklarını bulma
                    eslesme = st.session_state.eslesme_df
                    eslesme_dict = {}
                    
                    if not eslesme.empty:
                        # Eşleştirme matrisi sütunlarını kurşun geçirmez ayrıştırıcı ile eşleme
                        plaka_col, plaka_adi_col, blok_col, blok_adi_col = find_eslesme_columns(eslesme.columns)
                        
                        if not plaka_col or not blok_col:
                            st.error("❌ Eşleştirme matrisinde Plaka Kodu veya Blok Kodu sütunu okunamadı! Matris dosyasındaki (Excel/CSV) sütun isimlerini veya formatını kontrol edin.")
                        else:
                            st.success(f"🔗 **Eşleştirme Matrisi Sütunları Başarıyla Tanımlandı:** \n"
                                       f"• Plaka Kodu Sütunu: **{plaka_col}** \n"
                                       f"• Plaka Adı Sütunu: **{plaka_adi_col}** \n"
                                       f"• Blok Kodu Sütunu: **{blok_col}** \n"
                                       f"• Blok Adı Sütunu: **{blok_adi_col}**")

                        for _, r in eslesme.iterrows():
                            p_k = normalize_code(r.get(plaka_col, ''))
                            b_k = normalize_code(r.get(blok_col, ''))
                            b_a = str(r.get(blok_adi_col, '')) if blok_adi_col else ""
                            if p_k:
                                eslesme_dict[p_k] = {"blok_kodu": b_k, "blok_adi": b_a}

                    mapped_rows = []
                    for _, row in df_raw.iterrows():
                        sip_no = normalize_code(row.get(col_sip_no, 'Belirtilmemiş'))
                        p_kodu = normalize_code(row.get(col_plaka_kodu, ''))
                        p_adi = str(row.get(col_plaka_adi, '')).strip()
                        try:
                            p_adet = float(row.get(col_plaka_adet, 0.0))
                        except:
                            p_adet = 0.0
                        
                        if pd.isna(p_adet) or math.isnan(p_adet):
                            p_adet = 0.0

                        # Eşleşen bloku bulma
                        match_info = eslesme_dict.get(p_kodu)
                        if match_info:
                            b_kodu = match_info["blok_kodu"]
                            b_adi = match_info["blok_adi"]
                        else:
                            b_kodu = "UYGUN BLOK YOK"
                            b_adi = "Eşleşme Matrisinde Tanımsız"

                        # Verim / Blok Adet hesaplama motoru
                        ham_olcu = ayikla_karakter_ve_olcu(b_adi)
                        plaka_olcu = ayikla_karakter_ve_olcu(p_adi)

                        if plaka_olcu['boy'] > 0 and plaka_olcu['en'] > 0 and plaka_olcu['kalinlik'] > 0 and ham_olcu['boy'] > 0:
                            en_kat = math.floor(ham_olcu['en'] / plaka_olcu['en'])
                            boy_kat = math.floor(ham_olcu['boy'] / plaka_olcu['boy'])
                            kat_basina_plaka = en_kat * boy_kat if (en_kat > 0 and boy_kat > 0) else 1
                            max_plaka = math.floor(ham_olcu['kalinlik'] / plaka_olcu['kalinlik']) * kat_basina_plaka
                        else:
                            max_plaka = 10.0 # Varsayılan katsayı

                        if max_plaka <= 0:
                            max_plaka = 1.0

                        b_adet = math.ceil(p_adet / max_plaka)

                        mapped_rows.append({
                            "Sipariş No": sip_no,
                            "Plaka Kodu": p_kodu,
                            "Plaka Adı": p_adi,
                            "Blok Kodu": b_kodu,
                            "Blok Adı": b_adi,
                            "Plaka Adet": float(p_adet),
                            "Blok Adet": float(b_adet),
                            "Üretilen Plaka Miktarı": 0.0,
                            "Kesilen Blok Miktarı": 0.0
                        })

                    df_mapped = pd.DataFrame(mapped_rows)

                    # Önizleme Raporu
                    st.markdown("---")
                    st.subheader("👁️ Eşleştirilen Yeni Plan Önizlemesi")
                    st.dataframe(df_mapped, use_container_width=True, hide_index=True)

                    # Yazma Türü Seçimi
                    write_mode = st.radio(
                        "Drive Kayıt Modu Seçin:",
                        options=["Mevcut Planı Sil ve Yeni Planı Yaz (Overwrite)", "Mevcut Planın Altına Ekle (Append)"],
                        horizontal=True
                    )

                    st.warning("⚠️ Yukarıdaki verilerin Google Drive'daki 'Sunger_Kesim' sayfasına yazılması için aşağıdaki butona basın.")

                    # GÖZ KAMAŞTIRICI YÜKLEME VE DRIVE'A KAYDETME BUTONU!
                    if st.button("💾 YENİ PLANI GOOGLE DRIVE'A KAYDET VE KESİNLEŞTİR", type="primary", use_container_width=True):
                        with st.spinner("Bulut bağlantısı kuruluyor ve veriler Drive'a yazılıyor..."):
                            
                            if "Sil" in write_mode or sunger_kesim_df.empty:
                                df_final = df_mapped
                            else:
                                df_final = pd.concat([sunger_kesim_df, df_mapped], ignore_index=True)

                            # NaN'ları temizle ve kaydet
                            df_final = df_final.fillna(0.0)
                            success_write = save_sheet("Sunger_Kesim", df_final)

                            if success_write:
                                st.balloons()
                                st.success(f"🎉 Harika! {len(df_mapped)} satırlık yeni kesim planı Google Drive'a başarıyla yazıldı ve sabitlendi!")
                                st.rerun()
                            else:
                                st.error("❌ Drive'a kaydetme başarısız oldu. Lütfen veritabanı bağlantı yetkisini veya sayfa adını kontrol edin.")
                except Exception as e:
                    st.error(f"❌ Excel işlenirken kritik hata: {e}")

    # =========================================================================
    # EKRAN 2A: OPERATÖR - İŞ EMRİ HAZIRLAMA (PLAKA SEÇİMİ)
    # =========================================================================
    elif st.session_state.blok_kesim_page == 'kesim_menu':
        c_nav1, c_nav2 = st.columns([2.5, 7.5])
        with c_nav1:
            if st.button("⬅️ GERİ (ANA MENÜ)", use_container_width=True, key="back_from_kesim_menu"):
                st.session_state.blok_kesim_page = 'menu'
                st.session_state.operator_work_orders = []
                st.rerun()
        with c_nav2:
            st.subheader("🧱 Operatör Kesim Terminali - İş Emri Hazırlama")

        st.markdown("---")

        if sunger_kesim_df.empty:
            st.error("⚠️ Drive'da aktif bir kesim planı ('Sunger_Kesim') bulunamadı. Kesim başlatmak için önce 'Plan & İş Emri Yükle' ekranından plan kaydedin!")
        else:
            # Açık siparişleri filtrele (henüz başlanmamışlar)
            for col in ['Plaka Adet', 'Üretilen Plaka Miktarı', 'Blok Adet', 'Kesilen Blok Miktarı']:
                if col in sunger_kesim_df.columns:
                    sunger_kesim_df[col] = pd.to_numeric(sunger_kesim_df[col], errors='coerce').fillna(0.0)

            acik_siparisler = sunger_kesim_df[
                sunger_kesim_df['Üretilen Plaka Miktarı'] < sunger_kesim_df['Plaka Adet']
            ].copy()

            if acik_siparisler.empty:
                st.success("✅ Tüm siparişler tamamlanmıştır! Yeni bir plan yüklemek için 'Plan & İş Emri Yükle' sekmesine gidin.")
            else:
                # Plaka yüksekliklerini çıkart
                acik_siparisler['Kalinlik'] = acik_siparisler['Plaka Adı'].apply(lambda x: ayikla_karakter_ve_olcu(x)['kalinlik'])
                acik_siparisler['Kalan Plaka'] = acik_siparisler['Plaka Adet'] - acik_siparisler['Üretilen Plaka Miktarı']
                
                st.write(f"📊 **{len(acik_siparisler)} adet açık kesim emri mevcut. Aynı yükseklikte olanları seçerek bir iş emri oluşturun:**")
                st.markdown("---")

                # Tablo gösterimi - checkbox'larla
                col_checks = st.columns([0.5, 1.5, 2, 2, 1.5, 1.5, 1.5])
                with col_checks[0]:
                    st.write("**✓**")
                with col_checks[1]:
                    st.write("**Sipariş No**")
                with col_checks[2]:
                    st.write("**Plaka Adı**")
                with col_checks[3]:
                    st.write("**Plaka Kodu**")
                with col_checks[4]:
                    st.write("**Kalan (Adet)**")
                with col_checks[5]:
                    st.write("**Yükseklik (cm)**")
                with col_checks[6]:
                    st.write("**Blok Adı**")

                selected_indices = []
                for idx, (i, row) in enumerate(acik_siparisler.iterrows()):
                    col_check = st.columns([0.5, 1.5, 2, 2, 1.5, 1.5, 1.5])
                    with col_check[0]:
                        if st.checkbox("", key=f"select_row_{i}_{idx}"):
                            selected_indices.append(i)
                    with col_check[1]:
                        st.write(f"{row['Sipariş No']}")
                    with col_check[2]:
                        st.write(f"{row['Plaka Adı']}")
                    with col_check[3]:
                        st.write(f"{row['Plaka Kodu']}")
                    with col_check[4]:
                        st.write(f"{int(row['Kalan Plaka'])}")
                    with col_check[5]:
                        st.write(f"{row['Kalinlik']:.1f}")
                    with col_check[6]:
                        st.write(f"{row['Blok Adı']}")

                st.markdown("---")

                if st.button("✅ SEÇİLEN PLAKALARDAN İŞ EMRİ OLUŞTUR", type="primary", use_container_width=True):
                    if not selected_indices:
                        st.error("❌ Lütfen en az bir plaka seçiniz!")
                    else:
                        selected_rows = acik_siparisler.loc[selected_indices]
                        
                        # Yükseklik kontrolü
                        heights = selected_rows['Kalinlik'].unique()
                        if len(heights) > 1:
                            st.error(f"❌ **HATA:** Seçili plakalar farklı yüksekliklerde! ({heights}) Aynı yükseklikte olan plakları seçiniz. Farklı yükseklikteler aynı karusel makinesinde üretilelemez!")
                        else:
                            # İş emrini oluştur
                            work_order = {
                                'selected_rows': selected_rows.reset_index(drop=True),
                                'kalinlik': heights[0],
                                'blok_adet': selected_rows['Blok Adet'].sum(),
                                'toplam_plaka_adet': selected_rows['Plaka Adet'].sum(),
                                'kalan_plaka_adet': selected_rows['Kalan Plaka'].sum(),
                            }
                            st.session_state.operator_work_orders.append(work_order)
                            
                            st.success(f"✅ İş emri oluşturuldu! Toplam {len(work_order['selected_rows'])} ürün, Yükseklik: {work_order['kalinlik']:.1f} cm")
                            st.info(f"📋 Oluşturulan iş emirleri: {len(st.session_state.operator_work_orders)}")
                            st.rerun()

                st.markdown("---")
                st.subheader("📝 Oluşturulan İş Emirleri")
                
                if not st.session_state.operator_work_orders:
                    st.info("ℹ️ Henüz bir iş emri oluşturulmamıştır.")
                else:
                    for wo_idx, wo in enumerate(st.session_state.operator_work_orders):
                        with st.expander(f"📦 İş Emri #{wo_idx + 1} - Yükseklik: {wo['kalinlik']:.1f} cm ({len(wo['selected_rows'])} SKU)", expanded=False):
                            st.write(f"• **Blok Gereksinimi:** {wo['blok_adet']:.0f} adet")
                            st.write(f"• **Toplam Plaka Adet:** {wo['toplam_plaka_adet']:.0f} adet")
                            st.write(f"• **Kalan Üretilecek:** {wo['kalan_plaka_adet']:.0f} adet")
                            st.markdown("**Detaylar:**")
                            st.dataframe(wo['selected_rows'][['Sipariş No', 'Plaka Kodu', 'Plaka Adı', 'Kalan Plaka', 'Blok Adı']], use_container_width=True, hide_index=True)
                            
                            if st.button(f"🗑️ Bu İş Emrini Sil", key=f"delete_wo_{wo_idx}"):
                                st.session_state.operator_work_orders.pop(wo_idx)
                                st.rerun()

                    st.markdown("---")
                    if st.button("▶️ HAZIRLANMIŞ İŞ EMRİLERİYLE KESİM OPERASYONUNA GEÇ", type="primary", use_container_width=True):
                        st.session_state.blok_kesim_page = 'kesim'
                        st.rerun()

    # =========================================================================
    # EKRAN 2B: OPERATÖR - KESİM OPERASYONU (BARKOD + İŞ EMRİ SEÇİMİ)
    # =========================================================================
    elif st.session_state.blok_kesim_page == 'kesim':
        c_nav1, c_nav2 = st.columns([2.5, 7.5])
        with c_nav1:
            if st.button("⬅️ GERİ (İŞ EMRİ SEÇ)", use_container_width=True, key="back_from_kesim"):
                st.session_state.blok_kesim_page = 'kesim_menu'
                st.session_state.current_work_order_idx = None
                st.rerun()
        with c_nav2:
            st.subheader("🔧 Kesim Operasyonu - Barkod Okuma")

        st.markdown("---")

        if not st.session_state.operator_work_orders:
            st.error("❌ Hiçbir iş emri hazırlanmamıştır! Lütfen geri gidip iş emri oluşturunuz.")
        else:
            # İş emri seçimi
            st.subheader("📋 Hangi İş Emrinde Çalışmak İstiyorsunuz?")
            
            wo_options = [f"İş Emri #{idx + 1} - Yükseklik: {wo['kalinlik']:.1f} cm ({len(wo['selected_rows'])} SKU)" 
                         for idx, wo in enumerate(st.session_state.operator_work_orders)]
            
            selected_wo_idx = st.radio("", range(len(st.session_state.operator_work_orders)), 
                                       format_func=lambda x: wo_options[x], horizontal=False)
            
            st.session_state.current_work_order_idx = selected_wo_idx
            current_wo = st.session_state.operator_work_orders[selected_wo_idx]

            st.markdown("---")
            st.write("**Bu İş Emrinin Detayları:**")
            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                st.metric("Plaka Yüksekliği", f"{current_wo['kalinlik']:.1f} cm")
            with col_info2:
                st.metric("Blok Gereksinimi", f"{current_wo['blok_adet']:.0f} Adet")
            with col_info3:
                st.metric("Kalan Plaka", f"{current_wo['kalan_plaka_adet']:.0f} Adet")

            st.markdown("---")
            st.subheader("📝 Ürünler (Bu İş Emrinde)")
            st.dataframe(current_wo['selected_rows'][['Sipariş No', 'Plaka Kodu', 'Plaka Adı', 'Blok Adı', 'Kalan Plaka']], 
                        use_container_width=True, hide_index=True)

            st.markdown("---")
            st.subheader("🔍 Blok/Rulo Barkodu Okutunuz")
            
            barkod_giris = st.text_input("🔍 KESİLECEK BLOK VEYA RULO BARKODUNU OKUTUNUZ:", key="operator_scanned_barcode")

            if barkod_giris:
                scanned_norm = normalize_code(barkod_giris)

                # Stoktan barkodu normalize kodla bulalım
                if stok_barkod_col is not None and not stok_df.empty:
                    stok_df_temp = stok_df.copy()
                    stok_df_temp['Barcode_Norm'] = stok_df_temp[stok_barkod_col].apply(normalize_code)
                    match_stok = stok_df_temp[stok_df_temp['Barcode_Norm'] == scanned_norm]
                else:
                    match_stok = pd.DataFrame()

                if not match_stok.empty:
                    stok_satir = match_stok.iloc[0]
                    blok_kod = normalize_code(stok_satir.get('Kod', ''))
                    blok_adi = str(stok_satir.get('Malzeme_Adi', stok_satir.get('Malzeme Adı', stok_satir.get('Ad', '')))).strip()
                    
                    try:
                        stok_miktari = float(stok_satir.get('Miktar', 0.0))
                    except:
                        stok_miktari = 0.0
                        
                    blok_adres = str(stok_satir.get('Adres', 'Bilinmeyen Adres')).strip()

                    st.info(f"📍 **Bulunan Hammadde Stoğu:** {blok_adi} ({blok_kod}) | **Mevcut:** {stok_miktari} Adet | **Adres:** {blok_adres}")

                    # Mevcut iş emrindeki ürünleri filtrelenmiş eşleştir
                    current_wo_items = current_wo['selected_rows'].copy()
                    current_wo_items['Blok_Kodu_Norm'] = current_wo_items['Blok Kodu'].apply(normalize_code)
                    
                    # Eşleşen öğeleri bul
                    matching_items = current_wo_items[current_wo_items['Blok_Kodu_Norm'] == blok_kod]

                    if not matching_items.empty:
                        st.success(f"🎯 Bu blok ile eşleşen {len(matching_items)} ürün bulundu!")
                        st.dataframe(matching_items[['Sipariş No', 'Plaka Kodu', 'Plaka Adı', 'Kalan Plaka']], use_container_width=True, hide_index=True)

                        # Seçim - hangi ürüne kesim yapılacak
                        if len(matching_items) == 1:
                            secilen_sip_idx = 0
                        else:
                            secilen_sip_idx = st.selectbox(
                                "Kesim Yapılacak Ürünü Seçin:",
                                options=range(len(matching_items)),
                                format_func=lambda i: f"Sip No: {matching_items.iloc[i]['Sipariş No']} -> {matching_items.iloc[i]['Plaka Adı']} (Kalan: {int(matching_items.iloc[i]['Kalan Plaka'])} Ad)"
                            )

                        secilen_row = matching_items.iloc[secilen_sip_idx]
                        original_idx = secilen_row.name
                        
                        plaka_kodu = secilen_row['Plaka Kodu']
                        plaka_adi = secilen_row['Plaka Adı']
                        kalan_plaka_adedi = secilen_row['Kalan Plaka']

                        # Ölçü ve Fire Hesaplama
                        ham_olcu = ayikla_karakter_ve_olcu(blok_adi)
                        plaka_olcu = ayikla_karakter_ve_olcu(plaka_adi)

                        st.write("---")
                        st.subheader("📐 Akıllı Verim Hesaplama")
                        col_o1, col_o2 = st.columns(2)
                        with col_o1:
                            st.write(f"🧱 **Blok Ölçüsü:** {ham_olcu['boy']}x{ham_olcu['en']}x{ham_olcu['kalinlik']} cm")
                        with col_o2:
                            st.write(f"📐 **Plaka Ölçüsü:** {plaka_olcu['boy']}x{plaka_olcu['en']}x{plaka_olcu['kalinlik']} cm")

                        if plaka_olcu['boy'] > 0 and plaka_olcu['en'] > 0 and plaka_olcu['kalinlik'] > 0:
                            en_kat = math.floor(ham_olcu['en'] / plaka_olcu['en'])
                            boy_kat = math.floor(ham_olcu['boy'] / plaka_olcu['boy'])
                            kat_plaka = en_kat * boy_kat if (en_kat > 0 and boy_kat > 0) else 1
                            max_plaka = math.floor(ham_olcu['kalinlik'] / plaka_olcu['kalinlik']) * kat_plaka
                            st.info(f"💡 **Sistem Önerisi:** 1 Adet Bloktan maksimum **{max_plaka} adet** plaka çıkıyor.")
                        else:
                            max_plaka = 0

                        # Girdi alanları
                        val_uret = int(max_plaka) if max_plaka > 0 else 1
                        if val_uret > kalan_plaka_adedi:
                            val_uret = int(kalan_plaka_adedi)

                        kesim_adedi = st.number_input(
                            "Üretilen Plaka Miktarını Girin (Adet):",
                            min_value=1,
                            max_value=10000,
                            value=val_uret
                        )

                        blok_sarf_adedi = st.number_input(
                            "Tüketilen Blok Miktarını Girin (Adet):",
                            min_value=1.0,
                            max_value=float(stok_miktari) if stok_miktari > 0 else 1.0,
                            value=1.0,
                            step=1.0
                        )

                        if st.button("🔥 KESİMİ GERÇEKLEŞTİR VE DRIVE'A YAZ", type="primary"):
                            try:
                                # 1. DRIVE KESİM PLANINI GÜNCELLE (Sunger_Kesim)
                                original_index = sunger_kesim_df[
                                    (sunger_kesim_df['Sipariş No'] == secilen_row['Sipariş No']) &
                                    (sunger_kesim_df['Plaka Kodu'] == plaka_kodu)
                                ].index[0]
                                
                                sunger_kesim_df.at[original_index, 'Üretilen Plaka Miktarı'] += kesim_adedi
                                sunger_kesim_df.at[original_index, 'Kesilen Blok Miktarı'] += blok_sarf_adedi

                                # 2. HAMMADDE STOĞUNDAN DÜŞÜM
                                stok_index = match_stok.index[0]
                                kalan_stok = stok_miktari - blok_sarf_adedi
                                if kalan_stok <= 0:
                                    stok_df = stok_df.drop(stok_index)
                                else:
                                    stok_df.at[stok_index, 'Miktar'] = kalan_stok

                                # 3. PLAKA (YARI MAMUL) STOĞUNA EKLEME
                                plaka_stok_match = stok_df[
                                    (stok_df['Kod'].astype(str).str.strip() == str(plaka_kodu).strip()) & 
                                    (stok_df['Adres'].astype(str).str.strip() == str(blok_adres).strip())
                                ]
                                
                                if not plaka_stok_match.empty:
                                    p_idx = plaka_stok_match.index[0]
                                    mevcut_p_mik = float(stok_df.at[p_idx, 'Miktar'])
                                    stok_df.at[p_idx, 'Miktar'] = mevcut_p_mik + kesim_adedi
                                else:
                                    yeni_plaka_satir = {
                                        "Adres": blok_adres,
                                        "Kod": plaka_kodu,
                                        "Malzeme_Adi": plaka_adi,
                                        "Miktar": kesim_adedi,
                                        "Birim": "AD"
                                    }
                                    for col in stok_df.columns:
                                        if col not in yeni_plaka_satir:
                                            yeni_plaka_satir[col] = ""
                                    stok_df = pd.concat([stok_df, pd.DataFrame([yeni_plaka_satir])], ignore_index=True)

                                # 4. HAREKET GEÇMİŞİNİ YAZMA
                                t_tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                har_sarf = {
                                    "Tarih": t_tarih,
                                    "İşlem": "KESİM/SARF",
                                    "Adres": blok_adres,
                                    "Kod": blok_kod,
                                    "Malzeme_Adi": blok_adi,
                                    "Miktar": -blok_sarf_adedi,
                                    "Birim": "AD"
                                }
                                har_uret = {
                                    "Tarih": t_tarih,
                                    "İşlem": "ÜRETİM/GİRİŞ",
                                    "Adres": blok_adres,
                                    "Kod": plaka_kodu,
                                    "Malzeme_Adi": plaka_adi,
                                    "Miktar": kesim_adedi,
                                    "Birim": "AD"
                                }

                                for col in har_df.columns:
                                    if col not in har_sarf: har_sarf[col] = ""
                                    if col not in har_uret: har_uret[col] = ""

                                har_df = pd.concat([har_df, pd.DataFrame([har_sarf, har_uret])], ignore_index=True)

                                # Hepsini Drive'a Kaydet
                                run_kesim_save = save_sheet("Sunger_Kesim", sunger_kesim_df)
                                run_stok_save = save_sheet("Stok", stok_df)
                                run_har_save = save_sheet("Hareketler", har_df)

                                if run_kesim_save and run_stok_save and run_har_save:
                                    st.balloons()
                                    st.success(f"🎉 Kesim İşlemi Kaydedildi! {blok_sarf_adedi} adet Blok sarf edildi, {kesim_adedi} adet Plaka üretildi!")
                                    st.rerun()
                                else:
                                    st.error("❌ Kayıtlar yapılırken bir sorun oluştu! Lütfen Drive bağlantınızı kontrol edin.")
                            except Exception as ex:
                                st.error(f"❌ İşlem sırasında hata: {ex}")
                    else:
                        st.error(f"❌ Okunan blok bu iş emrindeki ürünlerden hiçbiriyle eşleşmiyor! Bu iş emrindeki bloklar: {current_wo_items['Blok Adı'].unique().tolist()}")
                else:
                    st.error(f"❌ '{barkod_giris}' barkodlu hammadde stokta bulunamadı! Lütfen kontrol edin.")

    # =========================================================================
    # EKRAN 3: KESİM RAPORLARI
    # =========================================================================
    elif st.session_state.blok_kesim_page == 'rapor':
        c_nav1, c_nav2 = st.columns([2.5, 7.5])
        with c_nav1:
            if st.button("⬅️ GERİ (ANA MENÜ)", use_container_width=True, key="back_from_rapor"):
                st.session_state.blok_kesim_page = 'menu'
                st.rerun()
        with c_nav2:
            st.subheader("📊 Blok ve Rulo Kesim Analiz Raporları")

        st.markdown("---")

        if not har_df.empty:
            har_df.columns = [str(c).strip() for c in har_df.columns]
            
            # Sadece Kesim/Sarf ve Üretim/Giriş işlemlerini süzme
            kesim_hareketleri = har_df[har_df['İşlem'].isin(['KESİM/SARF', 'ÜRETİM/GİRİŞ'])].copy()
            
            if not kesim_hareketleri.empty:
                # Yeni işlemler üstte görünecek
                kesim_hareketleri = kesim_hareketleri.iloc[::-1]
                
                # Toplam İstatistikler
                total_sarf = abs(pd.to_numeric(kesim_hareketleri[kesim_hareketleri['İşlem'] == 'KESİM/SARF']['Miktar'], errors='coerce').fillna(0.0).sum())
                total_giris = pd.to_numeric(kesim_hareketleri[kesim_hareketleri['İşlem'] == 'ÜRETİM/GİRİŞ']['Miktar'], errors='coerce').fillna(0.0).sum()
                
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    st.metric("🧱 Tüketilen Toplam Blok (Hammadde)", f"{total_sarf:.1f} Adet")
                with col_m2:
                    st.metric("🎯 Üretilen Toplam Plaka (Mamul)", f"{total_giris:.1f} Adet")
                
                st.markdown("---")
                st.write("📋 **Kesim İşlemleri Günlüğü (Canlı Hareketler):**")
                st.dataframe(kesim_hareketleri, use_container_width=True, hide_index=True)
            else:
                st.info("ℹ️ Sistemde henüz gerçekleştirilmiş bir sünger kesim hareketi bulunmamaktadır.")
        else:
            st.info("ℹ️ Hareket geçmişi boş.")

if __name__ == "__main__":
    st.warning("Bu modül doğrudan çalıştırılamaz. Lütfen app.py üzerinden erişin.")
