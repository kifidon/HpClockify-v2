from django.shortcuts import render
from django.http import JsonResponse
from django.core.handlers.asgi import ASGIRequest
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from django.db import  utils  #, transaction
from . import *
from .models import*
from asgiref.sync import sync_to_async
from rest_framework.exceptions import ValidationError 
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from .serializers import *
from Utilities.views import *
from time import time
from HillPlainAPI.Loggers import setup_server_logger
import httpx
from datetime import datetime


"""
Handles the creation of a new LemSheet entry or updating an existing entry in the database. This function accepts data
 related to a specific client's project, generates a unique ID and an incremented LemSheet number, validates the data, 
 and saves it to the database if valid.

Parameters:
    inputData (dict): Dictionary containing data fields for creating a LemSheet entry, including 'clientId' and 'projectId'.

Process:
    1. Generates a unique ID for the LemSheet entry based on the client's ID, project ID, and current timestamp.
    2. Finds existing LemSheet entries for the given client and project, then calculates the next lemNumber in sequence.
    3. Uses a serializer to validate and save the LemSheet data. Logs a success message if the operation is successful.
    4. If validation fails, logs the errors and raises a `ValidationError`.
    5. Catches database integrity errors (e.g., primary key conflicts) and logs appropriate error messages.
    6. Catches and logs any other exceptions, including traceback information, for debugging purposes.

Returns:
    bool: `True` if the LemSheet entry is successfully created; `False` if a validation or integrity error occurs.
"""
# @api_view(["PUT", "POST", "GET"])
def postThreadLemSheet(inputData):
    try:
        inputData["id"] = hash50(inputData['clientId'], datetime.now().strftime('%Y-%m-%dT%H-%M-%S'), inputData['projectId'])
        #gen LemNumber
        lems = LemSheet.objects.filter(clientId = inputData['clientId'], projectId=inputData['projectId'])
        # logger.debug(type(lems))
        lemNum = 0
        for lem in lems:
            if int(lem.lemNumber.split('-')[1]) > lemNum:
                lemNum = int(lem.lemNumber.split('-')[1])
        
        inputData['lemNumber'] = 'LEM-' + str(lemNum+1).zfill(4)
        serializer = LemSheetSerializer(data=inputData)
        if serializer.is_valid():
            serializer.save()
            logger.info('Opperation Succesful')
            return True
        else:
            for key, value in serializer.errors.items():
                logger.error(dumps({'Error Key': key, 'Error Value': value}, indent =4))
            raise ValidationError(serializer.errors)
    except ValidationError as v:
        logger.warning(f'Serializer could not be saved: {serializer.errors}')
        for key, value in serializer.errors.items():
            # Print the key and each error code and message
            logger.error(dumps({'Error Key': key, 'Error Value': value}, indent = 4))
                
        return False # Unknown, Raise error (BAD Request)
    except utils.IntegrityError as c:
        logger.error(f'{str(c)}')
        if "PRIMARY KEY constraint" in str(c):
            raise(utils.IntegrityError("A similar Lem already exists. Update the old Lem or change the current inputs "))
        return False
    except Exception as e: 
        logger.error(f'Traceback {e.__traceback__.tb_lineno}: {type(e)} - {str(e)}')
        raise e

