// Default Partition Categories
const defaultPartitions = [
    { id: 'increment',  name: 'Increment Data',    icon: 'fa-chart-line' },
    { id: 'experience', name: 'Experience Data',   icon: 'fa-award' },
    { id: 'relieving',  name: 'Relieving Data',    icon: 'fa-door-open' },
    { id: 'offer',      name: 'Offer Letter Data', icon: 'fa-briefcase' }
];

// App State and DB
let db = localforage.createInstance({ name: "HRAutoMerge" });
let state = {
    activePartition: 'increment',
    partitions: [ ...defaultPartitions ],
    datasets: {},     // { partId: { employees: [], columnKeys: [] } }
    employees: [],    // points to active dataset employees
    columnKeys: [],   // points to active dataset columnKeys
    templates: [],    // store { id, name, type, binary, placeholders }
    history: []
};

// DOM Elements
const views = document.querySelectorAll('.view-section');
const navItems = document.querySelectorAll('.nav-item');
const uploadModal = document.getElementById('upload-modal');
const closeBtn = document.querySelector('.close-modal');
const fileInput = document.getElementById('file-input');
const uploadErrors = document.getElementById('upload-errors');
let currentUploadContext = null; // 'excel' or 'template'

// Initialize App
async function initApp() {
    await loadData();
    checkLoginSession();
    setupNavigation();
    setupModals();
    setupPartitionModal();
    setupEmployeeModal();
    updateDashboard();
    renderEmployees();
    renderTemplates();
    renderMergeView();
    renderHistory();
}

window.handleLogin = function(e) {
    if (e) e.preventDefault();
    const userInput = document.getElementById('login-username');
    const passInput = document.getElementById('login-password');
    const user = userInput ? userInput.value.trim() : '';
    const pass = passInput ? passInput.value.trim() : '';
    const errEl = document.getElementById('login-error');

    const validUser = 'admin';
    const validPass = 'HR@Merge#2026!';

    if (user.toLowerCase() === validUser && pass === validPass) {
        sessionStorage.setItem('hr_logged_in', 'true');
        sessionStorage.setItem('hr_user_name', 'admin');
        
        const loginScreen = document.getElementById('login-screen');
        if (loginScreen) loginScreen.style.display = 'none';
        if (errEl) errEl.style.display = 'none';
        
        const avatarEl = document.querySelector('.user-profile .avatar');
        const nameEl = document.querySelector('.user-profile span');
        if (avatarEl) avatarEl.textContent = 'A';
        if (nameEl) nameEl.innerHTML = `admin <i class="fa-solid fa-chevron-down" style="font-size:0.75rem; margin-left:4px;"></i>`;
    } else {
        if (errEl) {
            errEl.textContent = 'Invalid username or password. Only "admin" username is allowed.';
            errEl.style.display = 'block';
        }
    }
};

window.handleLogout = function(e) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }
    sessionStorage.removeItem('hr_logged_in');
    
    // Clear inputs completely on logout for privacy & security
    const userInput = document.getElementById('login-username');
    const passInput = document.getElementById('login-password');
    const errEl = document.getElementById('login-error');

    if (userInput) userInput.value = '';
    if (passInput) {
        passInput.value = '';
        passInput.type = 'password';
    }
    if (errEl) errEl.style.display = 'none';

    const eyeIcon = document.querySelector('.toggle-pass-icon');
    if (eyeIcon) {
        eyeIcon.className = 'fa-solid fa-eye toggle-pass-icon';
    }

    const loginScreen = document.getElementById('login-screen');
    if (loginScreen) loginScreen.style.display = 'flex';
    const dropdown = document.getElementById('user-dropdown');
    if (dropdown) dropdown.classList.remove('active');
};

window.showLockScreen = function(e) {
    window.handleLogout(e);
};

window.toggleUserDropdown = function(e) {
    if (e) e.stopPropagation();
    const dropdown = document.getElementById('user-dropdown');
    if (dropdown) dropdown.classList.toggle('active');
};

window.togglePasswordVisibility = function() {
    const passInput = document.getElementById('login-password');
    const eyeIcon = document.querySelector('.toggle-pass-icon');
    if (passInput) {
        if (passInput.type === 'password') {
            passInput.type = 'text';
            if (eyeIcon) eyeIcon.className = 'fa-solid fa-eye-slash toggle-pass-icon';
        } else {
            passInput.type = 'password';
            if (eyeIcon) eyeIcon.className = 'fa-solid fa-eye toggle-pass-icon';
        }
    }
};

function checkLoginSession() {
    const isLoggedIn = sessionStorage.getItem('hr_logged_in');
    const loginScreen = document.getElementById('login-screen');
    if (!isLoggedIn) {
        const userInput = document.getElementById('login-username');
        const passInput = document.getElementById('login-password');
        if (userInput) userInput.value = '';
        if (passInput) {
            passInput.value = '';
            passInput.type = 'password';
        }
        const eyeIcon = document.querySelector('.toggle-pass-icon');
        if (eyeIcon) {
            eyeIcon.className = 'fa-solid fa-eye toggle-pass-icon';
        }
        if (loginScreen) loginScreen.style.display = 'flex';
    } else {
        if (loginScreen) loginScreen.style.display = 'none';
    }
}

async function loadData() {
    state.partitions = await db.getItem('partitions') || defaultPartitions;
    state.activePartition = await db.getItem('activePartition') || 'increment';
    let savedDatasets = await db.getItem('datasets');

    if (!savedDatasets) {
        savedDatasets = {};
        state.partitions.forEach(p => {
            savedDatasets[p.id] = { employees: [], columnKeys: [] };
        });
        // Migrate legacy single dataset into 'increment' partition
        const legacyEmps = await db.getItem('employees') || [];
        const legacyCols = await db.getItem('columnKeys') || [];
        if (legacyEmps.length > 0) {
            savedDatasets.increment = { employees: legacyEmps, columnKeys: legacyCols };
        }
        await db.setItem('datasets', savedDatasets);
    }

    // Ensure all defined partitions have dataset entry
    state.partitions.forEach(p => {
        if (!savedDatasets[p.id]) savedDatasets[p.id] = { employees: [], columnKeys: [] };
    });

    state.datasets = savedDatasets;
    syncActivePartition();
    state.templates = await db.getItem('templates') || [];
    state.history   = await db.getItem('history')   || [];
}

function syncActivePartition() {
    if (!state.datasets[state.activePartition]) {
        state.datasets[state.activePartition] = { employees: [], columnKeys: [] };
    }
    const current = state.datasets[state.activePartition];
    state.employees  = current.employees || [];
    state.columnKeys = current.columnKeys || [];
}

async function setActivePartition(partId) {
    state.activePartition = partId;
    syncActivePartition();
    await db.setItem('activePartition', partId);
    renderPartitionTabs();
    renderEmployees();
}

async function saveData(key, data) {
    await db.setItem(key, data);
    state[key] = data;
}

window.toggleMobileSidebar = function() {
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar) sidebar.classList.toggle('mobile-open');
    if (overlay) overlay.classList.toggle('active');
};

// Navigation Logic
function setupNavigation() {
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = item.getAttribute('data-target');
            
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');
            
            views.forEach(v => v.classList.remove('active'));
            document.getElementById(targetId).classList.add('active');

            if(targetId === 'dashboard-view') updateDashboard();
            if(targetId === 'employees-view') renderEmployees();
            if(targetId === 'templates-view') renderTemplates();
            if(targetId === 'mail-merge-view') renderMergeView();
            if(targetId === 'history-view') renderHistory();

            // Auto-close mobile drawer menu after selection
            const sidebar = document.querySelector('.sidebar');
            const overlay = document.getElementById('sidebar-overlay');
            if (sidebar) sidebar.classList.remove('mobile-open');
            if (overlay) overlay.classList.remove('active');
        });
    });
}

window.closeAllModals = function() {
    document.querySelectorAll('.modal').forEach(m => {
        m.style.display = 'none';
    });
    currentUploadContext = null;
    currentEditRowIdx = -1;
};

function closeModal() {
    closeAllModals();
}

