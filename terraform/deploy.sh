#!/bin/bash

# Calendar Sync Terraform Deployment Script
# This script automates the deployment of the calendar sync application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the terraform directory
if [ ! -f "main.tf" ]; then
    print_error "This script must be run from the terraform directory"
    exit 1
fi

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    print_warning "terraform.tfvars not found. Please create it from terraform.tfvars.example"
    print_status "Copying example file..."
    cp terraform.tfvars.example terraform.tfvars
    print_warning "Please edit terraform.tfvars and fill in the sensitive values before running this script again"
    exit 1
fi

# Check if required tools are installed
check_requirements() {
    print_status "Checking requirements..."
    
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform is not installed"
        exit 1
    fi
    
    if ! command -v gcloud &> /dev/null; then
        print_error "Google Cloud SDK is not installed"
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    
    print_status "All requirements met"
}

# Build and push Docker image
build_image() {
    print_status "Building and pushing Docker image..."
    
    # Go to project root (one directory up)
    cd ..
    
    # Build and push the image
    gcloud builds submit --tag us-central1-docker.pkg.dev/stevemcghee-slosports/cloud-run-source-deploy/calendar-sync
    
    # Go back to terraform directory
    cd terraform
    
    print_status "Docker image built and pushed successfully"
}

# Initialize Terraform
init_terraform() {
    print_status "Initializing Terraform..."
    terraform init
    print_status "Terraform initialized"
}

# Plan Terraform deployment
plan_deployment() {
    print_status "Planning Terraform deployment..."
    terraform plan
    print_status "Terraform plan completed"
}

# Apply Terraform deployment
apply_deployment() {
    print_status "Applying Terraform deployment..."
    terraform apply -auto-approve
    print_status "Terraform deployment completed"
}

# Show deployment outputs
show_outputs() {
    print_status "Deployment outputs:"
    terraform output
}

# Main deployment function
deploy() {
    print_status "Starting calendar sync deployment..."
    
    check_requirements
    build_image
    init_terraform
    plan_deployment
    apply_deployment
    show_outputs
    
    print_status "Deployment completed successfully!"
    print_status "The calendar sync service is now running at:"
    terraform output -raw cloud_run_service_url
}

# Function to destroy deployment
destroy() {
    print_warning "This will destroy all resources created by Terraform"
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Destroying deployment..."
        terraform destroy -auto-approve
        print_status "Deployment destroyed"
    else
        print_status "Destroy cancelled"
    fi
}

# Function to show help
show_help() {
    echo "Calendar Sync Terraform Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  deploy    Deploy the calendar sync application (default)"
    echo "  destroy   Destroy the deployment"
    echo "  plan      Show the Terraform plan without applying"
    echo "  init      Initialize Terraform"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0              # Deploy the application"
    echo "  $0 plan         # Show what will be deployed"
    echo "  $0 destroy      # Remove all resources"
}

# Parse command line arguments
case "${1:-deploy}" in
    "deploy")
        deploy
        ;;
    "destroy")
        destroy
        ;;
    "plan")
        check_requirements
        init_terraform
        plan_deployment
        ;;
    "init")
        check_requirements
        init_terraform
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac 