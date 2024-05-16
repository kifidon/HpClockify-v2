from .hpUtil import sqlConnect, cleanUp, get_current_time
from . import ClockifyPushV3
from .sqlDataFormatter import MonthylyProjReport, WeeklyTimeSheet

import datetime
import pytz
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

def ClientEvent(wkSpaceName = 'Hill Plain'):
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
    logger.info(ClockifyPushV3.pushClients(wid, conn, cursor))
    cleanUp(conn=conn, cursor=cursor)
    return 1

def ProjectEvent(wkSpaceName = 'Hill Plain'):
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
    logger.info(ClockifyPushV3.pushProjects(wid, conn, cursor))
    cleanUp(conn=conn, cursor=cursor)
    return 1

def PolicyEvent(wkSpaceName = 'Hill Plain'):
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
    logger.info(ClockifyPushV3.pushPolicies(wid, conn, cursor))
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
def UserGroupEvent(wkSpaceName = 'Hill Plain'):
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
    logger.info(ClockifyPushV3.pushUserGroups(wid, conn, cursor))
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

def main():
    UserEvent()
    ClientEvent()
    ProjectEvent()
    PolicyEvent()
    TimesheetEvent()
    TimeOffEvent()
    UserGroupEvent()
    return 'Opperation Complete. View Logging For errors @: https://hpclockifyapi.azurewebsites.net/'

if __name__ == "__main__":
    main()