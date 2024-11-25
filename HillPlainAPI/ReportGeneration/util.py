from .sqlDataFormatter import *
from Utilities.views import getMonthYear

"""
Function: BillingReportCaller

Description:
This asynchronous function generates a billing report based on a specified date range. 
It allows for either an automatic date range based on month and year or a custom 
date range using start and end dates. The function validates input, calculates date 
ranges if necessary, and calls a report generation function.

Parameters:
- month: The month (in numeric format or abbreviation) for which the billing report 
  is generated. Used if start and end dates are not provided.
- year: The year (in two-digit format) associated with the `month` for the report.
- pCode: The project code for which the billing report is generated.
- start: Custom start date for the billing period, in 'YYYY-MM-DD' format.
- end: Custom end date for the billing period, in 'YYYY-MM-DD' format.

Workflow:
1. Input Validation:
   - Ensures that either the month/year or start/end date is provided, but not both.
2. Date Range Calculation:
   - If `start` and `end` are not provided, calculates a date range using the provided
     or current month and year.
   - Adjusts the end date to the most recent Saturday and the start date to the most 
     recent Sunday for accurate monthly ranges.
3. Billing Report Generation:
   - Calls `BillableReportGenerate` asynchronously with the calculated or provided 
     start and end dates, along with the project code.
4. Logging:
   - Logs the generated file path and any relevant information.

Returns:
- file_path: The file path of the generated billing report.

Raises:
- Exception: If both date range and month/year inputs are provided simultaneously.
"""
async def BillingReportCaller(month= None, year = None, pCode = None, start=None, end = None):
    #obtain date range for this month 
    if((month is not None or year is not None) and (start is not None or end is not None)):
        raise Exception("Invalid Arguments on billingReport function")
    if(start is None and end is None):
        # Auto format dates. Either get current or format from input Abbriviation string
        if month is None or year is None:
            month, year = getMonthYear()
        else:
            month = getAbbreviation(month, reverse=True)
        logger.info(f'Biling Report Generating for - {month}-{year}')

        if int(month)-1 == 0: 
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
        else: startDate = f'20{previousYear}-{previousMonth}-25'
        logger.debug(f'Date Range: {startDate}-{endDate}')
    else: # custom format 
        startDate = start 
        endDate = end

    file_path = await BillableReportGenerate(startDate, endDate, pCode )
    logger.info(f"{file_path}")
    return file_path 

"""
Function: NonBillableReportCaller

Description:
This function generates a report for non-billable and billable work hours over a specified date range.
If no `start` or `end` dates are provided, it defaults to the most recent full week 
(from Sunday to Saturday).

Parameters:
- start: (Optional) The start date of the reporting period, formatted as 'YYYY-MM-DD'.
- end: (Optional) The end date of the reporting period, formatted as 'YYYY-MM-DD'.

Workflow:
1. Default Date Calculation:
   - If `start` or `end` is not provided, calculates a date range for the last complete week.
   - Determines the start date as the previous Sunday and the end date as the following Saturday.
2. Report Generation:
   - Calls `NonBillableReportGen` to generate the report for the specified date range.
3. Logging:
   - Logs the date range used and the file path of the generated report.

Returns:
- file_path: The file path to the generated non-billable report file.
"""
def NonBillableReportCaller(start = None, end = None):
    if start is None or end is None:
        start = (datetime.now() - timedelta(days = (7 + datetime.now().weekday() + 1))).strftime('%Y-%m-%d') # find sunday start time 
        end =   (datetime.now() - timedelta(days = (2 + datetime.now().weekday()))).strftime('%Y-%m-%d') #find saturday 
    logger.info(f'Biling Report Generating for - {start}-{end}')
    file_path = NonBillableReportGen(start, end)
    logger.info(f" {file_path}")
    return file_path

"""
Function: WeeklyPayrollCaller

Description:
Generates a payroll report over a specified date range. If `start_date` and `end_date`
are not provided, it defaults to the most recent two-week period ending on Saturday.

Parameters:
    - start_date: (Optional) The start date of the payroll period, formatted as 'YYYY-MM-DD'.
     defaults to the sunday 2 weeks prior
    - end_date: (Optional) The end date of the payroll period, formatted as 'YYYY-MM-DD'.
     defaults to the most recent saturday

Workflow:
1. Default Date Calculation:
   - If `start_date` or `end_date` is not provided, the function calculates a two-week
     date range from the last complete Saturday.
   - `start_date` is set to the Sunday of the week prior to the last full week (14 days back).
   - `end_date` is set to the most recent Saturday.
2. Report Generation:
   - Calls `PayrollGenerator` to generate the payroll report for the specified date range.
3. Logging:
   - Logs the date range used and the file path of the generated payroll report.

Returns:
- file_path: The file path to the generated payroll report file.
"""
def WeeklyPayrollCaller(start_date=None, end_date=None):
    if start_date is None or end_date is None:
        start_date = (datetime.now() - timedelta(days=(14 + datetime.now().weekday() + 1))).strftime('%Y-%m-%d')  # Find Sunday of two weeks ago
        end_date = (datetime.now() - timedelta(days=(2 + datetime.now().weekday()))).strftime('%Y-%m-%d')  # Find last Saturday
    
    logger.info(f'Billing Report Generating for - {start_date}-{end_date}')
    file_path = PayrollGenerator(start_date, end_date)
    logger.info(f"{file_path}")
    return file_path

"""
Generates a time status report for a specified date range or the last full week by default.

Parameters:
    start_date (str, optional): The start date of the report range in 'YYYY-MM-DD' format. 
     Defaults to the most recent Sunday of the last full week if not provided.
    end_date (str, optional): The end date of the report range in 'YYYY-MM-DD' format. 
     Defaults to the most recent Saturday of the last full week if not provided.

Returns:
    str: The file path of the generated time status report.

Description:
    This function calculates a default date range if none is provided, setting `start_date` 
    to the Sunday of the last full week and `end_date` to the following Saturday.
    If a custom `start_date` is provided, it adjusts to the previous Sunday to create 
    a full weekly range. It then generates a time status report for the specified range
    by calling `TimeStatusGenerator` and logs the file path of the generated report.
"""
def TimeStatusCaller(start_date=None, end_date=None):
    # Set default date range to last complete week if no dates provided
    if start_date is None or end_date is None:
        start_date = (datetime.now() - timedelta(days=(7 + datetime.now().weekday() + 1))).strftime('%Y-%m-%d')  # Find Sunday start time
        end_date = (datetime.now() - timedelta(days=(2 + datetime.now().weekday()))).strftime('%Y-%m-%d')  # Find last Saturday
    else:
        start_date = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=1 + datetime.strptime(start_date, '%Y-%m-%d').weekday())).strftime('%Y-%m-%d')    

    file_path = TimeStatusGenerator(start_date, end_date)
    logger.info(f"{file_path}")
    return file_path
    

