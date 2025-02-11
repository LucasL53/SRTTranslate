from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import os
import shutil

from ..translation_service.SRTTranslate import srt_translate
from ..translation_service.TargetLanguage import TargetLanguage


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
    ## TODO: Users can check on their own uploaded files
    return {"files": os.listdir(UPLOAD_DIR)}


# File upload endpoint
@app.post("/uploadfile/")
async def upload_file(
    file: UploadFile, target_lang: list[TargetLanguage], background_tasks: BackgroundTasks
):
    """
    Args:
        file (UploadFile, required): _description_. Defaults to File(...).
        target_lang (TargetLanguage], required): _description_. Defaults to [TargetLanguage.JA].

    Returns:
        status: completion status
    """
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    for lang in target_lang:
        background_tasks.add_task(srt_translate, file_path, lang)
    return {"status": "File uploaded and translated"}


# Fetch translated file endpoint
@app.get("/translatedfile/{filename}")
async def fetch_translated_file(filename: str, target_lang: TargetLanguage):
    file_path = os.path.join(TRANSLATED_DIR, f"{filename}-{target_lang.value}.srt")
    if not os.path.exists(file_path):
        uploaded_file_path = os.path.join(UPLOAD_DIR, f"{filename}.srt")
        if not os.path.exists(uploaded_file_path):
            raise HTTPException(status_code=404, detail=f"{filename} not found")
        else:
            file_name = srt_translate(uploaded_file_path, target_lang)
            file_path = os.path.join(TRANSLATED_DIR, file_name)
    return FileResponse(file_path)
