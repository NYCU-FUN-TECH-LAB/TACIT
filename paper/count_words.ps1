# count_words.ps1 -- measure the SoftwareX main-text word count.
#
#   powershell -ExecutionPolicy Bypass -File count_words.ps1
#
# This file is deliberately pure ASCII. Windows PowerShell 5.1 reads a .ps1
# as the system ANSI code page unless the file carries a UTF-8 BOM, so any
# non-ASCII character in a comment or a string is enough to break parsing
# with errors that point at the wrong lines entirely.
#
# Three numbers are reported, because "around 3000 words" means the prose:
#   total        every word between the section 1 heading and Acknowledgements
#   minus tables the same, with Table 3-6 cell contents removed
#   minus TODO   the same, with the red TO FILL / TO MEASURE markers removed.
#                That last figure is the one that will be submitted.

$ErrorActionPreference = 'Stop'
$docx = Join-Path $PSScriptRoot 'TACIT_SoftwareX_manuscript.docx'
if (-not (Test-Path $docx)) { throw "No $docx -- run npm run build first" }

# Say which build this is. Two rounds of edits once produced byte-identical
# counts because the .docx being measured was older than the edits -- Word
# holding the file open, or a rebuild that never ran. A count with no
# timestamp cannot tell you that, and you spend the next round confused.
$built = (Get-Item $docx).LastWriteTime
$src   = (Get-Item (Join-Path $PSScriptRoot 'build_paper.js')).LastWriteTime
'docx built        {0}' -f $built.ToString('yyyy-MM-dd HH:mm:ss')
'build_paper.js    {0}' -f $src.ToString('yyyy-MM-dd HH:mm:ss')
if ($src -gt $built) {
    Write-Warning 'The source is NEWER than the .docx. These numbers are stale -- run npm run build.'
}
''

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [IO.Compression.ZipFile]::OpenRead($docx)
try {
    $entry  = $zip.GetEntry('word/document.xml')
    $reader = New-Object IO.StreamReader($entry.Open())
    $xml    = $reader.ReadToEnd()
    $reader.Dispose()
} finally { $zip.Dispose() }

# The angle brackets around the TODO markers are U+3008 / U+3009. Built by
# code point so this file stays ASCII.
$OPEN  = [char]0x3008
$CLOSE = [char]0x3009

function Get-Text([string]$x) {
    # Put a space before each paragraph end, or adjacent paragraphs merge
    # into one word and the count comes out low.
    $t = [regex]::Replace($x, '</w:p>', ' </w:p>')
    $t = [regex]::Replace($t, '<[^>]+>', '')
    $t = $t -replace '&amp;', '&' -replace '&lt;', '<' -replace '&gt;', '>' -replace '&quot;', '"' -replace '&apos;', "'"
    return [regex]::Replace($t, '\s+', ' ').Trim()
}

function Count-Words([string]$t) {
    if ([string]::IsNullOrWhiteSpace($t)) { return 0 }
    return ($t -split '\s+').Count
}

function Get-Body([string]$t) {
    # Main text = section 1 heading up to Acknowledgements. The metadata
    # tables before it and the references after it do not count.
    $i = $t.IndexOf('1. Motivation and significance')
    $j = $t.IndexOf('Acknowledgements')
    if ($i -lt 0 -or $j -lt 0 -or $j -le $i) {
        throw 'Section markers not found -- were the headings renamed?'
    }
    return $t.Substring($i, $j - $i)
}

$stripped = [regex]::Replace($xml, '(?s)<w:tbl>.*?</w:tbl>', ' ')

$all      = Get-Body (Get-Text $xml)
$noTables = Get-Body (Get-Text $stripped)
$final    = [regex]::Replace($noTables, "$OPEN[^$CLOSE]*$CLOSE", ' ')

'{0,-34}{1,6}' -f 'total (tables + TODO markers)', (Count-Words $all)
'{0,-34}{1,6}' -f 'minus table contents',          (Count-Words $noTables)
'{0,-34}{1,6}' -f 'minus TODO markers  <-- this',  (Count-Words $final)
''

# Per-section breakdown of that last figure. Guessing where the words are
# wastes a build-and-measure round trip each time; this says outright.
$marks = @(
    '1. Motivation and significance',
    '2. Software description',
    '2.1. Software architecture',
    '2.2. Software functionalities',
    '2.3. Two routes to a codebook',
    '2.4. Long transcripts and model providers',
    '3. Illustrative examples',
    '4. Impact',
    '5. Conclusions'
)
$pos = @()
foreach ($m in $marks) {
    $k = $final.IndexOf($m)
    if ($k -lt 0) { Write-Warning "heading not found: $m" } else { $pos += ,@($m, $k) }
}
'by section:'
for ($i = 0; $i -lt $pos.Count; $i++) {
    $start = $pos[$i][1]
    $end   = if ($i + 1 -lt $pos.Count) { $pos[$i + 1][1] } else { $final.Length }
    $n     = Count-Words $final.Substring($start, $end - $start)
    '  {0,-44}{1,6}' -f $pos[$i][0], $n
}
