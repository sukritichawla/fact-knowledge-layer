import sqlite3
from pathlib import Path
from .models import KnowledgeLayer, DocumentRecord, Fact, Relationship
DB_PATH=Path("data/facts.db")

def connect():
    DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    with connect() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY,payload TEXT NOT NULL); CREATE TABLE IF NOT EXISTS facts (id TEXT PRIMARY KEY,document_id TEXT NOT NULL,payload TEXT NOT NULL); CREATE TABLE IF NOT EXISTS relationships (id TEXT PRIMARY KEY,payload TEXT NOT NULL);''')

def upsert_document(doc):
    with connect() as c: c.execute("INSERT OR REPLACE INTO documents VALUES (?,?)",(doc.id,doc.model_dump_json()))

def upsert_facts(facts):
    with connect() as c: c.executemany("INSERT OR REPLACE INTO facts VALUES (?,?,?)",[(f.id,f.evidence.document_id,f.model_dump_json()) for f in facts])

def upsert_relationships(rels):
    with connect() as c: c.executemany("INSERT OR REPLACE INTO relationships VALUES (?,?)",[(r.id,r.model_dump_json()) for r in rels])

def load_layer():
    init_db()
    with connect() as c:
        docs=[DocumentRecord.model_validate_json(x[0]) for x in c.execute("SELECT payload FROM documents ORDER BY rowid")]
        facts=[Fact.model_validate_json(x[0]) for x in c.execute("SELECT payload FROM facts ORDER BY rowid")]
        rels=[Relationship.model_validate_json(x[0]) for x in c.execute("SELECT payload FROM relationships ORDER BY rowid")]
    return KnowledgeLayer(documents=docs,facts=facts,relationships=rels)

def document_exists(doc_id):
    init_db()
    with connect() as c: return c.execute("SELECT 1 FROM documents WHERE id=?",(doc_id,)).fetchone() is not None
