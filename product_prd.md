# Product Requirements Document (PRD)
## Project: Real-time Web Crawler & Search Engine (Single Node)

### 1. Project Overview
Build a functional web crawler and real-time search engine from scratch. The system must support concurrent indexing and searching, managed via strict thread-safe data structures. Development will be steered using a Multi-Agent AI workflow with human-in-the-loop verification.

### 2. Core Constraints
* **Native Focus:** Strict adherence to language-native functionality. External high-level libraries (e.g., Scrapy, BeautifulSoup, Requests, Flask) are strictly prohibited. Use native libraries like `urllib`, `html.parser`, `sqlite3`, `threading`, and `queue`.
* **Environment:** Designed for a single-machine execution (localhost), but architecture must demonstrate scalability principles.

### 3. Technical Requirements

#### 3.1. Indexer (`index(origin, k)`)
* **Recursive Crawling:** Initiate from an `origin` URL up to a maximum depth `k`.
* **Uniqueness:** Implement a robust "Visited" set (in-memory or DB-backed) to ensure no page is crawled twice.
* **Back Pressure:** The system must proactively manage its own load. Implement bounded queues (`queue.Queue(maxsize=X)`) and rate limiting to prevent out-of-memory (OOM) crashes.
* **Resumability (Bonus):** Ability to resume crawling after an interruption without starting from scratch.

#### 3.2. Searcher (`search(query)`)
* **Query Engine:** Accept a string and return a list of triples: `(relevant_url, origin_url, depth)`.
* **Live Indexing:** Search must be fully operational and thread-safe while the indexer is actively writing to the database.
* **Concurrency:** Utilize thread-safe data structures (Mutexes, Locks, standard thread-safe Queues) to prevent data corruption during simultaneous read/write operations. SQLite should be configured for concurrent access (e.g., WAL mode).
* **Relevancy Heuristic:** Implement a simple scoring system (e.g., Title matching gets higher weight + keyword frequency in content).

#### 3.3. System Visibility & UI
* Provide a simple CLI or Web Dashboard (using native `http.server` or terminal output).
* **Real-time Metrics:**
  - Current Indexing Progress (URLs processed vs. queued).
  - Current Queue Depth.
  - Back-pressure/Throttling status (Idle, Active, Throttled).