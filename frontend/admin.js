// API base URL
const API_BASE = window.location.hostname.includes('railway') 
    ? `${window.location.protocol}//${window.location.host}/api`
    : 'http://localhost:8000/api';

// State
let acts = [];
let categories = [];
let filteredActs = [];
let radaActsList = [];
let radaPagination = {
    skip: 0,
    limit: 100,
    hasMore: false,
    loading: false,
    total: 0
};
let radaListRefreshInterval = null; // Global variable for auto-refresh interval

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadActs();
    loadCategories();
    loadStats();
});

// Event listeners
function setupEventListeners() {
    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tab = e.target.dataset.tab;
            switchTab(tab);
        });
    });

    // Refresh button
    document.getElementById('refresh-btn').addEventListener('click', () => {
        loadActs();
        loadCategories();
        loadStats();
    });

    // Process new act button
    document.getElementById('process-new-btn').addEventListener('click', () => {
        document.getElementById('process-modal').classList.add('active');
    });

    // Auto-download button
    document.getElementById('auto-download-btn').addEventListener('click', startAutoDownload);
    
    // Load Rada list button
    const loadRadaBtn = document.getElementById('load-rada-list-btn');
    if (loadRadaBtn) {
        loadRadaBtn.addEventListener('click', () => {
            console.log('Load Rada button clicked');
            loadRadaActsList(true);
        });
    } else {
        console.error('load-rada-list-btn not found!');
    }
    
    // Sync all Rada acts button
    const syncAllRadaBtn = document.getElementById('sync-all-rada-btn');
    if (syncAllRadaBtn) {
        syncAllRadaBtn.addEventListener('click', syncAllRadaActs);
    } else {
        console.error('sync-all-rada-btn not found!');
    }
    
    // Download active acts button
    const downloadActiveBtn = document.getElementById('download-active-acts-btn');
    if (downloadActiveBtn) {
        downloadActiveBtn.addEventListener('click', () => downloadActiveActs(false));
    }
    
    // Download active acts and process button
    const downloadActiveAndProcessBtn = document.getElementById('download-active-and-process-btn');
    if (downloadActiveAndProcessBtn) {
        downloadActiveAndProcessBtn.addEventListener('click', () => downloadActiveActs(true));
    }
    
    // Download from dataset button
    const downloadFromDatasetBtn = document.getElementById('download-from-dataset-btn');
    if (downloadFromDatasetBtn) {
        downloadFromDatasetBtn.addEventListener('click', downloadFromDataset);
    }
    
    // Process all overnight button
    const processAllOvernightBtn = document.getElementById('process-all-overnight-btn');
    if (processAllOvernightBtn) {
        processAllOvernightBtn.addEventListener('click', processAllOvernight);
    } else {
        console.error('process-all-overnight-btn not found!');
    }
    
    // Auto-refresh Rada list when tab is active
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tab = e.target.dataset.tab;
            if (tab === 'rada-list') {
                // Start auto-refresh when tab is active
                if (!radaListRefreshInterval) {
                    radaListRefreshInterval = setInterval(() => {
                        loadRadaActsList(false); // Don't reset, just update
                    }, 10000); // Refresh every 10 seconds
                }
            } else {
                // Stop auto-refresh when tab is not active
                if (radaListRefreshInterval) {
                    clearInterval(radaListRefreshInterval);
                    radaListRefreshInterval = null;
                }
            }
        });
    });

    // Close modals
    document.getElementById('close-modal').addEventListener('click', closeDetailsModal);
    document.getElementById('close-process-modal').addEventListener('click', closeProcessModal);
    document.getElementById('cancel-process-btn').addEventListener('click', closeProcessModal);

    // Process act
    document.getElementById('start-process-btn').addEventListener('click', processNewAct);

    // Filters
    document.getElementById('processed-only').addEventListener('change', applyFilters);
    document.getElementById('search-input').addEventListener('input', applyFilters);

    // Close modal on outside click
    window.addEventListener('click', (e) => {
        const detailsModal = document.getElementById('details-modal');
        const processModal = document.getElementById('process-modal');
        if (e.target === detailsModal) {
            closeDetailsModal();
        }
        if (e.target === processModal) {
            closeProcessModal();
        }
    });
}

// Load acts
async function loadActs() {
    try {
        const response = await fetch(`${API_BASE}/legal-acts/?limit=1000`);
        acts = await response.json();
        applyFilters();
    } catch (error) {
        console.error('Error loading acts:', error);
        document.getElementById('acts-list').innerHTML = 
            '<p class="loading">Помилка завантаження актів</p>';
    }
}

// Load categories
async function loadCategories() {
    try {
        const response = await fetch(`${API_BASE}/categories/`);
        categories = await response.json();
        renderCategories();
    } catch (error) {
        console.error('Error loading categories:', error);
        document.getElementById('categories-list').innerHTML = 
            '<p class="loading">Помилка завантаження категорій</p>';
    }
}

