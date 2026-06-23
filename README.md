# WNBA Knowledge Graph — Neo4j + GDS + LLM (Gemini)

Proyek ini membangun knowledge graph WNBA di Neo4j dan melengkapinya dengan
pipeline AI: **Text-to-Cypher**, **Graph Analytics**, **Machine Learning pada
Graph (GDS)**, **LLM Graph Builder**, dan **RAG (Graph-Augmented Retrieval)** —
memenuhi seluruh komponen wajib **Tier 4**.

## 1. Arsitektur

```
dataset_WNBA.csv
      │
      ▼
 load_data.py  ──────────────►  Neo4j (Player, Team, College, Position)
                                        │
        ┌───────────────┬──────────────┼───────────────────┐
        ▼               ▼              ▼                   ▼
 text_to_cypher.py  graph_ml.py   graph_builder.py       rag.py
 (Gemini → Cypher)  (GDS FastRP + (Gemini → entitas/    (subgraph retrieval
                     KMeans +      relasi → Neo4j)        + Gemini generation)
                     RandomForest)
```

**Skema graph:**

```
(:Player {name, height, draftYear})
(:Team {name})
(:College {name})
(:Position {name})

(Player)-[:PLAYS_FOR]->(Team)
(Player)-[:ATTENDED]->(College)
(Player)-[:PLAYS_POSITION]->(Position)
```

4 jenis entitas, 763 pemain, 20 tim, 143 universitas, 9 posisi → jauh di atas
syarat minimum (3 entitas, 50 node).

## 2. Instalasi

```bash
# 1. Clone repo
git clone <url-repo-kamu>
cd wnba-graph-project

# 2. Buat virtual environment (opsional tapi disarankan)
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Siapkan Neo4j
#    - Neo4j Desktop / AuraDB / Docker, versi 5.x, dengan plugin GDS aktif
#    - Docker contoh:
#      docker run -p7474:7474 -p7687:7687 \
#        -e NEO4J_AUTH=neo4j/yourpassword \
#        -e NEO4JLABS_PLUGINS='["graph-data-science"]' \
#        neo4j:5

# 5. Konfigurasi kredensial
cp .env.example .env
# isi NEO4J_PASSWORD dan GEMINI_API_KEY di file .env
```

## 3. Cara Menjalankan

```bash
# Muat dataset ke Neo4j (sekali saja di awal)
python src/load_data.py

# Jalankan masing-masing komponen secara terpisah (opsional, untuk testing cepat)
python src/db.py                # cek koneksi DB
python src/text_to_cypher.py    # demo Text-to-Cypher
python src/graph_ml.py          # demo ML on Graph (embedding + clustering + classification)
python src/graph_builder.py     # demo LLM Graph Builder
python src/rag.py               # demo RAG

# Atau jalankan semuanya secara terintegrasi via notebook:
jupyter notebook notebooks/main.ipynb
```

## 4. Penjelasan Logika Cypher & Pipeline AI

- **Load data (`load_data.py`)** — menggunakan `MERGE` (idempotent) supaya
  bisa dijalankan ulang tanpa duplikasi node, dengan constraint unique pada
  `name` setiap label.
- **Text-to-Cypher (`text_to_cypher.py`)** — skema graph dikirim sebagai
  *system instruction* ke Gemini supaya query yang dihasilkan valid terhadap
  skema nyata. Query hasil LLM divalidasi agar **read-only** (menolak
  `CREATE/DELETE/SET/MERGE`) sebelum dieksekusi, lalu hasilnya dikirim balik
  ke Gemini untuk dirangkai jadi jawaban natural language.
- **Graph Analytics** — traversal & path finding pakai pattern matching
  Cypher biasa; centrality & community detection menggunakan algoritma GDS
  (sudah dikerjakan pada tahap sebelumnya — lihat bagian referensi di
  notebook).
- **ML on Graph (`graph_ml.py`)** — membuat *in-memory graph projection* di
  GDS, menghasilkan **FastRP embedding** per node Player, lalu:
  - **Clustering**: K-Means di atas embedding untuk mengelompokkan pemain
    yang punya posisi struktural mirip di graph.
  - **Classification**: Random Forest memprediksi `Position` pemain dari
    embedding graph + tinggi badan (node classification).
- **LLM Graph Builder (`graph_builder.py`)** — Gemini diberi *prompt*
  terstruktur untuk mengekstrak entitas & relasi dari teks bebas (mis. bio
  pemain) dalam format JSON, lalu hasilnya ditulis ke Neo4j lewat `MERGE`
  dinamis per label/tipe relasi (anti-duplikasi, tanpa perlu APOC).
- **RAG (`rag.py`)** — alih-alih menjawab langsung, sistem dulu mengambil
  *subgraph* 2-hop di sekitar entitas yang disebut di pertanyaan (entity
  linking sederhana via `CONTAINS`), merangkainya jadi teks konteks, lalu
  menyuntikkannya ke prompt Gemini supaya jawaban **grounded** pada data
  graph aktual (mengurangi halusinasi LLM).

## 5. Struktur Folder

```
wnba-graph-project/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── data/
│   └── dataset_WNBA.csv
├── src/
│   ├── db.py                # koneksi Neo4j
│   ├── load_data.py         # load CSV -> graph
│   ├── text_to_cypher.py    # Tier 1: LLM Text-to-Cypher
│   ├── graph_ml.py          # Tier 2: ML on Graph (GDS)
│   ├── graph_builder.py     # Tier 3: LLM Graph Builder
│   └── rag.py               # Tier 4: RAG
├── notebooks/
│   └── main.ipynb           # demo terintegrasi semua komponen
└── screenshots/             # taruh 4 screenshot wajib di sini
```

## 6. Screenshot Wajib (taruh di folder `screenshots/`)

1. `01_koneksi_db.png` — output `python src/db.py` / cell koneksi di notebook
2. `02_query_graph_builder.png` — hasil query Cypher / output `graph_builder.py`
3. `03_analisis_ml.png` — output centrality/community detection + classification report dari `graph_ml.py`
4. `04_demo_llm.png` — output `text_to_cypher.py` dan/atau `rag.py` (pertanyaan → Cypher/jawaban)

## 7. Catatan

- Dataset bersumber dari Wikidata (763 pemain WNBA, kolom: player, team,
  college, position, height, draftYear).
- LLM yang digunakan: **Google Gemini** (`gemini-2.0-flash`), via
  `google-generativeai` SDK. API key disimpan di `.env`, **tidak** di-hardcode.
- Bagian Graph Analytics (centrality, dll.) merujuk pada hasil yang sudah
  dikerjakan sebelum proyek ini disusun ulang ke struktur final — pastikan
  query Cypher yang sebelumnya kamu jalankan ikut disalin ke
  `notebooks/main.ipynb` bagian 3, agar dokumentasi lengkap dalam satu file.
