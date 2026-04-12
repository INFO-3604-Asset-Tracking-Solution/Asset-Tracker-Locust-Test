/**
 * Audit Application Module
 * Manages the asset auditing process including scanning, tracking, and updating assets
 */

// QR Code Scanner Module
/**
 * QR Code Scanner Module
 * Supports both mobile camera scanning and desktop external QR scanners
 */
const QRScanner = (function() {
    // Private state
    let videoElem = null;
    let canvasElem = null;
    let isScanning = false;
    let scanInterval = null;
    let isMobileDevice = false;
    let scanBuffer = '';
    let scanTimeout = null;
    
    // Reference to processing function
    let processAssetCallback = null;
    
    /**
     * Check if the device is a mobile device
     * @returns {boolean} True if the device is mobile
     */
    function checkIfMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || 
               (window.innerWidth <= 800 && window.innerHeight <= 800);
    }
    
    /**
     * Initialize the QR scanner
     * @param {Function} processAssetFn - Callback function when asset is scanned
     */
    function init(processAssetFn) {
        processAssetCallback = processAssetFn;
        isMobileDevice = checkIfMobile();
        console.log(`Device detected as ${isMobileDevice ? 'mobile' : 'desktop'}`);
    }
    
    /**
     * Start QR code scanning
     */
    function startScanning() {
        if (isScanning) return;
        
        if (isMobileDevice) {
            // Mobile device: Use camera scanning
            startCameraScanning();
        } else {
            // Desktop: Use keyboard input mode for external scanners
            startExternalScannerMode();
        }
    }
    
    /**
     * Start camera-based QR scanning (for mobile devices)
     */
    function startCameraScanning() {
        // Create video and canvas elements if they don't exist
        setupVideoCanvas();
        
        // Check if the browser supports getUserMedia API
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            showScanError('Your browser does not support camera access for QR scanning.');
            return;
        }
        
        // Request camera access
        navigator.mediaDevices.getUserMedia({ 
            video: { facingMode: "environment" } // Use back camera if available
        })
        .then(function(stream) {
            videoElem.srcObject = stream;
            videoElem.setAttribute('playsinline', true); // Required for iOS
            videoElem.play();
            isScanning = true;
            
            // Start the scanning interval
            scanInterval = setInterval(scanQRCode, 500); // Scan every 500ms
        })
        .catch(function(error) {
            console.error('Error accessing camera:', error);
            showScanError('Could not access camera. Please check your camera permissions.');
        });
    }
    
    /**
     * Start external scanner mode (for desktop devices)
     * This mode listens for keyboard input from external QR scanners
     */
    function startExternalScannerMode() {
        // Create a container with instructions for desktop users
        setupDesktopScannerUI();
        
        // Reset scan buffer
        scanBuffer = '';
        isScanning = true;
        
        // Add event listener for keypress events from external scanner
        document.addEventListener('keypress', handleExternalScannerInput);
        
        console.log('External QR scanner mode activated. Ready to receive input.');
    }
    
    /**
     * Stop QR code scanning
     */
    function stopScanning() {
        if (!isScanning) return;
        
        if (isMobileDevice) {
            // Stop camera scanning
            stopCameraScanning();
        } else {
            // Stop external scanner mode
            stopExternalScannerMode();
        }
        
        isScanning = false;
    }
    
    /**
     * Stop camera scanning
     */
    function stopCameraScanning() {
        // Clear scan interval
        if (scanInterval) {
            clearInterval(scanInterval);
            scanInterval = null;
        }
        
        // Stop all video tracks
        if (videoElem && videoElem.srcObject) {
            videoElem.srcObject.getTracks().forEach(track => track.stop());
            videoElem.srcObject = null;
        }
        
        // Remove video and canvas elements
        removeVideoCanvas();
    }
    
    /**
     * Stop external scanner mode
     */
    function stopExternalScannerMode() {
        // Remove event listener for external scanner
        document.removeEventListener('keypress', handleExternalScannerInput);
        
        // Clear scan buffer and timeout
        scanBuffer = '';
        if (scanTimeout) {
            clearTimeout(scanTimeout);
            scanTimeout = null;
        }
        
        // Remove desktop scanner UI
        removeDesktopScannerUI();
    }
    
    /**
     * Handle input from external QR scanner (keypress events)
     * @param {Event} e - The keypress event
     */
    function handleExternalScannerInput(e) {
        // Make sure scanning is still active
        if (!isScanning) {
            return;
        }
        
        // Allow Enter key to work normally in search input
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }
        
        // Reset timeout if already waiting
        if (scanTimeout) {
            clearTimeout(scanTimeout);
        }
        
        // Process on Enter key
        if (e.key === 'Enter') {
            e.preventDefault(); // Prevent form submission
            processExternalScanBuffer();
            return;
        }
        
        // Add character to buffer
        scanBuffer += e.key;
        
        // Set timeout to process buffer after delay (for QR scanners that don't send Enter)
        scanTimeout = setTimeout(() => {
            if (scanBuffer.length > 0) {
                processExternalScanBuffer();
            }
        }, 100); // Short timeout for QR scanners, which typically send data quickly
        
        e.preventDefault();
    }
    
    /**
     * Process the external scan buffer
     */
    function processExternalScanBuffer() {
        if (scanBuffer.length === 0) return;
        
        console.log('External scanner input received:', scanBuffer);
        
        // Process the scanned QR code
        processQRCode(scanBuffer);
        
        // Clear the buffer
        scanBuffer = '';
    }
    
    /**
     * Create and append video and canvas elements for scanning
     */
    function setupVideoCanvas() {
        // Check if elements already exist
        if (videoElem && canvasElem) return;
        
        // Create container for scanner UI
        const containerDiv = document.createElement('div');
        containerDiv.id = 'qrScannerContainer';
        containerDiv.className = 'qr-scanner-container';
        
        // Create video element
        videoElem = document.createElement('video');
        videoElem.id = 'qrVideo';
        videoElem.className = 'qr-video';
        containerDiv.appendChild(videoElem);
        
        // Create canvas element (for processing frames)
        canvasElem = document.createElement('canvas');
        canvasElem.id = 'qrCanvas';
        canvasElem.className = 'qr-canvas';
        canvasElem.style.display = 'none';
        containerDiv.appendChild(canvasElem);
        
        // Add scan overlay
        const overlayDiv = document.createElement('div');
        overlayDiv.className = 'qr-scan-overlay';
        overlayDiv.innerHTML = `
            <div class="qr-scan-region"></div>
            <div class="qr-scan-instruction">Position the QR code within the frame</div>
        `;
        containerDiv.appendChild(overlayDiv);
        
        // Add to container
        const scanIndicatorContainer = document.getElementById('scanIndicatorContainer');
        scanIndicatorContainer.appendChild(containerDiv);
    }
    
    /**
     * Create UI for desktop external scanner mode
     */
    function setupDesktopScannerUI() {
        // Create container for desktop scanner UI
        const containerDiv = document.createElement('div');
        containerDiv.id = 'desktopScannerContainer';
        containerDiv.className = 'desktop-scanner-container alert alert-info';
        
        // Add instruction content
        containerDiv.innerHTML = `
            <div class="desktop-scanner-content">
                <i class="bi bi-upc-scan me-3" style="font-size: 1.5rem;"></i>
                <div>
                    <h5 class="mb-2">QR Scanner Mode Active</h5>
                    <p class="mb-0">Connect your QR scanner device and scan an asset tag.<br>
                    The scanner should work automatically like a keyboard input.</p>
                </div>
            </div>
        `;
        
        // Add to container
        const scanIndicatorContainer = document.getElementById('scanIndicatorContainer');
        scanIndicatorContainer.appendChild(containerDiv);
    }
    
    /**
     * Remove desktop scanner UI
     */
    function removeDesktopScannerUI() {
        const container = document.getElementById('desktopScannerContainer');
        if (container) {
            container.remove();
        }
    }
    
    /**
     * Remove video and canvas elements
     */
    function removeVideoCanvas() {
        const container = document.getElementById('qrScannerContainer');
        if (container) {
            container.remove();
        }
        videoElem = null;
        canvasElem = null;
    }
    
    /**
     * Process a video frame to detect QR codes
     */
    function scanQRCode() {
        if (!isScanning || !videoElem || !canvasElem) return;
        
        // Check if video is ready
        if (videoElem.readyState !== videoElem.HAVE_ENOUGH_DATA) return;
        
        // Get canvas context and draw video frame
        const ctx = canvasElem.getContext('2d');
        canvasElem.width = videoElem.videoWidth;
        canvasElem.height = videoElem.videoHeight;
        ctx.drawImage(videoElem, 0, 0, canvasElem.width, canvasElem.height);
        
        // Get image data for processing
        const imageData = ctx.getImageData(0, 0, canvasElem.width, canvasElem.height);
        
        try {
            // Use jsQR library if available
            if (window.jsQR) {
                const code = jsQR(imageData.data, imageData.width, imageData.height, {
                    inversionAttempts: "dontInvert",
                });
                
                if (code) {
                    processQRCode(code.data);
                }
            } else {
                // Fallback to simulation for demo purposes
                console.log("jsQR library not found");
                clearInterval(scanInterval);
            }
        } catch (error) {
            console.error('Error processing QR code:', error);
        }
    }
    
    /**
     * Process the scanned QR code data
     * @param {string} data - The QR code data
     */
    function processQRCode(data) {
        if (!data) return;
        
        // Temporarily pause scanning
        if (isMobileDevice && scanInterval) {
            clearInterval(scanInterval);
        }
        
        // Parse the QR code data (format: assetId|assetName)
        const parts = data.split('|');
        if (parts.length < 1) {
            console.error('Invalid QR code format:', data);
            if (isMobileDevice) {
                scanInterval = setInterval(scanQRCode, 500);
            }
            return;
        }
        
        // Extract asset ID (which is the first part before the pipe)
        const assetId = parts[0].trim();
        
        console.log('QR Code scanned:', data);
        console.log('Processing asset ID:', assetId);
        
        // Call the process asset callback with the asset ID
        if (processAssetCallback) {
            processAssetCallback(assetId, 'qrcode'); // Specify QR code method
            
            // Visual feedback that QR was scanned
            if (isMobileDevice) {
                const overlay = document.querySelector('.qr-scan-region');
                if (overlay) {
                    overlay.style.borderColor = '#28a745';
                    overlay.style.boxShadow = '0 0 0 4000px rgba(40, 167, 69, 0.3)';
                    
                    // Reset after a moment
                    setTimeout(() => {
                        overlay.style.borderColor = '#fff';
                        overlay.style.boxShadow = '0 0 0 4000px rgba(0, 0, 0, 0.3)';
                        scanInterval = setInterval(scanQRCode, 500);
                    }, 1000);
                } else {
                    scanInterval = setInterval(scanQRCode, 500);
                }
            } else {
                // Visual feedback for desktop scanner
                const container = document.getElementById('desktopScannerContainer');
                if (container) {
                    // Flash green background to indicate successful scan
                    container.style.backgroundColor = 'rgba(40, 167, 69, 0.2)';
                    setTimeout(() => {
                        container.style.backgroundColor = '';
                    }, 500);
                }
            }
        } else {
            if (isMobileDevice) {
                scanInterval = setInterval(scanQRCode, 500);
            }
        }
    }
    
    /**
     * Show an error message for scanning
     * @param {string} message - The error message
     */
    function showScanError(message) {
        const container = document.getElementById('scanIndicatorContainer');
        if (!container) return;
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger';
        errorDiv.innerHTML = `
            <i class="bi bi-exclamation-triangle-fill me-2"></i>
            <span>${message}</span>
        `;
        
        // Remove existing QR scanner container if present
        removeVideoCanvas();
        removeDesktopScannerUI();
        
        // Add error message
        container.appendChild(errorDiv);
    }
    
    // Return public API
    return {
        init,
        startScanning,
        stopScanning,
        isMobile: () => isMobileDevice
    };
})();

