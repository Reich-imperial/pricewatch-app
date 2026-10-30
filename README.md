# PriceWatch

A learning project: synthetic commodity price events go through an API into a queue, and a worker stores them in Postgres and flags big price drops.

    POST /v1/prices -> queue (ElasticMQ locally, SQS later) -> worker -> Postgres

## Run locally
    cd dev
    docker compose up -d --build
    source helpers.sh
    send RICE_50KG 92000

## Status
Tested by me:
- API accepts valid input (202) and rejects bad input (422)
- Duplicate event_id leaves one row (idempotent insert)
- Price drop of 5% or more is flagged
- Poison message goes to the DLQ after 3 receives
- Worker killed mid-message: message returns after the visibility timeout
- Postgres outage: worker retries and recovers with one row
- API and worker run as Docker containers; worker exposes a Prometheus counter on port 9100
- KEDA scaled a stand-in worker from 1 to 5 pods on 23 messages in a kind cluster

Not done yet: k6 load tests, Prometheus and Grafana dashboards, KEDA on the real worker, Kustomize, Argo CD, CI, Terraform and AWS, fault-drill write-ups.

See JOURNAL.md for what was tried, what broke and what I learned.
