/* tooltip.js — Dynamic tooltip positioning to prevent clipping */

let tooltipContainer = null;

function createTooltipContainer() {
    if (!tooltipContainer) {
        tooltipContainer = document.createElement('div');
        tooltipContainer.className = 'tooltip-container';
        document.body.appendChild(tooltipContainer);
    }
    return tooltipContainer;
}

function showTooltip(element, text) {
    const tooltip = createTooltipContainer();
    tooltip.textContent = text;
    
    const rect = element.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();
    
    // Calculate position to avoid clipping
    let left = rect.right;
    let top = rect.bottom;
    
    // Check if tooltip would go off right edge
    if (left + tooltipRect.width > window.innerWidth) {
        left = rect.left - tooltipRect.width;
    }
    
    // Check if tooltip would go off bottom edge
    if (top + tooltipRect.height > window.innerHeight) {
        top = rect.top - tooltipRect.height;
    }
    
    tooltip.style.left = `${left}px`;
    tooltip.style.top = `${top}px`;
    tooltip.classList.add('visible');
}

function hideTooltip() {
    if (tooltipContainer) {
        tooltipContainer.classList.remove('visible');
    }
}

function initTooltips() {
    const warningIcons = document.querySelectorAll('.warning-icon:not([data-tooltip-initialized])');
    
    warningIcons.forEach(icon => {
        icon.addEventListener('mouseenter', function(e) {
            const tooltipText = this.getAttribute('data-tooltip');
            if (tooltipText) {
                showTooltip(this, tooltipText);
            }
        });
        
        icon.addEventListener('mouseleave', function() {
            hideTooltip();
        });
        
        icon.setAttribute('data-tooltip-initialized', 'true');
    });
}

// Initialize tooltips on page load
document.addEventListener('DOMContentLoaded', initTooltips);

// Re-initialize tooltips after dynamic content updates
const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        if (mutation.addedNodes.length) {
            initTooltips();
        }
    });
});

observer.observe(document.body, { childList: true, subtree: true });

export { initTooltips };
