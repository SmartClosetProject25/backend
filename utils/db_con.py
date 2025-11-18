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


def init_db():
    """存在しないテーブルのみ作成（IF NOT EXISTS）。本番は SKIP_INIT_DB=1 でスキップ可。"""
    ddl = [
        """
        CREATE TABLE IF NOT EXISTS users (
          user_id    INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
          email      VARCHAR(255) NOT NULL UNIQUE,
          password   VARCHAR(255) NOT NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          is_deleted TINYINT(1) NOT NULL DEFAULT 0
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
        """,
        """
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
          token_id    INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
          user_id     INT NOT NULL,
          token       VARCHAR(255) NOT NULL UNIQUE,
          expires_at DATETIME NOT NULL,
          used        TINYINT(1) NOT NULL DEFAULT 0,
          created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          KEY idx_token (token),
          KEY idx_user (user_id),
          CONSTRAINT fk_password_reset_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
        """,
        """
        CREATE TABLE IF NOT EXISTS user_prefs (
          user_id    VARCHAR(64) PRIMARY KEY,
          w_warm     DOUBLE NOT NULL DEFAULT 0,
          w_plain    DOUBLE NOT NULL DEFAULT 0,
          w_formal   DOUBLE NOT NULL DEFAULT 0,
          w_casual   DOUBLE NOT NULL DEFAULT 0,
          updated_at BIGINT NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS closet_items (
          item_id      VARCHAR(64) PRIMARY KEY,
          user_id      VARCHAR(64) NOT NULL,
          category     VARCHAR(16) NOT NULL,  -- top/bottom/outer/shoes
          color_h      INT,
          tone_plain   TINYINT,
          tone_pattern TINYINT,
          formal_score DOUBLE,
          image_uri    TEXT,
          created_at   BIGINT NOT NULL,
          KEY idx_user (user_id),
          KEY idx_user_cat (user_id, category)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS coord_combinations (
          coord_id     VARCHAR(64) PRIMARY KEY,
          user_id      VARCHAR(64) NOT NULL,
          top_id       VARCHAR(64) NOT NULL,
          bottom_id    VARCHAR(64) NOT NULL,
          shoes_id     VARCHAR(64) NULL,
          scene        VARCHAR(32),
          style_label  VARCHAR(64),
          features_json JSON NOT NULL,
          created_at   BIGINT NOT NULL,
          KEY idx_user (user_id),
          KEY idx_user_scene (user_id, scene),
          CONSTRAINT fk_top    FOREIGN KEY (top_id)    REFERENCES closet_items(item_id) ON DELETE CASCADE,
          CONSTRAINT fk_bottom FOREIGN KEY (bottom_id) REFERENCES closet_items(item_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS ab_logs (
          log_id      BIGINT AUTO_INCREMENT PRIMARY KEY,
          user_id     VARCHAR(64) NOT NULL,
          scene       VARCHAR(32),
          temp_c      DOUBLE,
          coord_a     VARCHAR(64) NOT NULL,
          coord_b     VARCHAR(64) NOT NULL,
          chosen      CHAR(1) NOT NULL,
          decision_ms INT,
          created_at  BIGINT NOT NULL,
          KEY idx_user_time (user_id, created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    ]
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        for q in ddl:
            cur.execute(q)
        cur.close()
    finally:
        conn.close()