"""
Handles asynchronous HTTP requests for creating, updating, and deleting `LemSheet` records.

Parameters:
    request (ASGIRequest): The incoming HTTP request with a JSON body containing details for the `LemSheet` entry, including `clientId` and `projectId`.

Process:
    1. Parses the request body as JSON and logs the HTTP method and input data for debugging.
    
    POST (Create `LemSheet`):
        - Calls `postThreadLemSheet` asynchronously to generate a unique ID and save the `LemSheet` data if valid.
        - Returns a `201 Created` response with the generated `id` if successful, or a `400 Bad Request` response if validation fails.
        - Handles integrity errors, such as conflicts with existing records, with a `409 Conflict` response.
    
    DELETE (Archive `LemSheet`):
        - Retrieves the specified `LemSheet` record by `id`, marks it as archived, and saves the update.
        - Returns a `204 No Content` response if archiving is successful.
        - If the `LemSheet` record is not found, returns a `404 Not Found` response.
    
    Other HTTP Methods:
        - Returns a `510 Not Extended` response for unsupported methods.

    General Exception Handling:
        - Catches any unexpected errors, logs traceback details, and returns a `501 Not Implemented` response with error information.

Returns:
    JsonResponse: The response status and data, with specific messages for each scenario (e.g., success, conflict, not found, or errors).
"""
@csrf_exempt
async def lemSheet(request:ASGIRequest):
    logger = setup_server_logger()
    try: 
        inputData = loads(request.body)
        logger.info(request.method)
        logger.debug(reverseForOutput(inputData))
        if request.method == 'POST':
            post = sync_to_async(postThreadLemSheet, thread_sensitive=False)
            try:
                result = await post(inputData)
                logger.debug(result)
                if result:
                    return JsonResponse(data=inputData['id'], status= status.HTTP_201_CREATED, safe=False)
                else: return JsonResponse(data='There was a problem creating your LEM. A similar record may already exist. Review selection and try again. To update lem visit the View Lem Screen. If problem continues contact Admin', status =status.HTTP_400_BAD_REQUEST, safe = False)
            except utils.IntegrityError as c:
                return JsonResponse(data=str(c), status= status.HTTP_409_CONFLICT, safe=False)
        elif request.method == 'DELETE': #Update status gflag 
            try: 
                lemsheet = await LemSheet.objects.aget(pk = inputData.get('id'))
                logger.debug(lemsheet)
                lemsheet.archived = True
                await lemsheet.asave(force_update=True)
                logger.info('Archived Lemsheet record succsesfully')
                response = JsonResponse(data= 'Archived record succsesfully', status= status.HTTP_204_NO_CONTENT, safe=False)
                return response
            except LemSheet.DoesNotExist as e:
                logger.warning(f'Record to delete with id {inputData.get('id')} was not found. Canceling Opperation ')
                logger.critical(f'({e.__traceback__.tb_lineno}) - {str(e)}')
                response = JsonResponse(data='Cannot delete record because it was not found in database. Contact Admin to resolve issue', status=status.HTTP_404_NOT_FOUND, safe= False)
                return response
            
        else: #do this later if needed
            return JsonResponse(data='Not Extended', status = status.HTTP_510_NOT_EXTENDED, safe=False)  
    except Exception as e:
        response = JsonResponse(data={'Invalid Request': f'A problem occured while handling your request. If error continues, contact admin \\n({e.__traceback__.tb_lineno}): {str(e)}'}, status=status.HTTP_501_NOT_IMPLEMENTED)
        logger.error(response.content)
        return response


"""
Finds or creates a `LemWorker` record based on the provided employee ID and role ID.

Parameters:
    inputData (dict): Dictionary containing information for the `LemWorker` entry, including `empId` (employee ID) and `roleId`.

Process:
    1. Logs the attempt to find an existing `LemWorker` record that matches the provided `empId` and `roleId`.
    2. If a matching `LemWorker` is found, logs the success and returns `True`, indicating no new record is needed.
    3. If the record is not found:
        - Logs the creation of a new `LemWorker` record.
        - Generates a unique `_id` for the new record based on `empId` and `roleId`.
        - Uses a serializer (`LemWorkerSerializer`) to validate and save the new `LemWorker` entry.
        - If validation is successful, logs a success message and returns `True`.
        - If validation fails, logs each error detail and raises a `ValidationError`.
    4. Catches any unexpected errors, logs the error message with traceback details, and raises the exception.

Returns:
    bool: `True` if a matching record is found or a new record is successfully created.
    
Raises:
    ValidationError: If the input data fails serializer validation.
    Exception: For any other unexpected errors.
"""
def postThreadLemWorker(inputData: dict):
    logger = setup_server_logger()
    try:
        logger.info("Looking for LemWorker...")
        lemworker = LemWorker.objects.get(
            empId = inputData['empId'],
            roleId= inputData['roleId'],
        )
        logger.info("Found!")
        return True
        # do not need to insert a new one
    except LemWorker.DoesNotExist:
        logger.info("Not Found!")
        logger.info("Creating a new LemWorker Record")
        try:
            inputData["_id"] = hash50(inputData['empId'], inputData["roleId"])
            workerSerializer = LemWorkerSerializer(data=inputData)
            if workerSerializer.is_valid():
                # save new worker role 
                workerSerializer.save()
                logger.info('New Lem Worker Added Successfully')
                return True
            else:
                for key, value in workerSerializer.errors.items():
                    logger.error(dumps({'Error Key': key, 'Error Value': value}, indent =4))
                raise ValidationError(workerSerializer.errors)
        except Exception as e: 
            logger.error(f"({e.__traceback__.tb_lineno}) - {str(e)}")
            raise e
        
