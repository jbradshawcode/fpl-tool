/* navigation.js — URL building and navigation functions */

let FPL;

export function setFPLConfig(fplConfig) {
    FPL = fplConfig;
}

export function buildParams({ sort, order, page } = {}) {
    const difficultyToggle = document.getElementById('adjust-difficulty-toggle');
    const adjustOn = difficultyToggle ? difficultyToggle.getAttribute('data-on') === 'true' : false;
    const futureSlider = document.getElementById('future-slider');
    const newPlayersToggle = document.getElementById('new-players-toggle');
    const currentPosition = document.getElementById('position-dropdown').value;
    const searchValue = document.getElementById('search-input').value.trim();

    const params = new URLSearchParams({
        position: currentPosition,
        team: document.getElementById('team-dropdown').value,
        mins: document.getElementById('mins-slider').value,
        games: document.getElementById('games-slider').value,
        adjust_difficulty: adjustOn,
        sort: sort || FPL.sortBy,
        order: order || FPL.sortOrder,
        page: page || 1,
    });

    if (futureSlider) {
        params.set('horizon', futureSlider.value);
    }

    if (newPlayersToggle) {
        const newPlayersOn = newPlayersToggle.getAttribute('data-on') === 'true';
        if (newPlayersOn) {
            params.set('new_players_only', 'true');
        }
    }

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

export function applyFilters({ keepPage = false } = {}) {
    const page = keepPage ? FPL.page : 1;
    window.location.href = '/?' + buildParams({ page }).toString();
}

export function sortTable(column) {
    let newSort = column;
    let newOrder = 'desc';

    if (FPL.sortBy === column) {
        if (FPL.sortOrder === 'desc') {
            newOrder = 'asc';
        } else {
            // Third click: reset to default sort
            newSort = 'expected_points';
            newOrder = 'desc';
        }
    }

    window.location.href = '/?' + buildParams({ sort: newSort, order: newOrder, page: 1 }).toString();
}
