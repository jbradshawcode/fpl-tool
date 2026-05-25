/* navigation.js — URL building and navigation functions */

let FPL;

export function setFPLConfig(fplConfig) {
    FPL = fplConfig;
}

function getCheckedValues(multiselectId) {
    var boxes = document.querySelectorAll('#' + multiselectId + ' input[type="checkbox"]:checked');
    var vals = [];
    for (var i = 0; i < boxes.length; i++) vals.push(boxes[i].value);
    return vals.join(',');
}

export function buildParams({ sort, order, page } = {}) {
    const difficultyToggle = document.getElementById('adjust-difficulty-toggle');
    const adjustOn = difficultyToggle ? difficultyToggle.getAttribute('data-on') === 'true' : false;
    const futureSlider = document.getElementById('future-slider');
    const newPlayersToggle = document.getElementById('new-players-toggle');
    const currentPositions = getCheckedValues('position-multiselect');
    const currentTeams = getCheckedValues('team-multiselect');
    const searchValue = document.getElementById('search-input').value.trim();

    const params = new URLSearchParams({
        position: currentPositions,
        team: currentTeams,
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

    if (searchValue) {
        params.set('search', searchValue);
    }

    const positionChanged = currentPositions !== FPL.selectedPositions;
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

export function changeSortColumn(column) {
    window.location.href = '/?' + buildParams({ sort: column, order: 'desc', page: 1 }).toString();
}

export function toggleSortDirection() {
    const newOrder = FPL.sortOrder === 'desc' ? 'asc' : 'desc';
    window.location.href = '/?' + buildParams({ sort: FPL.sortBy, order: newOrder, page: 1 }).toString();
}
