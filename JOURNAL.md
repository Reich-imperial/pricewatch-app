# PriceWatch journal

Only things I actually ran. Newest at the bottom.

## 2026-10-28 Spike 0
kind cluster with KEDA 2.21.0 and ElasticMQ 1.7.1. A stand-in worker scaled from 1 to 5 pods on 23 messages and returned to 1 about 5 minutes after the queue emptied. kind load docker-image failed with Docker 29, fixed with docker save --platform linux/amd64 plus kind load image-archive.

## 2026-10-29 Milestones 1 and 2
Walking skeleton passed. Failure tests passed: poison message to DLQ, kill -9 mid-message, graceful stop, Postgres outage.

## 2026-10-30 Containers and metrics
Bug: Dockerfile.worker copied the api folder instead of worker. Fixed.
Lesson: my first container test passed for the wrong reason because an old local worker processed the messages. Before trusting a test, check that the thing I meant to test actually ran (container log line, no local worker in ps).
Added a Prometheus counter to the worker. Before any message the page shows only HELP and TYPE lines; after one message it shows result="inserted" 1.0.

## 2026-10-30 Observability and load test (Compose)
Worker exposes pricewatch_events_total{result}; Prometheus v3.11.2 scrapes worker:9100 (up = 1); Grafana 13.0.2 datasource health check returned OK.
k6 (grafana/k6 container, 10 req/s for 20 s) with the worker delay set to 200 ms: 200 of 200 returned 202, p95 18 ms, so the API stays fast while the worker is slow.
Worker speed measured from DB timestamps: about 4.2 to 4.4 messages per second at a 200 ms delay (nominal 5; DB and queue calls add roughly 30 to 40 ms).
Counters reset when the process restarts. Open item: one of two k6 batches had 201 rows, not 200; cause not found yet. Fix going forward: tag runs with RUN_ID in the source field (not yet used in a run).

## 2026-10-31 Postgres in kind
StatefulSet with a 1Gi PVC. Persistence drill: inserted a row, deleted the pod, row still there (new pod 40 s old, PVC 29 min old, 0 restarts).
Wrong guess: I expected the kind control plane CPU (about 55% of one core) to settle after startup. It did not. No ScaledObjects, no repeating KEDA errors or events; kubelet, apiserver and etcd were the busy processes. Likely baseline cost of kind, so stop the cluster when idle.
Next: worker and API images into kind, check ElasticMQ queues exist after its restart.
