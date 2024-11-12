from django.shortcuts import render
from ..HillPlainAPI.Loggers import setup_server_logger
from ..Utilities.views import download_text_file
from .util import *
from django.http import  HttpResponse
from rest_framework.decorators import api_view
from django.core.handlers.asgi import ASGIRequest

"""
Function: billableReport

Description:
This asynchronous function generates a billable report based on optional month, year, 
and project code (pCode) parameters. The report's data is logged, processed, and 
then made available for download as a text file.

Parameters:
- request: The HTTP request object.
- month (optional): Specifies the month for the report. Default is None.
- year (optional): Specifies the year for the report. Default is None.
- pCode (optional): Specifies the project code to filter the report by project. Default is None.

Workflow:
1. Logging: Initializes a server logger with setup_server_logger(), then logs the call 
   to billableReport, including details about the month and year.
2. Report Generation: Calls BillingReportCaller() asynchronously with the given parameters 
   (month, year, pCode). BillingReportCaller() is expected to return the path of the generated report file.
3. File Download: Returns the generated report file as a downloadable text file using download_text_file().

Returns:
- A response to download the text file at the location folder_path, which holds the generated report.
"""
async def BillableReport(request, month=None, year=None, pCode=None):
    logger = setup_server_logger()
    logger.info(f'BillableReport Called for {month}-{year}')
    folder_path = await BillingReportCaller(month=month, year=year, pCode=pCode)
    return download_text_file(folder_path)

"""
Function: billableReportCustom

Description:
This asynchronous function generates a customized billable report based on a specified 
start date, end date, and optional project code (pCode). The function logs the call with 
details of the provided dates and then processes the request, returning a downloadable 
text file with the report.

Parameters:
- request: The HTTP request object.
- start (optional): The start date for the report. Default is None.
- end (optional): The end date for the report. Default is None.
- pCode (optional): Specifies the project code to filter the report by project. Default is None.

Workflow:
1. Logging: Initializes a server logger using setup_server_logger() and logs the call 
   to billableReportCustom with start and end date details.
2. Report Generation: Calls BillingReportCaller() asynchronously with the specified start, 
   end, and pCode parameters, which generates the report and returns the path to the report file.
3. File Download: Uses download_text_file() to provide the generated report file as a downloadable text file.

Returns:
- A response to download the text file located at folder_path, containing the generated report data.
"""
async def BillableReportCustom(request, start= None, end = None, pCode= None):
    logger = setup_server_logger()
    logger.info(f'BillableReport Called for {start}-{end}')
    folder_path = await BillingReportCaller(start= start, end= end, pCode = pCode)
    return download_text_file(folder_path)

"""
Function: weeklyPayrollReport

Description:
This function handles GET requests to generate a weekly payroll report for a specified 
date range. The function logs the report request, generates the payroll data based on the 
start and end dates provided, and then returns the report as a downloadable text file.

Parameters:
- request: The HTTP request object.
- start_date (optional): The start date for the payroll report. Default is None.
- end_date (optional): The end date for the payroll report. Default is None.

Workflow:
1. Logging: Initializes a server logger with setup_server_logger() and logs the 
   initiation of the weekly payroll report generation.
2. Report Generation: Calls weeklyPayroll() with start_date and end_date to generate 
   the payroll report and stores the file path.
3. File Download: Uses download_text_file() to provide the generated payroll report file 
   as a downloadable text file.

Returns:
- A response to download the text file located at folder_path, containing the weekly payroll report data.
"""
@api_view(['GET'])
def WeeklyPayrollReport(request, start_date=None, end_date= None):
    logger = setup_server_logger()
    logger.info(f'Weekly Payroll Report Called')
    # return JsonResponse(data= 'Service disabled for maitenance.', status = status.HTTP_204_NO_CONTENT, safe=False)
    folder_path = WeeklyPayrollCaller(start_date, end_date )
    return download_text_file(folder_path)

