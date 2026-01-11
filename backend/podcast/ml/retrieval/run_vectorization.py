from db.db_utils import DBUtils
from get_all_articles_in_past import GetAllArticlesInPast
from sentence_transformers import SentenceTransformer
import codecs, json 

class RunVectorization:
    def __init__():
        pass
    def run_vectorization():
        # print current directory
        db_file = "direct/retrieval/db/vector.json"
        db_utils = DBUtils(db_file)

        articles = GetAllArticlesInPast().get_articles_as_one_list()
    
    # use SentenceTransformer to vectorize articles

        print("Vectorizing articles...")

        model = SentenceTransformer('multi-qa-MiniLM-L6-cos-v1')
        total_finished = 0

        print(f"Total articles to vectorize: {len(articles)}")

        for article in articles:
            # vectorize article
            full_keyword_string = ""

            for keyword in article["keywords"]:
                full_keyword_string += keyword["name"] + ", "


            full_text = f""" 
            {article['title']} 
            \n \
            {article['abstract']} \

            {article['lead_paragraph']}

            {article['snippet']}

            {full_keyword_string}
            """
            article["encoded_text"] = full_text
            article["vector"] = model.encode(article["encoded_text"]).tolist()
            # add article to db
            total_finished += 1

            if total_finished % 100 == 0:
                print(f"Finished {total_finished} articles of {len(articles)}")



        db_utils.write_all_articles(articles)

if __name__ == "__main__":
    RunVectorization.run_vectorization()

        