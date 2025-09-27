#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Phase 8: Role Management System
Tests role-based access control, user management, and permissions across all endpoints
"""

import requests
import json
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://salesync-1.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@salesmanager.com"
ADMIN_PASSWORD = "admin123"

class BackendTester:
    def __init__(self):
        self.admin_token = None
        self.manager_token = None
        self.server_token = None
        self.test_users = {}
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = f"{status} - {test_name}"
        if details:
            result += f": {details}"
        print(result)
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        
    def make_request(self, method: str, endpoint: str, token: str = None, data: dict = None) -> requests.Response:
        """Make HTTP request with optional authentication"""
        url = f"{BASE_URL}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=30)
            elif method == "PATCH":
                response = requests.patch(url, headers=headers, json=data, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            return response
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            raise
    
    def authenticate_admin(self) -> bool:
        """Authenticate as admin user"""
        try:
            response = self.make_request("POST", "/auth/login", data={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            })
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data["access_token"]
                self.log_test("Admin Authentication", True, f"Token obtained for {ADMIN_EMAIL}")
                return True
            else:
                self.log_test("Admin Authentication", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_test("Admin Authentication", False, f"Exception: {str(e)}")
            return False
    
    def create_test_users(self) -> bool:
        """Create test users with different roles"""
        timestamp = int(time.time())
        test_users_data = [
            {"email": f"manager.test.{timestamp}@salesmanager.com", "password": "manager123", "role": "gérant", "name": "Test Manager"},
            {"email": f"server.test.{timestamp}@salesmanager.com", "password": "server123", "role": "serveur", "name": "Test Server"}
        ]
        
        success_count = 0
        for user_data in test_users_data:
            try:
                response = self.make_request("POST", "/auth/register", data=user_data)
                
                if response.status_code == 200:
                    user_info = response.json()
                    self.test_users[user_data["role"]] = {
                        "id": user_info["id"],
                        "email": user_data["email"],
                        "password": user_data["password"],
                        "role": user_data["role"]
                    }
                    self.log_test(f"Create Test User ({user_data['role']})", True, f"User ID: {user_info['id']}")
                    success_count += 1
                else:
                    self.log_test(f"Create Test User ({user_data['role']})", False, f"Status: {response.status_code}")
            except Exception as e:
                self.log_test(f"Create Test User ({user_data['role']})", False, f"Exception: {str(e)}")
        
        return success_count == len(test_users_data)
    
    def authenticate_test_users(self) -> bool:
        """Authenticate test users and get their tokens"""
        success_count = 0
        
        for role, user_info in self.test_users.items():
            try:
                response = self.make_request("POST", "/auth/login", data={
                    "email": user_info["email"],
                    "password": user_info["password"]
                })
                
                if response.status_code == 200:
                    data = response.json()
                    if role == "gérant":
                        self.manager_token = data["access_token"]
                    elif role == "serveur":
                        self.server_token = data["access_token"]
                    
                    self.log_test(f"Authenticate Test User ({role})", True, f"Token obtained")
                    success_count += 1
                else:
                    self.log_test(f"Authenticate Test User ({role})", False, f"Status: {response.status_code}")
            except Exception as e:
                self.log_test(f"Authenticate Test User ({role})", False, f"Exception: {str(e)}")
        
        return success_count == len(self.test_users)
    
    def test_role_information_api(self):
        """Test GET /api/roles endpoint"""
        try:
            # Test with admin token
            response = self.make_request("GET", "/roles", token=self.admin_token)
            
            if response.status_code == 200:
                data = response.json()
                roles = data.get("roles", [])
                
                expected_roles = ["admin", "gérant", "serveur"]
                found_roles = [role["value"] for role in roles]
                
                if all(role in found_roles for role in expected_roles):
                    self.log_test("GET /api/roles - Admin Access", True, f"Found {len(roles)} roles")
                else:
                    self.log_test("GET /api/roles - Admin Access", False, f"Missing roles. Found: {found_roles}")
            else:
                self.log_test("GET /api/roles - Admin Access", False, f"Status: {response.status_code}")
                
            # Test with manager token
            response = self.make_request("GET", "/roles", token=self.manager_token)
            if response.status_code == 200:
                self.log_test("GET /api/roles - Manager Access", True, "Manager can access roles")
            else:
                self.log_test("GET /api/roles - Manager Access", False, f"Status: {response.status_code}")
                
            # Test with server token
            response = self.make_request("GET", "/roles", token=self.server_token)
            if response.status_code == 200:
                self.log_test("GET /api/roles - Server Access", True, "Server can access roles")
            else:
                self.log_test("GET /api/roles - Server Access", False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.log_test("GET /api/roles", False, f"Exception: {str(e)}")
    
    def test_user_management_api(self):
        """Test user management endpoints"""
        # Test GET /api/users (Admin only)
        try:
            response = self.make_request("GET", "/users", token=self.admin_token)
            if response.status_code == 200:
                users = response.json()
                self.log_test("GET /api/users - Admin Access", True, f"Retrieved {len(users)} users")
            else:
                self.log_test("GET /api/users - Admin Access", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("GET /api/users - Admin Access", False, f"Exception: {str(e)}")
        
        # Test GET /api/users with non-admin (should fail)
        try:
            response = self.make_request("GET", "/users", token=self.manager_token)
            if response.status_code == 403:
                self.log_test("GET /api/users - Manager Access (Should Fail)", True, "Correctly denied access")
            else:
                self.log_test("GET /api/users - Manager Access (Should Fail)", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("GET /api/users - Manager Access (Should Fail)", False, f"Exception: {str(e)}")
        
        try:
            response = self.make_request("GET", "/users", token=self.server_token)
            if response.status_code == 403:
                self.log_test("GET /api/users - Server Access (Should Fail)", True, "Correctly denied access")
            else:
                self.log_test("GET /api/users - Server Access (Should Fail)", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("GET /api/users - Server Access (Should Fail)", False, f"Exception: {str(e)}")
    
    def test_role_update_api(self):
        """Test PATCH /api/users/{id}/role endpoint"""
        if not self.test_users:
            self.log_test("Role Update Tests", False, "No test users available")
            return
            
        manager_user = self.test_users.get("gérant")
        if not manager_user:
            self.log_test("Role Update Tests", False, "Manager test user not found")
            return
        
        # Test valid role update (Admin changing manager to server)
        try:
            response = self.make_request("PATCH", f"/users/{manager_user['id']}/role", 
                                       token=self.admin_token, 
                                       data={"role": "serveur"})
            
            if response.status_code == 200:
                updated_user = response.json()
                if updated_user["role"] == "serveur":
                    self.log_test("PATCH /api/users/{id}/role - Valid Update", True, "Role updated successfully")
                    
                    # Update back to manager for other tests
                    self.make_request("PATCH", f"/users/{manager_user['id']}/role", 
                                    token=self.admin_token, 
                                    data={"role": "gérant"})
                else:
                    self.log_test("PATCH /api/users/{id}/role - Valid Update", False, "Role not updated correctly")
            else:
                self.log_test("PATCH /api/users/{id}/role - Valid Update", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("PATCH /api/users/{id}/role - Valid Update", False, f"Exception: {str(e)}")
        
        # Test invalid role
        try:
            response = self.make_request("PATCH", f"/users/{manager_user['id']}/role", 
                                       token=self.admin_token, 
                                       data={"role": "invalid_role"})
            
            if response.status_code == 400:
                self.log_test("PATCH /api/users/{id}/role - Invalid Role", True, "Correctly rejected invalid role")
            else:
                self.log_test("PATCH /api/users/{id}/role - Invalid Role", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("PATCH /api/users/{id}/role - Invalid Role", False, f"Exception: {str(e)}")
        
        # Test non-admin trying to update role
        try:
            response = self.make_request("PATCH", f"/users/{manager_user['id']}/role", 
                                       token=self.manager_token, 
                                       data={"role": "admin"})
            
            if response.status_code == 403:
                self.log_test("PATCH /api/users/{id}/role - Non-Admin Access", True, "Correctly denied access")
            else:
                self.log_test("PATCH /api/users/{id}/role - Non-Admin Access", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("PATCH /api/users/{id}/role - Non-Admin Access", False, f"Exception: {str(e)}")
    
    def test_self_protection_logic(self):
        """Test that admin cannot change own role or deactivate own account"""
        # Get admin user info
        try:
            response = self.make_request("GET", "/auth/me", token=self.admin_token)
            if response.status_code == 200:
                admin_user = response.json()
                admin_id = admin_user["id"]
                
                # Test admin trying to change own role
                response = self.make_request("PATCH", f"/users/{admin_id}/role", 
                                           token=self.admin_token, 
                                           data={"role": "gérant"})
                
                if response.status_code == 400:
                    self.log_test("Self-Protection - Role Change", True, "Admin cannot change own role")
                else:
                    self.log_test("Self-Protection - Role Change", False, f"Status: {response.status_code}")
                
                # Test admin trying to deactivate own account
                response = self.make_request("DELETE", f"/users/{admin_id}", token=self.admin_token)
                
                if response.status_code == 400:
                    self.log_test("Self-Protection - Account Deactivation", True, "Admin cannot deactivate own account")
                else:
                    self.log_test("Self-Protection - Account Deactivation", False, f"Status: {response.status_code}")
            else:
                self.log_test("Self-Protection Tests", False, "Could not get admin user info")
        except Exception as e:
            self.log_test("Self-Protection Tests", False, f"Exception: {str(e)}")
    
    def test_user_deactivation(self):
        """Test DELETE /api/users/{id} endpoint"""
        if not self.test_users:
            self.log_test("User Deactivation Tests", False, "No test users available")
            return
            
        server_user = self.test_users.get("serveur")
        if not server_user:
            self.log_test("User Deactivation Tests", False, "Server test user not found")
            return
        
        # Test admin deactivating user
        try:
            response = self.make_request("DELETE", f"/users/{server_user['id']}", token=self.admin_token)
            
            if response.status_code == 200:
                self.log_test("DELETE /api/users/{id} - Admin Access", True, "User deactivated successfully")
            else:
                self.log_test("DELETE /api/users/{id} - Admin Access", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("DELETE /api/users/{id} - Admin Access", False, f"Exception: {str(e)}")
        
        # Test non-admin trying to deactivate user
        manager_user = self.test_users.get("gérant")
        if manager_user:
            try:
                response = self.make_request("DELETE", f"/users/{manager_user['id']}", token=self.manager_token)
                
                if response.status_code == 403:
                    self.log_test("DELETE /api/users/{id} - Non-Admin Access", True, "Correctly denied access")
                else:
                    self.log_test("DELETE /api/users/{id} - Non-Admin Access", False, f"Status: {response.status_code}")
            except Exception as e:
                self.log_test("DELETE /api/users/{id} - Non-Admin Access", False, f"Exception: {str(e)}")
    
    def test_cross_endpoint_permissions(self):
        """Test role-based permissions across different endpoints"""
        
        # Test Products endpoints
        self.test_endpoint_permissions("/products", "GET", {
            "admin": True, "manager": True, "server": True
        })
        
        # Get a valid category ID first
        try:
            response = self.make_request("GET", "/categories", token=self.admin_token)
            if response.status_code == 200:
                categories = response.json()
                if categories:
                    category_id = categories[0]["id"]
                    self.test_endpoint_permissions("/products", "POST", {
                        "admin": True, "manager": True, "server": False
                    }, data={"name": "Test Product", "code": f"TEST{int(time.time())}", "category_id": category_id, 
                            "purchase_price": 10.0, "selling_price": 15.0, "stock": 100})
                else:
                    self.log_test("POST /products - No Categories Available", False, "No categories found for product creation")
            else:
                self.log_test("POST /products - Category Fetch Failed", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("POST /products - Category Fetch Error", False, f"Exception: {str(e)}")
        
        # Test Categories endpoints
        self.test_endpoint_permissions("/categories", "GET", {
            "admin": True, "manager": True, "server": True
        })
        
        self.test_endpoint_permissions("/categories", "POST", {
            "admin": True, "manager": True, "server": False
        }, data={"name": "Test Category", "description": "Test description"})
        
        # Test Sales endpoints
        self.test_endpoint_permissions("/sales", "POST", {
            "admin": True, "manager": True, "server": True
        })
        
        self.test_endpoint_permissions("/sales/pending", "GET", {
            "admin": True, "manager": True, "server": True
        })
        
        # Test Purchases endpoints (Admin/Manager only)
        self.test_endpoint_permissions("/suppliers", "GET", {
            "admin": True, "manager": True, "server": False
        })
        
        self.test_endpoint_permissions("/purchases", "GET", {
            "admin": True, "manager": True, "server": False
        })
        
        # Test Reports endpoints
        self.test_endpoint_permissions("/reports/sales-summary", "GET", {
            "admin": True, "manager": True, "server": True
        })
        
        self.test_endpoint_permissions("/reports/purchases-summary", "GET", {
            "admin": True, "manager": True, "server": False
        })
        
        self.test_endpoint_permissions("/reports/dashboard", "GET", {
            "admin": True, "manager": True, "server": True
        })
    
    def test_endpoint_permissions(self, endpoint: str, method: str, expected_access: dict, data: dict = None):
        """Test endpoint permissions for different roles"""
        tokens = {
            "admin": self.admin_token,
            "manager": self.manager_token,
            "server": self.server_token
        }
        
        for role, should_have_access in expected_access.items():
            token = tokens.get(role)
            if not token:
                continue
                
            try:
                response = self.make_request(method, endpoint, token=token, data=data)
                
                if should_have_access:
                    # Should have access (200, 201, etc.)
                    if response.status_code < 400:
                        self.log_test(f"{method} {endpoint} - {role.title()} Access", True, f"Status: {response.status_code}")
                    else:
                        self.log_test(f"{method} {endpoint} - {role.title()} Access", False, f"Status: {response.status_code}")
                else:
                    # Should be denied (403)
                    if response.status_code == 403:
                        self.log_test(f"{method} {endpoint} - {role.title()} Access (Should Fail)", True, "Correctly denied access")
                    else:
                        self.log_test(f"{method} {endpoint} - {role.title()} Access (Should Fail)", False, f"Status: {response.status_code}")
                        
            except Exception as e:
                self.log_test(f"{method} {endpoint} - {role.title()} Access", False, f"Exception: {str(e)}")
    
    def test_authentication_integration(self):
        """Test that all role endpoints require valid JWT authentication"""
        endpoints_to_test = [
            "/users",
            "/roles", 
            "/products",
            "/categories",
            "/sales/pending",
            "/suppliers",
            "/purchases",
            "/reports/dashboard"
        ]
        
        for endpoint in endpoints_to_test:
            try:
                # Test without token
                response = self.make_request("GET", endpoint)
                
                if response.status_code in [401, 403]:
                    self.log_test(f"Authentication Required - {endpoint}", True, "Correctly requires authentication")
                else:
                    self.log_test(f"Authentication Required - {endpoint}", False, f"Status: {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Authentication Required - {endpoint}", False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        """Run all role management tests"""
        print("=" * 80)
        print("PHASE 8: ROLE MANAGEMENT SYSTEM - COMPREHENSIVE BACKEND TESTING")
        print("=" * 80)
        
        # Step 1: Authentication
        print("\n1. AUTHENTICATION TESTS")
        print("-" * 40)
        if not self.authenticate_admin():
            print("❌ CRITICAL: Admin authentication failed. Cannot proceed with tests.")
            return False
        
        # Step 2: Create and authenticate test users
        print("\n2. TEST USER SETUP")
        print("-" * 40)
        self.create_test_users()
        self.authenticate_test_users()
        
        # Step 3: Role Information API
        print("\n3. ROLE INFORMATION API TESTS")
        print("-" * 40)
        self.test_role_information_api()
        
        # Step 4: User Management API
        print("\n4. USER MANAGEMENT API TESTS")
        print("-" * 40)
        self.test_user_management_api()
        
        # Step 5: Role Update API
        print("\n5. ROLE UPDATE API TESTS")
        print("-" * 40)
        self.test_role_update_api()
        
        # Step 6: Self-Protection Logic
        print("\n6. SELF-PROTECTION LOGIC TESTS")
        print("-" * 40)
        self.test_self_protection_logic()
        
        # Step 7: User Deactivation
        print("\n7. USER DEACTIVATION TESTS")
        print("-" * 40)
        self.test_user_deactivation()
        
        # Step 8: Cross-Endpoint Permissions
        print("\n8. CROSS-ENDPOINT PERMISSION TESTS")
        print("-" * 40)
        self.test_cross_endpoint_permissions()
        
        # Step 9: Authentication Integration
        print("\n9. AUTHENTICATION INTEGRATION TESTS")
        print("-" * 40)
        self.test_authentication_integration()
        
        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\nFAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"❌ {result['test']}: {result['details']}")
        
        return failed_tests == 0

if __name__ == "__main__":
    tester = BackendTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 ALL TESTS PASSED! Role Management System is fully functional.")
    else:
        print("\n⚠️  Some tests failed. Please review the issues above.")