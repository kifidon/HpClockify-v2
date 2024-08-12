import pyodbc
import copy
import json
# import logging
from .. Loggers import setup_background_logger, setup_server_logger
from .ClockifyPullV3 import getApiKey, getWorkspaces,getWorkspaceUsers, getProjects, getApprovedRequests, getHolidays, getClients, getPolocies, getTimeOff, getUserGroups
from .hpUtil import sqlConnect, cleanUp, pytz, datetime, timedelta, timeZoneConvert, timeDuration, count_working_days
logger = setup_server_logger('DEBUG')

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

def pushUsers(wkSpaceID, conn, cursor):
    """
    Inserts or updates user records into the database. Treats all user records as one transaction and rolls back on exceptions.

    Args:
        wkSpaceID: Workspace ID.
        conn: Connection object for the database.
        cursor: Cursor object for executing SQL queries.

    Returns:
        str: Message indicating the operation status.
    """

    count = 0
    update = 0
    exists = 0
    key = getApiKey()
    users = getWorkspaceUsers(wkSpaceID, key)
    try:
        for user in users:
            uName = user['name']
            uEmail = user['email']
            uid = user['id']
            status = user['status']
           # hourlyRate = user['memberships']['hourlyRate']['amount']/100
            # insert record 
            try: 
                cursor.execute(
                        # INSERT INTO EmployeeUser (id, email, name, [status], baseRate)
                    '''
                        INSERT INTO EmployeeUser (id, email, name, [status])
                        VALUES (?, ?, ?, ?)
                    ''', (uid, uEmail, uName, status )
                        # VALUES (?, ?, ?, ?, ?)
                    # (uid, uEmail, uName, status, hourlyRate )
                )
                logger.info(f"Adding Employee  information: {uName} ({count})")
                # pushRates(conn, cursor, user, uid)
                count += 1
            except pyodbc.IntegrityError as e:
                if "PRIMARY KEY constraint" in str(e):
                    try: 
                        cursor.execute(
                            '''
                            SELECT eu.[name], eu.email, eu.[status] FROM EmployeeUser eu
                            WHERE eu.id = ?
                            ''',(uid,)
                        )
                        employee = cursor.fetchone() 
                        if ((uName is not None or employee[0] is not None) and ( uName != employee[0])) or \
                            ((uEmail is not None or employee[1] is not None) and( uEmail != employee[1])) or \
                            ((status is not None or employee[2] is not None) and  (status != employee[2]) 
                            # or (round(float(employee[3]), 2) != round(float(hourlyRate,2)))
                        ):
                            # New and old column mismatch. Update record 
                            cursor.execute(
                                    #baseRate = ?
                                '''
                                UPDATE EmployeeUser 
                                SET 
                                    [name] = ?,
                                    email = ?,
                                    [status] = ?
                                WHERE [id] = ?
                                ''', (uName, uEmail, status, uid)
                                # (uName, uEmail, status, hourlyRate, uid)
                            )
                            logger.info(f"\tUpdating Employee information: {uName} ({update})")
                            update += 1
                        # record already exists and doesnt need to be updated 
                        else: 
                            exists += 1
                            logger.info(f"Loading..........{str(round((exists+update+count)/len(users), 2) *100)[:5]}%")
                    # Unknown error occured, most likley a problem with code logic (debugging)
                    except pyodbc.OperationalError:
                        raise
                    except pyodbc.ProgrammingError :
                        raise
                    except pyodbc.DatabaseError :
                        raise
                # Unknown integrity constraint that wasn't handled.
                else: 
                    raise          
    except Exception as  exc :
        conn.rollback()  # Roll back changes if an exception occurs
        logger.error(f"Error ({exc.__class__}): \n----------{exc.__traceback__.tb_frame} \n----------{str(exc)}")
        return f"Operation failed. Changes rolled back. Contact administer of problem persists"
    else:
        conn.commit()
        logger.info("Committing changes...")  # Commit changes if no exceptions occurred
        return(f"Operation Completed: EmployeeUser table has {count} new records and {exists} unchanged. {update} records updated. \n")

def deleteProjects(conn, cursor, wkSpaceID):
    """
    Deletes Projects for a given time sheet. Delete condition is "If still in database but not pullable from clockify"

    Args:
        conn: Connection object for the database.
        cursor: Cursor object for executing SQL queries.
        aID (str): Time sheet ID.
        projects (list): List of projects to delete.

    Returns:
        int: Number of entries deleted.
    """
    deleted = 0
    newProj = []
    page = 1
    key = getApiKey()
    projects = getProjects(wkSpaceID, key, page)
    while len(projects) != 0:
        for proj in projects:
            newProj.append(proj["id"])
        page += 1
        projects = getProjects(wkSpaceID, key, page)
    try: 
        cursor.execute(
            '''
            SELECT id, workspace_id  From Project
            '''
        )
        oldProjects = cursor.fetchall()
        for delete in oldProjects:
            try:
                if delete[0] not in newProj:
                    cursor.execute(
                        '''
                        DELETE FROM Project
                        WHERE 
                            id = ? and
                            workspace_id = ?
                        ''', (delete[0], wkSpaceID)
                    )
                    logger.info(f"\t\t\tDeleted...{deleted}")
                    deleted += 1
            except pyodbc.IntegrityError as e:
                logger.warning(f"Can't delete project: {e}") 
                continue
    except Exception as  exc :
        conn.rollback()  # Roll back changes if an exception occurs
        logger.error(f"Error ({exc.__class__}): \n----------{exc.__traceback__.tb_frame.f_code.co_filename}, {exc.__traceback__.tb_frame.f_code.co_name} \n\tLine: {exc.__traceback__.tb_lineno} \n----------{str(exc)}\n")
        logger.error("Operation failed. Changes rolled back. Contact administer of problem persists")
    else:
        # Commit changes in timesheet function if no exceptions occurred               
        return deleted

