# langchain-documentation-helper

A full RAG pipeline over the LangChain docs: crawl the documentation site with Tavily, chunk and embed it into Pinecone, then answer questions with an agent that retrieves its own context and cites sources. Ingestion and retrieval are split into separate entry points.

## What it does
- **`main.py`** — crawls `docs.langchain.com`, splits the pages into chunks, and indexes them into Pinecone concurrently
- **`retrieval.py`** — runs a tool-calling agent that queries the index and answers with citations
- **`logger.py`** — small colour-coded console logger used to trace each phase of the pipeline

## Notes & details
- **The crawler is query-aware.** `TavilyCrawl` takes an `instructions` argument ("content on ai agents"), which filters *which URLs get crawled* rather than filtering the text after the fact — a cheaper way to keep an index focused than scraping everything and sorting it out later.
- **Indexing runs concurrently.** Documents are batched and pushed through `aadd_documents` via `asyncio.gather`, with per-batch success/failure logged instead of one failed batch killing the run.
- **Retrieval is agentic, not a fixed chain.** Rather than always retrieving, `create_agent` decides when to call `retrieve_context`, so it can search more than once or skip retrieval entirely.
- **`response_format="content_and_artifact"`** is the interesting bit — the tool returns a formatted string *for the model* and the raw `Document` objects *for your code*. The raw docs are pulled back out of the `ToolMessage.artifact` fields, so `run_llm` can return both the answer and the exact context behind it.
- **Sources survive the whole trip** — the crawl stores each page URL in `metadata["source"]`, which the tool interpolates into the retrieved text, which the system prompt then tells the model to cite.
- **Chunking is bigger here**: `RecursiveCharacterTextSplitter` at 4000 chars with 200 overlap. Recursive splitting respects paragraph and newline boundaries, which matters much more for docs than for plain prose.
- **`text-embedding-3-small`** with `chunk_size=50` and `retry_min_seconds=10` to stay on the right side of embedding rate limits during a large crawl.
- **SSL is pinned to `certifi`** at import time — a pragmatic fix for cert failures when crawling many hosts from macOS.
- **`tavily_notes.md`** documents the alternative `TavilyMap` → `TavilyExtract` approach: map the site structure first, then extract pages in parallel batches. Useful when you want more control than `TavilyCrawl` gives you.
- **Requires** `OPENAI_API_KEY`, `TAVILY_API_KEY`, `PINECONE_API_KEY`, and `INDEX_NAME` in `.env`.

## Run
```bash
uv sync

# 1. Crawl + index (run once)
uv run main.py

# 2. Ask a question
uv run retrieval.py
```
