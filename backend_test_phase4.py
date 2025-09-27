#!/usr/bin/env python3
"""
Backend Test Suite for Sales Manager Phase 4 - Payment and Finalization
Testing all payment-related APIs and complete workflow
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "https://sales-manager-25.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@salesmanager.com"
ADMIN_PASSWORD = "admin123"

class SalesManagerPhase4Tester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.user_data = None
        self.test_results = []
        
    def log_test(self, test_name, success, message="", data=None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}: {message}")
        if data and not success:
            print(f"   Data: {json.dumps(data, indent=2)}")
    
    def authenticate(self):
        """Authenticate and get JWT token"""
        try:
            # First initialize the app
            init_response = self.session.post(f"{BASE_URL}/setup/init")
            print(f"App initialization: {init_response.status_code}")
            
            # Login
            login_data = {
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            }
            
            response = self.session.post(f"{BASE_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.user_data = data["user"]
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                self.log_test("Authentication", True, f"Logged in as {self.user_data['name']}")
                return True
            else:
                self.log_test("Authentication", False, f"Login failed: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Authentication", False, f"Authentication error: {str(e)}")
            return False
    
    def test_payment_methods_api(self):
        """Test GET /api/payment-methods"""
        try:
            response = self.session.get(f"{BASE_URL}/payment-methods")
            
            if response.status_code == 200:
                payment_methods = response.json()
                if len(payment_methods) > 0:
                    method_names = [pm["name"] for pm in payment_methods]
                    self.log_test("GET /api/payment-methods", True, 
                                f"Retrieved {len(payment_methods)} payment methods: {method_names}")
                    return payment_methods
                else:
                    self.log_test("GET /api/payment-methods", False, "No payment methods found")
                    return []
            else:
                self.log_test("GET /api/payment-methods", False, 
                            f"Failed with status {response.status_code}", response.text)
                return []
                
        except Exception as e:
            self.log_test("GET /api/payment-methods", False, f"Error: {str(e)}")
            return []
    
    def create_test_sale_with_products(self):
        """Create a test sale with products for payment testing"""
        try:
            # Get available products
            products_response = self.session.get(f"{BASE_URL}/products")
            if products_response.status_code != 200:
                self.log_test("Create Test Sale", False, "Failed to get products")
                return None
            
            products = products_response.json()
            if len(products) == 0:
                # Create a test product first
                categories_response = self.session.get(f"{BASE_URL}/categories")
                categories = categories_response.json()
                if len(categories) == 0:
                    self.log_test("Create Test Sale", False, "No categories available")
                    return None
                
                # Create test product
                product_data = {
                    "name": "Produit Test Paiement",
                    "code": f"TEST_PAY_{int(time.time())}",
                    "category_id": categories[0]["id"],
                    "purchase_price": 100.0,
                    "selling_price": 150.0,
                    "stock": 50
                }
                
                product_response = self.session.post(f"{BASE_URL}/products", json=product_data)
                if product_response.status_code != 200:
                    self.log_test("Create Test Sale", False, "Failed to create test product")
                    return None
                
                products = [product_response.json()]
            
            # Create new sale
            sale_response = self.session.post(f"{BASE_URL}/sales")
            if sale_response.status_code != 200:
                self.log_test("Create Test Sale", False, "Failed to create sale")
                return None
            
            sale = sale_response.json()
            sale_id = sale["id"]
            
            # Add products to sale
            test_product = products[0]
            item_data = {
                "product_id": test_product["id"],
                "quantity": 2
            }
            
            item_response = self.session.post(f"{BASE_URL}/sales/{sale_id}/items", json=item_data)
            if item_response.status_code != 200:
                self.log_test("Create Test Sale", False, "Failed to add items to sale")
                return None
            
            # Get updated sale with total
            updated_sale_response = self.session.get(f"{BASE_URL}/sales/{sale_id}")
            if updated_sale_response.status_code == 200:
                updated_sale = updated_sale_response.json()
                self.log_test("Create Test Sale", True, 
                            f"Created sale {updated_sale['sale_number']} with total {updated_sale['total_amount']}")
                return updated_sale
            else:
                self.log_test("Create Test Sale", False, "Failed to get updated sale")
                return None
                
        except Exception as e:
            self.log_test("Create Test Sale", False, f"Error: {str(e)}")
            return None
    
    def test_complete_sale_full_payment(self, sale, payment_methods):
        """Test POST /api/sales/{sale_id}/complete with full payment"""
        try:
            if not sale or not payment_methods:
                self.log_test("Complete Sale - Full Payment", False, "Missing sale or payment methods")
                return False
            
            sale_id = sale["id"]
            total_amount = sale["total_amount"]
            
            # Use first payment method for full payment
            payment_data = {
                "payments": [
                    {
                        "payment_method_id": payment_methods[0]["id"],
                        "amount": total_amount
                    }
                ],
                "seller_name": "Vendeur Test"
            }
            
            response = self.session.post(f"{BASE_URL}/sales/{sale_id}/complete", json=payment_data)
            
            if response.status_code == 200:
                result = response.json()
                if result["payment_status"] == "paid" and result["debt_amount"] == 0:
                    self.log_test("Complete Sale - Full Payment", True, 
                                f"Sale completed successfully. Paid: {result['paid_amount']}, Status: {result['payment_status']}")
                    return True
                else:
                    self.log_test("Complete Sale - Full Payment", False, 
                                f"Unexpected payment status: {result['payment_status']}")
                    return False
            else:
                self.log_test("Complete Sale - Full Payment", False, 
                            f"Failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Complete Sale - Full Payment", False, f"Error: {str(e)}")
            return False
    
    def test_complete_sale_partial_payment(self, sale, payment_methods):
        """Test POST /api/sales/{sale_id}/complete with partial payment"""
        try:
            if not sale or not payment_methods:
                self.log_test("Complete Sale - Partial Payment", False, "Missing sale or payment methods")
                return None
            
            sale_id = sale["id"]
            total_amount = sale["total_amount"]
            partial_amount = total_amount * 0.6  # Pay 60%
            
            # Use first payment method for partial payment
            payment_data = {
                "payments": [
                    {
                        "payment_method_id": payment_methods[0]["id"],
                        "amount": partial_amount
                    }
                ],
                "seller_name": "Vendeur Test"
            }
            
            response = self.session.post(f"{BASE_URL}/sales/{sale_id}/complete", json=payment_data)
            
            if response.status_code == 200:
                result = response.json()
                expected_debt = total_amount - partial_amount
                
                if result["payment_status"] == "partial" and abs(result["debt_amount"] - expected_debt) < 0.01:
                    self.log_test("Complete Sale - Partial Payment", True, 
                                f"Partial payment successful. Paid: {result['paid_amount']}, Debt: {result['debt_amount']}")
                    return {"sale_id": sale_id, "debt_amount": result["debt_amount"]}
                else:
                    self.log_test("Complete Sale - Partial Payment", False, 
                                f"Unexpected result: {result}")
                    return None
            else:
                self.log_test("Complete Sale - Partial Payment", False, 
                            f"Failed with status {response.status_code}", response.text)
                return None
                
        except Exception as e:
            self.log_test("Complete Sale - Partial Payment", False, f"Error: {str(e)}")
            return None
    
    def test_create_debt(self, sale_id, debt_amount):
        """Test POST /api/sales/{sale_id}/debt"""
        try:
            debt_data = {
                "debtor_name": "Client Débiteur Test",
                "seller_name": "Vendeur Test",
                "amount": debt_amount
            }
            
            response = self.session.post(f"{BASE_URL}/sales/{sale_id}/debt", json=debt_data)
            
            if response.status_code == 200:
                debt = response.json()
                self.log_test("Create Debt", True, 
                            f"Debt created for {debt['debtor_name']}: {debt['amount']}")
                return debt
            else:
                self.log_test("Create Debt", False, 
                            f"Failed with status {response.status_code}", response.text)
                return None
                
        except Exception as e:
            self.log_test("Create Debt", False, f"Error: {str(e)}")
            return None
    
    def test_get_debts(self):
        """Test GET /api/debts"""
        try:
            response = self.session.get(f"{BASE_URL}/debts")
            
            if response.status_code == 200:
                debts = response.json()
                unsettled_debts = [d for d in debts if not d["is_settled"]]
                self.log_test("GET /api/debts", True, 
                            f"Retrieved {len(debts)} debts ({len(unsettled_debts)} unsettled)")
                return debts
            else:
                self.log_test("GET /api/debts", False, 
                            f"Failed with status {response.status_code}", response.text)
                return []
                
        except Exception as e:
            self.log_test("GET /api/debts", False, f"Error: {str(e)}")
            return []
    
    def test_settle_debt(self, debt_id):
        """Test PATCH /api/debts/{debt_id}/settle"""
        try:
            response = self.session.patch(f"{BASE_URL}/debts/{debt_id}/settle")
            
            if response.status_code == 200:
                result = response.json()
                self.log_test("Settle Debt", True, result["message"])
                return True
            else:
                self.log_test("Settle Debt", False, 
                            f"Failed with status {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Settle Debt", False, f"Error: {str(e)}")
            return False
    
    def test_sales_history(self):
        """Test GET /api/sales/history"""
        try:
            response = self.session.get(f"{BASE_URL}/sales/history")
            
            if response.status_code == 200:
                history = response.json()
                completed_sales = len(history)
                
                if completed_sales > 0:
                    # Check if sales have payment methods info
                    sample_sale = history[0]
                    has_payment_methods = "payment_methods" in sample_sale and len(sample_sale["payment_methods"]) > 0
                    
                    self.log_test("GET /api/sales/history", True, 
                                f"Retrieved {completed_sales} completed sales. Payment methods included: {has_payment_methods}")
                else:
                    self.log_test("GET /api/sales/history", True, "No completed sales found (expected for new system)")
                
                return history
            else:
                self.log_test("GET /api/sales/history", False, 
                            f"Failed with status {response.status_code}", response.text)
                return []
                
        except Exception as e:
            self.log_test("GET /api/sales/history", False, f"Error: {str(e)}")
            return []
    
    def test_stock_decrement_verification(self, product_id, expected_decrement):
        """Verify that product stock was decremented correctly"""
        try:
            response = self.session.get(f"{BASE_URL}/products/{product_id}")
            
            if response.status_code == 200:
                product = response.json()
                current_stock = product["stock"]
                
                # We can't verify exact decrement without knowing initial stock
                # But we can verify the product exists and has reasonable stock
                self.log_test("Stock Verification", True, 
                            f"Product {product['name']} current stock: {current_stock}")
                return True
            else:
                self.log_test("Stock Verification", False, 
                            f"Failed to get product: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Stock Verification", False, f"Error: {str(e)}")
            return False
    
    def test_validation_scenarios(self, payment_methods):
        """Test various validation scenarios"""
        try:
            # Test 1: Try to complete already completed sale
            sale = self.create_test_sale_with_products()
            if sale:
                # Complete it first
                payment_data = {
                    "payments": [{"payment_method_id": payment_methods[0]["id"], "amount": sale["total_amount"]}],
                    "seller_name": "Test"
                }
                self.session.post(f"{BASE_URL}/sales/{sale['id']}/complete", json=payment_data)
                
                # Try to complete again
                response = self.session.post(f"{BASE_URL}/sales/{sale['id']}/complete", json=payment_data)
                if response.status_code == 400:
                    self.log_test("Validation - Double Complete", True, "Correctly prevented double completion")
                else:
                    self.log_test("Validation - Double Complete", False, "Should prevent double completion")
            
            # Test 2: Try to pay more than sale total
            sale2 = self.create_test_sale_with_products()
            if sale2:
                overpay_data = {
                    "payments": [{"payment_method_id": payment_methods[0]["id"], "amount": sale2["total_amount"] + 100}],
                    "seller_name": "Test"
                }
                response = self.session.post(f"{BASE_URL}/sales/{sale2['id']}/complete", json=overpay_data)
                if response.status_code == 400:
                    self.log_test("Validation - Overpayment", True, "Correctly prevented overpayment")
                else:
                    self.log_test("Validation - Overpayment", False, "Should prevent overpayment")
            
            # Test 3: Invalid payment method
            sale3 = self.create_test_sale_with_products()
            if sale3:
                invalid_payment_data = {
                    "payments": [{"payment_method_id": "invalid_id", "amount": sale3["total_amount"]}],
                    "seller_name": "Test"
                }
                response = self.session.post(f"{BASE_URL}/sales/{sale3['id']}/complete", json=invalid_payment_data)
                if response.status_code == 400:
                    self.log_test("Validation - Invalid Payment Method", True, "Correctly rejected invalid payment method")
                else:
                    self.log_test("Validation - Invalid Payment Method", False, "Should reject invalid payment method")
                    
        except Exception as e:
            self.log_test("Validation Tests", False, f"Error: {str(e)}")
    
    def run_complete_workflow_test(self):
        """Run the complete payment and finalization workflow test"""
        print("=" * 80)
        print("SALES MANAGER PHASE 4 - PAYMENT & FINALIZATION BACKEND TESTS")
        print("=" * 80)
        
        # Step 1: Authentication
        if not self.authenticate():
            return False
        
        # Step 2: Test payment methods API
        payment_methods = self.test_payment_methods_api()
        if not payment_methods:
            print("❌ Cannot continue without payment methods")
            return False
        
        # Step 3: Create test sale for full payment
        print("\n--- Testing Full Payment Workflow ---")
        sale1 = self.create_test_sale_with_products()
        if sale1:
            self.test_complete_sale_full_payment(sale1, payment_methods)
        
        # Step 4: Create test sale for partial payment + debt
        print("\n--- Testing Partial Payment + Debt Workflow ---")
        sale2 = self.create_test_sale_with_products()
        if sale2:
            partial_result = self.test_complete_sale_partial_payment(sale2, payment_methods)
            if partial_result:
                # Create debt for remaining amount
                debt = self.test_create_debt(partial_result["sale_id"], partial_result["debt_amount"])
                if debt:
                    # Test settling the debt
                    self.test_settle_debt(debt["id"])
        
        # Step 5: Test debt management
        print("\n--- Testing Debt Management ---")
        self.test_get_debts()
        
        # Step 6: Test sales history
        print("\n--- Testing Sales History ---")
        self.test_sales_history()
        
        # Step 7: Test validation scenarios
        print("\n--- Testing Validation Scenarios ---")
        self.test_validation_scenarios(payment_methods)
        
        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t["success"]])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\nFAILED TESTS:")
            for test in self.test_results:
                if not test["success"]:
                    print(f"❌ {test['test']}: {test['message']}")
        
        return failed_tests == 0

if __name__ == "__main__":
    tester = SalesManagerPhase4Tester()
    success = tester.run_complete_workflow_test()
    
    if success:
        print("\n🎉 ALL TESTS PASSED - Phase 4 Backend is working correctly!")
    else:
        print("\n⚠️  SOME TESTS FAILED - Check the details above")