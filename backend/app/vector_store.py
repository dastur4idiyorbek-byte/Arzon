"""ChromaDB vektor bazasi — mahsulotlarni semantik qidirish uchun (phase 2.4).

Mahsulotlar embedding qilinadi; /chat endpointi mijoz savoliga mos
mahsulotlarni shu yerdan topib, Claude'ga kontekst sifatida beradi (RAG).

Chroma o'rnatilmagan bo'lsa ham backend ishlashda davom etadi — bu holda
qidiruv bo'sh natija qaytaradi (ixtiyoriy bog'liqlik).
"""
from __future__ import annotations

from typing import List

from .config import settings

_client = None
_collection = None
_available = False

try:  # Chroma ixtiyoriy — o'rnatilmagan bo'lsa backend baribir ishlaydi.
    import chromadb

    _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    _collection = _client.get_or_create_collection(
        name="arzon_products", metadata={"hnsw:space": "cosine"}
    )
    _available = True
except Exception:  # noqa: BLE001
    _available = False


def is_available() -> bool:
    return _available


def _doc_text(nomi: str, tavsif: str | None, rang: str | None) -> str:
    parts = [nomi]
    if tavsif:
        parts.append(tavsif)
    if rang:
        parts.append(f"rang: {rang}")
    return ". ".join(parts)


def index_product(
    product_id: int,
    store_id: int,
    nomi: str,
    tavsif: str | None = None,
    rang: str | None = None,
    korinish: str = "ommaviy",
) -> None:
    """Bitta mahsulotni indekslaydi (qo'shish/yangilash)."""
    if not _available:
        return
    _collection.upsert(
        ids=[str(product_id)],
        documents=[_doc_text(nomi, tavsif, rang)],
        metadatas=[
            {
                "product_id": product_id,
                "store_id": store_id,
                "korinish": korinish,
            }
        ],
    )


def remove_product(product_id: int) -> None:
    if not _available:
        return
    try:
        _collection.delete(ids=[str(product_id)])
    except Exception:  # noqa: BLE001
        pass


def search(query: str, store_ids: List[int], n: int = 5) -> List[dict]:
    """Mijoz ko'ra oladigan do'konlar ichidan semantik qidiruv.

    store_ids — mijozga ochiq bo'lgan do'konlar. Faqat ommaviy yoki ochilgan
    mahfiy mahsulotlar mos keladi.
    """
    if not _available or not store_ids:
        return []
    try:
        res = _collection.query(
            query_texts=[query],
            n_results=n,
            where={"store_id": {"$in": store_ids}},
        )
    except Exception:  # noqa: BLE001
        return []

    out: List[dict] = []
    ids = res.get("ids", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    docs = res.get("documents", [[]])[0]
    for i, _id in enumerate(ids):
        out.append({"document": docs[i], **metas[i]})
    return out