"""
Function: TimeStatusEvent

Description:
This function handles GET requests to generate a time status report based on events 
within a specified date range. It logs the request, calls a function to generate 
the report data, and returns the report as a downloadable text file.

Parameters:
- request: The HTTP request object.
- start_date (optional): The start date for the time status report. Default is None.
- end_date (optional): The end date for the time status report. Default is None.

Workflow:
1. Logging: Initializes a server logger with setup_server_logger() and logs the initiation 
   of the time status report generation.
2. Report Generation: Calls TimeStatusCaller() with start_date and end_date to generate the 
   report and stores the file path.
3. File Download: Uses download_text_file() to provide the generated report as a downloadable 
   text file.

Returns:
- A response to download the text file located at folder_path, containing the time status event data.
"""
@api_view(['GET'])
def TimeStatusEvent(request, start_date=None, end_date= None):
    logger = setup_server_logger()
    logger.info(f'Weekly Payroll Report Called')
    folder_path = TimeStatusCaller(start_date, end_date )
    return download_text_file(folder_path)

"""
Function: viewServerLog

Description:
This function provides an endpoint to view the server log file. It retrieves the last 
5,000 lines from the log file, reverses their order (to display the most recent logs first), 
and returns them as a JSON-formatted response. If the log file is not found, it returns 
a 404 status with an appropriate message.

Parameters:
- request: The HTTP request object.

Workflow:
1. Log File Path: Constructs the file path to the server log using settings.LOGS_DIR.
2. File Check: Verifies if the log file exists at the specified path.
   - If the file exists:
      a. Opens and reads all lines from the log file.
      b. Extracts the last 5,000 lines.
      c. Reverses the order of the lines to show the latest entries first.
      d. Joins the reversed lines into a single string.
      e. Returns the log contents as an HTTP response in JSON format.
   - If the file does not exist:
      a. Returns an HTTP 404 response with a "logger file not found" message.

Returns:
- An HTTP response with the log contents (if available) in JSON format.
- An HTTP 404 response if the log file is not found.
"""
@api_view(['GET'])
def ViewServerLog(request):
    log_file_path = os.path.join(settings.LOGS_DIR, 'ServerLog.log')  # Update with the path to your logger file
    if os.path.exists(log_file_path):
        with open(log_file_path, 'r') as file:
            # Read all lines from the file
            lines = file.readlines()
            # Extract the last 1000 lines
            last_1000_lines = lines[-5000:]
            # Reverse the order of the lines
            reversed_lines = reversed(last_1000_lines)
            # Join the lines into a single string
            log_contents = ''.join(reversed_lines)
        return HttpResponse(log_contents, content_type='application/json')
    else:
        return HttpResponse('logger file not found', status=404)

"""
Function: viewTaskLog

Description:
This function serves as an endpoint to view logs specifically for background tasks. It reads 
the last 10,000 lines of the log file (if available) to provide insight into recent task activities. 
The lines are returned in reverse order to display the latest entries first. If the log file 
is missing, a 404 response is returned with an appropriate message.

Parameters:
- request: The HTTP request object.

Workflow:
1. Log File Path: Constructs the file path for the background tasks log using settings.LOGS_DIR.
2. File Check: Verifies if the specified log file exists at the given path.
   - If the file exists:
      a. Opens the file and reads all lines.
      b. Extracts the last 10,000 lines from the log file.
      c. Reverses the line order to display the latest entries at the top.
      d. Joins the lines into a single string.
      e. Returns the log contents as an HTTP response in JSON format.
   - If the file does not exist:
      a. Returns an HTTP 404 response with the message "logger file not found."

Returns:
- An HTTP response with the log contents (if available) in JSON format.
- An HTTP 404 response if the log file is not found.
"""
@api_view(['GET'])
def ViewTaskLog(request):
    log_file_path = os.path.join(settings.LOGS_DIR, 'BackgroundTasksLog.log')  # Update with the path to your logger file
    if os.path.exists(log_file_path):
        with open(log_file_path, 'r') as file:
            # Read all lines from the file
            lines = file.readlines()
            # Extract the last 1000 lines
            last_1000_lines = lines[-10000:]
            # Reverse the order of the lines
            reversed_lines = reversed(last_1000_lines)
            # Join the lines into a single string
            log_contents = ''.join(reversed_lines)
        return HttpResponse(log_contents, content_type='application/json')
    else:
        return HttpResponse('logger file not found', status=404)

