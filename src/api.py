"""
FastAPI Application for AI-Based Gherkin Test Generator
Provides REST API endpoints for test scenario generation.
"""

import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, HttpUrl
import uvicorn
from dotenv import load_dotenv

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from html_parser import load_html
from llm_agent import LLMAgent, convert_custom_test_to_gherkin
from playwright_agent import execute_actions
from scenario_builder import write_scenarios

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="AI-Based Gherkin Test Generator API",
    description="LLM-driven autonomous testing system that generates BDD Gherkin scenarios",
    version="1.0.0"
)


# Request Models
class AutoGenerateRequest(BaseModel):
    url: HttpUrl
    headless: bool = True
    model: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.tivdak.com/patient-stories/",
                "headless": True,
                "model": "gpt-4o"
            }
        }


class CustomTestRequest(BaseModel):
    url: HttpUrl
    test_steps: str
    model: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.tivdak.com/patient-stories/",
                "test_steps": """Test 1: Validate "Learn More" pop-up functionality

1. Goto the url https://www.tivdak.com/patient-stories/
2. Click the button called "Learn More"
3. A pop up will appear with the title saying "You are now leaving tivdak.com"
4. Click the cancel button
5. Verify the popup closes""",
                "model": "gpt-4o"
            }
        }


# Response Models
class GenerationResponse(BaseModel):
    success: bool
    message: str
    gherkin_content: str
    output_file: str
    timestamp: str
    metadata: dict


