import pandas as pd
import spacy
import re
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer

from retrieval.merger import Merger

# install spacy en_core_web_sm

class NewsKeywordExtractor:
    """
    A modular class for extracting the top N keywords from a collection of Article objects.
    
    Workflow:
      1. Filter articles by a specific category (if provided) using a field in Article.all_data.
      2. Preprocess text:
         - Lowercase conversion
         - Tokenization
         - Stopword removal
         - Lemmatization
      3. Compute TF-IDF scores (optional).
      4. Extract Named Entities (optional).
      5. Combine token frequencies, TF-IDF scores, and entity frequencies.
      6. Identify the top N keywords.
      7. Calculate the coverage percentage (the percentage of articles mentioning the keyword).
    
    All parameters are customizable.
    """
    
    def __init__(self, 
                 articles, 
                 category=None, 
                 category_field="category",
                 top_n=10, 
                 text_field="content", 
                 tfidf_max_features=1000, 
                 use_ner=True, 
                 use_tfidf=True, 
                 language_model="en_core_web_sm", 
                 custom_stopwords=None):
        """
        Initialize the extractor.
        
        Parameters:
            articles (list): List of Article objects.
            category (str, optional): Specific category to filter articles.
            category_field (str): Key in Article.all_data to filter by (default: "category").
            top_n (int): Number of top keywords to extract.
            text_field (str): Name of the Article attribute to use as text (e.g., "content").
            tfidf_max_features (int): Maximum features for TfidfVectorizer.
            use_ner (bool): Whether to extract keywords using Named Entity Recognition.
            use_tfidf (bool): Whether to include TF-IDF scores in keyword ranking.
            language_model (str): spaCy language model to load.
            custom_stopwords (iterable, optional): Additional stopwords to remove.
        """
        # List of Article objects
        self.articles = articles
        
        self.category = category
        self.category_field = category_field
        self.top_n = top_n
        self.text_field = text_field
        self.tfidf_max_features = tfidf_max_features
        self.use_ner = use_ner
        self.use_tfidf = use_tfidf
        self.language_model = language_model
        self.custom_stopwords = set(custom_stopwords) if custom_stopwords is not None else set()
        
        # Load spaCy model and add custom stopwords if provided
        self.nlp = spacy.load(language_model)
        if self.custom_stopwords:
            for word in self.custom_stopwords:
                self.nlp.Defaults.stop_words.add(word)
        
        # Internal storage for filtered and preprocessed articles
        self.filtered_articles = []
        self.preprocessed_articles = []  # List of dicts: { "article": Article, "tokens": [...] }
    
    def filter_data(self):
        """
        Filter articles based on the specified category.
        Assumes the Article object's all_data dict may contain a key for category_field.
        """
        if self.category:
            self.filtered_articles = [
                article for article in self.articles 
                if article.all_data.get(self.category_field) == self.category
            ]
            # use first 100
            self.filtered_articles = self.filtered_articles[:100]
        else:
            self.filtered_articles = self.articles[:]
    
    def preprocess_text(self, text):
        """
        Preprocess a single text:
          - Convert to lowercase.
          - Tokenize using spaCy.
          - Remove non-alphabetic tokens and stopwords.
          - Lemmatize tokens.
        """
        doc = self.nlp(text.lower())
        tokens = [token.lemma_ for token in doc if token.is_alpha and not token.is_stop]
        return tokens
    
    def apply_preprocessing(self):
        """Preprocess the text for each filtered article and store tokens."""
        self.preprocessed_articles = []
        finished = 0
        for article in self.filtered_articles:
            text = getattr(article, self.text_field)
            tokens = self.preprocess_text(text)
            finished += 1
            if finished %10 == 0:
                print(f"Finished preprocessing {finished} articles of {len(self.filtered_articles)}")
            self.preprocessed_articles.append({"article": article, "tokens": tokens})
    
    def get_token_counts(self):
        """
        Count the frequency of each token from the preprocessed articles.
        
        Returns:
            Counter: Frequency count of tokens.
        """
        all_tokens = [token for item in self.preprocessed_articles for token in item["tokens"]]
        return Counter(all_tokens)
    
    def compute_tfidf_scores(self):
        """
        Compute TF-IDF scores for the texts from the filtered articles.
        
        Returns:
            dict: Mapping terms to their aggregated TF-IDF score.
        """
        texts = [getattr(article, self.text_field) for article in self.filtered_articles]
        vectorizer = TfidfVectorizer(max_features=self.tfidf_max_features, stop_words='english')
        X = vectorizer.fit_transform(texts)
        feature_names = vectorizer.get_feature_names_out()
        tfidf_scores = X.toarray().sum(axis=0)
        return dict(zip(feature_names, tfidf_scores))
    
    def extract_entities(self):
        """
        Extract named entities from each article's text.
        
        Returns:
            Counter: Frequency count of all named entities (converted to lowercase).
        """
        entities = []
        for article in self.filtered_articles:
            text = getattr(article, self.text_field)
            doc = self.nlp(text)
            entities.extend([ent.text.lower() for ent in doc.ents])
        return Counter(entities)
    
    def combine_counts(self, token_counts, tfidf_scores=None, entity_counts=None):
        """
        Combine token counts, TF-IDF scores, and entity counts for keyword ranking.
        
        Returns:
            Counter: Combined counts used for ranking keywords.
        """
        combined = Counter(token_counts)
        if tfidf_scores and self.use_tfidf:
            combined += Counter(tfidf_scores)
        if entity_counts and self.use_ner:
            combined += entity_counts
        return combined
    
    def get_top_keywords(self, combined_counts):
        """
        Retrieve the top N keywords based on the combined counts.
        
        Returns:
            list: List of top keywords.
        """
        sorted_keywords = sorted(combined_counts.items(), key=lambda x: x[1], reverse=True)
        return [keyword for keyword, count in sorted_keywords[:self.top_n]]
    
    def compute_coverage(self, keywords):
        """
        Calculate the coverage percentage for each keyword.
        Coverage is the percentage of filtered articles that mention the keyword.
        
        Parameters:
            keywords (list): List of keywords.
        
        Returns:
            dict: Mapping from keyword to its coverage percentage.
        """
        coverage = {}
        for keyword in keywords:
            pattern = re.compile(r'\b{}\b'.format(re.escape(keyword)), flags=re.IGNORECASE)
            count = sum(1 for article in self.filtered_articles 
                        if pattern.search(getattr(article, self.text_field)))
            coverage[keyword] = (count / len(self.filtered_articles)) * 100 if self.filtered_articles else 0
        return coverage
    
    def run(self):
        """
        Execute the complete keyword extraction workflow:
          1. Filter articles by category.
          2. Preprocess texts.
          3. Compute token counts, TF-IDF scores, and extract entities.
          4. Combine counts.
          5. Identify top keywords.
          6. Calculate coverage for each keyword.
        
        Returns:
            pd.DataFrame: DataFrame with columns ['Keyword', 'Count', 'Coverage (%)'].
        """
        print("Filtering articles...")
        self.filter_data()
        if not self.filtered_articles:
            print("No articles available after filtering.")
            return pd.DataFrame()
        print("Preprocessing text...")
        self.apply_preprocessing()
        print("Computing token counts...")
        token_counts = self.get_token_counts()
        print("Computing TF-IDF scores..." if self.use_tfidf else "Skipping TF-IDF computation.")
        tfidf_scores = self.compute_tfidf_scores() if self.use_tfidf else None
        print("Extracting named entities..." if self.use_ner else "Skipping NER extraction.")
        entity_counts = self.extract_entities() if self.use_ner else None
        
        print("Combining counts...")
        combined_counts = self.combine_counts(token_counts, tfidf_scores, entity_counts)
        print("Identifying top keywords...")
        top_keywords = self.get_top_keywords(combined_counts)
        print("Computing coverage...")
        coverage = self.compute_coverage(top_keywords)
        
        print("Creating DataFrame...")
        result = pd.DataFrame({
            "Keyword": top_keywords,
            "Count": [combined_counts[kw] for kw in top_keywords],
            "Coverage (%)": [coverage[kw] for kw in top_keywords]
        })
        return result

# =================== USAGE EXAMPLE ===================

if __name__ == "__main__":
    # Example Article class
    print("Loading articles...")

    merger = Merger(db_path="direct/retrieval/db/")
    articles = merger.merge()
    
    print("Articles loaded.")
    print(len(articles))
    # Initialize the extractor. For example, we filter by category "politics" and use the "content" field.
    extractor = NewsKeywordExtractor(
        articles=articles,
        category="World",
        category_field="section_name",
        top_n=10,
        text_field="content",
        tfidf_max_features=500,
        use_ner=True,
        use_tfidf=True,
        language_model="en_core_web_sm",
        custom_stopwords=["said", "will"]
    )
    
    # Run the workflow and display results.
    keyword_df = extractor.run()
    print(keyword_df)