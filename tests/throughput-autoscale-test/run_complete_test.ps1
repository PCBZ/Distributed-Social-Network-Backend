#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Automated test runner for all three fanout strategies
    
.DESCRIPTION
    Runs Locust tests for Push, Pull, and Hybrid strategies
    Monitors metrics in real-time and collects CloudWatch data
    
.PARAMETER Strategy
    Which strategy to test (push, pull, hybrid, or all)
    
.PARAMETER Users
    Maximum number of concurrent users (default: 1000)
    
.PARAMETER SpawnRate
    User spawn rate per second (default: 50)
    
.PARAMETER Duration
    Test duration in minutes (default: 20)
    
.EXAMPLE
    .\run_complete_test.ps1 -Strategy all
    .\run_complete_test.ps1 -Strategy push -Users 500 -Duration 10
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('push', 'pull', 'hybrid', 'all')]
    [string]$Strategy = 'all',
    
    [int]$Users = 1000,
    [int]$SpawnRate = 50,
    [int]$Duration = 20,
    
    [string]$ServiceName = 'timeline-service',
    [string]$ClusterName = 'cs6650-project-dev-cluster',
    [string]$AlbName = 'app/cs6650-project-dev-alb/xxxxx',
    [string]$AlbHost = 'http://cs6650-project-dev-alb-315577819.us-west-2.elb.amazonaws.com',
    [string]$AwsRegion = 'us-west-2'
)

$ErrorActionPreference = 'Stop'

# Colors for output
function Write-Step($msg) { Write-Host "`n[STEP] $msg" -ForegroundColor Cyan }
function Write-Success($msg) { Write-Host "[✓] $msg" -ForegroundColor Green }
function Write-Error-Custom($msg) { Write-Host "[✗] $msg" -ForegroundColor Red }
function Write-Info($msg) { Write-Host "[ℹ] $msg" -ForegroundColor Yellow }

# Results directory
$ResultsDir = "./results"
if (-not (Test-Path $ResultsDir)) {
    New-Item -ItemType Directory -Path $ResultsDir | Out-Null
    Write-Success "Created results directory: $ResultsDir"
}

# Check prerequisites
function Test-Prerequisites {
    Write-Step "Checking prerequisites..."
    
    # Check Python
    try {
        $pythonVersion = python --version 2>&1
        Write-Success "Python: $pythonVersion"
    } catch {
        Write-Error-Custom "Python not found. Please install Python 3.8+"
        exit 1
    }
    
    # Check required Python packages
    $requiredPackages = @('locust', 'boto3', 'pandas', 'matplotlib')
    foreach ($pkg in $requiredPackages) {
        $installed = pip show $pkg 2>$null
        if (-not $installed) {
            Write-Info "Installing $pkg..."
            pip install $pkg
        } else {
            Write-Success "Package installed: $pkg"
        }
    }
    
    # Check AWS credentials
    try {
        aws sts get-caller-identity | Out-Null
        Write-Success "AWS credentials configured"
    } catch {
        Write-Error-Custom "AWS credentials not configured. Run 'aws configure'"
        exit 1
    }
    
    # Check if Locust files exist
    if (-not (Test-Path "./locustfile.py")) {
        Write-Error-Custom "locustfile.py not found in current directory"
        exit 1
    }
    
    Write-Success "All prerequisites satisfied"
}

# Update ECS Task Definition with new environment variable
function Update-ServiceStrategy {
    param([string]$StrategyName)
    
    Write-Step "Updating Timeline Service to use $StrategyName strategy..."
    
    try {
        # Use the automated update script
        .\update_strategy.ps1 `
            -Strategy $StrategyName `
            -ServiceName $ServiceName `
            -ClusterName $ClusterName `
            -AwsRegion $AwsRegion
        
        Write-Success "Service updated successfully"
        
        # Additional stabilization time
        Write-Info "Waiting 30 seconds for tasks to fully initialize..."
        Start-Sleep -Seconds 30
        
    } catch {
        Write-Error-Custom "Failed to update service strategy: $_"
        Write-Info "You can update manually via ECS Console"
        
        $response = Read-Host "`nContinue anyway? (yes/no)"
        if ($response -ne 'yes') {
            exit 1
        }
    }
}

