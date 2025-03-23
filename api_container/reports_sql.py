from datetime import datetime, timedelta
import random
from typing import Optional, Union
from sqlalchemy import MetaData, Table, Column, String, Boolean
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import logging as logger
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import text
import os
import sys
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))
from lib.utils import get_actual_time, get_engine

HOUR = 60 * 60
MINUTE = 60
MILLISECOND = 1_000

# TODO: (General) -> Create tests for each method && add the required checks in each method

class Reports:
    """
    Reports class that stores data in a db through sqlalchemy
    Fields:
    - uuid: str (unique) [pk]
    - type: str (ACCOUNT or SERVICE)
    - target_identifier: str
    - title: str
    - description: str
    - complainant: str
    - created_at: datetime
    - updated_at: datetime
    - resolved: bool
    """

    def __init__(self, engine=None):
        self.engine = engine or get_engine()
        self.create_table()
        logger.getLogger('sqlalchemy.engine').setLevel(logger.DEBUG)
        self.metadata = MetaData()
        self.metadata.bind = self.engine
        self.Session = sessionmaker(bind=self.engine)
        
    def drop(self):
        with Session(self.engine) as session:
            self.reports.drop(self.engine)
            session.commit()

    def create_table(self):
        with Session(self.engine) as session:
            metadata = MetaData()
            self.reports = Table(
                'reports',
                metadata,
                Column('uuid', String, primary_key=True, default=lambda: str(uuid.uuid4())),
                Column('type', String),
                Column('target_identifier', String),
                Column('title', String),
                Column('description', String),
                Column('complainant', String),
                Column('created_at', String),
                Column('updated_at', String),
                Column('resolved', Boolean)
            )
            metadata.create_all(self.engine)
            session.commit()
    
    def insert(self, type: str, target_identifier: str, title: str, description: str, complainant: str) -> Optional[str]:
        with Session(self.engine) as session:
            try:
                query = self.reports.insert().values(
                    type=type,
                    target_identifier=target_identifier,
                    title=title,
                    description=description,
                    complainant=complainant,
                    created_at=get_actual_time(),
                    updated_at=get_actual_time(),
                    resolved=False
                ).returning(self.reports.c.uuid)
                result = session.execute(query)
                inserted_uuid = result.scalar() # TODO: Check if this works
                session.commit()
                return inserted_uuid
            except IntegrityError as e:
                logger.error(f"IntegrityError: {e}")
                session.rollback()
                return None
            except SQLAlchemyError as e:
                logger.error(f"SQLAlchemyError: {e}")
                session.rollback()
                return None
    
    def get(self, uuid: str) -> Optional[dict]:
        with self.engine.connect() as connection:
            query = self.reports.select().where(self.reports.c.uuid == uuid)
            result = connection.execute(query)
            report = result.fetchone()
            if report is None:
                return None
            return report._asdict()
    
    def get_by_target(self, type: str, target_identifier: str) -> Optional[list[dict]]:
        with self.engine.connect() as connection:
            query = self.reports.select().where(self.reports.c.type == type).where(self.reports.c.target_identifier == target_identifier)
            result = connection.execute(query)
            reports = result.fetchall()
            if reports is None:
                return None
            return [report._asdict() for report in reports]
        
    def delete(self, uuid: str) -> bool:
        with Session(self.engine) as session:
            try:
                query = self.reports.delete().where(self.reports.c.uuid == uuid)
                session.execute(query)
                session.commit()
            except SQLAlchemyError as e:
                logger.error(f"SQLAlchemyError: {e}")
                session.rollback()
                return False
        return True
    
    def resolve(self, uuid: str) -> bool:
        with Session(self.engine) as session:
            try:
                query = self.reports.update().where(self.reports.c.uuid == uuid).values(
                    resolved=True,
                    updated_at=get_actual_time()
                )
                session.execute(query)
                session.commit()
            except SQLAlchemyError as e:
                logger.error(f"SQLAlchemyError: {e}")
                session.rollback()
                return False
        return True
    
    def _get_new_tks(self, from_date: str, to_date: str) -> int:
        with self.engine.connect() as connection:
            query = self.reports.select().where(
                (self.reports.c.created_at >= from_date) & 
                (self.reports.c.created_at <= to_date)
            )
            result = connection.execute(query)
            return result.fetchall()
        
    def _get_resolved_tks(self, from_date: str, to_date: str) -> int:
        with self.engine.connect() as connection:
            query = self.reports.select().where(
                (self.reports.c.updated_at >= from_date) & 
                (self.reports.c.updated_at <= to_date) &
                (self.reports.c.resolved == True)
            )
            result = connection.execute(query)
            return result.fetchall()
    
    def last_month_stats(self) -> Optional[dict]:
        """
        Stats to collect:
        - new tks this month and % difference with last month
        - resolved tks this month and % difference with last month
        """
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        this_month = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        previous_month = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d %H:%M:%S')
        
        perc_diff = lambda new, last: round(((new - last) / last) if last != 0 else 1, 2)
        
        new_this_month = len(self._get_new_tks(this_month, now))
        new_last_month = len(self._get_new_tks(previous_month, this_month))
        perc_diff_new = perc_diff(new_this_month, new_last_month)
        
        resolved_this_month = len(self._get_resolved_tks(this_month, now))
        resolved_last_month = len(self._get_resolved_tks(previous_month, this_month))
        perc_diff_resolved = perc_diff(resolved_this_month, resolved_last_month)
        
        # return {
        #     "new_this_month": new_this_month,
        #     "perc_diff_new": perc_diff_new,
        #     "resolved_this_month": resolved_this_month,
        #     "perc_diff_resolved": perc_diff_resolved
        # }
        return { # MOCK HERE
            "new_this_month": random.randint(1, 100),
            "perc_diff_new": random.choice([1, -1]) * random.randint(1, 100) / 100,
            "resolved_this_month": random.randint(1, 100),
            "perc_diff_resolved": random.choice([1, -1]) * random.randint(1, 100) / 100
        }
        
    def tickets_by_day(self, from_date: str, to_date: str) -> Optional[dict]:
        """
        Stats to collect:
        - new tks by day
        - resolved tks by day
        format:
        { <date>: { "new": <int>, "resolved": <int> } }
        """
        all_tks = self._get_new_tks(from_date, to_date)
        resolved_tks = self._get_resolved_tks(from_date, to_date)
        results = {}
        for tk in all_tks:
            created_date = tk['created_at'].split(' ')[0]
            results[created_date] = results.get(created_date, {"new": 0, "resolved": 0})
            results[created_date]["new"] += 1
        for tk in resolved_tks:
            updated_date = tk['updated_at'].split(' ')[0]
            results[updated_date] = results.get(updated_date, {"new": 0, "resolved": 0})
            results[updated_date]["resolved"] += 1
        return results