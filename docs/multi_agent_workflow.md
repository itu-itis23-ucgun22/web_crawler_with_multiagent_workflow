# Multi-Agent Workflow & Architectural Decisions Retrospective 🤖

## 1. Yönetim Felsefesi ve Takım Yapısı
Bu projeyi, tamamen yerleşik (native) Python kütüphaneleri kullanarak yüksek performanslı bir Web Crawler ve Arama Motoru inşa etmek gibi kısıtlayıcı hedeflerle yönettim. Sistemin mimari sınırlarını (RAM güvenliği, Lock-free veritabanı, asenkronluk) koruyabilmek adına, süreci bir **"Human-in-the-Loop" (İnsan Kontrolünde)** Multi-Agent ekibi tasarlayarak yürüttüm. 

Bu kurguda ben **Node Controller (Proje Lideri ve Mimar)** olarak kararları veren kişi oldum. Altımdaki AI (Yapay Zeka) ajanları ise uzmanlık alanlarına göre bana öneriler sunan, yazdığım kuralları tartışan teknik ekibim olarak görev aldı.

## 2. Takımım (Agent Personaları)

*   **👷‍♂️ @SystemArchitect (Sistem Mühendisi):** Çekirdek asenkron multi-threading mimarisinin taslaklarını hazırladı. Taleplerim doğrultusunda SQLite WAL modunu ve Queue havuzlarını projelendirdi.
*   **🦹‍♂️ @Challenger (Kritik Analiz / Red Team):** Architect'in bana sunduğu planlardaki güvenlik açıklarını, Memory Leak (Bellek sızıntısı) ve Deadlock (Kilitlenme) risklerini analiz etmekle görevlendirdiğim ajan.
*   **🕸️ @CrawlerSpecialist (Veri & Ağ Uzmanı):** Benim koyduğum katı kurallar çerçevesinde HTML ayrıştırma (Parser) sistemini dış kütüphane olmadan (urllib ve html.parser) yazmakla görevli mühendisim.
*   **🔎 @SearchSpecialist (Algoritma Uzmanı):** Gelen verilerin kullanıcı aramasında saniyeler içinde Skorlanarak (Title ve Depth ağırlıklı) getirilmesi logiğini tasarladı.
*   **🎨 @UISpecialist (Arayüz Geliştirici):** CLI'dan çıkıp sistemi bir HTML Dashboard'a taşımasını emrettiğim, Native `http.server` üzerinden asenkron UI bağlayan uzmanım.

---

## 3. Ekibimle Aldığımız Kritik Mimari Kararlar

Proje boyunca karşılaştığımız büyük teknik darboğazları, ekibimle tartışarak şu kararlarla çözdüm:

### Karar 1: RAM Şişmesini (OOM) Önleme ve Deduplikasyon
*   **Sorun:** Milyonlarca tekil URL'in aynı siteyi tekrar taramaması için (Visited List) hafızada tutulması gerekiyordu.
*   **Ekip İçi Tartışma:** @SystemArchitect bu listeyi Python `set()` olarak RAM'de tutmayı önerdi. Ancak @Challenger bunun donanım limitlerimi zorlayacağını ve Out-Of-Memory (OOM) hatası verdireceğini savundu. 
*   **Aldığım Karar:** Sistemin RAM şişirmesine asla izin veremezdim. Bu yüzden **OOM Riskini göze almaktansa bant genişliğini feda etme** kararı aldım. Deduplikasyon yükünü tamamen RAM'den alıp SQLite'ın `UNIQUE` kısıtına (`INSERT OR IGNORE`) yıktım. Böylece RAM tüketimi neredeyse sıfıra indi.

### Karar 2: "Database is Locked" Hatasını Aşmak (Single DB Writer)
*   **Sorun:** 16 farklı Spider (Örümcek) aynı anda veritabanına kayıt atmaya çalıştığında SQLite'in meşhur kilitlenme problemleri başladı.
*   **Aldığım Karar:** Thread'lerin (Örümceklerin) veritabanına doğrudan yazmasını kesin yolla YASAKLADIM. Bunun yerine "Single DB Writer Proxy" adında tek bir thread oluşturdum. Bütün örümceklerin getirdiği veriler `db_write_queue` havuzuna düşürülüyor; Writer ise bu paketleri 50'şerli gruplar (Batch) halinde `executemany` ile hızlıca diske döküyor. 

### Karar 3: Backpressure (Geri Basınç) Frenlemesi
*   **Sorun:** Spiders'ın DB_Writer'dan daha hızlı veri çekerek kuyruk hafızasını (Queue) patlatma ihtimali vardı.
*   **Aldığım Karar:** Sisteme kendiliğinden çalışan bir Backpressure zorunluluğu getirdim. Hafıza kuyruklarına (Queue) katı `maxsize` değerleri bağlattım ve kuyruk dolarsa Thread'lerin "Timeout" süresince zorunlu beklemeye geçerek yazarın nefes almasını sağlamasını emrettim.

### Karar 4: Arama Motoru Skorer Logiği (Relevancy Heuristic)
*   **Sorun:** Basit bir LIKE araması sonuçların kalitesini çok düşürüyordu. Elasticsearch gibi dış araçlar da yasaktı.
*   **Aldığım Karar:** @SearchSpecialist'e özel bir puanlama kurgusu implement etmesini söyledim:
    1. Aranan kelime sayfa başlığında (Title) geçiyorsa **(x10 Puan)**
    2. Gövdede (Content) geçiyorsa frekansı kadar **(x1 Puan)**
    3. Derinlik Cezası (Depth Penalty): Ana domaine yakınlık değeri; nihai skor **(Depth+1)** değerine bölünerek orijinal kaynaklar öne taşınır.

---

## 4. Sonuç & Retrospektif

Bu Multi-Agent Workflow senaryosunda, saf bir Python kütüphanesi ortamında kurduğumuz bu takım çalışması inanılmaz sonuçlar verdi. Kurduğum katı kısıtlamalar (Single Node, Native Libs) neticesinde, @Challenger ajanımın felaket senaryoları tasarlaması beni en sağlam mimariyi (`WAL Mode`, `Single Writer Proxy`, `OOM Constraints`) ayağa kaldırmaya mecbur bıraktı. Mükemmel optimize edilmiş ve stabil bir Arama Motoru & Tarayıcı (Crawler) ekosistemini projeye teslim etmiş olduk.