import asyncio
from typing import Tuple, List
from retrieval_pipeline import RetrievalPipeline
from nyt_parser import parse_nyt_article_direct, parse_nyt_article_batch
from pull_headlines import HeadlineRetrieval
from db.db_utils import DBUtils
import json

class OndemandPull():
    def __init__(self):
        pass
    
    async def get_article_urls(self):
        # get all articles
        db_file = "direct/retrieval/db/vector.json"
        db_utils = DBUtils(db_file)
        articles = db_utils.get_articles()

        # filter articles
        filtered_articles = [article for article in articles if article["all_data"]["document_type"] == "article"]
        
        id_urls = [(article["all_data"]["_id"], article["all_data"]["web_url"]) for article in filtered_articles]

        return id_urls

    async def get_finished_urls(self):
        db_file="direct/retrieval/db/content.json"
        db_utils = DBUtils(db_file)
        articles = db_utils.get_articles()

        finished_urls = [article["_id"] for article in articles]

        return finished_urls

    async def get_finish_urls_data(self):
        db_file="direct/retrieval/db/content.json"
        db_utils = DBUtils(db_file)
        articles = db_utils.get_articles()

        return articles

    async def get_skipped(self):
        db_file="direct/retrieval/db/skipped.json"
        db_utils = DBUtils(db_file)
        articles = db_utils.get_articles()

        return articles

    async def continue_fetch(self, batch_size: int = 3):
        
        candidate_data = (await self.get_article_urls())[5000:]
        len_total = len(candidate_data)

        db_file="direct/retrieval/db/content.json"
        db_utils = DBUtils(db_file)

        db_skip_file="direct/retrieval/db/skipped.json"
        db_utils_skip = DBUtils(db_skip_file)

        # get finished articles
        finished_urls = await self.get_finished_urls()

        # get skipped urls
        skipped_urls = await self.get_skipped()

        print(f"All finished or skipped articles: {len(finished_urls) + len(skipped_urls)}")

        unfinished_urls: Tuple[str, str] = [url for url in candidate_data if url[0] not in finished_urls]
        unfinished_urls = [url for url in unfinished_urls if url[1] not in skipped_urls]

        print(f"Remaining unfinished articles: {len(unfinished_urls)}")

        finished_articles = await self.get_finish_urls_data()

        # Batch the URLs
        for i in range(0, len(unfinished_urls), batch_size):
            batch = unfinished_urls[i:i + batch_size]
            
            # Process the batch concurrently
            results = await parse_nyt_article_batch([url[1] for url in batch])

            if "RATE_LIMITED" in results:
                # exit python
                exit(1)
            
            for (id, url), content in zip(batch, results):
                if content is not None:
                    finished_articles.append({
                        "_id": id,
                        "content": content
                    })
                    db_utils.write_all_articles(finished_articles)
                else:
                    skipped_urls.append(url)
                    db_utils_skip.write_all_articles(skipped_urls)
                
                print(f"Finished {len(finished_articles) + len(skipped_urls)} articles out of {len_total}: {(len(finished_articles) + len(skipped_urls)) / len_total * 100:.2f}%")
if __name__ == "__main__":
    asyncio.run(OndemandPull().continue_fetch())

                