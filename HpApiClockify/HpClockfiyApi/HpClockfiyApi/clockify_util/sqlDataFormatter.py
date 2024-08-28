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
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import win32com.client as win32
import asyncio
import time
import random 
from asgiref.sync import sync_to_async
import pythoncom
from concurrent.futures import ThreadPoolExecutor

logger = setup_background_logger()
def convertXlsxPdf(folder_path, file_path, retry = 0):
    try:
        while retry < 2:
            # wait = random.randint(0,10)
            # logger.info(f'Waiting for - {wait}s.')
            # time.sleep(wait)
            logger.info(f'File path {file_path}')
            logger.info('Generating PDF from XL file')
            pythoncom.CoInitialize()  # Initialize COM for the current thread
            excel = win32.Dispatch('Excel.Application')
            excel.Visible = False
            excel.ScreenUpdating = False
            pdfFile = os.path.join(folder_path, f"{os.path.splitext(file_path)[0]}.pdf")
            wb = excel.Workbooks.Open(file_path)
            i = 0
            logger.debug(f'Number of worksheets {len(wb.Worksheets)}')
            for ws in wb.Worksheets:
                # ws = wb.Worksheets[i]
                logger.info(f'Formating Page {i}')
                ws.PageSetup.Zoom = False  # Disable Zoom to use FitToPages
                ws.PageSetup.FitToPagesWide = 1
                ws.PageSetup.FitToPagesTall = False
                ws.PageSetup.PaperSize = 1
                ws.PageSetup.CenterHorizontally = True
                
                # ws.PageSetup.Orientation = 1
                # ws.PageSetup.CenterVertically = True
                ws.PageSetup.CenterFooter = '&P'  # Page number
                ws.PageSetup.LeftFooter = '&D'    # Date
                ws.PageSetup.RightFooter = '&T'   # Time
                i += 1


            logger.info(f'Exporting as Pdf')
            wb.ExportAsFixedFormat(0, f'{pdfFile}')
            logger.info('Operation Successful')
            wb.Close(SaveChanges=0)  # Ensure SaveChanges is set to 0 to avoid saving changes

            excel.Quit()
            # Release COM objects
            del ws
            del wb
            del excel
            break
        if retry >=4:
            logger.warning('Operation failed after exceeding max Retries')
    except Exception as e:
        logger.error(f'({e.__traceback__.tb_lineno}) - {str(e)}')
        wait = random.randint(0,10)
        logger.info(f'Pausing for {wait}s...')
        for i in range(0,wait):
            logger.info(f'\tWaiting...{file_path}')
            time.sleep(1)
        logger.info(f'Resuming operation. Retry at {retry+ 1}')
        try:
            wb.Close(SaveChanges=0)  # Ensure SaveChanges is set to 0 to avoid saving changes

            excel.Quit()
            # Release COM objects
            del ws
            del wb
            del excel
        except Exception as e:
            logger.warning(f'Error occured when trying to close resources {str(e)}')
        convertXlsxPdf(folder_path, file_path, retry=retry+ 1)
    finally:
        pythoncom.CoUninitialize()  # Uninitialize COM for the current thread

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
        
