from inference.rl_bandit import HybridLinUCBModel
from retrieval.db.db_utils import DBUtils
from inference.embed import Embedor
from backend.podcast.ml.retrieval.merger import Article, Merger

import numpy as np

# ---------------------------
# Example usage:
# Suppose we have 5000 articles and each article embedding is a 50-dimensional vector.
# (In practice, these embeddings would come from your database.)
if __name__ == '__main__':

    # Load the article embeddings from the database.
    url = "direct/retrieval/db/"
    merger = Merger(db_path = url)
    articles = merger.merge()

    print(f"Total number of articles: {len(articles)}")
    
    # Initialize the model.
    model = HybridLinUCBModel(articles=articles, alpha=1.0, learning_rate=1.0, stabilization=0.001, feedback_exponent=2.0)
    
    liked_topics = [
        "Technology",
        "Health",
        "Science",
    ]

    topic_embeddigns = [

    ]

    score = [
        5,
        2,
        1
    ]

    for topic in liked_topics:
        topic_embedding = Embedor().embed(topic)
        topic_embeddigns.append(topic_embedding)
        # score.append(3)

    # Seed the model with user-specified topics.
    model.seeding(seed_embeddings=topic_embeddigns, seed_scores=score)

    # use user input
    while True:
        user_input = input("Enter 'next' to get the next article, or 'exit' to quit: ")
        if user_input.lower() == 'next':
            print("Getting the next article...")
            next_article = model.return_next_articles(num_articles=5)[0]
            print(f"ID: {next_article.id}, Title: {next_article.title}, Section: {next_article.section}")

            # get input from user
            user_input = input("Enter your score (1-100): ")
            article_index = int(next_article._id)  # assuming id is the index as a string
            model.feedback(article_index, score=int(user_input))

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

    # if __name__ == '__main__':
    # # Suppose we have 5000 articles; here we simulate a few for demonstration.
    # np.random.seed(42)
    # num_articles = 5000
    # d = 50  # embedding dimension
    
    # # Create dummy Article objects.
    # articles = []
    # sections = ['Science', 'Sports', 'Politics', 'Technology', 'Entertainment']
    # for i in range(num_articles):
    #     # Random embedding as a list of floats.
    #     embedding = np.random.randn(d).tolist()
    #     # For demonstration, randomly assign a section.
    #     section = np.random.choice(sections)
    #     all_data = {
    #         "lead_paragraph": "Lead paragraph text",
    #         "abstract": "Abstract text",
    #         "snippet": "Snippet text",
    #         "keywords": ["keyword1", "keyword2"],
    #         "web_url": f"http://example.com/article{i}",
    #         "section_name": section
    #     }
    #     art = Article(id=str(i), title=f"Article {i}", content="Some content", embedding=embedding, all_data=all_data)
    #     articles.append(art)
    
    # # Initialize the model.
    # model = HybridLinUCBModel(articles, alpha=1.0, learning_rate=1.0, stabilization=0.001, feedback_exponent=2.0)
    
    # # (Optional) Seed the model with user-specified topics.
    # # For example, assume the user provided 3 seed embeddings with scores [-3, 2, 5]:
    # seed_embeddings = [np.random.randn(d).tolist() for _ in range(3)]
    # seed_scores = [-3, 2, 5]
    # model.seeding(seed_embeddings, seed_scores, seed_lr=5.0)
    
    # # Return 5 next articles that are both high scoring and diverse in topic.
    # recommended_articles = model.return_next_articles(num_articles=5)
    # print("Recommended articles:")
    # for art in recommended_articles:
    #     print(f"ID: {art.id}, Title: {art.title}, Section: {art.section}")
    
    # # Simulate receiving feedback for one of the recommended articles.
    # # For example, if the first article receives a score of 80.
    # article_index = int(recommended_articles[0].id)  # assuming id is the index as a string
    # model.feedback(article_index, score=80)
    
    # # Later, the app can call return_next_articles(num_articles) again, and use reset() if needed.
    # # For instance, after a session is complete:
    # model.reset()