def updateProjects(conn, cursor, count, update, exists, pID, pCode, pTitle, pName, cID, projects, wkSpaceID):
    try:
        cursor.execute(
            '''
            SELECT [title], code, client_id, workspace_id FROM Project
            WHERE [id] = ?
            ''', (pID,)
        )
        oldProj = cursor.fetchone()              
        if (
            ((pName is not None or oldProj[0] is not None) and (oldProj[0] != pName))
            or ((pCode is not None or oldProj[1] is not None) and (oldProj[1] != pCode))
            or ((cID is not None or oldProj[2] is not None) and (oldProj[2] != cID))
        ):
            cursor.execute(
                '''
                UPDATE Project
                SET 
                    title= ?,
                    name = ?,
                    client_id = ?,
                    code = ?
                WHERE id = ? and workspace_id = ?
                ''', (pName, pTitle, cID, pCode, pID, wkSpaceID)
            )
            logger.info(f"\tUpdating Project information...({update})")
            update += 1
            return (count, update, exists, True)
        else: # record is unchanged 
            exists += 1
            logger.info(f"\tLoading..........{str(round((exists+update+count)/len(projects),2)*100)[:5]}%")
            return (count, update, exists, True)
    except pyodbc.IntegrityError as ex: # error in updating or checking for update 
        if 'FOREIGN KEY constraint' in str(ex):
            logger.error(pushClients(wkSpaceID, conn, cursor) + " Called by Project Function (update)")
            return (count, update, exists, False)
        else:
            raise          

def pushProjects(wkSpaceID, conn, cursor):
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
    gExists = 0
    gUpdate = 0
    gCount = 0
    exists = 0
    update = 0
    count = 0
    key = getApiKey()
    projects = getProjects(wkSpaceID, key)
    deleted = 0
    # deleted = deleteProjects(conn, cursor, wkSpaceID)
    try:
        while len(projects) >=1 and page != 10:
            gExists += exists; exists = 0
            gUpdate += update; update = 0
            gCount += count; count = 0
            logger.info(f"Inserting Page: {page} of Projects ({len(projects)} records)")
            for project in projects:
                pID = project['id']
                pTitle = project['name']
                proj = pTitle.split(' - ')
                pCode = proj[0]
                if len(pCode)== 0 :
                    pCode = None
                pName = ' - '.join(proj[1:])
                if len(pName)== 0 :
                    pName = None
                if len(project['clientId'])==0:
                    cID = '65e8b30e3676853154086777'
                    logger.info(f'client is Null so mapping to HPC')
                else: cID = project['clientId'] or '65e8b30e3676853154086777'
                # insert project 
                for i in range (0,2): 
                    try:
                        cursor.execute(
                            '''
                            Select id, workspace_id from Project where id = ? and workspace_id = ?
                            ''', (pID, wkSpaceID)
                        )
                        oldID = cursor.fetchone()
                        if oldID is not None:
                            count, update, exists, FLG_update = updateProjects(conn, cursor, count, update, exists, pID, pCode, pTitle,  pName, cID, projects, wkSpaceID)
                            if FLG_update:
                                break
                        else: 
                            cursor.execute(
                                '''
                                    INSERT INTO Project( id, name, title, client_id, code, workspace_id)
                                    Values ( ?, ?, ?, ?, ?, ?) 
                                ''', (pID, pTitle, pName, cID, pCode, wkSpaceID)#title and name semantics are switched
                            )
                            logger.info(f"\tAdding Project information...({count})")
                            count += 1
                            break
                    except pyodbc.IntegrityError as e:
                        message = str(e)
                        # record is already in table, check for update 
                        if 'PRIMARY KEY constraint' in message:
                            count, update, exists, FLG_update = updateProjects(conn, cursor, count, update, exists, pID, pCode, pName, cID, projects, wkSpaceID)
                            if FLG_update:
                                break    
                        elif 'FOREIGN KEY constraint' in message: 
                            logger.info(pushClients(wkSpaceID, conn, cursor) + " Called by Project Function (insert)")
                        else: 
                            raise
            page += 1
            projects = getProjects(wkSpaceID, key, page)
    except Exception as  exc :
        conn.rollback()  # Roll back changes if an exception occurs
        logger.error(f"Error ({exc.__class__}): \n----------{exc.__traceback__.tb_frame.f_code.co_filename}, {exc.__traceback__.tb_frame.f_code.co_name} \n\tLine: {exc.__traceback__.tb_lineno} \n----------{str(exc)}\n")
        return f"Operation failed. Changes rolled back. Contact administer of problem persists"
    else:
        conn.commit()
        logger.error("Committing changes...")  # Commit changes if no exceptions occurred              
        return(f"Operation Completed: Project table has {gCount} new records and {gExists} unchanged. {gUpdate} records updated. {deleted} deleted" +"\n")

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
    
    key = getApiKey()
    clients = getClients(wkSpaceID, key)
    try:
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
        return f"Operation failed. Changes rolled back. Contact administer of problem persists"
    else:
        conn.commit()
        logger.info("Committing changes...")  # Commit changes if no exceptions occurred                    
        return(f"Client: {count} new records. {exists} unchanged. {update} updated.\n")

def pushTags(wkSpaceID, conn, cursor, tags: list, aID, enID):
    update = 0; exists = 0; count = 0
    try:
        for tag in tags: 
            cursor.execute(
                '''
                select id, entryID, timeID, name, workspace_id
                from TagsFor
                where id = ? and entryID = ? and workspace_id =?
                ''', (tag["id"], enID, wkSpaceID)
            )
            existingTag = cursor.fetchone()
            if existingTag is None: # insert new 
                cursor.execute(
                    '''
                    insert into TagsFor (id, entryID, timeID, name, workspace_id)
                    values (?, ?, ?, ?, ?)
                    ''', (tag["id"], enID, aID, tag["name"], wkSpaceID)
                )
                count += 1
                logger.info(f"\t\tAdding Tag {tag['name']} to Entry")
            else: # Check if update is needed 
                if existingTag[3] == tag['name']: # exists 
                    exists += 1
                    logger.info (f"\t\t\tLoading tag {tag['name']}")
                else: # update 
                    cursor.execute(
                        '''
                        Update TagFor
                        set name = ?
                        where id = ? and workspace_id = ?, and entryId = ?
                        ''', (tag["name"], tag["id"], wkSpaceID, enID)
                    )
                    update += 1
                    logger.info(f"\t\t\tUpdating tag name {existingTag[3]} to {tag['name']}")
    except Exception as  exc :
        conn.rollback()  # Roll back changes if an exception occurs
        logger.error(f"Error ({exc.__class__}): \n----------{exc.__traceback__.tb_frame.f_code.co_filename}, {exc.__traceback__.tb_frame.f_code.co_name} \n\tLine: {exc.__traceback__.tb_lineno} \n----------{str(exc)}\n")
        logger.error("Operation failed. Changes rolled back. Contact administer of problem persists")
        raise
    else:
        # Commit changes in Timesheet Function function if no exceptions occurred       
        # logger.info(f"\t\t\tTag:  {count} new records. {exists} unchanged. {update} updated. {deleted} deleted.")
        return(f"\t\t\tTag:  {count} new records. {exists} unchanged. {update} updated.")
         
