import pytest
import mongomock
from unittest.mock import patch
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))
from strikes_nosql import Strikes

# Run with the following command:
# pytest SupportService/api_container/tests/test_strikes_nosql.py

# Set the TESTING environment variable
os.environ['TESTING'] = '1'
os.environ['MONGOMOCK'] = '1'

# Set a default MONGO_TEST_DB for testing
os.environ['MONGO_TEST_DB'] = 'test_db'

@pytest.fixture(scope='function')
def mongo_client():
    client = mongomock.MongoClient()
    yield client
    client.drop_database(os.getenv('MONGO_TEST_DB'))
    client.close()

@pytest.fixture(scope='function')
def strikes(mongo_client):
    return Strikes(test_client=mongo_client)

def test_create_strikes_profile(strikes, mocker):
    mocker.patch('strikes_nosql.get_actual_time', return_value="2023-01-01 00:00:00")
    success = strikes._create_strikes_profile('user_1')
    assert success is True

def test_get_strikes_profile(strikes, mocker):
    mocker.patch('strikes_nosql.get_actual_time', return_value="2023-01-01 00:00:00")
    strikes._create_strikes_profile('user_1')
    profile = strikes.get('user_1')
    assert profile is not None
    assert profile['user_id'] == 'user_1'
    assert profile['strikes'] == []
    assert profile['suspensions'] == []
    assert profile['created_at'] == "2023-01-01 00:00:00"
    assert profile['updated_at'] == "2023-01-01 00:00:00"

def test_get_non_existent_strikes_profile(strikes, mocker):
    profile = strikes.get('user_1')
    assert profile is None

def test_add_strike(strikes, mocker):
    mocker.patch('strikes_nosql.get_actual_time', return_value="2023-01-01 00:00:00")
    strikes._create_strikes_profile('user_1')
    suspension = strikes.add_strike('user_1', 'report_1', 'HIGH', 'Test strike')
    assert suspension is False

    strikes_profile = strikes.get('user_1')
    assert strikes_profile is not None
    assert len(strikes_profile['strikes']) == 1
    assert len(strikes_profile['suspensions']) == 0
    assert strikes_profile['strikes'][0]['report_tk'] == 'report_1'
    assert strikes_profile['strikes'][0]['strike_value'] == 1.5
    assert strikes_profile['strikes'][0]['strike_reason'] == 'Test strike'
    assert strikes_profile['strikes'][0]['ammended'] is False

def test_add_strike_ammend(strikes, mocker):
    mocker.patch('strikes_nosql.get_actual_time', return_value="2023-01-01 00:00:00")
    strikes._create_strikes_profile('user_1')
    suspension = strikes.add_strike('user_1', 'report_1', 'HIGH', 'Test strike')
    assert suspension is False

    success = strikes.ammend_strike('user_1', 'report_1', 'Ammended test strike')
    assert success is True

    strikes_profile = strikes.get('user_1')
    assert strikes_profile is not None
    assert len(strikes_profile['strikes']) == 1
    assert len(strikes_profile['suspensions']) == 0
    assert strikes_profile['strikes'][0]['report_tk'] == 'report_1'
    assert strikes_profile['strikes'][0]['strike_value'] == 1.0
    assert strikes_profile['strikes'][0]['strike_reason'] == 'Test strike'
    assert strikes_profile['strikes'][0]['ammended'] is True
    assert strikes_profile['strikes'][0]['ammended_reason'] == 'Ammended test strike'

def test_suspension(strikes, mocker):
    mocker.patch('strikes_nosql.get_actual_time', return_value="2023-01-01 00:00:00")
    strikes._create_strikes_profile('user_1')
    suspension = strikes.add_strike('user_1', 'report_1', 'HIGH', 'Test strike')
    assert suspension is False

    suspension = strikes.add_strike('user_1', 'report_2', 'HIGH', 'Test strike')
    assert suspension is False

    suspension = strikes.add_strike('user_1', 'report_3', 'LOW', 'Test strike')
    assert suspension is True

    strikes_profile = strikes.get('user_1')
    assert strikes_profile is not None
    assert len(strikes_profile['strikes']) == 0
    assert len(strikes_profile['suspensions']) == 1
    strikes = set([strike['report_tk'] for strike in strikes_profile['suspensions'][0]['suspension_strikes']])
    assert strikes == set(['report_1', 'report_2', 'report_3'])