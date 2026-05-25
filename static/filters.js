/* filters.js — Filter UI and scheduling functions */

let changeTimeout;
let searchTimeout;

export function toggleFutureWindow(pill) {
    const nowOn = pill.getAttribute('data-on') !== 'true';
    pill.setAttribute('data-on', nowOn);
    pill.querySelector('.pill-label').textContent = nowOn ? 'On' : 'Off';
    const futureItem = document.getElementById('future-window-item');
    if (futureItem) {
        futureItem.setAttribute('data-visible', nowOn);
    }
    window.applyFilters({ keepPage: true });
}

export function toggleNewPlayers(pill) {
    const nowOn = pill.getAttribute('data-on') !== 'true';
    pill.setAttribute('data-on', nowOn);
    pill.querySelector('.pill-label').textContent = nowOn ? 'On' : 'Off';
    window.applyFilters();
}

export function updateLabel(id, text) {
    document.getElementById(id).textContent = text;
}

export function updateGamesLabel(value, maxGames) {
    const suffix = value == 1 ? ' Game' : ' Games';
    const all = value == maxGames ? ' (All)' : '';
    updateLabel('games-value', value + suffix + all);
}

export function scheduleApply() {
    clearTimeout(changeTimeout);
    changeTimeout = setTimeout(() => window.applyFilters(), 500); // Keep 500ms for non-search filters
}

export function scheduleSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        window.applyFilters();  // Use full-page navigation so server handles pagination
    }, 600);
}
