# ... (existing imports) ...
from datetime import datetime, timedelta
from App.controllers.room import get_room
from App.models import Asset, Room
import os, csv
from App.controllers.assignee import *
from App.controllers.scanevent import add_scan_event
from flask_jwt_extended import current_user
from sqlalchemy.exc import IntegrityError # Import IntegrityError

from App.database import db
from App.models.room import Room
from App.models.scanevent import ScanEvent

# --- Existing functions (get_asset, get_all_assets, etc.) ---
def get_asset(id):
    return Asset.query.filter_by(id=id).first()

def get_all_assets():
    return Asset.query.all()

def get_all_assets_by_room_id(room_id):
    assets = Asset.query.filter_by(room_id=room_id).all()
    return assets

def get_all_assets_json():
    assets = get_all_assets()
    if not assets:
        return[]
    assets = [asset.get_json() for asset in assets]
    return assets

def get_all_assets_by_room_json(room_id):
    assets = get_all_assets_by_room_id(room_id)
    if not assets:
        return[]
    assets = [asset.get_json() for asset in assets]
    return assets

def add_asset(id, description, model, brand, serial_number, room_id, last_located, assignee_id, last_update, notes):
    # Check if room exists
    existing_room = Room.query.filter_by(room_id=room_id).first()
    if existing_room is None:
        # Room doesn't exist, use the "UNKNOWN" room
        print(f"Warning: Room {room_id} not found for asset {id}. Assigning to UNKNOWN.")
        room_id = "UNKNOWN"
        last_located = room_id  # Also update last_located to match the unknown room
        status = "Unassigned"
    else:
        # Room exists, set status normally
        status = "Misplaced"
        if last_located == room_id:
            status = "Good"

    newAsset = Asset(id, description, model, brand, serial_number, room_id, last_located, assignee_id, last_update, notes, status)

    try:
        db.session.add(newAsset)
        db.session.commit()
        return newAsset
    except IntegrityError: # Catch specific duplicate key error
        db.session.rollback()
        print(f"Error: Asset with ID {id} already exists.")
        return None
    except Exception as e: # Catch other potential errors
        db.session.rollback()
        print(f"Error adding asset {id}: {e}")
        return None

# --- (set_last_located, set_status, upload_csv, delete_asset, update_asset_location remain the same) ---
def set_last_located(id,last_located):
    new_asset = get_asset(id)
    new_asset.last_located = last_located

def set_status(id):
    new_asset= Asset.query.filter_by(id = id).first()
    if new_asset.room_id == new_asset.last_located :
        new_asset.status = "Good"
    else:
        new_asset.status = "Misplaced"

    return new_asset


