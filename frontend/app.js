// API base URL
// Автоматично визначає URL: якщо на Railway - використовує поточний домен, інакше localhost
const API_BASE = window.location.hostname.includes('railway') 
    ? `${window.location.protocol}//${window.location.host}/api`
    : 'http://localhost:8000/api';

// State
let categories = [];
let selectedCategories = [];
let graphData = null;
let simulation = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing app...');
    loadCategories();
    setupEventListeners();
    
    // Ensure chat tab is accessible
    const chatTab = document.getElementById('chat-tab');
    const chatBtn = document.querySelector('[data-tab="chat"]');
    if (chatTab && chatBtn) {
        console.log('Chat tab and button found');
    } else {
        console.error('Chat tab or button not found!', { chatTab, chatBtn });
    }
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

    // Load graph button
    document.getElementById('load-graph-btn').addEventListener('click', loadGraph);

    // Depth slider
    const depthSlider = document.getElementById('depth-slider');
    depthSlider.addEventListener('input', (e) => {
        document.getElementById('depth-value').textContent = e.target.value;
    });

    // Chat input
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');

    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    sendBtn.addEventListener('click', sendMessage);
}

// Load categories
async function loadCategories() {
    try {
        const response = await fetch(`${API_BASE}/categories/`);
        categories = await response.json();
        renderCategories();
    } catch (error) {
        console.error('Error loading categories:', error);
        document.getElementById('category-list').innerHTML = 
            '<p class="loading">Помилка завантаження категорій</p>';
    }
}

// Render categories
function renderCategories() {
    const container = document.getElementById('category-list');
    
    if (categories.length === 0) {
        container.innerHTML = '<p class="loading">Категорії не знайдено</p>';
        return;
    }

    container.innerHTML = categories.map(cat => `
        <div class="category-item ${selectedCategories.includes(cat.id) ? 'selected' : ''}">
            <label>
                <input 
                    type="checkbox" 
                    value="${cat.id}"
                    ${selectedCategories.includes(cat.id) ? 'checked' : ''}
                    onchange="toggleCategory(${cat.id})"
                >
                <span class="category-name">${cat.name}</span>
                <span class="category-count">(${cat.element_count})</span>
            </label>
        </div>
    `).join('');

    updateLoadButton();
}

// Toggle category selection
function toggleCategory(categoryId) {
    const index = selectedCategories.indexOf(categoryId);
    if (index > -1) {
        selectedCategories.splice(index, 1);
    } else {
        selectedCategories.push(categoryId);
    }
    renderCategories();
    updateLoadButton();
}

// Update load button state
function updateLoadButton() {
    const btn = document.getElementById('load-graph-btn');
    btn.disabled = selectedCategories.length === 0;
}

// Load graph
async function loadGraph() {
    if (selectedCategories.length === 0) return;

    const depth = parseInt(document.getElementById('depth-slider').value);
    const btn = document.getElementById('load-graph-btn');
    btn.disabled = true;
    btn.textContent = 'Завантаження...';

    try {
        const categoryIds = selectedCategories.join(',');
        const response = await fetch(
            `${API_BASE}/graph/categories?category_ids=${categoryIds}&depth=${depth}`
        );
        graphData = await response.json();
        renderGraph();
        loadStatistics();
    } catch (error) {
        console.error('Error loading graph:', error);
        alert('Помилка завантаження графа');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Побудувати граф';
    }
}

// Render graph using D3.js
function renderGraph() {
    const svg = d3.select('#graph-svg');
    svg.selectAll('*').remove();

    if (!graphData || graphData.nodes.length === 0) {
        document.getElementById('graph-info').innerHTML = 
            '<p>Граф порожній або дані не знайдено</p>';
        return;
    }

    document.getElementById('graph-info').innerHTML = '';

    const width = svg.node().getBoundingClientRect().width;
    const height = svg.node().getBoundingClientRect().height;

    // Create force simulation
    simulation = d3.forceSimulation(graphData.nodes)
        .force('link', d3.forceLink(graphData.edges).id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(30));

    // Create links
    const link = svg.append('g')
        .selectAll('line')
        .data(graphData.edges)
        .enter()
        .append('line')
        .attr('class', 'link')
        .attr('stroke-width', 2);

    // Create nodes
    const node = svg.append('g')
        .selectAll('g')
        .data(graphData.nodes)
        .enter()
        .append('g')
        .attr('class', 'node')
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));

    // Add circles to nodes
    node.append('circle')
        .attr('r', d => {
            if (d.label === 'Category') return 15;
            if (d.label === 'Subset') return 10;
            return 8;
        })
        .attr('fill', d => {
            if (d.label === 'Category') return '#2563eb';
            if (d.label === 'Subset') return '#10b981';
            return '#64748b';
        });

    // Add labels
    node.append('text')
        .text(d => d.properties.name || d.properties.title || d.id)
        .attr('dx', 20)
        .attr('dy', 5)
        .attr('font-size', '12px')
        .attr('fill', '#1e293b');

    // Update positions on simulation tick
    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);

        node
            .attr('transform', d => `translate(${d.x},${d.y})`);
    });
}

