from typing import Optional, List, Dict
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError, OperationFailure
import logging as logger
import os
import sys
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))
from imported_lib.SupportService.lib.utils import get_actual_time, get_mongo_client

HOUR = 60 * 60
MINUTE = 60
MILLISECOND = 1_000

MAX_STRIKES = 3
STRIKE_VALUES = {"HIGH": 1.5, "MEDIUM": 1.0, "LOW": 0.5}
AMMEND_STRIKE = 0.5

SUSPEND_TIME = 90 # days

# TODO: (General) -> Create tests for each method && add the required checks in each method

class Strikes:
    """
    Strikes class that stores data in a MongoDB collection.
    Fields:
    - user_id: str (unique) [pk] The id of the user
    - strikes: list(dict) The list of strikes
    - suspensions: list(dict) The list of suspensions (dates)
    - suspension_ends: int The timestamp of the last suspension
    - created_at: int The timestamp of the creation of the strikes
    - updated_at: int The timestamp of the last update of the strikes

    Strikes structure:
    - report_tk: str The report ticket id
    - strike_value: float The value of the strike
    - strike_reason: str The reason of the strike
    - ammended: bool If the strike was ammended of not
    - ammended_reason: str The reason of the ammended strike
    - strike_at: int The timestamp of the strike
    - updated_at: int The timestamp of the last update of the strike

    Suspensions structure:
    - suspension_at: str The date of the suspension
    - suspension strikes: list(strikes) The list of strikes that caused the suspension
    """

    def __init__(self, test_client=None, test_db=None):
        self.client = test_client or get_mongo_client()
        if not self._check_connection():
            raise Exception("Failed to connect to MongoDB")
        if test_client:
            self.db = self.client[os.getenv('MONGO_TEST_DB')]
        else:
            self.db = self.client[test_db or os.getenv('MONGO_DB')]
        self.collection = self.db['strikes']
        self._create_collection()

    def _check_connection(self):
        try:
            self.client.admin.command('ping')
        except Exception as e:
            logger.error(e)
            return False
        return True
    
    def _create_collection(self):
        self.collection.create_index([('uuid', ASCENDING)], unique=True)
    
    def check_suspension(self, user_id: str) -> Optional[str]:
        strikes_profile = self.get(user_id)
        if not strikes_profile or len(strikes_profile['suspensions']) == 0:
            return None
        suspension_ends = strikes_profile['suspension_ends']
        if not suspension_ends:
            return None
        return None if get_actual_time() < suspension_ends else suspension_ends
    
    def get_all_suspendend(self) -> set[Dict]:
        actual_time = get_actual_time()
        return set(user['user_id'] for user in self.collection.find({'suspension_ends': {'$gt': actual_time}}, {'user_id': 1}))

        
        
        