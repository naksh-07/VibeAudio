const DEFAULT_PALETTE = [
    [198, 78, 0],
    [110, 110, 115],
    [242, 242, 247],
    [245, 245, 247]
];

const SURFACES = ['library', 'history', 'player'];
const SURFACE_BASE_PALETTES = {
    library: [
        [198, 78, 0],
        [110, 110, 115],
        [242, 242, 247],
        [245, 245, 247]
    ],
    history: [
        [198, 78, 0],
        [110, 110, 115],
        [242, 242, 247],
        [245, 245, 247]
    ],
    player: [
        [198, 78, 0],
        [110, 110, 115],
        [242, 242, 247],
        [245, 245, 247]
    ]
};
const SURFACE_DYNAMIC_THEME = {
    library: false,
    history: false,
    player: true
};
const paletteCache = new Map();
const surfaceThemes = {
    library: null,
    history: null,
    player: null
};
const pendingThemeTokens = {
    library: 0,
    history: 0,
    player: 0
};

let activeSurface = 'library';

export function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return "00:00";

    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);

    if (h > 0) {
        return `${h}:${m < 10 ? '0' + m : m}:${s < 10 ? '0' + s : s}`;
    }

    return `${m}:${s < 10 ? '0' + s : s}`;
}

export function showToast(msg) {
    const toast = document.createElement('div');
    toast.className = 'toast-msg';
    toast.innerText = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function clampChannel(value) {
    return Math.max(0, Math.min(255, Math.round(value)));
}

function mixColor(colorA, colorB, weight = 0.5) {
    return colorA.map((channel, index) => clampChannel(channel * (1 - weight) + colorB[index] * weight));
}

function rgb(color) {
    return `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
}

function rgba(color, alpha) {
    return `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${alpha})`;
}

function rgbToHsl(r, g, b) {
    r /= 255; g /= 255; b /= 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    let h, s, l = (max + min) / 2;

    if (max === min) {
        h = s = 0;
    } else {
        const d = max - min;
        s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
        switch (max) {
            case r: h = (g - b) / d + (g < b ? 6 : 0); break;
            case g: h = (b - r) / d + 2; break;
            case b: h = (r - g) / d + 4; break;
        }
        h /= 6;
    }
    return [h * 360, s * 100, l * 100];
}

function hslToRgb(h, s, l) {
    h /= 360; s /= 100; l /= 100;
    let r, g, b;

    if (s === 0) {
        r = g = b = l;
    } else {
        const hue2rgb = (p, q, t) => {
            if (t < 0) t += 1;
            if (t > 1) t -= 1;
            if (t < 1 / 6) return p + (q - p) * 6 * t;
            if (t < 1 / 2) return q;
            if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
            return p;
        };
        const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
        const p = 2 * l - q;
        r = hue2rgb(p, q, h + 1 / 3);
        g = hue2rgb(p, q, h);
        b = hue2rgb(p, q, h - 1 / 3);
    }
    return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
}

function clampLightBloom(color) {
    const [h, s, l] = rgbToHsl(color[0], color[1], color[2]);
    const clampedS = Math.min(s, 35);
    const clampedL = Math.max(l, 85);
    return hslToRgb(h, clampedS, clampedL);
}

function normalizeSurface(surface) {
    return SURFACES.includes(surface) ? surface : 'library';
}

function getSurfaceBasePalette(surface) {
    return SURFACE_BASE_PALETTES[normalizeSurface(surface)] || DEFAULT_PALETTE;
}

function buildSurfacePalette(palette, surface) {
    const basePalette = getSurfaceBasePalette(surface);

    if (!SURFACE_DYNAMIC_THEME[normalizeSurface(surface)] || !Array.isArray(palette) || !palette.length) {
        return basePalette;
    }

    const blendWeights = [0.26, 0.24, 0.18, 0.1];
    return basePalette.map((baseColor, index) => {
        const sourceColor = palette[index] || baseColor;
        return mixColor(baseColor, sourceColor, blendWeights[index]);
    });
}

function buildTheme(palette, surface = 'library') {
    const [primaryBase, secondaryBase] = buildSurfacePalette(palette, surface);
    const bloomPrimary = clampLightBloom(primaryBase);
    const bloomSecondary = clampLightBloom(secondaryBase);

    return {
        '--primary': '#C64E00',
        '--secondary': '#6E6E73',
        '--accent-soft': 'rgba(198, 78, 0, 0.08)',
        '--theme-bg-1': rgba(bloomPrimary, 0.45),
        '--theme-bg-2': rgba(bloomSecondary, 0.35),
        '--theme-bg-3': 'rgba(242, 242, 247, 0.8)',
        '--theme-bg-4': '#FFFFFF',
        '--theme-surface-1': '#FFFFFF',
        '--theme-surface-2': '#F2F2F7',
        '--theme-surface-3': '#E5E5EA',
        '--theme-border': 'rgba(0, 0, 0, 0.08)',
        '--theme-border-strong': 'rgba(0, 0, 0, 0.14)',
        '--theme-glow': 'rgba(198, 78, 0, 0.12)',
        '--theme-glow-soft': 'rgba(198, 78, 0, 0.04)',
        '--theme-shadow': 'var(--shadow-card)',
        '--theme-shadow-strong': 'var(--shadow-elevated)',
        '--theme-title': '#1D1D1F',
        '--theme-text': '#1D1D1F',
        '--theme-text-soft': '#48484A',
        '--theme-text-dim': '#86868B',
        '--theme-title-gradient-start': '#1D1D1F',
        '--theme-title-gradient-end': '#6E6E73',
        '--theme-progress-track': 'rgba(0, 0, 0, 0.06)',
        '--theme-progress-fill': 'linear-gradient(90deg, #C64E00, #E65A00)',
        '--theme-player-overlay': `linear-gradient(135deg, ${rgba(bloomPrimary, 0.35)}, ${rgba(bloomSecondary, 0.2)} 42%, #F5F5F7)`
    };
}

