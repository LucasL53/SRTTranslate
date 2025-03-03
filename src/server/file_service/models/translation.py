from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from .translation_job import TranslationStatus

class TranslationJobCreate(BaseModel):
    original_filename: str
    target_language: str
    owner_id: str

class TranslationJobResponse(BaseModel):
    id: int
    original_filename: str
    target_language: str
    status: TranslationStatus
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None

    class Config:
        from_attributes = True
