#!/usr/bin/env python3
"""
Diagnostic script to test the World Bank API connection and response structure.
This will help us understand why data retrieval is failing in Claude Desktop.
"""

import json
import httpx
import asyncio


API_BASE_URL = "https://search.worldbank.org/api/v3/wds"


async def test_basic_api_call():
    """Test a simple API call to see what we get"""
    print("=" * 70)
    print("TEST 1: Basic API Call")
    print("=" * 70)
    
    params = {
        "format": "json",
        "qterm": "climate",
        "rows": 2,
        "os": 0
    }
    
    print(f"\n📡 Making API request to: {API_BASE_URL}")
    print(f"📋 Parameters: {json.dumps(params, indent=2)}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(API_BASE_URL, params=params)
            
            print(f"\n✅ Response Status: {response.status_code}")
            print(f"✅ Response Headers:")
            for key, value in response.headers.items():
                if key.lower() in ['content-type', 'content-length']:
                    print(f"   {key}: {value}")
            
            # Try to parse JSON
            try:
                data = response.json()
                print(f"\n✅ JSON Parsed Successfully")
                print(f"✅ Response Keys: {list(data.keys())}")
                
                # Check for documents
                if 'documents' in data:
                    documents = data['documents']
                    print(f"✅ Documents field type: {type(documents).__name__}")
                    
                    if isinstance(documents, dict):
                        doc_keys = [k for k in documents.keys() if k != 'facets']
                        print(f"✅ Document IDs found: {doc_keys}")
                        print(f"✅ Number of documents: {len(doc_keys)}")
                        
                        if doc_keys:
                            # Show first document structure
                            first_doc_id = doc_keys[0]
                            first_doc = documents[first_doc_id]
                            print(f"\n📄 First Document Fields:")
                            for key in sorted(first_doc.keys()):
                                value = first_doc[key]
                                value_type = type(value).__name__
                                if isinstance(value, str):
                                    preview = value[:50] + "..." if len(value) > 50 else value
                                    print(f"   {key}: {value_type} = {preview}")
                                else:
                                    print(f"   {key}: {value_type}")
                
                # Check total
                if 'total' in data:
                    print(f"\n✅ Total documents in database: {data['total']:,}")
                
                # Print full response (truncated)
                print(f"\n📋 Full Response (first 1000 chars):")
                response_text = json.dumps(data, indent=2)
                print(response_text[:1000])
                if len(response_text) > 1000:
                    print("... (truncated)")
                
                return True, data
                
            except json.JSONDecodeError as e:
                print(f"\n❌ Failed to parse JSON: {e}")
                print(f"❌ Raw response text (first 500 chars):")
                print(response.text[:500])
                return False, None
                
    except httpx.HTTPStatusError as e:
        print(f"\n❌ HTTP Error: {e.response.status_code}")
        print(f"❌ Response: {e.response.text[:500]}")
        return False, None
        
    except httpx.RequestError as e:
        print(f"\n❌ Network Error: {str(e)}")
        return False, None


async def test_with_filters():
    """Test API call with filters"""
    print("\n\n" + "=" * 70)
    print("TEST 2: API Call with Filters")
    print("=" * 70)
    
    params = {
        "format": "json",
        "qterm": "climate change",
        "count_exact": "Kenya",
        "rows": 1,
        "os": 0
    }
    
    print(f"\n📡 Making API request with filters")
    print(f"📋 Parameters: {json.dumps(params, indent=2)}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(API_BASE_URL, params=params)
            data = response.json()
            
            documents = data.get('documents', {})
            if isinstance(documents, dict):
                doc_keys = [k for k in documents.keys() if k != 'facets']
                print(f"\n✅ Found {len(doc_keys)} documents")
                print(f"✅ Total in database: {data.get('total', 0):,}")
            else:
                print(f"\n❌ Unexpected documents structure: {type(documents).__name__}")
            
            return True, data
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False, None


async def test_document_extraction():
    """Test our document extraction logic"""
    print("\n\n" + "=" * 70)
    print("TEST 3: Document Extraction Logic")
    print("=" * 70)
    
    # Make a fresh API call for this test
    params = {
        "format": "json",
        "qterm": "climate",
        "rows": 2,
        "os": 0
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(API_BASE_URL, params=params)
            data = response.json()
    except Exception as e:
        print(f"\n❌ Cannot test extraction - API call failed: {str(e)}")
        return False
    
    print(f"\n🔧 Testing document extraction...")
    
    # Test current extraction method
    documents = data.get('documents', {})
    docs_list = [
        doc 
        for key, doc in documents.items() 
        if key != 'facets' and isinstance(doc, dict)
    ]
    
    print(f"✅ Extracted {len(docs_list)} documents")
    
    if docs_list:
        print(f"\n📄 First document structure:")
        first_doc = docs_list[0]
        
        # Test field extractions
        print(f"\n🔧 Testing field extractions:")
        
        # Test title
        repnme = first_doc.get('repnme', {})
        if isinstance(repnme, dict):
            repnme = repnme.get('repnme', 'Untitled')
        title = first_doc.get('display_title', repnme)
        print(f"   Title: {title}")
        
        # Test count
        count = first_doc.get('count', 'N/A')
        if isinstance(count, list):
            countries = ', '.join(count)
        elif isinstance(count, str):
            countries = count
        else:
            countries = 'N/A'
        print(f"   Countries: {countries}")
        
        # Test abstracts
        abstracts = first_doc.get('abstracts', 'No abstract')
        if isinstance(abstracts, dict):
            abstract = abstracts.get('cdata!', abstracts.get('abstract', 'No abstract'))
        else:
            abstract = abstracts
        abstract_preview = abstract[:100] + "..." if len(abstract) > 100 else abstract
        print(f"   Abstract: {abstract_preview}")
        
        print(f"\n✅ All field extractions working correctly!")
        return True
    else:
        print(f"\n❌ No documents extracted!")
        return False


async def test_empty_query():
    """Test what happens with empty or broad query"""
    print("\n\n" + "=" * 70)
    print("TEST 4: Empty/Broad Query")
    print("=" * 70)
    
    params = {
        "format": "json",
        "qterm": "*",  # Match everything
        "rows": 2,
        "os": 0
    }
    
    print(f"\n📡 Testing with broad query (*)")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(API_BASE_URL, params=params)
            data = response.json()
            
            total = data.get('total', 0)
            documents = data.get('documents', {})
            doc_count = len([k for k in documents.keys() if k != 'facets'])
            
            print(f"\n✅ Total documents in database: {total:,}")
            print(f"✅ Documents returned: {doc_count}")
            
            return True, data
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False, None


async def main():
    """Run all diagnostic tests"""
    print("\n" + "=" * 70)
    print("🔬 WORLD BANK MCP SERVER - API DIAGNOSTICS")
    print("=" * 70)
    print("\nThis will test the actual World Bank API to diagnose retrieval issues.")
    print()
    
    # Run tests
    tests = [
        ("Basic API Call", test_basic_api_call),
        ("API with Filters", test_with_filters),
        ("Document Extraction", test_document_extraction),
        ("Broad Query", test_empty_query),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            if isinstance(result, tuple):
                success = result[0]
            else:
                success = result
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {str(e)}")
            results.append((name, False))
    
    # Print summary
    print("\n\n" + "=" * 70)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 70)
    
    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All diagnostics passed! The API is working correctly.")
        print("   If you're still having issues in Claude Desktop, the problem might be:")
        print("   1. MCP server configuration in Claude Desktop")
        print("   2. Network connectivity from Claude Desktop")
        print("   3. Tool invocation format")
    else:
        print("\n❌ Some diagnostics failed. Please review the output above.")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
