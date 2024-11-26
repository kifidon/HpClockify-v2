import pyodbc #depreciated. Replase with django.db
from django import db
from django.db import transaction
import copy
import json
import asyncio
from Clockify.models import *
# import logging
from HillPlainAPI.Loggers import setup_background_logger, setup_server_logger
from .ClockifyPullV3 import getApiKey, getWorkspaces,getWorkspaceUsers, getProjects, getTimesheets, getHolidays, getClients, getPolocies, getTimeOff, getUserGroups
from ..views import sqlConnect, cleanUp, pytz, datetime, timedelta, toMST, timeDuration, count_working_days
import threading
from Clockify.models import *

logger = setup_server_logger('DEBUG')

def getWID(wSpace_Name):
    count = 0
    while True:
        try:
            quickCursor, quickConn = sqlConnect()
        except pyodbc.Error as p: 
            return 'INVALID'
        quickCursor.execute('''SELECT id FROM Workspace WHERE name = ? ''', wSpace_Name)
        row = quickCursor.fetchone()
        if row is not None:
            break
        elif row is None and count <= 1:
            count += 1
            pushWorkspaces(quickConn, quickCursor) 
        else: 
            break
    check = cleanUp(quickConn, quickCursor)
    if check and row is not None:
        return row[0]
    elif check and row is None:
        logger.error("Invalid Workspace Name")
        return 'INVALID'
    else:
        logger.error("An error occured on the system. Please Contact Administrator. Cannot close connection.")
        return 'INVALID'

class ThreadPrimitives:
    def __init__(self):
        # Initialize the threading primitives
        self.lock = threading.Lock()
        self.rollback = threading.Event()
        self.atomic = 0  # tracks the number of active threads
        self.commit = threading.Condition()

    def increment_atomic(self):
        """Safely increment the atomic counter within the lock."""
        with self.lock:
            self.atomic += 1
            logger.info(f"Atomic count incremented to: {self.atomic}")

    def decrement_atomic(self):
        """Safely decrement the atomic counter within the lock."""
        with self.lock:
            self.atomic -= 1
            try:
                assert self.atomic >= 0, "Assertion failed: self.atomic must be non-negative"
            except AssertionError as a:
                logger.error((str(a)))
                
            logger.info(f"Atomic count decremented to: {self.atomic}")
        return self.atomic
    def get_atomic(self):
        """Safely read the value of the atomic counter within the lock."""
        with self.lock:
            return self.atomic
        
    def wait_for_commit(self):
        """Wait until the commit condition is met."""
        with self.commit:
            self.commit.wait()
            logger.info("Commit condition met, resuming operation.")

    def notify_commit(self):
        """Notify all threads waiting on the commit condition."""
        with self.commit:
            self.commit.notify_all()
            logger.info("Notified all threads on commit condition.")

    def set_rollback(self):
        """Set the rollback event to trigger a rollback."""
        self.rollback.set()
        logger.info("Rollback event set.")

    def clear_rollback(self):
        """Clear the rollback event."""
        self.rollback.clear()
        logger.info("Rollback event cleared.")

    def check_rollback(self):
        """Check if rollback event is set."""
        return self.rollback.is_set()
    
primitives = ThreadPrimitives()

def pushTags(inputData, wkspace, entry):
    id = inputData['id']
    name = inputData['name']
    try:
        tags, created = Tagsfor.objects.update_or_create(
            id = id,
            entryid = entry, 
            workspaceId = wkspace,
            name = name
        )
        if created is True:
            logger.info("\t\tCreated new tag")
        else:
            logger.info("\t\tUpdated old tag")

    except Exception as e:
        primitives.set_rollback()
        logger.info(f'{str(e)}- {e.__traceback__.tb_lineno}')
    finally:
        if primitives.check_rollback():
            tags.delete()
        
    return