function getDefaultTheme() {
    return buildTheme(DEFAULT_PALETTE, 'library');
}

function resolveImageUrl(imageUrl) {
    try {
        return new URL(imageUrl, window.location.href).href;
    } catch (error) {
        console.warn("Theme image URL fallback used.", error);
        return imageUrl;
    }
}

function setCssVariables(theme) {
    const root = document.documentElement;
    Object.entries(theme).forEach(([key, value]) => {
        root.style.setProperty(key, value);
    });

    const themeMeta = document.querySelector('meta[name="theme-color"]');
    if (themeMeta) {
        themeMeta.setAttribute('content', '#F5F5F7');
    }
}

function applyThemeForSurface(surface) {
    const safeSurface = normalizeSurface(surface);
    activeSurface = safeSurface;
    document.body.dataset.themeSurface = safeSurface;
    setCssVariables(surfaceThemes[safeSurface] || getDefaultTheme());
}

function extractPaletteFromImage(imageUrl) {
    if (!imageUrl) return Promise.resolve(DEFAULT_PALETTE);

    const resolvedUrl = resolveImageUrl(imageUrl);
    if (paletteCache.has(resolvedUrl)) {
        return Promise.resolve(paletteCache.get(resolvedUrl));
    }

    if (!window.ColorThief) {
        paletteCache.set(resolvedUrl, DEFAULT_PALETTE);
        return Promise.resolve(DEFAULT_PALETTE);
    }

    return new Promise((resolve) => {
        const colorThief = new ColorThief();
        const img = new Image();
        img.crossOrigin = 'Anonymous';
        img.referrerPolicy = 'no-referrer';

        img.onload = () => {
            try {
                const palette = colorThief.getPalette(img, 4);
                const finalPalette = Array.isArray(palette) && palette.length ? palette : DEFAULT_PALETTE;
                paletteCache.set(resolvedUrl, finalPalette);
                resolve(finalPalette);
            } catch (error) {
                console.warn("Palette extraction failed. Using fallback theme.", error);
                paletteCache.set(resolvedUrl, DEFAULT_PALETTE);
                resolve(DEFAULT_PALETTE);
            }
        };

        img.onerror = () => {
            console.warn("Theme image load failed. Using fallback theme.");
            paletteCache.set(resolvedUrl, DEFAULT_PALETTE);
            resolve(DEFAULT_PALETTE);
        };

        if (resolvedUrl.startsWith('blob:') || resolvedUrl.startsWith('data:')) {
            img.removeAttribute('crossOrigin');
            img.src = resolvedUrl;
        } else if (typeof navigator !== 'undefined' && !navigator.onLine) {
            if (resolvedUrl.startsWith('http://') || resolvedUrl.startsWith('https://')) {
                paletteCache.set(resolvedUrl, DEFAULT_PALETTE);
                resolve(DEFAULT_PALETTE);
                return;
            }
            img.src = resolvedUrl;
        } else if (resolvedUrl.startsWith('http://') || resolvedUrl.startsWith('https://')) {
            img.src = `https://wsrv.nl/?url=${encodeURIComponent(resolvedUrl)}&w=480&fit=cover`;
        } else {
            img.src = resolvedUrl;
        }
    });
}

