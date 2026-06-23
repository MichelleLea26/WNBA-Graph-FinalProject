"""
graph_builder.py
Komponen "LLM for Graph Builder" menggunakan Groq API.
"""

import os
import json
from groq import Groq
from dotenv import load_dotenv
from db import get_connection

load_dotenv()

# Inisialisasi Client Groq
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
# Menggunakan model Llama-3, sangat cepat dan cerdas untuk ekstraksi
MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

EXTRACTION_SYSTEM_PROMPT = """Kamu adalah sistem ekstraksi entitas & relasi untuk membangun
knowledge graph tentang pemain basket WNBA.

Dari teks yang diberikan, ekstrak entitas dan relasi dalam format JSON murni (tanpa markdown
fences, tanpa penjelasan tambahan) dengan struktur:

{
  "entities": [
    {"type": "Player", "name": "..."},
    {"type": "Team", "name": "..."},
    {"type": "College", "name": "..."},
    {"type": "Award", "name": "..."},
    {"type": "Event", "name": "..."}
  ],
  "relations": [
    {"source": "...", "type": "PLAYS_FOR", "target": "..."},
    {"source": "...", "type": "ATTENDED", "target": "..."},
    {"source": "...", "type": "WON", "target": "..."},
    {"source": "...", "type": "PARTICIPATED_IN", "target": "..."}
  ]
}

Aturan:
- Hanya keluarkan JSON murni, jangan sertakan penjelasan, kata-kata pembuka, atau markdown blocks.
"""

def extract_graph_from_text(text: str) -> dict:
    """Panggil Groq API untuk ekstraksi entitas & relasi."""
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ],
        model=MODEL_NAME,
        temperature=0.1, # Rendah agar hasilnya konsisten/deterministik
    )
    
    raw = chat_completion.choices[0].message.content.strip()
    # Bersihkan jika LLM masih menyelipkan markdown
    raw = raw.replace("```json", "").replace("```", "").strip()
    
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Groq tidak mengembalikan JSON valid:\n{raw}") from e

# Fungsi _simple_upsert_relation dan _simple_upsert_entity tetap sama seperti sebelumnya
def _simple_upsert_relation(conn, source: str, rel_type: str, target: str):
    safe_rel = "".join(ch for ch in rel_type.upper() if ch.isalnum() or ch == "_")
    query = f"""
    MATCH (a {{name: $source}})
    MATCH (b {{name: $target}})
    MERGE (a)-[:{safe_rel}]->(b)
    """
    conn.write(query, {"source": source, "target": target})

def _simple_upsert_entity(conn, label: str, name: str):
    safe_label = "".join(ch for ch in label if ch.isalnum())
    query = f"MERGE (n:{safe_label} {{name: $name}})"
    conn.write(query, {"name": name})

def populate_graph(extracted: dict) -> dict:
    """Tulis hasil ekstraksi ke Neo4j."""
    conn = get_connection()
    created_entities, created_relations = 0, 0
    try:
        for ent in extracted.get("entities", []):
            _simple_upsert_entity(conn, ent["type"], ent["name"])
            created_entities += 1
        for rel in extracted.get("relations", []):
            _simple_upsert_relation(conn, rel["source"], rel["type"], rel["target"])
            created_relations += 1
    finally:
        conn.close()
    return {"entities_written": created_entities, "relations_written": created_relations}

def build_graph_from_text(text: str) -> dict:
    extracted = extract_graph_from_text(text)
    write_summary = populate_graph(extracted)
    return {"extracted": extracted, "write_summary": write_summary}

if __name__ == "__main__":
    contoh_teks = "A'ja Wilson bermain untuk Las Vegas Aces dan merupakan alumni dari University of South Carolina."
    result = build_graph_from_text(contoh_teks)
    print(json.dumps(result["extracted"], indent=2, ensure_ascii=False))