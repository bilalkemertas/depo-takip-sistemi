import sqlite3
import pandas as pd
from datetime import datetime
import streamlit as st
from streamlit_gsheets import GSheetsConnection

DB = "depo.db"

def conn():
    return sqlite3.connect(DB, check_same_thread=False, timeout=30)

def init_db():
    with conn() as c:
        c.execute("PRAGMA journal_mode=WAL;")
        cur = c.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS stok (id INTEGER PRIMARY KEY AUTOINCREMENT, kod TEXT, isim TEXT, adres TEXT, miktar REAL, durum TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS hareketler (id INTEGER PRIMARY KEY AUTOINCREMENT, tarih TEXT, islem TEXT, kod TEXT, isim TEXT, kaynak TEXT, hedef TEXT, miktar REAL, user TEXT, aciklama TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS urun_listesi (kod TEXT PRIMARY KEY, isim TEXT, birim TEXT, adres TEXT)")
        c.commit()

def read(table):
    try:
        with conn() as c:
            # Tablo ismini küçük harfe zorlayarak SQLite uyumunu garanti et
            return pd.read_sql_query(f"SELECT * FROM {table.lower()}", c)
    except:
        return pd.DataFrame()

# --- HATA ÇÖZÜCÜ: APPEND ÇAKIŞMASINI BİTİREN YAZMA MANTIĞI ---
def write(table, df, exists_action='replace'):
    with conn() as c:
        table_name = table.lower()
        
        if exists_action == 'append':
            # Veritabanındaki gerçek sütun isimlerini al
            cursor = c.execute(f"PRAGMA table_info({table_name})")
            db_cols = [col[1] for col in cursor.fetchall()]
            
            # DataFrame içindeki sütunları veritabanındakilerle eşle (id hariç)
            # Eğer df içinde 'id' varsa onu düşür, SQLite kendi versin
            cols_to_keep = [col for col in df.columns if col in db_cols and col != 'id']
            df_to_save = df[cols_to_keep]
            
            df_to_save.to_sql(table_name, c, if_exists='append', index=False)
        else:
            # Stok tablosu gibi 'replace' işlemleri için standart yol
            df.to_sql(table_name, c, if_exists='replace', index=False)

def sync_to_drive():
    g_conn = st.connection("gsheets", type=GSheetsConnection)
    tablolar = {"stok": "Stok", "hareketler": "Hareketler"}
    for sql_t, sheet_n in tablolar.items():
        df = read(sql_t)
        if not df.empty:
            g_conn.update(worksheet=sheet_n, data=df)

def sync_from_drive():
    g_conn = st.connection("gsheets", type=GSheetsConnection)
    tablolar = {"Stok": "stok", "Urun_Listesi": "urun_listesi", "Hareketler": "hareketler"}
    for sheet, sql in tablolar.items():
        try:
            df = g_conn.read(worksheet=sheet, ttl=0)
            if not df.empty:
                df.columns = [str(c).strip().lower() for c in df.columns]
                write(sql, df, 'replace')
        except: pass
