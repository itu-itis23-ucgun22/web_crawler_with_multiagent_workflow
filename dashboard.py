import http.server
import socketserver
import threading
import json
import urllib.parse
from database import get_connection
from search import search

class DashboardRequestHandler(http.server.BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        # Arka plan UI isteklerinin Terminali kirletmemesini sağlıyoruz.
        pass
        
    def do_GET(self):
        url_queue = getattr(self.server, 'url_queue', None)
        db_write_queue = getattr(self.server, 'db_write_queue', None)
        stop_event = getattr(self.server, 'stop_event', None)
        
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query_params = urllib.parse.parse_qs(parsed_path.query)

        # 1. METRİKLER VE SON İNDEKSLENENLER API'Sİ
        if path == '/api/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            conn = get_connection()
            c = conn.cursor()
            
            total_indexed = 0
            recent_urls = []
            try:
                c.execute("SELECT COUNT(*) FROM pages")
                total_indexed = c.fetchone()[0]
                
                # En son eklenen 10 site çekilir
                c.execute("SELECT url FROM pages ORDER BY ROWID DESC LIMIT 10")
                recent_urls = [row[0] for row in c.fetchall()]
            except Exception:
                pass
            finally:
                conn.close()
            
            q_depth = url_queue.qsize() if url_queue else 0
            db_depth = db_write_queue.qsize() if db_write_queue else 0
            
            status = "🟢 Active (Crawling)"
            if stop_event and stop_event.is_set():
                status = "🛑 Shutting Down..."
            elif q_depth == 0 and db_depth == 0:
                status = "🟡 Idle (Waiting for Seed URL)"
            elif url_queue and q_depth >= (url_queue.maxsize * 0.9):
                status = "🔴 Throttled (Backpressure Active)"
            
            metrics = {
                "indexed": total_indexed,
                "queue_depth": q_depth,
                "status": status,
                "recent_urls": recent_urls
            }
            self.wfile.write(json.dumps(metrics).encode('utf-8'))
            return

        # 2. ARAMA MOTORU API'Sİ (search.py modülünü kullanır)
        elif path == '/api/search':
            q = query_params.get('q', [''])[0]
            if not q:
                results = []
            else:
                results = search(q) # Formats: [(url, origin, depth), ...]
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # JSON formatına uygun sözlük (dictionary) listesine çeviriyoruz
            out = [{"url": r[0], "origin": r[1], "depth": r[2], "score": r[3]} for r in results]
            self.wfile.write(json.dumps(out).encode('utf-8'))
            return
            
        # 3. İNDEKSLEME BAŞLATICI API'Sİ (url_queue'a yeni seed ekler)
        elif path == '/api/start':
            origin = query_params.get('origin', [''])[0]
            depth_str = query_params.get('depth', ['1'])[0]
            try:
                depth = int(depth_str)
            except ValueError:
                depth = 1
                
            if origin and url_queue:
                url_queue.put((origin, origin, 0)) # Yeni tohum atılır
                
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            return

        # 4. ANA UI HTML ARAYÜZÜ (Front-End)
        elif path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Web Crawler OS Dashboard</title>
                <style>
                    body { font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
                    h1, h2, h3 { color: #38bdf8; }
                    .container { display: flex; flex-direction: column; gap: 20px; max-width: 1200px; margin: auto; }
                    .row { display: flex; gap: 20px; flex-wrap: wrap; }
                    .panel { background: #1e293b; padding: 20px; border-radius: 8px; border: 1px solid #334155; flex: 1; min-width: 300px; }
                    .metric { font-size: 32px; font-weight: bold; margin-bottom: 5px; }
                    .metric-title { color: #94a3b8; font-size: 0.9em; text-transform: uppercase; }
                    input[type="text"], input[type="number"] { padding: 10px; border-radius: 4px; border: 1px solid #475569; background: #0f172a; color: #fff; width: calc(100% - 24px); margin-bottom: 10px; font-size: 16px;}
                    button { padding: 10px 20px; background: #0ea5e9; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 16px; margin-top:5px; }
                    button:hover { background: #0284c7; }
                    ul { list-style: none; padding: 0; margin: 0; max-height: 350px; overflow-y: auto; }
                    li { padding: 8px; border-bottom: 1px solid #334155; word-wrap: break-word; font-size: 0.9em;}
                    li:last-child { border-bottom: none; }
                    .search-result { background: #0f172a; padding: 10px; border-radius: 4px; margin-bottom: 10px; border-left: 3px solid #0ea5e9; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🕸️ Crawler Engine Control Panel</h1>
                    
                    <div class="row">
                        <div class="panel" style="flex: 2;">
                            <h2 style="margin-top:0;">Initiate Crawl / Indexer</h2>
                            <p style="color:#94a3b8; font-size: 0.9em; margin-top: -10px;">Enjekte edeceğiniz URL'den başlayarak Spider'lar indekslemeye başlar.</p>
                            <input type="text" id="seed_url" placeholder="Origin URL (e.g. https://python.org)">
                            <div style="display:flex; gap:10px;">
                                <div style="flex:1;">
                                    <label style="color:#94a3b8; font-size:0.8em;">Max Depth (K)</label>
                                    <input type="number" id="seed_depth" value="2" min="1" max="5" style="width:100%;">
                                </div>
                            </div>
                            <button onclick="startIndex()">Deploy Spiders 🚀</button>
                        </div>
                        
                        <div class="panel">
                            <h2 style="margin-top:0;">System Metrics</h2>
                            <div class="metric-title">System Status</div>
                            <div class="metric" id="status" style="font-size: 20px; color:#10b981;">...</div>
                            <br>
                            <div class="row">
                                <div>
                                    <div class="metric-title">Total Indexed DB</div>
                                    <div class="metric" id="indexed">0</div>
                                </div>
                                <div>
                                    <div class="metric-title">Queue Depth (Load)</div>
                                    <div class="metric" id="q_depth">0</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="panel" style="flex:2;">
                            <h2 style="margin-top:0;">Live Search Engine</h2>
                            <p style="color:#94a3b8; font-size: 0.9em; margin-top: -10px;">Sistem indeksleme yaparken aynı anda arama yapar (WAL Mode sayesinde).</p>
                            <div style="display:flex; gap:10px;">
                                <input type="text" id="search_query" placeholder="Type keyword to search in DB..." style="margin-bottom:0;" onkeypress="if(event.key==='Enter') doSearch()">
                                <button onclick="doSearch()" style="margin-top:0;">Search</button>
                            </div>
                            <div id="search_results" style="margin-top: 15px; max-height: 400px; overflow-y: auto;">
                                <!-- Results appear here -->
                                <i style="color:#64748b;">Search results will appear here...</i>
                            </div>
                        </div>
                        
                        <div class="panel">
                            <h2 style="margin-top:0;">Recently Crawled URLs</h2>
                            <ul id="recent_list">
                                <!-- Recent URLs appear here -->
                            </ul>
                        </div>
                    </div>
                </div>
                
                <script>
                    function fetchMetrics() {
                        fetch('/api/metrics')
                            .then(r => r.json())
                            .then(d => {
                                document.getElementById('indexed').innerText = d.indexed;
                                document.getElementById('q_depth').innerText = d.queue_depth;
                                
                                let statEl = document.getElementById('status');
                                statEl.innerText = d.status;
                                if(d.status.includes('Active')) statEl.style.color = '#10b981';
                                else if(d.status.includes('Idle')) statEl.style.color = '#eab308';
                                else statEl.style.color = '#ef4444';
                                
                                let listHtml = '';
                                d.recent_urls.forEach(url => {
                                    listHtml += `<li><a href="${url}" target="_blank" style="color:#38bdf8; text-decoration:none;">${url}</a></li>`;
                                });
                                if (listHtml === '') listHtml = '<li style="color:#64748b;">No URLs indexed yet.</li>';
                                document.getElementById('recent_list').innerHTML = listHtml;
                            })
                            .catch(e => console.error(e));
                    }
                    
                    function doSearch() {
                        let query = document.getElementById('search_query').value;
                        if (!query) return;
                        
                        document.getElementById('search_results').innerHTML = '<i style="color:#64748b;">Searching Engine...</i>';
                        
                        fetch('/api/search?q=' + encodeURIComponent(query))
                            .then(r => r.json())
                            .then(data => {
                                if (data.length === 0) {
                                    document.getElementById('search_results').innerHTML = '<i style="color:#ef4444;">No highly relevant matches found.</i>';
                                    return;
                                }
                                let html = '';
                                data.forEach((item, index) => {
                                    let scoreFixed = Number(item.score).toFixed(2);
                                    html += `<div class="search-result">
                                        <div style="color:#0ea5e9; font-weight:bold; margin-bottom:4px;">${index+1}. <a href="${item.url}" target="_blank" style="color:#0ea5e9;">${item.url}</a> <span style="background:#0ea5e9; color:#fff; font-size:12px; padding:2px 6px; border-radius:10px; margin-left:10px;">Score: ${scoreFixed}</span></div>
                                        <div style="font-size: 0.85em; color:#94a3b8;"><b>Origin:</b> ${item.origin} &nbsp; | &nbsp; <b>Depth:</b> ${item.depth}</div>
                                    </div>`;
                                });
                                document.getElementById('search_results').innerHTML = html;
                            });
                    }
                    
                    function startIndex() {
                        let origin = document.getElementById('seed_url').value.trim();
                        let depth = document.getElementById('seed_depth').value;
                        if (!origin) {
                            alert("Please enter an Origin URL to start crawling.");
                            return;
                        }
                        // Eğer kullanıcı https:// yazmayı unuttuysa otomatik ekle:
                        if (!origin.startsWith("http://") && !origin.startsWith("https://")) {
                            origin = "http://" + origin;
                            document.getElementById('seed_url').value = origin;
                        }
                        
                        fetch(`/api/start?origin=${encodeURIComponent(origin)}&depth=${encodeURIComponent(depth)}`)
                            .then(r => r.json())
                            .then(d => {
                                alert("🕷️ Spiders deployed to: " + origin);
                                document.getElementById('seed_url').value = ''; // clear input
                            });
                    }
                    
                    fetchMetrics();
                    setInterval(fetchMetrics, 2000); // 2 saniyede bir paneli güceller
                </script>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_error(404)

class DashboardServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True

def start_dashboard(url_queue, db_write_queue, stop_event, port=8000):
    server = DashboardServer(("0.0.0.0", port), DashboardRequestHandler)
    server.url_queue = url_queue
    server.db_write_queue = db_write_queue
    server.stop_event = stop_event
    
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    return server
