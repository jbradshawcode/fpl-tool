/* pinning.js — Pin/unpin player functionality */

const PINNED_STORAGE_KEY = 'fpl-pinned-players';
let contextMenu = null;

export function getPinnedPlayers() {
    try {
        const stored = localStorage.getItem(PINNED_STORAGE_KEY);
        return stored ? JSON.parse(stored) : [];
    } catch (e) {
        return [];
    }
}

export function savePinnedPlayers(pinnedIds) {
    try {
        const json = JSON.stringify(pinnedIds);
        localStorage.setItem(PINNED_STORAGE_KEY, json);
    } catch (e) {
        console.error('Failed to save pinned players to localStorage:', e);
    }
}

export function togglePin(playerName) {
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

export function showContextMenu(event, playerName) {
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

export function closeContextMenu() {
    if (contextMenu) {
        contextMenu.remove();
        contextMenu = null;
    }
    document.removeEventListener('click', closeContextMenu);
}

export function getCleanPlayerName(playerNameCell) {
    // Remove pin icon if present to get clean name
    const pinIcon = playerNameCell.querySelector('.pin-icon');
    if (pinIcon) {
        return playerNameCell.textContent.replace('📌 ', '').trim();
    }
    return playerNameCell.textContent.trim();
}

export function initPinFunctionality() {
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
