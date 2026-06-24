"""
db.py
Modul koneksi ke Neo4j. 
"""

import os
from typing import Optional  
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


class Neo4jConnection:
    

    def __init__(self, uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD,
                 database=NEO4J_DATABASE):
        if not password:
            raise ValueError(
                "NEO4J_PASSWORD belum diset. Salin .env.example -> .env lalu isi."
            )
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._database = database

    def close(self):
        self._driver.close()

    def verify_connectivity(self) -> bool:
        self._driver.verify_connectivity()
        return True

    def run(self, query: str, parameters: Optional[dict] = None):
        with self._driver.session(database=self._database) as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def write(self, query: str, parameters: Optional[dict] = None):
        with self._driver.session(database=self._database) as session:
            return session.execute_write(
                lambda tx: list(tx.run(query, parameters or {}))
            )


def get_connection() -> Neo4jConnection:
    return Neo4jConnection()


if __name__ == "__main__":
    conn = get_connection()
    ok = conn.verify_connectivity()
    print(f"Koneksi ke Neo4j berhasil: {ok}")
    counts = conn.run(
        "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS jumlah "
        "ORDER BY jumlah DESC"
    )
    for row in counts:
        print(row)
    conn.close()
