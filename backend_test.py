#!/usr/bin/env python3
"""
Backend Test Suite for Sales Manager Application - Phase 2
Testing Product Management APIs and Security
"""

import requests
import json
import base64
from datetime import datetime
import sys
import time

# Configuration
BASE_URL = "https://sales-manager-25.preview.emergentagent.com/api"

# Test users
ADMIN_USER = {
    "email": "admin@salesmanager.com",
    "password": "admin123"
}

SERVER_USER = {
    "email": "serveur@salesmanager.com", 
    "password": "serveur123",
    "name": "Serveur Test",
    "role": "serveur"
}

class TestRunner:
    def __init__(self):
        self.admin_token = None
        self.server_token = None
        self.test_category_id = None
        self.test_product_id = None
        self.results = []
        
    def log_result(self, test_name, success, message="", details=""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "details": details
        })
        print(f"{status} {test_name}: {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def make_request(self, method, endpoint, token=None, data=None, params=None):
        """Make HTTP request with proper headers"""
        url = f"{BASE_URL}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=10)
            elif method == "PATCH":
                response = requests.patch(url, headers=headers, json=data, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            return response
        except requests.exceptions.RequestException as e:
            print(f"Request error for {method} {url}: {str(e)}")
            return None
        except Exception as e:
            print(f"Unexpected error for {method} {url}: {str(e)}")
            return None
    
    def setup_authentication(self):
        """Setup authentication tokens for admin and server users"""
        print("\n=== SETUP AUTHENTICATION ===")
        
        # Initialize app first
        response = self.make_request("POST", "/setup/init")
        if response and response.status_code == 200:
            self.log_result("App Initialization", True, "App initialized successfully")
        else:
            self.log_result("App Initialization", False, "Failed to initialize app")
            return False
        
        # Login as admin
        response = self.make_request("POST", "/auth/login", data=ADMIN_USER)
        if response and response.status_code == 200:
            data = response.json()
            self.admin_token = data["access_token"]
            self.log_result("Admin Login", True, f"Admin logged in successfully")
        else:
            self.log_result("Admin Login", False, "Failed to login as admin", 
                          f"Status: {response.status_code if response else 'No response'}")
            return False
        
        # Create server user
        response = self.make_request("POST", "/auth/register", self.admin_token, SERVER_USER)
        if response and response.status_code == 200:
            self.log_result("Server User Creation", True, "Server user created successfully")
        else:
            # User might already exist, try to login
            self.log_result("Server User Creation", True, "Server user already exists or created")
        
        # Login as server
        server_login = {"email": SERVER_USER["email"], "password": SERVER_USER["password"]}
        response = self.make_request("POST", "/auth/login", data=server_login)
        if response and response.status_code == 200:
            data = response.json()
            self.server_token = data["access_token"]
            self.log_result("Server Login", True, "Server user logged in successfully")
        else:
            self.log_result("Server Login", False, "Failed to login as server user",
                          f"Status: {response.status_code if response else 'No response'}")
            return False
            
        return True
    
    def test_categories_crud(self):
        """Test Categories CRUD operations"""
        print("\n=== TESTING CATEGORIES CRUD ===")
        
        # Get existing categories
        response = self.make_request("GET", "/categories", self.admin_token)
        if response and response.status_code == 200:
            categories = response.json()
            self.log_result("Get Categories", True, f"Retrieved {len(categories)} categories")
            if categories:
                self.test_category_id = categories[0]["id"]
        else:
            self.log_result("Get Categories", False, "Failed to get categories")
            return False
        
        # Test category creation (admin)
        new_category = {
            "name": "Test Category",
            "description": "Category for testing"
        }
        response = self.make_request("POST", "/categories", self.admin_token, new_category)
        if response and response.status_code == 200:
            created_category = response.json()
            test_category_id = created_category["id"]
            self.log_result("Create Category (Admin)", True, "Category created successfully")
        else:
            self.log_result("Create Category (Admin)", False, "Failed to create category")
            return False
        
        # Test category update (admin)
        updated_category = {
            "name": "Updated Test Category",
            "description": "Updated description"
        }
        response = self.make_request("PUT", f"/categories/{test_category_id}", self.admin_token, updated_category)
        if response and response.status_code == 200:
            self.log_result("Update Category (Admin)", True, "Category updated successfully")
        else:
            self.log_result("Update Category (Admin)", False, "Failed to update category")
        
        # Test category update permission (server - should fail)
        time.sleep(0.5)  # Small delay to avoid race conditions
        response = self.make_request("PUT", f"/categories/{test_category_id}", self.server_token, updated_category)
        if response:
            print(f"DEBUG: Server category update response: {response.status_code}")
            if response.status_code == 403:
                self.log_result("Update Category Permission (Server)", True, "Server correctly denied access")
            else:
                self.log_result("Update Category Permission (Server)", False, f"Expected 403, got {response.status_code}")
        else:
            self.log_result("Update Category Permission (Server)", False, "No response received")
        
        # Test category deletion with products (should fail)
        if self.test_category_id:
            response = self.make_request("DELETE", f"/categories/{self.test_category_id}", self.admin_token)
            if response and response.status_code == 400:
                self.log_result("Delete Category with Products", True, "Correctly prevented deletion of category with products")
            else:
                self.log_result("Delete Category with Products", False, "Should prevent deletion of category with products")
        
        # Test category deletion (empty category - should succeed)
        response = self.make_request("DELETE", f"/categories/{test_category_id}", self.admin_token)
        if response and response.status_code == 200:
            self.log_result("Delete Empty Category (Admin)", True, "Empty category deleted successfully")
        else:
            self.log_result("Delete Empty Category (Admin)", False, "Failed to delete empty category")
        
        # Test category deletion permission (server - should fail)
        response = self.make_request("DELETE", f"/categories/{test_category_id}", self.server_token)
        if response and response.status_code == 403:
            self.log_result("Delete Category Permission (Server)", True, "Server correctly denied delete access")
        else:
            self.log_result("Delete Category Permission (Server)", False, "Server should not have delete access")
        
        return True
    
    def test_products_crud(self):
        """Test Products CRUD operations"""
        print("\n=== TESTING PRODUCTS CRUD ===")
        
        if not self.test_category_id:
            self.log_result("Products Test Setup", False, "No category available for product testing")
            return False
        
        # Test get all products
        response = self.make_request("GET", "/products", self.admin_token)
        if response and response.status_code == 200:
            products = response.json()
            self.log_result("Get All Products", True, f"Retrieved {len(products)} products")
        else:
            self.log_result("Get All Products", False, "Failed to get products")
        
        # Test get products by category
        response = self.make_request("GET", "/products", self.admin_token, params={"category_id": self.test_category_id})
        if response and response.status_code == 200:
            filtered_products = response.json()
            self.log_result("Get Products by Category", True, f"Retrieved {len(filtered_products)} products for category")
        else:
            self.log_result("Get Products by Category", False, "Failed to get products by category")
        
        # Test product creation with base64 image (admin)
        sample_image_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        new_product = {
            "name": "Produit Test",
            "code": "TEST001",
            "category_id": self.test_category_id,
            "purchase_price": 100.0,
            "selling_price": 150.0,
            "stock": 50,
            "image": sample_image_b64
        }
        response = self.make_request("POST", "/products", self.admin_token, new_product)
        if response and response.status_code == 200:
            created_product = response.json()
            self.test_product_id = created_product["id"]
            self.log_result("Create Product with Image (Admin)", True, "Product with base64 image created successfully")
        else:
            self.log_result("Create Product with Image (Admin)", False, "Failed to create product with image",
                          f"Status: {response.status_code if response else 'No response'}")
            return False
        
        # Test product creation permission (server - should fail)
        duplicate_product = new_product.copy()
        duplicate_product["code"] = "TEST002"
        response = self.make_request("POST", "/products", self.server_token, duplicate_product)
        if response and response.status_code == 403:
            self.log_result("Create Product Permission (Server)", True, "Server correctly denied create access")
        else:
            self.log_result("Create Product Permission (Server)", False, "Server should not have create access")
        
        # Test duplicate product code (should fail)
        duplicate_code_product = new_product.copy()
        duplicate_code_product["name"] = "Autre Produit"
        response = self.make_request("POST", "/products", self.admin_token, duplicate_code_product)
        if response and response.status_code == 400:
            self.log_result("Duplicate Product Code", True, "Correctly prevented duplicate product code")
        else:
            self.log_result("Duplicate Product Code", False, "Should prevent duplicate product codes")
        
        # Test get specific product
        response = self.make_request("GET", f"/products/{self.test_product_id}", self.admin_token)
        if response and response.status_code == 200:
            product = response.json()
            self.log_result("Get Specific Product", True, f"Retrieved product: {product['name']}")
        else:
            self.log_result("Get Specific Product", False, "Failed to get specific product")
        
        # Test product update (admin)
        updated_product = {
            "name": "Produit Test Modifié",
            "code": "TEST001",
            "category_id": self.test_category_id,
            "purchase_price": 110.0,
            "selling_price": 160.0,
            "stock": 45,
            "image": sample_image_b64
        }
        response = self.make_request("PUT", f"/products/{self.test_product_id}", self.admin_token, updated_product)
        if response and response.status_code == 200:
            self.log_result("Update Product (Admin)", True, "Product updated successfully")
        else:
            self.log_result("Update Product (Admin)", False, "Failed to update product")
        
        # Test product update permission (server - should fail)
        response = self.make_request("PUT", f"/products/{self.test_product_id}", self.server_token, updated_product)
        if response and response.status_code == 403:
            self.log_result("Update Product Permission (Server)", True, "Server correctly denied update access")
        else:
            self.log_result("Update Product Permission (Server)", False, "Server should not have update access")
        
        # Test stock update (admin)
        stock_update = {"stock": 75}
        response = self.make_request("PATCH", f"/products/{self.test_product_id}/stock", self.admin_token, stock_update)
        if response and response.status_code == 200:
            updated_product = response.json()
            if updated_product["stock"] == 75:
                self.log_result("Update Product Stock (Admin)", True, "Product stock updated successfully")
            else:
                self.log_result("Update Product Stock (Admin)", False, "Stock not updated correctly")
        else:
            self.log_result("Update Product Stock (Admin)", False, "Failed to update product stock")
        
        # Test stock update permission (server - should fail)
        response = self.make_request("PATCH", f"/products/{self.test_product_id}/stock", self.server_token, stock_update)
        if response and response.status_code == 403:
            self.log_result("Update Stock Permission (Server)", True, "Server correctly denied stock update access")
        else:
            self.log_result("Update Stock Permission (Server)", False, "Server should not have stock update access")
        
        # Test invalid stock update (negative value)
        invalid_stock = {"stock": -10}
        response = self.make_request("PATCH", f"/products/{self.test_product_id}/stock", self.admin_token, invalid_stock)
        if response and response.status_code == 400:
            self.log_result("Invalid Stock Update", True, "Correctly rejected negative stock value")
        else:
            self.log_result("Invalid Stock Update", False, "Should reject negative stock values")
        
        # Test product deletion permission (server - should fail)
        response = self.make_request("DELETE", f"/products/{self.test_product_id}", self.server_token)
        if response and response.status_code == 403:
            self.log_result("Delete Product Permission (Server)", True, "Server correctly denied delete access")
        else:
            self.log_result("Delete Product Permission (Server)", False, "Server should not have delete access")
        
        # Test product deletion (admin)
        response = self.make_request("DELETE", f"/products/{self.test_product_id}", self.admin_token)
        if response and response.status_code == 200:
            self.log_result("Delete Product (Admin)", True, "Product deleted successfully")
        else:
            self.log_result("Delete Product (Admin)", False, "Failed to delete product")
        
        return True
    
    def test_server_read_only_access(self):
        """Test that server users can only read data"""
        print("\n=== TESTING SERVER READ-ONLY ACCESS ===")
        
        # Test server can read categories
        response = self.make_request("GET", "/categories", self.server_token)
        if response and response.status_code == 200:
            self.log_result("Server Read Categories", True, "Server can read categories")
        else:
            self.log_result("Server Read Categories", False, "Server should be able to read categories")
        
        # Test server can read products
        response = self.make_request("GET", "/products", self.server_token)
        if response and response.status_code == 200:
            self.log_result("Server Read Products", True, "Server can read products")
        else:
            self.log_result("Server Read Products", False, "Server should be able to read products")
        
        # Test server can read specific product
        if self.test_product_id:
            response = self.make_request("GET", f"/products/{self.test_product_id}", self.server_token)
            if response and response.status_code == 200:
                self.log_result("Server Read Specific Product", True, "Server can read specific product")
            else:
                self.log_result("Server Read Specific Product", False, "Server should be able to read specific product")
    
    def test_edge_cases(self):
        """Test edge cases and error handling"""
        print("\n=== TESTING EDGE CASES ===")
        
        # Test invalid product ID
        response = self.make_request("GET", "/products/invalid_id", self.admin_token)
        if response and response.status_code == 400:
            self.log_result("Invalid Product ID", True, "Correctly handled invalid product ID")
        else:
            self.log_result("Invalid Product ID", False, "Should handle invalid product ID gracefully")
        
        # Test non-existent product ID
        fake_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format but non-existent
        response = self.make_request("GET", f"/products/{fake_id}", self.admin_token)
        if response and response.status_code == 404:
            self.log_result("Non-existent Product", True, "Correctly handled non-existent product")
        else:
            self.log_result("Non-existent Product", False, "Should return 404 for non-existent product")
        
        # Test invalid category ID in product creation
        invalid_product = {
            "name": "Test Product",
            "code": "INVALID001",
            "category_id": "invalid_category_id",
            "purchase_price": 100.0,
            "selling_price": 150.0,
            "stock": 10
        }
        response = self.make_request("POST", "/products", self.admin_token, invalid_product)
        if response and response.status_code == 400:
            self.log_result("Invalid Category ID in Product", True, "Correctly rejected invalid category ID")
        else:
            self.log_result("Invalid Category ID in Product", False, "Should reject invalid category ID")
    
    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting Backend Tests for Sales Manager - Phase 2")
        print("=" * 60)
        
        # Setup
        if not self.setup_authentication():
            print("❌ Authentication setup failed. Aborting tests.")
            return False
        
        # Run test suites
        self.test_categories_crud()
        self.test_products_crud()
        self.test_server_read_only_access()
        self.test_edge_cases()
        
        # Summary
        self.print_summary()
        return True
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.results if r["success"])
        failed = sum(1 for r in self.results if not r["success"])
        total = len(self.results)
        
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        if failed > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.results:
                if not result["success"]:
                    print(f"  ❌ {result['test']}: {result['message']}")
                    if result["details"]:
                        print(f"     Details: {result['details']}")
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    tester = TestRunner()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)