// Main application module
const AuditApp = (function() {
    // Load jsQR library dynamically
    function loadJsQRLibrary() {
        if (window.jsQR) return Promise.resolve();
        
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.min.js';
            script.onload = () => resolve();
            script.onerror = () => {
                console.warn('Could not load jsQR library. QR scanning will be simulated.');
                resolve(); // Resolve anyway to continue with simulation
            };
            document.head.appendChild(script);
        });
    }
    
    // Private state
    const state = {
        currentAuditMethod: 'manual',
        currentBuilding: null,
        currentFloor: null,
        currentRoom: null,
        expectedAssets: [],
        scannedAssets: [],
        isRoomAuditActive: false
    };
    
    // Barcode scanning state
    const scannerState = {
        isScanning: false,
        scanBuffer: '',
        scanTimeout: null,
        SCAN_TIMEOUT_MS: 20
    };
    
    // Simulation intervals
    let rfidSimulationInterval = null;
    let qrSimulationInterval = null;
    
    /**
     * Initialize the application
     */
    function init() {
        // Load jsQR library
        loadJsQRLibrary().then(() => {
            // Initialize QR scanner with asset processing callback
            QRScanner.init(processScannedAsset);
            
            // Setup other event listeners
            setupEventListeners();
            setAuditMethod('manual');
        });

        
    }
    
    /**
     * Set up all event listeners
     */
    function setupEventListeners() {
        // Method selection buttons
        document.querySelectorAll('.audit-method-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const method = e.currentTarget.dataset.method;
                setAuditMethod(method);
            });
        });
        
        // Room audit toggle button
        const toggleButton = document.getElementById('toggleRoomAudit');
        if (toggleButton) {
            toggleButton.addEventListener('click', toggleRoomAudit);
        }
        
        // Cancel audit button
        const cancelButton = document.getElementById('cancelRoomAudit');
        if (cancelButton) {
            cancelButton.addEventListener('click', cancelRoomAudit);
        }
        
        // Manual search button
        const searchButton = document.getElementById('manualSearchButton');
        if (searchButton) {
            searchButton.addEventListener('click', manualSearchAsset);
        }
        
        // Manual search input
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    manualSearchAsset();
                }
            });
        }
        
        // Global event listener to prevent Enter from stopping scan
        document.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && state.isRoomAuditActive) {
                // Only prevent default if not in a text input
                if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
                    e.preventDefault();
                }
            }
        }, true);

        document.addEventListener('click', function(e) {
            if (e.target.closest('.undo-scan-btn')) {
                const button = e.target.closest('.undo-scan-btn');
                const row = button.closest('tr');
                const assetId = row.querySelector('.asset-id').textContent;
                
                if (confirm(`Are you sure you want to undo the scan for asset ${assetId}?`)) {
                    AuditApp.undoScan(assetId);
                }
            }
        });
    }
    
    // --------------------------------------
    // Building, Floor, and Room Selection
    // --------------------------------------
    
    /**
     * Load floors for the selected building
     */
    function loadFloors() {
        const buildingSelect = document.getElementById('buildingSelect');
        state.currentBuilding = buildingSelect.value;
        
        // Reset selections
        state.currentFloor = null;
        state.currentRoom = null;
        
        if (state.currentBuilding && state.currentBuilding !== 'Select Building') {
            const floorSelectContainer = document.getElementById('floorSelectContainer');
            floorSelectContainer.style.display = 'block';
            const floorSelect = document.getElementById('floorSelect');
            
            floorSelect.innerHTML = '<option selected>Select Floor</option>';
            
            // Fetch floors for the selected building
            fetch(`/api/floors/${state.currentBuilding}`)
                .then(response => {
                    if (!response.ok) throw new Error('Failed to fetch floors');
                    return response.json();
                })
                .then(floors => {
                    floors.forEach(floor => {
                        const option = document.createElement('option');
                        option.value = floor.floor_id;
                        option.textContent = floor.floor_name;
                        floorSelect.appendChild(option);
                    });
                })
                .catch(error => {
                    console.error('Error fetching floors:', error);
                    UI.showMessage('Error loading floors. Please try again.', 'danger');
                });
            
            UI.hideElements(['roomSelectContainer', 'auditMethodButtons', 'searchContainer', 
                           'assetList', 'scannedAssetsList']);
        } else {
            UI.hideElements(['floorSelectContainer', 'roomSelectContainer', 'auditMethodButtons',
                           'searchContainer', 'assetList', 'scannedAssetsList']);
        }
    }
    
    /**
     * Load rooms for the selected floor
     */
    function loadRooms() {
        const floorSelect = document.getElementById('floorSelect');
        state.currentFloor = floorSelect.value;
        
        state.currentRoom = null;
        
        if (state.currentFloor && state.currentFloor !== 'Select Floor') {
            const roomSelectContainer = document.getElementById('roomSelectContainer');
            roomSelectContainer.style.display = 'block';
            const roomSelect = document.getElementById('roomSelect');
            
            roomSelect.innerHTML = '<option selected>Select Room</option>';
            
            // Fetch rooms for the selected floor
            fetch(`/api/rooms/${state.currentFloor}`)
                .then(response => {
                    if (!response.ok) throw new Error('Failed to fetch rooms');
                    return response.json();
                })
                .then(rooms => {
                    rooms.forEach(room => {
                        const option = document.createElement('option');
                        option.value = room.room_id;
                        option.textContent = room.room_name;
                        roomSelect.appendChild(option);
                    });
                })
                .catch(error => {
                    console.error('Error fetching rooms:', error);
                    UI.showMessage('Error loading rooms. Please try again.', 'danger');
                });
            
            UI.hideElements(['auditMethodButtons', 'searchContainer', 'assetList', 'scannedAssetsList']);
        } else {
            UI.hideElements(['roomSelectContainer', 'auditMethodButtons', 'searchContainer', 
                           'assetList', 'scannedAssetsList']);
        }
    }
    
    /**
     * Load assets for the selected room
     */
    function loadRoomAssets() {
        const roomSelect = document.getElementById('roomSelect');
        state.currentRoom = roomSelect.value;
        
        if (state.currentRoom && state.currentRoom !== 'Select Room') {
            UI.showElements(['auditMethodButtons', 'searchContainer']);
            
            // Fetch assets for the selected room
            fetch(`/api/assets/${state.currentRoom}`)
                .then(response => {
                    if (!response.ok) throw new Error('Failed to fetch assets');
                    return response.json();
                })
                .then(assets => {
                    if (assets && assets.length > 0) {
                        state.expectedAssets = assets.map(asset => {
                            // Normalize asset properties
                            return {
                                id: asset.id || asset['id:'] || asset.asset_id || '',
                                description: asset.description || 'Unknown Asset',
                                model: asset.model || '',
                                brand: asset.brand || '',
                                serial_number: asset.serial_number || '',
                                room_id: asset.room_id || state.currentRoom,
                                last_located: asset.last_located || state.currentRoom,
                                
                                // Make sure we preserve the assignee_name from the API
                                assignee_id: asset.assignee_id || 'Unassigned',
                                assignee_name: asset.assignee_name || (asset.assignee_id ? `Assignee ID: ${asset.assignee_id}` : 'Unassigned'),
                                
                                last_update: asset.last_update || new Date().toISOString(),
                                notes: asset.notes || '',
                                status: asset.status || 'Active',
                                found: false
                            };
                        });
                    } else {
                        state.expectedAssets = [];
                        UI.showMessage('No assets found in this room.', 'info');
                    }
                    
                    UI.displayExpectedAssets(state.expectedAssets);
                    UI.showElements(['assetList', 'scannedAssetsList']);
                })
                .catch(error => {
                    console.error('Error fetching assets:', error);
                    UI.showMessage('Error loading assets. Please try again.', 'danger');
                });
        } else {
            UI.hideElements(['auditMethodButtons', 'searchContainer', 'assetList', 'scannedAssetsList']);
        }
    }
    
    // --------------------------------------
    // Audit Method Management
    // --------------------------------------
    
    /**
     * Set the current audit method
     * @param {string} method - The audit method (manual, barcode, rfid, qrcode)
     */
    function setAuditMethod(method) {
        // Don't reset scanning if we're just changing methods
        if (method === state.currentAuditMethod) return;

        stopAllScanningMethods()
        
        // Stop the current scanning method
        if (state.currentAuditMethod === 'barcode') {
            stopBarcodeScan();
        } else if (state.currentAuditMethod === 'rfid') {
            if (rfidSimulationInterval) {
                clearInterval(rfidSimulationInterval);
                rfidSimulationInterval = null;
            }
        } else if (state.currentAuditMethod === 'qrcode') {
            // Stop real QR scanning
            QRScanner.stopScanning();
            
            // Also stop simulation if active
            if (qrSimulationInterval) {
                clearInterval(qrSimulationInterval);
                qrSimulationInterval = null;
            }
        }
        
        state.currentAuditMethod = method;
        
        // Update UI to show active method
        document.querySelectorAll('.audit-method-btn').forEach(btn => {
            btn.classList.remove('btn-primary');
            btn.classList.remove('active');
            btn.classList.add('btn-light');
        });

        const activeBtn = document.querySelector(`.audit-method-btn[data-method="${method}"]`);
        if (activeBtn) {
            activeBtn.classList.remove('btn-light');
            activeBtn.classList.add('btn-primary');
            activeBtn.classList.add('active');
        }

        // Update scanning interface for the new method
        UI.updateScanningInterface(method, state.isRoomAuditActive);
        
        // If room audit is active, start the new scanning method
        if (state.isRoomAuditActive) {
            startScanningMethod(method);
        }
    }
    
    /**
     * Start the appropriate scanning method
     * @param {string} method - The scanning method to start
     */
    function startScanningMethod(method) {
        if (!state.isRoomAuditActive) return;
        
        if (method === 'barcode') {
            startBarcodeScan();
        } else if (method === 'rfid') {
            startRFIDScan();
        } else if (method === 'qrcode') {
            startQRCodeScan();
        }
    }
    
    /**
     * Stop all active scanning methods
     */
    function stopAllScanningMethods() {
        // Stop barcode scanning
        if (scannerState.isScanning) {
            stopBarcodeScan();
        }
        
        // Stop RFID simulation
        if (rfidSimulationInterval) {
            clearInterval(rfidSimulationInterval);
            rfidSimulationInterval = null;
        }
        
        // Stop QR code scanning
        if (state.currentAuditMethod === 'qrcode') {
            QRScanner.stopScanning();
            
            if (qrSimulationInterval) {
                clearInterval(qrSimulationInterval);
                qrSimulationInterval = null;
            }
        }
    }
    
    // --------------------------------------
    // Room Audit Controls
    // --------------------------------------
    
    /**
     * Toggle room audit state (start/stop)
     */
    function toggleRoomAudit() {
        // Toggle room audit state
        if (!state.isRoomAuditActive) {
            startRoomAudit();
        } else {
            // Show confirmation dialog with options
            if (confirm("Do you want to stop the audit? Unscanned assets will be marked as missing. Click Cancel to use the Cancel Audit option instead.")) {
                stopRoomAudit(true); // Stop with marking missing
            }
        }
    }
    
    /**
     * Cancel room audit without marking assets as missing
     */
    function cancelRoomAudit() {
        if (confirm("Are you sure you want to cancel the audit? No changes will be made to unscanned assets.")) {
            stopRoomAudit(false); // Stop without marking missing
            UI.showMessage('Audit cancelled. No assets were marked as missing.', 'info');
        }
    }
    
    /**
     * Start the room audit process
     */
    function startRoomAudit() {
        if (!state.currentRoom || state.currentRoom === 'Select Room') {
            UI.showMessage('Please select a room first', 'warning');
            return;
        }
        
        // If already active, do nothing
        if (state.isRoomAuditActive) return;
        
        state.isRoomAuditActive = true;
        
        // Update Toggle button
        const toggleButton = document.getElementById('toggleRoomAudit');
        toggleButton.innerHTML = '<i class="bi bi-stop-circle me-2"></i>Stop Room Audit';
        toggleButton.classList.remove('btn-success');
        toggleButton.classList.add('btn-danger');
        toggleButton.classList.add('active');
        
        // Show Cancel button
        const cancelButton = document.getElementById('cancelRoomAudit');
        if (cancelButton) {
            cancelButton.style.display = 'block';
        }
        
        // Disable room selection while audit is active
        document.getElementById('buildingSelect').disabled = true;
        document.getElementById('floorSelect').disabled = true;
        document.getElementById('roomSelect').disabled = true;
        
        // Update the UI
        UI.updateScanningInterface(state.currentAuditMethod, true);
        
        // Ensure Enter key doesn't trigger any default actions on the page
        document.addEventListener('keydown', preventEnterDefault, true);
        
        // Start the selected scanning method
        startScanningMethod(state.currentAuditMethod);
        
        UI.updateScanCounter(state.expectedAssets);
        
        UI.showMessage(`Audit started for room ${state.currentRoom}`, 'success');
    }
    
    /**
     * Stop the room audit process
     * @param {boolean} markMissing - Whether to mark unscanned assets as missing
     */
    function stopRoomAudit(markMissing = true) {
        // If not active, do nothing
        if (!state.isRoomAuditActive) return;
        
        console.log("Stopping room audit, markMissing:", markMissing);
        
        state.isRoomAuditActive = false;
        
        stopAllScanningMethods();
        
        // Remove the Enter key prevention handler
        document.removeEventListener('keydown', preventEnterDefault, true);
        
        // Update the toggle button
        const toggleButton = document.getElementById('toggleRoomAudit');
        toggleButton.innerHTML = '<i class="bi bi-play-circle me-2"></i>Start Room Audit';
        toggleButton.classList.remove('btn-danger');
        toggleButton.classList.remove('active');
        toggleButton.classList.add('btn-success');
        
        // Hide Cancel button
        const cancelButton = document.getElementById('cancelRoomAudit');
        if (cancelButton) {
            cancelButton.style.display = 'none';
        }
        
        // Re-enable room selection
        document.getElementById('buildingSelect').disabled = false;
        document.getElementById('floorSelect').disabled = false;
        document.getElementById('roomSelect').disabled = false;
        
        UI.updateScanningInterface(state.currentAuditMethod, false);
        
        // Mark unscanned assets as missing if requested
        if (markMissing) {
            markUnscannedAssetsMissing();
            UI.showMessage('Audit completed. Unscanned assets marked as missing.', 'info');
        }
    }
    
    /**
     * Prevent Enter key default actions except in search input
     * @param {Event} e - The keydown event
     */
    function preventEnterDefault(e) {
        // Allow Enter in search input for manual searching
        if (e.target.id === 'searchInput') {
            return true;
        }
        
        if (e.key === 'Enter') {
            e.preventDefault();
            return false;
        }
    }
    
    // --------------------------------------
    // Barcode Scanning
    // --------------------------------------
    
    /**
     * Start barcode scanning
     */
    function startBarcodeScan() {
        if (!state.isRoomAuditActive || state.currentAuditMethod !== 'barcode') return;
        
        if (scannerState.isScanning) {
            // Already scanning, don't start again
            return;
        }
        
        scannerState.isScanning = true;
        scannerState.scanBuffer = '';
        
        // Add event listener for keypress events
        document.addEventListener('keypress', handleScannerInput);
        
        console.log('Barcode scanning started');
    }
    
    /**
     * Stop barcode scanning
     */
    function stopBarcodeScan() {
        if (!scannerState.isScanning) return;
        
        // Set scanning flag to false
        scannerState.isScanning = false;
        
        // Remove event listener
        document.removeEventListener('keypress', handleScannerInput);
        
        console.log('Barcode scanning stopped');
    }
    
    /**
     * Handle scanner input (keypress)
     * @param {Event} e - The keypress event
     */
    function handleScannerInput(e) {
        // Make sure scanning is still active
        if (!scannerState.isScanning || !state.isRoomAuditActive) {
            return;
        }
        
        // Allow Enter key to work normally in search input
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }
        
        // Reset timeout if already waiting
        if (scannerState.scanTimeout) {
            clearTimeout(scannerState.scanTimeout);
        }
        
        // Process on Enter key
        if (e.key === 'Enter') {
            e.preventDefault(); // Prevent form submission
            processScanBuffer();
            return;
        }
        
        // Add character to buffer
        scannerState.scanBuffer += e.key;
        
        // Set timeout to process buffer after delay (for barcode scanners that don't send Enter)
        scannerState.scanTimeout = setTimeout(() => {
            if (scannerState.scanBuffer.length > 0) {
                processScanBuffer();
            }
        }, scannerState.SCAN_TIMEOUT_MS);
        
        e.preventDefault();
    }
    
    /**
     * Process the scan buffer
     */
    function processScanBuffer() {
        if (scannerState.scanBuffer.length === 0) return;
        
        // Process the scanned barcode/ID
        processScannedAsset(scannerState.scanBuffer, 'barcode'); // Specify barcode method
        
        // Clear the buffer
        scannerState.scanBuffer = '';
        
        // Make sure we're still scanning after processing
        if (state.currentAuditMethod === 'barcode' && !scannerState.isScanning && state.isRoomAuditActive) {
            // If scanning got turned off somehow, turn it back on
            startBarcodeScan();
        }
    }
    
    // --------------------------------------
    // RFID and QR Code Scanning/Simulation
    // --------------------------------------
    
    /**
     * Start RFID scanning simulation
     */
    function startRFIDScan() {
        if (!state.isRoomAuditActive || state.currentAuditMethod !== 'rfid') return;
        
        // Simulate RFID scanning at random intervals
        if (rfidSimulationInterval) clearInterval(rfidSimulationInterval);
        
        rfidSimulationInterval = setInterval(() => {
            if (state.expectedAssets.length > 0) {
                // Randomly select an asset to "scan" with higher probability for unscanned assets
                const unscannedAssets = state.expectedAssets.filter(asset => !asset.found);
                
                if (unscannedAssets.length > 0 && Math.random() > 0.2) {
                    // 80% chance to scan an unscanned asset
                    const randomIndex = Math.floor(Math.random() * unscannedAssets.length);
                    processScannedAsset(unscannedAssets[randomIndex].id, 'rfid'); // Specify RFID method
                } else if (state.expectedAssets.length > 0) {
                    // 20% chance to scan any asset
                    const randomIndex = Math.floor(Math.random() * state.expectedAssets.length);
                    processScannedAsset(state.expectedAssets[randomIndex].id, 'rfid'); // Specify RFID method
                }
                
                // 5% chance to scan an unexpected asset
                if (Math.random() < 0.05) {
                    const randomId = 'RFID-' + Math.floor(Math.random() * 10000);
                    processScannedAsset(randomId, 'rfid'); // Specify RFID method
                }
            }
        }, 3000); // Simulate a scan every 3 seconds
    }
    
    /**
     * Start QR Code scanning
     */
    function startQRCodeScan() {
        if (!state.isRoomAuditActive || state.currentAuditMethod !== 'qrcode') return;
        
        // Stop simulation if running
        if (qrSimulationInterval) {
            clearInterval(qrSimulationInterval);
            qrSimulationInterval = null;
        }
        
        // Start the QR scanner using the camera
        QRScanner.startScanning();
    }
    
    // --------------------------------------
    // Asset Processing
    // --------------------------------------
    
    /**
     * Manual search for an asset
     */
    async function manualSearchAsset() {
        if (!state.isRoomAuditActive) {
            UI.showMessage('Please start a room audit first', 'warning');
            return;
        }
        
        const searchInput = document.getElementById('searchInput');
        const assetId = searchInput.value.trim();
       
        if (!assetId) {
            UI.showMessage('Please enter an asset ID', 'warning');
            return;
        }
    
        try {
            await processScannedAsset(assetId, 'manual'); // Specify manual method
            // Clear the input after successful processing
            searchInput.value = '';
            // Focus back on the input for the next scan
            searchInput.focus();
        } catch (error) {
            console.error('Error in manual search:', error);
            UI.showMessage('Error processing asset', 'danger');
        }
    }
    
    /**
     * Process a scanned asset
     * @param {string} assetId - The ID of the scanned asset
     */
    async function processScannedAsset(assetId, scanMethod) {
        // Add scanMethod parameter with default to manual if not specified
        scanMethod = scanMethod || 'manual';
        
        if (!state.isRoomAuditActive) return;
        
        // Check if the asset is in the expected assets list for this room
        const assetInRoom = state.expectedAssets.find(a => a.id === assetId);
        
        if (assetInRoom) {
            // Asset is expected in this room
            if (!assetInRoom.found) {
                // First time scanning this asset
                await updateAssetLocation(assetInRoom.id, state.currentRoom);
                markAssetAsFound(assetInRoom, scanMethod); // Pass scan method
            } else {
                // Asset already scanned
                UI.showMessage(`Asset already scanned: ${assetInRoom.description} (${assetInRoom.id})`, 'info');
            }
        } else {
            // Asset not in expected list, check if it exists elsewhere
            try {
                const response = await fetch(`/api/asset/${assetId}`);
                
                if (response.ok) {
                    // Asset exists in database but not in this room
                    const asset = await response.json();
                    
                    // Update asset location to current room and mark as misplaced
                    await updateAssetLocation(assetId, state.currentRoom);
                    
                    // Make sure we preserve the assignee_name from the API
                    if (!asset.assignee_name && asset.assignee_id) {
                        asset.assignee_name = `Assignee ID: ${asset.assignee_id}`;
                    }
                    
                    addMisplacedAsset(asset, scanMethod); // Pass scan method
                } else {
                    // Asset not found in database - automatically add as unexpected
                    addUnexpectedAsset(assetId, scanMethod); // Pass scan method
                    UI.showMessage(`Unknown asset: ${assetId} - Added as unexpected asset`, 'warning');
                }
            } catch (error) {
                console.error('Error checking asset in database:', error);
                UI.showMessage(`Error checking asset: ${assetId}`, 'danger');
            }
        }
    }
    
    /**
     * Update asset location in the database
     * @param {string} assetId - The ID of the asset
     * @param {string} roomId - The ID of the room
     */
    async function updateAssetLocation(assetId, roomId) {
        try {
            const response = await fetch('/api/update-asset-location', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    assetId: assetId,
                    roomId: roomId
                })
            });
            
            if (!response.ok) {
                console.error('Failed to update asset location:', await response.text());
            }
        } catch (error) {
            console.error('Error updating asset location:', error);
        }
    }
    
    /**
     * Mark an asset as found
     * @param {Object} asset - The asset to mark as found
     */
    function markAssetAsFound(asset, scanMethod) {
        asset.found = true;
        asset.status = 'Good';
        asset.last_located = state.currentRoom;
        asset.last_update = new Date().toISOString();
        asset.scanTime = new Date().toISOString();
        asset.scanMethod = scanMethod; // Store the scan method
        
        // Ensure assignee_name is preserved
        if (!asset.assignee_name && asset.assignee_id) {
            if (typeof asset.assignee_id === 'number' || 
                (typeof asset.assignee_id === 'string' && !isNaN(parseInt(asset.assignee_id)))) {
                // If it looks like a numeric ID, format it differently
                asset.assignee_name = `Assignee ${asset.assignee_id}`;
            } else {
                // It's probably already a name or text identifier
                asset.assignee_name = asset.assignee_id;
            }
        }
        
        // Update UI
        UI.updateAssetFoundStatus(asset, true);
        
        // Add to scanned assets list if not already there
        if (!state.scannedAssets.find(a => a.id === asset.id)) {
            // Create a copy to prevent reference issues
            const assetCopy = {...asset};
            state.scannedAssets.push(assetCopy);
            UI.updateScannedAssetsTable(state.scannedAssets, state.currentRoom);
        }
        
        UI.updateScanCounter(state.expectedAssets);
        
        UI.showMessage(`Asset found: ${asset.description} (${asset.id})`, 'success');
    }
    
    /**
     * Add a misplaced asset to scanned assets
     * @param {Object} asset - The misplaced asset
     */
    function addMisplacedAsset(asset, scanMethod) {
        // Format the asset data
        const assetId = asset.id || asset['id:'] || '';
        const formattedAsset = {
            id: assetId,
            description: asset.description || 'Unknown Asset',
            brand: asset.brand || 'Unknown',
            model: asset.model || 'Unknown',
            status: 'Misplaced',
            room_id: asset.room_id || 'Unknown',
            last_located: state.currentRoom,
            assignee_id: asset.assignee_id || 'Unassigned',
            last_update: asset.last_update || new Date().toISOString(),
            scanTime: new Date().toISOString(),
            scanMethod: scanMethod, // Store the scan method
            found: true
        };
        
        // Copy assignee_name if available
        if (asset.assignee_name) {
            formattedAsset.assignee_name = asset.assignee_name;
        }
        
        // Add to scanned assets list if not already there
        if (!state.scannedAssets.find(a => a.id === assetId)) {
            state.scannedAssets.push(formattedAsset);
            UI.updateScannedAssetsTable(state.scannedAssets, state.currentRoom);
        }
        
        UI.showMessage(
            `Asset found: ${formattedAsset.description} (${assetId}) - Not assigned to this room!`, 
            'warning'
        );
    }
    
    
    /**
     * Add an unexpected asset to scanned assets
     * @param {string} assetId - The ID of the unexpected asset
     */
    function addUnexpectedAsset(assetId, scanMethod) {
        const unexpectedAsset = {
            id: assetId,
            description: 'Unexpected Asset',
            brand: 'Unknown',
            model: 'Unknown',
            status: 'Unexpected',
            room_id: 'Unknown',
            last_located: state.currentRoom,
            assignee_id: 'Unassigned',
            assignee_name: 'Unassigned', // Add assignee_name explicitly
            last_update: new Date().toISOString(),
            scanTime: new Date().toISOString(),
            scanMethod: scanMethod, // Store the scan method
            found: true
        };
        
        // Add to scanned assets list
        state.scannedAssets.push(unexpectedAsset);
        UI.updateScannedAssetsTable(state.scannedAssets, state.currentRoom);
        
        UI.showMessage(`Unexpected asset added: ${assetId}`, 'warning');
    }
    
    /**
     * Mark unscanned assets as missing
     */
    function markUnscannedAssetsMissing() {
        let missingCount = 0;
        const missingAssets = [];
        
        state.expectedAssets.forEach(asset => {
            if (!asset.found) {
                asset.status = 'Missing';
                missingCount++;
                missingAssets.push(asset.id);
                
                // Update status in the UI
                UI.updateAssetStatus(asset.id, 'Missing');
            }
        });
        
        console.log(`Marking ${missingCount} assets as missing:`, missingAssets);
        
        if (missingCount > 0) {
            // Update the assets in the database
            updateMissingAssets(missingAssets);
            UI.showMessage(`${missingCount} assets marked as missing`, 'warning');
        }
    }
    
    /**
     * Update missing assets in the database
     * @param {Array} missingAssetIds - Array of missing asset IDs
     */
    async function updateMissingAssets(missingAssetIds) {
        if (!missingAssetIds || missingAssetIds.length === 0) {
            console.log("No assets to mark as missing");
            return;
        }
        
        console.log(`Sending ${missingAssetIds.length} asset IDs to server for marking as missing:`, missingAssetIds);
        
        try {
            const response = await fetch('/api/mark-assets-missing', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    assetIds: missingAssetIds
                })
            });
            
            if (!response.ok) {
                const responseData = await response.json();
                console.error('Failed to mark assets as missing:', responseData);
                UI.showMessage(`Error marking assets as missing: ${responseData.message || 'Unknown error'}`, 'danger');
            } else {
                const responseData = await response.json();
                console.log(`Successfully marked ${responseData.processed_count || missingAssetIds.length} assets as missing`);
                
                // Confirm UI updates for all missing assets
                state.expectedAssets.forEach(asset => {
                    if (missingAssetIds.includes(asset.id)) {
                        asset.status = 'Missing';
                        UI.updateAssetStatus(asset.id, 'Missing');
                    }
                });
            }
        } catch (error) {
            console.error('Error marking assets as missing:', error);
            UI.showMessage(`Network error marking assets as missing: ${error.message}`, 'danger');
        }
    }
    function undoScan(assetId) {
        if (!state.isRoomAuditActive) {
            UI.showMessage('Audit must be active to undo scans', 'warning');
            return false;
        }
        
        // Check if the asset is in the scanned assets list
        const scannedIndex = state.scannedAssets.findIndex(a => a.id === assetId);
        if (scannedIndex === -1) {
            UI.showMessage(`Asset ${assetId} not found in scanned assets`, 'danger');
            return false;
        }
        
        const scannedAsset = state.scannedAssets[scannedIndex];
        
        // Remove from scanned assets
        state.scannedAssets.splice(scannedIndex, 1);
        
        // If this is an expected asset, mark it as not found
        const expectedAsset = state.expectedAssets.find(a => a.id === assetId);
        if (expectedAsset) {
            expectedAsset.found = false;
            // Update UI to show asset as not found
            UI.updateAssetFoundStatus(expectedAsset, false);
            UI.updateScanCounter(state.expectedAssets);
        }
        
        // Update the UI
        UI.updateScannedAssetsTable(state.scannedAssets, state.currentRoom);
        
        // Show success message
        UI.showMessage(`Scan for asset ${assetId} has been undone`, 'success');
        
        return true;
    }
    
    
    // Return public methods
    return {
        init,
        loadFloors,
        loadRooms,
        loadRoomAssets,
        manualSearchAsset,
        undoScan  // Add this
    };
})();

