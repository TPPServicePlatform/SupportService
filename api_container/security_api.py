from reports_sql import Reports
import logging as logger
import time
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))
from lib.utils import time_to_string, get_test_engine

time_start = time.time()

logger.basicConfig(format='%(levelname)s: %(asctime)s - %(message)s',
                   stream=sys.stdout, level=logger.INFO)
logger.info("Starting the app")
load_dotenv()

DEBUG_MODE = os.getenv("DEBUG_MODE").title() == "True"
if DEBUG_MODE:
    logger.getLogger().setLevel(logger.DEBUG)
logger.info("DEBUG_MODE: " + str(DEBUG_MODE))

app = FastAPI(
    title="Security API",
    description="API for security reports management",
    version="1.0.0",
    root_path=os.getenv("ROOT_PATH")
)

origins = [
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.getenv('TESTING'):
    test_engine = get_test_engine()
    sql_manager = Reports(engine=test_engine)
else:
    sql_manager = Reports()

VALID_REPORT_TYPES = {"ACCOUNT", "SERVICE"}
REQUIRED_REPORT_FIELDS = {"title", "description", "complainant", "type", "target_identifier"}

starting_duration = time_to_string(time.time() - time_start)
logger.info(f"Security API started in {starting_duration}")

# TODO: (General) -> Create tests for each endpoint && add the required checks in each endpoint

@app.put("/accounts/{username}")
def report_account(username: str, body: dict):
    data = {key: value for key, value in body.items() if key in REQUIRED_REPORT_FIELDS}
    data["type"] = "ACCOUNT"
    data["target_identifier"] = username

    if not all([field in data for field in REQUIRED_REPORT_FIELDS]):
        missing_fields = REQUIRED_REPORT_FIELDS - set(data.keys())
        raise HTTPException(status_code=400, detail=f"Missing fields: {', '.join(missing_fields)}")
    
    uuid = sql_manager.insert(**data)
    if not uuid:
        raise HTTPException(status_code=400, detail="Error while inserting the report")
    return {"status": "ok", "report_id": uuid}

@app.put("/services/{uuid}")
def report_service(uuid: str, body: dict):
    data = {key: value for key, value in body.items() if key in REQUIRED_REPORT_FIELDS}
    data["type"] = "SERVICE"
    data["target_identifier"] = uuid

    if not all([field in data for field in REQUIRED_REPORT_FIELDS]):
        missing_fields = REQUIRED_REPORT_FIELDS - set(data.keys())
        raise HTTPException(status_code=400, detail=f"Missing fields: {', '.join(missing_fields)}")
    
    uuid = sql_manager.insert(**data)
    if not uuid:
        raise HTTPException(status_code=400, detail="Error while inserting the report")
    return {"status": "ok", "report_id": uuid}

@app.get("/accounts/{username}")
def get_account_reports(username: str):
    reports = sql_manager.get_by_target("ACCOUNT", username)
    if not reports:
        raise HTTPException(status_code=404, detail="Reports not found")
    return reports

@app.get("/services/{uuid}")
def get_service_reports(uuid: str):
    reports = sql_manager.get_by_target("SERVICE", uuid)
    if not reports:
        raise HTTPException(status_code=404, detail="Reports not found")
    return reports
