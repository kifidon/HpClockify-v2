from .hpUtil import sqlConnect, cleanUp, get_current_time, getMonthYear, getAbbreviation, getCurrentPaycycle, reverseForOutput
from .ClockifyPushV3 import getWID, pushApprovedTime, pushTimeOff
from .ClockifyPullV3 import getDetailedEntryReport
from decimal import Decimal
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

# def WeeklyTimeSheet(startDate = "2024-02-11" , endDate = "2024-02-17"):
    #     if startDate is None or endDate is None:
    #         start, end = getCurrentPaycycle()
    #         startDate = start
    #         endDate = end
    #     current_dir = settings.BASE_DIR
    #     folder_name = f"PayrollLog-{startDate}-{endDate}"
    #     folder_path = os.path.join(current_dir, folder_name)
    #     if not os.path.exists(folder_path):
    #         os.makedirs(folder_path )
    #     file_path = os.path.join(folder_path, f"{folder_name}-Data.xlsx")

    #     cursor, conn = sqlConnect()

    #     try:
    #         cursor.execute(
    #             '''
    #             SELECT att.name, att.Date, att.RegularHrs, att.Overtime, att.TotalHours , att.TimeOff, att.policy_name, att.Holiday  FROM AttendanceApproved att
    #             WHERE att.Date BETWEEN ? AND ?

    #             Union ALL

    #             Select tt.name,Null, Sum(tt.RegularHrs), Sum(tt.Overtime), Sum(tt.TotalHours), Sum(tt.TimeOff), 'Policy_name', 'Holiday' From AttendanceApproved tt
    #             WHERE [Date] BETWEEN ? AND ?
    #             Group By tt.name

    #             ORDER BY [name], Date DESC
    #             ''', ( startDate, endDate, startDate, endDate)
    #         )
    #         rows = cursor.fetchall()

    #         rows = [['' if val is None else val for val in row] for row in rows]
    #         df = pd.DataFrame(rows, columns = ['Name', 'Date', 'Regular Hours', 'Overtime', 'Total', 'Paid Time Off', 'Reason', 'Holiday'])
    #         if not (df.empty):
    #             df.to_excel(file_path, index = False)
    #         # Combine the directory path with the file name
    #         cleanUp(conn, cursor) 

    #         return folder_path 
    #     except pyodbc.Error as e:
    #         logging.error( f"{get_current_time()} - ERROR: SQL Error: {str(e)} at line {e.__traceback__.tb_lineno} in sqlDataFormatter.py")
    #     except FileNotFoundError as e:
    #         logging.error(f"{get_current_time()} - ERROR: Error: {str(e)} at line {e.__traceback__.tb_lineno} in sqlDataFormatter.py")
    #     except PermissionError as e:
    #         logging.error(f"{get_current_time()} - ERROR: Error: {str(e)} at line {e.__traceback__.tb_lineno} in sqlDataFormatter.py")

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
        
