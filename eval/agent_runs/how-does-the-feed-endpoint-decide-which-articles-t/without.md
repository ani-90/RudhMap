# without get_context: how does the feed endpoint decide which articles to return

`GET /api/feed` returns the newest stored articles, optionally filtered by domain. It does no personalization, ranking or retrieval.

- **Parameters:** the endpoint takes an optional `domain` and a `limit`. `limit` defaults to 20 and must be between 1 and 100 (`app/api/feed.py:91-96`).
- **Validation:** a `domain` that isn't in `DOMAINS` gets a 400 (`feed.py:97-98`).
- **With a domain:** it calls `crud.get_articles_by_domain` (`feed.py:100-101`). That filters `Article.domain == domain`, orders by `fetched_at` descending, and applies the limit (`app/db/crud.py:91-98`).
- **Without a domain:** it calls `crud.get_all_recent_articles` (`feed.py:102-103`). That orders all articles by `fetched_at` descending and applies the limit (`crud.py:101-102`).
- **Response:** each row is mapped to an `ArticleResponse`, with `tags` parsed from JSON (`feed.py:105-118`). The result is wrapped in a `FeedResponse` with `total=len(articles)` (`feed.py:120`).

- **No per-user filtering:** there is no `user_id` parameter, so read articles aren't excluded.
- **Summaries can be empty:** the pipeline leaves summaries empty and fills them lazily. Feed items can therefore come back with a blank `summary`.
- **Dedup happens earlier:** exact-URL dedup is done at insert time in the aggregator, not when the feed is read.
