from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import declarative_base, relationship
import datetime

Base = declarative_base()

class Campaign(Base):
    __tablename__ = 'campaigns'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    entities = relationship("Entity", back_populates="campaign")
    documents = relationship("Document", back_populates="campaign")

class Document(Base):
    """Tracks files (PDFs/URLs) ingested into the system."""
    __tablename__ = 'documents'
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), nullable=True) # Null = Global Library
    title = Column(String, nullable=False)
    source_type = Column(String) # 'pdf', 'url', 'note'
    source_path = Column(String)
    category = Column(String, default="Uncategorized")
    content_hash = Column(String, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    indexed_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    campaign = relationship("Campaign", back_populates="documents")

class Entity(Base):
    """NPCs, Locations, Player Characters."""
    __tablename__ = 'entities'
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), nullable=False)
    name = Column(String, nullable=False)
    entity_type = Column(String) # 'NPC', 'PC', 'Location', 'Monster'
    stat_block_json = Column(Text, nullable=True) # Stored JSON stats
    
    campaign = relationship("Campaign", back_populates="entities")
    relations_from = relationship("Relationship", foreign_keys='Relationship.source_entity_id', back_populates="source_entity")
    relations_to = relationship("Relationship", foreign_keys='Relationship.target_entity_id', back_populates="target_entity")

class Relationship(Base):
    """Graph linking entities based on events/table talk."""
    __tablename__ = 'relationships'
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), nullable=False)
    source_entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    target_entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    description = Column(Text, nullable=False) # e.g. "Met in combat", "Insulted"
    source_log = Column(Text) # Where this came from (e.g., Fathom transcript snippet)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    source_entity = relationship("Entity", foreign_keys=[source_entity_id], back_populates="relations_from")
    target_entity = relationship("Entity", foreign_keys=[target_entity_id], back_populates="relations_to")
