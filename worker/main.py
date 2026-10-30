import logging
import os
import signal
import time

import psycopg
from pydantic import ValidationError

from common.models import QueuedPriceUpdate
from common.queue_adapter import QueueAdapter
from prometheus_client import Counter, start_http_server

logging.basicConfig(level=logging.INFO, format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}')

DELAY_S = float(os.environ.get("PROCESSING_DELAY_MS", "0")) / 1000  # SYNTHETIC delay, only to make autoscaling visible
DROP_THRESHOLD = float(os.environ.get("DROP_THRESHOLD_PCT", "5.0"))
BACKOFF_S = float(os.environ.get("WORKER_BACKOFF_SECONDS", "5"))

PREVIOUS_SQL = ("SELECT price_ngn FROM price_events WHERE symbol = %s AND observed_at < %s "
                "ORDER BY observed_at DESC LIMIT 1")
INSERT_SQL = """INSERT INTO price_events
  (event_id, symbol, price_ngn, observed_at, source, received_at, drop_pct, is_drop)
  VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
  ON CONFLICT (event_id) DO NOTHING
  RETURNING event_id"""

running = True
EVENTS = Counter("pricewatch_events_total", "Messages handled by the worker",["result"])



def request_stop(signum, frame):
    global running
    running = False
    logging.info("stop requested, finishing the current message")


def process(conn, body):
    """Validate, then write in ONE transaction. Returns (outcome, event_id).
    Raises on invalid input or database errors. Never deletes anything."""
    update = QueuedPriceUpdate.model_validate_json(body)
    time.sleep(DELAY_S)
    with conn.transaction():
        row = conn.execute(PREVIOUS_SQL, (update.symbol, update.observed_at)).fetchone()
        drop_pct = round((update.price_ngn - row[0]) / row[0] * 100, 2) if row else None
        is_drop = drop_pct is not None and drop_pct <= -DROP_THRESHOLD
        inserted = conn.execute(INSERT_SQL, (update.event_id, update.symbol, update.price_ngn,
                                             update.observed_at, update.source, update.received_at,
                                             drop_pct, is_drop)).fetchone()
    return ("inserted" if inserted else "duplicate"), update.event_id


def main():
    start_http_server(9100)
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    queue = QueueAdapter(read_timeout=15)
    conn = None
    while running:
        try:
            if conn is None or conn.closed:
                conn = psycopg.connect(os.environ["DATABASE_URL"], autocommit=True)
            for msg in queue.receive(wait_seconds=5):
                outcome, event_id = process(conn, msg["Body"])  # the commit happens inside process()
                queue.delete(msg["ReceiptHandle"])              # only AFTER the commit
                logging.info("%s event_id=%s", outcome, event_id)
                EVENTS.labels(outcome).inc()
        except ValidationError as e:
            logging.warning("invalid message left on queue: %s", e.errors()[0]["msg"])  # not deleted
            EVENTS.labels("invalid").inc()
        except Exception:
            logging.exception("processing failed, message left on queue, backing off")
            EVENTS.labels("error").inc()
            time.sleep(BACKOFF_S)


if __name__ == "__main__":
    main()
