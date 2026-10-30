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
