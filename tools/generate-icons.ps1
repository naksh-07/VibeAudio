
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
Generate-Png "C:/Users/Suraj/Documents/Antigravity/VibeAudio-main/VibeAudio-main/frontend/src/icons/favicon-16.png" 16 "" "#E5A93C" 0 0.88 0.088
Generate-Png "C:/Users/Suraj/Documents/Antigravity/VibeAudio-main/VibeAudio-main/frontend/src/icons/favicon-32.png" 32 "" "#E5A93C" 0 0.85 0.082

# 2. PWA Icon 192x192 & 512x512 (#0C0D11 Warm Obsidian background, Warm Amber #E5A93C)
Generate-Png "C:/Users/Suraj/Documents/Antigravity/VibeAudio-main/VibeAudio-main/frontend/public/icons/icon-192.png" 192 "#0C0D11" "#E5A93C" -3.2 0.62 0.077
Generate-Png "C:/Users/Suraj/Documents/Antigravity/VibeAudio-main/VibeAudio-main/frontend/public/icons/icon-512.png" 512 "#0C0D11" "#E5A93C" -3.2 0.62 0.077

# 3. Maskable Icon 512x512 (>10% safe margin, art box 52%, -3.2% optical offset)
Generate-Png "C:/Users/Suraj/Documents/Antigravity/VibeAudio-main/VibeAudio-main/frontend/public/icons/icon-maskable-512.png" 512 "#0C0D11" "#E5A93C" -3.2 0.52 0.077

# 4. Apple Touch Icon 180x180
Generate-Png "C:/Users/Suraj/Documents/Antigravity/VibeAudio-main/VibeAudio-main/frontend/public/icons/apple-touch-icon.png" 180 "#0C0D11" "#E5A93C" -3.2 0.62 0.077

# 5. High-Res Logo fallback (replaces legacy 481 KB cartoon illustration)
Generate-Png "C:/Users/Suraj/Documents/Antigravity/VibeAudio-main/VibeAudio-main/frontend/public/icons/logo.png" 512 "#0C0D11" "#E5A93C" -3.2 0.62 0.077

# 6. Build favicon.ico containing 16x16 icon
$icoPath = "C:/Users/Suraj/Documents/Antigravity/VibeAudio-main/VibeAudio-main/frontend/src/icons/favicon.ico"
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
