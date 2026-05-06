import streamlit as st
import pandas as pd
from datetime import datetime

def run_islem(conn):
    st.subheader("📊 Stok Giriş / Çıkış Paneli")
    try:
        df_stok = conn.read(worksheet="Urun_Listesi")
        df_hareketler = conn.read(worksheet="HAREKETLER")
        
        search = st.text_input("🔍 Ürün Ara (Ad/Kod)", "", key="stok_search")
        if search:
            filtered = df_stok[df_stok['isim'].astype(str).str.contains(search, case=False, na=False) | 
                               df_stok['kod'].astype(str).str.contains(search, case=False, na=False)]
        else:
            filtered = df_stok

        if not filtered.empty:
            sel = st.selectbox("Ürünü Onaylayın:", filtered.apply(lambda x: f"{x['kod']} | {x['isim']}", axis=1))
            kod = sel.split(" | ")[0]
            info = df_stok[df_stok['kod'] == kod].iloc[0]
            
            with st.form("islem_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    islem = st.selectbox("İşlem Türü", ["GİRİŞ", "ÇIKIŞ"])
                    miktar = st.number_input("İşlem Miktarı", min_value=0.1, step=1.0)
                with col2:
                    adres = st.text_input("Depo Adresi", value=info.get('ADRES', ''))
                
                if st.form_submit_button("KAYDET"):
                    personel = st.session_state.get('user', 'Sistem')
                    final_miktar = miktar if islem == "GİRİŞ" else -miktar
                    yeni_kayit = pd.DataFrame([{
                        "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Ürün Kodu": kod, "Ürün Adı": info['isim'], "Adres": adres,
                        "Miktar": final_miktar, "İşlem": islem, "Personel": personel
                    }])
                    conn.update(worksheet="HAREKETLER", data=pd.concat([df_hareketler, yeni_kayit], ignore_index=True))
                    st.success("İşlem Başarıyla Kaydedildi!")
                    st.balloons()
    except Exception as e:
        st.error(f"Hata: {e}")

def run_transfer(conn):
    st.subheader("↔️ Depo İçi Transfer (Adres Değişimi)")
    
    try:
        # VERİ ÇEKME - Daha güvenli hale getirildi
        df_stok = conn.read(worksheet="Urun_Listesi", ttl=0) # TTL=0 ile önbelleği zorla temizle
        df_hareketler = conn.read(worksheet="HAREKETLER", ttl=0)
        
        # Sütun isimlerini zorla temizle (Boşluk vs. varsa)
        df_stok.columns = [str(c).strip() for c in df_stok.columns]
        df_hareketler.columns = [str(c).strip() for c in df_hareketler.columns]

        search_transfer = st.text_input("🔍 Transfer Edilecek Ürünü Ara", key="trans_search")
        
        if search_transfer:
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
                    transfer_miktar = st.number_input("Transfer Miktarı", min_value=0.1)
                
                if st.form_submit_button("TRANSFERİ TAMAMLA"):
                    personel = st.session_state.get('user', 'Sistem')
                    tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    cikis = {"Tarih": tarih, "Ürün Kodu": sel_kodu, "Ürün Adı": urun_bilgi['isim'], 
                             "Adres": urun_bilgi.get('ADRES'), "Miktar": -transfer_miktar, "İşlem": "TRANSFER ÇIKIŞ", "Personel": personel}
                    
                    giris = {"Tarih": tarih, "Ürün Kodu": sel_kodu, "Ürün Adı": urun_bilgi['isim'], 
                             "Adres": yeni_adres, "Miktar": transfer_miktar, "İşlem": "TRANSFER GİRİŞ", "Personel": personel}
                    
                    updated_h = pd.concat([df_hareketler, pd.DataFrame([cikis, giris])], ignore_index=True)
                    conn.update(worksheet="HAREKETLER", data=updated_h)
                    st.success(f"Başarılı! {yeni_adres} adresine transfer edildi.")
                    st.balloons()
        else:
            st.warning("Ürün bulunamadı.")
            
    except Exception as e:
        st.error(f"Transfer ekranında veri işleme hatası: {e}")
