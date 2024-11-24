from Utilities.views import sqlConnect, cleanUp, getAbbreviation, reverseForOutput
import os
import pandas as pd
from datetime import datetime, timedelta
from HillPlainAPI.settings import BASE_DIR  
from HillPlainAPI.Loggers import setup_background_logger
import win32com.client as win32
import asyncio
import time
import random 
from asgiref.sync import sync_to_async
import pythoncom
import shutil
import traceback

'''
Functions can be condensed for better readability like what has been don for generateBilling 
and BillableReportGenerate functions
'''

logger = setup_background_logger()
"""
Converts an Excel (.xlsx) file to a PDF file, applying page setup formatting and handling retries on failure.

Parameters:
    folder_path (str): The path to the folder where the PDF file will be saved.
    file_path (str): The path to the Excel (.xlsx) file to convert.
    retry (int, optional): The current retry count. Defaults to 0.

Returns:
    None

Description:
    This function uses the COM interface to automate Excel and convert a specified .xlsx file to PDF format.
    It applies page setup properties for optimal PDF formatting, including setting the page to fit the width
    of one page, enabling headers and footers, and centering horizontally. If the conversion fails, the function
    retries up to two times, with randomized delays between attempts. If the maximum retry count is reached,
    a warning is logged, and the process terminates. COM resources are initialized and released appropriately
    to prevent resource locking.
    
    Error handling includes logging the error and retrying if needed. Additionally, the function performs cleanup
    by closing Excel and uninitializing COM resources.
"""
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