def BillableReportGenerate(month = None, year = None):
    logger = setup_background_logger()
    try: 
        #obtain date range for this month 
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
        endDateObj = datetime.strptime(f'20{year}-{month}-25', '%Y-%m-%d')
        startDateObj = datetime.strptime(f'20{previousYear}-{previousMonth}-25', '%Y-%m-%d')
        # Calculate the most recent previous Saturday
        endDate = (endDateObj - timedelta(days=(endDateObj.weekday() + 2) % 7)).strftime('%Y-%m-%d')
        if(endDate[-2:] == "25"):
            endDate = (endDateObj -timedelta(days=7) - timedelta(days=(endDateObj.weekday() + 2) % 7)).strftime('%Y-%m-%d')
        # most recent previous Sunday before the 25th of this month 
        startDate = (startDateObj - timedelta(days=(startDateObj.weekday()+ 1) %7)).strftime('%Y-%m-%d')
        logger.debug(f'Date Range: {startDate}-{endDate}')
        cursor, conn = sqlConnect()
        
    #Get Relavant projects  
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

        # Generate Folder for spreadsheets
        current_dir = settings.BASE_DIR
        folder_name = f"HP-IND-{year}-{month}"
        folder_path = os.path.join(current_dir, folder_name)
        logger.debug(f'Created Folder at {folder_path}')

        for pId in pIds:
            if not os.path.exists(folder_path):
                os.makedirs(folder_path )
            file_path = os.path.join(folder_path, f"{folder_name}-{pId[1]}.xlsx")
        #Get billing Data 
            logger.debug('Getting Labor Data')
            #labour data 
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
                where p.id = '{pId[0]}' and Cast(en.start_time as Date)>= '{startDate}' and Cast(en.start_time as Date)<= '{endDate}'
                    and en.billable = 1
                    and ts.[status] = 'APPROVED'
                group by eu.name, eu.role, cast(en.rate/100 as Decimal(10,2))
                order by eu.name 
                '''
            )
            labourData = cursor.fetchall()
            logger.debug('Aquired Labor Data')
            logger.debug('Getting Equipment Data')
            #Equipment Data 
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
                where p.id = '{pId[0]}' and Cast(en.start_time as Date)>= '{startDate}' and Cast(en.start_time as Date)<= '{endDate}'
                    and eu.hasTruck = 1 
                    and en.billable = 1
                    and ts.[status] = 'APPROVED'
                group by eu.name, eu.role, cast(en.rate/100 as Decimal(10,2))
                ''')
            equipmentData = cursor.fetchall()
            logger.debug('Aquired Equipment Data')
            #labour Totals
            cursor.execute(
                f'''
                Select 
                    Cast(SUM(en.duration * en.rate/100) as Decimal(10,2))
                From Entry en
                inner join Timesheet ts on ts.id = en.time_sheet_id
                inner join EmployeeUser eu on eu.id = ts.emp_id
                inner join Project p on p.id = en.project_id
                where p.id = '{pId[0]}' and Cast(en.start_time as Date)>= '{startDate}' and Cast(en.start_time as Date)<= '{endDate}'
                    and en.billable = 1
                    and ts.[status] = 'APPROVED'
                '''
            )
            labourTotal = cursor.fetchone()
            # equipment totals
            cursor.execute(
                f'''
                Select 
                    Cast(SUM(en.duration * 18.75) as Decimal(10,2))
                From Entry en
                inner join Timesheet ts on ts.id = en.time_sheet_id
                inner join EmployeeUser eu on eu.id = ts.emp_id
                inner join Project p on p.id = en.project_id
                where p.id = '{pId[0]}' and Cast(en.start_time as Date)>= '{startDate}' and Cast(en.start_time as Date)<= '{endDate}'
                    and en.billable = 1
                    and ts.[status] = 'APPROVED'
                    and eu.hasTruck = 1 
                '''
            )
            equipmentTotal = cursor.fetchone()
            
            #format results for opperations 
            labourData = [['' if val is None else val for val in data] for data in labourData]
            equipmentData = [['' if val is None else val for val in data] for data in equipmentData]
            if equipmentTotal[0] is not None:
                grandTotal = labourTotal[0] + equipmentTotal[0]
                equipmentTotal = float(equipmentTotal[0])
            else: 
                grandTotal = labourTotal[0]
            labourTotal = float(labourTotal[0])
            logger.debug(f'Totals: {labourTotal} {type(labourTotal)}')
            grandTotal = float(grandTotal)
            
            with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
                #Generate file and initilize writers and formats 
                workbook = writer.book
                worksheet = workbook.add_worksheet("Hill Plain - Monthly LEM")
                writer.sheets['Hill Plain - Monthly LEM'] = worksheet        

                # Merged cells Title Format
                mergeCells = workbook.add_format({'align': 'center', 'bold': True})
                mergeCells.set_center_across()
                mergeCells.set_bg_color('#FCD5B4') 
                mergeCells.set_font_size(24)
                mergeCells.set_border(2)
                worksheet.merge_range(0,0,1,8, "Hill Plain - Monthly LEM (Indirects)", mergeCells)

                #subTotals Format
                subTotals = workbook.add_format({'align': 'left', 'bold': True}) 
                subTotals.set_bg_color('#FFFF99')              
                subTotals.set_font_size(14)              
                subTotals.set_italic()              
                #GrandTotal Format
                grandTotalFormat = workbook.add_format({'align': 'left', 'bold': True}) 
                grandTotalFormat.set_bg_color('#FCD5B4')              
                grandTotalFormat.set_font_size(14)              
                grandTotalFormat.set_italic()              
                
                #File headers info 
                headers = {
                    "Project Name:": pId[2],
                    "Project Number:": pId[1],
                    "Invoice Month:" : getAbbreviation(month, year),
                    "Time Period Start:": startDate,
                    "Time Period End:": endDate,
                    "Generated On:": datetime.now().strftime("%Y-%m-%d at %H:%m")
                }
                logger.info(reverseForOutput(headers))

                #bold Text format 
                bold_format = workbook.add_format({'bold':True})
                bold_format.set_italic()
                row = 2
                #write file headers
                for key, value in headers.items():
                    worksheet.merge_range(row, 0,row,1, key, bold_format)
                    worksheet.write(row, 2, value)
                    row += 1
                    logger.debug(f'Writing to row {row}')
                row += 1
                
                #insert image 
                worksheet.insert_image("H4",
                                        # r"C:\Users\TimmyIfidon\Desktop\Docs and Projects\Hill Plain Logo New (May2023)\PNG\Hill Plain Logo - NEW (colour).png",
                                        r"C:\Users\Script\Desktop\unnamed.png",
                                       {'x_scale': 0.4, 'y_scale': 0.4})

                #table headers Formater 

                headersFormat = workbook.add_format({'align': 'center', 'bold': True})
                headersFormat.set_center_across()
                headersFormat.set_bg_color('#F2F2F2')
                headersFormat.set_font_size(16)
                headersFormat.set_border(1)
                #dollar value formats 
                numFormat = workbook.add_format({'align': 'center', 'num_format': '$#,##0.00'})
                numFormat.set_border(1)
                #dollar bold value formats 
                boldNum = workbook.add_format({'align': 'center', 'bold': True, 'num_format': '$#,##0.00'})
                boldNum.set_num_format(7)
                boldNum.set_font_size(14)
                boldNum.set_bg_color('#FFFF99')
                #Grand total value formats 
                gt = workbook.add_format({'align': 'center', 'bold': True, 'num_format': '$#,##0.00'})
                gt.set_num_format(7)
                gt.set_font_size(14)
                gt.set_bg_color('#FCD5B4')
                # table data format
                dataFormat = workbook.add_format()
                dataFormat.set_border(1)
                #table column format 
                columnFormat = workbook. add_format({'align': 'center', 'bold': True})
                columnFormat.set_border(1)

            # Table  Data 
                worksheet.merge_range(row,0,row,8, 'LABOUR', headersFormat)
                row += 1
                
                #write column names 
                worksheet.merge_range(row,0,row, 1, 'Staff Member', columnFormat)
                worksheet.merge_range(row,2,row, 3, 'Position', columnFormat)
                worksheet.write( row,4, 'Qty', columnFormat)
                worksheet.write( row,5, 'Unit Cost', columnFormat)
                worksheet.write( row,6, 'Rate', columnFormat)
                worksheet.merge_range( row,7, row, 8, 'Amount', columnFormat)
                row += 1

                for rowData in labourData:
                    worksheet.merge_range(row,0, row, 1, rowData[0], dataFormat)
                    worksheet.merge_range(row,2, row, 3 ,rowData[1], dataFormat)
                    worksheet.write( row,4, rowData[2], dataFormat)
                    worksheet.write( row,5, rowData[3], dataFormat)
                    worksheet.write( row,6, rowData[4], numFormat)
                    worksheet.merge_range( row,7,row, 8, rowData[5], numFormat)
                    row += 1
                logger.info(f'Labour Items - {len(labourData)}')
                #sub Total
                worksheet.merge_range(row,5,row,6,'SUB TOTAL', subTotals)
                worksheet.merge_range(row,7,row,8, labourTotal, boldNum)
                row += 1
            # equipment Table 
                if type(equipmentTotal) is float:
                    row += 1
                    worksheet.merge_range(row,0,row,8, 'EQUIPMENT', headersFormat)
                    row += 1

                    worksheet.merge_range(row,0,row, 1, 'Staff Member', columnFormat)
                    worksheet.merge_range(row,2,row, 3, 'Position', columnFormat)
                    worksheet.write( row,4, 'Qty', columnFormat)
                    worksheet.write( row,5, 'Unit Cost', columnFormat)
                    worksheet.write( row,6, 'Rate', columnFormat)
                    worksheet.merge_range( row,7, row, 8, 'Amount', columnFormat)
                    row += 1

                    for rowData in equipmentData:
                        worksheet.merge_range(row,0, row, 1, rowData[0], dataFormat)
                        worksheet.merge_range(row,2, row, 3 ,rowData[1], dataFormat)
                        worksheet.write( row,4, rowData[2], dataFormat)
                        worksheet.write( row,5, rowData[3], dataFormat)
                        worksheet.write( row,6, rowData[4], numFormat)
                        worksheet.merge_range( row,7,row, 8 , rowData[5], numFormat)
                        row += 1

                    worksheet.merge_range(row,5,row,6,'SUB TOTAL', subTotals)
                    worksheet.merge_range(row,7 ,row,8, equipmentTotal, boldNum)
                    row += 1
                worksheet.merge_range(row,5,row, 6, "GRAND TOTAL", grandTotalFormat)
                worksheet.merge_range(row,7,row,8,grandTotal, gt)
                # df = pd.DataFrame([], columns=["GRAND TOTAL", None, f"{grandTotal}"])
                # df.to_excel(writer, sheet_name="Hill Plain - Monthly LEM", startrow=row, startcol= 4, index=False)
                
                
                writer.close()

        return folder_path        

    except Exception as e: 
        logger.error(f'{e.__traceback__.tb_lineno} - {str(e)}')

