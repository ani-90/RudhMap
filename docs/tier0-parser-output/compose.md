# `parse_compose` output reference

Extractor: [`src/rudhmap/extract/tier0_iac/compose.py`](../../src/rudhmap/extract/tier0_iac/compose.py)

---

## Fixture: `tests/fixtures/compose/docker-compose.yml`

### Source

```yaml
services:
  api:
    image: myorg/api:latest
    depends_on:
      - db
      - cache

  db:
    image: postgres:16

  cache:
    image: redis:7

  worker:
    build: ./worker
```

### Output

```json
{
  "nodes": [
    {
      "kind": "service",
      "identity": "compose:api",
      "file": "tests\\fixtures\\compose\\docker-compose.yml",
      "line": 2,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "image": "myorg/api:latest" }
    },
    {
      "kind": "datastore",
      "identity": "compose:db",
      "file": "tests\\fixtures\\compose\\docker-compose.yml",
      "line": 8,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "image": "postgres:16" }
    },
    {
      "kind": "datastore",
      "identity": "compose:cache",
      "file": "tests\\fixtures\\compose\\docker-compose.yml",
      "line": 11,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "image": "redis:7" }
    },
    {
      "kind": "service",
      "identity": "compose:worker",
      "file": "tests\\fixtures\\compose\\docker-compose.yml",
      "line": 14,
      "tier": 0,
      "confidence": 1.0,
      "attrs": {}
    }
  ],
  "edges": [
    {
      "src": "compose:api",
      "dst": "compose:db",
      "file": "tests\\fixtures\\compose\\docker-compose.yml",
      "line": 2,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "relation": "depends_on" }
    },
    {
      "src": "compose:api",
      "dst": "compose:cache",
      "file": "tests\\fixtures\\compose\\docker-compose.yml",
      "line": 2,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "relation": "depends_on" }
    }
  ]
}
```

`worker` has no `image`, only `build`, so `_kind_for_image(None)` falls
back to `"service"` and `attrs` is empty (no `image` key added).

---

## Fixture: `tests/fixtures/compose_extended/docker-compose.yml`

### Source

```yaml
services:
  web:
    image: nginx:1.25
    depends_on:
      api:
        condition: service_healthy

  api:
    image: myorg/api:latest
    depends_on:
      - queue
      - search-index

  queue:
    image: RABBITMQ:3-management

  search-index:
    image: opensearchproject/opensearch:2

  scratch:
    build: ./scratch
```

This fixture exercises: the long-form (dict) `depends_on:` syntax, a
short-form list `depends_on:`, case-insensitive image-name matching
(`RABBITMQ` uppercase still matches the `rabbitmq` needle), a substring
match against `opensearch`, and a dashed service name.

### Output

```json
{
  "nodes": [
    {
      "kind": "gateway",
      "identity": "compose:web",
      "file": "tests\\fixtures\\compose_extended\\docker-compose.yml",
      "line": 2,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "image": "nginx:1.25" }
    },
    {
      "kind": "service",
      "identity": "compose:api",
      "file": "tests\\fixtures\\compose_extended\\docker-compose.yml",
      "line": 5,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "image": "myorg/api:latest" }
    },
    {
      "kind": "queue",
      "identity": "compose:queue",
      "file": "tests\\fixtures\\compose_extended\\docker-compose.yml",
      "line": 14,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "image": "RABBITMQ:3-management" }
    },
    {
      "kind": "datastore",
      "identity": "compose:search-index",
      "file": "tests\\fixtures\\compose_extended\\docker-compose.yml",
      "line": 17,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "image": "opensearchproject/opensearch:2" }
    },
    {
      "kind": "service",
      "identity": "compose:scratch",
      "file": "tests\\fixtures\\compose_extended\\docker-compose.yml",
      "line": 20,
      "tier": 0,
      "confidence": 1.0,
      "attrs": {}
    }
  ],
  "edges": [
    {
      "src": "compose:web",
      "dst": "compose:api",
      "file": "tests\\fixtures\\compose_extended\\docker-compose.yml",
      "line": 2,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "relation": "depends_on" }
    },
    {
      "src": "compose:api",
      "dst": "compose:queue",
      "file": "tests\\fixtures\\compose_extended\\docker-compose.yml",
      "line": 5,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "relation": "depends_on" }
    },
    {
      "src": "compose:api",
      "dst": "compose:search-index",
      "file": "tests\\fixtures\\compose_extended\\docker-compose.yml",
      "line": 5,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "relation": "depends_on" }
    }
  ]
}
```

`web`'s `depends_on` uses `{api: {condition: service_healthy}}` — a dict,
not a list. `_normalize_depends_on` resolves this via `list(value.keys())`,
so it still produces a `compose:web -> compose:api` edge identical in shape
to a list-form dependency.
