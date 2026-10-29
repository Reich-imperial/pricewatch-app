CREATE TABLE price_events (
  event_id     uuid PRIMARY KEY,
  symbol       text NOT NULL,
  price_ngn    integer NOT NULL CHECK (price_ngn > 0),
  observed_at  timestamptz NOT NULL,
  source       text NOT NULL,
  received_at  timestamptz NOT NULL,
  processed_at timestamptz NOT NULL DEFAULT now(),
  drop_pct     numeric(6,2),
  is_drop      boolean NOT NULL DEFAULT false
);
CREATE INDEX price_events_symbol_observed ON price_events (symbol, observed_at DESC);
