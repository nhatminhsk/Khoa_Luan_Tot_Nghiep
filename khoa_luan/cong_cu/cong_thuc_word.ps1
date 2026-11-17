param([string]$Docx, [string]$Out)
# Mở bản sao khóa luận, chuyển mọi công thức sang dạng chữ UnicodeMath (Linearize), ghi ra JSON theo thứ tự xuất hiện.
$ErrorActionPreference = "Stop"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($Docx, $false, $true)
    $list = @()
    $n = $doc.OMaths.Count
    for ($i = 1; $i -le $n; $i++) {
        $om = $doc.OMaths.Item($i)
        $kieu = $om.Type          # 0 = hiển thị, 1 = trong dòng
        $om.Linearize()
        $txt = $doc.OMaths.Item($i).Range.Text
        $para = $doc.OMaths.Item($i).Range.Paragraphs.Item(1).Range.Text
        $list += [pscustomobject]@{ i = $i; kieu = $kieu; text = $txt; doan = $para.Substring(0, [Math]::Min(80, $para.Length)) }
    }
    $list | ConvertTo-Json -Depth 3 | Out-File -FilePath $Out -Encoding utf8
    Write-Output "Công thức: $n"
    $doc.Close($false)
} finally {
    $word.Quit()
}
