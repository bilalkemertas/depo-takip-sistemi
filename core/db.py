import sqlite3
import pandas as pd
from datetime import datetime
import streamlit as st
from streamlit_gsheets import GSheetsConnection

DB = "depo.db" # BÜTÜN SİSTEM ARTIK TEK BİR DB KULLANACAK

def conn():
    return sqlite3.connect(DB, check_same_thread=False)

# ---------------- INIT ----------------
def init_db():
    c = conn()
    cur = c.cursor()

    # Bütün modüllerin ihtiyaç duyduğu tüm tablolar burada yaratılıyor
    cur.execute('''CREATE TABLE IF NOT EXISTS Stok (id INTEGER PRIMARY KEY AUTOINCREMENT, Adres TEXT, Kod TEXT, İsim TEXT, Birim TEXT, Miktar REAL, Durum TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS Urun_Listesi (kod TEXT PRIMARY KEY, isim TEXT, Birim TEXT, adres TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS Hareketler (id INTEGER PRIMARY KEY AUTOINCREMENT, Tarih TEXT, İşlem TEXT, Kod TEXT, İsim TEXT, Adres TEXT, Miktar REAL, Personel TEXT, Lot TEXT, Kaynak_Adres TEXT, Hedef_Adres TEXT, "İş Emri" TEXT, Durum TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS Is_Emirleri ("İş Emri" TEXT, "Ürün Kodu" TEXT, "Mamül Adı" TEXT, "Stok Kodu" TEXT, "Stok Adı" TEXT, "İhtiyaç Miktarı" REAL, "Hazırlanan Adet" REAL, Birim TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS Mal_Kabul (Tarih TEXT, Irsaliye_No TEXT, Siparis_No TEXT, Tedarikci TEXT, Kod TEXT, Isim TEXT, Miktar REAL, Adres TEXT, Personel TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS sayim_snapshot (Oturum_Adi TEXT, Adres TEXT, Kod TEXT, İsim TEXT, Sistem_Stogu REAL)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS sayim (Oturum_Adi TEXT, Tarih TEXT, Adres TEXT, Kod TEXT, Miktar REAL, Personel TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS blokeli_stok (id INTEGER PRIMARY KEY AUTOINCREMENT, kod TEXT, adres TEXT, miktar REAL, sebep TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, tarih TEXT, user TEXT, action TEXT, detay TEXT)''')

    c.commit()
    c.close()

# ---------------- READ ----------------
def read(table):
    c = conn()
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table}", c)
    except Exception:
        df = pd.DataFrame()
    c.close()
    return df

# ---------------- WRITE (FULL REPLACE) ----------------
def write(table, df):
    c = conn()
    df.to_sql(table, c, if_exists="replace", index=False)
    c.close()

# ---------------- LOG ----------------
def log(user, action, detail):
    c = conn()
    cur = c.cursor()
    cur.execute("""
        INSERT INTO audit_log (tarih, user, action, detay)
        VALUES (?, ?, ?, ?)
    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user, action, detail))
    c.commit()
    c.close()

# ---------------- DRIVE EXCEL (GSHEETS) EŞİTLEME ----------------
def get_drive_conn():
    return st.connection("gsheets", type=GSheetsConnection)

def sync_to_drive():
    g_conn = get_drive_conn()
    tablolar = {
        "Stok": "Stok",
        "Urun_Listesi": "Urun_Listesi",
        "Hareketler": "Hareketler",
        "sayim_snapshot": "sayim_snapshot",
        "Is_Emirleri": "Is_Emirleri"
    }
    for sql_table, sheet_name in tablolar.items():
        try:
            df = read(sql_table)
            if not df.empty:
                g_conn.update(worksheet=sheet_name, data=df)
        except Exception:
            pass

def sync_from_drive():
    g_conn = get_drive_conn()
    tablolar = {
        "Stok": "Stok",
        "Urun_Listesi": "Urun_Listesi",
        "Hareketler": "Hareketler",
        "sayim_snapshot": "sayim_snapshot",
        "Is_Emirleri": "Is_Emirleri"
    }
    
    basarili = []
    hatali = []
    
    for sheet_name, sql_table in tablolar.items():
        try:
            df = g_conn.read(worksheet=sheet_name, ttl=0)
            if isinstance(df, pd.DataFrame):
                df.columns = [str(c).strip() for c in df.columns] # Sütun isimlerini koru
                write(sql_table, df)
                basarili.append(sheet_name)
            else:
                hatali.append(f"{sheet_name} (Veri formati geçersiz)")
        except Exception as e:
            hata_mesaji = str(e)
            if "Response [200]" in hata_mesaji:
                hatali.append(f"{sheet_name} (Google güvenlik engeli! Lütfen Excel'i 'Web'de Yayınla' yapın)")
            else:
                hatali.append(f"{sheet_name} (Hata: {hata_mesaji[:30]}...)")
            
    return basarili, hatali
