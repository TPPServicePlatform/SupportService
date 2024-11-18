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

class HelpTKs:
    """
    HelpTKs class that stores data in a db through sqlalchemy
    Fields:
    - uuid: str (unique) [pk]
    - title: str
    - description: str
    - requester: str
    - created_at: datetime
    - comments: list[dict]
    - resolved: bool
    - updated_at: datetime
    """

    def __init__(self, engine=None):
        self.engine = engine or get_engine()
        self.create_table()
        logger.getLogger('sqlalchemy.engine').setLevel(logger.DEBUG)
        self.metadata = MetaData()
        self.metadata.bind = self.engine
        self.Session = sessionmaker(bind=self.engine)

    def create_table(self):
        with Session(self.engine) as session:
            metadata = MetaData()
            self.help_tks = Table(
                'help_tks',
                metadata,
                Column('uuid', String, primary_key=True, default=lambda: str(uuid.uuid4())),
                Column('title', String),
                Column('description', String),
                Column('requester', String),
                Column('created_at', String),
                Column('comments', String),
                Column('resolved', Boolean),
                Column('updated_at', String)
            )
            metadata.create_all(self.engine)
            session.commit()
    
    def insert(self, title: str, description: str, requester: str) -> Optional[str]:
        with Session(self.engine) as session:
            try:
                query = self.help_tks.insert().values(
                    title=title,
                    description=description,
                    requester=requester,
                    created_at=get_actual_time(),
                    comments="[]",
                    resolved=False,
                    updated_at=get_actual_time()
                ).returning(self.help_tks.c.uuid)
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
            query = self.help_tks.select().where(self.help_tks.c.uuid == uuid)
            result = connection.execute(query)
            tk = result.fetchone()
            if tk is None:
                return None
            dict_tk = tk._asdict()
            dict_tk['comments'] = eval(dict_tk['comments'])
            return dict_tk
        
    def delete(self, uuid: str) -> bool:
        with Session(self.engine) as session:
            try:
                query = self.help_tks.delete().where(self.help_tks.c.uuid == uuid)
                session.execute(query)
                session.commit()
            except SQLAlchemyError as e:
                logger.error(f"SQLAlchemyError: {e}")
                session.rollback()
                return False
        return True
    
    def get_by_user(self, requester: str) -> Optional[list[dict]]:
        with self.engine.connect() as connection:
            query = self.help_tks.select().where(self.help_tks.c.requester == requester)
            result = connection.execute(query)
            tks = result.fetchall()
            if tks is None:
                return None
            tks_list = []
            for tk in tks:
                dict_tk = tk._asdict()
                dict_tk['comments'] = eval(dict_tk['comments'])
                tks_list.append(dict_tk)
            return tks_list
    
    def update(self, uuid: str, comment: str, resolved: bool) -> bool:
        now = get_actual_time()
        if not self.get(uuid):
            return False
        previous_comments = self.get(uuid)['comments']
        previous_comments.append({
            "comment": comment,
            "created_at": now
        })
        with Session(self.engine) as session:
            try:
                query = self.help_tks.update().where(self.help_tks.c.uuid == uuid).values(
                    comments=str(previous_comments),
                    resolved=resolved,
                    updated_at=now
                )
                session.execute(query)
                session.commit()
            except SQLAlchemyError as e:
                logger.error(f"SQLAlchemyError: {e}")
                session.rollback()
                return False
        return True