def NonBillableReportGen(start = None, end = None):
    logger = setup_background_logger()
    try: 
        #obtain date range for this month 
        if start is None or end is None:
            start = (datetime.now() - timedelta(days = (7 + datetime.now().weekday() + 1))).strftime('%Y-%m-%d') # find sunday start time 
            end =   (datetime.now() - timedelta(days = (2 + datetime.now().weekday()))).strftime('%Y-%m-%d') #find saturday 
        logger.info(f'Biling Report Generating for - {start}-{end}')

        cursor, conn = sqlConnect()

        #obtain relavant data 
        cursor.execute(
            f'''
            Select
                eu.name, 
                eu.manager,
                SUM(case when en.billable = 1 then en.duration else 0 end) as Billable,
                Sum(case when en.billable = 0 then en.duration else 0 end) as NonBillable
            From Entry en 
            Inner join Timesheet ts on ts.id = en.time_sheet_id
            inner join EmployeeUser eu on eu.id = ts.emp_id
            where Cast(en.start_time as Date) between '{start}' and '{end}'
            Group by 
                eu.name, 
                eu.manager
            order by eu.name
            '''
            )
        data = cursor.fetchall()
        data = [['' if val is None else val for val in row] for row in data]
    
         # Generate Folder for spreadsheets
        current_dir = settings.BASE_DIR
        folder_name = f"Weekly Report- Billable vs Non Billable - {start} - {end}"
        folder_path = os.path.join(current_dir, folder_name)
        logger.debug(f'Created Folder at {folder_path}')
        if not os.path.exists(folder_path):
                os.makedirs(folder_path )
        file_path = os.path.join(folder_path, f"{folder_name}.xlsx")

        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
            #Generate file and initilize writers and formats 
            workbook = writer.book
            worksheet = workbook.add_worksheet("Hill Plain - Billing Summary ")
            writer.sheets['Hill Plain - Billing Summary'] = worksheet 
            
            row = 0 #initilize row pointer 

        #formats  
            #title 
            titleFormat = workbook.add_format({'bold': True, 'align': 'center'})
            titleFormat.set_font_size(20)
            titleFormat.set_bg_color('#D9D9D9')
            #file Heaaders
            headerFormat = workbook.add_format({'bold': True, "italic": True})
            #Billable Vs Non Billable 
            billableFormat = workbook.add_format()
            billableFormat.set_bg_color("#c1f0c8")
            nBillableFormat = workbook.add_format()
            nBillableFormat.set_bg_color("#f7c7ac")
            #columnNameFormat 
            columnNameFormat = workbook.add_format({'bold': True})
            columnNameFormat.set_border(1)
            columnNameFormat.set_bg_color('#d9d9d9')
            # Text Data Format 
            textFormat = workbook.add_format()
            textFormat.set_border(1)

            #write Data
            worksheet.merge_range(row,0,row+1,9 , 'Weekly Report - Clockify - Billable vs Non-Billable', titleFormat)
            row += 2

            headers = {
                "Issue Date/Time Stamp:" : datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                "Date Range Start:": start,
                "Date Range End:": end
            }
            for key, value in headers.items():
                worksheet.merge_range(row,0,row,1,key, headerFormat)
                worksheet.merge_range(row,2,row,3,value)
                row += 1
            # row -= 3
    
            # worksheet.write(row,4, "Billable Legend", headerFormat)
            # row+=1
            # worksheet.write(row,4, "Billable", billableFormat)
            # row += 1
            # worksheet.write(row,4, "Non-Billable", nBillableFormat)
            # row += 2
            row += 1
            worksheet.merge_range(row,0,row,1, 'Employee Name', columnNameFormat)
            worksheet.merge_range(row,2,row,3, 'Reporting Manager', columnNameFormat)
            worksheet.write(row,4, 'Billable', columnNameFormat)
            worksheet.write(row,5, 'Non-Billable', columnNameFormat)
            worksheet.write(row,6, 'Total', columnNameFormat)
            worksheet.merge_range(row,7,row,9, 'Notes', columnNameFormat)
            row += 1
            for rowData in data:
                worksheet.merge_range(row,0,row,1, rowData[0], textFormat)
                worksheet.merge_range(row,2,row,3, rowData[1], textFormat)
                worksheet.write(row,4, rowData[2], textFormat)
                worksheet.write(row,5, rowData[3], textFormat)
                worksheet.write(row,6, rowData[3] + rowData[2], textFormat)
                worksheet.merge_range(row,7,row, 9 ,'', textFormat)
                row+= 1
            
            writer.close()

        return folder_path
    except Exception as e: 
        logger.error(f'{e.__traceback__.tb_lineno} - {str(e)}')

