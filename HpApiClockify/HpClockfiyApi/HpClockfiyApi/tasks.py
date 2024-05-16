
from .serializers import (
    ExpenseSerializer, 
    CategorySerializer,
    EntrySerializer,
    TagsForSerializer
)
from .models import (
    Category,
    Entry,
    Tagsfor, 
    Expense,
    BackGroundTaskResult
)
from django.utils import timezone
from django.core.handlers.asgi import ASGIRequest
from django.http import HttpRequest, JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.exceptions import ValidationError
from rest_framework import status
from asgiref.sync import sync_to_async

from json import loads, dumps
from .Loggers import setup_background_logger
from .clockify_util.ClockifyPullV3 import getCategories
from .clockify_util import ClockifyPullV3
from .clockify_util.hpUtil import bytes_to_dict, check_category_for_deletion, reverseForOutput, timeZoneConvert, get_current_time

import requests
import asyncio


loggerLevel = 'WARNING'
logger = setup_background_logger(loggerLevel) #pass level argument 

def taskResult(response: JsonResponse, inputData, caller: str):
    logger = setup_background_logger(loggerLevel)
    logger.info('Saving task result')
    BackGroundTaskResult.objects.create(
        status_code = response.status_code,
        message = response.content.decode() or None,
        data = inputData,
        caller = caller,
        time = timeZoneConvert(get_current_time(), '%Y-%m-%d %H:%M:%S')
    )

saveTaskResult = sync_to_async(taskResult, thread_sensitive=True)


def deleteCategory(newCategories):
    logger = setup_background_logger(loggerLevel)
    deleted = 0
    categories = Category.objects.all()
    for category in categories:
        if check_category_for_deletion(category.id, newCategories):
            logger.info('Found Stale Cateogory')
            category.delete
            deleted += 1
    return deleted 

    

@csrf_exempt
async def retryExpenses(request):   
    logger = setup_background_logger(loggerLevel)
    if request.method == 'POST':
        caller = 'Pulling Expense Category and trying again'
        logger.info(caller)
        inputData = request.POST
        logger.debug(reverseForOutput(inputData))
        categories = getCategories(inputData['workspaceId'], 1)
        
        logger.info('Checking for stale Categories... ')
        deleteCategoryAsync = sync_to_async(deleteCategory)
        deleted = deleteCategoryAsync(categories['categories'])
        logger.info(f'Deleted {deleted} Categories')
        logger.debug(reverseForOutput(categories))
        def pushCategories(category:dict):
            try:
                categoryInstanece = Category.objects.get(pk=category['id'])
                serializer = CategorySerializer(data= category, instance=categoryInstanece)
                logger.info(f'Existing Category... Updatiing')
            except Category.DoesNotExist:
                serializer = CategorySerializer(data = category)
                logger.info(f'New Category... Inserting')
            if serializer.is_valid():
                serializer.save()
                logger.info(f'Changes Saved')
                return 1
            else:
                raise ValidationError
        
        tasks = []
        pushCategoriesAsync = sync_to_async(pushCategories, thread_sensitive=True)
        for i in range(0,len(categories['categories'])): # updates all entries async 
            tasks.append(
                pushCategoriesAsync(categories['categories'][i])
            )
        try:
            await asyncio.gather(*tasks)
            logger.info(f'Categories updated')
            url =  'http://localhost:8000/HpClockifyApi/newExpense'
            requests.post(url=url, data=inputData)
            response = JsonResponse(data = 'Retry Expense Event Completed Succesfully', status=status.HTTP_201_CREATED, safe = False)
            await saveTaskResult(response, inputData, caller)
            return response
        except Exception as e:
            response = JsonResponse(data = 'Error Occured in retry', status=status.HTTP_400_BAD_REQUEST, safe = False)
            await saveTaskResult(response, inputData, caller)
            return response
    else:
        response =  JsonResponse(
            data={
                'Message': 'Method Not Suported'
            }, status= status.HTTP_405_METHOD_NOT_ALLOWED
        )
        await saveTaskResult(response, inputData, caller)
        return response

