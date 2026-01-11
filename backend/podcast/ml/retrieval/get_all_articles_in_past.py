import os
import json
class GetAllArticlesInPast:
    def __init__(self):
        # find all files in directory direct/retrieval/ starting with "all_metadata_"
        self.raw_files = [
            f for f in os.listdir("direct/retrieval/") if f.startswith("all_metadata_") and f.endswith(".json")
        ]
        
        # file format "all_metadata_year_MM.json," get year and month
        self.files = [
            {
                "year": int(f.split("_")[2]),
                "month": int(f.split("_")[3].split(".")[0]),
                # read file and jsojn load
                "file": json.load(open("direct/retrieval/" + f, "r"))["response"]["docs"],
            }
            for f in self.raw_files
        ]

        for f in self.files:
            # print(len(f["file"]))
            pass

    def get_articles(self):
        return self.files

    def get_articles_as_one_list(self):
        articles = [

        ]

        for f in self.files:
            for article in f["file"]:
                articles.append({
                    "year": f["year"],
                    "month": f["month"],
                    "title": article["headline"]["main"],
                    "lead_paragraph": article["lead_paragraph"],
                    "abstract": article["abstract"],
                    "snippet": article["snippet"],
                    "keywords": article["keywords"],
                    "all_data": article,
                    "url": article["web_url"],
                })
        return articles
    

if __name__ == "__main__":
    GetAllArticlesInPast()