def deleteEntries(conn, cursor, entries, aID):
    """
    Deletes entries for a given time sheet. Delete condition is "If still in database but not pullable from clockify"

    Args:
        conn: Connection object for the database.
        cursor: Cursor object for executing SQL queries.
        aID (str): Time sheet ID.
        entries (list): List of entries to delete.

    Returns:
        int: Number of entries deleted.
    """
    newEntries = []
    deleted =0 
    try: 
        cursor.execute(
            '''
            SELECT id From Entry
            WHERE time_sheet_id = ?
            ''',(aID,)
        )
        entriesForTimesheet = cursor.fetchall()
        for entry in entries:
            newEntries.append(entry['id'])
        for delete in entriesForTimesheet:
            if delete[0] not in newEntries:
                cursor.execute(
                    '''
                    DELETE FROM Entry
                    WHERE id = ? AND time_sheet_id = ?
                    ''', (delete[0], aID)
                )
                logger.info(f"\t\t\tDeleted...{deleted}")
                deleted += 1
    except Exception as  exc :
        conn.rollback()  # Roll back changes if an exception occurs
        logger.error(f"Error ({exc.__class__}): \n----------{exc.__traceback__.tb_frame.f_code.co_filename}, {exc.__traceback__.tb_frame.f_code.co_name} \n\tLine: {exc.__traceback__.tb_lineno} \n----------{str(exc)}\n")
        logger.error("Operation failed. Changes rolled back. Contact administer of problem persists")
        raise
    else:
        # Commit changes in timesheet function if no exceptions occurred      
        return(deleted)

def pushEntries(approve, conn, cursor, wkSpaceID, aID, FK_ConstraintOnEntry):
    logger.info('\t\tPush time Entries')
    """
    Pushes entries data to the database. 

    Parameters:
        approve (dict): A dictionary containing entries data to be pushed.
        conn (pyodbc.Connection): A connection object to the database.
        cursor (pyodbc.Cursor): A cursor object to execute SQL queries.
        wkSpaceID (str): Workspace ID associated with the entries data.

    Returns:
        str: A string indicating the status of the operation, including the number of new records, updates, and errors.
    """
    update = 0
    exists = 0
    count = 0
    entries = approve['entries']
    deleted = 0 
    deleteEntries(conn, cursor, entries, aID) # delete stale entries before inserting, as to minimize transactions
    try:
        for entry in entries:
            approval = entry['approvalRequestId'] or aID
            if entry['approvalRequestId'] is not None and entry['approvalRequestId'] != '' and entry['approvalRequestId'] != aID:
                logger.critical("Critical logic error - Timesheet ID and 'approvalRequestId' do not match")
            eID = entry['id']
            duration = timeDuration(entry['timeInterval']['duration'])
            description = entry['description']
            billable = entry['billable']
            projectID = entry['project']['id']
            type = entry['type']
            # set default start time to 8am and end time to {duration} hours after
            startTime = timeZoneConvert(entry['timeInterval']['start'], '%Y-%m-%dT%H:%M:%SZ')
            endTime = timeZoneConvert(entry['timeInterval']['end'], '%Y-%m-%dT%H:%M:%SZ') 
            rate = entry['hourlyRate']['amount'] if entry['hourlyRate'] is not None else 0
            tags = entry['tags']
            logger.info(f'\t\t\t{description}')
            while True:
                try: # insert entry
                    cursor.execute( 
                        '''
                        SELECT time_sheet_id, duration, description, billable, project_id, type, start_time, end_time, rate 
                        FROM Entry
                        WHERE id = ?  and workspace_id = ?
                        ''', (eID, wkSpaceID)
                    )
                    oldEntry = cursor.fetchone()
                    if(oldEntry is None): # insert new 
                        cursor.execute(
                            '''
                                INSERT INTO Entry (id, time_sheet_id, duration, description, billable, project_id, type, start_time, end_time, rate, workspace_id)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''',(
                                eID, 
                                approval, 
                                duration, 
                                description, 
                                billable,
                                projectID, 
                                type, 
                                startTime,
                                endTime, 
                                rate, 
                                wkSpaceID
                                )
                        )
                        count +=1
                        break
                    else: # update entry
                        try:
                            cursor.execute(
                                '''
                                UPDATE Entry
                                SET 
                                    duration = ?,
                                    description = ?,
                                    billable = ?,
                                    project_id = ?,
                                    type = ?,
                                    start_time = ?,
                                    end_time = ?,
                                    rate = ?
                                WHERE id = ? and workspace_id = ?
                                ''',
                                (duration, description, billable, projectID, type, startTime, endTime, rate, eID,  wkSpaceID)
                            )
                            logger.info(f"\tUpdating Entry information...({startTime})")
                            update += 1
                            break
                        except pyodbc.IntegrityError as ex:
                            if "FOREIGN KEY constraint" in str(ex): # update projects and re try for this entry
                                logger.info(pushProjects(wkSpaceID, conn, cursor) + ". Called from Entries Function. (Update) \n")
                            else: # could be any error
                                raise                                 
                except pyodbc.IntegrityError as e:                   
                    if 'FOREIGN KEY constraint' in str(e): # update projects and try agaun. Only once per push request of timesheets
                        FK_ConstraintOnEntry += 1
                        if FK_ConstraintOnEntry <=1:
                            logger.info(f"Foreign Key Constraint on Projects. Attempting to handle\n----------------------")
                            logger.info(pushProjects(wkSpaceID, conn, cursor) + "\tCalled from Entries Function. (Insert) \n")
                        else:
                            if (FK_ConstraintOnEntry ==2):
                                logger.info(f"\tstaleEntry for TimeSheet{approval}- Project ({projectID}) No Longer Exists")
                            break
                        # Loop through this record again after adding reference 
                    elif 'PRIMARY KEY constraint' in str(e): 
                        logger.warning(f'Trying to insert a douplicate record - {eID}. Skipping operation and proceding to the next')
                        break
                        
            if len(tags)!= 0:
                logger.info(pushTags(wkSpaceID, conn, cursor, tags, approval, enID=eID))            
    except Exception as  exc :
        conn.rollback()  # Roll back changes if an exception occurs
        logger.error(f"Error ({exc.__class__}): \n----------{exc.__traceback__.tb_frame.f_code.co_filename}, {exc.__traceback__.tb_frame.f_code.co_name} \n\tLine: {exc.__traceback__.tb_lineno} \n----------{str(exc)}\n")
        logger.error("Operation failed. Changes rolled back. Contact administer of problem persists")
        raise
    else: # Commit changes in Timesheet function  if no exceptions occurredand check to delete 
        conn.commit()
        logger.info(f"\t\tEntry:  {count} new records. {update} updated. {deleted} deleted.")
        return(FK_ConstraintOnEntry)
