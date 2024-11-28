from . import ClockifyPullV3
from . import ClockifyPushV3
from HillPlainAPI.Loggers import setup_background_logger
from Utilities.views import sqlConnect
import time
from ..views import reverseForOutput
from requests import patch

'''
Fetches user balances from the BankedTimeOffPolicy table in the database.

Args:
    conn (pyodbc.Connection): The database connection object.
    cursor (pyodbc.Cursor): The cursor object for executing SQL queries.

Returns:
    tuple: A dictionary containing user balances with user IDs as keys and balances as values,
           along with the last policy ID retrieved.

Raises:
    Exception: Logs and re-raises any exception encountered during database operations.
    
Process:
    - Executes a SQL query to select the `id`, `polID`, and `balance` fields from the 
      `BankedTimeOffPolicy` table.
    - Iterates through the results to construct a dictionary (`usrBalances`) where the user ID 
      (`id`) is the key and `balance` is the value.
    - Logs detailed error information if an exception occurs, including traceback details.
    - Logs the status on successful execution and returns `usrBalances` and the last retrieved `polID`.
'''
def getUsrBallances(conn, cursor):
    logger = setup_background_logger('DEBUG')
    try:
        cursor.execute(
            '''
            select id, polID, balance from BankedTimeOffPolicy
            '''
        )
        results = cursor.fetchall()
        if results is not None:
            usrBalances = dict()
            for result in results :
                usrBalances[result[0]] = result[2]

        else:
            return dict()
    except Exception as  exc:
        # Roll back changes if an exception occurs
        conn.rollback()
        logger.error(f"({exc.__class__}): \n----------{exc.__traceback__.tb_frame.f_code.co_filename}, {exc.__traceback__.tb_frame.f_code.co_name} \n\tLine: {exc.__traceback__.tb_lineno} \n----------{str(exc)}\n")
        raise
    else:
        logger.info(" Checking User Balances")
        return usrBalances, result[1]
       

def checkBalanceUpdate(usrBalances, polID, page):
    logger = setup_background_logger('DEBUG')
    try:
        wid = ClockifyPushV3.getWID('Hill Plain')
        url = f"https://pto.api.clockify.me/v1/workspaces/{wid}/balance/policy/{polID}?page-size=100&page={page}"
        headers = {
            'X-Api-Key': ClockifyPullV3.getApiKey()
        }
        response = ClockifyPullV3.requests.get(url, headers=headers)
        if response.status_code == 200:
            updateBalances = dict()
            for balance in response.json()['balances']:
                if balance['userId'] in usrBalances.keys():
                    if usrBalances[balance['userId']] != balance['balance']:
                        updateBalances[balance['userId']] = [usrBalances[balance['userId']], balance['balance']]
                else:
                    continue
    except Exception as  exc:
        # Roll back changes if an exception occurs
        logger.error(f"({exc.__class__}): \n----------{exc.__traceback__.tb_frame.f_code.co_filename}, {exc.__traceback__.tb_frame.f_code.co_name} \n\tLine: {exc.__traceback__.tb_lineno} \n----------{str(exc)}\n")
        raise
    else:
        logger.info(reverseForOutput(updateBalances))
        logger.info(f"Updating User Balances: {{Employee ID: [New Balance, Old Balance]}}, updateBalances")
        return updateBalances
    
'''
Checks and logs balance updates for users in a specified policy by comparing stored balances 
with the balances retrieved from the Clockify API.

Args:
    usrBalances (dict): A dictionary of user balances from the database with user IDs as keys and 
                        their current balance as values.
    polID (str): The policy ID for which balance updates need to be checked.
    page (int): The page number to request in the paginated Clockify API response.

Returns:
    dict: A dictionary of users with updated balances, where each key is a user ID, 
          and the value is a list containing the previous and updated balance.

Raises:
    Exception: Logs and re-raises any exception encountered during the HTTP request 
               or data processing.

Process:
    - Retrieves the workspace ID using the `getWID` function for the 'Hill Plain' workspace.
    - Constructs the API endpoint URL to fetch the current balance data from Clockify.
    - Sends a GET request to the API with required headers.
    - If the response is successful (status code 200), compares each user's balance with 
      their stored balance in `usrBalances`.
    - Updates `updateBalances` with users whose balances have changed.
    - Logs detailed error information in case of exceptions, including traceback details.
    - Logs and returns the updated balances.
'''
def updateUsrBalances(updateBalances, polID):
    logger = setup_background_logger('DEBUG')
    try:
        wid = ClockifyPushV3.getWID('Hill Plain')
        url = f"https://pto.api.clockify.me/v1/workspaces/{wid}/balance/policy/{polID}"
        for id in updateBalances.keys():
            value = updateBalances[id][0] - updateBalances[id][1]
            headers = {
                "X-Api-Key": ClockifyPullV3.getApiKey(),
                'Content-Type': 'application/json',
            }
            request = {
                "note": "Updating banked hours with database records",
                "userIds": [id],
                "value": value
            }
            response = ClockifyPullV3.requests.patch(url, headers = headers, json= request)
            if response.status_code != 204:
                raise Exception(f"Failed to update balance for user {id}: {response.reason}")
    except Exception as  exc:
        # Roll back changes if an exception occurs
        logger.error(f"({exc.__class__}): \n----------{exc.__traceback__.tb_frame.f_code.co_filename}, {exc.__traceback__.tb_frame.f_code.co_name} \n\tLine: {exc.__traceback__.tb_lineno} \n----------{str(exc)}\n")
        raise
    else:
        logger.info('Updated Banked Time')

