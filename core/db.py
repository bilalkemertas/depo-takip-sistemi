import sqlite3
import pandas as pd
from datetime import datetime
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import time

DB = "depo.db"

def conn():
    # SQLite kilitlenmelerini önlemek için timeout ve WAL modu aktif
    return sqlite3.connect(DB, check_same_thread=False, timeout=30)

# ---------------- INIT ----------------
def init_db():
    with conn() as c:
        # HIZ İÇİN KRİTİK AYAR: WAL Modu
        c.execute("PRAGMA journal_mode=WAL;")
        c.execute("PRAGMA synchronous=NORMAL;")
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

# ---------------- READ ----------------
def read(table):
    try:
        with conn() as c:
            df = pd.read_sql_query(f"SELECT * FROM {table}", c)
            return df
    except:
        return pd.DataFrame()

# ---------------- WRITE ----------------
def write(table, df):
    for attempt in range(3):
        try:
            with conn() as c:
                df.to_sql(table, c, if_exists="replace", index=False)
                return
        except sqlite3.OperationalError:
            if attempt < 2:
                time.sleep(1)
                continue
            else:
                st.error("Veritabanı meşgul, lütfen bekleyin...")
        except Exception as e:
            st.error(f"Yazma Hatası: {e}")
            break

# ---------------- LOG ----------------
def log(user, action, detail):
    with conn() as c:
        cur = c.cursor()
        cur.execute("""
            INSERT INTO audit_log (tarih, user, action, detay)
            VALUES (?, ?, ?, ?)
        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user, action, detail))
        c.commit()

# ---------------- DRIVE EXCEL EŞİTLEME ----------------
def get_drive_conn():
    return st.connection("gsheets", type=GSheetsConnection)

def sync_to_drive():
    # Bu fonksiyon artık sadece ihtiyaç duyulduğunda çağrılacak
    g_conn = get_drive_conn()
    tablolar = {"stok": "Stok", "urun_listesi": "Urun_Listesi", "hareketler": "Hareketler"}
    for sql_table, sheet_name in tablolar.items():
        try:
            df = read(sql_table)
            if not df.empty:
                g_conn.update(worksheet=sheet_name, data=df)
        except:
            pass

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
        except:
            hatali.append(sheet_name)
    return basarili, hatali
