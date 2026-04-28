df_emirler_master = get_internal_data("Is_Emirleri")
    if not df_emirler_master.empty:
        # YENİ: Tekli seçim yerine Çoklu Seçim (Multiselect) eklendi
        is_emri_listesi = sorted(df_emirler_master["İş Emri"].unique().tolist())
        s_list = st.multiselect("📋 Hazırlanacak İş Emirlerini Seçin:", is_emri_listesi, key="u_sel_multi", placeholder="Birden fazla iş emri seçebilirsiniz...")
        
        if s_list:
            # Seçilen TÜM iş emirlerini tek havuza alıyoruz
            df_is_emri = df_emirler_master[df_emirler_master["İş Emri"].isin(s_list)].copy()
            # Aynı hammaddeleri toplayıp birleştiriyoruz
            df_prep = df_is_emri.groupby(['Stok Kodu', 'Stok Adı', 'Birim']).agg({'İhtiyaç Miktarı': 'sum', 'Hazırlanan Adet': 'sum'}).reset_index()
            
            stok_verisi = get_internal_data("Stok")
            stok_verisi['Miktar'] = pd.to_numeric(stok_verisi['Miktar'], errors='coerce').fillna(0)
            stok_verisi['Kod'] = stok_verisi['Kod'].astype(str).str.strip().str.upper()

            def get_best_address(kod):
                kod_str = str(kod).strip().upper()
                urun_raflari = stok_verisi[(stok_verisi['Kod'] == kod_str) & (stok_verisi['Miktar'] > 0)]
                if urun_raflari.empty: return "STOK YOK"
                return urun_raflari.loc[urun_raflari['Miktar'].idxmin(), 'Adres']

            df_prep["Alınan Adres"] = df_prep["Stok Kodu"].apply(get_best_address)
            
            bt = df_prep.groupby('Birim')['İhtiyaç Miktarı'].sum()
            ozet = " | ".join([f"{m:.2f} {b}" for b, m in bt.items()])
            st.info(f"💡 Seçilen {len(s_list)} İş Emrinde Toplam {len(df_prep)} Farklı Kalem | {ozet}")
            
            c_u1, c_u2 = st.columns([0.7, 0.3])
            c_u2.download_button("📥 Excel", data=get_excel_buffer(df_prep, "Toplu_Hazirlik"), file_name=f"Toplu_Hazirlik.xlsx", use_container_width=True)
            
            ed = st.data_editor(df_prep, disabled=["Stok Kodu", "Stok Adı", "İhtiyaç Miktarı", "Birim"], hide_index=True, use_container_width=True, key="u_ed")
            
            if st.button("HAZIRLIĞI ONAYLA", key="u_ok"):
                fresh_emirler = conn.read(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", ttl=0)
                secilen_isimler = ", ".join(s_list) # Loglara yazmak için isimleri birleştir
                
                for idx, row in ed.iterrows():
                    fark = float(row["Hazırlanan Adet"]) - float(df_prep.loc[idx, "Hazırlanan Adet"])
                    if fark > 0:
                        ok, mevcut = check_address_stock(row["Stok Kodu"], row["Alınan Adres"], fark)
                        
                        if not ok:
                            eksik = fark - mevcut
                            hedef_adr = update_stock_record(row["Stok Kodu"], row["Stok Adı"], row["Alınan Adres"], eksik, is_increase=True)
                            log_movement("OTOMATİK SİSTEM GİRİŞİ (HAZIRLIK)", hedef_adr, row["Stok Kodu"], row["Stok Adı"], eksik)
                        
                        adr_son = update_stock_record(row["Stok Kodu"], row["Stok Adı"], row["Alınan Adres"], fark, is_increase=False)
                        log_movement(f"{secilen_isimler} ÜRETİM ÇIKIŞ", adr_son, row["Stok Kodu"], row["Stok Adı"], fark)
                        
                        # YENİ: Toplanan ürünü seçili iş emirlerine sırasıyla paylaştır
                        kalan = float(row["Hazırlanan Adet"])
                        mask = (fresh_emirler["İş Emri"].isin(s_list)) & (fresh_emirler["Stok Kodu"].astype(str).str.strip().str.upper() == str(row["Stok Kodu"]).strip().upper())
                        
                        for i in fresh_emirler[mask].index:
                            iht = float(fresh_emirler.at[i, "İhtiyaç Miktarı"])
                            val = iht if kalan >= iht else kalan
                            fresh_emirler.at[i, "Hazırlanan Adet"] = val
                            kalan -= val
                            
                conn.update(spreadsheet=SHEET_URL, worksheet="Is_Emirleri", data=fresh_emirler)
                get_internal_data.clear()
                st.success("Sanal tamamlama yapıldı ve toplu hazırlık onaylandı!"); st.rerun()
    
    # KULLANICIYI BİLGİLENDİREN YENİ ELSE BLOĞU BURASI:
    else:
        st.info("📂 Veritabanında kayıtlı iş emri bulunmuyor. Lütfen yukarıdaki '📥 Yeni İş Emri Yükle' sekmesinden excel dosyası yükleyiniz.")
