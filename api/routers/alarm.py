"""Code for email api"""

import os
from datetime import datetime
from fastapi import status, APIRouter, UploadFile,File, Depends
from ..dependencies.users import get_current_user
from ..dependencies.classes import User

alarm_location = os.getenv("ALARM_PATH")

router = APIRouter()

@router.post("/alarm/send/", status_code=status.HTTP_200_OK)
async def alarm_team(drone_name: str,
                    location: str,
                    alarm_type: str,
                    notes: str,
                    file: UploadFile | None = File(),
                    current_user: User = Depends(get_current_user)):
    """API call to alarm the team

    Args:
        drone_name (str): drone
        location (str): location
        alarm_type (str): type
        notes (str): notes
        file (UploadFile | None, optional): file Defaults to File().
        current_user (User, optional): user. Defaults to Depends(get_current_user).

    Returns:
        dict: response
    """

    if not current_user:
        return {"message": "Invalid user"}

    try:
        content = f"""
        Drone: {drone_name}
        location: {location}
        type: {alarm_type}
        notes: {notes}
        """

        sub_path = f"{alarm_location}/{str(datetime.now())}"

        if not os.path.exists(sub_path):
            os.makedirs(sub_path)
        with open(f"{sub_path}/info.txt", "w+") as file_object:
            file_object.write(content)
        file_location = f"{sub_path}/{file.filename}"
        with open(file_location, "wb+") as file_object:
            file_object.write(file.file.read())
        print("CRRRRRRR")
        return {"message": "Alarmierung erhalten"}
    except Exception as err:
        print(err)
        return {"message": "Alarmierung fehlgeschlagen"}


@router.get("/alarm/get-all/", status_code=status.HTTP_200_OK)
async def get_incidents(current_user: User = Depends(get_current_user)):
    """API cal te get all incidents

    Args:
        current_user (User, optional): current user. Defaults to Depends(get_current_user).

    Returns:
        Alarm[]: list of alarms
    """
    alarms = []
    return alarms
    