import numpy as np

class HybridLinUCBModel:
    """
    A Hybrid LinUCB-based recommender system.
    
    We assume there are N articles (here, 5000) and each article 'a' is associated with
    a d-dimensional embedding vector. The hybrid model is defined as:
    
        E[r_{t,a}] = z_a^T beta* + x_a^T theta*_a,
    
    where x_a (the disjoint feature) and z_a (the shared feature) are both taken to be the
    article embedding (for simplicity). The algorithm maintains:
    
      - Global (shared) parameters: A0 (d x d matrix) and b0 (d x 1 vector), with
        beta_hat = A0^{-1} * b0.
      - For each article a (arm):
            A[a]   (d x d matrix),  b[a]   (d x 1 vector)
            B[a]   (d x d matrix) -- linking the disjoint and shared parts.
            
    The UCB for an article is computed as:
    
        p_a = z_a^T beta_hat + x_a^T theta_hat_a + alpha * sqrt(s),
    
    where theta_hat_a = A[a]^{-1} (b[a] - B[a] beta_hat) and s is a (complicated) measure
    of uncertainty (see details in the code).
    
    This model also supports fast adaptation via a learning_rate parameter and a stabilization
    mechanism that makes updates less aggressive after many updates.
    
    Public methods:
      - return_next_article(): returns the next best article (by index) that has not yet been returned.
      - reset(): resets the "returned" state so that all articles are again eligible.
      - feedback(article, score): updates the model using the feedback for a given article.
      
    Parameters such as alpha, learning_rate, stabilization, and feedback_exponent can be tuned.
    """
    
    def __init__(self, article_embeddings, alpha=1.0, learning_rate=1.0, 
                 stabilization=0.001, feedback_exponent=2.0):
        """
        Initialize the HybridLinUCBModel.
        
        Parameters
        ----------
        article_embeddings : np.ndarray
            A NumPy array of shape (n_articles, d) representing the article embeddings.
        alpha : float, optional
            Exploration parameter (default is 1.0).
        learning_rate : float, optional
            Initial learning rate for online updates (default is 1.0). This will decay over time.
        stabilization : float, optional
            Stabilization factor. The effective learning rate will be
            lr_effective = learning_rate / (1 + stabilization * num_updates).
            (default is 0.001)
        feedback_exponent : float, optional
            Exponent to weight feedback (default is 2.0). For a score s (1-100),
            reward is computed as: reward = sign(s-50) * (abs(s-50)/50)^(feedback_exponent).
        """
        self.embeddings = article_embeddings
        self.n_articles, self.d = article_embeddings.shape
        
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
    
    def return_next_article(self):
        """
        Return the next best article (by index) from the set of articles that have not yet been returned.
        
        Uses the hybrid LinUCB score:
            p_a = z_a^T beta_hat + x_a^T theta_hat_a + alpha * sqrt(s)
        where:
            beta_hat = A0_inv * b0,
            theta_hat_a = A_inv[a] * (b[a] - B[a] * beta_hat)
        and s is a measure of uncertainty computed as:
            s = z_a^T A0_inv z_a - 2 * z_a^T A0_inv B[a]^T A_inv[a] x_a 
                + x_a^T A_inv[a] x_a + x_a^T A_inv[a] B[a] A0_inv B[a]^T A_inv[a] x_a.
        
        Returns
        -------
        article_index : int
            The index (from 0 to n_articles-1) of the selected article.
        """
        if not self.unreturned_articles:
            raise Exception("All articles have been returned. Call reset() to start over.")
        
        # Compute global beta_hat.
        beta_hat = self.A0_inv @ self.b0  # shape (d, 1)
        
        best_score = -np.inf
        best_article = None
        
        # Loop over all articles that have not yet been returned.
        for a in self.unreturned_articles:
            # Get the article's embedding. We'll use it both as x and z.
            x = self.embeddings[a].reshape(self.d, 1)
            z = x  # shared feature
            
            # Compute the per-article parameter: theta_hat_a = A_inv[a] * (b[a] - B[a]*beta_hat)
            theta_hat = self.A_inv[a] @ (self.b[a] - self.B[a] @ beta_hat)  # shape (d, 1)
            
            # Predicted reward (exploitation term)
            reward_pred = (z.T @ beta_hat + x.T @ theta_hat).item()
            
            # Compute uncertainty (exploration bonus) term.
            # s = z^T A0_inv z - 2 z^T A0_inv B[a]^T A_inv[a] x + x^T A_inv[a] x 
            #     + x^T A_inv[a] B[a] A0_inv B[a]^T A_inv[a] x.
            term1 = (z.T @ self.A0_inv @ z).item()
            term2 = 2 * (z.T @ self.A0_inv @ self.B[a].T @ self.A_inv[a] @ x).item()
            term3 = (x.T @ self.A_inv[a] @ x).item()
            term4 = (x.T @ self.A_inv[a] @ self.B[a] @ self.A0_inv @ self.B[a].T @ self.A_inv[a] @ x).item()
            s = term1 - term2 + term3 + term4
            bonus = self.alpha * np.sqrt(max(s, 0))  # ensure non-negative
            
            score = reward_pred + bonus
            
            if score > best_score:
                best_score = score
                best_article = a
        
        # Mark the selected article as "returned" and return its index.
        self.unreturned_articles.remove(best_article)
        return best_article
    
    def feedback(self, article, score):
        """
        Incorporate user feedback for a given article and update the model.
        
        Parameters
        ----------
        article : int
            The index (0-indexed) of the article for which feedback is received.
        score : float
            Feedback score in the range [1, 100]. A score of 50 is neutral.
            Very high (e.g. 75+) or very low (e.g. <25) scores should be weighted heavily.
        
        The update uses an effective learning rate that decays over time:
        
            eta = learning_rate / (1 + stabilization * num_updates)
            
        and the reward is computed as:
        
            reward = sign(score - 50) * (|score - 50|/50)^(feedback_exponent)
            
        so that feedback far from 50 (in either direction) is amplified.
        """
        # Compute reward from feedback score.
        deviation = score - 50.0
        # If the score is neutral, reward is 0.
        if deviation == 0:
            reward = 0.0
        else:
            reward = np.sign(deviation) * ((abs(deviation) / 50.0) ** self.feedback_exponent)
        
        # Compute effective learning rate.
        eta = self._compute_effective_lr()
        
        # Get the article's feature vectors.
        x = self.embeddings[article].reshape(self.d, 1)  # disjoint feature
        z = x.copy()  # shared feature
        
        # --- Update per-article (disjoint) parameters for article 'a' ---
        # A[a] <- A[a] + eta * (x * x^T)
        self.A[article] = self.A[article] + eta * (x @ x.T)
        # b[a] <- b[a] + eta * (reward * x)
        self.b[article] = self.b[article] + eta * (reward * x)
        # B[a] <- B[a] + eta * (x * z^T)
        self.B[article] = self.B[article] + eta * (x @ z.T)
        
        # Update the inverse for article 'a'
        self.A_inv[article] = np.linalg.inv(self.A[article])
        
        # --- Update global (shared) parameters ---
        # Following the hybrid LinUCB update (see Algorithm 2 in the paper):
        # A0 <- A0 + eta * (z * z^T - B[a]^T * A[a]^{-1} * B[a])
        self.A0 = self.A0 + eta * (z @ z.T - self.B[article].T @ self.A_inv[article] @ self.B[article])
        # b0 <- b0 + eta * (reward * z - B[a]^T * A[a]^{-1} * b[a])
        self.b0 = self.b0 + eta * (reward * z - self.B[article].T @ self.A_inv[article] @ self.b[article])
        
        # Update the global inverse.
        self.A0_inv = np.linalg.inv(self.A0)
        
        # Increment the update counter.
        self.num_updates += 1

# ---------------------------
# Example usage:
# Suppose we have 5000 articles and each article embedding is a 50-dimensional vector.
# (In practice, these embeddings would come from your database.)
if __name__ == '__main__':
    print("Hybrid LinUCB Model Example")
    # For demonstration, create random embeddings.
    np.random.seed(42)
    n_articles = 5000
    d = 500
    embeddings = np.random.randn(n_articles, d)
    
    print("Intializing model...")
    # Initialize the model.
    model = HybridLinUCBModel(article_embeddings=embeddings, alpha=1.0, learning_rate=1.0, stabilization=0.001, feedback_exponent=2.0)
    
    print("Getting the next article...")
    # Get the next best article (for example, for a given user session).
    next_article = model.return_next_article()
    print("Next article to show (index):", next_article)
    
    # Simulate receiving feedback for that article.
    # For example, if the user gave a score of 80 (positive feedback).
    model.feedback(next_article, score=80)
    
    # Later, get another article.
    another_article = model.return_next_article()
    print("Another article to show (index):", another_article)
    
    # Reset the session (so that all articles become eligible again).
    model.reset()