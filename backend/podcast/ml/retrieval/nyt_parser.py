import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import logging
import re
from typing import Optional, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def get_archive_url(url):
    """
    """
    archive_url = f"http://archive.is/latest/{url}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(archive_url, allow_redirects=False) as response:
                if response.status == 302:
                    return response.headers['Location']
                elif response.status == 429:
                    logging.warning(f"Rate limited while accessing {archive_url}.")
                    return "RATE_LIMITED"
                else:
                    logging.warning(f"No redirect found for {url}. Status: {response.status}")
                    return None
    except aiohttp.ClientError as e:
        logging.error(f"Error fetching archive.is URL: {e}")
        return None

async def parse_archive_article(archive_url):
    """
    Parses the archived article from archive.is and extracts the article body.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(archive_url) as response:
                if response.status != 200:
                    logging.error(f"Failed to fetch archived article: {archive_url} with status code: {response.status}")
                    return None

                html = await response.text()
                
                # write html to file
                # with open("archive.html", "w") as f:
                #     f.write(html)

                soup = BeautifulSoup(html, 'html.parser')

                # Extract article body (this might need adjustment based on archive.is layout)
                article_body = ''
                # Attempt to extract from main content area
                content_div = soup.find('div', {'id': 'app'})  # Adjust selector as needed
                if content_div:
                    paragraphs = content_div.find_all('div')
                    article_body = '\n\n'.join(p.text for p in paragraphs)
                else:
                    # Fallback: extract all paragraphs from the body
                    paragraphs = soup.find_all('p')
                    article_body = '\n\n'.join(p.text for p in paragraphs)

                return article_body.strip()

    except aiohttp.ClientError as e:
        logging.error(f"HTTP error occurred: {e}")
        return None
    except Exception as e:
        logging.error(f"Error parsing archived article: {e}")
        return None

async def pull_out_first_content(article_body: str) -> str:
    # spit by newlines
    paragraphs = article_body.split("\n")
    # remove empty paragraphs
    paragraphs = [p for p in paragraphs if p.strip()]

    # return first paragraph
    return paragraphs[0]

async def parse_nyt_article(url, session):
    """
    Parses a New York Times article by first retrieving its archive.is snapshot.
    """
    try:
        archive_url = await get_archive_url(url)
        if archive_url == "RATE_LIMITED":
            return "RATE_LIMITED"
        if not archive_url:
            logging.warning(f"No archive found for {url}")
            return None

        article_body = await parse_archive_article(archive_url)
        if not article_body:
            logging.warning(f"Failed to parse article from archive: {archive_url}")
            return None
        
        # Since we're using archive.is, we might not reliably get title/author/date
        # Consider extracting them from the original URL's HTML if needed, but this
        # might trigger paywalls. For now, we'll leave them as "Not found".
        return {
            'title': 'Title not found (archive.is)',
            'author': 'Author not found (archive.is)',
            'date': 'Date not found (archive.is)',
            'article_body': await pull_out_first_content(article_body)
        }

    except Exception as e:
        logging.error(f"Error parsing NYT article via archive.is: {e}")
        return None

async def parse_nyt_article_direct(url):
    article_data = await parse_nyt_article(url, None)
    if article_data:
        pass
    else:
        print("Failed to parse the article.")
        return None

    return article_data["article_body"]

async def parse_nyt_article_batch(urls: List[str]):
    """
    Parses a batch of New York Times articles.
    """
    tasks = []
    for url in urls:
        tasks.append(parse_nyt_article(url, None))
    return await asyncio.gather(*tasks)

async def main():
    """
    Main function to demonstrate the usage of the NYT article parser.
    """
    # nyt_url = 'https://www.nytimes.com/2024/04/16/us/politics/house-impeachment-mayorkas.html'  # Replace with a valid NYT URL
    nyt_url = "https://www.nytimes.com/2025/02/14/nyregion/eric-adams-drop-charges-sdny.html"

    data = await parse_nyt_article_direct(nyt_url)
    
    if data:
        # write data to file
        with open("nyt_article.txt", "w") as f:
            f.write(data)


if __name__ == '__main__':
    asyncio.run(main())