def upload_csv(file_path):
    results = {
        'success': False,
        'total': 0,
        'imported': 0,
        'skipped': 0,
        'errors': []
    }

    try:
        with open(file_path, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)


            expected_columns = ["Item", "Asset Tag", "Model", "Brand", "Serial Number",
                               "Location", "Condition", "Assignee"]
            actual_columns = [col.strip() for col in reader.fieldnames]

            missing_columns = [col for col in expected_columns if col not in actual_columns]
            if missing_columns:
                results['errors'].append(f"Missing required columns: {', '.join(missing_columns)}")
                return results

            for row_num, row in enumerate(reader, start=2):  # Start at 2 to account for header row
                results['total'] += 1

                try:
                    row = {key.strip(): (value.strip() if isinstance(value, str) else value)
                          for key, value in row.items()}

                    new_item = row.get('Item', '')
                    new_id = row.get('Asset Tag', '')
                    new_model = row.get('Model', '')
                    new_brand = row.get('Brand', '')
                    new_sn = row.get('Serial Number', '')
                    new_room = row.get('Location', '')
                    new_condition = row.get('Condition', 'Good')  # Get condition from CSV
                    new_assignee = row.get('Assignee', '')
                    new_last = datetime.now()
                    new_notes = None  # Default to None

                    if not new_id:
                        results['errors'].append(f"Row {row_num}: Missing Asset Tag (required)")
                        results['skipped'] += 1
                        continue

                    if not new_item:
                        results['errors'].append(f"Row {row_num}: Missing Item description (required)")
                        results['skipped'] += 1
                        continue

                    existing_room = Room.query.filter_by(room_id=new_room).first()
                    if existing_room is None:
                        # Room doesn't exist, log that it's being redirected to Unknown Room
                        results['errors'].append(f"Row {row_num}: Location '{row.get('Location', '')}' not found, assigned to Unknown Room")

                    # Let add_asset handle the room assignment and status determination
                    new_asset = add_asset(
                        id=new_id,
                        description=new_item,
                        model=new_model,
                        brand=new_brand,
                        serial_number=new_sn,
                        room_id=new_room,
                        last_located=new_room,  # Initially set last_located to match room_id
                        assignee_id=new_assignee,
                        last_update=new_last,
                        notes=new_notes
                    )

                    if new_asset:
                        # If the condition from CSV doesn't match the calculated status,
                        # override it (e.g., for "Missing" or "Lost" conditions)
                        if new_condition not in ["Good", "Misplaced", "Unassigned", "Found"]: # Added Found
                            new_asset.status = new_condition
                            db.session.commit()

                        results['imported'] += 1
                    else:
                        # Check if the error was due to duplicate ID
                        if f"Asset with ID {new_id} already exists." in str(db.session.rollback): # Approximate check
                             results['errors'].append(f"Row {row_num}: Asset Tag '{new_id}' already exists, skipped.")
                        else:
                             results['errors'].append(f"Row {row_num}: Failed to add asset to database.")
                        results['skipped'] += 1


                except IntegrityError as e:
                    db.session.rollback()
                    # Check if it's specifically a duplicate primary key error
                    # This check depends slightly on the DB engine, but often contains 'UNIQUE constraint' or 'Duplicate entry'
                    error_str = str(e).lower() # Convert error to lowercase string for easier checking
                    if 'unique constraint' in error_str \
                    or 'duplicate entry' in error_str \
                    or 'violates unique constraint' in error_str \
                    or (hasattr(e, 'orig') and 'duplicate key value violates unique constraint' in str(e.orig).lower()): # More specific check for psycopg2
                        results['errors'].append(f"Row {row_num}: Asset Tag '{row.get('Asset Tag', '')}' already exists, skipped.")
                    else:
                        # Other type of IntegrityError (e.g., foreign key violation if a room didn't exist and wasn't handled)
                        results['errors'].append(f"Row {row_num}: Database integrity error - {str(e)}")
                    results['skipped'] += 1
                except Exception as e:
                    db.session.rollback()
                    results['errors'].append(f"Row {row_num}: Error processing row - {str(e)}")
                    results['skipped'] += 1

            # Set success if at least one asset was imported
            results['success'] = results['imported'] > 0
            return results

    except Exception as e:
        results['errors'].append(f"File processing error: {str(e)}")
        return results


def delete_asset(id):
    asset = get_asset(id)
    if asset:
        try:
            # Check for related scan events before deleting
            scan_events = ScanEvent.query.filter_by(asset_id=id).count()
            if scan_events > 0:
                 # Option 1: Prevent deletion
                 # return False, f"Cannot delete asset {id}. It has associated scan history."

                 # Option 2: Delete scan events first (use with caution!)
                 ScanEvent.query.filter_by(asset_id=id).delete()
                 print(f"Warning: Deleted {scan_events} scan events associated with asset {id}.")


            db.session.delete(asset)
            db.session.commit()
            return True, f"Asset {id} was successfully deleted."
        except Exception as e: # Catch specific exceptions if needed
            db.session.rollback()
            return False, f"Failed to delete asset {id}. Error: {str(e)}"
    return False, f"Asset {id} does not exist."

