from datetime import date, datetime
from typing import List, Optional
from sqlalchemy import String, Date, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class QCOStandardMapping(Base):
    __tablename__ = "qco_standard_mappings"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    qco_bis_entity_id: Mapped[str] = mapped_column(ForeignKey("qcos.bis_entity_id", ondelete="CASCADE"))
    standard_bis_entity_id: Mapped[str] = mapped_column(ForeignKey("standards.bis_entity_id", ondelete="CASCADE"))

class Standard(Base):
    __tablename__ = "standards"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    bis_entity_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    is_number: Mapped[str] = mapped_column(String, unique=True)
    title: Mapped[str] = mapped_column(String)
    scope: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    source_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    qcos: Mapped[List["QCO"]] = relationship(
        secondary="qco_standard_mappings",
        primaryjoin="Standard.bis_entity_id == QCOStandardMapping.standard_bis_entity_id",
        secondaryjoin="QCO.bis_entity_id == QCOStandardMapping.qco_bis_entity_id",
        back_populates="standards"
    )

class QCO(Base):
    __tablename__ = "qcos"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    bis_entity_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    qco_identifier: Mapped[str] = mapped_column(String, unique=True)
    product_category: Mapped[str] = mapped_column(String)
    ministry: Mapped[str] = mapped_column(String)
    publication_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    exemptions: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    standards: Mapped[List["Standard"]] = relationship(
        secondary="qco_standard_mappings",
        primaryjoin="QCO.bis_entity_id == QCOStandardMapping.qco_bis_entity_id",
        secondaryjoin="Standard.bis_entity_id == QCOStandardMapping.standard_bis_entity_id",
        back_populates="qcos"
    )

class Laboratory(Base):
    __tablename__ = "laboratories"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    bis_entity_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    recognition_status: Mapped[str] = mapped_column(String)
    scope: Mapped[str] = mapped_column(String)
    validity: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    location: Mapped[str] = mapped_column(String)
    source_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

class HallmarkingRecord(Base):
    __tablename__ = "hallmarking_records"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    bis_entity_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    metal: Mapped[str] = mapped_column(String)
    article_type: Mapped[str] = mapped_column(String)
    huid: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True, nullable=True)
    jeweller_registration: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

class CanonicalConcept(Base):
    __tablename__ = "canonical_concepts"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    bis_entity_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    domain: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationships
    aliases: Mapped[List["ConceptAlias"]] = relationship(
        back_populates="canonical_concept", 
        cascade="all, delete-orphan"
    )

class ConceptAlias(Base):
    __tablename__ = "concept_aliases"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    alias: Mapped[str] = mapped_column(String)
    language: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("canonical_concepts.id"))

    # Relationships
    canonical_concept: Mapped["CanonicalConcept"] = relationship(back_populates="aliases")

class ConceptStandardMapping(Base):
    __tablename__ = "concept_standard_mappings"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("canonical_concepts.id"))
    standard_id: Mapped[int] = mapped_column(ForeignKey("standards.id"))
    validated: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationships
    canonical_concept: Mapped["CanonicalConcept"] = relationship()
    standard: Mapped["Standard"] = relationship()
