from reports_sql import Reports
from helptks_sql import HelpTKs
from chats_nosql import Chats
from strikes_nosql import Strikes
import logging as logger
import time
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import sys
import os
import mongomock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'lib')))
from lib.utils import sentry_init, time_to_string, get_test_engine

time_start = time.time()

logger.basicConfig(format='%(levelname)s: %(asctime)s - %(message)s',
                   stream=sys.stdout, level=logger.INFO)
logger.info("Starting the app")
load_dotenv()

DEBUG_MODE = os.getenv("DEBUG_MODE").title() == "True"
if DEBUG_MODE:
    logger.getLogger().setLevel(logger.DEBUG)
logger.info("DEBUG_MODE: " + str(DEBUG_MODE))

sentry_init()

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

    client = mongomock.MongoClient()
    chats_manager = Chats(test_client=client)
    strikes_manager = Strikes(test_client=client)
else:
    reports_manager = Reports()
    help_tks_manager = HelpTKs()
    chats_manager = Chats()
    strikes_manager = Strikes()

VALID_REPORT_TYPES = {"ACCOUNT", "SERVICE"}
REQUIRED_REPORT_FIELDS = {"title", "description", "complainant", "type", "target_identifier"}
REQUIRED_HELP_TK_FIELDS = {"title", "description"}
REQUIRED_HELP_TK_UPDATE_FIELDS = {"comment", "resolved"}
REQUIRED_SUPPORT_CHAT_FIELDS = {"message", "tk_type", "support_agent"}
VALID_STRIKE_TYPES = {"HIGH", "MEDIUM", "LOW"}
REQUIRED_STRIKE_FIELDS = {"user_id", "report_tk", "strike_type", "strike_reason"}
REQUIRED_AMMEND_STRIKE_FIELDS = {"user_id", "report_tk", "ammend_reason"}

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
def create_help_tk(requester_id: str, body: dict):
    if not all([field in body for field in REQUIRED_HELP_TK_FIELDS]):
        missing_fields = REQUIRED_HELP_TK_FIELDS - set(body.keys())
        raise HTTPException(status_code=400, detail=f"Missing fields: {', '.join(missing_fields)}")
    extra_fields = REQUIRED_HELP_TK_FIELDS - set(body.keys())
    if extra_fields:
        raise HTTPException(status_code=400, detail=f"Extra fields: {', '.join(extra_fields)}")
    if len(body["title"]) == 0 or len(body["description"]) == 0:
        raise HTTPException(status_code=400, detail="Title and description cannot be empty")
    uuid = help_tks_manager.insert(**body, requester=requester_id)
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
def update_help_tk(uuid: str, body: dict):
    if not all([field in body for field in REQUIRED_HELP_TK_UPDATE_FIELDS]):
        missing_fields = REQUIRED_HELP_TK_UPDATE_FIELDS - set(body.keys())
        raise HTTPException(status_code=400, detail=f"Missing fields: {', '.join(missing_fields)}")
    extra_fields = REQUIRED_HELP_TK_UPDATE_FIELDS - set(body.keys())
    if extra_fields:
        raise HTTPException(status_code=400, detail=f"Extra fields: {', '.join(extra_fields)}")
    if len(body["comment"]) == 0:
        raise HTTPException(status_code=400, detail="Comment cannot be empty")
    result = help_tks_manager.update(uuid, **body)
    if not result:
        raise HTTPException(status_code=400, detail="Error while updating the report")
    return {"status": "ok"}

@app.put("/chats/{uuid}")
def update_support_chat(uuid: str, body: dict):
    if not all([field in body for field in REQUIRED_SUPPORT_CHAT_FIELDS]):
        missing_fields = REQUIRED_SUPPORT_CHAT_FIELDS - set(body.keys())
        raise HTTPException(status_code=400, detail=f"Missing fields: {', '.join(missing_fields)}")
    extra_fields = REQUIRED_SUPPORT_CHAT_FIELDS - set(body.keys())
    if extra_fields:
        raise HTTPException(status_code=400, detail=f"Extra fields: {', '.join(extra_fields)}")
    if len(body["message"]) == 0:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    if body["tk_type"] not in {"HELP", "REPORT"}:
        raise HTTPException(status_code=400, detail="Invalid tk_type, must be 'HELP' or 'REPORT'")
    tks_manager = help_tks_manager if body["tk_type"] == "HELP" else reports_manager
    if not tks_manager.get(uuid):
        raise HTTPException(status_code=404, detail=f"{body['tk_type']} tk {uuid} not found")
    
    sender = "SUPPORT_AGENT" if body["support_agent"] else "USER"
    if not chats_manager.insert_message(body["message"], sender, uuid):
        raise HTTPException(status_code=400, detail="Error while sending the message")
    return {"status": "ok"}

@app.get("/chats/{uuid}")
def get_chat_messages(uuid: str, limit: int, offset: int):
    messages = chats_manager.get_messages(uuid, limit, offset)
    if not messages:
        raise HTTPException(status_code=404, detail="Chat not found")
    total_messages = chats_manager.count_messages(uuid)
    return {"status": "ok", "messages": messages, "total_messages": total_messages}

@app.put("/strikes/{user_id}")
def add_strike(user_id: str, body: dict):
    if not all([field in body for field in REQUIRED_STRIKE_FIELDS]):
        missing_fields = REQUIRED_STRIKE_FIELDS - set(body.keys())
        raise HTTPException(status_code=400, detail=f"Missing fields: {', '.join(missing_fields)}")
    extra_fields = REQUIRED_STRIKE_FIELDS - set(body.keys())
    if extra_fields:
        raise HTTPException(status_code=400, detail=f"Extra fields: {', '.join(extra_fields)}")
    if body["strike_type"] not in VALID_STRIKE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid strike type, must be one of {', '.join(VALID_STRIKE_TYPES)}")
    if len(body["strike_reason"]) == 0:
        raise HTTPException(status_code=400, detail="Strike reason cannot be empty")
    
    report = reports_manager.get(body["report_tk"])
    if not report:
        raise HTTPException(status_code=404, detail=f"Report ticket {body['report_tk']} not found")
    if user_id not in {report["complainant"], report["target_identifier"]}:
        raise HTTPException(status_code=400, detail="User not involved in the report")
    
    result_suspension = strikes_manager.add_strike(user_id, **body)
    if result_suspension is None:
        raise HTTPException(status_code=400, detail="Error while adding the strike")
    if result_suspension is False:
        return {"status": "ok", "suspension": False}
    return {"status": "ok", "suspension": True}
    