def pushEntries(inputData, timesheet, wkspace):
    # conn = connections.acquire_connection()
    # cursor = conn.cursor()

    id = inputData['id']
    timesheetID = inputData['approvalRequestId'] or None
    # logger.debug(f"TimesheetID:{timesheetID}")
    description = inputData['description']
    taskName = inputData['task']['name'] or None
    billable = inputData['billable']
    project_id = inputData['project']['id']
    project, created = Project.objects.get_or_create(id = project_id,
        defaults={
            'clientId': Client.objects.get(id='0000000000'), 
            'workspaceId': wkspace})
    if created is True: 
        logger.warning(f"Created Empty Project with id {project_id}. Run ProjectEvent and try again.")
        logger.warning("Proceeding with operation")
    if inputData.get('hourlyRate') is not None:
        rate = inputData.get('hourlyRate')['amount']
    else:
        rate = 0
    
    duration = timeDuration(inputData['timeInterval']['duration'])
    startO = datetime.strptime(inputData['timeInterval']['start'], '%Y-%m-%dT%H:%M:%SZ')
    endO = datetime.strptime(inputData['timeInterval']['end'], '%Y-%m-%dT%H:%M:%SZ')
    startStr = toMST(startO, True)
    endStr = toMST(endO, True)   

    try:
        created = False
        try: 
            entry = Entry.objects.get(id = id, workspaceId= wkspace)
            entry.timesheetId = timesheet
            entry.duration = duration
            entry.description = description
            entry.billable = billable
            entry.project = project
            entry.hourlyRate = rate
            entry.start = startStr
            entry.end = endStr 
            entry.task = taskName

            logger.debug(f"Entry Time: {str(entry.start)}")

        except Entry.DoesNotExist:
            created = True
            entry = Entry.objects.create( # use created flag to log updates or creations 
                id = id,
                timesheetId = timesheet,
                duration = duration,
                description = description,
                billable = billable,
                project = project,
                hourlyRate = rate,
                start = startStr,
                end = endStr,
                workspaceId = wkspace,
                task = taskName
            )
        if len(inputData['tags']) != 0:
            task = []
            for tag in inputData['tags']:
                # task.append(asyncio.create_task(pushTags(inputData, wkspace, cursor)))
                pushTags(tag, wkspace, entry)
    except db.IntegrityError as e:
        logger.critical('An Integrity occured on thread while trying to update an entry')   
        logger.critical(str(e))
        primitives.set_rollback() 
        primitives.notify_commit()
    except Exception as e:
        logger.critical(f'{str(e)} - {e.__traceback__.tb_lineno}')
        primitives.set_rollback()
        primitives.notify_commit()
    finally:
        atomic = primitives.decrement_atomic()
        if atomic != 0 :
            primitives.wait_for_commit()
            if primitives.check_rollback():
                logger.warning("***There was a problem saving record on an alternative thread. Rolling back changes")
            else:
                primitives.lock.acquire()
                if(not created):
                    logger.info("\tCommiting Updates to Entry...") #simulation
                    logger.debug(f"[ID: {id}]-[START: {startStr}]")
                    logger.debug(f"Entry Record Time before save: {entry.start}")
                else: 
                    logger.warning("\tCommiting New Entry on backup...")
                entry.save()
                newEntry = Entry.objects.get(id=id, workspaceId= wkspace)
                logger.debug(f"New Entry Start time after save: {newEntry.start}")
                primitives.lock.release()
        elif atomic == 0 and not primitives.check_rollback():
            primitives.notify_commit()
            primitives.lock.acquire()
            entry.save()
            logger.info("\tCommiting Entry...") #simulation
            primitives.lock.release()
        else:
            entry.delete()
            raise Exception("***There was a problem saving record on an alternative thread. Rolling back changes")
        

    return

