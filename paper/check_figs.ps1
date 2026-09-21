# check_figs.ps1 -- will the figure text still be legible after Elsevier
# scales it to the column width?
#
#   powershell -ExecutionPolicy Bypass -File check_figs.ps1
#
# Pure ASCII on purpose: Windows PowerShell 5.1 reads a .ps1 as the system
# ANSI code page unless the file has a UTF-8 BOM.
#
# A figure is placed 6.27 in wide (A4 minus 1 in margins), so a glyph that
# occupies a fraction f of the image width prints at f * 6.27 * 72 points.
# Elsevier asks for 7 pt or larger.
#
# The two kinds of figure here need different treatment, and an earlier
# version of this script got that wrong -- it applied the screenshot rule
# to the vector figures and reported 1.8 pt for a figure that is actually
# 7.9 pt by construction.
#
#   Vector figures  have a .svg beside the .png. The answer is exact: read
#                   the viewBox width and the smallest font-size, and the
#                   pixel size of the .png is irrelevant.
#
#   Screenshots     have no .svg. Nothing in the file records how tall the
#                   glyphs are, so the script cannot decide. It reports the
#                   minimum glyph height instead, which you can compare with
#                   what your browser was actually rendering.

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$FIG_WIDTH_IN = 6.27
$MIN_PT       = 7.0
$PT_PER_WIDTH = $FIG_WIDTH_IN * 72    # points across the placed figure

$files = Get-ChildItem -Path $PSScriptRoot -Filter 'fig*.png' | Sort-Object Name
if (-not $files) { throw "No fig*.png in $PSScriptRoot" }

foreach ($f in $files) {
    $img = [System.Drawing.Image]::FromFile($f.FullName)
    try { $w = $img.Width; $h = $img.Height } finally { $img.Dispose() }

    $svg = [IO.Path]::ChangeExtension($f.FullName, '.svg')
    if (Test-Path $svg) {
        $text = Get-Content $svg -Raw

        $vb = [regex]::Match($text, 'viewBox\s*=\s*"[\d.\-]+\s+[\d.\-]+\s+([\d.]+)\s+([\d.]+)"')
        if (-not $vb.Success) {
            '{0,-34} {1} px   vector, but no viewBox found -- check by hand' -f $f.Name, "$w x $h"
            continue
        }
        $vbw = [double]$vb.Groups[1].Value

        # Two spellings, and missing the second one is how fig6 passed
        # unnoticed for weeks: a CSS declaration inside <style> looks like
        # font-size:21px, while a presentation attribute on a <text> element
        # looks like font-size="10.5". Both are valid SVG.
        $sizes = @()
        $sizes += [regex]::Matches($text, 'font-size\s*:\s*([\d.]+)\s*px') |
                  ForEach-Object { [double]$_.Groups[1].Value }
        $sizes += [regex]::Matches($text, 'font-size\s*=\s*"([\d.]+)(?:px)?"') |
                  ForEach-Object { [double]$_.Groups[1].Value }
        if (-not $sizes) {
            '{0,-34} {1} px   vector, no font-size declared -- check by hand' -f $f.Name, "$w x $h"
            continue
        }
        $minPx = ($sizes | Measure-Object -Minimum).Minimum
        $pt    = [math]::Round($minPx * $PT_PER_WIDTH / $vbw, 1)
        $ok    = if ($pt -ge $MIN_PT) { 'OK' } else { 'FAIL' }

        '{0,-34} {1,11} px   vector' -f $f.Name, "$w x $h"
        '    viewBox {0} wide, smallest font {1} px  ->  {2} pt   {3}' -f $vbw, $minPx, $pt, $ok
    }
    else {
        # For a screenshot, 7 pt after scaling means the glyph must occupy
        # at least 7 / (6.27*72) of the image width.
        $need = [math]::Ceiling($MIN_PT * $w / $PT_PER_WIDTH)
        '{0,-34} {1,11} px   screenshot' -f $f.Name, "$w x $h"
        '    body text must be at least {0} px tall in this capture' -f $need
        '    (Streamlit renders about 14 px at 100% zoom, 21 px at 150%)'
        if ($need -gt 21) {
            '    -> too wide for a 150% capture. Crop narrower, or zoom further.'
        } elseif ($need -gt 14) {
            '    -> fine if captured at 150%; not fine at 100%.'
        } else {
            '    -> fine at any zoom.'
        }
    }
    ''
}