# Health Check
@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": "AI-Based Gherkin Test Generator API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "auto_generate": "/api/generate/auto",
            "custom_test": "/api/generate/custom",
            "custom_test_file": "/api/generate/custom/file",
            "download_feature": "/api/download/{filename}"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    api_key = os.getenv("OPENAI_API_KEY")
    return {
        "status": "healthy",
        "api_key_configured": bool(api_key),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/generate/auto", response_model=GenerationResponse)
async def generate_auto(request: AutoGenerateRequest):
    """
    Automatically analyze webpage and generate Gherkin scenarios.
    
    This endpoint:
    1. Loads the webpage HTML
    2. Uses LLM to identify interactive elements
    3. Executes Playwright actions
    4. Interprets results
    5. Generates Gherkin scenarios
    """
    try:
        url = str(request.url)
        model = request.model or os.getenv("OPENAI_MODEL") or "gpt-4-turbo-preview"
        
        print(f"\n[AUTO MODE] Processing URL: {url}")
        print(f"[AUTO MODE] Model: {model}, Headless: {request.headless}")
        
        # Step 1: Load HTML
        print("[AUTO MODE] Step 1: Loading HTML...")
        raw_html, soup = load_html(url, headless=request.headless)
        
        # Step 2: LLM Analysis
        print("[AUTO MODE] Step 2: Analyzing HTML with LLM...")
        llm_agent = LLMAgent(model=model)
        analysis = llm_agent.analyze_html(raw_html)
        
        # Step 3: Execute Actions
        print("[AUTO MODE] Step 3: Executing actions with Playwright...")
        action_plan = analysis.get('action_plan', [])
        
        if action_plan:
            execution_results = execute_actions(url, action_plan, headless=request.headless)
        else:
            execution_results = {
                "actions_executed": [],
                "hover_results": [],
                "popup_results": [],
                "final_url": url,
                "errors": []
            }
        
        # Step 4: Interpret Results
        print("[AUTO MODE] Step 4: Interpreting results...")
        interpretation = llm_agent.interpret_execution_results(execution_results, raw_html)
        
        # Step 5: Generate Gherkin
        print("[AUTO MODE] Step 5: Generating Gherkin scenarios...")
        gherkin_content = llm_agent.generate_gherkin_scenarios(
            analysis, execution_results, interpretation, url
        )
        
        # Step 6: Write Output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"auto_generated_{timestamp}.feature"
        output_file = write_scenarios(gherkin_content, filename=filename)
        
        print(f"[AUTO MODE] ✓ Complete! Generated: {output_file}")
        
        return GenerationResponse(
            success=True,
            message="Gherkin scenarios generated successfully",
            gherkin_content=gherkin_content,
            output_file=filename,
            timestamp=datetime.now().isoformat(),
            metadata={
                "url": url,
                "mode": "auto",
                "model": model,
                "hover_candidates": len(analysis.get('hover_candidates', [])),
                "popup_candidates": len(analysis.get('popup_candidates', [])),
                "actions_executed": len(execution_results.get('actions_executed', [])),
                "errors": len(execution_results.get('errors', []))
            }
        )
        
    except Exception as e:
        print(f"[AUTO MODE] ❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate/custom", response_model=GenerationResponse)
async def generate_custom(request: CustomTestRequest):
    """
    Convert custom plain-text test steps to Gherkin scenarios.
    
    Accepts test steps in plain text format and uses LLM to convert
    them into proper BDD Gherkin scenarios.
    """
    try:
        url = str(request.url)
        model = request.model or os.getenv("OPENAI_MODEL") or "gpt-4-turbo-preview"
        
        print(f"\n[CUSTOM MODE] Processing custom test for URL: {url}")
        print(f"[CUSTOM MODE] Model: {model}")
        print(f"[CUSTOM MODE] Test steps length: {len(request.test_steps)} characters")
        
        # Convert to Gherkin
        print("[CUSTOM MODE] Converting test steps to Gherkin...")
        gherkin_content = convert_custom_test_to_gherkin(
            request.test_steps,
            url,
            model=model
        )
        
        # Write Output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"custom_generated_{timestamp}.feature"
        output_file = write_scenarios(gherkin_content, filename=filename)
        
        print(f"[CUSTOM MODE] ✓ Complete! Generated: {output_file}")
        
        return GenerationResponse(
            success=True,
            message="Custom test steps converted to Gherkin successfully",
            gherkin_content=gherkin_content,
            output_file=filename,
            timestamp=datetime.now().isoformat(),
            metadata={
                "url": url,
                "mode": "custom",
                "model": model,
                "test_steps_length": len(request.test_steps)
            }
        )
        
    except Exception as e:
        print(f"[CUSTOM MODE] ❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate/custom/file", response_model=GenerationResponse)
async def generate_custom_file(
    url: str = Form(...),
    test_file: UploadFile = File(...),
    model: Optional[str] = Form(None)
):
    """
    Convert custom test steps from uploaded file to Gherkin scenarios.
    
    Accepts a text file containing test steps and converts them to Gherkin.
    """
    try:
        # Read file content
        content = await test_file.read()
        test_steps = content.decode('utf-8')
        
        model = model or os.getenv("OPENAI_MODEL") or "gpt-4-turbo-preview"
        
        print(f"\n[CUSTOM FILE MODE] Processing file: {test_file.filename}")
        print(f"[CUSTOM FILE MODE] URL: {url}")
        print(f"[CUSTOM FILE MODE] Model: {model}")
        
        # Convert to Gherkin
        print("[CUSTOM FILE MODE] Converting test steps to Gherkin...")
        gherkin_content = convert_custom_test_to_gherkin(
            test_steps,
            url,
            model=model
        )
        
        # Write Output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"custom_generated_{timestamp}.feature"
        output_file = write_scenarios(gherkin_content, filename=filename)
        
        print(f"[CUSTOM FILE MODE] ✓ Complete! Generated: {output_file}")
        
        return GenerationResponse(
            success=True,
            message="Custom test file converted to Gherkin successfully",
            gherkin_content=gherkin_content,
            output_file=filename,
            timestamp=datetime.now().isoformat(),
            metadata={
                "url": url,
                "mode": "custom_file",
                "model": model,
                "source_file": test_file.filename,
                "test_steps_length": len(test_steps)
            }
        )
        
    except Exception as e:
        print(f"[CUSTOM FILE MODE] ❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download/{filename}")
async def download_feature_file(filename: str):
    """
    Download a generated feature file.
    
    Args:
        filename: Name of the generated feature file
    """
    file_path = Path("src/output") / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="text/plain"
    )


@app.get("/api/files")
async def list_generated_files():
    """List all generated feature files."""
    output_dir = Path("src/output")
    
    if not output_dir.exists():
        return {"files": []}
    
    files = []
    for file_path in output_dir.glob("*.feature"):
        stat = file_path.stat()
        files.append({
            "filename": file_path.name,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        })
    
    # Sort by modified time, newest first
    files.sort(key=lambda x: x['modified'], reverse=True)
    
    return {"files": files, "count": len(files)}


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    # Check environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY environment variable not set")
        print("\nPlease set your OpenAI API key in .env file:")
        print("  OPENAI_API_KEY=your-api-key-here")
        sys.exit(1)
    
    print("\n" + "="*70)
    print("🚀 Starting AI-Based Gherkin Test Generator API Server")
    print("="*70)
    print(f"\n📋 Configuration:")
    print(f"   OpenAI API Key: {'✓ Configured' if api_key else '✗ Not set'}")
    print(f"   Default Model: {os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')}")
    print(f"\n🌐 Server will start at: http://localhost:8000")
    print(f"📚 API Documentation: http://localhost:8000/docs")
    print(f"📖 Alternative docs: http://localhost:8000/redoc")
    print("\n" + "="*70 + "\n")
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

