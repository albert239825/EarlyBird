from ml.inference.rl_bandit_old import HybridLinUCBModel
from retrieval.db.db_utils import DBUtils

import numpy as np

# ---------------------------
# Example usage:
# Suppose we have 5000 articles and each article embedding is a 50-dimensional vector.
# (In practice, these embeddings would come from your database.)
if __name__ == '__main__':

    # Load the article embeddings from the database.
    db_file = "direct/retrieval/db/vector.json"
    db_utils = DBUtils(db_file)
    articles = db_utils.get_articles()

    embeddings = np.array([article["vector"] for article in articles])
    
    # Initialize the model.
    model = HybridLinUCBModel(article_embeddings=embeddings, alpha=1.0, learning_rate=1.0, stabilization=0.001, feedback_exponent=2.0)
    
    # use user input
    while True:
        user_input = input("Enter 'next' to get the next article, or 'exit' to quit: ")
        if user_input.lower() == 'next':
            next_article = model.return_next_article()
            print("Next article to show (index):", next_article)
            print("Title:", articles[next_article]["title"])

            # get input from user
            user_input = input("Enter your score (1-100): ")
            score = int(user_input)
            model.feedback(next_article, score=score)
        elif user_input.lower() == 'exit':
            break
        else:
            print("Invalid input. Please try again.")


    # # Get the next best article (for example, for a given user session).
    # next_article = model.return_next_article()
    # print("Next article to show (index):", next_article)
    
    # # Simulate receiving feedback for that article.
    # # For example, if the user gave a score of 80 (positive feedback).
    # model.feedback(next_article, score=80)
    
    # # Later, get another article.
    # another_article = model.return_next_article()
    # print("Another article to show (index):", another_article)
    
    # # Reset the session (so that all articles become eligible again).
    # model.reset()