
from .serializers import (
    ExpenseSerializer, 
    CategorySerializer,
    EntrySerializer,
    TagsForSerializer
)
from .models import (
    Category,
    Entry,
    Tagsfor
)
from django.core.handlers.asgi import ASGIRequest
from rest_framework.exceptions import ValidationError
import requests
import asyncio
from django.http import HttpRequest, JsonResponse, HttpResponse
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from .Loggers import setup_background_logger
from json import loads, dumps
from asgiref.sync import sync_to_async
from .clockify_util.ClockifyPullV3 import getCategories
from .clockify_util import ClockifyPullV3
from .clockify_util.hpUtil import bytes_to_dict, check_category_for_deletion
import httpx

logger = setup_background_logger('DEBUG') #pass level argument 

def deleteCategory(newCategories):
    logger = setup_background_logger('DEBUG')
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
    logger = setup_background_logger('DEBUG')
    if request.method == 'POST':
        logger.info(f'Pulling Expense Category and trying again')
        inputData = request.POST
        logger.debug(dumps(inputData, indent=4))
        categories = getCategories(inputData['workspaceId'], 1)
        
        logger.info('Checking for stale Categories... ')
        deleteCategoryAsync = sync_to_async(deleteCategory)
        deleted = deleteCategoryAsync(categories['categories'])
        logger.info(f'Deleted {deleted} Categories')
        logger.debug(dumps(categories, indent=4))
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
            return JsonResponse(data = [inputData, categories], status=status.HTTP_201_CREATED, safe = False)

        except Exception as e:
            raise e
    else:
        return JsonResponse(
            data={
                'Message': 'Method Not Suported'
            }, status= status.HTTP_405_METHOD_NOT_ALLOWED
        )

@csrf_exempt
def updateTags(inputdata: dict):
    logger = setup_background_logger('DEBUG')
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
async def updateEntries(request: ASGIRequest):  
    logger = setup_background_logger('DEBUG')
    logger.debug(type(request))
    if request.method == 'POST':
        logger.debug(request.body)
        logger.debug(type(request.body))
        inputData = bytes_to_dict(request.body)
        logger.info(f'updateEntries Function called')
        logger.debug(dumps(inputData,indent=4))
        key = ClockifyPullV3.getApiKey()
        try: 
            timeId = inputData.get('id')
            workspaceId = inputData.get('workspaceId')
            stat = inputData.get('status').get('state') or None
        except Exception as e:
            logger.critical(str(e))
            logger. critical(dumps(inputData, indent=4))
            stat = 'NONE'
        if stat == 'APPROVED':
            allEntries = await ClockifyPullV3.getEntryForApproval(workspaceId, key, timeId, stat, 1)

            def syncUpdateEntries(entries): # create thread 
                try: 
                    try: # try and update if exists, otherwise create
                        approvalID = entries['approvalRequestId'] if entries['approvalRequestId'] is not None else timeId
                        # (f"{entries[i]['id']}, {workspaceId}, {approvalID} ")
                        entry = Entry.objects.get(id = entries['id'], workspace = workspaceId , time_sheet = approvalID)
                        serializer = EntrySerializer(data=entries, instance=entry, context = {'workspaceId': workspaceId,'approvalRequestId': timeId})
                        logger.info(f'Updating Entry {entries['id']}')
                    except Entry.DoesNotExist:
                        serializer = EntrySerializer(data=entries, context = {'workspaceId': workspaceId,'approvalRequestId': timeId})
                        logger.warning(f'Creating new Entry on timesheet {timeId}')
                        logger.debug(dumps(entries, indent=3))
                    if serializer.is_valid():
                        serializer.save()
                        logger.info(f'UpdateEntries on timesheet({timeId}): E-{entries['id']} 202 ACCEPTED') 
                        data_lines = dumps(serializer.validated_data, indent=4).split('\n')
                        reversed_data = '\n'.join(data_lines[::-1])
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
                        updateAsync(allEntries[i])
                    )
                try:
                    await asyncio.gather(*tasks)
                    logger.info(f'Entries added for timesheet {timeId}') 
                    return JsonResponse(data = allEntries, status=status.HTTP_201_CREATED, safe=False)

                except Exception as e:
                    logger.error(f'{str(e)} at line {e.__traceback__.tb_lineno} in \n\t{e.__traceback__.tb_frame}')
                    return JsonResponse(data = None, status=status.HTTP_417_EXPECTATION_FAILED, safe = False)

            else: 
                logger.warning(f'No entries were found on timesheet with id {timeId}. Review Clockify. 304 NOT_MODIFIED')
                return JsonResponse(data = None, status=status.HTTP_204_NO_CONTENT, safe = False)
        else:
                logger.info(f'UpdateEntries on timesheet({timeId}): Update on Pending or Withdrawn timesheet not necessary: {stat}  406 NOT_ACCEPTED    ')
                return JsonResponse(data = None, status=status.HTTP_204_NO_CONTENT, safe = False)
    else:
        response = JsonResponse(data=None, status = status.HTTP_405_METHOD_NOT_ALLOWED, safe = False)
        return response


