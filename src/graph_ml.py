"""
graph_ml.py
"""

from graphdatascience import GraphDataScience
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "wnba") 

GRAPH_NAME = "wnbaGraph"

def get_gds() -> GraphDataScience:
    return GraphDataScience(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD), database=NEO4J_DATABASE)

def project_graph(gds: GraphDataScience):
    if gds.graph.exists(GRAPH_NAME)["exists"]:
        gds.graph.get(GRAPH_NAME).drop()

    graph, _ = gds.graph.project(
        GRAPH_NAME,
        ["Player", "Team", "College", "Position"],
        {
            "PLAYS_FOR": {"orientation": "UNDIRECTED"},
            "EDUCATED_AT": {"orientation": "UNDIRECTED"},
            "PLAYS_POSITION": {"orientation": "UNDIRECTED"},
        },
    )
    return graph

def run_node_embedding(gds: GraphDataScience, graph, dim: int = 32):
    gds.fastRP.mutate(
        graph,
        embeddingDimension=dim,
        mutateProperty="embedding",
        randomSeed=42,
    )
    gds.graph.nodeProperties.write(graph, ["embedding"], ["Player"])

def run_clustering(gds: GraphDataScience, n_clusters: int = 5) -> pd.DataFrame:
    df = gds.run_cypher(
        "MATCH (p:Player) WHERE p.embedding IS NOT NULL "
        "RETURN p.name AS name, p.embedding AS embedding"
    )
    
    embeddings = pd.DataFrame(df["embedding"].tolist())
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df["cluster"] = km.fit_predict(embeddings)

    gds.run_cypher(
        "UNWIND $rows AS row "
        "MATCH (p:Player {name: row.name}) "
        "SET p.playerCluster = row.cluster",
        params={"rows": df[["name", "cluster"]].to_dict("records")},
    )
    return df[["name", "cluster"]]

def run_position_classification(gds: GraphDataScience) -> str:
    df = gds.run_cypher(
        """
        MATCH (p:Player)-[:PLAYS_POSITION]->(pos:Position)
        WHERE p.embedding IS NOT NULL AND p.height IS NOT NULL
        RETURN p.name AS name, p.embedding AS embedding, p.height AS height,
               pos.name AS position
        """
    )

    if df.empty or df["position"].nunique() < 2:
        return "Data tidak cukup untuk klasifikasi."

    X = pd.DataFrame(df["embedding"].tolist())
    X["height"] = df["height"].values
    X.columns = X.columns.astype(str)
    y = df["position"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y if y.value_counts().min() > 1 else None
    )

    clf = RandomForestClassifier(n_estimators=200, random_state=42)
    clf.fit(X_train, y_train)
    preds = clf.predict(X_test)

    return classification_report(y_test, preds, zero_division=0)


if __name__ == "__main__":
    gds = get_gds()
    
    print(f"Memulai proyeksi graf ke dalam memori dari database '{NEO4J_DATABASE}'...")
    graph = project_graph(gds)
    print(f"Graph projection '{GRAPH_NAME}' dibuat: "
          f"{graph.node_count()} node, {graph.relationship_count()} relasi")

    print("\nMenjalankan FastRP Embedding...")
    run_node_embedding(gds, graph)
    print("FastRP embedding selesai & ditulis ke properti Player.embedding")

    print("\nMenjalankan K-Means Clustering...")
    clusters = run_clustering(gds, n_clusters=5)
    print("Contoh hasil clustering pemain:")
    print(clusters.head(10))

    print("\nMenjalankan Random Forest Classification...")
    report = run_position_classification(gds)
    print("Classification report (prediksi posisi pemain):")
    print(report)

    graph.drop()
    gds.close()
    print("\nProses Graph ML selesai dengan sukses!")
