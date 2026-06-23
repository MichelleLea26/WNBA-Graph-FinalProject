"""
load_data.py
Memuat dataset_WNBA.csv ke Neo4j dengan skema graph:

    (:Player {name, height, draftYear})
    (:Team {name})
    (:College {name})
    (:Position {name})

    (Player)-[:PLAYS_FOR]->(Team)
    (Player)-[:ATTENDED]->(College)
    (Player)-[:PLAYS_POSITION]->(Position)

Skema ini memenuhi syarat "minimal 3 entitas berbeda" (Player, Team,
College, Position = 4 entitas) dengan >50 node dan relasi bermakna.

Jalankan sekali saja saat setup awal:
    python src/load_data.py
"""

import pandas as pd
from db import get_connection

CSV_PATH = "/Users/byg/Desktop/GRAF UAS WNBA/WNBA-Gaph-FinalProject/data/dataset_WNBA.csv"

CONSTRAINTS = [
    "CREATE CONSTRAINT player_name IF NOT EXISTS FOR (p:Player) REQUIRE p.name IS UNIQUE",
    "CREATE CONSTRAINT team_name IF NOT EXISTS FOR (t:Team) REQUIRE t.name IS UNIQUE",
    "CREATE CONSTRAINT college_name IF NOT EXISTS FOR (c:College) REQUIRE c.name IS UNIQUE",
    "CREATE CONSTRAINT position_name IF NOT EXISTS FOR (pos:Position) REQUIRE pos.name IS UNIQUE",
]

LOAD_QUERY = """
UNWIND $rows AS row
MERGE (p:Player {name: row.playerLabel})
  ON CREATE SET p.height = row.height, p.draftYear = row.draftYear

MERGE (t:Team {name: row.teamLabel})
MERGE (p)-[:PLAYS_FOR]->(t)

FOREACH (_ IN CASE WHEN row.collegeLabel IS NOT NULL THEN [1] ELSE [] END |
  MERGE (c:College {name: row.collegeLabel})
  MERGE (p)-[:ATTENDED]->(c)
)

FOREACH (_ IN CASE WHEN row.positionLabel IS NOT NULL THEN [1] ELSE [] END |
  MERGE (pos:Position {name: row.positionLabel})
  MERGE (p)-[:PLAYS_POSITION]->(pos)
)
"""


def load():
    df = pd.read_csv(CSV_PATH)
    df = df.where(pd.notnull(df), None)
    rows = df.to_dict("records")

    conn = get_connection()
    try:
        for stmt in CONSTRAINTS:
            conn.write(stmt)

        batch_size = 200
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            conn.write(LOAD_QUERY, {"rows": batch})
            print(f"  loaded {min(i + batch_size, len(rows))}/{len(rows)} baris")

        summary = conn.run(
            "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS jumlah ORDER BY jumlah DESC"
        )
        print("\nRingkasan node setelah load:")
        for row in summary:
            print(f"  {row['label']}: {row['jumlah']}")
    finally:
        conn.close()


if __name__ == "__main__":
    load()
