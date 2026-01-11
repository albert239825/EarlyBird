import json
from backend.podcast.ml.retrieval.db.db_utils import DBUtils


class Article:
    def __init__(self, id: str, title: str, content: str, embedding, all_data: dict):
        self.id = id
        self.title = title
        self.content = content
        self.all_data = all_data

        self.lead_paragraph = all_data["lead_paragraph"]
        self.abstract = all_data["abstract"]
        self.snippet = all_data["snippet"]

        self.keywords = all_data["keywords"]
        self.url = all_data["web_url"]

        self.section = all_data["section_name"]

        self.embedding = embedding

        self.date = all_data["pub_date"]

        self._id = None

        self.interest_score = 0
        self.embedding_3d = []

    # allow hashing
    def __hash__(self):
        return hash(self.id)
    # allow equality
    def __eq__(self, other):
        return self.id == other.id

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "embedding": self.embedding,
            "all_data": self.all_data,
            "lead_paragraph": self.lead_paragraph,
            "abstract": self.abstract,
            "snippet": self.snippet,
            "keywords": self.keywords,
            "url": self.url,
            "section": self.section,
            "date": self.date,
            "_id": self._id,
            "interest_score": self.interest_score,
        }
     
class Merger:
    def __init__(self, db_path: str):

        self.db_path = db_path

        self.content_files = [
            "content0-1000.json",
            "content1000-2000.json",
            "content2000-3000.json",
            "content3000-4000.json",
            "content4000-5000.json",
            "content5000-6000.json",
        ]

        self.metadata_file = "vector.json"

        for i in range(len(self.content_files)):
            self.content_files[i] = self.db_path + self.content_files[i]
        
        self.metadata_file = self.db_path + self.metadata_file


    def merge(self):
        paths_content= self.content_files
        path_metadata = self.metadata_file

        metadata = DBUtils(db_file=path_metadata).get_articles()

        all_content = {

        }

        for path in paths_content:
            content_db = DBUtils(db_file=path)
            for article in content_db.get_articles():

                if article["content"] is None:
                    continue

                if type(article["content"]) == str:
                    all_content[article["_id"]] = article["content"]
                else:
                    inner_data = article["content"]
                    id = article["_id"]
                    content = inner_data["article_body"]    
                    all_content[id] = content
                
                
        
        all_articles: list[Article] = []

        for article in metadata:
            if article["all_data"]["document_type"] == "article":
                id = article["all_data"]["_id"]
                if id in all_content:
                    title = article["all_data"]["headline"]["main"]
                    content = all_content[id]
                    embedding = article["vector"]
                    article_obj = Article(id, title, content, embedding, article["all_data"])
                    all_articles.append(article_obj)
        
        return all_articles

if __name__ == "__main__":
    merger = Merger(db_path="ml/retrieval/db/")




