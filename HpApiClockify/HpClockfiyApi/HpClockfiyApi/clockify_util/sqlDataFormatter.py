from .hpUtil import sqlConnect, cleanUp, get_current_time, getMonthYear, getAbbreviation, getCurrentPaycycle, reverseForOutput
from .ClockifyPushV3 import getWID, pushApprovedTime, pushTimeOff
from .ClockifyPullV3 import getDetailedEntryReport
import pyodbc
import os
import pandas as pd
from json import loads, dumps
from datetime import datetime, timedelta
from .. import settings 
import logging
from ..Loggers import setup_background_logger

def MonthylyProjReport(month = None, year = None):
    if month is None or year is None:
        month, year = getMonthYear()
    else:
        month = getAbbreviation(month, reverse=True)

    if int(month) -1 == 0: 
        previousMonth = '12'
        previousYear = str(int(year) - 1).rjust(2, '0')
    else: 
        previousMonth = str(int(month) -1 ).rjust(2, '0')
        previousYear = year
    startDate = f"20{previousYear}-{previousMonth}-25"
    endDate = f"20{year}-{month}-25" # non inclusive 
    
    cursor, conn = sqlConnect()
    try:
        cursor.execute(
            f'''
            select Distinct p.id,  p.code  from Project p 
            inner join Entry en on en.project_id = p.id
            inner join TimeSheet ts on ts.id = en.time_sheet_id
            where ts.status = 'APPROVED' 
            and en.start_time between '{startDate}' and '{endDate}'
            '''
        )
        pIds = cursor.fetchall()
        for pId in pIds:
            current_dir = settings.BASE_DIR
           # current_dir = r"C:\Users\TimmyIfidon\Desktop"
            folder_name = f"HP-IND-{year}-{month}"
            folder_path = os.path.join(current_dir, folder_name)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path )
            file_path = os.path.join(folder_path, f"{folder_name}-{pId[1]}.xlsx")
            df = []
            cursor.execute(
                '''
                DECLARE @ProjID VARCHAR(100)= ?;
                SELECT 
                    [Number],
                    case 
                        when mb.Number is null then 
                            FORMAT(ROW_NUMBER() OVER ( PARTITION BY mb.project_id ORDER BY mb.project_id)-1, '0000') 
                        else Null
                    end as [Row],
                    [Name],
                    [Supplier],
                    SUM([QTY]),
                    [Unit],
                    [Unit Cost],
                    Sum(Amount) as Amount
                FROM MonthlyBillable mb
                WHERE 
                    Cast(mb.start_time as Date ) >= ? AND
                    Cast(mb.start_time as Date ) < ? AND
                    mb.project_id = @ProjID 
                GROUP BY 
                    [Number],
                    mb.project_id,
                    [Name],
                    [Supplier],
                    [Unit],
                    [Unit Cost]
                ORDER BY [Number] DESC;
                ''', (pId[0], startDate, endDate)
            )
            outputRows = cursor.fetchall()
            outputRows = [['' if val is None else val for val in row] for row in outputRows]
            df = pd.DataFrame(outputRows, columns = ['Number', 'Row', 'Name', 'Supplier', 'Qty', 'Unit', 'Unit Cost', 'Amount'] )
            if not (df.empty):
                df.iloc[0,0] = f"HP-IND-{year}-{month}-{df.iloc[0,0]}" 
                df.iloc[0, 2] =f"{getAbbreviation(month, year)} Indirect: {df.iloc[0,2]}" 

                df.to_excel(file_path, index = False)
            # Combine the directory path with the file name
        cleanUp(conn, cursor) 
        if len(pIds) != 0:
            return folder_path
        else: 
            return None     
    except pyodbc.Error as e:
        logging.error( f"SQL Error: {str(e)}")
        return None
    except FileNotFoundError as e:
        logging.error(f"Error: {str(e)}")
        return None
    except PermissionError as e:
        logging.error(f"Error: {str(e)}")
        return None