def update_asset_location(asset_id, new_location, user_id=None):
    asset = get_asset(asset_id)
    if not asset:
        print(f"Error: Asset {asset_id} not found for location update.")
        return None

    # Store old status and location for changelog
    old_status = asset.status
    old_location_id = asset.last_located # Use last_located as the "from" location

    asset.last_located = new_location
    asset.last_update = datetime.now()

    # Set status based on whether the asset is in its *assigned* room
    if asset.room_id == new_location:
        asset.status = "Good"
    else:
        asset.status = "Misplaced" # Mark as misplaced if found outside its assigned room

    try:

        # Create a scan event to record this update
        old_room = get_room(old_location_id)
        new_room = get_room(new_location)
        old_room_name = old_room.room_name if old_room else f"Room {old_location_id}"
        new_room_name = new_room.room_name if new_room else f"Room {new_location}"

        notes = f"Asset found in {new_room_name}."
        if old_location_id != new_location:
             notes += f" Moved from {old_room_name}."
        if old_status != asset.status:
             notes += f" Status changed from {old_status} to {asset.status}."


        # Use the current_user's ID if user_id not provided
        if not user_id and current_user:
            user_id = current_user.id

        # If we still don't have a user_id, use a default (e.g., system update)
        if not user_id:
            user_id = "SYSTEM" # Or handle as an error if user context is mandatory

        scan_event = add_scan_event(
            asset_id=asset_id,
            user_id=user_id,
            room_id=new_location, # Log the room where it was scanned/found
            status=asset.status,
            notes=notes
        )
        if not scan_event:
             print(f"Warning: Failed to create scan event for asset {asset_id} update.")
             # Decide if this should cause a rollback or just a warning

        db.session.commit()
        return asset
    except Exception as e:
        print(f"Error updating asset location for {asset_id}: {e}")
        db.session.rollback()
        return None


# Function to mark assets as missing (from audit)

def mark_assets_missing(asset_ids, user_id=None, misplaced_threshold_days=30):
    processed_count = 0
    error_count = 0
    errors = []
    
    # Get current time for comparison
    current_time = datetime.now()
    # Calculate the threshold date
    threshold_date = current_time - timedelta(days=misplaced_threshold_days)
    
    if not user_id:
        if current_user:
            user_id = current_user.id
        else:
            user_id = "SYSTEM" # Or raise error if user is required

    # Collect all assets to update first to ensure batch processing works correctly
    assets_to_update = []
    scan_events_to_add = []

    for asset_id in asset_ids:
        asset = get_asset(asset_id)
        if asset:
            if asset.status == "Lost":
                # Don't override "Lost" status
                print(f"Info: Asset {asset_id} already marked as Lost, skipping.")
                error_count += 1
                errors.append(f"Asset {asset_id} already Lost.")
            elif asset.status == "Misplaced":
                # Check if the asset has been misplaced for longer than the threshold
                last_update_time = asset.last_update
                
                if last_update_time < threshold_date:
                    # Asset has been misplaced for too long, mark as missing
                    old_status = asset.status
                    asset.status = "Missing"
                    asset.last_update = current_time
                    
                    notes = f"Asset marked as Missing during audit. Previously misplaced for over {misplaced_threshold_days} days. Previous status: {old_status}."
                    scan_event_data = {
                        'asset_id': asset_id,
                        'user_id': user_id,
                        'room_id': asset.room_id,
                        'status': "Missing",
                        'notes': notes
                    }
                    
                    assets_to_update.append(asset)
                    scan_events_to_add.append(scan_event_data)
                    processed_count += 1
                else:
                    # Asset was recently misplaced, keep as misplaced
                    print(f"Info: Asset {asset_id} was recently misplaced (less than {misplaced_threshold_days} days ago), keeping status.")
                    error_count += 1
                    errors.append(f"Asset {asset_id} recently misplaced.")
            else:
                # For any other status, mark as missing
                old_status = asset.status
                asset.status = "Missing"
                asset.last_update = current_time
                
                notes = f"Asset marked as Missing during audit. Previous status: {old_status}."
                scan_event_data = {
                    'asset_id': asset_id,
                    'user_id': user_id,
                    'room_id': asset.room_id,
                    'status': "Missing",
                    'notes': notes
                }
                
                assets_to_update.append(asset)
                scan_events_to_add.append(scan_event_data)
                processed_count += 1
        else:
            errors.append(f"Asset {asset_id} not found.")
            error_count += 1

    try:
        if processed_count > 0:
            # Explicitly add all assets to the session
            for asset in assets_to_update:
                db.session.add(asset)
                
            # Create all scan events
            for event_data in scan_events_to_add:
                add_scan_event(**event_data)
                
            # Commit all changes at once
            db.session.commit()
            print(f"Successfully marked {processed_count} assets as missing")
        return processed_count, error_count, errors
    except Exception as e:
        db.session.rollback()
        print(f"Error committing missing assets update: {e}")
        # Add a general error if commit fails
        errors.append(f"Database commit error: {e}")
        return 0, len(asset_ids), errors # Assume all failed if commit fails
    
