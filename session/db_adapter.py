from session.session import SessionBase, CreateError, UpdateError
from sqlalchemy import Column, String, DateTime, Text, and_
from sqlalchemy import create_engine
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
    exire_date = Column(DateTime(timezone=True), index=True, nullable=False)



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
    
    def exists(self):
        return bool(
            session.query(FastAPI_Session).filter(
                FastAPI_Session.session_key == self.session_key
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
    
    