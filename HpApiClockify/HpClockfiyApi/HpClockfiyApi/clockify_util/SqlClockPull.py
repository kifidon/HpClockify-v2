from . import ClockifyPullV3
from . import ClockifyPushV3
from ..Loggers import setup_background_logger
import time

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
        logger.info(f" Updating User Balances: {{Employee ID: [New Balance, Old Balance]}}, updateBalances")
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
        logger.info(updateBalances)
        updateUsrBalances(updateBalances, polID)
        page += 1
        updateBalances= checkBalanceUpdate(usrBalances, polID, page)
    logger.info("SqlClockPull: Banked Time")

if __name__ == "__main__":
    main()