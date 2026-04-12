from flask import Blueprint, render_template, jsonify, request
from flask_jwt_extended import jwt_required, current_user
from App.controllers.asset import get_all_assets_json, get_asset, update_asset_details, add_asset
from App.controllers.assignee import get_all_assignees_json, get_assignee_by_id, get_or_create_assignee_by_name # Import new function
from App.controllers.room import get_room
from App.controllers.scanevent import add_scan_event, get_scans_by_asset
from datetime import datetime

inventory_views = Blueprint('inventory_views', __name__, template_folder='../templates')

@inventory_views.route('/inventory', methods=['GET'])
@jwt_required()
def inventory_page():
    return render_template('inventory.html')

@inventory_views.route('/api/assets', methods=['GET'])
@jwt_required()
def get_assets():
    assets = get_all_assets_json()
    for asset in assets:
        if asset.get('room_id'):
            room = get_room(asset['room_id'])
            if room:
                asset['room_name'] = room.room_name
            else:
                asset['room_name'] = f"Room {asset['room_id']}"
        else:
            asset['room_name'] = "Unknown"
        if asset.get('assignee_id'):
            assignee = get_assignee_by_id(asset['assignee_id'])
            if assignee:
                asset['assignee_name'] = str(assignee) # Use __str__
            else:
                asset['assignee_name'] = f"Assignee ID: {asset['assignee_id']}"
        else:
            asset['assignee_name'] = "Unassigned"
    return jsonify(assets)

@inventory_views.route('/asset/<asset_id>', methods=['GET'])
@jwt_required()
def asset_report(asset_id):
    asset = get_asset(asset_id)
    if not asset:
        return render_template('message.html',
                              title="Asset Not Found",
                              message=f"The asset with ID {asset_id} was not found.")
    room = get_room(asset.room_id) if asset.room_id else None
    room_name = room.room_name if room else "Unknown"
    last_location = get_room(asset.last_located) if asset.last_located else None
    last_location_name = last_location.room_name if last_location else "Unknown"
    assignee = get_assignee_by_id(asset.assignee_id) if asset.assignee_id else None
    assignee_name = str(assignee) if assignee else "Unassigned" # Use __str__
    scan_events = get_scans_by_asset(asset_id)
    enriched_scan_events = []
    for event in scan_events:
        try:
            event_dict = {}
            if hasattr(event, 'get_json') and callable(event.get_json):
                # Get the JSON representation and clean up the keys
                raw_dict = event.get_json()
                # Remove colons and spaces from keys
                event_dict = {key.rstrip(': '): value for key, value in raw_dict.items()}
            else:
                event_dict_raw = event.__dict__.copy()
                event_dict_raw.pop('_sa_instance_state', None)
                for key, value in event_dict_raw.items():
                    # Fix key names - remove trailing colons and spaces
                    clean_key = key.rstrip(': ') if isinstance(key, str) else key
                    if isinstance(value, datetime):
                        # Store datetime objects directly instead of strings
                        event_dict[clean_key] = value
                    else:
                        event_dict[clean_key] = value
            
            # Add room name
            scan_room = get_room(event.room_id)
            event_dict['room_name'] = scan_room.room_name if scan_room else f"Room {event.room_id}"
            enriched_scan_events.append(event_dict)
        except Exception as e:
            print(f"Error processing scan event {getattr(event, 'scan_id', 'N/A')}: {e}")
            enriched_scan_events.append({
                'scan_id': getattr(event, 'scan_id', 'N/A'),  # Remove colon
                'error': 'Could not process event data',
                'scan_time': getattr(event, 'scan_time', datetime.now())  # Store as datetime object
            })

    def get_scan_time(event_dict):
        time_val = event_dict.get('scan_time')  # Use clean key
        if isinstance(time_val, str):
            try:
                return datetime.strptime(time_val, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return datetime.min
        elif isinstance(time_val, datetime):
            return time_val
        else:
            return datetime.min
    
    enriched_scan_events.sort(key=get_scan_time, reverse=True)
    return render_template('asset.html',
                          asset=asset,
                          room_name=room_name,
                          last_location_name=last_location_name,
                          assignee_name=assignee_name,
                          scan_events=enriched_scan_events)

@inventory_views.route('/api/asset/<asset_id>/update', methods=['POST'])
@jwt_required()
def update_asset_details_endpoint(asset_id):
    data = request.json
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    description = data.get('description')
    model = data.get('model')
    brand = data.get('brand')
    serial_number = data.get('serial_number')
    assignee_id = data.get('assignee_id')
    notes = data.get('notes')
    if not description:
        return jsonify({'success': False, 'message': 'Description is required'}), 400
    updated_asset = update_asset_details(
        asset_id, description, model, brand, serial_number, assignee_id, notes
    )
    if not updated_asset:
        return jsonify({'success': False, 'message': 'Failed to update asset. Asset not found or error occurred.'}), 404
    try:
        add_scan_event(
            asset_id=asset_id,
            user_id=current_user.id,
            room_id=updated_asset.room_id,
            status=updated_asset.status,
            notes=f"Asset details updated by {current_user.username}"
        )
    except Exception as e:
        print(f"Error adding scan event: {e}")
    return jsonify({
        'success': True,
        'message': 'Asset details updated successfully',
        'asset': updated_asset.get_json()
    })

@inventory_views.route('/api/assignees', methods=['GET'])
@jwt_required()
def get_assignees():
    assignees = get_all_assignees_json()
    return jsonify(assignees)

@inventory_views.route('/api/asset/add', methods=['POST'])
@jwt_required()
def add_asset_api():
    data = request.json
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    asset_id = data.get('id')
    description = data.get('description')
    room_id = data.get('room_id')
    assignee_name = data.get('assignee_name')
    if not all([asset_id, description, room_id, assignee_name]):
        missing = [field for field, value in {'Asset ID': asset_id, 'Description': description, 'Room': room_id, 'Assignee Name': assignee_name}.items() if not value]
        return jsonify({'success': False, 'message': f'Missing required fields: {", ".join(missing)}'}), 400
    assignee = get_or_create_assignee_by_name(assignee_name)
    if not assignee:
        return jsonify({'success': False, 'message': f'Could not find or create assignee "{assignee_name}". Check name format or server logs.'}), 400
    assignee_id = assignee.id
    model = data.get('model')
    brand = data.get('brand')
    serial_number = data.get('serial_number')
    notes = data.get('notes')
    last_update = datetime.now()
    last_located = room_id
    try:
        new_asset = add_asset(
            id=asset_id,
            description=description,
            model=model,
            brand=brand,
            serial_number=serial_number,
            room_id=room_id,
            last_located=last_located,
            assignee_id=assignee_id,
            last_update=last_update,
            notes=notes
        )
        if new_asset:
            try:
                add_scan_event(
                    asset_id=new_asset.id,
                    user_id=current_user.id,
                    room_id=new_asset.room_id,
                    status=new_asset.status,
                    notes=f"Asset created by {current_user.username}"
                )
            except Exception as e:
                print(f"Warning: Could not add creation scan event for asset {new_asset.id}: {e}")
            return jsonify({'success': True, 'asset': new_asset.get_json()}), 201
        else:
            existing_asset = get_asset(asset_id)
            if existing_asset:
                 return jsonify({'success': False, 'message': f'Asset with ID "{asset_id}" already exists.'}), 409
            else:
                 return jsonify({'success': False, 'message': 'Failed to add asset. Check if Room ID is valid.'}), 400
    except Exception as e:
        print(f"Error adding asset via API: {e}")
        return jsonify({'success': False, 'message': 'An internal server error occurred.'}), 500