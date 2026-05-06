import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- VERİTABANI BAĞLANTISI ---
def get_db_connection():
    return sqlite3.connect('depo.db', check_same_thread=False)

def get_katalog():
    db = get_db_connection()
    try:
        df = pd.read_sql("SELECT kod, isim FROM Urun_Listesi", db)
        if not df.empty:
            return df.apply(lambda x: f"{x['kod']} | {x['isim']}", axis=1).tolist()
        return []
    except:
        return []
    finally:
        db.close()

# --- FORM TEMİZLEME ---
def clear_form():
    st.session_state.reset_form = True

# --- ÜRÜN SEÇİLİNCE KODU OTOMATİK DOLDUR ---
def urun_secildi():
    sec = st.session_state.get("sec")
    if sec and sec != "+ MANUEL GİRİŞ":
        st.session_state.s_kod = sec.split(" | ")[0]

# --- ANA FONKSİYON (app.py ile uyumlu olması için run_islem yapıldı) ---
def run_islem():
    # --- TOPLU LİSTE İÇİN SESSION STATE BAŞLATMA ---
    if "gecici_liste" not in st.session_state:
        st.session_state.gecici_liste = []

    # --- SIFIRLAMA BLOĞU ---
    if st.session_state.get("reset_form"):
        for k in ["s_kod", "s_lot", "s_mik", "sec", "src_adr", "dst_adr"]:
            if k in st.session_state:
                # Sayısal alan için özel durum, diğerleri için boş string
                st.session_state[k] = 0.0 if k == "s_mik" else ""
        st.session_state.reset_form = False

    # --- KAYIT SONRASI MESAJ ---
    if st.session_state.get("islem_basarili"):
        st.success(st.session_state.get("mesaj", "İşlem başarılı"))
        del st.session_state["islem_basarili"]
        del st.session_state["mesaj"]

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
            s_kod = st.text_input(
                "📦 Malzeme Kodu:",
                key="s_kod"
            ).upper().strip()
            
            s_lot = st.text_input("🔢 Parti/Lot No:", key="s_lot").upper().strip()
            
        with c2:
            s_mik = st.number_input("Miktar:", min_value=0.0, step=1.0, key="s_mik")
            s_dur = st.selectbox(
                "Durum:", 
                ["Kullanılabilir", "Hasarlı", "Karantina"], 
                key="s_dur"
            )

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

        # --- LİSTEYE EKLE ---
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
                
                # SIFIRLAMA TETİKLE
                clear_form()
                st.rerun()

    # --- GEÇİCİ LİSTE ---
    if st.session_state.gecici_liste:
        st.markdown("### 📋 İşlem Bekleyen Kalemler")
        for i, item in enumerate(st.session_state.gecici_liste):
            with st.expander(f"{i+1}. {item['İşlem']} | {item['Kod']} | {item['Miktar']} Adet"):
                st.write(f"**Ürün:** {item['İsim']} | **Lot:** {item['Lot']} | **Durum:** {item['Durum']}")
                st.write(f"**Adres:** {item['Kaynak']} ➡️ {item['Hedef']}")
                
                if st.button(f"🗑️ Bu Satırı Sil", key=f"del_{i}"):
                    st.session_state[f"confirm_del_{i}"] = True
                
                if st.session_state.get(f"confirm_del_{i}"):
                    st.warning("Emin misiniz?")
                    if st.button("Evet, Sil", key=f"yes_{i}"):
                        st.session_state.gecici_liste.pop(i)
                        del st.session_state[f"confirm_del_{i}"]
                        st.rerun()

        st.divider()

        # --- TOPLU KAYDET ---
        if st.button("🚀 TÜM HAREKETLERİ VERİTABANINA İŞLE", use_container_width=True, type="primary"):
            db = get_db_connection()
            try:
                df_stok = pd.read_sql("SELECT * FROM Stok", db)
                df_hareketler = pd.read_sql("SELECT * FROM Hareketler", db)
            except Exception as e:
                st.error(f"Veritabanı okuma hatası: {e}")
                db.close()
                return

            islem_zamani = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            personel = st.session_state.user if 'user' in st.session_state else "Sistem"
            
            df_stok['Kod'] = df_stok['Kod'].astype(str).str.strip().str.upper()
            df_stok['Adres'] = df_stok['Adres'].astype(str).str.strip().str.upper()
            df_stok['Miktar'] = pd.to_numeric(df_stok['Miktar'], errors='coerce').fillna(0)

            kaydedilen_sayi = 0
            for satir in st.session_state.gecici_liste:
                yeni_hareket_satiri = {
                    "Tarih": islem_zamani, "İşlem": satir["İşlem"], "İş Emri": "-", "Kod": satir["Kod"],
                    "İsim": satir["İsim"], "Adres": satir["Hedef"] if satir["İşlem"] == "GİRİŞ" else satir["Kaynak"],
                    "Miktar": satir["Miktar"], "Personel": personel, "Durum": satir["Durum"],
                    "Lot": satir["Lot"], "Kaynak_Adres": satir["Kaynak"], "Hedef_Adres": satir["Hedef"]
                }
                
                success_stok = False
                if satir["İşlem"] == "GİRİŞ":
                    mask = (df_stok['Kod'] == satir["Kod"]) & (df_stok['Adres'] == satir["Hedef"])
                    if mask.any(): 
                        df_stok.loc[mask, 'Miktar'] += satir["Miktar"]
                    else:
                        new_row = pd.DataFrame([{"Kod": satir["Kod"], "İsim": satir["İsim"], "Adres": satir["Hedef"], "Miktar": satir["Miktar"], "Durum": satir["Durum"]}])
                        df_stok = pd.concat([df_stok, new_row], ignore_index=True)
                    success_stok = True
                elif satir["İşlem"] == "ÇIKIŞ":
                    mask = (df_stok['Kod'] == satir["Kod"]) & (df_stok['Adres'] == satir["Kaynak"])
                    if mask.any():
                        mevcut = df_stok.loc[mask, 'Miktar'].values[0]
                        df_stok.loc[mask, 'Miktar'] = max(0, mevcut - satir["Miktar"])
                        success_stok = True
                elif satir["İşlem"] == "İÇ TRANSFER":
                    src_mask = (df_stok['Kod'] == satir["Kod"]) & (df_stok['Adres'] == satir["Kaynak"])
                    dst_mask = (df_stok['Kod'] == satir["Kod"]) & (df_stok['Adres'] == satir["Hedef"])
                    if src_mask.any():
                        mevcut_src = df_stok.loc[src_mask, 'Miktar'].values[0]
                        df_stok.loc[src_mask, 'Miktar'] = max(0, mevcut_src - satir["Miktar"])
                        if dst_mask.any(): 
                            df_stok.loc[dst_mask, 'Miktar'] += satir["Miktar"]
                        else:
                            new_row = pd.DataFrame([{"Kod": satir["Kod"], "İsim": satir["İsim"], "Adres": satir["Hedef"], "Miktar": satir["Miktar"], "Durum": satir["Durum"]}])
                            df_stok = pd.concat([df_stok, new_row], ignore_index=True)
                        success_stok = True

                if success_stok:
                    df_hareketler = pd.concat([df_hareketler, pd.DataFrame([yeni_hareket_satiri])], ignore_index=True)
                    kaydedilen_sayi += 1

            # --- PANDAS İLE SQLITE'A GERİ YAZMA ---
            df_stok.to_sql("Stok", db, if_exists="replace", index=False)
            df_hareketler.to_sql("Hareketler", db, if_exists="replace", index=False)
            db.close()
            
            st.session_state["islem_basarili"] = True
            st.session_state["mesaj"] = f"✅ {kaydedilen_sayi} kalem stok hareketi işlendi!"
            st.session_state.gecici_liste = []
            st.cache_data.clear()
            st.rerun()

# --- APP.PY TRANSFER MENÜSÜ İÇİN YÖNLENDİRİCİ ---
def run_transfer():
    run_islem()
