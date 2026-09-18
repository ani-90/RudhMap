# `parse_terraform` output reference

Extractor: [`src/rudhmap/extract/tier0_iac/terraform.py`](../../src/rudhmap/extract/tier0_iac/terraform.py)

---

## Fixture: `tests/fixtures/terraform/main.tf`

### Source

```hcl
resource "aws_s3_bucket" "raw_telemetry" {
  bucket = "raw-telemetry"
}

resource "aws_lambda_function" "normalize" {
  function_name = "normalize-lambda"
  s3_bucket     = aws_s3_bucket.raw_telemetry.id
  environment {
    variables = {
      TABLE = aws_dynamodb_table.events.name
    }
  }
}

resource "aws_dynamodb_table" "events" {
  name = "events"
}

resource "aws_iam_role" "unmapped_kind" {
  name = "some-role"
}
```

### Output

```json
{
  "nodes": [
    {
      "kind": "datastore",
      "identity": "aws_s3_bucket.raw_telemetry",
      "file": "tests\\fixtures\\terraform\\main.tf",
      "line": 1,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "resource_type": "aws_s3_bucket" }
    },
    {
      "kind": "service",
      "identity": "aws_lambda_function.normalize",
      "file": "tests\\fixtures\\terraform\\main.tf",
      "line": 5,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "resource_type": "aws_lambda_function" }
    },
    {
      "kind": "datastore",
      "identity": "aws_dynamodb_table.events",
      "file": "tests\\fixtures\\terraform\\main.tf",
      "line": 15,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "resource_type": "aws_dynamodb_table" }
    },
    {
      "kind": "unknown",
      "identity": "aws_iam_role.unmapped_kind",
      "file": "tests\\fixtures\\terraform\\main.tf",
      "line": 19,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "resource_type": "aws_iam_role" }
    }
  ],
  "edges": [
    {
      "src": "aws_lambda_function.normalize",
      "dst": "aws_s3_bucket.raw_telemetry",
      "file": "tests\\fixtures\\terraform\\main.tf",
      "line": 5,
      "tier": 0,
      "confidence": 1.0,
      "attrs": {}
    },
    {
      "src": "aws_lambda_function.normalize",
      "dst": "aws_dynamodb_table.events",
      "file": "tests\\fixtures\\terraform\\main.tf",
      "line": 5,
      "tier": 0,
      "confidence": 1.0,
      "attrs": {}
    }
  ]
}
```

`aws_iam_role` has no entry in `KIND_MAP`, so it falls back to `"unknown"`
rather than being dropped — an unmapped resource is still real evidence.

---

## Fixture: `tests/fixtures/terraform_extended/main.tf`

### Source

```hcl
resource "aws_sqs_queue" "events_queue" {
  name = "events-queue"
}

resource "aws_lambda_function" "consumer" {
  function_name = "consumer-lambda"
  environment {
    variables = {
      QUEUE_URL = aws_sqs_queue.events_queue.id
      TABLE     = var.table_name
      REGION    = data.aws_region.current.name
      BUCKET    = module.storage.bucket_name
    }
  }
}

resource "aws_iam_role" "consumer_role" {
  name = "consumer-role"
}

resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_sns_topic" "alerts-topic" {
  name = "alerts-topic"
}

resource "aws_lambda_function" "publisher" {
  function_name = "publisher-lambda"
  environment {
    variables = {
      TOPIC_ARN = aws_sns_topic.alerts-topic.arn
    }
  }
}
```

This fixture exercises: a `queue`-kind resource, a resource whose
interpolations mix a real cross-resource reference with `var.`/`data.`/
`module.` references that must **not** become edges, and a resource name
containing a dash (`alerts-topic`).

### Output

```json
{
  "nodes": [
    {
      "kind": "queue",
      "identity": "aws_sqs_queue.events_queue",
      "file": "tests\\fixtures\\terraform_extended\\main.tf",
      "line": 1,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "resource_type": "aws_sqs_queue" }
    },
    {
      "kind": "service",
      "identity": "aws_lambda_function.consumer",
      "file": "tests\\fixtures\\terraform_extended\\main.tf",
      "line": 5,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "resource_type": "aws_lambda_function" }
    },
    {
      "kind": "unknown",
      "identity": "aws_iam_role.consumer_role",
      "file": "tests\\fixtures\\terraform_extended\\main.tf",
      "line": 17,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "resource_type": "aws_iam_role" }
    },
    {
      "kind": "unknown",
      "identity": "random_id.suffix",
      "file": "tests\\fixtures\\terraform_extended\\main.tf",
      "line": 21,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "resource_type": "random_id" }
    },
    {
      "kind": "queue",
      "identity": "aws_sns_topic.alerts-topic",
      "file": "tests\\fixtures\\terraform_extended\\main.tf",
      "line": 25,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "resource_type": "aws_sns_topic" }
    },
    {
      "kind": "service",
      "identity": "aws_lambda_function.publisher",
      "file": "tests\\fixtures\\terraform_extended\\main.tf",
      "line": 29,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "resource_type": "aws_lambda_function" }
    }
  ],
  "edges": [
    {
      "src": "aws_lambda_function.consumer",
      "dst": "aws_sqs_queue.events_queue",
      "file": "tests\\fixtures\\terraform_extended\\main.tf",
      "line": 5,
      "tier": 0,
      "confidence": 1.0,
      "attrs": {}
    },
    {
      "src": "aws_lambda_function.publisher",
      "dst": "aws_sns_topic.alerts-topic",
      "file": "tests\\fixtures\\terraform_extended\\main.tf",
      "line": 29,
      "tier": 0,
      "confidence": 1.0,
      "attrs": {}
    }
  ]
}
```

Note what's **missing**: `consumer` references `var.table_name`,
`data.aws_region.current.name`, and `module.storage.bucket_name` in its
`environment` block, but none of those produce edges — `_iter_refs` filters
out `var`/`local`/`data`/`module`/`each`/`count`/`path`/`terraform` prefixes
specifically so the graph never contains dangling edges to non-resource
identities.