"""
The `generateBilling` function is designed to create a detailed billing report for a specified project within 
a specified date range, writing the output to an Excel file.

Parameters:
- `file_path`: The file path where the generated Excel report will be saved.
- `pId`: Project ID tuple containing relevant identifiers and project name.
- `startDate` and `endDate`: The date range for which billing data should be fetched.
- `logger`: A logger instance for debugging and information messages.
- `month` and `year`: Specifies the month and year for the billing period.

Process:
1. Database Connection: Establishes a SQL database connection and creates a cursor.
2. Data Retrieval: Executes SQL queries to retrieve labor and equipment data for the specified project and date range:
    - `labourData`: Contains labor-related information, including employee name, role, hours, and billing rates.
    - `equipmentData`: Contains equipment-related information, including equipment type, hours, and rates.
    - `labourTotal` and `equipmentTotal`: Calculated totals for labor and equipment.
3. Excel Report Generation:
    - Initializes an Excel writer and workbook, then creates a sheet named "Hill Plain - Monthly LEM."
    - Styles and formatting for the report are set, including title, subtotal, and grand total styles.
    - Writes project-specific headers and inserts a logo image.
    - Writes labor and equipment data in tables, with columns for staff member, position/equipment type, quantity, unit cost, rate, and total amount.
    - Adds subtotal and grand total rows.
4. Description Data: For each employee, creates a separate sheet with a detailed description of entries, 
 including the date, duration, and description of work performed.

Notes:
- Handles null values in data and formats them appropriately in the output.
- Logs key steps and data points for debugging purposes.
"""
def GenerateBilling(file_path, pId, startDate, endDate, logger, month, year):
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
        
    #Remove Nulls 
        labourData = [['' if val is None else val for val in data] for data in labourData]
        equipmentData = [['' if val is None else val for val in data] for data in equipmentData]
    
        labourTotal = float(labourTotal[0]) if labourTotal[0] is not None else 0
        equipmentTotal = float(equipmentTotal[0]) if equipmentTotal[0] is not None else 0
        grandTotal = labourTotal + equipmentTotal
        logger.debug(f'Totals: {labourTotal} {type(labourTotal)}')
        
        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
            #Generate file and initilize writers and formats 
            workbook = writer.book
            worksheet = workbook.add_worksheet("Hill Plain - Monthly LEM")
            writer.sheets['Hill Plain - Monthly LEM'] = worksheet        
            
            # Merged cells Title Format
            TITLE = workbook.add_format({'align': 'center', 'bold': True, 'bg_color': '#FCD5B4', 'font_size': 24, 'border': 2}).set_center_across()
            worksheet.merge_range(0,0,1,11, "Hill Plain - Monthly LEM (Indirects)", TITLE)
            #subTotals Format
            subTotals = workbook.add_format({'align': 'left', 'bold': True, 'bg_color': '#FFFF99', 'font_size': 14, 'italic': True})
            #GrandTotal Format
            grandTotalFormat = workbook.add_format({'align': 'left', 'bold': True, 'bg_color': '#FCD5B4', 'font_size': 14, 'italic': True})
            #table headers Formater 
            headersFormat = workbook.add_format({'align': 'center', 'bold': True, 'bg_color': '#F2F2F2', 'font_size': 16, 'border': 1}).set_center_across()
            #dollar value formats 
            numFormat = workbook.add_format({'align': 'center', 'num_format': '$#,##0.00', 'border': 1})
            #dollar bold value formats 
            boldNum = workbook.add_format({'align': 'center', 'bold': True, 'num_format': '$#,##0.00', 'font_size': 14, 'bg_color': '#FFFF99'})
            #bold Text format 
            bold_format = workbook.add_format({'bold': True, 'text_wrap': True, 'italic': True})
            #Grand total value formats 
            grandTotalFormat = workbook.add_format({'align': 'center', 'bold': True, 'num_format': '$#,##0.00', 'font_size': 14, 'bg_color': '#FCD5B4'})
            # table data format
            dataFormat = workbook.add_format({'border': 1})
            #table column format 
            columnFormat = workbook.add_format({'align': 'center', 'bold': True, 'border': 1})
           
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

            row = 2
            #write file headers
            for key, value in headers.items():
                worksheet.merge_range(row, 0,row,1, key, bold_format)
                worksheet.write(row, 2, value)
                row += 1
                logger.debug(f'Writing to row {row}')
            row += 1 
            #insert image 
            worksheet.insert_image(
                "J4",
                # r"C:\Users\TimmyIfidon\Desktop\Docs and Projects\Hill Plain Logo New (May2023)\PNG\Hill Plain Logo - NEW (colour).png", # For Testing on Timm's machine 
                r"C:\Users\Script\Desktop\unnamed.png", # Path to image on scripting machine
                {'x_scale': 0.4, 'y_scale': 0.4} # scale down for testing on local machine 
            )

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
            if equipmentTotal > 0:
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
            worksheet.merge_range(row,10,row,11, grandTotal, grandTotalFormat)

            

        # Description of work data 
            dateDataFormat = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'num_format': 'yyyy-mm-dd', 'border': 1})
            textFormat = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'text_wrap': True, 'border': 1, 'font_size': 8})
            previousEmp = None 

            for description in descriptionData:
                if description[0] != previousEmp:
                    rowsPerPage = 0
                    # logger.debug(f'Writing to Headers - {row}')
                    # logger.debug(pId)
                    row = 2 #print title after Columns are known 
                    previousEmp = description[0]
                    worksheet = workbook.add_worksheet(f"{previousEmp}")
                    writer.sheets[f"{previousEmp}"] = worksheet   
                    worksheet.merge_range(0,0,1,11, "Hill Plain - Monthly LEM (Indirects)", TITLE)
                    # worksheet.print_area('A1:K100')
                    for key, value in headers.items():
                        worksheet.merge_range(row, 0,row,1, key, bold_format)
                        worksheet.write(row, 2, value)
                        row += 1
                    row += 1
                    
                    #insert image 
                    worksheet.insert_image(
                        "J4",
                        # r"C:\Users\TimmyIfidon\Desktop\Docs and Projects\Hill Plain Logo New (May2023)\PNG\Hill Plain Logo - NEW (colour).png",
                        # {'x_scale': 0.04, 'y_scale': 0.04})
                        r"C:\Users\Script\Desktop\unnamed.png",
                        {'x_scale': 0.4, 'y_scale': 0.4}
                        )
                    
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
                    rowsPerPage = 0
                    pageBreak = True     
                else: 
                    rowsPerPage += 1 # counts rows per page therafter 
                    pageBreak = False 
                if pageBreak or rowsPerPage == 11: 
                    logger.info(f'Page Break Occured at row {row} for {description[0]}')
                    rowsPerPage = 0
                    row += 8
                else: row += 5                   
                    

            writer.close()
    except Exception as e:
        logger.error(f'({e.__traceback__.tb_lineno}) - {str(e)}')
    finally:
        cleanUp(conn, cursor)

