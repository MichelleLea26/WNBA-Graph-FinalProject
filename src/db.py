"""
db.py
Modul koneksi ke Neo4j. Dipakai oleh semua modul lain (text_to_cypher,
graph_builder, graph_ml, rag) supaya koneksi konsisten dan reusable.
"""

import os
from typing import Optional  # Tambahkan modul ini untuk mengganti fungsi '|'
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


class Neo4jConnection:
    """Wrapper sederhana di atas neo4j driver resmi."""

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
        """Untuk screenshot (a): bukti koneksi DB berhasil."""
        self._driver.verify_connectivity()
        return True

    # Perubahan di sini: Mengganti dict | None menjadi Optional[dict]
    def run(self, query: str, parameters: Optional[dict] = None):
        """Jalankan satu query Cypher dan kembalikan list of dict."""
        with self._driver.session(database=self._database) as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    # Perubahan di sini juga
    def write(self, query: str, parameters: Optional[dict] = None):
        """Jalankan write-transaction (untuk Graph Builder / load data)."""
        with self._driver.session(database=self._database) as session:
            return session.execute_write(
                lambda tx: list(tx.run(query, parameters or {}))
            )


def get_connection() -> Neo4jConnection:
    return Neo4jConnection()


if __name__ == "__main__":
    # Contoh: python src/db.py  -> dipakai untuk screenshot koneksi DB
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