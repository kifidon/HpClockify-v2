from .hpUtil import sqlConnect, cleanUp, get_current_time, getMonthYear, getAbbreviation, getCurrentPaycycle
from .ClockifyPushV3 import getWID, pushApprovedTime, pushTimeOff 
import pyodbc
import os
import pandas as pd
from .. import settings 
import logging


def MonthylyProjReport(startDate = None, endDate = None):
    if startDate is None or endDate is None:
        month, year = getMonthYear()
        if int(month) -1 == 0: 
            previousMonth = '12'
            year = str(int(year) - 1).rjust(2, '0')
        else: previousMonth = str(int(month) -1 ).rjust(2, '0')
        startDate = f"20{year}-{previousMonth}-25"
        endDate = f"20{year}-{month}-25"
    else: 
        month = endDate[5:7]
        year = endDate[2:4]
    cursor, conn = sqlConnect()
    try:
        cursor.execute(
            f'''
            Select 
                 p.id, p.code
            from Project p
            where exists (
                select 1 From Entry en 
                inner join TimeSheet ts on ts.id = en.time_sheet_id
                where ts.status = 'APPROVED'
            )
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
                    mb.start_time BETWEEN ? AND ? AND
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

def MonthylyProjReportEqp(startDate = None, endDate = None):
    if startDate is None or endDate is None:
        month, year = getMonthYear()
        if int(month) -1 == 0: 
            previousMonth = '12'
            year = str(int(year) - 1).rjust(2, '0')
        else: previousMonth = str(int(month) -1 ).rjust(2, '0')
        startDate = f"20{year}-{previousMonth}-25"
        endDate = f"20{year}-{month}-25"
    else: 
        month = endDate[5:7]
        year = endDate[2:4]
    cursor, conn = sqlConnect()
    try:
        cursor.execute(
            f'''
            Select 
                 p.id, p.code
            from Project p
            where exists (
                select 1 From Entry en 
                inner join TimeSheet ts on ts.id = en.time_sheet_id
                inner join EmployeeUser eu on eu.id = ts.emp_id
                where ts.status = 'APPROVED' and eu.hasTruck = 1
            )
            '''
        )
        pIds = cursor.fetchall()
        for pId in pIds:
            current_dir = settings.BASE_DIR
           # current_dir = r"C:\Users\TimmyIfidon\Desktop"
            folder_name = f"HP-IND-EQP-{year}-{month}"
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
                FROM MonthlyBillableEqp mb
                WHERE 
                    mb.start_time BETWEEN ? AND ? AND
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


def WeeklyTimeSheet(startDate = "2024-02-11" , endDate = "2024-02-17"):
    if startDate is None or endDate is None:
        start, end = getCurrentPaycycle()
        startDate = start
        endDate = end
    print (endDate)
    current_dir = settings.BASE_DIR
    folder_name = f"PayrollLog-{startDate}-{endDate}"
    folder_path = os.path.join(current_dir, folder_name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path )
    file_path = os.path.join(folder_path, f"{folder_name}-Data.xlsx")
    df = []
    cursor, conn = sqlConnect()
    
    try:
        cursor.execute(
            '''
            SELECT name, date, RegularHrs, Overtime, TotalHours , TimeOff, policy_name, Holiday  FROM AttendanceApproved
            WHERE [Date] BETWEEN ? AND ?
            ORDER BY [date] , [name]
            ''', ( startDate, endDate)
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


def main():
    
    MonthylyProjReport('2024-02-25', '2024-03-24')
   

if __name__ == "__main__": 
    main()