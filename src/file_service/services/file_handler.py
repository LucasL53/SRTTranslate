# from ..main import TargetLanguage, UPLOAD_DIR, TRANSLATED_DIR


# def handle_file_upload(file: UploadFile = File(...)):
#     file_path = os.path.join(UPLOAD_DIR, file.filename)
#     with open(file_path, "wb") as f:
#         shutil.copyfileobj(file.file, f)
#     return {"filename": file.filename}


# # TODO: Redesign the process_translation function to use the new translation service
# def process_translation(file_path, target_lang: TargetLanguage):
#     if target_lang == JA:
#         srt_translate_JA(file_path)
#     elif target_lang == KO:
#         srt_translate_KO(file_path)
#     elif target_lang == ES:
#         srt_translate_ES(file_path)
#     elif target_lang == CH:
#         srt_translate_CH(file_path)
#     return {"filename": file_path.split("/")[-1]}
