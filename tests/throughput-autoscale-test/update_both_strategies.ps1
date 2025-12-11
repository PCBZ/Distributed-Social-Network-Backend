param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("push", "pull", "hybrid")]
    [string]$Strategy
)

$ErrorActionPreference = "Stop"

Write-Host "`n╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                                    ║" -ForegroundColor Cyan
Write-Host "║          Update Post & Timeline Service Strategies                ║" -ForegroundColor Cyan
Write-Host "║                                                                    ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Write-Host "`n[ℹ] Target Strategy: $($Strategy.ToUpper())" -ForegroundColor Yellow
Write-Host "[ℹ] Region: us-west-2`n" -ForegroundColor Yellow

# Update Post Service
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " POST SERVICE" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan

Write-Host "`n[STEP 1/3] Fetching post-service task definition..." -ForegroundColor Yellow
$postTaskDefArn = aws ecs describe-services `
    --cluster post-service `
    --services post-service `
    --region us-west-2 `
    --query "services[0].taskDefinition" `
    --output text

Write-Host "[✓] Current task definition: $postTaskDefArn" -ForegroundColor Green

Write-Host "`n[STEP 2/3] Creating new task definition with POST_STRATEGY='$Strategy'..." -ForegroundColor Yellow
$postTaskDef = aws ecs describe-task-definition --task-definition $postTaskDefArn --region us-west-2 | ConvertFrom-Json

# Update POST_STRATEGY environment variable
$container = $postTaskDef.taskDefinition.containerDefinitions[0]
$envVars = $container.environment | Where-Object { $_.name -ne "POST_STRATEGY" }
$envVars += @{ name = "POST_STRATEGY"; value = $Strategy }

# Create new task definition
$newTaskDef = @{
    family = $postTaskDef.taskDefinition.family
    taskRoleArn = $postTaskDef.taskDefinition.taskRoleArn
    executionRoleArn = $postTaskDef.taskDefinition.executionRoleArn
    networkMode = $postTaskDef.taskDefinition.networkMode
    requiresCompatibilities = @($postTaskDef.taskDefinition.requiresCompatibilities)
    cpu = $postTaskDef.taskDefinition.cpu
    memory = $postTaskDef.taskDefinition.memory
    containerDefinitions = @(@{
        name = $container.name
        image = $container.image
        portMappings = @($container.portMappings)
        environment = @($envVars)
        logConfiguration = $container.logConfiguration
    })
} | ConvertTo-Json -Depth 10 -Compress

$newPostRev = (aws ecs register-task-definition --cli-input-json $newTaskDef --region us-west-2 | ConvertFrom-Json).taskDefinition.revision
Write-Host "[✓] Created new revision: $($postTaskDef.taskDefinition.family):$newPostRev" -ForegroundColor Green

Write-Host "`n[STEP 3/3] Updating post-service..." -ForegroundColor Yellow
aws ecs update-service `
    --cluster post-service `
    --service post-service `
    --task-definition "$($postTaskDef.taskDefinition.family):$newPostRev" `
    --force-new-deployment `
    --region us-west-2 | Out-Null
Write-Host "[✓] Post-service update initiated" -ForegroundColor Green

# Update Timeline Service
Write-Host "`n═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " TIMELINE SERVICE" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan

Write-Host "`n[STEP 1/3] Fetching timeline-service task definition..." -ForegroundColor Yellow
$timelineTaskDefArn = aws ecs describe-services `
    --cluster timeline-service `
    --services timeline-service `
    --region us-west-2 `
    --query "services[0].taskDefinition" `
    --output text

Write-Host "[✓] Current task definition: $timelineTaskDefArn" -ForegroundColor Green

Write-Host "`n[STEP 2/3] Creating new task definition with FANOUT_STRATEGY='$Strategy'..." -ForegroundColor Yellow
$timelineTaskDef = aws ecs describe-task-definition --task-definition $timelineTaskDefArn --region us-west-2 | ConvertFrom-Json

# Update FANOUT_STRATEGY environment variable
$container = $timelineTaskDef.taskDefinition.containerDefinitions[0]
$envVars = $container.environment | Where-Object { $_.name -ne "FANOUT_STRATEGY" }
$envVars += @{ name = "FANOUT_STRATEGY"; value = $Strategy }

# Create new task definition
$newTaskDef = @{
    family = $timelineTaskDef.taskDefinition.family
    taskRoleArn = $timelineTaskDef.taskDefinition.taskRoleArn
    executionRoleArn = $timelineTaskDef.taskDefinition.executionRoleArn
    networkMode = $timelineTaskDef.taskDefinition.networkMode
    requiresCompatibilities = @($timelineTaskDef.taskDefinition.requiresCompatibilities)
    cpu = $timelineTaskDef.taskDefinition.cpu
    memory = $timelineTaskDef.taskDefinition.memory
    containerDefinitions = @(@{
        name = $container.name
        image = $container.image
        portMappings = @($container.portMappings)
        environment = @($envVars)
        logConfiguration = $container.logConfiguration
    })
} | ConvertTo-Json -Depth 10 -Compress

$newTimelineRev = (aws ecs register-task-definition --cli-input-json $newTaskDef --region us-west-2 | ConvertFrom-Json).taskDefinition.revision
Write-Host "[✓] Created new revision: $($timelineTaskDef.taskDefinition.family):$newTimelineRev" -ForegroundColor Green

Write-Host "`n[STEP 3/3] Updating timeline-service..." -ForegroundColor Yellow
aws ecs update-service `
    --cluster timeline-service `
    --service timeline-service `
    --task-definition "$($timelineTaskDef.taskDefinition.family):$newTimelineRev" `
    --force-new-deployment `
    --region us-west-2 | Out-Null
Write-Host "[✓] Timeline-service update initiated" -ForegroundColor Green

# Wait for stabilization
Write-Host "`n═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " WAITING FOR DEPLOYMENT" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan

Write-Host "`n[ℹ] Waiting for services to stabilize (2-5 minutes)..." -ForegroundColor Yellow
Write-Host "[ℹ] New tasks will start and old tasks will be drained...`n" -ForegroundColor Yellow

$stable = $false
$maxAttempts = 30
$attempt = 0

while (-not $stable -and $attempt -lt $maxAttempts) {
    $attempt++
    Start-Sleep -Seconds 10
    
    # Check both services
    $postSvc = aws ecs describe-services --cluster post-service --services post-service --region us-west-2 --output json | ConvertFrom-Json
    $timelineSvc = aws ecs describe-services --cluster timeline-service --services timeline-service --region us-west-2 --output json | ConvertFrom-Json
    
    $postRunning = $postSvc.services[0].runningCount
    $postDesired = $postSvc.services[0].desiredCount
    $timelineRunning = $timelineSvc.services[0].runningCount
    $timelineDesired = $timelineSvc.services[0].desiredCount
    
    Write-Host "[Check $attempt] Post: $postRunning/$postDesired | Timeline: $timelineRunning/$timelineDesired" -ForegroundColor White
    
    if ($postRunning -eq $postDesired -and $timelineRunning -eq $timelineDesired) {
        $stable = $true
    }
}

if ($stable) {
    Write-Host "`n[✓] Both services stabilized successfully!" -ForegroundColor Green
    Write-Host "[✓] Strategy updated to: $($Strategy.ToUpper())" -ForegroundColor Green
} else {
    Write-Host "`n[⚠] Services still deploying after $($attempt * 10) seconds" -ForegroundColor Yellow
    Write-Host "[ℹ] Continue monitoring in AWS Console" -ForegroundColor Yellow
}

Write-Host "`n╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                    Update Complete                                 ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan
