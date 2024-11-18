import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))
from helptks_sql import HelpTKs
from lib.utils import get_actual_time

# Run with the following command:
# pytest SupportService/api_container/tests/test_helptks_sql.py

# Set the TESTING environment variable
os.environ['TESTING'] = '1'

# Set a default DATABASE_URL for testing
os.environ['DATABASE_URL'] = 'sqlite:///test.db'

@pytest.fixture(scope='module')
def test_engine():
    engine = create_engine('sqlite:///:memory:', echo=True)
    yield engine
    engine.dispose()

@pytest.fixture(scope='module')
def helptks(test_engine):
    return HelpTKs(engine=test_engine)

@pytest.fixture(autouse=True)
def clear_database(helptks):
    helptks.create_table()
    session = helptks.Session()
    session.query(helptks.help_tks).delete()
    session.commit()
    session.close()

def test_create_table(helptks):
    helptks.create_table()
    assert helptks.help_tks is not None
    def test_insert_helptk(helptks, mocker):
        mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
        helptk_uuid = helptks.insert(
            title='Test Title',
            description='Test Description',
            requester='test_user'
        )
        assert helptk_uuid is not None

def test_get_helptk(helptks, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    helptk_uuid = helptks.insert(
        title='Test Title',
        description='Test Description',
        requester='test_user'
    )
    helptk = helptks.get(helptk_uuid)
    assert helptk is not None
    assert helptk['title'] == 'Test Title'
    assert helptk['description'] == 'Test Description'
    assert helptk['requester'] == 'test_user'

def test_delete_helptk(helptks, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    helptk_uuid = helptks.insert(
        title='Test Title',
        description='Test Description',
        requester='test_user'
    )
    result = helptks.delete(helptk_uuid)
    assert result is True
    helptk = helptks.get(helptk_uuid)
    assert helptk is None

def test_get_helptks_by_user(helptks, mocker):
    mocker.patch('lib.utils.get_actual_time', return_value='2023-01-01 00:00:00')
    helptks.insert(
        title='Test Title 1',
        description='Test Description 1',
        requester='test_user'
    )
    helptks.insert(
        title='Test Title 2',
        description='Test Description 2',
        requester='test_user'
    )
    helptk_list = helptks.get_by_user(requester='test_user')
    assert helptk_list is not None
    assert len(helptk_list) == 2
