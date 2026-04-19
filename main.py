import threading
import queue
import time
import sys

from database import init_db, db_writer
from crawler import spider_worker
from dashboard import start_dashboard
from search import search

def main():
    print("="*60)
    print("🕷️  Native Python Web Crawler & Search Engine Initialization")
    print("="*60)
    
    init_db()

    # Core Queues Setup
    url_queue = queue.Queue(maxsize=5000)
    db_write_queue = queue.Queue(maxsize=1000)
    stop_event = threading.Event()

    # 1. Start DB Writer Thread
    # - DB'ye yazma işini sadece bir Thead üstlenerek "database is locked" durumunu önlüyor.
    writer_thread = threading.Thread(
        target=db_writer, 
        args=(db_write_queue, stop_event), 
        name="DBWriter_Thread"
    )
    writer_thread.start()

    # 2. Start Dashboard UI Server
    # - Arka planda çalışıp durumu izleyen HTTP Server
    ui_server = start_dashboard(url_queue, db_write_queue, stop_event, port=8000)
    print("📟 Dashboard launched. Open HTTP Server at -> http://localhost:8000")

    # 3. Start Spider Workers
    origin_url = "https://docs.python.org/3/"
    max_depth = 2
    num_workers = 16
    workers = []
    
    for i in range(num_workers):
        t = threading.Thread(
            target=spider_worker, 
            args=(url_queue, db_write_queue, stop_event, max_depth),
            name=f"Spider-{i+1}",
            daemon=True
        )
        t.start()
        workers.append(t)

    # 4. Wait for Seed URLs via Dashboard UI
    # - UI dashboard (http://localhost:8000) üzerinden "Initiate Crawl" yapılana kadar Spiderlar bekler.
    print(f"🚀 Spiders deployed and waiting for commands! (0 active tasks)")

    time.sleep(1) # Visual output padding
    print("\n" + "*"*60)
    print("🔍 LIVE SEARCH ENGINE COMMAND LINE ACTIVE")
    print("   Tip: Type a keyword and press ENTER to search crawler DB live.")
    print("   Tip: Type 'exit' to gracefully terminate the ecosystem.")
    print("*"*60 + "\n")

    # 5. UI Repl loop (Main Thread)
    try:
        while True:
            try:
                cmd = input("Search> ").strip()
            except EOFError:
                break
                
            if not cmd: continue
            if cmd.lower() in ('exit', 'quit'):
                break
                
            start_t = time.time()
            results = search(cmd) # DB'den Arama algoritmasını çağırıyoruz. WAL devrede!
            duration = time.time() - start_t
            
            if not results:
                print("  ❌ No relevant URLs found.")
            else:
                print(f"  ✅ Found {len(results)} exact/partial matches in {duration:.3f}s. Top hits:")
                for i, (rel_url, orig_url, depth, score) in enumerate(results[:5]): # En iyi 5 sonucu bas.
                    print(f"    {i+1}. {rel_url} (Score: {score:.2f} | Depth: {depth})")
            print()
            
    except KeyboardInterrupt:
        print("\nCTRL+C captured. Interpolating System...")
        
    finally:
        print("\n🛑 Initiating Graceful Shutdown Protocol...")
        stop_event.set() # Bu sinyalle Spider ve DB Writer beklemeyi keser
        ui_server.shutdown() # UI Server'i porttan serbest bırak
        
        print("💾 Flushing remaining queue items into persistent storage... Please wait.")
        writer_thread.join(timeout=4.0) 
        
        print("👋 Node closed gracefully. Thank you.")
        sys.exit(0)

if __name__ == '__main__':
    main()