def Payroll(start = None, end = None): 
    logger = setup_background_logger()
    try:
        if start is None or end is None:
            start = (datetime.now() - timedelta(days = (14 + datetime.now().weekday() + 1))).strftime('%Y-%m-%d') # find sunday start time 
            end =   (datetime.now() - timedelta(days = (2 + datetime.now().weekday()))).strftime('%Y-%m-%d') #find saturday 
        logger.info(f'Biling Report Generating for - {start}-{end}')

        cursor, conn = sqlConnect()

        #obtain relavant data 
        cursor.execute(
            f'''
            SELECT 
                at.name, 
                at.[Type], 
                at.[date], 
                at.RegularHrs, 
                at.Accrued,
                at.Overtime,
                at.TimeOff,
                at.policy_name,
                at.TotalHours,
                at.Holiday
            from AttendanceApproved at
            where at.date between '{start}' and '{end}'
            order by at.name
            '''
        )
        data = cursor.fetchall()

        cursor.execute(f'''
        SELECT 
            at.name, 
            Null as Type, 
            Null as [day], 
            SUM(at.RegularHrs) as Reg, 
            SUM(at.Accrued) as Banked,
            SUM(at.Overtime) as OT,
            SUM(at.TimeOff) as PTO,
            'Policy Name' as reason,
            SUM(at.TotalHours) as Total,
            Null as holiday
        from AttendanceApproved at
        where at.date between '{start}' and '{end}'
        group by at.name
        order by at.name
        '''
        )
        totalsData = cursor.fetchall()
        data = [['' if val is None else val for val in row] for row in data]
        totalsData = [['' if val is None else val for val in row] for row in totalsData]

         # Generate Folder for spreadsheets
        current_dir = settings.BASE_DIR
        folder_name = f"Weekly Report-payroll-{start}-{end}"
        folder_path = os.path.join(current_dir, folder_name)
        logger.debug(f'Created Folder at {folder_path}')
        if not os.path.exists(folder_path):
                os.makedirs(folder_path )
        file_path = os.path.join(folder_path, f"{folder_name}.xlsx")

        

        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
            #Generate file and initilize writers and formats 
            workbook = writer.book
            worksheet = workbook.add_worksheet("Hill Plain - Payroll")
            writer.sheets['Hill Plain - Payroll'] = worksheet 
            
            row = 0 #initilize row pointer 

            #formats
            titleFormat = workbook.add_format({'bold': True, 'align': 'center'})
            titleFormat.set_font_size(20)
            titleFormat.set_bg_color('#D9D9D9')
            #file Heaaders
            headerFormat = workbook.add_format({'bold': True, "italic": True})
            #columnNameFormat 
            columnNameFormat = workbook.add_format({'bold': True})
            columnNameFormat.set_border(1)
            columnNameFormat.set_bg_color('#808080')
            columnNameFormat.set_font_color('#ffffff')
            # Text Data Format 
            textFormat = workbook.add_format()
            textFormat.set_border(1)
            # date Data Format 
            dateFormat = workbook.add_format({'num_format': 'yyyy-mm-dd'})
            dateFormat.set_border(1)
            dateFormat.set_border(1)

            #totals
            totalFormat = workbook.add_format({"bold": True, 'italic': True, 'align': 'center'})
            totalFormat.set_border(1)
            totalFormat.set_bg_color('#D9D9D9')
            logger.info('Writing data')

        #write data 
            worksheet.merge_range(row,0,row+1,13 , 'BiWeekly Report - Clockify - Payroll', titleFormat)
            row += 2

            headers = {
                "Issue Date/Time Stamp:" : datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                "Date Range Start:": start,
                "Date Range End:": end
            }
            for key, value in headers.items():
                worksheet.merge_range(row,0,row,1,key, headerFormat)
                worksheet.merge_range(row,2,row,3,value)
                row += 1
            row += 1

            #write columns 
            worksheet.merge_range(row,0,row,1, 'Staff Member', columnNameFormat)
            worksheet.write(row,2,'Type', columnNameFormat)
            worksheet.write(row,3,'Date', columnNameFormat)
            worksheet.write(row,4,'REG', columnNameFormat)
            worksheet.write(row,5,'BANKED', columnNameFormat)
            worksheet.write(row,6,'OT', columnNameFormat)
            worksheet.write(row,7,'Used PTO', columnNameFormat)
            worksheet.merge_range(row,8,row,9,'Policy', columnNameFormat)
            worksheet.write(row,10,'Total Paid', columnNameFormat)
            worksheet.write(row,11,'Holidy', columnNameFormat)
            row += 1
            currentEmp = None
            previousEmp = None
            i = 0
            while i < len(totalsData): 
                for rowData in data:
                    currentEmp = str(rowData[0])
                    if currentEmp is not None and previousEmp is not None and currentEmp != previousEmp:
                            logger.info(totalsData[i])
                            worksheet.merge_range(row,0,row,1, totalsData[i][0], totalFormat)
                            worksheet.write(row,2,totalsData[i][1], totalFormat)
                            worksheet.write(row,3,totalsData[i][2], totalFormat)
                            worksheet.write(row,4,totalsData[i][3], totalFormat)
                            worksheet.write(row,5,totalsData[i][4], totalFormat)
                            worksheet.write(row,6,totalsData[i][5], totalFormat)
                            worksheet.write(row,7,totalsData[i][6], totalFormat)
                            worksheet.merge_range(row,8,row,9,totalsData[i][7], totalFormat)
                            worksheet.write(row,10,totalsData[i][8], totalFormat)
                            worksheet.write(row,11,totalsData[i][9], totalFormat)
                            i += 1
                            row+=1
                    worksheet.merge_range(row,0,row,1, rowData[0], textFormat)
                    worksheet.write(row,2,rowData[1], textFormat)
                    worksheet.write(row,3,rowData[2], dateFormat)
                    worksheet.write(row,4,rowData[3], textFormat)
                    worksheet.write(row,5,rowData[4], textFormat)
                    worksheet.write(row,6,rowData[5], textFormat)
                    worksheet.write(row,7,rowData[6], textFormat)
                    worksheet.merge_range(row,8,row,9,rowData[7], textFormat)
                    worksheet.write(row,10,rowData[8], textFormat)
                    worksheet.write(row,11,rowData[9], textFormat)
                    previousEmp=str(rowData[0])
                    row+=1
                break
        
            writer.close()
        return folder_path
            

    except Exception as e:
        logger.error(f'{e.__traceback__.tb_lineno} - {str(e)}')

