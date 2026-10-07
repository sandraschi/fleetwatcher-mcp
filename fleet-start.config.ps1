# Per-repo fleet start config for fleetwatcher-mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'fleetwatcher-mcp'
    BackendPort  = 10918
    FrontendPort = 10919
    HealthPath   = '/health'
    WebRoot      = 'webapp'
    Backend = @{
        Kind       = 'module-serve'
        Module     = 'fleetwatcher_mcp'
        SyncExtras = @('dev')
        SyncOnStart  = $true
        Env        = @{ FLEETWATCHER_PORT = '10918' }
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}
