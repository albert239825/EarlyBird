from nyt_parser import parse_nyt_article_direct
from pull_headlines import HeadlineRetrieval
import asyncio
import aiohttp
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class RetrievalPipeline:
    def __init__(self):
        self.headline_retrieval = HeadlineRetrieval()

    def get_headlines(self, topic="home", use_api=True):
        return self.headline_retrieval.get_top_nyt_headlines(topic, use_api)

    async def fetch_and_parse_articles(self, urls):
        tasks = [parse_nyt_article_direct(url) for url in urls]
        results = await asyncio.gather(*tasks)
        return results
    
    async def run_pipeline(self, topic="home", use_api=True, batch_size=1, max_limit=100):
        headlines_with_data = self.headline_retrieval.get_top_nyt_data(topic, use_api)
        headlines = [article["title"] for article in headlines_with_data]
        urls = [article["url"] for article in headlines_with_data]

        logging.info(f"Retrieving {len(urls)} articles in batches of {batch_size}")
        
        all_parsed_articles = []

        for i in range(0, min(len(urls), max_limit), batch_size):
            batch_urls = urls[i:i + batch_size]
            parsed_articles = await self.fetch_and_parse_articles(batch_urls)
            
            for j, article_data in enumerate(parsed_articles):
                if article_data:
                    logging.info(f"Successfully parsed article from {batch_urls[j]}")
                else:
                    logging.warning(f"Failed to parse article from {batch_urls[j]}")
            
            all_parsed_articles.extend(parsed_articles)

        # combine headlines with article content
        for i, article in enumerate(headlines_with_data):
            if i >= len(all_parsed_articles):
                break
            if all_parsed_articles[i]:
                article["content"] = all_parsed_articles[i]
            else:
                article["content"] = "Failed to retrieve content."

        return headlines_with_data

async def main():
    pipeline = RetrievalPipeline()
    results = await pipeline.run_pipeline(use_api=False, max_limit=3)

    # write results to file
    import json
    with open("retrieval_results.json", "w") as f:
        json.dump(results, f, indent=4)

if __name__ == "__main__":
    asyncio.run(main())