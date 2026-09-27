import asyncio
import os
import ssl
from typing import Any, Dict, List
import certifi
from openai import batches, embeddings
from openai.types.shared import metadata
from logger import Colors, log_error, log_header, log_info, log_success, log_warning

from dotenv import load_dotenv

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_tavily import TavilyCrawl, TavilyExtract, TavilyMap

load_dotenv()

# configure SSL to not run into SSL issues 
ssl_context = ssl.create_default_context(cafile=certifi.where())
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

embeddings = OpenAIEmbeddings(model="text-embedding-3-small", chunk_size=50, retry_min_seconds=10)
vectorStore = PineconeVectorStore(index_name=os.environ["INDEX_NAME"], embedding=embeddings)
tavily_extract = TavilyExtract()
tavily_map = TavilyMap(max_depth=5, max_breadth=20, max_pages=1000)
tavily_crawl = TavilyCrawl()

async def index_documents(documents: List[Document], batch_size: int = 50):
    log_header("VECTOR STORAGE PHASE")
    log_info(f"Vector indexing: Preparing to add {len(documents)} to vector store.", Colors.DARKCYAN)

    batches = [
        documents[i : i + batch_size] for i in range(0, len(documents), batch_size)
    ]

    log_info(f"VectorStore indexing: Split into {len(batches)} each of {batch_size} documents.")

    async def add_batch(batch: List[Document], batch_num: int):
        try:
            await vectorStore.aadd_documents(batch)
            log_success(f"VectorStore Indexing: Successfully added batch {batch_num}/{len(batches)} of {len(batch)} documents")
        except Exception as e:
            log_error(f"VectorStore Indexing: Failed to add batch {batch_num}: {e}")
            return False
        
        return True
    
    # process batches concurrently
    tasks = [add_batch(batch, i+1) for i, batch in enumerate(batches)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    successful = sum(1 for result in results if result is True)

    if successful == len(batches):
        log_success(f"VectorStore Indexing: All batches processed successfully! {successful}/{len(batches)}")
    else:
        log_warning(f"VectorStore Indexing: Processed {successful}/{len(batches)} batches successfully.")

async def main():
    log_header("DOCUMENTATION INGESTION")
    log_info("TavilyCrawl: on python.langchain.com", Colors.PURPLE)

    res = tavily_crawl.invoke({
        "url": "https://docs.langchain.com/oss/python/langchain/overview/",
        "max_depth": 5,
        "extract_depth": "advanced", # include more data, tables, etc
        "instructions": "content on ai agents" # tells the crawler to get results based on a query and skip anything else. filters URLs to scrape and not the content.
    })

    all_docs = [Document(page_content=result['raw_content'], metadata={"source": result['url']}) for result in res["results"]]
    log_success(f"TavilyCrawl: Success. Crawled {len(all_docs)}.")

    log_header("CHUNKING PHASE")
    log_info(f"Text splitter: processing {len(all_docs)}", Colors.YELLOW)

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=200)
    splitted_docs = text_splitter.split_documents(all_docs)

    log_success(f"Text Splitter: Created {len(splitted_docs)} chunks from {len(all_docs)} documents")

    # Process documents async
    await index_documents(splitted_docs, batch_size=500)

    log_header("PIPELINE COMPLETE")
    log_success("Documentation ingestion pipeline finished successfully.")
    log_info("Summary:", Colors.BOLD)
    log_info(f" * URLS Mapped:          {len(res["results"])}")
    log_info(f" * Documents extracted:  {len(all_docs)}")
    log_info(f" * Chunks created:       {len(splitted_docs)}")

if __name__ == "__main__":
    asyncio.run(main())
