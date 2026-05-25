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

export function getCleanPlayerName(el) {
    let text = el.textContent;
    text = text.replace('📌 ', '').replace('⚠️', '').replace('✨', '').trim();
    return text;
}

export function initPinFunctionality() {
    const list = document.querySelector('.list');
    if (!list) return;

    list.addEventListener('contextmenu', function(event) {
        const card = event.target.closest('.card');
        if (!card) return;

        const nameEl = card.querySelector('.nm');
        if (!nameEl) return;

        const playerName = getCleanPlayerName(nameEl);
        showContextMenu(event, playerName);
    });

    const cards = list.querySelectorAll('.card');
    cards.forEach(card => {
        card.classList.remove('pinned-card');
        const pinIcon = card.querySelector('.pin-icon');
        if (pinIcon) pinIcon.remove();
    });

    const pinned = getPinnedPlayers();
    cards.forEach(card => {
        const nameEl = card.querySelector('.nm');
        if (!nameEl) return;

        const playerName = getCleanPlayerName(nameEl);
        if (pinned.includes(playerName)) {
            card.classList.add('pinned-card');
            const icon = document.createElement('span');
            icon.className = 'pin-icon';
            icon.textContent = '📌 ';
            nameEl.insertBefore(icon, nameEl.firstChild);
        }
    });
}
