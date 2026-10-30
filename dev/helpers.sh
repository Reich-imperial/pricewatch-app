export AWS_ACCESS_KEY_ID=x AWS_SECRET_ACCESS_KEY=x AWS_DEFAULT_REGION=elasticmq
Q=http://localhost:9324/000000000000/prices
pg() { (cd ~/pricewatch/app/dev && docker compose exec -T postgres psql -U pricewatch -c "$1"); }
qn() { aws --endpoint-url http://localhost:9324 sqs get-queue-attributes --queue-url $Q --attribute-names ApproximateNumberOfMessages --query Attributes.ApproximateNumberOfMessages --output text; }
send() { local ts=${3:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}
  curl -s -o /dev/null -w "%{http_code} " -X POST localhost:8000/v1/prices -H 'content-type: application/json' \
  -d "{\"schema_version\":1,\"event_id\":\"$(python3 -c 'import uuid;print(uuid.uuid4())')\",\"symbol\":\"$1\",\"price_ngn\":$2,\"observed_at\":\"$ts\",\"source\":\"manual\"}"; }
DLQ=http://localhost:9324/000000000000/prices-dlq
qa() { aws --endpoint-url http://localhost:9324 sqs get-queue-attributes --queue-url ${1:-$Q} --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible --query '[Attributes.ApproximateNumberOfMessages,Attributes.ApproximateNumberOfMessagesNotVisible]' --output text | awk '{print "visible="$1" in_flight="$2}'; }
