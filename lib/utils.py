import datetime
import os
import time
from typing import Optional, Union
from fastapi import HTTPException
from sqlalchemy import create_engine
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import logging as logger
import sentry_sdk

DAY = 24 * 60 * 60
HOUR = 60 * 60
MINUTE = 60
MILLISECOND = 1_000

def time_to_string(time_in_seconds: float) -> str:
    minutes = int(time_in_seconds // MINUTE)
    seconds = int(time_in_seconds % MINUTE)
    millis = int((time_in_seconds - int(time_in_seconds)) * MILLISECOND)
    return f"{minutes}m {seconds}s {millis}ms"

def get_engine() -> Optional[create_engine]:
    return create_engine(
        f"postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}",
        echo=True
    )

def get_test_engine():
    database_url = os.getenv('DATABASE_URL', 'sqlite:///test.db')  # Default to a SQLite database for testing
    return create_engine(database_url)

def get_actual_time() -> str:
    return datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')

def get_time_plus_days(days: int) -> str:
    return datetime.datetime.fromtimestamp(time.time() + days * DAY).strftime('%Y-%m-%d %H:%M:%S')

def get_mongo_client() -> MongoClient:
    if not all([os.getenv('MONGO_USER'), os.getenv('MONGO_PASSWORD'), os.getenv('MONGO_HOST'), os.getenv('MONGO_APP_NAME')]):
        raise HTTPException(status_code=500, detail="MongoDB environment variables are not set properly")
    uri = f"mongodb+srv://{os.getenv('MONGO_USER')}:{os.getenv('MONGO_PASSWORD')}@{os.getenv('MONGO_HOST')}/?retryWrites=true&w=majority&appName={os.getenv('MONGO_APP_NAME')}"
    print(f"Connecting to MongoDB: {uri}")
    logger.getLogger('pymongo').setLevel(logger.WARNING)
    return MongoClient(uri, server_api=ServerApi('1'))

def sentry_init():
    sentry_sdk.init(
        dsn=os.getenv('SENTRY_DSN'),
        # Add data like request headers and IP for users,
        # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
        send_default_pii=True,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for tracing.
        traces_sample_rate=1.0,
        _experiments={
            # Set continuous_profiling_auto_start to True
            # to automatically start the profiler on when
            # possible.
            "continuous_profiling_auto_start": True,
        },
    )
