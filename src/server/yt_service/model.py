from typing import Optional
from pydantic import BaseModel

class CaptionInsertRequest(BaseModel):
    video_id: str
    language: str
    name: Optional[str] = None
    is_draft: Optional[bool] = False
    is_cc: Optional[bool] = False

class CaptionUpdateRequest(BaseModel):
    caption_id: str
    is_draft: Optional[bool] = None
    is_cc: Optional[bool] = None

class CaptionResponse(BaseModel):
    id: str
    video_id: str
    language: str
    name: Optional[str]
    is_draft: bool
    is_cc: bool