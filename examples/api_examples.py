"""
Example usage of the Gherkin Test Generator API
Run this after starting the API server: python src/api.py
"""

import requests
import json

# API Base URL
BASE_URL = "http://localhost:8000"


def health_check():
    """Check if API is running."""
    print("\n1. HEALTH CHECK")
    print("-"*70)
    response = requests.get(f"{BASE_URL}/health")
    print(json.dumps(response.json(), indent=2))


def auto_generate_test(url, model="gpt-4o", headless=True):
    """Automatically generate test scenarios from URL."""
    print(f"\n2. AUTO GENERATE TEST")
    print("-"*70)
    print(f"Analyzing: {url}")
    
    payload = {
        "url": url,
        "headless": headless,
        "model": model
    }
    
    response = requests.post(
        f"{BASE_URL}/api/generate/auto",
        json=payload,
        timeout=300
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✓ Success!")
        print(f"Output file: {result['output_file']}")
        print(f"\nMetadata:")
        print(json.dumps(result['metadata'], indent=2))
        print("\nGenerated Gherkin (preview):\n")
        print(result['gherkin_content'][:500] + "...")
        return result
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)
        return None


def custom_test_from_text(url, test_steps, model="gpt-4o"):
    """Convert custom test steps to Gherkin."""
    print(f"\n3. CUSTOM TEST CONVERSION")
    print("-"*70)
    print(f"URL: {url}")
    print(f"Test steps: {len(test_steps)} characters")
    
    payload = {
        "url": url,
        "test_steps": test_steps,
        "model": model
    }
    
    response = requests.post(
        f"{BASE_URL}/api/generate/custom",
        json=payload,
        timeout=300
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✓ Success!")
        print(f"Output file: {result['output_file']}")
        print("\nGenerated Gherkin:\n")
        print(result['gherkin_content'])
        return result
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)
        return None


def custom_test_from_file(url, file_path, model="gpt-4o"):
    """Upload file with custom test steps."""
    print(f"\n4. CUSTOM TEST FROM FILE")
    print("-"*70)
    print(f"File: {file_path}")
    
    with open(file_path, 'rb') as f:
        files = {'test_file': f}
        data = {
            'url': url,
            'model': model
        }
        
        response = requests.post(
            f"{BASE_URL}/api/generate/custom/file",
            files=files,
            data=data,
            timeout=300
        )
    
    if response.status_code == 200:
        result = response.json()
        print("✓ Success!")
        print(f"Output file: {result['output_file']}")
        print("\nGenerated Gherkin:\n")
        print(result['gherkin_content'])
        return result
    else:
        print(f"✗ Error: {response.status_code}")
        print(response.text)
        return None


def list_files():
    """List all generated feature files."""
    print(f"\n5. LIST GENERATED FILES")
    print("-"*70)
    response = requests.get(f"{BASE_URL}/api/files")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Total files: {result['count']}")
        for file in result['files'][:5]:  # Show first 5
            print(f"\n  📄 {file['filename']}")
            print(f"     Size: {file['size']} bytes")
            print(f"     Modified: {file['modified']}")
    else:
        print(f"✗ Error: {response.status_code}")


def download_file(filename, output_path="downloaded.feature"):
    """Download a generated feature file."""
    print(f"\n6. DOWNLOAD FILE")
    print("-"*70)
    response = requests.get(f"{BASE_URL}/api/download/{filename}")
    
    if response.status_code == 200:
        with open(output_path, 'wb') as f:
            f.write(response.content)
        print(f"✓ Downloaded: {output_path}")
    else:
        print(f"✗ Error: {response.status_code}")


if __name__ == "__main__":
    print("="*70)
    print("AI-Based Gherkin Test Generator - API Examples")
    print("="*70)
    print("\nMake sure the API server is running: python src/api.py")
    print("API Docs: http://localhost:8000/docs")
    
    # Example 1: Health check
    health_check()
    
    # Example 2: Custom test from text
    custom_test_steps = """
Test 1: Validate "Learn More" pop-up functionality

1. Goto the url https://www.tivdak.com/patient-stories/
2. Click the button called "Learn More"
3. A pop up will appear with the title saying "You are now leaving tivdak.com"
4. Click the cancel button
5. Click the button called "Learn More"
6. A pop up will appear with the title saying "You are now leaving tivdak.com"
7. Click the continue button
8. Verify the url has changed to "https://alishasjourney.com/"
    """
    
    custom_test_from_text(
        "https://www.tivdak.com/patient-stories/",
        custom_test_steps
    )
    
    # Example 3: List files
    list_files()
    
    print("\n" + "="*70)
    print("Examples complete!")
    print("="*70)