async def pushTimesheets(wkSpaceID, offset = 1):
    """
    Pushes attendance data from Clockify to the database. Attendance is the hours worked (regula, overtime, total, Paid Time Off)
    for all Users with active time entries. 

    Args:
    - wkSpaceID: The workspace ID.
    - conn: The connection to the database.
    - cursor: The cursor for executing SQL commands.
    - startDate (optional): The start date for fetching attendance data. Default is "2024-02-11T00:00:00Z".
    - endDate (optional): The end date for fetching attendance data. Default is "2024-02-17T23:59:59.999Z".
    - page (optional): The page number for pagination. Default is 1.

    Returns:
    - str: A message indicating the operation's completion status.
    """
    page = 1 * offset
    startPage = page
    try: 
        logger.info('Pulling Data from Application Server')
        attendance = await getTimesheets(wkSpaceID, 'ZjZhM2MwZmEtOTFiZi00MWE0LTk5NTMtZWUxNGJjN2FmNmQy', page)
        logger.info('Data aquired')
        length = 0
        wkspace = await Workspace.objects.aget(id = wkSpaceID)
        # while len(attendance) != 0 and page < page + 1:
        while len(attendance) != 0 and page < startPage+10:
            logger.info(f"Page: {page}")
            page +=1 
            intermediate = asyncio.create_task(getTimesheets(wkSpaceID, 'ZjZhM2MwZmEtOTFiZi00MWE0LTk5NTMtZWUxNGJjN2FmNmQy', page))
            length += len(attendance)
            logger.info(f"Inserting Page: {page-1}. ({length} entries)")
            # conn = connections.acquire_connection()
            # cursor = conn.cursor()
            for timesheetData in attendance: 
                primitives.clear_rollback()
                id = timesheetData['approvalRequest']['id']
                emp_id = timesheetData['approvalRequest']['owner']['userId']
                emp = await Employeeuser.objects.aget(id = emp_id)
                start_timeO = datetime.strptime(timesheetData['approvalRequest']['dateRange']['start'], '%Y-%m-%dT%H:%M:%SZ')
                end_timeO = datetime.strptime(timesheetData['approvalRequest']['dateRange']['end'], '%Y-%m-%dT%H:%M:%SZ')
                start = toMST(start_timeO)
                end = toMST(end_timeO)
                status = timesheetData['approvalRequest']['status']['state']
                try:
                    
                    try:
                        timesheet = await Timesheet.objects.aget(id=id, workspace = wkspace, emp = emp)
                        timesheet.start_time = start
                        timesheet.end_time = end
                        timesheet.status = status
                        logger.info("Updating Timesheet")
                    except Timesheet.DoesNotExist:
                        logger.info("Creating new Timesheet")
                        timesheet= await Timesheet.objects.acreate(
                            id = id,
                            emp = emp,
                            start_time = start,
                            end_time = end, 
                            workspace = wkspace,
                            status = status
                        )
                    if status != "APPROVED": 
                        logger.info(f'Skipping entries on {status} timesheet')
                    
                    else:
                        i = 0
                        while i < len(timesheetData['entries']):
                            tasks = []    
                            for entry in timesheetData['entries'][i:i+15]:
                                task = asyncio.to_thread(pushEntries, entry, timesheet, wkspace)
                                primitives.increment_atomic()
                                tasks.append(task)
                        # Increment by 10 for the next batch
                            await asyncio.gather(*tasks,return_exceptions=False)
                            i += 15
                    if primitives.check_rollback():
                        Exception("An exception occured when trying on one of the threads. Rolling back changes")
                except db.IntegrityError as e:
                    logger.error("Exception occured when trying to insert entry")
                    logger.error(str(e))
                except Exception as ex:
                    logger.error(f'{str(ex)} - {ex.__traceback__.tb_lineno}')
                finally:
                    if primitives.check_rollback():
                        logger.warning("Could not save timesheet data, rolling back changes")
                    else:
                        await timesheet.asave()

            logger.info("Waiting for next Timesheet")
            attendance = await intermediate
        return "TimesheetEvent: Sucess"

    except Exception as ex:
        logger.error(f'{str(ex)} - {ex.__traceback__.tb_lineno}')
        raise ex

def pushHolidays(wkSpaceID, conn, cursor):
    holidays = getHolidays(wkSpaceID)
    failed = False
    try:
        for day in holidays:
            id = day['id']
            date = day.get("datePeriod").get('startDate')
            name = day['name']
            try:
                holiday = Holidays.objects.get(id = id)

                holiday.name = name
                holiday.date 
            except Holidays.DoesNotExist as h:
                holiday = Holidays.objects.create(id = id, name=name, 
                                                    date=date)
            except pyodbc.IntegrityError as e:
                failed = True
                if "PRIMARY KEY constraint" in str(e):
                # this is where we will check to update if new users or groups are added 
                    logger.critical(F"Problem inserting Holiday...")
                elif"FOREIGN KEY constraint" in str(e):   
                    updateCalendar(date, conn, cursor)
                else:
                    raise
            finally  :
                if not failed:
                    holiday.save()
                    logger.info(f"\tCommitting Holiday{name}")         
    except Exception as exc :
        logger.error(f"Error ({exc.__class__}): \n----------{exc.__traceback__.tb_frame.f_code.co_filename}, {exc.__traceback__.tb_frame.f_code.co_name} \n\tLine: {exc.__traceback__.tb_lineno} \n----------{str(exc)}\n")
        logger.critical(f"Operation failed. Changes rolled back. Contact administer of problem persists")