async function queueSurfaceTheme(imageUrl, surface, activate = false) {
    const safeSurface = normalizeSurface(surface);
    const token = ++pendingThemeTokens[safeSurface];

    if (activate) {
        applyThemeForSurface(safeSurface);
    }

    if (!SURFACE_DYNAMIC_THEME[safeSurface] || !imageUrl) {
        const theme = buildTheme(null, safeSurface);
        surfaceThemes[safeSurface] = theme;

        if (activeSurface === safeSurface) {
            setCssVariables(theme);
        }

        return theme;
    }

    const palette = await extractPaletteFromImage(imageUrl);
    if (pendingThemeTokens[safeSurface] !== token) {
        return surfaceThemes[safeSurface] || getDefaultTheme();
    }

    const theme = buildTheme(palette, safeSurface);
    surfaceThemes[safeSurface] = theme;

    if (activeSurface === safeSurface) {
        setCssVariables(theme);
    }

    return theme;
}

export function setActiveThemeSurface(surface) {
    applyThemeForSurface(surface);
}

export function applyLibraryTheme(imageUrl, activate = true) {
    return queueSurfaceTheme(imageUrl, 'library', activate);
}

export function applyHistoryTheme(imageUrl, activate = true) {
    return queueSurfaceTheme(imageUrl, 'history', activate);
}

export function applyChameleonTheme(imageUrl) {
    return queueSurfaceTheme(imageUrl, 'player', true);
}

export function renderComments(comments) {
    const list = document.getElementById('comments-list');
    if (list) {
        list.innerHTML = '';
        comments.forEach((comment) => renderSingleComment(comment));
    }
}

export function renderSingleComment(comment) {
    const list = document.getElementById('comments-list');
    if (!list) return null;

    const div = document.createElement('div');
    div.className = 'comment-item';

    const timeButton = document.createElement('button');
    timeButton.type = 'button';
    timeButton.className = 'comment-time';
    timeButton.textContent = formatTime(comment.time);
    timeButton.addEventListener('click', () => window.app.seekToComment(Number(comment.time || 0)));

    const copyWrap = document.createElement('div');
    const userEl = document.createElement('span');
    userEl.className = 'comment-user';
    userEl.textContent = String(comment.user || 'Listener');

    const textEl = document.createElement('p');
    textEl.textContent = String(comment.text || '');

    copyWrap.appendChild(userEl);
    copyWrap.appendChild(textEl);
    div.appendChild(timeButton);
    div.appendChild(copyWrap);
    list.appendChild(div);
    return div;
}

surfaceThemes.library = getDefaultTheme();
surfaceThemes.history = buildTheme(null, 'history');
surfaceThemes.player = buildTheme(null, 'player');
