import requests
from datetime import datetime, timedelta
import gtfs_realtime_NYCT_pb2
import gtfs_realtime_pb2
import time


def get_feed(api_endpoint):
    response = requests.get(api_endpoint)
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)
    return feed


# %%
def get_base_data(endpoints, last_updated):
    while last_updated["last_updated"] is not None and last_updated[
        "last_updated"
    ] > datetime.now() - timedelta(seconds=25):
        print("Sleeping")
        time.sleep(1)
    last_updated["last_updated"] = datetime.now()
    return {k: get_feed(v) for k, v in endpoints.items()}
