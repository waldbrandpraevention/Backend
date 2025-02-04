""" Main file for the API. """
import datetime
import os
import sqlite3
import random
from threading import Thread
from typing import List
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware


from simulation.sim import simulate
from api.dependencies.authentication import get_password_hash
from api.dependencies.classes import UserWithSensitiveInfo, Zone
from api.routers import emails, users, zones, drones, simulation,territories, incidents
from database import (users_table,
                      organizations_table,
                      drones_table,
                      drone_events_table,
                      drone_updates_table,
                      zones_table)

from database.database import create_table, initialise_spatialite
from database.drone_events_table import CREATE_DRONE_EVENT_TABLE
from database.territory_zones_table import CREATE_TERRITORYZONES_TABLE, link_territory_zone
from database.territories_table import CREATE_TERRITORY_TABLE, create_territory
from database.drones_table import CREATE_DRONES_TABLE
from database.organizations_table import CREATE_ORGANISATIONS_TABLE
from database.users_table import CREATE_USER_TABLE
from database.zones_table import CREATE_ZONE_TABLE
from database.incidents import CREATE_INCIDENTS_TABLE

app = FastAPI(  title="KIWA",
                description="test")
app.include_router(users.router)
app.include_router(emails.router)
app.include_router(zones.router)
app.include_router(drones.router)
app.include_router(simulation.router)
app.include_router(territories.router)
app.include_router(incidents.router)

# CORS https://fastapi.tiangolo.com/tutorial/cors/
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def create_default_user():
    """Creates a default user if the environment variables are set."""
    # Save default user only if env var is set
    if os.getenv("ADMIN_MAIL") is not None \
            and os.getenv("ADMIN_PASSWORD") is not None \
            and os.getenv("ADMIN_ORGANIZATION") is not None:
        try:
            organization = organizations_table.create_orga(
                organame=os.getenv("ADMIN_ORGANIZATION"),
                orga_abb=os.getenv("ADMIN_ORGANIZATION")
                )
            if os.getenv("ADMIN_ORGANIZATION_TWO") is not None:
                organization_two = organizations_table.create_orga(
                    organame=os.getenv("ADMIN_ORGANIZATION_TWO"),
                    orga_abb=os.getenv("ADMIN_ORGANIZATION_TWO")
                    )
        except sqlite3.IntegrityError:
            organization = organizations_table.get_orga(os.getenv("ADMIN_ORGANIZATION"))

        create_user_helper(os.getenv("ADMIN_MAIL"),os.getenv("ADMIN_PASSWORD"),organization)
        if os.getenv("ADMIN_ORGANIZATION_TWO") is not None \
                and os.getenv("ADMIN_MAIL_TWO") is not None:
            organization_two = organizations_table.get_orga(os.getenv("ADMIN_ORGANIZATION_TWO"))
            create_user_helper(os.getenv("ADMIN_MAIL_TWO"),os.getenv("ADMIN_PASSWORD"),organization_two)

        print("user done")

def create_user_helper(mail,password,organization):
    """Helper function to create a user with the given parameters.

    Args:
        mail (str): email of the user
        pw (str): password of the user (not hashed)
        organization (str): organization of the user
    """
    if organization is None:
        print("organization not found")
        return

    hashed_pw = get_password_hash(password)
    user = UserWithSensitiveInfo(email=mail,
                                     first_name="Admin",
                                     last_name="Admin",
                                     hashed_password=hashed_pw,
                                     organization=organization,
                                     permission=2,
                                     disabled=0,
                                     email_verified=1)
    try:
        users_table.create_user(user)
    except sqlite3.IntegrityError:
        print(f'could not create user ({mail})')

def create_drone_events():
    """ Creates drone events for demo purposes.
        set demo events with env vars DEMO_LONG and DEMO_LAT
    """
    if os.getenv("DEMO_LONG") is not None \
            and os.getenv("DEMO_LAT") is not None:

        drones_table.create_drone(
                name='Trinity F01',
                drone_type="Unmanned Aerial Vehicle",
                cc_range=7.5,
                flight_range=100.0,
                flight_time=90.0
            )
        insert_demo_events(
                            float(os.getenv("DEMO_LONG")),
                            float(os.getenv("DEMO_LAT"))
                            )
    print("drone_events done")

