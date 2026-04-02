// Command Palette - Global Search Modal
// ========================================================================

const FILTER_CATEGORIES = [
    { id: 'contacts', name: 'Contacts', icon: 'fa-users' },
    { id: 'products', name: 'Products', icon: 'fa-box' },
    { id: 'orders', name: 'Orders', icon: 'fa-shopping-cart' },
    { id: 'menu', name: 'Navigation', icon: 'fa-compass' },
    { id: 'settings', name: 'Settings', icon: 'fa-cog' },
    { id: 'blogs', name: 'Blogs', icon: 'fa-newspaper' },
];

// Use MENU_ITEMS from search_sidebar.js if available, otherwise define our own
const CMD_MENU_ITEMS = (typeof MENU_ITEMS !== 'undefined') ? MENU_ITEMS : [
    { name: 'Dashboard', url: '/dashboard/', icon: 'fa-chart-line', category: 'General' },
    { name: 'Reports', url: '/reports/', icon: 'fa-paste', category: 'General' },
    { name: 'Settings', url: '/settings/', icon: 'fa-cog', category: 'General' },
    { name: 'Contact List', url: '/crm/contacts/', icon: 'fa-users', category: 'CRM' },
    { name: 'Company List', url: '/crm/companies/', icon: 'fa-building', category: 'CRM' },
    { name: 'Product List', url: '/marketing/product_list/', icon: 'fa-box', category: 'Marketing' },
    { name: 'Order List', url: '/operating/orders/', icon: 'fa-shopping-cart', category: 'Operating' },
    { name: 'Task List', url: '/todo/tasks/', icon: 'fa-check-circle', category: 'Todo' },
];

let cmdCurrentTab = 'contacts';
let cmdActiveFilter = null;
let cmdSearchTimeout;
let cmdRecentSearches = JSON.parse(localStorage.getItem('cmdRecentSearches') || '[]');

// Open/Close Search Dropdown
function openSearchDropdown() {
    const container = document.getElementById('searchContainer');
    if (!container || container.classList.contains('active')) return;

    container.classList.add('active');

    // Show recent searches
    renderCmdRecentSearches();
    renderCmdFilterMenu();

    // Add click outside listener with delay to prevent immediate trigger
    setTimeout(() => {
        document.addEventListener('click', handleOutsideClick);
    }, 10);
}

function closeSearchDropdown() {
    const container = document.getElementById('searchContainer');
    if (!container) return;

    container.classList.remove('active');
    document.removeEventListener('click', handleOutsideClick);

    // Reset state
    const input = document.getElementById('cmdSearchInput');
    if (input) input.value = '';

    const clearBtn = document.getElementById('cmdClearBtn');
    if (clearBtn) clearBtn.classList.add('hidden');

    const results = document.getElementById('cmdResultsContainer');
    if (results) results.innerHTML = '';

    const filterMenu = document.getElementById('cmdFilterMenu');
    if (filterMenu) filterMenu.classList.add('hidden');

    clearCmdFilter();
}

// Alias for compatibility
function openCommandPalette() { openSearchDropdown(); }
function closeCommandPalette() { closeSearchDropdown(); }

// Tab Management
function setCmdTab(tab) {
    cmdCurrentTab = tab;
    document.querySelectorAll('.cmd-tab').forEach(el => {
        el.classList.toggle('active', el.dataset.tab === tab);
    });

    const input = document.getElementById('cmdSearchInput');
    if (input) {
        performCmdSearch(input.value.trim());
    }
}

// Filter Management
function toggleCmdFilterMenu() {
    const filterMenu = document.getElementById('cmdFilterMenu');
    if (filterMenu) filterMenu.classList.toggle('hidden');
}

function renderCmdFilterMenu() {
    const container = document.getElementById('cmdFilterMenuList');
    if (!container) return;

    container.innerHTML = FILTER_CATEGORIES.map(cat => `
        <button class="filter-option ${cmdActiveFilter === cat.id ? 'active' : ''}" 
                onclick="applyCmdFilter('${cat.id}', '${cat.name}')">
            ${cat.name}
        </button>
    `).join('');
}

