import sqlite3
from database import get_connection

def search(query):
    """
    Search functionality (Relevancy Heuristic: Title contains > Content contains)
    Reads safely from SQLite using WAL mode, ensuring no DB lock errors
    while the Crawler engine is concurrently inserting data.
    """
    conn = get_connection()
    c = conn.cursor()
    
    # Kullanıcı sorgusunu kelimelere böler
    words = query.lower().split()
    if not words:
        conn.close()
        return []
        
    # Herhangi bir kelimenin eşleştiği dokümanları SQL ile hızlıca filtrele.
    conditions = []
    params = []
    for word in words:
        conditions.append("(title LIKE ? OR content LIKE ?)")
        params.extend([f'%{word}%', f'%{word}%'])
        
    sql = "SELECT url, origin, depth, title, content FROM pages WHERE " + " OR ".join(conditions)
    
    try:
        c.execute(sql, params)
        candidates = c.fetchall()
    except sqlite3.OperationalError as e:
        print(f"Search Engine Error: {e}")
        conn.close()
        return []
        
    results = []
    
    # Relevancy algoritmasını Python memory'sinde uygulayarak sonuçları sırala
    for url, origin, depth, title, content in candidates:
        if title is None: title = ""
        if content is None: content = ""
        
        t_low = title.lower()
        c_low = content.lower()
        
        score = 0
        for word in words:
            # Relevancy Heuristic: Title (Başlık) içerisindeki geçişlere yüksek puan (x10) 
            # Content (İçerik) içerisindeki geçişlere normal puan (x1) verilir.
            title_matches = t_low.count(word)
            content_matches = c_low.count(word)
            
            score += (title_matches * 10) + (content_matches * 1)
            
        if score > 0:
            # Depth Penalty: Kök URL'e daha yakın olan (düşük depth) sayfalar daha kıymetli sayılır.
            # Toplam raw skoru, (depth + 1) değerine bölerek derinlerdeki sayfaların puanını kırıyoruz.
            final_score = score / (depth + 1)
            
            results.append({
                "score": final_score,
                "url": url,
                "origin": origin,
                "depth": depth
            })
            
    conn.close()
    
    # Skorlara göre en yüksekten en düşüğe doğru sırala
    results.sort(key=lambda x: x["score"], reverse=True)
    
    # İstenilen liste formatında (Relevant_URL, Origin_URL, Depth, Score) verileri dön
    return [(item["url"], item["origin"], item["depth"], item["score"]) for item in results]
