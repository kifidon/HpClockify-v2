from . import ClockifyPull
from . import ClockifyPush
import pyodbc
import csv
import os
import datetime
import pandas as pd

from types import MappingProxyType

# Define your dictionary
original_dict = {
    'Jax Chen': 200, 
    'Saqleen Desai': 200
    }

# Create an immutable view of the dictionary
lubiconDayRates = MappingProxyType(original_dict)

def getMonthYear():
    # Get the current date
    current_date = datetime.datetime.now()
    
    # Extract the month and year
    month = str(current_date.month)
    year = str(current_date.year)[2:]
    
    return month.rjust(2, '0'), year

def getAbbreviation(month = None, year = None ):
    months = {
        '01': 'Jan',
        '02': 'Feb',
        '03': 'Mar',
        '04': 'Apr',
        '05': 'May',
        '06': 'Jun',
        '07': 'Jul',
        '08': 'Aug',
        '09': 'Sep',
        '10': 'Oct',
        '11': 'Nov',
        '12': 'Dec'
    }
    if month is None:
        month, year = getMonthYear()
    return f"{ months.get(month, 'Invalid Month')} 20{year}"

def MonthylyProjReport(startDate = None, endDate = None):
    if startDate is None or endDate is None:
        month, year = getMonthYear()
        if int(month) -1 == 0: 
            previousMonth = '12'
            year = str(int(year) - 1).rjust(2, '0')
        else: previousMonth = str(int(month) -1 ).rjust(2, '0')
        startDate = f"20{year}-{previousMonth}-25"
        endDate = f"20{year}-{month}-24"
    else: 
        month = endDate[5:7]
        year = endDate[2:4]
    cursor, conn = ClockifyPull.sqlConnect()
    try:
        cursor.execute(
            f'''
            Select 
                DISTINCT en.project_id, p.code
            FROM TimeSheet TS
            INNER JOIN Entry en ON en.time_sheet_id = ts.id
            INNER JOIN Project p on p.id = en.project_id
            WHERE ts.start_time BETWEEN '{startDate}' AND '{endDate}'
                AND ts.[status] = 'APPROVED'
            '''
        )
        pIds = cursor.fetchall()
        for pId in pIds:
            current_dir = r"C:\Users\TimmyIfidon\OneDrive - Hill Plain Construction Services LP\Billable Report (ACC) - Hill Plain Hub"
           # current_dir = r"C:\Users\TimmyIfidon\Desktop"
            folder_name = f"HP-IND-{year}-{month}"
            folder_path = os.path.join(current_dir, folder_name)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
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
        ClockifyPull.cleanUp(conn, cursor)   
        return f"File stored at: {file_path}"     
    except pyodbc.Error as e:
        print( f"SQL Error: {str(e)}")
    except FileNotFoundError as e:
        print(f"Error: {str(e)}")
    except PermissionError as e:
        print(f"Error: {str(e)}")

def WeeklyTimeSheet(startDate = "2024-02-11" , endDate = "2024-02-17"):
    cursor, conn = ClockifyPull.sqlConnect()
    retried = True
    try:
        while True: 
            cursor.execute(
                '''
                SELECT * FROM AttendanceApproved
                WHERE [Date] BETWEEN ? AND ?
                ORDER BY [date] , [name]
                ''', ( startDate, endDate)
            )
            rows = cursor.fetchall()
            if len(rows) == 0 and retried:
                wid = ClockifyPush.getWID('Hill Plain')
                ClockifyPush.pushApprovedTime(wid, conn, cursor)
                ClockifyPush.pushTimeOff
                retried = False
            else:
                break
        with open(f'timeSheet_{startDate}-{endDate}.csv', 'w', newline = '') as file:
            writer = csv.writer(file)
            writer.writerow(
                ['Name', 'Date', 'Regular Hours', 'Overtime', 'Total', 'Paid Time Off', 'Reason']
                )
            if(len(rows) != 0):
                for i in range(len(rows) - 1): 
                    writer.writerow(rows[i])
                    if rows[i+1][1] != rows[i][1]:
                        writer.writerow([]) 
                writer.writerow(rows[(len(rows))])
            else:
                writer.writerow([]) 
                writer.writerow([f"No data was found for period {startDate} - {endDate}"])

    except pyodbc.Error as e:
        print( f"SQL Error: {str(e)}")
    except FileNotFoundError as e:
        print(f"Error: {str(e)}")
    except PermissionError as e:
        print(f"Error: {str(e)}")


def main():
    
    MonthylyProjReport('2024-02-25', '2024-03-24')
    # WeeklyTimeSheet()
   

if __name__ == "__main__": 
    main()