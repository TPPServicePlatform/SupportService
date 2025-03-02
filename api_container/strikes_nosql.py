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
from lib.utils import get_actual_time, get_mongo_client, get_time_plus_days

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
    
    def _create_strikes_profile(self, user_id: str) -> bool:
        try:
            self.collection.insert_one({
                'user_id': user_id,
                'strikes': [],
                'suspensions': [],
                'suspension_ends': None,
                'created_at': get_actual_time(),
                'updated_at': get_actual_time()
            })
            return True
        except DuplicateKeyError as e:
            logger.error(f"DuplicateKeyError: {e}")
            return False
        except OperationFailure as e:
            logger.error(f"OperationFailure: {e}")
            return False
        except Exception as e:
            logger.error(f"Error creating strikes profile for user '{user_id}': {e}")
            return False
        
    def get(self, user_id: str) -> Optional[Dict]:
        return self.collection.find_one({'user_id': user_id})
    
    def _check_suspension(self, user_id: str) -> bool:
        strikes_profile = self.get(user_id)
        if not strikes_profile or len(strikes_profile['strikes']) == 0:
            return False
        strikes_sum = sum(strike['strike_value'] for strike in strikes_profile['strikes'])
        if strikes_sum <= MAX_STRIKES:
            return False
        time_now = get_actual_time()
        self.collection.update_one({'user_id': user_id}, {
            '$push': {
                'suspensions': {
                    'suspension_at': time_now,
                    'suspension_strikes': strikes_profile['strikes']
                }
            },
            '$set': {
                'strikes': [],
                'updated_at': time_now,
                'suspension_ends': get_time_plus_days(SUSPEND_TIME)
            }
        })
        return True
        
    def add_strike(self, user_id: str, report_tk: str, strike_type: str, strike_reason: str) -> Optional[bool]:
        strikes_profile = self.get(user_id)
        if not strikes_profile:
            if not self._create_strikes_profile(user_id):
                return None
            strikes_profile = self.get(user_id)
        
        if not strike_type in STRIKE_VALUES:
            logger.error(f"Invalid strike type '{strike_type}'")
            return None
        time_now = get_actual_time()
        try:
            self.collection.update_one({'user_id': user_id}, {
                '$push': {
                    'strikes': {
                        'report_tk': report_tk,
                        'strike_value': STRIKE_VALUES[strike_type],
                        'strike_reason': strike_reason,
                        'ammended': False,
                        'ammended_reason': "",
                        'strike_at': time_now,
                        'updated_at': time_now
                    }
                },
                '$set': {
                    'updated_at': time_now
                }
            })
            return self._check_suspension(user_id)
        except Exception as e:
            logger.error(f"Error adding strike to user '{user_id}': {e}")
            return None
        
    def ammend_strike(self, user_id: str, report_tk: str, ammend_reason: str) -> bool:
        strikes_profile = self.get(user_id)
        if not strikes_profile or len(strikes_profile['strikes']) == 0:
            return False
        if not report_tk in set(strike['report_tk'] for strike in strikes_profile['strikes']):
            logger.error(f"Report ticket '{report_tk}' not found in user '{user_id}' strikes")
            return False
        strike = next(strike for strike in strikes_profile['strikes'] if strike['report_tk'] == report_tk)
        if strike['ammended']:
            logger.error(f"Strike with report ticket '{report_tk}' already ammended")
            return False
        time_now = get_actual_time()
        self.collection.update_one({
            'user_id': user_id,
            'strikes.report_tk': report_tk
        }, {
            '$set': {
                'strikes.$.strike_value': strike['strike_value'] - AMMEND_STRIKE,
                'strikes.$.ammended': True,
                'strikes.$.ammended_reason': ammend_reason,
                'strikes.$.updated_at': time_now,
                'updated_at': time_now
            }
        })
        return True
    
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

        
        
        