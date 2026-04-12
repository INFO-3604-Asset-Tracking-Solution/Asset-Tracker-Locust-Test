from App.models import Building
from App.database import db
from App.controllers.floor import *

def create_building(building_id, building_name):
    new_building = Building(building_id=building_id, building_name=building_name)
    db.session.add(new_building)
    db.session.commit()
    return new_building

def get_building(building_id):
    return Building.query.get(building_id)

def edit_building(building_id, building_name):
    print(f"Starting edit_building with ID: {building_id}, Name: {building_name}")
    
    # Use a direct SQL UPDATE instead of ORM to avoid identity issues
    try:
        db.session.execute(
            db.update(Building)
            .where(Building.building_id == building_id)
            .values(building_name=building_name)
        )
        db.session.commit()
        # Get the updated building
        updated_building = get_building(building_id)
        print(f"Updated building: {updated_building.building_name}")
        return updated_building
    except Exception as e:
        db.session.rollback()
        print(f"Error updating building: {e}")
        return None

def get_all_building_json():
    buildings = Building.query.filter(Building.building_id != "DEFAULT").all()
    if not buildings:
        return[]
    buildings = [building.get_json() for building in buildings]
    return buildings

def update_building(building_id, building_name):
    building = get_building(building_id)
    if not building: return None
    building.building_name = building_name
    return db.session.commit()

def delete_building(building_id):
    building = get_building(building_id)
    if not building:
        return False  # Building not found

    try:
        db.session.delete(building)
        db.session.commit()
        return True  # Building deleted successfully
    except Exception as e:
        db.session.rollback()
        # Optionally log the error: log.error(f"Error deleting building: {e}")
        return False


