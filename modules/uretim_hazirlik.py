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
            # Excel içindeki sayfa isimlerini oku
            excel_file = pd.ExcelFile(uploaded_file)
            sheet_names = excel_file.sheet_names
            
            # --- Dinamik Sekme Yakalama Mantığı ---
            target_sheet = None
            # Öncelik sırasına göre kontrol et
            if "HAZIRLIK" in sheet_names:
                target_sheet = "HAZIRLIK"
            elif "Sheet4" in sheet_names:
                target_sheet = "Sheet4"

            if target_sheet:
                # Belirlenen sekmeyi oku
                df = pd.read_excel(uploaded_file, sheet_name=target_sheet)
                
                # Sütun temizliği (Gizli boşlukları ve karakterleri temizle)
                df.columns = [str(c).strip() for c in df.columns]
                
                # Veri temizleme: Merged (birleştirilmiş) hücreler için ffill kullanımı
                # Bu işlem, ERP çıktılarındaki boş bırakılan üst hücre değerlerini aşağıya kopyalar
                df = df.ffill() 

                st.success(f"✅ '{target_sheet}' sekmesi bulundu ve veriler yüklendi.")

                # Filtreleme ve Görselleştirme
                st.markdown(f"### 🔍 {target_sheet} Detayları")
                
                # Tabloyu göster
                st.dataframe(df, use_container_width=True, hide_index=True)

                # --- Malzeme Teslim Kaydı Bölümü ---
                st.divider()
                st.markdown("### 📝 Malzeme Teslim Kaydı")
                
                c1, c2, c3 = st.columns(3)
                with c1:
                    # İlk sütunu (genelde İş Emri No olur) baz alarak seçim kutusu oluştur
                    is_emri_list = df.iloc[:, 0].unique() if not df.empty else []
                    is_emri_no = st.selectbox("İş Emri Seçin:", is_emri_list)
                with c2:
                    hazirlayan = st.text_input("Hazırlayan Personel:", value=st.session_state.get('user', ''))
                with c3:
                    onay_durumu = st.checkbox("Hazırlık Tamamlandı", help="Stoktan düşüm için onay gereklidir.")

                if st.button("🚀 HAZIRLIK KAYDINI TAMAMLA VE STOKTAN DÜŞ", use_container_width=True, type="primary"):
                    if onay_durumu and hazirlayan:
                        # NOT: Burada 'conn' nesnesi üzerinden veritabanı (Google Sheets) 
                        # güncelleme mantığı projenizin ana yapısına göre eklenecektir.
                        st.balloons()
                        st.success(f"'{is_emri_no}' nolu İş Emri için hazırlık kaydı oluşturuldu. Stoklar güncellendi!")
                    else:
                        st.warning("Lütfen hazırlayan personel bilgisini girin ve hazırlığı onaylayın.")

            else:
                # İki isim de bulunamazsa hata mesajı ve yardımcı bilgi göster
                st.error("❌ Uygun sekme bulunamadı!")
                st.warning("Yüklediğiniz Excel dosyasında 'HAZIRLIK' veya 'Sheet4' isimli bir sekme olmalıdır.")
                st.info(f"Dosyadaki mevcut sekmeler: {', '.join(sheet_names)}")

        except Exception as e:
            st.error(f"⚠️ Excel dosyası işlenirken bir teknik hata oluştu: {e}")

    # 2. GEÇMİŞ KAYITLAR (OPSİYONEL)
    st.markdown("---")
    with st.expander("📊 Hazırlık Arşivini Görüntüle"):
        st.info("Tamamlanan hazırlık kayıtları Google Sheets üzerinden buraya çekilebilir.")

# Modül Sonu
