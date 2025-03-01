import os
from typing import Optional, List
from fastapi import HTTPException, Depends, UploadFile, File, Form, Body

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload

from ..file_service.main import app
from .model import CaptionInsertRequest, CaptionResponse, CaptionUpdateRequest

# Helper function to get authenticated YouTube service
def get_authenticated_service(token: str):
    pass
    # try:
    #     # Load credentials from the token
    #     credentials = google.oauth2.credentials.Credentials.from_authorized_user_info(
    #         info={"token": token},
    #         scopes=SCOPES
    #     )
        
    #     # Build the YouTube service
    #     return build('youtube', 'v3', credentials=credentials)
    # except Exception as e:
    #     raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

# Endpoint to insert a caption
@app.post("/captions", response_model=CaptionResponse)
async def insert_caption(
    request: CaptionInsertRequest,
    caption_file: UploadFile = File(...),
    youtube = Depends(get_authenticated_service)
):
    try:
        # Read the caption file content
        caption_content = await caption_file.read()
        
        # Prepare the request body
        body = {
            'snippet': {
                'videoId': request.video_id,
                'language': request.language,
                'name': request.name,
                'isDraft': request.is_draft,
                'isCC': request.is_cc
            }
        }
        
        # Insert the caption
        response = youtube.captions().insert(
            part='snippet',
            body=body,
            media_body=caption_content,
            media_mime_type=get_mime_type(caption_file.filename)
        ).execute()
        
        # Return the response
        return CaptionResponse(
            id=response['id'],
            video_id=response['snippet']['videoId'],
            language=response['snippet']['language'],
            name=response['snippet'].get('name'),
            is_draft=response['snippet']['isDraft'],
            is_cc=response['snippet']['isCC']
        )
    except HttpError as e:
        raise HTTPException(status_code=e.resp.status, detail=e.content.decode())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# Endpoint to update a caption
@app.put("/captions/{caption_id}", response_model=CaptionResponse)
async def update_caption(
    caption_id: str,
    request: CaptionUpdateRequest = Body(...),
    caption_file: Optional[UploadFile] = File(None),
    youtube = Depends(get_authenticated_service)
):
    try:
        # Prepare the request body
        body = {
            'id': caption_id,
            'snippet': {}
        }
        
        # Add optional fields if provided
        if request.is_draft is not None:
            body['snippet']['isDraft'] = request.is_draft
        if request.is_cc is not None:
            body['snippet']['isCC'] = request.is_cc
        
        # Prepare media body if caption file is provided
        media_body = None
        media_mime_type = None
        if caption_file:
            media_body = await caption_file.read()
            media_mime_type = get_mime_type(caption_file.filename)
        
        # Update the caption
        response = youtube.captions().update(
            part='snippet',
            body=body,
            media_body=media_body,
            media_mime_type=media_mime_type
        ).execute()
        
        # Return the response
        return CaptionResponse(
            id=response['id'],
            video_id=response['snippet']['videoId'],
            language=response['snippet']['language'],
            name=response['snippet'].get('name'),
            is_draft=response['snippet']['isDraft'],
            is_cc=response['snippet']['isCC']
        )
    except HttpError as e:
        raise HTTPException(status_code=e.resp.status, detail=e.content.decode())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# Endpoint to list captions for a video
@app.get("/videos/{video_id}/captions", response_model=List[CaptionResponse])
def list_captions(
    video_id: str,
    youtube = Depends(get_authenticated_service)
):
    try:
        # List captions for the video
        response = youtube.captions().list(
            part='snippet',
            videoId=video_id
        ).execute()
        
        # Process and return the captions
        captions = []
        for item in response.get('items', []):
            captions.append(CaptionResponse(
                id=item['id'],
                video_id=item['snippet']['videoId'],
                language=item['snippet']['language'],
                name=item['snippet'].get('name'),
                is_draft=item['snippet']['isDraft'],
                is_cc=item['snippet']['isCC']
            ))
        
        return captions
    except HttpError as e:
        raise HTTPException(status_code=e.resp.status, detail=e.content.decode())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# Helper function to determine the MIME type based on the file extension
def get_mime_type(filename: str) -> str:
    if filename.endswith('.srt'):
        return 'application/x-subrip'
    elif filename.endswith('.vtt'):
        return 'text/vtt'
    elif filename.endswith('.ttml') or filename.endswith('.xml'):
        return 'application/ttml+xml'
    else:
        return 'text/plain'