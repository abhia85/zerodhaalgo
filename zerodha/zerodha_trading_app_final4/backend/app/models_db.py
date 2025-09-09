
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os
from datetime import datetime, timedelta

DB_URL = os.getenv('DATABASE_URL', 'sqlite:///./data.db')
engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith('sqlite') else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    kite_user_id = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Strategy(Base):
    __tablename__ = 'strategies'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    payload = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship('User')

class TradeJournal(Base):
    __tablename__ = 'trades'
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id'), nullable=True)
    symbol = Column(String, index=True)
    side = Column(String)
    qty = Column(Integer)
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    status = Column(String, default='OPEN')  # OPEN, CLOSED, SIMULATED
    created_at = Column(DateTime, default=datetime.utcnow)
    strategy = relationship('Strategy')

class TokenStore(Base):
    __tablename__ = 'tokens'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    token = Column(Text)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class DailyLoss(Base):
    __tablename__ = 'daily_loss'
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow, index=True)
    loss = Column(Float, default=0.0)

def init_db():
    Base.metadata.create_all(bind=engine)
