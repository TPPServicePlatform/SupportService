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
    """

    def __init__(self, engine=None):
        self.engine = engine or get_engine()
        self.create_table()
        logger.getLogger('sqlalchemy.engine').setLevel(logger.DEBUG)
        self.metadata = MetaData()
        self.metadata.bind = self.engine
        self.Session = sessionmaker(bind=self.engine)

    def create_table(self):
        if self.engine.dialect.name == 'sqlite':
            uuid_column = Column('uuid', String, primary_key=True, default=lambda: str(uuid.uuid4()))
        else:
            uuid_column = Column('uuid', UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
            
        with Session(self.engine) as session:
            metadata = MetaData()
            self.reports = Table(
                'reports',
                metadata,
                uuid_column,
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