'''
def pushExpenses(approve, timesheetID, conn, cursor):

    count = 0
    expenses = approve['expenses']
    for expense in expenses:
        eID = expense['id']
        billable = expense['billable']
        date = expense['date']
        notes = expense['notes']
        projectID = expense['project']['id']
        qty = expense['quantity']
        total = expense['total']
        category = expense['category']['id']
        try: 
            cursor.execute(
                \'''
                INSERT INTO Expenses(id, billable, date, notes, project_id, quantity, total, timesheet_id, category_id)
                SELECT ?, ?, ?, ?, ?, ?, ?, ?
                WHERE NOT EXISTS(
                    SELECT 1 FROM Expense WHERE id = ?
                )
                \''',
                (eID, billable, date, notes, projectID, qty, total, timesheetID, category, eID)
            )
            conn.commit()
    logger.info("Committing changes...")
            count += 1
        except pyodbc.IntegrityError as e:
            if 'PRIMARY KEY constraint' in str(e):
                continue
            else:
                logger.info(f"IntegrityError: {e}")
        except pyodbc.Error as e: 
            logger.info(f"Error: {e}")
    return(f"Operation Completed. Expenses table has {count} new records")
'''

def updateApprovals(update, count, exists, cursor, aID, userID, startDateO, endDateO, approvedTime, billableTime, 
                    billableAmount, costAmount, expenseTotal, status,  approve, approved, conn, wkSpaceID,FK_ConstraintOnEntry ):  
    try:
        cursor.execute(
            '''
            SELECT emp_id ,
                start_time,
                end_time,
                approved_time ,
                billable_time ,
                billable_amount ,
                cost_amount ,
                expense_total,
                status
            FROM TimeSheet 
            Where id = ? and workspace_id = ?
            ''', (aID, wkSpaceID)
        )
        oldTime = cursor.fetchone()

        startDateObject = copy.copy(startDateO).date()
        endDateObject = copy.copy(endDateO).date()

        if ((userID != oldTime[0]) or (startDateObject != oldTime[1]) or (endDateObject != oldTime[2])
            or (round(approvedTime, 2) != round(oldTime[3], 2))
            or (round(billableTime, 2) != round(oldTime[4], 2))
            or (round(float(billableAmount), 2) != round(float(oldTime[5]), 2))
            or (round(float(costAmount), 2) != round(float(oldTime[6]), 2))
            or (round(float(expenseTotal), 2) != round(float(oldTime[7]), 2)) or (status != oldTime[8])
        ):
            
            cursor.execute(
                '''
                UPDATE TimeSheet
                SET emp_id = ?,
                    start_time = ?,
                    end_time = ?,
                    approved_time = ?,
                    billable_time = ?,
                    billable_amount = ?,
                    cost_amount = ?,
                    expense_total = ?,
                    status = ?
                WHERE id = ? and workspace_id = ?;    
                ''', (userID, startDateO, endDateO, approvedTime, billableTime,
                    billableAmount, costAmount, expenseTotal, status, aID, wkSpaceID)
            )
            logger.info(f"\t\tUpdating Time Sheet...{str(round((exists + update + count) / len(approved), 2) * 100)[:5]}% ({aID})")
            update += 1
        else:
            exists += 1
            logger.info(f"\tTimeSheet Loading({aID})----------{str(round((exists + update + count) / len(approved), 2) * 100)[:5]}% (updateAproval)")
        # regardless if update on Time Sheet, Check for update on entries
        if status != 'WITHDRAWN_APPROVAL':
            FK_ConstraintOnEntry = pushEntries(approve, conn, cursor, wkSpaceID, aID, FK_ConstraintOnEntry)
            logger.info("\t\tTime Entry Information Added\n")
        return update, count, exists, True, FK_ConstraintOnEntry
    except pyodbc.IntegrityError as ex:
        if "FOREIGN KEY constraint" in str(ex):
            pushUsers(wkSpaceID, conn, cursor)
            return update, count, exists, False, FK_ConstraintOnEntry
        else:
            raise
    except Exception as e:
        logger.error(f'({e.__traceback__.tb_lineno}) - (str)')
        logger.warning(f'Skipping operaiion')
        return update, count, exists, True , FK_ConstraintOnEntry

