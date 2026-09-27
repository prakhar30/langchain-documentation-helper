# Tavily Notes

A more custom way to scape some website is to use more advanced tools such as TavilyMap and TavilyExtract.


1. We can use TavilyMap to map out the structure of a given website.
```
tavily_map = TavilyMap(
    max_depth = 3,      # crawl 3 levels deep
    max_breadth = 15,   # Follow upto 15 links per page
    limit = 500,        # limit to toal 500 pages for demo
)

demo_url = "https://something.com/"
site_map = tavily_map.invoke(demo_url)
urls = site_map.get('results', [])
```

2. We can then use TavilyExtract to then extract the pages, from the map generated above.
```
tavily_extract = TavilyExtract()

extraction_result = await tavily_extract.ainvoke(input={"urls": urls})
extracted_docs = extraction_result.get('results', [])
```

3. For scale we might want to break our entire list of URLs in batches to be fetched simultaneoulsy. We can use the async invoke ainvoke method to be called in parallel with batches of URLs, that we can await on by using `await asyncio.gather(*tasks)`