# --- (get_assets_by_status, get_discrepant_assets remain the same) ---
def get_assets_by_status(status):
    assets = Asset.query.filter_by(status=status).all()
    if not assets:
        return []
    assets_json = [asset.get_json() for asset in assets] # Corrected variable name
    return assets_json


def get_discrepant_assets():
    # Query for assets with status 'Missing' or 'Misplaced'
    assets = Asset.query.filter(Asset.status.in_(["Missing", "Misplaced"])).all()
    if not assets:
        return []
    assets_json = [asset.get_json() for asset in assets] # Corrected variable name
    return assets_json


# Function to mark a single asset as Lost
def mark_asset_lost(asset_id, user_id=None):
    asset = get_asset(asset_id)
    if not asset:
        print(f"Error: Asset {asset_id} not found for marking as Lost.")
        return None

    # Store old status for changelog
    old_status = asset.status

    # Check if already Lost
    if old_status == "Lost":
         print(f"Info: Asset {asset_id} is already marked as Lost.")
         return asset # Return the asset as is

    # Set status to Lost
    asset.status = "Lost"
    asset.last_update = datetime.now()

    # Determine user_id
    if not user_id:
        if current_user:
            user_id = current_user.id
        else:
            user_id = "SYSTEM" # Or handle error

    # Create a scan event to record this update
    notes = f"Asset marked as Lost. Previous status: {old_status}."

    scan_event = add_scan_event(
        asset_id=asset_id,
        user_id=user_id,
        room_id=asset.room_id, # Log against assigned room
        status="Lost",
        notes=notes
    )
    if not scan_event:
         print(f"Warning: Failed to create scan event for Lost asset {asset_id}.")
         # Decide if rollback is needed

    try:
        db.session.commit()
        return asset
    except Exception as e:
        print(f"Error marking asset {asset_id} as lost: {e}")
        db.session.rollback()
        return None