"""
The `BillableReportGenerate` asynchronous function generates a billable report for approved, billable entries within a specified date range for a given project code.

Parameters:
- `startDate` (str, optional): The start date of the period to include in the report.
- `endDate` (str, optional): The end date of the period to include in the report.
- `pCode` (str, optional): The project code to filter the report by a specific project.

Process:
1. **Logger Setup**: Initializes a logger for tracking process details and errors.
2. **SQL Connection**: Establishes a connection to the SQL database and retrieves a cursor for executing queries.
3. **Project Retrieval**: Queries the database for projects with approved, billable entries in the specified date range:
   - If `pCode` is provided, retrieves only that project.
   - Otherwise, retrieves all projects with billable entries in the date range.
4. **Report Directory Creation**: 
   - Constructs a folder path based on the current directory, date, and report details.
   - Clears any existing folder and creates a new one to store the report files.
5. **Billing Report Generation**:
   - Iterates through each project and generates an individual billing report using `GenerateBilling`.
   - Each report is saved as an Excel file with a unique file path.
6. **PDF Conversion**:
   - Converts each generated Excel report into a PDF using `convertXlsxPdf`.
   - This task is also executed asynchronously to enhance performance.
7. **Return Path**: Returns the path to the folder containing all generated billing reports.

Notes:
- **Error Handling**: Logs critical errors with details about their location.
- **Async Execution**: Uses `asyncio.gather` to concurrently generate billing reports and convert them to PDFs, improving the function’s efficiency.
"""
async def BillableReportGenerate(startDate = None| str, endDate = None | str, pCode = None):
    logger = setup_background_logger()
    try: 
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
        year = startDate.split("-")[0][-2:]
        month = endDate.split("-")[1]
        # Generate Folder for spreadsheets
        current_dir = BASE_DIR
        reports = 'Reports'
        directory = 'Billing'
        folder_name = f"HP-IND-{year}-{month}"
        # folder_name = f"HP-IND-{startDate}"
        folder_path = os.path.join(current_dir,reports, directory, folder_name)
        logger.debug(f'Created Folder at {folder_path}')
        tasks = []
        filePaths = []
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
            logger.info(f"Clearing existing folder: {folder_path}")
        os.makedirs(folder_path )
        
        for pId in pIds:
            file_path = os.path.join(folder_path, f"{getAbbreviation(month)}-{pId[1]}.xlsx")
            filePaths.append(file_path[:-5])
            agenerateBilling = sync_to_async(GenerateBilling, thread_sensitive= False)
            tasks.append(agenerateBilling(file_path, pId, startDate, endDate, logger, month, year))
        await asyncio.gather(*tasks)
        
        convertAsync = sync_to_async(convertXlsxPdf, thread_sensitive=True)
        tasks.clear()
        for file in filePaths:    
            tasks.append(convertAsync(folder_path, file))
        await asyncio.gather(*tasks)
        return folder_path        

    except Exception as e: 
        logger.critical(f'{e.__traceback__.tb_lineno} - {str(e)}')
    finally: 
        cleanUp(conn, cursor)