#deprecitated 
def pushApprovedTime(wkSpaceID, conn, cursor, stat):

    """
    Pushes approved time data to the database. TimeSheets should not be updated. Include deletion in a future update 

    Parameters:
        wkSpaceID (str): The workspace ID associated with the approved time data.
        conn (pyodbc.Connection): A connection object to the database.
        cursor (pyodbc.Cursor): A cursor object to execute SQL queries.

    Returns:
        str: A string indicating the status of the operation, including the number of new records added.
    """
    key = getApiKey()
    approved = getApprovedRequests(wkSpaceID, key, status= stat)
    page = 1
    gCount = 0
    gUpdate = 0
    gExists = 0
    count = 0
    update = 0
    exists = 0
    FK_ConstraintOnEntry = 0
    try:
        while len(approved) != 0 and page < 30:
            
            logger.info(f"Inserting Page: {page} of TimeSheets ({len(approved)} records)")
            for approve in approved:
                aID = approve['approvalRequest']['id']
                userID = approve['approvalRequest']['owner']['userId']
                status = approve['approvalRequest']['status']['state']
                
                startDateO = timeZoneConvert(approve['approvalRequest']['dateRange']['start'])
                endDateO = timeZoneConvert(approve['approvalRequest']['dateRange']['end'])

                approvedTime = timeDuration(approve['approvedTime'])
                billableTime = timeDuration(approve['billableTime'])
                billableAmount = approve['billableAmount']
                costAmount = approve['costAmount']
                expenseTotal = approve['expenseTotal']
                # logger.info(f'{aID}, {userID}, {status}, {startDateO},')
                
                # continue
                while True:
                    try:   
                        #Check for the existance of this time sheet   
                        cursor.execute(
                            ''' 
                            select id, workspace_id, status, emp_id , start_time from Timesheet
                            where id = ? and workspace_id = ? and emp_id=?
                            ''', (aID, wkSpaceID, userID)
                        )
                        tsExists = cursor.fetchone()
                        if tsExists is None:
                            '''
                            New timesheet being added, or timesheet status has 
                            been reversed -> create a new timesheet 
                            '''
                            cursor.execute(
                                '''
                                INSERT INTO TimeSheet (
                                    id, 
                                    emp_id,
                                    start_time, 
                                    end_time, 
                                    approved_time, 
                                    billable_time, 
                                    billable_amount, 
                                    cost_amount, 
                                    expense_total,
                                    [status], 
                                    workspace_id)
                                VALUES (?, ?, CAST(? AS DATE) , CAST(? AS DATE) , ?, ?, ?, ?, ? ,?, ?)
                                '''
                                ,(
                                    aID, 
                                    userID, 
                                    startDateO, 
                                    endDateO,
                                    approvedTime, 
                                    billableTime, 
                                    billableAmount, 
                                    costAmount, 
                                    expenseTotal, 
                                    status, 
                                    wkSpaceID
                                    )
                            )
                            logger.info(f"\tAdding TimeSheet information...{aID}({count})")
                            FK_ConstraintOnEntry = pushEntries(approve, conn, cursor, wkSpaceID, aID, FK_ConstraintOnEntry)
                            logger.info("\tTime Entry Information Added\n")
                            # pushExpenses(approve, aID, conn, cursor)
                            count += 1
                            logger.debug(f'{approvedTime}, {costAmount}, {str(startDateO)}')
                            break
                        # elif tsExists is not None:
                        elif tsExists is not None or (tsExists[2] != status):
                            # logging.debug(f'DEBUG: Existing timeSheet "{aID}"')
                            # if (status != 'PENDING'):
                            #     logger.info(f'\tStatus change from {tsExists[2]} to {status} on timesheet: {aID}')
                            # else:
                            logger.info(f'\tChecking for updates Timesheet: {aID}')
                            update, count, exists, FK_errorOnUpdate ,FK_ConstraintOnEntry = updateApprovals( update, count, exists,
                                    cursor, aID, userID, startDateO, endDateO, approvedTime, billableTime, 
                                    billableAmount, costAmount, expenseTotal, status,  approve, approved, conn, wkSpaceID, FK_ConstraintOnEntry
                                    )
                            if (FK_errorOnUpdate):
                                break
                        else:
                            exists += 1
                            # logging.debug(f'{aID} {status}, {userID} {str(startDateO)}, {tsExists}')
                            logger.info(f"\tTimeSheet Loading({aID})----------{str(round((exists + update + count) / len(approved), 2) * 100)[:5]}%")
                           # FK_ConstraintOnEntry = pushEntries(approve, conn, cursor, wkSpaceID, aID, FK_ConstraintOnEntry)
                            break
                    except pyodbc.IntegrityError as e: 
                        if "FOREIGN KEY constraint" in str(e):
                            logger.info(pushUsers(wkSpaceID, conn, cursor) + ". Called by Approval Function")
                        elif "PRIMARY KEY constraint" or 'UNIQUE KEY constraint'in str(e):
                            update, count, exists, FK_errorOnUpdate, FK_ConstraintOnEntry = updateApprovals( update, count, exists,
                                    cursor, aID, userID, startDateO, endDateO, approvedTime, billableTime, 
                                    billableAmount, costAmount, expenseTotal, status,  approve, approved, conn, wkSpaceID, FK_ConstraintOnEntry
                                    )
                            if (FK_errorOnUpdate):
                                break
                        else:
                            raise # unknown integrity error on timesheet insert 
            
            page += 1
            gCount += count;  count = 0 
            gUpdate += update; update = 0
            gExists += exists ; exists = 0
            approved = getApprovedRequests(wkSpaceID, key, page, stat)
    except Exception as  exc :
        conn.rollback()  # Roll back changes if an exception occurs
        logger.error(f"Error ({exc.__class__}): \n----------{exc.__traceback__.tb_frame.f_code.co_filename}, {exc.__traceback__.tb_frame.f_code.co_name} \n\tLine: {exc.__traceback__.tb_lineno} \n----------{str(exc)}\n")
        return f"Operation failed. Changes rolled back. Contact administer of problem persists"
    else:
        conn.commit()
        logger.info("Committing changes...")  # Commit changes if no exceptions occurred                      
        return(f"Operation Completed: TimeSheet table has {gCount} new records and {gExists} unchanged. {gUpdate} records updated.\n")

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

def removeGroupMembership(conn, cursor, groupID, users, wkspace):
    """
    Removes group membership records from the database.

    Args:
        conn: Connection object for the database.
        cursor: Cursor object for executing SQL queries.
        groupID (str): ID of the group.
        users (list): List of user IDs to be removed from the group.
        wkspace (str): Workspace ID.

    Returns:
        int: Number of group membership records deleted.
    """
    newMembers = []
    deleted =0 
    try: 
        cursor.execute(
            '''
            SELECT user_id From GroupMembership
            WHERE group_id = ? and workspace_id = ?
            ''',(groupID, wkspace)
        )
        existingMembers = cursor.fetchall()
        for user in users:
            newMembers.append(user)
        for delete in existingMembers:
            if delete[0] not in newMembers:
                cursor.execute(
                    '''
                    DELETE FROM GroupMembership
                    WHERE user_id = ? AND group_id = ? and workspace_id = ?
                    ''', (delete[0], groupID, wkspace)
                )
                logger.info(f"\t\t\tDeleted...{deleted}")
                deleted += 1
    except Exception as  exc :
        conn.rollback()  # Roll back changes if an exception occurs
        logger.error(f"Error ({exc.__class__}): \n----------{exc.__traceback__.tb_frame.f_code.co_filename}, {exc.__traceback__.tb_frame.f_code.co_name} \n\tLine: {exc.__traceback__.tb_lineno} \n----------{str(exc)}\n")
        logger.error("Operation failed. Changes rolled back. Contact administer of problem persists")
        raise
    else:
        # Commit changes in Groups Function if no exceptions occurred  
        conn.commit() # saves deletions                    
        return(deleted)