// Load statistics
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/status/`);
        const data = await response.json();
        
        document.getElementById('total-acts').textContent = data.database?.legal_acts_count || 0;
        document.getElementById('processed-acts').textContent = 
            acts.filter(a => a.is_processed).length;
        document.getElementById('total-categories').textContent = 
            data.database?.categories_count || 0;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Apply filters
function applyFilters() {
    const processedOnly = document.getElementById('processed-only').checked;
    const searchTerm = document.getElementById('search-input').value.toLowerCase();

    filteredActs = acts.filter(act => {
        if (processedOnly && !act.is_processed) return false;
        if (searchTerm && !act.title.toLowerCase().includes(searchTerm)) return false;
        return true;
    });

    renderActs();
}

// Render acts
function renderActs() {
    const container = document.getElementById('acts-list');

    if (filteredActs.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📭</div>
                <p>Актів не знайдено</p>
            </div>
        `;
        return;
    }

            container.innerHTML = filteredActs.map(act => {
                const formatDate = (dateStr) => {
                    if (!dateStr) return 'Не вказано';
                    try {
                        const date = new Date(dateStr);
                        return date.toLocaleDateString('uk-UA', { 
                            year: 'numeric', 
                            month: 'long', 
                            day: 'numeric' 
                        });
                    } catch {
                        return dateStr;
                    }
                };

                return `
        <div class="act-card ${act.is_processed ? 'processed' : 'not-processed'}">
            <div class="act-header">
                <div style="flex: 1;">
                    <div class="act-title">${escapeHtml(act.title)}</div>
                    <div class="act-nreg">📋 ${escapeHtml(act.nreg)}</div>
                    <div class="act-metadata">
                        ${act.document_type ? `<span class="meta-item">📄 ${escapeHtml(act.document_type)}</span>` : ''}
                        ${act.status ? `<span class="meta-item status-${act.status.toLowerCase().replace(/\s+/g, '-')}">${getStatusIcon(act.status)} ${escapeHtml(act.status)}</span>` : ''}
                        ${act.date_acceptance ? `<span class="meta-item">📅 Прийнято: ${formatDate(act.date_acceptance)}</span>` : ''}
                        ${act.date_publication ? `<span class="meta-item">📰 Опубліковано: ${formatDate(act.date_publication)}</span>` : ''}
                    </div>
                </div>
                <div class="act-badges">
                    ${act.is_processed 
                        ? '<span class="badge badge-success">✅ Оброблено</span>' 
                        : '<span class="badge badge-warning">⏳ Не оброблено</span>'}
                </div>
            </div>
            <div class="act-actions">
                <button class="btn btn-primary btn-small" onclick="showActDetails('${escapeHtml(act.nreg)}')">
                    <span>👁️</span> Деталі
                </button>
                <button class="btn btn-info btn-small" onclick="checkActOnRada('${escapeHtml(act.nreg)}')">
                    <span>🔍</span> Перевірити на Rada
                </button>
                ${!act.is_processed 
                    ? `<button class="btn btn-success btn-small" onclick="processAct('${escapeHtml(act.nreg)}')">
                        <span>⚙️</span> Обробити
                    </button>`
                    : ''}
            </div>
        </div>
    `;
            }).join('');
}

