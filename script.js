// Initialize map centered on UNPAD Jatinangor
const map = L.map('map').setView([-7.374928, 107.497925], 11);

// Add OpenStreetMap tiles
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap'
}).addTo(map);

// State
let currentMarker = null;
let currentMode = 'direct'; // 'direct' or 'convert'
const defaultView = { lat: -7.374928, lng: 107.497925, zoom: 11 };

// DOM Elements
const latInput = document.getElementById('lat');
const lngInput = document.getElementById('lng');
const keteranganInput = document.getElementById('keterangan');
const runBtn = document.getElementById('run-btn');
const resetBtn = document.getElementById('reset-btn');
const outputText = document.getElementById('output-text');

// Mode toggle elements
const modeDirectBtn = document.getElementById('mode-direct-btn');
const modeConvertBtn = document.getElementById('mode-convert-btn');
const uploadDirectSection = document.getElementById('upload-direct');
const uploadConvertSection = document.getElementById('upload-convert');

// Mode 1 (Direct) elements
const fileInput = document.getElementById('file-upload');
const fileNameDisplay = document.getElementById('file-name-display');
const fileWrapper = document.getElementById('file-wrapper');

// Mode 2 (Convert) elements
const binInput = document.getElementById('bin-upload');
const jsonInput = document.getElementById('json-upload');
const binNameDisplay = document.getElementById('bin-name-display');
const jsonNameDisplay = document.getElementById('json-name-display');
const binWrapper = document.getElementById('bin-wrapper');
const jsonWrapper = document.getElementById('json-wrapper');

// HVSR Graph & Zoom elements
const hvsrPlot = document.getElementById('hvsr-plot');
const graphPlaceholder = document.getElementById('graph-placeholder');
const zoomModal = document.getElementById('zoom-modal');
const zoomImg = document.getElementById('zoom-img');
const zoomCloseBtn = document.getElementById('zoom-close-btn');
const zoomBackdrop = document.querySelector('.zoom-modal-backdrop');

// ======== MODE TOGGLE LOGIC ========
function setMode(mode) {
    currentMode = mode;

    // Toggle button active state
    modeDirectBtn.classList.toggle('active', mode === 'direct');
    modeConvertBtn.classList.toggle('active', mode === 'convert');

    // Toggle upload sections
    uploadDirectSection.style.display = mode === 'direct' ? 'block' : 'none';
    uploadConvertSection.style.display = mode === 'convert' ? 'grid' : 'none';
}

modeDirectBtn.addEventListener('click', () => setMode('direct'));
modeConvertBtn.addEventListener('click', () => setMode('convert'));

// ======== ZOOM FUNCTIONS ========
function openZoom(src) {
    zoomImg.src = src;
    zoomModal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeZoom() {
    zoomModal.classList.remove('active');
    document.body.style.overflow = '';
}

hvsrPlot.addEventListener('click', () => openZoom(hvsrPlot.src));
zoomCloseBtn.addEventListener('click', closeZoom);
zoomBackdrop.addEventListener('click', closeZoom);
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeZoom();
        if (typeof closeTutorial === 'function') {
            closeTutorial();
        }
    }
});

// ======== MAP LOGIC ========
function updateMarker(lat, lng) {
    if (currentMarker) {
        currentMarker.setLatLng([lat, lng]);
    } else {
        currentMarker = L.marker([lat, lng]).addTo(map);
    }
    map.panTo([lat, lng]);
}

map.on('click', (e) => {
    const { lat, lng } = e.latlng;
    latInput.value = lat.toFixed(6);
    lngInput.value = lng.toFixed(6);
    updateMarker(lat, lng);
});

function handleInputChange() {
    const lat = parseFloat(latInput.value);
    const lng = parseFloat(lngInput.value);
    if (!isNaN(lat) && !isNaN(lng)) {
        updateMarker(lat, lng);
    }
}

latInput.addEventListener('change', handleInputChange);
lngInput.addEventListener('change', handleInputChange);

// ======== FILE UPLOAD: MODE 1 (DIRECT) ========
const allowedExtensions = ['.mseed', '.miniseed', '.saf', '.minishark', '.sac', '.gcf', '.peer'];

// Drag and Drop for direct mode
fileWrapper.addEventListener('dragover', (e) => {
    e.preventDefault();
    fileWrapper.classList.add('dragover');
});

fileWrapper.addEventListener('dragleave', (e) => {
    e.preventDefault();
    fileWrapper.classList.remove('dragover');
});

fileWrapper.addEventListener('drop', (e) => {
    e.preventDefault();
    fileWrapper.classList.remove('dragover');

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        fileInput.files = e.dataTransfer.files;
        const event = new Event('change');
        fileInput.dispatchEvent(event);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        const fileName = e.target.files[0].name;
        const ext = '.' + fileName.split('.').pop().toLowerCase();

        if (!allowedExtensions.includes(ext)) {
            alert(`Format file tidak didukung.\n\nFormat yang diizinkan: ${allowedExtensions.join(', ')}`);
            fileInput.value = '';
            fileNameDisplay.textContent = 'File mikrotremor belum ada';
            return;
        }

        fileNameDisplay.textContent = fileName;
    } else {
        fileNameDisplay.textContent = 'File mikrotremor belum ada';
    }
});