"""
Function: GenerateLemView

Description:
This function acts as an API endpoint to generate a LEM (Labour, Equipment, and Materials) report 
based on a specific project code and LEM ID. It logs the request details and generates the report 
using the `GenerateLem` function, then provides the generated report as a downloadable file.

Parameters:
- reqiest: An ASGIRequest object representing the HTTP request.
- projectCode (optional): A string representing the unique project code associated with the LEM report.
- lemId (optional): A string representing the unique identifier for the specific LEM report to generate.

Workflow:
1. Logger Initialization:
   - Initializes a logger to record request details for debugging and audit purposes.
2. Log the Request:
   - Logs an informational message indicating the project code and LEM ID for which the report generation 
     has been requested.
3. Generate Report:
   - Calls `GenerateLem` with the provided project code and LEM ID, which returns the file path to the 
     generated report.
4. Download File:
   - Uses `download_text_file` to send the generated report as an HTTP response, enabling the user to 
     download the report.

Returns:
- An HTTP response containing the generated report file for download.
"""
@api_view(['GET'])
def GenerateLemView(reqiest:ASGIRequest, projectCode = None, lemId = None):
    logger = setup_server_logger()
    logger.info(f'Lem Generate for {projectCode} Report Called: {lemId}')
    folder_path = LemGenerator(projectCode, lemId )
    return download_text_file(folder_path)

"""
Function: lemTimesheetsView

Description:
This function serves as an API endpoint to generate timesheet data for a specified project within a date range.
It constructs a start and end date string based on the input parameters, then generates the timesheet report 
using the `GenerateTimeSheetLem` function and returns the report as a downloadable file.

Parameters:
- request: An ASGIRequest object representing the incoming HTTP request.
- projectId: A string or integer representing the unique identifier of the project for which the timesheet 
  report is generated.
- startMonth, startDay, startYear: Integers representing the starting date (month, day, and year) of the report period.
- endMonth, endDay, endYear: Integers representing the ending date (month, day, and year) of the report period.

Workflow:
1. Construct Start and End Dates:
   - Builds `startDate` and `endDate` strings in the format 'YYYY-MM-DD' by combining the year, month, 
     and day inputs, padding month and day with zeros if necessary.
2. Generate Timesheet Report:
   - Calls `GenerateTimeSheetLem` with the `projectId`, `startDate`, and `endDate` to generate a timesheet 
     report for the specified project and date range.
3. Download File:
   - Uses `download_text_file` to send the generated report as an HTTP response for the user to download.

Returns:
- An HTTP response containing the generated timesheet report file for download.
"""
def LemTimesheetsView(request: ASGIRequest, projectId, startMonth, startDay,startYear, endMonth, endDay, endYear):
    startDate = str(startYear) + '-' + str(startMonth).zfill(2) +'-' + str(startDay).zfill(2)
    endDate = str(endYear) + '-' + str(endMonth).zfill(2) +'-' + str(endDay).zfill(2)
    folder_path = LemTimesheetGenerator(projectId, startDate, endDate)
    return download_text_file(folder_path)

"""
Function: billableNonBillable

Description:
This function serves as an API endpoint to generate a report comparing billable and non-billable work 
for a specified date range. It logs the request, generates the report by calling `NonBillableReport`, 
and returns the report as a downloadable file.

Parameters:
- reqiest: An ASGIRequest object representing the incoming HTTP request.
- start_date: A string representing the start date of the report period (optional).
- end_date: A string representing the end date of the report period (optional).

Workflow:
1. Log the Report Request:
   - Initializes the server logger and logs that the Billable vs. Non-billable report was requested.
2. Generate Report:
   - Calls `NonBillableReport` with `start_date` and `end_date` to generate a report for the specified 
     date range, which includes both billable and non-billable work details.
3. Download File:
   - Uses `download_text_file` to return the generated report as an HTTP response for user download.

Returns:
- An HTTP response containing the generated billable vs. non-billable report file for download.
"""
@api_view(['GET'])
def BillableNonBillable(reqiest:ASGIRequest, start_date = None, end_date = None):
    logger = setup_server_logger()
    logger.info(f'Billable vs. Non billable Report Called')
    folder_path = NonBillableReportCaller(start_date, end_date )
    return download_text_file(folder_path)