def pushGroupMembership(conn, cursor, groupID, users ,wkspace):
    """
    Adds users to a group in the database.

    Args:
        conn: Connection object for the database.
        cursor: Cursor object for executing SQL queries.
        groupID (str): ID of the group.
        users (list): List of user IDs to be added to the group.
        wkspace (str): Workspace ID.

    Returns:
        str: Message indicating the operation status.
    """
    count = 0
    exists = 0
    update = 0 
    try:
        for userID in users:
            try: 
                cursor.execute(
                    '''
                    insert into GroupMembership (group_id, user_id, workspace_id)
                    values (?, ?, ?)
                    ''', (groupID, userID, wkspace)
                )
                logger.info(f"\t\tAdding User to Group: {userID}.")
                count += 1
            except pyodbc.IntegrityError as e:
                if "PRIMARY KEY constraint" in str(e):
                    exists += 1
                    logger.info(f"\t\tLoading..........{str(round((exists+update+count)/len(users),2)*100)[:5]}%")
                else:
                    raise   
        deleted = 0
    except Exception as  exc :
        conn.rollback()  # Roll back changes if an exception occurs
        logger.error(f"Error ({exc.__class__}): \n----------{exc.__traceback__.tb_frame.f_code.co_filename}, {exc.__traceback__.tb_frame.f_code.co_name} \n\tLine: {exc.__traceback__.tb_lineno} \n----------{str(exc)}\n")
        return f"Operation failed. Changes rolled back. Contact administer of problem persists"
    else:
        # Commit changes in Group Users function if no exceptions occurred
        conn.commit() 
        removeGroupMembership(conn, cursor, groupID, users, wkspace)
        return(f"\t\tOperation Completed: Added {count} new records, {exists} unchanged. {deleted} records deleted From group {groupID}. \n")
    
def pushUserGroups(wkSpaceID, conn, cursor):
    """
    Inserts or updates user group records in the database.

    Args:
        wkSpaceID: Workspace ID.
        conn: Connection object for the database.
        cursor: Cursor object for executing SQL queries.

    Returns:
        str: Message indicating the operation status.
    """
    count = 0
    update = 0
    exists = 0
    groups = getUserGroups(wkSpaceID)
    try:
        for group in groups:
            groupID = group['id']
            gName = group['name']
            wkscpace = group['workspaceId']
            users = group['userIds']
            # insert into groups 
            while True:
                try:
                    cursor.execute(
                        '''
                        insert into UserGroups(id, [name], [workspace_id] )
                        values( ?, ?, ? )
                        ''',(groupID, gName, wkscpace )
                    )
                    # assign users to a group
                    logger.info(f"Adding User Group ID: \"{gName}\" ({count})") 
                    count += 1
                    # add users to a group 
                    logger.info(pushGroupMembership(conn, cursor, groupID, users, wkscpace))
                    break
                except pyodbc.IntegrityError as e:
                    if "FOREIGN KEY constraint" in str(e):
                        pushUsers(wkscpace, conn, cursor)
                    elif "PRIMARY KEY constraint" in str(e):
                        cursor.execute(
                            '''
                            select [name] from UserGroups
                            where id = ? and workspace_id = ?
                            ''', ( groupID, wkscpace)
                        )
                        existingName = cursor.fetchone()
                        if((existingName[0] is not None or gName is not None)
                        and (existingName[0] != gName)
                        ):
                            cursor.execute(
                                '''
                                update UserGroups
                                set [name] = ?
                                where id = ? and workspace_id = ?
                                ''', (gName, groupID, wkscpace )
                            )
                            logger.info(f"Updating User Group {existingName[0]} to {gName}")
                            update += 1
                            pushGroupMembership(conn, cursor, groupID, users, wkscpace)
                            break
                        else:
                            exists += 1
                            logger.info(f"\tLoading ({gName})..........{str(round((exists+update+count)/len(groups),2)*100)[:5]}%")
                        logger.info(pushGroupMembership(conn, cursor, groupID, users, wkscpace))
                        break
                    else:
                        raise
    except Exception as  exc :
        conn.rollback()  # Roll back changes if an exception occurs
        logger.error(f"Error ({exc.__class__}): \n----------{exc.__traceback__.tb_frame.f_code.co_filename}, {exc.__traceback__.tb_frame.f_code.co_name} \n\tLine: {exc.__traceback__.tb_lineno} \n----------{str(exc)}\n")
        return f"Operation failed. Changes rolled back. Contact administer of problem persists"
    else:
        conn.commit()
        logger.info("Committing changes...")  # Commit changes if no exceptions occurred                 
        return(f"Operation Completed: User Groups table has {count} new records and {exists} unchanged. {update} records updated.\n")

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
    conn.commit()
    logger.info("Committing changes...")
    logger.info(f"Updated Calander Dates for Year {date[:4]}")

def pushHolidays(wkSpaceID, conn, cursor):
    count = 0
    update = 0
    exists = 0
    holidays = getHolidays(wkSpaceID)
    try:
        for day in holidays:
            holID = day['id']
            date = day.get("datePeriod").get('startDate')
            name = day['name']
            # add user groups
            while True:
                try:
                    cursor.execute(
                        '''
                        INSERT INTO Holidays (holidayID, name, date, workspace_id)
                        values (?, ?, ?, ?)
                        ''', (holID, name, date, wkSpaceID )
                    )
                    logger.info(f"\tAdding Holiday Information...{count}")
                    update += 1
                    break
                except pyodbc.IntegrityError as e:
                    if "PRIMARY KEY constraint" in str(e):
                        # this is where we will check to update if new users or groups are added 
                        try:
                            cursor.execute(
                                '''
                            select [date], [name] from Holidays
                            where holidayID = ? and workspace_id = ?
                            ''', (holID, wkSpaceID)
                            )
                            oldDays = cursor.fetchone()

                            if (
                                (str(oldDays[0]) != date)
                                    or 
                                (
                                    (oldDays[1] is not None or name is not None) 
                                        and 
                                    (oldDays[1] != name)
                                )
                            ):
                                cursor.execute(
                                    '''
                                    update Holidays
                                    set 
                                        [date] = ?,
                                        [name] = ?
                                    where 
                                        holidayID = ? and workspace_id =?
                                    ''', (date, name, holID, wkSpaceID)
                                )
                                logger.info(f"\tUpdating Holiday: {name}.")
                                update += 1
                            else: 
                                exists += 1
                                logger.info(f"Loading {name}..........{str(round((exists+update+count)/len(holidays),2)*100)[:5]}%")
                            break
                        except pyodbc.IntegrityError:
                            updateCalendar(date, conn, cursor)
                    elif"FOREIGN KEY constraint" in str(e):   
                        updateCalendar(date, conn, cursor)
                    else:
                        raise
    except Exception as exc :
        conn.rollback()  # Roll back changes if an exception occurs
        logger.error(f"Error ({exc.__class__}): \n----------{exc.__traceback__.tb_frame.f_code.co_filename}, {exc.__traceback__.tb_frame.f_code.co_name} \n\tLine: {exc.__traceback__.tb_lineno} \n----------{str(exc)}\n")
        return f"Operation failed. Changes rolled back. Contact administer of problem persists"
    else:
        conn.commit()
        logger.info("Committing changes...")  # Commit changes if no exceptions occurred                 
        return ( f"Operation Complete: Holidays table has {count} new records and {exists} unchanged. {update} records updated.\n")


