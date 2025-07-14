#!/usr/bin/env python3
"""
Verification script for AI Tutor setup
This script checks that all required dependencies and environment variables are properly configured.
"""

import os
import sys
from dotenv import load_dotenv

def check_environment():
    """Check if all required environment variables are set."""
    print("🔍 Checking environment variables...")
    
    # Load .env file if it exists
    if os.path.exists('.env'):
        load_dotenv()
        print("✅ Found .env file")
    else:
        print("⚠️  No .env file found (using system environment variables)")
    
    required_vars = ['OPENAI_API_KEY', 'DATABASE_URL']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if var == 'OPENAI_API_KEY':
                print(f"✅ {var}: {'*' * (len(value) - 5)}{value[-5:]}")
            else:
                print(f"✅ {var}: {value[:20]}...")
        else:
            missing_vars.append(var)
            print(f"❌ {var}: Not set")
    
    return missing_vars

def check_dependencies():
    """Check if all required Python packages are installed."""
    print("\n📦 Checking Python dependencies...")
    
    required_packages = [
        'chainlit',
        'langchain',
        'langchain_openai',
        'asyncpg',
        'dotenv',
        'PyPDF2',
        'docx'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    return missing_packages

def check_files():
    """Check if all required files are present."""
    print("\n📁 Checking required files...")
    
    required_files = [
        'my_agent_bot.py',
        'chainlit.toml',
        'requirements.txt',
        'README.md',
        '.env.example',
        '.gitignore',
        'LICENSE'
    ]
    
    missing_files = []
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            missing_files.append(file)
            print(f"❌ {file}")
    
    return missing_files

def main():
    """Run all verification checks."""
    print("🚀 AI Tutor Setup Verification")
    print("=" * 40)
    
    # Check files
    missing_files = check_files()
    
    # Check dependencies
    missing_packages = check_dependencies()
    
    # Check environment
    missing_vars = check_environment()
    
    print("\n" + "=" * 40)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 40)
    
    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
    else:
        print("✅ All required files present")
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("   Run: pip install -r requirements.txt")
    else:
        print("✅ All required packages installed")
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("   Copy .env.example to .env and fill in your values")
    else:
        print("✅ All required environment variables set")
    
    if not missing_files and not missing_packages and not missing_vars:
        print("\n🎉 Setup verification PASSED! You're ready to run the AI Tutor.")
        print("   Run: chainlit run my_agent_bot.py")
        return True
    else:
        print("\n⚠️  Setup verification FAILED. Please fix the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
