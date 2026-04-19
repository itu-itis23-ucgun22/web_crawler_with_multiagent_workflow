# Multi-Agent Workflow & Architectural Decisions Retrospective 🤖

## 1. Management Philosophy and Team Structure
I led this project with the strict overarching goals of building a high-performance Web Crawler and Search Engine utilizing purely native Python libraries. To maintain the intricate architectural boundaries (RAM safety, Lock-free database, asynchronous throughput), I executed the process designing a **"Human-in-the-Loop" Multi-Agent** team.

In this setup, I acted as the **Node Controller (Lead Project Manager & Architect)**. The AI agents positioned beneath me served as my technical engineering staff—debating my rules, offering specialized solutions, and implementing the rigorous constraints I set.

## 2. My Team (Agent Personas)

*   **👷‍♂️ @SystemArchitect (Lead Systems Engineer):** Drafted the core asynchronous multi-threading blueprints. Conceived the SQLite WAL mode integration and the Queue backpressure pools specifically adapted to my demands.
*   **🦹‍♂️ @Challenger (Red Team QA / Critic):** Tasked with continuously poking holes in the System Architect's proposals, specifically analyzing for Deadlock risks, Race Conditions, and severe Memory Leaks.
*   **🕸️ @CrawlerSpecialist (Network & Data Engineer):** Tasked with operating strictly under my "No External Libraries" rule to write a secure, custom HTML Parser (extending `html.parser`) that ignores `<style>` bloat and normalizes absolute URLs.
*   **🔎 @SearchSpecialist (Algorithms Expert):** Designed the live relevance scoring logic (prioritizing Titles over Content frequency) ensuring immediate fetch speeds over the populated database.
*   **🎨 @UISpecialist (Frontend Developer):** The engineer I ordered to pull the system out of the CLI. Built the robust asynchronous HTML Dashboard relying solely on the native `http.server`.

---

## 3. Critical Architectural Decisions 

Throughout the project lifecycle, I guided my team through severe technical bottlenecks by imposing the following rules:

### Decision 1: OOM Prevention & Deduplication
*   **The Issue:** Millions of URLs needed to be deduplicated to avoid re-crawling the exact same site (a massive Visited list).
*   **Internal Debate:** @SystemArchitect originally proposed storing this massive list as a Python `set()` in RAM. However, @Challenger argued this would inevitably trigger an Out-Of-Memory (OOM) crash given our hardware limits.
*   **My Ruling:** I refused to risk RAM bloat. I decided to **trade minor network bandwidth for strict 100% RAM safety**. I forced the entire deduplication workload onto SQLite via a `UNIQUE` index constraint passing `INSERT OR IGNORE`. This dropped Python memory consumption to near zero.

### Decision 2: Bypassing "Database is Locked" Errors (Single DB Writer)
*   **The Issue:** When 16 concurrent Spiders attempted to log their crawled pages simultaneously, SQLite violently crashed with locking errors.
*   **My Ruling:** I strictly FORBADE crawler threads from directly accessing the database. Instead, I introduced a "Single DB Writer Proxy" pattern. All Spiders now dump their scraped data into a shared memory pool (`db_write_queue`), while one dedicated DB Writer thread collects them in batches of 50 and executes `executemany` flush inserts quietly.

### Decision 3: Autonomous Backpressure Braking
*   **The Issue:** Fast Spiders could easily outpace the DB Writer, eventually overflowing the `db_write_queue` and exploding memory variables.
*   **My Ruling:** I implemented a self-regulating Backpressure mechanism. Both queues were initialized with a strict `maxsize`. If the writer falls behind, the pools max out, and the Spider threads are forced into a temporary "Timeout" block—giving the writer vital breathing room automatically.

### Decision 4: Relevancy Scoring Heuristics
*   **The Issue:** Standard SQL `LIKE` queries returned scattered, unranked results, and we were banned from utilizing Elasticsearch.
*   **My Ruling:** I ordered @SearchSpecialist to implement an in-memory scoring engine post-fetch with three distinct metrics:
    1. Direct hits on the Page `<title>` **(x10 Points)**
    2. Exact recurrence inside the `<content>` body **(x1 Point per hit)**
    3. Depth Penalty: The total score is then divided by **(Depth + 1)**, artificially boosting source domain authorities over deeply buried secondary links.

---

## 4. Conclusion & Retrospective

In this Multi-Agent Workflow, utilizing a pure native Python environment yielded fantastic results. Because of the strict constraints I drafted (Single Node, Native Libs Only), my @Challenger agent's apocalyptic scenarios forced us to build an extraordinarily resilient architecture (`WAL Mode`, `Single Writer Proxy`, `OOM Constraints`). Ultimately, my simulated AI project team successfully delivered an industry-grade, highly-optimized Search Engine and continuous Web Crawler.