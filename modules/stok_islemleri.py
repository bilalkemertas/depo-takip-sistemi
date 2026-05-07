import streamlit as st
from core import db
import pandas as pd
from datetime import datetime

@st.cache_data(ttl=600)
def get_katalog():
    try:
        # Tablo yoksa önce yarat! ---
        db.init_db()
        
        df_katalog = db.read("urun_listesi")
        if not df_katalog.empty:
            # Sütunları temizle ve büyük harf yap (Eşleşme için)
            df_katalog.columns = [str(c).strip().upper() for c in df_katalog.columns]
            
            # Hem küçük hem büyük harf başlıkları yakalar
            kod_col = next((c for c in df_katalog.columns if 'KOD' in c), None)
            isim_col = next((c for c in df_katalog.columns if 'ISIM' in c or 'İSİM' in c), None)
            
            if kod_col and isim_col:
                return df_katalog.apply(lambda x: f"{x[kod_col]} | {x[isim_col]}", axis=1).tolist()
            else:
                st.error("Urun_Listesi tablosunda 'KOD' ve 'İSİM' sütunları bulunamadı!")
                return []
        return []
    except Exception as e:
        st.error(f"Katalog okuma hatası: {e}")
        return []

def clear_form():
    st.session_state.reset_form = True

def urun_secildi():
    sec = st.session_state.get("sec")
    if sec and sec != "+ MANUEL GİRİŞ":
        st.session_state.s_kod = sec.split(" | ")[0]

