/* fpl.js — Alpine component + HTMX integration */

function filters() {
    return {
        positions: [],
        teams: [],
        search: '',
        mins: 70,
        priceMax: '15.0',
        games: 5,
        maxGames: 38,
        horizon: 1,
        adjustDifficulty: true,
        newPlayersOnly: false,
        sort: 'expected_points',
        order: 'desc',
        page: 1,
        initialPositions: [],

        posOpen: false,
        teamOpen: false,

        init() {
            var s = window._fplState || {};
            this.positions = s.positions || [];
            this.teams = s.teams || [];
            this.search = s.search || '';
            this.mins = s.mins || 70;
            this.priceMax = s.priceMax || '15.0';
            this.games = s.games || 5;
            this.maxGames = s.maxGames || 38;
            this.horizon = s.horizon || 1;
            this.adjustDifficulty = s.adjustDifficulty !== false;
            this.newPlayersOnly = s.newPlayersOnly || false;
            this.sort = s.sort || 'expected_points';
            this.order = s.order || 'desc';
            this.page = s.page || 1;
            this.initialPositions = s.initialPositions || [];
        },

        positionLabel() {
            if (this.positions.length === 0) return 'All positions';
            return this.positions.join(', ');
        },

        teamLabel() {
            if (this.teams.length === 0) return 'All teams';
            if (this.teams.length <= 2) return this.teams.join(', ');
            return this.teams.length + ' teams';
        },

        gamesLabel() {
            var suffix = this.games == 1 ? ' Game' : ' Games';
            var all = this.games == this.maxGames ? ' (All)' : '';
            return this.games + suffix + all;
        },

        togglePosition(code) {
            var idx = this.positions.indexOf(code);
            if (idx === -1) this.positions.push(code);
            else this.positions.splice(idx, 1);
            this.apply();
        },

        toggleTeam(name) {
            var idx = this.teams.indexOf(name);
            if (idx === -1) this.teams.push(name);
            else this.teams.splice(idx, 1);
            this.apply();
        },

        buildUrl(overrides) {
            var p = overrides || {};
            var params = new URLSearchParams();
            params.set('position', (p.positions || this.positions).join(','));
            params.set('team', (p.teams || this.teams).join(','));
            params.set('mins', p.mins || this.mins);
            params.set('games', p.games || this.games);
            params.set('adjust_difficulty', p.adjustDifficulty !== undefined ? p.adjustDifficulty : this.adjustDifficulty);
            params.set('horizon', p.horizon || this.horizon);
            params.set('sort', p.sort || this.sort);
            params.set('order', p.order || this.order);
            params.set('page', p.page || 1);

            if (this.search) params.set('search', this.search);
            if (this.newPlayersOnly) params.set('new_players_only', 'true');

            var posChanged = this.positions.join(',') !== this.initialPositions.join(',');
            if (!posChanged) {
                params.set('price_max', parseFloat(this.priceMax).toFixed(1));
            }

            return '/?' + params.toString();
        },

        apply(overrides) {
            var url = this.buildUrl(overrides);
            htmx.ajax('GET', url, {
                target: '#results',
                swap: 'innerHTML',
                pushUrl: url
            });
        }
    };
}

// Re-initialize pinning and tooltips after HTMX swaps
document.addEventListener('htmx:afterSwap', function(event) {
    if (event.detail.target.id === 'results') {
        initPinFunctionality();
        initTooltips();
    }
});

// Pinning
var PINNED_STORAGE_KEY = 'fpl-pinned-players';
var contextMenu = null;

function getPinnedPlayers() {
    try {
        var stored = localStorage.getItem(PINNED_STORAGE_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch (e) {
        return [];
    }
}

function savePinnedPlayers(pinnedIds) {
    try {
        localStorage.setItem(PINNED_STORAGE_KEY, JSON.stringify(pinnedIds));
    } catch (e) {}
}

function togglePin(playerName) {
    var pinned = getPinnedPlayers();
    var isPinned = pinned.indexOf(playerName) !== -1;
    var action = isPinned ? 'unpin' : 'pin';

    fetch('/api/pin-player', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player_name: playerName, action: action })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.success) {
            savePinnedPlayers(data.pinned_players);
            location.reload();
        }
    });
}

