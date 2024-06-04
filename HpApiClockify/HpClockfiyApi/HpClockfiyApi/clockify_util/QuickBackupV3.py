from .hpUtil import sqlConnect, cleanUp, get_current_time
from . import ClockifyPushV3
from .sqlDataFormatter import MonthylyProjReport, WeeklyTimeSheet
import asyncio
import datetime
import pytz
from asgiref.sync import sync_to_async
from .. Loggers import setup_server_logger
logger = setup_server_logger('DEBUG')

def UserEvent(wkSpaceName = 'Hill Plain'):
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
    logger.info(ClockifyPushV3.pushUsers(wid, conn, cursor))

    cleanUp(conn=conn, cursor=cursor)
    return 1

async def ClientEvent(wkSpaceName = 'Hill Plain'):
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
    clients = sync_to_async(ClockifyPushV3.pushClients, thread_sensitive=True)
    logger.info( await clients(wid, conn, cursor))
    cleanUp(conn=conn, cursor=cursor)
    return 1

async def ProjectEvent(wkSpaceName = 'Hill Plain'):
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
    projects = sync_to_async(ClockifyPushV3.pushProjects, thread_sensitive=True)
    logger.info(await projects(wid, conn, cursor))
    cleanUp(conn=conn, cursor=cursor)
    return 1

async def PolicyEvent(wkSpaceName = 'Hill Plain'):
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
    policies = sync_to_async(ClockifyPushV3.pushPolicies, thread_sensitive= True)
    logger.info(await policies(wid, conn, cursor))
    cleanUp(conn=conn, cursor=cursor)
    return 1

def TimesheetEvent(wkSpaceName = 'Hill Plain', status = 'APPROVED'):
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
    logger.info(f"({status}) {ClockifyPushV3.pushApprovedTime(wid, conn, cursor, status)}")
    cleanUp(conn=conn, cursor=cursor)

def TimeOffEvent(wkSpaceName = 'Hill Plain'):
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
    logger.info(ClockifyPushV3.pushTimeOff(wid, conn, cursor))
    cleanUp(conn=conn, cursor=cursor)
    return 1

async def HolidayEvent(wkSpaceName = 'Hill Plain'):
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
    holidays = sync_to_async(ClockifyPushV3.pushHolidays, thread_sensitive=True)
    logger.info(await holidays(wid, conn, cursor))
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
         
def monthlyBillable(start_date = None, end_date = None):
    file_path = (MonthylyProjReport(start_date, end_date ))
    logger.info(f" {file_path}")
    return file_path
    
def weeklyPayroll(start_date = None, end_date = None):
    file_path = WeeklyTimeSheet(start_date, end_date)
    logger.info(f" {file_path}")
    return file_path

async def main(): # Move the sql connection to the thread to increase performance by running async 
    await asyncio.gather(
    (ClientEvent()),
    (ProjectEvent()),
    (PolicyEvent()),
    (HolidayEvent()),
    (UserGroupEvent())
    )
    return 'Opperation Complete. View Logging For errors'

if __name__ == "__main__":
    main()