function applyCmdFilter(filterId, filterName) {
    cmdActiveFilter = filterId;

    const chipsContainer = document.getElementById('cmdFilterChips');
    if (chipsContainer) {
        chipsContainer.innerHTML = `
            <div class="filter-chip">
                <span>${filterName}</span>
                <i class="fas fa-times remove-chip" onclick="clearCmdFilter()"></i>
            </div>
        `;
    }

    const input = document.getElementById('cmdSearchInput');
    if (input) input.placeholder = `Search in ${filterName}...`;

    const filterMenu = document.getElementById('cmdFilterMenu');
    if (filterMenu) filterMenu.classList.add('hidden');

    if (input) performCmdSearch(input.value.trim());
}

function clearCmdFilter() {
    cmdActiveFilter = null;

    const chipsContainer = document.getElementById('cmdFilterChips');
    if (chipsContainer) chipsContainer.innerHTML = '';

    const input = document.getElementById('cmdSearchInput');
    if (input) input.placeholder = 'Search...';
}

// Recent Searches
function renderCmdRecentSearches() {
    const container = document.getElementById('cmdRecentList');
    const section = document.getElementById('cmdRecentSection');
    if (!container || !section) return;

    if (cmdRecentSearches.length === 0) {
        section.classList.add('hidden');
        return;
    }

    section.classList.remove('hidden');
    container.innerHTML = cmdRecentSearches.slice(0, 5).map(item => `
        <div class="recent-item" onclick="useCmdRecentSearch('${item.replace(/'/g, "\\'")}')">
            <i class="fas fa-clock"></i>
            <span>${item}</span>
        </div>
    `).join('');
}

function useCmdRecentSearch(term) {
    const input = document.getElementById('cmdSearchInput');
    if (input) {
        input.value = term;
        performCmdSearch(term);
    }
}

function addToCmdRecentSearches(term) {
    if (!term || term.length < 2) return;
    cmdRecentSearches = cmdRecentSearches.filter(s => s !== term);
    cmdRecentSearches.unshift(term);
    cmdRecentSearches = cmdRecentSearches.slice(0, 10);
    localStorage.setItem('cmdRecentSearches', JSON.stringify(cmdRecentSearches));
}

function clearCmdRecentSearches() {
    cmdRecentSearches = [];
    localStorage.removeItem('cmdRecentSearches');
    renderCmdRecentSearches();
}

// Clear search
function clearCmdSearch() {
    const input = document.getElementById('cmdSearchInput');
    if (input) {
        input.value = '';
        input.focus();
    }

    const clearBtn = document.getElementById('cmdClearBtn');
    if (clearBtn) clearBtn.classList.add('hidden');

    const results = document.getElementById('cmdResultsContainer');
    if (results) results.innerHTML = '';

    const recentSection = document.getElementById('cmdRecentSection');
    if (recentSection) recentSection.classList.remove('hidden');
}

// Search Logic
async function performCmdSearch(query) {
    const resultsContainer = document.getElementById('cmdResultsContainer');
    const recentSection = document.getElementById('cmdRecentSection');
    const emptyState = document.getElementById('cmdEmptyState');
    const filterMenu = document.getElementById('cmdFilterMenu');

    if (!resultsContainer) return;

    // Check for filter mode (starts with /)
    if (query.startsWith('/')) {
        if (filterMenu) filterMenu.classList.remove('hidden');
        if (recentSection) recentSection.classList.add('hidden');
        resultsContainer.innerHTML = '';

        const filterQuery = query.slice(1).toLowerCase();
        const filteredCategories = FILTER_CATEGORIES.filter(cat =>
            cat.name.toLowerCase().includes(filterQuery)
        );

        const filterList = document.getElementById('cmdFilterMenuList');
        if (filterList) {
            filterList.innerHTML = filteredCategories.map(cat => `
                <button class="filter-option" onclick="applyCmdFilter('${cat.id}', '${cat.name}')">
                    ${cat.name}
                </button>
            `).join('');
        }
        return;
    }

    if (filterMenu) filterMenu.classList.add('hidden');

    // Empty query - show recent
    if (query.length < 2) {
        resultsContainer.innerHTML = '';
        if (recentSection) recentSection.classList.remove('hidden');
        if (emptyState) emptyState.classList.add('hidden');
        return;
    }

    if (recentSection) recentSection.classList.add('hidden');

    // Show loading
    resultsContainer.innerHTML = `
        <div class="search-loading">
            <div class="spinner"></div>
        </div>
    `;

    let searchType = cmdActiveFilter || cmdCurrentTab;
    if (searchType === 'all') searchType = 'all';

    // Menu search (local)
    let menuResults = [];
    if (searchType === 'menu') {
        menuResults = CMD_MENU_ITEMS.filter(item =>
            item.name.toLowerCase().includes(query.toLowerCase()) ||
            item.category.toLowerCase().includes(query.toLowerCase())
        );
    }

    // API search
    let dbResults = [];
    try {
        const res = await fetch(`/search/?q=${encodeURIComponent(query)}&type=${searchType}`);
        const data = await res.json();
        dbResults = data.results || [];
    } catch (e) {
        console.error('Search error:', e);
    }

    renderCmdResults(menuResults, dbResults);
    addToCmdRecentSearches(query);
}

