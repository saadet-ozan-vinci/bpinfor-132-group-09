"""The index and the two retrievers.

Chroma is a black box here, exactly as the syllabus asks. You put vectors in
with metadata and you get ranked ids out. What is worth your attention is
what you put in and how you score what comes back.

Two retrievers, because block 2 compares them:

  dense     embeddings, cosine similarity. Good at meaning, indifferent to
            exact strings.
  keyword   term overlap. The reverse. Deliberately crude, so it is obvious
            what it is doing.
"""

from __future__ import annotations
import chromadb
import json
import re
import urllib.request

from .chunking import Chunk

from project.models import EMBED, OLLAMA_URL

EMBED_MODEL = EMBED.name


def embed(texts: list[str], batch: int = 32) -> list[list[float]]:
    """Embed a list of texts in batches.

    One call per chunk is the obvious version and it is roughly thirty times
    slower on this corpus. The endpoint takes a list, so give it one.

    POST to f"{OLLAMA_URL}/api/embed" with a JSON body of
    {"model": EMBED_MODEL, "input": [...]} and read the "embeddings" key.
    """
    if batch <= 0:
        raise ValueError("batch must be positive")
    if not texts:
        return []

    vectors: list[list[float]] = []
    dimension: int | None = None
    for start in range(0, len(texts), batch):
        body = json.dumps({
            "model": EMBED_MODEL,
            "input": texts[start:start + batch],
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{OLLAMA_URL}/api/embed",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=180) as response:
            payload = json.loads(response.read())

        batch_vectors = payload["embeddings"]
        expected_count = min(batch, len(texts) - start)
        if len(batch_vectors) != expected_count:
            raise ValueError(
                f"embedding endpoint returned {len(batch_vectors)} vectors "
                f"for {expected_count} inputs"
            )
        for vector in batch_vectors:
            if not vector:
                raise ValueError("embedding endpoint returned an empty vector")
            if dimension is None:
                dimension = len(vector)
            elif len(vector) != dimension:
                raise ValueError("embedding endpoint returned inconsistent dimensions")
            vectors.append(vector)
    return vectors


class DenseIndex:
    """Build once per configuration, then query it."""

    def __init__(self, chunks: list[Chunk], name: str = "run_a"):
        """Build the index.

        chromadb.EphemeralClient(), then get_or_create_collection(name),
        then add() with ids, embeddings, and metadatas carrying doc_id and
        section.

        Give the collection a NAME that encodes the configuration. Two
        chunkings have to be able to coexist during the block 3 sweep, and
        rebuilding without deleting is the classic way to end up with two
        chunkings in one index and numbers nobody can explain.

        Keep a dict from chunk_id to Chunk, because search has to map the
        ids Chroma returns back to objects. Set self.dim so the brief's
        conditions line has something to record.
        """
        if not chunks:
            raise ValueError("cannot build a dense index without chunks")


        self.chunks = {chunk.chunk_id: chunk for chunk in chunks}
        self.client = chromadb.EphemeralClient()
        self.collection = self.client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

        ids = [chunk.chunk_id for chunk in chunks]
        embeddings = embed([chunk.text for chunk in chunks])
        self.dim = len(embeddings[0])
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=[
                {"doc_id": chunk.doc_id, "section": chunk.section}
                for chunk in chunks
            ],
        )

    def search(self, query: str, k: int = 20) -> list[Chunk]:
        """Embed the query, ask the collection, map ids back to Chunks."""
        if k < 0:
            raise ValueError("k must be non-negative")
        if k == 0:
            return []

        query_embedding = embed([query])[0]
        if len(query_embedding) != self.dim:
            raise ValueError(
                f"query embedding has dimension {len(query_embedding)}, "
                f"expected {self.dim}"
            )
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(k, len(self.chunks)),
        )
        ids = result["ids"][0]
        try:
            return [self.chunks[chunk_id] for chunk_id in ids]
        except KeyError as exc:
            raise ValueError(
                f"Chroma returned unknown chunk id: {exc.args[0]}"
            ) from exc


def keyword_search(chunks: list[Chunk], query: str,
                   k: int = 20) -> list[Chunk]:
    """Term overlap. No model, no cost.

    Score each chunk by how many query terms appear in it, return the top k.
    Crude on purpose: in block 2 you will see a document that repeats a term
    in the wrong section outrank the section that answers the question.

    Break ties deterministically, by chunk_id, or two runs of your own code
    will disagree and you will spend ten minutes blaming the embedder.
    """
    if k < 0:
        raise ValueError("k must be non-negative")
    if k == 0:
        return []

    terms = {
        term.lower() for term in re.findall(r"[\w-]+", query)
        if len(term) > 2
    }
    if not terms:
        return []

    scored = []
    for chunk in chunks:
        words = {word.lower() for word in re.findall(r"[\w-]+", chunk.text)}
        overlap = len(terms & words)
        if overlap:
            scored.append((overlap, chunk.chunk_id, chunk))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [chunk for _, _, chunk in scored[:k]]
