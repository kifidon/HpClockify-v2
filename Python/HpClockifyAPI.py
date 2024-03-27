from fastapi import FastAPI, Request
import logging
import json
import func
import services
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

#from fastapi.middleware.swagger import SwaggerUI

# Configure logging
logging.basicConfig(
    level=logging.ERROR,  # Set the logging level to ERROR
    filename='HpClockifyAPI.log',   # Set the file name for logging
    format='%(asctime)s - %(levelname)s - %(message)s'  # Set the log message format
)

app = FastAPI()

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Docs")

@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint():
    return JSONResponse(get_openapi(title="HpCLockifyAPI", version="1.0.0", routes=app.routes))

@app.post('/timesheetUpdate')
async def updateApproval(ApprovalR: services.ApprovalRequest):
    approve = await ApprovalR.json() # wait until request is sent 
    wkSpaceID = approve['workspaceId']
    aID = approve['id'] 
    userID = approve['owner']['userId']
    status = approve['status']['state']
    
    startDateO = func.timeZoneConvert(approve['dateRange']['start'])
    endDateO = func.timeZoneConvert(approve['dateRange']['end'])
    try:
       cursor, conn =  func.sqlConnect() 
       cursor.execute(
                '''
                UPDATE TimeSheet
                SET emp_id = ?,
                    start_time = ?,
                    end_dfsdtime = ?,
                    status = ?
                WHERE id = ? and workspace_id = ?;    
                ''', (userID, startDateO, endDateO, status, aID, wkSpaceID)
            )
    
    except Exception as  exc :
        cursor.execute(
           '''
            select * From TimeSheet
            where id = ? and workspace_id = ?
            ''', (aID, wkSpaceID)
        )
        result = cursor.fetchone()
        conn.rollback()  # Roll back changes if an exception occurs
        logging.error(f"An error occurred while updating timesheet: {json.dumps(func.errorToJson(exc), indent=4)}")
        logging.error(f"{json.dumps(func.rowToJson(result), indent=4)}")
        return func.errorToJson(exc)
    else:
        cursor.execute(
           '''
            select * From TimeSheet
            where id = ? and workspace_id = ?
            ''', (aID, wkSpaceID)
        )
        result = cursor.fetchone()
        conn.commit() 
        logging.info("Committing changes...")  # Commit changes if no exceptions occurred                     
        return(func.rowToJson(result))


    