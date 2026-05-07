import sqlite3
import pandas as pd
from datetime import datetime
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# VERİTABANI AYARLARI
DB = "depo.db"

def conn():
    """SQLite veritabanı bağlantısını oluşturur ve döndürür."""
    return sqlite3.connect(DB, check_same_thread=False, timeout=60)

def init_db():
    """Veritabanı tablolarını ilk kez oluşturur (IF NOT EXISTS)."""
    with conn() as c:
        c.execute("PRAGMA journal_mode=WAL;")
        cur = c.cursor()
        
        # 1. STOK TABLOSU (GÜNCEL DURUM)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stok (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                kod TEXT, 
                isim TEXT, 
                adres TEXT, 
                miktar REAL, 
                durum TEXT
            )
        """)
        
        # 2. HAREKETLER TABLOSU (LOG KAYITLARI)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS hareketler (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                tarih TEXT, 
                islem TEXT, 
                kod TEXT, 
                isim TEXT, 
                kaynak TEXT, 
                hedef TEXT, 
                miktar REAL, 
                user TEXT, 
                aciklama TEXT
            )
        """)
        
        # 3. ÜRÜN KATALOĞU TABLOSU
        cur.execute("""
            CREATE TABLE IF NOT EXISTS urun_listesi (
                kod TEXT PRIMARY KEY, 
                isim TEXT, 
                birim TEXT, 
                adres TEXT
            )
        """)
        
        # 4. MAL KABUL TABLOSU (PATRONUN EMRİ)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mal_kabul (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT,
                irsaliye_no TEXT,
                siparis_no TEXT,
                tedarikci TEXT,
                kod TEXT,
                isim TEXT,
                miktar REAL,
                adres TEXT,
                personel TEXT
            )
        """)
        
        # 5. LOG SİSTEMİ (OPSİYONEL AMA KURUMSAL YAPI İÇİN ŞART)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT,
                personel TEXT,
                islem_tipi TEXT,
                detay TEXT
            )
        """)
        
        c.commit()

def read(table):
    """Belirtilen tabloyu okur ve sütun isimlerini standart hale getirir."""
    try:
        with conn() as c:
            table_name = table.lower()
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", c)
            if not df.empty:
                # Sütun isimlerini zorla küçük harf yap (Hata Çözümü)
                df.columns = [str(c).strip().lower() for c in df.columns]
            return df
    except Exception as e:
        # Hata durumunda boş dataframe döner
        return pd.DataFrame()

def write(table, df, exists_action='replace'):
    """
    Veriyi veritabanına yazar.
    exists_action: 'replace' (üstüne yazar - stok için)
    exists_action: 'append' (altına ekler - hareketler için)
    """
    with conn() as c:
        table_name = table.lower()
        
        # EĞER APPEND YAPILIYORSA VE ID VARSA SQLite ÇAKIŞMASINI ÖNLE
        if exists_action == 'append':
            if 'id' in df.columns:
                df = df.drop(columns=['id'])
            
            # SADECE VERİTABANINDA OLAN SÜTUNLARI GÖNDER
            df.to_sql(table_name, c, if_exists='append', index=False)
        else:
            # Standart replace işlemi (Komple güncelleme)
            df.to_sql(table_name, c, if_exists='replace', index=False)

def log(personel, islem, detay):
    """Sistem loglarını kaydeder."""
    try:
        with conn() as c:
            is_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO logs (tarih, personel, islem_tipi, detay) VALUES (?, ?, ?, ?)",
                      (is_time, personel, islem, detay))
            c.commit()
    except:
        pass

def sync_to_drive():
    """SQLite verilerini Google Sheets sekmelerine (Stok, Hareketler, Mal_Kabul) basar."""
    try:
        g_conn = st.connection("gsheets", type=GSheetsConnection)
        
        # SQL Tablo İsmi -> Drive Sekme İsmi
        tablolar = {
            "stok": "Stok", 
            "hareketler": "Hareketler", 
            "mal_kabul": "Mal_Kabul"
        }
        
        for sql_t, sheet_n in tablolar.items():
            df = read(sql_t)
            if not df.empty:
                # Drive tarafına yazarken id sütununu da ekleyebiliriz (Takip için)
                g_conn.update(worksheet=sheet_n, data=df)
    except Exception as e:
        st.error(f"Drive Senkronizasyon Hatası (Buluta Yazılamadı): {e}")

def sync_from_drive():
    """Google Sheets sekmelerinden veriyi çekip SQLite'a 'replace' modunda yazar."""
    try:
        g_conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Drive Sekme İsmi -> SQL Tablo İsmi
        tablolar = {
            "Stok": "stok", 
            "Urun_Listesi": "urun_listesi", 
            "Hareketler": "hareketler", 
            "Mal_Kabul": "mal_kabul"
        }
        
        for sheet, sql in tablolar.items():
            try:
                df = g_conn.read(worksheet=sheet, ttl=0)
                if df is not None and not df.empty:
                    # Sütun isimlerini SQLite standardına getir (Küçük harf ve boşluksuz)
                    df.columns = [str(c).strip().lower() for c in df.columns]
                    write(sql, df, 'replace')
            except:
                continue
    except Exception as e:
        st.error(f"Katalog İndirme Hatası: {e}")

# --- DB.PY SONU ---
