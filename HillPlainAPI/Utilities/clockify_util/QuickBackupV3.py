'''Combine all the report generator caller functions into one function that selectrs the report generator. This should simplify the code and internal dependancies'''
from ..views import sqlConnect, cleanUp, get_current_time
from . import ClockifyPushV3
from ...ReportGeneration.sqlDataFormatter import *
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
        