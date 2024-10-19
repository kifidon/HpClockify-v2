from . import ClockifyPullV3
from . import ClockifyPushV3
from ..Loggers import setup_background_logger
import time
from .hpUtil import reverseForOutput
from requests import patch

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



def updateSalaryVacation(userId, cursor):
    
    query = f'''
        with cte as (
        Select 
            eu.id,
            eu.name,
            Case when DATEPART(year,eu.start_date ) = '2024' then 
            DATEDIFF(week, eu.start_date, GETDATE()) * 3.08
            else DATEDIFF(week, '2024-01-01', GETDATE()) * 3.08
            end as Accrual,
            Sum(tr.paidTimeOff) as Used,
            eu.[status]

        From EmployeeUser eu 
        LEFT join TimeOffRequests tr on tr.eID = eu.id
        Left join TimeOffPolicies tp on tp.id = tr.pID and tp.policy_name like '%Vacation - S%'
        where eu.hourly = 0 and tr.status = 'APPROVED'
        group by 
        eu.id,
        eu.name,
        eu.start_date,
        eu.[status]
    )
    Select c.Accrual- Coalesce(c.Used, 0) from cte c
        where c.id = {userId}
        order by c.[status], c.name 
    '''
    cursor.execute(balance)
    balance = cursor.fetchone()
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
    result = patch(url=url, headers= headers, json=payload)
    if result.status_code == 204:
        return True
    else: 
        logger = setup_background_logger()
        logger.error(result.reason)
        return False

def main():
    logger = setup_background_logger('DEBUG')
    while True:
        cursor, conn =ClockifyPullV3.sqlConnect()
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

    

if __name__ == "__main__":
    main()