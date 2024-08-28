'''Combine all the report generator caller functions into one function that selectrs the report generator. This should simplify the code and internal dependancies'''
from .hpUtil import sqlConnect, cleanUp, get_current_time
from . import ClockifyPushV3
from .sqlDataFormatter import *
import asyncio
import datetime
import pytz
from asgiref.sync import sync_to_async
from .. Loggers import setup_server_logger
logger = setup_server_logger('DEBUG')

async def UserEvent(wkSpaceName = 'Hill Plain'):
    logger.info('User Event Called')
    wid = ClockifyPushV3.getWID(wkSpaceName)
    cursor , conn = sqlConnect()
    attempts = 0
    while cursor is None and conn is None and attempts < 10:
        attempts += 1
        logger.info(f" Retrying.....Connecting to server")
        cursor , conn = sqlConnect() 
    if cursor is None and conn is None:
        logger.error('cannot connect to server')
        return 0
    logger.info( ClockifyPushV3.pushUsers(wid, conn, cursor))

    cleanUp(conn=conn, cursor=cursor)
    return 1

async def ClientEvent(wkSpaceName = 'Hill Plain'):
    logger.info('Client Event Called')
    wid = ClockifyPushV3.getWID(wkSpaceName)
    cursor , conn = sqlConnect()
    attempts = 0
    while cursor is None and conn is None and attempts < 10:
        attempts += 1
        logger.info(f" Retrying.....Connecting to server")
        cursor , conn = sqlConnect()
    if cursor is None and conn is None:
        logger.error('cannot connect to server')
        return 0
    logger.debug('Transfering to handler function')
    result = ClockifyPushV3.pushClients(wid ,conn, cursor)
    
    logger.info(result)
    cleanUp(conn=conn, cursor=cursor)
    return result

async def ProjectEvent(wkSpaceName = 'Hill Plain'):
    logger.info('Project Event Called')
    wid = ClockifyPushV3.getWID(wkSpaceName)
    cursor , conn = sqlConnect()
    attempts = 0
    while cursor is None and conn is None and attempts < 10:
        attempts += 1
        logger.info(f" Retrying.....Connecting to server")
        cursor , conn = sqlConnect()
    if cursor is None and conn is None:
        logger.error('cannot connect to server')
        return 0
    projects = sync_to_async(ClockifyPushV3.pushProjects, thread_sensitive=True)
    result = await projects(wid, conn, cursor)
    logger.info(result)
    cleanUp(conn=conn, cursor=cursor)
    return result

async def PolicyEvent(wkSpaceName = 'Hill Plain'):
    logger.info('Policy Event Called')
    wid = ClockifyPushV3.getWID(wkSpaceName)
    cursor , conn = sqlConnect()
    attempts = 0
    while cursor is None and conn is None and attempts < 10:
        attempts += 1
        logger.info(f" Retrying.....Connecting to server")
        cursor , conn = sqlConnect()
    if cursor is None and conn is None:
        logger.error('cannot connect to server')
        return 0
    policies = sync_to_async(ClockifyPushV3.pushPolicies, thread_sensitive= True)
    result = await policies(wid, conn, cursor)
    logger.info(result)
    cleanUp(conn=conn, cursor=cursor)
    return result

async def TimesheetEvent(wkSpaceName = 'Hill Plain', status = 'APPROVED'):
    logger.info('Timesheet Event Called')
    wid = ClockifyPushV3.getWID(wkSpaceName)
    cursor , conn = sqlConnect()
    attempts = 0
    while cursor is None and conn is None and attempts < 10:
        attempts += 1
        logger.info(f" Retrying.....Connecting to server")
        cursor , conn = sqlConnect()
    if cursor is None and conn is None:
        logger.error('cannot connect to server')
        return 0
    result =  ClockifyPushV3.pushApprovedTime(wid, conn, cursor, status)
    logger.info(result)
    cleanUp(conn=conn, cursor=cursor)

async def TimeOffEvent(wkSpaceName = 'Hill Plain'):
    logger.info('Timeoff Event Called')
    wid = ClockifyPushV3.getWID(wkSpaceName)
    cursor , conn = sqlConnect()
    attempts = 0
    while cursor is None and conn is None and attempts < 10:
        attempts += 1
        logger.info(f" Retrying.....Connecting to server")
        cursor , conn = sqlConnect()
    if cursor is None and conn is None:
        logger.error('cannot connect to server')
        return 0
    result = ClockifyPushV3.pushTimeOff(wid, conn, cursor)
    logger.info(result)
    cleanUp(conn=conn, cursor=cursor)
    return result

