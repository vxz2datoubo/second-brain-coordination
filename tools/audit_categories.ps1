$json = Get-Content 'F:\ai\data\knowledge-graph.json' -Raw -Encoding UTF8 | ConvertFrom-Json
$nodes = $json.nodes
$props = @($nodes.PSObject.Properties)
$total = $props.Count
Write-Host "总节点数: $total"

$cats = @{}
$sources = @{}
foreach ($p in $props) {
    $n = $p.Value
    $c = if ($n.category) { $n.category } else { 'unknown' }
    $cats[$c] = [int]($cats[$c]) + 1
    $s = if ($n.source) { $n.source } else { 'unknown' }
    $sources[$s] = [int]($sources[$s]) + 1
}

Write-Host "`n=== 分类分布 ==="
foreach ($c in ($cats.GetEnumerator() | Sort-Object Value -Descending)) {
    $pct = [math]::Round([int]$c.Value / $total * 100, 1)
    Write-Host "  $($c.Key): $($c.Value) ($pct%)"
}

Write-Host "`n=== 来源分布(合并前5大类) ==="
$sourceGroups = @{}
foreach ($p in $props) {
    $n = $p.Value
    $raw = if ($n.source) { $n.source } else { 'unknown' }
    if ($raw -match '^workbuddy-session') { $group = 'workbuddy-session' }
    elseif ($raw -match '^workbuddy-memory') { $group = 'workbuddy-memory' }
    elseif ($raw -match '^project-memory') { $group = 'project-memory' }
    elseif ($raw -match '^conversation') { $group = 'conversation' }
    elseif ($raw -match '^user-file') { $group = 'user-file' }
    else { $group = $raw }
    $sourceGroups[$group] = [int]($sourceGroups[$group]) + 1
}
foreach ($g in ($sourceGroups.GetEnumerator() | Sort-Object Value -Descending)) {
    $pct = [math]::Round([int]$g.Value / $total * 100, 1)
    Write-Host "  $($g.Key): $($g.Value) ($pct%)"
}

Write-Host "`n=== 来源x分类交叉 ==="
$cross = @{}
foreach ($p in $props) {
    $n = $p.Value
    $raw = if ($n.source) { $n.source } else { 'unknown' }
    if ($raw -match '^workbuddy-session') { $group = 'workbuddy-session' }
    elseif ($raw -match '^workbuddy-memory') { $group = 'workbuddy-memory' }
    elseif ($raw -match '^project-memory') { $group = 'project-memory' }
    elseif ($raw -match '^conversation') { $group = 'conversation' }
    elseif ($raw -match '^user-file') { $group = 'user-file' }
    else { $group = $raw }
    $c = if ($n.category) { $n.category } else { 'unknown' }
    $key = "$group -> $c"
    $cross[$key] = [int]($cross[$key]) + 1
}
foreach ($k in ($cross.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 20)) {
    Write-Host "  $($k.Key): $($k.Value)"
}

Write-Host "`n=== 标签质量 ==="
$allTags = @{}
$singleChar = @{}
foreach ($p in $props) {
    $n = $p.Value
    foreach ($t in $n.tags) {
        $allTags[$t] = [int]($allTags[$t]) + 1
        if ($t.Length -le 1) { $singleChar[$t] = [int]($singleChar[$t]) + 1 }
    }
}
Write-Host "  唯一标签: $($allTags.Count)"
Write-Host "  单字标签: $($singleChar.Count) 种, 共 $(($singleChar.Values | Measure-Object -Sum).Sum) 次"
Write-Host "  有效标签(>=2字): $(($allTags.GetEnumerator() | Where-Object { $_.Key.Length -ge 2 }).Count) 种"
Write-Host "`n  有效标签 Top30:"
$valid = $allTags.GetEnumerator() | Where-Object { $_.Key.Length -ge 2 } | Sort-Object Value -Descending | Select-Object -First 30
foreach ($t in $valid) {
    Write-Host "    $($t.Key): $($t.Value)"
}
