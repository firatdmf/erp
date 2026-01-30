
// Menu Data
const MENU_ITEMS = [
    { name: 'Dashboard', url: '/dashboard/', icon: 'fa-chart-line', category: 'General' },
    { name: 'Reports', url: '/reports/', icon: 'fa-paste', category: 'General' },
    { name: 'Settings', url: '/settings/', icon: 'fa-cog', category: 'General' },
    { name: 'Contact List', url: '/crm/contacts/', icon: 'fa-users', category: 'CRM' },
    { name: 'Company List', url: '/crm/companies/', icon: 'fa-building', category: 'CRM' },
    { name: 'Create Contact', url: '/crm/add_contact/', icon: 'fa-user-plus', category: 'CRM' },
    { name: 'Product List', url: '/marketing/product_list/', icon: 'fa-box', category: 'Marketing' },
    { name: 'Create Product', url: '/marketing/product_create/', icon: 'fa-plus-square', category: 'Marketing' },
    { name: 'Blog List', url: '/marketing/blog_list/', icon: 'fa-newspaper', category: 'Marketing' },
    { name: 'Order List', url: '/operating/orders/', icon: 'fa-shopping-cart', category: 'Operating' },
    { name: 'Create Order', url: '/operating/orders/create', icon: 'fa-cart-plus', category: 'Operating' },
    { name: 'QR Scan', url: '/operating/scan_order_item_unit/', icon: 'fa-qrcode', category: 'Operating' },
    { name: 'Accounting Books', url: '/accounting/', icon: 'fa-book', category: 'Accounting' },
    { name: 'Sales Dashboard', url: '/accounting/reports/sales_dashboard/', icon: 'fa-chart-bar', category: 'Accounting' },
    { name: 'Task List', url: '/todo/tasks/', icon: 'fa-check-circle', category: 'Todo' },
];

let searchTimeout;
let currentTab = 'all';

function openSearchSidebar() {
    document.getElementById('searchSidebar').classList.add('active');
    setTimeout(() => document.getElementById('globalSearchInput').focus(), 100);
    document.body.style.overflow = 'hidden';
    switchTab('all');
}

function closeSearchSidebar() {
    document.getElementById('searchSidebar').classList.remove('active');
    document.body.style.overflow = '';
}

function clearSearch() {
    const input = document.getElementById('globalSearchInput');
    input.value = '';
    input.focus();
    handleSearch('');
    document.getElementById('clearSearchBtn').classList.add('hidden');
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-item').forEach(el => {
        el.classList.toggle('active', el.dataset.tab === tabName);
    });
    currentTab = tabName;

    // Re-trigger search with new tab context
    const query = document.getElementById('globalSearchInput').value.trim();
    handleSearch(query);
}

document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('globalSearchInput');

    input.addEventListener('input', function (e) {
        const query = e.target.value.trim();
        document.getElementById('clearSearchBtn').classList.toggle('hidden', !query);

        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => handleSearch(query), 300);
    });

    // Keyboard
    document.addEventListener('keydown', function (e) {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            const sidebar = document.getElementById('searchSidebar');
            sidebar.classList.contains('active') ? closeSearchSidebar() : openSearchSidebar();
        }
        if (e.key === 'Escape') closeSearchSidebar();
    });
});