"""
Handles asynchronous HTTP requests to create or manage `LemWorker` entries. 

Parameters:
    request (ASGIRequest): The incoming HTTP request with a JSON body containing details for the `LemWorker` entry, including `empId` and `roleId`.

Process:
    1. Parses the JSON request body, logs the HTTP method, and logs input data for debugging purposes.
    
    POST (Create or Find `LemWorker`):
        - Calls `postThreadLemWorker` asynchronously to check if the `LemWorker` entry exists. If not, it creates a new one.
        - Sends a POST request to an external API at `'http://localhost:5000/HpClockifyApi/task/lemEntry'` with the `LemWorker` data.
        - Returns a `201 Created` response with the `LemWorker` data if the external API call is successful.
        - If the external API call fails, returns a `400 Bad Request` response with an error message.
        
    Other HTTP Methods:
        - Returns a `510 Not Extended` response for unsupported methods.

    Exception Handling:
        - Catches `ValidationError` and returns a `400 Bad Request` response with a message for invalid input data.
        - Catches `IntegrityError`, logs duplicate record details if related to primary key constraint, and raises an error message.
        - Catches any other unexpected exceptions, logs traceback information, and returns a `501 Not Implemented` response with the error details.

Returns:
    JsonResponse: The response status and data, with specific messages for each scenario (e.g., success, conflict, not implemented, or errors).
    
Raises:
    ValidationError: For input data failing validation.
    IntegrityError: For primary key conflicts or duplicate records.
"""
@csrf_exempt
async def LemWorkerEntry(request:ASGIRequest):
    logger = setup_server_logger()
    try: 
        inputData = loads(request.body)
        logger.debug(reverseForOutput(inputData))
        logger.info(request.method)
        if request.method == 'POST':
            
            post = sync_to_async(postThreadLemWorker, thread_sensitive=False)

            await post(inputData)

            url =  'http://localhost:5000/HpClockifyApi/task/lemEntry'
            async with httpx.AsyncClient(timeout=300) as client:
                response = await client.post(url=url, data=inputData)
            if response.status_code <=299:
                return JsonResponse(data=inputData, status= status.HTTP_201_CREATED)
            else:
                return JsonResponse(data='Failed To insert Entry. Review Selections and try again or contact Admin if problem persists', status= status.HTTP_400_BAD_REQUEST, safe=False)
        else: #do this later if needed
            return JsonResponse(data='Feture Not Extended', status = status.HTTP_510_NOT_EXTENDED, safe=False)
    except ValidationError as v:
            return JsonResponse(data="Invalid Request. Review Selections and try again. Contact admin if problem persists", status =status.HTTP_400_BAD_REQUEST, safe=False) 
    except utils.IntegrityError as c:
            if "PRIMARY KEY constraint" in str(c):
                logger.error(reverseForOutput(inputData))
                raise(utils.IntegrityError("Server is trying to insert a douplicate record. Contact Adin if problem persists "))
            return JsonResponse(data = inputData, status= status.HTTP_409_CONFLICT, safe = False)
    except Exception as e:
        response = JsonResponse(data=f'A problem occured while handling your request. If error continues, contact admin \n({e.__traceback__.tb_lineno}): {str(e)}', status=status.HTTP_501_NOT_IMPLEMENTED, safe = False)
        logger.error(response.content)
        return response

"""
Creates a new `EquipEntry` record based on the provided input data.

Parameters:
    inputData (dict): Dictionary containing details for the `EquipEntry`, including `lemId` and `equipId`.

Process:
    1. Generates a unique `_id` for the entry using `lemId`, `equipId`, and the current timestamp.
    2. Logs the input data for debugging purposes.
    3. Uses `EquipEntrySerializer` to validate the `EquipEntry` data.
        - If the data is valid, saves the `EquipEntry` and logs a success message, returning `True`.
        - If validation fails, logs each error detail and raises a `ValidationError` with the initial data.
    4. Catches any unexpected errors, logs the input data and error details (including traceback), and raises the exception.

Returns:
    bool: `True` if the `EquipEntry` record is successfully saved.

Raises:
    ValidationError: If the input data fails serializer validation.
    Exception: For any other unexpected errors.
"""
def postThreadEquipEntry(inputData: dict):
    logger = setup_server_logger()
    try:
        inputData["_id"] = hash50(inputData["lemId"], inputData["equipId"], str(time.time())) 
        logger.debug(dumps(inputData, indent=4))
        threadSerializer = EquipEntrySerializer(data=inputData)
        if threadSerializer.is_valid():
            logger.info("Saving Expense Entry")
            threadSerializer.save()
            logger.info("Equip Entry saved succsesfully")
            return True
        else:
            for key, value in threadSerializer.errors.items():
                logger.error(dumps({'Error Key': key, 'Error Value': value}, indent =4))
            raise ValidationError(threadSerializer.initial_data)
    except Exception as e: 
        logger.debug(f"Initial Data: {dumps(inputData, indent = 4)}")
        logger.error(f"{type(e)} ({e.__traceback__.tb_lineno}) - {str(e)} ")
        raise e
        