// UI Module for handling templates and DOM updates
const UI = (function() {
    /**
     * Display expected assets in the table
     * @param {Array} assets - The expected assets
     */
    function displayExpectedAssets(assets) {
        const tableBody = document.getElementById('expectedAssetsTableBody');
        tableBody.innerHTML = '';
        
        if (!assets || assets.length === 0) {
            const emptyTemplate = document.getElementById('empty-state-template');
            const clone = document.importNode(emptyTemplate.content, true);
            const row = clone.querySelector('td');
            row.textContent = 'No assets expected in this room';
            tableBody.appendChild(clone);
            return;
        }
        
        // Create a document fragment for better performance
        const fragment = document.createDocumentFragment();
        
        assets.forEach(asset => {
            const row = createExpectedAssetRow(asset);
            fragment.appendChild(row);
        });
        
        tableBody.appendChild(fragment);
        
        // Clear the scanned assets table
        document.getElementById('scannedAssetsTableBody').innerHTML = '';
        
        // Initialize scan counter
        updateScanCounter(assets);
    }
    
    /**
     * Create a row for an expected asset
     * @param {Object} asset - The asset data
     * @returns {HTMLElement} The row element
     */
    function createExpectedAssetRow(asset) {
        const template = document.getElementById('expected-asset-row-template');
        const clone = document.importNode(template.content, true);
        
        // Set row ID for later reference
        const row = clone.querySelector('tr');
        row.id = `expected-asset-${asset.id}`;
        
        // Fill in data
        clone.querySelector('.asset-description').textContent = asset.description;
        clone.querySelector('.asset-id').textContent = asset.id;
        clone.querySelector('.asset-brand-model').textContent = `${asset.brand} ${asset.model}`;

        const assigneeText = clone.querySelector('.asset-assignee');
        if (asset.assignee_name) {
            assigneeText.textContent = asset.assignee_name;
        } else if (asset.assignee_id) {
            // If we only have ID, try to make it look better than just a number
            if (asset.assignee_id === 'Unassigned' || 
                asset.assignee_id === 'Unknown' || 
                typeof asset.assignee_id === 'string') {
                assigneeText.textContent = asset.assignee_id;
            } else {
                // placeholder text
                assigneeText.textContent = `Assignee: ${asset.assignee_id}`;
            }
        } else {
            assigneeText.textContent = 'Unassigned';
        }

        
        // Status
        const statusDot = clone.querySelector('.status-dot');
        const statusText = clone.querySelector('.status-text');
        
        if (asset.status === 'Missing') {
            statusDot.className = 'status-dot status-poor';
            statusText.textContent = 'Missing';
        } else if (asset.status === 'Misplaced') {
            statusDot.className = 'status-dot status-warning';
            statusText.textContent = 'Misplaced';
        } else {
            statusDot.className = 'status-dot status-good';
            statusText.textContent = 'Good';
        }
        
        // Last updated
        const lastUpdated = clone.querySelector('.asset-last-updated');
        const date = new Date(asset.last_update);
        lastUpdated.textContent = date.toLocaleDateString();
        
        // Found status
        const foundStatus = clone.querySelector('.asset-found-status');
        foundStatus.id = `found-status-${asset.id}`;
        foundStatus.className = asset.found ? 'found-yes' : 'found-no';
        foundStatus.textContent = asset.found ? 'YES' : 'NO';
        
        return clone;
    }
    
    /**
     * Update the scanned assets table
     * @param {Array} assets - The scanned assets
     * @param {string} currentRoom - The current room ID
     */
    function updateScannedAssetsTable(assets, currentRoom) {
        const tableBody = document.getElementById('scannedAssetsTableBody');
        tableBody.innerHTML = '';
        
        if (!assets || assets.length === 0) {
            const emptyTemplate = document.getElementById('empty-state-template');
            const clone = document.importNode(emptyTemplate.content, true);
            const row = clone.querySelector('td');
            row.textContent = 'No assets scanned yet';
            tableBody.appendChild(clone);
            return;
        }
        
        // Sort assets: misplaced or unexpected first, then by scan time (most recent first)
        const sortedAssets = [...assets].sort((a, b) => {
            if (a.status === 'Misplaced' && b.status !== 'Misplaced') return -1;
            if (a.status !== 'Misplaced' && b.status === 'Misplaced') return 1;
            if (a.status === 'Unexpected' && b.status !== 'Unexpected') return -1;
            if (a.status !== 'Unexpected' && b.status === 'Unexpected') return 1;
            
            // Sort by scan time (most recent first)
            return new Date(b.scanTime || b.last_update) - new Date(a.scanTime || a.last_update);
        });
        
        // Create a document fragment for better performance
        const fragment = document.createDocumentFragment();
        
        sortedAssets.forEach(asset => {
            const row = createScannedAssetRow(asset, currentRoom);
            fragment.appendChild(row);
        });
        
        tableBody.appendChild(fragment);
        
        // Show the scanned assets list
        document.getElementById('scannedAssetsList').style.display = 'block';
    }
    
    /**
     * Create a row for a scanned asset
     * @param {Object} asset - The asset data
     * @param {string} currentRoom - The current room ID
     * @returns {HTMLElement} The row element
     */
    function createScannedAssetRow(asset, currentRoom) {
        const template = document.getElementById('scanned-asset-row-template');
        const clone = document.importNode(template.content, true);
        
        // Set row class based on status
        const row = clone.querySelector('tr');
        if (asset.status === 'Unexpected' || asset.status === 'Misplaced') {
            row.classList.add('table-warning');
        }
        
        // Fill in data
        clone.querySelector('.asset-description').textContent = asset.description;
        clone.querySelector('.asset-id').textContent = asset.id;
        clone.querySelector('.asset-brand-model').textContent = `${asset.brand || ''} ${asset.model || ''}`;
        
        // Location
        const locationCell = clone.querySelector('.asset-location');
        const roomSelect = document.getElementById('roomSelect');
        const currentRoomName = roomSelect ? 
            roomSelect.options[roomSelect.selectedIndex].textContent : 
            `Room ${currentRoom}`;
            
        if (asset.status === 'Misplaced') {
            locationCell.innerHTML = `<span class="text-warning">Current: ${currentRoomName}</span><br>
                                     <small>Assigned: Room ${asset.room_id}</small>`;
        } else {
            locationCell.textContent = currentRoomName;
        }
        
        // Status
        const statusDot = clone.querySelector('.status-dot');
        const statusText = clone.querySelector('.status-text');
        
        if (asset.status === 'Unexpected') {
            statusDot.className = 'status-dot status-warning';
            statusText.textContent = 'Unexpected';
        } else if (asset.status === 'Misplaced') {
            statusDot.className = 'status-dot status-warning';
            statusText.textContent = 'Misplaced';
        } else if (asset.status === 'Good') {
            statusDot.className = 'status-dot status-good';
            statusText.textContent = 'Good';
        } else {
            statusDot.className = 'status-dot status-poor';
            statusText.textContent = asset.status;
        }
        
        // Assignee
        const assigneeText = clone.querySelector('.asset-assignee');
        if (asset.assignee_name) {
            assigneeText.textContent = asset.assignee_name;
        } else if (asset.assignee_id) {
            // If we only have ID, try to make it look better than just a number
            if (asset.assignee_id === 'Unassigned' || 
                asset.assignee_id === 'Unknown' || 
                typeof asset.assignee_id === 'string') {
                assigneeText.textContent = asset.assignee_id;
            } else {
                //add placeholder text
                assigneeText.textContent = `Assignee ${asset.assignee_id}`;
            }
        } else {
            assigneeText.textContent = 'Unassigned';
        }
        
        // Last updated
        const lastUpdated = clone.querySelector('.asset-last-updated');
        const date = new Date(asset.scanTime || asset.last_update);
        lastUpdated.textContent = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
        
        // Add scan method badge
        const methodCell = clone.querySelector('.asset-scan-method');
        if (methodCell && asset.scanMethod) {
            let badgeClass = '';
            switch(asset.scanMethod) {
                case 'manual':
                    badgeClass = 'bg-secondary';
                    break;
                case 'barcode':
                    badgeClass = 'bg-info';
                    break;
                case 'rfid':
                    badgeClass = 'bg-primary';
                    break;
                case 'qrcode':
                    badgeClass = 'bg-success';
                    break;
                default:
                    badgeClass = 'bg-secondary';
            }
            
            methodCell.innerHTML = `<span class="badge ${badgeClass}">${asset.scanMethod}</span>`;
        } else if (methodCell) {
            methodCell.textContent = 'unknown';
        }
        
        return clone;
    }
    
    /**
     * Update the scan counter
     * @param {Array} assets - The expected assets
     */
    function updateScanCounter(assets) {
        const foundCount = assets.filter(asset => asset.found).length;
        const totalCount = assets.length;
        const percentage = Math.round(foundCount/totalCount*100 || 0);
        
        // Get or create scan counter
        let scanCounterContainer = document.getElementById('scanCounterContainer');
        if (!scanCounterContainer) {
            console.error('Scan counter container not found');
            return;
        }
        
        // Clear existing counter
        scanCounterContainer.innerHTML = '';
        
        // Create new counter from template
        const template = document.getElementById('scan-counter-template');
        const clone = document.importNode(template.content, true);
        
        // Update counter values
        clone.querySelector('.counter-text').textContent = `${foundCount} of ${totalCount} assets found (${percentage}%)`;
        
        // Update progress bar
        const progressBar = clone.querySelector('.progress-bar');
        progressBar.style.width = `${percentage}%`;
        
        // Change color if all assets found
        const counterAlert = clone.querySelector('.scan-counter');
        if (foundCount === totalCount && totalCount > 0) {
            counterAlert.classList.remove('alert-primary');
            counterAlert.classList.add('alert-success');
            clone.querySelector('.counter-title').innerHTML += ' <i class="bi bi-check-circle-fill"></i>';
        }
        
        scanCounterContainer.appendChild(clone);
    }
    
    /**
     * Update the found status of an asset in the UI
     * @param {Object} asset - The asset
     * @param {boolean} highlight - Whether to highlight the row
     */
    function updateAssetFoundStatus(asset, isFound) {
        const foundCell = document.getElementById(`found-status-${asset.id}`);
        if (foundCell) {
            if (isFound) {
                foundCell.className = 'found-yes';
                foundCell.textContent = 'YES';
                
                // Highlight the row briefly to show it was found
                const row = document.getElementById(`expected-asset-${asset.id}`);
                if (row) {
                    row.classList.add('highlight-success');
                    setTimeout(() => {
                        row.classList.remove('highlight-success');
                    }, 2000);
                }
            } else {
                // Reset to not found
                foundCell.className = 'found-no';
                foundCell.textContent = 'NO';
            }
        }
    }
    
    /**
     * Update the status of an asset in the UI
     * @param {string} assetId - The asset ID
     * @param {string} status - The new status
     */
    function updateAssetStatus(assetId, status) {
        const row = document.getElementById(`expected-asset-${assetId}`);
        if (!row) return;
        
        const statusCell = row.querySelector('.asset-status');
        if (!statusCell) return;
        
        const statusDot = statusCell.querySelector('.status-dot');
        const statusText = statusCell.querySelector('.status-text');
        
        // Update status UI
        if (status === 'Missing') {
            statusDot.className = 'status-dot status-poor';
            statusText.textContent = 'Missing';
        } else if (status === 'Misplaced') {
            statusDot.className = 'status-dot status-warning';
            statusText.textContent = 'Misplaced';
        } else if (status === 'Good') {
            statusDot.className = 'status-dot status-good';
            statusText.textContent = 'Good';
        } else {
            statusDot.className = 'status-dot status-poor';
            statusText.textContent = status;
        }
    }
    
    /**
     * Show a message to the user
     * @param {string} message - The message text
     * @param {string} type - The message type (success, info, warning, danger)
     */
    function showMessage(message, type) {
        const container = document.getElementById('scanMessageContainer');
        if (!container) return;
        
        // Clear previous message
        container.innerHTML = '';
        
        // Create message from template
        const template = document.getElementById('scan-message-template');
        const clone = document.importNode(template.content, true);
        
        // Configure message
        const alert = clone.querySelector('.scan-message');
        alert.classList.add(`alert-${type}`);
        
        // Set icon based on type
        const icon = clone.querySelector('.bi');
        switch (type) {
            case 'success':
                icon.className = 'bi bi-check-circle-fill';
                break;
            case 'warning':
                icon.className = 'bi bi-exclamation-triangle-fill';
                break;
            case 'danger':
                icon.className = 'bi bi-x-circle-fill';
                break;
            default:
                icon.className = 'bi bi-info-circle-fill';
        }
        
        // Set message text
        clone.querySelector('.message-text').textContent = message;
        
        // Add to container
        container.appendChild(clone);
        
        // Auto-hide after delay for success and info messages
        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                const messageElement = container.querySelector('.scan-message');
                if (messageElement) {
                    messageElement.style.opacity = '0';
                    setTimeout(() => {
                        container.innerHTML = '';
                    }, 300);
                }
            }, 3000);
        }
    }
    
    /**
     * Update the scanning interface for the current method
     * @param {string} method - The current scanning method
     * @param {boolean} isActive - Whether scanning is active
     */
    function updateScanningInterface(method, isActive) {
        const manualSearchGroup = document.getElementById('manualSearchGroup');
        const container = document.getElementById('scanIndicatorContainer');
        
        // Clear existing indicators
        container.innerHTML = '';
        
        if (method === 'manual') {
            manualSearchGroup.style.display = 'flex';
            document.getElementById('searchInput').placeholder = "Enter asset ID...";
        } else {
            manualSearchGroup.style.display = 'none';
        }
        
        // If scanning is active, show the appropriate indicator
        if (isActive) {
            if (method !== 'manual') {
                // Create appropriate indicator
                container.appendChild(createScanIndicator(method));
            }
        }
    }
    
    /**
     * Create a scan indicator element
     * @param {string} method - The scanning method
     * @returns {HTMLElement} The scan indicator element
     */
    function createScanIndicator(method) {
        const template = document.getElementById('scan-indicator-template');
        const clone = document.importNode(template.content, true);
        
        const indicator = clone.querySelector('.scan-indicator');
        const icon = clone.querySelector('.bi');
        const title = clone.querySelector('.indicator-title');
        const text = clone.querySelector('.indicator-text');
        
        // Configure based on method
        switch (method) {
            case 'barcode':
                icon.className = 'bi bi-upc-scan';
                title.textContent = 'Barcode scanning active';
                text.textContent = 'Scan assets or select a different scanning method';
                break;
            case 'rfid':
                icon.className = 'bi bi-broadcast';
                title.textContent = 'RFID scanning active';
                text.textContent = 'Please place RFID reader near assets to scan';
                break;
            case 'qrcode':
                icon.className = 'bi bi-qr-code-scan';
                title.textContent = 'QR Code scanning active';
                text.textContent = 'Point the camera at QR codes to scan';
                break;
        }
        
        return clone;
    }
    
    /**
     * Hide multiple elements
     * @param {Array} elementIds - Array of element IDs to hide
     */
    function hideElements(elementIds) {
        elementIds.forEach(id => {
            const element = document.getElementById(id);
            if (element) element.style.display = 'none';
        });
    }
    
    /**
     * Show multiple elements
     * @param {Array} elementIds - Array of element IDs to show
     */
    function showElements(elementIds) {
        elementIds.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                if (id === 'auditMethodButtons') {
                    element.style.display = 'flex';
                } else {
                    element.style.display = 'block';
                }
            }
        });
    }
    
    // Return public methods
    return {
        displayExpectedAssets,
        updateScannedAssetsTable,
        updateScanCounter,
        updateAssetFoundStatus,
        updateAssetStatus,
        showMessage,
        updateScanningInterface,
        hideElements,
        showElements
    };
})();

// Initialize the application on document ready
document.addEventListener('DOMContentLoaded', function() {
    AuditApp.init();
});