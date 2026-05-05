import streamlit as st
import pandas as pd
import io
from datetime import datetime

# Navigasyon Fonksiyonları
def go_home(): 
    st.session_state.page = 'home'
    st.session_state.uretim_page = 'menu'

def go_uretim_menu(): 
    st.session_state.uretim_page = 'menu'
    if 'local_stok' in st.session_state: del st.session_state.local_stok
    if 'local_emirler' in st.session_state: del st.session_state.local_emirler

def go_is_emri(): st.session_state.uretim_page = 'is_emri'
def go_hazirlik(): st.session_state.uretim_page = 'hazirlik'
def go_rapor(): st.session_state.uretim_page = 'rapor'

def run(conn):
    # Sayfa Kontrolü
    if 'uretim_page' not in st.session_state:
        st.session_state.uretim_page = 'menu'

    # --- 0. ANA MENÜ ---
    if st.session_state.uretim_page == 'menu':
        if st.button("⬅️ ANA MENÜYE DÖN"): 
            st.session_state.page = 'home'
            st.rerun()
            
        st.subheader("🏭 Üretim Hazırlık Modülü")
        st.markdown("---")
        st.button("📥 İŞ EMRİ YÜKLE", use_container_width=True, type="primary", on_click=go_is_emri)
        st.button("🏗️ ÜRETİM HAZIRLIK", use_container_width=True, type="primary", on_click=go_hazirlik)
        st.button("📊 HAZIRLIK RAPORU", use_container_width=True, type="primary", on_click=go_rapor)

    # --- 1. İŞ EMRİ YÜKLEME ---
    elif st.session_state.uretim_page == 'is_emri':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("📤 Yeni İş Emri Yükle")
        uploaded_file = st.file_uploader("Excel dosyasını seçin (HAZIRLIK sekmesi aranır):", type=['xlsx', 'xls'])
        
        if uploaded_file:
            try:
                # Excel'den HAZIRLIK sayfasını oku
                df_raw = pd.read_excel(uploaded_file, sheet_name="HAZIRLIK", header=None)
                baslik_satiri = 0
                for i in range(min(20, len(df_raw))):
                    satir = [str(x).strip().lower() for x in df_raw.iloc[i].fillna("").values]
                    if "stok kodu" in satir:
                        baslik_satiri = i
                        break
                
                df_raw.columns = df_raw.iloc[baslik_satiri]
                df_raw = df_raw.iloc[baslik_satiri+1:].reset_index(drop=True)
                df_raw.columns = [str(c).strip() for c in df_raw.columns]
                
                # Sütun Eşleştirme Mantığı
                if "Mamül Kodu" in df_raw.columns: df_raw["Ürün Kodu"] = df_raw["Mamül Kodu"]
                for col in df_raw.columns:
                    if "total" in str(col).lower():
                        df_raw["İhtiyaç Miktarı"] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0)
                        break
                
                is_emri_adi = uploaded_file.name.rsplit('.', 1)[0]
                df_raw['İş Emri'] = is_emri_adi
                
                cols_target = ["İş Emri", "Ürün Kodu", "Mamül Adı", "Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Hazırlanan Adet", "Birim"]
                for c in cols_target:
                    if c not in df_raw.columns: df_raw[c] = 0 if ("Adet" in c or "Miktar" in c) else ""
                
                df_raw = df_raw.dropna(subset=['Stok Kodu'])
                df_final_save = df_raw[cols_target]
                
                st.dataframe(df_final_save.head(), use_container_width=True)

                if st.button("VERİTABANINA ŞİMDİ KAYDET", type="primary"):
                    existing = conn.read(worksheet="Is_Emirleri")
                    updated = pd.concat([existing, df_final_save], ignore_index=True)
                    conn.update(worksheet="Is_Emirleri", data=updated)
                    st.success("İş Emri Veritabanına Eklendi!")
                    st.cache_data.clear(); st.rerun()
            except Exception as e: st.error(f"Hata: {e}")

    # --- 2. HAZIRLIK OPERASYONU ---
    elif st.session_state.uretim_page == 'hazirlik':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("🏗️ Üretim Hazırlık Operasyonu")
        
        # Verileri Bir Kez Çek (Local Cache)
        if 'local_stok' not in st.session_state:
            st.session_state.local_stok = conn.read(worksheet="Urun_Listesi")
        if 'local_emirler' not in st.session_state:
            st.session_state.local_emirler = conn.read(worksheet="Is_Emirleri")
        
        df_emirler = st.session_state.local_emirler.copy()
        df_stok_ana = st.session_state.local_stok.copy()
        
        if not df_emirler.empty:
            df_emirler['Hazırlanan Adet'] = pd.to_numeric(df_emirler['Hazırlanan Adet'], errors='coerce').fillna(0)
            df_emirler['İhtiyaç Miktarı'] = pd.to_numeric(df_emirler['İhtiyaç Miktarı'], errors='coerce').fillna(0)
            
            emir_list = sorted(df_emirler["İş Emri"].astype(str).unique().tolist())
            s_list = st.multiselect("📋 Takip Edilecek İş Emirlerini Seçin:", emir_list)
            
            if s_list:
                sub_df = df_emirler[df_emirler["İş Emri"].astype(str).isin(s_list)].copy()
                
                pivot_df = sub_df.groupby(['Stok Kodu', 'Stok Adı', 'Birim']).agg({
                    'İhtiyaç Miktarı': 'sum',
                    'Hazırlanan Adet': 'sum'
                }).reset_index()
                
                pivot_df['Tamamlandi'] = (pivot_df['Hazırlanan Adet'] >= pivot_df['İhtiyaç Miktarı']).astype(int)
                pivot_df = pivot_df.sort_values(by=['Tamamlandi', 'Stok Adı'], ascending=[True, True])

                # Giriş Paneli
                with st.container(border=True):
                    st.markdown("🔍 **Üretim Hazırlık Girişi**")
                    p1, p2, p3, p4 = st.columns([2, 1, 1, 1])
                    
                    bekleyen_isimler = sorted(pivot_df[pivot_df['Tamamlandi'] == 0]['Stok Adı'].unique().tolist())
                    input_isim = p1.selectbox("📝 Malzeme İsmi:", ["Seçiniz..."] + bekleyen_isimler)
                    
                    if input_isim != "Seçiniz...":
                        row_info = pivot_df[pivot_df['Stok Adı'] == input_isim].iloc[0]
                        selected_kod = row_info['Stok Kodu']
                        current_req = row_info['İhtiyaç Miktarı']
                        current_prep = row_info['Hazırlanan Adet']
                        is_haya = str(selected_kod).upper().startswith("HAYA")
                        
                        p2.text_input("📊 İhtiyaç:", value=f"{int(current_req)} {row_info['Birim']}", disabled=True)

                        # Adres Bulma (Sütun isimleri: kod, ADRES, MIKTAR)
                        temp_stok = df_stok_ana.copy()
                        if is_haya:
                            valid_stocks = temp_stok[temp_stok['kod'] == str(selected_kod)].sort_values('ADRES')
                        else:
                            valid_stocks = temp_stok[(temp_stok['kod'] == str(selected_kod)) & (temp_stok['MIKTAR'] > 0)].sort_values('ADRES')
                        
                        if not valid_stocks.empty:
                            adrs_list = valid_stocks['ADRES'].unique().tolist()
                            input_adr = p3.selectbox(f"📍 Adres:", ["Seçiniz..."] + adrs_list)
                            
                            if input_adr != "Seçiniz...":
                                current_stock_at_adr = valid_stocks[valid_stocks['ADRES'] == input_adr]['MIKTAR'].sum()
                                st.write(f"📦 **Raf Stoğu:** `{int(current_stock_at_adr)}` | 🎯 **Kalan:** `{int(current_req - current_prep)}`")
                            
                            input_mik = p4.number_input("🔢 Miktar:", min_value=0.0, step=1.0)
                            
                            if st.button("⚡ HAREKETİ KAYDET", use_container_width=True, type="primary"):
                                personel = st.session_state.get('user', 'Bilinmeyen')
                                
                                # Kayıt Kontrolleri
                                if not is_haya and input_mik > current_stock_at_adr:
                                    st.error("⚠️ Stok yetersiz!")
                                elif (current_prep + input_mik) > current_req:
                                    st.error("🚫 İhtiyaçtan fazlasını hazırlayamazsınız!")
                                else:
                                    # 1. Stok Güncelleme
                                    mask_stok = (st.session_state.local_stok['kod'] == selected_kod) & (st.session_state.local_stok['ADRES'] == input_adr)
                                    if is_haya:
                                        st.session_state.local_stok.loc[mask_stok, 'MIKTAR'] += input_mik
                                    else:
                                        st.session_state.local_stok.loc[mask_stok, 'MIKTAR'] -= input_mik
                                    
                                    # 2. İş Emri Hazırlanan Adet Güncelleme
                                    kalan_hazirlik = input_mik
                                    emir_indices = st.session_state.local_emirler[(st.session_state.local_emirler['İş Emri'].astype(str).isin(s_list)) & 
                                                                                 (st.session_state.local_emirler['Stok Kodu'] == selected_kod)].index
                                    for idx in emir_indices:
                                        if kalan_hazirlik <= 0: break
                                        iht = st.session_state.local_emirler.at[idx, 'İhtiyaç Miktarı']
                                        haz = st.session_state.local_emirler.at[idx, 'Hazırlanan Adet']
                                        bosluk = iht - haz
                                        alinacak = min(kalan_hazirlik, bosluk if bosluk > 0 else 0)
                                        st.session_state.local_emirler.at[idx, 'Hazırlanan Adet'] += alinacak
                                        kalan_hazirlik -= alinacak

                                    # 3. Hareket Arşivi Kaydı
                                    df_h_eski = conn.read(worksheet="HAREKETLER")
                                    h_satir = {
                                        "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "İşlem": "ÜRETİM HAZIRLIK (GİRİŞ)" if is_haya else "ÜRETİM HAZIRLIK",
                                        "İş Emri": ", ".join(s_list),
                                        "Ürün Kodu": selected_kod,
                                        "Ürün Adı": input_isim,
                                        "Adres": input_adr,
                                        "Miktar": input_mik,
                                        "Personel": personel
                                    }
                                    df_h_yeni = pd.concat([df_h_eski, pd.DataFrame([h_satir])], ignore_index=True)

                                    # Senkronizasyon
                                    conn.update(worksheet="Urun_Listesi", data=st.session_state.local_stok)
                                    conn.update(worksheet="Is_Emirleri", data=st.session_state.local_emirler)
                                    conn.update(worksheet="HAREKETLER", data=df_h_yeni)
                                    
                                    st.success("Kayıt Tamamlandı!")
                                    st.rerun()
                        else:
                            st.warning("⚠️ Bu ürün için rafta stok bulunamadı!")

                st.markdown("---")
                st.dataframe(pivot_df.drop(columns=['Tamamlandi']), use_container_width=True, hide_index=True)

    # --- 3. RAPORLAMA ---
    elif st.session_state.uretim_page == 'rapor':
        if st.button("⬅️ GERİ DÖN"): go_uretim_menu(); st.rerun()
        st.subheader("📊 Hazırlık Raporu")
        df_lh = conn.read(worksheet="Is_Emirleri")
        
        if not df_lh.empty:
            c1, c2 = st.columns(2)
            r_e = c1.multiselect("📋 İş Emri Seç:", sorted(df_lh["İş Emri"].unique().tolist()))
            r_p = c2.multiselect("📦 Ana Mamül Seç:", sorted(df_lh["Mamül Adı"].unique().tolist()))
            
            res = df_lh
            if r_e: res = res[res["İş Emri"].isin(r_e)]
            if r_p: res = res[res["Mamül Adı"].isin(r_p)]
            
            st.dataframe(res, use_container_width=True, hide_index=True)
            
            # Excel İndirme
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                res.to_excel(writer, index=False, sheet_name='Rapor')
            st.download_button("📥 EXCEL OLARAK İNDİR", buffer.getvalue(), "Hazirlik_Raporu.xlsx", use_container_width=True)
