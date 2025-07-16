from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, create_engine, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import json
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    domain = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    forms = relationship("Form", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant(id={self.id}, name='{self.name}')>"

class Form(Base):
    __tablename__ = "forms"
    
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    schema = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    submissions = relationship("FormSubmission", back_populates="form", cascade="all, delete-orphan")
    tenant = relationship("Tenant", back_populates="forms")

    __table_args__ = (
        Index('idx_tenant_form', 'tenant_id', 'id'),
    )

    def __repr__(self):
        return f"<Form(id={self.id}, title='{self.title}')>"

class FormSubmission(Base):
    __tablename__ = "form_submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("forms.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    data = Column(JSON, nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    form = relationship("Form", back_populates="submissions")
    tenant = relationship("Tenant")

    __table_args__ = (
        Index('idx_tenant_submission', 'tenant_id', 'form_id', 'submitted_at'),
    )

    def __repr__(self):
        return f"<FormSubmission(id={self.id}, form_id={self.form_id})>"

# Create SQLite database engine
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/formio.db")
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
    json_deserializer=lambda obj: json.loads(obj)
)

# Create all tables
Base.metadata.create_all(bind=engine)

# Create session for initialization
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_or_create_default_tenant():
    """Get or create the default tenant for single-tenant usage"""
    try:
        session = SessionLocal()
        
        # Check if default tenant exists
        default_tenant = session.query(Tenant).filter(
            Tenant.name == "Default Tenant"
        ).first()
        
        if not default_tenant:
            logger.info("Creating default tenant...")
            default_tenant = Tenant(
                name="Default Tenant",
                domain="localhost"
            )
            session.add(default_tenant)
            session.commit()
            session.refresh(default_tenant)
            logger.info(f"Default tenant created with ID: {default_tenant.id}")
        
        tenant_id = default_tenant.id
        session.close()
        return tenant_id
        
    except Exception as e:
        logger.error(f"Error creating/getting default tenant: {str(e)}")
        if 'session' in locals():
            session.rollback()
            session.close()
        raise

# Initialize default tenant on module import
try:
    DEFAULT_TENANT_ID = get_or_create_default_tenant()
    logger.info(f"Using default tenant ID: {DEFAULT_TENANT_ID}")
except Exception as e:
    logger.error(f"Failed to initialize default tenant: {str(e)}")
    DEFAULT_TENANT_ID = None 