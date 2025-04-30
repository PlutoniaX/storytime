import requests
import sys
import time
from datetime import datetime

class BedtimeStoryAPITester:
    def __init__(self, base_url="https://44a617fb-1c44-47e1-970b-45c67994ebc6.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.story_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                if response.headers.get('content-type') and 'application/json' in response.headers.get('content-type'):
                    return success, response.json()
                return success, None
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"Response: {response.text}")
                return False, None

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, None

    def test_root_endpoint(self):
        """Test the root endpoint"""
        success, response = self.run_test(
            "Root Endpoint",
            "GET",
            "",
            200
        )
        return success

    def test_generate_story(self, prompt="a friendly dragon who learns to share", duration=5, age=5):
        """Test story generation with age parameter"""
        success, response = self.run_test(
            "Generate Story",
            "POST",
            "generate-story",
            200,
            data={"prompt": prompt, "duration": duration, "age": age}
        )
        
        if success and response:
            self.story_id = response.get('id')
            content = response.get('content', '')
            title = content.split('\n')[0] if content else 'No title'
            print(f"Generated story with ID: {self.story_id}")
            print(f"Story title: {title}")
            print(f"Image URL: {response.get('image_url', 'None')}")
            return True
        return False

    def test_generate_story_different_ages(self):
        """Test story generation for different age groups"""
        age_groups = [3, 5, 8, 11]  # Representative of age ranges 2-3, 4-6, 7-9, 10-12
        prompts = ["a teddy bear's adventure", "a magical forest", "space explorers", "a time travel mystery"]
        
        results = []
        for i, age in enumerate(age_groups):
            print(f"\n🧒 Testing story generation for age: {age}")
            success, response = self.run_test(
                f"Generate Story for Age {age}",
                "POST",
                "generate-story",
                200,
                data={"prompt": prompts[i], "duration": 5, "age": age}
            )
            
            if success and response:
                content = response.get('content', '')
                title = content.split('\n')[0] if content else 'No title'
                print(f"Generated age-appropriate story: {title}")
                results.append(True)
            else:
                results.append(False)
        
        return all(results)

    def test_generate_story_different_languages(self):
        """Test story generation with prompts in different languages"""
        language_prompts = [
            "a cat who learns to fly",  # English
            "un gato que aprende a volar",  # Spanish
            "un chat qui apprend à voler"   # French
        ]
        
        results = []
        for i, prompt in enumerate(language_prompts):
            language = ["English", "Spanish", "French"][i]
            print(f"\n🌐 Testing story generation in {language}")
            success, response = self.run_test(
                f"Generate Story in {language}",
                "POST",
                "generate-story",
                200,
                data={"prompt": prompt, "duration": 5, "age": 5}
            )
            
            if success and response:
                content = response.get('content', '')
                title = content.split('\n')[0] if content else 'No title'
                print(f"Generated story in {language}: {title}")
                results.append(True)
            else:
                results.append(False)
        
        return all(results)

    def test_get_stories(self):
        """Test retrieving all stories"""
        success, response = self.run_test(
            "Get All Stories",
            "GET",
            "stories",
            200
        )
        
        if success and response:
            print(f"Retrieved {len(response)} stories")
            return True
        return False

    def test_get_story(self, story_id):
        """Test retrieving a specific story"""
        success, response = self.run_test(
            "Get Specific Story",
            "GET",
            f"story/{story_id}",
            200
        )
        
        if success and response:
            content = response.get('content', '')
            title = content.split('\n')[0] if content else 'No title'
            print(f"Retrieved story: {title}")
            return True
        return False

    def test_text_to_speech(self, story_id):
        """Test text-to-speech generation"""
        success, _ = self.run_test(
            "Text-to-Speech Generation",
            "POST",
            "text-to-speech",
            200,
            data={"story_id": story_id}  # Send the story_id as a JSON object with a "story_id" field
        )
        return success

def main():
    # Setup
    tester = BedtimeStoryAPITester()
    
    # Run tests
    print("🧪 Starting Bedtime Story API Tests 🧪")
    
    # Test root endpoint
    if not tester.test_root_endpoint():
        print("❌ Root endpoint test failed, stopping tests")
        return 1
    
    # Test story generation with default parameters
    if not tester.test_generate_story():
        print("❌ Story generation failed, stopping tests")
        return 1
    
    # Test story generation for different age groups
    print("\n🧪 Testing Age-Appropriate Content Generation 🧪")
    if not tester.test_generate_story_different_ages():
        print("❌ Age-appropriate story generation tests failed")
    else:
        print("✅ Successfully generated stories for different age groups")
    
    # Test story generation with different languages
    print("\n🧪 Testing Multi-Language Support 🧪")
    if not tester.test_generate_story_different_languages():
        print("❌ Multi-language story generation tests failed")
    else:
        print("✅ Successfully generated stories in different languages")
    
    # Test get all stories
    if not tester.test_get_stories():
        print("❌ Get stories failed")
    
    # Test get specific story
    if tester.story_id and not tester.test_get_story(tester.story_id):
        print("❌ Get specific story failed")
    
    # Test text-to-speech
    if tester.story_id and not tester.test_text_to_speech(tester.story_id):
        print("❌ Text-to-speech generation failed")
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())