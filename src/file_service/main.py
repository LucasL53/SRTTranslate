from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
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


# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the file service"}


@app.get("/files")
def read_files():
    """
    Endpoint to list all files in the upload directory.

    Returns:
        dict: A dictionary containing a list of filenames in the upload directory.
    """
    ## TODO: Users can only check on their own uploaded files
    return {"files": os.listdir(UPLOAD_DIR)}


# File upload endpoint
@app.post("/uploadfile/", response_model=TranslationJobResponse)
async def upload_file(
    file: UploadFile,
    target_lang: list[TargetLanguage],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
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
                status=TranslationStatus.PENDING
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
async def get_translation_status(job_id: int, db: Session = Depends(get_db)):
    job = db.query(TranslationJob).filter(TranslationJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Translation job not found")
    return job


@app.get("/translations/", response_model=list[TranslationJobResponse])
async def list_translations(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    jobs = db.query(TranslationJob).offset(skip).limit(limit).all()
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
