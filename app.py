# --- 7. SAYIM SİSTEMİ (HATASIZ VE TABLO DÜZENLİ) ---
elif st.session_state.page == 'sayim':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    st.title("⚖️ Sayım ve Durum Yönetimi")
    
    # Sekme Tanımlamaları
    st_tab1, st_tab2 = st.tabs(["📝 Sayım Girişi", "📊 Sayım & Fark Raporu"])
    kod_map = get_kod_map()
    durum_opsiyonlari = ["Kullanılabilir", "Hasarlı", "Kayıp", "İncelemede"]

    with st_tab1:
        # 1. Veri Giriş Formu
        with st.container(border=True):
            s_adr = st.text_input("📍 Adres").upper()
            s_kod = st.selectbox("📦 Kod Seçin", [""] + sorted(list(kod_map.keys())))
            st.caption(f"Ürün Adı: {kod_map.get(s_kod, 'Seçilmedi')}")
            s_mik = st.number_input("Miktar", min_value=0.0, step=1.0)
            s_dur = st.selectbox("🛠️ Durum", durum_opsiyonlari)
            
            if st.button("➕ Listeye Ekle", use_container_width=True):
                if s_adr and s_kod:
                    st.session_state['gecici_sayim_listesi'].append({
                        "Tarih": datetime.now().strftime("%Y-%m-%d"),
                        "Personel": st.session_state.user, "Adres": s_adr, "Kod": s_kod, 
                        "Ürün Adı": kod_map.get(s_kod, ""), "Miktar": s_mik, "Durum": s_dur
                    })
                    st.toast("Eklendi")
                else: st.warning("Adres ve Kod alanları boş bırakılamaz!")

        # 2. Onay Bekleyen Tablosu
        if st.session_state['gecici_sayim_listesi']:
            st.markdown("### 📥 Onay Bekleyen Sayımlar")
            
            # Tablo Başlıkları
            h_col = st.columns([1, 1.2, 1.5, 0.8, 1, 0.5])
            h_col[0].write("**Adres**")
            h_col[1].write("**Kod**")
            h_col[2].write("**Ürün Adı**")
            h_col[3].write("**Adet**")
            h_col[4].write("**Durum**")
            h_col[5].write("**Sil**")
            st.markdown("---")

            # Tablo Satırları
            for idx, item in enumerate(st.session_state['gecici_sayim_listesi']):
                r_col = st.columns([1, 1.2, 1.5, 0.8, 1, 0.5])
                r_col[0].write(item['Adres'])
                r_col[1].write(item['Kod'])
                r_col[2].write(f"<small>{item['Ürün Adı']}</small>", unsafe_allow_html=True)
                r_col[3].write(str(item['Miktar']))
                r_col[4].write(item['Durum'])
                
                # Tekli Silme Butonu
                if r_col[5].button("🗑️", key=f"del_row_{idx}"):
                    st.session_state['gecici_sayim_listesi'].pop(idx)
                    st.rerun()
            
            st.write("---")
            if st.button("📤 DRIVE'A KAYDET VE ONAYLA", type="primary", use_container_width=True):
                try:
                    df_db = get_internal_data("sayim")
                    conn.update(spreadsheet=SHEET_URL, worksheet="sayim", data=pd.concat([df_db, pd.DataFrame(st.session_state['gecici_sayim_listesi'])], ignore_index=True))
                    st.session_state['gecici_sayim_listesi'] = []
                    st.success("Tüm sayımlar Drive'a işlendi!"); st.rerun()
                except Exception as e: st.error(f"Hata: {e}")

    with st_tab2:
        try:
            # Mobil Fix CSS
            st.markdown("<style>.stMetric { border: 1px solid #eee; padding: 10px; border-radius: 5px; }</style>", unsafe_allow_html=True)
            
            df_s_db = get_internal_data("sayim")
            df_stok_ana = get_internal_data("Stok")
            
            if not df_s_db.empty:
                df_s_db['Miktar'] = pd.to_numeric(df_s_db['Miktar'], errors='coerce').fillna(0)
                df_stok_ana['Miktar'] = pd.to_numeric(df_stok_ana['Miktar'], errors='coerce').fillna(0)
                
                with st.expander("🔍 Rapor Filtreleri", expanded=True):
                    f_tarih = st.selectbox("Tarih Seç:", ["Tümü"] + sorted(df_s_db["Tarih"].astype(str).unique().tolist(), reverse=True))
                    sel_k = st.multiselect("Kod:", sorted(df_s_db["Kod"].unique().tolist()))
                    sel_a = st.multiselect("Adres:", sorted(df_s_db["Adres"].unique().tolist()))

                # Filtreleme
                act = df_s_db.copy()
                if f_tarih != "Tümü": act = act[act["Tarih"] == f_tarih]
                if sel_k: act = act[act["Kod"].isin(sel_k)]
                if sel_a: act = act[act["Adres"].isin(sel_a)]

                if not act.empty:
                    say_ozet = act.groupby(['Adres', 'Kod', 'Ürün Adı'])['Miktar'].sum().reset_index()
                    sis_ozet = df_stok_ana.groupby(['Adres', 'Kod'])['Miktar'].sum().reset_index()
                    res = pd.merge(say_ozet, sis_ozet, on=['Adres', 'Kod'], how='left').fillna(0)
                    res.columns = ["Adres", "Kod", "Ürün Adı", "Sayılan", "Sistem"]
                    res['FARK'] = res['Sayılan'] - res['Sistem']
                    
                    m1, m2 = st.columns(2)
                    m1.metric("Sayılan", f"{res['Sayılan'].sum():,.0f}")
                    m2.metric("Fark", f"{res['FARK'].sum():,.0f}", delta=int(res['FARK'].sum()))
                    
                    st.dataframe(res.style.applymap(lambda v: 'color:red' if v < 0 else 'color:green' if v > 0 else '', subset=['FARK']), use_container_width=True, hide_index=True)
                else: st.warning("Filtreye uygun veri yok.")
            else: st.info("Sayım verisi yok.")
        except Exception as e: st.error(f"Rapor hatası: {e}")

# --- 8. RAPORLAR ---
elif st.session_state.page == 'rapor':
    if st.button("⬅️ ANA MENÜ"): go_home(); st.rerun()
    # Raporlama ekranı devamı...