// Modal Logic
function setupModals() {
    document.getElementById('btn-import-excel').addEventListener('click', () => openUploadModal('excel'));
    document.getElementById('btn-upload-template').addEventListener('click', () => openUploadModal('template'));
    
    // Global click outside modal backdrop closes open modal
    window.addEventListener('click', (e) => {
        if (e.target.classList && e.target.classList.contains('modal')) {
            closeAllModals();
        }
    });

    // ESC key closes any open modal
    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeAllModals();
        }
    });

    fileInput.addEventListener('change', handleFileUpload);

    // Setup full Drag & Drop for upload modal
    const dropArea = document.querySelector('.file-drop-area');
    if (dropArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, e => {
                e.preventDefault();
                e.stopPropagation();
            }, false);
        });

        ['dragenter', 'dragover'].forEach(() => {
            dropArea.style.borderColor = 'var(--primary-color)';
            dropArea.style.backgroundColor = '#eff6ff';
        });

        ['dragleave', 'drop'].forEach(() => {
            dropArea.style.borderColor = 'var(--border-color)';
            dropArea.style.backgroundColor = 'transparent';
        });

        dropArea.addEventListener('drop', e => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files && files.length > 0) {
                processUploadedFile(files[0]);
            }
        });
    }

    // Export button handler
    const btnExport = document.getElementById('btn-export-excel');
    if (btnExport) {
        btnExport.addEventListener('click', exportActivePartitionSheet);
    }
}

function populateUploadTargetPartitions() {
    const select = document.getElementById('upload-target-partition');
    if (!select) return;
    select.innerHTML = '';
    state.partitions.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.name + (p.id === state.activePartition ? ' (Active)' : '');
        if (p.id === state.activePartition) opt.selected = true;
        select.appendChild(opt);
    });
}

function openUploadModal(context) {
    currentUploadContext = context;
    document.getElementById('upload-modal-title').innerText = context === 'excel'
        ? 'Import Employee Data (.xlsx, .ods, .csv)'
        : 'Upload Document Template (.docx, .odt)';
    
    const targetGrp = document.getElementById('target-partition-group');
    if (targetGrp) {
        if (context === 'excel') {
            populateUploadTargetPartitions();
            targetGrp.style.display = 'block';
        } else {
            targetGrp.style.display = 'none';
        }
    }

    // Allow .odt, .docx, .doc, .ott and all file types in Windows Browse dialog
    fileInput.accept = context === 'excel'
        ? '.xlsx, .xls, .ods, .csv, .tsv, .fods, .xlsm, .xlsb, *'
        : '.docx, .odt, .doc, .ott, .rtf, *';
    fileInput.value = '';
    uploadErrors.style.display = 'none';
    uploadModal.style.display = 'flex';
}

function closeModal() {
    uploadModal.style.display = 'none';
    currentUploadContext = null;
}

// File Upload Handling
function handleFileUpload(e) {
    const file = e.target.files[0];
    if (file) processUploadedFile(file);
}

function processUploadedFile(file) {
    if (currentUploadContext === 'excel') {
        processExcel(file);
    } else if (currentUploadContext === 'template') {
        processTemplate(file);
    }
}

function processExcel(file) {
    const reader = new FileReader();
    reader.onload = async function(e) {
        try {
            const data = new Uint8Array(e.target.result);

            // XLSX.read handles .xlsx, .xls, .ods (LibreOffice Calc), .csv, .fods, etc.
            const workbook = XLSX.read(data, { type: 'array', cellText: true, cellDates: true });
            if (!workbook || !workbook.SheetNames || workbook.SheetNames.length === 0) {
                throw new Error('No sheets found in this file.');
            }

            const firstSheetName = workbook.SheetNames[0];
            const worksheet = workbook.Sheets[firstSheetName];

            const rawRows = XLSX.utils.sheet_to_json(worksheet, { raw: false, defval: '', header: 1 });

            if (!rawRows || rawRows.length === 0) {
                throw new Error('The selected sheet appears to be empty.');
            }

            // Smart Header Row Detection: Find the first non-empty row to use as column headers
            let headerRowIdx = -1;
            for (let r = 0; r < rawRows.length; r++) {
                if (Array.isArray(rawRows[r]) && rawRows[r].some(cell => String(cell).trim() !== '')) {
                    headerRowIdx = r;
                    break;
                }
            }

            if (headerRowIdx === -1) {
                throw new Error('Could not find any data rows in this spreadsheet.');
            }

            const headers = rawRows[headerRowIdx].map(h => String(h).trim()).filter(h => h !== '');
            if (headers.length === 0) {
                throw new Error('Could not detect any column headers in row ' + (headerRowIdx + 1) + '.');
            }

            // Extract records after header row
            const records = [];
            for (let i = headerRowIdx + 1; i < rawRows.length; i++) {
                const rawRow = rawRows[i];
                if (!Array.isArray(rawRow)) continue;
                const record = {};
                let hasValue = false;
                headers.forEach((h, col) => {
                    let val = (rawRow[col] !== undefined && rawRow[col] !== null) ? String(rawRow[col]).trim() : '';
                    // Convert Excel serial date numbers (e.g. 44697 -> 16-May-2022)
                    val = formatPossibleDate(val, h);
                    record[h] = val;
                    if (val !== '') hasValue = true;
                });
                if (hasValue) records.push(record);
            }

            if (records.length === 0) {
                throw new Error('No employee data rows found after column header row.');
            }

            // Determine target partition
            const targetSelect = document.getElementById('upload-target-partition');
            const targetPartId = (targetSelect && targetSelect.value) ? targetSelect.value : state.activePartition;

            // Save dataset into specified partition
            state.datasets[targetPartId] = { employees: records, columnKeys: headers };
            await db.setItem('datasets', state.datasets);

            // Also update legacy items for backward compatibility
            await db.setItem('employees', records);
            await db.setItem('columnKeys', headers);

            await setActivePartition(targetPartId);
            updateDashboard();
            closeModal();

            const activePart = state.partitions.find(p => p.id === targetPartId);
            const partName = activePart ? activePart.name : targetPartId;
            alert(`✅ Successfully imported ${records.length} row(s) into Partition "${partName}" from "${firstSheetName}"`);

        } catch (error) {
            console.error('Spreadsheet Import Error:', error);
            uploadErrors.innerHTML = `<strong>Error reading spreadsheet:</strong> ${error.message}<br><br><small style="color:#64748b">Supported formats: LibreOffice Calc (.ods), Excel (.xlsx, .xls), CSV (.csv)</small>`;
            uploadErrors.style.display = 'block';
        }
    };
    reader.onerror = function(err) {
        uploadErrors.innerHTML = `<strong>FileReader Error:</strong> ${err.message || 'Could not read file.'}`;
        uploadErrors.style.display = 'block';
    };
    reader.readAsArrayBuffer(file);
}

function exportActivePartitionSheet() {
    if (state.employees.length === 0) return alert('No data in current partition to export.');
    const activePart = state.partitions.find(p => p.id === state.activePartition);
    const partName = activePart ? activePart.name : 'Employees';
    const ws = XLSX.utils.json_to_sheet(state.employees);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, partName);
    XLSX.writeFile(wb, `${partName.replace(/\s+/g, '_')}_Export.xlsx`);
}

// ─────────────────────────────────────────────────────────────────
// UNIVERSAL TEMPLATE XML REPAIR — LibreOffice Writer (.odt) & Word (.docx)
// ─────────────────────────────────────────────────────────────────

function isDocumentXmlPart(n) {
    return (n.startsWith('word/') || n === 'content.xml' || n.endsWith('/content.xml') || n === 'styles.xml') && n.endsWith('.xml') && !n.includes('/_rels/');
}

function fixDocxSplitTags(zip) {
    const xmlParts = Object.keys(zip.files).filter(isDocumentXmlPart);

    xmlParts.forEach(partName => {
        let xml = zip.files[partName].asText();

        // ── Pass A: merge split delimiters that span across XML tags ──
        xml = xml.replace(/\{(<[^>]+>)+\{/g, '{{');
        xml = xml.replace(/\}(<[^>]+>)+\}/g, '}}');

        // ── Pass B: merge placeholder content split across run boundaries (<w:t> or <text:span>) ──
        let changed = true;
        while (changed) {
            const next = xml.replace(
                /\{\{([^{}]*?)<\/(?:w:t|text:span)>((?:(?!<\/(?:w:p|text:p>))[\s\S])*?)<(?:w:t|text:span)(?:[^>]*?)>([^{}]*?)\}\}/g,
                (_, a, _mid, b) => '{{' + a + b + '}}'
            );
            changed = next !== xml;
            xml = next;
        }

        // ── Pass C: strip stray XML tags still inside {{ … }} ──
        xml = xml.replace(/\{\{((?:[^{}]|<[^>]*>)*?)\}\}/g, (_, inner) =>
            '{{' + inner.replace(/<[^>]*>/g, '').trim() + '}}'
        );

        zip.file(partName, xml);
    });

    return zip;
}

