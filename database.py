import sqlite3
import threading
import queue

DB_NAME = 'crawler_db.sqlite'

def get_connection():
    """
    Returns a new, thread-safe SQLite connection configured for WAL mode.
    Every thread should obtain its own connection for concurrent DB access.
    """
    # timeout parametresi, db_writer yazım yaparken kısa süreli kilitlenmelerde beklentiyi ayarlar.
    conn = sqlite3.connect(DB_NAME, timeout=15.0)
    # WAL (Write-Ahead Logging) Modu: Eşzamanlı Okuma/Yazma işlemlerine (Concurrency) izin verir.
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # url sütunu UNIQUE olarak işaretlendi. Deduplication bu kısıtla (constraint) sağlanacak.
    c.execute('''
        CREATE TABLE IF NOT EXISTS pages (
            url TEXT PRIMARY KEY,
            origin TEXT,
            depth INTEGER,
            title TEXT,
            content TEXT
        )
    ''')
    conn.commit()
    conn.close()

def db_writer(write_queue, stop_event):
    """
    Dedicated DB Writer Thread. Worker'lardan gelen verileri batch (grup) halinde alır,
    ve 'executemany' ile veritabanına basar. 
    'INSERT OR IGNORE' kullanarak, UNIQUE(url) kısıtına çarpan tekrar kayıtlarını RAM şişirmeden reddeder.
    """
    conn = get_connection()
    c = conn.cursor()
    
    batch_size = 50
    batch = []
    
    # Stop eventi gelene ya da kuyruk tamamen boşalana kadar çalış.
    while not stop_event.is_set() or not write_queue.empty():
        try:
            # Graceful shutdown yapabilmek için timeout ile bekliyoruz (Deadlock Önlemi #3)
            item = write_queue.get(timeout=1.0)
            batch.append(item)
            
            # Batch limiti dolarsa diske yaz
            if len(batch) >= batch_size:
                c.executemany('''
                    INSERT OR IGNORE INTO pages (url, origin, depth, title, content)
                    VALUES (?, ?, ?, ?, ?)
                ''', batch)
                conn.commit()
                batch.clear()
                
            write_queue.task_done()
        except queue.Empty:
            # Queue boş kaldıysa ve kuyrukta yarım kalan batch varsa diske işle (flush)
            if batch:
                c.executemany('''
                    INSERT OR IGNORE INTO pages (url, origin, depth, title, content)
                    VALUES (?, ?, ?, ?, ?)
                ''', batch)
                conn.commit()
                batch.clear()

    # Thread kapanmadan önce elde kalan son verileri de DB'ye yazar (Final Flush).
    if batch:
        c.executemany('''
            INSERT OR IGNORE INTO pages (url, origin, depth, title, content)
            VALUES (?, ?, ?, ?, ?)
        ''', batch)
        conn.commit()
    
    conn.close()

def is_url_indexed(conn, url):
    """
    Worker'ların ağ iletişimine geçmeden önce hızlıca URL dedup kontrolü yapmasını sağlar.
    DB Writer 'INSERT OR IGNORE' yapsa da, henüz çekilmemiş bir linki boş yere indirmemek için kullanılır.
    Race condition olsa dahi SQLite yazma fâzında tekrarı ezer.
    """
    c = conn.cursor()
    c.execute("SELECT 1 FROM pages WHERE url = ?", (url,))
    return c.fetchone() is not None
