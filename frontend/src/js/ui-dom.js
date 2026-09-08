export function setupImageObserver() {
    window.imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) return;

            const img = entry.target;
            img.src = img.dataset.src;
            img.onload = () => img.classList.add('visible');
            observer.unobserve(img);
        });
    }, { rootMargin: "100px 0px", threshold: 0.01 });
}

export function injectUiRuntimeStyles() {
    if (document.getElementById('ui-runtime-styles')) return;

    const style = document.createElement('style');
    style.id = 'ui-runtime-styles';
    style.textContent = `
        .lazy-img { opacity: 0; transition: opacity 0.6s ease-in-out; }
        .lazy-img.visible { opacity: 1; }
        .skeleton-loader {
            height: 52px; margin: 12px 0; border-radius: 18px;
            background: var(--color-surface-2);
            background-image: linear-gradient(90deg, transparent 0, var(--color-surface-3) 24%, var(--color-surface-2) 56%, transparent 100%);
            background-size: 200% 100%;
            animation: skeleton 2s infinite linear;
        }
        .global-sync-indicator {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 0.7rem;
            padding: 8px 12px;
            border-radius: 999px;
            background: var(--color-surface-2);
            border: 1px solid var(--color-border);
            color: var(--color-text-secondary);
            cursor: pointer;
            transition: all 0.3s ease;
            margin-left: auto;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            font-weight: 700;
        }
        .global-sync-indicator:hover { background: var(--color-surface-3); border-color: var(--color-border-strong); }
        .global-sync-indicator[data-status="synced"] { color: #4EBA87; }
        .global-sync-indicator[data-status="pending"] { color: var(--color-accent); }
        .global-sync-indicator[data-status="offline"] { color: var(--color-text-dim); }
        #recent-searches-panel { margin-top: 8px; }
        .recent-searches-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .recent-searches-header span { font-size: 0.72rem; color: var(--color-text-dim); font-weight: 700; text-transform: uppercase; letter-spacing: 0.14em; }
        .clear-recent-btn { background: none; border: none; color: var(--color-text-dim); font-size: 0.75rem; cursor: pointer; padding: 4px; }
        .clear-recent-btn:hover { color: var(--color-accent); }
        .recent-searches-tags { display: flex; flex-wrap: wrap; gap: 8px; }
        .recent-search-tag {
            background: var(--color-surface-2);
            border: 1px solid var(--color-border);
            color: var(--color-text-secondary);
            padding: 7px 12px;
            border-radius: 999px;
            font-size: 0.78rem;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .recent-search-tag:hover { background: var(--color-surface-3); border-color: var(--color-accent); color: var(--color-text-primary); }
        #search-clear-btn {
            position: absolute;
            right: 14px;
            top: 50%;
            transform: translateY(-50%);
            background: none;
            border: none;
            color: var(--color-text-dim);
            cursor: pointer;
            padding: 4px;
            width: 28px;
            height: 28px;
            border-radius: 50%;
        }
        #search-clear-btn:hover { background: var(--color-surface-2); color: var(--color-text-primary); }
        #search-clear-btn.hidden { display: none; }
        .search-wrapper { position: relative; }
        @keyframes skeleton { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }
    `;

    document.head.appendChild(style);
}