def MonthylyProjReportEqp(month = None, year = None):
    logger = setup_background_logger()
    try:
        if month is None or year is None:
            month, year = getMonthYear()
        else:
            month = getAbbreviation(month, reverse=True)

        if int(month) -1 == 0: 
            previousMonth = '12'
            previousYear = str(int(year) - 1).rjust(2, '0')
        else: 
            previousMonth = str(int(month) -1 ).rjust(2, '0')
            previousYear = year
        startDate = f"20{previousYear}-{previousMonth}-25"
        endDate = f"20{year}-{month}-25" # non inclusive 
        
        cursor, conn = sqlConnect()
    
        cursor.execute(
            f'''
            select Distinct p.id, p.code  from Project p 
            inner join Entry en on en.project_id = p.id
            inner join TimeSheet ts on ts.id = en.time_sheet_id
            inner join EmployeeUser eu on eu.id = ts.emp_id
            where eu.hasTruck = 1 and ts.status = 'APPROVED' and en.start_time between '{startDate}' and '{endDate}'
            '''
        )
        pIds = cursor.fetchall()
        if pIds is None:
            return None
        for pId in pIds:
            current_dir = settings.BASE_DIR
           # current_dir = r"C:\Users\TimmyIfidon\Desktop"
            folder_name = f"HP-IND-EQP-{year}-{month}"
            folder_path = os.path.join(current_dir, folder_name)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path )
            file_path = os.path.join(folder_path, f"{folder_name}-{pId[1]}.xlsx")
            df = []
            logger.info(f"{startDate}  {endDate}")
            cursor.execute(
                '''
                DECLARE @ProjID VARCHAR(100)= ?;
                SELECT 
                    [Number],
                    case 
                        when mb.Number is null then 
                            FORMAT(ROW_NUMBER() OVER ( PARTITION BY mb.project_id ORDER BY mb.project_id)-1, '0000') 
                        else Null
                    end as [Row],
                    [Name],
                    [Supplier],
                    SUM([QTY]),
                    [Unit],
                    [Unit Cost],
                    Sum(Amount) as Amount
                FROM MonthlyBillableEqp mb
                WHERE 
                    Cast(mb.start_time as Date ) >= ? AND
                    Cast(mb.start_time as Date ) < ? AND
                    mb.project_id = @ProjID 
                GROUP BY 
                    [Number],
                    mb.project_id,
                    [Name],
                    [Supplier],
                    [Unit],
                    [Unit Cost]
                ORDER BY [Number] DESC;
                ''', (pId[0], startDate, endDate)
            )
            outputRows = cursor.fetchall()
            logger.info(outputRows)
            outputRows = [['' if val is None else val for val in row] for row in outputRows]
            df = pd.DataFrame(outputRows, columns = ['Number', 'Row', 'Name', 'Supplier', 'Qty', 'Unit', 'Unit Cost', 'Amount'] )
            
            if not (df.empty):
                df.iloc[0,0] = f"HP-IND-EQP-{year}-{month}-{df.iloc[0,0]}"
                df.iloc[0, 2] =f"{getAbbreviation(month, year)} Indirect: {df.iloc[0,2]}" 

                df.to_excel(file_path, index = False)
            # Combine the directory path with the file name
        cleanUp(conn, cursor) 
        if len(pIds) != 0:
            return folder_path
        else: 
            return None     
    except pyodbc.Error as e:
        logging.error( f"SQL Error: {str(e)}")
        return None
    except FileNotFoundError as e:
        logging.error(f"Error: {str(e)}")
        return None
    except PermissionError as e:
        logging.error(f"Error: {str(e)}")
        return None
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return None

