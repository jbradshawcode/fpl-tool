/* fpl.js — all interactivity for the FPL Expected Points page
 *
 * Depends on a data-* attributes on #fpl-config in index.html.
 */

(function () {
    'use strict';

    const cfg = document.getElementById('fpl-config').dataset;
    const FPL = {
        maxGames:         parseInt(cfg.maxGames),
        selectedPosition: cfg.selectedPosition,
        sortBy:           cfg.sortBy,
        sortOrder:        cfg.sortOrder,
        page:             parseInt(cfg.page),
    };

    let changeTimeout;
    let searchTimeout;

    // ── Toggle ────────────────────────────────────────────────────────────────

    function toggleFutureWindow(pill) {
        const nowOn = pill.getAttribute('data-on') !== 'true';
        pill.setAttribute('data-on', nowOn);
        pill.querySelector('.pill-label').textContent = nowOn ? 'On' : 'Off';
        document.getElementById('future-window-item').setAttribute('data-visible', nowOn);
        applyFilters({ keepPage: true });
    }

    // ── Label helpers ─────────────────────────────────────────────────────────

    function updateLabel(id, text) {
        document.getElementById(id).textContent = text;
    }

    function updateGamesLabel(value) {
        const suffix = value == 1 ? ' Game' : ' Games';
        const all    = value == FPL.maxGames ? ' (All)' : '';
        updateLabel('games-value', value + suffix + all);
    }

    function scheduleApply() {
        clearTimeout(changeTimeout);
        changeTimeout = setTimeout(applyFilters, 500); // Keep 500ms for non-search filters
    }

    function scheduleSearch() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(function () {
            applyFilters();  // Use full-page navigation so server handles pagination
        }, 600);
    }

    // ── Build query-string from current UI state ──────────────────────────────

    function buildParams({ sort = FPL.sortBy, order = FPL.sortOrder, page = 1 } = {}) {
        const adjustOn        = document.getElementById('adjust-difficulty-toggle').getAttribute('data-on') === 'true';
        const currentPosition = document.getElementById('position-dropdown').value;
        const searchValue     = document.getElementById('search-input').value.trim();

        const params = new URLSearchParams({
            position:          currentPosition,
            team:              document.getElementById('team-dropdown').value,
            mins:              document.getElementById('mins-slider').value,
            games:             document.getElementById('games-slider').value,
            adjust_difficulty: adjustOn,
            horizon:           document.getElementById('future-slider').value,
            sort,
            order,
            page,
        });

        // Only add search parameter if it has a value
        if (searchValue) {
            params.set('search', searchValue);
        }

        // Only omit price_max when the position has changed — the backend will
        // then reset it to the new position's maximum automatically.
        const positionChanged = currentPosition !== FPL.selectedPosition;
        if (!positionChanged) {
            params.set('price_max', parseFloat(document.getElementById('price-slider').value).toFixed(1));
        }

        return params;
    }

    // ── Navigate ──────────────────────────────────────────────────────────────

    function applyFilters({ keepPage = false } = {}) {
        clearTimeout(changeTimeout);
        const page = keepPage ? FPL.page : 1;
        window.location.href = '/?' + buildParams({ page }).toString();
    }

    function sortTable(column) {
        let newSort  = column;
        let newOrder = 'desc';

        if (FPL.sortBy === column) {
            if (FPL.sortOrder === 'desc') {
                newOrder = 'asc';
            } else {
                // Third click: reset to default sort
                newSort  = 'expected_points';
                newOrder = 'desc';
            }
        }

        window.location.href = '/?' + buildParams({ sort: newSort, order: newOrder, page: 1 }).toString();
    }

    // ── Pin functionality ─────────────────────────────────────────────────────

    const PINNED_STORAGE_KEY = 'fpl-pinned-players';
    let contextMenu = null;

    function getPinnedPlayers() {
        try {
            const stored = localStorage.getItem(PINNED_STORAGE_KEY);
            return stored ? JSON.parse(stored) : [];
        } catch (e) {
            return [];
        }
    }

    function savePinnedPlayers(pinnedIds) {
        try {
            const json = JSON.stringify(pinnedIds);
            localStorage.setItem(PINNED_STORAGE_KEY, json);
        } catch (e) {
            console.error('Failed to save pinned players to localStorage:', e);
        }
    }

    function togglePin(playerName) {
        const pinned = getPinnedPlayers();
        const isPinned = pinned.includes(playerName);
        const action = isPinned ? 'unpin' : 'pin';
        
        // Save to server via API
        fetch('/api/pin-player', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                player_name: playerName,
                action: action
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update localStorage to match server response
                savePinnedPlayers(data.pinned_players);
                
                // Reload to show updated pins
                location.reload();
            } else {
                console.error('Failed to pin player:', data.error);
            }
        })
        .catch(error => {
            console.error('Error pinning player:', error);
        });
    }

    function showContextMenu(event, playerName) {
        event.preventDefault();
        
        // Remove existing menu if any
        if (contextMenu) {
            contextMenu.remove();
        }
        
        const pinned = getPinnedPlayers();
        const isPinned = pinned.includes(playerName);
        
        // Create context menu
        contextMenu = document.createElement('div');
        contextMenu.className = 'context-menu';
        contextMenu.innerHTML = `
            <div class="context-menu-item" data-action="pin">
                ${isPinned ? '📌 Unpin Player' : '📍 Pin Player'}
            </div>
        `;
        contextMenu.style.left = event.pageX + 'px';
        contextMenu.style.top = event.pageY + 'px';
        document.body.appendChild(contextMenu);
        
        // Handle menu click
        contextMenu.querySelector('[data-action="pin"]').addEventListener('click', function() {
            togglePin(playerName);
        });
        
        // Close menu on outside click
        setTimeout(() => {
            document.addEventListener('click', closeContextMenu);
        }, 0);
    }

    function closeContextMenu() {
        if (contextMenu) {
            contextMenu.remove();
            contextMenu = null;
        }
        document.removeEventListener('click', closeContextMenu);
    }

    function getCleanPlayerName(playerNameCell) {
        // Remove pin icon if present to get clean name
        const pinIcon = playerNameCell.querySelector('.pin-icon');
        if (pinIcon) {
            return playerNameCell.textContent.replace('📌 ', '').trim();
        }
        return playerNameCell.textContent.trim();
    }

    function initPinFunctionality() {
        const tbody = document.querySelector('tbody');
        if (!tbody) return;
        
        // Add right-click handlers to all player rows
        tbody.addEventListener('contextmenu', function(event) {
            const row = event.target.closest('tr');
            if (!row) return;
            
            const playerNameCell = row.querySelector('.player-name');
            if (!playerNameCell) return;
            
            const playerName = getCleanPlayerName(playerNameCell);
            showContextMenu(event, playerName);
        });
        
        // Clean up existing pin styling and icons first
        const rows = tbody.querySelectorAll('tr');
        rows.forEach(row => {
            row.classList.remove('pinned-row');
            const pinIcon = row.querySelector('.pin-icon');
            if (pinIcon) {
                pinIcon.remove();
            }
        });
        
        // Mark pinned rows
        const pinned = getPinnedPlayers();
        rows.forEach(row => {
            const playerNameCell = row.querySelector('.player-name');
            if (!playerNameCell) return;
            
            const playerName = getCleanPlayerName(playerNameCell);
            if (pinned.includes(playerName)) {
                row.classList.add('pinned-row');
                // Add pin icon to player name
                const icon = document.createElement('span');
                icon.className = 'pin-icon';
                icon.textContent = '📌 ';
                playerNameCell.insertBefore(icon, playerNameCell.firstChild);
            }
        });
    }

    // ── Expose to inline HTML handlers ────────────────────────────────────────

    window.toggleFutureWindow = toggleFutureWindow;
    window.updateLabel        = updateLabel;
    window.updateGamesLabel   = updateGamesLabel;
    window.scheduleApply      = scheduleApply;
    window.scheduleSearch     = scheduleSearch;
    window.applyFilters       = applyFilters;
    window.sortTable          = sortTable;

    // Initialize pin functionality on page load
    initPinFunctionality();
}());