@csrf_exempt
def updateTags(inputdata: dict):
    logger = setup_background_logger(loggerLevel)
    logger.info(f'updateTags Function called')

    workspaceId = inputdata.get('timesheet').get('workspaceId')
    timeId = inputdata.get('timesheet').get('id')
    tags_data = inputdata.get('entry').get('tags')
    entry_id = inputdata.get('entry').get('id')
    # Get existing tags associated with the entry
    def deleteOldTags():
        try: 
            existing_tags = list(Tagsfor.objects.filter(entryid=entry_id, workspace=workspaceId))
                # Extract tag ids from the existing tags
            existing_tag_ids = []
            for tag in existing_tags: 
                existing_tag_ids.append(tag.id) 
            existing_tag_ids = set(existing_tag_ids)
                # Extract tag ids from the request payload
            request_tag_ids = set(tag['id'] for tag in tags_data)
                # Find tags to delete
            tags_to_delete = existing_tag_ids - request_tag_ids
            Tagsfor.objects.filter(id__in=tags_to_delete).delete()
            logger.info(f'Deleting old tags...{tags_to_delete}')
        except Tagsfor.DoesNotExist: 
            logger.info('No tags to delete')
            pass
            # Find new tags to create

    def updateTagSync(tag): # as thread 
        # Create new tags
        logger.debug(dumps(tags_data, indent= 4))
        try: 
            tagObj = Tagsfor.objects.get(id=tag['id'], entryid = entry_id, workspace = workspaceId)
            serializer = TagsForSerializer(data=tag, instance=tagObj, context={
                'workspaceId': workspaceId,
                'timeid': timeId,
                'entryid': entry_id
            })
            logger.warning('Updating Tag')
        except Tagsfor.DoesNotExist:
            serializer = TagsForSerializer(data=tag, context={
                'workspaceId': workspaceId,
                'timeid': timeId,
                'entryid': entry_id
            })
            logger.info(f'Creating new tag')
        if serializer.is_valid():
            serializer.save()
            logger.info(f'UpdateTags on timesheet({timeId}): E-{entry_id}-T-{tag['id']} 202 ACCEPTED') 
            data_lines = dumps(serializer.validated_data, indent=4).split('\n')
            reversed_data = '\n'.join(data_lines[::-1])
            logger.info(f'{reversed_data}')
            return tags_data
        else: 
            #  (serializer.validated_data)
            logger.error(f'Could not validate data\n{dumps(serializer.errors, indent=4)}')

            raise ValidationError(serializer.errors)
    
    deleteOldTags()
    for i in range(0, len(tags_data)):
        updateTagSync(tags_data[i])
        logger.info(f'Update TagsFor on Timesheet{timeId}: Complete ')
    return tags_data

@csrf_exempt
async def approvedEntries(request: ASGIRequest):  
    logger = setup_background_logger(loggerLevel)
    caller = 'Approved Entry Function Called'
    logger.info(caller)
    logger.debug(type(request))
    if request.method == 'POST':
        logger.debug(type(request.body))
        inputData = bytes_to_dict(request.body)
        logger.debug(dumps(inputData,indent=4))
        key = ClockifyPullV3.getApiKey()
        
        timeId = inputData.get('id')
        workspaceId = inputData.get('workspaceId')
        stat = inputData.get('status').get('state') or None
    
        if stat == 'APPROVED':
            allEntries = await ClockifyPullV3.getDataForApproval(workspaceId, key, timeId, stat, entryFlag=True)
            if len(allEntries) == 0:
                logger.warning('No Content. Is this expected?')
                response =  JsonResponse(data = {f'Message': f'No Entry for timesheet {timeId}'}, status=status.HTTP_204_NO_CONTENT, safe=False)
                await saveTaskResult(response, inputData, caller)
                return response
            def syncUpdateEntries(entries): # create thread 
                try: 
                    #refactoring 
                    entries['workspaceId']= workspaceId
                    entries['timesheetId'] = entries['approvalRequestId']
                    try: # try and update if exists, otherwise create
                
                        entry = Entry.objects.get(id = entries['id'], workspaceId = workspaceId )
                        serializer = EntrySerializer(data=entries, instance=entry, context = {'workspaceId': workspaceId,'timesheetId': timeId})
                        logger.info(f'Updating Entry {entries['id']}')
                    except Entry.DoesNotExist:
                        serializer = EntrySerializer(data=entries, context = {'workspaceId': workspaceId,'approvalRequestId': timeId})
                        logger.warning(f'Creating new Entry on timesheet {timeId}')

                    if serializer.is_valid():
                        serializer.save()
                        logger.info(f'UpdateEntries on timesheet({timeId}): E-{entries['id']} 202 ACCEPTED') 
                        reversed_data = reverseForOutput(entries)
                        logger.info(f'{reversed_data}')
                        if (len(entries['tags']) != 0):
                            data = {
                                'timesheet': inputData,
                                'entry': entries
                            }
                            updateTags(data)
                        return serializer.validated_data
                    else: 
                        logger.error(f'{serializer.errors}')
                        raise ValidationError(serializer.errors)
                except Exception as e:
                    logger.error(f'{str(e)} at line {e.__traceback__.tb_lineno} in \n\t{e.__traceback__.tb_frame}') 
                    raise  e
            updateAsync = sync_to_async(syncUpdateEntries, thread_sensitive=True)
            tasks = []
            if len(allEntries) != 0:
                for i in range(0,len(allEntries)): # updates all entries async 
                    tasks.append(
                        asyncio.create_task(updateAsync(allEntries[i]))
                    )
                try:
                    await asyncio.gather(*tasks)
                    logger.info(f'Entries added for timesheet {timeId}') 
                    response = JsonResponse(data = 'Approved Entries Opperation Completed Succesfully', status=status.HTTP_201_CREATED, safe=False)
                    await saveTaskResult(response, inputData, caller)
                    return response

                except Exception as e:
                    logger.error(f'{str(e)} at line {e.__traceback__.tb_lineno} in \n\t{e.__traceback__.tb_frame}')
                    response = JsonResponse(data = None, status=status.HTTP_417_EXPECTATION_FAILED, safe = False)
                    await saveTaskResult(response, inputData, caller)
                    return response
            else: 
                logger.warning(f'No entries were found on timesheet with id {timeId}. Review Clockify. 304 NOT_MODIFIED')
                response =  JsonResponse(data = None, status=status.HTTP_204_NO_CONTENT, safe = False)
                await saveTaskResult(response, inputData, caller)
                return response
        else:
                logger.info(f'UpdateEntries on timesheet({timeId}): Update on Pending or Withdrawn timesheet not necessary: {stat}  406 NOT_ACCEPTED    ')
                response = JsonResponse(data = None, status=status.HTTP_204_NO_CONTENT, safe = False)
                await saveTaskResult(response, inputData, caller)
                return response
    else:
        response = JsonResponse(data=None, status = status.HTTP_405_METHOD_NOT_ALLOWED, safe = False)
        await saveTaskResult(response, inputData, caller)
        return response
        return response