"""
Generates a weekly report summarizing billable vs non-billable hours for active employees during a specified date range.

Parameters:
    start (str, optional): The start date of the report range in 'YYYY-MM-DD' format. If None, the default value will be used.
    end (str, optional): The end date of the report range in 'YYYY-MM-DD' format. If None, the default value will be used.

Process:
 1. Initializes a logger for background logging.
 2. Establishes a database connection and retrieves the relevant data using an SQL query.
 3. Generates a folder structure and creates directories for storing the generated report.
 4. Writes the fetched data into an Excel file, with special formatting for headers, sub-totals, percentages, and grand totals.
 5. Each employee's name, manager, project details, and billable/non-billable hours are included in the report.
 6. Calculates and displays subtotals and percentages for billable and non-billable hours.
 7. Finally, the report is converted to a PDF and saved in the specified directory.

If an error occurs during execution, an exception is logged with detailed trace information.

The function returns the folder path where the report is stored.
"""
def NonBillableReportGen(start = None, end = None):
    logger = setup_background_logger()
    try: 

        cursor, conn = sqlConnect()

        #obtain relavant data 
        query = f'''
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
        logger.debug(query)
        cursor.execute(query)
        data = cursor.fetchall()
        data = [['' if val is None else val for val in row] for row in data]
    
        # Generate Folder for spreadsheets
        current_dir = BASE_DIR
        reports = 'Reports'
        directory = 'BillableVsNonBillable'
        folder_name = f"Weekly Report- Billable vs Non Billable - {start} - {end}"
        folder_path = os.path.join(current_dir,reports, directory, folder_name)
        logger.debug(f'Created Folder at {folder_path}')
        if not os.path.exists(folder_path):
            logger.info('Making Dir')
            os.makedirs(folder_path, exist_ok=True)
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
            subTotalFormatNum = workbook.add_format({'bold': True, 'align': 'center'})
            subTotalFormatNum.set_bg_color('#DAEEF3')
            subTotalFormatNum.set_border(1)
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
            grandBill = 0
            grandNonBill = 0
            for rowData in data:
                current = rowData[0]
                if (current is not None or previous is not None) and current != previous:
                    if billingAmount != 0 or nonBillingAmount != 0:
                        worksheet.merge_range(row,0,row,7, 'SUB TOTAL', subTotalFormat)
                        worksheet.write(row,8,totalBillable,subTotalFormatNum)
                        worksheet.write(row,9,totalNonBillable,subTotalFormatNum)
                        worksheet.merge_range(row,10,row, 11, '', textFormat)
                        row += 1
                        worksheet.merge_range(row,0,row,7, 'PERCENTAGE', subTotalFormat)
                        worksheet.write(row,8,f'%{round((totalBillable/subTotal)*100, 2)}',subTotalFormatNum)
                        worksheet.write(row,9,f'%{round((totalNonBillable/subTotal)*100, 2)}',subTotalFormatNum)
                        worksheet.merge_range(row,10,row, 11, '', textFormat)
                        row += 1
                        worksheet.merge_range(row,0,row,7, 'GRAND TOTAL', subTotalFormat)
                        worksheet.merge_range(row,8,row,9, subTotal,subTotalFormatNum)
                        worksheet.merge_range(row,10,row, 11, '', textFormat)
                        row += 1
                    
                    totalBillable = 0
                    totalNonBillable = 0
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
                    # worksheet.merge_range(row,0,row,3, '', textFormat)
                    row += 1
                else: 
                    worksheet.merge_range(row,0,row,3, '', textFormat)
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
                grandBill +=float(rowData[4])
                grandNonBill +=float(rowData[5])
                row+= 1
            
            if billingAmount != 0 or nonBillingAmount != 0:
                worksheet.merge_range(row,0,row,7, 'SUB TOTAL', subTotalFormat)
                worksheet.write(row,8,totalBillable,subTotalFormatNum)
                worksheet.write(row,9,totalNonBillable,subTotalFormatNum)
                worksheet.merge_range(row,10,row, 11, '', textFormat)
                row += 1
                
            if subTotal!= 0 :
                worksheet.merge_range(row,0,row,7, 'PERCENTAGE', subTotalFormat)
                worksheet.write(row,8,f'%{round((totalBillable/subTotal)*100, 2)}',subTotalFormatNum)
                worksheet.write(row,9,f'%{round((totalNonBillable/subTotal)*100, 2)}',subTotalFormatNum)
                worksheet.merge_range(row,10,row, 11, '', textFormat)
                row += 1
                worksheet.merge_range(row,0,row,7, 'GRAND TOTAL', subTotalFormat)
                worksheet.merge_range(row,8,row,9, subTotal,subTotalFormatNum)
                worksheet.merge_range(row,10,row, 11, '', textFormat)
                row += 1

            worksheet.merge_range(row,5,row,7, 'GRAND TOTAL', columnNameFormat)
            worksheet.write(row,8, grandBill,columnNameFormat)
            worksheet.write(row,9,grandNonBill,columnNameFormat)
            worksheet.write(row+1,9,(grandBill+ grandNonBill),columnNameFormat)
            writer.close()
        convertXlsxPdf(folder_path, file_path)
        return folder_path
    except Exception as e: 
        logger.error(f'Error occurred at line {e.__traceback__.tb_lineno}: {traceback.format_exc()}')
    finally: 
        cleanUp(cursor=cursor, conn=conn)

'''
The `NonBillableReportGen` asynchronous function generates a weekly report summarizing billable vs. non-billable hours for 
active employees, formatting the data in an Excel file with specific styles for easy readability.