def TimeStatus(start = None, end = None):
    logger = setup_background_logger()
    try: 
        #obtain date range for this month 
        if start is None or end is None:
            start = (datetime.now() - timedelta(days = (7 + datetime.now().weekday() + 1))).strftime('%Y-%m-%d') # find sunday start time 
            end =   (datetime.now() - timedelta(days = (2 + datetime.now().weekday()))).strftime('%Y-%m-%d') #find saturday 
        endRange = end
        startRange = start
        while datetime.strptime(start, '%Y-%m-%d')  <= datetime.strptime(endRange, '%Y-%m-%d'):
            end = (datetime.strptime(start, '%Y-%m-%d') + timedelta(days=6)).strftime('%Y-%m-%d')
            logger.info(f'Biling Report Generating for - {start}-{end}')

            cursor, conn = sqlConnect()

            query = f'''
                Select 
                    eu.name,
                    eu.manager,
                    Case 
                        when Exists (
                            select 1 from Timesheet ts 
                            where ts.status = 'APPROVED' 
                            and DATEADD(day ,1, ts.start_time) between '{start}' and '{end}'
                            and ts.emp_id = eu.id
                        ) then 1
                        when Exists (
                            select 1 from Timesheet ts 
                            where ts.status = 'PENDING' 
                            and DATEADD(day ,1, ts.start_time) between '{start}' and '{end}'
                            and ts.emp_id = eu.id 
                        ) then 2
                        when not Exists (
                            select 1 from AttendanceApproved ap
                            where ap.name = eu.name 
                            and ap.date between '{start}' and '{end}'
                        ) then 3
                        when Exists (
                            select 1 from AttendanceApproved ap
                            where ap.name = eu.name and ap.TimeOff != 0
                            and ap.date between '{start}' and '{end}'
                        ) then 4
                        else 5
                    end as [Status]
                From EmployeeUser eu
                order by eu.name
                '''
            logger.debug(query)
            #obtain relavant data 
            cursor.execute(query)
            data = cursor.fetchall()
            data = [['' if val is None else val for val in row] for row in data]
        
            # Generate Folder for spreadsheets
            current_dir = settings.BASE_DIR
            folder_name = f"Weekly Report-Weekly Time Status-{startRange}-{endRange}"
            folder_path = os.path.join(current_dir, folder_name)
            logger.debug(f'Created Folder at {folder_path}')
            if not os.path.exists(folder_path):
                    os.makedirs(folder_path )
            file_path = os.path.join(folder_path, f"Time Status {start} to {end}.xlsx")

            with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
                #Generate file and initilize writers and formats 
                workbook = writer.book
                worksheet = workbook.add_worksheet("Hill Plain - Time Status ")
                writer.sheets['Hill Plain - Time Status'] = worksheet 
                
                row = 0 #initilize row pointer 

            #formats  
                #title 
                titleFormat = workbook.add_format({'bold': True, 'align': 'center'})
                titleFormat.set_font_size(20)
                titleFormat.set_bg_color('#D9D9D9')
                #file Heaaders
                headerFormat = workbook.add_format({'bold': True, "italic": True})
                #status formats  
                approvedFormat = workbook.add_format()
                approvedFormat.set_bg_color("#daf2d0")
                approvedFormat.set_border(1)
                submittedFormat = workbook.add_format()
                submittedFormat.set_bg_color("#ffff99")
                submittedFormat.set_border(1)
                missingFormat = workbook.add_format()
                missingFormat.set_bg_color("#f7c7ac")
                missingFormat.set_border(1)
                timeOffFormat = workbook.add_format()
                timeOffFormat.set_bg_color("#caedfb")
                timeOffFormat.set_border(1)
                #columnNameFormat 
                columnNameFormat = workbook.add_format({'bold': True, 'align': 'center'})
                columnNameFormat.set_border(1)
                columnNameFormat.set_bg_color('#d9d9d9')
                # Text Data Format 
                textFormat = workbook.add_format({ 'align': 'center'})
                textFormat.set_border(1)

                #write Data
                worksheet.merge_range(row,0,row+1,11 , 'Weekly Report - Weekly Report - Clockify - Time Entry Status', titleFormat)
                row += 2

                headers = {
                    "Issue Date/Time Stamp:" : datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                    "Date Range Start:": start,
                    "Date Range End:": end
                }
                for key, value in headers.items():
                    worksheet.merge_range(row,0,row,1,key, headerFormat)
                    worksheet.merge_range(row,2,row,3,value)
                    row += 1
                row -= 3
        
                worksheet.write(row,4, "LEGEND", headerFormat)
                row+=1
                statuses = {
                    '1': [
                        'APPROVED', approvedFormat
                    ],
                    '2': [
                        'SUBMITTED', submittedFormat
                    ],
                    '3': [
                        'NO TIME', missingFormat
                    ],
                    '4': [
                        'NOT APPLICABLE', timeOffFormat
                    ]
                }
                for key, value in statuses.items():
                    worksheet.merge_range(row,4,row,5 , value[0], value[1])
                    row += 1
                row +=1 

                worksheet.merge_range(row,0,row,1, 'Employee Name', columnNameFormat)
                worksheet.merge_range(row,2,row,3, 'Reporting Manager', columnNameFormat)
                worksheet.merge_range(row,4,row,5 ,'Status', columnNameFormat)
                worksheet.merge_range(row,6,row,8, 'Notes', columnNameFormat)
                row += 1
                for rowData in data:
                    worksheet.merge_range(row,0,row,1, rowData[0], textFormat)
                    worksheet.merge_range(row,2,row,3, rowData[1], textFormat)
                    worksheet.merge_range(row,4,row,5, statuses[str(rowData[2])][0], statuses[str(rowData[2])][1])
                    worksheet.merge_range(row,6,row,8, '', textFormat)
                    row+= 1
                
                writer.close()
            start = (datetime.strptime(start, '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
            end = (datetime.strptime(end, '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
        return folder_path
    except Exception as e: 
        logger.error(f'{e.__traceback__.tb_lineno} - {str(e)}')

def main():
    BillableReportGenerate('07','24')
    # MonthylyProjReport('2024-02-25', '2024-03-24')
   

if __name__ == "__main__": 
    main()