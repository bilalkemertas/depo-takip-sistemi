import sqlite3
import pandas as pd
from datetime import datetime
import streamlit as st
from streamlit_gsheets import GSheetsConnection

DB = "depo.db"

def conn():
    return sqlite3.connect(DB, check_same_thread=False, timeout=60)

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
            return pd.read_sql_query(f"SELECT * FROM {table.lower()}", c)
    except:
        return pd.DataFrame()

# --- GÜVENLİ WRITE: DEFAULT 'FAIL' MODUNU YASAKLADIK ---
def write(table, df, exists_action='replace'):
    with conn() as c:
        table_name = table.lower()
        
        # Hata Analizi: Eğer bir şekilde parametre gelmezse 'fail' yerine 'replace' yap
        action = exists_action if exists_action in ['append', 'replace'] else 'replace'
        
        # Append sırasında id çakışmasını engelle
        if action == 'append' and 'id' in df.columns:
            df = df.drop(columns=['id'])
            
        df.to_sql(table_name, c, if_exists=action, index=False)

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
