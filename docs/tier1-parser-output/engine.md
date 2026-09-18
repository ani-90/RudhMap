# `parse_tier1_rules` output reference

Extractor: [`src/rudhmap/extract/tier1_rules/engine.py`](../../src/rudhmap/extract/tier1_rules/engine.py)
Rules: [`src/rudhmap/extract/tier1_rules/rules/aws.yaml`](../../src/rudhmap/extract/tier1_rules/rules/aws.yaml), [`databases.yaml`](../../src/rudhmap/extract/tier1_rules/rules/databases.yaml)

Read-only reference, not a test suite — `tests/` is untouched. This shows
the actual `EvidenceRecord` output for the fixture repo used in
`tests/test_tier1_engine.py`, so the shape of Tier 1's output is visible
without running anything.

**The one thing to notice throughout this page: `"edges": []`, always.**
Unlike Tier 0, Tier 1 never produces an `EdgeRecord`. See "Why no edges"
at the bottom.

---

## Fixture: `tests/fixtures/tier1_rules/`

Three source files, one per language the starter rule set covers, plus a
`.md` file that must never be scanned at all (wrong extension).

### `app.py`

```python
import boto3
import psycopg2
import redis

# boto3.client("sqs") -- old queue code, no longer used
s3 = boto3.client("s3")
bucket = s3.Bucket("raw-telemetry")

table = boto3.resource("dynamodb")

queue = boto3.client("sqs")

conn = psycopg2.connect("dbname=app user=admin")

cache = redis.Redis(host="localhost")
```

### `worker.js`

```javascript
// new SQSClient() setup used to live here, ripped out
const { S3Client } = require("@aws-sdk/client-s3");
const s3 = new S3Client({ region: "us-east-1" });

const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const ddb = new DynamoDBClient({});

/* multi-line comment
   new Redis() should not match inside here
*/
const pg = require("pg");
const Redis = require("ioredis");
const cache = new Redis();
```

### `main.go`

```go
package main

import (
	"database/sql"

	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/aws/aws-sdk-go-v2/service/sqs"
	"github.com/go-redis/redis/v8"
)

func main() {
	s3Client := s3.NewFromConfig(cfg)
	ddbClient := dynamodb.NewFromConfig(cfg)
	sqsClient := sqs.NewFromConfig(cfg)
	rdb := redis.NewClient(&redis.Options{})

	db, _ := sql.Open("postgres", "connstr")
	_ = db
}
```

### `notes.md` (not shown in output — see below)

```markdown
We use `boto3.client("s3")` and `redis.Redis()` in this service.
```

---

## Output