async function handleSearch(query) {
    const container = document.getElementById('searchResults');
    const defaultState = document.getElementById('defaultState');
    const loading = document.getElementById('loadingSpinner');

    // State 1: Empty Query
    if (query.length < 2) {

        // Check if we need to fetch "recent" for specific tabs (Products/Orders)
        if (currentTab === 'products' || currentTab === 'orders') {
            loading.classList.remove('hidden');
            defaultState.style.display = 'none';
            container.innerHTML = '';

            try {
                const res = await fetch(`/search/?q=&type=${currentTab}`);
                const data = await res.json();
                const dbResults = data.results || [];
                renderSearchResults(container, [], dbResults);
            } catch (e) {
                console.error(e);
            }
            loading.classList.add('hidden');
            return;
        }

        loading.classList.add('hidden');
        defaultState.style.display = 'none'; // Hide by default
        container.innerHTML = ''; // Clear results

        // A. Menu Tab: Show All Menu Items
        if (currentTab === 'menu') {
            renderBrowseMenu(container);
            return;
        }

        // B. Other Tabs: Show filtered recent activity
        // We filter the #defaultState DOM elements based on tab
        defaultState.style.display = 'block';
        const recentItems = document.querySelectorAll('#defaultState .result-card');
        let hasCount = 0;

        recentItems.forEach(item => {
            const type = item.dataset.type; // 'Contact', 'Company'
            let show = false;

            if (currentTab === 'all' || currentTab === 'recent') show = true;
            else if (currentTab === 'contacts' && (type === 'Contact' || type === 'Company')) show = true;
            // Add filtering for other types if they were in the recent list

            item.style.display = show ? 'flex' : 'none';
            if (show) hasCount++;
        });

        if (hasCount === 0 && currentTab !== 'all' && currentTab !== 'recent') {
            container.innerHTML = `<div style="padding: 2rem; text-align: center; color: #94a3b8;">No recent items in this section.</div>`;
            defaultState.style.display = 'none';
        }
        return;
    }

    // State 2: Active Search
    defaultState.style.display = 'none';
    loading.classList.remove('hidden');
    container.innerHTML = '';

    // 1. Menu Search (Local)
    let menuResults = [];
    if (currentTab === 'all' || currentTab === 'menu') {
        menuResults = MENU_ITEMS.filter(item =>
            item.name.toLowerCase().includes(query.toLowerCase()) ||
            item.category.toLowerCase().includes(query.toLowerCase())
        );
    }

    // 2. DB Search (Backend)
    let dbResults = [];
    try {
        // Pass the tab as 'type' to backend
        const res = await fetch(`/search/?q=${encodeURIComponent(query)}&type=${currentTab}`);
        const data = await res.json();
        dbResults = data.results || [];
    } catch (e) {
        console.error(e);
    }

    renderSearchResults(container, menuResults, dbResults);
    loading.classList.add('hidden');
}

function renderBrowseMenu(container) {
    let html = `<div class="result-section"><div class="section-title"><i class="fas fa-compass"></i> All Pages</div>`;
    MENU_ITEMS.forEach(item => {
        html += renderCard(item.name, item.category, item.url, item.icon, 'menu');
    });
    html += `</div>`;
    container.innerHTML = html;
}

function renderSearchResults(container, menu, db) {
    let html = '';

    // Render Menu (if any)
    if (menu.length > 0) {
        html += `<div class="result-section"><div class="section-title"><i class="fas fa-compass"></i> Navigation</div>`;
        menu.forEach(item => {
            html += renderCard(item.name, item.category, item.url, item.icon, 'menu');
        });
        html += `</div>`;
    }

    // Render DB items grouped
    const grouped = db.reduce((acc, item) => {
        if (!acc[item.type]) acc[item.type] = [];
        acc[item.type].push(item);
        return acc;
    }, {});

    for (const [type, items] of Object.entries(grouped)) {
        let icon = 'fa-circle';
        if (type === 'Contact') icon = 'fa-user';
        if (type === 'Company') icon = 'fa-building';
        if (type === 'Product') icon = 'fa-box';
        if (type === 'Order') icon = 'fa-shopping-cart';
        if (type === 'Task') icon = 'fa-check';

        html += `<div class="result-section"><div class="section-title"><i class="fas ${icon}"></i> ${type}s</div>`;
        items.forEach(item => {
            html += renderCard(item.name, item.detail, item.url, item.icon, type.toLowerCase());
        });
        html += `</div>`;
    }

    if (html === '') {
        html = `<div style="padding: 2rem; text-align: center; color: #94a3b8;">No results found.</div>`;
    }

    container.innerHTML = html;
}

function renderCard(title, subtitle, url, icon, type) {
    let iconClass = type;
    return `
    <div class="result-card" onclick="window.location.href='${url}'">
        <div class="result-icon ${iconClass}">
            <i class="fas ${icon}"></i>
        </div>
        <div class="result-info">
            <span class="result-name">${title}</span>
            <span class="result-meta">${subtitle}</span>
        </div>
    </div>
    `;
}
