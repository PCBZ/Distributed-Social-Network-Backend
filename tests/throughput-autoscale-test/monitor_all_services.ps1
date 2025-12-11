# Real-time ECS Service Monitor
# Monitors all 5 services: task count, CPU, Memory every 30 seconds

param(
    [int]$IntervalSeconds = 30,
    [int]$DurationMinutes = 20
)

$services = @(
    @{Name="timeline-service"; Cluster="timeline-service"},
    @{Name="post-service"; Cluster="post-service"},
    @{Name="user-service"; Cluster="user-service"},
    @{Name="social-graph-service"; Cluster="social-graph-service"},
    @{Name="web-service"; Cluster="web-service"}
)

$endTime = (Get-Date).AddMinutes($DurationMinutes)
$outputFile = "results/service_monitor_$(Get-Date -Format 'yyyy-MM-dd_HHmmss').csv"

# Create CSV header
"Timestamp,Service,DesiredTasks,RunningTasks,PendingTasks,CPUAvg,MemAvg" | Out-File -FilePath $outputFile

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "ECS Service Real-time Monitor" -ForegroundColor Cyan
Write-Host "Monitoring 5 services every $IntervalSeconds seconds" -ForegroundColor Cyan
Write-Host "Duration: $DurationMinutes minutes" -ForegroundColor Cyan
Write-Host "Output: $outputFile" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$iteration = 0

while ((Get-Date) -lt $endTime) {
    $iteration++
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    Write-Host "[$timestamp] Iteration $iteration" -ForegroundColor Yellow
    Write-Host ("-" * 80)
    
    foreach ($svc in $services) {
        try {
            # Get service details
            $serviceResult = aws ecs describe-services --cluster $svc.Cluster --services $svc.Name --output json 2>&1
            
            # Check if result is an error
            if ($serviceResult -is [string] -and ($serviceResult -like "*error*" -or $serviceResult -like "*Could not*")) {
                Write-Host "✗ $($svc.Name.PadRight(20)) AWS Error: $($serviceResult.Substring(0, [Math]::Min(50, $serviceResult.Length)))" -ForegroundColor Red
                continue
            }
            
            # Try to parse JSON
            try {
                $serviceJson = $serviceResult | ConvertFrom-Json
            } catch {
                Write-Host "✗ $($svc.Name.PadRight(20)) JSON Parse Error" -ForegroundColor Red
                continue
            }
            
            if ($serviceJson.services -and $serviceJson.services.Count -gt 0) {
                $desired = $serviceJson.services[0].desiredCount
                $running = $serviceJson.services[0].runningCount
                $pending = $serviceJson.services[0].pendingCount
            } else {
                Write-Host "✗ $($svc.Name.PadRight(20)) Service not found" -ForegroundColor Red
                continue
            }
            
            # Get CPU/Memory from CloudWatch (last 5 minutes average)
            $endTimeUtc = (Get-Date).ToUniversalTime()
            $startTimeUtc = $endTimeUtc.AddMinutes(-5)
            
            # CPU - get all datapoints and average them
            $cpuResult = aws cloudwatch get-metric-statistics `
                --namespace AWS/ECS `
                --metric-name CPUUtilization `
                --dimensions Name=ServiceName,Value=$($svc.Name) Name=ClusterName,Value=$($svc.Cluster) `
                --start-time $startTimeUtc.ToString("yyyy-MM-ddTHH:mm:ss") `
                --end-time $endTimeUtc.ToString("yyyy-MM-ddTHH:mm:ss") `
                --period 300 `
                --statistics Average `
                --output json 2>$null
            
            $cpuAvg = "N/A"
            if ($cpuResult) {
                $cpuJson = $cpuResult | ConvertFrom-Json
                if ($cpuJson.Datapoints -and $cpuJson.Datapoints.Count -gt 0) {
                    $cpuValues = $cpuJson.Datapoints | ForEach-Object { $_.Average }
                    $cpuAvg = [math]::Round(($cpuValues | Measure-Object -Average).Average, 1)
                }
            }
            
            # Memory - get all datapoints and average them
            $memResult = aws cloudwatch get-metric-statistics `
                --namespace AWS/ECS `
                --metric-name MemoryUtilization `
                --dimensions Name=ServiceName,Value=$($svc.Name) Name=ClusterName,Value=$($svc.Cluster) `
                --start-time $startTimeUtc.ToString("yyyy-MM-ddTHH:mm:ss") `
                --end-time $endTimeUtc.ToString("yyyy-MM-ddTHH:mm:ss") `
                --period 300 `
                --statistics Average `
                --output json 2>$null
            
            $memAvg = "N/A"
            if ($memResult) {
                $memJson = $memResult | ConvertFrom-Json
                if ($memJson.Datapoints -and $memJson.Datapoints.Count -gt 0) {
                    $memValues = $memJson.Datapoints | ForEach-Object { $_.Average }
                    $memAvg = [math]::Round(($memValues | Measure-Object -Average).Average, 1)
                }
            }
            
            # Display
            $status = if ($running -eq $desired) { "✓" } else { "⚠" }
            Write-Host "$status $($svc.Name.PadRight(20)) Tasks: $desired/$running/$pending  CPU: $cpuAvg%  Mem: $memAvg%" -ForegroundColor $(if ($running -eq $desired) { "Green" } else { "Yellow" })
            
            # Save to CSV
            "$timestamp,$($svc.Name),$desired,$running,$pending,$cpuAvg,$memAvg" | Out-File -FilePath $outputFile -Append
        }
        catch {
            Write-Host "✗ $($svc.Name.PadRight(20)) Exception: $_" -ForegroundColor Red
        }
    }
    
    Write-Host ""
    
    if ((Get-Date) -lt $endTime) {
        Start-Sleep -Seconds $IntervalSeconds
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Monitoring completed!" -ForegroundColor Cyan
Write-Host "Results saved to: $outputFile" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan
