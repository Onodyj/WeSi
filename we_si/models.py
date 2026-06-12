"""
Database models for WeSi application.
"""
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime,
    ForeignKey, Enum, LargeBinary, Boolean, Float, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import enum

Base = declarative_base()


class SubscriptionTier(enum.Enum):
    """Subscription tier levels."""
    FREE = "free"
    STANDARD = "standard"
    FULL = "full"


class JobStatus(enum.Enum):
    """Job status values."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    """User model."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    site_analyses = relationship("SiteAnalysis", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"


class Subscription(Base):
    """Subscription model."""
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)
    tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.FREE, nullable=False)
    max_pages_per_run = Column(Integer, default=10, nullable=False)
    max_pages_stored = Column(Integer, default=50, nullable=False)
    max_analyses_per_month = Column(Integer, default=5, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="subscription")
    
    def __repr__(self):
        return f"<Subscription(user_id={self.user_id}, tier={self.tier.value})>"
    
    @classmethod
    def get_tier_limits(cls, tier: SubscriptionTier) -> dict:
        """Get limits for a subscription tier."""
        limits = {
            SubscriptionTier.FREE: {
                'max_pages_per_run': 10,
                'max_pages_stored': 50,
                'max_analyses_per_month': 5,
                'max_depth': 2,
                'include_ai_assistant': False,
                'include_google_docs': False
            },
            SubscriptionTier.STANDARD: {
                'max_pages_per_run': 50,
                'max_pages_stored': 500,
                'max_analyses_per_month': 20,
                'max_depth': 3,
                'include_ai_assistant': True,
                'include_google_docs': True
            },
            SubscriptionTier.FULL: {
                'max_pages_per_run': 200,
                'max_pages_stored': 2000,
                'max_analyses_per_month': 100,
                'max_depth': 5,
                'include_ai_assistant': True,
                'include_google_docs': True
            }
        }
        return limits.get(tier, limits[SubscriptionTier.FREE])


class APIKey(Base):
    """Encrypted API key storage."""
    __tablename__ = 'api_keys'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    service = Column(String(50), nullable=False)  # 'openai', 'google', etc.
    encrypted_key = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    def __repr__(self):
        return f"<APIKey(user_id={self.user_id}, service='{self.service}')>"


class SiteAnalysis(Base):
    """Site analysis job and results."""
    __tablename__ = 'site_analyses'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    base_url = Column(String(500), nullable=False)
    domain = Column(String(255), nullable=False, index=True)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    progress = Column(Float, default=0.0)  # 0-100
    pages_crawled = Column(Integer, default=0)
    pages_analyzed = Column(Integer, default=0)
    error_message = Column(Text)
    
    # Analysis results stored as JSON
    summary = Column(JSON)
    insights = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="site_analyses")
    pages = relationship("PageAnalysis", back_populates="site_analysis", cascade="all, delete-orphan")
    conversations = relationship("AssistantConversation", back_populates="site_analysis", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<SiteAnalysis(id={self.id}, domain='{self.domain}', status={self.status.value})>"


class PageAnalysis(Base):
    """Individual page analysis results."""
    __tablename__ = 'page_analyses'
    
    id = Column(Integer, primary_key=True)
    site_analysis_id = Column(Integer, ForeignKey('site_analyses.id'), nullable=False)
    url = Column(String(1000), nullable=False)
    status_code = Column(Integer)
    depth = Column(Integer, default=0)
    load_time = Column(Float)
    
    # Analysis data stored as JSON
    analysis_data = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    site_analysis = relationship("SiteAnalysis", back_populates="pages")
    
    def __repr__(self):
        return f"<PageAnalysis(id={self.id}, url='{self.url}')>"


class AssistantConversation(Base):
    """AI Assistant conversation history."""
    __tablename__ = 'assistant_conversations'
    
    id = Column(Integer, primary_key=True)
    site_analysis_id = Column(Integer, ForeignKey('site_analyses.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    site_analysis = relationship("SiteAnalysis", back_populates="conversations")
    messages = relationship("AssistantMessage", back_populates="conversation", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AssistantConversation(id={self.id}, site_analysis_id={self.site_analysis_id})>"


class AssistantMessage(Base):
    """Individual messages in an assistant conversation."""
    __tablename__ = 'assistant_messages'
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('assistant_conversations.id'), nullable=False)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("AssistantConversation", back_populates="messages")
    
    def __repr__(self):
        return f"<AssistantMessage(id={self.id}, role='{self.role}')>"


def init_db(database_url: str = 'sqlite:///wesi.db'):
    """
    Initialize the database.
    
    Args:
        database_url: Database connection URL
        
    Returns:
        Tuple of (engine, Session)
    """
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session
