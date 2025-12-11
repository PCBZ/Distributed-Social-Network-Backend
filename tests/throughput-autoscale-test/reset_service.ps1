#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Reset ECS service to baseline state after load testing
    
.DESCRIPTION
    Scales down the service to baseline task count and waits for stabilization
    Use this between tests to ensure clean starting conditions
    
.PARAMETER ServiceName
    Name of the ECS service to reset
    
.PARAMETER BaselineCount
    Number of tasks to scale down to (default: 2)
    
.EXAMPLE
    .\reset_service.ps1 -ServiceName timeline-service -BaselineCount 2
#>

param(
    [string]$ServiceName = 'timeline-service',
    [string]$ClusterName = 'cs6650-project-dev-cluster',
    [int]$BaselineCount = 2,
    [string]$AwsRegion = 'us-west-2',
    [int]$WaitMinutes = 5
)

$ErrorActionPreference = 'Stop'

function Write-Step($msg) { Write-Host "`n[STEP] $msg" -ForegroundColor Cyan }
function Write-Success($msg) { Write-Host "[✓] $msg" -ForegroundColor Green }
function Write-Error-Custom($msg) { Write-Host "[✗] $msg" -ForegroundColor Red }
function Write-Info($msg) { Write-Host "[ℹ] $msg" -ForegroundColor Yellow }

Write-Host @"

╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║              Reset ECS Service to Baseline State                   ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

Write-Info "Service: $ServiceName"
Write-Info "Cluster: $ClusterName"
Write-Info "Target Task Count: $BaselineCount"
Write-Info "Region: $AwsRegion`n"

# Get current service state
Write-Step "Checking current service state..."
try {
    $serviceInfo = aws ecs describe-services `
        --cluster $ClusterName `
        --services $ServiceName `
        --region $AwsRegion | ConvertFrom-Json
    
    $currentDesired = $serviceInfo.services[0].desiredCount
    $currentRunning = $serviceInfo.services[0].runningCount
    
    Write-Info "Current state: Desired=$currentDesired, Running=$currentRunning"
    
    if ($currentDesired -le $BaselineCount) {
        Write-Success "Service already at or below baseline ($currentDesired ≤ $BaselineCount)"
        Write-Info "No action needed"
        exit 0
    }
    
} catch {
    Write-Error-Custom "Failed to get service info: $_"
    exit 1
}

# Check if autoscaling is enabled
Write-Step "Checking for Application Auto Scaling..."
try {
    $scalingTargets = aws application-autoscaling describe-scalable-targets `
        --service-namespace ecs `
        --resource-ids "service/$ClusterName/$ServiceName" `
        --region $AwsRegion | ConvertFrom-Json
    
    if ($scalingTargets.ScalableTargets.Count -gt 0) {
        Write-Info "Auto Scaling is configured for this service"
        $minCapacity = $scalingTargets.ScalableTargets[0].MinCapacity
        $maxCapacity = $scalingTargets.ScalableTargets[0].MaxCapacity
        
        Write-Info "  Min Capacity: $minCapacity"
        Write-Info "  Max Capacity: $maxCapacity"
        
        if ($BaselineCount -lt $minCapacity) {
            Write-Info "⚠ Baseline ($BaselineCount) is below min capacity ($minCapacity)"
            Write-Info "  Service will scale back to $minCapacity automatically"
            $BaselineCount = $minCapacity
        }
    }
} catch {
    Write-Info "No auto scaling configured (this is fine)"
}

# Scale down to baseline
Write-Step "Scaling down service to baseline..."
Write-Info "Scaling: $currentDesired tasks → $BaselineCount tasks"

try {
    aws ecs update-service `
        --cluster $ClusterName `
        --service $ServiceName `
        --desired-count $BaselineCount `
        --region $AwsRegion | Out-Null
    
    Write-Success "Desired count updated to $BaselineCount"
    
} catch {
    Write-Error-Custom "Failed to update service: $_"
    exit 1
}

# Wait for scale-down to complete
Write-Step "Waiting for tasks to scale down..."
Write-Info "This may take 2-3 minutes (draining connections + stopping tasks)"

$maxAttempts = 20
$attempt = 0

while ($attempt -lt $maxAttempts) {
    Start-Sleep -Seconds 15
    $attempt++
    
    try {
        $serviceInfo = aws ecs describe-services `
            --cluster $ClusterName `
            --services $ServiceName `
            --region $AwsRegion | ConvertFrom-Json
        
        $runningCount = $serviceInfo.services[0].runningCount
        $desiredCount = $serviceInfo.services[0].desiredCount
        
        Write-Host "  [Attempt $attempt/$maxAttempts] Running: $runningCount / Desired: $desiredCount" -ForegroundColor Gray
        
        if ($runningCount -eq $desiredCount -and $runningCount -eq $BaselineCount) {
            Write-Success "Scale-down completed! Running tasks: $runningCount"
            break
        }
        
    } catch {
        Write-Error-Custom "Failed to check status: $_"
    }
}

# Get final task list
Write-Step "Verifying final state..."
try {
    $tasks = aws ecs list-tasks `
        --cluster $ClusterName `
        --service-name $ServiceName `
        --desired-status RUNNING `
        --region $AwsRegion | ConvertFrom-Json
    
    $taskCount = $tasks.taskArns.Count
    Write-Success "Active tasks: $taskCount"
    
    if ($taskCount -gt 0) {
        Write-Info "Task ARNs:"
        foreach ($taskArn in $tasks.taskArns) {
            $taskId = $taskArn.Split('/')[-1]
            Write-Host "  • $taskId" -ForegroundColor Gray
        }
    }
    
} catch {
    Write-Error-Custom "Failed to list tasks: $_"
}

# Cool-down recommendation
Write-Step "Post-scale-down cool-down..."
Write-Info "Recommended wait time: $WaitMinutes minutes"
Write-Info "This allows:"
Write-Info "  • CloudWatch metrics to stabilize"
Write-Info "  • Auto-scaling cool-down period to reset"
Write-Info "  • Connection pools to drain completely"

$waitSeconds = $WaitMinutes * 60
Write-Info "`nWaiting $WaitMinutes minutes..."

for ($i = 0; $i -lt $WaitMinutes; $i++) {
    $remaining = $WaitMinutes - $i
    Write-Host "  ⏳ $remaining minutes remaining..." -ForegroundColor Gray
    Start-Sleep -Seconds 60
}

Write-Host @"

╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║                  ✓ Service Reset Complete!                         ║
║                                                                    ║
║              Service is ready for next test                        ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝

"@ -ForegroundColor Green

# Final status check
try {
    $finalService = aws ecs describe-services `
        --cluster $ClusterName `
        --services $ServiceName `
        --region $AwsRegion | ConvertFrom-Json
    
    Write-Info "Final Status:"
    Write-Host "  • Desired Tasks: $($finalService.services[0].desiredCount)" -ForegroundColor White
    Write-Host "  • Running Tasks: $($finalService.services[0].runningCount)" -ForegroundColor White
    Write-Host "  • Pending Tasks: $($finalService.services[0].pendingCount)" -ForegroundColor White
    
} catch {
    Write-Error-Custom "Failed to get final status"
}

Write-Host ""
