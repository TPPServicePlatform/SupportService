import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))
from reports_sql import Reports
from reports_sql import get_actual_time

# Run with the following command:
# pytest SupportService/api_container/tests/test_reports_sql.py

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
def reports(test_engine):
    return Reports(engine=test_engine)

@pytest.fixture(autouse=True)
def clear_database(reports):
    reports.create_table()
    session = reports.Session()
    session.query(reports.reports).delete()
    session.commit()
    session.close()

def test_create_table(reports):
    reports.create_table()
    assert reports.reports is not None

def test_insert_report(reports, mocker):
    mocker.patch('reports_sql.get_actual_time', return_value='2023-01-01 00:00:00')
    report_uuid = reports.insert(
        type='ACCOUNT',
        target_identifier='target_123',
        title='Test Title',
        description='Test Description',
        complainant='test_user'
    )
    assert report_uuid is not None

def test_get_report(reports, mocker):
    mocker.patch('reports_sql.get_actual_time', return_value='2023-01-01 00:00:00')
    report_uuid = reports.insert(
        type='ACCOUNT',
        target_identifier='target_123',
        title='Test Title',
        description='Test Description',
        complainant='test_user'
    )
    report = reports.get(report_uuid)
    assert report is not None
    assert report['type'] == 'ACCOUNT'
    assert report['target_identifier'] == 'target_123'

def test_get_reports_by_target(reports, mocker):
    mocker.patch('reports_sql.get_actual_time', return_value='2023-01-01 00:00:00')
    reports.insert(
        type='ACCOUNT',
        target_identifier='target_123',
        title='Test Title 1',
        description='Test Description 1',
        complainant='test_user'
    )
    reports.insert(
        type='ACCOUNT',
        target_identifier='target_123',
        title='Test Title 2',
        description='Test Description 2',
        complainant='test_user'
    )
    report_list = reports.get_by_target(type='ACCOUNT', target_identifier='target_123')
    assert report_list is not None
    assert len(report_list) == 2

def test_delete_report(reports, mocker):
    mocker.patch('reports_sql.get_actual_time', return_value='2023-01-01 00:00:00')
    report_uuid = reports.insert(
        type='ACCOUNT',
        target_identifier='target_123',
        title='Test Title',
        description='Test Description',
        complainant='test_user'
    )
    result = reports.delete(report_uuid)
    assert result is True
    report = reports.get(report_uuid)
    assert report is None
    