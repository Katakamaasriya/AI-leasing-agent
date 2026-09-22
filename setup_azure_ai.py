"""
Azure OpenAI Setup Script
This script helps you configure and test your Azure OpenAI integration
"""

import os
import sys
from dotenv import load_dotenv
from openai import AzureOpenAI

def test_azure_openai_connection():
    """Test Azure OpenAI connection with provided credentials"""
    
    print("Azure OpenAI Configuration Test")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Get Azure OpenAI credentials
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    model = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o-mini")
    
    print(f"\nConfiguration Check:")
    print(f"API Key: {'Set' if api_key else 'Missing'}")
    print(f"Endpoint: {'Set' if endpoint else 'Missing'}")
    print(f"API Version: {api_version}")
    print(f"Model: {model}")
    
    if not api_key or not endpoint:
        print("\nAzure OpenAI credentials not configured!")
        print("\nPlease set the following in your .env file:")
        print("AZURE_OPENAI_API_KEY=your_api_key_here")
        print("AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/")
        return False
    
    print(f"\nTesting connection to Azure OpenAI...")
    
    try:
        # Initialize Azure OpenAI client
        client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint
        )
        
        # Test with a simple completion
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Azure OpenAI connection successful!' in one sentence."}
            ],
            max_tokens=50
        )
        
        result = response.choices[0].message.content
        print(f"Azure OpenAI connection successful!")
        print(f"AI Response: {result}")
        print(f"Model used: {model}")
        print(f"Connection test passed!")
        
        return True
        
    except Exception as e:
        print(f"Azure OpenAI connection failed!")
        print(f"Error: {e}")
        print(f"\nTroubleshooting tips:")
        print("1. Check your API key is correct")
        print("2. Verify your endpoint URL is correct")
        print("3. Ensure your model deployment exists")
        print("4. Check your Azure subscription has credits")
        return False

def show_setup_instructions():
    """Show step-by-step Azure OpenAI setup instructions"""
    
    print("\nAzure OpenAI Setup Instructions")
    print("=" * 50)
    
    print("\nStep 1: Create Azure OpenAI Resource")
    print("   1. Go to Azure Portal: https://portal.azure.com")
    print("   2. Search for 'Azure OpenAI'")
    print("   3. Click 'Create' and fill in:")
    print("      - Subscription: Your subscription with credits")
    print("      - Resource group: Create new or use existing")
    print("      - Region: Choose nearest region (e.g., eastus)")
    print("      - Name: e.g., 'leasing-openai'")
    print("      - Pricing tier: Standard S0")
    
    print("\nStep 2: Deploy GPT-4o-mini Model")
    print("   1. Go to your Azure OpenAI resource")
    print("   2. Go to 'Deployments' in left menu")
    print("   3. Click 'Create deployment'")
    print("   4. Select model: 'gpt-4o-mini'")
    print("   5. Deployment name: 'gpt4o-mini' (or your choice)")
    print("   6. Click 'Create'")
    
    print("\nStep 3: Get Credentials")
    print("   1. Go to your Azure OpenAI resource")
    print("   2. Go to 'Keys and Endpoint' in left menu")
    print("   3. Copy:")
    print("      - API Key")
    print("      - Endpoint URL")
    
    print("\nStep 4: Configure .env File")
    print("   Update your .env file with:")
    print("   AZURE_OPENAI_API_KEY=your_copied_api_key")
    print("   AZURE_OPENAI_ENDPOINT=your_copied_endpoint")
    print("   AZURE_OPENAI_MODEL=gpt4o-mini")  # Your deployment name
    
    print("\nStep 5: Test Connection")
    print("   Run this script again to test:")
    print("   python setup_azure_ai.py")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        show_setup_instructions()
    else:
        success = test_azure_openai_connection()
        if not success:
            print("\nNeed help? Run: python setup_azure_ai.py --help")
        
        sys.exit(0 if success else 1)