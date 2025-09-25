#!/usr/bin/env python3
"""
Script to run the LangGraph training application locally
"""
import os
import sys
import subprocess
from pathlib import Path

def check_requirements():
    """Check if all requirements are installed"""
    print("= Checking requirements...")

    # Check if .env file exists
    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        print("   .env file not found!")
        print("=Ý Please copy .env.example to .env and configure your API keys")
        return False

    # Check if requirements.txt exists and packages are installed
    requirements_file = Path(__file__).parent.parent / "requirements.txt"
    if not requirements_file.exists():
        print("L requirements.txt not found!")
        return False

    try:
        # Try importing key modules
        import fastapi
        import uvicorn
        import langgraph
        print(" All requirements appear to be installed")
        return True
    except ImportError as e:
        print(f"L Missing required package: {e.name}")
        print("=¡ Run: pip install -r requirements.txt")
        return False

def start_application():
    """Start the FastAPI application"""
    print("\n=€ Starting LangGraph Training API...")

    # Change to the parent directory
    os.chdir(Path(__file__).parent.parent)

    # Add current directory to Python path
    sys.path.insert(0, str(Path.cwd()))

    try:
        # Import and run the app
        import uvicorn
        from app.main import app

        print("=á Starting server on http://localhost:8000")
        print("=Ö API Documentation: http://localhost:8000/docs")
        print("= Alternative Docs: http://localhost:8000/redoc")
        print("\nù  Press Ctrl+C to stop the server\n")

        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )

    except KeyboardInterrupt:
        print("\n=K Shutting down server...")
    except Exception as e:
        print(f"L Error starting server: {str(e)}")
        sys.exit(1)

def main():
    """Main function"""
    print("<¯ LangGraph Training - Local Development Server")
    print("=" * 50)

    # Check requirements
    if not check_requirements():
        sys.exit(1)

    # Start application
    start_application()

if __name__ == "__main__":
    main()