// Drag handlers
function dragstarted(event) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    event.subject.fx = event.subject.x;
    event.subject.fy = event.subject.y;
}

function dragged(event) {
    event.subject.fx = event.x;
    event.subject.fy = event.y;
}

function dragended(event) {
    if (!event.active) simulation.alphaTarget(0);
    event.subject.fx = null;
    event.subject.fy = null;
}

// Load statistics
async function loadStatistics() {
    try {
        const response = await fetch(`${API_BASE}/graph/statistics`);
        const data = await response.json();
        renderStatistics(data.statistics);
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// Render statistics
function renderStatistics(stats) {
    const container = document.getElementById('stats-content');
    
    if (!stats || stats.length === 0) {
        container.innerHTML = '<p>Статистика недоступна</p>';
        return;
    }

    // Filter by selected categories
    const selectedStats = stats.filter(s => selectedCategories.includes(s.id));
    
    container.innerHTML = selectedStats.map(stat => `
        <div class="stat-item">
            <div class="stat-label">${stat.name}</div>
            <div class="stat-value">
                Актів: ${stat.act_count || 0} | Підмножин: ${stat.subset_count || 0}
            </div>
        </div>
    `).join('');
}

// Switch tabs
function switchTab(tab) {
    console.log('Switching to tab:', tab);
    
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    const tabBtn = document.querySelector(`[data-tab="${tab}"]`);
    const tabContent = document.getElementById(`${tab}-tab`);
    
    if (tabBtn && tabContent) {
        tabBtn.classList.add('active');
        tabContent.classList.add('active');
        console.log('Tab switched successfully');
    } else {
        console.error('Tab elements not found!', { tabBtn, tabContent, tab });
    }

    // Enable/disable chat input based on selection
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    
    if (tab === 'chat') {
        // Chat is always enabled now - can ask general questions
        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.placeholder = "Задайте питання про акти, категорії, зв'язки...";
        
        // Show welcome message if chat is empty
        const chatMessages = document.getElementById('chat-messages');
        if (chatMessages && chatMessages.children.length === 0) {
            addChatMessage('assistant', 'Привіт! Я допоможу вам з аналізом нормативно-правових актів. Задайте питання про акти, категорії, зв\'язки або статистику бази даних.');
        }
    }
}

// Chat conversation history
let chatHistory = [];

// Send chat message
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const question = input.value.trim();

    if (!question) return;

    // Add user message to chat
    addChatMessage('user', question);
    chatHistory.push({ role: 'user', content: question });
    input.value = '';

    // Show loading
    const loadingId = addChatMessage('assistant', 'Обробка запиту...');

    try {
        const selectedCategories = getSelectedCategories();
        const response = await fetch(`${API_BASE}/chat/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: question,
                category_ids: selectedCategories.length > 0 ? selectedCategories : null,
                context_type: 'general',
                conversation_history: chatHistory.slice(-10) // Last 10 messages for context
            })
        });

        if (response.ok) {
            const data = await response.json();
            
            // Remove loading message
            const loadingEl = document.getElementById(loadingId);
            if (loadingEl) loadingEl.remove();

            // Add assistant response to history
            chatHistory.push({ role: 'assistant', content: data.answer });
            
            // Show answer
            addChatMessage('assistant', data.answer);
            
            // Show relevant acts and categories if available
            if (data.relevant_acts && data.relevant_acts.length > 0) {
                const actsInfo = data.relevant_acts.map(act => 
                    `• ${act.title} (${act.nreg})`
                ).join('\n');
                addChatMessage('system', `Знайдені релевантні акти:\n${actsInfo}`);
            }
            
            if (data.relevant_categories && data.relevant_categories.length > 0) {
                const catsInfo = data.relevant_categories.map(cat => 
                    `• ${cat.name} (${cat.acts_count || 0} актів)`
                ).join('\n');
                addChatMessage('system', `Релевантні категорії:\n${catsInfo}`);
            }
        } else {
            const errorData = await response.json().catch(() => ({}));
            const loadingEl = document.getElementById(loadingId);
            if (loadingEl) loadingEl.remove();
            addChatMessage('assistant', errorData.detail || 'Вибачте, сталася помилка при обробці запиту.');
        }
    } catch (error) {
        console.error('Error sending message:', error);
        const loadingEl = document.getElementById(loadingId);
        if (loadingEl) loadingEl.remove();
        addChatMessage('assistant', 'Вибачте, сталася помилка при обробці запиту. Перевірте підключення до сервера.');
    }
}

// Add chat message
function addChatMessage(role, text) {
    const container = document.getElementById('chat-messages');
    const messageId = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const time = new Date().toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' });

    const messageDiv = document.createElement('div');
    messageDiv.id = messageId;
    messageDiv.className = `message ${role}`;
    
    // Format text with line breaks
    const formattedText = text.replace(/\n/g, '<br>');
    messageDiv.innerHTML = `
        <div>${formattedText}</div>
        <div class="message-time">${time}</div>
    `;

    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;

    return messageId;
}

// Make toggleCategory available globally
window.toggleCategory = toggleCategory;