async def pushTimeOff(wkSpaceID):
    """
    Pushes time off requests retrieved from Clockify API to the database.

    Args:

    Returns:
        str: Message indicating the operation status.

    Calls:
        - pushHolidays(wkSpaceID, conn, cursor): Pushes holidays to the database.
        - count_working_days(start_date, end_date, conn, cursor): Counts the number of working days between two dates.
        - pushPolicies(wkSpaceID, conn, cursor): Pushes policies to the database.
        - pushUsers(wkSpaceID, conn, cursor): Pushes users to the database.
    """
    try:
        logger.info("Pushing Time off data ")
        # logger.info(pushHolidays(wkSpaceID, conn, cursor))
        page = 1
        mst = pytz.timezone('America/Denver')
        currentDate = datetime.now(mst)
        endRange= datetime(currentDate.year,12,31)
        # endRange= datetime(currentDate.year,1,2)
        startRange= endRange - timedelta(weeks=5)
        logger.debug(f"Gathering: Time Off Requests {toMST(startRange)} to {toMST(endRange)}")
        timeOffrequest = await getTimeOff(wkSpaceID, startRange.strftime("%Y-%m-%d"), endRange.strftime("%Y-%m-%d"), page)
        logger.debug("Data Collected ")
        while endRange.year == currentDate.year:
            logger.info(f"Inserting From: of Time Off Requests {toMST(startRange)} to {toMST(endRange)}")
            logger.debug(f'Number of Records: {len(timeOffrequest["requests"])}')
            if len(timeOffrequest["requests"]) == 200:
                logger.info("New page on current Month")
                page += 1
            else:
                page = 1 
                endRange = startRange
                logger.debug(f"[Start: {startRange}] - [END: {endRange}]")
                startRange = endRange - timedelta(weeks=5)
            intermediate = getTimeOff(wkSpaceID, startRange.strftime("%Y-%m-%d"), endRange.strftime("%Y-%m-%d"), page)
            for requests in timeOffrequest["requests"]:
                failed = True
                userID = requests["userId"]
                user = await Employeeuser.objects.aget(id = userID)
                policyID = requests["policyId"]
                requestID = requests["id"] 
                status = requests['status']['statusType']
                start = datetime.strptime(requests["timeOffPeriod"]["period"]["start"], '%Y-%m-%dT%H:%M:%SZ')
                end   = datetime.strptime(requests["timeOffPeriod"]["period"]["end"], '%Y-%m-%dT%H:%M:%SZ') 
                startDate = toMST(start , True)
                endDate   = toMST(end, True)
                duration = await sync_to_async(count_working_days)(start.date(), end.date())
                logger.debug("Counted Days")
                paidTimeOff = requests["balanceDiff"]
                balance = requests['balance']

                workspace = await Workspace.objects.aget(id=wkSpaceID)
                try:
                    timeOff = await TimeOffRequests.objects.aget(id=requestID, workspaceId=workspace)                   
                    timeOff.userId= user
                    timeOff.policyId = policyID
                    timeOff.start = startDate
                    timeOff.end = endDate
                    timeOff.duration = duration
                    timeOff.status=status
                    timeOff.balanceDiff = paidTimeOff
                    logger.info(f"Updating Timeoff Request")
                    failed = False
                except TimeOffRequests.DoesNotExist:
                    logger.info(f"Inserting Timeoff Request")
                    timeOff = await TimeOffRequests.objects.acreate(
                        id=requestID,
                        userId=user,
                        policyId=policyID,
                        start=startDate,
                        end=endDate,
                        duration=duration,
                        status=status,
                        balanceDiff=paidTimeOff,
                        workspaceId=workspace
                    )
                    failed = False
                finally:
                    if not failed:
                        logger.info(f"\tSaving record with status: {status}")
                        await timeOff.asave()
            logger.info("Loading Next Page")
            timeOffrequest = await intermediate
        logger.info("Operation Completed: TimeOffRequest table")
        return "TimeOffEvent: Success"
    except Exception as e: 
        logger.critical(f'{str(e)} - {e.__traceback__.tb_lineno}')
        raise e