def generateBilling(file_path, pId, startDate, endDate, logger, month, year):
    try:
        cursor, conn = sqlConnect()
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
                eu.truckDetails, 
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
            group by eu.name, eu.truckDetails, cast(en.rate/100 as Decimal(10,2))
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
        #entries data 
        query =f'''
                Select 
                    Coalesce(eu.name, 'Missing name info'),
                    Cast(en.start_time as date),
                    en.duration,
                    Coalesce(en.[description],'No Description')
                from Entry en 
                Inner join TimeSheet ts on ts.id = en.time_sheet_id
                Inner join EmployeeUser eu on eu.id = ts.emp_id
                inner join Project p on p.id = '{pId[0]}' and en.project_id = p.id
                where en.billable = 1 and Cast(en.start_time as Date) between '{startDate}' and '{endDate}'
                and ts.status = 'APPROVED'
                order by eu.name, Cast(en.start_time as date)
        '''   
        logger.debug(query)
        cursor.execute(query)
        descriptionData = cursor.fetchall()
        
        #format results for opperations 
        labourData = [['' if val is None else val for val in data] for data in labourData]
        equipmentData = [['' if val is None else val for val in data] for data in equipmentData]
        if equipmentTotal[0] is not None:
            grandTotal = labourTotal[0] + equipmentTotal[0]
            equipmentTotal = float(equipmentTotal[0])
        else: 
            grandTotal = labourTotal[0]
        if labourTotal[0] is not None:
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
            worksheet.merge_range(0,0,1,11, "Hill Plain - Monthly LEM (Indirects)", mergeCells)

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
            # worksheet.set_column('E:E', 15)  # Width for column B
            #File headers info 
            headers = {
                "Project Name:": pId[2],
                "Project Number:": pId[1],
                "Invoice Month:" : getAbbreviation(month, year),
                "Time Period Start:": startDate,
                "Time Period End:": endDate,
                "Generated On:": datetime.now().strftime("%Y-%m-%d at %H:%M")
            }
            logger.info(reverseForOutput(headers))

            #bold Text format 
            bold_format = workbook.add_format({'bold':True, 'text_wrap': True})
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
            worksheet.merge_range(row,0,row,11, 'LABOUR', headersFormat)
            row += 1
            
            #write column names 
            worksheet.merge_range(row,0,row, 2, 'Staff Member', columnFormat)
            worksheet.merge_range(row,3,row, 6, 'Position', columnFormat)
            worksheet.write( row,7, 'Qty', columnFormat)
            worksheet.write( row,8, 'Unit Cost', columnFormat)
            worksheet.write( row,9, 'Rate', columnFormat)
            worksheet.merge_range( row,10, row, 11, 'Amount', columnFormat)
            row += 1

            for rowData in labourData:
                worksheet.merge_range(row,0,row, 2, rowData[0], dataFormat)
                worksheet.merge_range(row,3,row, 6, rowData[1], dataFormat)
                worksheet.write( row,7, rowData[2], dataFormat)
                worksheet.write( row,8, rowData[3], dataFormat)
                worksheet.write( row,9, rowData[4], numFormat)
                worksheet.merge_range( row,10, row, 11, rowData[5], numFormat)
                row += 1
            logger.info(f'Labour Items - {len(labourData)}')
            #sub Total
            worksheet.merge_range(row,8,row,9,'SUB TOTAL', subTotals)
            worksheet.merge_range(row,10,row,11, labourTotal, boldNum)
            row += 1
        # equipment Table 
            if type(equipmentTotal) is float:
                row += 1
                worksheet.merge_range(row,0,row,11, 'EQUIPMENT', headersFormat)
                row += 1

                worksheet.merge_range(row,0,row, 2, 'Staff Member', columnFormat)
                worksheet.merge_range(row,3,row, 6, 'Equipment Type', columnFormat)
                worksheet.write( row,7, 'Qty', columnFormat)
                worksheet.write( row,8, 'Unit Cost', columnFormat)
                worksheet.write( row,9, 'Rate', columnFormat)
                worksheet.merge_range( row,10, row,  11, 'Amount', columnFormat)
                row += 1

                for rowData in equipmentData:
                    worksheet.merge_range(row,0,row, 2, rowData[0], dataFormat)
                    worksheet.merge_range(row,3,row, 6, rowData[1], dataFormat)
                    worksheet.write( row,7, rowData[2], dataFormat)
                    worksheet.write( row,8, rowData[3], dataFormat)
                    worksheet.write( row,9, rowData[4], numFormat)
                    worksheet.merge_range( row,10, row, 11, rowData[5], numFormat)
                    row += 1

                worksheet.merge_range(row,8,row,9,'SUB TOTAL', subTotals)
                worksheet.merge_range(row,10,row,11, equipmentTotal, boldNum)
                row += 1
            worksheet.merge_range(row,8,row,9, "GRAND TOTAL", grandTotalFormat)
            worksheet.merge_range(row,10,row,11, grandTotal, gt)

            

        # Description of work data 
            dateDataFormat = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'num_format': 'yyyy-mm-dd'})
            dateDataFormat.set_border(1)
            textFormat = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
            textFormat.set_border(1)
            textFormat.set_font(8)
            previousEmp = None 
            for description in descriptionData:
                if description[0] != previousEmp:
                    columnsPerPage = 0
                    # logger.debug(f'Writing to Headers - {row}')
                    logger.debug(pId)
                    row = 2
                    previousEmp = description[0]
                    worksheet = workbook.add_worksheet(f"{previousEmp}")
                    writer.sheets[f"{previousEmp}"] = worksheet   
                    worksheet.merge_range(0,0,1,11, "Hill Plain - Monthly LEM (Indirects)", mergeCells)
                    # worksheet.print_area('A1:K100')
                    for key, value in headers.items():
                        worksheet.merge_range(row, 0,row,1, key, bold_format)
                        worksheet.write(row, 2, value)
                        row += 1
                    row += 1
                    
                    #insert image 
                    worksheet.insert_image("J4",
                                            # r"C:\Users\TimmyIfidon\Desktop\Docs and Projects\Hill Plain Logo New (May2023)\PNG\Hill Plain Logo - NEW (colour).png",
                                            # {'x_scale': 0.04, 'y_scale': 0.04})
                                            r"C:\Users\Script\Desktop\unnamed.png",
                                            {'x_scale': 0.4, 'y_scale': 0.4})
                    
                    worksheet.merge_range(row,0,row,11, description[0], headersFormat)
                    row +=1
                    worksheet.merge_range(row, 0, row, 1, 'Date', columnFormat)
                    worksheet.write(row, 2, 'QTY', columnFormat)
                    worksheet.merge_range(row, 3, row, 11, 'Description', columnFormat)
                    row+=1
                worksheet.merge_range(row, 0, row + 4, 1, f'{description[1]}', dateDataFormat)
                worksheet.merge_range(row, 2, row + 4, 2, f'{description[2]}', textFormat)
                # row+=1 
                worksheet.merge_range(row, 3, row + 4, 11, description[3].replace('\n', ' // '), textFormat)
                # row += 3
                if  row == 51 : # first page break with headers 
                    columnsPerPage = 0
                    pageBreak = True
                    
                else: 
                    columnsPerPage += 1 # counts rows per page therafter 
                    pageBreak = False 
                if pageBreak or columnsPerPage == 11: 
                    logger.info(f'Page Break Occured at row {row} for {description[0]}')
                    columnsPerPage = 0
                    row += 7
                else: row += 5                   
                    

            writer.close()
            
        cleanUp(conn, cursor)
    except Exception as e:
        logger.error(f'({e.__traceback__.tb_lineno}) - {str(e)}')
        
