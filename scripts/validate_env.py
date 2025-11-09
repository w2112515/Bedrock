#!/usr/bin/env python3
"""
Enhanced environment variable validation script.

This script validates:
1. All required environment variables are set
2. Variable types are correct (URL, integer, boolean)
3. Dependencies are satisfied (e.g., if QWEN_API_KEY is set, QWEN_API_URL must also be set)
4. Sensitive file permissions (.env should not be world-readable)
5. URL formats are valid
6. Port numbers are in valid range
"""

import os
import sys
import re
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse
from pathlib import Path


class Color:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_success(message: str):
    """Print success message in green."""
    print(f"{Color.GREEN}✓ {message}{Color.END}")


def print_warning(message: str):
    """Print warning message in yellow."""
    print(f"{Color.YELLOW}⚠ {message}{Color.END}")


def print_error(message: str):
    """Print error message in red."""
    print(f"{Color.RED}✗ {message}{Color.END}")


def print_info(message: str):
    """Print info message in blue."""
    print(f"{Color.BLUE}ℹ {message}{Color.END}")


# Required environment variables with their types
REQUIRED_VARS: Dict[str, str] = {
    # Database
    "POSTGRES_HOST": "string",
    "POSTGRES_PORT": "integer",
    "POSTGRES_USER": "string",
    "POSTGRES_PASSWORD": "string",
    "POSTGRES_DB": "string",
    "DATABASE_URL": "url",
    # Redis
    "REDIS_HOST": "string",
    "REDIS_PORT": "integer",
    "REDIS_DB": "integer",
    "REDIS_URL": "url",
    # Application
    "SECRET_KEY": "string",
}

# Optional environment variables with their types
OPTIONAL_VARS: Dict[str, str] = {
    "DEBUG": "boolean",
    "LOG_LEVEL": "string",
    # External APIs
    "BINANCE_API_KEY": "string",
    "BINANCE_API_SECRET": "string",
    "BITQUERY_API_KEY": "string",
    "BITQUERY_API_URL": "url",
    "QWEN_API_KEY": "string",
    "QWEN_API_URL": "url",
    # Service Ports
    "DATAHUB_PORT": "integer",
    "DECISION_ENGINE_PORT": "integer",
    "PORTFOLIO_PORT": "integer",
    "BACKTESTING_PORT": "integer",
    "MLOPS_PORT": "integer",
    "NOTIFICATION_PORT": "integer",
    "WEBAPP_PORT": "integer",
    # Celery
    "CELERY_BROKER_URL": "url",
    "CELERY_RESULT_BACKEND": "url",
    # MLflow
    "MLFLOW_TRACKING_URI": "url",
}

# Variable dependencies (if key is set, values must also be set)
DEPENDENCIES: Dict[str, List[str]] = {
    "BINANCE_API_KEY": ["BINANCE_API_SECRET"],
    "BINANCE_API_SECRET": ["BINANCE_API_KEY"],
    "BITQUERY_API_KEY": ["BITQUERY_API_URL"],
    "QWEN_API_KEY": ["QWEN_API_URL"],
}

# Sensitive variables that should not have default values in production
SENSITIVE_VARS: List[str] = [
    "SECRET_KEY",
    "POSTGRES_PASSWORD",
    "BINANCE_API_SECRET",
    "BITQUERY_API_KEY",
    "QWEN_API_KEY",
]

# Default values that should be changed in production
INSECURE_DEFAULTS: Dict[str, List[str]] = {
    "SECRET_KEY": ["change-this-to-a-strong-random-key-in-production", "test-secret-key-not-for-production"],
    "POSTGRES_PASSWORD": ["bedrock_password", "bedrock_test_password"],
}


