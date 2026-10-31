# PriceWatch journal

A working log of what I tried, what broke, and what I learned.

**Rules for this file**

- Only things I actually ran. Numbers come from real output.
- Each entry separates what was **tested** from what is only a **guess** or still **open**.
- Wrong guesses stay in. They are the useful part.
- Dates before 30 October 2026 are not recorded here. Entries are grouped by phase. Check `git log` for exact times.

**Method:** understand, design, implement, predict, test, troubleshoot, explain, rebuild. Before a meaningful test I write down a prediction, then compare it with the real result.

---

## Contents

- [Phase 1: Spike on kind with KEDA](#phase-1-spike-on-kind-with-keda)
- [Phase 2: Walking skeleton and failure tests](#phase-2-walking-skeleton-and-failure-tests)
- [2026-10-30: Containers, metrics and load test](#2026-10-30-containers-metrics-and-load-test)
- [2026-10-31: Postgres in kind](#2026-10-31-postgres-in-kind)
- [Predictions log](#predictions-log)
- [Open items](#open-items)

---

## Phase 1: Spike on kind with KEDA

**Goal:** check that queue length can drive pod count before building anything real.

**Setup:** kind cluster `pricewatch` (Kubernetes v1.35.8), KEDA 2.21.0, ElasticMQ 1.7.1 in the cluster, and a stand-in worker.

**Result (tested):** an `awsEndpoint` trigger scaled the stand-in worker from 1 to 5 pods on 23 messages, then back to 1 after about 5 minutes.

**Problem:** `kind load docker-image` failed with Docker 29.
**Fix:** `docker save --platform linux/amd64 <image> -o file.tar`, then `kind load image-archive file.tar --name pricewatch`.

**Lesson:** the scale-down delay is a setting, not a bug. Waiting 5 minutes is the cooldown.

---

## Phase 2: Walking skeleton and failure tests

**Built:** Pydantic models, queue adapter, FastAPI service, worker.

**Passed (tested, local):**

- `202` for valid input and `422` for invalid input
- duplicate `event_id` leaves one row
- a drop of 5% or more is flagged
- a backlog drains
- poison message goes to the DLQ after 3 receives
- `kill -9` mid-message recovers after the visibility timeout
- graceful stop finishes the current message
- Postgres outage recovers with exactly 1 row

---

## 2026-10-30: Containers, metrics and load test

### Containers

**Bug:** `Dockerfile.worker` copied the `api` folder instead of `worker`. Fixed.

**Lesson:** my first container test passed for the wrong reason. A local worker I had forgotten about processed the messages, not the container.

**Check I now run before trusting a test:**

```bash
ps -eo pid,cmd | grep "[w]orker.main" || echo "no local worker"
docker compose logs worker --tail 3
```

After stopping the local worker, the container logged `inserted event_id=...` and the row's `processed_at` matched the log time. That was the first valid pass.

### Metrics

- Added a Prometheus counter `pricewatch_events_total{result}` and a metrics server on port 9100.
- Before any message, the metrics page shows only the `# HELP` and `# TYPE` lines. A labelled counter has no value line until the first `.labels(...)` call.
- A counter lives in process memory, so a restart resets it.
- Prometheus v3.11.2 scrapes `worker:9100` (`up` is `1`). Inside Compose the target is the service name `worker`, not `localhost`.
- Grafana 13.0.2 datasource health check returned OK. The datasource URL is `http://prometheus:9090` because `localhost` inside Grafana's container means Grafana itself.

**Mistake:** I split a `curl` command across two lines in the terminal, so the first "empty" result proved nothing. Filters like `grep '^name'` can also hide the `#` lines you want to see.

### Load test (k6)

Conditions: 10 requests per second for 20 seconds, worker delay set to 200 ms (confirmed inside the container).

| Measurement | Value |
|---|---|
| Accepted | 200 of 200 returned `202` |
| API latency | p95 18 ms |
| Worker speed | about 4.2 to 4.4 messages per second (about 0.23 s per message) |

**What it means:** the API stays fast while the worker is slow. The real ceiling is below the nominal 5 per second because database and queue calls add roughly 30 to 40 ms per message.

**Open:** the database held 401 k6 rows from two batches (200 and 201). The extra row and a 14.8 s run time in one k6 summary are unexplained. This is not data loss, but a mismatch I do not want to explain away. Fix going forward: tag each run with `RUN_ID` in the `source` field.

### Code review finding

I wondered whether a bad message could strand good messages in the same batch. Reading `queue_adapter.py` showed `receive` defaults to `max_messages=1`, so it cannot happen today. This is from reading code, not from a test. It would become real if the batch size is raised.

---

## 2026-10-31: Postgres in kind

**Built:** a Postgres StatefulSet with a 1Gi PersistentVolumeClaim, the schema loaded from a ConfigMap, credentials from a Secret created by command (not stored in git).

**Persistence drill (tested):** inserted a row, deleted `postgres-0`, waited for the new pod, counted rows. The row survived. The new pod was 40 seconds old with 0 restarts, while the PVC was 29 minutes old and still `Bound`.

**Wrong guess:** I expected the kind control plane CPU (about 55% of one core) to settle after a restart. It did not. There were no ScaledObjects, no repeating KEDA errors and no odd events. `kubelet`, `kube-apiserver` and `etcd` were the busy processes while the machine overall was about 91% idle. My best explanation is that this is the baseline cost of kind on WSL. That is an explanation, not a proof. Practical rule: stop the cluster when it is idle.

**Also noticed:** ElasticMQ restarted once around the time I stopped containers. Its queues have not been re-checked.

---

## Predictions log

| Question | My answer | Result |
|---|---|---|
| Port needed to `curl` the worker metrics from WSL | publish the port in Compose | Correct |
| Metrics page before any message | only `#` lines | Correct (restart check showed HELP and TYPE only) |
| Counter value after 5 new messages | 6 | Wrong. The restart had reset it. Logs showed 5 inserts since the restart |
| Prometheus `up` for the worker | 1 | Correct |
| Wrong Grafana datasource URL | `http://localhost:9090` | Correct |
| API behaviour with a slow worker under k6 | stays fast, backlog grows | Correct |
| Rows per minute at 200 ms delay | about 300 (the ceiling) | Correct as a ceiling. Real speed was a bit lower |
| Time to drain 200 messages | about 40 s | Close: 45.6 s and 48.6 s measured |
| Postgres row after deleting the pod | survives | Correct |

---

## Open items

- [ ] Explain the 201st k6 row and the 14.8 s run time.
- [ ] Verify the Grafana panel with a real run.
- [ ] Export the Grafana dashboard to a file in git.
- [ ] Check the worker container's user (`docker compose exec worker id`).
- [ ] Re-check that ElasticMQ in kind has its queues after the restart.
- [ ] Deploy the real worker and API to kind, then KEDA on the real worker.
- [ ] Write short incident-style notes for each fault drill.
