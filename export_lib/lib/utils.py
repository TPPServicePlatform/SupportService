import datetime
import os
import time
from typing import Optional, Union
from fastapi import HTTPException
from sqlalchemy import create_engine
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import logging as logger

DAY = 24 * 60 * 60
HOUR = 60 * 60
MINUTE = 60
MILLISECOND = 1_000

def get_actual_time() -> str:
    return datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')

def get_mongo_client() -> MongoClient:
    if not all([os.getenv('MONGO_USER'), os.getenv('MONGO_PASSWORD'), os.getenv('MONGO_HOST'), os.getenv('MONGO_APP_NAME')]):
        raise HTTPException(status_code=500, detail="MongoDB environment variables are not set properly")
    uri = f"mongodb+srv://{os.getenv('MONGO_USER')}:{os.getenv('MONGO_PASSWORD')}@{os.getenv('MONGO_HOST')}/?retryWrites=true&w=majority&appName={os.getenv('MONGO_APP_NAME')}"
    print(f"Connecting to MongoDB: {uri}")
    logger.getLogger('pymongo').setLevel(logger.WARNING)
    return MongoClient(uri, server_api=ServerApi('1'))