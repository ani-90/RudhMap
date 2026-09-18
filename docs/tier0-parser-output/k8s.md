# `parse_k8s` output reference

Extractor: [`src/rudhmap/extract/tier0_iac/k8s.py`](../../src/rudhmap/extract/tier0_iac/k8s.py)

---

## Fixture: `tests/fixtures/k8s/api.yaml`

### Source

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: default
spec:
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
        - name: api
          image: myorg/api:latest
          envFrom:
            - configMapRef:
                name: api-config
---
apiVersion: v1
kind: Service
metadata:
  name: api-svc
  namespace: default
spec:
  selector:
    app: api
  ports:
    - port: 80
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-config
  namespace: default
data:
  LOG_LEVEL: info
```

### Output

```json
{
  "nodes": [
    {
      "kind": "service",
      "identity": "Deployment/default/api",
      "file": "tests\\fixtures\\k8s\\api.yaml",
      "line": 4,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "k8s_kind": "Deployment", "namespace": "default" }
    },
    {
      "kind": "route",
      "identity": "Service/default/api-svc",
      "file": "tests\\fixtures\\k8s\\api.yaml",
      "line": 22,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "k8s_kind": "Service", "namespace": "default" }
    },
    {
      "kind": "config",
      "identity": "ConfigMap/default/api-config",
      "file": "tests\\fixtures\\k8s\\api.yaml",
      "line": 33,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "k8s_kind": "ConfigMap", "namespace": "default" }
    }
  ],
  "edges": [
    {
      "src": "Deployment/default/api",
      "dst": "ConfigMap/default/api-config",
      "file": "tests\\fixtures\\k8s\\api.yaml",
      "line": 4,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "relation": "mounts_or_reads" }
    },
    {
      "src": "Service/default/api-svc",
      "dst": "Deployment/default/api",
      "file": "tests\\fixtures\\k8s\\api.yaml",
      "line": 22,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "relation": "routes_to" }
    }
  ]
}
```

Identity format is `{kind}/{namespace}/{name}`. The `Service -> Deployment`
edge exists because the Service's `spec.selector` (`app: api`) matches the
labels under the Deployment's `spec.template.metadata.labels`.

---

## Fixture: `tests/fixtures/k8s_extended/mixed.yaml`

13 documents covering every workload/job/datastore/config kind bucket, a
`secretRef` + `configMap` volume + PVC claim reference, same-selector
Services in two different namespaces (only the same-namespace one may
match), a quoted `name:` value, a document with no `metadata.name` (must be
skipped), and a bare-scalar document (`justastring`, not a mapping — must
be skipped). Full source: [`tests/fixtures/k8s_extended/mixed.yaml`](../../tests/fixtures/k8s_extended/mixed.yaml).

### Output

```json
{
  "nodes": [
    {
      "kind": "service",
      "identity": "StatefulSet/data/db",
      "file": "tests\\fixtures\\k8s_extended\\mixed.yaml",
      "line": 4,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "k8s_kind": "StatefulSet", "namespace": "data" }
    },
    {
      "kind": "service",
      "identity": "DaemonSet/default/agent",
      "file": "tests\\fixtures\\k8s_extended\\mixed.yaml",
      "line": 29,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "k8s_kind": "DaemonSet", "namespace": "default" }
    },
    {
      "kind": "job",
      "identity": "CronJob/default/nightly",
      "file": "tests\\fixtures\\k8s_extended\\mixed.yaml",
      "line": 44,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "k8s_kind": "CronJob", "namespace": "default" }
    },
    {
      "kind": "job",
      "identity": "Job/default/onetime",
      "file": "tests\\fixtures\\k8s_extended\\mixed.yaml",
      "line": 58,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "k8s_kind": "Job", "namespace": "default" }
    },
    {
      "kind": "service",
      "identity": "ReplicaSet/default/legacy",
      "file": "tests\\fixtures\\k8s_extended\\mixed.yaml",
      "line": 73,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "k8s_kind": "ReplicaSet", "namespace": "default" }
    },
    {
      "kind": "datastore",
      "identity": "PersistentVolumeClaim/data/db-pvc",
      "file": "tests\\fixtures\\k8s_extended\\mixed.yaml",
      "line": 88,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "k8s_kind": "PersistentVolumeClaim", "namespace": "data" }
    },
    {
      "kind": "config",
      "identity": "Secret/data/db-secret",
      "file": "tests\\fixtures\\k8s_extended\\mixed.yaml",
      "line": 96,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "k8s_kind": "Secret", "namespace": "data" }
    },
    {
      "kind": "config",
      "identity": "ConfigMap/data/db-cfg",
      "file": "tests\\fixtures\\k8s_extended\\mixed.yaml",
      "line": 104,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "k8s_kind": "ConfigMap", "namespace": "data" }
    },
    {
      "kind": "config",
      "identity": "Secret/default/job-secret",
      "file": "tests\\fixtures\\k8s_extended\\mixed.yaml",
      "line": 112,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "k8s_kind": "Secret", "namespace": "default" }
    },
    {
      "kind": "route",
      "identity": "Service/data/db-svc",
      "file": "tests\\fixtures\\k8s_extended\\mixed.yaml",
      "line": 120,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "k8s_kind": "Service", "namespace": "data" }
    },
    {
      "kind": "route",
      "identity": "Service/default/cross-ns-svc",
      "file": "tests\\fixtures\\k8s_extended\\mixed.yaml",
      "line": 131,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "k8s_kind": "Service", "namespace": "default" }
    },
    {
      "kind": "route",
      "identity": "Service/default/legacy-svc",
      "file": "tests\\fixtures\\k8s_extended\\mixed.yaml",
      "line": 142,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "k8s_kind": "Service", "namespace": "default" }
    },
    {
      "kind": "config",
      "identity": "Secret/default/quoted-secret",
      "file": "tests\\fixtures\\k8s_extended\\mixed.yaml",
      "line": 163,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "k8s_kind": "Secret", "namespace": "default" }
    }
  ],
  "edges": [
    {
      "src": "StatefulSet/data/db",
      "dst": "Secret/data/db-secret",
      "file": "tests\\fixtures\\k8s_extended\\mixed.yaml",
      "line": 4,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "relation": "mounts_or_reads" }
    },
    {
      "src": "StatefulSet/data/db",
      "dst": "ConfigMap/data/db-cfg",
      "file": "tests\\fixtures\\k8s_extended\\mixed.yaml",
      "line": 4,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "relation": "mounts_or_reads" }
    },
    {
      "src": "StatefulSet/data/db",
      "dst": "PersistentVolumeClaim/data/db-pvc",
      "file": "tests\\fixtures\\k8s_extended\\mixed.yaml",
      "line": 4,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "relation": "mounts_or_reads" }
    },
    {
      "src": "Job/default/onetime",
      "dst": "Secret/default/job-secret",
      "file": "tests\\fixtures\\k8s_extended\\mixed.yaml",
      "line": 58,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "relation": "mounts_or_reads" }
    },
    {
      "src": "Service/data/db-svc",
      "dst": "StatefulSet/data/db",
      "file": "tests\\fixtures\\k8s_extended\\mixed.yaml",
      "line": 120,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "relation": "routes_to" }
    },
    {
      "src": "Service/default/legacy-svc",
      "dst": "ReplicaSet/default/legacy",
      "file": "tests\\fixtures\\k8s_extended\\mixed.yaml",
      "line": 142,
      "tier": 0,
      "confidence": 1.0,
      "attrs": { "relation": "routes_to" }
    }
  ]
}
```

Two things worth calling out that are **absent** from this output because
of current parser limitations, not oversights in the fixture:

- **`CronJob/default/nightly` produces no `mounts_or_reads` edges** even
  though it has containers. `_config_refs` only looks at
  `spec.template.spec`, but a CronJob's pod spec actually lives under
  `spec.jobTemplate.spec.template.spec` — one level deeper than a Job or
  Deployment. The extractor doesn't special-case CronJob, so its container
  refs are silently invisible today.
- **`Service/default/cross-ns-svc` produces no `routes_to` edge** despite
  having the exact same selector (`app: db`) as `db-svc`. It lives in
  `default` while the `StatefulSet/data/db` it would otherwise match lives
  in `data` — the extractor requires `svc_entry["namespace"] ==
  wl_entry["namespace"]` before even checking the selector, so
  cross-namespace matches are correctly rejected.
- The `Pod` document with `metadata: {}` (no `name`) and the bare-scalar
  `justastring` document both vanish silently — no node, no error. That's
  `if not name: continue` and `if not isinstance(doc, dict): continue`
  respectively.
