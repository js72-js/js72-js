#!/usr/bin/env python3
"""
Backend Test Suite for Sales Manager Phase 3 - Sales and Cart System
Testing all sales and cart management endpoints
"""

import requests
import json
import time
import sys
from typing import Dict, Any, List

# Configuration
BASE_URL = "https://sales-manager-25.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@salesmanager.com"
ADMIN_PASSWORD = "admin123"

class SalesBackendTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.token = None
        self.headers = {}
        self.test_results = []
        self.created_sale_id = None
        self.created_items = []
        self.available_products = []
        
    def log_test(self, test_name: str, success: bool, message: str, details: Any = None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def authenticate(self) -> bool:
        """Authenticate and get JWT token"""
        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.headers = {"Authorization": f"Bearer {self.token}"}
                self.log_test("Authentication", True, f"Successfully authenticated as {ADMIN_EMAIL}")
                return True
            else:
                self.log_test("Authentication", False, f"Failed to authenticate: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Authentication", False, f"Authentication error: {str(e)}")
            return False
    
    def get_available_products(self) -> bool:
        """Get available products for testing cart functionality"""
        try:
            response = requests.get(
                f"{self.base_url}/products",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                products = response.json()
                # Filter products with stock > 0
                self.available_products = [p for p in products if p.get("stock", 0) > 0]
                
                if len(self.available_products) >= 2:
                    self.log_test("Get Products", True, f"Found {len(self.available_products)} products with stock")
                    return True
                else:
                    self.log_test("Get Products", False, f"Need at least 2 products with stock, found {len(self.available_products)}")
                    return False
            else:
                self.log_test("Get Products", False, f"Failed to get products: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Get Products", False, f"Error getting products: {str(e)}")
            return False
    
    def test_generate_sale_number(self) -> bool:
        """Test POST /api/sales/generate-number"""
        try:
            response = requests.post(
                f"{self.base_url}/sales/generate-number",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                sale_number = data.get("sale_number")
                
                if sale_number and sale_number.startswith("VTE") and len(sale_number) == 11:
                    self.log_test("Generate Sale Number", True, f"Generated unique sale number: {sale_number}")
                    return True
                else:
                    self.log_test("Generate Sale Number", False, f"Invalid sale number format: {sale_number}")
                    return False
            else:
                self.log_test("Generate Sale Number", False, f"Failed: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Generate Sale Number", False, f"Error: {str(e)}")
            return False
    
    def test_create_sale(self) -> bool:
        """Test POST /api/sales"""
        try:
            response = requests.post(
                f"{self.base_url}/sales",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.created_sale_id = data.get("id")
                sale_number = data.get("sale_number")
                status = data.get("status")
                total_amount = data.get("total_amount")
                
                if (self.created_sale_id and sale_number and sale_number.startswith("VTE") 
                    and status == "pending" and total_amount == 0.0):
                    self.log_test("Create Sale", True, f"Created sale {sale_number} with ID {self.created_sale_id}")
                    return True
                else:
                    self.log_test("Create Sale", False, "Invalid sale data structure", data)
                    return False
            else:
                self.log_test("Create Sale", False, f"Failed: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Create Sale", False, f"Error: {str(e)}")
            return False
    
    def test_get_sale(self) -> bool:
        """Test GET /api/sales/{sale_id}"""
        if not self.created_sale_id:
            self.log_test("Get Sale", False, "No sale ID available for testing")
            return False
            
        try:
            response = requests.get(
                f"{self.base_url}/sales/{self.created_sale_id}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("id") == self.created_sale_id:
                    self.log_test("Get Sale", True, f"Successfully retrieved sale {self.created_sale_id}")
                    return True
                else:
                    self.log_test("Get Sale", False, "Sale ID mismatch", data)
                    return False
            else:
                self.log_test("Get Sale", False, f"Failed: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Get Sale", False, f"Error: {str(e)}")
            return False
    
    def test_add_items_to_cart(self) -> bool:
        """Test POST /api/sales/{sale_id}/items"""
        if not self.created_sale_id or len(self.available_products) < 2:
            self.log_test("Add Items to Cart", False, "Prerequisites not met")
            return False
        
        success_count = 0
        
        # Add first product
        try:
            product1 = self.available_products[0]
            response = requests.post(
                f"{self.base_url}/sales/{self.created_sale_id}/items",
                headers=self.headers,
                json={
                    "product_id": product1["id"],
                    "quantity": 2
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.created_items.append(data)
                self.log_test("Add Item 1 to Cart", True, f"Added {product1['name']} x2 to cart")
                success_count += 1
            else:
                self.log_test("Add Item 1 to Cart", False, f"Failed: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Add Item 1 to Cart", False, f"Error: {str(e)}")
        
        # Add second product
        try:
            product2 = self.available_products[1]
            response = requests.post(
                f"{self.base_url}/sales/{self.created_sale_id}/items",
                headers=self.headers,
                json={
                    "product_id": product2["id"],
                    "quantity": 1
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.created_items.append(data)
                self.log_test("Add Item 2 to Cart", True, f"Added {product2['name']} x1 to cart")
                success_count += 1
            else:
                self.log_test("Add Item 2 to Cart", False, f"Failed: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Add Item 2 to Cart", False, f"Error: {str(e)}")
        
        return success_count == 2
    
    def test_get_cart_items(self) -> bool:
        """Test GET /api/sales/{sale_id}/items"""
        if not self.created_sale_id:
            self.log_test("Get Cart Items", False, "No sale ID available")
            return False
            
        try:
            response = requests.get(
                f"{self.base_url}/sales/{self.created_sale_id}/items",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                items = response.json()
                if len(items) >= 2:
                    # Check if items have product details (JOIN functionality)
                    first_item = items[0]
                    required_fields = ["id", "product_name", "product_code", "quantity", "unit_price", "total_price", "available_stock"]
                    
                    if all(field in first_item for field in required_fields):
                        self.log_test("Get Cart Items", True, f"Retrieved {len(items)} items with product details")
                        return True
                    else:
                        self.log_test("Get Cart Items", False, "Missing product details in items", first_item)
                        return False
                else:
                    self.log_test("Get Cart Items", False, f"Expected at least 2 items, got {len(items)}")
                    return False
            else:
                self.log_test("Get Cart Items", False, f"Failed: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Get Cart Items", False, f"Error: {str(e)}")
            return False
    
    def test_update_item_quantity(self) -> bool:
        """Test PUT /api/sales/{sale_id}/items/{item_id}"""
        if not self.created_items:
            self.log_test("Update Item Quantity", False, "No items available for testing")
            return False
            
        try:
            item = self.created_items[0]
            item_id = item.get("id")
            
            response = requests.put(
                f"{self.base_url}/sales/{self.created_sale_id}/items/{item_id}",
                headers=self.headers,
                json={"quantity": 3},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("quantity") == 3:
                    self.log_test("Update Item Quantity", True, f"Updated item quantity to 3")
                    return True
                else:
                    self.log_test("Update Item Quantity", False, "Quantity not updated correctly", data)
                    return False
            else:
                self.log_test("Update Item Quantity", False, f"Failed: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Update Item Quantity", False, f"Error: {str(e)}")
            return False
    
    def test_stock_verification(self) -> bool:
        """Test stock verification when adding items"""
        if not self.created_sale_id or not self.available_products:
            self.log_test("Stock Verification", False, "Prerequisites not met")
            return False
            
        try:
            product = self.available_products[0]
            excessive_quantity = product["stock"] + 10  # More than available stock
            
            response = requests.post(
                f"{self.base_url}/sales/{self.created_sale_id}/items",
                headers=self.headers,
                json={
                    "product_id": product["id"],
                    "quantity": excessive_quantity
                },
                timeout=10
            )
            
            if response.status_code == 400:
                error_message = response.json().get("detail", "")
                if "Insufficient stock" in error_message:
                    self.log_test("Stock Verification", True, "Correctly prevented adding more than available stock")
                    return True
                else:
                    self.log_test("Stock Verification", False, f"Wrong error message: {error_message}")
                    return False
            else:
                self.log_test("Stock Verification", False, f"Should have returned 400, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Stock Verification", False, f"Error: {str(e)}")
            return False
    
    def test_sale_total_calculation(self) -> bool:
        """Test automatic sale total calculation"""
        if not self.created_sale_id:
            self.log_test("Sale Total Calculation", False, "No sale ID available")
            return False
            
        try:
            # Get current sale to check total
            response = requests.get(
                f"{self.base_url}/sales/{self.created_sale_id}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                sale_data = response.json()
                total_amount = sale_data.get("total_amount", 0)
                
                if total_amount > 0:
                    self.log_test("Sale Total Calculation", True, f"Sale total automatically calculated: {total_amount}")
                    return True
                else:
                    self.log_test("Sale Total Calculation", False, f"Sale total is {total_amount}, expected > 0")
                    return False
            else:
                self.log_test("Sale Total Calculation", False, f"Failed to get sale: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Sale Total Calculation", False, f"Error: {str(e)}")
            return False
    
    def test_update_sale_status(self) -> bool:
        """Test PATCH /api/sales/{sale_id}/status"""
        if not self.created_sale_id:
            self.log_test("Update Sale Status", False, "No sale ID available")
            return False
            
        try:
            # Change status to on_hold
            response = requests.patch(
                f"{self.base_url}/sales/{self.created_sale_id}/status",
                headers=self.headers,
                json={"status": "on_hold"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "on_hold":
                    self.log_test("Update Sale Status", True, "Successfully changed status to on_hold")
                    return True
                else:
                    self.log_test("Update Sale Status", False, f"Status not updated correctly: {data.get('status')}")
                    return False
            else:
                self.log_test("Update Sale Status", False, f"Failed: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Update Sale Status", False, f"Error: {str(e)}")
            return False
    
    def test_get_pending_sales(self) -> bool:
        """Test GET /api/sales/pending"""
        try:
            response = requests.get(
                f"{self.base_url}/sales/pending",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                sales = response.json()
                # Should include our on_hold sale
                our_sale = next((s for s in sales if s.get("id") == self.created_sale_id), None)
                
                if our_sale and our_sale.get("status") == "on_hold":
                    self.log_test("Get Pending Sales", True, f"Found {len(sales)} pending/on_hold sales including our test sale")
                    return True
                else:
                    self.log_test("Get Pending Sales", False, "Our test sale not found in pending sales")
                    return False
            else:
                self.log_test("Get Pending Sales", False, f"Failed: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Get Pending Sales", False, f"Error: {str(e)}")
            return False
    
    def test_remove_item_from_cart(self) -> bool:
        """Test DELETE /api/sales/{sale_id}/items/{item_id}"""
        if not self.created_items:
            self.log_test("Remove Item from Cart", False, "No items available for testing")
            return False
            
        try:
            item = self.created_items[-1]  # Remove last item
            item_id = item.get("id")
            
            response = requests.delete(
                f"{self.base_url}/sales/{self.created_sale_id}/items/{item_id}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.log_test("Remove Item from Cart", True, "Successfully removed item from cart")
                return True
            else:
                self.log_test("Remove Item from Cart", False, f"Failed: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Remove Item from Cart", False, f"Error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("=" * 80)
        print("SALES MANAGER PHASE 3 - BACKEND TESTING")
        print("Testing Sales and Cart Management System")
        print("=" * 80)
        
        # Prerequisites
        if not self.authenticate():
            print("❌ CRITICAL: Authentication failed - cannot proceed with tests")
            return False
            
        if not self.get_available_products():
            print("❌ CRITICAL: No products available - cannot test cart functionality")
            return False
        
        # Core Sales API Tests
        print("\n📋 TESTING SALES API...")
        self.test_generate_sale_number()
        self.test_create_sale()
        self.test_get_sale()
        self.test_update_sale_status()
        self.test_get_pending_sales()
        
        # Cart Management Tests
        print("\n🛒 TESTING CART MANAGEMENT...")
        self.test_add_items_to_cart()
        self.test_get_cart_items()
        self.test_update_item_quantity()
        self.test_remove_item_from_cart()
        
        # Critical Functionality Tests
        print("\n🔍 TESTING CRITICAL FUNCTIONALITIES...")
        self.test_stock_verification()
        self.test_sale_total_calculation()
        
        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if total - passed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        return passed == total

if __name__ == "__main__":
    tester = SalesBackendTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 ALL TESTS PASSED - Phase 3 Backend is fully functional!")
    else:
        print("\n⚠️  Some tests failed - Phase 3 Backend needs attention")
    
    sys.exit(0 if success else 1)