import json
import codecs, json 

class DBUtils():
    def __init__(self, db_file):
        self.db_file = db_file
        # open db file (json)
        self.db = json.load(open(self.db_file, "r"))

    def put_article(self, article):
        # add article to db
        self.db["data"].append(article)
        # write db to file
        with open(self.db_file, "w") as f:
            json.dump(self.db, f)

    def write_all_articles(self, articles):
        # write all articles to db

        json.dump({"data": articles}, codecs.open(self.db_file, 'w', encoding='utf-8'), 
          separators=(',', ':'), 
          sort_keys=True, 
          indent=4)
        

    def get_articles(self):
        return self.db["data"]