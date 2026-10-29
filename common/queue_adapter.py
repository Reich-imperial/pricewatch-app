import os

import boto3
from botocore.config import Config


class QueueAdapter:
    """The only place that talks to the queue. Works on ElasticMQ and real SQS."""

    def __init__(self, queue_url=None, read_timeout=5):
        self.queue_url = queue_url or os.environ["QUEUE_URL"]
        self.client = boto3.client(
            "sqs",
            endpoint_url=os.environ.get("SQS_ENDPOINT_URL"),  # unset on real AWS
            region_name=os.environ.get("AWS_REGION", "elasticmq"),
            config=Config(connect_timeout=2, read_timeout=read_timeout, retries={"max_attempts": 1}),
        )

    def send(self, body: str):
        return self.client.send_message(QueueUrl=self.queue_url, MessageBody=body)

    def receive(self, wait_seconds=10, max_messages=1):
        r = self.client.receive_message(
            QueueUrl=self.queue_url, MaxNumberOfMessages=max_messages, WaitTimeSeconds=wait_seconds
        )
        return r.get("Messages", [])

    def delete(self, receipt_handle: str):
        self.client.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt_handle)
