from sqlDataFormatter import *


async def billingReport(month= None, year = None, pCode = None, start=None, end = None):
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

        if int(month) -1 == 0: 
            previousMonth = '12'
            previousYear = str(int(year) - 1).rjust(2, '0')
        else: 
            previousMonth = str(int(month) -1 ).rjust(2, '0')
            previousYear = year

    #format date strings
        endDateObj = datetime.datetime.strptime(f'20{year}-{month}-25', '%Y-%m-%d')
        startDateObj = datetime.datetime.strptime(f'20{previousYear}-{previousMonth}-25', '%Y-%m-%d')
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

def NonBillableReport(start = None, end = None):
    file_path = NonBillableReportGen(start, end)
    logger.info(f" {file_path}")
    return file_path

    
def weeklyPayroll(start_date = None, end_date = None):
    file_path = Payroll(start_date, end_date)
    logger.info(f" {file_path}")
    return file_path

def TimeStatusCaller(start_date = None, end_date = None):
    file_path = TimeStatus(start_date, end_date)
    logger.info(f" {file_path}")
    return file_path

def GenerateLem(projectCode,lemId):
    file_path = lemGenerator(projectCode, lemId)
    logger.info(f" {file_path}")
    return file_path
    
def GenerateTimeSheetLem(projectId, startDate, endDate):
    file_path = lemTimesheet(projectId, startDate,endDate )
    logger.info(f" {file_path}")
    return file_path