"""
Handles asynchronous HTTP requests for managing `EquipEntry` records.

Parameters:
    request (ASGIRequest): The incoming HTTP request containing JSON data with details for the `EquipEntry`, such as `lemId` and `equipId`.

Process:
    1. Parses the JSON request body and logs the input data and HTTP method for debugging purposes.

    POST (Create `EquipEntry`):
        - Calls `postThreadEquipEntry` asynchronously to create a new `EquipEntry` record.
        - If the entry is successfully created, returns a `201 Created` response with the `EquipEntry` data.
        - If creation fails, returns a `400 Bad Request` response with the input data.

    Other HTTP Methods:
        - Returns a `510 Not Extended` response for unsupported methods.

    Exception Handling:
        - Catches `ValidationError` and returns a `400 Bad Request` response with a message indicating invalid data.
        - Catches `IntegrityError`, logs a message if there's a primary key conflict, and returns a `409 Conflict` response.
        - Catches any other unexpected exceptions, logs traceback information, and returns a `501 Not Implemented` response with error details.

Returns:
    JsonResponse: A response with a specific status code and message based on the outcome (e.g., success, conflict, error).

Raises:
    ValidationError: For invalid input data.
    IntegrityError: For primary key conflicts.
    Exception: For any other unexpected errors.
"""
@csrf_exempt
async def equipmentEntries(request: ASGIRequest):
    logger = setup_server_logger()
    try: 
        inputData = loads(request.body)
        logger.debug(reverseForOutput(inputData))
        logger.info(request.method)

        if request.method == 'POST':
            post = sync_to_async(postThreadEquipEntry, thread_sensitive=False)
            result = await post(inputData)
            if result:
                return JsonResponse(data=inputData, status= status.HTTP_201_CREATED)
            else: return JsonResponse(data=inputData, status =status.HTTP_400_BAD_REQUEST)

        else: #do this later if needed
            return JsonResponse(data='Not Extended', status = status.HTTP_510_NOT_EXTENDED, safe=False)  
    except ValidationError as v:
            return JsonResponse(data="Invalid Request. Review Selections and try again. Contact admin if problem persists", status =status.HTTP_400_BAD_REQUEST, safe=False) 
    except utils.IntegrityError as c:
            if "PRIMARY KEY constraint" in str(c):
                logger.critical(f"Primary Key Conflict on request - \n{reverseForOutput(inputData)}")
            return JsonResponse(data = inputData, status= status.HTTP_409_CONFLICT, safe = False)
    except Exception as e:
        response = JsonResponse(data=f'A problem occured while handling your request. If error continues, contact admin | ({e.__traceback__.tb_lineno}): {str(e)}', status=status.HTTP_501_NOT_IMPLEMENTED, safe = False)
        logger.error(response.content)
        return response


@api_view(["POST"])
def insertRoleOrEquipment(request:ASGIRequest):
    logger = setup_server_logger()
    logger.info("Creating Hash id for new record")
    try: 
        inputData = loads(request.body)
        logger.debug(reverseForOutput(inputData))
        if request.method == 'POST':
            inputData['id'] = hash50(inputData['name'], inputData['clientId'])
            if inputData['isRole']:
                logger.info("Creating serializer for Role Table")
                serializer = RoleSerializer(data=inputData)
                inputData['roleId'] = inputData['id']
                #make default later 
                inputData["workRate"]= 0
                inputData["travelRate"]=0
                inputData["calcRate"] = 0
                inputData["mealRate"] =0 
                inputData["hotelRate"] = 0
            else:
                logger.info("Creating serializer for Equipment Table")                 
                serializer = EquipmentSerializer(data=inputData)
                inputData['equipId'] = inputData['id']
                #make these the default when no key is passed 
                inputData["dayRate"] = 0
                inputData["unitRate"] = 0
            if serializer.is_valid():
                logger.info("Saving Request Data...")
                serializer.save()
                logger.info("Operation Completed Succesfully")
                request.session['inputData'] = inputData
                url ='https://hillplain-api.ngrok.app/HpClockifyApi/rateSheet'
                return JsonResponse(data={"url": url, "inputdata": inputData} , status=status.HTTP_201_CREATED, safe=False)
            else:
                for key, value in serializer.errors.items():
                    logger.error(dumps({'Error Key': key, 'Error Value': value}, indent =4))
                    if any('already exists' in str(v) for v in value):
                        raise utils.IntegrityError('An entry with this id already exists')
                raise ValidationError(serializer.initial_data)
        else:
            return JsonResponse(data='Method not implemented yet', status=status.HTTP_405_METHOD_NOT_ALLOWED, safe=False)
    except utils.IntegrityError as c:
            if "PRIMARY KEY constraint" in str(c):
                logger.critical(f"Primary Key Conflict on request - \n{reverseForOutput(inputData)}")
            return JsonResponse(data = 'A Record with this name already exists', status= status.HTTP_409_CONFLICT, safe = False)
    except ValidationError as v:
        logger.debug(f"Validation error - ({v.__traceback__.tb_lineno}) {str(v.args[0])}")
        return JsonResponse(data='Invalid Requests. Check selections and try again. If problem persists, contact server admin', status=status.HTTP_400_BAD_REQUEST, safe=False)
    except Exception as e:
        response = JsonResponse(data=f'A problem occured while handling your request. If error continues, contact admin | ({e.__traceback__.tb_lineno}): {str(e)}', status=status.HTTP_501_NOT_IMPLEMENTED, safe = False)
        logger.error(f"({e.__traceback__.tb_lineno}) - {str(e)}")
        return response

