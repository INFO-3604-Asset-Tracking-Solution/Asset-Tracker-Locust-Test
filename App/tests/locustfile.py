from locust import HttpUser, task, between, events
import random
import logging

class AssetAuditorUser(HttpUser):
    wait_time = between(1, 4)

    @events.init.add_listener
    def on_locust_init(environment, **kwargs):
        """Initialize global state if needed"""
        environment.assets_to_add = 500

    def on_start(self):
        """Executed when a simulated user starts. Performs login and setup."""
        # Login using the default user configured in initialize.py
        login_data = {
            "email": "bob@gmail.com", 
            "password": "bobpass"
        }
        res = self.client.post("/api/login", json=login_data)
        if res.status_code == 200:
            self.logged_in = True
            token = res.json().get("access_token")
            if token:
                self.client.headers.update({"Authorization": f"Bearer {token}"})
                

                if hasattr(self.environment, 'assets_to_add') and self.environment.assets_to_add > 0:
                    # Capture current count to avoid race conditions in simple local runs
                    count = self.environment.assets_to_add
                    self.environment.assets_to_add = 0 # Mark as handled immediately
                    self.populate_inventory(count)
        else:
            self.logged_in = False
            logging.error(f"Login failed: {res.text}")

    def populate_inventory(self, count):
        """One-time setup to add a batch of assets"""
        logging.info(f"Starting setup: Adding {count} assets...")
        
        # Get rooms for assignment
        res = self.client.get("/api/rooms/all", name="Setup: Get All Rooms")
        if res.status_code != 200: return
        rooms = res.json()
        if not rooms: return

        for i in range(count):
            room = random.choice(rooms)
            room_id = room.get('room_id')
            asset_tag = f"SETUP-{random.randint(10000, 999999)}"
            
            payload = {
                "id": asset_tag,
                "description": f"Setup Asset {i+1}",
                "room_id": room_id,
                "assignee_name": "Setup Auditor",
                "model": "Setup-X1",
                "brand": "System",
                "serial_number": f"SN-SETUP-{i}",
                "notes": "Initial setup asset"
            }
            self.client.post("/api/asset/add", json=payload, name="Setup: Add Asset")
        
        logging.info("Setup complete.")

    @task(5)
    def simulate_auditor_scans(self):
        """Simulates an auditor scanning assets in a room"""
        if not self.logged_in: return

        # 1. Pick a random room to audit
        res = self.client.get("/api/rooms/all", name="API: Get All Rooms (for audit)")
        if res.status_code != 200: return
        rooms = res.json()
        if not rooms: return
        
        target_room = random.choice(rooms)
        target_room_id = target_room.get('id')
        
        # 2. Get expected assets for this room
        assets_res = self.client.get(f"/api/assets/{target_room_id}", name="API: Get Room Assets")
        if assets_res.status_code != 200: return
        expected_assets = assets_res.json()
        
        # 3. Simulate scanning some of them (Found Status: Good)
        num_to_scan = random.randint(0, len(expected_assets))
        scanned_assets = random.sample(expected_assets, num_to_scan) if expected_assets else []
        
        for asset in scanned_assets:
            self.client.post("/api/update-asset-location", json={
                "assetId": asset.get('id'),
                "roomId": target_room_id
            }, name="API: Scan Asset (Correct Room)")
            
        # 4. Simulate scanning some "Misplaced" assets (assets from other rooms found here)
        all_assets_res = self.client.get("/api/assets", name="API: Get All Assets")
        if all_assets_res.status_code == 200:
            all_assets = all_assets_res.json()
            other_assets = [a for a in all_assets if a.get('room_id') != target_room_id]
            if other_assets:
                misplaced_count = random.randint(0, 2)
                misplaced_assets = random.sample(other_assets, min(misplaced_count, len(other_assets)))
                for asset in misplaced_assets:
                    self.client.post("/api/update-asset-location", json={
                        "assetId": asset.get('id'),
                        "roomId": target_room_id
                    }, name="API: Scan Asset (Misplaced)")

        # 5. Mark remaining expected assets as "Missing"
        if expected_assets and random.random() < 0.5: # 50% chance to finish the audit by marking missing
            scanned_ids = [s.get('id') for s in scanned_assets]
            unscanned_ids = [a.get('id') for a in expected_assets if a.get('id') not in scanned_ids]
            if unscanned_ids:
                self.client.post("/api/mark-assets-missing", json={
                    "assetIds": unscanned_ids
                }, name="API: Mark Assets Missing")

    @task(3)
    def view_discrepancy_report(self):
        """Simulates an auditor loading the discrepancy report page and related data"""
        if not self.logged_in: return
            
        # UI page load
        self.client.get("/discrepancy-report", name="UI: Discrepancy Report")
        
        # Load discrepancies
        self.client.get("/api/discrepancies", name="API: Get All Discrepancies")
        
        # Auditor might filter missing or misplaced
        filter_choice = random.choice([None, "missing", "misplaced"])
        if filter_choice == "missing":
            self.client.get("/api/discrepancies/missing", name="API: Get Missing")
        elif filter_choice == "misplaced":
            self.client.get("/api/discrepancies/misplaced", name="API: Get Misplaced")
            
        # Get all rooms for dropdowns
        self.client.get("/api/rooms/all", name="API: Get All Rooms")

    @task(2)
    def resolve_discrepancy(self):
        """Simulates an auditor resolving an existing discrepancy"""
        if not self.logged_in: return

        # Fetch current discrepancies
        with self.client.get("/api/discrepancies", catch_response=True, name="API: Get All Discrepancies (for resolve)") as response:
            if response.status_code != 200:
                response.failure("Failed to get discrepancies")
                return
            
            discrepancies = response.json()
            if not discrepancies:
                return # No discrepancies to resolve
                
            # Pick a random discrepant asset
            asset = random.choice(discrepancies)
            asset_id = asset.get('id')
            
            # Fetch rooms
            room_res = self.client.get("/api/rooms/all", name="API: Get All Rooms (for resolve)")
            if room_res.status_code != 200:
                return
                
            rooms = room_res.json()
            if not rooms:
                return
                
            resolution_action = random.choice(["mark_found", "relocate_single"])
            
            if resolution_action == "mark_found":
                payload = {
                    "assetIds": [asset_id],
                    "notes": "Locust test: mark found"
                }
                self.client.post("/api/assets/bulk-mark-found", json=payload, name="API: Bulk Mark Found")
                
            elif resolution_action == "relocate_single":
                new_room = random.choice(rooms)
                room_id = new_room.get('id')
                payload = {
                    "roomId": room_id,
                    "notes": "Locust test: single relocate"
                }
                self.client.post(f"/api/asset/{asset_id}/relocate", json=payload, name="API: Single Relocate")

    @task(1)
    def download_report(self):
        """Simulate downloading the discrepancy CSV report"""
        if not self.logged_in: return
        
        filter_choice = random.choice(["all", "missing", "misplaced"])
        self.client.get(f"/api/discrepancies/download?filter={filter_choice}", name=f"API: Download CSV ({filter_choice})")