function renderCmdResults(menuResults, dbResults) {
    const container = document.getElementById('cmdResultsContainer');
    const emptyState = document.getElementById('cmdEmptyState');
    if (!container) return;

    let html = '';

    if (menuResults.length > 0) {
        html += `
            <div class="result-group">
                <div class="result-group-title">
                    <i class="fas fa-compass"></i> Navigation
                </div>
                ${menuResults.map(item => `
                    <div class="result-item" onclick="window.location.href='${item.url}'">
                        <div class="result-item-icon menu">
                            <i class="fas ${item.icon}"></i>
                        </div>
                        <div class="result-item-info">
                            <div class="result-item-name">${item.name}</div>
                            <div class="result-item-meta">${item.category}</div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    const grouped = dbResults.reduce((acc, item) => {
        if (!acc[item.type]) acc[item.type] = [];
        acc[item.type].push(item);
        return acc;
    }, {});

    for (const [type, items] of Object.entries(grouped)) {
        const iconMap = {
            'Contact': 'fa-user',
            'Company': 'fa-building',
            'Product': 'fa-box',
            'Order': 'fa-shopping-cart',
            'Task': 'fa-check-circle'
        };
        const icon = iconMap[type] || 'fa-circle';
        const cssClass = type.toLowerCase();

        html += `
            <div class="result-group">
                <div class="result-group-title">
                    <i class="fas ${icon}"></i> ${type}s
                </div>
                ${items.map(item => `
                    <div class="result-item" onclick="window.location.href='${item.url}'">
                        <div class="result-item-icon ${cssClass}">
                            <i class="fas ${item.icon}"></i>
                        </div>
                        <div class="result-item-info">
                            <div class="result-item-name">${item.name}</div>
                            <div class="result-item-meta">${item.detail || ''}</div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    if (html === '') {
        container.innerHTML = '';
        if (emptyState) {
            emptyState.classList.remove('hidden');
            emptyState.innerHTML = `
                <i class="fas fa-search"></i>
                <p>No results found</p>
            `;
        }
    } else {
        if (emptyState) emptyState.classList.add('hidden');
        container.innerHTML = html;
    }
}

// Handle click outside dropdown
function handleOutsideClick(e) {
    const container = document.getElementById('searchContainer');
    if (container && !container.contains(e.target)) {
        closeCommandPalette();
        document.removeEventListener('click', handleOutsideClick);
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('cmdSearchInput');

    if (input) {
        input.addEventListener('input', function (e) {
            const query = e.target.value.trim();
            const clearBtn = document.getElementById('cmdClearBtn');
            if (clearBtn) clearBtn.classList.toggle('hidden', !query);

            clearTimeout(cmdSearchTimeout);
            cmdSearchTimeout = setTimeout(() => performCmdSearch(query), 300);
        });

        input.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                closeCommandPalette();
            }
        });
    }

    // Keyboard shortcut - Ctrl+K
    document.addEventListener('keydown', function (e) {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            const dropdown = document.getElementById('searchDropdown');
            if (dropdown && dropdown.classList.contains('active')) {
                closeCommandPalette();
            } else {
                openCommandPalette();
            }
        }
    });
});