// Render categories
function renderCategories() {
    const container = document.getElementById('categories-list');

    if (categories.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📁</div>
                <p>Категорії не знайдено</p>
            </div>
        `;
        return;
    }

    container.innerHTML = categories.map(cat => `
        <div class="category-card">
            <div class="act-header">
                <div>
                    <div class="act-title">${cat.name}</div>
                    <div class="act-nreg">ID: ${cat.id} | Елементів: ${cat.element_count}</div>
                </div>
            </div>
        </div>
    `).join('');
}

// Process all NPA overnight
async function processAllOvernight() {
    const btn = document.getElementById('process-all-overnight-btn');
    if (!btn) {
        console.error('process-all-overnight-btn not found!');
        return;
    }
    
    if (!confirm('🌙 Запустити нічну обробку всіх необроблених НПА?\n\nЦе може зайняти багато часу. Обробка буде виконуватися в фоновому режимі.')) {
        return;
    }
    
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<span>⏳</span> Запуск обробки...';
    
    // Show notification
    const notification = document.createElement('div');
    notification.id = 'overnight-notification';
    notification.className = 'notification notification-info';
    notification.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 10000; padding: 16px; background: #6366f1; color: white; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); max-width: 400px;';
    notification.innerHTML = `
        <div style="display: flex; align-items: flex-start; gap: 12px;">
            <div style="font-size: 24px;">🌙</div>
            <div style="flex: 1;">
                <div style="font-weight: 600; font-size: 16px; margin-bottom: 4px;">Нічна обробка запущена</div>
                <div style="font-size: 14px; opacity: 0.9;">Обробка всіх необроблених НПА виконується в фоновому режимі. Перевірте логи на сервері для прогресу.</div>
            </div>
        </div>
    `;
    document.body.appendChild(notification);
    
    try {
        const response = await fetch(`${API_BASE}/legal-acts/process-all-overnight`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        // Update notification to success
        notification.className = 'notification notification-success';
        notification.style.background = '#10b981';
        notification.innerHTML = `
            <div style="display: flex; align-items: flex-start; gap: 12px;">
                <div style="font-size: 24px;">✅</div>
                <div style="flex: 1;">
                    <div style="font-weight: 600; font-size: 16px; margin-bottom: 4px;">Обробка запущена</div>
                    <div style="font-size: 14px; opacity: 0.9;">${data.message}</div>
                </div>
            </div>
        `;
        
        // Remove notification after 10 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 10000);
        
    } catch (error) {
        console.error('Error starting overnight processing:', error);
        
        // Update notification to error
        notification.className = 'notification notification-error';
        notification.style.background = '#ef4444';
        notification.innerHTML = `
            <div style="display: flex; align-items: flex-start; gap: 12px;">
                <div style="font-size: 24px;">❌</div>
                <div style="flex: 1;">
                    <div style="font-weight: 600; font-size: 16px; margin-bottom: 4px;">Помилка</div>
                    <div style="font-size: 14px; opacity: 0.9;">${error.message}</div>
                </div>
            </div>
        `;
        
        // Remove notification after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// Sync all Rada acts (one-time download of all NPA from Rada API)
async function syncAllRadaActs() {
    const btn = document.getElementById('sync-all-rada-btn');
    if (!btn) {
        console.error('sync-all-rada-btn not found!');
        return;
    }
    
    const originalText = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<span>⏳</span> Завантаження всіх НПА...';
    
    // Show notification
    const notification = document.createElement('div');
    notification.id = 'sync-notification';
    notification.className = 'notification notification-info';
    notification.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 10000; padding: 16px; background: #3b82f6; color: white; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);';
    notification.textContent = '⏳ Запущено завантаження всіх НПА з Rada API. Це може зайняти багато часу...';
    document.body.appendChild(notification);
    
    try {
        const response = await fetch(`${API_BASE}/legal-acts/rada-list/sync-all`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        // Update notification to success
        notification.className = 'notification notification-success';
        notification.style.background = '#10b981';
        notification.textContent = `✅ ${data.message}`;
        
        // Remove notification after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
        
        // Refresh the list after a delay
        setTimeout(() => {
            loadRadaActsList(true);
        }, 2000);
        
    } catch (error) {
        console.error('Error syncing all Rada acts:', error);
        
        // Update notification to error
        notification.className = 'notification notification-error';
        notification.style.background = '#ef4444';
        notification.textContent = `❌ Помилка: ${error.message}`;
        
        // Remove notification after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// Load Rada acts list (with pagination)
async function loadRadaActsList(reset = true) {
    console.log('loadRadaActsList called, reset:', reset);
    
    if (radaPagination.loading) {
        console.log('Already loading, skipping...');
        return;
    }
    
    const container = document.getElementById('rada-list');
    const statsContainer = document.getElementById('rada-stats');
    
    if (!container) {
        console.error('rada-list container not found!');
        return;
    }
    
    if (reset) {
        radaPagination.skip = 0;
        radaActsList = [];
        container.innerHTML = '<p class="loading">Завантаження списку з Rada API...</p>';
        if (statsContainer) statsContainer.innerHTML = '';
    } else {
        // Show loading indicator at bottom
        const loadingIndicator = document.createElement('div');
        loadingIndicator.id = 'rada-loading-indicator';
        loadingIndicator.className = 'loading';
        loadingIndicator.textContent = 'Завантаження...';
        container.appendChild(loadingIndicator);
    }
    
    radaPagination.loading = true;
    
    try {
        const url = `${API_BASE}/legal-acts/rada-list?skip=${radaPagination.skip}&limit=${radaPagination.limit}`;
        console.log('Fetching from:', url);
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Received data:', data);
        
        // Remove loading indicator
        const loadingIndicator = document.getElementById('rada-loading-indicator');
        if (loadingIndicator) loadingIndicator.remove();
        
        // Append new acts to list
        if (reset) {
            radaActsList = data.acts || [];
        } else {
            radaActsList = [...radaActsList, ...(data.acts || [])];
        }
        
        // Update pagination state
        radaPagination.skip = data.skip || radaPagination.skip;
        radaPagination.hasMore = data.has_more || false;
        radaPagination.total = data.total || 0;
        
        // Update stats (only on first load)
        if (reset) {
            statsContainer.innerHTML = `
                <div class="rada-stat-item">
                    <span class="rada-stat-label">Всього НПА:</span>
                    <span class="rada-stat-value">${data.total || 0}</span>
                </div>
                <div class="rada-stat-item">
                    <span class="rada-stat-label">Завантажено:</span>
                    <span class="rada-stat-value">${data.loaded || 0}</span>
                </div>
                <div class="rada-stat-item">
                    <span class="rada-stat-label">Оброблено:</span>
                    <span class="rada-stat-value">${data.processed || 0}</span>
                </div>
                <div class="rada-stat-item">
                    <span class="rada-stat-label">Не завантажено:</span>
                    <span class="rada-stat-value">${data.not_loaded || 0}</span>
                </div>
            `;
        }
        
        renderRadaActsList();
    } catch (error) {
        console.error('Error loading Rada acts list:', error);
        const loadingIndicator = document.getElementById('rada-loading-indicator');
        if (loadingIndicator) loadingIndicator.remove();
        
        if (reset && container) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">❌</div>
                    <p>Помилка завантаження списку з Rada API</p>
                    <p class="error-detail">${error.message}</p>
                    <p style="margin-top: 10px; font-size: 0.9rem; color: var(--text-muted);">
                        Перевірте консоль браузера (F12) для деталей
                    </p>
                </div>
            `;
        }
    } finally {
        radaPagination.loading = false;
        console.log('loadRadaActsList finished, loading:', radaPagination.loading);
    }
}

