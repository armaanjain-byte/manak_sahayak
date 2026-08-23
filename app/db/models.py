from sqlalchemy import Column, Integer, String, Date, ForeignKey
from app.db.session import Base

class Standard(Base):
    __tablename__ = "standards"
    id = Column(Integer, primary_key=True)
    is_number = Column(String, unique=True)
    title = Column(String)
    scope = Column(String)
    status = Column(String)
    
class QCO(Base):
    __tablename__ = "qcos"
    id = Column(Integer, primary_key=True)
    qco_identifier = Column(String, unique=True)
    product_category = Column(String)
    effective_date = Column(Date)

class Laboratory(Base):
    __tablename__ = "laboratories"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    recognition_status = Column(String)
    validity = Column(Date)
    
class HallmarkingRecord(Base):
    __tablename__ = "hallmarking_records"
    id = Column(Integer, primary_key=True)
    huid = Column(String, unique=True)
    article_type = Column(String)
    
class VocabularyConcept(Base):
    __tablename__ = "vocabulary_concepts"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)

class VocabularyAlias(Base):
    __tablename__ = "vocabulary_aliases"
    id = Column(Integer, primary_key=True)
    alias = Column(String)
    concept_id = Column(Integer, ForeignKey("vocabulary_concepts.id"))