def pushWorkspaces(conn, cursor):
    """
    Inserts workspace records into the database if they do not already exist.

    Args:
        conn: Connection object for the database.
        cursor: Cursor object for executing SQL queries.

    Returns:
        str: Message indicating the operation status.
    """
    count = 0
    key = getApiKey()
    workspaces = getWorkspaces(key)
    for key, value in workspaces.items():
        try:
            cursor.execute(
                '''
                INSERT INTO Workspace (id, name)
                SELECT ?, ? 
                WHERE NOT EXISTS (
                        SELECT 1 FROM Workspace WHERE id = ?
                    )
                ''',(
                    (value, key, value)
                )
            )
            conn.commit()
            logger.info("Committing changes...")
        except pyodbc.OperationalError as e:
            logger.error("OperationalError:", str(e))
        except pyodbc.ProgrammingError as e:
            logger.error("ProgrammingError:", str(e))
        except pyodbc.DatabaseError as e:
            logger.error("DatabaseError:", str(e))
        except Exception :
            logger.error("Unexpected Error:", str(e))  
    return(f"Operation Completed. Workspace table has {count} new records")

def pushProjects(wkSpaceID):
    """
    Inserts project records into the database. Treats all project quearies as one trasaction and rolls back on exceptions.

    Args:
        wkSpaceID: Workspace ID.
        conn: Connection object for the database.
        cursor: Cursor object for executing SQL queries.

    Returns:
        str: Message indicating the operation status.
    """
    page = 1
    key = getApiKey()
    projects = getProjects(wkSpaceID, key)
    try:
        while len(projects) >=1:
            logger.info(f"Inserting Page: {page} of Projects ({len(projects)} records)")
            for project in projects:
                id = project['id']
                name = project['name']
                proj = name.split(' - ')
                code = proj[0]
                if len(code)== 0 :
                    code = "N/A"
                title = ' - '.join(proj[1:])
                if len(title)== 0 :
                    title = "INVALID"
                if len(project['clientId'])==0:
                    cID = '65e8b30e3676853154086777'
                    logger.warning(f'client is Null so mapping to HPC')
                else: cID = project['clientId']
                client = Client.objects.get(id=cID)
                workspace = Workspace.objects.get(id=wkSpaceID)
                try:
                    proj = Project.objects.get(id=id, workspaceId=workspace)
                    proj.name = name
                    proj.title = title
                    proj.code = code
                    proj.clientId = client 
                    failed = False
                    logger.info(f"Updating Project Record")
                except Project.DoesNotExist:
                    proj = Project.objects.create(
                        id = id,
                        name = name,
                        title = title,
                        code = code,
                        clientId = client,
                        workspaceId = workspace
                    )
                    logger.info("Inserting Project Record")
                    failed = False
                finally:
                    if not failed:
                        proj.save()
                    
            page += 1
            projects = getProjects(wkSpaceID, key, page)
        return "ProjectEvent: Success"
    except Exception as e :
        logger.error(f"{e.__class__}): {e.__traceback__.tb_frame.f_code.co_filename}, {e.__traceback__.tb_frame.f_code.co_name}/ Line: {e.__traceback__.tb_lineno}. {str(e)}\n")
        raise e

def pushUsers(wkSpaceID):
    """
    Inserts or updates user records into the database. Treats all user records as one transaction and rolls back on exceptions.

    Args:
        wkSpaceID: Workspace ID.
        conn: Connection object for the database.
        cursor: Cursor object for executing SQL queries.

    Returns:
        str: Message indicating the operation status.
    """

    key = getApiKey()
    users = getWorkspaceUsers(wkSpaceID, key)
    try:
        for user in users:
            name = user['name']
            email = user['email']
            id = user['id']
            status = user['status']
            for custom in user["customFields"]:
                fieldName =  custom['customFieldName']
                if fieldName == "Role":
                    role = custom["value"]
                elif fieldName == "Start Date":
                    start = custom["value"]
                elif fieldName == "Truck":
                    hasTruck = custom["value"]
                elif fieldName == "Rate Type":
                    rateType = custom["value"]
                elif fieldName == "Reporting Manager":
                    manager = custom["value"]
                elif fieldName == "End Date":
                    end = custom["value"]
                elif fieldName == "Truck Details":
                    truckDetails = custom["value"]
                else:
                    raise KeyError(fieldName)
           # hourlyRate = user['memberships']['hourlyRate']['amount']/100
            # insert record 
            failed = True
            try: 
                emp = Employeeuser.objects.get(id=id)
                emp.email = email
                emp.name = name
                emp.status = status 
                emp.role = role 
                emp.manager = manager 
                emp.start_date = start 
                emp.end_date = end 
                emp.hourly = rateType
                emp.Truck = hasTruck
                emp.truckDetails = truckDetails
                logger.info(f"Updating EmployeeUser")
                failed = False
            except Employeeuser.DoesNotExist: 
                logger.info(f'Inserting EmployeeUser ')
                emp = Employeeuser.objects.create(
                    id = id,
                    email = email,
                    name = name,
                    status = status ,
                    role = role ,
                    manager = manager ,
                    start_date = start ,
                    end_date = end ,
                    hourly = rateType,
                    Truck = hasTruck,
                    truckDetails = truckDetails
                )
                failed = False
            finally:
                if not failed:
                    emp.save()
    except Exception as  exc :
        logger.error(f"{exc.__class__}({exc.__traceback__.tb_lineno}): {str(exc)}")
        raise exc



