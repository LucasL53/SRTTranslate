from fastapi import HTTPException, UploadFile

def validate_srt_file(file: UploadFile):
    if not file.filename.endswith('.srt'):
        raise HTTPException(status_code=400, detail="Only .srt files are allowed")
    if file.size > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File size too large. Maximum size is 10MB")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Check if file is empty
    file_content = file.file.read()
    if len(file_content) == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    
    # Reset file pointer after reading
    file.file.seek(0)
    return file
