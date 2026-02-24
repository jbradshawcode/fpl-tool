/* fpl.js — all interactivity for the FPL Expected Points page
 *
 * Depends on a small inline <script> in index.html that sets:
 *   const FPL = { maxGames, selectedPosition, sortBy, sortOrder, page };
 */

(function () {
    'use strict';

    let changeTimeout;

    // ── Toggle ────────────────────────────────────────────────────────────────

    function toggleFutureWindow(pill) {
        const nowOn = pill.getAttribute('data-on') !== 'true';
        pill.setAttribute('data-on', nowOn);
        pill.querySelector('.pill-label').textContent = nowOn ? 'On' : 'Off';
        document.getElementById('future-window-item').style.display = nowOn ? 'flex' : 'none';
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
        changeTimeout = setTimeout(applyFilters, 500);
    }

    // ── Build query-string from current UI state ──────────────────────────────

    function buildParams({ sort = FPL.sortBy, order = FPL.sortOrder, page = 1 } = {}) {
        const adjustOn       = document.getElementById('adjust-difficulty-toggle').getAttribute('data-on') === 'true';
        const currentPosition = document.getElementById('position-dropdown').value;

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
        const page   = keepPage ? FPL.page : 1;
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

    // ── Expose to inline HTML handlers ────────────────────────────────────────

    window.toggleFutureWindow = toggleFutureWindow;
    window.updateLabel        = updateLabel;
    window.updateGamesLabel   = updateGamesLabel;
    window.scheduleApply      = scheduleApply;
    window.applyFilters       = applyFilters;
    window.sortTable          = sortTable;
}());