def run_islem():
    if "gecici_liste" not in st.session_state:
        st.session_state.gecici_liste = []

    if st.session_state.get("reset_form"):
        for k in ["s_kod", "s_lot", "s_mik", "sec", "src_adr", "dst_adr"]:
            if k in st.session_state:
                st.session_state[k] = 0.0 if k == "s_mik" else ""
        st.session_state.reset_form = False

    if st.session_state.get("islem_basarili"):
        st.success(st.session_state.get("mesaj", "İşlem başarılı"))
        del st.session_state["islem_basarili"]
        del st.session_state["mesaj"]

    # --- YENİ SENKRONİZASYON BUTONU ---
    if st.button("🔄 Drive'dan Katalog İndir", type="secondary"):
        with st.spinner("Katalog güncelleniyor..."):
            db.init_db()
            basarili, hatali = db.sync_from_drive()
        
        if basarili:
            st.success(f"✅ Başarıyla İnenler: {', '.join(basarili)}")
            st.cache_data.clear()
        if hatali:
            st.error(f"❌ İndirilemeyenler: {', '.join(hatali)}")
            st.info("💡 Lütfen Drive Excel dosyanızdaki sekme isimlerinin (örn: 'Urun_Listesi') birebir aynı olduğundan emin olun.")
        st.rerun()

    st.subheader("📊 Stok Hareketleri (Toplu İşlem)")
    
    with st.container(border=True):
        move_type = st.selectbox(
            "İşlem Tipi:", 
            ["GİRİŞ", "ÇIKIŞ", "İÇ TRANSFER"], 
            key="move_type"
        )
        
        katalog = get_katalog()
        sec = st.selectbox(
            "🔍 Ürün Seç:", 
            ["+ MANUEL GİRİŞ"] + katalog, 
            key="sec",
            on_change=urun_secildi
        )
        
        c1, c2 = st.columns(2)
        with c1:
            s_kod = st.text_input("📦 Malzeme Kodu:", key="s_kod").upper().strip()
            s_lot = st.text_input("🔢 Parti/Lot No:", key="s_lot").upper().strip()
            
        with c2:
            s_mik = st.number_input("Miktar:", min_value=0.0, step=1.0, key="s_mik")
            s_dur = st.selectbox("Durum:", ["Kullanılabilir", "Hasarlı", "Karantina"], key="s_dur")

        st.markdown("---")
        
        src_adr = "-"
        dst_adr = "-"
        
        a1, a2 = st.columns(2)

        if move_type == "GİRİŞ":
            with a1:
                dst_adr = st.text_input("📍 Hedef Adres (Nereye):", key="dst_adr").upper().strip()
        elif move_type == "ÇIKIŞ":
            with a1:
                src_adr = st.text_input("📍 Kaynak Adres (Nereden):", key="src_adr").upper().strip()
        elif move_type == "İÇ TRANSFER":
            with a1:
                src_adr = st.text_input("📍 Kaynak Adres (Nereden):", key="src_adr").upper().strip()
            with a2:
                dst_adr = st.text_input("📍 Hedef Adres (Nereye):", key="dst_adr").upper().strip()

        if st.button("➕ LİSTEYE EKLE", use_container_width=True):
            if not s_kod or s_mik <= 0:
                st.error("Eksik bilgi!")
            else:
                kalem = {
                    "İşlem": move_type,
                    "Kod": s_kod,
                    "İsim": sec.split(" | ")[1] if sec != "+ MANUEL GİRİŞ" and len(sec.split(" | ")) > 1 else "MANUEL ÜRÜN",
                    "Miktar": s_mik,
                    "Lot": s_lot,
                    "Durum": s_dur,
                    "Kaynak": src_adr,
                    "Hedef": dst_adr
                }
                st.session_state.gecici_liste.append(kalem)
                clear_form()
                st.rerun()

    if st.session_state.gecici_liste:
        st.markdown("### 📋 İşlem Bekleyen Kalemler")
        for i, item in enumerate(st.session_state.gecici_liste):
            with st.expander(f"{i+1}. {item['İşlem']} | {item['Kod']} | {item['Miktar']} Adet"):
                st.write(f"**Ürün:** {item['İsim']} | **Lot:** {item['Lot']} | **Durum:** {item['Durum']}")
                st.write(f"**Adres:** {item['Kaynak']} ➡️ {item['Hedef']}")
                
                if st.button(f"🗑️ Bu Satırı Sil", key=f"del_{i}"):
                    st.session_state.gecici_liste.pop(i)
                    st.rerun()

        st.divider()

        if st.button("🚀 TÜM HAREKETLERİ VERİTABANINA İŞLE", use_container_width=True, type="primary"):
            try:
                # --- SQLITE SENKRONİZASYON HATASINI ÇÖZEN KRİTİK BLOK ---
                isleme_alinacaklar = list(st.session_state.gecici_liste)
                st.session_state.gecici_liste = [] # Hafızayı hemen boşalt ki vagon yapmasın
                
                df_stok = db.read("stok")
                df_hareketler = db.read("hareketler")
                
                islem_zamani = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                personel = st.session_state.user if 'user' in st.session_state else "Sistem"
                
                # Veri tipi zorlaması (Mükerrer kontrolü için şart)
                df_stok['kod'] = df_stok['kod'].astype(str).str.strip().upper()
                df_stok['adres'] = df_stok['adres'].astype(str).str.strip().upper()

                kaydedilen_sayi = 0
                for satir in isleme_alinacaklar:
                    yeni_hkt = {"tarih": islem_zamani, "islem": satir["İşlem"], "kod": satir["Kod"], "isim": satir["İsim"], "kaynak": satir["Kaynak"], "hedef": satir["Hedef"], "miktar": satir["Miktar"], "user": personel, "aciklama": satir["Lot"]}
                    
                    if satir["İşlem"] == "GİRİŞ":
                        mask = (df_stok['kod'] == satir["Kod"]) & (df_stok['adres'] == satir["Hedef"])
                        if mask.any(): 
                            df_stok.loc[mask, 'miktar'] += satir["Miktar"]
                        else:
                            new_row = pd.DataFrame([{"kod": satir["Kod"], "isim": satir["İsim"], "adres": satir["Hedef"], "miktar": satir["Miktar"], "durum": satir["Durum"]}])
                            df_stok = pd.concat([df_stok, new_row], ignore_index=True)
                    elif satir["İşlem"] == "ÇIKIŞ":
                        mask = (df_stok['kod'] == satir["Kod"]) & (df_stok['adres'] == satir["Kaynak"])
                        if mask.any():
                            df_stok.loc[mask, 'miktar'] = max(0, df_stok.loc[mask, 'miktar'].values[0] - satir["Miktar"])

                    df_hareketler = pd.concat([df_hareketler, pd.DataFrame([yeni_hkt])], ignore_index=True)
                    kaydedilen_sayi += 1

                # SQLite'a yaz ve Drive'ı zorla güncelle
                db.write("stok", df_stok)
                db.write("hareketler", df_hareketler)
                db.sync_to_drive()
                
                st.session_state["islem_basarili"] = True
                st.session_state["mesaj"] = f"✅ {kaydedilen_sayi} kalem işlendi."
                st.cache_data.clear() # Cache'i temizle ki Stok sekmesi yeni halini görsün
                st.rerun()
            except Exception as e:
                st.error(f"Hata: {e}")

def run_transfer():
    run_islem()