/**
 * Extract all {{placeholder}} names directly from raw XML text
 * Works for both LibreOffice Writer (.odt -> content.xml) and Word (.docx -> word/*.xml)
 */
function extractPlaceholdersFromXml(zip) {
    const names = new Set();
    Object.keys(zip.files)
        .filter(isDocumentXmlPart)
        .forEach(n => {
            const text = zip.files[n].asText();
            for (const m of text.matchAll(/\{\{\s*([^{}\s][^{}]*?)\s*\}\}/g)) {
                names.add(m[1].trim());
            }
        });
    return [...names];
}

function processUploadedFile(file) {
    if (currentUploadContext === 'excel') {
        processExcel(file);
    } else if (currentUploadContext === 'template') {
        processTemplate(file);
    }
}

function processTemplate(file, replaceTargetId = null) {
    const reader = new FileReader();
    reader.onload = async function(e) {
        try {
            const arrayBuffer = e.target.result;
            const zip = fixDocxSplitTags(new PizZip(arrayBuffer));
            const placeholders = extractPlaceholdersFromXml(zip);
            const fixedBinary = zip.generate({ type: 'arraybuffer' });

            const uploadDate = new Date().toLocaleDateString('en-US');
            const cleanName = file.name.replace(/\.(docx|odt|doc|ott|rtf)$/i, '');
            
            let category = 'Offer Letter';
            if (/experience|reliev|releav/i.test(file.name)) category = 'Experience Letter';
            else if (/increment|appraisal|salary/i.test(file.name)) category = 'Increment Letter';
            else if (/joining|appointment/i.test(file.name)) category = 'Joining Letter';

            if (replaceTargetId) {
                const idx = state.templates.findIndex(t => t.id === replaceTargetId);
                if (idx !== -1) {
                    state.templates[idx].name = cleanName;
                    state.templates[idx].filename = file.name;
                    state.templates[idx].type = file.name.endsWith('.odt') ? 'odt' : 'docx';
                    state.templates[idx].category = category;
                    state.templates[idx].uploadDate = uploadDate;
                    state.templates[idx].binary = fixedBinary;
                    state.templates[idx].placeholders = placeholders;
                }
                await saveData('templates', state.templates);
                alert(`✅ Template replaced with "${file.name}"!`);
            } else {
                const newTemplate = {
                    id: 'tmpl_' + Date.now(),
                    name: cleanName,
                    filename: file.name,
                    type: file.name.endsWith('.odt') ? 'odt' : 'docx',
                    category: category,
                    uploadDate: uploadDate,
                    binary: fixedBinary,
                    placeholders: placeholders,
                    dateAdded: new Date().toISOString()
                };
                const templates = [...state.templates, newTemplate];
                await saveData('templates', templates);
                alert(`✅ Template "${file.name}" uploaded! (${placeholders.length} placeholders found)`);
            }

            renderTemplates();
            renderMergeView();
            updateDashboard();
            closeModal();

        } catch (error) {
            console.error('Template Upload Error:', error);
            if (uploadErrors) {
                uploadErrors.innerHTML = `<strong>Template Error:</strong> ${error.message}`;
                uploadErrors.style.display = 'block';
            } else {
                alert('Error processing template: ' + error.message);
            }
        }
    };
    reader.readAsArrayBuffer(file);
}

// Render Data
function updateDashboard() {
    document.getElementById('stat-employees').innerText = state.employees.length;
    document.getElementById('stat-templates').innerText = state.templates.length;
    document.getElementById('stat-generated').innerText = state.history.length;
}

function renderPartitionTabs() {
    const container = document.getElementById('partition-tabs-bar');
    if (!container) return;
    container.innerHTML = '';

    state.partitions.forEach(p => {
        const dataset = state.datasets[p.id] || { employees: [] };
        const count = dataset.employees.length;

        const tab = document.createElement('button');
        tab.className = `partition-tab${p.id === state.activePartition ? ' active' : ''}`;
        tab.innerHTML = `
            <i class="fa-solid ${p.icon || 'fa-folder'}"></i>
            <span>${p.name}</span>
            <span class="part-badge">${count}</span>
        `;
        tab.addEventListener('click', () => setActivePartition(p.id));
        container.appendChild(tab);
    });

    const addTab = document.createElement('button');
    addTab.className = 'partition-tab partition-tab-add';
    addTab.innerHTML = `<i class="fa-solid fa-plus"></i> <span>New Partition</span>`;
    addTab.addEventListener('click', () => {
        document.getElementById('new-part-name').value = '';
        document.getElementById('partition-modal').style.display = 'flex';
    });
    container.appendChild(addTab);
}

function renderWizPartitionTabs() {
    const container = document.getElementById('wiz-partition-tabs-bar');
    if (!container) return;
    container.innerHTML = '';

    state.partitions.forEach(p => {
        const dataset = state.datasets[p.id] || { employees: [] };
        const count = dataset.employees.length;

        const tab = document.createElement('button');
        tab.className = `partition-tab${p.id === state.activePartition ? ' active' : ''}`;
        tab.innerHTML = `
            <i class="fa-solid ${p.icon || 'fa-folder'}"></i>
            <span>${p.name}</span>
            <span class="part-badge">${count}</span>
        `;
        tab.addEventListener('click', async () => {
            await setActivePartition(p.id);
            wizardState.selectedIndexes = [];
            renderWizPartitionTabs();
            populateStep1();
        });
        container.appendChild(tab);
    });
}

function renderEmployees() {
    renderPartitionTabs();

    const table  = document.getElementById('employees-table');
    const thead  = table.querySelector('thead');
    const tbody  = table.querySelector('tbody');
    thead.innerHTML = '';
    tbody.innerHTML = '';

    const cols = state.columnKeys.length > 0
        ? state.columnKeys
        : (state.employees.length > 0 ? Object.keys(state.employees[0]) : []);

    const activePart = state.partitions.find(p => p.id === state.activePartition);
    const partName = activePart ? activePart.name : 'Active Partition';

    if (state.employees.length === 0 || cols.length === 0) {
        thead.innerHTML = '<tr><th>Data</th><th>Actions</th></tr>';
        tbody.innerHTML = `<tr><td colspan="2" style="text-align:center;padding:2.5rem;color:var(--text-muted)">
            No data in <strong>${partName}</strong> partition.<br>
            Click <strong>Import Excel</strong> to add records to this partition.
        </td></tr>`;
        updateEmpTableBulkButtons();
        return;
    }

    // Build dynamic header with Select All checkbox
    const headerRow = document.createElement('tr');
    
    const thSelect = document.createElement('th');
    thSelect.style.width = '40px';
    thSelect.style.textAlign = 'center';
    thSelect.innerHTML = `<input type="checkbox" id="emp-table-select-all" onclick="toggleEmpTableSelectAll(this)" title="Select All Records">`;
    headerRow.appendChild(thSelect);

    cols.forEach(col => {
        const th = document.createElement('th');
        th.textContent = col;
        headerRow.appendChild(th);
    });
    const thAct = document.createElement('th');
    thAct.textContent = 'Actions';
    headerRow.appendChild(thAct);
    thead.appendChild(headerRow);

    // Build dynamic rows
    state.employees.forEach((emp, rowIdx) => {
        const tr = document.createElement('tr');
        
        const tdCb = document.createElement('td');
        tdCb.style.textAlign = 'center';
        tdCb.innerHTML = `<input type="checkbox" class="emp-row-cb" data-idx="${rowIdx}" onclick="updateEmpTableBulkButtons()">`;
        tr.appendChild(tdCb);

        cols.forEach(col => {
            const td = document.createElement('td');
            const rawVal = emp[col];
            const formattedVal = formatPossibleDate(rawVal, col);
            td.textContent = (formattedVal !== undefined && formattedVal !== '') ? formattedVal : '—';
            tr.appendChild(td);
        });
        const tdAct = document.createElement('td');
        tdAct.style.whiteSpace = 'nowrap';
        tdAct.innerHTML = `
            <i class="fa-solid fa-pen-to-square text-primary" style="cursor:pointer; margin-right:12px; font-size:1.05rem;" onclick="editEmployee(${rowIdx})" title="Edit record"></i>
            <i class="fa-solid fa-trash text-danger" style="cursor:pointer; font-size:1.05rem;" onclick="deleteEmployee(${rowIdx})" title="Delete record"></i>
        `;
        tr.appendChild(tdAct);
        tbody.appendChild(tr);
    });

    updateEmpTableBulkButtons();
}