# Function to mark a single asset as Found
def mark_asset_found(asset_id, user_id=None, return_to_room=True, notes_prefix=""):
    """Marks an asset as Found.

    Args:
        asset_id: The ID of the asset.
        user_id: The ID of the user performing the action.
        return_to_room (bool): If True, sets last_located to match room_id.
                               If False, updates room_id to match last_located (reassigns).
        notes_prefix (str): Optional prefix for the scan event notes (used by bulk actions).

    Returns:
        Asset object if successful, None otherwise.
    """
    asset = get_asset(asset_id)
    if not asset:
        print(f"Error: Asset {asset_id} not found for marking as Found.")
        return None

    # Store old status and location for changelog
    old_status = asset.status
    old_location_id = asset.room_id # Assigned room before change
    found_location_id = asset.last_located # Where it was actually found/last seen

    # Determine action based on return_to_room flag
    if return_to_room:
        # Action: Return to assigned room
        asset.last_located = asset.room_id # Update last_located to match assigned room
        final_room_id = asset.room_id
        action_desc = "returned to assigned room"
    else:
        # Action: Reassign to current found location
        asset.room_id = asset.last_located # Update assigned room to match where it was found
        final_room_id = asset.last_located
        action_desc = f"reassigned to current location ({get_room(final_room_id).room_name if get_room(final_room_id) else final_room_id})"


    # Set status to Good
    asset.status = "Good"
    asset.last_update = datetime.now()


    # Determine user_id
    if not user_id:
        if current_user:
            user_id = current_user.id
        else:
            user_id = "SYSTEM" # Or handle error

    # Create scan event notes
    scan_notes = f"{notes_prefix}Asset marked as Found and {action_desc}. Previous status: {old_status}."

    scan_event = add_scan_event(
        asset_id=asset_id,
        user_id=user_id,
        room_id=final_room_id, # Log against the final room
        status="Good",
        notes=scan_notes
    )
    if not scan_event:
         print(f"Warning: Failed to create scan event for Found asset {asset_id}.")
         # Decide if rollback is needed

    try:
        # Commit changes for the single asset
        # db.session.add(asset) # Not needed if asset is already tracked
        db.session.commit()
        return asset
    except Exception as e:
        print(f"Error marking asset {asset_id} as found: {e}")
        db.session.rollback()
        return None


# --- (update_asset_details remains the same) ---
def update_asset_details(asset_id, description, model, brand, serial_number, assignee_id, notes):
    """Update basic asset details excluding location and status fields"""
    asset = get_asset(asset_id)
    if not asset:
        return None

    # Store original values for logging if needed (optional)
    # old_description = asset.description ...

    # Update only the editable fields
    asset.description = description
    asset.model = model
    asset.brand = brand
    asset.serial_number = serial_number
    asset.assignee_id = assignee_id
    asset.notes = notes

    # Automatically update the last_update timestamp
    asset.last_update = datetime.now()

    try:
        # Add a scan event or audit log entry here if desired
        # e.g., log_change(asset_id, current_user.id, "Details Updated", old_values, new_values)

        db.session.commit()
        return asset
    except Exception as e:
        print(f"Error updating asset details for {asset_id}: {e}")
        db.session.rollback()
        return None


# --- NEW BULK ACTION CONTROLLERS ---

