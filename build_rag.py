import os
import ollama
import chromadb
import pandas as pd
from pypdf import PdfReader
from docx import Document

# =========================
# Konfigurasi
# =========================
DATA_FOLDER = "./untuk rag" 
CHUNK_SIZE = 500
DB_PATH = "./chroma_db"

# Persistent database
client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_or_create_collection(name="geodata")


# =========================
# Fungsi Baca File
# =========================

def read_txt(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def read_md(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def read_pdf(path):
    reader = PdfReader(path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def read_csv(path):
    df = pd.read_csv(path)
    return df.to_string()

def read_excel(path):
    df = pd.read_excel(path)
    return df.to_string()

def read_docx(path):
    doc = Document(path)
    return "\n".join([para.text for para in doc.paragraphs])


def read_file(path):
    ext = path.lower().split(".")[-1]

    if ext == "txt":
        return read_txt(path)
    elif ext == "md":
        return read_md(path)
    elif ext == "pdf":
        return read_pdf(path)
    elif ext == "csv":
        return read_csv(path)
    elif ext in ["xlsx", "xls"]:
        return read_excel(path)
    elif ext == "docx":
        return read_docx(path)
    else:
        return ""


# =========================
# Chunking
# =========================

def chunk_text(text, size):
    return [text[i:i+size] for i in range(0, len(text), size)]


# =========================
# Reset Collection (opsional)
# =========================
print("Menghapus collection lama (jika ada)...")
client.delete_collection("geodata")
collection = client.get_or_create_collection(name="geodata")

# =========================
# Proses Embedding
# =========================

doc_id = 0

for filename in os.listdir(DATA_FOLDER):
    path = os.path.join(DATA_FOLDER, filename)

    print(f"Memproses: {filename}")
    content = read_file(path)

    if not content.strip():
        continue

    chunks = chunk_text(content, CHUNK_SIZE)

    for chunk in chunks:
        embedding = ollama.embeddings(
            model="nomic-embed-text",
            prompt=chunk
        )["embedding"]

        collection.add(
            ids=[str(doc_id)],
            embeddings=[embedding],
            documents=[chunk],
            metadatas=[{"source": filename}]
        )

        doc_id += 1

print("Semua file berhasil di-embedding dan disimpan permanen.")