"""
Handles HTTP POST requests to create a new record in either the `Role` or `Equipment` table.

Parameters:
    request (ASGIRequest): The incoming HTTP request containing JSON data with attributes for either a `Role` or `Equipment`.

Process:
    1. Parses the JSON request body, creates a unique hash ID for the new record, and logs input data and request method.

    POST (Insert `Role` or `Equipment`):
        - If `isRole` is `True` in `inputData`, configures a serializer for `Role` with relevant fields (`roleId`, `workRate`, etc.).
        - If `isRole` is `False`, configures a serializer for `Equipment` with relevant fields (`equipId`, `dayRate`, etc.).
        - Validates the serializer. If valid, saves the record and stores input data in the session.
        - Returns a `201 Created` response with the `rateSheet` URL and `inputData`.
        - If the serializer is invalid, logs validation errors, and raises `ValidationError` or `IntegrityError` for duplicate records.

    Other HTTP Methods:
        - Returns a `405 Method Not Allowed` response for unsupported methods.

    Exception Handling:
        - Catches `IntegrityError`, logs a primary key conflict message if applicable, and returns a `409 Conflict` response.
        - Catches `ValidationError` and returns a `400 Bad Request` response with an error message for invalid requests.
        - Catches any other unexpected exceptions, logs traceback details, and returns a `501 Not Implemented` response with error information.

Returns:
    JsonResponse: A response with a specific status code and message based on the outcome (e.g., success, conflict, error).

Raises:
    ValidationError: For invalid input data.
    IntegrityError: For primary key conflicts.
    Exception: For any other unexpected errors.
"""
@api_view(["POST", "GET"])
def rateSheets(request: ASGIRequest = None): #maybe make async later 
    logger = setup_server_logger()
    logger.info("Inserting Data for Client Rate Sheet")
    try: 
        inputData = request.session['inputData']
        logger.info('Redirect Caught')
    except KeyError : 
        inputData = loads(request.body)
    logger.debug(dumps(inputData, indent= 4))
    try:
        if request.method == 'POST' or request.method == 'GET': 
            if inputData['isRole'] == True: # Worker rate sheet 
                logger.info("Worker Rate sheet path")
                inputData['_id'] = hash50(inputData['clientId'], inputData['roleId'], inputData['projectId']) #maybe include workspace in this later 
                #try update 
                try:
                    rates = WorkerRateSheet.objects.get(pk=inputData['_id'])
                    serializer = WorkerRateSheetSerializer(instance=rates, data = inputData)
                    logger.info("Updating rate sheet")
                    updated = True
                except WorkerRateSheet.DoesNotExist:
                    serializer = WorkerRateSheetSerializer(data= inputData)
                    logger.info("Creating new rate sheet recorde")
                    updated = False
                if serializer.is_valid():
                    logger.info("Saving Changes")
                    serializer.save()
                    logger.info("opperaiton complete")
                    if not updated:
                        return JsonResponse(data=inputData, status=status.HTTP_201_CREATED)
                    else: return JsonResponse(data=inputData, status=status.HTTP_202_ACCEPTED)
                else:
                    for key, value in serializer.errors.items():
                        logger.error(dumps({'Error Key': key, 'Error Value': value}, indent =4))
                        if any('already exists' in str(v) for v in value):
                            raise utils.IntegrityError('An record with this id already exists')
                    raise ValidationError(serializer.initial_data)
            else: #Eqp rate sheet 
                logger.info('Equipment Rate sheet path')
                logger.debug(f'Hash Fields: {inputData.get('clientId', "Missing")}, {inputData.get('equipId', "Missing")}, {inputData.get('projectId', "Missing")}')
                inputData['_id'] = hash50(inputData['clientId'], inputData['equipId'], inputData['projectId']) #maybe include workspace in this later 
                #try update 
                try:
                    rates = EqpRateSheet.objects.get(pk=inputData['_id'])
                    serializer = EqpRateSheetSerializer(instance=rates, data = inputData)
                    logger.info("Updating rate sheet")
                    updated = True
                except EqpRateSheet.DoesNotExist:
                    serializer = EqpRateSheetSerializer(data= inputData)
                    logger.info("Creating new rate sheet recorde")
                    updated = False
                if serializer.is_valid():
                    logger.info("Saving Changes")
                    serializer.save()
                    logger.info("opperaiton complete")
                    if not updated:
                        return JsonResponse(data=inputData, status=status.HTTP_201_CREATED)
                    else: return JsonResponse(data=inputData, status=status.HTTP_202_ACCEPTED)
                else:
                    for key, value in serializer.errors.items():
                        logger.error(dumps({'Error Key': key, 'Error Value': value}, indent =4))
                        if any('already exists' in str(v) for v in value):
                            raise utils.IntegrityError('An record with this id already exists')
                    raise ValidationError(serializer.initial_data)
    except utils.IntegrityError as c:
            if "PRIMARY KEY constraint" in str(c):
                logger.critical(f"Primary Key Conflict on request - \n{reverseForOutput(inputData)}")
            return JsonResponse(data = 'A Record with this name already exists', status= status.HTTP_409_CONFLICT, safe = False)
    except ValidationError as v:
        logger.debug(f"Validation error - ({v.__traceback__.tb_lineno}) {str(v.args[0])}")
        return JsonResponse(data='Invalid Requests. Check selections and try again. If problem persists, contact server admin', status=status.HTTP_400_BAD_REQUEST, safe=False)
    except KeyError as k:
        logger.error(f"({k.__traceback__.tb_lineno})Missing or incorrect key. Check isRole: \n{reverseForOutput(inputData)}")
        return JsonResponse(data='Internal server Key Error', status=status.HTTP_500_INTERNAL_SERVER_ERROR, safe= False)
    except Exception as e:
        response = JsonResponse(data=f'A problem occured while handling your request. If error continues, contact admin | ({e.__traceback__.tb_lineno}): {str(e)}', status=status.HTTP_501_NOT_IMPLEMENTED, safe = False)
        logger.error(f"{type(e)} ({e.__traceback__.tb_lineno}) - {str(e)}")
        return response
                

