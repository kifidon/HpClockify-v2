from pydantic import BaseModel
from typing import Optional
from fastapi import Request
class Creator(BaseModel):
    userId: str
    userName: str
    userEmail: str

class Status(BaseModel):
    state: str
    updatedBy: str
    updatedByUserName: str
    updatedAt: str
    note: Optional[str] = ""

class Owner(BaseModel):
    userId: str
    userName: str
    timeZone: str
    startOfWeek: str

class DateRange(BaseModel):
    start: str
    end: str

class ApprovalRequest(BaseModel):
    id: str
    workspaceId: str
    dateRange: DateRange
    owner: Owner
    status: Status
    creator: Creator

    # Specify example value for Swagger documentation
    class Config:
        schema_extra = {
            "example": {
                "id": "66034527a9e0d922a6783603",
                "workspaceId": "65c249bfedeea53ae19d7dad",
                "dateRange": {
                    "start": "2024-03-17T06:00:00Z",
                    "end": "2024-03-24T05:59:59Z"
                },
                "owner": {
                    "userId": "65dcdd57ea15ab53ab7b14d7",
                    "userName": "Margaretta Potts Petawaysin",
                    "timeZone": "America/Denver",
                    "startOfWeek": "SUNDAY"
                },
                "status": {
                    "state": "APPROVED",
                    "updatedBy": "65c253aeffbbb676c5e05ff2",
                    "updatedByUserName": "Shawna Applejohn",
                    "updatedAt": "2024-03-27T17:05:30Z",
                    "note": ""
                },
                "creator": {
                    "userId": "65dcdd57ea15ab53ab7b14d7",
                    "userName": "Shawna Applejohn",
                    "userEmail": "shawna.applejohn@hillplain.com"
                }
            }
        }