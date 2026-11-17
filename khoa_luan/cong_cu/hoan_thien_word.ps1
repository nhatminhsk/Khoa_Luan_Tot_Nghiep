# Hoàn thiện file khóa luận bằng Microsoft Word:
#   1. dựng công thức (OMML) từ các đoạn EQ{{...}}EQ do build_docx.py để lại
#   2. cập nhật mục lục, danh mục bảng, danh mục hình
#   3. lưu lại .docx và xuất .pdf
# Chạy: powershell -ExecutionPolicy Bypass -File khoa_luan\cong_cu\hoan_thien_word.ps1
param(
    [string]$Docx = (Join-Path $PSScriptRoot "..\dau_ra\khoa_luan.docx"),
    [switch]$KhongXuatPdf
)
$ErrorActionPreference = "Stop"
$Docx = (Resolve-Path $Docx).Path
$Pdf = [System.IO.Path]::ChangeExtension($Docx, ".pdf")

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($Docx, $false, $false)

    # 1. Công thức
    $soCongThuc = 0
    while ($true) {
        $rng = $doc.Content
        $f = $rng.Find
        $f.ClearFormatting()
        $f.Text = "EQ{{"
        $f.MatchWildcards = $false
        if (-not $f.Execute()) { break }
        $start = $rng.Start
        $rng.Text = ""                       # xóa dấu mốc mở
        $rng2 = $doc.Range($start, $doc.Content.End)
        $f2 = $rng2.Find
        $f2.Text = "}}EQ"
        if (-not $f2.Execute()) { throw "Thiếu dấu mốc đóng công thức" }
        $end = $rng2.Start
        $rng2.Text = ""                      # xóa dấu mốc đóng
        $eq = $doc.Range($start, $end)
        $om = $doc.OMaths.Add($eq)
        $om.OMaths.Item(1).BuildUp()
        $soCongThuc++
    }
    Write-Output "Công thức đã dựng: $soCongThuc"

    # 2. Trường tự động (cập nhật hai lần để số trang ổn định)
    for ($k = 0; $k -lt 2; $k++) {
        foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
        $doc.Fields.Update() | Out-Null
    }
    Write-Output "Mục lục và danh mục: $($doc.TablesOfContents.Count) trường"

    # Thuộc tính tài liệu: bỏ tên công ty / người soạn mẫu
    foreach ($p in @("Company", "Manager")) {
        try { $doc.BuiltInDocumentProperties.Item($p).Value = "" } catch {}
    }

    $doc.Save()
    if (-not $KhongXuatPdf) {
        $doc.ExportAsFixedFormat($Pdf, 17)   # 17 = wdExportFormatPDF
        Write-Output "Đã xuất $Pdf"
    }
    Write-Output "Số trang: $($doc.ComputeStatistics(2))"
    $doc.Close($false)
}
finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
