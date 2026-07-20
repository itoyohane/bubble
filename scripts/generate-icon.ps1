$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Drawing

$iconDirectory = Join-Path $PSScriptRoot "..\apps\desktop\src-tauri\icons"
New-Item -ItemType Directory -Force -Path $iconDirectory | Out-Null

$size = 256
$bitmap = [System.Drawing.Bitmap]::new($size, $size)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit

try {
    $background = [System.Drawing.ColorTranslator]::FromHtml("#12372A")
    $accent = [System.Drawing.ColorTranslator]::FromHtml("#C9F55A")
    $ink = [System.Drawing.ColorTranslator]::FromHtml("#102A22")
    $graphics.Clear($background)

    $accentBrush = [System.Drawing.SolidBrush]::new($accent)
    $inkBrush = [System.Drawing.SolidBrush]::new($ink)
    try {
        $graphics.FillEllipse($accentBrush, 26, 26, 204, 204)
        $font = [System.Drawing.Font]::new("Arial", 122, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
        try {
            $format = [System.Drawing.StringFormat]::new()
            $format.Alignment = [System.Drawing.StringAlignment]::Center
            $format.LineAlignment = [System.Drawing.StringAlignment]::Center
            $graphics.DrawString("B", $font, $inkBrush, [System.Drawing.RectangleF]::new(26, 22, 204, 204), $format)
            $format.Dispose()
        }
        finally {
            $font.Dispose()
        }
    }
    finally {
        $accentBrush.Dispose()
        $inkBrush.Dispose()
    }

    $pngPath = Join-Path $iconDirectory "icon.png"
    $bitmap.Save($pngPath, [System.Drawing.Imaging.ImageFormat]::Png)
}
finally {
    $graphics.Dispose()
    $bitmap.Dispose()
}

$pngBytes = [System.IO.File]::ReadAllBytes((Join-Path $iconDirectory "icon.png"))
$iconPath = Join-Path $iconDirectory "icon.ico"
$stream = [System.IO.File]::Create($iconPath)
$writer = [System.IO.BinaryWriter]::new($stream)
try {
    $writer.Write([uint16]0)
    $writer.Write([uint16]1)
    $writer.Write([uint16]1)
    $writer.Write([byte]0)
    $writer.Write([byte]0)
    $writer.Write([byte]0)
    $writer.Write([byte]0)
    $writer.Write([uint16]1)
    $writer.Write([uint16]32)
    $writer.Write([uint32]$pngBytes.Length)
    $writer.Write([uint32]22)
    $writer.Write($pngBytes)
}
finally {
    $writer.Dispose()
}

Write-Output $iconPath
