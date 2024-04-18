from . import ClockifyPullV2
from . import ClockifyPushV2
from . import sqlDataFormatter

import datetime
import pytz
import logging


def UserEvent(wkSpaceName = 'Hill Plain'):
    wid = ClockifyPushV2.getWID(wkSpaceName)
    cursor , conn = ClockifyPullV2.sqlConnect()
    attempts = 0
    while cursor is None and conn is None and attempts < 10:
        attempts += 1
        logging.info("Retrying.....Connecting to server")
        cursor , conn = ClockifyPullV2.sqlConnect() 
    if cursor is None and conn is None:
        logging.error('cannot connect to server')
        return 0
    logging.info(ClockifyPushV2.pushUsers(wid, conn, cursor))

    ClockifyPullV2.cleanUp(conn=conn, cursor=cursor)
    return 1
def ClientEvent(wkSpaceName = 'Hill Plain'):
    wid = ClockifyPushV2.getWID(wkSpaceName)
    cursor , conn = ClockifyPullV2.sqlConnect()
    attempts = 0
    while cursor is None and conn is None and attempts < 10:
        attempts += 1
        logging.info("Retrying.....Connecting to server")
        cursor , conn = ClockifyPullV2.sqlConnect()
    if cursor is None and conn is None:
        logging.error('cannot connect to server')
        return 0
    logging.info(ClockifyPushV2.pushClients(wid, conn, cursor))
    ClockifyPullV2.cleanUp(conn=conn, cursor=cursor)
    return 1
def ProjectEvent(wkSpaceName = 'Hill Plain'):
    wid = ClockifyPushV2.getWID(wkSpaceName)
    cursor , conn = ClockifyPullV2.sqlConnect()
    attempts = 0
    while cursor is None and conn is None and attempts < 10:
        attempts += 1
        logging.info("Retrying.....Connecting to server")
        cursor , conn = ClockifyPullV2.sqlConnect()
    if cursor is None and conn is None:
        logging.error('cannot connect to server')
        return 0
    logging.info(ClockifyPushV2.pushProjects(wid, conn, cursor))
    ClockifyPullV2.cleanUp(conn=conn, cursor=cursor)
    return 1
def PolicyEvent(wkSpaceName = 'Hill Plain'):
    wid = ClockifyPushV2.getWID(wkSpaceName)
    cursor , conn = ClockifyPullV2.sqlConnect()
    attempts = 0
    while cursor is None and conn is None and attempts < 10:
        attempts += 1
        logging.info("Retrying.....Connecting to server")
        cursor , conn = ClockifyPullV2.sqlConnect()
    if cursor is None and conn is None:
        logging.error('cannot connect to server')
        return 0
    logging.info(ClockifyPushV2.pushPolicies(wid, conn, cursor))
    ClockifyPullV2.cleanUp(conn=conn, cursor=cursor)
    return 1
def TimesheetEvent(wkSpaceName = 'Hill Plain', status = 'APPROVED'):
    wid = ClockifyPushV2.getWID(wkSpaceName)
    cursor , conn = ClockifyPullV2.sqlConnect()
    attempts = 0
    while cursor is None and conn is None and attempts < 10:
        attempts += 1
        logging.info("Retrying.....Connecting to server")
        cursor , conn = ClockifyPullV2.sqlConnect()
    if cursor is None and conn is None:
        logging.error('cannot connect to server')
        return 0
    logging.info(f"({status}) {ClockifyPushV2.pushApprovedTime(wid, conn, cursor, status)}")
    ClockifyPullV2.cleanUp(conn=conn, cursor=cursor)

def TimeOffEvent(wkSpaceName = 'Hill Plain'):
    wid = ClockifyPushV2.getWID(wkSpaceName)
    cursor , conn = ClockifyPullV2.sqlConnect()
    attempts = 0
    while cursor is None and conn is None and attempts < 10:
        attempts += 1
        logging.info("Retrying.....Connecting to server")
        cursor , conn = ClockifyPullV2.sqlConnect()
    if cursor is None and conn is None:
        logging.error('cannot connect to server')
        return 0
    logging.info(ClockifyPushV2.pushTimeOff(wid, conn, cursor))
    ClockifyPullV2.cleanUp(conn=conn, cursor=cursor)
    return 1
def UserGroupEvent(wkSpaceName = 'Hill Plain'):
    wid = ClockifyPushV2.getWID(wkSpaceName)
    cursor , conn = ClockifyPullV2.sqlConnect()
    attempts = 0
    while cursor is None and conn is None and attempts < 10:
        attempts += 1
        logging.info("Retrying.....Connecting to server")
        cursor , conn = ClockifyPullV2.sqlConnect()
    if cursor is None and conn is None:
        logging.error('cannot connect to server')
        return 0
    logging.info(ClockifyPushV2.pushUserGroups(wid, conn, cursor))
    ClockifyPullV2.cleanUp(conn=conn, cursor=cursor)
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
    logging.info(filePath, end="")
         
def monthlyBillable(start_date = None, end_date = None):
    file_path = (sqlDataFormatter.MonthylyProjReport(start_date, end_date ))
    logging.info(file_path)
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
