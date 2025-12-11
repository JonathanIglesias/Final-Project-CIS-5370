import os, psycopg2, psycopg2.extras
from contextlib import contextmanager

@contextmanager
def get_conn():
    conn = psycopg2.connect(dbname="Project",
            user="postgres",
            password="", #The password was removed for security reasons.
            host="localhost",
            port="5432"
            )
    try:
        yield conn
    finally:
        conn.close()

def upsert_article(rec):
    sql = """
    INSERT INTO articles (url, source, title, http_status, fetched_at, text, raw_html)
    VALUES (%(url)s, %(source)s, %(title)s, %(http_status)s, %(fetched_at)s, %(text)s, %(raw_html)s)
    ON CONFLICT (url) DO UPDATE
      SET title = EXCLUDED.title,
          http_status = EXCLUDED.http_status,
          fetched_at = EXCLUDED.fetched_at
    RETURNING url;
    """
    with get_conn() as conn:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, rec)
                return cur.fetchone()[0]