window.toggleEmpTableSelectAll = function(masterCb) {
    const rowCbs = document.querySelectorAll('.emp-row-cb');
    rowCbs.forEach(cb => cb.checked = masterCb.checked);
    updateEmpTableBulkButtons();
};

window.updateEmpTableBulkButtons = function() {
    const selectedCbs = document.querySelectorAll('.emp-row-cb:checked');
    const totalCbs = document.querySelectorAll('.emp-row-cb');
    const masterCb = document.getElementById('emp-table-select-all');
    if (masterCb && totalCbs.length > 0) {
        masterCb.checked = selectedCbs.length === totalCbs.length;
    }
    const btnDeleteSelected = document.getElementById('btn-delete-selected-emps');
    const countSpan = document.getElementById('selected-emp-count');
    if (btnDeleteSelected && countSpan) {
        if (selectedCbs.length > 0) {
            countSpan.textContent = selectedCbs.length;
            btnDeleteSelected.style.display = 'inline-flex';
        } else {
            btnDeleteSelected.style.display = 'none';
        }
    }
};

window.deleteSelectedEmployees = async function() {
    const selectedCbs = Array.from(document.querySelectorAll('.emp-row-cb:checked'));
    if (selectedCbs.length === 0) return alert('Please select at least one record to delete.');
    
    const selectedIndexes = selectedCbs.map(cb => parseInt(cb.getAttribute('data-idx'))).sort((a, b) => b - a);
    if (confirm(`Are you sure you want to delete ${selectedIndexes.length} selected record(s)?`)) {
        let emps = [...state.employees];
        selectedIndexes.forEach(idx => {
            emps.splice(idx, 1);
        });
        state.employees = emps;
        state.datasets[state.activePartition].employees = emps;
        await db.setItem('datasets', state.datasets);
        await db.setItem('employees', emps);
        renderEmployees();
        updateDashboard();
        alert(`✅ Successfully deleted ${selectedIndexes.length} record(s).`);
    }
};

window.clearAllEmployeesInPartition = async function() {
    if (state.employees.length === 0) return alert('Active partition is already empty.');
    const activePart = state.partitions.find(p => p.id === state.activePartition);
    const partName = activePart ? activePart.name : 'Active Partition';
    
    if (confirm(`⚠️ Are you sure you want to DELETE ALL ${state.employees.length} record(s) in "${partName}"?`)) {
        state.employees = [];
        state.datasets[state.activePartition].employees = [];
        state.datasets[state.activePartition].columnKeys = [];
        state.columnKeys = [];
        await db.setItem('datasets', state.datasets);
        await db.setItem('employees', []);
        await db.setItem('columnKeys', []);
        renderEmployees();
        updateDashboard();
        alert(`✅ All data in "${partName}" has been deleted.`);
    }
};

// Edit & Add Employee Modal Functions
let currentEditRowIdx = -1;

function setupEmployeeModal() {
    const btnAddEmp = document.getElementById('btn-add-employee');
    if (btnAddEmp) {
        btnAddEmp.addEventListener('click', openAddEmployeeModal);
    }
}

window.saveEmployeeRecord = async function() {
    try {
        const inputs = document.querySelectorAll('#emp-form-fields input.emp-input-field');
        if (!inputs || inputs.length === 0) {
            alert('No editable fields found.');
            return;
        }

        const updatedEmp = {};
        inputs.forEach(input => {
            const col = input.getAttribute('data-col');
            if (col) {
                updatedEmp[col] = input.value.trim();
            }
        });

        if (!state.datasets[state.activePartition]) {
            state.datasets[state.activePartition] = { employees: [], columnKeys: [] };
        }

        if (currentEditRowIdx >= 0) {
            // Update existing record
            state.employees[currentEditRowIdx] = updatedEmp;
            if (!state.datasets[state.activePartition].employees) {
                state.datasets[state.activePartition].employees = [];
            }
            state.datasets[state.activePartition].employees[currentEditRowIdx] = updatedEmp;
        } else {
            // Add new record
            state.employees.push(updatedEmp);
            if (!state.datasets[state.activePartition].employees) {
                state.datasets[state.activePartition].employees = [];
            }
            state.datasets[state.activePartition].employees.push(updatedEmp);
        }

        // Sync dataset column keys if not set
        if (!state.datasets[state.activePartition].columnKeys || state.datasets[state.activePartition].columnKeys.length === 0) {
            const newCols = Object.keys(updatedEmp);
            state.datasets[state.activePartition].columnKeys = newCols;
            state.columnKeys = newCols;
        }

        // Persist changes to IndexedDB
        await db.setItem('datasets', state.datasets);
        await db.setItem('employees', state.employees);
        await db.setItem('columnKeys', state.columnKeys);

        // Close modal and refresh UI
        closeAllModals();
        renderEmployees();
        updateDashboard();

        // Invalidate wizard cache
        wizardState.previewBlobs = [];

    } catch (err) {
        console.error('[SaveRecord Error]:', err);
        alert('Could not save record: ' + err.message);
    }
};

window.editEmployee = function(rowIdx) {
    const emp = state.employees[rowIdx];
    if (!emp) return;

    currentEditRowIdx = rowIdx;
    const titleEl = document.getElementById('emp-modal-title');
    if (titleEl) titleEl.innerHTML = `<i class="fa-solid fa-pen-to-square"></i> Edit Record (Row ${rowIdx + 1})`;
    
    const saveBtn = document.getElementById('btn-save-employee');
    if (saveBtn) saveBtn.innerHTML = `<i class="fa-solid fa-check"></i> Save Changes`;

    populateEmployeeForm(emp);
    const empModal = document.getElementById('employee-modal');
    if (empModal) empModal.style.display = 'flex';
};

window.openAddEmployeeModal = function() {
    const cols = getAvailableCols();
    if (cols.length === 0) {
        return alert('Please import an Excel spreadsheet first or select a partition with columns.');
    }

    currentEditRowIdx = -1;
    const titleEl = document.getElementById('emp-modal-title');
    if (titleEl) titleEl.innerHTML = `<i class="fa-solid fa-plus"></i> Add New Record`;

    const saveBtn = document.getElementById('btn-save-employee');
    if (saveBtn) saveBtn.innerHTML = `<i class="fa-solid fa-plus"></i> Add Record`;

    const emptyEmp = {};
    cols.forEach(c => emptyEmp[c] = '');

    populateEmployeeForm(emptyEmp);
    const empModal = document.getElementById('employee-modal');
    if (empModal) empModal.style.display = 'flex';
};

function populateEmployeeForm(empObj) {
    const fieldsContainer = document.getElementById('emp-form-fields');
    if (!fieldsContainer) return;
    fieldsContainer.innerHTML = '';

    const cols = getAvailableCols();
    cols.forEach(col => {
        const group = document.createElement('div');
        group.className = 'form-group';
        group.style.marginBottom = '12px';

        const isDateCol = /date|dob|doj|joining|reliev|resig|offer|issue|birth|day/i.test(col);
        const rawVal = empObj[col] !== undefined ? String(empObj[col]) : '';

        group.innerHTML = `
            <label style="font-weight:600; font-size:0.85rem; margin-bottom:4px; display:block;">${col}:</label>
            <input type="text" class="form-control emp-input-field" data-col="${col}" value="${rawVal.replace(/"/g, '&quot;')}" placeholder="Enter ${col}">
            ${isDateCol ? '<small style="color:var(--text-muted); font-size:0.75rem;">Format example: 16-May-2022</small>' : ''}
        `;
        fieldsContainer.appendChild(group);
    });
}

