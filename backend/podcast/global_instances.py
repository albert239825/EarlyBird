from backend.podcast.ml.inference.rl_bandit import HybridLinUCBModel
from backend.podcast.generate_graph_nodes import InterestGraph
from backend.podcast.ml.retrieval.merger import Merger

url = "backend/podcast/ml/retrieval/db/"
merger = Merger(db_path = url)
articles = merger.merge()
rl_model = HybridLinUCBModel(articles)
graph = InterestGraph(rl_model)