// ======== FILE UPLOAD: MODE 2 (CONVERT) ========
function setupDualDropzone(wrapper, input, nameDisplay, acceptExt) {
    wrapper.addEventListener('dragover', (e) => {
        e.preventDefault();
        wrapper.classList.add('dragover');
    });

    wrapper.addEventListener('dragleave', (e) => {
        e.preventDefault();
        wrapper.classList.remove('dragover');
    });

    wrapper.addEventListener('drop', (e) => {
        e.preventDefault();
        wrapper.classList.remove('dragover');

        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            const ext = '.' + file.name.split('.').pop().toLowerCase();

            if (ext !== acceptExt) {
                alert(`File harus berformat ${acceptExt}`);
                return;
            }

            input.files = e.dataTransfer.files;
            nameDisplay.textContent = file.name;
        }
    });

    input.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            nameDisplay.textContent = e.target.files[0].name;
        } else {
            nameDisplay.textContent = `File ${acceptExt} belum ada`;
        }
    });
}

setupDualDropzone(binWrapper, binInput, binNameDisplay, '.bin');
setupDualDropzone(jsonWrapper, jsonInput, jsonNameDisplay, '.json');

// ======== RUN BUTTON ========
runBtn.addEventListener('click', async () => {
    const lat = latInput.value.trim();
    const lng = lngInput.value.trim();

    // Validate coordinates
    if (!lat || !lng) {
        alert('Masukan koordinat terlebih dahulu.');
        return;
    }

    // Validate files based on mode
    if (currentMode === 'direct') {
        if (fileInput.files.length === 0) {
            alert('Silahkan masukan file mikrotremor terlebih dahulu.');
            return;
        }
    } else {
        if (binInput.files.length === 0 || jsonInput.files.length === 0) {
            alert('Silahkan masukan file .bin dan .json terlebih dahulu.');
            return;
        }
    }

    // Build FormData
    const formData = new FormData();
    formData.append('lat', lat);
    formData.append('lng', lng);
    formData.append('keterangan', keteranganInput.value.trim());
    formData.append('mode', currentMode);

    if (currentMode === 'direct') {
        formData.append('file', fileInput.files[0]);
    } else {
        formData.append('bin_file', binInput.files[0]);
        formData.append('json_file', jsonInput.files[0]);
    }

    // Show loading state
    outputText.innerHTML = 'Sabar data sedang diolah dulu...';
    runBtn.disabled = true;
    runBtn.querySelector('.btn-text').textContent = 'Mengolah data…';

    try {
        const response = await fetch('/process', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            outputText.innerHTML = `<strong>Error:</strong> ${data.error || 'An unknown error occurred.'}`;
            return;
        }

        // Display results
        const f0 = parseFloat(data.f0).toFixed(3);
        const a0 = parseFloat(data.a0).toFixed(3);
        const kg = data.kg !== undefined ? parseFloat(data.kg).toFixed(3) : 'N/A';
        const explanation = data.explanation || 'No explanation available.';

        // Show HVSR plot
        if (data.plot_url) {
            hvsrPlot.src = data.plot_url + '?t=' + Date.now();
            hvsrPlot.style.display = 'block';
            graphPlaceholder.style.display = 'none';
        }

        outputText.innerHTML = `
            <strong>Frekuensi Dominan (f0):</strong> ${f0} Hz<br>
            <strong>Amplifikasi (A0):</strong> ${a0}<br>
            <strong>Indeks Kerentanan Seismik (Kg):</strong> ${kg}<br><br>
            <strong>Interpretasi:</strong><br>
            ${explanation.replace(/\n/g, '<br>')}
        `;

    } catch (err) {
        outputText.innerHTML = `<strong>Error:</strong> Could not connect to the server. Make sure the Flask backend is running.<br><small>${err.message}</small>`;
    } finally {
        runBtn.disabled = false;
        runBtn.querySelector('.btn-text').textContent = 'Olah Data';
    }
});

// ======== RESET BUTTON ========
resetBtn.addEventListener('click', () => {
    // Clear inputs
    latInput.value = '';
    lngInput.value = '';
    if (keteranganInput) keteranganInput.value = '';

    // Clear direct mode file
    fileInput.value = '';
    fileNameDisplay.textContent = 'File mikrotremor belum ada';

    // Clear convert mode files
    binInput.value = '';
    jsonInput.value = '';
    binNameDisplay.textContent = 'File .bin belum ada';
    jsonNameDisplay.textContent = 'File .json belum ada';

    // Clear output
    outputText.innerHTML = '';

    // Clear HVSR graph
    hvsrPlot.src = '';
    hvsrPlot.style.display = 'none';
    graphPlaceholder.style.display = 'flex';

    // Remove marker
    if (currentMarker) {
        map.removeLayer(currentMarker);
        currentMarker = null;
    }

    // Reset map view
    map.setView([defaultView.lat, defaultView.lng], defaultView.zoom);

    // Reset to direct mode
    setMode('direct');
});

// ======== TUTORIAL MODAL ========
const tutorialBtn = document.getElementById('tutorial-btn');
const tutorialModal = document.getElementById('tutorial-modal');
const tutorialCloseBtn = document.getElementById('tutorial-close-btn');
const tutorialBackdrop = document.getElementById('tutorial-backdrop');

function openTutorial() {
    tutorialModal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeTutorial() {
    tutorialModal.classList.remove('active');
    document.body.style.overflow = '';
}

if (tutorialBtn) {
    tutorialBtn.addEventListener('click', openTutorial);
}
if (tutorialCloseBtn) {
    tutorialCloseBtn.addEventListener('click', closeTutorial);
}
if (tutorialBackdrop) {
    tutorialBackdrop.addEventListener('click', closeTutorial);
}

