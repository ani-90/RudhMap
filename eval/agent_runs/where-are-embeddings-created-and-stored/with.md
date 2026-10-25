# with get_context: where are embeddings created and stored

Embeddings are called in one place and stored nowhere, because the embedder is a stub that returns nothing.

**Created**
- `app/pipeline/agents/base_agent.py:60` is the only call site. `BaseAgent.run` calls `embedder.embed(item["title"] + " " + content[:500])` for each article that passes the quality filter.
- `app/services/embedder.py:4-5` defines `embed()`, which just does `return []`. No model is loaded.
- The result goes into `ArticleData.embedding` (`app/pipeline/agents/base_agent.py:72`). The field is `Optional[List[float]]` (`app/pipeline/state.py:15`). It is always an empty list in practice.

**Stored**
- **Qdrant:** `app/db/qdrant.py` has `upsert_articles()` and `search_similar()`. According to CLAUDE.md, the aggregator only upserts when `article.embedding` is truthy. An empty list is falsy, so nothing is ever written to Qdrant. I didn't open `aggregator.py` or `qdrant.py` to check that gate. The context pack didn't include them.
- **SQL database:** the embedding vector isn't persisted there. The SQL `articles` table only keeps a `qdrant_id` reference (exposed at `app/api/feed.py:~154`). CLAUDE.md says that ID is generated for every article even though no Qdrant point exists.

If embeddings are re-enabled, `embed()` is the only function you'd need to implement.