async def HolidayEvent(wkSpaceName = 'Hill Plain'):
    logger.info('Holiday Event Called')
    wid = ClockifyPushV3.getWID(wkSpaceName)
    cursor , conn = sqlConnect()
    attempts = 0
    while cursor is None and conn is None and attempts < 10:
        attempts += 1
        logger.info(f" Retrying.....Connecting to server")
        cursor , conn = sqlConnect()
    if cursor is None and conn is None:
        logger.error('cannot connect to server')
        return 0
    holidays = sync_to_async(ClockifyPushV3.pushHolidays, thread_sensitive=True)
    result = await holidays(wid, conn, cursor)
    logger.info(result)
    cleanUp(conn=conn, cursor=cursor)
    return 1

async def UserGroupEvent(wkSpaceName = 'Hill Plain'):
    logger.info('Called')
    wid = ClockifyPushV3.getWID(wkSpaceName)
    cursor , conn = sqlConnect()
    attempts = 0
    while cursor is None and conn is None and attempts < 10:
        attempts += 1
        logger.info(f" Retrying.....Connecting to server")
        cursor , conn = sqlConnect()
    if cursor is None and conn is None:
        logger.error('cannot connect to server')
        return 0
    usergroups = sync_to_async(ClockifyPushV3.pushUserGroups, thread_sensitive= True)
    logger.info(await usergroups(wid, conn, cursor))
    cleanUp(conn=conn, cursor=cursor)
    return 1

async def main(): # Move the sql connection to the thread to increase performance by running async 
    result = await asyncio.gather(
    (ClientEvent()),
    (ProjectEvent()),
    (PolicyEvent()),
    # (HolidayEvent()),
    # (UserGroupEvent()),
    (TimeOffEvent())
    ,return_exceptions= True)
    return result

async def eventSelect(event = None):
    try:
        events = {
            'user': UserEvent(wkSpaceName = 'Hill Plain'),
            'client': ClientEvent(wkSpaceName = 'Hill Plain'),
            'project': ProjectEvent(wkSpaceName = 'Hill Plain'),
            'policy': PolicyEvent(wkSpaceName = 'Hill Plain'),
            'timesheet': TimesheetEvent(wkSpaceName = 'Hill Plain', status = 'APPROVED'),
            'timeoff': TimeOffEvent(wkSpaceName = 'Hill Plain'),
            'holiday': HolidayEvent(wkSpaceName = 'Hill Plain'),
            'userGroup': UserGroupEvent(wkSpaceName = 'Hill Plain'),
        }
        results = await asyncio.gather(events.get(event, main()), return_exceptions= True)
        logger.debug(results)
        logger.debug(type(results))
        return results
    except Exception as e:
        logger.error(({e.__traceback__.tb_lineno}) - {str(e)})
        raise e
        
######################################################################################################################################################################


def CreateTextFile():
    timezone = pytz.timezone('America/Denver')
    currentDateTimeObject = datetime.datetime.now(timezone)
    currentDateTime = currentDateTimeObject.strftime("%Y-%m-%d_T%H_%M_%S")
    filePath = f"C:/Users/TimmyIfidon/OneDrive - Hill Plain Construction Services LP/Event Logs/ClockifyPullLog-{currentDateTime}.txt"
    with open(filePath, "w") as file:
        file.write(f"Clockify to Sql Data Push Log - {currentDateTime}\n")
        file.write("--------------------------------------------------------------------\n")
    file.close()
    logger.info(filePath, end="")

async def billingReport(month= None, year = None, pCode = None):
    file_path = await BillableReportGenerate(month, year, pCode )
    logger.info(f" {file_path}")
    return file_path 

#depreciated         
def monthlyBillable(month = None, year = None):
    file_path = (MonthylyProjReport(month, year ))
    logger.info(f" {file_path}")
    return file_path
#depreciated
def monthlyBillableEqp(month = None, year = None):
    file_path = (MonthylyProjReportEqp(month, year))
    logger.info(f" {file_path}")
    return file_path

def NonBillableReport(start = None, end = None):
    file_path = NonBillableReportGen(start, end)
    logger.info(f" {file_path}")
    return file_path

def dailyEntries():
    file_path = DailyTimeEntryReport()
    logger.info(f" {file_path}")
    return file_path
    
def weeklyPayroll(start_date = None, end_date = None):
    file_path = Payroll(start_date, end_date)
    logger.info(f" {file_path}")
    return file_path

def TimeStatusCaller(start_date = None, end_date = None):
    file_path = TimeStatus(start_date, end_date)
    logger.info(f" {file_path}")
    return file_path

def GenerateLem(projectCode,lemId):
    file_path = lemGenerator(projectCode, lemId)
    logger.info(f" {file_path}")
    return file_path
    


if __name__ == "__main__":
    main()