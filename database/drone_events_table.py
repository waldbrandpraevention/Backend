"""funcs to read and write on the drone_event table in database."""
import datetime
from typing import List

import pytz
from api.dependencies.classes import DroneEvent, EventType, FireRisk
from database.database import TIMEZONE, fetched_match_class
import database.database as db
from database import drone_updates_table

EVENT_ID = 'id'
DRONE_ID = 'drone_id'
TIMESTAMP = 'timestamp'
EVENT_TYPE = 'event_type'
CONFIDENCE = 'confidence'
PICTURE_PATH='picture_path'
CSV_FILE_PATH= 'csv_file_path'
COORDINATES= 'coordinates'

CREATE_DRONE_EVENT_TABLE = f'''CREATE TABLE drone_event
(
{EVENT_ID}     integer NOT NULL ,
{DRONE_ID}     integer NOT NULL ,
{TIMESTAMP}    timestamp NOT NULL ,
{EVENT_TYPE}   integer NOT NULL,
{CONFIDENCE}   integer NOT NULL,
{PICTURE_PATH}   text,
{CSV_FILE_PATH}  text ,
PRIMARY KEY ({EVENT_ID}),
FOREIGN KEY ({DRONE_ID}) REFERENCES drones (id)
);

CREATE INDEX drone_event_FK_1 ON drone_event ({DRONE_ID});
CREATE INDEX drone_event_AK_1 ON drone_event ({TIMESTAMP});
SELECT AddGeometryColumn('drone_event', '{COORDINATES}', 4326, 'POINT', 'XY');'''

CREATE_ENTRY = '''
INSERT INTO drone_event (drone_id,timestamp,coordinates,event_type,confidence,picture_path,csv_file_path) 
VALUES (? ,?,MakePoint(?, ?, 4326)  ,? ,?,?,?);'''

GET_ENTRY = '''
SELECT drone_event.id, drone_id,timestamp, X(coordinates), Y(coordinates),event_type,confidence,picture_path,csv_file_path, zones.id
FROM drone_event
LEFT JOIN zones ON ST_Intersects(zones.area, coordinates)
JOIN territory_zones ON zones.id = territory_zones.zone_id
JOIN territories ON territories.id = territory_zones.territory_id
{}
ORDER BY timestamp DESC;'''

GET_EVENT_IN_ZONE = '''
SELECT drone_event.id,drone_id,timestamp, X(coordinates), Y(coordinates),event_type,confidence,picture_path,csv_file_path, zones.id
FROM drone_event
JOIN zones ON ST_Intersects(zones.area, coordinates)
AND timestamp > ? AND timestamp < ?;'''

GET_EVENT_BY_ID = '''
SELECT drone_event.id,drone_id,timestamp, X(coordinates), Y(coordinates),event_type,confidence,picture_path,csv_file_path, zones.id
FROM drone_event
JOIN zones ON ST_Intersects(zones.area, coordinates)
AND drone_event.id = ?;'''


def create_drone_event_entry(drone_id: int,
                             timestamp: datetime.datetime,
                             longitude: float,
                             latitude: float,
                             event_type: int,
                             confidence: int,
                             picture_path: str | None,
                             csv_file_path: str | None) -> bool:
    """store the data sent by the drone.

    Args:
        drone_id (int): id of the drone.
        timestamp (datetime.datetime): datime timestamp of the event.
        longitude (float): longitute of the event's location.
        latitude (float): latitude of the event's location.
        picture_path (str | None): path to the folder containing the events pictures.
        csv_file_path (str | None): path to the folder containing the events csv files.

    Returns:
        bool: True for success, False if something went wrong.
    """

    inserted_id = db.insert(CREATE_ENTRY,
                            (drone_id,
                            timestamp,
                            longitude,
                            latitude,
                            event_type,
                            confidence,
                            picture_path,
                            csv_file_path))
    if inserted_id is not None:
        return True
    return False


def get_event_by_id(event_id: int) -> DroneEvent | None:
    """get the requested drone just by the id

    Args:
        name (str): name of that drone.

    Returns:
        Drone | None: the drone obj or None if not found.
    """
    fetched_event = db.fetch_one(GET_EVENT_BY_ID, (event_id,))
    return get_obj_from_fetched(fetched_event)

