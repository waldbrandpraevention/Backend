"""api tests"""
import datetime
import os
import cProfile
from fastapi import HTTPException
import pytest
from api.routers import zones,users,drones
from api.routers.territories import read_territories,read_territory
from database import drone_events_table, zones_table, drone_updates_table, drone_updates_table
from database import territories_table
from database.spatia import spatiageostr_to_geojson
from database.territories_table import get_orga_area

def test_improvements():
    """test.
    """
    polygon = territories_table.get_orga_area(1)

    print(datetime.datetime.now())
    dat = drone_updates_table.get_drone_updates(polygon=polygon,
                                              drone_id=1,
                                              get_coords_only=True)
    print(datetime.datetime.now())
    dat = drone_updates_table.get_drone_updates(orga_id=1,
                                              drone_id=1,
                                              get_coords_only=True)
    print(datetime.datetime.now())
    dat = drone_updates_table.get_drone_updates(polygon=polygon,
                                              drone_id=1,
                                              get_coords_only=True)
    print(datetime.datetime.now())
    dat = drone_updates_table.get_drone_updates(orga_id=1,
                                              drone_id=1,
                                              get_coords_only=True)
    print(datetime.datetime.now())
    cProfile.run('test_improvements()',sort='tottime')


@pytest.mark.asyncio
async def test_zones():
    """zone api tests.
    """
    #fetched = zones_table.get_zones()
    user = users.get_user(os.getenv("ADMIN_MAIL"))
    territories = await read_territories(user)
    assert len(territories) == 1
    with pytest.raises(HTTPException):
        await read_territory(0,user)
    territory = await read_territory(1,user)
    assert territory.name == 'Landkreis Potsdam-Mittelmark'
    orga_area = get_orga_area(1)
    orga_geo = spatiageostr_to_geojson(orga_area)
    assert orga_geo == territory.geo_json


    zones_arr = await zones.get_all_zones(user.organization.id)
    demo_distr = os.getenv("DEMO_DISTRICT")
    for fetched in zones_arr:
        assert fetched.district == demo_distr, 'Wrong Zone linked.'

    index = len(zones_arr)-1
    zone = await zones.read_zone(zones_arr[index].id,user)
    assert zone == zones_arr[index]
    count = await zones.get_zone_count(user.organization.id)
    assert len(zones_arr) == count

@pytest.mark.asyncio
async def test_drones():
    """drone api tests
    """
    user = users.get_user(os.getenv("ADMIN_MAIL"))
    drone = await drones.read_drone(drone_id=1,current_user=user)
    zone = zones_table.get_zone(drone.zone_id)
    with pytest.raises(HTTPException):
        await drones.read_drone_events(current_user=user,zone_id=-1)

    try:
        now = datetime.datetime.now()
        zone_events = await drones.read_drone_events(current_user=user,zone_id=zone.id)
        diff = datetime.datetime.now()-now
        print(diff)
    except HTTPException:
        print('No events in zone')
        zone_events = None
    
    zone_updates = await drones.read_drone_route(current_user=user,zone_id=zone.id)
    assert zone_events == zone.events
    assert zone_updates[0].timestamp == zone.last_update
    drone_events_table.insert_demo_events(
                                            zone.lon,
                                            zone.lat,
                                            1,
                                            True
                                            )
    drone_events_table.insert_demo_events(
                                            zone.lon,
                                            zone.lat,
                                            2,
                                            True
                                            )
    
    polygon = territories_table.get_orga_area(1)
    now = datetime.datetime.now()
    drone_routes = drone_updates_table.get_drone_updates(polygon=polygon,get_coords_only=True)
    diff = datetime.datetime.now()-now
    print(diff)
    now = datetime.datetime.now()
    drone_routes_two = drone_updates_table.get_drone_updates(orga_id=1,get_coords_only=True)
    diff = datetime.datetime.now()-now
    print(diff)
    assert drone_routes == drone_routes_two
    with pytest.raises(HTTPException):
        await drones.read_drone_route(current_user=user,zone_id=zone.id,drone_id=-1)
    zone_copunt = await drones.read_drones_count(current_user=user,zone_id=zone.id)
    assert zone_copunt == zone.drone_count
    drone_events_table.insert_demo_events(
                                            8.66697,
                                            49.54887,
                                            1,
                                            True
                                            )
    zone_copunt = await drones.read_drones_count(current_user=user,zone_id=zone.id)
    assert zone_copunt == zone.drone_count-1
    d1events = await drones.read_drone_events(current_user=user,drone_id=1)
    allevents = await drones.read_drone_events(current_user=user)

    #assert len(d1events) < len(allevents)
    drone_events_table.insert_demo_events(
                                            zone.lon,
                                            zone.lat,
                                            1,
                                            True
                                            )


@pytest.mark.asyncio
async def test_users():
    """user api tests
    """
    adminmail = os.getenv("ADMIN_MAIL")
    user = users.get_user(adminmail)
    first_name = f'{user.first_name}s'
    last_name = f'{user.last_name}s'
    email = 'Hans@admin.org'

    newmail = 'mailtest66@mail.de'

    await users.register(email=newmail,
                         password='test09Tpw',
                         first_name='testusers',
                         last_name='huhududu',
                         organization=os.getenv("ADMIN_ORGANIZATION"))
    newuser = users.get_user(newmail)
    await users.delete_users(newuser.id,user)

    await users.update_user_info(current_user=user,first_name=first_name,last_name=last_name)
    updated = users.get_user(adminmail)
    assert updated.first_name == first_name
    assert updated.last_name == last_name

    verified = not updated.email_verified
    await users.admin_update_user_info(
        update_user_id=user.id,
        current_user=updated,
        email_verified=verified,#
        email=email
    )
    updated = users.get_user(email)
    assert updated.first_name == first_name
    assert updated.last_name == last_name
    assert updated.email == email
    assert updated.email_verified == verified

    await users.update_user_info(current_user=updated,
                                 email=adminmail,
                                 first_name='Admin',
                                 last_name='Admin')