def pushClients(wkSpaceID, conn, cursor):
    """
    Inserts client records into the database. 
    Updates client table.
    treatese all client operations as one transaction, rollsback on exceptions

    Args:
        wkSpaceID: Workspace ID.
        conn: Connection object for the database.
        cursor: Cursor object for executing SQL queries.

    Returns:
        str: Message indicating the operation status.
    """
    logger = setup_server_logger('DEBUG')
    count = 0
    update =0
    exists = 0
    try:  
        key = getApiKey()
        clients = getClients(wkSpaceID, key)
        for client in clients:
            logger.debug(json.dumps(client))
            cID = client['id']
            cEmail = client['email']
            cAddress = client['address']
            cName = client ['name']
            cLongName = client['note']
            try:
                cursor.execute(
                    '''
                    INSERT INTO Client ( id, email, address, name, workspace_id, longName)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''',
                    (cID, cEmail, cAddress, cName, wkSpaceID, cLongName)
                )
                logger.info(f"Adding Client information...({count})")
                count += 1
            except pyodbc.IntegrityError as e:
                if 'PRIMARY KEY constraint' in str(e) or 'PRIMARY KEY constraint' in str(e):
                    cursor.execute( 
                        '''
                        SELECT email, address, name, longName FROM Client
                        Where id = ? and workspace_id = ?
                        ''', (cID, wkSpaceID)
                    )
                    oldClient = cursor.fetchone()
                    if (
                        ((cEmail is not None or oldClient[0] is not None) and cEmail != oldClient[0])
                        or ((cAddress is not None or oldClient[1] is not None) and cAddress != oldClient[1])
                        or ((cName is not None or oldClient[2] is not None) and cName != oldClient[2])
                        or ((cLongName is not None or oldClient[3] is not None) and cLongName != oldClient[3])
                    ):
                        
                        logger.debug(cLongName)
                        logger.debug(oldClient)
                        cursor.execute(
                            '''
                            Update Client
                            set 
                                email = ?,
                                address = ?,
                                name = ?,
                                longName = ?
                            where 
                                id = ? and workspace_id = ?
                            ''',
                            (cEmail, cAddress, cName, cLongName, cID, wkSpaceID )
                        )
                        logger.info(f"\tUpdating Client information...({cName})")
                        update += 1
                    else:
                        exists += 1
                        logger.info(f"Loading..........{str(round( (exists+update+count)/len(clients) ,2)*100)[:5]}%")                
                else:
                    raise
    except Exception as  exc :
        conn.rollback()  # Roll back changes if an exception occurs
        logger.error(f"Error ({exc.__class__}): \n----------{exc.__traceback__.tb_frame.f_code.co_filename}, {exc.__traceback__.tb_frame.f_code.co_name} \n\tLine: {exc.__traceback__.tb_lineno} \n----------{str(exc)}\n")
        raise e
    else:
        conn.commit()
        logger.info("Committing changes...")  # Commit changes if no exceptions occurred                    
        return(f"ClientEvent: Success")

