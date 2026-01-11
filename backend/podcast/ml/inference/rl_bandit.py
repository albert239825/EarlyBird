from datetime import datetime, timezone
import numpy as np
from backend.podcast.ml.retrieval.merger import Article

class HybridLinUCBModel:
    """
    A Hybrid LinUCB-based recommender system.
    
    We assume there are N articles (e.g. 5000) and each article 'a' is represented
    as an Article object. Each Article has a d-dimensional embedding (accessible via
    article.embedding). For simplicity the hybrid model assumes that both the disjoint
    (arm-specific) feature x_a and the shared feature z_a are taken to be the article's
    embedding.
    
    The hybrid model is defined as:
    
        E[r_{t,a}] = z_a^T beta* + x_a^T theta*_a,
    
    and the model maintains:
    
      - Global (shared) parameters: A0 (k x k matrix) and b0 (k x 1 vector), with
        beta_hat = A0^{-1} * b0.
      - For each article a (arm):
            A[a]   (d x d matrix),  b[a]   (d x 1 vector)
            B[a]   (d x k matrix) linking the disjoint and shared parts.
            
    The UCB for an article is computed as:
    
        p_a = z_a^T beta_hat + x_a^T theta_hat_a + alpha * sqrt(s),
    
    where theta_hat_a = A_inv[a] * (b[a] - B[a] * beta_hat) and s is computed as:
    
        s = z_a^T A0_inv z_a - 2 z_a^T A0_inv B[a]^T A_inv[a] x_a 
            + x_a^T A_inv[a] x_a + x_a^T A_inv[a] B[a] A0_inv B[a]^T A_inv[a] x_a.
    
    This model supports fast adaptation via a learning_rate parameter and a stabilization
    mechanism that makes updates less aggressive over time.
    
    Public methods:
      - return_next_articles(num_articles): Returns a list of num_articles articles (as Article objects)
         from the set of unreturned articles. The returned list is personalized and diverse in topic,
         as determined by the article.section field.
      - reset(): Resets the "returned" state so that all articles are again eligible.
      - feedback(article, score): Incorporates feedback for a given article and updates the model.
      - seeding(seed_embeddings, seed_scores, seed_lr=5.0): Updates the global parameters using initial
         topic feedback provided by the user (seed embeddings and scores in the range -5 to 5).
    """
    
    def __init__(self, articles, alpha=1.0, learning_rate=1.0, 
                 stabilization=0.001, feedback_exponent=2.0, last_n_hours=96):
        """
        Initialize the HybridLinUCBModel.
        
        Parameters
        ----------
        articles : list of Article
            A list of Article objects.
        alpha : float, optional
            Exploration parameter (default is 1.0).
        learning_rate : float, optional
            Initial learning rate for online updates (default is 1.0). This decays over time.
        stabilization : float, optional
            Stabilization factor. The effective learning rate is:
            learning_rate / (1 + stabilization * num_updates) (default is 0.001).
        feedback_exponent : float, optional
            Exponent to weight feedback (default is 2.0). For a feedback score s (1-100),
            reward is computed as: reward = sign(s-50) * (|s-50|/50)^(feedback_exponent).
        """

        # date is in format of "2025-01-01T00:44:39+0000"

        # filter articles has date object to only be in the last_n_hours
        # Ensure datetime.now() is timezone-aware
        now = datetime.now(timezone.utc)

        # Filter articles to only include those from the last `last_n_hours`
        articles = [
            article for article in articles
            if (now - datetime.strptime(article.date, "%Y-%m-%dT%H:%M:%S%z")).total_seconds() < last_n_hours * 3600
        ]


        _indx_count = 0
        for article in articles:
            article._id = _indx_count
            _indx_count += 1

        self.articles: list[Article] = articles

        print(len(self.articles))

        self.n_articles = len(articles)
        
        # Assume that each article.embedding is a list of floats; convert them to a NumPy array.
        # All embeddings are stacked into a (n_articles x d) array.
        self.embeddings = np.array([np.array(article.embedding, dtype=float) for article in articles])
        self.n_articles, self.d = self.embeddings.shape
        
        # Exploration parameter.
        self.alpha = alpha
        
        # Learning rate and stabilization parameters.
        self.learning_rate = learning_rate
        self.stabilization = stabilization
        self.feedback_exponent = feedback_exponent
        self.num_updates = 0  # counts the number of feedback updates
        
        # For simplicity, we use the article embedding dimension for the shared part.
        self.k = self.d
        
        # Global (shared) parameters: A0 and b0.
        self.A0 = np.identity(self.k)
        self.A0_inv = np.identity(self.k)
        self.b0 = np.zeros((self.k, 1))
        
        # For each article (arm), initialize disjoint parameters.
        # A[a] is a d x d matrix; B[a] is a d x k matrix; b[a] is a d x 1 vector.
        self.A = [np.identity(self.d) for _ in range(self.n_articles)]
        self.A_inv = [np.identity(self.d) for _ in range(self.n_articles)]
        self.B = [np.zeros((self.d, self.k)) for _ in range(self.n_articles)]
        self.b = [np.zeros((self.d, 1)) for _ in range(self.n_articles)]
        
        # Keep track of which articles have not yet been returned.
        self.unreturned_articles = set(range(self.n_articles))
        self._all_articles = set(range(self.n_articles))
    
    def reset(self):
        """
        Reset the list of returned articles so that all articles are again eligible.
        (Does not reset learned parameters.)
        """
        self.unreturned_articles = set(range(self.n_articles))
    
    def _compute_effective_lr(self):
        """
        Compute the effective learning rate (eta) based on the number of updates.
        """
        return self.learning_rate / (1 + self.stabilization * self.num_updates)
    
    def return_next_articles(self, num_articles, update_state=True):
        """
        Return the next best 'num_articles' articles (as a list of Article objects)
        from the set of unreturned articles. This method uses the hybrid LinUCB score:
        
            p_a = z_a^T beta_hat + x_a^T theta_hat_a + alpha * sqrt(s)
        
        where:
            beta_hat = A0_inv * b0,
            theta_hat_a = A_inv[a] * (b[a] - B[a] * beta_hat),
        and s is defined as:
            s = z_a^T A0_inv z_a - 2 z_a^T A0_inv B[a]^T A_inv[a] x_a 
                + x_a^T A_inv[a] x_a + x_a^T A_inv[a] B[a] A0_inv B[a]^T A_inv[a] x_a.
        
        To promote diversity, the method first attempts to select articles from different
        sections (based on article.section). If not enough unique sections are available,
        the remaining articles are filled in based solely on score.
        
        Parameters
        ----------
        num_articles : int
            The number of articles to return.
            
        Returns
        -------
        list of Article
            A list of Article objects selected for recommendation.
        """
        if update_state and not self.unreturned_articles:
            raise Exception("All articles have been returned. Call reset() to start over.")
        
        # Compute global beta_hat.
        beta_hat = self.A0_inv @ self.b0  # shape (k, 1)
        
        scores = []  # list of tuples: (score, article_index)

        # Compute the LinUCB score for each unreturned article.
        loop_articles = self.unreturned_articles if update_state else self._all_articles
        for a in loop_articles:
            x = self.embeddings[a].reshape(self.d, 1)
            z = x  # using the same vector for the shared feature
            theta_hat = self.A_inv[a] @ (self.b[a] - self.B[a] @ beta_hat)
            reward_pred = (z.T @ beta_hat + x.T @ theta_hat).item()
            
            # Compute the uncertainty (exploration bonus) term.
            term1 = (z.T @ self.A0_inv @ z).item()
            term2 = 2 * (z.T @ self.A0_inv @ self.B[a].T @ self.A_inv[a] @ x).item()
            term3 = (x.T @ self.A_inv[a] @ x).item()
            term4 = (x.T @ self.A_inv[a] @ self.B[a] @ self.A0_inv @ self.B[a].T @ self.A_inv[a] @ x).item()
            s = term1 - term2 + term3 + term4
            bonus = self.alpha * np.sqrt(max(s, 0))
            
            score = reward_pred + bonus
            scores.append((score, a))

        # Sort articles by descending score.
        scores.sort(key=lambda tup: tup[0], reverse=True)
        
        # Select articles trying to maximize diversity in 'section'.
        selected = []
        selected_sections = set()
        # First pass: try to select one article per unique section.
        for score, a in scores:
            art_section = self.articles[a].section
            if art_section not in selected_sections:
                selected.append(a)
                selected_sections.add(art_section)
            if len(selected) >= num_articles:
                break
        # Second pass: if fewer than num_articles are selected, fill in with top scoring articles.
        if len(selected) < num_articles:
            for score, a in scores:
                if a not in selected:
                    selected.append(a)
                if len(selected) >= num_articles:
                    break
        
        # Mark the selected articles as returned.
        if update_state:
            for a in selected:
                self.unreturned_articles.remove(a)
        
        # Return the corresponding Article objects.
        return [self.articles[a] for a in selected]
    
    def feedback(self, article, score):
        """
        Incorporate user feedback for a given article and update the model.
        
        Parameters
        ----------
        article : int
            The index (0-indexed) of the article for which feedback is received.
        score : float
            Feedback score in the range [1, 100]. A score of 50 is neutral.
            Very high (e.g. 75+) or very low (e.g. <25) scores are weighted heavily.
        
        The update uses an effective learning rate that decays over time:
            eta = learning_rate / (1 + stabilization * num_updates)
        and the reward is computed as:
            reward = sign(score - 50) * (|score - 50| / 50)^(feedback_exponent)
        so that feedback far from 50 (in either direction) is amplified.
        """
        # Compute reward from feedback score.
        deviation = score - 50.0
        if deviation == 0:
            reward = 0.0
        else:
            reward = np.sign(deviation) * ((abs(deviation) / 50.0) ** self.feedback_exponent)
        
        eta = self._compute_effective_lr()
        
        # Get the article's feature vectors.
        x = self.embeddings[article].reshape(self.d, 1)
        z = x.copy()  # shared feature
        
        # --- Update per-article (disjoint) parameters ---
        self.A[article] = self.A[article] + eta * (x @ x.T)
        self.b[article] = self.b[article] + eta * (reward * x)
        self.B[article] = self.B[article] + eta * (x @ z.T)
        self.A_inv[article] = np.linalg.inv(self.A[article])
        
        # --- Update global (shared) parameters ---
        self.A0 = self.A0 + eta * (z @ z.T - self.B[article].T @ self.A_inv[article] @ self.B[article])
        self.b0 = self.b0 + eta * (reward * z - self.B[article].T @ self.A_inv[article] @ self.b[article])
        self.A0_inv = np.linalg.inv(self.A0)
        
        self.num_updates += 1

    def seeding(self, seed_embeddings, seed_scores, seed_lr=5.0):
        """
        Seed the initial algorithm with topics the user likes or dislikes.
        
        Parameters
        ----------
        seed_embeddings : list of list(float)
            A list of embeddings representing topics submitted by the user.
        seed_scores : list of float
            A list of corresponding scores (ranging from -5 to 5) for each seed embedding.
            A positive score indicates liking a topic; a negative score indicates disliking.
        seed_lr : float, optional
            A weighting factor for the seeding update (default is 5.0).
        
        This function updates the global parameters (A0 and b0) to bias the model
        toward topics the user likes (or away from topics the user dislikes). After processing
        the seeds, the global inverse is updated.
        """
        for emb, score in zip(seed_embeddings, seed_scores):
            z = np.array(emb, dtype=float).reshape(self.k, 1)
            reward = score  # using the seed score directly as reward
            self.A0 = self.A0 + seed_lr * (z @ z.T)
            self.b0 = self.b0 + seed_lr * (reward * z)
        self.A0_inv = np.linalg.inv(self.A0)

