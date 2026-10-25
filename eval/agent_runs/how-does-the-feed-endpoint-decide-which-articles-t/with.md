# with get_context: how does the feed endpoint decide which articles to return

`GET /api/feed` picks articles with a plain database query on two inputs, `domain` and `limit`. It does no personalization or ranking beyond recency.

- **Inputs:** `get_feed` takes an optional `domain` and a `limit` that defaults to 20 and must be between 1 and 100 (`app/api/feed.py:92-95`).
- **Validation:** an unknown `domain` returns a 400 (`app/api/feed.py:97-98`).
- **With a domain:** `crud.get_articles_by_domain` filters `Article.domain == domain`, orders by `fetched_at` descending, and applies the limit (`app/api/feed.py:100-101`, `app/db/crud.py:91-98`).
- **Without a domain:** `crud.get_all_recent_articles` returns the newest articles across all domains, again ordered by `fetched_at` descending with the limit (`app/api/feed.py:102-103`, `app/db/crud.py:101-102`).
- **Response:** each row is mapped to an `ArticleResponse`, with `tags` parsed from the stored JSON string. The result is wrapped in a `FeedResponse` with `total=len(articles)` (`app/api/feed.py:105-120`).

The feed doesn't use Qdrant, even though `app/db/qdrant.py` has `get_by_domain` and `get_all_recent` helpers. It also takes no user ID, so it doesn't filter out articles the user has already read.

What's in the table is decided earlier, when the pipeline inserts articles. `bulk_insert_articles` skips any article whose URL already exists (`app/db/crud.py:42-45`). Summaries are empty until someone opens the article (per CLAUDE.md), so feed items may show a blank `summary`.
