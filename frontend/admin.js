// API base URL
const API_BASE = window.location.hostname.includes('railway') 
    ? `${window.location.protocol}//${window.location.host}/api`
    : 'http://localhost:8000/api';

// State
let acts = [];
let categories = [];
let filteredActs = [];

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
        statusDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <span>❌</span>
                <div style="font-weight: 600;">Помилка при запуску обробки</div>
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

// Make functions available globally
window.showActDetails = showActDetails;
window.processAct = processAct;
