// API base URL
const API_BASE = 'http://localhost:8000/api';

// State
let categories = [];
let selectedCategories = [];
let graphData = null;
let simulation = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadCategories();
    setupEventListeners();
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
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
    document.getElementById(`${tab}-tab`).classList.add('active');

    // Enable/disable chat input based on selection
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    
    if (tab === 'chat') {
        chatInput.disabled = selectedCategories.length === 0;
        sendBtn.disabled = selectedCategories.length === 0;
    }
}

// Send chat message
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const question = input.value.trim();

    if (!question || selectedCategories.length === 0) return;

    // Add user message to chat
    addChatMessage('user', question);
    input.value = '';

    // Show loading
    const loadingId = addChatMessage('assistant', 'Обробка запиту...');

    try {
        const response = await fetch(`${API_BASE}/chat/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: question,
                category_ids: selectedCategories,
                context_type: 'relations'
            })
        });

        const data = await response.json();

        // Remove loading message
        document.getElementById(loadingId).remove();

        // Add assistant response
        addChatMessage('assistant', data.answer);
    } catch (error) {
        console.error('Error sending message:', error);
        document.getElementById(loadingId).remove();
        addChatMessage('assistant', 'Вибачте, сталася помилка при обробці запиту.');
    }
}

// Add chat message
function addChatMessage(role, text) {
    const container = document.getElementById('chat-messages');
    const messageId = `msg-${Date.now()}`;
    const time = new Date().toLocaleTimeString('uk-UA');

    const messageDiv = document.createElement('div');
    messageDiv.id = messageId;
    messageDiv.className = `message ${role}`;
    messageDiv.innerHTML = `
        <div>${text}</div>
        <div class="message-time">${time}</div>
    `;

    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;

    return messageId;
}

// Make toggleCategory available globally
window.toggleCategory = toggleCategory;

