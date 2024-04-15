from . import ClockifyPull
from . import ClockifyPush
from . import sqlDataFormatter
import argparse
import datetime
import pytz
import logging


def UserEvent(wkSpaceName = 'Hill Plain'):
    wid = ClockifyPush.getWID(wkSpaceName)
    cursor , conn = ClockifyPull.sqlConnect()
    attempts = 0
    while cursor is None and conn is None and attempts < 10:
        attempts += 1
        logging.info("Retrying.....Connecting to server")
        cursor , conn = ClockifyPull.sqlConnect() 
    if cursor is None and conn is None:
        logging.error('cannot connect to server')
        return 0
    logging.info(ClockifyPush.pushUsers(wid, conn, cursor))

    ClockifyPull.cleanUp(conn=conn, cursor=cursor)
    
def ClientEvent(wkSpaceName = 'Hill Plain'):
    wid = ClockifyPush.getWID(wkSpaceName)
    cursor , conn = ClockifyPull.sqlConnect()
    attempts = 0
    while cursor is None and conn is None and attempts < 10:
        attempts += 1
        logging.info("Retrying.....Connecting to server")
        cursor , conn = ClockifyPull.sqlConnect()
    if cursor is None and conn is None:
        logging.error('cannot connect to server')
        return 0
    logging.info(ClockifyPush.pushClients(wid, conn, cursor))
    ClockifyPull.cleanUp(conn=conn, cursor=cursor)

def ProjectEvent(wkSpaceName = 'Hill Plain'):
    wid = ClockifyPush.getWID(wkSpaceName)
    cursor , conn = ClockifyPull.sqlConnect()
    attempts = 0
    while cursor is None and conn is None and attempts < 10:
        attempts += 1
        logging.info("Retrying.....Connecting to server")
        cursor , conn = ClockifyPull.sqlConnect()
    if cursor is None and conn is None:
        logging.error('cannot connect to server')
        return 0
    logging.info(ClockifyPush.pushProjects(wid, conn, cursor))
    ClockifyPull.cleanUp(conn=conn, cursor=cursor)
    
def PolicyEvent(wkSpaceName = 'Hill Plain'):
    wid = ClockifyPush.getWID(wkSpaceName)
    cursor , conn = ClockifyPull.sqlConnect()
    attempts = 0
    while cursor is None and conn is None and attempts < 10:
        attempts += 1
        logging.info("Retrying.....Connecting to server")
        cursor , conn = ClockifyPull.sqlConnect()
    if cursor is None and conn is None:
        logging.error('cannot connect to server')
        return 0
    logging.info(ClockifyPush.pushPolicies(wid, conn, cursor))
    ClockifyPull.cleanUp(conn=conn, cursor=cursor)

def TimesheetEvent(wkSpaceName = 'Hill Plain'):
    wid = ClockifyPush.getWID(wkSpaceName)
    cursor , conn = ClockifyPull.sqlConnect()
    attempts = 0
    while cursor is None and conn is None and attempts < 10:
        attempts += 1
        logging.info("Retrying.....Connecting to server")
        cursor , conn = ClockifyPull.sqlConnect()
    status = [ 'APPROVED']
    if cursor is None and conn is None:
        logging.error('cannot connect to server')
        return 0
    for stat in status:
        logging.info(f"({stat})",ClockifyPush.pushApprovedTime(wid, conn, cursor, stat))
    ClockifyPull.cleanUp(conn=conn, cursor=cursor)

def TimeOffEvent(wkSpaceName = 'Hill Plain'):
    wid = ClockifyPush.getWID(wkSpaceName)
    cursor , conn = ClockifyPull.sqlConnect()
    attempts = 0
    while cursor is None and conn is None and attempts < 10:
        attempts += 1
        logging.info("Retrying.....Connecting to server")
        cursor , conn = ClockifyPull.sqlConnect()
    if cursor is None and conn is None:
        logging.error('cannot connect to server')
        return 0
    logging.info(ClockifyPush.pushTimeOff(wid, conn, cursor))
    ClockifyPull.cleanUp(conn=conn, cursor=cursor)

def UserGroupEvent(wkSpaceName = 'Hill Plain'):
    wid = ClockifyPush.getWID(wkSpaceName)
    cursor , conn = ClockifyPull.sqlConnect()
    attempts = 0
    while cursor is None and conn is None and attempts < 10:
        attempts += 1
        logging.info("Retrying.....Connecting to server")
        cursor , conn = ClockifyPull.sqlConnect()
    if cursor is None and conn is None:
        logging.error('cannot connect to server')
        return 0
    logging.info(ClockifyPush.pushUserGroups(wid, conn, cursor))
    ClockifyPull.cleanUp(conn=conn, cursor=cursor)

def CreateTextFile():
    timezone = pytz.timezone('America/Denver')
    currentDateTimeObject = datetime.datetime.now(timezone)
    currentDateTime = currentDateTimeObject.strftime("%Y-%m-%d_T%H_%M_%S")
    filePath = f"C:/Users/TimmyIfidon/OneDrive - Hill Plain Construction Services LP/Event Logs/ClockifyPullLog-{currentDateTime}.txt"
    with open(filePath, "w") as file:
        file.write(f"Clockify to Sql Data Push Log - {currentDateTime}\n")
        file.write("--------------------------------------------------------------------\n")
    file.close()
    logging.info(filePath, end="")
        
def monthlyBillable():
    logging.info(sqlDataFormatter.MonthylyProjReport())

def main():
    UserEvent()
    ClientEvent()
    ProjectEvent()
    PolicyEvent()
    TimesheetEvent()
    TimeOffEvent()
    UserGroupEvent()
    return 'Opperation Complete. View Logging For errors '

if __name__ == "__main__":
    main()

    # parser = argparse.ArgumentParser(description="Run a specific function.")
    # parser.add_argument(
    #     "function",
    #     choices=[
    #         "UserEvent", "ClientEvent", "ProjectEvent", "PolicyEvent", "TimesheetEvent", "TimeOffEvent", "UserGroupEvent", "CreateTextFile", "monthlyBillable"
    #         ]
    # )

    # args = parser.parse_args()
    # try:
    #     if args.function == "UserEvent":
    #         UserEvent()
    #     elif args.function == "ClientEvent":
    #         ClientEvent()
    #     elif args.function == "ProjectEvent":
    #         ProjectEvent()
    #     elif args.function == "PolicyEvent":
    #         PolicyEvent()
    #     elif args.function == "TimesheetEvent":
    #         TimesheetEvent()
    #     elif args.function == "TimeOffEvent":
    #         TimeOffEvent()
    #     elif args.function == "UserGroupEvent":
    #         UserGroupEvent()
    #     elif args.function == "CreateTextFile":
    #         CreateTextFile()
    #     elif args.function == "monthlyBillable":
    #         monthlyBillable()
    # except Exception as  exc :
    #     # Roll back changes if an exception occurs
    #     logging.info(f"Error ({exc.__class__}): \n----------{exc.__traceback__.tb_frame.f_code.co_filename}, {exc.__traceback__.tb_frame.f_code.co_name} \n\tLine: {exc.__traceback__.tb_lineno} \n----------{str(exc)}\n")
    # else:
    #     logging.info("Operation Complete")
