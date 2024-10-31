'''Combine all the report generator caller functions into one function that selectrs the report generator. This should simplify the code and internal dependancies'''
from ..views import sqlConnect, cleanUp, get_current_time
from . import ClockifyPushV3
from .sqlDataFormatter import *
import asyncio
import datetime
from asgiref.sync import sync_to_async
from ...HillPlainAPI.Loggers import setup_server_logger
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

async def TimesheetEvent(wkSpaceName = 'Hill Plain', status = ['APPROVED', 'PENDING', 'WITHDRAWN_APPROVAL']):
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
    output = []
    for stat in status: 
        logger.info(f'Updating {stat}')
        result = await ClockifyPushV3.pushTimesheet(wid, conn, cursor, stat)
        logger.info(result)
        output.append(result)
    cleanUp(conn=conn, cursor=cursor)
    return output 

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
            'timesheet': TimesheetEvent(wkSpaceName = 'Hill Plain'),
            'timeoff': TimeOffEvent(wkSpaceName = 'Hill Plain'),
            'holiday': HolidayEvent(wkSpaceName = 'Hill Plain'),
            'userGroup': UserGroupEvent(wkSpaceName = 'Hill Plain'),
        }
        results = await asyncio.gather(events.get(event, main()), return_exceptions= True)
        logger.debug(f'Results Data {results}')
        logger.debug(f'Results Type {type(results)}')
        return results
    except Exception as e:
        logger.error(({e.__traceback__.tb_lineno}) - {str(e)})
        raise e
        
######################################################################################################################################################################


async def billingReport(month= None, year = None, pCode = None, start=None, end = None):
    #obtain date range for this month 
    if((month is not None or year is not None) and (start is not None or end is not None)):
        raise Exception("Invalid Arguments on billingReport function")
    if(start is None and end is None):
        # Auto format dates. Either get current or format from input Abbriviation string
        if month is None or year is None:
            month, year = getMonthYear()
        else:
            month = getAbbreviation(month, reverse=True)
        logger.info(f'Biling Report Generating for - {month}-{year}')

        if int(month) -1 == 0: 
            previousMonth = '12'
            previousYear = str(int(year) - 1).rjust(2, '0')
        else: 
            previousMonth = str(int(month) -1 ).rjust(2, '0')
            previousYear = year

    #format date strings
        endDateObj = datetime.datetime.strptime(f'20{year}-{month}-25', '%Y-%m-%d')
        startDateObj = datetime.datetime.strptime(f'20{previousYear}-{previousMonth}-25', '%Y-%m-%d')
        # Calculate the most recent previous Saturday
        if(endDateObj.weekday() != 5):
            endDate = (endDateObj - timedelta(days=(endDateObj.weekday() + 2) % 7)).strftime('%Y-%m-%d')
        else: endDate = f'20{year}-{month}-25'
        if(startDateObj.weekday() != 6):
            startDate = (startDateObj - timedelta(days=(startDateObj.weekday()+ 1) %7)).strftime('%Y-%m-%d')
        else: startDate = f'20{previousYear}-{previousMonth}-25'
        logger.debug(f'Date Range: {startDate}-{endDate}')
    else: # custom format 
        startDate = start 
        endDate = end

    
    file_path = await BillableReportGenerate(startDate, endDate, pCode )
    logger.info(f"{file_path}")
    return file_path 

def NonBillableReport(start = None, end = None):
    file_path = NonBillableReportGen(start, end)
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
    
def GenerateTimeSheetLem(projectId, startDate, endDate):
    file_path = lemTimesheet(projectId, startDate,endDate )
    logger.info(f" {file_path}")
    return file_path

if __name__ == "__main__":
    main()