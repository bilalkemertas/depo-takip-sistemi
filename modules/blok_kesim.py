import streamlit as st
import pandas as pd

def run_blok_kesim(conn):
    st.title("✂️ Blok & Rulo Kesim Otomasyonu")
    
    # --- 1. VERİ YÜKLEME VE KÖPRÜ ---
    with st.sidebar:
        st.header("📁 Veri Kaynağı")
        uploaded_file = st.file_uploader("DataGrid Excel Dosyasını Yükleyin", type=['xlsx'])
        
        if uploaded_file:
            # Excel sekmelerini oku
            df_main = pd.read_excel(uploaded_file, sheet_name='Main sheet')
            df_sunger = pd.read_excel(uploaded_file, sheet_name='Sünger')
            
            # Senin mantığınla kategorize etme fonksiyonu
            def classify_and_map(row):
                tanim = str(row['Malzeme Tanımı']).upper()
                miktar = row['Teslimat Miktarı']
                
                if "BLOKCM" in tanim:
                    return "Blok", "cm (Yükseklik)", miktar
                elif "RULO" in tanim:
                    return "Rulo", "mt (Uzunluk)", miktar
                elif "DUZ" in tanim:
                    return "Plaka", "Adet (Paket içi)", miktar
                return "Diğer", "Birim", miktar

            # Köprüyü kur
            df_main[['Kategori', 'Birim', 'Net_Miktar']] = df_main.apply(
                lambda x: pd.Series(classify_and_map(x)), axis=1
            )
            
            st.session_state['main_data'] = df_main
            st.session_state['sunger_data'] = df_sunger
            st.success("Excel Köprüsü Kuruldu!")

    # --- 2. ANALİZ VE ÖZET PANELİ ---
    if 'main_data' in st.session_state:
        df = st.session_state['main_data']
        
        c1, c2, c3 = st.columns(3)
        with c1:
            blok_sayisi = len(df[df['Kategori'] == "Blok"])
            st.metric("Toplam Blok", f"{blok_sayisi} Adet")
        with c2:
            rulo_sayisi = len(df[df['Kategori'] == "Rulo"])
            st.metric("Toplam Rulo", f"{rulo_sayisi} Adet")
        with c3:
            plaka_paket = len(df[df['Kategori'] == "Plaka"])
            plaka_adet = df[df['Kategori'] == "Plaka"]['Net_Miktar'].sum()
            st.metric("Plaka (Paket/Adet)", f"{plaka_paket} Pk / {int(plaka_adet)} Adet")

        st.divider()

        # --- 3. OPERASYON: PARTİ NO İLE İŞLEM ---
        st.subheader("🛠️ Kesim / Sevkiyat İşlemi")
        parti_no = st.text_input("🔍 Parti No (Seri No) Okutun veya Girin")

        if parti_no:
            # Parti No üzerinden ürünü bul
            match = df[df['Parti No'].astype(str) == str(parti_no)]
            
            if not match.empty:
                row = match.iloc[0]
                with st.container(border=True):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**Ürün:** {row['Malzeme Tanımı']}")
                        st.write(f"**Kategori:** {row['Kategori']}")
                    with col_b:
                        st.write(f"**Mevcut Miktar:** {row['Net_Miktar']} {row['Birim']}")
                        st.write(f"**Malzeme Kodu:** {row['Malzeme Kodu']}")

                # --- 4. STOK KARTI EŞLEŞTİRME (KÖPRÜ) ---
                st.info("🔗 Bu ürünü bizim stok kartımızla eşleştirin:")
                bizim_kartlar = st.session_state['sunger_data']
                
                # İsimden otomatik öneri yapalım
                search_term = str(row['Malzeme Tanımı']).split(' ')[0] # Örn: '27'
                önerilenler = bizim_kartlar[bizim_kartlar['isim'].str.contains(search_term, na=False)]
                
                secilen_kart = st.selectbox(
                    "Bizim Stok Kartımız:", 
                    options=bizim_kartlar['isim'].tolist(),
                    index=bizim_kartlar['isim'].tolist().index(önerilenler.iloc[0]['isim']) if not önerilenler.empty else 0
                )
                
                # Seçilen kartın kodunu getir
                bizim_kod = bizim_kartlar[bizim_kartlar['isim'] == secilen_kart]['kod'].values[0]
                st.code(f"Eşleşen Kod: {bizim_kod}", language="text")

                # --- 5. KESİM GİRİŞİ ---
                st.divider()
                if row['Kategori'] == "Blok":
                    st.write("📐 **Blok Kesim Detayları**")
                    k_kalinlik = st.number_input("Kesilecek Plaka Kalınlığı (cm)", min_value=0.5, step=0.5)
                    k_adet = st.number_input("Çıkan Plaka Adedi", min_value=1, step=1)
                    
                    if st.button("KESİMİ ONAYLA VE STOĞA İŞLE"):
                        # Burada Google Sheets'e (conn) yazma işlemi yapılacak
                        st.balloons()
                        st.success(f"{secilen_kart} stok kartına {k_adet} adet giriş yapıldı.")
                
                elif row['Kategori'] == "Plaka":
                    st.write("📦 **Paket Açma / Sevkiyat**")
                    if st.button("PAKETİ STOĞA AL"):
                        st.success(f"{row['Net_Miktar']} adet ürün {bizim_kod} koduyla stoğa işlendi.")
            else:
                st.error("Girdiğiniz Parti No bulunamadı. Lütfen Excel'i kontrol edin.")
    else:
        st.info("Sistemi başlatmak için lütfen sol taraftan Excel dosyasını yükleyin.")
