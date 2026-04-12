from App.models import ScanEvent
from App.database import db
from datetime import datetime

def add_scan_event(asset_id, user_id, room_id, status, notes=None):
    scan_id = f"SCAN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    scan_time = datetime.now()
    last_update = scan_time
    changeLog = f"Asset {asset_id} scanned in room {room_id} with status {status}"
    
    newScan = ScanEvent(scan_id, asset_id, user_id, room_id, scan_time, status, notes, last_update, changeLog)
    
    try:
        db.session.add(newScan)
        db.session.commit()
        return newScan
    except:
        db.session.rollback()
        return None

def get_all_scans():
    events = ScanEvent.query.all()
    return events

def get_scan_event(id):
    event = ScanEvent.query.filter_by(id=id).first()
    return event

def get_scans_by_asset(asset_id):
    events = ScanEvent.query.filter_by(asset_id=asset_id).order_by(ScanEvent.scan_time.desc()).all()
    return events

def get_scans_by_room(room_id):
    events = ScanEvent.query.filter_by(room_id=room_id).order_by(ScanEvent.scan_time.desc()).all()
    return events

def get_scans_by_status(status):
    event = ScanEvent.query.filter_by(status=status).all()
    return event

def get_scans_by_last_update(last_update):
    event = ScanEvent.query.filter_by(last_update=last_update).all()
    return event

def get_scans_by_changelog(changeLog):
    event = ScanEvent.query.filter_by(changeLog=changeLog).all()
    return event

def get_recent_scans(limit=50):
    events = ScanEvent.query.order_by(ScanEvent.scan_time.desc()).limit(limit).all()
    return events

def get_recent_scans_json(limit=50):
    events = get_recent_scans(limit)
    if not events:
        return []
    return [event.get_json() for event in events]