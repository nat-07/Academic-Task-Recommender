from psycopg2 import pool
import os
from dotenv import load_dotenv
load_dotenv()
connection_pool = pool.SimpleConnectionPool(
    1, 10,
    dsn=os.getenv("DATABASE_URL"),
    sslmode="require"
)

def get_db_connection():
    return connection_pool.getconn()

def release_db_connection(conn):
    connection_pool.putconn(conn)