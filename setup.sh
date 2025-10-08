#!/bin/bash

# Setup script for Real-Time Health Monitoring System
# This script helps you set up your development environment

set -e

echo "🏥 Health Monitoring System - Setup Script"
echo "==========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "ℹ $1"
}

# Check prerequisites
echo "📋 Checking prerequisites..."
echo ""

# Check Java
if command -v java &> /dev/null; then
    JAVA_VERSION=$(java -version 2>&1 | head -n 1 | cut -d'"' -f2)
    print_success "Java $JAVA_VERSION installed"
else
    print_warning "Java not found - needed for Android development"
fi

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python $PYTHON_VERSION installed"
else
    print_error "Python 3 not found - required for ML pipeline"
    exit 1
fi

# Check Flutter
if command -v flutter &> /dev/null; then
    FLUTTER_VERSION=$(flutter --version | head -n 1 | cut -d' ' -f2)
    print_success "Flutter $FLUTTER_VERSION installed"
else
    print_warning "Flutter not found - needed for mobile dashboard"
fi

# Check AWS CLI
if command -v aws &> /dev/null; then
    AWS_VERSION=$(aws --version | cut -d' ' -f1 | cut -d'/' -f2)
    print_success "AWS CLI $AWS_VERSION installed"
else
    print_warning "AWS CLI not found - needed for cloud deployment"
fi

# Check Git
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version | cut -d' ' -f3)
    print_success "Git $GIT_VERSION installed"
else
    print_error "Git not found - required"
fi

echo ""
echo "==========================================="
echo ""

# Ask user what to set up
echo "What would you like to set up?"
echo "1) ML Pipeline (Python environment)"
echo "2) Cloud Backend (AWS deployment)"
echo "3) Mobile Dashboard (Flutter)"
echo "4) All of the above"
echo "5) Just show me the next steps"
echo ""
read -p "Enter your choice (1-5): " choice

case $choice in
    1)
        echo ""
        print_info "Setting up ML Pipeline..."
        cd MLPipeline
        
        # Create virtual environment
        print_info "Creating Python virtual environment..."
        python3 -m venv venv
        
        # Activate and install dependencies
        print_info "Installing dependencies..."
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        
        # Generate synthetic data
        print_info "Generating synthetic training data..."
        python src/data/generate_synthetic_data.py
        
        print_success "ML Pipeline setup complete!"
        echo ""
        echo "Next steps:"
        echo "1. Activate environment: source MLPipeline/venv/bin/activate"
        echo "2. Train model: python src/models/train_lstm_autoencoder.py"
        ;;
    
    2)
        echo ""
        print_info "Setting up Cloud Backend..."
        
        # Check AWS credentials
        if aws sts get-caller-identity &> /dev/null; then
            print_success "AWS credentials configured"
            
            read -p "Do you want to deploy to AWS now? (y/n): " deploy
            if [ "$deploy" = "y" ]; then
                cd CloudBackend/aws-lambda
                chmod +x deploy.sh
                ./deploy.sh
            else
                print_info "Skipping deployment. Run ./CloudBackend/aws-lambda/deploy.sh when ready"
            fi
        else
            print_warning "AWS credentials not configured"
            echo "Run: aws configure"
        fi
        ;;
    
    3)
        echo ""
        print_info "Setting up Mobile Dashboard..."
        cd MobileDashboard
        
        # Get Flutter dependencies
        print_info "Getting Flutter packages..."
        flutter pub get
        
        print_success "Mobile Dashboard setup complete!"
        echo ""
        echo "Next steps:"
        echo "1. Setup Firebase: flutterfire configure"
        echo "2. Update API endpoint in lib/config/api_config.dart"
        echo "3. Run: flutter run"
        ;;
    
    4)
        echo ""
        print_info "Setting up everything..."
        
        # ML Pipeline
        print_info "1/3 Setting up ML Pipeline..."
        cd MLPipeline
        python3 -m venv venv
        source venv/bin/activate
        pip install -q --upgrade pip
        pip install -q -r requirements.txt
        python src/data/generate_synthetic_data.py
        cd ..
        
        # Cloud Backend
        print_info "2/3 Cloud Backend ready (manual deployment required)"
        
        # Mobile Dashboard
        print_info "3/3 Setting up Mobile Dashboard..."
        cd MobileDashboard
        flutter pub get
        cd ..
        
        print_success "All components set up!"
        ;;
    
    5)
        echo ""
        print_info "Quick Start Guide:"
        echo ""
        echo "📱 Phase 1: Test Wear OS App Locally (30 min)"
        echo "   1. Open WearOSApp in Android Studio"
        echo "   2. Create Wear OS emulator (API 30+)"
        echo "   3. Run the app"
        echo "   4. Use Virtual Sensors to simulate data"
        echo ""
        echo "🤖 Phase 2: Train ML Model (30 min)"
        echo "   cd MLPipeline"
        echo "   python3 -m venv venv && source venv/bin/activate"
        echo "   pip install -r requirements.txt"
        echo "   python src/data/generate_synthetic_data.py"
        echo "   python src/models/train_lstm_autoencoder.py"
        echo ""
        echo "☁️  Phase 3: Deploy Cloud Backend (30 min)"
        echo "   cd CloudBackend/aws-lambda"
        echo "   aws configure  # Set up AWS credentials"
        echo "   ./deploy.sh"
        echo ""
        echo "📊 Phase 4: Run Mobile Dashboard (20 min)"
        echo "   cd MobileDashboard"
        echo "   flutter pub get"
        echo "   flutterfire configure"
        echo "   flutter run"
        echo ""
        echo "📖 Full documentation: see QUICK_START.md"
        ;;
esac

echo ""
echo "==========================================="
echo ""
print_success "Setup script completed!"
echo ""
echo "📚 Helpful resources:"
echo "   • Quick Start Guide: QUICK_START.md"
echo "   • Detailed Setup: PROJECT_SETUP_GUIDE.md"
echo "   • Project Overview: README.md"
echo "   • Development Roadmap: ROADMAP.md"
echo ""
echo "🆘 Need help? Check docs/TESTING.md for troubleshooting"
echo ""