function showContextMenu(event, playerName) {
    event.preventDefault();
    if (contextMenu) contextMenu.remove();

    var pinned = getPinnedPlayers();
    var isPinned = pinned.indexOf(playerName) !== -1;

    contextMenu = document.createElement('div');
    contextMenu.className = 'context-menu';
    contextMenu.innerHTML = '<div class="context-menu-item" data-action="pin">' +
        (isPinned ? '📌 Unpin Player' : '📍 Pin Player') + '</div>';
    contextMenu.style.left = event.pageX + 'px';
    contextMenu.style.top = event.pageY + 'px';
    document.body.appendChild(contextMenu);

    contextMenu.querySelector('[data-action="pin"]').addEventListener('click', function() {
        togglePin(playerName);
    });

    setTimeout(function() {
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

function getCleanPlayerName(el) {
    var text = el.textContent;
    return text.replace('📌 ', '').replace('⚠️', '').replace('✨', '').trim();
}

function initPinFunctionality() {
    var list = document.querySelector('.list');
    if (!list) return;

    list.removeEventListener('contextmenu', handleContextMenu);
    list.addEventListener('contextmenu', handleContextMenu);

    var cards = list.querySelectorAll('.card');
    cards.forEach(function(card) {
        card.classList.remove('pinned-card');
        var pinIcon = card.querySelector('.pin-icon');
        if (pinIcon) pinIcon.remove();
    });

    var pinned = getPinnedPlayers();
    cards.forEach(function(card) {
        var nameEl = card.querySelector('.nm');
        if (!nameEl) return;
        var playerName = getCleanPlayerName(nameEl);
        if (pinned.indexOf(playerName) !== -1) {
            card.classList.add('pinned-card');
            var icon = document.createElement('span');
            icon.className = 'pin-icon';
            icon.textContent = '📌 ';
            nameEl.insertBefore(icon, nameEl.firstChild);
        }
    });
}

function handleContextMenu(event) {
    var card = event.target.closest('.card');
    if (!card) return;
    var nameEl = card.querySelector('.nm');
    if (!nameEl) return;
    showContextMenu(event, getCleanPlayerName(nameEl));
}

// Tooltips
var tooltipContainer = null;

function createTooltipContainer() {
    if (!tooltipContainer) {
        tooltipContainer = document.createElement('div');
        tooltipContainer.className = 'tooltip-container';
        document.body.appendChild(tooltipContainer);
    }
    return tooltipContainer;
}

function showTooltip(element, text) {
    var tooltip = createTooltipContainer();
    tooltip.textContent = text;

    var rect = element.getBoundingClientRect();
    var left = rect.right;
    var top = rect.bottom;

    tooltip.style.left = left + 'px';
    tooltip.style.top = top + 'px';
    tooltip.classList.add('visible');

    var tooltipRect = tooltip.getBoundingClientRect();
    if (left + tooltipRect.width > window.innerWidth) {
        tooltip.style.left = (rect.left - tooltipRect.width) + 'px';
    }
    if (top + tooltipRect.height > window.innerHeight) {
        tooltip.style.top = (rect.top - tooltipRect.height) + 'px';
    }
}

function hideTooltip() {
    if (tooltipContainer) tooltipContainer.classList.remove('visible');
}

function initTooltips() {
    document.querySelectorAll('.warning-icon:not([data-tip-init])').forEach(function(icon) {
        icon.addEventListener('mouseenter', function() {
            var text = this.getAttribute('data-tooltip');
            if (text) showTooltip(this, text);
        });
        icon.addEventListener('mouseleave', hideTooltip);
        icon.setAttribute('data-tip-init', '1');
    });
}

// Initial setup
document.addEventListener('DOMContentLoaded', function() {
    initPinFunctionality();
    initTooltips();
});
