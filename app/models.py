from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class Relation(str, Enum):
    CORROBORATED = "Corroborated"
    CONTRADICTED = "Contradicted"
    CONTEXT_RESOLVED = "Context-Resolved"
    RELATED = "Related"

class Evidence(BaseModel):
    document_id: str
    filename: str
    page: int = Field(ge=1)
    quote: str = Field(min_length=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    verified: bool = True
    verification_note: Optional[str] = None

class Fact(BaseModel):
    id: str
    subject: str
    predicate: str
    value: str
    normalized_value: Optional[str] = None
    unit: Optional[str] = None
    date: Optional[str] = None
    scope: Optional[str] = None
    evidence: Evidence
    confidence: float = Field(ge=0, le=1)
    extraction_note: Optional[str] = None

class Relationship(BaseModel):
    id: str
    source_fact_id: str
    target_fact_id: str
    relation: Relation
    rationale: str
    confidence: float = Field(ge=0, le=1)

class DocumentRecord(BaseModel):
    id: str
    filename: str
    publication_date: Optional[str] = None
    pages: int

class KnowledgeLayer(BaseModel):
    documents: list[DocumentRecord] = Field(default_factory=list)
    facts: list[Fact] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
