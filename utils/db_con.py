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