async def BillableReportGenerate(month = None, year = None, pCode = None):
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
        if(endDateObj.weekday() != 5):
            endDate = (endDateObj - timedelta(days=(endDateObj.weekday() + 2) % 7)).strftime('%Y-%m-%d')
        else: endDate = f'20{year}-{month}-25'
        if(startDateObj.weekday() != 6):
            startDate = (startDateObj - timedelta(days=(startDateObj.weekday()+ 1) %7)).strftime('%Y-%m-%d')
        else: f'20{previousYear}-{previousMonth}-25', '%Y-%m-%d'
        logger.debug(f'Date Range: {startDate}-{endDate}')
        # startDate = month
        # endDate = year

        
        cursor, conn = sqlConnect()
    #Get Relavant projects 
        if pCode: 
            query = f'''
                select p.id, p.code, p.title from Project p 
                where exists(
                    select en.id from Entry en
                    inner join TimeSheet ts on ts.id = en.time_sheet_id 
                    where en.billable = 1 and ts.status = 'APPROVED' and
                    en.project_id = p.id 
                    and Cast(en.start_time As Date) between '{startDate}' and '{endDate}'
                )
                and p.code = '{pCode}'
                '''
        else:
            query = f'''
                select p.id, p.code, p.title from Project p 
                where exists(
                    select en.id from Entry en
                    inner join TimeSheet ts on ts.id = en.time_sheet_id 
                    where en.billable = 1 and ts.status = 'APPROVED' and
                    en.project_id = p.id 
                    and Cast(en.start_time As Date) between '{startDate}' and '{endDate}'
                )
                '''
        logger.debug(query)
        cursor.execute(query)
        pIds = cursor.fetchall()
        logger.debug(f'{len(pIds)} Projects')
        cleanUp(conn, cursor)
        # Generate Folder for spreadsheets
        current_dir = settings.BASE_DIR
        reports = 'Reports'
        directory = 'Billing'
        folder_name = f"HP-IND-{year}-{month}"
        # folder_name = f"HP-IND-{startDate}"
        folder_path = os.path.join(current_dir,reports, directory, folder_name)
        logger.debug(f'Created Folder at {folder_path}')
        tasks = []
        filePaths = []
        for pId in pIds:
            if not os.path.exists(folder_path):
                os.makedirs(folder_path )
            file_path = os.path.join(folder_path, f"{getAbbreviation(month)}-{pId[1]}.xlsx")
            filePaths.append(file_path[:-5])
            agenerateBilling = sync_to_async(generateBilling, thread_sensitive= False)
            tasks.append(agenerateBilling(file_path, pId, startDate, endDate, logger, month, year))
        await asyncio.gather(*tasks)
        
        convertAsync = sync_to_async(convertXlsxPdf, thread_sensitive=True)
        tasks.clear()
        j = 0
        # def batch_convert(filePaths, folder_path):
        #     logger.info(f'Converting: {len(filePaths)} files')
        #     with ThreadPoolExecutor(max_workers=2) as executor:
        #         for file_path in filePaths:
        #             executor.submit(convertXlsxPdf, folder_path, file_path)
        # batch_convert(filePaths, folder_path)
        # while j <= len(pIds):
        for file in filePaths:    
            tasks.append(convertAsync(folder_path, file))
        await asyncio.gather(*tasks)
        # while j <= len(pIds):
        #     for i in range(0,2):
        #         if(i + j < len(filePaths)):
        #             tasks.append(convertAsync(folder_path, filePaths[i+ j]))
        #         else: break
        #     await asyncio.gather(*tasks)
        #     tasks.clear()
        #     j +=2
        return folder_path        

    except Exception as e: 
        logger.critical(f'{e.__traceback__.tb_lineno} - {str(e)}')
        
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
                p.code,
                p.title,
                SUM(case when en.billable = 1 then en.duration else 0 end) as Billable,
                Sum(case when en.billable = 0 then en.duration else 0 end) as NonBillable
            From Entry en 
            Inner join Timesheet ts on ts.id = en.time_sheet_id
            inner join Project p on p.id = en.project_id
            inner join EmployeeUser eu on eu.id = ts.emp_id
            where Cast(en.start_time as Date) between '{start}' and '{end}'
            and eu.status = 'ACTIVE'
            Group by 
                eu.name, 
                eu.manager,
                p.code,
                p.title
            order by eu.name
            '''
            )
        data = cursor.fetchall()
        data = [['' if val is None else val for val in row] for row in data]
    
         # Generate Folder for spreadsheets
        current_dir = settings.BASE_DIR
        reports = 'Reports'
        directory = 'BillableVsNonBillable'
        folder_name = f"Weekly Report- Billable vs Non Billable - {start} - {end}"
        folder_path = os.path.join(current_dir,reports, directory, folder_name)
        logger.debug(f'Created Folder at {folder_path}')
        if not os.path.exists(folder_path):
            logger.info('Making Dir')
            os.makedirs(folder_path )
        file_path = os.path.join(folder_path, f"data.xlsx")

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
            # Total  Data Format 
            totalFormat = workbook.add_format({'bold': True})
            totalFormat.set_border(1)
            # Total  Data Format 
            subTotalFormat = workbook.add_format({'bold': True, 'align': 'right'})
            subTotalFormat.set_bg_color('#DAEEF3')
            subTotalFormat.set_border(1)
            # rowTotals 
            rowTotalFormat = workbook.add_format({'bold': True, 'align': 'right'})
            rowTotalFormat.set_border(1)

            #write Data
            worksheet.merge_range(row,0,row+1,11 , 'Weekly Report - Clockify - Billable vs Non-Billable', titleFormat)
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
            worksheet.write(row,4, 'Project Code', columnNameFormat)
            worksheet.merge_range(row,5, row, 7 ,'Project Name', columnNameFormat)
            worksheet.write(row,8, 'Billable', columnNameFormat)
            worksheet.write(row,9, 'Non-Billable', columnNameFormat)
            worksheet.merge_range(row,10, row,11, 'Notes', columnNameFormat)
            row += 1
            totalBillable = 0 
            totalNonBillable = 0
            current = None
            previous = None
            subTotal = 0
            billingAmount = 0
            nonBillingAmount = 0
            for rowData in data:
                current = rowData[0]
                
                if (current is not None or previous is not None) and current != previous:
                    if billingAmount != 0 or nonBillingAmount != 0:
                        worksheet.merge_range(row,0,row,3, '', textFormat)
                        worksheet.write(row,4, '', textFormat)
                        worksheet.merge_range(row,5,row,7, 'TOTAL', rowTotalFormat)
                        worksheet.write(row,8,totalBillable,textFormat)
                        worksheet.write(row,9,totalNonBillable,textFormat)
                        worksheet.merge_range(row,10,row, 11, '', textFormat)
                        row += 1
                        totalBillable = 0
                        totalNonBillable = 0
                    if subTotal!= 0 :
                        worksheet.merge_range(row,0,row,8, 'GRAND TOTAL', subTotalFormat)
                        worksheet.write(row,9,subTotal,subTotalFormat)
                        worksheet.merge_range(row,10,row, 11, '', textFormat)
                        row += 1
                    subTotal = 0
                    billingAmount = 0
                    nonBillingAmount = 0
                    
                    worksheet.merge_range(row,0,row,1, rowData[0], textFormat)
                    worksheet.merge_range(row,2,row,3, rowData[1], textFormat)
                    worksheet.write(row,4, '', textFormat)
                    worksheet.merge_range(row,5, row, 7 , '', textFormat)
                    worksheet.write(row,8, '', textFormat)
                    worksheet.write(row,9, '', textFormat)
                    worksheet.merge_range(row,10,row, 11 ,'', textFormat)
                    row += 1
                    worksheet.merge_range(row,0,row,3, '', textFormat)
                else: worksheet.merge_range(row,0,row,3, '', textFormat)
                worksheet.write(row, 4, rowData[2], textFormat)
                worksheet.merge_range(row,5, row, 7, rowData[3], textFormat)
                worksheet.write(row, 8, rowData[4], textFormat)
                totalBillable += float(rowData[4])
                worksheet.write(row,9, rowData[5], textFormat)
                totalNonBillable += float(rowData[5])
                worksheet.merge_range(row,10, row, 11 ,'', textFormat)
                subTotal += float(rowData[4])
                subTotal += float(rowData[5])
                billingAmount +=  rowData[5] 
                nonBillingAmount += rowData[4]
                previous = rowData[0]
                row+= 1
            
            if subTotal!= 0 :
                worksheet.merge_range(row,0,row,7, 'GRAND TOTAL', subTotalFormat)
                worksheet.write(row,8,subTotal,subTotalFormat)
                worksheet.write(row,9, '', textFormat)
                worksheet.write(row,10, '', textFormat)
                row += 1

            worksheet.merge_range(row,5,row,6, 'Totals', columnNameFormat)
            worksheet.write(row,6,totalBillable,columnNameFormat)
            worksheet.write(row,7,totalNonBillable,columnNameFormat)
            worksheet.write(row,8,(totalBillable+ totalNonBillable),columnNameFormat)
            writer.close()

        convertXlsxPdf(folder_path, file_path)
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
        types = ['Salary', 'Hourly']
        for type in types:
            query = f'''
            SELECT 
                Coalesce(at.name, 'Missing Name Information'), 
                at.[Type], 
                at.[date], 
                at.RegularHrs, 
                at.Accrued,
                at.TimeOff,
                at.Holiday,
                at.policy_name,
                at.TotalHours + at.holiday as TotalHrs,
                Coalesce(eu.manager, 'Missing Manager Information')
            from AttendanceApproved at
            Left Join EmployeeUser eu on eu.name = at.name
            where at.date between '{start}' and '{end}' and at.[Type] = '{type}'
            order by at.name, at.[Type], at.[date] 
            '''
            logger.debug(query)
            #obtain relavant data 
            cursor.execute(query)
            data = cursor.fetchall()
            query = f'''
                SELECT 
                    Coalesce(at.name, 'Missing Name Information'), 
                    Null as Type, 
                    Null as [day], 
                    SUM(at.RegularHrs) as Reg, 
                    SUM(at.Accrued) as Banked,
                    SUM(at.TimeOff) as PTO,
                    Sum(at.Holiday) as holiday,
                    'Policy Name' as reason,
                    SUM(at.TotalHours + at.Holiday) as Total
                from AttendanceApproved at
                
                where at.date between '{start}' and '{end}'  and at.[Type] = '{type}'
                group by at.name, at.[Type]
                order by at.name
            '''
            logger.debug(query)
            cursor.execute(query)
            totalsData = cursor.fetchall()
            data = [['' if val is None else val for val in row] for row in data]
            totalsData = [['' if val is None else val for val in row] for row in totalsData]

            # Generate Folder for spreadsheets
            current_dir = settings.BASE_DIR
            reports = 'Reports'
            payrollDir = 'Payroll'
            folder_name = f"Weekly Report-Payroll-{start}-{end}"
            folder_path = os.path.join(current_dir,reports, payrollDir,  folder_name)
            logger.debug(f'Created Folder at {folder_path}')
            if not os.path.exists(folder_path):
                os.makedirs(folder_path )
            file_path = os.path.join(folder_path, f"{folder_name}-{type}.xlsx")

            

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
                # red text format 
                redTextFormat = workbook.add_format()
                redTextFormat.set_border(1)
                redTextFormat.set_bg_color('#ff0000')
                #missing info format = 
                missingFormat = workbook.add_format()
                missingFormat.set_border(1)
                missingFormat.set_bg_color('#ffff00')
                # missing date Format 
                missingDateFormat = workbook.add_format({'num_format': 'yyyy-mm-dd'})
                missingDateFormat.set_border(1)
                missingDateFormat.set_bg_color('#ffff00')
                # Highlight  Data Format 
                highlightFormat = workbook.add_format({"bold": True, 'italic': True, 'align': 'center'})
                highlightFormat.set_border(1)
                highlightFormat.set_bg_color('#FFCCCB')
                #highlight Green format 
                hlGreenFormat = workbook.add_format({"bold": True, 'italic': True, 'align': 'center'})
                hlGreenFormat.set_border(1)
                hlGreenFormat.set_bg_color('#92d050')
                # date Data Format 
                dateFormat = workbook.add_format({'num_format': 'yyyy-mm-dd'})
                dateFormat.set_border(1)
                dateFormat.set_border(1)
                # staff name title format 
                nameFormat = workbook.add_format({'align': 'center', 'bold': True, 'italic': True})
                nameFormat.set_border(1)
                nameFormat.set_bg_color('#dce6f1')
                #manager Format
                managerFormat = workbook.add_format({'bold': True, "italic": True, 'align':'center'})
                managerFormat.set_border(1)

                #totals
                totalFormat = workbook.add_format({"bold": True, 'italic': True, 'align': 'center'})
                totalFormat.set_border(1)
                totalFormat.set_bg_color('#D9D9D9')
                logger.info('Writing data')

            #write data 
                worksheet.merge_range(row,0,row+1,10 , 'BiWeekly Report - Clockify - Payroll', titleFormat)
                row += 2

                headers = {
                    "Issue Date/Time Stamp:" : datetime.now().strftime('%Y-%m-%d at %H:%M'),
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
                worksheet.write(row,6,'Used PTO', columnNameFormat)
                worksheet.write(row,7,'STAT', columnNameFormat)
                worksheet.merge_range(row,8,row,9,'Policy', columnNameFormat)
                worksheet.write(row,10,'Total Paid', columnNameFormat)
                row += 1
                currentEmp = None
                previousEmp = None
                i = 0
                while i < len(totalsData): 
                    logger.debug(len(totalsData))
                    logger.debug(i)
                    for rowData in data:
                        currentEmp = rowData
                        if currentEmp is not None and previousEmp is not None and str(currentEmp[0]) != str(previousEmp[0]):
                            logger.debug(totalsData[i])
                            worksheet.merge_range(row,0,row,1, totalsData[i][0], totalFormat)
                            worksheet.write(row,2,totalsData[i][1], totalFormat)
                            worksheet.write(row,3,totalsData[i][2], totalFormat)
                            worksheet.write(row,4,totalsData[i][3], totalFormat)
                            worksheet.write(row,5,totalsData[i][4], totalFormat)
                            worksheet.write(row,6,totalsData[i][5], totalFormat)
                            worksheet.write(row,7,totalsData[i][6], totalFormat)
                            worksheet.merge_range(row,8,row,9,totalsData[i][7], totalFormat)
                            if float(totalsData[i][8]) != 80 and str(previousEmp[1]) == 'Salary': 
                                worksheet.write(row,10,totalsData[i][8], highlightFormat)
                            else: worksheet.write(row,10,totalsData[i][8], hlGreenFormat)
                            
                            i += 1
                            row+=1
                        if previousEmp is None or str(currentEmp[0]) != str(previousEmp[0]):
                            worksheet.merge_range(row,0,row,10, rowData[0], nameFormat, )
                            worksheet.merge_range(row+1,0,row+1,10, f'Reporting Manager: {rowData[9]}', managerFormat)
                            row += 2
                        if rowData[0] == 'Missing Name Information': 
                            worksheet.merge_range(row,0,row,1, rowData[0], missingFormat)
                            worksheet.write(row,2, rowData[1], missingFormat)
                            worksheet.write(row,3, rowData[2], missingDateFormat)
                            worksheet.write(row,4, rowData[3], missingFormat)
                            worksheet.write(row,5, rowData[4], missingFormat)
                            worksheet.write(row,6, rowData[5], missingFormat)
                            worksheet.write(row,7, rowData[6], missingFormat)
                            worksheet.merge_range(row,8,row,9,rowData[7], missingFormat)
                            worksheet.write(row,10, rowData[8], missingFormat)
                        else: 
                            worksheet.merge_range(row,0,row,1, rowData[0], textFormat)
                            worksheet.write(row,2, rowData[1], textFormat)
                            worksheet.write(row,3, rowData[2], dateFormat)
                            worksheet.write(row,4, rowData[3], textFormat)
                            worksheet.write(row,5, rowData[4], textFormat)
                            worksheet.write(row,6, rowData[5], textFormat)
                            worksheet.write(row,7, rowData[6], textFormat)
                            worksheet.merge_range(row,8,row,9,rowData[7], textFormat)
                            if int(rowData[8]) > 8: worksheet.write(row,10, rowData[8], redTextFormat)
                            else: worksheet.write(row,10, rowData[8], textFormat)
                        previousEmp=rowData
                        row+=1
                    break
                if totalsData is None or  len(totalsData) < 1: 
                    return folder_path
                logger.debug(totalsData[i])
                worksheet.merge_range(row,0,row,1, totalsData[i][0], totalFormat)
                worksheet.write(row,2,totalsData[i][1], totalFormat)
                worksheet.write(row,3,totalsData[i][2], totalFormat)
                worksheet.write(row,4,totalsData[i][3], totalFormat)
                worksheet.write(row,5,totalsData[i][4], totalFormat)
                worksheet.write(row,6,totalsData[i][5], totalFormat)
                worksheet.write(row,7,totalsData[i][6], totalFormat)
                worksheet.merge_range(row,8,row,9,totalsData[i][7], totalFormat)
                if float(totalsData[i][8]) != 80 and str(previousEmp[1]) == 'Salary': 
                    worksheet.write(row,10,totalsData[i][8], highlightFormat)
                else: worksheet.write(row,10,totalsData[i][8], hlGreenFormat)
                

                writer.close()
            # convertXlsxPdf(folder_path, file_path[:-5])

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
        else: start = (datetime.strptime(start, '%Y-%m-%d') - timedelta(days = 1 + datetime.strptime(start, '%Y-%m-%d').weekday() )).strftime('%Y-%m-%d')
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
                        when Exists (
                            select 1 from AttendanceApproved ap
                            where ap.name = eu.name 
                            and ap.date between '{start}' and '{end}'
                            and ap.Accrued = 0
                            and ap.TotalHours = 0
                        ) then 3
                        when Exists (
                            select 1 from AttendanceApproved ap
                            where ap.name = eu.name and ap.TimeOff != 0
                            and ap.date between '{start}' and '{end}'
                        ) then 4
                        else 5
                    end as [Status]
                From EmployeeUser eu
                where eu.status = 'ACTIVE'
                order by eu.name
                
                '''
            logger.debug(query)
            #obtain relavant data 
            cursor.execute(query)
            data = cursor.fetchall()
            data = [['' if val is None else val for val in row] for row in data]
        
            # Generate Folder for spreadsheets
            current_dir = settings.BASE_DIR
            reports = 'Reports'
            timeStatusDir = 'TimeStatus'
            folder_name = f"Weekly Report-Weekly Time Status-{startRange}-{endRange}"
            folder_path = os.path.join(current_dir,reports, timeStatusDir,  folder_name)
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
                unknownFormat = workbook.add_format()
                unknownFormat.set_bg_color("#FFC000")
                unknownFormat.set_border(1)
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
                row += 3

                headers = {
                    "Issue Date/Time Stamp:" : datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                    "Date Range Start:": start,
                    "Date Range End:": end
                }
                for key, value in headers.items():
                    worksheet.merge_range(row,0,row,1,key, headerFormat)
                    worksheet.merge_range(row,2,row,3,value)
                    row += 1
                row -= 4
        
                worksheet.write(row,4, "LEGEND", headerFormat)
                row+=1
                statuses = {
                    '1': [
                        'APPROVED', approvedFormat, 'Manager has approved timesheet.'
                    ],
                    '2': [
                        'SUBMITTED', submittedFormat, 'Employee has submitted time for approval. Waiting on managers approval.'
                    ],
                    '3': [
                        'NO TIME', missingFormat, 'Time has not been recorded and no PTO\'s submitted. Unknown time entry.'
                    ],
                    '4': [
                        'NOT APPLICABLE', timeOffFormat, 'No Entries need. Time Off/Vacation'
                    ],
                    '5': [
                        'UNKNOWN STATUS', unknownFormat, 'Time Status for this user cannot be asserted. Review Clockify and logs for more information'
                    ]
                }
                for key, value in statuses.items():
                    worksheet.merge_range(row,4,row,5 , value[0], value[1])
                    worksheet.write(row,6,value[2])
                    row += 1
                row +=1 

                worksheet.merge_range(row,0,row,1, 'Employee Name', columnNameFormat)
                worksheet.merge_range(row,2,row,3, 'Reporting Manager', columnNameFormat)
                worksheet.merge_range(row,4,row,5,'Status', columnNameFormat)
                worksheet.merge_range(row,6,row,8, 'Notes', columnNameFormat)
                row +=1
                for rowData in data:
                    worksheet.merge_range(row,0,row,1, rowData[0], textFormat)
                    worksheet.merge_range(row,2,row,3, rowData[1], textFormat)
                    worksheet.merge_range(row,4,row,5, statuses[str(rowData[2])][0], statuses[str(rowData[2])][1])
                    worksheet.merge_range(row,6,row,8, '', textFormat)
                    row+= 1
                
                writer.close()
            start = (datetime.strptime(start, '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
            end = (datetime.strptime(end, '%Y-%m-%d') + timedelta(days=7)).strftime('%Y-%m-%d')
            convertXlsxPdf(folder_path, file_path)

        return folder_path
    except Exception as e: 
        logger.error(f'{e.__traceback__.tb_lineno} - {str(e)}')

def lemGenerator( projectCode: str, lemId: str):
    logger = setup_background_logger()
    try:
        cursor, conn = sqlConnect()

        #get Summary Data
        query = f''' 
            
            -- For generating lem spreadsheet
            Declare @lemId Nvarchar(MAX) = '{lemId}'
            select Concat(lw.role, ' - Work'), Sum(lw.[work]), lw.workRate, SUM(lw.work * lw.workRate)  From lemWorkerEntries lw
            where lw.id = @lemId
            group by lw.role, lw.workRate
            having Sum(lw.work) != 0
             UNION
            select Concat(lw.role, ' - Travel'), SUM(lw.travel), lw.travelRate, SUM(lw.travel * lw.travelRate)  From lemWorkerEntries lw
            where lw.id = @lemId
            group by lw.role, lw.travelRate
            having Sum(lw.travel) != 0
             Union
            select Concat(lw.role, ' - Calc'), Sum(lw.Calc) , lw.[Calc Rate], SUM(lw.calc * lw.[Calc Rate])  From lemWorkerEntries lw
            where lw.id = @lemId
            group by lw.role, lw.[Calc Rate]
            having Sum(lw.calc) != 0
             Union
            select Concat(lw.role, ' - Meal'), Sum(lw.Meals) , lw.mealRate, SUM(lw.mealTotal)  From lemWorkerEntries lw
            where lw.id = @lemId
            group by lw.role, lw.mealRate
            having Sum(lw.Meals) != 0
             Union
            select Concat(lw.role, ' - Hotel'), Sum(lw.Hotel) , lw.hotelRate, SUM(lw.hotelTotal)  From lemWorkerEntries lw
            where lw.id = @lemId
            group by lw.role, lw.hotelRate
            having Sum(lw.Hotel) != 0
        '''
        logger.debug(query)
        cursor.execute(query)
        dataSummary = cursor.fetchall()
        #get lem info 
        query = f'''
             
            Declare @lemId Nvarchar(MAX) = '{lemId}'
            select ls.lemNumber, c.name, ls.lem_sheet_date, eu.name,  ls.notes, ls.[description], ls.clientRep From LemSheet ls
            inner join Client c on c.id = ls.clientId
            inner join EmployeeUser eu on eu.id = ls.projectManagerId
            where ls.id =  @lemId
        '''
        logger.debug(query)
        cursor.execute(query)
        lemInfo = cursor.fetchone()

        #lem worker Entries
        query = f'''
             
            Declare @lemId Nvarchar(MAX) = '{lemId}'
            Select 
                lw.emp,
                lw.role,
                lw.work,
                lw.WorkTotal,
                lw.travel,
                lw.TravelTotal, 
                lw.Calc,
                lw.CalcTotal,
                lw.Meals,
                lw.Hotel
            from lemWorkerEntries lw
            where lw.id = @lemId
        '''
        logger.debug(query)
        cursor.execute(query)
        workerEntries = cursor.fetchall()
        #lem Equipment Entries
        query = f'''
            
            Declare @lemId Nvarchar(MAX) = '{lemId}'
            Select 
                le.name,
                le.qty,
                le.Rate,
                le.cost

            from lemEquipEntries le
            where le.id = @lemId
        '''
        logger.debug(query)
        cursor.execute(query)
        equipmentEntries = cursor.fetchall()
        
        #format Null values
        dataSummary = [['Missing Rate' if val is None else val for val in row] for row in dataSummary]
        lemInfo = ['----' if val is None else val for val in lemInfo] 
        workerEntries = [['' if val is None else val for val in row] for row in workerEntries]
        equipmentEntries = [['' if val is None else val for val in row] for row in equipmentEntries]

        # Generate Folder for spreadsheets
        current_dir = settings.BASE_DIR
        reports = 'Reports'
        lemDir = f"LemSheets"
        projDir = projectCode
        folder_name = lemInfo[0]

        folder_path = os.path.join(current_dir, reports, lemDir, projDir, folder_name)
        logger.debug(f'Created Folder at {folder_path}')
        if not os.path.exists(folder_path):
                os.makedirs(folder_path )
        file_path = os.path.join(folder_path, f"{projDir}-{folder_name}.xlsx")
        logger.debug(f'File at {file_path}')

        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
            #Generate file and initilize writers and formats 
            workbook = writer.book
            worksheet = workbook.add_worksheet(f"{projectCode} - {lemInfo[0]}")
            writer.sheets[f'{projectCode} - {lemInfo[0]}'] = worksheet 
            
            row = 0 #initilize row pointer 

            #formats
            #title 
            titleFormat = workbook.add_format({'bold': True, 'align': 'center'})
            titleFormat.set_font_size(20)
            titleFormat.set_bg_color('#FFDB69')
            #file Heaaders
            headerFormat = workbook.add_format({'bold': True, "italic": True, 'align': 'right', 'valign':'top'})
            headerValueFormat = workbook.add_format({'italic': True,'align': 'left', 'text_wrap': True, 'valign':'top'})
            #columnNameFormat 
            columnNameFormat = workbook.add_format({'bold': True, 'align': 'center'})
            columnNameFormat.set_border(1)
            columnNameFormat.set_bg_color('#d9d9d9')
            # Text Data Format 
            textFormat = workbook.add_format({ 'align': 'center', 'text_wrap': True, 'valign': 'vcenter'})
            textFormat.set_border(1)
            textFormat.set_font_size(10)
            #numFormat
            numFormat = workbook.add_format({'align': 'center', 'num_format': '$#,##0.00', 'valign': 'vcenter', 'text_wrap': True})
            numFormat.set_border(1)
            numFormat.set_font_size(10)
            dateFormat = workbook.add_format({'num_format': 'yyyy-mm-dd', 'align':'left', 'valign':'top'})
            
            descripTitleFormat = workbook.add_format({'bold': True, 'align':'center'})
            descripTitleFormat.set_font_size(15)
            descripTitleFormat.set_border(1)
            descripTitleFormat.set_bg_color('#D9D9D9')

            descripFormat = workbook.add_format({'italic': True,'align': 'center', 'text_wrap': True, 'valign': 'vcenter'})
            descripFormat.set_border(1)
            descripFormat.set_font_size(9)
            descripFormat.set_bg_color('#F2F2F2')
            

            logger.info('Writting Data....')
            

            logger.debug(row)
            row += 2
            headersLeft = {
                'Client:': lemInfo[1],
                'Client Rep': lemInfo[6],
                'Date:': lemInfo[2],
                'PM:': lemInfo[3],
            }
            headersRight = {
                'Timesheet No. :': lemInfo[0],
                'Task Code:': projectCode,
                'Task Description:': lemInfo[4],
            }
            top = row
            for key, value in headersLeft.items():
                if key != 'Date:':
                    worksheet.merge_range(row,0,row+1, 1, key, headerFormat)
                    worksheet.merge_range(row,2,row+1,3, value, headerValueFormat)
                else: 
                    worksheet.merge_range(row,0,row+1, 1, key, headerFormat)
                    worksheet.merge_range(row,2,row+1, 3, value, dateFormat)
                row += 2
            
            bottom = row
            row = top 
            logger.debug(row)

            for key, value in headersRight.items():
                if key != "Task Description:":
                    worksheet.merge_range(row,4,row+1, 5, key, headerFormat)
                    worksheet.merge_range(row,6,row+1, 8, value, headerValueFormat)
                    row += 2
                    continue
                else: 
                    worksheet.merge_range(row,4,row+1, 5, key, headerFormat)
                    worksheet.merge_range(row,6,row+3, 8, value,headerValueFormat)
                    row += 4
                    continue
            logger.debug(row)
            row = bottom 
            row += 1
            logger.debug(row)
            worksheet.insert_image("J3",
                # r"C:\Users\TimmyIfidon\Desktop\Docs and Projects\Hill Plain Logo New (May2023)\PNG\Hill Plain Logo - NEW (colour).png",
                # {'x_scale': 0.08, 'y_scale': 0.08}
                r"C:\Users\Script\Desktop\unnamed.png",
                {'x_scale': 0.5, 'y_scale': 0.5}
                )

            workerEntriesColumns = [
                'Emp Name',
                'Role',
                'Work Hrs',
                'Travel Hrs',
                'Calc Hrs',
                'Meals',
                'Hotel'
            ]

            top = row
            column = 0
            for i in range(0,len(workerEntriesColumns)):
                if i in [0,1]:
                    worksheet.merge_range(row, column, row, column+2,workerEntriesColumns[i],columnNameFormat)
                    column += 3
                    continue
                worksheet.write(row,column, workerEntriesColumns[i], columnNameFormat)
                column += 1
            row+=1
            logger.debug(row)

            for rowData in workerEntries:
                column = 0
                for i in range(0,len(rowData)):
                    if i<= 1:
                        worksheet.merge_range(row,column,row,column+2, rowData[i], textFormat)
                        column += 3
                        continue
                    elif i in [3,5,7]: #not includesd in this table 
                        # worksheet.write(row,column, rowData[i], numFormat )
                        # column += 1
                        continue
                    else:
                        worksheet.write(row,column, rowData[i], textFormat)
                        column += 1
                        continue
                row += 1
                logger.debug(row)


            row += 1
            top = row
            worksheet.merge_range(row,0,row,5, 'Description of Work Performed', descripTitleFormat)
            row += 1
            worksheet.merge_range(row,0, row+6, 5, lemInfo[5] , descripFormat)
            row += 7

            # column += 1 #write next table to the right of the second table
            # left = column 
            # write next table under second table 
            row += 1
            left = 0
            column = left

            summaryColumns = [
                'Item', 
                'QTY (Hrs)',
                'Rate',
                'Cost'
            ]
            
            for i in range(0,len(summaryColumns)):
                if i < 1:
                    worksheet.merge_range(row, column, row, column+2,summaryColumns[i],columnNameFormat)
                    column +=3
                    continue
                worksheet.write(row,column, summaryColumns[i], columnNameFormat)
                column += 1
            row += 1
            labourTotal = 0
            for rowData in dataSummary:
                column = left
                for i in range(0,len(rowData)):
                    if i == 0:
                        worksheet.merge_range(row,column,row+1,column+2, rowData[i], textFormat)
                        column += 3
                        continue
                    elif i in [2,3]:
                        worksheet.merge_range(row,column,row+1,column, rowData[i], numFormat )
                        column += 1
                        if i ==3 and type(rowData[i]):
                            try:
                                labourTotal += float(rowData[i])
                            except (ValueError, TypeError) as e:
                                logger.warning(f'Row Data type is {type(rowData[i])}')

                        continue
                    else:
                        worksheet.merge_range(row,column,row+1,column, rowData[i], textFormat)
                        column += 1
                        continue
                row += 2
            
            row = top
            column += 1 #write next table to the right of the description  table
            left = column 
            logger.debug(f'{row}, {column}')
            #write next table under first table 
            # row += 1
            # left = 0
            # column = left
            
            equipmentEntriesColumns = [
                'Equipment',
                'QTY',
                'Rate',
                'Cost'
            ]
            equipTotal =0
            for i in range(0,len(equipmentEntriesColumns)):
                if i < 1:
                    worksheet.merge_range(row, column, row, column+1,equipmentEntriesColumns[i],columnNameFormat)
                    column +=2
                    continue
                worksheet.write(row,column, equipmentEntriesColumns[i], columnNameFormat)
                column += 1
            row += 1


            for rowData in equipmentEntries:
                column = left
                for i in range(0,len(rowData)):
                    if i == 0:
                        worksheet.merge_range(row,column,row+1,column+1, rowData[i], textFormat)
                        column += 2
                        continue
                    elif i in [2,3]:
                        worksheet.merge_range(row,column,row+1, column, rowData[i], numFormat )
                        column += 1
                        if i ==3:
                            try:    
                                equipTotal += float(rowData[i])
                            except (ValueError, TypeError) as e:
                                logger.warning(f'Row Data type is {type(rowData[i])}')

                        continue
                    else:
                        worksheet.merge_range(row,column,row+1, column, rowData[i], textFormat)
                        column += 1
                        continue
                row += 2
            right = column -1
            row += 1
            
            totalNumFormat = workbook.add_format({'bold': True, 'num_format': 7, 'align': 'center'})
            grandTotalNumFormat = workbook.add_format({'bold': True, 'num_format': 7 ,'align': 'center'})
            grandTotalNumFormat.set_bg_color('#FFFF99')

            worksheet.merge_range(row, left,row, left+2, 'Labour Total', headerFormat)
            worksheet.merge_range(row, right-1,row, right, labourTotal, totalNumFormat)
            row+= 1
            worksheet.merge_range(row, left,row, left+2, 'Equip Total', headerFormat)
            worksheet.merge_range(row, right-1,row, right, equipTotal, totalNumFormat)
            row+=1

            grandTotalFormat = workbook.add_format({'bold': True, 'italic': True, 'align':'right'})
            grandTotalFormat.set_bg_color('#FFFF99')
            grandTotalFormat.set_num_format('$#,##0.00')

            

            worksheet.merge_range(row, left, row, left+2, 'Grand Total', grandTotalFormat)
            worksheet.merge_range(row, right-1, row, right, labourTotal + equipTotal, grandTotalNumFormat)


            worksheet.merge_range(0, 0, 1, right, f'{projectCode} {lemInfo[0]}', titleFormat)

        writer.close() 
        convertXlsxPdf(folder_path, file_path)

        return folder_path
    except Exception as e: 

        logger.error(f'{e.__traceback__.tb_lineno} - {str(e)}')
        return None











def main():
    BillableReportGenerate('07','24')
    # MonthylyProjReport('2024-02-25', '2024-03-24')
   

if __name__ == "__main__": 
    main()