def deleteTimeOff(wkSpaceID, conn , cursor , timeOff):
    deleted = 0
    """
    Deletes entries for a given time sheet. Delete condition is "If still in database but not pullable from clockify"

    Args:
        conn: Connection object for the database.
        cursor: Cursor object for executing SQL queries.
        aID (str): Time sheet ID.
        entries (list): List of entries to delete.

    Returns:
        int: Number of entries deleted.
    """
    try: 
        cursor.execute(
            '''
            SELECT id From TimeOffRequests
            '''
        )
        
        oldTimeOff = cursor.fetchall()
        for delete in oldTimeOff:
            if delete[0] not in timeOff:
                cursor.execute(
                    '''
                    DELETE FROM TimeOffRequests
                    WHERE id = ?  and workspace_id = ? 
                    ''', (delete[0], wkSpaceID )
                )
                logger.info(f"\t\t\tDeleted...{deleted}")
                deleted += 1
    except Exception as  exc :
        conn.rollback()  # Roll back changes if an exception occurs
        logger.error(f"Error ({exc.__class__}): \n----------{exc.__traceback__.tb_frame.f_code.co_filename}, {exc.__traceback__.tb_frame.f_code.co_name} \n\tLine: {exc.__traceback__.tb_lineno} \n----------{str(exc)}\n")
        logger.error("Operation failed. Changes rolled back. Contact administer of problem persists")
        raise
    else:
        # Commit changes in timesheet function if no exceptions occurred  
        conn.commit() # saving deletions              
        return(deleted)

def pushTimeOff(wkSpaceID, conn, cursor, startRange= "None", endRange ="None", window= -1):
    """
    Pushes time off requests retrieved from Clockify API to the database.

    Args:
        wkSpaceID (str): The ID of the Clockify workspace.
        conn: Connection object for the database.
        cursor: Cursor object for executing SQL queries.
        startFilter (str): Start date filter for time off requests. Defaults to "None".
        endFilter (str): End date filter for time off requests. Defaults to "None".
        window (int): Size of the window for paginated retrieval. Defaults to -1.

    Returns:
        str: Message indicating the operation status.

    Calls:
        - pushHolidays(wkSpaceID, conn, cursor): Pushes holidays to the database.
        - count_working_days(start_date, end_date, conn, cursor): Counts the number of working days between two dates.
        - pushPolicies(wkSpaceID, conn, cursor): Pushes policies to the database.
        - pushUsers(wkSpaceID, conn, cursor): Pushes users to the database.
    """
    logger.info(pushHolidays(wkSpaceID, conn, cursor))
    page = 1
    gCount = 0
    gUpdate = 0
    gExists = 0
    count = 0
    update = 0
    exists = 0
    newRequests = [] # for deletions (ID's)
    timeOff = getTimeOff(wkSpaceID, page, startRange, endRange)
    try:
        while len(timeOff['requests']) != 0 and page <= 3:
            
            logger.info(f"Inserting From Page: {page} of Time Off Requests ({len(timeOff['requests'])} records)")
            for requests in timeOff["requests"]:
                userID = requests["userId"]
                policyID = requests["policyId"]
                requestID = requests["id"] ; newRequests.append(requestID)
                status = requests['status']['statusType']
                
                startDate = requests["timeOffPeriod"]["period"]["start"]
                startFromatString = '%Y-%m-%dT%H:%M:%SZ' if len(startDate) == 20 else '%Y-%m-%dT%H:%M:%S.%fZ'
                endDate = requests["timeOffPeriod"]["period"]["end"]
                endFromatString = '%Y-%m-%dT%H:%M:%SZ' if len(endDate) == 20 else '%Y-%m-%dT%H:%M:%S.%fZ'
                startDate = timeZoneConvert(startDate , startFromatString)
                endDate = timeZoneConvert(endDate, endFromatString)
                duration = count_working_days(startDate.date(), endDate.date() , conn, cursor)
                
                paidTimeOff = requests["balanceDiff"]
                balance = requests['balance']
                while True:
                    try:
                        cursor.execute( # Check to see if it exists in db already 
                            '''
                            Select pid, startDate, end_date, duration, [status], paidTimeOff, balanceAfterRequest
                            FROM TimeOffRequests
                            WHERE id = ? AND workspace_id = ?
                            ''', (requestID, wkSpaceID)
                        )
                        oldRequest = cursor.fetchone()
                        if oldRequest is None: # insert into db and break while loop
                            cursor.execute(
                                '''
                                INSERT INTO TimeOffRequests (id, eID, pID, startDate, end_date, duration, [status], paidTimeOff, balanceAfterRequest, workspace_id)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ''', (requestID, userID, policyID, startDate, endDate, duration, status, paidTimeOff, balance, wkSpaceID)
                            )
                            logger.info(f"\tAdding Time Off Request Information...({count})")
                            count += 1
                            break
                        elif oldRequest is not None and status != oldRequest[4]: # updates by raising error
                            raise pyodbc.IntegrityError("PRIMARY KEY constraint") #the sub funciton in pushApprovals seems to be faster 
                        else: # exists already
                            exists += 1
                            logger.info(f"\tLoading..........{str(round((exists+update+count)/len(timeOff['requests']),2)*100)[:5]}%")
                            break
                    except pyodbc.IntegrityError as e:
                        if "FOREIGN KEY constraint" in str(e):
                            logger.info(pushPolicies(wkSpaceID, conn, cursor) + ". Called From Time Off Function")
                            logger.info(pushUsers(wkSpaceID, conn, cursor) + ". Called From Time Off Function")
                        elif "PRIMARY KEY constraint" in str(e):
                            try: # check for update in db and compute if needed 
                                startDateObject = copy.copy(startDate)
                                endDateObject = copy.copy(endDate)
                                # round datetime to nearest minute
                                startDateObject += timedelta(seconds=30)
                                endDateObject += timedelta(seconds=30)
                                startDateObject = startDateObject.replace(second = 0, microsecond = 0)
                                endDateObject = endDateObject.replace(second = 0, microsecond = 0) 
                                if ( # check for an update 
                                    (oldRequest[0] != policyID ) or (startDateObject != oldRequest[1])
                                    or (oldRequest[2] != endDateObject) or ( int(duration) != int(oldRequest[3]) )
                                    or (status != oldRequest[4]) 
                                    or (round(float(paidTimeOff), 2) != round(float(oldRequest[5]), 2))
                                    or (round(float(balance),2) != round(float(oldRequest[6]),2))
                                ):
                                    cursor.execute( #updates 
                                        '''
                                        UPDATE TimeOffRequests 
                                        SET 
                                            pid = ?,
                                            startDate = ?,
                                            end_date = ?,
                                            duration = ?,
                                            status = ?,
                                            paidTimeOff = ?,
                                            balanceAfterRequest = ?
                                        WHERE 
                                            id = ? AND workspace_id = ?
                                        ''', (policyID, startDate, endDate, duration, status, paidTimeOff, balance, requestID, wkSpaceID )
                                    )
                                    logger.info(f"\tUpdating TimeOffRequests {oldRequest[4]} to {status}:...({requestID})")
                                    update += 1
                                    break
                                else: # no updates were made - should never run 
                                    exists += 1
                                    logger.info(f"\tLoading..........{str(round((exists+update+count)/len(timeOff['requests']),2)*100)[:5]}%")
                                    break
                            except pyodbc.IntegrityError as ex:
                                if "FOREIGN KEY constraint" in str(ex):
                                    logger.info(pushUsers(wkSpaceID, conn, cursor), "Called by TimeOff FK_ERROR")
                                    logger.info(pushPolicies(wkSpaceID, conn, cursor),  "Called by TimeOff FK_ERROR")
                                else: # unknown error 
                                    raise
                        else: # unknown error 
                            raise # Unkown integrity error on insert 
            page += 1
            gCount += count 
            gUpdate += update
            gExists += exists 
            count = 0 
            update = 0
            exists = 0
            timeOff = getTimeOff(wkSpaceID, page, startRange, endRange) 
    except Exception as exc :
        conn.rollback()  # Roll back changes if an exception occurs
        logger.error(f"Error ({exc.__class__}): \n----------{exc.__traceback__.tb_frame.f_code.co_filename}, {exc.__traceback__.tb_frame.f_code.co_name} \n\tLine: {exc.__traceback__.tb_lineno} \n----------{str(exc)}\n")
        return f"Operation failed. Changes rolled back. Contact administer of problem persists"
    else:
        conn.commit() # saving inserts 
        deleted = 0
        # deleteTimeOff(wkSpaceID, conn, cursor, newRequests)
        logger.info("Committing changes...")  # Commit changes if no exceptions occurred
                           
        return(f"Operation Completed: TimeOffRequest table has {gCount} new records and {gExists} unchanged. {gUpdate} records updated. {deleted} deleted\n")