def bulk_mark_assets_found(asset_ids, user_id, notes="", skip_failed_scan_events=False):
    """Marks multiple assets as Found and returns them to their assigned rooms.
    
    Args:
        asset_ids: List of asset IDs to mark as found
        user_id: ID of the user performing the action
        notes: Optional notes to add to scan events
        skip_failed_scan_events: If True, continue processing assets even if scan event creation fails
    
    Returns:
        Tuple of (processed_count, error_count, errors list)
    """
    processed_count = 0
    error_count = 0
    errors = []
    
    if not user_id:
        if current_user:
             user_id = current_user.id
        else:
             # Handle missing user context - maybe raise an error or use SYSTEM
             return 0, len(asset_ids), ["User context required for bulk action."]

    notes_prefix = f"Bulk Mark Found action by User {user_id}. "
    if notes:
        notes_prefix += f"Note: {notes}. "

    # First update all assets in memory
    assets_to_update = []
    scan_events_to_add = []
    
    # Prepare all updates as a batch
    for asset_id in asset_ids:
        asset = get_asset(asset_id)
        if not asset:
            error_count += 1
            errors.append(f"Asset {asset_id} not found")
            continue
            
        # Store old status and location for changelog
        old_status = asset.status
        
        # Set the asset as found and returned to its room
        asset.last_located = asset.room_id  # Return to assigned room
        asset.status = "Good"
        asset.last_update = datetime.now()
        
        # Create scan event notes
        scan_notes = f"{notes_prefix}Asset marked as Found and returned to assigned room. Previous status: {old_status}."
        
        # Prepare scan event data
        scan_event_data = {
            'asset_id': asset_id,
            'user_id': user_id,
            'room_id': asset.room_id,
            'status': "Good",
            'notes': scan_notes
        }
        
        assets_to_update.append(asset)
        scan_events_to_add.append(scan_event_data)
    
    # Now process everything in a single database transaction
    try:
        # Add all updated assets to the session
        for asset in assets_to_update:
            db.session.add(asset)
            
        # Try to create all scan events
        for event_data in scan_events_to_add:
            try:
                add_scan_event(**event_data)
                processed_count += 1
            except Exception as e:
                if skip_failed_scan_events:
                    # Log the error but continue processing
                    print(f"Warning: Failed to create scan event for Found asset {event_data['asset_id']}. Error: {str(e)}")
                    errors.append(f"Scan event creation failed for asset {event_data['asset_id']}: {str(e)}")
                    error_count += 1
                else:
                    # Re-raise the exception if we're not skipping failures
                    raise
        
        # Commit all changes at once
        db.session.commit()
        print(f"Successfully marked {processed_count} assets as found")
        return processed_count, error_count, errors
    except Exception as e:
        db.session.rollback()
        print(f"Error committing bulk mark-as-found: {e}")
        errors.append(f"Database error: {str(e)}")
        return 0, len(asset_ids), errors
  
def bulk_relocate_assets(asset_ids, new_room_id, user_id, notes=""):
    """Marks multiple assets as Found and relocates/reassigns them to a new room."""
    processed_count = 0
    error_count = 0
    errors = []

    if not user_id:
        if current_user:
             user_id = current_user.id
        else:
             return 0, len(asset_ids), ["User context required for bulk action."]

    # Check if the target room exists
    target_room = get_room(new_room_id)
    if not target_room:
        return 0, len(asset_ids), [f"Target room {new_room_id} not found."]
    target_room_name = target_room.room_name


    notes_prefix = f"Bulk Relocate action by User {user_id} to {target_room_name} ({new_room_id}). "

    assets_to_update = []
    scan_events_to_add = []

    for asset_id in asset_ids:
        asset = get_asset(asset_id)
        if not asset:
            error_count += 1
            errors.append(f"Asset {asset_id} not found.")
            continue

        old_status = asset.status
        old_location_id = asset.room_id # Original assigned room

        # Update asset fields directly for bulk processing
        asset.last_located = new_room_id
        asset.room_id = new_room_id # Reassign to the new room
        asset.status = "Good"
        asset.last_update = datetime.now()
        assets_to_update.append(asset) # Add to list for bulk save

        # Prepare scan event data (don't create yet)
        old_room_name = get_room(old_location_id).room_name if get_room(old_location_id) else f"Room {old_location_id}"
        scan_note = f"{notes_prefix}Asset relocated from {old_room_name}. Previous status: {old_status}."
        if notes:
         scan_note += f"\nUser Note: {notes}. "

        scan_event_data = {
             'asset_id': asset_id,
             'user_id': user_id,
             'room_id': new_room_id,
             'status': "Good",
             'notes': scan_note
        }
        scan_events_to_add.append(scan_event_data)
        processed_count += 1

    # Perform bulk update and scan event creation within a transaction
    if assets_to_update:
        try:
            # Bulk save assets
            db.session.add_all(assets_to_update)

            # Bulk create scan events (more efficient if add_scan_event supports bulk or direct insert)
            # For simplicity, calling add_scan_event individually here, but consider optimizing
            for event_data in scan_events_to_add:
                 add_scan_event(**event_data) # Unpack dict as arguments

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error during bulk relocate commit: {e}")
            # Mark all processed items as failed if commit fails
            return 0, len(asset_ids), [f"Database commit error: {e}"]


    return processed_count, error_count, errors