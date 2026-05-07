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
        
        # 1. STOK TABLOSU
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
        
        # 2. HAREKETLER TABLOSU
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
        
        # 3. ÜRÜN KATALOĞU
        cur.execute("""
            CREATE TABLE IF NOT EXISTS urun_listesi (
                kod TEXT PRIMARY KEY, 
                isim TEXT, 
                birim TEXT, 
                adres TEXT
            )
        """)
        
        # 4. MAL KABUL TABLOSU
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mal_kabul (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT, irsaliye_no TEXT, siparis_no TEXT, tedarikci TEXT,
                kod TEXT, isim TEXT, miktar REAL, adres TEXT, personel TEXT
            )
        """)
        
        # 5. LOG SİSTEMİ
        cur.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT, personel TEXT, islem_tipi TEXT, detay TEXT
            )
        """)
        c.commit()

def read(table):
    """Tabloyu okur ve sütun isimlerini standart küçük harfe çeker."""
    try:
        with conn() as c:
            df = pd.read_sql_query(f"SELECT * FROM {table.lower()}", c)
            if not df.empty:
                # SÜTUN ZIRHLAMA: Tüm sütunları temizle ve küçük harf yap
                df.columns = [str(c).strip().lower() for c in df.columns]
            return df
    except Exception as e:
        return pd.DataFrame()

def write(table, df, exists_action='replace'):
    with conn() as c:
        table_name = table.lower()
        if exists_action == 'append':
            # SQLite Auto-Increment id ile Pandas'ın çakışmasını engelle
            if 'id' in df.columns:
                df = df.drop(columns=['id'])
            df.to_sql(table_name, c, if_exists='append', index=False)
        else:
            df.to_sql(table_name, c, if_exists='replace', index=False)

def sync_to_drive():
    try:
        g_conn = st.connection("gsheets", type=GSheetsConnection)
        tablolar = {"stok": "Stok", "hareketler": "Hareketler", "mal_kabul": "Mal_Kabul"}
        for sql_t, sheet_n in tablolar.items():
            df = read(sql_t)
            if not df.empty:
                g_conn.update(worksheet=sheet_n, data=df)
    except Exception as e:
        st.error(f"Drive Yazma Hatası: {e}")

def sync_from_drive():
    try:
        g_conn = st.connection("gsheets", type=GSheetsConnection)
        tablolar = {"Stok": "stok", "Urun_Listesi": "urun_listesi", "Hareketler": "hareketler", "Mal_Kabul": "mal_kabul"}
        for sheet, sql in tablolar.items():
            try:
                df = g_conn.read(worksheet=sheet, ttl=0)
                if df is not None and not df.empty:
                    df.columns = [str(c).strip().lower() for c in df.columns]
                    write(sql, df, 'replace')
            except: continue
    except Exception as e:
        st.error(f"Katalog İndirme Hatası: {e}")
