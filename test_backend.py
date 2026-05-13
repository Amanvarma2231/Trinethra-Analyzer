"""
Comprehensive testing script for the Trinethra backend.
Run this to verify all components work correctly.
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def test_health():
    """Test 1: Health Check"""
    print_section("Test 1: Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        data = response.json()
        
        print(f"Status: {data.get('status', 'unknown')}")
        print(f"Ollama: {data.get('ollama', 'unknown')}")
        
        if data.get('ollama') == 'connected':
            models = data.get('models_available', [])
            print(f"Available models: {', '.join(models[:5])}")
            return True
        else:
            print("❌ Ollama is not connected. Please start it with: ollama serve")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Backend is not running. Start it with: cd backend && python app.py")
        return False

def test_evidence_extraction():
    """Test 2: Evidence Extraction with minimal transcript"""
    print_section("Test 2: Evidence Extraction")
    
    # Minimal test transcript
    transcript = """
    Interviewer: How is the Fellow doing?
    
    Supervisor: The Fellow has been reliable. She completes work on time and the team likes her.
    She built a tracking system for our inventory. But she needs to communicate more proactively.
    I'd give her a 6 out of 10.
    """
    
    payload = {
        "transcript": transcript,
        "model": "llama3.2"
    }
    
    try:
        print("Sending analysis request...")
        start = time.time()
        response = requests.post(f"{BASE_URL}/analyze", json=payload, timeout=120)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            
            # Check evidence
            evidence = data.get('evidence', {})
            if evidence and 'evidence' in evidence:
                print(f"✅ Evidence extracted: {len(evidence['evidence'])} items")
                for item in evidence['evidence'][:3]:
                    print(f"   - [{item.get('sentiment', '?')}] {item.get('quote', '')[:50]}...")
            else:
                print(f"⚠️  Evidence extraction issues: {evidence.get('error', 'unknown')}")
            
            # Check scoring
            scoring = data.get('scoring', {})
            if scoring and 'score' in scoring:
                print(f"✅ Score: {scoring['score']}/10 - {scoring.get('level_description', '')}")
                print(f"   Confidence: {scoring.get('confidence', '?')}")
            else:
                print(f"⚠️  Scoring issues: {scoring.get('error', 'unknown')}")
            
            # Check KPIs
            kpi = data.get('kpi_mapping', {})
            if kpi and 'kpi_mappings' in kpi:
                print(f"✅ KPIs mapped: {len(kpi['kpi_mappings'])} connections")
                for k in kpi['kpi_mappings'][:2]:
                    print(f"   - {k.get('kpi', '?')}: {k.get('strength', '?')}")
            
            # Check gaps
            gaps = data.get('gap_analysis', {})
            if gaps and 'gaps' in gaps:
                print(f"✅ Gaps identified: {len(gaps['gaps'])} dimensions")
            
            # Check questions
            questions = data.get('followup_questions', {})
            if questions and 'followup_questions' in questions:
                print(f"✅ Follow-up questions: {len(questions['followup_questions'])} generated")
            
            # Check errors
            errors = data.get('errors', [])
            if errors:
                print(f"⚠️  Warnings: {len(errors)}")
                for error in errors:
                    print(f"   - {error[:100]}")
            
            print(f"\n⏱️  Total processing time: {elapsed:.2f} seconds")
            return True
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out. Check if Ollama model is loaded.")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_sample_transcripts():
    """Test 3: Process all sample transcripts"""
    print_section("Test 3: Sample Transcripts")
    
    try:
        with open('../data/sample-transcripts.json', 'r') as f:
            samples = json.load(f)
    except FileNotFoundError:
        print("❌ sample-transcripts.json not found")
        return False
    
    for i, sample in enumerate(samples[:1]):  # Test first one for speed
        print(f"\nProcessing: {sample.get('supervisor_name', 'Unknown')} - {sample.get('company', '')}")
        print(f"Fellow: {sample.get('fellow_name', 'Unknown')} ({sample.get('fellow_tenure_months', '?')} months)")
        
        payload = {
            "transcript": sample['transcript'],
            "model": "llama3.2"
        }
        
        try:
            response = requests.post(f"{BASE_URL}/analyze", json=payload, timeout=120)
            if response.status_code == 200:
                data = response.json()
                scoring = data.get('scoring', {})
                print(f"✅ Analysis complete - Score: {scoring.get('score', '?')}/10")
                
                # Save results for reference
                output_file = f"test_result_{sample['id']}.json"
                with open(output_file, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"   Results saved to {output_file}")
            else:
                print(f"❌ Failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    return True

if __name__ == "__main__":
    print("🧪 Trinethra Backend Test Suite")
    print("="*60)
    
    # Test 1: Health
    if not test_health():
        print("\n❌ Health check failed. Fix issues and try again.")
        sys.exit(1)
    
    # Test 2: Evidence extraction
    if not test_evidence_extraction():
        print("\n❌ Basic analysis failed.")
        sys.exit(1)
    
    # Test 3: Sample transcripts
    test_sample_transcripts()
    
    print("\n" + "="*60)
    print("  ✅ Test suite complete!")
    print("="*60)