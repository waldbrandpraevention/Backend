""" This file contains all the classes used in the API. """
import datetime
from typing import List
from enum import Enum
from datetime import datetime
from pydantic import BaseModel

class Token(BaseModel):
    """Token class."""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """TokenData class"""
    email: str | None = None

class Permission(Enum):
    """Permission class with the following values:
    1: user
    2: admin
    3: third party."""
    USER = 1
    ADMIN = 2
    THIRD_PARTY = 3

class SettingsType(int,Enum):
    """Enum that defines the type of the stored setting.
    Can be one of the following:
    INTEGER,
    STRING,
    JSON"""
    INTEGER=0
    STRING =1
    JSON =2

class Setting(BaseModel):
    """Setting class. Defines the setting itself."""
    id: int|None =None
    name: str|None =None
    description: str|None =None
    default_value: str|int|dict|None =None
    type: SettingsType|None=None

class UserSetting(BaseModel):
    """UserSetting class. Defines the setting for a specific user."""
    id: int|None =None
    user_id: int|None=None
    name: str|None =None
    description: str|None =None
    value: str|int|dict|None=None
    type: SettingsType|None=None

class Organization(BaseModel):
    """Organization class"""
    id: int | None = None
    name: str | None = None
    abbreviation: str | None = None

class User(BaseModel):
    """User class excluding sensitive data."""
    id: int | None = None
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    organization: Organization | None = None
    permission: Permission | None = None
    disabled: bool | None = None
    email_verified: bool

class UserWithSensitiveInfo(User):
    """User class including sensitive data."""
    hashed_password: str | None = None

class FireRisk(Enum):
    """Firerisk class with the following values:
    0: very low,
    1: low,
    2: middle,
    3: high,
    4: very high."""
    VERY_LOW = 0
    LOW = 1
    MIDDLE = 2
    HIGH = 3
    VERY_HIGH = 4

class Alert(BaseModel):
    """ Alert class.  """
    content: str | None = None
    date: datetime | None = None

class Drone(BaseModel):
    """ Drone class.
        name: name of the aerial vehicle according to manufacturer,
        type: type of the aerial vehicle,
        flight_range: maximum flight range of the aerial vehicle in [km],
        cc_range: maximum command and control range of the aerial vehicle in [km],
        flight_time: maximum flight time of the aerial vehicle in [minutes],
        last_update: last update of the drone,
        zone: zone the drone is currently in."""
    id: int | None = None
    name: str | None = None
    type: str | None = None
    flight_range: float | None = None
    cc_range: float | None = None
    flight_time: float | None = None
    last_update: datetime | None = None
    zone_id: int | None = None

class DroneWithRoute(Drone):
    """Done including its route.

    Args:
        Drone (geojson): geojsnon including the points.
    """
    route : dict | None = None

class DroneUpdate(BaseModel):
    """ DroneUpdate class. Contains all the information about a drone update."""
    id: int | None = None
    drone_id :int | None = None
    timestamp :datetime | None = None
    lon :float | None = None
    lat:float | None = None
    flight_range: float | None = None
    flight_time: float | None = None
    zone_id :int| None = None

class DroneUpdateWithRoute(DroneUpdate):
    """ DroneUpdate including its route.

    Args:
        Drone (geojson): geojsnon including the points.
    """
    geojson : dict | None = None

class EventType(Enum):
    """ EventType class. Defines the type of an event."""
    SMOKE = 1
    FIRE = 2

class Incident(BaseModel):
    """ Incident class."""
    id:int | None = None
    drone_name: str | None = None
    location: str | None = None
    alarm_type: str | None = None
    notes: str | None = None
    timestamp :datetime | None = None

class DroneEvent(BaseModel):
    """DroneEvent class. Contains all the information about a drone event."""
    id :int | None = None
    drone_id :int | None = None
    timestamp :datetime | None = None
    lon :float | None = None
    lat :float | None = None
    event_type: EventType | None = None
    confidence: int | None = None
    picture_path :str| None = None
    csv_file_path :str| None = None
    zone_id :int| None = None

class Zone(BaseModel):
    """ Zone class. Contains all the information about a zone. """
    id: int | None = None
    name: str | None = None
    federal_state: str | None = None
    district: str | None = None
    events: List[DroneEvent] | None = None
    dwd_fire_risk: FireRisk | None = None
    ai_fire_risk: FireRisk | None = None
    ai_fire_detection: FireRisk | None = None
    ai_smoke_detection: FireRisk | None = None
    geo_json: dict | None = None
    lon :float | None = None
    lat :float | None = None
    drone_count: int | None = None
    last_update: datetime | None = None

class Territory(BaseModel):
    """ Territory class. Contains all the information about a territory. """
    id: int | None = None
    name: str | None = None
    orga_id :int | None = None
    description: str | None = None

class TerritoryWithZones(Territory):
    """ Territory class. Contains all the information about a territory. """
    dwd_fire_risk: FireRisk | None = None
    ai_fire_risk: FireRisk | None = None
    drone_count: int | None = None
    last_update: datetime | None = None
    zone_count: int | None = None
    geo_json: dict | None = None
    lon : float | None = None
    lat : float | None = None

class WindInfo(BaseModel):
    """Wind inforamtion"""
    lat: float
    lon: float
    wind_speed: float | None = None
    wind_direction: float | None = None


class DroneForSimulation(BaseModel):
    """Drone for the simulation"""
    drone: Drone | None = None
    token: str
    geo_json: dict
    speed: float
    direction: tuple[float,float] #vector with length 1
    lat: float
    lon: float
