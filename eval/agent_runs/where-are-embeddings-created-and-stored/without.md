# without get_context: where are embeddings created and stored

In practice, embeddings are neither created nor stored. The code paths exist, but the embedder is a stub.

**Creation**
- `app/services/embedder.py:4-5`: `embed()` always returns `[]`. No model is loaded, and `warmup()` is a no-op (`embedder.py:8-9`).
- `app/pipeline/agents/base_agent.py:60`: each agent calls `embedder.embed(title + " " + content[:500])` and puts the result in `ArticleData.embedding`. That field is declared at `app/pipeline/state.py:18`.
- `app/config.py:21` still sets `embedding_model = "all-MiniLM-L6-v2"`, but nothing uses it.

**Intended storage (Qdrant)**
- `app/pipeline/aggregator.py:64-80`: it builds a `url_to_embedding` map from only the articles with a truthy embedding. It then calls `upsert_articles()`, defined at `app/db/qdrant.py:51-63`. Since every embedding is `[]`, the map is empty and nothing is upserted.
- `aggregator.py:29-31`: the semantic-dedup call `search_similar(..., threshold=0.85)` is gated on `if article.embedding:`, so it never runs.

**What is stored**
- SQL only stores a `qdrant_id` string (`app/db/models.py:26`, set at `app/db/crud.py:47`). It is generated for every article, whether or not a vector exists in Qdrant. No vector is saved in SQL.

This matches the CLAUDE.md description.
