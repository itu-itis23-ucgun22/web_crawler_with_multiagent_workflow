# Multi-Agent Workflow Definition & Retrospective 🤖

## 1. Project Objective and Workflow Philosophy
For this project, the goal was to construct a robust, thread-safe Web Crawler and Search Engine using solely native Python libraries. To achieve the rigorous architectural standards required (memory safety, backpressure, lock-free SQLite), we implemented an **AI-Augmented Collaborative Workflow**.

The "Human" (Node Controller) steered the discussion, while multiple distinct AI personas generated solutions, critiqued limitations, and provided comprehensive testing mechanisms. This cooperative AI discourse shaped the entire `crawl -> index -> search` ecosystem before any code was written.

## 2. Agent Personas & Responsibilities

### 👷‍♂️ @SystemArchitect (Lead Engineer)
* **Responsibility:** Designed the core asynchronous multi-threading architecture.
* **Contributions:** Proposed the `WAL mode` configuration for SQLite, established the global `queue.Queue` maxsize limitations to enforce Backpressure, and engineered the "Single DB Writer Thread" proxy pattern to bypass the notorious SQLite database-is-locked limitation.

### 🦹‍♂️ @Challenger (Red Team Critic)
* **Responsibility:** Vulnerability probing and edge-case testing of the Architect's proposals.
* **Contributions:** Pointed out a systemic Deadlock flaw if thread locks were held during queue operations. Warned against the massive out-of-memory overhead of keeping a Python `set()` for visited URLs. Championed the pivot to offloading Deduplication onto SQLite's `UNIQUE` constraint schema using `INSERT OR IGNORE`. Formatted strict adherence to network timeouts within `urllib` to prevent thread starvation globally.

### 🧪 @TestEngineer (Quality Assurance)
* **Responsibility:** Defined the stress testing standards.
* **Contributions:** Developed logic proofs for validating Queue Bottlenecks and verifying the DB deduplication success rate under the pressure of 50 simultaneous identical spider requests.

### 🔎 @SearchSpecialist & 🕸️ @CrawlerSpecialist
* **Responsibility:** Core algorithm implementation.
* **Contributions:** The Crawler agent meticulously structured a native `html.parser` extending ignoring `<script>` and `<style>` blocks, and sanitizing absolute URLs. The Search agent engineered the in-memory tuple calculation scoring `(title-matches * 10) + (content-matches * 1)` while actively executing concurrent non-blocking reads relying on the WAL journal mode.

### 🎨 @UISpecialist (Visibility Engineer)
* **Responsibility:** Built the native dashboard interface.
* **Contributions:** Built a zero-dependency HTML dashboard on `http.server`. Hooked an asynchronous Javascript `fetch()` engine to pull `api/metrics` and `api/search` queries. This allowed the human user to initiate Deep Web Seed Crawls, track "Recently Indexed" URLs, and fire search terms seamlessly while crawler processes run asynchronously in the background.

## 3. Decision Matrix & Iteration History
1. The **SystemArchitect** proposed an initial memory-based deduplication hash-map.
2. The **Challenger** rejected it due to OOM constraints strictly adhering to the "Native Only" environment limits.
3. The **Human Controller** reviewed the debate, finalizing the architecture: Drop the memory map, utilize Queue `timeout` mechanics, enforce a DB Writer Proxy, and utilize SQLite indexes for uniqueness.
4. **Iterative Build Phase:** Files (`database.py`, `crawler.py`, `dashboard.py`, `search.py`, `main.py`) were sequentially scripted, rigorously checking back to the multi-agent constraints before execution.