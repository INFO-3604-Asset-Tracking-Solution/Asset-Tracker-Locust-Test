
from flask import Blueprint, render_template, jsonify, request, send_file
from flask_jwt_extended import jwt_required, current_user
from App.controllers.asset import get_all_assets_by_room_id, get_all_assets_json, upload_csv
from App.controllers.user import update_user
from App.controllers.building import (
    create_building, get_building, get_all_building_json, 
    edit_building, delete_building
)
from App.controllers.floor import (
    create_floor, get_floor, get_floors_by_building,
    update_floor, delete_floor
)
from App.controllers.room import (
    create_room, get_room, get_rooms_by_floor,
    update_room, delete_room
)
import os
import csv
import io
from werkzeug.utils import secure_filename
from datetime import datetime


settings_views = Blueprint('settings_views', __name__, template_folder='../templates')

@settings_views.route('/settings', methods=['GET'])
@jwt_required()

def settings_page():
    return render_template('settings.html')

# User account endpoints
@settings_views.route('/api/user/update', methods=['POST'])
@jwt_required()
def update_user_settings():
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        username = data.get('username')
        email = data.get('email')
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        # Basic validation
        if not username or not email:
            return jsonify({'success': False, 'message': 'Username and email are required'}), 400
        
        # Check if current password is provided if changing password
        if new_password and not current_password:
            return jsonify({'success': False, 'message': 'Current password is required to set a new password'}), 400
        
        # If changing password, verify current password
        if new_password:
            if not current_user.check_password(current_password):
                return jsonify({'success': False, 'message': 'Current password is incorrect'}), 401
        
        # Add logging
        print(f"Updating user {current_user.id} - {username} - {email}")
        
        try:
            # Call controller to update user
            if new_password:
                # Update with new password
                result = update_user(current_user.id, email, username, new_password)
            else:
                # Update without changing password
                result = update_user(current_user.id, email, username)
            
            if result is not None:  # Check for None explicitly, as 0 could be a valid result
                return jsonify({'success': True, 'message': 'User updated successfully'})
            else:
                return jsonify({'success': False, 'message': 'Failed to update user. User not found or database error.'}), 500
        except Exception as e:
            print(f"Error updating user: {str(e)}")
            return jsonify({'success': False, 'message': f'Error updating user: {str(e)}'}), 500
            
    except Exception as e:
        print(f"Exception in user update endpoint: {str(e)}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500
    
# CSV upload endpoints
@settings_views.route('/api/upload/assets-csv', methods=['POST'])
@jwt_required()
def upload_assets_csv():
    if 'csvFile' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'}), 400
    
    file = request.files['csvFile']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'}), 400
    
    if file and file.filename.endswith('.csv'):
        try:
            # Make sure uploads directory exists
            os.makedirs('App/uploads', exist_ok=True)
            
            filename = secure_filename(file.filename)
            filepath = os.path.join('App/uploads', filename)
            file.save(filepath)
            
            # Process the CSV file
            result = upload_csv(filepath)
            
            # Clean up the uploaded file
            if os.path.exists(filepath):
                os.remove(filepath)
            
            if result['success']:
                return jsonify({
                    'success': True, 
                    'message': f"Successfully imported {result['imported']} assets. {result['skipped']} skipped.",
                    'details': result
                })
            else:
                return jsonify({
                    'success': False, 
                    'message': f"Failed to import assets: {result['errors'][0] if result['errors'] else 'Unknown error'}",
                    'details': result
                }), 400
        except Exception as e:
            return jsonify({'success': False, 'message': f'Error processing CSV: {str(e)}'}), 500
    else:
        return jsonify({'success': False, 'message': 'File must be a CSV'}), 400
    
@settings_views.route('/api/upload/locations-csv', methods=['POST'])
@jwt_required()
def upload_locations_csv():
    if 'csvFile' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'}), 400
    
    file = request.files['csvFile']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'}), 400
    
    if file and file.filename.endswith('.csv'):
        try:
            # Read CSV file
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.DictReader(stream)
            
            # Initialize counters and error collection
            buildings_created = 0
            floors_created = 0
            rooms_created = 0
            skipped_rows = 0
            errors = []
            
            # Track which entities we've already processed to avoid duplicates
            processed_buildings = {}  # Dict of id -> building object
            processed_floors = {}  # Dict of id -> floor object
            processed_rooms = {}  # Dict of id -> room object
            
            for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 to account for header row
                try:
                    # Extract data with defaults for missing values
                    building_id = row.get('building_id', '').strip()
                    building_name = row.get('building_name', '').strip()
                    floor_id = row.get('floor_id', '').strip()
                    floor_name = row.get('floor_name', '').strip()
                    room_id = row.get('room_id', '').strip()
                    room_name = row.get('room_name', '').strip()
                    
                    # Skip empty rows
                    if not building_name:
                        errors.append(f"Row {row_num}: Missing building name (required)")
                        skipped_rows += 1
                        continue
                    
                    # BUILDING HANDLING
                    current_building = None
                    
                    # If building_id provided, check if it exists
                    if building_id:
                        existing_building = get_building(building_id)
                        if existing_building:
                            # Building exists with this ID
                            current_building = existing_building
                            
                            # Verify the building name matches
                            if existing_building.building_name != building_name:
                                errors.append(f"Row {row_num}: Building ID {building_id} exists but with name '{existing_building.building_name}' (not '{building_name}')")
                                skipped_rows += 1
                                continue
                        else:
                            # Building ID provided but doesn't exist, create it
                            current_building = create_building(building_id, building_name)
                            buildings_created += 1
                    else:
                        # No building_id provided, check if a building with this name exists
                        buildings = get_all_building_json()
                        existing_building = next((b for b in buildings if b['building_name'].lower() == building_name.lower()), None)
                        
                        if existing_building:
                            # Building exists with this name
                            current_building = get_building(existing_building['building_id'])
                        else:
                            # Generate a unique building ID
                            new_building_id = f"B{datetime.now().strftime('%Y%m%d%H%M%S')}"
                            current_building = create_building(new_building_id, building_name)
                            buildings_created += 1
                    
                    # Store the building for reference
                    processed_buildings[current_building.building_id] = current_building
                    
                    # If we don't have floor information, we're done with this row
                    if not floor_name:
                        continue
                    
                    # FLOOR HANDLING
                    current_floor = None
                    
                    # If floor_id provided, check if it exists
                    if floor_id:
                        existing_floor = get_floor(floor_id)
                        if existing_floor:
                            # Floor exists with this ID
                            current_floor = existing_floor
                            
                            # Verify the floor belongs to the right building
                            if existing_floor.building_id != current_building.building_id:
                                errors.append(f"Row {row_num}: Floor ID {floor_id} exists but belongs to building {existing_floor.building_id} (not {current_building.building_id})")
                                skipped_rows += 1
                                continue
                                
                            # Verify the floor name matches
                            if existing_floor.floor_name != floor_name:
                                errors.append(f"Row {row_num}: Floor ID {floor_id} exists but with name '{existing_floor.floor_name}' (not '{floor_name}')")
                                skipped_rows += 1
                                continue
                        else:
                            # Floor ID provided but doesn't exist, create it
                            current_floor = create_floor(floor_id, current_building.building_id, floor_name)
                            floors_created += 1
                    else:
                        # No floor_id provided, check if a floor with this name exists in the building
                        floors = get_floors_by_building(current_building.building_id)
                        existing_floor = next((f for f in floors if f.floor_name.lower() == floor_name.lower()), None)
                        
                        if existing_floor:
                            # Floor exists with this name in this building
                            current_floor = existing_floor
                        else:
                            # Generate a unique floor ID
                            new_floor_id = f"F{datetime.now().strftime('%Y%m%d%H%M%S')}"
                            current_floor = create_floor(new_floor_id, current_building.building_id, floor_name)
                            floors_created += 1
                    
                    # Store the floor for reference
                    processed_floors[current_floor.floor_id] = current_floor
                    
                    # If we don't have room information, we're done with this row
                    if not room_name:
                        continue
                    
                    # ROOM HANDLING
                    current_room = None
                    
                    # If room_id provided, check if it exists
                    if room_id:
                        existing_room = get_room(room_id)
                        if existing_room:
                            # Room exists with this ID
                            current_room = existing_room
                            
                            # Verify the room belongs to the right floor
                            if existing_room.floor_id != current_floor.floor_id:
                                errors.append(f"Row {row_num}: Room ID {room_id} exists but belongs to floor {existing_room.floor_id} (not {current_floor.floor_id})")
                                skipped_rows += 1
                                continue
                                
                            # Verify the room name matches
                            if existing_room.room_name != room_name:
                                errors.append(f"Row {row_num}: Room ID {room_id} exists but with name '{existing_room.room_name}' (not '{room_name}')")
                                skipped_rows += 1
                                continue
                        else:
                            # Room ID provided but doesn't exist, create it
                            current_room = create_room(room_id, current_floor.floor_id, room_name)
                            rooms_created += 1
                    else:
                        # No room_id provided, check if a room with this name exists in the floor
                        rooms = get_rooms_by_floor(current_floor.floor_id)
                        existing_room = next((r for r in rooms if r.room_name.lower() == room_name.lower()), None)
                        
                        if existing_room:
                            # Room exists with this name in this floor
                            current_room = existing_room
                        else:
                            # Generate a unique room ID
                            new_room_id = f"R{datetime.now().strftime('%Y%m%d%H%M%S')}"
                            current_room = create_room(new_room_id, current_floor.floor_id, room_name)
                            rooms_created += 1
                    
                    # Store the room for reference
                    processed_rooms[current_room.room_id] = current_room
                    
                except Exception as e:
                    errors.append(f"Row {row_num}: Error - {str(e)}")
                    skipped_rows += 1
            
            # Construct response
            response_data = {
                'success': buildings_created > 0 or floors_created > 0 or rooms_created > 0,
                'message': f'Successfully imported {buildings_created} buildings, {floors_created} floors, and {rooms_created} rooms. {skipped_rows} rows skipped.',
                'buildings_created': buildings_created,
                'floors_created': floors_created,
                'rooms_created': rooms_created,
                'skipped_rows': skipped_rows,
                'errors': errors[:10]  # Limit number of errors returned to avoid huge responses
            }
            
            if errors and len(errors) > 10:
                response_data['message'] += f" Showing first 10 of {len(errors)} errors."
            
            return jsonify(response_data)
            
        except Exception as e:
            return jsonify({'success': False, 'message': f'Error processing CSV: {str(e)}'}), 500
    else:
        return jsonify({'success': False, 'message': 'File must be a CSV'}), 400

# Template download endpoints
@settings_views.route('/api/download/asset-template', methods=['GET'])
@jwt_required()
def download_asset_template():
    # Create a CSV template for assets
    csv_content = io.StringIO()
    writer = csv.writer(csv_content)
    
    # Write header row
    writer.writerow(['Item', 'Asset Tag', 'Brand', 'Model', 'Serial Number', 'Location', 'Condition', 'Assignee'])
    
    # Write example row
    writer.writerow(['Laptop', 'A001', 'Dell', 'XPS 15', 'SN12345', '1', 'Good', '1'])
    
    # Create a response with the CSV content
    csv_content.seek(0)
    return send_file(
        io.BytesIO(csv_content.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='asset_template.csv'
    )

@settings_views.route('/api/download/location-template', methods=['GET'])
@jwt_required()
def download_location_template():
    # Create a CSV template for locations
    csv_content = io.StringIO()
    writer = csv.writer(csv_content)
    
    # Write header row with all fields
    writer.writerow(['building_id', 'building_name', 'floor_id', 'floor_name', 'room_id', 'room_name'])
    
    # Write example rows
    writer.writerow(['B001', 'Main Building', 'F001', '1st Floor', 'R001', 'Room 101'])
    writer.writerow(['B001', 'Main Building', 'F001', '1st Floor', 'R002', 'Room 102'])
    writer.writerow(['B001', 'Main Building', 'F002', '2nd Floor', 'R003', 'Room 201'])
    writer.writerow(['B002', 'Annex Building', 'F003', 'Ground Floor', 'R004', 'Meeting Room'])
    
    # Add a row to show that IDs are optional (will be generated if not provided)
    writer.writerow(['', 'IT Building', '', '3rd Floor', '', 'Server Room'])
    
    # Create a response with the CSV content
    csv_content.seek(0)
    return send_file(
        io.BytesIO(csv_content.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='location_template.csv'
    )
    

# Location management endpoints - Buildings
@settings_views.route('/api/buildings', methods=['GET'])
@jwt_required()
def get_buildings():
    buildings = get_all_building_json()
    return jsonify(buildings)

@settings_views.route('/api/building/add', methods=['POST'])
@jwt_required()
def add_building():
    data = request.json
    
    if not data or 'building_name' not in data:
        return jsonify({'success': False, 'message': 'Building name is required'}), 400
    
    building_name = data['building_name'].strip()
    
    if not building_name:
        return jsonify({'success': False, 'message': 'Building name cannot be empty'}), 400
    
    # Generate a unique building ID
    building_id = f"B{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    building = create_building(building_id, building_name)
    
    if building:
        return jsonify({
            'success': True,
            'message': 'Building created successfully',
            'building': {
                'building_id': building.building_id,
                'building_name': building.building_name
            }
        })
    else:
        return jsonify({'success': False, 'message': 'Failed to create building'}), 500

@settings_views.route('/api/building/<building_id>/update', methods=['POST'])
@jwt_required()
def update_building_endpoint(building_id):
    data = request.json
    
    if not data or 'building_name' not in data:
        return jsonify({'success': False, 'message': 'Building name is required'}), 400
    
    building_name = data['building_name'].strip()
    
    if not building_name:
        return jsonify({'success': False, 'message': 'Building name cannot be empty'}), 400
    
    # Check if building exists first
    building = get_building(building_id)
    if not building:
        return jsonify({'success': False, 'message': f'Building with ID {building_id} not found'}), 404
    
    # If building exists, update it
    result = edit_building(building_id, building_name)
    
    if result:  # Check if a building was returned (success)
        return jsonify({
            'success': True,
            'message': 'Building updated successfully',
            'building': {
                'building_id': result.building_id,
                'building_name': result.building_name
            }
        })
    else:
        return jsonify({'success': False, 'message': 'Failed to update building. Database error.'}), 500

@settings_views.route('/api/building/<building_id>/delete', methods=['DELETE'])
@jwt_required()
def delete_building_endpoint(building_id):
    if get_floors_by_building(building_id):
        return jsonify({
            'success': False,
            'message': 'Failed to delete building. It may have associated floors or rooms.'
        }), 400

    if delete_building(building_id):
        return jsonify({
            'success': True,
            'message': 'Building deleted successfully'
        })

    return jsonify({
        'success': False,
        'message': 'Could not delete building.'
    }), 400


# Location management endpoints - Floors
@settings_views.route('/api/floors/<building_id>', methods=['GET'])
@jwt_required()
def get_building_floors(building_id):
    floors = get_floors_by_building(building_id)
    if not floors:
        return jsonify([])
    floors_json = [floor.get_json() for floor in floors]
    return jsonify(floors_json)

@settings_views.route('/api/floor/add', methods=['POST'])
@jwt_required()
def add_floor():
    data = request.json
    
    if not data or 'building_id' not in data or 'floor_name' not in data:
        return jsonify({'success': False, 'message': 'Building ID and floor name are required'}), 400
    
    building_id = data['building_id']
    floor_name = data['floor_name'].strip()
    
    if not floor_name:
        return jsonify({'success': False, 'message': 'Floor name cannot be empty'}), 400
    
    # Check if building exists
    building = get_building(building_id)
    if not building:
        return jsonify({'success': False, 'message': 'Building not found'}), 404
    
    # Generate a unique floor ID
    floor_id = f"F{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    floor = create_floor(floor_id, building_id, floor_name)
    
    if floor:
        return jsonify({
            'success': True,
            'message': 'Floor created successfully',
            'floor': {
                'floor_id': floor.floor_id,
                'building_id': floor.building_id,
                'floor_name': floor.floor_name
            }
        })
    else:
        return jsonify({'success': False, 'message': 'Failed to create floor'}), 500

@settings_views.route('/api/floor/<floor_id>/update', methods=['POST'])
@jwt_required()
def update_floor_endpoint(floor_id):
    data = request.json
    
    if not data or 'building_id' not in data or 'floor_name' not in data:
        return jsonify({'success': False, 'message': 'Building ID and floor name are required'}), 400
    
    building_id = data['building_id']
    floor_name = data['floor_name'].strip()
    
    if not floor_name:
        return jsonify({'success': False, 'message': 'Floor name cannot be empty'}), 400
    
    result = update_floor(floor_id, building_id, floor_name)
    
    if result is not None:
        return jsonify({
            'success': True,
            'message': 'Floor updated successfully'
        })
    else:
        return jsonify({'success': False, 'message': 'Failed to update floor'}), 500

@settings_views.route('/api/floor/<floor_id>/delete', methods=['DELETE'])
@jwt_required()
def delete_floor_endpoint(floor_id):
    # Prevent deletion if there are rooms linked to the floor
    if get_rooms_by_floor(floor_id):
        return jsonify({
            'success': False,
            'message': 'Failed to delete floor. It may have associated rooms.'
        }), 400

    # Proceed to delete floor
    if delete_floor(floor_id):
        return jsonify({
            'success': True,
            'message': 'Floor deleted successfully'
        })

    return jsonify({
        'success': False,
        'message': 'Could not delete Floor.'
    }), 400


# Location management endpoints - Rooms
@settings_views.route('/api/rooms/<floor_id>', methods=['GET'])
@jwt_required()
def get_floor_rooms(floor_id):
    rooms = get_rooms_by_floor(floor_id)
    if not rooms:
        return jsonify([])
    rooms_json = [room.get_json() for room in rooms]
    return jsonify(rooms_json)

@settings_views.route('/api/room/add', methods=['POST'])
@jwt_required()
def add_room():
    data = request.json
    
    if not data or 'floor_id' not in data or 'room_name' not in data:
        return jsonify({'success': False, 'message': 'Floor ID and room name are required'}), 400
    
    floor_id = data['floor_id']
    room_name = data['room_name'].strip()
    
    if not room_name:
        return jsonify({'success': False, 'message': 'Room name cannot be empty'}), 400
    
    # Check if floor exists
    floor = get_floor(floor_id)
    if not floor:
        return jsonify({'success': False, 'message': 'Floor not found'}), 404
    
    # Generate a unique room ID
    room_id = f"R{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    room = create_room(room_id, floor_id, room_name)
    
    if room:
        return jsonify({
            'success': True,
            'message': 'Room created successfully',
            'room': {
                'room_id': room.room_id,
                'floor_id': room.floor_id,
                'room_name': room.room_name
            }
        })
    else:
        return jsonify({'success': False, 'message': 'Failed to create room'}), 500

@settings_views.route('/api/room/<room_id>/update', methods=['POST'])
@jwt_required()
def update_room_endpoint(room_id):
    data = request.json
    
    if not data or 'floor_id' not in data or 'room_name' not in data:
        return jsonify({'success': False, 'message': 'Floor ID and room name are required'}), 400
    
    floor_id = data['floor_id']
    room_name = data['room_name'].strip()
    
    if not room_name:
        return jsonify({'success': False, 'message': 'Room name cannot be empty'}), 400
    
    result = update_room(room_id, floor_id, room_name)
    
    if result is not None:
        return jsonify({
            'success': True,
            'message': 'Room updated successfully'
        })
    else:
        return jsonify({'success': False, 'message': 'Failed to update room'}), 500

@settings_views.route('/api/room/<room_id>/delete', methods=['DELETE'])
@jwt_required()
def delete_room_endpoint(room_id):
    if get_all_assets_by_room_id(room_id):
        return jsonify({
            'success': False,
            'message': 'Failed to delete room. It may be in use by assets.'
        }), 400

    if delete_room(room_id):
        return jsonify({
            'success': True,
            'message': 'Room deleted successfully'
        })

    return jsonify({
        'success': False,
        'message': 'Could not delete room.'
    }), 400

        
@settings_views.route('/api/users', methods=['GET'])
@jwt_required()
def get_all_users_api():
    """Get all users for the user management section"""
    from App.controllers.user import get_all_users_json
    users = get_all_users_json()
    return jsonify(users)

@settings_views.route('/api/user/create', methods=['POST'])
@jwt_required()
def create_user_api():
    """Create a new user"""
    from App.controllers.user import create_user, get_user_by_email
    
    data = request.json
    
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')
    
    # Basic validation
    if not email or not username or not password:
        return jsonify({'success': False, 'message': 'Email, username and password are required'}), 400
    
    # Check if user already exists
    existing_user = get_user_by_email(email)
    if existing_user:
        return jsonify({'success': False, 'message': 'A user with this email already exists'}), 409
    
    try:
        # Create the user
        new_user = create_user(email, username, password)
        
        if new_user:
            return jsonify({
                'success': True, 
                'message': 'User created successfully',
                'user': {
                    'id': new_user.id,
                    'email': new_user.email,
                    'username': new_user.username
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to create user'}), 500
            
    except Exception as e:
        print(f"Error creating user: {str(e)}")
        return jsonify({'success': False, 'message': f'Error creating user: {str(e)}'}), 500