''' 
def pushAttendance(wkSpaceID, conn, cursor, startDate="2024-02-11T00:00:00Z", endDate="2024-02-17T23:59:59.999Z", page =1):
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
    attendance = ClockifyPull.getAttendance(wkSpaceID, startDate, endDate, page)
    exists = 0
    update = 0
    count = 0
    
    length = 0
    while len(attendance['entities']) != 0 and page < 10:
        length += len(attendance['entities'])
        logger.info(f"Inserting Page: {page}. ({len(attendance['entities'])} entries)")
        page += 1
        for atten in attendance["entities"]: 
            uID = atten["userId"]
            date = atten["date"]
            overtime = (atten["overtime"])/3600
            timeOff = (atten["timeOff"])/3600
            totalDuration = (atten["totalDuration"])/3600
            while True:
                try: 
                    cursor.execute(
                        \'''
                        INSERT INTO Attendance ( id, [date], overtime, timeOff, totalDuration)
                        VALUES ( ?, ?, ?, ?, ?)
                        \''', (uID, date, overtime, timeOff, totalDuration)
                    )
                    logger.info(f"Adding Attendance information...({count})")
                    conn.commit()
logger.info("Committing changes...")
                    count += 1
                    break
                except pyodbc.IntegrityError as e:
                    if "FOREIGN KEY constraint" in str(e):
                        logger.info(pushUsers(wkSpaceID, conn, cursor) + ". Called from Attendance Function (insert)")
                    elif "PRIMARY KEY constraint" in str(e):
                        try:
                            cursor.execute(
                                \'''
                                SELECT overtime, timeOff, totalDuration FROM Attendance
                                WHERE id = ? and [date] = ?
                                \''', (uID, date)
                            )
                            oldAtt = cursor.fetchone()
                            
                            if (round(float(oldAtt[0]), 2) != round(float(overtime),2) 
                                or round(float(oldAtt[1]), 2) != round(float(timeOff),2) 
                                or round(float(oldAtt[2]),2) != round(float(totalDuration),2)):
                                cursor.execute(
                                    \'''
                                    UPDATE Attendance
                                    SET
                                        overtime = ?,
                                        timeOff = ?,
                                        totalDuration = ?
                                    WHERE 
                                        id = ? and [date] = ?
                                    \''', (overtime, timeOff, totalDuration, uID, date)
                                )
                                conn.commit()
logger.info("Committing changes...")
                                update += 1
                                break
                            else:
                                exists += 1
                                logger.info(f"Loading..........{str(round((exists+update+count)/length,2)*100)[:5]}%")
                                break
                        except pyodbc.OperationalError :
                            raise
                        except pyodbc.ProgrammingError :
                            raise
                        except pyodbc.DatabaseError :
                            raise
                        except Exception :
                            logger.info("Unexpected Error:", str(ex))
                             
                            break                           
                    else: 
                        logger.info(f"Error inserting {uID} into Attendance: {e}")
                        
                        break
                except pyodbc.OperationalError as e:
                    raise
                except pyodbc.ProgrammingError as e:
                    raise
                except pyodbc.DatabaseError as e:
                    raise
                except Exception as e:
                    raise                  
        attendance = ClockifyPull.getAttendance(wkSpaceID, startDate, endDate, page)               
    return(f"Operation Completed: Attendance table has {count} new records and {exists} unchanged. {update} records updated. ({errors} errors)")
'''