def load_zones_from_geojson():
    """ store all zones from geojson file in the database.
        link the zones, of the DEMO_DISTRICT env var, to the territory of the ADMIN_ORGANIZATION.
    """
    if os.getenv("GEOJSON_PATH") is not None:
        main_path = os.path.realpath(os.path.dirname(__file__))
        path_to_geo = os.path.join(main_path,os.getenv("GEOJSON_PATH"))
        added_zones = zones_table.add_from_geojson(path_to_geo)
        print(f'Zones added: {added_zones}')

        if os.getenv("DEMO_DISTRICT") is not None \
                and os.getenv("ADMIN_ORGANIZATION") is not None:
            fetched_zones = zones_table.get_zone_of_district(os.getenv("DEMO_DISTRICT"))
            create_territory_link_zones(1,os.getenv("DEMO_DISTRICT"),fetched_zones)

            if os.getenv("DEMO_DISTRICT_TWO") is not None:
                fetched_zones = zones_table.get_zone_of_district(os.getenv("DEMO_DISTRICT_TWO"))
                create_territory_link_zones(1,os.getenv("DEMO_DISTRICT_TWO"),fetched_zones)

            if os.getenv("DEMO_DISTRICT_THREE") is not None \
                and os.getenv("ADMIN_ORGANIZATION_TWO") is not None:
                fetched_zones = zones_table.get_zone_of_district(os.getenv("DEMO_DISTRICT_THREE"))

                create_territory_link_zones(2,os.getenv("DEMO_DISTRICT_THREE"),fetched_zones)


            print("zones linked")

def create_territory_link_zones(orga_id,name,fetched_zones:List[Zone]):
    """ create a territory for an organization.
        Args:
            orga_id (int): id of the organization
            name (str): name of the territory
            fetched_zones (list): list of zones to link to the territory
    """
    try:
        territorry_id = create_territory(orga_id=orga_id,name=name)
    except sqlite3.IntegrityError:
        print('couldnt create territory')
        return

    for zone in fetched_zones:
        try:
            link_territory_zone(territorry_id,zone.id)
        except sqlite3.IntegrityError:
            print(f'couldnt link {zone.name} to the territory')

def insert_demo_events(long: float, lat: float, droneid = 1, ignore_existing: bool = False):
    """insert 5 demo drone events.

    Args:
        long (float): long of the coordinate.
        lat (float): lat of the coordinate.
    """
    if not ignore_existing:
        update = drone_updates_table.get_latest_update(droneid)
        if update is not None:
            print('already created drone events.')
            return

    timestamp = datetime.datetime.utcnow()
    i = 0
    num_inserted = 0
    flight_range = 100
    flight_time =0
    while num_inserted < 4:
        event_rand = random.randint(0, 2)
        long_rand = random.randint(0, 100)/100000
        lat_rand = random.randint(0, 100)/100000
        long= long+long_rand
        lat = lat+lat_rand
        flight_range-=2
        flight_time+=10
        drone_updates_table.create_drone_update(
            drone_id=droneid,
            timestamp=timestamp,
            longitude=long,
            latitude=lat,
            flight_range=flight_range,
            flight_time=flight_time
        )
        zones_table.set_update_for_coordinate(long, lat, timestamp)
        if event_rand > 0:
            confidence = random.randint(20, 90)

            drone_events_table.create_drone_event_entry(
                drone_id=droneid,
                timestamp=timestamp,
                longitude=long,
                latitude=lat,
                event_type=event_rand,
                confidence=confidence,
                picture_path='/data/events/1',
                csv_file_path=f'demo/path/{i}'
            )
            num_inserted += 1
        timestamp += datetime.timedelta(seconds=10)
        i += 1

def main():
    """ Initialise the database and create the tables.
        Create a default user if the environment variables are set.
        Create a default territory and link zones to it, if the environment variables are set.
    """
    initialise_spatialite()
    create_table(CREATE_ORGANISATIONS_TABLE)
    create_table(CREATE_USER_TABLE)
    create_table(CREATE_ZONE_TABLE)
    create_table(CREATE_DRONES_TABLE)
    create_table(drone_updates_table.CREATE_DRONE_DATA_TABLE)
    create_table(CREATE_DRONE_EVENT_TABLE)
    create_table(CREATE_TERRITORY_TABLE)
    create_table(CREATE_TERRITORYZONES_TABLE)
    create_table(CREATE_INCIDENTS_TABLE)
    create_default_user()
    load_zones_from_geojson()
    create_drone_events()
    run_sim = os.getenv("RUN_SIMULATION")
    if run_sim == 'True':
        try:
            simulation_thread = Thread(target = simulate)
            simulation_thread.start()
        except Exception as err: # pylint: disable=broad-exception-caught
            print(err)

main()

@app.get("/")
async def root():
    """ Root function to check if the server is running."""
    number_one = random.randint(0,100)
    number_two = random.randint(0,100)
    raise HTTPException(
                status_code=status.HTTP_418_IM_A_TEAPOT,
                detail=f"""Random addition: {number_one} + {number_one} = {number_one + number_two}""",
            )

@app.get("/test")
async def test(test_input: str):
    """ Test function to check if the server is running."""
    return {"message": test_input}
