from dotenv import load_dotenv
import os
import requests
import json

load_dotenv()

class HeadlineRetrieval:
    def __init__(self):
        self.keys = {
            "nyt_key": os.getenv("NYT_API_KEY"),
        }

    def get_top_nyt_data(self, topic="home", use_api=True):
        if not use_api:
            with open("mock_nyt_api.json", "r") as f:
                articles = json.load(f)
            return articles["results"]

        url = "https://api.nytimes.com/svc/topstories/v2/" + topic + ".json?api-key=" + self.keys["nyt_key"]
        response = requests.get(url).json()
        articles = response["results"]
        return articles
    
    def get_top_nyt_headlines(self, topic="home", use_api=True):
        articles = self.get_top_nyt_data(topic, use_api)
        headlines = [article["title"] for article in articles]
        return headlines

if __name__ == "__main__":
    headline_retrieval = HeadlineRetrieval()
    nyt_data = headline_retrieval.get_top_nyt_headlines(use_api=False)
    print(nyt_data)

    # write json to file
    with open("headlines.json", "w") as f:
        json.dump(nyt_data, f)
        
    
    