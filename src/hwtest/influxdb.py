from influxdb_client import BucketsApi, InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from hwtest.logging import LogEvent, Logger
from hwtest.telemetry import Telemetry


class InfluxDbLogger(Logger):
    def __init__(self, bucket: str) -> None:
        self.bucket = bucket
        self.client = InfluxDBClient.from_env_properties()
        # FIXME: change this to async or batch for performance
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.create_bucket()

    def log(self, event: LogEvent) -> None:
        if isinstance(event, Telemetry):
            # Convert timestamp in seconds (from time.time()), to nanoseconds
            ts = int(event.timestamp * 1e9)
            device = event.device
            for k, v in event.items().items():
                if k not in ("device", "timestamp", "type_tag",):
                    p = Point(device).time(ts).field(k, v)
                    self.write_api.write(bucket=self.bucket, record=p)

    def create_bucket(self):
        buckets_api = BucketsApi(self.client)
        if not buckets_api.find_bucket_by_name(self.bucket):
            buckets_api.create_bucket(bucket_name=self.bucket)
