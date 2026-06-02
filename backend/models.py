import os
import psycopg2
from psycopg2 import pool

# Database configuration - local PostgreSQL
_DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB", "documents_db"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("POSTGRES_PASSWORD", "1234"),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
}

# Initialize a connection pool (thread-safe)
_connection_pool = pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    **_DB_CONFIG
)

def get_conn():
    """Acquire a connection from the pool. Caller should close it when done."""
    return _connection_pool.getconn()

def release_conn(conn):
    """Return a connection to the pool."""
    _connection_pool.putconn(conn)

def create_tables():
    """Create required tables if they do not exist."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    employee_code VARCHAR(20) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    name VARCHAR(100),
                    email VARCHAR(100),
                    role VARCHAR(20) DEFAULT 'user',
                    accessed_menus VARCHAR(255) DEFAULT 'fin-report,documat',
                    is_initial_password BOOLEAN DEFAULT TRUE,
                    security_question VARCHAR(255),
                    security_answer VARCHAR(255)
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS company_addresses (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    pan_number VARCHAR(10),
                    address TEXT
                );
            """)
            conn.commit()
    finally:
        release_conn(conn)

# Export symbols for import elsewhere
__all__ = ["get_conn", "release_conn", "create_tables"]
