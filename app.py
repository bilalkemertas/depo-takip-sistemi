with st_tab2:
        try:
            # CSS ile Mobil Görünümü İyileştir (Buton ve Input yüksekliğini ayarla)
            st.markdown("""
                <style>
                [data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 10px; }
                .stSelectbox, .stMultiSelect { margin-bottom: 10px !important; }
                @media (max-width: 640px) {
                    .stMetric { padding: 5px !important; border: 1px solid #eee; margin-bottom: 5px; }
                }
                </style>
            """, unsafe_allow_html=True)

            df_s_db = get_internal_data("sayim")
            df_stok_ana = get_internal_data("Stok")
            
            if df_s_db is not None and not df_s_db.empty:
                # Veri temizleme
                df_s_db['Miktar'] = pd.to_numeric(df_s_db['Miktar'], errors='coerce').fillna(0)
                df_stok_ana['Miktar'] = pd.to_numeric(df_stok_ana['Miktar'], errors='coerce').fillna(0)
                df_s_db['Tarih'] = df_s_db['Tarih'].astype(str)
                
                # --- FİLTRELER (MOBİL UYUMLU SIRALAMA) ---
                with st.expander("🔍 Rapor Filtreleri", expanded=True):
                    # Mobilde sütunlar otomatik alt alta düşer
                    f_tarih = st.selectbox("📅 Tarih Seç:", ["Tümü"] + sorted(df_s_db["Tarih"].unique().tolist(), reverse=True))
                    
                    c1, c2 = st.columns(2)
                    sel_k = c1.multiselect("📦 Kod:", sorted(df_s_db["Kod"].unique().tolist()))
                    sel_a = c2.multiselect("📍 Adres:", sorted(df_s_db["Adres"].unique().tolist()))
                    
                    sel_d = st.multiselect("🛠️ Durum:", durum_opsiyonlari)

                # --- FİLTRELEME ---
                act = df_s_db.copy()
                if f_tarih != "Tümü": act = act[act["Tarih"] == f_tarih]
                if sel_k: act = act[act["Kod"].isin(sel_k)]
                if sel_a: act = act[act["Adres"].isin(sel_a)]
                if sel_d: act = act[act["Durum"].isin(sel_d)]

                if not act.empty:
                    say_ozet = act.groupby(['Adres', 'Kod', 'Ürün Adı', 'Durum'])['Miktar'].sum().reset_index()
                    say_ozet.columns = ["Adres", "Kod", "Ürün Adı", "Durum", "Sayılan_Miktar"]
                    
                    sis_ozet = df_stok_ana.groupby(['Adres', 'Kod'])['Miktar'].sum().reset_index()
                    sis_ozet.columns = ["Adres", "Kod", "Sistem_Miktarı"]
                    
                    res = pd.merge(say_ozet, sis_ozet, on=['Adres', 'Kod'], how='left').fillna(0)
                    res['FARK'] = res['Sayılan_Miktar'] - res['Sistem_Miktarı']
                    
                    # --- MOBİL METRİKLER ---
                    # Mobilde yan yana 3 metrik sığmayabilir, 1'erli veya 2'şerli gösteriyoruz
                    col_m1, col_m2 = st.columns(2)
                    col_m1.metric("Sayılan", f"{res['Sayılan_Miktar'].sum():,.0f}")
                    col_m2.metric("Fark", f"{res['FARK'].sum():,.0f}", delta=int(res['FARK'].sum()))
                    
                    # --- TABLO (YATAY KAYDIRMA AKTİF) ---
                    st.dataframe(
                        res.style.applymap(lambda v: 'color:red;font-weight:bold' if v < 0 else 'color:green;font-weight:bold' if v > 0 else '', subset=['FARK']),
                        use_container_width=True, 
                        hide_index=True
                    )
                else:
                    st.warning("Seçime uygun veri yok.")
            else:
                st.info("Kayıtlı sayım verisi bulunamadı.")
                
        except Exception as e:
            st.error(f"Hata: {e}")
