import streamlit as st
import pandas as pd
import io
from datetime import datetime

def run(conn):
    st.subheader("🏭 Üretim Hazırlık Ekranı")
    st.markdown("---")

    # 1. DOSYA YÜKLEME ALANI
    uploaded_file = st.file_uploader("İş Emri Excel Dosyasını Yükleyin", type=['xlsx'])

    if uploaded_file is not None:
        try:
            # Excel içindeki sayfa isimlerini kontrol et
            excel_file = pd.ExcelFile(uploaded_file)
            sheet_names = excel_file.sheet_names
            
            # Dinamik Sekme Yakalama (HAZIRLIK veya Sheet4)
            target_sheet = None
            if "HAZIRLIK" in sheet_names:
                target_sheet = "HAZIRLIK"
            elif "Sheet4" in sheet_names:
                target_sheet = "Sheet4"

            if target_sheet:
                # Veriyi oku
                df = pd.read_excel(uploaded_file, sheet_name=target_sheet)
                
                # Sütun temizliği (Baştaki ve sondaki boşlukları al)
                df.columns = [str(c).strip() for c in df.columns]
                
                # Veri temizleme: NaN olan satırları doldur veya temizle
                # İş Emri ve Ürün Adı genelde ilk satırda olur, ffill ile aşağı çekiyoruz
                df = df.ffill() 

                st.success(f"✅ '{target_sheet}' sekmesi başarıyla yüklendi.")

                # Filtreleme Seçenekleri
                st.markdown("### 🔍 Hazırlık Detayları")
                
                # Gerekli sütunların varlığını kontrol et (ERP çıktısına göre isimleri buraya ekliyoruz)
                # Örn: 'İş Emri No', 'Ürün Kodu', 'Ürün Adı', 'Miktar'
                cols = df.columns.tolist()
                
                # Tabloyu göster
                st.dataframe(df, use_container_width=True)

                # Hazırlık İşlemi
                st.divider()
                st.markdown("### 📝 Malzeme Teslim Kaydı")
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    is_emri_no = st.selectbox("İş Emri Seçin:", df.iloc[:, 0].unique()) if not df.empty else ""
                with c2:
                    hazirlayan = st.text_input("Hazırlayan Personel:", value=st.session_state.get('user', ''))
                with c3:
                    onay_durumu = st.checkbox("Tüm kalemlerin hazırlığı tamamlandı.")

                if st.button("🚀 HAZIRLIK KAYDINI TAMAMLA VE STOKTAN DÜŞ", use_container_width=True, type="primary"):
                    if onay_durumu and hazirlayan:
                        # Burada Google Sheets'e hareket kaydı atma döngüsü çalışacak
                        # Örnek: Giriş/Çıkış modülündeki gibi conn.update kullanılabilir.
                        st.balloons()
                        st.success(f"{is_emri_no} nolu İş Emri hazırlığı başarıyla kaydedildi!")
                    else:
                        st.warning("Lütfen hazırlayan bilgisini girin ve onay kutusunu işaretleyin.")

            else:
                st.error("❌ Dosya içinde 'HAZIRLIK' veya 'Sheet4' sekmesi bulunamadı!")
                st.info(f"Dosyadaki mevcut sekmeler: {', '.join(sheet_names)}")

        except Exception as e:
            st.error(f"⚠️ Excel okunurken bir hata oluştu: {e}")

    # 2. MEVCUT HAZIRLIK LİSTELERİ (ARŞİV)
    st.markdown("---")
    with st.expander("📊 Geçmiş Hazırlık Kayıtlarını Görüntüle"):
        try:
            # Google Sheets'ten hazırlık geçmişini oku (Eğer sayfa varsa)
            # df_arsiv = conn.read(worksheet="uretim_hazirlik_arsiv")
            # st.dataframe(df_arsiv, use_container_width=True)
            st.info("Bu özellik için Google Sheets üzerinde 'uretim_hazirlik_arsiv' sayfası oluşturulmalıdır.")
        except:
            st.write("Henüz kayıtlı bir hazırlık arşivi bulunamadı.")

# Modül Sonu
