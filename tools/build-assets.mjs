import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execSync } from 'node:child_process';
import {
    BRAND_MARK_SVG,
    BRAND_MARK_CURRENT_COLOR_SVG,
    BRAND_MARK_MONOCHROME_WHITE_SVG,
    BRAND_LOCKUP_HORIZONTAL_SVG,
    BRAND_LOCKUP_COMPACT_SVG,
    BRAND_LOCKUP_STACKED_SVG,
    FAVICON_SVG
} from './brand-svg-definitions.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');
const frontendDir = path.resolve(rootDir, 'frontend');
const srcIconsDir = path.resolve(frontendDir, 'src', 'icons');
const publicIconsDir = path.resolve(frontendDir, 'public', 'icons');

// Ensure output directories exist
fs.mkdirSync(srcIconsDir, { recursive: true });
fs.mkdirSync(publicIconsDir, { recursive: true });

console.log('=== VIBEAUDIO ASSET GENERATOR (STAGE 2) ===\n');

// 1. Write Master Vector Brand Mark & Lockups
console.log('1. Writing master vector SVG files...');
fs.writeFileSync(path.join(publicIconsDir, 'brand-mark.svg'), BRAND_MARK_SVG.trim(), 'utf8');
fs.writeFileSync(path.join(publicIconsDir, 'brand-mark-monochrome.svg'), BRAND_MARK_MONOCHROME_WHITE_SVG.trim(), 'utf8');
fs.writeFileSync(path.join(publicIconsDir, 'brand-lockup-horizontal.svg'), BRAND_LOCKUP_HORIZONTAL_SVG.trim(), 'utf8');
fs.writeFileSync(path.join(publicIconsDir, 'brand-lockup-compact.svg'), BRAND_LOCKUP_COMPACT_SVG.trim(), 'utf8');
fs.writeFileSync(path.join(publicIconsDir, 'brand-lockup-stacked.svg'), BRAND_LOCKUP_STACKED_SVG.trim(), 'utf8');
fs.writeFileSync(path.join(srcIconsDir, 'favicon.svg'), FAVICON_SVG.trim(), 'utf8');
console.log('  ✓ Created brand-mark.svg, brand-lockup-*.svg, and favicon.svg');

// 2. Build Master SVG Icon Sprite (frontend/src/icons/icons.svg)
console.log('\n2. Building Master SVG Icon Sprite (frontend/src/icons/icons.svg)...');

