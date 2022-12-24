from fastapi import FastAPI, File, UploadFile, BackgroundTasks, Response, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Union
import json
import os
import pandas as pd
from report import TakeoutReport
import dotenv
import tempfile
import time
import zipfile
from io import BytesIO
import uuid
from fastapi.logger import logger
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Branche Winter Activity",
              description="""
The first Branche winter is coming...
            """)

dotenv.load_dotenv()

QUEUE_BUFFER = {}

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=[""],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Pong"}


def generate_report(api_key, dirname, id_generated: uuid.UUID):
    QUEUE_BUFFER[str(id_generated)] = {"ready": False}
    logger.info("report added to queue buffer, id: {}".format(id_generated))
    takeout = TakeoutReport(
        api_key, dirname).generate_report()
    logger.info("report generated, id: {}".format(id_generated))
    QUEUE_BUFFER[str(id_generated)] = {"takeout": takeout, "ready": True}


@app.post("/upload", summary="NOTE: Required to be protected")
async def upload(file: UploadFile, res: Response, background_tasks: BackgroundTasks):
    if file.__sizeof__() > 10 * 1024 * 1024 or file.content_type != "application/zip":
        res.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "File too large or not a zip file."}
    else:
        dirname = f'{os.getcwd()}/upload/{int(time.time())}-{file.filename}'
        file_to_read = BytesIO(file.file.read())
        zipfile.ZipFile(file_to_read, 'r').extractall(dirname)
        # api_key = os.getenv("YOUTUBE_API_KEY")
        id_generated = uuid.uuid4()
        keysFile = open(f'{os.getcwd()}/keys.txt', 'r')
        keys = keysFile.readlines()
        background_tasks.add_task(
            generate_report, keys, dirname, id_generated)
        return {"id": id_generated}


@app.get("/data/")
async def get_data(id: str, response: Response):
    # print(id, QUEUE_BUFFER)
    if id in QUEUE_BUFFER:
        data = QUEUE_BUFFER[id]
        # if data["ready"]:
        # del QUEUE_BUFFER[id]
        return {"id": id, "data": data}
    else:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": "id not found"}
