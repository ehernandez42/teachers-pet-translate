import os
import uuid

import uvicorn
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import deepl
from dotenv import load_dotenv
from elevenlabs import ElevenLabs
from contextlib import asynccontextmanager

from pydantic import BaseModel

app = FastAPI()
load_dotenv()

DEEPL_API_KEY = os.getenv("DEEPL_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")


class TranslationRequest(BaseModel):
    text: str


@app.get("/")
async def root():
    return {"message": "Hello, welcome to the translation API. Navigate to /translate-eng-to-span to get started!"}


AUDIO_DIR = "generated_audio"
os.makedirs(AUDIO_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    os.makedirs(AUDIO_DIR, exist_ok=True)
    print(f"Audio files will be stored in: {AUDIO_DIR}")
    yield


@app.post("/translate-eng-to-span")
async def translate(request: TranslationRequest):
    task_id = str(uuid.uuid4())
    try:
        token_credential = DefaultAzureCredential()
        azure_url = os.getenv("AZURE_CONTAINER")
        #ignore the yellow line; it says that the types don't match
        blob_service_client = BlobServiceClient(account_url=azure_url,
                                                credential=token_credential)

        translator = deepl.Translator(DEEPL_API_KEY)
        result = translator.translate_text(request.text, target_lang="ES")
        client = ElevenLabs(
            api_key=ELEVEN_API_KEY
        )
        audio = client.generate(
            text=f"{result}",
            voice="Rachel",
            model="eleven_multilingual_v2"
        )
        audio_bytes = b"".join(audio)
        # danger for large audio projects Depending on the size of the audio, this approach loads the entire audio
        # into memory. For very large audio files, you might need to consider a more memory-efficient streaming
        # approach.
        # another aspect is to take out the file path saving part that goes to your local storage; or maybe we have to deploy to find out what happens??
        filename = f"{task_id}.mp3"
        file_path = os.path.join(AUDIO_DIR, filename)
        blob_client = blob_service_client.get_blob_client(container="audio-files", blob=filename)

        with open(file_path, "wb") as f:
            f.write(audio_bytes)
        with open(file_path, "rb") as data:
            blob_client.upload_blob(data)
        return {"task_id": task_id, "message": "Audio generated successfully and sent to blob"}
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))


@app.get("/translate-eng-to-span/{task_id}")
async def download_audio(task_id: str):
    filename = f"{task_id}.mp3"
    file_path = os.path.join(AUDIO_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(file_path, media_type="audio/mpeg", filename=filename)

if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8000)

"""
Clerk/Convex

Now that you have a working implementation, here are a few things you might want to consider for the future:

File management: Consider implementing a cleanup mechanism to delete old audio files 
after a certain period or if they're no longer needed.

Error handling: You might want to add more specific error handling for different scenarios 
(e.g., API errors, file system errors).

Scaling: If you expect high traffic, you might need to consider how to scale this solution, possibly using background 
tasks or a queue system for audio generation.

Security: Ensure that your endpoints are properly secured, especially if this API will be publicly accessible.
Monitoring: Adding logging or monitoring can help you track usage and troubleshoot issues more easily.
"""
