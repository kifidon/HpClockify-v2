from . import ClockifyPullV3
from . import ClockifyPushV3
from .hpUtil import logging, get_current_time

def getUsrBallances(conn, cursor):
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
        logging.error(f"{get_current_time()} - ERROR: ({exc.__class__}): \n----------{exc.__traceback__.tb_frame.f_code.co_filename}, {exc.__traceback__.tb_frame.f_code.co_name} \n\tLine: {exc.__traceback__.tb_lineno} \n----------{str(exc)}\n")
        raise
    else:
        logging.info(f"{get_current_time()} - INFO: Checking User Balances")
        return usrBalances, result[1]
       
def checkBalanceUpdate(usrBalances, polID, page):
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
        logging.error(f"{get_current_time()} - ERROR: ({exc.__class__}): \n----------{exc.__traceback__.tb_frame.f_code.co_filename}, {exc.__traceback__.tb_frame.f_code.co_name} \n\tLine: {exc.__traceback__.tb_lineno} \n----------{str(exc)}\n")
        raise
    else:
        logging.info(f"{get_current_time()} - INFO: Updating User Balances: {{Employee ID: [New Balance, Old Balance]}}, updateBalances")
        return updateBalances
    
def updateUsrBalances(updateBalances, polID):
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
        logging.error(f"{get_current_time()} - ERROR: ({exc.__class__}): \n----------{exc.__traceback__.tb_frame.f_code.co_filename}, {exc.__traceback__.tb_frame.f_code.co_name} \n\tLine: {exc.__traceback__.tb_lineno} \n----------{str(exc)}\n")
        raise
    else:
        logging.info(f'{get_current_time()} - INFO: Updated Banked Time')

def main():
    cursor, conn =ClockifyPullV3.sqlConnect()
    usrBalances, polID = getUsrBallances(conn, cursor)
    page = 1
    updateBalances= checkBalanceUpdate(usrBalances, polID, page)
    while len(updateBalances) != 0 :
        logging.info(updateBalances)
        updateUsrBalances(updateBalances, polID)
        page += 1
        updateBalances= checkBalanceUpdate(usrBalances, polID, page)
    logging.info("SqlClockPull: Banked Time")

if __name__ == "__main__":
    main()