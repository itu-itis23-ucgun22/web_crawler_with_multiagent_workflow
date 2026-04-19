# Native Python Web Crawler & Search Engine 🕷️

## Github Account
https://github.com/itu-itis23-ucgun22/web_crawler_with_multiagent_workflow

## Overview
This project is a high-performance, single-node web crawler and real-time search engine built *entirely* with native Python libraries. No external dependencies (like Scrapy, BeautifulSoup, Pandas, or SQLAlchemy) are used. 

The system features concurrent crawling, real-time live indexing, an interactive CLI search engine, and a live web UI dashboard running cohesively.

## Quick Start
1. Ensure you have Python 3.8+ installed on your machine.
2. Clone this repository directly.
3. Run the main orchestration file:
```bash
python3 main.py
```
4. **Live Dashboard:** Open `http://localhost:8080` in your web browser to monitor spider threads and queue depths in real-time.
5. **Interactive Search:** Use the CLI loop presented in your terminal to search indexed documents while crawling operates in the background. Type `exit` to trigger a graceful shutdown sequence.

## Architectural Decisions
To guarantee thread-safety, bypass database locking, and prevent memory/OOM crashes without relying on third-party modules, several strict architectural decisions were enforced during the design phase:

*   **Single DB Writer & WAL Mode:** To prevent constant `sqlite3.OperationalError: database is locked` exceptions caused by multiple worker threads writing simultaneously, spiders never write directly to the DB. They push data to a `db_write_queue`. A dedicated single `DBWriter` thread processes this queue using batched `executemany` inserts. SQLite is explicitly configured with `PRAGMA journal_mode=WAL;` to allow the Search Engine and Dashboard modules to perform concurrent reads seamlessly while the writer is active.
*   **Backpressure & Bounded Queues:** To prevent Out-Of-Memory crashes, both `url_queue` and `db_write_queue` have strict `maxsize` limits. When the queues reach bottleneck thresholds, worker threads dynamically block using a `timeout` parameter, actively throttling themselves. This provides a natural, zero-dependency backpressure mechanism.
*   **Deduplication via SQLite Engine:** Tracking millions of URLs in RAM risks severe memory leaks. Instead of an in-memory Hash Set or Bloom Filter, deduplication is offloaded to the database engine via a `UNIQUE(url)` secondary constraint on the `pages` table combined with `INSERT OR IGNORE` batch statements.
*   **Graceful Shutdown:** The ecosystem actively listens for `SIGINT` (Ctrl+C). A global `threading.Event()` safely intercepts the termination, coordinating thread halts, flushing the remaining pipeline items inside memory queues strictly to disk, and cleanly unbinding the HTTP socket.

## The Multi-Agent Workflow
This codebase was designed cooperatively via an AI "Human-in-the-loop" process involving distinct AI personas guided by a human Project Architect:
*   **@SystemArchitect:** Designed the queue boundaries, DB Writer separation, and overall `main.py` orchestration logic.
*   **@Challenger (Red Team):** Ruthlessly analyzed early proposals for deadlock vulnerabilities, memory leaks, and thread starvation exceptions, forcing the "timeout" implementations on queues.
*   **@SearchSpecialist & @CrawlerSpecialist:** Developed the Python native heuristic search and built the native `html.parser` logic that safely normalizes URLs.
*   **@UISpecialist:** Built the non-blocking `http.server` dashboard that utilizes modern JavaScript asynchronous fetches to bypass screen flashes without using external web frameworks.
