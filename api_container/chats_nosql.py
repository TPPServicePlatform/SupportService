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
from lib.utils import get_actual_time, get_mongo_client

HOUR = 60 * 60
MINUTE = 60
MILLISECOND = 1_000

# TODO: (General) -> Create tests for each method && add the required checks in each method

class Chats:
    """
    Chats class that stores data in a MongoDB collection.
    Fields:
    - id: int (unique) [pk] The format is "HELP-<id>" or "REPORT-<id>"
    - messages (List[Dict]): The list of messages
    - created_at (int): The timestamp of the creation of the chat
    - last_message_at (int): The timestamp of the last message sent in the chat

    Messages structure:
    - sender (str): Name of the sender, it can be "User" or "Support Agent"
    - message (str): The message content
    - sent_at (int): The timestamp of the message sent
    """

    def __init__(self, test_client=None, test_db=None):
        self.client = test_client or get_mongo_client()
        if not self._check_connection():
            raise Exception("Failed to connect to MongoDB")
        if test_client:
            self.db = self.client[os.getenv('MONGO_TEST_DB')]
        else:
            self.db = self.client[test_db or os.getenv('MONGO_DB')]
        self.collection = self.db['support-chats']
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
    
    def insert_message(self, message_content: str, message_sender: str, chat_id: str) -> Optional[str]:
        actual_time = get_actual_time()
        if not self._chat_exists(chat_id):
            try:
                return self._create_chat(message_content, message_sender, chat_id, actual_time)
            except DuplicateKeyError as e:
                logger.error(f"DuplicateKeyError: {e}")
                return None
            except OperationFailure as e:
                logger.error(f"OperationFailure: {e}")
                return None
        
        try:
            self._update_chat(message_content, message_sender, actual_time, chat_id)
            return chat_id
        except Exception as e:
            logger.error(f"Error updating chat with id '{chat_id}': {e}")
            return None

    def _update_chat(self, message_content, message_sender, actual_time, chat_id):
        self.collection.update_one({'uuid': chat_id}, {
                    '$push': {
                        'messages': {
                            'sender': message_sender,
                            'message': message_content,
                            'sent_at': actual_time
                        }
                    },
                    '$set': {
                        'last_message_at': actual_time
                    }
                })

    def _create_chat(self, message_content, message_sender, chat_id, actual_time):
        self.collection.insert_one({
                    'uuid': chat_id,
                    'messages': [{
                        'sender': message_sender,
                        'message': message_content,
                        'sent_at': actual_time
                    }],
                    'created_at': actual_time,
                    'last_message_at': actual_time
                })
        
        return chat_id
        
    def _chat_exists(self, id: str) -> Optional[str]:
        doc = self.collection.find_one({'uuid': id})
        return doc['uuid'] if doc else None
    
    def delete(self, uuid: str) -> bool:
        result = self.collection.delete_one({'uuid': uuid})
        return result.deleted_count > 0

    def get_messages(self, chat_id: str, limit: int, offset: int) -> Optional[List[Dict]]:
        chat_id = self._chat_exists(chat_id)
        if not chat_id:
            return None
        messages = self.collection.aggregate([
            {'$match': {'uuid': chat_id}},
            {'$unwind': '$messages'},
            {'$sort': {'messages.sent_at': ASCENDING}},
            {'$skip': offset},
            {'$limit': limit},
            {'$group': {
                '_id': '$_id',
                'messages': {'$push': '$messages'}
            }}
        ])
        results = list(messages)
        if not results:
            return None
        return results[0]['messages']
    
    def count_messages(self, chat_id: str) -> int:
        chat_id = self._chat_exists(chat_id)
        if not chat_id:
            return 0
        messages = self.collection.aggregate([
            {'$match': {'uuid': chat_id}},
            {'$unwind': '$messages'},
            {'$count': 'count'}
        ])
        result = list(messages)
        if not result:
            return 0
        return result[0]['count']
    
    def print_all(self):
        for chat in self.collection.find():
            print(chat)
