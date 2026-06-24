"""
rag.py
"""

import os
from groq import Groq
from dotenv import load_dotenv
from db import get_connection

load_dotenv()

# Inisialisasi client Groq menggunakan API key dari .env
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

ENTITY_SEARCH_QUERY = """
MATCH (n)
WHERE (n:Player OR n:Team OR n:College OR n:Position)
  AND toLower(n.name) CONTAINS toLower($term)
RETURN labels(n)[0] AS label, n.name AS name
LIMIT 5
"""

SUBGRAPH_QUERY = """
MATCH (start {name: $name})
MATCH path = (start)-[*1..2]-(neighbor)
RETURN start.name AS start,
       [r IN relationships(path) | type(r)] AS rel_types,
       neighbor.name AS neighbor,
       labels(neighbor)[0] AS neighbor_label
LIMIT 40
"""

def _extract_candidate_terms(question: str) -> list[str]:
    """Heuristik sederhana: ambil kata berkapital ganda / frasa panjang sebagai
    kandidat nama entitas yang mungkin disebut di pertanyaan."""
    words = question.replace("?", "").split()
    candidates = []
    buffer = []
    for w in words:
        if w[:1].isupper():
            buffer.append(w)
        else:
            if len(buffer) >= 1:
                candidates.append(" ".join(buffer))
            buffer = []
    if buffer:
        candidates.append(" ".join(buffer))
    return candidates or [question]


def retrieve_subgraph_context(question: str, max_entities: int = 3) -> str:
    """Cari entitas yang relevan dari pertanyaan, lalu ambil subgraph 2-hop."""
    conn = get_connection()
    context_lines = []
    try:
        candidates = _extract_candidate_terms(question)
        matched_names = set()

        for term in candidates:
            matches = conn.run(ENTITY_SEARCH_QUERY, {"term": term})
            for m in matches:
                matched_names.add(m["name"])
            if len(matched_names) >= max_entities:
                break

        for name in list(matched_names)[:max_entities]:
            rows = conn.run(SUBGRAPH_QUERY, {"name": name})
            for r in rows:
                rel_chain = " -> ".join(r["rel_types"]) if r["rel_types"] else "terhubung"
                context_lines.append(
                    f"{r['start']} -[{rel_chain}]- {r['neighbor']} ({r['neighbor_label']})"
                )
    finally:
        conn.close()

    if not context_lines:
        return "(Tidak ditemukan entitas relevan di graph untuk pertanyaan ini.)"

    unique_lines = list(dict.fromkeys(context_lines))[:50]
    return "\n".join(unique_lines)


RAG_PROMPT_TEMPLATE = """Kamu adalah asisten yang menjawab pertanyaan tentang WNBA
berdasarkan konteks graph (Graph-Augmented Retrieval) di bawah ini. Jawab HANYA
berdasarkan konteks yang diberikan. Jika informasi tidak cukup, katakan dengan jelas
bahwa data tidak tersedia di graph.

Konteks subgraph (format: entitas -[relasi]- entitas):
{context}

Pertanyaan: {question}

Jawaban (Bahasa Indonesia, ringkas dan jelas, sebutkan entitas relevan):
"""


def rag_answer(question: str) -> dict:
    """Pipeline RAG penuh: retrieval subgraph -> augmented generation via Groq."""
    context = retrieve_subgraph_context(question)
    prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=question)
    
    response = client.chat.completions.create(
        messages=[
            {"role": "user", "content": prompt}
        ],
        model=MODEL_NAME,
        temperature=0.3 
    )
    
    return {"question": question, "context": context, "answer": response.choices[0].message.content.strip()}


if __name__ == "__main__":
    contoh = [
        "Apa hubungan antara Paige Bueckers dan Dallas Wings?",
        "Universitas mana saja yang memiliki hubungan (alumni) yang bermain di tim Dallas Wings?"
    ]
    
    print("Memulai proses Graph-Augmented Retrieval (RAG)...\n" + "="*70)
    for q in contoh:
        res = rag_answer(q)
        print("Pertanyaan:", res["question"])
        print("\n[Mengekstrak Konteks Subgraph dari Neo4j...]")
        print(res["context"])
        print("\nJawaban AI (Groq):")
        print(res["answer"])
        print("=" * 70)
