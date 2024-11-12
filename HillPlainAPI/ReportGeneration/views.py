from django.shortcuts import render
from ..HillPlainAPI.Loggers import setup_server_logger
from ..Utilities.views import download_text_file
from .util import *
from django.http import  HttpResponse
from rest_framework.decorators import api_view
from django.core.handlers.asgi import ASGIRequest


async def billableReport(request, month= None, year = None, pCode= None):
    logger = setup_server_logger()
    logger.info(f'BillableReport Called for {month}-{year}')
    folder_path = await billingReport(month=month, year=year, pCode=pCode )
    return download_text_file(folder_path)

async def billableReportCustom(request, start= None, end = None, pCode= None):
    logger = setup_server_logger()
    logger.info(f'BillableReport Called for {start}-{end}')
    folder_path = await billingReport(start= start, end= end, pCode = pCode)
    return download_text_file(folder_path)


@api_view(['GET'])
def weeklyPayrollReport(request, start_date=None, end_date= None):
    '''
    Function Description: 
       Calls format function to build the payroll report based on the information in the database. Default values when no start and end date is given 
       are taken as the current month. Otherwise start_date and end_date are specified in the URL in the YYYY-MM-DD format.

       In future versions create a form web submission where the start date and end date can be passed as input and not part of the endpoint url 
    Param: 
        request(ASGIRequest): Request sent to endpoint from client 
    
    Returns: 
        response(Response): contains Payroll Report File to be directly uploaded into ACC
    '''
    logger = setup_server_logger()
    logger.info(f'Weekly Payroll Report Called')
    # return JsonResponse(data= 'Service disabled for maitenance.', status = status.HTTP_204_NO_CONTENT, safe=False)
    folder_path = weeklyPayroll(start_date, end_date )
    return download_text_file(folder_path)

@api_view(['GET'])
def TimeStatusEvent(request, start_date=None, end_date= None):
    '''
    Function Description: 
       Calls format function to build the payroll report based on the information in the database. Default values when no start and end date is given 
       are taken as the current month. Otherwise start_date and end_date are specified in the URL in the YYYY-MM-DD format.

       In future versions create a form web submission where the start date and end date can be passed as input and not part of the endpoint url 
    Param: 
        request(ASGIRequest): Request sent to endpoint from client 
    
    Returns: 
        response(Response): contains Payroll Report File to be directly uploaded into ACC
    '''
    logger = setup_server_logger()
    logger.info(f'Weekly Payroll Report Called')
    folder_path = TimeStatusCaller(start_date, end_date )
    return download_text_file(folder_path)

@api_view(['GET'])
def viewServerLog(request):
    '''
    Function Description: 
       Displays Server log file through the browser.

       In future versions impliment a submission form to have the user log in. This data should not be completly public as it contains all the data passed 
       to the database 
    Param: 
        request(ASGIRequest): Request sent to endpoint from client 
    
    Returns: 
        response(Response): 
    '''
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

@api_view(['GET'])
def viewTaskLog(request):
    '''
    Function Description: 
       Displays Server log file through the browser.

       In future versions impliment a submission form to have the user log in. This data should not be completly public as it contains all the data passed 
       to the database 
    Param: 
        request(ASGIRequest): Request sent to endpoint from client 
    
    Returns: 
        response(Response): 
    '''
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


@api_view(['GET'])
def GenerateLemView(reqiest:ASGIRequest, projectCode = None, lemId = None):
    logger = setup_server_logger()
    logger.info(f'Lem Generate for {projectCode} Report Called: {lemId}')
    folder_path = GenerateLem(projectCode, lemId )
    return download_text_file(folder_path)

def lemTimesheetsView(request: ASGIRequest, projectId, startMonth, startDay,startYear, endMonth, endDay, endYear):
    startDate = str(startYear) + '-' + str(startMonth).zfill(2) +'-' + str(startDay).zfill(2)
    endDate = str(endYear) + '-' + str(endMonth).zfill(2) +'-' + str(endDay).zfill(2)
    folder_path = GenerateTimeSheetLem(projectId, startDate, endDate)
    return download_text_file(folder_path)


@api_view(['GET'])
def billableNonBillable(reqiest:ASGIRequest, start_date = None, end_date = None):
    logger = setup_server_logger()
    logger.info(f'Billable vs. Non billable Report Called')
    folder_path = NonBillableReport(start_date, end_date )
    return download_text_file(folder_path)