# Run test for a single strategy
function Invoke-StrategyTest {
    param([string]$StrategyName)
    
    Write-Host "`n$('='*80)" -ForegroundColor Magenta
    Write-Host "Testing Strategy: $($StrategyName.ToUpper())" -ForegroundColor Magenta
    Write-Host "$('='*80)`n" -ForegroundColor Magenta
    
    # Update service configuration
    Update-ServiceStrategy -StrategyName $StrategyName
    
    # Start Locust monitoring in background
    Write-Step "Starting Locust metrics monitor..."
    $monitorJob = Start-Job -ScriptBlock {
        param($strategy, $resultsDir)
        Set-Location $using:PWD
        python monitor_locust.py --strategy $strategy --output-dir $resultsDir --interval 10
    } -ArgumentList $StrategyName, $ResultsDir
    
    Write-Success "Monitor started (Job ID: $($monitorJob.Id))"
    Start-Sleep -Seconds 5  # Give monitor time to start
    
    # Run Locust test
    Write-Step "Starting Locust load test..."
    Write-Info "Users: $Users | Spawn Rate: $SpawnRate/sec | Duration: ${Duration}m"
    
    $locustCmd = @(
        'locust',
        '-f', 'locustfile.py',
        '--host', $AlbHost,
        '--users', $Users,
        '--spawn-rate', $SpawnRate,
        '--run-time', "${Duration}m",
        '--headless',
        '--html', "$ResultsDir/locust_report_$StrategyName.html",
        '--csv', "$ResultsDir/locust_data_$StrategyName"
    )
    
    Write-Info "Command: $($locustCmd -join ' ')"
    
    try {
        & $locustCmd[0] $locustCmd[1..($locustCmd.Length-1)]
        Write-Success "Locust test completed"
    } catch {
        Write-Error-Custom "Locust test failed: $_"
        Stop-Job -Job $monitorJob
        exit 1
    }
    
    # Stop monitor
    Write-Step "Stopping metrics monitor..."
    Stop-Job -Job $monitorJob
    Receive-Job -Job $monitorJob
    Remove-Job -Job $monitorJob
    Write-Success "Monitor stopped"
    
    # Collect CloudWatch metrics
    Write-Step "Collecting CloudWatch metrics..."
    try {
        python collect_cloudwatch_metrics.py `
            --strategy $StrategyName `
            --service-name $ServiceName `
            --cluster-name $ClusterName `
            --alb-name $AlbName `
            --duration $($Duration + 5) `
            --region $AwsRegion `
            --output-dir $ResultsDir
        
        Write-Success "CloudWatch metrics collected"
    } catch {
        Write-Error-Custom "CloudWatch collection failed: $_"
    }
    
    # Generate summary report
    Write-Step "Generating summary report..."
    try {
        python monitor_locust.py `
            --summarize "$ResultsDir/locust_stats_$StrategyName.csv"
        
        Write-Success "Summary report generated"
    } catch {
        Write-Error-Custom "Summary generation failed: $_"
    }
    
    Write-Host "`n$('='*80)" -ForegroundColor Green
    Write-Host "✓ $($StrategyName.ToUpper()) Strategy Test Completed" -ForegroundColor Green
    Write-Host "$('='*80)`n" -ForegroundColor Green
    
    # Cool-down and scale-down period between tests
    if ($Strategy -eq 'all') {
        Write-Step "Post-test cleanup and cool-down..."
        
        # Reset task count to baseline
        Write-Info "Scaling down service to baseline (2 tasks)..."
        try {
            aws ecs update-service `
                --cluster $ClusterName `
                --service $ServiceName `
                --desired-count 2 `
                --region $AwsRegion | Out-Null
            
            Write-Success "Service scaled down to baseline"
        } catch {
            Write-Error-Custom "Failed to scale down: $_"
        }
        
        Write-Info "Cool-down period: 5 minutes (waiting for scale-down and metrics reset)..."
        Write-Info "  - Tasks scaling down: 0-2 minutes"
        Write-Info "  - Metrics cooling down: 2-5 minutes"
        Start-Sleep -Seconds 300
        
        # Verify baseline before next test
        try {
            $serviceInfo = aws ecs describe-services `
                --cluster $ClusterName `
                --services $ServiceName `
                --region $AwsRegion | ConvertFrom-Json
            
            $runningCount = $serviceInfo.services[0].runningCount
            Write-Info "Current running tasks: $runningCount"
        } catch {
            Write-Error-Custom "Failed to verify task count"
        }
    }
}

# Main execution
function Main {
    Write-Host @"

╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║        CS6650 Social Media Platform - Performance Testing         ║
║              Throughput & AutoScaling Evaluation                   ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

    Test-Prerequisites
    
    $strategies = if ($Strategy -eq 'all') { @('push', 'pull', 'hybrid') } else { @($Strategy) }
    
    Write-Host "`nTest Configuration:" -ForegroundColor Cyan
    Write-Host "  Strategies: $($strategies -join ', ')" -ForegroundColor White
    Write-Host "  Max Users: $Users" -ForegroundColor White
    Write-Host "  Spawn Rate: $SpawnRate users/sec" -ForegroundColor White
    Write-Host "  Duration: $Duration minutes per test" -ForegroundColor White
    Write-Host "  Total Time: ~$($Duration * $strategies.Count + 10 * ($strategies.Count - 1)) minutes`n" -ForegroundColor White
    
    $confirm = Read-Host "Proceed with testing? (yes/no)"
    if ($confirm -ne 'yes') {
        Write-Info "Test cancelled by user"
        exit 0
    }
    
    $startTime = Get-Date
    
    foreach ($strat in $strategies) {
        Invoke-StrategyTest -StrategyName $strat
    }
    
    $endTime = Get-Date
    $totalDuration = ($endTime - $startTime).TotalMinutes
    
    Write-Host @"

╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║                    ALL TESTS COMPLETED! ✓                          ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝

"@ -ForegroundColor Green

    Write-Host "Test Summary:" -ForegroundColor Cyan
    Write-Host "  Start Time: $($startTime.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor White
    Write-Host "  End Time: $($endTime.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor White
    Write-Host "  Total Duration: $([math]::Round($totalDuration, 1)) minutes" -ForegroundColor White
    Write-Host "  Results Directory: $ResultsDir`n" -ForegroundColor White
    
    Write-Host "Generated Files:" -ForegroundColor Cyan
    Get-ChildItem -Path $ResultsDir | ForEach-Object {
        Write-Host "  • $($_.Name)" -ForegroundColor White
    }
    
    Write-Host "`nNext Steps:" -ForegroundColor Yellow
    Write-Host "  1. Review HTML reports: $ResultsDir/locust_report_*.html" -ForegroundColor White
    Write-Host "  2. Analyze infrastructure graphs: $ResultsDir/infrastructure_*.png" -ForegroundColor White
    Write-Host "  3. Compare metrics across strategies" -ForegroundColor White
    Write-Host "  4. Document findings in your report`n" -ForegroundColor White
}

Main