def WeeklyTimeSheet(startDate = "2024-02-11" , endDate = "2024-02-17"):
    if startDate is None or endDate is None:
        start, end = getCurrentPaycycle()
        startDate = start
        endDate = end
    current_dir = settings.BASE_DIR
    folder_name = f"PayrollLog-{startDate}-{endDate}"
    folder_path = os.path.join(current_dir, folder_name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path )
    file_path = os.path.join(folder_path, f"{folder_name}-Data.xlsx")
    
    cursor, conn = sqlConnect()
    
    try:
        cursor.execute(
            '''
            SELECT att.name, att.Date, att.RegularHrs, att.Overtime, att.TotalHours , att.TimeOff, att.policy_name, att.Holiday  FROM AttendanceApproved att
            WHERE att.Date BETWEEN ? AND ?

            Union ALL

            Select tt.name,Null, Sum(tt.RegularHrs), Sum(tt.Overtime), Sum(tt.TotalHours), Sum(tt.TimeOff), 'Policy_name', 'Holiday' From AttendanceApproved tt
            WHERE [Date] BETWEEN ? AND ?
            Group By tt.name

            ORDER BY [name], Date DESC
            ''', ( startDate, endDate, startDate, endDate)
        )
        rows = cursor.fetchall()

        rows = [['' if val is None else val for val in row] for row in rows]
        df = pd.DataFrame(rows, columns = ['Name', 'Date', 'Regular Hours', 'Overtime', 'Total', 'Paid Time Off', 'Reason', 'Holiday'])
        if not (df.empty):
            df.to_excel(file_path, index = False)
        # Combine the directory path with the file name
        cleanUp(conn, cursor) 
        
        return folder_path 
    except pyodbc.Error as e:
        logging.error( f"{get_current_time()} - ERROR: SQL Error: {str(e)} at line {e.__traceback__.tb_lineno} in sqlDataFormatter.py")
    except FileNotFoundError as e:
        logging.error(f"{get_current_time()} - ERROR: Error: {str(e)} at line {e.__traceback__.tb_lineno} in sqlDataFormatter.py")
    except PermissionError as e:
        logging.error(f"{get_current_time()} - ERROR: Error: {str(e)} at line {e.__traceback__.tb_lineno} in sqlDataFormatter.py")

