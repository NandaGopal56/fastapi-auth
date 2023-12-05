from session.session import SessionBase, CreateError, UpdateError
from sqlalchemy import Column, String, DateTime, Text, and_
from sqlalchemy import create_engine, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./sqllite.db"
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
session = SessionLocal()

class FastAPI_Session(Base):
    __tablename__ = "fastapi_sessions"

    session_key = Column(String(40), primary_key=True, index=True, nullable=False)
    session_data = Column(Text)
    expire_date = Column(DateTime(timezone=True), index=True, nullable=False)



class SessionStore(SessionBase):
    '''
    Implement session store with DB as the backend
    '''

    def __init__(self, session_key=None) -> None:
        super().__init__(session_key)

    def _get_session_from_db(self):
        try:
            return session.query(FastAPI_Session).filter(and_(
                FastAPI_Session.session_key == self.session_key,
                FastAPI_Session.exire_date > datetime.now()
            )).get()
        except Exception:
            self._session_key = None
    
    def load(self):
        s = self._get_session_from_db()
        return self.decode(s.session_data) if s else {}
    
    def exists(self, session_key):
        return bool(
            session.query(FastAPI_Session).filter(
                FastAPI_Session.session_key == session_key
            ).first()
            )
    
    def create(self):
        while True:
            self._session_key = self._get_new_session_key()
            try:
                # save immediately to ensure we have a unique entry in the db
                self.save(must_create=True)
            except CreateError:
                # key was not unique try again
                continue

            self.modified = True
            return
    
    def create_model_instance(self, data):
        return FastAPI_Session(
            session_key = self._get_or_create_session_key(),
            session_data = self.encode(data),
            expire_date = self.get_expiry_date()
        )
    
    def save(self, must_create=False):
        '''
        save the current session data to teh database. if 'must_create'
        is True, raise a database error if the saving operation doesn't create a new entry (as opposed to possibly updating an existing entry)
        '''
        if self._session_key is None:
            return self.create()
        
        data = self._get_session(no_load=must_create)
        obj = self.create_model_instance(data)

        qry_object = session.query(FastAPI_Session).where(FastAPI_Session.session_key == obj.session_key)

        try:
            if qry_object.first() is None:
                session.add(obj)
            else:
                qry_object.update(obj)
            session.commit()
        except exc.IntegrityError:
            if must_create:
                raise CreateError
            raise
        except exc.DatabaseError:
            if not must_create:
                raise UpdateError
            raise
    
    def delete(self, session_key=None):
        if session_key is None:
            if self.session_key is None:
                return
            session_key = self.session_key
        
        try:
            qry_object = session.query(FastAPI_Session).where(FastAPI_Session.session_key == session_key)
            session.delete(qry_object)
            session.commit()
        except exc.NoSuchColumnError:
            pass