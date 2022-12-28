
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, Response, status, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Any
import os
import pandas as pd
from report import TakeoutReport
import dotenv
import time
import zipfile
from io import BytesIO
import uuid
import logging
# from fastapi.logger import logger
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import Column, String, JSON, Boolean

from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger("uvicorn.default")

SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


Base = declarative_base()


class Report(Base):
    __tablename__ = "report"
    id = Column(String, primary_key=True, index=True)
    takeout = Column(JSON)
    ready = Column(Boolean, default=False)


def get_report(db: Session, id: str) -> Report | None:
    return db.query(Report).filter(Report.id == id).first()


def write_report(db: Session, id: str, takeout: dict, ready: bool):
    report = get_report(db, id)
    if report is not None:
        # delete report if exists, act like update
        db.delete(report)
    report = Report(id=id, takeout=takeout, ready=ready)
    db.add(report)
    db.commit()
    db.refresh(report)


class ReportDTO(BaseModel):
    id: str
    takeout: Optional[dict]
    ready: bool

    class Config:
        orm_mode = True


dotenv.load_dotenv()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Branche Winter Activity",
              description="""
The first Branche winter is coming...
            """)
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def generate_report(api_key: list[str], dirname: str, id_generated: uuid.UUID, db: Session):
    write_report(db, str(id_generated), {}, False)
    logger.info(f"report added to db queue buffer, id: {str(id_generated)}")
    takeout = TakeoutReport(
        api_key, dirname).generate_report()
    logger.info("report generated, id: {}".format(id_generated))
    write_report(db, str(id_generated), takeout, True)


@app.get("/")
async def root():
    return {"message": "Pong"}


@app.post("/upload", summary="NOTE: Required to be protected")
def upload(file: UploadFile, res: Response, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if file.__sizeof__() > 10 * 1024 * 1024 or file.content_type != "application/zip":
        res.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "File too large or not a zip file."}
    else:
        dirname = f'{os.getcwd()}/upload/{int(time.time())}-{file.filename}'
        file_to_read = BytesIO(file.file.read())
        zipfile.ZipFile(file_to_read, 'r').extractall(dirname)
        id_generated = uuid.uuid4()
        keysFile = open(f'{os.getcwd()}/keys.txt', 'r')
        keys = keysFile.readlines()
        background_tasks.add_task(
            generate_report, keys, dirname, id_generated, db)
        return {"id": id_generated}


@app.get("/data/", response_model=ReportDTO)
def get_data(id: str, db: Session = Depends(get_db)):
    report = get_report(db, id)
    if report is not None:
        return report
    else:
        raise HTTPException(status_code=404, detail="Report not found")