# ---------------------------
# Example usage:
if __name__ == '__main__':
    # Suppose we have 5000 articles; here we simulate a few for demonstration.
    np.random.seed(42)
    num_articles = 5000
    d = 50  # embedding dimension
    
    # Create dummy Article objects.
    articles = []
    sections = ['Science', 'Sports', 'Politics', 'Technology', 'Entertainment']
    for i in range(num_articles):
        # Random embedding as a list of floats.
        embedding = np.random.randn(d).tolist()
        # For demonstration, randomly assign a section.
        section = np.random.choice(sections)
        all_data = {
            "lead_paragraph": "Lead paragraph text",
            "abstract": "Abstract text",
            "snippet": "Snippet text",
            "keywords": ["keyword1", "keyword2"],
            "web_url": f"http://example.com/article{i}",
            "section_name": section
        }
        art = Article(id=str(i), title=f"Article {i}", content="Some content", embedding=embedding, all_data=all_data)
        articles.append(art)
    
    # Initialize the model.
    model = HybridLinUCBModel(articles, alpha=1.0, learning_rate=1.0, stabilization=0.001, feedback_exponent=2.0)
    
    # (Optional) Seed the model with user-specified topics.
    # For example, assume the user provided 3 seed embeddings with scores [-3, 2, 5]:
    seed_embeddings = [np.random.randn(d).tolist() for _ in range(3)]
    seed_scores = [-3, 2, 5]
    model.seeding(seed_embeddings, seed_scores, seed_lr=5.0)
    
    # Return 5 next articles that are both high scoring and diverse in topic.
    recommended_articles = model.return_next_articles(num_articles=5)
    print("Recommended articles:")
    for art in recommended_articles:
        print(f"ID: {art.id}, Title: {art.title}, Section: {art.section}")
    
    # Simulate receiving feedback for one of the recommended articles.
    # For example, if the first article receives a score of 80.
    article_index = int(recommended_articles[0].id)  # assuming id is the index as a string
    model.feedback(article_index, score=80)
    
    # Later, the app can call return_next_articles(num_articles) again, and use reset() if needed.
    # For instance, after a session is complete:
    model.reset()