// Delete by row index from current partition
window.deleteEmployee = async function(rowIdx) {
    if (confirm('Delete this record from active partition?')) {
        const newEmps = state.employees.filter((_, i) => i !== rowIdx);
        state.employees = newEmps;
        state.datasets[state.activePartition].employees = newEmps;
        await db.setItem('datasets', state.datasets);
        await db.setItem('employees', newEmps);
        renderEmployees();
        updateDashboard();
    }
};

function renderTemplates() {
    const container = document.getElementById('templates-container');
    if (!container) return;
    container.innerHTML = '';
    
    if (!state.templates || state.templates.length === 0) {
        container.innerHTML = `
            <div style="grid-column: 1 / -1; text-align:center; padding: 40px 20px; background: white; border: 1.5px dashed var(--border-color); border-radius: 16px;">
                <i class="fa-regular fa-file-word" style="font-size: 3rem; color: var(--text-muted); opacity: 0.5; margin-bottom: 12px;"></i>
                <h3 style="font-size: 1.1rem; color: var(--text-main); margin-bottom: 6px;">No Templates Uploaded Yet</h3>
                <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 16px;">Upload a Word (.docx) or LibreOffice (.odt) template file to begin generating documents.</p>
                <button class="btn btn-primary" onclick="openUploadModal('template')"><i class="fa-solid fa-upload"></i> Upload Template</button>
            </div>
        `;
        return;
    }

    state.templates.forEach(t => {
        const placeholdersCount = t.placeholders ? t.placeholders.length : 0;
        const uploadDateStr = t.uploadDate || new Date().toLocaleDateString('en-US');
        const categoryStr = t.category || 'Offer Letter';
        const filenameStr = t.filename || `${t.name}.${t.type || 'docx'}`;

        const card = document.createElement('div');
        card.className = 'tpl-card-exact';
        card.innerHTML = `
            <div class="tpl-header-row">
                <div class="tpl-icon-box">
                    <i class="fa-regular fa-file-lines"></i>
                </div>
                <div class="tpl-header-info">
                    <div class="tpl-title" title="${t.name}">${t.name}</div>
                    <div class="tpl-subtitle">${categoryStr} · uploaded ${uploadDateStr}</div>
                </div>
            </div>

            <div class="tpl-pills-row">
                <span class="tpl-pill tpl-pill-blue">${placeholdersCount} placeholders</span>
                <span class="tpl-pill tpl-pill-gray">${filenameStr}</span>
            </div>

            <div class="tpl-buttons-group">
                <div class="tpl-btn-row">
                    <button type="button" class="tpl-action-btn" onclick="previewTemplate('${t.id}')">
                        <i class="fa-regular fa-eye"></i> Preview
                    </button>
                    <button type="button" class="tpl-action-btn" onclick="showPlaceholders('${t.id}')">
                        <i class="fa-solid fa-tag"></i> Fields
                    </button>
                </div>
                <div class="tpl-btn-row">
                    <button type="button" class="tpl-action-btn" onclick="downloadTemplate('${t.id}')">
                        <i class="fa-solid fa-download"></i> Download
                    </button>
                    <button type="button" class="tpl-action-btn" onclick="replaceTemplate('${t.id}')">
                        Replace
                    </button>
                    <button type="button" class="tpl-action-btn tpl-btn-danger" onclick="deleteTemplate('${t.id}')" title="Delete template">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

window.deleteTemplate = async function(id) {
    if (confirm('Delete this template?')) {
        const newTmps = state.templates.filter(t => t.id !== id);
        await saveData('templates', newTmps);
        renderTemplates();
        renderMergeView();
        updateDashboard();
    }
};

window.replaceTemplate = function(id) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.docx, .odt, .doc, .ott, .rtf, *';
    input.onchange = e => {
        const file = e.target.files[0];
        if (file) {
            processTemplate(file, id);
        }
    };
    input.click();
};

window.downloadTemplate = function(id) {
    const t = state.templates.find(x => x.id === id);
    if (!t || !t.binary) return alert('Template file binary data not available.');
    
    const isOdt = t.type === 'odt' || (t.filename && t.filename.endsWith('.odt'));
    const mime = isOdt ? 'application/vnd.oasis.opendocument.text' : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
    const filename = t.filename || `${t.name}.${isOdt ? 'odt' : 'docx'}`;
    
    const blob = new Blob([t.binary], { type: mime });
    saveAs(blob, filename);
};

window.previewTemplate = async function(id) {
    const t = state.templates.find(x => x.id === id);
    if (!t) return;
    
    const sampleEmp = state.employees[0] || {};
    const modal = document.getElementById('template-preview-modal');
    const docEl = document.getElementById('tpl-preview-doc');
    const titleEl = document.getElementById('tpl-preview-modal-title');
    
    if (titleEl) titleEl.innerHTML = `<i class="fa-regular fa-eye"></i> Preview: ${t.name}`;
    if (docEl) docEl.innerHTML = `<div class="preview-loading"><div class="preview-spinner"></div> Rendering preview...</div>`;
    if (modal) modal.style.display = 'flex';
    
    try {
        const blob = await generateDocumentBlob(t, sampleEmp);
        const arrayBuffer = await blob.arrayBuffer();
        const result = await mammoth.convertToHtml({ arrayBuffer });
        docEl.innerHTML = result.value || '<p style="color:#999; text-align:center">No document text content found.</p>';
    } catch (err) {
        docEl.innerHTML = `<p style="color:var(--danger)">Preview error: ${err.message}</p>`;
    }
};

window.showPlaceholders = function(id) {
    const t = state.templates.find(x => x.id === id);
    if (!t) return;

    const modal = document.getElementById('template-fields-modal');
    const listEl = document.getElementById('tpl-fields-list');
    const titleEl = document.getElementById('tpl-fields-modal-title');

    if (titleEl) titleEl.innerHTML = `<i class="fa-solid fa-tags"></i> Placeholders in ${t.name}`;
    if (listEl) {
        if (!t.placeholders || t.placeholders.length === 0) {
            listEl.innerHTML = '<span style="color:var(--text-muted); font-size:0.85rem">No {{placeholders}} detected.</span>';
        } else {
            listEl.innerHTML = t.placeholders.map(p =>
                `<span class="tpl-field-tag" style="margin:2px; font-size:0.8rem;">{{${p}}}</span>`
            ).join('');
        }
    }
    if (modal) modal.style.display = 'flex';
};

function renderHistory() {
    const tbody = document.querySelector('#history-table tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    
    if (!state.history || state.history.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:2.5rem; color:var(--text-muted)">No documents generated yet.</td></tr>';
        return;
    }

    const sorted = [...state.history].reverse();

    sorted.forEach((h, idx) => {
        const tr = document.createElement('tr');
        const formattedDate = h.date ? new Date(h.date).toLocaleString() : 'Just now';
        const realHistIndex = state.history.length - 1 - idx;
        tr.innerHTML = `
            <td>${formattedDate}</td>
            <td><strong>${h.employeeName || 'Unknown'}</strong></td>
            <td>${h.templateName || 'Template'}</td>
            <td><span style="color:var(--success); font-weight:600;"><i class="fa-solid fa-circle-check"></i> Generated</span></td>
            <td>
                <i class="fa-solid fa-trash text-danger" style="cursor:pointer" onclick="deleteHistoryEntry(${realHistIndex})" title="Delete log"></i>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

window.deleteHistoryEntry = async function(histIdx) {
    if (confirm('Delete this history record?')) {
        const newHist = state.history.filter((_, i) => i !== histIdx);
        await saveData('history', newHist);
        renderHistory();
        updateDashboard();
    }
};

window.clearAllHistory = async function() {
    if (confirm('Clear all document generation history?')) {
        await saveData('history', []);
        renderHistory();
        updateDashboard();
    }
};

// ══════════════════════════════════════════════════════════════════
// MAIL MERGE WIZARD
// ══════════════════════════════════════════════════════════════════

let wizardState = {
    step: 1,
    selectedIndexes: [],   // employee row indices
    templateId: null,
    fieldMapping: {},      // { templateTag: excelColumnKey }
    previewBlobs: [],      // ArrayBuffer per record
    previewIdx: 0,
};

// ── helpers ──────────────────────────────────────────────────────
function formatPossibleDate(val, colName = '') {
    if (val === null || val === undefined || val === '') return '';
    const strVal = String(val).trim();

    // 1. Is it an Excel Date Serial Number? (e.g., 44697 -> 16-May-2022, 46184 -> 12-Jun-2026)
    const num = Number(strVal);
    if (!isNaN(num) && num > 10000 && num < 100000) {
        const isSalaryCol = /salary|monthly|yearly|revised|old|ctc|amount|pay|fee|allowance|bonus|incentive|stipend|gross|basic|net/i.test(colName);
        const isDateCol = /date|dob|doj|joining|reliev|resig|offer|issue|birth|day|period|start|end|from|to/i.test(colName);
        if (!isSalaryCol && isDateCol) {
            try {
                if (window.XLSX && window.XLSX.SSF) {
                    const parsed = window.XLSX.SSF.parse_date_code(num);
                    if (parsed && parsed.y && parsed.m && parsed.d) {
                        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                        const dd = String(parsed.d).padStart(2, '0');
                        const mmm = months[parsed.m - 1];
                        const yyyy = parsed.y;
                        return `${dd}-${mmm}-${yyyy}`;
                    }
                }
            } catch (e) {
                console.warn('XLSX.SSF date parse error:', e);
            }
        }
    }

    // 2. Is it an ISO date string? (e.g. "2022-05-16T00:00:00.000Z" or "2022-05-16")
    if (typeof strVal === 'string' && /^\d{4}[-/]\d{1,2}[-/]\d{1,2}/.test(strVal)) {
        const d = new Date(strVal);
        if (!isNaN(d.getTime())) {
            const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            const dd = String(d.getDate()).padStart(2, '0');
            const mmm = months[d.getMonth()];
            const yyyy = d.getFullYear();
            return `${dd}-${mmm}-${yyyy}`;
        }
    }

    return strVal;
}

function getRecordLabel(emp) {
    if (!emp) return 'Record';
    const cols = Object.keys(emp);
    const nameCol =
        cols.find(c => /^(employee\s*name|emp\s*name|full\s*name|staff\s*name|candidate\s*name|name)$/i.test(c.trim())) ||
        cols.find(c => /name/i.test(c) && !/company|org|department|dept|project|file|sheet|template/i.test(c)) ||
        cols.find(c => /name/i.test(c));

    const val = nameCol ? emp[nameCol] : '';
    if (val) return val;

    const fallbackCol = cols.find(c => !/company|org/i.test(c) && emp[c]) || cols[0];
    return emp[fallbackCol] || 'Record';
}

const norm = str => String(str).toLowerCase().replace(/[^a-z0-9]/g, '');

// ── updateStepBar ────────────────────────────────────────────────
function updateStepBar(step) {
    for (let i = 1; i <= 5; i++) {
        const circle = document.getElementById(`wiz-sc-${i}`);
        const label  = circle?.nextElementSibling;
        circle?.classList.remove('active', 'done');
        label?.classList.remove('active', 'done');
        if (i < step) {
            circle?.classList.add('done');
            label?.classList.add('done');
            circle.innerHTML = '<i class="fa-solid fa-check" style="font-size:0.7rem"></i>';
        } else if (i === step) {
            circle?.classList.add('active');
            label?.classList.add('active');
            circle.textContent = i;
        } else {
            circle.textContent = i;
        }
        if (i < 5) {
            const line = document.getElementById(`wiz-line-${i}`);
            line?.classList.toggle('done', i < step);
        }
    }
    // back/next buttons
    const btnBack = document.getElementById('btn-wiz-back');
    const btnNext = document.getElementById('btn-wiz-next');
    btnBack.style.display = step > 1 ? '' : 'none';
    btnNext.style.display = step < 5 ? '' : 'none';
    // breadcrumb
    const crumbs = ['Employee data', 'Template', 'Map fields', 'Preview', 'Generate'];
    const bc = document.getElementById('wiz-breadcrumb');
    bc.innerHTML = crumbs.slice(0, step).map((c, i) =>
        `<span class="bc-item${i === step - 1 ? ' bc-active' : ''}">${c}</span>`
    ).join('');
}

// ── goToStep ─────────────────────────────────────────────────────
function goToStep(step) {
    document.querySelectorAll('.wiz-panel').forEach(p => p.classList.remove('active'));
    document.getElementById(`wiz-panel-${step}`)?.classList.add('active');
    wizardState.step = step;
    updateStepBar(step);
    // populate each step
    if (step === 1) populateStep1();
    if (step === 2) populateStep2();
    if (step === 3) populateStep3();
}

// ── Step 1: Employee selection ───────────────────────────────────
function populateStep1() {
    renderWizPartitionTabs();
    const grid = document.getElementById('wiz-emp-list');
    grid.innerHTML = '';

    const activePart = state.partitions.find(p => p.id === state.activePartition);
    const partName = activePart ? activePart.name : 'selected partition';

    if (state.employees.length === 0) {
        grid.innerHTML = `<p style="color:var(--text-muted);padding:20px">No employees in <strong>${partName}</strong> partition. Switch partition above or import an Excel file.</p>`;
        return;
    }
    state.employees.forEach((emp, i) => {
        const cols = state.columnKeys.length > 0 ? state.columnKeys : Object.keys(emp);

        // Smart Person Name Finder (ignoring Company Name / Org Name)
        const nameCol =
            cols.find(c => /^(employee\s*name|emp\s*name|full\s*name|staff\s*name|candidate\s*name|name)$/i.test(c.trim())) ||
            cols.find(c => /name/i.test(c) && !/company|org|department|dept|project|file|sheet|template/i.test(c)) ||
            cols.find(c => /name/i.test(c));

        // Subtitle Finder (Designation, Employee ID, or Code)
        const subCol =
            cols.find(c => /^(employee\s*id|emp\s*id|emp\s*code|employee\s*code|id)$/i.test(c.trim())) ||
            cols.find(c => /designation|title|role|position/i.test(c)) ||
            cols.find(c => /id|code|ref|no\.?/i.test(c) && !/company|org/i.test(c));

        const nonCompanyCol = cols.find(c => !/company|org/i.test(c) && emp[c]);
        const nameLabel = (nameCol && emp[nameCol]) ? emp[nameCol] : (nonCompanyCol ? emp[nonCompanyCol] : `Row ${i + 1}`);
        const subLabel  = (subCol && emp[subCol] && emp[subCol] !== nameLabel) ? emp[subCol] : '';

        const isSelected = wizardState.selectedIndexes.includes(i);

        const card = document.createElement('div');
        card.className = `wiz-emp-card${isSelected ? ' selected' : ''}`;
        card.innerHTML = `
            <input type="checkbox" class="wiz-emp-cb" data-idx="${i}" ${isSelected ? 'checked' : ''}>
            <div class="wiz-emp-card-info">
                <div class="wiz-emp-name">${nameLabel}</div>
                ${subLabel ? `<div class="wiz-emp-sub">${subLabel}</div>` : ''}
            </div>
        `;
        const cb = card.querySelector('.wiz-emp-cb');
        const toggle = () => {
            const idx = parseInt(cb.dataset.idx);
            if (cb.checked) {
                if (!wizardState.selectedIndexes.includes(idx))
                    wizardState.selectedIndexes.push(idx);
                card.classList.add('selected');
            } else {
                wizardState.selectedIndexes = wizardState.selectedIndexes.filter(x => x !== idx);
                card.classList.remove('selected');
            }
        };
        cb.addEventListener('change', toggle);
        card.addEventListener('click', e => { if (e.target !== cb) { cb.checked = !cb.checked; toggle(); } });
        grid.appendChild(card);
    });

    // Select All
    const selAll = document.getElementById('wiz-select-all');
    selAll.checked = wizardState.selectedIndexes.length === state.employees.length;
    selAll.onchange = () => {
        wizardState.selectedIndexes = selAll.checked ? state.employees.map((_, i) => i) : [];
        populateStep1();
        selAll.checked = wizardState.selectedIndexes.length === state.employees.length;
    };
}

// ── Step 2: Template selection ───────────────────────────────────
function populateStep2() {
    const grid = document.getElementById('wiz-template-list');
    grid.innerHTML = '';
    if (state.templates.length === 0) {
        grid.innerHTML = '<p style="color:var(--text-muted);padding:20px">No templates uploaded yet.</p>';
        return;
    }
    state.templates.forEach(t => {
        const isSelected = wizardState.templateId === t.id;
        const card = document.createElement('div');
        card.className = `wiz-tpl-card${isSelected ? ' selected' : ''}`;
        card.innerHTML = `
            <i class="fa-solid fa-file-word"></i>
            <h4>${t.name}</h4>
            <small>${t.placeholders.length} field(s)</small>
            ${isSelected ? '<div class="wiz-tpl-check"><i class="fa-solid fa-check"></i></div>' : ''}
        `;
        card.addEventListener('click', () => {
            if (wizardState.templateId !== t.id) {
                wizardState.fieldMapping = {}; // reset mapping when template changes
            }
            wizardState.templateId = t.id;
            populateStep2();
            setTimeout(() => {
                goToStep(3);
            }, 120);
        });
        grid.appendChild(card);
    });
}

// ── getTemplateTags: always scan binary XML — never fails ────────
// Tries placeholders[] first, falls back to scanning the stored DOCX binary.
// This ensures the mapping table is populated even if the template was uploaded
// before the placeholder-extraction fix was in place.
function getTemplateTags(templateDef) {
    if (templateDef.placeholders && templateDef.placeholders.length > 0) {
        return templateDef.placeholders;
    }
    // Scan the stored binary directly
    try {
        const zipScan = fixDocxSplitTags(new PizZip(templateDef.binary));
        const tags = extractPlaceholdersFromXml(zipScan);
        if (tags.length > 0) return tags;
    } catch (e) {
        console.warn('getTemplateTags scan failed:', e);
    }
    // Last resort: keys already in fieldMapping (from a previous session)
    return Object.keys(wizardState.fieldMapping);
}

// ── getAvailableCols: NEVER returns empty ────────────────────────
// Derives column list from state.columnKeys first, then from
// employee objects directly — so it works even if columnKeys wasn’t saved.
function getAvailableCols() {
    if (state.columnKeys && state.columnKeys.length > 0) {
        return state.columnKeys;
    }
    // Collect all unique keys across all employees
    const keySet = new Set();
    state.employees.forEach(emp => Object.keys(emp).forEach(k => keySet.add(k)));
    return Array.from(keySet);
}

// ── Step 3: Map fields ───────────────────────────────────────────
function populateStep3() {
    const templateDef = state.templates.find(t => t.id === wizardState.templateId);
    if (!templateDef) return;

    const cols = getAvailableCols();

    // Pick first selected employee as sample
    const sampleEmp = state.employees[wizardState.selectedIndexes[0]] || {};
    document.getElementById('map-sample-name').textContent = getRecordLabel(sampleEmp);

    // Always get tags from the most reliable source
    const tags = getTemplateTags(templateDef);

    // Debug info shown in UI so we can see what was detected
    console.log('[AutoMatch] Tags found:', tags);
    console.log('[AutoMatch] Columns available:', cols);

    // Auto-match on first entry (mapping empty)
    if (Object.keys(wizardState.fieldMapping).length === 0) {
        autoMatchFields(tags, cols);
    }

    const tbody = document.getElementById('mapping-tbody');
    tbody.innerHTML = '';

    if (cols.length === 0) {
        tbody.innerHTML = `<tr><td colspan="3" style="padding:20px;color:#ef4444;text-align:center">
            <i class="fa-solid fa-triangle-exclamation"></i>&nbsp;
            No Excel columns detected. Please import an Excel file first.
        </td></tr>`;
        return;
    }

    if (tags.length === 0) {
        tbody.innerHTML = `<tr><td colspan="3" style="padding:20px;color:var(--text-muted);text-align:center">
            No template fields detected. Make sure your template uses <code>{{Field}}</code> placeholders.
        </td></tr>`;
        return;
    }

    tags.forEach(tag => {
        const currentCol = wizardState.fieldMapping[tag] || '';
        const rawSample = currentCol ? (sampleEmp[currentCol] ?? '') : '';
        const sampleVal = formatPossibleDate(rawSample, currentCol);

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><span class="tpl-field-tag">{{${tag}}}</span></td>
            <td>
                <select class="form-control map-col-select" data-tag="${tag}">
                    <option value="">-- not mapped --</option>
                    ${cols.map(c => `<option value="${c}" ${c === currentCol ? 'selected' : ''}>${c}</option>`).join('')}
                </select>
            </td>
            <td class="sample-value-cell">${sampleVal}</td>
        `;
        tbody.appendChild(tr);

        tr.querySelector('.map-col-select').addEventListener('change', e => {
            const col = e.target.value;
            wizardState.fieldMapping[tag] = col;
            const updatedRaw = col ? (sampleEmp[col] ?? '') : '';
            tr.querySelector('.sample-value-cell').textContent = formatPossibleDate(updatedRaw, col);
        });
    });
}

// ── autoMatchFields: 4-level cascade matching ───────────────────────
// Level 1: exact match            — "Name" → "Name"
// Level 2: normalised match       — "Employee ID" → "employeeid" == norm("Employee id")
// Level 3: col-contains-tag       — tag "Name" inside col "Employee Name"
// Level 4: tag-contains-col       — col "Ref" inside tag "Reference No"
function autoMatchFields(tags, cols) {
    const normCols = cols.map(c => ({ original: c, normalized: norm(c) }));

    tags.forEach(tag => {
        const normTag = norm(tag);

        // Level 1: exact (case-sensitive)
        let match = cols.find(c => c === tag);

        // Level 2: fully normalised
        if (!match) match = normCols.find(c => c.normalized === normTag)?.original;

        // Level 3: column's normalized name contains the tag's normalized name
        if (!match) match = normCols.find(c => c.normalized.includes(normTag) && normTag.length >= 2)?.original;

        // Level 4: tag's normalized name contains the column's normalized name
        if (!match) match = normCols.find(c => normTag.includes(c.normalized) && c.normalized.length >= 2)?.original;

        wizardState.fieldMapping[tag] = match || '';
        console.log(`[AutoMatch] "${tag}" → "${match || '(no match)'}"`);
    });
}

document.getElementById('btn-auto-match-fields').addEventListener('click', () => {
    const templateDef = state.templates.find(t => t.id === wizardState.templateId);
    if (!templateDef) return;

    const cols = getAvailableCols();
    const tags = getTemplateTags(templateDef);

    console.log('[AutoMatch Button] Tags:', tags, 'Cols:', cols);

    // Clear existing mapping for a fresh auto-match
    wizardState.fieldMapping = {};
    autoMatchFields(tags, cols);
    populateStep3();
});

// ── Step 4: Preview ──────────────────────────────────────────────
async function runPreview() {
    const templateDef = state.templates.find(t => t.id === wizardState.templateId);
    const previewEl   = document.getElementById('wiz-preview-doc');
    previewEl.innerHTML = `<div class="preview-loading"><div class="preview-spinner"></div> Generating preview…</div>`;

    try {
        const blobs = [];
        for (const i of wizardState.selectedIndexes) {
            const blob = await generateDocumentBlob(templateDef, state.employees[i], wizardState.fieldMapping);
            blobs.push(await blob.arrayBuffer());
        }
        wizardState.previewBlobs = blobs;
        wizardState.previewIdx   = 0;
        updateWizPreviewNav();
        await renderWizPreview(blobs[0]);
    } catch (err) {
        console.error(err);
        previewEl.innerHTML = `<div class="preview-placeholder"><i class="fa-solid fa-triangle-exclamation" style="color:#ef4444"></i><p style="color:#ef4444">Preview error:<br>${err.message}</p></div>`;
    }
}

async function renderWizPreview(arrayBuffer) {
    const el = document.getElementById('wiz-preview-doc');
    el.innerHTML = `<div class="preview-loading"><div class="preview-spinner"></div> Rendering…</div>`;
    try {
        const result = await mammoth.convertToHtml({ arrayBuffer });
        el.innerHTML = result.value || '<p style="color:#999;font-family:Inter,sans-serif">No content.</p>';
    } catch (err) {
        el.innerHTML = `<p style="color:#ef4444;font-family:Inter,sans-serif">Render error: ${err.message}</p>`;
    }
}

function updateWizPreviewNav() {
    const badge   = document.getElementById('wiz-record-badge');
    const btnPrev = document.getElementById('wiz-btn-prev');
    const btnNext = document.getElementById('wiz-btn-next');
    const total   = wizardState.previewBlobs.length;
    if (total <= 1) {
        badge.style.display = btnPrev.style.display = btnNext.style.display = 'none';
    } else {
        badge.style.display = btnPrev.style.display = btnNext.style.display = '';
        badge.textContent = `${wizardState.previewIdx + 1} / ${total}`;
        btnPrev.disabled = wizardState.previewIdx === 0;
        btnNext.disabled = wizardState.previewIdx === total - 1;
    }
}

document.getElementById('wiz-btn-prev').addEventListener('click', async () => {
    if (wizardState.previewIdx > 0) {
        wizardState.previewIdx--;
        updateWizPreviewNav();
        await renderWizPreview(wizardState.previewBlobs[wizardState.previewIdx]);
    }
});
document.getElementById('wiz-btn-next').addEventListener('click', async () => {
    if (wizardState.previewIdx < wizardState.previewBlobs.length - 1) {
        wizardState.previewIdx++;
        updateWizPreviewNav();
        await renderWizPreview(wizardState.previewBlobs[wizardState.previewIdx]);
    }
});

// ── Step 5: Download ─────────────────────────────────────────────
document.getElementById('btn-wiz-download').addEventListener('click', async () => {
    const templateDef = state.templates.find(t => t.id === wizardState.templateId);
    if (!templateDef || !wizardState.previewBlobs.length) return;

    try {
        if (wizardState.selectedIndexes.length === 1) {
            const emp   = state.employees[wizardState.selectedIndexes[0]];
            const label = getRecordLabel(emp);
            const blob  = new Blob([wizardState.previewBlobs[0]], {
                type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            });
            saveAs(blob, `${label.replace(/\s+/g, '_')}_${templateDef.name}`);
            await logHistory(emp, templateDef.name);
        } else {
            const zip = new JSZip();
            for (let i = 0; i < wizardState.selectedIndexes.length; i++) {
                const emp   = state.employees[wizardState.selectedIndexes[i]];
                const label = getRecordLabel(emp);
                zip.file(`${label.replace(/\s+/g, '_')}_${templateDef.name}`, wizardState.previewBlobs[i]);
                await logHistory(emp, templateDef.name);
            }
            const zipBlob = await zip.generateAsync({ type: 'blob' });
            saveAs(zipBlob, `Bulk_${templateDef.name.replace('.docx', '')}_${Date.now()}.zip`);
        }
        renderHistory();
        updateDashboard();
    } catch (err) {
        console.error(err);
        alert('Download failed: ' + err.message);
    }
});

// ── Wizard Next/Back navigation ──────────────────────────────────
document.getElementById('btn-wiz-next').addEventListener('click', async () => {
    const step = wizardState.step;

    if (step === 1) {
        if (wizardState.selectedIndexes.length === 0)
            return alert('Please select at least one employee.');
        goToStep(2);

    } else if (step === 2) {
        if (!wizardState.templateId)
            return alert('Please select a template.');
        goToStep(3);

    } else if (step === 3) {
        goToStep(4);
        await runPreview(); // generate all previews

    } else if (step === 4) {
        // populate Step 5 summary
        const count = wizardState.selectedIndexes.length;
        document.getElementById('gen-summary').textContent =
            `${count} document${count > 1 ? 's are' : ' is'} ready to download.`;
        goToStep(5);
    }
});

document.getElementById('btn-wiz-back').addEventListener('click', () => {
    if (wizardState.step > 1) goToStep(wizardState.step - 1);
});

// ── Entry point called when navigating to Mail Merge ─────────────
function renderMergeView() {
    // Reset wizard to step 1 (keep selections if re-entering)
    goToStep(1);
}



async function generateDocumentBlob(templateDef, empData, customMapping = null) {
    // Re-apply split-tag fix
    const zip = fixDocxSplitTags(new PizZip(templateDef.binary));

    // ── Step 1: Build a normalised lookup from Excel columns ──────────────────
    const normFn = str => String(str).toLowerCase().replace(/[^a-z0-9]/g, '');

    const colLookup = {};
    for (const key of Object.keys(empData)) {
        const rawVal = empData[key] ?? '';
        const formattedVal = formatPossibleDate(rawVal, key);
        colLookup[normFn(key)] = { originalKey: key, value: formattedVal };
    }

    // ── Step 3: Build surgically-correct mappedData ────────────────────────
    const mappedData = {};

    if (customMapping && Object.keys(customMapping).length > 0) {
        // Wizard mapping: { templateTag → excelColumnKey }
        for (const [tag, colKey] of Object.entries(customMapping)) {
            const rawVal = colKey ? (empData[colKey] ?? '') : '';
            mappedData[tag] = formatPossibleDate(rawVal, colKey || tag);
        }
    }

    // Scan the actual XML for every {{tag}} and auto-match any not covered by customMapping
    const allXml = Object.keys(zip.files)
        .filter(isDocumentXmlPart)
        .map(n => zip.files[n].asText())
        .join('\n');

    const templateTags = [...new Set(
        [...allXml.matchAll(/\{\{\s*([^{}]+?)\s*\}\}/g)].map(m => m[1].trim())
    )];

    for (const tag of templateTags) {
        if (mappedData[tag] !== undefined) continue; // already set by customMapping
        const match = colLookup[normFn(tag)];
        const rawVal = match ? match.value : '';
        mappedData[tag] = formatPossibleDate(rawVal, match ? match.originalKey : tag);
    }

    // Also add column key variants as safety net for docxtemplater
    for (const key of Object.keys(empData)) {
        const rawVal = empData[key] ?? '';
        const val = formatPossibleDate(rawVal, key);
        mappedData[key] = val;
        mappedData[key.replace(/\s+/g, '_')] = val;
        mappedData[key.replace(/\s+/g, '')] = val;
        mappedData[key.toLowerCase()] = val;
        mappedData[key.toLowerCase().replace(/\s+/g, '_')] = val;
    }


    // ── Step 4: Try docxtemplater first ───────────────────────────────────
    try {
        const doc = new window.docxtemplater(zip, {
            paragraphLoop: true,
            linebreaks: true,
            nullGetter: () => '',
        });
        doc.render(mappedData);
        return doc.getZip().generate({
            type: 'blob',
            mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        });
    } catch (docxErr) {
        console.warn('docxtemplater render failed, using XML fallback:', docxErr);
    }

    // ── Step 5: Fallback — direct XML string replacement ─────────────────
    const fallbackZip = fixDocxSplitTags(new PizZip(templateDef.binary));
    const xmlFiles = Object.keys(fallbackZip.files).filter(isDocumentXmlPart);

    xmlFiles.forEach(partName => {
        let xml = fallbackZip.files[partName].asText();

        // For every {{tag}} still in this file, replace using our fuzzy match
        xml = xml.replace(/\{\{\s*([^{}]+?)\s*\}\}/g, (fullMatch, rawTag) => {
            const tag = rawTag.trim();

            // 1. Direct mappedData lookup (exact tag)
            if (mappedData[tag] !== undefined) return mappedData[tag];

            // 2. Fuzzy lookup: normalise the tag and find best Excel column
            const normalizedTag = norm(tag);
            const fuzzyMatch = colLookup[normalizedTag];
            if (fuzzyMatch) return formatPossibleDate(fuzzyMatch.value, fuzzyMatch.originalKey || tag);

            // 3. No match → leave blank
            return '';
        });

        fallbackZip.file(partName, xml);
    });

    return fallbackZip.generate({
        type: 'blob',
        mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    });
}

async function logHistory(empData, templateName) {
    const employeeName = getRecordLabel(empData);
    const entry = {
        id: Date.now() + Math.random(),
        date: new Date().toISOString(),
        employeeName: employeeName || 'Employee',
        templateName: templateName || 'Document'
    };
    const hist = [...state.history, entry];
    await saveData('history', hist);
    renderHistory();
    updateDashboard();
}

// Start app
window.onload = initApp;
