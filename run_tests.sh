#!/bin/bash

# Test runner script for coupon system
# 쿠폰 시스템을 위한 테스트 실행 스크립트

set -e  # Exit on error

echo "🧪 Coupon System Test Runner"
echo "============================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if test requirements are installed
check_requirements() {
    print_status "Checking test requirements..."
    
    if [ ! -f "test_requirements.txt" ]; then
        print_error "test_requirements.txt not found!"
        exit 1
    fi
    
    # Install test requirements if needed
    if ! python -c "import pytest" &> /dev/null; then
        print_warning "Installing test requirements..."
        pip install -r test_requirements.txt
    fi
    
    print_success "Test requirements verified"
}

# Run unit tests
run_unit_tests() {
    print_status "Running unit tests..."
    echo "========================"
    
    if ! pytest tests/unit/ -v --tb=short; then
        print_error "Unit tests failed!"
        return 1
    fi
    
    print_success "Unit tests passed!"
    return 0
}

# Run integration tests (requires running services)
run_integration_tests() {
    print_status "Running integration tests..."
    echo "============================"
    
    # Check if services are running
    if ! curl -s http://localhost/health > /dev/null; then
        print_warning "Services not running. Starting with docker-compose..."
        if [ -f "docker-compose.yml" ]; then
            docker-compose up -d
            print_status "Waiting for services to be ready..."
            sleep 30
        else
            print_error "docker-compose.yml not found and services not running!"
            return 1
        fi
    fi
    
    if ! pytest tests/integration/ -v --tb=short; then
        print_error "Integration tests failed!"
        return 1
    fi
    
    print_success "Integration tests passed!"
    return 0
}

# Run load tests
run_load_tests() {
    print_status "Running load tests..."
    echo "====================="
    
    # Check if services are running
    if ! curl -s http://localhost/health > /dev/null; then
        print_error "Services not running! Please start with: docker-compose up -d"
        return 1
    fi
    
    print_status "Running Locust load test (web interface)..."
    print_status "Access the web interface at: http://localhost:8089"
    print_status "Target host: http://localhost"
    
    cd load_testing
    locust -f locustfile.py --host=http://localhost
    cd ..
}

# Run stress tests
run_stress_tests() {
    print_status "Running stress tests..."
    echo "======================="
    
    # Check if services are running
    if ! curl -s http://localhost/health > /dev/null; then
        print_error "Services not running! Please start with: docker-compose up -d"
        return 1
    fi
    
    cd load_testing
    python stress_test.py
    cd ..
}

# Generate test coverage report
generate_coverage() {
    print_status "Generating test coverage report..."
    echo "=================================="
    
    if ! python -c "import coverage" &> /dev/null; then
        print_warning "Installing coverage..."
        pip install coverage
    fi
    
    coverage run --source=app -m pytest tests/unit/ tests/integration/
    coverage report -m
    coverage html
    
    print_success "Coverage report generated in htmlcov/"
}

# Clean test artifacts
clean_test_artifacts() {
    print_status "Cleaning test artifacts..."
    
    rm -rf .pytest_cache/
    rm -rf htmlcov/
    rm -rf .coverage
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -delete
    
    print_success "Test artifacts cleaned"
}

# Main script logic
case "${1:-all}" in
    "unit")
        check_requirements
        run_unit_tests
        ;;
    "integration")
        check_requirements
        run_integration_tests
        ;;
    "load")
        check_requirements
        run_load_tests
        ;;
    "stress")
        check_requirements
        run_stress_tests
        ;;
    "coverage")
        check_requirements
        generate_coverage
        ;;
    "clean")
        clean_test_artifacts
        ;;
    "all")
        check_requirements
        echo
        run_unit_tests
        echo
        run_integration_tests
        echo
        generate_coverage
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [unit|integration|load|stress|coverage|clean|all|help]"
        echo
        echo "Commands:"
        echo "  unit        - Run unit tests only"
        echo "  integration - Run integration tests (requires running services)"
        echo "  load        - Run Locust load tests (interactive)"
        echo "  stress      - Run automated stress tests"
        echo "  coverage    - Generate test coverage report"
        echo "  clean       - Clean test artifacts"
        echo "  all         - Run unit + integration tests + coverage (default)"
        echo "  help        - Show this help message"
        echo
        echo "Examples:"
        echo "  $0 unit                    # Run only unit tests"
        echo "  $0 integration            # Run only integration tests"
        echo "  $0 load                   # Start Locust web interface"
        echo "  $0 stress                 # Run automated stress test"
        exit 0
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac

print_success "Test execution completed!"