```json
{
  "nodes": [
    {
      "kind": "datastore",
      "identity": "aws-s3-client:tests\\fixtures\\tier1_rules\\app.py:6",
      "file": "tests\\fixtures\\tier1_rules\\app.py",
      "line": 6,
      "tier": 1,
      "confidence": 0.75,
      "subtype": "s3",
      "attrs": { "rule_id": "aws-s3-client" }
    },
    {
      "kind": "datastore",
      "identity": "aws-s3-bucket-name:raw-telemetry",
      "file": "tests\\fixtures\\tier1_rules\\app.py",
      "line": 7,
      "tier": 1,
      "confidence": 0.9,
      "subtype": "s3",
      "attrs": { "rule_id": "aws-s3-bucket-name", "bucket_name": "raw-telemetry" }
    },
    {
      "kind": "datastore",
      "identity": "aws-dynamodb-client:tests\\fixtures\\tier1_rules\\app.py:9",
      "file": "tests\\fixtures\\tier1_rules\\app.py",
      "line": 9,
      "tier": 1,
      "confidence": 0.75,
      "subtype": "dynamodb",
      "attrs": { "rule_id": "aws-dynamodb-client" }
    },
    {
      "kind": "queue",
      "identity": "aws-sqs-client:tests\\fixtures\\tier1_rules\\app.py:11",
      "file": "tests\\fixtures\\tier1_rules\\app.py",
      "line": 11,
      "tier": 1,
      "confidence": 0.75,
      "subtype": "sqs",
      "attrs": { "rule_id": "aws-sqs-client" }
    },
    {
      "kind": "datastore",
      "identity": "postgres-client:tests\\fixtures\\tier1_rules\\app.py:13",
      "file": "tests\\fixtures\\tier1_rules\\app.py",
      "line": 13,
      "tier": 1,
      "confidence": 0.75,
      "subtype": "postgres",
      "attrs": { "rule_id": "postgres-client" }
    },
    {
      "kind": "datastore",
      "identity": "redis-client:tests\\fixtures\\tier1_rules\\app.py:15",
      "file": "tests\\fixtures\\tier1_rules\\app.py",
      "line": 15,
      "tier": 1,
      "confidence": 0.75,
      "subtype": "redis",
      "attrs": { "rule_id": "redis-client" }
    },
    {
      "kind": "datastore",
      "identity": "aws-s3-client:tests\\fixtures\\tier1_rules\\main.go:13",
      "file": "tests\\fixtures\\tier1_rules\\main.go",
      "line": 13,
      "tier": 1,
      "confidence": 0.75,
      "subtype": "s3",
      "attrs": { "rule_id": "aws-s3-client" }
    },
    {
      "kind": "datastore",
      "identity": "aws-dynamodb-client:tests\\fixtures\\tier1_rules\\main.go:14",
      "file": "tests\\fixtures\\tier1_rules\\main.go",
      "line": 14,
      "tier": 1,
      "confidence": 0.75,
      "subtype": "dynamodb",
      "attrs": { "rule_id": "aws-dynamodb-client" }
    },
    {
      "kind": "queue",
      "identity": "aws-sqs-client:tests\\fixtures\\tier1_rules\\main.go:15",
      "file": "tests\\fixtures\\tier1_rules\\main.go",
      "line": 15,
      "tier": 1,
      "confidence": 0.75,
      "subtype": "sqs",
      "attrs": { "rule_id": "aws-sqs-client" }
    },
    {
      "kind": "datastore",
      "identity": "redis-client:tests\\fixtures\\tier1_rules\\main.go:16",
      "file": "tests\\fixtures\\tier1_rules\\main.go",
      "line": 16,
      "tier": 1,
      "confidence": 0.75,
      "subtype": "redis",
      "attrs": { "rule_id": "redis-client" }
    },
    {
      "kind": "datastore",
      "identity": "postgres-client:tests\\fixtures\\tier1_rules\\main.go:18",
      "file": "tests\\fixtures\\tier1_rules\\main.go",
      "line": 18,
      "tier": 1,
      "confidence": 0.75,
      "subtype": "postgres",
      "attrs": { "rule_id": "postgres-client" }
    },
    {
      "kind": "datastore",
      "identity": "aws-s3-client:tests\\fixtures\\tier1_rules\\worker.js:3",
      "file": "tests\\fixtures\\tier1_rules\\worker.js",
      "line": 3,
      "tier": 1,
      "confidence": 0.75,
      "subtype": "s3",
      "attrs": { "rule_id": "aws-s3-client" }
    },
    {
      "kind": "datastore",
      "identity": "aws-dynamodb-client:tests\\fixtures\\tier1_rules\\worker.js:6",
      "file": "tests\\fixtures\\tier1_rules\\worker.js",
      "line": 6,
      "tier": 1,
      "confidence": 0.75,
      "subtype": "dynamodb",
      "attrs": { "rule_id": "aws-dynamodb-client" }
    },
    {
      "kind": "datastore",
      "identity": "postgres-client:tests\\fixtures\\tier1_rules\\worker.js:11",
      "file": "tests\\fixtures\\tier1_rules\\worker.js",
      "line": 11,
      "tier": 1,
      "confidence": 0.75,
      "subtype": "postgres",
      "attrs": { "rule_id": "postgres-client" }
    },
    {
      "kind": "datastore",
      "identity": "redis-client:tests\\fixtures\\tier1_rules\\worker.js:13",
      "file": "tests\\fixtures\\tier1_rules\\worker.js",
      "line": 13,
      "tier": 1,
      "confidence": 0.75,
      "subtype": "redis",
      "attrs": { "rule_id": "redis-client" }
    }
  ],
  "edges": []
}
```

15 nodes, 0 edges, across all three files. Nothing from `notes.md` appears
anywhere — `.md` isn't in `LANGUAGE_BY_EXT`, so the file is never even
opened, regardless of what text it contains.

---

## Reading the two identity shapes

Every node's `identity` was built one of two ways, and both are visible
above:

- **No `capture_arg` on the rule** → `{rule_id}:{file}:{line}`, e.g.
  `aws-s3-client:tests\fixtures\tier1_rules\app.py:6`. Each occurrence
  stays a distinct piece of evidence — there's no name to key on, so
  nothing gets merged.
- **`capture_arg` fired** → `{rule_id}:{captured_value}`, e.g.
  `aws-s3-bucket-name:raw-telemetry`. This is the one row in the table
  with `attrs.bucket_name` populated. The shape is deliberate: a future
  identity-resolution phase (Phase 4, not built yet) is meant to recognize
  this as *the same real bucket* as a Tier-0-declared
  `aws_s3_bucket.raw_telemetry`, and fold the two into one corroborated
  node instead of two separate ones.

## What's absent, and why it's correct

- **`app.py` line 5** — `# boto3.client("sqs") -- old queue code, no
  longer used` — produces no node. The real, uncommented `boto3.client("sqs")`
  on line 11 is the only `aws-sqs-client` match for that file.
- **`worker.js` line 1** (`// new SQSClient() ...`) and the block comment on
  lines 8–9 (`/* ... new Redis() should not match inside here ... */`)
  produce nothing either — the real `new Redis()` on line 13 is the only
  match. Both the `#` stripper (Python) and the `//`/`/* */` stripper
  (JS/Go/Java) blank comment characters out to spaces *before* matching,
  so a pattern that would otherwise fire inside a comment simply isn't
  there anymore by the time the regex runs — while every real character's
  line number is untouched, since spaces preserve position exactly.
- **`notes.md`** never appears at all — extension-based language dispatch
  means a file with no mapped language is never opened for matching,
  regardless of its contents.

## Why no edges

Every record above has evidence — a `file`/`line` and a `kind`/`subtype` —
but none has a `src`/`dst` pair. That's not a gap to fill in later; it's
the tier's actual scope. A regex match has no notion of which function or
component it belongs to, so there's no way to name the *caller* side of an
edge — only that a pattern fired somewhere in a file. Building a real
caller → callee edge requires actually parsing the language's structure
(imports, function boundaries, resolved call sites), which is explicitly
Tier 2 (tree-sitter AST)'s job, not this one's.
