"""
text_to_cypher.py
Komponen LLM untuk Text-to-Cypher menggunakan Groq.
"""

import os
import re
from groq import Groq
from dotenv import load_dotenv
from db import get_connection

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL_NAME = "llama-3.1-8b-instant"

GRAPH_SCHEMA = """
Node labels dan properti:
  (:Player {name: string, height: float, draftYear: int, position: string})
  (:Team {name: string})
  (:College {name: string})

Relationship types:
  (Player)-[:PLAYS_FOR]->(Team)
  (Player)-[:EDUCATED_AT]->(College)
"""

CYPHER_SYSTEM_PROMPT = f"""Kamu adalah asisten yang mengubah pertanyaan natural language
menjadi query Cypher untuk database Neo4j dengan skema berikut:

{GRAPH_SCHEMA}

Aturan:
- Hanya kembalikan satu query Cypher yang valid, tanpa penjelasan tambahan.
- Gunakan MATCH/WHERE/RETURN yang sesuai skema di atas.
- Jika pertanyaan butuh agregasi (jumlah, rata-rata, dll) gunakan fungsi Cypher.
- Batasi hasil dengan LIMIT 25 kecuali user minta jumlah lain secara eksplisit.
- Jangan menghasilkan query yang mengubah data (CREATE/DELETE/SET/MERGE dilarang).
- Gunakan ALIAS (AS) pada RETURN agar hasil JSON mudah dibaca (contoh: RETURN p.name AS Nama, p.height AS Tinggi).
- Jika mengurutkan data angka (seperti tinggi badan), pastikan memfilter nilai kosong dengan menambah WHERE properti IS NOT NULL.
"""

def _clean_cypher(text: str) -> str:
    """Bersihkan teks dari markdown."""
    text = text.strip()
    text = re.sub(r"^```(cypher)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()
    return text

def natural_language_to_cypher(question: str) -> str:
    """Panggil Groq untuk generate Cypher."""
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": CYPHER_SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ],
        model=MODEL_NAME,
        temperature=0.0
    )
    return _clean_cypher(response.choices[0].message.content)

def _is_read_only(cypher: str) -> bool:
    forbidden = ["CREATE", "DELETE", "SET", "MERGE", "REMOVE", "DROP", "DETACH"]
    upper = cypher.upper()
    return not any(kw in upper for kw in forbidden)

def ask(question: str, explain: bool = True) -> dict:
    cypher = natural_language_to_cypher(question)

    if not _is_read_only(cypher):
        return {"question": question, "cypher": cypher, "rows": [], "answer": "Query diblokir demi keamanan."}

    conn = get_connection()
    try:
        rows = conn.run(cypher)
    finally:
        conn.close()

    answer = None
    if explain:
        prompt = (
            f"Pertanyaan user: {question}\n"
            f"Hasil query (JSON): {rows}\n\n"
            "Jawab pertanyaan user dalam 1-3 kalimat dalam Bahasa Indonesia yang natural. "
            "Jika hasil kosong ([]), katakan datanya tidak ditemukan."
        )
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=MODEL_NAME,
            temperature=0.3
        )
        answer = response.choices[0].message.content.strip()

    return {"question": question, "cypher": cypher, "rows": rows, "answer": answer}

if __name__ == "__main__":
    contoh_pertanyaan = [
        "Berapa jumlah pemain di tim Las Vegas Aces?",
        "Sebutkan 5 pemain dengan tinggi badan tertinggi beserta universitasnya",
        "Universitas mana yang paling banyak menghasilkan pemain?",
    ]
    for q in contoh_pertanyaan:
        result = ask(q)
        print("Pertanyaan :", result["question"])
        print("Cypher     :", result["cypher"])
        print("Jawaban    :", result["answer"])
        print("-" * 60)