Parameters:
- `startDate` (str, optional): The start date of the period to include in the report.
- `endDate` (str, optional): The end date of the period to include in the report.

Process:
1. **Logger Setup**: Initializes a logger to track the process and any encountered errors during the report generation.
2. **SQL Connection**: Establishes a connection to the SQL database to retrieve the required data and execute queries.
3. **Employee Data Retrieval**: Queries the database for active employees who have billable and non-billable hours within the specified date range:
   - Retrieves data for the specified period and calculates the total hours, differentiating between billable and non-billable hours.
4. **Report Directory Creation**: 
   - Constructs a directory path to store the generated Excel file, ensuring the path follows the folder structure defined in the Django settings.
   - Clears any existing directory and creates a new folder to store the current report.
5. **Report Generation**:
   - Iterates through each employee's data and formats it according to predefined styles in the Excel template.
   - Ensures that specific formatting is applied, including titles, headers, subtotals, percentages, and grand totals.
6. **Excel File Creation**:
   - Uses the `xlsxwriter` library to create an Excel file with the formatted data, adding multiple sheets as necessary to organize the report.
7. **Return Path**: Returns the path to the folder where the generated report is stored.

Notes:
- **Error Handling**: Logs errors with detailed information to help with debugging.
- **Async Execution**: Uses asynchronous tasks to allow for concurrent report generation and processing, improving performance.
'''
def PayrollGenerator(start = None, end = None): 
    logger = setup_background_logger()
    try:
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
                Coalesce(eu.manager, 'Missing Manager Information'),
                Coalesce(at.status, 'NO SUBMISSION')
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
            current_dir = BASE_DIR
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
                worksheet.set_column(11, 11, 30)

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
                worksheet.merge_range(row,0,row+1,11 , 'BiWeekly Report - Clockify - Payroll', titleFormat)
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
                worksheet.write(row,11,'Status', columnNameFormat)
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
                            worksheet.write(row,11, '', totalFormat)
                            
                            i += 1
                            row+=1
                        if previousEmp is None or str(currentEmp[0]) != str(previousEmp[0]):
                            worksheet.merge_range(row,0,row,11, rowData[0], nameFormat, )
                            worksheet.merge_range(row+1,0,row+1,11, f'Reporting Manager: {rowData[9]}', managerFormat)
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
                            worksheet.write(row,11, rowData[10], missingFormat)
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
                            worksheet.write(row,11, rowData[10], textFormat)
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
                if float(totalsData[i][8]) not in (80, 50, 68) and str(previousEmp[1]) == 'Salary': 
                    worksheet.write(row,10,totalsData[i][8], highlightFormat)
                else: worksheet.write(row,10, totalsData[i][8], hlGreenFormat)
                worksheet.write(row,11, '', totalFormat)
                
                writer.close()
            # convertXlsxPdf(folder_path, file_path[:-5])

        return folder_path
    except Exception as e:
        logger.error(f'{e.__traceback__.tb_lineno} - {str(e)}')
    finally:
        cleanUp(conn, cursor)

'''
The `TimeStatusGenerator` asynchronous function generates a weekly report of employees' time entry statuses, categorizing them by approval status and formatting the data in an Excel file for easy reference.

