# Install and Run Script for Resident Read Review Tool
# This script checks for UV, installs it if needed, syncs packages, and runs the main.py file

# Function to display status messages with color
function Write-Status {
    param (
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host "[$([DateTime]::Now.ToString('HH:mm:ss'))] $Message" -ForegroundColor $Color
}

# Function to check if a command exists
function Test-CommandExists {
    param (
        [string]$Command
    )

    try {
        $null = Get-Command $Command -ErrorAction Stop
        return $true
    }
    catch {
        return $false
    }
}

# Set the error action preference to stop
$ErrorActionPreference = "Stop"

# Check if the script is being run directly (not from an existing PowerShell session)
$runningInteractively = [Environment]::UserInteractive -and !$psISE -and $Host.Name -eq 'ConsoleHost'

# Display welcome message
Write-Status "Starting installation and setup for Resident Read Review Tool..." "Cyan"
Write-Status "This script will check for UV, install it if needed, sync packages, and run the application." "Cyan"

try {
    # Check if UV is already installed
    $uvInstalled = Test-CommandExists "uv"

    if ($uvInstalled) {
        $uvVersion = (uv --version 2>&1).ToString()
        Write-Status "UV is already installed: $uvVersion" "Green"
    } else {
        Write-Status "UV is not installed. Installing UV as recommended by astral.sh..." "Yellow"

        try {
            # Install UV using the recommended command from docs.astral.sh/uv
            Write-Status "Running UV installer..." "Yellow"
            powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

            # Check if UV was installed successfully
            if (Test-CommandExists "uv") {
                $uvVersion = (uv --version 2>&1).ToString()
                Write-Status "UV installed successfully: $uvVersion" "Green"
            } else {
                Write-Status "UV installation failed. Please install UV manually and try again." "Red"
                Write-Status "Visit https://astral.sh/uv for installation instructions." "Yellow"
                exit 1
            }
        }
        catch {
            Write-Status "Failed to install UV: $_" "Red"
            Write-Status "Please install UV manually and try again." "Yellow"
            Write-Status "Visit https://astral.sh/uv for installation instructions." "Yellow"
            exit 1
        }
    }

    # Ensure we're in the correct directory (the script directory)
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    Set-Location $scriptDir
    Write-Status "Working directory: $scriptDir" "Green"

    # Check if pyproject.toml exists
    if (-not (Test-Path "pyproject.toml")) {
        Write-Status "pyproject.toml not found in the current directory. Please ensure you're running this script from the project root." "Red"
        exit 1
    }

    # Create virtual environment if it doesn't exist
    if (-not (Test-Path ".venv")) {
        Write-Status "Creating virtual environment..." "Yellow"
        uv venv

        if (-not (Test-Path ".venv")) {
            Write-Status "Failed to create virtual environment." "Red"
            exit 1
        }
        Write-Status "Virtual environment created successfully." "Green"
    } else {
        Write-Status "Virtual environment already exists." "Green"
    }

    # Sync packages using UV
    Write-Status "Installing required packages using UV sync..." "Yellow"
    uv sync

    if ($LASTEXITCODE -ne 0) {
        Write-Status "Failed to install packages. Check the error messages above." "Red"
        exit 1
    }

    Write-Status "Packages installed successfully." "Green"

    # Check if main.py exists
    $srcPath = Join-Path $scriptDir "src"
    $mainPath = Join-Path $srcPath "main.py"
    if (-not (Test-Path $mainPath)) {
        Write-Status "main.py not found at $mainPath. Please ensure the project structure is correct." "Red"
        exit 1
    }

    # Run the main.py file
    Write-Status "Starting the application..." "Cyan"
    Write-Status "Running: python src/main.py" "Cyan"

    # Activate the virtual environment and run the script
    # Using the call operator (&) and enclosing the path in quotes to handle paths with spaces
    & ".\.venv\Scripts\python.exe" ".\src\main.py"

    # Check if the script ran successfully
    if ($LASTEXITCODE -ne 0) {
        Write-Status "The application exited with code $LASTEXITCODE. Check the error messages above." "Red"
        exit 1
    }

    Write-Status "Application completed." "Yellow"
}
catch {
    Write-Status "An error occurred: $_" "Red"
    Write-Status "Stack trace: $($_.ScriptStackTrace)" "Red"

    # Keep window open if running directly
    if ($runningInteractively) {
        Write-Status "Press any key to exit..." "Yellow"
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    }

    exit 1
}

# Keep window open at the end if running directly
if ($runningInteractively) {
    Write-Status "Script has completed. Press any key to exit..." "Yellow"
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