'''
Updates the vacation balance for a salaried user by calculating their accrued vacation time 
and posting the updated balance to the Clockify API.

Args:
    userId (str): The ID of the user whose vacation balance is to be updated.
    cursor (pyodbc.Cursor): Database cursor for executing SQL queries.

Process:
    - Constructs a query that calculates accrued vacation time (`Accrual`) for the user based 
      on their employment start date and total approved vacation time used.
    - Executes the query and retrieves the user's current balance, ID, name, used vacation, 
      and accrual.
    - Prepares an API request payload to update the user's vacation balance in Clockify, 
      including a weekly accrual value.
    - Sends the updated balance to the Clockify API.
    - Logs and returns a success status based on the response from the Clockify API.

Returns:
    bool: True if the update was successful (status code 204), otherwise False.

Raises:
    Logs errors to the background logger if the API request fails.
'''
def updateSalaryVacation(userId, cursor):
    query = f'''
        SET DATEFIRST 7;
        with TotalAcrued as (
            Select 
                eu.id,
                eu.name,
                eu.start_date,
                DATEDIFF(
                            DAY, eu.start_date, DATEADD(
                                DAY, -1 * (DATEPART(WEEKDAY, GETDATE()) ) % 7, GETDATE()
                            )
                        ) 
                AS [Days Employeed],
                Case when DATEPART(year,eu.start_date ) = '2024' then 
                    Convert(Real,
                        DATEDIFF(
                            DAY, eu.start_date, DATEADD(
                                DAY, -1 * (DATEPART(WEEKDAY, GETDATE()) ) % 7, GETDATE()
                            )
                        ) 
                    )* 0.44
                else 
                    Convert(REAL,
                        DATEDIFF(
                            day, Concat(Convert(VARCHAR, YEAR(GETDATE())), '-01-01'), DATEADD(
                                DAY, -1 * (DATEPART(WEEKDAY, GETDATE()) ) % 7, GETDATE()
                            )
                        )
                    ) * 0.44
                end as Accrual
            from EmployeeUser eu
            where eu.hourly = 0 and eu.status = 'ACTIVE'
        ),
        totalVacationSalary as (
            Select 
                eu.id,
                eu.name,
                Sum(tr.paidTimeOff) as Used,
                tp.policy_name
            From TimeOffRequests tr 
            inner join TimeOffPolicies tp on tp.id = tr.pID
            inner join EmployeeUser eu on eu.id = tr.eID
            where tp.policy_name = 'Vacation - Salary' and eu.[status] = 'ACTIVE'
            and tr.[status] = 'APPROVED'
            group by eu.name, tp.policy_name, eu.id
        )
        SELECT 
            ta.Accrual - Coalesce(tv.Used, 0) as Balance,
            ta.id,
            ta.name, 
            tv.Used, 
            ta.Accrual
        From TotalAcrued ta 
        Left join totalVacationSalary as tv on tv.id= ta.id 
            where ta.id = '{userId}'
    '''
    logger = setup_background_logger()
    try:
        cursor.execute(query)
        balance = cursor.fetchone()
        if balance is None: 
            return False
        headers = {
                'X-Api-Key': 'YWUzMTBiZTYtNjUzNi00MzJmLWFjNmUtYmZlMjM1Y2U5MDY3',
                'Content-Type': 'application/json'
            }
        url = f'https://pto.api.clockify.me/v1/workspaces/65c249bfedeea53ae19d7dad/balance/policy/65dcba39a37a682370014ad8'

        payload = {
            "note": "Adding Accrued time for this week.",
            "userIds": [
                userId
            ],
            "value": 3.08 + float(balance[0])
        }
        logger.info(reverseForOutput(payload))
        result = patch(url=url, headers= headers, json=payload)
        if result.status_code == 204:
            return True
        else: 
            logger.error(result.reason)
            return False
    except Exception as e: 
        logger.error(f"{e.__traceback__.tb_lineno} - {str(e)}")
        raise e 
'''
Updates banked time balances for users by retrieving current balances and checking 
for discrepancies with Clockify. Updates balances as needed through Clockify API.

Process:
    - Establishes a connection to the database, retrying if connection fails.
    - Retrieves current user balances and the relevant policy ID.
    - Iteratively checks and updates user balances through the Clockify API, page by page.
    - Logs process and results, including any balance discrepancies.

Returns:
    None

Raises:
    Logs warnings if unable to initialize database connection and logs info 
    on successful completion of the banked time update process.
'''
def BankedTime():
    logger = setup_background_logger('DEBUG')
    while True:
        cursor, conn = sqlConnect()
        if cursor is None or conn is None:
            logger.warning(f' Failed to initilize cursor and connection in Banked Time')
            time.sleep(2)
        else: 
            break
    usrBalances, polID = getUsrBallances(conn, cursor)
    page = 1
    updateBalances= checkBalanceUpdate(usrBalances, polID, page)
    while len(updateBalances) != 0 :
        updateUsrBalances(updateBalances, polID)
        page += 1
        updateBalances= checkBalanceUpdate(usrBalances, polID, page)
    logger.info("SqlClockPull: Banked Time")

    

# if __name__ == "__main__":
#     main()