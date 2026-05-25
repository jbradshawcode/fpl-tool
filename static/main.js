/* main.js — Initialization and configuration */

import { toggleFutureWindow, toggleNewPlayers, updateLabel, updateGamesLabel, scheduleApply, scheduleSearch } from './filters.js';
import { setFPLConfig, buildParams, applyFilters, sortTable, changeSortColumn, toggleSortDirection } from './navigation.js';
import { initPinFunctionality } from './pinning.js';
import { initTooltips } from './tooltip.js';

(function () {
    'use strict';

    // Load configuration from HTML data attributes
    const cfg = document.getElementById('fpl-config').dataset;
    const FPL = {
        maxGames: parseInt(cfg.maxGames),
        selectedPositions: cfg.selectedPositions || '',
        selectedTeams: cfg.selectedTeams || '',
        sortBy: cfg.sortBy,
        sortOrder: cfg.sortOrder,
        page: parseInt(cfg.page),
    };

    // Set FPL config in navigation module
    setFPLConfig(FPL);

    // Override updateGamesLabel to use FPL.maxGames
    const originalUpdateGamesLabel = updateGamesLabel;
    window.updateGamesLabel = (value) => originalUpdateGamesLabel(value, FPL.maxGames);

    // Multi-select dropdown toggle
    window.toggleMultiselect = function(id) {
        var el = document.getElementById(id);
        var wasOpen = el.classList.contains('open');
        // Close all open multiselects first
        document.querySelectorAll('.multiselect.open').forEach(function(ms) {
            ms.classList.remove('open');
        });
        if (!wasOpen) el.classList.add('open');
    };

    // Close multiselects on outside click
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.multiselect')) {
            document.querySelectorAll('.multiselect.open').forEach(function(ms) {
                ms.classList.remove('open');
            });
        }
    });

    // Expose functions to window for inline HTML handlers
    window.toggleFutureWindow = toggleFutureWindow;
    window.toggleNewPlayers = toggleNewPlayers;
    window.updateLabel = updateLabel;
    window.scheduleApply = scheduleApply;
    window.scheduleSearch = scheduleSearch;
    window.applyFilters = applyFilters;
    window.sortTable = sortTable;
    window.changeSortColumn = changeSortColumn;
    window.toggleSortDirection = toggleSortDirection;

    // Initialize pin functionality on page load
    initPinFunctionality();

    // Initialize tooltips
    initTooltips();
})();