@csrf_exempt
async def approvedExpenses(request:ASGIRequest):
    logger = setup_background_logger()
    caller = 'Approved Expense function called'
    logger.info(caller)
    if request.method == 'POST':
        inputData = bytes_to_dict(request.body)
        logger.debug(f'InputData\n{reverseForOutput(inputData)}')
        key = ClockifyPullV3.getApiKey()
        timeId = inputData.get('id')
        workspaceId = inputData.get('workspaceId')
        stat = inputData.get('status').get('state') or None

        if stat =='APPROVED':
            allExpenses = await ClockifyPullV3.getDataForApproval(workspaceId, key, timeId, stat, expenseFlag=True)
            if len(allExpenses) == 0:
                logger.warning('No Content. Is this expected?')
                response =  JsonResponse(data = {f'Message': f'No Expenes for timesheet {timeId}'}, status=status.HTTP_204_NO_CONTENT, safe=False)
                await saveTaskResult(response, inputData, caller)
                return response
            def syncUpdateExpense(expense):
                #refactoring 
                expense['categoryId'] = expense['category']['id']
                expense[ 'projectId'] = expense['project']['id']
                expense['timesheetId'] = expense['approvalRequestId']
                try:
                    try:
                        approvalID = expense['approvalRequestId'] if expense['approvalRequestId'] is not None else timeId
                        expenseObj = Expense.objects.get(id=expense['id'], workspaceId = workspaceId)

                        serializer = ExpenseSerializer(instance=expenseObj, data=expense)
                        logger.info('Updating Expense...')
                    except Expense.DoesNotExist:
                        serializer = ExpenseSerializer(data=expense)
                        logger.warning(f'Creating new Expense on timesheet {timeId}')
                    if serializer.is_valid():
                        serializer.save()
                        logger.info(f'UpdateExpense on timesheet({timeId}): EX-{expense['id']} 202 ACCEPTED')
                        logger.info(reverseForOutput(expense))
                        return serializer.validated_data
                    else:
                        logger.error(serializer.error)
                        raise ValidationError(serializer.errors)
                except Exception as e:
                    logger.error(f'{str(e)} at line {e.__traceback__.tb_lineno} in \n\t{e.__traceback__.tb_frame}') 
                    raise  e
                
            asyncUpdateExpense = sync_to_async(syncUpdateExpense)
            tasks = []
            for expense in allExpenses:
                tasks.append(
                    asyncio.create_task(asyncUpdateExpense(expense))
                )
            try:
                await asyncio.gather(*tasks)
                logger.info(f'Expense added for timesheet {timeId}') 
                response =  JsonResponse(data = 'Approved Expense Opperation Completed Succesfully', status=status.HTTP_201_CREATED, safe=False)
                await saveTaskResult(response, inputData, caller)
                return response
            except Exception as e:
                logger.error(f'{str(e)} at line {e.__traceback__.tb_lineno} in \n\t{e.__traceback__.tb_frame}')
                response =  JsonResponse(data = None, status=status.HTTP_417_EXPECTATION_FAILED, safe = False)
                await saveTaskResult(response, inputData, caller)
                return response

        else:
            logger.info(f'UpdateExpense on timesheet({timeId}): Update on Pending or Withdrawn timesheet not necessary: {stat}  406 NOT_ACCEPTED    ')
            response =  JsonResponse(data = None, status=status.HTTP_204_NO_CONTENT, safe = False)
            await saveTaskResult(response, inputData, caller)
            return response
    else:
        response = JsonResponse(data=None, status = status.HTTP_405_METHOD_NOT_ALLOWED, safe = False)
        await saveTaskResult(response, inputData, caller)
        return response
        
