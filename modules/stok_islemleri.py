import streamlit as st
import pandas as pd
from datetime import datetime

def run_transfer(conn):
    st.subheader("↔️ Depo İçi Transfer (Adres Değişimi)")
    
    try:
        # Verileri senin güncel sekme isimlerine göre çekiyoruz
        df_stok = conn.read(worksheet="Urun_Listesi")
        df_hareketler = conn.read(worksheet="HAREKETLER")
        
        # Akıllı Arama Bölümü
        search_transfer = st.text_input("🔍 Transfer Edilecek Ürünü Ara", key="trans_search")
        
        if search_transfer:
            # Sütun isimlerini 'kod' ve 'isim' olarak güncelledim
            filtered_df = df_stok[
                df_stok['isim'].astype(str).str.contains(search_transfer, case=False, na=False) | 
                df_stok['kod'].astype(str).str.contains(search_transfer, case=False, na=False)
            ]
        else:
            filtered_df = df_stok

        if not filtered_df.empty:
            options = filtered_df.apply(lambda x: f"{x['kod']} | {x['isim']}", axis=1).tolist()
            selected_option = st.selectbox("Ürün Seçin:", options, key="trans_select")
            
            sel_kodu = selected_option.split(" | ")[0]
            urun_bilgi = df_stok[df_stok['kod'] == sel_kodu].iloc[0]
            
            with st.form("transfer_formu"):
                st.info(f"📦 Ürün: {urun_bilgi['isim']}")
                st.write(f"📍 **Mevcut Adres:** {urun_bilgi.get('ADRES', 'Tanımsız')}")
                
                col1, col2 = st.columns(2)
                with col1:
                    yeni_adres = st.text_input("Hedef (Yeni) Adres")
                with col2:
                    # Mevcut miktarı aşmamak için kontrol
                    max_mik = float(urun_bilgi.get('MIKTAR', 999999))
                    transfer_miktar = st.number_input("Transfer Miktarı", min_value=0.1, max_value=max_mik)
                
                submitted = st.form_submit_button("TRANSFERİ TAMAMLA")
                
                if submitted:
                    personel = st.session_state.get('user', 'Bilinmeyen Personel')
                    tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Transfer işlemini iki hareket satırı olarak kaydediyoruz
                    # 1. Eski adresten çıkış
                    cikis = {
                        "Tarih": tarih, "Ürün Kodu": sel_kodu, "Ürün Adı": urun_bilgi['isim'], 
                        "Adres": urun_bilgi.get('ADRES'), "Miktar": -transfer_miktar, 
                        "İşlem": "TRANSFER ÇIKIŞ", "Personel": personel
                    }
                    
                    # 2. Yeni adrese giriş
                    giris = {
                        "Tarih": tarih, "Ürün Kodu": sel_kodu, "Ürün Adı": urun_bilgi['isim'], 
                        "Adres": yeni_adres, "Miktar": transfer_miktar, 
                        "İşlem": "TRANSFER GİRİŞ", "Personel": personel
                    }
                    
                    # HAREKETLER tablosuna ekle
                    yeni_h = pd.concat([df_hareketler, pd.DataFrame([cikis, giris])], ignore_index=True)
                    conn.update(worksheet="HAREKETLER", data=yeni_h)
                    
                    st.success(f"Başarılı! Ürün {yeni_adres} adresine transfer edildi.")
                    st.balloons()
        else:
            st.warning("Aranan ürün bulunamadı.")
            
    except Exception as e:
        st.error(f"Transfer ekranında bir hata oluştu: {e}")
        st.info("Lütfen 'Urun_Listesi' ve 'HAREKETLER' sekmelerinin doğruluğunu kontrol edin.")