Parameters:
- `start` (str, optional): The start date of the report period. Defaults to one week before the current week.
- `end` (str, optional): The end date of the report period. Defaults to the previous week.

Process:
1. **Logger Setup**: Initializes a logger to track the report generation process and record any errors.
2. **Date Range Calculation**: Determines the date range for each week within the specified period.
   - If `start` and `end` are not provided, it defaults to the previous week's Sunday-Saturday range.
3. **SQL Query Execution**: 
   - Connects to the SQL database and retrieves employee time statuses based on approval categories (`APPROVED`, `PENDING`, `NO TIME`, `NOT APPLICABLE`, `UNKNOWN STATUS`).
   - Groups data by each employee and their manager, focusing on active employees only.
4. **Report Directory Creation**:
   - Creates a directory path for storing the generated Excel files.
   - Clears any existing folder and generates a new folder for storing the weekly reports.
5. **Excel File Generation**:
   - Iterates over each weekly data set and creates a formatted Excel file using `xlsxwriter`.
   - Applies specific formatting styles for different sections: title, headers, and status legend.
   - Writes data to the worksheet, categorizing each employee's time entry status and adding explanatory notes.
6. **PDF Conversion**:
   - Converts each generated Excel report into a PDF using `convertXlsxPdf` for better sharing and readability.
7. **Return Path**: Returns the path to the folder containing the generated reports.

