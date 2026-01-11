from sentence_transformers import SentenceTransformer

class Embedor:
    def __init__(self, model_name='multi-qa-MiniLM-L6-cos-v1'):
        """
        Initialize the Embedor class with a SentenceTransformer model.
        :param model_name: Name of the model to load from sentence-transformers.
        """
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str):
        """
        Embed the given text using the model.
        :param text: The text to be embedded.
        :return: The vector representation of the text.
        """
        return self.model.encode(text).tolist()