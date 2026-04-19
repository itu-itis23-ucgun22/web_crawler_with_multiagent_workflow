import urllib.request
import urllib.parse
from html.parser import HTMLParser
import threading
import queue
import time
from database import init_db, db_writer, get_connection, is_url_indexed

class CrawlerHTMLParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.links = []
        self.text_content = []
        self.in_ignored_tag = False
        self.title = ""
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        # Yalnızca <style> etiketleri filtrelenecek, <script> içerikleri genel gövdeye alınacak
        if tag == 'style':
            self.in_ignored_tag = True
        elif tag == 'title':
            self.in_title = True
        elif tag == 'a':
            for attr, value in attrs:
                if attr == 'href':
                    # Kural #4: Mutlak URL (absolute URL) çevirimi ve Fragment (#) temizliği
                    full_url = urllib.parse.urljoin(self.base_url, value)
                    full_url = urllib.parse.urlsplit(full_url)._replace(fragment="").geturl()
                    
                    if full_url.startswith('http'):
                        self.links.append(full_url)

    def handle_endtag(self, tag):
        if tag == 'style':
            self.in_ignored_tag = False
        elif tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        data = data.strip()
        if not data:
            return
        
        if self.in_title:
            self.title += data + " "
        elif not self.in_ignored_tag:
            self.text_content.append(data)
    
    def get_content(self):
        return " ".join(self.text_content)
    
    def get_title(self):
        return self.title.strip()


def spider_worker(url_queue, db_write_queue, stop_event, max_depth):
    # Kural #2: Worker'lar okuma yapmak için dahi thread-safe local DB connection alırlar.
    local_db_conn = get_connection()
    
    while not stop_event.is_set():
        try:
            # Kural #3: Timeout ile deadlock önlemi.
            current_url, origin, depth = url_queue.get(timeout=2.0)
        except queue.Empty:
            continue
            
        try:
            if depth > max_depth:
                continue
                
            # Kural #1: RAM şişirmemek için deduplication işlemini DB'den hızlı bir okuma sorusu ile yönet.
            # Eşzamanlılıkta (race-condition) minik sızıntılar olsa da, DB Writer INSERT OR IGNORE ile yedeğini sıfırlayacaktır.
            if is_url_indexed(local_db_conn, current_url):
                continue
                
            print(f"[{threading.current_thread().name}] Fetching: {current_url} (Depth: {depth})")
            
            req = urllib.request.Request(
                current_url, 
                headers={'User-Agent': 'NativePythonCrawler/1.0'}
            )
            
            try:
                # Kural #3 & Ağ hataları: urllib hanging yapmaması için timeout ZORUNLUDUR.
                with urllib.request.urlopen(req, timeout=5.0) as response:
                    content_type = response.getheader('Content-Type')
                    if content_type and 'text/html' not in content_type:
                        continue
                        
                    html_bytes = response.read()
                    html_str = html_bytes.decode('utf-8', errors='ignore')
            except Exception as e:
                # 404, 500 veya timeout durumlarında graceful pass. DB_queue'ye eklenmez.
                continue

            # Kural #4: Native parser ile ayrıştırma işlemi.
            parser = CrawlerHTMLParser(current_url)
            parser.feed(html_str)
            
            title = parser.get_title()
            content = parser.get_content()
            links = parser.links
            
            # Bulunan orijinal sayfayı Writer kuyruğuna doldur.
            try:
                # Database dolarsa burada thread bloke olur (Backpressure)
                db_write_queue.put((current_url, origin, depth, title, content), timeout=5.0)
            except queue.Full:
                print(f"Warning: db_write_queue FULL! Data dropped: {current_url}")
                continue
                
            # Yeni Linkleri kuyruğa aktar
            if depth < max_depth:
                for link in links:
                    try:
                        url_queue.put((link, origin, depth + 1), timeout=2.0)
                    except queue.Full:
                        # Queue şişerse burası da backpressure limitöre çarpar.
                        pass

        except Exception as e:
            print(f"Unexpected error on {current_url}: {e}")
        finally:
            url_queue.task_done()
            
    local_db_conn.close()

def index(origin, k):
    """
    Spider sistemini başlatan ve koordine eden ana root fonksiyon.
    """
    print(f"Starting crawler on origin='{origin}' with max_depth={k}")
    
    init_db()
    
    # BACKPRESSURE YÖNETİMİ: Queue'lara maxsize katı kuralları konuldu.
    url_queue = queue.Queue(maxsize=10000)
    db_write_queue = queue.Queue(maxsize=1000)
    
    stop_event = threading.Event()
    
    # 1 Adet Dedicated Yazar Thread (Kural #2 Database is Locked önlemi)
    writer_thread = threading.Thread(
        target=db_writer, 
        args=(db_write_queue, stop_event), 
        name="DBWriter_Thread"
    )
    writer_thread.start()
    
    # N Adet Spider Worker Havuzu
    num_workers = 5
    workers = []
    for i in range(num_workers):
        t = threading.Thread(
            target=spider_worker, 
            args=(url_queue, db_write_queue, stop_event, k),
            name=f"Spider-{i+1}"
        )
        t.start()
        workers.append(t)
        
    # İlk tohum atılıyor...
    url_queue.put((origin, origin, 0))
    
    try:
        # Kuyruktaki tüm linkler eriyene yada manuel olarak durulanana kadar bekle
        url_queue.join()
        print("Kuyruk tamamlandı, işçiler kapatılıyor (Graceful Shutdown)...")
    except KeyboardInterrupt:
        print("\nCTRL+C tetiklendi. Güvenli kapatılma dizisi devrede...")
    finally:
        # Kural #3: Sıkışmadan ve zombileşmeyi engellemek için stop event fırlat ve bekle
        stop_event.set()
        
        for w in workers:
            w.join()
            
        writer_thread.join()
        print("Crawler başarıyla sonlandı. DB kilitleri açıldı.")

if __name__ == '__main__':
    # Basit run testi
    index("https://docs.python.org/3/", 1)
