from .user import create_user
from App.controllers.asset import *
from App.controllers.assetassignment import *
from App.controllers.assignee import *
from App.controllers.building import *
from App.controllers.floor import *
from App.controllers.provider import *
from App.controllers.room import *
from App.controllers.scanevent import *
from datetime import datetime
from App.database import db
from sqlalchemy import inspect

from sqlalchemy import inspect # Add this import
from App.models import Asset, ScanEvent, AssetAssignment # Import models used for deletion

def initialize():
    print("--- Running Database Initialization ---")
    inspector = inspect(db.engine) # Get an inspector object

    # Explicitly delete data in reverse order of dependencies IF tables exist
    # This helps avoid foreign key constraint errors during drop_all
    try:
        if inspector.has_table(ScanEvent.__tablename__):
            print(f"Attempting to delete data from {ScanEvent.__tablename__}...")
            num_deleted = db.session.query(ScanEvent).delete()
            db.session.commit()
            print(f"Deleted {num_deleted} records from {ScanEvent.__tablename__}.")
        else:
            print(f"Table {ScanEvent.__tablename__} does not exist, skipping delete.")

        if inspector.has_table(AssetAssignment.__tablename__): # Add for AssetAssignment
            print(f"Attempting to delete data from {AssetAssignment.__tablename__}...")
            num_deleted = db.session.query(AssetAssignment).delete()
            db.session.commit()
            print(f"Deleted {num_deleted} records from {AssetAssignment.__tablename__}.")
        else:
            print(f"Table {AssetAssignment.__tablename__} does not exist, skipping delete.")

        if inspector.has_table(Asset.__tablename__):
            print(f"Attempting to delete data from {Asset.__tablename__}...")
            num_deleted = db.session.query(Asset).delete()
            db.session.commit()
            print(f"Deleted {num_deleted} records from {Asset.__tablename__}.")
        else:
            print(f"Table {Asset.__tablename__} does not exist, skipping delete.")

        # Add similar blocks for other tables with potential dependencies if needed

    except Exception as e:
        db.session.rollback()
        print(f"!!! Warning: Error during explicit data deletion: {e}. Proceeding with drop_all...")

    # Now try dropping all tables
    try:
        print("Attempting db.drop_all()...")
        # db.reflect() # Sometimes helps metadata refresh, uncomment if needed
        db.drop_all()
        db.session.commit() # Commit after drop
        print("db.drop_all() completed.")
    except Exception as e:
        db.session.rollback() # Rollback on error
        print(f"!!!!!! ERROR during db.drop_all(): {e}")
        # It's often better to stop if drop_all fails
        # return

    # Proceed with creation
    try:
        print("Attempting db.create_all()...")
        db.create_all()
        db.session.commit() # Commit after create
        print("db.create_all() completed.")

        # Verify asset table is empty
        asset_count = db.session.query(Asset).count()
        print(f"--- Asset count immediately after db.create_all(): {asset_count} ---")
        if asset_count != 0:
             print("!!!!!! CRITICAL WARNING: Asset table is NOT empty after create_all! Something is wrong with drop/create.")

    except Exception as e:
        db.session.rollback() # Rollback on error
        print(f"!!!!!! ERROR during db.create_all(): {e}")
        return # Stop if create fails

    # Add default data (user, rooms, etc.)
    try:
        print("Adding default user...")
        create_user('bob@gmail.com','bob marley', 'bobpass') # Ensure this doesn't fail
        print("Default user added.")

        # ... (rest of your default data creation: buildings, floors, rooms, assignees) ...
        # Make sure these use IDs that don't conflict if hardcoded (e.g., use strings '1', '2' if IDs are strings)
        print("Adding default buildings...")
        create_building("1", "Main Building") # Use strings if IDs are strings
        create_building("2", "Annex Building")
        print("Default buildings added.")

        print("Adding default floors...")
        create_floor("1", "1", "1st Floor")
        create_floor("2", "2", "2nd Floor")
        print("Default floors added.")


        print("Adding default rooms...")
        create_room("1", "1", "Asset Room: 101")
        create_room("2", "2", "Asset Room: 201")
        print("Default rooms added.")

        print("Adding default assignees...")
        # Assuming assignee IDs are auto-incrementing integers
        assignee1 = create_assignee("John", "Doe", "john.doe@mail.com", "1")
        assignee2 = create_assignee("Jane", "Smith", "jane.smith@mail.com", "2")
        print(f"Default assignees added (IDs: {assignee1.id if assignee1 else 'ERR'}, {assignee2.id if assignee2 else 'ERR'}).")
        
        print("Adding additional assignees for sample data...")
        assignees_created_count = 0
        for i in range(3, 21):
            # Check if an assignee with this ID somehow already exists (unlikely after drop/create)
            if not Assignee.query.get(i):
                temp_assignee = create_assignee(
                    fname=f"SampleFirst{i}",
                    lname=f"SampleLast{i}",
                    email=f"sample{i}@example.com",
                    room_id=str((i % 2) + 1) # Assign to room 1 or 2 alternately
                )
                if temp_assignee:
                    assignees_created_count += 1
                else:
                    print(f"Warning: Could not create sample assignee {i}")
            else:
                print(f"Info: Assignee with ID {i} already exists, skipping creation.")
        print(f"Added {assignees_created_count} additional sample assignees.")

        print("Ensuring default building/floor/room exist...")
        ensure_defaults() # Call ensure_defaults here
        print("ensure_defaults() completed.")

        print("--- Database Initialization Finished Successfully ---")

    except Exception as e:
        db.session.rollback()
        print(f"!!!!!! ERROR during default data creation: {e}")


def ensure_defaults():
    """
    Ensures default data exists without wiping existing data.
    This is safe to run in production.
    """
    inspector = inspect(db.engine)
    
    if not (inspector.has_table('building') and 
        inspector.has_table('floor') and 
        inspector.has_table('room') and 
        inspector.has_table('user')):
        # Tables don't exist yet, so don't try to add defaults
        return
    
    # Create default building if it doesn't exist
    default_building_id = "DEFAULT"
    default_building = get_building(default_building_id)
    if not default_building:
        default_building = create_building(default_building_id, "Default Building")
        print(f"Created default building: {default_building_id}")
    
    # Create default floor if it doesn't exist
    default_floor_id = "DEFAULT"
    default_floor = get_floor(default_floor_id)
    if not default_floor:
        default_floor = create_floor(default_floor_id, default_building_id, "Default Floor")
        print(f"Created default floor: {default_floor_id}")
    
    # Create unknown room if it doesn't exist
    unknown_room_id = "UNKNOWN"
    unknown_room = get_room(unknown_room_id)
    if not unknown_room:
        unknown_room = create_room(unknown_room_id, default_floor_id, "Unknown Room")
        print(f"Created unknown room: {unknown_room_id}")
    
    return {
        "building": default_building,
        "floor": default_floor, 
        "room": unknown_room
    }