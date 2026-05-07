import sqlite3
import pandas as pd
from datetime import datetime
import streamlit as st
from streamlit_gsheets import GSheetsConnection

DB = "depo.db"

def conn():
    return sqlite3.connect(DB, check_same_thread=False)

# ---------------- INIT ----------------
def init_db():
    c = conn()
    cur = c.cursor()

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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS urun_listesi (
        kod TEXT PRIMARY KEY,
        isim TEXT,
        birim TEXT,
        adres TEXT
    )
    """)

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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS blokeli_stok (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kod TEXT,
        adres TEXT,
        miktar REAL,
        sebep TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sayim_snapshot (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        oturum TEXT,
        kod TEXT,
        adres TEXT,
        miktar REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tarih TEXT,
        user TEXT,
        action TEXT,
        detay TEXT
    )
    """)

    c.commit()
    c.close()

# ---------------- READ ----------------
def read(table):
    c = conn()
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table}", c)
    except:
        df = pd.DataFrame()
    c.close()
    return df

# ---------------- WRITE (TABLO ÇAKIŞMASINI ÇÖZEN KISIM) ----------------
def write(table, df):
    c = conn()
    try:
        # Tablo varsa içini tamamen sil ve yeni veriyi yaz (Eski kilitleri aşar)
        df.to_sql(table, c, if_exists="replace", index=False)
    except Exception as e:
        # Eğer hala hata verirse tabloyu zorla düşür ve baştan yarat
        cur = c.cursor()
        cur.execute(f"DROP TABLE IF EXISTS {table}")
        df.to_sql(table, c, if_exists="replace", index=False)
    finally:
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
    tablolar = {"stok": "Stok", "urun_listesi": "Urun_Listesi", "hareketler": "Hareketler"}
    for sql_table, sheet_name in tablolar.items():
        try:
            df = read(sql_table)
            if not df.empty:
                g_conn.update(worksheet=sheet_name, data=df)
        except: pass

def sync_from_drive():
    g_conn = get_drive_conn()
    tablolar = {
        "Stok": "stok", "Urun_Listesi": "urun_listesi", "Hareketler": "hareketler",
        "Blokeli_Stok": "blokeli_stok", "Sayim_Snapshot": "sayim_snapshot", "Audit_Log": "audit_log"
    }
    basarili, hatali = [], []
    for sheet_name, sql_table in tablolar.items():
        try:
            df = g_conn.read(worksheet=sheet_name, ttl=0)
            if isinstance(df, pd.DataFrame) and not df.empty:
                df.columns = [str(c).strip().lower() for c in df.columns]
                write(sql_table, df)
                basarili.append(sheet_name)
        except Exception as e:
            hatali.append(f"{sheet_name}")
    return basarili, hatali
