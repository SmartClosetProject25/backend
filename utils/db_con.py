# db_con.py
import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import pooling

load_dotenv()

MYSQL_CFG = {
    "user": os.getenv("DB_USER", ""),
    "password": os.getenv("DB_PASSWORD", ""),
    "host": os.getenv("DB_HOST", ""),
    "database": os.getenv("DB_NAME", "")
}

_pool = pooling.MySQLConnectionPool(
    pool_name="smart_closet_pool",
    pool_size=8,
    **MYSQL_CFG
)
def get_db_connection():
    """Get a connection from the MySQL connection pool."""
    return _pool.get_connection()

# DB接続
def db_query_one(sql, params=()):
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        row = cur.fetchone()
        cur.close()
        return row
    finally:
        conn.close()


def db_query_all(sql, params=()):
    conn = get_db_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        conn.close()


def db_execute(sql, params=()):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        affected = cur.rowcount
        cur.close()
        return affected
    finally:
        conn.close()