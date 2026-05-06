import streamlit as st
import pandas as pd
from datetime import datetime

def run_islem(conn):
    st.subheader("📊 Stok Giriş / Çıkış Paneli")
    try:
        # Veri çekme ve sütun temizliği
        df_stok = conn.read(worksheet="Urun_Listesi", ttl=0)
        df_hareketler = conn.read(worksheet="Hareketler", ttl=0)
        
        # Sütun isimlerini normalize et
        df_stok.columns = [str(c).strip() for c in df_stok.columns]
        
        search = st.text_input("🔍 Ürün Ara (Ad/Kod)", "", key="stok_search")
        
        # Görseline göre 'kod' ve 'isim' sütunlarını kontrol ediyoruz
        if search:
            mask = df_stok['isim'].astype(str).str.contains(search, case=False, na=False) | \
                   df_stok['kod'].astype(str).str.contains(search, case=False, na=False)
            filtered = df_stok[mask]
        else:
            filtered = df_stok

        if not filtered.empty:
            # Görseldeki küçük harf başlıklarına göre seçim kutusu
            options = filtered.apply(lambda x: f"{x['kod']} | {x['isim']}", axis=1).tolist()
            selected_option = st.selectbox("Ürünü Onaylayın:", options)
            
            sel_kodu = selected_option.split(" | ")[0]
            urun_bilgi = df_stok[df_stok['kod'] == sel_kodu].iloc[0]
            
            # Stok bilgisini 'Stok' sekmesinden güncel çekmek için (Görseldeki Stok sayfası)
            df_canli = conn.read(worksheet="Stok", ttl=0)
            mevcut_miktar = df_canli[df_canli['Kod'] == sel_kodu]['Miktar'].sum()
            
            st.info(f"📦 Mevcut Toplam Stok: {mevcut_miktar}")
            
            with st.form("islem_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    islem = st.selectbox("İşlem Türü", ["GİRİŞ", "ÇIKIŞ"])
                    miktar = st.number_input("İşlem Miktarı", min_value=0.1, step=1.0)
                with col2:
                    # 'Stok' sayfasındaki Adres başlığına göre varsayılan getir
                    varsayilan_adres = df_canli[df_canli['Kod'] == sel_kodu]['Adres'].iloc[0] if not df_canli[df_canli['Kod'] == sel_kodu].empty else ""
                    adres = st.text_input("Depo Adresi", value=varsayilan_adres)
                
                if st.form_submit_button("KAYDET"):
                    personel = st.session_state.get('user', 'Patron')
                    final_miktar = miktar if islem == "GİRİŞ" else -miktar
                    
                    yeni_kayit = pd.DataFrame([{
                        "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "İşlem": islem,
                        "Kod": sel_kodu,
                        "İsim": urun_bilgi['isim'],
                        "Adres": adres,
                        "Miktar": final_miktar,
                        "Personel": personel
                    }])
                    
                    updated_h = pd.concat([df_hareketler, yeni_kayit], ignore_index=True)
                    conn.update(worksheet="Hareketler", data=updated_h)
                    st.success("İşlem başarıyla kaydedildi!")
                    st.balloons()
    except Exception as e:
        st.error(f"Hata: {e}")

def run_transfer(conn):
    st.subheader("↔️ Depo İçi Transfer (Adres Değişimi)")
    
    try:
        # Görseldeki 'Stok' sayfasını ana kaynak olarak kullanıyoruz
        df_stok = conn.read(worksheet="Stok", ttl=0)
        df_hareketler = conn.read(worksheet="Hareketler", ttl=0)
        
        # Sütun isimlerini görsele göre normalize et (Adres, Kod, İsim, Miktar)
        df_stok.columns = [str(c).strip() for c in df_stok.columns]

        search_transfer = st.text_input("🔍 Transfer Edilecek Ürünü Ara (Ad/Kod)", key="trans_search")
        
        if search_transfer:
            mask = df_stok['İsim'].astype(str).str.contains(search_transfer, case=False, na=False) | \
                   df_stok['Kod'].astype(str).str.contains(search_transfer, case=False, na=False)
            filtered_df = df_stok[mask]
        else:
            filtered_df = df_stok

        if not filtered_df.empty:
            # Görseldeki başlıklar: Kod | İsim | Adres
            options = filtered_df.apply(lambda x: f"{x['Kod']} | {x['İsim']} | {x['Adres']}", axis=1).tolist()
            selected_option = st.selectbox("Ürünü ve Mevcut Adresi Seçin:", options, key="trans_select")
            
            sel_kodu = selected_option.split(" | ")[0]
            eski_adres = selected_option.split(" | ")[2]
            urun_bilgi = df_stok[(df_stok['Kod'] == sel_kodu) & (df_stok['Adres'] == eski_adres)].iloc[0]
            
            with st.form("transfer_formu"):
                st.info(f"📦 Ürün: {urun_bilgi['İsim']} (Mevcut: {urun_bilgi['Miktar']})")
                
                col1, col2 = st.columns(2)
                with col1:
                    yeni_adres = st.text_input("Hedef (Yeni) Adres")
                with col2:
                    transfer_miktar = st.number_input("Transfer Miktarı", min_value=0.1, max_value=float(urun_bilgi['Miktar']))
                
                if st.form_submit_button("TRANSFERİ TAMAMLA"):
                    personel = st.session_state.get('user', 'Patron')
                    tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Çıkış ve Giriş hareketlerini hazırla
                    cikis = {"Tarih": tarih, "İşlem": "TRANSFER ÇIKIŞ", "Kod": sel_kodu, "İsim": urun_bilgi['İsim'], 
                             "Adres": eski_adres, "Miktar": -transfer_miktar, "Personel": personel}
                    
                    giris = {"Tarih": tarih, "İşlem": "TRANSFER GİRİŞ", "Kod": sel_kodu, "İsim": urun_bilgi['İsim'], 
                             "Adres": yeni_adres, "Miktar": transfer_miktar, "Personel": personel}
                    
                    updated_h = pd.concat([df_hareketler, pd.DataFrame([cikis, giris])], ignore_index=True)
                    conn.update(worksheet="Hareketler", data=updated_h)
                    st.success(f"Başarılı! Ürün {eski_adres} -> {yeni_adres} adresine taşındı.")
                    st.balloons()
        else:
            st.warning("Ürün bulunamadı.")
            
    except Exception as e:
        st.error(f"Transfer ekranında hata: {e}")
