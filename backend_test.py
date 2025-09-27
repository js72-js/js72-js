#!/usr/bin/env python3
"""
Backend API Testing for Sales Manager Application - Phase 1
Testing Infrastructure and Authentication endpoints
"""

import requests
import json
import sys
from datetime import datetime

# Base URL from environment
BASE_URL = "https://sales-manager-25.preview.emergentagent.com/api"

class SalesManagerTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.auth_token = None
        self.test_results = []
        
    def log_test(self, test_name, success, details, response_data=None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "response_data": response_data
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        if response_data and not success:
            print(f"   Response: {response_data}")
        print()

    def test_initialization(self):
        """Test POST /api/setup/init"""
        print("=== Testing Application Initialization ===")
        
        try:
            response = self.session.post(f"{self.base_url}/setup/init")
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "initialized successfully" in data["message"]:
                    self.log_test(
                        "Application Initialization", 
                        True, 
                        f"App initialized successfully (Status: {response.status_code})",
                        data
                    )
                else:
                    self.log_test(
                        "Application Initialization", 
                        False, 
                        f"Unexpected response format (Status: {response.status_code})",
                        data
                    )
            else:
                self.log_test(
                    "Application Initialization", 
                    False, 
                    f"HTTP {response.status_code}: {response.text}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "Application Initialization", 
                False, 
                f"Request failed: {str(e)}"
            )

    def test_admin_login(self):
        """Test POST /api/auth/login with admin credentials"""
        print("=== Testing Admin Login ===")
        
        login_data = {
            "email": "admin@salesmanager.com",
            "password": "admin123"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if response has required fields
                required_fields = ["access_token", "token_type", "user"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    # Store token for future requests
                    self.auth_token = data["access_token"]
                    
                    # Verify user data
                    user = data["user"]
                    if (user.get("email") == "admin@salesmanager.com" and 
                        user.get("role") == "admin" and
                        user.get("name") == "Administrateur"):
                        
                        self.log_test(
                            "Admin Login", 
                            True, 
                            f"Login successful, JWT token received, user data correct",
                            {
                                "token_type": data["token_type"],
                                "user_email": user["email"],
                                "user_role": user["role"],
                                "user_name": user["name"]
                            }
                        )
                    else:
                        self.log_test(
                            "Admin Login", 
                            False, 
                            f"User data incorrect",
                            user
                        )
                else:
                    self.log_test(
                        "Admin Login", 
                        False, 
                        f"Missing required fields: {missing_fields}",
                        data
                    )
            else:
                self.log_test(
                    "Admin Login", 
                    False, 
                    f"HTTP {response.status_code}: {response.text}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "Admin Login", 
                False, 
                f"Request failed: {str(e)}"
            )

    def test_protected_endpoint(self):
        """Test GET /api/auth/me with JWT token"""
        print("=== Testing Protected Endpoint (/auth/me) ===")
        
        if not self.auth_token:
            self.log_test(
                "Protected Endpoint Access", 
                False, 
                "No auth token available from previous login test"
            )
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{self.base_url}/auth/me", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                if (data.get("email") == "admin@salesmanager.com" and 
                    data.get("role") == "admin"):
                    
                    self.log_test(
                        "Protected Endpoint Access", 
                        True, 
                        f"Successfully accessed protected endpoint with JWT token",
                        {
                            "user_email": data["email"],
                            "user_role": data["role"],
                            "user_name": data.get("name")
                        }
                    )
                else:
                    self.log_test(
                        "Protected Endpoint Access", 
                        False, 
                        f"Unexpected user data returned",
                        data
                    )
            else:
                self.log_test(
                    "Protected Endpoint Access", 
                    False, 
                    f"HTTP {response.status_code}: {response.text}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "Protected Endpoint Access", 
                False, 
                f"Request failed: {str(e)}"
            )

    def test_user_registration(self):
        """Test POST /api/auth/register"""
        print("=== Testing User Registration ===")
        
        # Use realistic test data
        user_data = {
            "email": "marie.dupont@salesmanager.com",
            "password": "marie2025!",
            "role": "serveur",
            "name": "Marie Dupont"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/auth/register",
                json=user_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if user was created with correct data
                if (data.get("email") == user_data["email"] and 
                    data.get("role") == user_data["role"] and
                    data.get("name") == user_data["name"] and
                    "id" in data):
                    
                    self.log_test(
                        "User Registration", 
                        True, 
                        f"User registered successfully with correct role",
                        {
                            "user_id": data["id"],
                            "email": data["email"],
                            "role": data["role"],
                            "name": data["name"]
                        }
                    )
                else:
                    self.log_test(
                        "User Registration", 
                        False, 
                        f"User data mismatch or missing fields",
                        data
                    )
            else:
                self.log_test(
                    "User Registration", 
                    False, 
                    f"HTTP {response.status_code}: {response.text}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "User Registration", 
                False, 
                f"Request failed: {str(e)}"
            )

    def test_categories_endpoint(self):
        """Test GET /api/categories with authentication"""
        print("=== Testing Categories Endpoint ===")
        
        if not self.auth_token:
            self.log_test(
                "Categories Endpoint", 
                False, 
                "No auth token available"
            )
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            response = self.session.get(f"{self.base_url}/categories", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, list) and len(data) >= 3:
                    # Check for default categories
                    category_names = [cat.get("name") for cat in data]
                    expected_categories = ["Boissons", "Alimentaire", "Hygiène"]
                    
                    found_categories = [cat for cat in expected_categories if cat in category_names]
                    
                    if len(found_categories) == len(expected_categories):
                        self.log_test(
                            "Categories Endpoint", 
                            True, 
                            f"Default categories found: {found_categories}",
                            {"categories_count": len(data), "categories": category_names}
                        )
                    else:
                        self.log_test(
                            "Categories Endpoint", 
                            False, 
                            f"Missing default categories. Found: {found_categories}, Expected: {expected_categories}",
                            {"categories": category_names}
                        )
                else:
                    self.log_test(
                        "Categories Endpoint", 
                        False, 
                        f"Expected list with at least 3 categories, got: {type(data)} with {len(data) if isinstance(data, list) else 'N/A'} items",
                        data
                    )
            else:
                self.log_test(
                    "Categories Endpoint", 
                    False, 
                    f"HTTP {response.status_code}: {response.text}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "Categories Endpoint", 
                False, 
                f"Request failed: {str(e)}"
            )

    def test_error_scenarios(self):
        """Test error scenarios"""
        print("=== Testing Error Scenarios ===")
        
        # Test 1: Login with wrong credentials
        try:
            wrong_login = {
                "email": "admin@salesmanager.com",
                "password": "wrongpassword"
            }
            
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json=wrong_login,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 401:
                self.log_test(
                    "Wrong Credentials Error", 
                    True, 
                    f"Correctly rejected wrong credentials with HTTP 401",
                    {"status_code": response.status_code}
                )
            else:
                self.log_test(
                    "Wrong Credentials Error", 
                    False, 
                    f"Expected HTTP 401, got {response.status_code}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "Wrong Credentials Error", 
                False, 
                f"Request failed: {str(e)}"
            )
        
        # Test 2: Access protected endpoint without token
        try:
            response = self.session.get(f"{self.base_url}/auth/me")
            
            if response.status_code == 403:
                self.log_test(
                    "Unauthorized Access Error", 
                    True, 
                    f"Correctly rejected unauthorized access with HTTP 403",
                    {"status_code": response.status_code}
                )
            else:
                self.log_test(
                    "Unauthorized Access Error", 
                    False, 
                    f"Expected HTTP 403, got {response.status_code}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "Unauthorized Access Error", 
                False, 
                f"Request failed: {str(e)}"
            )

    def test_api_root(self):
        """Test GET /api/ root endpoint"""
        print("=== Testing API Root Endpoint ===")
        
        try:
            response = self.session.get(f"{self.base_url}/")
            
            if response.status_code == 200:
                data = response.json()
                if "Sales Manager API" in data.get("message", ""):
                    self.log_test(
                        "API Root Endpoint", 
                        True, 
                        f"API root accessible and returns correct message",
                        data
                    )
                else:
                    self.log_test(
                        "API Root Endpoint", 
                        False, 
                        f"Unexpected response format",
                        data
                    )
            else:
                self.log_test(
                    "API Root Endpoint", 
                    False, 
                    f"HTTP {response.status_code}: {response.text}",
                    response.text
                )
                
        except Exception as e:
            self.log_test(
                "API Root Endpoint", 
                False, 
                f"Request failed: {str(e)}"
            )

    def run_all_tests(self):
        """Run all tests in sequence"""
        print(f"🚀 Starting Backend API Tests for Sales Manager")
        print(f"📍 Base URL: {self.base_url}")
        print(f"⏰ Test started at: {datetime.now().isoformat()}")
        print("=" * 60)
        
        # Test sequence
        self.test_api_root()
        self.test_initialization()
        self.test_admin_login()
        self.test_protected_endpoint()
        self.test_user_registration()
        self.test_categories_endpoint()
        self.test_error_scenarios()
        
        # Summary
        print("=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  • {result['test']}: {result['details']}")
        
        print(f"\n⏰ Test completed at: {datetime.now().isoformat()}")
        
        return passed_tests == total_tests

if __name__ == "__main__":
    tester = SalesManagerTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)