def get_drone_event(drone_id: int = None,
                    zone_id: int = None,
                    org_id: int = None,
                    polygon: str=None,
                    after: datetime.datetime = None,
                    before: datetime.datetime = None
                    ) -> List[DroneEvent] | None:
    """fetches all entrys that are within the choosen timeframe.
    If only drone_id is set, every entry will be fetched.

    Args:
        drone_id (int): the id of the drone.
        after (datetime.datetime): fetches everything after this date (not included)
        before (datetime.datetime): fetches everything before this date (not included)

    Returns:
        List[DroneData]: List with the fetched data.
    """
    sql_arr, tuple_arr = drone_updates_table.gernerate_drone_sql(polygon,org_id ,zone_id,drone_id, after, before)

    sql = db.add_where_clause(GET_ENTRY, sql_arr)

    fetched_data = db.fetch_all(
        sql, tuple(tuple_arr)
        )

    if fetched_data is None:
        return None

    output = []

    for drone_event in fetched_data:
        droneevent_obj = get_obj_from_fetched(drone_event)
        if droneevent_obj:
            output.append(droneevent_obj)
    return output

def get_obj_from_fetched(fetched_dronedata) -> DroneEvent | None:
    """generating DroneData objects with the fetched data.

    Args:
        fetched_dronedata: the fetched data from the sqlite cursor.

    Returns:
        DroneData| None: the generated object.
    """
    if fetched_match_class(DroneEvent, fetched_dronedata):

        try:
            longitude = float(fetched_dronedata[3])
            latitude = float(fetched_dronedata[4])
        except ValueError:
            longitude, latitude = None, None

        try:
            eventtype = EventType(fetched_dronedata[5])
        except ValueError:
            eventtype = None

        try:
            timestamp:datetime.datetime = fetched_dronedata[2]
            if timestamp is not None:
                timestamp = timestamp.astimezone(pytz.timezone(TIMEZONE))
        except ValueError:
            timestamp = fetched_dronedata[2]

        drone_data_obj = DroneEvent(
            id=fetched_dronedata[0],
            drone_id=fetched_dronedata[1],
            timestamp=timestamp,
            lon =longitude,
            lat =latitude,
            event_type=eventtype,
            confidence=fetched_dronedata[6],
            picture_path=fetched_dronedata[7],
            csv_file_path=fetched_dronedata[8],
            zone_id=fetched_dronedata[9]
        )
        return drone_data_obj
    return None


def calculate_firerisk(events: List[DroneEvent]) -> tuple[FireRisk,FireRisk,FireRisk]:
    """calculates the firerisk, based on the events fire/smoke confidences.

    very low        rauch: >5 feuer: >0
    low             rauch:>40 feuer: > 10
    middle          rauch: >60 feuer: >30
    high            rauch: >80 feuer: >70
    very high       rauch: >90 feuer: >90
    Args:
        events (List[DroneEvent]): list of drone events.

    Returns:
        tuple[FireRisk,FireRisk,FireRisk]: tuple with the calculated firerisk. (gernal, fire, smoke)
    """
    smokerisk= 0
    firerisk = 0
    for event in events:
        if event.event_type == EventType.SMOKE:
            if smokerisk < event.confidence:
                smokerisk = event.confidence
        else:
            if firerisk < event.confidence:
                firerisk = event.confidence

    try:
        calculated_enum = round(smokerisk/100 * 4)
        calculated_enum = min(calculated_enum, 4)
        smoke_risk = FireRisk(calculated_enum)
    except TypeError:
        smoke_risk = None

    try:
        calculated_enum = round(firerisk/100 * 4)
        calculated_enum = min(calculated_enum, 4)
        fire_risk = FireRisk(calculated_enum)
    except TypeError:
        fire_risk = None

    if smokerisk > 90 or firerisk > 90:
        return FireRisk.VERY_HIGH, fire_risk, smoke_risk

    if smokerisk > 80 or firerisk > 70:
        return FireRisk.HIGH, fire_risk, smoke_risk

    if smokerisk > 60 or firerisk > 30:
        return FireRisk.MIDDLE, fire_risk, smoke_risk

    if smokerisk > 40 or firerisk > 10:
        return FireRisk.LOW, fire_risk, smoke_risk

    return FireRisk.VERY_LOW, fire_risk, smoke_risk
