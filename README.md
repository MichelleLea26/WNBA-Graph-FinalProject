# WNBA Knowledge Graph 

Proyek ini membangun knowledge graph WNBA di Neo4j dan melengkapinya dengan
pipeline AI: **Text-to-Cypher**, **Graph Analytics**, **Machine Learning pada
Graph (GDS)**, **LLM Graph Builder**, dan **RAG (Graph-Augmented Retrieval)**.

## Arsitektur

```text
dataset_WNBA.csv
      │
      ▼
 load_data.py  ──────────────►  Neo4j Lokal (Player, Team, College, Position)
                                        │
        ┌───────────────┬──────────────┼───────────────────┐
        ▼               ▼              ▼                   ▼
 text_to_cypher.py  graph_ml.py   graph_builder.py       rag.py
 (Groq LLM → Cypher) (GDS FastRP + (Groq → entitas/    (subgraph retrieval
                     KMeans +      relasi → Neo4j)        + Groq generation)
                     RandomForest)
```

**Skema graph:**

```
(:Player {name, height, draftYear})
(:Team {name})
(:College {name})
(:Position {name})

(Player)-[:PLAYS_FOR]->(Team)
(Player)-[:EDUCATED_AT]->(College)
(Player)-[:PLAYS_POSITION]->(Position)
```

4 jenis entitas, 934 node keseluruhan (763 pemain, 20 tim, 143 universitas, 9 posisi) dan >4000 relasi 


## Cara Menjalankan

```bash
# Muat dataset ke Neo4j (sekali saja di awal)
python src/load_data.py

# Jalankan masing-masing komponen secara terpisah 
python src/db.py                # cek koneksi DB
python src/text_to_cypher.py    # demo Text-to-Cypher
python src/graph_ml.py          # demo ML on Graph (embedding + clustering + classification)
python src/graph_builder.py     # demo LLM Graph Builder
python src/rag.py               # demo RAG

# Atau jalankan semuanya secara terintegrasi via notebook:
jupyter notebook notebooks/main.ipynb
```