def validate_type(var_name: str, var_value: str, var_type: str) -> Tuple[bool, Optional[str]]:
    """
    Validate variable type.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if var_type == "string":
        return True, None
    
    elif var_type == "integer":
        try:
            int_value = int(var_value)
            if var_name.endswith("_PORT"):
                if not (1 <= int_value <= 65535):
                    return False, f"Port number must be between 1 and 65535, got {int_value}"
            return True, None
        except ValueError:
            return False, f"Expected integer, got '{var_value}'"
    
    elif var_type == "boolean":
        if var_value.lower() not in ["true", "false", "1", "0", "yes", "no"]:
            return False, f"Expected boolean (true/false), got '{var_value}'"
        return True, None
    
    elif var_type == "url":
        try:
            result = urlparse(var_value)
            if not all([result.scheme, result.netloc]):
                return False, f"Invalid URL format: '{var_value}'"
            return True, None
        except Exception as e:
            return False, f"Invalid URL: {str(e)}"
    
    return True, None


def check_required_variables() -> List[str]:
    """Check if all required variables are set."""
    missing = []
    for var_name in REQUIRED_VARS:
        if not os.getenv(var_name):
            missing.append(var_name)
    return missing


def check_variable_types() -> List[Tuple[str, str]]:
    """Check if variable types are correct."""
    errors = []
    
    all_vars = {**REQUIRED_VARS, **OPTIONAL_VARS}
    
    for var_name, var_type in all_vars.items():
        var_value = os.getenv(var_name)
        if var_value:
            is_valid, error_msg = validate_type(var_name, var_value, var_type)
            if not is_valid:
                errors.append((var_name, error_msg))
    
    return errors


def check_dependencies() -> List[Tuple[str, List[str]]]:
    """Check if variable dependencies are satisfied."""
    errors = []
    
    for var_name, dependencies in DEPENDENCIES.items():
        if os.getenv(var_name):
            missing_deps = [dep for dep in dependencies if not os.getenv(dep)]
            if missing_deps:
                errors.append((var_name, missing_deps))
    
    return errors


def check_insecure_defaults() -> List[Tuple[str, str]]:
    """Check if sensitive variables have insecure default values."""
    warnings = []
    
    # Only check if not in test environment
    if os.getenv("POSTGRES_DB") != "bedrock_test_db":
        for var_name, insecure_values in INSECURE_DEFAULTS.items():
            var_value = os.getenv(var_name)
            if var_value and var_value in insecure_values:
                warnings.append((var_name, var_value))
    
    return warnings


def check_file_permissions() -> Optional[str]:
    """Check if .env file has secure permissions."""
    env_file = Path(".env")
    
    if not env_file.exists():
        return "File .env does not exist"
    
    # Check file permissions (Unix-like systems only)
    if sys.platform != "win32":
        import stat
        file_stat = env_file.stat()
        mode = file_stat.st_mode
        
        # Check if file is world-readable or world-writable
        if mode & stat.S_IROTH or mode & stat.S_IWOTH:
            return "File .env is world-readable or world-writable (should be 600 or 640)"
    
    return None


def main():
    """Main validation function."""
    print(f"\n{Color.BOLD}=== Environment Variable Validation ==={Color.END}\n")
    
    has_errors = False
    has_warnings = False
    
    # Check 1: Required variables
    print(f"{Color.BOLD}1. Checking required variables...{Color.END}")
    missing_vars = check_required_variables()
    if missing_vars:
        has_errors = True
        for var in missing_vars:
            print_error(f"Missing required variable: {var}")
    else:
        print_success("All required variables are set")
    print()
    
    # Check 2: Variable types
    print(f"{Color.BOLD}2. Checking variable types...{Color.END}")
    type_errors = check_variable_types()
    if type_errors:
        has_errors = True
        for var_name, error_msg in type_errors:
            print_error(f"{var_name}: {error_msg}")
    else:
        print_success("All variable types are correct")
    print()
    
    # Check 3: Dependencies
    print(f"{Color.BOLD}3. Checking variable dependencies...{Color.END}")
    dep_errors = check_dependencies()
    if dep_errors:
        has_errors = True
        for var_name, missing_deps in dep_errors:
            print_error(f"{var_name} is set, but missing dependencies: {', '.join(missing_deps)}")
    else:
        print_success("All variable dependencies are satisfied")
    print()
    
    # Check 4: Insecure defaults
    print(f"{Color.BOLD}4. Checking for insecure default values...{Color.END}")
    insecure_warnings = check_insecure_defaults()
    if insecure_warnings:
        has_warnings = True
        for var_name, var_value in insecure_warnings:
            print_warning(f"{var_name} has insecure default value: '{var_value}'")
    else:
        print_success("No insecure default values detected")
    print()
    
    # Check 5: File permissions
    print(f"{Color.BOLD}5. Checking .env file permissions...{Color.END}")
    perm_error = check_file_permissions()
    if perm_error:
        has_warnings = True
        print_warning(perm_error)
    else:
        print_success(".env file permissions are secure")
    print()
    
    # Summary
    print(f"{Color.BOLD}=== Validation Summary ==={Color.END}\n")
    
    if has_errors:
        print_error("Validation failed with errors!")
        print_info("Please fix the errors above and run this script again.")
        sys.exit(1)
    elif has_warnings:
        print_warning("Validation passed with warnings!")
        print_info("Consider addressing the warnings above for better security.")
        sys.exit(0)
    else:
        print_success("All validations passed!")
        sys.exit(0)


if __name__ == "__main__":
    # Load .env file if python-dotenv is available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print_warning("python-dotenv not installed, reading from system environment only")
        print_info("Install with: pip install python-dotenv")
        print()
    
    main()