// Render Rada acts list
function renderRadaActsList() {
    const container = document.getElementById('rada-list');
    
    if (radaActsList.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📭</div>
                <p>НПА не знайдено</p>
            </div>
        `;
        return;
    }
    
    // Create or update container
    let listContainer = container.querySelector('.rada-list-container');
    if (!listContainer) {
        listContainer = document.createElement('div');
        listContainer.className = 'rada-list-container';
        container.innerHTML = '';
        container.appendChild(listContainer);
    }
    
    // Render all acts with improved status display
    listContainer.innerHTML = radaActsList.map(act => {
        // Determine status based on in_database and is_processed
        let statusClass, statusIcon, statusBadge;
        
        if (act.is_processed) {
            statusClass = 'status-processed';
            statusIcon = '✅';
            statusBadge = '<span class="status-badge badge-processed">Оброблено</span>';
        } else if (act.in_database) {
            statusClass = 'status-loaded';
            statusIcon = '📥';
            statusBadge = '<span class="status-badge badge-loaded">Завантажено</span>';
        } else {
            statusClass = 'status-not-loaded';
            statusIcon = '⭕';
            statusBadge = '<span class="status-badge badge-not-loaded">Не завантажено</span>';
        }
        
        // Show status from Rada API if available
        const radaStatus = act.status ? `<span class="rada-status">Статус: ${escapeHtml(act.status)}</span>` : '';
        
        return `
            <div class="rada-act-item ${statusClass}" data-nreg="${escapeHtml(act.nreg)}">
                <div class="rada-act-info">
                    <div class="rada-act-nreg">${escapeHtml(act.nreg)}</div>
                    ${act.title && act.title !== act.nreg ? `
                        <div class="rada-act-title">${escapeHtml(act.title)}</div>
                    ` : ''}
                    ${radaStatus}
                </div>
                <div class="rada-act-status">
                    <span class="status-icon">${statusIcon}</span>
                    ${statusBadge}
                </div>
                ${!act.is_processed ? `
                    <button class="btn btn-sm btn-success process-act-btn" data-nreg="${escapeHtml(act.nreg)}">
                        <span>⚙️</span> ${act.in_database ? 'Обробити' : 'Завантажити та обробити'}
                    </button>
                ` : ''}
            </div>
        `;
    }).join('');
    
    // Add event listeners for process buttons
    listContainer.querySelectorAll('.process-act-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const nreg = e.target.closest('.process-act-btn').dataset.nreg;
            await processAct(nreg);
            // Refresh list after processing
            setTimeout(() => {
                loadRadaActsList(true);
            }, 2000);
        });
    });
    
    // Add scroll listener for auto-loading
    setupRadaScrollListener(container);
}

// Setup scroll listener for auto-loading more items
function setupRadaScrollListener(container) {
    // Remove existing listener if any
    container.removeEventListener('scroll', handleRadaScroll);
    
    // Add new scroll listener
    container.addEventListener('scroll', handleRadaScroll);
}

// Handle scroll event for auto-loading
function handleRadaScroll(e) {
    const container = e.target;
    const scrollTop = container.scrollTop;
    const scrollHeight = container.scrollHeight;
    const clientHeight = container.clientHeight;
    
    // Load more when user scrolls to 80% of the content
    if (scrollTop + clientHeight >= scrollHeight * 0.8) {
        if (radaPagination.hasMore && !radaPagination.loading) {
            radaPagination.skip += radaPagination.limit;
            loadRadaActsList(false); // Don't reset, append
        }
    }
}

// Show act details
async function showActDetails(nreg) {
    const modal = document.getElementById('details-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');

    modal.classList.add('active');
    modalTitle.textContent = `Деталі акту: ${nreg}`;
    modalBody.innerHTML = '<p class="loading">Завантаження...</p>';

    try {
        // Encode NREG but preserve / characters for path segments
        // Split by /, encode each part, then join back
        const encodedNreg = nreg.split('/').map(part => encodeURIComponent(part)).join('/');
        const response = await fetch(`${API_BASE}/legal-acts/${encodedNreg}/details`);
        const data = await response.json();

        let html = `
            <div class="details-section">
                <h3>📋 Основна інформація</h3>
                <div class="details-grid">
                    <div class="detail-item">
                        <div class="detail-label">Назва</div>
                        <div class="detail-value">${escapeHtml(data.title)}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Статус обробки</div>
                        <div class="detail-value">${data.is_processed ? '✅ Оброблено' : '⏳ Не оброблено'}</div>
                    </div>
                    ${data.processed_at ? `
                    <div class="detail-item">
                        <div class="detail-label">Дата обробки</div>
                        <div class="detail-value">${new Date(data.processed_at).toLocaleString('uk-UA')}</div>
                    </div>
                    ` : ''}
                    ${data.document_type ? `
                    <div class="detail-item">
                        <div class="detail-label">Тип документа</div>
                        <div class="detail-value">${escapeHtml(data.document_type)}</div>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;

        if (data.categories && data.categories.length > 0) {
            html += `
                <div class="details-section">
                    <h3>📁 Категорії (${data.categories.length})</h3>
                    <div class="act-categories">
                        ${data.categories.map(cat => `
                            <span class="category-tag">${escapeHtml(cat.name)}</span>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        if (data.extracted_elements) {
            const elements = data.extracted_elements;
            
            if (elements.categories && elements.categories.length > 0) {
                html += `
                    <div class="details-section">
                        <h3>🏷️ Виділені категорії</h3>
                        <div class="act-categories">
                            ${elements.categories.map(cat => `
                                <span class="category-tag">${escapeHtml(cat)}</span>
                            `).join('')}
                        </div>
                    </div>
                `;
            }

            if (elements.elements && elements.elements.length > 0) {
                html += `
                    <div class="details-section">
                        <h3>📝 Виділені елементи (${elements.elements.length})</h3>
                        <div class="elements-list">
                            ${elements.elements.slice(0, 10).map(el => `
                                <div class="element-item">
                                    <div class="element-header">
                                        <span class="element-type">${el.type || 'Елемент'} ${el.number || ''}</span>
                                    </div>
                                    <div class="element-text">${escapeHtml(el.text || '')}</div>
                                </div>
                            `).join('')}
                            ${elements.elements.length > 10 ? `<p>... та ще ${elements.elements.length - 10} елементів</p>` : ''}
                        </div>
                    </div>
                `;
            }

            if (elements.relations && elements.relations.length > 0) {
                html += `
                    <div class="details-section">
                        <h3>🔗 Зв'язки з іншими актами (${elements.relations.length})</h3>
                        <div class="relations-list">
                            ${elements.relations.map(rel => `
                                <div class="relation-item">
                                    <div>
                                        <span class="relation-type">${rel.type || 'зв\'язок'}</span>
                                        <div>${rel.target_nreg || 'N/A'}</div>
                                    </div>
                                    <div>${escapeHtml(rel.description || '')}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            }
        }

        modalBody.innerHTML = html;
    } catch (error) {
        console.error('Error loading details:', error);
        modalBody.innerHTML = '<p class="loading">Помилка завантаження деталей</p>';
    }
}

// Check if act exists on Rada website
async function checkActExists(nreg) {
    try {
        const encodedNreg = nreg.split('/').map(part => encodeURIComponent(part)).join('/');
        const response = await fetch(`${API_BASE}/legal-acts/${encodedNreg}/check`);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error checking act:', error);
        return {
            exists: false,
            message: 'Помилка при перевірці акту'
        };
    }
}

// Check act on Rada website (standalone function with UI)
async function checkActOnRada(nreg) {
    const statusDiv = document.createElement('div');
    statusDiv.className = 'status-message';
    statusDiv.style.cssText = 'position: fixed; top: 20px; right: 20px; padding: 20px; border-radius: 12px; z-index: 10000; max-width: 450px; box-shadow: 0 8px 24px rgba(0,0,0,0.4); font-family: Inter, sans-serif;';
    statusDiv.style.background = 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)';
    statusDiv.style.color = 'white';
    statusDiv.innerHTML = `
        <div style="display: flex; align-items: center; gap: 12px;">
            <div style="font-size: 24px;">🔍</div>
            <div>
                <div style="font-weight: 600; font-size: 16px; margin-bottom: 4px;">Перевірка акту...</div>
                <div style="font-size: 14px; opacity: 0.9;">Перевіряємо на сайті data.rada.gov.ua</div>
            </div>
        </div>
    `;
    document.body.appendChild(statusDiv);
    
    const checkResult = await checkActExists(nreg);
    
    if (checkResult.exists) {
        statusDiv.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
        statusDiv.innerHTML = `
            <div style="display: flex; align-items: flex-start; gap: 12px;">
                <div style="font-size: 24px;">✅</div>
                <div style="flex: 1;">
                    <div style="font-weight: 600; font-size: 16px; margin-bottom: 8px;">Акт знайдено!</div>
                    <div style="font-size: 14px; opacity: 0.95; margin-bottom: 4px; font-weight: 500;">${checkResult.title || nreg}</div>
                    <div style="font-size: 12px; opacity: 0.8; margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.2);">
                        ${checkResult.in_database ? '📦 Вже є в базі даних' : '🌐 Знайдено на сайті Rada'}
                        ${checkResult.is_processed ? ' | ✅ Оброблено' : ''}
                    </div>
                    <div style="font-size: 11px; opacity: 0.7; margin-top: 4px;">${checkResult.message}</div>
                </div>
            </div>
        `;
        setTimeout(() => statusDiv.remove(), 8000);
    } else {
        statusDiv.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
        statusDiv.innerHTML = `
            <div style="display: flex; align-items: flex-start; gap: 12px;">
                <div style="font-size: 24px;">❌</div>
                <div style="flex: 1;">
                    <div style="font-weight: 600; font-size: 16px; margin-bottom: 8px;">Акт не знайдено</div>
                    <div style="font-size: 14px; opacity: 0.95; margin-bottom: 4px;">NREG: ${nreg}</div>
                    <div style="font-size: 12px; opacity: 0.8; margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.2);">
                        ${checkResult.message}
                    </div>
                </div>
            </div>
        `;
        setTimeout(() => statusDiv.remove(), 8000);
    }
}

// Process act
async function processAct(nreg) {
    // Check if act is already processed in the current list
    const actInList = radaActsList.find(a => a.nreg === nreg);
    if (actInList && actInList.is_processed) {
        showNotification('info', `ℹ️ Акт ${nreg} вже оброблено. Використовуйте force_reprocess=true для повторної обробки.`, 5000);
        return;
    }
    
    // First check if act exists
    const statusDiv = document.createElement('div');
    statusDiv.className = 'status-message';
    statusDiv.style.cssText = 'position: fixed; top: 20px; right: 20px; padding: 16px; border-radius: 8px; z-index: 10000; max-width: 400px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);';
    statusDiv.innerHTML = '<div style="display: flex; align-items: center; gap: 8px;"><span>🔍</span> Перевірка акту на сайті data.rada.gov.ua...</div>';
    document.body.appendChild(statusDiv);
    
    const checkResult = await checkActExists(nreg);
    
    // Check if already processed
    if (checkResult.is_processed) {
        statusDiv.style.background = 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)';
        statusDiv.innerHTML = `
            <div style="display: flex; align-items: flex-start; gap: 12px;">
                <div style="font-size: 24px;">ℹ️</div>
                <div style="flex: 1;">
                    <div style="font-weight: 600; font-size: 16px; margin-bottom: 8px;">Акт вже оброблено</div>
                    <div style="font-size: 14px; opacity: 0.95; margin-bottom: 4px; font-weight: 500;">${checkResult.title || nreg}</div>
                    <div style="font-size: 12px; opacity: 0.8; margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.2);">
                        Акт вже був оброблено раніше. Повторна обробка не потрібна.
                    </div>
                </div>
            </div>
        `;
        setTimeout(() => statusDiv.remove(), 5000);
        return;
    }
    
    if (!checkResult.exists) {
        statusDiv.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
        statusDiv.style.color = 'white';
        statusDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <span>❌</span>
                <div>
                    <div style="font-weight: 600; margin-bottom: 4px;">Акт не знайдено</div>
                    <div style="font-size: 0.9rem; opacity: 0.9;">${checkResult.message}</div>
                </div>
            </div>
        `;
        setTimeout(() => statusDiv.remove(), 5000);
        return;
    }
    
    statusDiv.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
    statusDiv.style.color = 'white';
    statusDiv.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px;">
            <span>✅</span>
            <div>
                <div style="font-weight: 600; margin-bottom: 4px;">Акт знайдено!</div>
                <div style="font-size: 0.9rem; opacity: 0.9;">${checkResult.title || nreg}</div>
            </div>
        </div>
    `;
    
    if (!confirm(`Акт знайдено на сайті data.rada.gov.ua!\n\n"${checkResult.title || nreg}"\n\nОбробити акт "${nreg}"?`)) {
        statusDiv.remove();
        return;
    }
    
    statusDiv.innerHTML = '<div style="display: flex; align-items: center; gap: 8px;"><span>⚙️</span> Запуск обробки...</div>';
    statusDiv.style.background = 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)';

    try {
        const encodedNreg = nreg.split('/').map(part => encodeURIComponent(part)).join('/');
        const response = await fetch(`${API_BASE}/legal-acts/${encodedNreg}/process`, {
            method: 'POST'
        });
        const data = await response.json();
        
        statusDiv.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
        statusDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <span>✅</span>
                <div>
                    <div style="font-weight: 600; margin-bottom: 4px;">Обробка запущена</div>
                    <div style="font-size: 0.9rem; opacity: 0.9;">${data.message}</div>
                </div>
            </div>
        `;
        
        setTimeout(() => {
            statusDiv.remove();
            loadActs();
        }, 3000);
    } catch (error) {
        console.error('Error processing act:', error);
        statusDiv.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
        statusDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <span>❌</span>
                <div style="font-weight: 600;">Помилка при запуску обробки</div>
            </div>
        `;
        setTimeout(() => statusDiv.remove(), 5000);
    }
}

// Process new act
async function processNewAct() {
    const nreg = document.getElementById('nreg-input').value.trim();
    if (!nreg) {
        alert('Введіть номер реєстрації');
        return;
    }

    const statusDiv = document.getElementById('process-status');
    statusDiv.classList.add('active', 'info');
    statusDiv.innerHTML = '<div style="display: flex; align-items: center; gap: 8px;"><span>🔍</span> Перевірка акту на сайті data.rada.gov.ua...</div>';

    // First check if act exists
    const checkResult = await checkActExists(nreg);
    
    if (!checkResult.exists) {
        statusDiv.classList.remove('info');
        statusDiv.classList.add('error');
        statusDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <span>❌</span>
                <div>
                    <div style="font-weight: 600; margin-bottom: 4px;">Акт не знайдено</div>
                    <div style="font-size: 0.9rem; opacity: 0.9;">${checkResult.message}</div>
                </div>
            </div>
        `;
        return;
    }
    
    statusDiv.classList.remove('error');
    statusDiv.classList.add('info');
    statusDiv.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px;">
            <span>✅</span>
            <div>
                <div style="font-weight: 600; margin-bottom: 4px;">Акт знайдено!</div>
                <div style="font-size: 0.9rem; opacity: 0.9;">${checkResult.title || nreg}</div>
                <div style="font-size: 0.85rem; margin-top: 8px; opacity: 0.8;">Запуск обробки...</div>
            </div>
        </div>
    `;

    try {
        // Encode NREG but preserve / characters for path segments
        const encodedNreg = nreg.split('/').map(part => encodeURIComponent(part)).join('/');
        const response = await fetch(`${API_BASE}/legal-acts/${encodedNreg}/process`, {
            method: 'POST'
        });
        const data = await response.json();
        
        statusDiv.classList.remove('info');
        statusDiv.classList.add('success');
        statusDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <span>✅</span>
                <div>
                    <div style="font-weight: 600; margin-bottom: 4px;">Обробка запущена</div>
                    <div style="font-size: 0.9rem; opacity: 0.9;">${data.message}</div>
                </div>
            </div>
        `;
        
        document.getElementById('nreg-input').value = '';
        
        setTimeout(() => {
            closeProcessModal();
            loadActs();
        }, 2000);
    } catch (error) {
        console.error('Error processing act:', error);
        statusDiv.classList.remove('info');
        statusDiv.classList.add('error');
        const errorMsg = error.message || 'Невідома помилка';
        statusDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <span>❌</span>
                <div>
                    <div style="font-weight: 600; margin-bottom: 4px;">Помилка при запуску обробки</div>
                    <div style="font-size: 0.9rem; opacity: 0.9;">${errorMsg}</div>
                </div>
            </div>
        `;
    }
}

// Close modals
function closeDetailsModal() {
    document.getElementById('details-modal').classList.remove('active');
}

function closeProcessModal() {
    document.getElementById('process-modal').classList.remove('active');
    document.getElementById('process-status').classList.remove('active', 'success', 'error', 'info');
    document.getElementById('nreg-input').value = '';
}

// Switch tabs
function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
    document.getElementById(`${tab}-tab`).classList.add('active');
    
    // Load database schema when switching to database tab
    if (tab === 'database') {
        loadDatabaseSchema();
    }
    
    // Load Rada list when switching to rada-list tab
    if (tab === 'rada-list') {
        loadRadaActsList(true);
        // Start auto-refresh when tab is active
        if (!radaListRefreshInterval) {
            radaListRefreshInterval = setInterval(() => {
                loadRadaActsList(false); // Don't reset, just update
            }, 10000); // Refresh every 10 seconds
        }
    } else {
        // Stop auto-refresh when tab is not active
        if (radaListRefreshInterval) {
            clearInterval(radaListRefreshInterval);
            radaListRefreshInterval = null;
        }
    }
}

// Get status icon
function getStatusIcon(status) {
    const statusLower = status.toLowerCase();
    if (statusLower.includes('діє') || statusLower.includes('чинний')) return '✅';
    if (statusLower.includes('втрат') || statusLower.includes('недійсн')) return '❌';
    if (statusLower.includes('змін')) return '🔄';
    return '📋';
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Download active acts function
async function downloadActiveActs(process = false) {
    const btn = process 
        ? document.getElementById('download-active-and-process-btn')
        : document.getElementById('download-active-acts-btn');
    
    if (!btn) {
        console.error('Download active acts button not found!');
        return;
    }
    
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span>⏳</span> Запуск...';
    
    // Show progress bar
    const progressContainer = document.getElementById('download-progress-container');
    const progressBar = document.getElementById('progress-bar-fill');
    const progressText = document.getElementById('progress-text');
    const progressPercent = document.getElementById('progress-percent');
    const progressDetails = document.getElementById('progress-details');
    
    if (progressContainer) {
        progressContainer.style.display = 'block';
        progressBar.style.width = '0%';
        progressPercent.textContent = '0%';
        progressText.textContent = process ? 'Завантаження та обробка діючих НПА...' : 'Завантаження діючих НПА...';
        progressDetails.innerHTML = '';
    }
    
    try {
        const url = `${API_BASE}/legal-acts/download-active-acts?process=${process}`;
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        // Update progress
        if (progressContainer) {
            progressText.textContent = data.message || 'Завантаження запущено в фоновому режимі';
            progressBar.style.width = '10%';
            progressPercent.textContent = '10%';
            progressDetails.innerHTML = '<p>⏳ Завантаження почалося. Перевіряйте прогрес нижче...</p>';
        }
        
        // Start polling for progress
        startProgressPolling();
        
        // Refresh list after a delay
        setTimeout(() => {
            loadRadaActsList(true);
        }, 2000);
        
    } catch (error) {
        console.error('Error downloading active acts:', error);
        if (progressContainer) {
            progressText.textContent = `❌ Помилка: ${error.message}`;
            progressBar.style.width = '0%';
        }
        showNotification('error', `❌ Помилка: ${error.message}`, 5000);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// Poll for download progress
let progressPollingInterval = null;
function startProgressPolling() {
    // Clear existing interval
    if (progressPollingInterval) {
        clearInterval(progressPollingInterval);
    }
    
    // Poll every 5 seconds
    progressPollingInterval = setInterval(async () => {
        try {
            // Get current stats
            const statsResponse = await fetch(`${API_BASE}/legal-acts/rada-list?skip=0&limit=1`);
            if (statsResponse.ok) {
                const stats = await statsResponse.json();
                updateProgressBar(stats);
            }
        } catch (error) {
            console.error('Error polling progress:', error);
        }
    }, 5000);
    
    // Stop polling after 10 minutes
    setTimeout(() => {
        if (progressPollingInterval) {
            clearInterval(progressPollingInterval);
            progressPollingInterval = null;
        }
    }, 600000);
}

// Update progress bar based on stats
function updateProgressBar(stats) {
    const progressBar = document.getElementById('progress-bar-fill');
    const progressPercent = document.getElementById('progress-percent');
    const progressText = document.getElementById('progress-text');
    const progressDetails = document.getElementById('progress-details');
    
    if (!progressBar || !stats) return;
    
    const total = stats.total || 0;
    const loaded = stats.loaded || 0;
    const processed = stats.processed || 0;
    
    if (total > 0) {
        const loadedPercent = Math.round((loaded / total) * 100);
        const processedPercent = Math.round((processed / total) * 100);
        
        progressBar.style.width = `${loadedPercent}%`;
        progressPercent.textContent = `${loadedPercent}%`;
        progressText.textContent = `Завантажено: ${loaded} / ${total} НПА`;
        
        progressDetails.innerHTML = `
            <div class="progress-stats">
                <div class="progress-stat-item">
                    <span>Всього:</span>
                    <strong>${total}</strong>
                </div>
                <div class="progress-stat-item">
                    <span>Завантажено:</span>
                    <strong style="color: var(--success)">${loaded}</strong>
                </div>
                <div class="progress-stat-item">
                    <span>Оброблено:</span>
                    <strong style="color: var(--primary)">${processed}</strong>
                </div>
                <div class="progress-stat-item">
                    <span>Не завантажено:</span>
                    <strong style="color: var(--warning)">${total - loaded}</strong>
                </div>
            </div>
        `;
        
        // Hide progress bar when complete
        if (loaded >= total) {
            setTimeout(() => {
                const progressContainer = document.getElementById('download-progress-container');
                if (progressContainer) {
                    progressContainer.style.display = 'none';
                }
                if (progressPollingInterval) {
                    clearInterval(progressPollingInterval);
                    progressPollingInterval = null;
                }
            }, 5000);
        }
    }
}

// Auto-download function
async function startAutoDownload() {
    const btn = document.getElementById('auto-download-btn');
    const originalText = btn.innerHTML;
    
    // Disable button
    btn.disabled = true;
    btn.innerHTML = '<span>⏳</span> Завантаження...';
    
    try {
        const response = await fetch(`${API_BASE}/legal-acts/auto-download?count=10`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        // Show success message
        showNotification('success', `✅ Автозавантаження запущено! Буде оброблено ${data.count} документів у порядку з сайту Rada.`, 5000);
        
        // Refresh acts list after a delay
        setTimeout(() => {
            loadActs();
            loadStats();
        }, 3000);
        
    } catch (error) {
        console.error('Error starting auto-download:', error);
        showNotification('error', `❌ Помилка: ${error.message}`, 5000);
    } finally {
        // Re-enable button after delay
        setTimeout(() => {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }, 2000);
    }
}

// Show notification
function showNotification(type, message, duration = 3000) {
    // Remove existing notifications
    const existing = document.querySelectorAll('.notification');
    existing.forEach(n => n.remove());
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        background: ${type === 'success' ? '#10b981' : '#ef4444'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        z-index: 10000;
        max-width: 400px;
        animation: slideIn 0.3s ease-out;
        font-size: 14px;
        line-height: 1.5;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Remove after duration
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, duration);
}

// Add CSS for notification animation
if (!document.getElementById('notification-styles')) {
    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}

// Load database schema
async function loadDatabaseSchema() {
    const container = document.getElementById('database-schema');
    container.innerHTML = '<p class="loading">Завантаження схеми бази даних...</p>';
    
    try {
        const response = await fetch(`${API_BASE}/status/database-schema`);
        const data = await response.json();
        
        if (data.error) {
            container.innerHTML = `<div class="error-state">Помилка: ${escapeHtml(data.error)}</div>`;
            return;
        }
        
        renderDatabaseSchema(data);
    } catch (error) {
        console.error('Error loading database schema:', error);
        container.innerHTML = `<div class="error-state">Помилка завантаження схеми: ${escapeHtml(error.message)}</div>`;
    }
}

// Render database schema
function renderDatabaseSchema(data) {
    const container = document.getElementById('database-schema');
    
    let html = `
        <div class="db-schema-header">
            <h2>🗄️ Схема бази даних</h2>
            <div class="db-info">
                <span class="db-type">Тип: ${escapeHtml(data.database_type || 'unknown')}</span>
                <span class="db-tables-count">Таблиць: ${data.tables?.length || 0}</span>
            </div>
        </div>
        
        <div class="db-stats-overview">
            <h3>📊 Загальна статистика</h3>
            <div class="stats-grid">
    `;
    
    // Add relationship stats
    if (data.relationships) {
        html += `
            <div class="stat-card">
                <div class="stat-label">Зв'язки Категорія → Підмножина</div>
                <div class="stat-value">${data.relationships.category_to_subset || 0}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Зв'язки Підмножина → Акт</div>
                <div class="stat-value">${data.relationships.subset_to_act || 0}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Зв'язки Акт → Категорія</div>
                <div class="stat-value">${data.relationships.act_to_category || 0}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Зв'язки Акт → Акт</div>
                <div class="stat-value">${data.relationships.act_to_act || 0}</div>
            </div>
        `;
    }
    
    html += `</div></div>`;
    
    // Render each table
    if (data.tables && data.tables.length > 0) {
        html += '<div class="tables-section"><h3>📋 Таблиці</h3>';
        
        for (const tableName of data.tables) {
            const schema = data.schemas[tableName] || {};
            const stats = data.statistics[tableName] || {};
            
            html += `
                <div class="table-card">
                    <div class="table-header">
                        <h4>${escapeHtml(tableName)}</h4>
                        ${stats.count !== undefined ? `<span class="table-count">${stats.count} записів</span>` : ''}
                    </div>
                    
                    ${stats.error ? `
                        <div class="error-message">Помилка: ${escapeHtml(stats.error)}</div>
                    ` : ''}
                    
                    ${stats.processed !== undefined ? `
                        <div class="table-stats">
                            <span>Оброблено: ${stats.processed}</span>
                            <span>Не оброблено: ${stats.not_processed || 0}</span>
                            ${stats.with_text !== undefined ? `<span>З текстом: ${stats.with_text}</span>` : ''}
                            ${stats.with_embeddings !== undefined ? `<span>З embeddings: ${stats.with_embeddings}</span>` : ''}
                        </div>
                    ` : ''}
                    
                    ${stats.by_type ? `
                        <div class="relation-types">
                            <strong>Типи зв'язків:</strong>
                            ${Object.entries(stats.by_type).map(([type, count]) => 
                                `<span class="relation-type-badge">${escapeHtml(type)}: ${count}</span>`
                            ).join('')}
                        </div>
                    ` : ''}
                    
                    <div class="table-schema">
                        <h5>Колонки:</h5>
                        <table class="schema-table">
                            <thead>
                                <tr>
                                    <th>Назва</th>
                                    <th>Тип</th>
                                    <th>Nullable</th>
                                    <th>Default</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${(schema.columns || []).map(col => `
                                    <tr>
                                        <td><code>${escapeHtml(col.name)}</code></td>
                                        <td><span class="type-badge">${escapeHtml(col.type)}</span></td>
                                        <td>${col.nullable ? '✅' : '❌'}</td>
                                        <td>${col.default ? `<code>${escapeHtml(col.default)}</code>` : '-'}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                    
                    ${(schema.foreign_keys || []).length > 0 ? `
                        <div class="foreign-keys">
                            <h5>Зовнішні ключі:</h5>
                            <ul>
                                ${schema.foreign_keys.map(fk => `
                                    <li>
                                        <code>${escapeHtml(fk.constrained_columns.join(', '))}</code> 
                                        → <code>${escapeHtml(fk.referred_table)}.${escapeHtml(fk.referred_columns.join(', '))}</code>
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                    ` : ''}
                    
                    ${(schema.indexes || []).length > 0 ? `
                        <div class="indexes">
                            <h5>Індекси:</h5>
                            <ul>
                                ${schema.indexes.map(idx => `
                                    <li>
                                        <code>${escapeHtml(idx.name)}</code> 
                                        на <code>${escapeHtml(idx.columns.join(', '))}</code>
                                        ${idx.unique ? '<span class="unique-badge">UNIQUE</span>' : ''}
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                    ` : ''}
                    
                    ${stats.sample && stats.sample.length > 0 ? `
                        <div class="sample-data">
                            <h5>Приклад даних (${stats.sample.length} записів):</h5>
                            <pre class="sample-json">${JSON.stringify(stats.sample, null, 2)}</pre>
                        </div>
                    ` : ''}
                </div>
            `;
        }
        
        html += '</div>';
    }
    
    container.innerHTML = html;
}

// Make functions available globally
window.showActDetails = showActDetails;
window.processAct = processAct;
window.checkActOnRada = checkActOnRada;
