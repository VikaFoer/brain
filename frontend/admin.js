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
    
    // Render all acts
    listContainer.innerHTML = radaActsList.map(act => {
        const statusClass = act.status === 'processed' ? 'status-processed' 
            : act.status === 'loaded' ? 'status-loaded' 
            : 'status-not-loaded';
        const statusIcon = act.status === 'processed' ? '✅' 
            : act.status === 'loaded' ? '📥' 
            : '⭕';
        const statusText = act.status === 'processed' ? 'Оброблено' 
            : act.status === 'loaded' ? 'Завантажено' 
            : 'Не завантажено';
        
        return `
            <div class="rada-act-item ${statusClass}">
                <div class="rada-act-info">
                    <div class="rada-act-nreg">${escapeHtml(act.nreg)}</div>
                    ${act.title && act.title !== act.nreg ? `
                        <div class="rada-act-title">${escapeHtml(act.title)}</div>
                    ` : ''}
                </div>
                <div class="rada-act-status">
                    <span class="status-icon">${statusIcon}</span>
                    <span class="status-text">${statusText}</span>
                </div>
                ${act.status !== 'processed' ? `
                    <button class="btn btn-sm btn-success process-act-btn" data-nreg="${escapeHtml(act.nreg)}">
                        <span>⚙️</span> Опрацювати
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
    // First check if act exists
    const statusDiv = document.createElement('div');
    statusDiv.className = 'status-message';
    statusDiv.style.cssText = 'position: fixed; top: 20px; right: 20px; padding: 16px; border-radius: 8px; z-index: 10000; max-width: 400px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);';
    statusDiv.innerHTML = '<div style="display: flex; align-items: center; gap: 8px;"><span>🔍</span> Перевірка акту на сайті data.rada.gov.ua...</div>';
    document.body.appendChild(statusDiv);
    
    const checkResult = await checkActExists(nreg);
    
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

// Make functions available globally
window.showActDetails = showActDetails;
window.processAct = processAct;
window.checkActOnRada = checkActOnRada;