def DailyTimeEntryReport():
    try:
        logger = setup_background_logger()
        logger.info("Generating daily time entry report...")
        today = datetime.now().strftime("%Y-%m-%d")
        current_dir = settings.BASE_DIR
        folder_name = f"TimeEntryReport-{today}"
        folder_path = os.path.join(current_dir, folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        file_path = os.path.join(folder_path, f"HillPlainClockifyTime.xlsx")
        data=  getDetailedEntryReport("65c249bfedeea53ae19d7dad") #HP clockify workspace id
        logger.debug(dumps(data, indent=4))
        df = pd.DataFrame(columns=["Employee", "Start", "End","Duration", "Rate", "Amount", "Project", "Client", "Description"])
        for entry in data['timeentries']:
            summary = {
                "Employee": entry['userName'],
                "Start": 
                    datetime.strftime( #format date time 
                        datetime.strptime(entry['timeInterval']['start'], "%Y-%m-%dT%H:%M:%S-06:00"),
                        "%H:%M:%S - %Y/%m/%d"    
                    ),
                "End":
                    datetime.strftime( #format date time 
                        datetime.strptime(entry['timeInterval']['end'],"%Y-%m-%dT%H:%M:%S-06:00"),
                        "%H:%M:%S - %Y/%m/%d"    
                    ),
                "Duration": round(float(entry['timeInterval']['duration'])/3600, 2),
                "Rate": round(float(entry["rate"])/100, 2),
                "Amount": round(float(entry["amount"])/100, 2),
                "Project": entry["projectName"],
                "Client": entry["clientName"],
                "Description": entry["description"]
            }
            df.loc[len(df)] = summary
        
        logger.debug(df)
        if not (df.empty):
            df.to_excel(file_path, index = False)

        return folder_path
    except Exception as e:
        logger.error(f"({e.__traceback__.tb_lineno}) - {str(e)}") 
        pass
        
def ReportGenerate(month = None, year = None):
    logger = setup_background_logger()
    try: 
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
#
        endDate = datetime.strptime(f'20{year}-{month}-25', '%Y-%m-%d')
        startDate = datetime.strptime(f'20{previousYear}-{previousMonth}-25', '%Y-%m-%d')
        # Calculate the most recent previous Saturday
        endDate = (endDate - timedelta(days=(endDate.weekday() + 2) % 7)).strftime('%Y-%m-%d')
        startDate = (startDate - timedelta(days=(startDate.weekday()+ 1) %7)).strftime('%Y-%m-%d')
        logger.debug(f'Date Range: {startDate}-{endDate}')
        cursor, conn = sqlConnect()
        cursor.execute(
            f'''
            select p.id, p.code, p.title from Project p 
            where exists(
                select en.id from Entry en 
                where en.billable = 1 and 
                en.project_id = p.id 
                and Cast(en.start_time As Date) between '{startDate}' and '{endDate}'
            )
            '''
        )

        pIds = cursor.fetchall()
        logger.debug(f'{len(pIds)} Projects')
        current_dir = settings.BASE_DIR
        # current_dir = r"C:\Users\TimmyIfidon\Desktop"
        folder_name = f"HP-IND-{year}-{month}"
        folder_path = os.path.join(current_dir, folder_name)
        logger.debug(f'Created Folder at {folder_path}')
        for pId in pIds:
            if not os.path.exists(folder_path):
                os.makedirs(folder_path )
            file_path = os.path.join(folder_path, f"{folder_name}-{pId[1]}.xlsx")
            
            logger.debug('Getting Labor Data')
            cursor.execute(
                f'''
                Select 
                    eu.name, 
                    eu.role, 
                    SUM(en.duration), 
                    'hr' as [Unit Cost] ,
                    Cast(en.rate/100 as Decimal(10,2)),
                    cast(
                        sum(en.duration * en.rate/100) as decimal(10,2)
                    )
                From Entry en
                inner join Timesheet ts on ts.id = en.time_sheet_id
                inner join EmployeeUser eu on eu.id = ts.emp_id
                inner join Project p on p.id = en.project_id
                where p.id = '{pId[0]}'
                    and en.billable = 1
                    and ts.[status] = 'APPROVED'
                group by eu.name, eu.role, cast(en.rate/100 as Decimal(10,2))
                order by eu.name 
                '''
            )
            labourData = cursor.fetchall()
            logger.debug('Aquired Labor Data')
            logger.debug('Getting Equipment Data')
            cursor.execute(
                f'''
                Select 
                    eu.name, 
                    eu.role, 
                    SUM(en.duration), 
                    'hr' as [Unit Cost] ,
                    Cast('18.75' as Decimal(10,2)),
                    cast(
                        sum(en.duration * 18.75) as decimal(10,2)
                    )
                From Entry en
                inner join Timesheet ts on ts.id = en.time_sheet_id
                inner join EmployeeUser eu on eu.id = ts.emp_id
                inner join Project p on p.id = en.project_id
                where p.id = '{pId[0]}'
                    and eu.hasTruck = 1 
                    and en.billable = 1
                    and ts.[status] = 'APPROVED'
                group by eu.name, eu.role, cast(en.rate/100 as Decimal(10,2))
                ''')
            equipmentData = cursor.fetchall()
            logger.debug('Aquired Equipment Data')

            labourData = [['' if val is None else val for val in data] for data in labourData]
            equipmentData = [['' if val is None else val for val in data] for data in equipmentData]
            logger.debug(equipmentData)
            # logger.debug(labourData)
            labourDF = pd.DataFrame(labourData, columns=['Staff Member', 'Role', 'QTY', 'Unit Cost', 'Rate', 'Amount'])
            equipDF = pd.DataFrame(equipmentData, columns=['Staff Member', 'Role', 'QTY', 'Unit Cost', 'Rate', 'Amount'])

            with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
                writer.sheets['Sheet1'] = writer.book.add_worksheet("Hill Plain - Monthly LEM")
                worksheet = writer.sheets['Hill Plain - Monthly LEM']
                worksheet.write(1,0, "Hill Plain - Monthly LEM (Indirects)" )
                headers = {
                    "Project Name:": pId[2],
                    "Project Number:": pId[1],
                    "Invoice Month:" : getAbbreviation(month, year),
                    "Time Period Start:": startDate,
                    "Time Period End:": endDate
                }

                logger.info(reverseForOutput(headers))

                row = 2
                for key, value in headers.items():
                    worksheet.write(row, 0, key)
                    worksheet.write(row, 1, None)
                    worksheet.write(row, 2, value)
                    row += 1
                    logger.debug(f'Writing to row {row}')
                row += 1
                worksheet.write(row,3, "LABOUR" )
                labourDF.to_excel(writer, sheet_name="Hill Plain - Monthly LEM", startrow=row, startcol= 1, index=False)
                row += len(labourData)
                row += 1
                worksheet.write(row,3, "EQUIPMENT" )
                equipDF.to_excel(writer, sheet_name="Hill Plain - Monthly LEM", startrow=row, startcol= 1, index=False)
                row += len(equipmentData)
        return folder_path        


                    


    except Exception as e: 
        logger.error(f'{e.__traceback__.tb_lineno} - {str(e)}')
def main():
    ReportGenerate('07','24')
    # MonthylyProjReport('2024-02-25', '2024-03-24')
   

if __name__ == "__main__": 
    main()