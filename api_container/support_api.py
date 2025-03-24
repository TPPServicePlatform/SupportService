from datetime import datetime, timedelta
import random
from mobile_token_nosql import MobileToken, send_notification
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
from lib.utils import sentry_init, time_to_string, get_test_engine, validate_date

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    mobile_token_manager = MobileToken(test_client=client)
else:
    reports_manager = Reports()
    help_tks_manager = HelpTKs()
    chats_manager = Chats()
    strikes_manager = Strikes()
    mobile_token_manager = MobileToken()

VALID_REPORT_TYPES = {"ACCOUNT", "SERVICE"}
REQUIRED_REPORT_FIELDS = {"title", "description", "complainant", "type", "target_identifier"}
REQUIRED_HELP_TK_FIELDS = {"title", "description"}
REQUIRED_HELP_TK_UPDATE_FIELDS = {"resolved"}
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

@app.get("/report/{uuid}")
def get_report_tk(uuid: str):
    report = reports_manager.get(uuid)
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
    user_id = help_tks_manager.get(uuid)["requester"]
    send_notification(mobile_token_manager, user_id, "Help Ticket Updated", f"Your help ticket {uuid} has been updated")
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
    user_id_field = "requester" if body["tk_type"] == "HELP" else "complainant"
    if not tks_manager.get(uuid):
        raise HTTPException(status_code=404, detail=f"{body['tk_type']} tk {uuid} not found")
    
    sender = "SUPPORT_AGENT" if body["support_agent"] else "USER"
    if not chats_manager.insert_message(body["message"], sender, uuid):
        raise HTTPException(status_code=400, detail="Error while sending the message")
    if sender == "SUPPORT_AGENT":
        user_id = tks_manager.get(uuid)[user_id_field]
        send_notification(mobile_token_manager, user_id, "New Support Chat Message", f"New message in your {body['tk_type']} chat {uuid}")
    
    tks_manager.set_last_updated(uuid)
    return {"status": "ok"}

@app.get("/chats/{uuid}")
def get_chat_messages(uuid: str, limit: int, offset: int):
    messages = chats_manager.get_messages(uuid, limit, offset)
    if not messages:
        raise HTTPException(status_code=404, detail="Chat not found")
    total_messages = chats_manager.count_messages(uuid)
    return {"status": "ok", "messages": messages, "total_messages": total_messages}

@app.get("/tks/unresolved")
def get_unresolved_tks():
    help_tks = help_tks_manager.get_not_resolved()
    report_tks = reports_manager.get_not_resolved()
    result = []
    if help_tks:
        result.extend(help_tks)
    if report_tks:
        result.extend(report_tks)
    if len(result) == 0:
        for i in range(10):
            result.append({
                "uuid": str(i),
                "title": f"Title {i}",
                "updated_at": random.choice(["2021-01-01", "2021-01-02", "2021-01-03", "2021-01-04", "2021-01-05"]),
                "type": random.choice(["help_tk", "report_tk"])
            })
    sorted_result = sorted(result, key=lambda x: x["updated_at"], reverse=True)
    return {"status": "ok", "tks": sorted_result}

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
    send_notification(mobile_token_manager, user_id, "New Strike", f"You have received a new {body['strike_type']} strike")
    if result_suspension:
        send_notification(mobile_token_manager, user_id, "Account Suspended", "Your account has been suspended for some time")
    return {"status": "ok", "suspension": result_suspension}

@app.get("/stats/last_month")
def get_last_month_stats():
    help_stats = help_tks_manager.last_month_stats()
    if not help_stats:
        raise HTTPException(status_code=404, detail="Stats not found")
    report_stats = reports_manager.last_month_stats()
    if not report_stats:
        raise HTTPException(status_code=404, detail="Stats not found")
    return {"status": "ok", "stats": {"help": help_stats, "reports": report_stats}}

@app.get("/stats/by_day")
def get_stats_by_day(from_date: str, to_date: str):
    if from_date > to_date:
        raise HTTPException(status_code=400, detail="from_date must be before to_date")
    from_date = validate_date(from_date)
    to_date = validate_date(to_date)
    help_by_day = help_tks_manager.tickets_by_day(from_date, to_date)
    report_by_day = reports_manager.tickets_by_day(from_date, to_date)
    results = {}
    for date in help_by_day:
        results[date] = {"new": help_by_day[date]["new"], "resolved": help_by_day[date]["resolved"]}
    for date in report_by_day:
        if date in results:
            results[date]["new"] += report_by_day[date]["new"]
            results[date]["resolved"] += report_by_day[date]["resolved"]
        else:
            results[date] = {"new": report_by_day[date]["new"], "resolved": report_by_day[date]["resolved"]}
    actual_date = from_date
    while actual_date <= to_date:
        if actual_date not in results:
            # results[actual_date] = {"new": 0, "resolved": 0}
            results[actual_date] = {"new": random.randint(0, 10), "resolved": random.randint(0, 8)} # MOCK HERE
        actual_date = (datetime.strptime(actual_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
    return {"status": "ok", "results": results}
    