from reports_sql import Reports
from helptks_sql import HelpTKs
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
    title="Support API",
    description="API for support reports management",
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
    reports_manager = Reports(engine=test_engine)
    help_tks_manager = HelpTKs(engine=test_engine)
else:
    reports_manager = Reports()
    help_tks_manager = HelpTKs()

VALID_REPORT_TYPES = {"ACCOUNT", "SERVICE"}
REQUIRED_REPORT_FIELDS = {"title", "description", "complainant", "type", "target_identifier"}

starting_duration = time_to_string(time.time() - time_start)
logger.info(f"Support API started in {starting_duration}")

# TODO: (General) -> Create tests for each endpoint && add the required checks in each endpoint

@app.put("/accounts/{username}")
def report_account(username: str, body: dict):
    data = {key: value for key, value in body.items() if key in REQUIRED_REPORT_FIELDS}
    data["type"] = "ACCOUNT"
    data["target_identifier"] = username

    if not all([field in data for field in REQUIRED_REPORT_FIELDS]):
        missing_fields = REQUIRED_REPORT_FIELDS - set(data.keys())
        raise HTTPException(status_code=400, detail=f"Missing fields: {', '.join(missing_fields)}")
    
    uuid = reports_manager.insert(**data)
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
    
    uuid = reports_manager.insert(**data)
    if not uuid:
        raise HTTPException(status_code=400, detail="Error while inserting the report")
    return {"status": "ok", "report_id": uuid}

@app.get("/accounts/{username}")
def get_account_reports(username: str):
    reports = reports_manager.get_by_target("ACCOUNT", username)
    if not reports:
        raise HTTPException(status_code=404, detail="Reports not found")
    return reports

@app.get("/services/{uuid}")
def get_service_reports(uuid: str):
    reports = reports_manager.get_by_target("SERVICE", uuid)
    if not reports:
        raise HTTPException(status_code=404, detail="Reports not found")
    return reports

@app.put("/help/new/{requester_id}")
def create_help_tk(requester_id: str, title: str, description: str):
    uuid = help_tks_manager.insert(title, description, requester_id)
    if not uuid:
        raise HTTPException(status_code=400, detail="Error while inserting the report")
    return {"status": "ok", "report_id": uuid}

@app.get("/help/{uuid}")
def get_help_tk(uuid: str):
    report = help_tks_manager.get(uuid)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@app.get("/help/list/{requester_id}")
def get_help_tks(requester_id: str):
    reports = help_tks_manager.get_by_user(requester_id)
    if not reports:
        raise HTTPException(status_code=404, detail="Reports not found")
    return reports

@app.put("/help/{uuid}")
def update_help_tk(uuid: str, comment: str, resolved: bool):
    result = help_tks_manager.update(uuid, comment, resolved)
    if not result:
        raise HTTPException(status_code=400, detail="Error while updating the report")
    return {"status": "ok"}