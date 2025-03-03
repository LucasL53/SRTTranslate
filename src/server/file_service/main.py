from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Depends, Header
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional
from uuid import uuid4
import os
import shutil

from ..translation_service.SRTTranslate import srt_translate
from ..translation_service.TargetLanguage import TargetLanguage
from .services.file_handler import validate_srt_file
from .database import get_db, engine
from .models.translation import TranslationJobResponse
from .models.translation_job import TranslationJob, TranslationStatus, Base

# SQL table create
Base.metadata.create_all(bind=engine)

app = FastAPI()

UPLOAD_DIR = "/Users/yunseolee/Documents/GitHub/SRTTranslate/src/file_service/uploads/"
TRANSLATED_DIR = "/Users/yunseolee/Documents/GitHub/SRTTranslate/src/file_service/translated/"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TRANSLATED_DIR, exist_ok=True)

# Dependency: Decode the Authorization header to get user info (if logged in)
def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Return user information if a valid OAuth token is provided;
    otherwise, return None to indicate an anonymous session.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header. Please include 'Bearer {your_token}"
        )
    
    token = authorization.replace("Bearer ", "")
    try:
        user_info = "" # TODO: Here you would decode/validate the token (for example, using google.oauth2.id_token)
        return user_info
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid Token: {str(e)}"
        )

# Dependency: Get a session identifier.
# If the user is logged in, use their persistent user_id.
# Otherwise, generate or retrieve a temporary anonymous id.
def get_session_id(current_user: Optional[dict] = Depends(get_current_user)):
    if current_user:
        return current_user["user_id"]
    return "anon-" + str(uuid4())

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the file service"}


# List files uploaded by the current session/user
@app.get("/files")
def read_files(db: Session = Depends(get_db), session_id: str = Depends(get_session_id)):
    """
    List only the files that belong to the current session (persistent if logged in, temporary if anonymous).
    """
    # Query the database for translation jobs owned by this session.
    jobs = db.query(TranslationJob).filter(TranslationJob.owner_id == session_id).all()
    files = [job.original_filename for job in jobs]
    return {"files": files}


# File upload endpoint
@app.post("/uploadfile/", response_model=TranslationJobResponse)
async def upload_file(
    file: UploadFile,
    target_lang: list[TargetLanguage],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_session_id)
):
    try:
        _ = validate_srt_file(file)
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Create translation jobs for each target language
        jobs = []
        for lang in target_lang:
            job = TranslationJob(
                original_filename=file.filename,
                target_language=lang.value,
                status=TranslationStatus.PENDING,
                owner_id = session_id
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            jobs.append(job)

            # Add translation task to background tasks
            background_tasks.add_task(
                process_translation,
                file_path,
                lang,
                job.id,
                db
            )

        return jobs[0]  # Return the first job for simplicity
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/translation/{job_id}", response_model=TranslationJobResponse)
async def get_translation_status(job_id: int, db: Session = Depends(get_db), session_id: str = Depends(get_session_id)):
    job = db.query(TranslationJob).filter(TranslationJob.id == job_id, TranslationJob.owner_id == session_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Translation job not found")
    return job.status
    

@app.get("/translations/", response_model=list[TranslationJobResponse])
async def list_translations(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_session_id)
):
    jobs = db.query(TranslationJob).filter(TranslationJob.owner_id == session_id).offset(skip).limit(limit).all()
    return jobs


@app.get("/download/{job_id}")
async def download_translation(job_id: int, db: Session = Depends(get_db)):
    job = db.query(TranslationJob).filter(TranslationJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Translation job not found")
    
    if job.status != TranslationStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Translation not completed yet")
    
    if not os.path.exists(job.translated_file_path):
        raise HTTPException(status_code=404, detail="Translated file not found")
    
    return FileResponse(
        job.translated_file_path,
        filename=os.path.basename(job.translated_file_path),
        media_type="application/x-subrip"
    )


async def process_translation(
    file_path: str,
    target_lang: TargetLanguage,
    job_id: int,
    db: Session
):
    """Background task to process translation and update job status"""
    try:
        # Update status to processing
        job = db.query(TranslationJob).filter(TranslationJob.id == job_id).first()
        job.status = TranslationStatus.PROCESSING
        db.commit()

        # Perform translation
        translated_subs = srt_translate(file_path, target_lang)

        # Save translated subtitles as a new file
        translated_filename = f"{job.original_filename}-{target_lang.value}.srt"
        translated_file_path = os.path.join(TRANSLATED_DIR, translated_filename)
        translated_subs.save(translated_file_path)

        # Update status to completed
        job.status = TranslationStatus.COMPLETED
        job.translated_file_path = translated_file_path
        db.commit()
    except Exception as e:
        # Update status to failed with error message
        job.status = TranslationStatus.FAILED
        job.error_message = str(e)
        db.commit()

# TODO: Use unique filenames to prevent collisions
# Implement file cleanup for old translations
# Move to cloud storage (AWS S3, Google Cloud Storage, etc.)
# Add file expiration dates
# Implement user-specific file access controls
