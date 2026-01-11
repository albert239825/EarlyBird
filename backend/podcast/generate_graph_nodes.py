from sklearn.manifold import TSNE
from backend.podcast.ml.retrieval.merger import Merger
from backend.podcast.ml.inference.rl_bandit import HybridLinUCBModel
import numpy as np
import math

class InterestGraph:

    def __init__(self, rl_model):
        self.nodes = rl_model.articles
        self.rl_model = rl_model

    def generate_init_nodes(self):
        embeddings = []
        for node in self.nodes:
            embeddings.append(node.embedding)
        tsne = TSNE(n_components=3, perplexity=30, learning_rate=200, n_iter=1000)
        embeddings_3d = tsne.fit_transform(np.array(embeddings))
        for i in range(len(embeddings_3d)):
            self.nodes[i].embedding_3d = embeddings_3d[i].tolist()
        
        return embeddings_3d

    def update_interest_scores(self):
        n = self.rl_model.n_articles
        top_articles = self.rl_model.return_next_articles(n, update_state=False)
        
        for x in range(1, n + 1):
            top_articles[x - 1].interest_score = 1 - (1 / n * x)**(1/3)

    
    def update_rl_model(self, x, y, z):
        closest_article = self.nodes[0]
        dist = float('inf')
        for node in self.nodes:
            e = node.embedding_3d
            d = (e[0] - x) ** 2 + (e[1] - y) ** 2 + (e[2] - z) ** 2
            if d < dist:
                dist = d
                closest_article = node
        
        category = closest_article.section
        print(category)
        delta = 80
        for i in range(len(self.nodes)):
            if self.nodes[i].section == category:
                self.rl_model.feedback(i, delta)







    