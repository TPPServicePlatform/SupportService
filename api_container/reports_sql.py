from typing import Optional, Union
from sqlalchemy import MetaData, Table, Column, String, Boolean
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from lib.utils import get_actual_time, get_engine
import logging as logger
from sqlalchemy.orm import Session

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
    """

    def __init__(self):
        self.engine = get_engine()
        self.create_table()
        logger.getLogger('sqlalchemy.engine').setLevel(logger.DEBUG)

    def create_table(self):
        with Session(self.engine) as session:
            metadata = MetaData()
            self.reports = Table(
                'reports',
                metadata,
                Column('uuid', String, primary_key=True, unique=True),
                Column('type', String),
                Column('target_identifier', String),
                Column('title', String),
                Column('description', String),
                Column('complainant', String),
                Column('created_at', String)
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
                    created_at=get_actual_time()
                ).returning(self.reports.c.uuid)
                result = session.execute(query)
                session.commit()
                inserted_uuid = result.scalar() # TODO: Check if this works
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