# @api_view(["POST"])
# def clientRep(request: ASGIRequest):
#     logger.info("inserting new client rep")
#     inputData = loads(request.body)
#     if request.method == 'POST':
#         try:
#             serializer = 

'''
Future Proof   
    @api_view(['PUT', 'POST', 'GET'])
    @csrf_exempt
    async def lemWorker(request:ASGIRequest):
        logger = setup_server_logger()
        try: 
            inputData = loads(request.body)
            logger.debug(reverseForOutput(inputData))
            logger.info(request.method)
            if request.method == 'POST':
                def postThread(inputData):
                    try:
                        serializer = LemSheetSerializer(data=inputData)
                        if serializer.is_valid():
                            serializer.save()
                            return True
                        else:
                            for key, value in serializer.errors.items():
                                logger.info(dumps({'Error Key': key, 'Error Value': value}, indent =4))
                            raise ValidationError(serializer.errors)
                    except ValidationError as v:
                        return False
                    except Exception as e: 
                        logger.error(f'Traceback {e.__traceback__.tb_lineno}: {type(e)} - {str(e)}')
                        raise e
                post = sync_to_async(postThread, thread_sensitive=False)

                result = await post(inputData)
                if result:
                    return JsonResponse(data=inputData, status= status.HTTP_201_CREATED)
                else: return JsonResponse(data=inputData, status =status.HTTP_400_BAD_REQUEST)
            else: #do this later if needed
                return JsonResponse(data='Not Extended', status = status.HTTP_510_NOT_EXTENDED, safe=False)  
        except Exception as e:
            response = JsonResponse(data={'Invalid Request': f'A problem occured while handling your request. If error continues, contact admin \n({e.__traceback__.tb_lineno}): {str(e)}'}, status=status.HTTP_501_NOT_IMPLEMENTED)
            logger.error(response.content)
            return response

    @api_view(['PUT', 'POST', 'GET'])
    @csrf_exempt
    async def lemEntry(request:ASGIRequest):
        logger = setup_server_logger()
        try: 
            inputData = loads(request.body)
            logger.debug(reverseForOutput(inputData))
            logger.info(request.method)
            if request.method == 'POST':
                def postThread(inputData):
                    try:
                        serializer = LemSheetSerializer(data=inputData)
                        if serializer.is_valid():
                            serializer.save()
                            return True
                        else:
                            for key, value in serializer.errors.items():
                                logger.info(dumps({'Error Key': key, 'Error Value': value}, indent =4))
                            raise ValidationError(serializer.errors)
                    except ValidationError as v:
                        return False
                    except Exception as e: 
                        logger.error(f'Traceback {e.__traceback__.tb_lineno}: {type(e)} - {str(e)}')
                        raise e
                post = sync_to_async(postThread, thread_sensitive=False)

                result = await post(inputData)
                if result:
                    return JsonResponse(data=inputData, status= status.HTTP_201_CREATED)
                else: return JsonResponse(data=inputData, status =status.HTTP_400_BAD_REQUEST)
            else: #do this later if needed
                return JsonResponse(data='Not Extended', status = status.HTTP_510_NOT_EXTENDED, safe=False)  
        except Exception as e:
            response = JsonResponse(data={'Invalid Request': f'A problem occured while handling your request. If error continues, contact admin \n({e.__traceback__.tb_lineno}): {str(e)}'}, status=status.HTTP_501_NOT_IMPLEMENTED)
            logger.error(response.content)
            return response
        
        
    @api_view(['PUT', 'POST', 'GET'])
    @csrf_exempt
    async def equipEntry(request:ASGIRequest):
        logger = setup_server_logger()
        try: 
            inputData = loads(request.body)
            logger.debug(reverseForOutput(inputData))
            logger.info(request.method)
            if request.method == 'POST':
                def postThread(inputData):
                    try:
                        serializer = LemSheetSerializer(data=inputData)
                        if serializer.is_valid():
                            serializer.save()
                            return True
                        else:
                            for key, value in serializer.errors.items():
                                logger.info(dumps({'Error Key': key, 'Error Value': value}, indent =4))
                            raise ValidationError(serializer.errors)
                    except ValidationError as v:
                        return False
                    except Exception as e: 
                        logger.error(f'Traceback {e.__traceback__.tb_lineno}: {type(e)} - {str(e)}')
                        raise e
                post = sync_to_async(postThread, thread_sensitive=False)

                result = await post(inputData)
                if result:
                    return JsonResponse(data=inputData, status= status.HTTP_201_CREATED)
                else: return JsonResponse(data=inputData, status =status.HTTP_400_BAD_REQUEST)
            else: #do this later if needed
                return JsonResponse(data='Not Extended', status = status.HTTP_510_NOT_EXTENDED, safe=False)  
        except Exception as e:
            response = JsonResponse(data={'Invalid Request': f'A problem occured while handling your request. If error continues, contact admin \n({e.__traceback__.tb_lineno}): {str(e)}'}, status=status.HTTP_501_NOT_IMPLEMENTED)
            logger.error(response.content)
            return response
        

    @api_view(['PUT', 'POST', 'GET'])
    @csrf_exempt
    async def eqpRateSheet(request:ASGIRequest):
        logger = setup_server_logger()
        try: 
            inputData = loads(request.body)
            logger.debug(reverseForOutput(inputData))
            logger.info(request.method)
            if request.method == 'POST':
                def postThread(inputData):
                    try:
                        serializer = LemSheetSerializer(data=inputData)
                        if serializer.is_valid():
                            serializer.save()
                            return True
                        else:
                            for key, value in serializer.errors.items():
                                logger.info(dumps({'Error Key': key, 'Error Value': value}, indent =4))
                            raise ValidationError(serializer.errors)
                    except ValidationError as v:
                        return False
                    except Exception as e: 
                        logger.error(f'Traceback {e.__traceback__.tb_lineno}: {type(e)} - {str(e)}')
                        raise e
                post = sync_to_async(postThread, thread_sensitive=False)

                result = await post(inputData)
                if result:
                    return JsonResponse(data=inputData, status= status.HTTP_201_CREATED)
                else: return JsonResponse(data=inputData, status =status.HTTP_400_BAD_REQUEST)
            else: #do this later if needed
                return JsonResponse(data='Not Extended', status = status.HTTP_510_NOT_EXTENDED, safe=False)  
        except Exception as e:
            response = JsonResponse(data={'Invalid Request': f'A problem occured while handling your request. If error continues, contact admin \n({e.__traceback__.tb_lineno}): {str(e)}'}, status=status.HTTP_501_NOT_IMPLEMENTED)
            logger.error(response.content)
            return response
        
    @api_view(['PUT', 'POST', 'GET'])
    @csrf_exempt
    async def workerRateSheet(request:ASGIRequest):
        logger = setup_server_logger()
        try: 
            inputData = loads(request.body)
            logger.debug(reverseForOutput(inputData))
            logger.info(request.method)
            if request.method == 'POST':
                def postThread(inputData):
                    try:
                        serializer = LemSheetSerializer(data=inputData)
                        if serializer.is_valid():
                            serializer.save()
                            return True
                        else:
                            for key, value in serializer.errors.items():
                                logger.info(dumps({'Error Key': key, 'Error Value': value}, indent =4))
                            raise ValidationError(serializer.errors)
                    except ValidationError as v:
                        return False
                    except Exception as e: 
                        logger.error(f'Traceback {e.__traceback__.tb_lineno}: {type(e)} - {str(e)}')
                        raise e
                post = sync_to_async(postThread, thread_sensitive=False)

                result = await post(inputData)
                if result:
                    return JsonResponse(data=inputData, status= status.HTTP_201_CREATED)
                else: return JsonResponse(data=inputData, status =status.HTTP_400_BAD_REQUEST)
            else: #do this later if needed
                return JsonResponse(data='Not Extended', status = status.HTTP_510_NOT_EXTENDED, safe=False)  
        except Exception as e:
            response = JsonResponse(data={'Invalid Request': f'A problem occured while handling your request. If error continues, contact admin \n({e.__traceback__.tb_lineno}): {str(e)}'}, status=status.HTTP_501_NOT_IMPLEMENTED)
            logger.error(response.content)
            return response
        

    @api_view(['PUT', 'POST', 'GET'])
    @csrf_exempt
    async def eqpRateSheet(request:ASGIRequest):
        logger = setup_server_logger()
        try: 
            inputData = loads(request.body)
            logger.debug(reverseForOutput(inputData))
            logger.info(request.method)
            if request.method == 'POST':
                def postThread(inputData):
                    try:
                        serializer = LemSheetSerializer(data=inputData)
                        if serializer.is_valid():
                            serializer.save()
                            return True
                        else:
                            for key, value in serializer.errors.items():
                                logger.info(dumps({'Error Key': key, 'Error Value': value}, indent =4))
                            raise ValidationError(serializer.errors)
                    except ValidationError as v:
                        return False
                    except Exception as e: 
                        logger.error(f'Traceback {e.__traceback__.tb_lineno}: {type(e)} - {str(e)}')
                        raise e
                post = sync_to_async(postThread, thread_sensitive=False)

                result = await post(inputData)
                if result:
                    return JsonResponse(data=inputData, status= status.HTTP_201_CREATED)
                else: return JsonResponse(data=inputData, status =status.HTTP_400_BAD_REQUEST)
            else: #do this later if needed
                return JsonResponse(data='Not Extended', status = status.HTTP_510_NOT_EXTENDED, safe=False)  
        except Exception as e:
            response = JsonResponse(data={'Invalid Request': f'A problem occured while handling your request. If error continues, contact admin \n({e.__traceback__.tb_lineno}): {str(e)}'}, status=status.HTTP_501_NOT_IMPLEMENTED)
            logger.error(response.content)
            return response
        

    @api_view(['PUT', 'POST', 'GET'])
    @csrf_exempt
    async def clientRep(request:ASGIRequest):
        logger = setup_server_logger()
        try: 
            inputData = loads(request.body)
            logger.debug(reverseForOutput(inputData))
            logger.info(request.method)
            if request.method == 'POST':
                def postThread(inputData):
                    try:
                        serializer = LemSheetSerializer(data=inputData)
                        if serializer.is_valid():
                            serializer.save()
                            return True
                        else:
                            for key, value in serializer.errors.items():
                                logger.info(dumps({'Error Key': key, 'Error Value': value}, indent =4))
                            raise ValidationError(serializer.errors)
                    except ValidationError as v:
                        return False
                    except Exception as e: 
                        logger.error(f'Traceback {e.__traceback__.tb_lineno}: {type(e)} - {str(e)}')
                        raise e
                post = sync_to_async(postThread, thread_sensitive=False)

                result = await post(inputData)
                if result:
                    return JsonResponse(data=inputData, status= status.HTTP_201_CREATED)
                else: return JsonResponse(data=inputData, status =status.HTTP_400_BAD_REQUEST)
            else: #do this later if needed
                return JsonResponse(data='Not Extended', status = status.HTTP_510_NOT_EXTENDED, safe=False)  
        except Exception as e:
            response = JsonResponse(data={'Invalid Request': f'A problem occured while handling your request. If error continues, contact admin \n({e.__traceback__.tb_lineno}): {str(e)}'}, status=status.HTTP_501_NOT_IMPLEMENTED)
            logger.error(response.content)
            return response
'''