def pushPolicies(wkSpaceID, conn, cursor):
    """
    Updates or inserts time off policies into the database.

    Args:
        wkSpaceID (str): Workspace ID.
        conn: Connection object for the database.
        cursor: Cursor object for executing SQL queries.

    Returns:
        str: Message indicating the operation status.
    """
    count = 0
    key = getApiKey()
    policies = getPolocies(wkSpaceID , key)
    update = 0
    exists = 0
    try:
        for policy in policies:
            pId = policy["id"]
            pName = policy["name"]
            accrual_amount = policy["automaticAccrual"]["amount"] if policy["automaticAccrual"] is not None else 0
            accrual_period = policy["automaticAccrual"]["period"] if policy["automaticAccrual"] is not None else 'N/A'
            timeUnit = policy["automaticAccrual"]["timeUnit"] if policy["automaticAccrual"] is not None else 'HOURS'
            archived = policy["archived"]
            try:
                cursor.execute(
                    '''
                    INSERT INTO TimeOffPolicies(id, policy_name ,accrual_amount, accrual_period , time_unit, wID, archived)
                    VALUES (?, ?, ?, ?, ? , ? , ?) 
                    ''', (pId, pName, accrual_amount, accrual_period, timeUnit, wkSpaceID, archived)
                )
                logger.info(f"Adding Policies Information...({count})")
                count += 1
            except pyodbc.IntegrityError:
                cursor.execute(
                    '''
                    SELECT policy_name ,accrual_amount, accrual_period , time_unit, archived
                    FROM TimeOffPolicies
                    WHERE id = ? 
                    ''', (pId)
                )
                oldPolicy = cursor.fetchone()
                if (
                    (pName != oldPolicy[0] ) or (round(accrual_amount,2) != round(oldPolicy[1], 2))
                    or (accrual_period != oldPolicy[2]) or (timeUnit != oldPolicy[3]) 
                    or ( archived != oldPolicy[4])
                ):
                    cursor.execute(
                        '''
                        UPDATE TimeOffPolicies
                        SET 
                            policy_name = ?,
                            accrual_amount = ?,
                            accrual_period = ?,
                            time_unit = ?,
                            archived = ?
                        WHERE id = ?
                        ''', ( pName, accrual_amount, accrual_period, timeUnit, archived, pId)
                    )
                    logger.info(f"\tUpdating Policies information...{update}")
                    update += 1
                else:
                    exists += 1
                    logger.info(f"Loading..........{str(round((exists+update+count)/len(policies),2)*100)[:5]}%")
    except Exception as  exc :
        conn.rollback()  # Roll back changes if an exception occurs
        logger.error(f"Error ({exc.__class__}): \n----------{exc.__traceback__.tb_frame.f_code.co_filename}, {exc.__traceback__.tb_frame.f_code.co_name} \n\tLine: {exc.__traceback__.tb_lineno} \n----------{str(exc)}\n")
        return f"Operation failed. Changes rolled back. Contact administer of problem persists"
    else:
        conn.commit()
        logger.info("Committing changes...")  # Commit changes if no exceptions occurred                     
        return(f"Operation Completed: Policies table has {count} new records and {exists} unchanged. {update} records updated.\n")

def updateCalendar(date, conn, cursor):
    """
    Updates the calendar table for the specified year.

    Args:
        date (str): The year to update the calendar for (format: "YYYY").
        conn: Connection object for the database.
        cursor: Cursor object for executing SQL queries.
    """
    #days are not in the calander yet , add that current year 
    startDate = date[:4] + "-01-01"
    endDate = date[:4] + "-12-31"
    try:
        cursor.execute(
            '''
            DECLARE @startDate DATE = ?;
            DECLARE @endDate DATE = ?;

            -- Loop through each day within the specified range and insert into the Calendar table
            DECLARE @currentDate DATE = @startDate;
            WHILE @currentDate <= @endDate
            BEGIN
                INSERT INTO Calendar ([date], dayOfWeek, [month], [year])
                VALUES (
                    @currentDate,
                    DATEPART(WEEKDAY, @currentDate),  -- Day of the week (1 = Sunday, 2 = Monday, ..., 7 = Saturday)
                    DATEPART(MONTH, @currentDate),    -- Month (1-12)
                    DATEPART(YEAR, @currentDate)      -- Year
                );
                
                -- Increment the current date by one day
                SET @currentDate = DATEADD(DAY, 1, @currentDate);
            END;
        ''', (startDate, endDate)
            )
    except Exception:
        logger.warning("Rolling Back Calendar changes")
        conn.rollback()
        return "Rolling Back Calendar changes"
    else:
        conn.commit()
        logger.info("Committing changes...")
        logger.info(f"Updated Calander Dates for Year {date[:4]}")
        return "Calendar: Success"
####################################################################################################################################################################################