const ICONS = {
    'brand-mark': `<path d="M3.5 4.5 Q5.5 12.5 12 20.5 Q18.5 12.5 20.5 4.5" /><path d="M7.5 4.5 Q9 9.5 12 13.5 Q15 9.5 16.5 4.5" /><path d="M12 13.5 L12 17.5" /><path d="M9.8 20.5 H14.2" />`,
    'home': `<path d="M3 10.5 L12 3.5 L21 10.5 V20 C21 20.6 20.6 21 20 21 H14.5 V15.5 C14.5 14.7 13.8 14 13 14 H11 C10.2 14 9.5 14.7 9.5 15.5 V21 H4 C3.4 21 3 20.6 3 20 V10.5 Z" />`,
    'library': `<path d="M4 19.5 V5 C4 4.2 4.7 3.5 5.5 3.5 H8.5 C9.3 3.5 10 4.2 10 5 V19.5" /><path d="M10 19.5 V7 C10 6.2 10.7 5.5 11.5 5.5 H14.5 C15.3 5.5 16 6.2 16 7 V19.5" /><path d="M16 19.5 L19.2 6.5 C19.4 5.7 20.2 5.2 21 5.4 C21.8 5.6 22.3 6.4 22.1 7.2 L19.8 19.5" /><path d="M2 20.5 H22" />`,
    'offline': `<rect x="4" y="4" width="16" height="16" rx="2" /><path d="M12 8 V14" /><path d="M9 11 L12 14 L15 11" /><path d="M8 17 H16" />`,
    'device': `<rect x="4" y="4" width="16" height="16" rx="2" /><path d="M12 8 V14" /><path d="M9 11 L12 14 L15 11" /><path d="M8 17 H16" />`,
    'history': `<path d="M3.5 12 A8.5 8.5 0 1 0 6 6 M3.5 4 V8.5 H8" /><path d="M12 7.5 V12 L15.5 14" />`,
    'account': `<circle cx="12" cy="7.5" r="4" /><path d="M4.5 20.5 C4.5 16.5 8 14.5 12 14.5 C16 14.5 19.5 16.5 19.5 20.5" />`,
    'user': `<circle cx="12" cy="7.5" r="4" /><path d="M4.5 20.5 C4.5 16.5 8 14.5 12 14.5 C16 14.5 19.5 16.5 19.5 20.5" />`,
    'user-check': `<circle cx="10" cy="7.5" r="3.5" /><path d="M3.5 19.5 C3.5 16.2 6.5 14.5 10 14.5 C11.5 14.5 12.8 14.8 13.9 15.4" /><path d="M15.5 17 L18 19.5 L22.5 14" />`,
    'menu': `<path d="M4 6.5 H20 M4 12 H20 M4 17.5 H20" />`,
    'search': `<circle cx="10.5" cy="10.5" r="7" /><path d="M15.5 15.5 L21 21" />`,
    'clear': `<path d="M6 6 L18 18 M18 6 L6 18" />`,
    'close': `<path d="M6 6 L18 18 M18 6 L6 18" />`,
    'play': `<polygon points="8,5 19,12 8,19" fill="currentColor" stroke="currentColor" />`,
    'pause': `<line x1="8" y1="5.5" x2="8" y2="18.5" stroke-width="2.5" /><line x1="16" y1="5.5" x2="16" y2="18.5" stroke-width="2.5" />`,
    'seek-back': `<path d="M4.5 10 A7.5 7.5 0 1 1 5.2 15 M4.5 4.5 V10 H10" />`,
    'seek-forward': `<path d="M19.5 10 A7.5 7.5 0 1 0 18.8 15 M19.5 4.5 V10 H14" />`,
    'previous': `<line x1="6" y1="5.5" x2="6" y2="18.5" /><polygon points="18,5.5 9,12 18,18.5" fill="currentColor" stroke="currentColor" />`,
    'next': `<line x1="18" y1="5.5" x2="18" y2="18.5" /><polygon points="6,5.5 15,12 6,18.5" fill="currentColor" stroke="currentColor" />`,
    'chapters': `<path d="M4 6.5 H7 M11 6.5 H20 M4 12 H7 M11 12 H20 M4 17.5 H7 M11 17.5 H20" />`,
    'list': `<path d="M4 6.5 H7 M11 6.5 H20 M4 12 H7 M11 12 H20 M4 17.5 H7 M11 17.5 H20" />`,
    'speed': `<path d="M12 4 A8 8 0 1 0 20 12" /><path d="M12 12 L16.5 8.5" /><circle cx="12" cy="12" r="1.8" />`,
    'sleep': `<path d="M19.5 14.2 C18.5 18.2 14.5 20.8 10.5 20 C6.5 19.2 3.5 15.2 4.2 11 C4.8 7.2 8.5 4.2 12.5 4.8 C11.5 7.2 12 10 14 12 C16 14 18.8 14.2 19.5 14.2 Z" />`,
    'bookmark': `<path d="M6 4.5 C6 3.7 6.7 3 7.5 3 H16.5 C17.3 3 18 3.7 18 4.5 V21 L12 17.5 L6 21 V4.5 Z" />`,
    'bookmark-active': `<path d="M6 4.5 C6 3.7 6.7 3 7.5 3 H16.5 C17.3 3 18 3.7 18 4.5 V21 L12 17.5 L6 21 V4.5 Z" fill="currentColor" />`,
    'note': `<path d="M14 3.5 L20.5 10 L8.5 22 H2 V15.5 L14 3.5 Z" /><path d="M12.5 5 L19 11.5" /><path d="M6 18 H9" />`,
    'vocal-clarity': `<path d="M3 12 H5 M7 8 V16 M11 4 V20 M15 7 V17 M17 10 V14 M19 12 H21" />`,
    'waveform': `<path d="M3 12 H5 M7 8 V16 M11 4 V20 M15 7 V17 M17 10 V14 M19 12 H21" />`,
    'download': `<path d="M12 3.5 V14.5 M7.5 10.5 L12 15 L16.5 10.5 M4 19.5 H20" />`,
    'cloud-download': `<path d="M6.5 17.5 C4 17.5 2.5 15.5 2.5 13 C2.5 10.8 4.2 9 6.4 9 C7 6.5 9.3 4.5 12 4.5 C15.3 4.5 18 7.2 18 10.5 C19.7 10.8 21 12.2 21 14 C21 16 19.5 17.5 17.5 17.5 M12 10.5 V19.5 M9 16.5 L12 19.5 L15 16.5" />`,
    'downloaded': `<circle cx="12" cy="12" r="9" /><path d="M8 12 L11 15 L16.5 9" />`,
    'check-circle': `<circle cx="12" cy="12" r="9" /><path d="M8 12 L11 15 L16.5 9" />`,
    'cloud-sync': `<path d="M6.5 17 C4 17 2.5 15.2 2.5 13 C2.5 10.8 4.2 9 6.4 9 C7 6.5 9.3 4.5 12 4.5 C15.3 4.5 18 7.2 18 10.5 C19.7 10.8 21 12.2 21 14 C21 16 19.5 17 17.5 17 M12 17 V10 M9.5 12.5 L12 10 L14.5 12.5" />`,
    'cloud': `<path d="M6.5 17 C4 17 2.5 15.2 2.5 13 C2.5 10.8 4.2 9 6.4 9 C7 6.5 9.3 4.5 12 4.5 C15.3 4.5 18 7.2 18 10.5 C19.7 10.8 21 12.2 21 14 C21 16 19.5 17 17.5 17" />`,
    'import': `<path d="M14 3.5 H6 C4.9 3.5 4 4.4 4 5.5 V18.5 C4 19.6 4.9 20.5 6 20.5 H18 C19.1 20.5 20 19.6 20 18.5 V9.5 L14 3.5 Z" /><path d="M14 3.5 V9.5 H20 M12 12.5 V17.5 M9.5 15 H14.5" />`,
    'storage': `<rect x="3" y="5" width="18" height="14" rx="2" /><line x1="3" y1="13" x2="21" y2="13" /><circle cx="17" cy="16" r="1" /><circle cx="14" cy="16" r="1" />`,
    'hard-drive': `<rect x="3" y="5" width="18" height="14" rx="2" /><line x1="3" y1="13" x2="21" y2="13" /><circle cx="17" cy="16" r="1" /><circle cx="14" cy="16" r="1" />`,
    'sync': `<path d="M20 12 A8 8 0 0 1 5.5 17.5 M4 12 A8 8 0 0 1 18.5 6.5" /><path d="M20 4 V9 H15 M4 20 V15 H9" />`,
    'spinner': `<path d="M12 3 A9 9 0 1 0 21 12" />`,
    'trash': `<path d="M4 6.5 H20 M9 6.5 V4 C9 3.4 9.4 3 10 3 H14 C14.6 3 15 3.4 15 4 V6.5" /><path d="M6 6.5 L7.2 19.2 C7.3 20.2 8.2 21 9.2 21 H14.8 C15.8 21 16.7 20.2 16.8 19.2 L18 6.5" /><line x1="10" y1="10.5" x2="10" y2="16.5" /><line x1="14" y1="10.5" x2="14" y2="16.5" />`,
    'share': `<circle cx="18" cy="5.5" r="2.5" /><circle cx="6" cy="12" r="2.5" /><circle cx="18" cy="18.5" r="2.5" /><line x1="8.3" y1="10.8" x2="15.7" y2="6.7" /><line x1="8.3" y1="13.2" x2="15.7" y2="17.3" />`,
    'arrow-left': `<line x1="19" y1="12" x2="5" y2="12" /><polyline points="11,6 5,12 11,18" />`,
    'back': `<line x1="19" y1="12" x2="5" y2="12" /><polyline points="11,6 5,12 11,18" />`,
    'arrow-right': `<line x1="5" y1="12" x2="19" y2="12" /><polyline points="13,6 19,12 13,18" />`,
    'chevron-up': `<polyline points="6,15 12,9 18,15" />`,
    'chevron-down': `<polyline points="6,9 12,15 18,9" />`,
    'chevron-right': `<polyline points="9,6 15,12 9,18" />`,
    'check': `<polyline points="5,12.5 9.5,17 19,7" />`,
    'success': `<polyline points="5,12.5 9.5,17 19,7" />`,
    'warning': `<polygon points="12,3.5 21,19.5 3,19.5" /><line x1="12" y1="9" x2="12" y2="13.5" /><circle cx="12" cy="16.5" r="0.8" fill="currentColor" />`,
    'error': `<circle cx="12" cy="12" r="9" /><line x1="5.5" y1="5.5" x2="18.5" y2="18.5" />`,
    'ban': `<circle cx="12" cy="12" r="9" /><line x1="5.5" y1="5.5" x2="18.5" y2="18.5" />`,
    'info': `<circle cx="12" cy="12" r="9" /><line x1="12" y1="11" x2="12" y2="16.5" /><circle cx="12" cy="7.5" r="0.8" fill="currentColor" />`,
    'open-external': `<path d="M14 4 H20 V10" /><line x1="10" y1="14" x2="20" y2="4" /><path d="M19 13 V18.5 C19 19.6 18.1 20.5 17 20.5 H5.5 C4.4 20.5 3.5 19.6 3.5 18.5 V7 C3.5 5.9 4.4 5 5.5 5 H11" />`,
    'headphones': `<path d="M3 13 V11 C3 6 7 2 12 2 C17 2 21 6 21 11 V13" /><rect x="3" y="11.5" width="5" height="8" rx="2" /><rect x="16" y="11.5" width="5" height="8" rx="2" />`,
    'sanctuary': `<path d="M3 13 V11 C3 6 7 2 12 2 C17 2 21 6 21 11 V13" /><rect x="3" y="11.5" width="5" height="8" rx="2" /><rect x="16" y="11.5" width="5" height="8" rx="2" />`,
    'equalizer': `<line x1="6" y1="10" x2="6" y2="18" stroke-width="2.2" /><line x1="12" y1="5" x2="12" y2="18" stroke-width="2.2" /><line x1="18" y1="12" x2="18" y2="18" stroke-width="2.2" />`,
    'sparkles': `<path d="M12 2.5 L14 8.5 L20 10.5 L14 12.5 L12 18.5 L10 12.5 L4 10.5 L10 8.5 Z" /><path d="M18.5 16.5 L19.5 19.5 L22.5 20.5 L19.5 21.5 L18.5 24.5 L17.5 21.5 L14.5 20.5 L17.5 19.5 Z" />`,
    'book-open': `<path d="M3 19 C5.5 18 8.5 18 12 19.5 C15.5 18 18.5 18 21 19 V5.5 C18.5 4.5 15.5 4.5 12 6 C8.5 4.5 5.5 4.5 3 5.5 V19 Z" /><line x1="12" y1="6" x2="12" y2="19.5" />`,
    'wifi-off': `<line x1="2" y1="3" x2="22" y2="21" /><path d="M8.5 8.5 C9.6 7.8 10.8 7.5 12 7.5 C15.8 7.5 19.2 9.2 21.5 12" /><path d="M1.5 12 C3.3 10.1 5.7 8.9 8.5 8.5" /><path d="M5.5 15.5 C7.2 14.3 9.5 13.5 12 13.5 C13.2 13.5 14.4 13.8 15.5 14.3" /><circle cx="12" cy="18" r="1" />`,
    'shield': `<path d="M12 3 L4 6.5 V12 C4 17 7.5 20.5 12 21.5 C16.5 20.5 20 17 20 12 V6.5 L12 3 Z" />`,
    'lanes': `<polygon points="3,8 12,4 21,8 12,12" /><polyline points="3,13 12,17 21,13" /><polyline points="3,17.5 12,21.5 21,17.5" />`,
    'install': `<rect x="5" y="3" width="14" height="18" rx="2" /><line x1="12" y1="8" x2="12" y2="14" /><polyline points="9,11 12,14 15,11" /><circle cx="12" cy="17.5" r="0.6" fill="currentColor" />`,
    'send': `<path d="M21 3 L3 10.5 L10.5 13.5 L13.5 21 L21 3 Z" /><line x1="10.5" y1="13.5" x2="21" y2="3" />`,
    'logout': `<polyline points="10,17.5 15,12 10,6.5" /><line x1="15" y1="12" x2="4" y2="12" /><path d="M14 3.5 H19 C19.6 3.5 20 3.9 20 4.5 V19.5 C20 20.1 19.6 20.5 19 20.5 H14" />`,
    'video': `<rect x="2" y="6.5" width="14" height="11" rx="2" /><polygon points="16,10 22,7 22,17 16,14" />`
};