Notes:
- **Error Handling**: Logs errors with line number and exception details for easy troubleshooting.
- **Async Execution**: Uses asynchronous processes to manage data retrieval, report generation, and PDF conversion, ensuring efficiency in execution.
'''
def TimeStatusGenerator(start = None, end = None):
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
            current_dir = BASE_DIR
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

"""
Generates a LEM (Labor, Equipment, Material) spreadsheet in Excel format 
for a specified project and LEM ID. This function retrieves and organizes 
relevant data from SQL tables, formats the data into different sections, 
and saves the spreadsheet in a specified directory.

Parameters:
    projectCode (str): The code for the project associated with the LEM.
    lemId (str): The unique identifier for the LEM entry in the database.

Process:
    - Connects to a SQL database to retrieve LEM information, worker entries, 
        and equipment entries based on the given LEM ID.
    - Formats retrieved data, replacing null values as needed, and organizes 
        it into specific sections of the spreadsheet.
    - Creates a project directory if it does not exist and saves the Excel 
        file with a structured layout and formatted tables.

Sections:
    - Header Information: Includes client name, client representative, 
        project manager, date, and task description.
    - Worker Entries: Displays details of employees’ roles, hours worked, 
        travel hours, and other metrics.
    - Equipment Entries: Lists equipment used, quantities, rates, and costs.
    - Work Description: Describes work performed for the project.

Output:
    The generated Excel file is saved in a nested directory structure under 
    'Reports/LemSheets/{projectCode}/{lemId}', with the file name format 
    '{projectCode}-{lemId}.xlsx'.
    
Notes:
    - Logging is implemented to track query executions, folder creation, 
        and data writing progress.
    - Special formats are applied to header sections, column headers, text, 
        numeric cells, and date fields for readability.
"""
def LemGenerator( projectCode: str, lemId: str):
    logger = setup_background_logger()
    try:
        cursor, conn = sqlConnect()

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
        current_dir = BASE_DIR
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

"""
Generates a timesheet in Excel format for a specified project and date range, 
detailing work and equipment entries for each day within the range.

Parameters:
    projectId (str): The unique identifier of the project.
    startDate (str): The start date of the timesheet period in 'YYYY-MM-DD' format.
    endDate (str): The end date of the timesheet period in 'YYYY-MM-DD' format.

Process:
    - Connects to a SQL database and queries work entries and equipment entries 
    for the specified project within the date range.
    - Cleans data by replacing null values as needed, then organizes it into 
    work and equipment sections in the timesheet.
    - Generates an Excel file with distinct formatting for headers, columns, 
    dates, and values, as well as missing information highlights.

Sections:
    - Work Entries: Lists the date, role, work details, travel hours, meals, 
    and hotel entries associated with each worker.
    - Equipment Entries: Displays the equipment used, quantity, and rate type 
    for each day within the date range.

File Structure:
    - Creates a directory at 'Reports/LemSheets/Timesheets/{projectCode}' 
    if it doesn't exist.
    - Saves the generated Excel file with the format '{startDate} to {endDate}.xlsx'.

Output:
    - The file is saved in the designated directory, and its path is returned.
    - Additionally, the Excel file may be converted to a PDF for reporting purposes.

Notes:
    - Formats are applied to ensure readability, with distinct styles for 
    headers, missing data, and specific column types (e.g., dates, totals).
    - Data for each row is dynamically written, allowing multi-column merging 
    for select fields.
"""
def LemTimesheetGenerator(projectId, startDate,endDate ):
    cursor, conn = sqlConnect()
    query = f'''
        select ls.lem_sheet_date as "Date", lw.name as Role, r.name as "Role", 
            le.[work] as "Work", 
            le.Calc, 
            le.travel as 'Travel', 
            le.Meals,
            le.Hotel
        from LemEntry le 
        inner join LemSheet ls on ls.id = le.lemId
        Inner Join LemWorker lw on lw._id = le.workerId
        inner Join Role r on r.id = lw.roleId
        inner join Project p on p.id = ls.projectId
        where p.id = '{projectId}' and
        ls.lem_sheet_date between '{startDate}' and '{endDate}'
        order by ls.lem_sheet_date ;
    '''
    logger.debug(query)
    cursor.execute(query)
    workEntry = cursor.fetchall()
    workerColumns = [desc[0] for desc in cursor.description]
    query = f'''
        select ls.lem_sheet_date as 'Date', eu.name as 'Equipment', 
            ee.qty as "QTY",
            Case when ee.isUnitRate = 0 then 'Day'
            else 'Unit'
            end as 'Rate Type'
        from LemSheet ls 
        inner join EquipEntry ee on ee.lemId = ls.id
        Inner join Equipment eu on eu.id = ee.equipId 
        inner join Project p on p.id = ls.projectId
        where p.id = '{projectId}' and
        ls.lem_sheet_date between '{startDate}' and '{endDate}'
        order by ls.lem_sheet_date ;
    '''
    logger.debug(query)
    cursor.execute(query)
    equipEntry = cursor.fetchall()
    equipColumns = [desc[0] for desc in cursor.description]

    cursor.execute(f'''
                Select code from Project where id = '{projectId}'
                   ''')
    projectCode = cursor.fetchone()
    assert projectCode is not None  
    

    equipEntry = [['---' if val is None else val for val in row] for row in equipEntry]
    workEntry  = [['---' if val is None else val for val in row] for row in  workEntry]

    # Generate Folder for spreadsheets
    current_dir = BASE_DIR
    reports = 'Reports'
    lemSheet = 'LemSheets'
    payrollDir = 'Timesheets'
    folder_name = f"{projectCode[0]}"
    folder_path = os.path.join(current_dir,reports,lemSheet, payrollDir,  folder_name)
    logger.debug(f'Created Folder at {folder_path}')
    if not os.path.exists(folder_path):
        os.makedirs(folder_path )
    file_path = os.path.join(folder_path, f"{startDate} to {endDate}.xlsx")

    

    with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
        #Generate file and initilize writers and formats 
        workbook = writer.book
        worksheet = workbook.add_worksheet("Hill Plain - LEM")
        writer.sheets['Hill Plain - Payroll'] = worksheet 
        
        row = 0 #initilize row pointer 
        
    #formats 
        titleFormat = workbook.add_format({'bold': True, 'align': 'center'})
        titleFormat.set_font_size(20)
        titleFormat.set_bg_color('#D9D9D9')
        #file Heaaders
        headerFormat = workbook.add_format({'bold': True, "italic": True, "align": 'right', 'valign': 'vcenter'})
        headerValueFormat = workbook.add_format({'italic': True,'align': 'left', 'text_wrap': True, 'valign':'vcenter',  'num_format': 'yyyy-mm-dd'})
        #columnNameFormat 
        columnNameFormat = workbook.add_format({'bold': True, 'num_format': 'yyyy-mm-dd', 'align': 'center'})
        columnNameFormat.set_border(1)
        columnNameFormat.set_bg_color('#808080')
        columnNameFormat.set_font_color('#ffffff')
        # Text Data Format 
        textFormat = workbook.add_format({'text_wrap': True, "align": 'center', 'valign': 'vcenter'})
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
        dateFormat = workbook.add_format({'num_format': 'yyyy-mm-dd', "align": 'center', 'valign': 'vcenter'})
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
        worksheet.merge_range(row,0,row+1,10 , f'LEM Timesheet - {projectCode[0]}', titleFormat)
        row += 2
        headers = {
                'Generated on:': time.now(),
                'Date Range Start:': startDate,
                'Date Range End:': endDate
            }
        for key, value in headers.items():
            worksheet.merge_range(row,0,row+1, 1, key, headerFormat)
            worksheet.merge_range(row,2,row+1,4, value, headerValueFormat)
            row += 2

        logger.debug(row)
        row += 1
        logger.debug(row)
        worksheet.insert_image("J3",
            # r"C:\Users\TimmyIfidon\Desktop\Docs and Projects\Hill Plain Logo New (May2023)\PNG\Hill Plain Logo - NEW (colour).png",
            # {'x_scale': 0.04, 'y_scale': 0.04}
            r"C:\Users\Script\Desktop\unnamed.png",
            {'x_scale': 0.5, 'y_scale': 0.5}
        )
    #columns 
        column = 0
        right = 0
        for i  , value in enumerate(workerColumns):
            if column > right: right = column
            if i in (0,1,2): #name or Role 
                worksheet.merge_range(row,column, row, column +1, value, columnNameFormat)
                column += 2
            else: 
                worksheet.write(row,column, value , columnNameFormat)
                column += 1
        row += 1
        column = 0
        for rowData in workEntry:
            
            for i, data in enumerate(rowData):
                if i in (1,2):
                    worksheet.merge_range(row,column, row+1, column +1, data, textFormat)
                    column += 2
                elif i == 0:
                    worksheet.merge_range(row, column,row+1, column + 1, data, dateFormat )
                    column +=2
                else:
                    worksheet.merge_range(row, column,row+1, column, data, textFormat )
                    column +=1
            # if row in range(48, 4800,48):
            #     row += 4 #page break
            # else: row += 2
            row += 2
            column = 0

        column = 0
        row +=2
        for i  , value in enumerate(equipColumns):
            if i in (0,1): #name 
                worksheet.merge_range(row,column, row, column +1, value, columnNameFormat)
                column += 2
            else: 
                worksheet.write(row,column, value , columnNameFormat)
                column += 1
        row += 1
        column = 0
        for rowData in equipEntry:
            for i, data in enumerate(rowData):
                if i ==1:
                    worksheet.merge_range(row,column, row+1, column +1, data, textFormat)
                    column += 2
                elif i == 0:
                    worksheet.merge_range(row, column,row+1, column + 1, data, dateFormat )
                    column +=2
                else:
                    worksheet.merge_range(row, column,row+1, column, data, textFormat )
                    column +=1
            # if row in range(48, 4800,48):
            #     row += 4 #page break
            # else: row += 2
            row += 2
            column = 0

        

        writer.close()
    
    convertXlsxPdf(folder_path, file_path)
    return folder_path



# def main():
#     BillableReportGenerate('07','24')
#     # MonthylyProjReport('2024-02-25', '2024-03-24')
   

# if __name__ == "__main__": 
#     main()