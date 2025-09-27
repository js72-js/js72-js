#!/usr/bin/env python3
"""
Backend Test Suite for Sales Manager Application - Phase 5: Purchase Management
Testing all purchase-related endpoints and functionality
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any

# Configuration
BASE_URL = "https://sales-manager-25.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@salesmanager.com"
ADMIN_PASSWORD = "admin123"

class SalesManagerTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.admin_token = None
        self.server_token = None
        self.test_results = []
        self.suppliers = []
        self.products = []
        self.categories = []
        self.purchases = []
        
    def log_test(self, test_name: str, success: bool, message: str, details: str = ""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        result = {
            "test": test_name,
            "status": status,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        print(f"{status} - {test_name}: {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def setup_authentication(self):
        """Setup authentication tokens for admin and server users"""
        print("\n=== SETTING UP AUTHENTICATION ===")
        
        # Login as admin
        try:
            response = requests.post(f"{self.base_url}/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            })
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data["access_token"]
                self.log_test("Admin Authentication", True, "Admin login successful")
            else:
                self.log_test("Admin Authentication", False, f"Admin login failed: {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Admin Authentication", False, f"Admin login error: {str(e)}")
            return False
        
        # Create a server user for permission testing
        try:
            response = requests.post(f"{self.base_url}/auth/register", 
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={
                    "email": "serveur@test.com",
                    "password": "server123",
                    "name": "Test Serveur",
                    "role": "serveur"
                })
            
            if response.status_code in [200, 201]:
                self.log_test("Server User Creation", True, "Server user created successfully")
            else:
                # User might already exist, try to login
                pass
                
        except Exception as e:
            pass
        
        # Login as server user
        try:
            response = requests.post(f"{self.base_url}/auth/login", json={
                "email": "serveur@test.com",
                "password": "server123"
            })
            
            if response.status_code == 200:
                data = response.json()
                self.server_token = data["access_token"]
                self.log_test("Server Authentication", True, "Server login successful")
            else:
                self.log_test("Server Authentication", False, f"Server login failed: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Server Authentication", False, f"Server login error: {str(e)}")
        
        return self.admin_token is not None
    
    def setup_test_data(self):
        """Setup test data - categories and products needed for purchases"""
        print("\n=== SETTING UP TEST DATA ===")
        
        # Get existing categories
        try:
            response = requests.get(f"{self.base_url}/categories",
                headers={"Authorization": f"Bearer {self.admin_token}"})
            
            if response.status_code == 200:
                self.categories = response.json()
                self.log_test("Get Categories", True, f"Retrieved {len(self.categories)} categories")
            else:
                self.log_test("Get Categories", False, f"Failed to get categories: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Get Categories", False, f"Error getting categories: {str(e)}")
            return False
        
        # Get existing products
        try:
            response = requests.get(f"{self.base_url}/products",
                headers={"Authorization": f"Bearer {self.admin_token}"})
            
            if response.status_code == 200:
                self.products = response.json()
                self.log_test("Get Products", True, f"Retrieved {len(self.products)} products")
            else:
                self.log_test("Get Products", False, f"Failed to get products: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Get Products", False, f"Error getting products: {str(e)}")
            return False
        
        # Create test products if none exist
        if len(self.products) == 0 and len(self.categories) > 0:
            test_products = [
                {
                    "name": "Produit Test Achat 1",
                    "code": "PTA001",
                    "category_id": self.categories[0]["id"],
                    "purchase_price": 10.0,
                    "selling_price": 15.0,
                    "stock": 5
                },
                {
                    "name": "Produit Test Achat 2", 
                    "code": "PTA002",
                    "category_id": self.categories[0]["id"],
                    "purchase_price": 20.0,
                    "selling_price": 30.0,
                    "stock": 3
                }
            ]
            
            for product_data in test_products:
                try:
                    response = requests.post(f"{self.base_url}/products",
                        headers={"Authorization": f"Bearer {self.admin_token}"},
                        json=product_data)
                    
                    if response.status_code in [200, 201]:
                        product = response.json()
                        self.products.append(product)
                        self.log_test("Create Test Product", True, f"Created product: {product['name']}")
                    else:
                        self.log_test("Create Test Product", False, f"Failed to create product: {response.status_code}")
                        
                except Exception as e:
                    self.log_test("Create Test Product", False, f"Error creating product: {str(e)}")
        
        return len(self.products) > 0
    
    def test_suppliers_crud(self):
        """Test complete CRUD operations for suppliers"""
        print("\n=== TESTING SUPPLIERS CRUD ===")
        
        # Test 1: GET /api/suppliers (empty list initially)
        try:
            response = requests.get(f"{self.base_url}/suppliers",
                headers={"Authorization": f"Bearer {self.admin_token}"})
            
            if response.status_code == 200:
                suppliers = response.json()
                self.log_test("GET Suppliers", True, f"Retrieved {len(suppliers)} suppliers")
            else:
                self.log_test("GET Suppliers", False, f"Failed to get suppliers: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("GET Suppliers", False, f"Error getting suppliers: {str(e)}")
        
        # Test 2: POST /api/suppliers (create new supplier)
        supplier_data = {
            "name": "Fournisseur Test 1",
            "contact_person": "Jean Dupont",
            "phone": "+33123456789",
            "email": "contact@fournisseur1.com",
            "address": "123 Rue de Test, Paris"
        }
        
        try:
            response = requests.post(f"{self.base_url}/suppliers",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json=supplier_data)
            
            if response.status_code in [200, 201]:
                supplier = response.json()
                self.suppliers.append(supplier)
                self.log_test("POST Suppliers", True, f"Created supplier: {supplier['name']}")
            else:
                self.log_test("POST Suppliers", False, f"Failed to create supplier: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("POST Suppliers", False, f"Error creating supplier: {str(e)}")
        
        # Test 3: Create second supplier
        supplier_data2 = {
            "name": "Fournisseur Test 2",
            "contact_person": "Marie Martin",
            "phone": "+33987654321",
            "email": "contact@fournisseur2.com",
            "address": "456 Avenue de Test, Lyon"
        }
        
        try:
            response = requests.post(f"{self.base_url}/suppliers",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json=supplier_data2)
            
            if response.status_code in [200, 201]:
                supplier = response.json()
                self.suppliers.append(supplier)
                self.log_test("POST Suppliers 2", True, f"Created second supplier: {supplier['name']}")
            else:
                self.log_test("POST Suppliers 2", False, f"Failed to create second supplier: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("POST Suppliers 2", False, f"Error creating second supplier: {str(e)}")
        
        # Test 4: Test unique name constraint
        try:
            response = requests.post(f"{self.base_url}/suppliers",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json={"name": "Fournisseur Test 1"})  # Duplicate name
            
            if response.status_code == 400:
                self.log_test("Supplier Unique Name", True, "Correctly rejected duplicate supplier name")
            else:
                self.log_test("Supplier Unique Name", False, f"Should reject duplicate name: {response.status_code}")
                
        except Exception as e:
            self.log_test("Supplier Unique Name", False, f"Error testing unique name: {str(e)}")
        
        # Test 5: PUT /api/suppliers/{supplier_id} (update supplier)
        if self.suppliers:
            supplier_id = self.suppliers[0]["id"]
            update_data = {
                "name": "Fournisseur Test 1 Modifié",
                "contact_person": "Jean Dupont Jr",
                "phone": "+33123456790",
                "email": "nouveau@fournisseur1.com",
                "address": "789 Boulevard de Test, Paris"
            }
            
            try:
                response = requests.put(f"{self.base_url}/suppliers/{supplier_id}",
                    headers={"Authorization": f"Bearer {self.admin_token}"},
                    json=update_data)
                
                if response.status_code == 200:
                    updated_supplier = response.json()
                    self.suppliers[0] = updated_supplier
                    self.log_test("PUT Suppliers", True, f"Updated supplier: {updated_supplier['name']}")
                else:
                    self.log_test("PUT Suppliers", False, f"Failed to update supplier: {response.status_code}", response.text)
                    
            except Exception as e:
                self.log_test("PUT Suppliers", False, f"Error updating supplier: {str(e)}")
        
        # Test 6: DELETE /api/suppliers/{supplier_id} (deactivate supplier)
        if len(self.suppliers) > 1:
            supplier_id = self.suppliers[1]["id"]
            
            try:
                response = requests.delete(f"{self.base_url}/suppliers/{supplier_id}",
                    headers={"Authorization": f"Bearer {self.admin_token}"})
                
                if response.status_code == 200:
                    self.log_test("DELETE Suppliers", True, "Successfully deactivated supplier")
                    
                    # Verify supplier is no longer in active list
                    response = requests.get(f"{self.base_url}/suppliers",
                        headers={"Authorization": f"Bearer {self.admin_token}"})
                    
                    if response.status_code == 200:
                        active_suppliers = response.json()
                        deactivated_found = any(s["id"] == supplier_id for s in active_suppliers)
                        if not deactivated_found:
                            self.log_test("Supplier Deactivation", True, "Deactivated supplier not in active list")
                        else:
                            self.log_test("Supplier Deactivation", False, "Deactivated supplier still in active list")
                else:
                    self.log_test("DELETE Suppliers", False, f"Failed to deactivate supplier: {response.status_code}", response.text)
                    
            except Exception as e:
                self.log_test("DELETE Suppliers", False, f"Error deactivating supplier: {str(e)}")
    
    def test_supplier_permissions(self):
        """Test supplier permissions - only admin/manager should access"""
        print("\n=== TESTING SUPPLIER PERMISSIONS ===")
        
        if not self.server_token:
            self.log_test("Supplier Permissions Setup", False, "Server token not available")
            return
        
        # Test server user cannot access suppliers
        try:
            response = requests.get(f"{self.base_url}/suppliers",
                headers={"Authorization": f"Bearer {self.server_token}"})
            
            if response.status_code == 403:
                self.log_test("Supplier GET Permission", True, "Server user correctly denied access to suppliers")
            else:
                self.log_test("Supplier GET Permission", False, f"Server user should be denied access: {response.status_code}")
                
        except Exception as e:
            self.log_test("Supplier GET Permission", False, f"Error testing supplier permissions: {str(e)}")
        
        # Test server user cannot create suppliers
        try:
            response = requests.post(f"{self.base_url}/suppliers",
                headers={"Authorization": f"Bearer {self.server_token}"},
                json={"name": "Test Supplier"})
            
            if response.status_code == 403:
                self.log_test("Supplier POST Permission", True, "Server user correctly denied supplier creation")
            else:
                self.log_test("Supplier POST Permission", False, f"Server user should be denied creation: {response.status_code}")
                
        except Exception as e:
            self.log_test("Supplier POST Permission", False, f"Error testing supplier creation permissions: {str(e)}")
    
    def test_purchase_number_generation(self):
        """Test purchase number generation"""
        print("\n=== TESTING PURCHASE NUMBER GENERATION ===")
        
        # Test 1: Generate purchase number
        try:
            response = requests.post(f"{self.base_url}/purchases/generate-number",
                headers={"Authorization": f"Bearer {self.admin_token}"})
            
            if response.status_code == 200:
                data = response.json()
                purchase_number = data.get("purchase_number")
                
                if purchase_number and purchase_number.startswith("ACH"):
                    self.log_test("Generate Purchase Number", True, f"Generated number: {purchase_number}")
                    
                    # Test uniqueness by generating another
                    time.sleep(0.01)  # Small delay to ensure different timestamp
                    response2 = requests.post(f"{self.base_url}/purchases/generate-number",
                        headers={"Authorization": f"Bearer {self.admin_token}"})
                    
                    if response2.status_code == 200:
                        data2 = response2.json()
                        purchase_number2 = data2.get("purchase_number")
                        
                        if purchase_number != purchase_number2:
                            self.log_test("Purchase Number Uniqueness", True, f"Generated unique numbers: {purchase_number} != {purchase_number2}")
                        else:
                            self.log_test("Purchase Number Uniqueness", False, "Generated identical numbers")
                else:
                    self.log_test("Generate Purchase Number", False, f"Invalid number format: {purchase_number}")
            else:
                self.log_test("Generate Purchase Number", False, f"Failed to generate number: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Generate Purchase Number", False, f"Error generating purchase number: {str(e)}")
        
        # Test server user permissions
        if self.server_token:
            try:
                response = requests.post(f"{self.base_url}/purchases/generate-number",
                    headers={"Authorization": f"Bearer {self.server_token}"})
                
                if response.status_code == 403:
                    self.log_test("Purchase Number Permission", True, "Server user correctly denied purchase number generation")
                else:
                    self.log_test("Purchase Number Permission", False, f"Server user should be denied: {response.status_code}")
                    
            except Exception as e:
                self.log_test("Purchase Number Permission", False, f"Error testing purchase number permissions: {str(e)}")
    
    def test_purchases_crud(self):
        """Test complete CRUD operations for purchases"""
        print("\n=== TESTING PURCHASES CRUD ===")
        
        if not self.suppliers:
            self.log_test("Purchase CRUD Setup", False, "No suppliers available for testing")
            return
        
        # Test 1: POST /api/purchases (create new purchase)
        purchase_data = {
            "supplier_id": self.suppliers[0]["id"],
            "invoice_number": "INV-2025-001",
            "notes": "Premier achat de test"
        }
        
        try:
            response = requests.post(f"{self.base_url}/purchases",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json=purchase_data)
            
            if response.status_code in [200, 201]:
                purchase = response.json()
                self.purchases.append(purchase)
                
                # Verify purchase number format
                if purchase["purchase_number"].startswith("ACH"):
                    self.log_test("POST Purchases", True, f"Created purchase: {purchase['purchase_number']}")
                else:
                    self.log_test("POST Purchases", False, f"Invalid purchase number format: {purchase['purchase_number']}")
            else:
                self.log_test("POST Purchases", False, f"Failed to create purchase: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("POST Purchases", False, f"Error creating purchase: {str(e)}")
        
        # Test 2: GET /api/purchases (list purchases)
        try:
            response = requests.get(f"{self.base_url}/purchases",
                headers={"Authorization": f"Bearer {self.admin_token}"})
            
            if response.status_code == 200:
                purchases = response.json()
                self.log_test("GET Purchases", True, f"Retrieved {len(purchases)} purchases")
                
                # Verify supplier details are included
                if purchases and "supplier_name" in purchases[0]:
                    self.log_test("Purchase Supplier Details", True, "Purchases include supplier details")
                else:
                    self.log_test("Purchase Supplier Details", False, "Purchases missing supplier details")
            else:
                self.log_test("GET Purchases", False, f"Failed to get purchases: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("GET Purchases", False, f"Error getting purchases: {str(e)}")
        
        # Test 3: GET /api/purchases/{purchase_id} (specific purchase)
        if self.purchases:
            purchase_id = self.purchases[0]["id"]
            
            try:
                response = requests.get(f"{self.base_url}/purchases/{purchase_id}",
                    headers={"Authorization": f"Bearer {self.admin_token}"})
                
                if response.status_code == 200:
                    purchase = response.json()
                    self.log_test("GET Purchase by ID", True, f"Retrieved purchase: {purchase['purchase_number']}")
                else:
                    self.log_test("GET Purchase by ID", False, f"Failed to get purchase: {response.status_code}", response.text)
                    
            except Exception as e:
                self.log_test("GET Purchase by ID", False, f"Error getting purchase by ID: {str(e)}")
    
    def test_purchase_items_crud(self):
        """Test CRUD operations for purchase items"""
        print("\n=== TESTING PURCHASE ITEMS CRUD ===")
        
        if not self.purchases or not self.products:
            self.log_test("Purchase Items Setup", False, "No purchases or products available for testing")
            return
        
        purchase_id = self.purchases[0]["id"]
        
        # Test 1: GET /api/purchases/{purchase_id}/items (empty initially)
        try:
            response = requests.get(f"{self.base_url}/purchases/{purchase_id}/items",
                headers={"Authorization": f"Bearer {self.admin_token}"})
            
            if response.status_code == 200:
                items = response.json()
                self.log_test("GET Purchase Items", True, f"Retrieved {len(items)} purchase items")
            else:
                self.log_test("GET Purchase Items", False, f"Failed to get purchase items: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("GET Purchase Items", False, f"Error getting purchase items: {str(e)}")
        
        # Test 2: POST /api/purchases/{purchase_id}/items (add item)
        if self.products:
            item_data = {
                "product_id": self.products[0]["id"],
                "quantity": 10,
                "unit_cost": 8.50
            }
            
            try:
                response = requests.post(f"{self.base_url}/purchases/{purchase_id}/items",
                    headers={"Authorization": f"Bearer {self.admin_token}"},
                    json=item_data)
                
                if response.status_code in [200, 201]:
                    item = response.json()
                    self.log_test("POST Purchase Items", True, f"Added item: {item_data['quantity']} x {item_data['unit_cost']}")
                    
                    # Verify total calculation
                    expected_total = item_data["quantity"] * item_data["unit_cost"]
                    if item.get("total_cost") == expected_total:
                        self.log_test("Purchase Item Total Calculation", True, f"Correct total: {expected_total}")
                    else:
                        self.log_test("Purchase Item Total Calculation", False, f"Incorrect total: expected {expected_total}, got {item.get('total_cost')}")
                else:
                    self.log_test("POST Purchase Items", False, f"Failed to add purchase item: {response.status_code}", response.text)
                    
            except Exception as e:
                self.log_test("POST Purchase Items", False, f"Error adding purchase item: {str(e)}")
        
        # Test 3: Add second item
        if len(self.products) > 1:
            item_data2 = {
                "product_id": self.products[1]["id"],
                "quantity": 5,
                "unit_cost": 18.00
            }
            
            try:
                response = requests.post(f"{self.base_url}/purchases/{purchase_id}/items",
                    headers={"Authorization": f"Bearer {self.admin_token}"},
                    json=item_data2)
                
                if response.status_code in [200, 201]:
                    self.log_test("POST Purchase Items 2", True, f"Added second item: {item_data2['quantity']} x {item_data2['unit_cost']}")
                else:
                    self.log_test("POST Purchase Items 2", False, f"Failed to add second purchase item: {response.status_code}", response.text)
                    
            except Exception as e:
                self.log_test("POST Purchase Items 2", False, f"Error adding second purchase item: {str(e)}")
        
        # Test 4: GET purchase items with product details
        try:
            response = requests.get(f"{self.base_url}/purchases/{purchase_id}/items",
                headers={"Authorization": f"Bearer {self.admin_token}"})
            
            if response.status_code == 200:
                items = response.json()
                if items and "product_name" in items[0]:
                    self.log_test("Purchase Items Product Details", True, f"Items include product details: {items[0]['product_name']}")
                else:
                    self.log_test("Purchase Items Product Details", False, "Items missing product details")
            else:
                self.log_test("Purchase Items Product Details", False, f"Failed to get items with details: {response.status_code}")
                
        except Exception as e:
            self.log_test("Purchase Items Product Details", False, f"Error getting items with details: {str(e)}")
        
        # Test 5: Verify purchase total is updated
        try:
            response = requests.get(f"{self.base_url}/purchases/{purchase_id}",
                headers={"Authorization": f"Bearer {self.admin_token}"})
            
            if response.status_code == 200:
                purchase = response.json()
                if purchase["total_amount"] > 0:
                    self.log_test("Purchase Total Update", True, f"Purchase total updated: {purchase['total_amount']}")
                else:
                    self.log_test("Purchase Total Update", False, "Purchase total not updated")
            else:
                self.log_test("Purchase Total Update", False, f"Failed to get updated purchase: {response.status_code}")
                
        except Exception as e:
            self.log_test("Purchase Total Update", False, f"Error checking purchase total: {str(e)}")
    
    def test_purchase_finalization(self):
        """Test purchase finalization and stock updates"""
        print("\n=== TESTING PURCHASE FINALIZATION ===")
        
        if not self.purchases or not self.products:
            self.log_test("Purchase Finalization Setup", False, "No purchases available for testing")
            return
        
        purchase_id = self.purchases[0]["id"]
        
        # Get initial stock levels
        initial_stocks = {}
        for product in self.products[:2]:  # First 2 products
            try:
                response = requests.get(f"{self.base_url}/products/{product['id']}",
                    headers={"Authorization": f"Bearer {self.admin_token}"})
                
                if response.status_code == 200:
                    product_data = response.json()
                    initial_stocks[product["id"]] = product_data["stock"]
                    
            except Exception as e:
                self.log_test("Get Initial Stock", False, f"Error getting initial stock: {str(e)}")
        
        # Test finalization
        try:
            response = requests.post(f"{self.base_url}/purchases/{purchase_id}/finalize",
                headers={"Authorization": f"Bearer {self.admin_token}"})
            
            if response.status_code == 200:
                result = response.json()
                self.log_test("Purchase Finalization", True, f"Purchase finalized: {result['message']}")
                
                # Verify stock updates
                time.sleep(0.5)  # Small delay to ensure stock updates are processed
                
                for product_id, initial_stock in initial_stocks.items():
                    try:
                        response = requests.get(f"{self.base_url}/products/{product_id}",
                            headers={"Authorization": f"Bearer {self.admin_token}"})
                        
                        if response.status_code == 200:
                            product_data = response.json()
                            new_stock = product_data["stock"]
                            
                            if new_stock > initial_stock:
                                self.log_test("Stock Update", True, f"Stock increased: {initial_stock} → {new_stock}")
                            else:
                                self.log_test("Stock Update", False, f"Stock not increased: {initial_stock} → {new_stock}")
                        else:
                            self.log_test("Stock Update", False, f"Failed to get updated product: {response.status_code}")
                            
                    except Exception as e:
                        self.log_test("Stock Update", False, f"Error checking stock update: {str(e)}")
                        
            else:
                self.log_test("Purchase Finalization", False, f"Failed to finalize purchase: {response.status_code}", response.text)
                
        except Exception as e:
            self.log_test("Purchase Finalization", False, f"Error finalizing purchase: {str(e)}")
    
    def test_purchase_permissions(self):
        """Test purchase permissions - only admin/manager should access"""
        print("\n=== TESTING PURCHASE PERMISSIONS ===")
        
        if not self.server_token:
            self.log_test("Purchase Permissions Setup", False, "Server token not available")
            return
        
        # Test server user cannot access purchases
        endpoints_to_test = [
            ("GET /purchases", "get", f"{self.base_url}/purchases"),
            ("POST /purchases", "post", f"{self.base_url}/purchases", {"supplier_id": "test", "invoice_number": "test"}),
            ("POST /purchases/generate-number", "post", f"{self.base_url}/purchases/generate-number"),
        ]
        
        for test_name, method, url, *data in endpoints_to_test:
            try:
                if method == "get":
                    response = requests.get(url, headers={"Authorization": f"Bearer {self.server_token}"})
                elif method == "post":
                    json_data = data[0] if data else {}
                    response = requests.post(url, headers={"Authorization": f"Bearer {self.server_token}"}, json=json_data)
                
                if response.status_code == 403:
                    self.log_test(f"Purchase Permission {test_name}", True, "Server user correctly denied access")
                else:
                    self.log_test(f"Purchase Permission {test_name}", False, f"Server user should be denied: {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Purchase Permission {test_name}", False, f"Error testing permissions: {str(e)}")
        
        # Test purchase items permissions
        if self.purchases:
            purchase_id = self.purchases[0]["id"]
            
            try:
                response = requests.get(f"{self.base_url}/purchases/{purchase_id}/items",
                    headers={"Authorization": f"Bearer {self.server_token}"})
                
                if response.status_code == 403:
                    self.log_test("Purchase Items Permission", True, "Server user correctly denied access to purchase items")
                else:
                    self.log_test("Purchase Items Permission", False, f"Server user should be denied: {response.status_code}")
                    
            except Exception as e:
                self.log_test("Purchase Items Permission", False, f"Error testing purchase items permissions: {str(e)}")
    
    def run_complete_workflow_test(self):
        """Test complete purchase workflow"""
        print("\n=== TESTING COMPLETE PURCHASE WORKFLOW ===")
        
        if not self.suppliers or not self.products:
            self.log_test("Complete Workflow Setup", False, "Missing suppliers or products for workflow test")
            return
        
        # Step 1: Create new purchase
        purchase_data = {
            "supplier_id": self.suppliers[0]["id"],
            "invoice_number": "WORKFLOW-001",
            "notes": "Test complet du workflow d'achat"
        }
        
        workflow_purchase = None
        
        try:
            response = requests.post(f"{self.base_url}/purchases",
                headers={"Authorization": f"Bearer {self.admin_token}"},
                json=purchase_data)
            
            if response.status_code in [200, 201]:
                workflow_purchase = response.json()
                self.log_test("Workflow Step 1", True, f"Created purchase: {workflow_purchase['purchase_number']}")
            else:
                self.log_test("Workflow Step 1", False, f"Failed to create purchase: {response.status_code}")
                return
                
        except Exception as e:
            self.log_test("Workflow Step 1", False, f"Error creating purchase: {str(e)}")
            return
        
        # Step 2: Add multiple products
        purchase_id = workflow_purchase["id"]
        items_added = 0
        
        for i, product in enumerate(self.products[:2]):
            item_data = {
                "product_id": product["id"],
                "quantity": (i + 1) * 5,  # 5, 10
                "unit_cost": 12.50 + (i * 2.5)  # 12.50, 15.00
            }
            
            try:
                response = requests.post(f"{self.base_url}/purchases/{purchase_id}/items",
                    headers={"Authorization": f"Bearer {self.admin_token}"},
                    json=item_data)
                
                if response.status_code in [200, 201]:
                    items_added += 1
                    self.log_test(f"Workflow Step 2.{i+1}", True, f"Added item: {item_data['quantity']} x {product['name']}")
                else:
                    self.log_test(f"Workflow Step 2.{i+1}", False, f"Failed to add item: {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Workflow Step 2.{i+1}", False, f"Error adding item: {str(e)}")
        
        # Step 3: Verify totals
        try:
            response = requests.get(f"{self.base_url}/purchases/{purchase_id}",
                headers={"Authorization": f"Bearer {self.admin_token}"})
            
            if response.status_code == 200:
                purchase = response.json()
                expected_total = (5 * 12.50) + (10 * 15.00)  # 62.50 + 150.00 = 212.50
                
                if abs(purchase["total_amount"] - expected_total) < 0.01:
                    self.log_test("Workflow Step 3", True, f"Correct total calculated: {purchase['total_amount']}")
                else:
                    self.log_test("Workflow Step 3", False, f"Incorrect total: expected {expected_total}, got {purchase['total_amount']}")
            else:
                self.log_test("Workflow Step 3", False, f"Failed to get purchase for total verification: {response.status_code}")
                
        except Exception as e:
            self.log_test("Workflow Step 3", False, f"Error verifying totals: {str(e)}")
        
        # Step 4: Get initial stock levels
        initial_stocks = {}
        for product in self.products[:2]:
            try:
                response = requests.get(f"{self.base_url}/products/{product['id']}",
                    headers={"Authorization": f"Bearer {self.admin_token}"})
                
                if response.status_code == 200:
                    product_data = response.json()
                    initial_stocks[product["id"]] = product_data["stock"]
                    
            except Exception as e:
                pass
        
        # Step 5: Finalize purchase
        try:
            response = requests.post(f"{self.base_url}/purchases/{purchase_id}/finalize",
                headers={"Authorization": f"Bearer {self.admin_token}"})
            
            if response.status_code == 200:
                self.log_test("Workflow Step 4", True, "Purchase finalized successfully")
                
                # Step 6: Verify stock updates
                time.sleep(0.5)
                
                stock_updates_correct = 0
                for i, product in enumerate(self.products[:2]):
                    try:
                        response = requests.get(f"{self.base_url}/products/{product['id']}",
                            headers={"Authorization": f"Bearer {self.admin_token}"})
                        
                        if response.status_code == 200:
                            product_data = response.json()
                            new_stock = product_data["stock"]
                            initial_stock = initial_stocks.get(product["id"], 0)
                            expected_increase = (i + 1) * 5  # 5, 10
                            
                            if new_stock == initial_stock + expected_increase:
                                stock_updates_correct += 1
                                self.log_test(f"Workflow Step 5.{i+1}", True, f"Stock correctly updated: {initial_stock} + {expected_increase} = {new_stock}")
                            else:
                                self.log_test(f"Workflow Step 5.{i+1}", False, f"Stock incorrectly updated: expected {initial_stock + expected_increase}, got {new_stock}")
                                
                    except Exception as e:
                        self.log_test(f"Workflow Step 5.{i+1}", False, f"Error checking stock update: {str(e)}")
                
                if stock_updates_correct == 2:
                    self.log_test("Complete Workflow", True, "All workflow steps completed successfully")
                else:
                    self.log_test("Complete Workflow", False, f"Workflow partially successful: {stock_updates_correct}/2 stock updates correct")
                    
            else:
                self.log_test("Workflow Step 4", False, f"Failed to finalize purchase: {response.status_code}")
                
        except Exception as e:
            self.log_test("Workflow Step 4", False, f"Error finalizing purchase: {str(e)}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("PHASE 5 PURCHASE MANAGEMENT - TEST SUMMARY")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if "✅ PASS" in t["status"]])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS ({failed_tests}):")
            for result in self.test_results:
                if "❌ FAIL" in result["status"]:
                    print(f"  - {result['test']}: {result['message']}")
                    if result["details"]:
                        print(f"    Details: {result['details']}")
        
        print(f"\n✅ PASSED TESTS ({passed_tests}):")
        for result in self.test_results:
            if "✅ PASS" in result["status"]:
                print(f"  - {result['test']}: {result['message']}")
        
        print("\n" + "="*80)
        
        return passed_tests, failed_tests
    
    def run_all_tests(self):
        """Run all Phase 5 purchase management tests"""
        print("🚀 STARTING PHASE 5 PURCHASE MANAGEMENT TESTS")
        print("="*80)
        
        # Setup
        if not self.setup_authentication():
            print("❌ Authentication setup failed. Cannot continue.")
            return
        
        if not self.setup_test_data():
            print("❌ Test data setup failed. Cannot continue.")
            return
        
        # Run all test suites
        self.test_suppliers_crud()
        self.test_supplier_permissions()
        self.test_purchase_number_generation()
        self.test_purchases_crud()
        self.test_purchase_items_crud()
        self.test_purchase_finalization()
        self.test_purchase_permissions()
        self.run_complete_workflow_test()
        
        # Print summary
        passed, failed = self.print_summary()
        
        return passed, failed

def main():
    """Main test execution"""
    tester = SalesManagerTester()
    passed, failed = tester.run_all_tests()
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Phase 5 Purchase Management is fully functional.")
        sys.exit(0)
    else:
        print(f"\n⚠️  {failed} tests failed. Please review the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()