let spriteContent = `<svg xmlns="http://www.w3.org/2000/svg" style="display: none;">\n`;
for (const [name, inner] of Object.entries(ICONS)) {
    spriteContent += `  <symbol id="icon-${name}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round">\n`;
    spriteContent += `    ${inner}\n`;
    spriteContent += `  </symbol>\n`;
}
spriteContent += `</svg>\n`;

const spritePath = path.join(srcIconsDir, 'icons.svg');
fs.writeFileSync(spritePath, spriteContent, 'utf8');
console.log(`  ✓ Master sprite generated with ${Object.keys(ICONS).length} symbols at: ${spritePath}`);

// 3. Generate Raster PNG & ICO Assets via PowerShell System.Drawing script
console.log('\n3. Generating raster assets (PNGs & Favicon bundle)...');

const psScript = `
Add-Type -AssemblyName System.Drawing

function Draw-VibeBrandMark($graphics, $width, $height, $bgHex, $markHex, $offsetYPercent, $artBoxPercent, $strokeRatio) {
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality

    if ($bgHex -ne $null -and $bgHex -ne "") {
        $bgColor = [System.Drawing.ColorTranslator]::FromHtml($bgHex)
        $bgBrush = New-Object System.Drawing.SolidBrush($bgColor)
        $graphics.FillRectangle($bgBrush, 0, 0, $width, $height)
        $bgBrush.Dispose()
    }

    $markColor = [System.Drawing.ColorTranslator]::FromHtml($markHex)
    $strokePx = [Math]::Max(1.0, ($height * $strokeRatio))
    $pen = New-Object System.Drawing.Pen($markColor, $strokePx)
    $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $pen.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round

    $artSize = $height * $artBoxPercent
    $scale = $artSize / 24.0
    $offsetX = ($width - $artSize) / 2.0
    $offsetY = (($height - $artSize) / 2.0) + ($height * ($offsetYPercent / 100.0))

    # Outer Organic Wing: (3.5, 4.5) -> (12, 20.5) -> (20.5, 4.5) with bezier
    $path1 = New-Object System.Drawing.Drawing2D.GraphicsPath
    $p1_start = New-Object System.Drawing.PointF(($offsetX + (3.5 * $scale)), ($offsetY + (4.5 * $scale)))
    $p1_c1    = New-Object System.Drawing.PointF(($offsetX + (5.5 * $scale)), ($offsetY + (12.5 * $scale)))
    $p1_c2    = New-Object System.Drawing.PointF(($offsetX + (8.5 * $scale)), ($offsetY + (18.5 * $scale)))
    $p1_mid   = New-Object System.Drawing.PointF(($offsetX + (12.0 * $scale)), ($offsetY + (20.5 * $scale)))
    $p1_c3    = New-Object System.Drawing.PointF(($offsetX + (15.5 * $scale)), ($offsetY + (18.5 * $scale)))
    $p1_c4    = New-Object System.Drawing.PointF(($offsetX + (18.5 * $scale)), ($offsetY + (12.5 * $scale)))
    $p1_end   = New-Object System.Drawing.PointF(($offsetX + (20.5 * $scale)), ($offsetY + (4.5 * $scale)))

    $path1.AddBezier($p1_start, $p1_c1, $p1_c2, $p1_mid)
    $path1.AddBezier($p1_mid, $p1_c3, $p1_c4, $p1_end)
    $graphics.DrawPath($pen, $path1)
    $path1.Dispose()

    # Inner Resonant V: (7.5, 4.5) -> (12, 13.5) -> (16.5, 4.5)
    $path2 = New-Object System.Drawing.Drawing2D.GraphicsPath
    $p2_start = New-Object System.Drawing.PointF(($offsetX + (7.5 * $scale)), ($offsetY + (4.5 * $scale)))
    $p2_c1    = New-Object System.Drawing.PointF(($offsetX + (9.0 * $scale)), ($offsetY + (9.5 * $scale)))
    $p2_c2    = New-Object System.Drawing.PointF(($offsetX + (10.5 * $scale)), ($offsetY + (12.0 * $scale)))
    $p2_mid   = New-Object System.Drawing.PointF(($offsetX + (12.0 * $scale)), ($offsetY + (13.5 * $scale)))
    $p2_c3    = New-Object System.Drawing.PointF(($offsetX + (13.5 * $scale)), ($offsetY + (12.0 * $scale)))
    $p2_c4    = New-Object System.Drawing.PointF(($offsetX + (15.0 * $scale)), ($offsetY + (9.5 * $scale)))
    $p2_end   = New-Object System.Drawing.PointF(($offsetX + (16.5 * $scale)), ($offsetY + (4.5 * $scale)))

    $path2.AddBezier($p2_start, $p2_c1, $p2_c2, $p2_mid)
    $path2.AddBezier($p2_mid, $p2_c3, $p2_c4, $p2_end)
    $graphics.DrawPath($pen, $path2)
    $path2.Dispose()

    # Vertical Spine & Base Ballast
    $graphics.DrawLine($pen, [float]($offsetX + (12.0 * $scale)), [float]($offsetY + (13.5 * $scale)), [float]($offsetX + (12.0 * $scale)), [float]($offsetY + (17.5 * $scale)))
    $graphics.DrawLine($pen, [float]($offsetX + (9.8 * $scale)), [float]($offsetY + (20.5 * $scale)), [float]($offsetX + (14.2 * $scale)), [float]($offsetY + (20.5 * $scale)))

    $pen.Dispose()
}

function Generate-Png($filePath, $size, $bgHex, $markHex, $offsetYPercent, $artBoxPercent, $strokeRatio) {
    $bmp = New-Object System.Drawing.Bitmap($size, $size, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    Draw-VibeBrandMark $g $size $size $bgHex $markHex $offsetYPercent $artBoxPercent $strokeRatio
    $g.Dispose()
    $bmp.Save($filePath, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Write-Host "Generated $filePath ($size x $size)"
}

# 1. Favicon 16x16 & 32x32 (Transparent background, Warm Amber #E5A93C)
Generate-Png "${path.join(srcIconsDir, 'favicon-16.png').replace(/\\/g, '/')}" 16 "" "#E5A93C" 0 0.88 0.088
Generate-Png "${path.join(srcIconsDir, 'favicon-32.png').replace(/\\/g, '/')}" 32 "" "#E5A93C" 0 0.85 0.082

# 2. PWA Icon 192x192 & 512x512 (#0C0D11 Warm Obsidian background, Warm Amber #E5A93C)
Generate-Png "${path.join(publicIconsDir, 'icon-192.png').replace(/\\/g, '/')}" 192 "#0C0D11" "#E5A93C" -3.2 0.62 0.077
Generate-Png "${path.join(publicIconsDir, 'icon-512.png').replace(/\\/g, '/')}" 512 "#0C0D11" "#E5A93C" -3.2 0.62 0.077

# 3. Maskable Icon 512x512 (>10% safe margin, art box 52%, -3.2% optical offset)
Generate-Png "${path.join(publicIconsDir, 'icon-maskable-512.png').replace(/\\/g, '/')}" 512 "#0C0D11" "#E5A93C" -3.2 0.52 0.077

# 4. Apple Touch Icon 180x180
Generate-Png "${path.join(publicIconsDir, 'apple-touch-icon.png').replace(/\\/g, '/')}" 180 "#0C0D11" "#E5A93C" -3.2 0.62 0.077

# 5. High-Res Logo fallback (replaces legacy 481 KB cartoon illustration)
Generate-Png "${path.join(publicIconsDir, 'logo.png').replace(/\\/g, '/')}" 512 "#0C0D11" "#E5A93C" -3.2 0.62 0.077

# 6. Build favicon.ico containing 16x16 icon
$icoPath = "${path.join(srcIconsDir, 'favicon.ico').replace(/\\/g, '/')}"
$bmp16 = New-Object System.Drawing.Bitmap(16, 16, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$g16 = [System.Drawing.Graphics]::FromImage($bmp16)
Draw-VibeBrandMark $g16 16 16 "" "#E5A93C" 0 0.88 0.088
$g16.Dispose()

$hIcon = $bmp16.GetHicon()
$icon = [System.Drawing.Icon]::FromHandle($hIcon)
$fs = New-Object System.IO.FileStream($icoPath, [System.IO.FileMode]::Create)
$icon.Save($fs)
$fs.Close()
$icon.Dispose()
$bmp16.Dispose()
Write-Host "Generated $icoPath"
`;

const psPath = path.join(rootDir, 'tools', 'generate-icons.ps1');
fs.writeFileSync(psPath, psScript, 'utf8');

execSync(`powershell -ExecutionPolicy Bypass -File "${psPath}"`, { stdio: 'inherit' });

console.log('\nAsset generation complete!');
