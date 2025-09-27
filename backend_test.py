#!/usr/bin/env python3
"""
Backend Test Suite for Phase 7 - Synchronisation Offline/Online
Tests all sync endpoints and scenarios as requested
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Configuration
BASE_URL = "https://salesync-1.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@salesmanager.com"
ADMIN_PASSWORD = "admin123"

class SalesManagerSyncTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.token = None
        self.headers = {}
        self.test_results = []
        self.device_id = f"test_device_{int(time.time())}"
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "status": status,
            "success": success,
            "details": details
        })
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
    
    def authenticate(self) -> bool:
        """Authenticate and get token"""
        try:
            # First initialize the app
            init_response = requests.post(f"{self.base_url}/setup/init")
            print(f"App initialization: {init_response.status_code}")
            
            # Login
            login_data = {
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            }
            
            response = requests.post(f"{self.base_url}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.headers = {"Authorization": f"Bearer {self.token}"}
                self.log_test("Authentication", True, f"Token obtained for {data['user']['email']}")
                return True
            else:
                self.log_test("Authentication", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Authentication", False, f"Exception: {str(e)}")
            return False
    
    def setup_test_data(self) -> Dict[str, Any]:
        """Setup test data for sync operations"""
        test_data = {}
        
        try:
            # Get categories
            categories_response = requests.get(f"{self.base_url}/categories", headers=self.headers)
            if categories_response.status_code == 200:
                categories = categories_response.json()
                test_data['category_id'] = categories[0]['id'] if categories else None
            
            # Get payment methods
            payment_methods_response = requests.get(f"{self.base_url}/payment-methods", headers=self.headers)
            if payment_methods_response.status_code == 200:
                payment_methods = payment_methods_response.json()
                test_data['payment_method_id'] = payment_methods[0]['id'] if payment_methods else None
            
            # Create a test product for sync operations
            product_data = {
                "name": "Produit Test Sync",
                "code": f"SYNC{int(time.time())}",
                "category_id": test_data['category_id'],
                "purchase_price": 100.0,
                "selling_price": 150.0,
                "stock": 50
            }
            
            product_response = requests.post(f"{self.base_url}/products", json=product_data, headers=self.headers)
            if product_response.status_code == 200:
                test_data['product'] = product_response.json()
                test_data['product_id'] = test_data['product']['id']
            
            # Create a test supplier
            supplier_data = {
                "name": f"Fournisseur Test Sync {int(time.time())}",
                "contact_person": "Jean Dupont",
                "phone": "+33123456789",
                "email": "jean@supplier.com"
            }
            
            supplier_response = requests.post(f"{self.base_url}/suppliers", json=supplier_data, headers=self.headers)
            if supplier_response.status_code == 200:
                test_data['supplier'] = supplier_response.json()
                test_data['supplier_id'] = test_data['supplier']['id']
            
            self.log_test("Test Data Setup", True, f"Created product, supplier, got categories and payment methods")
            return test_data
            
        except Exception as e:
            self.log_test("Test Data Setup", False, f"Exception: {str(e)}")
            return {}
    
    def test_sync_upload_sale_creation(self, test_data: Dict[str, Any]) -> bool:
        """Test POST /api/sync/upload - Sale creation"""
        try:
            sync_id = f"sale_sync_{int(time.time())}"
            sale_number = f"VTE{int(time.time())}"
            
            sync_batch = {
                "device_id": self.device_id,
                "sync_items": [
                    {
                        "sync_id": sync_id,
                        "data_type": "sale",
                        "action": "create",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {
                            "sale_number": sale_number,
                            "status": "completed",
                            "total_amount": 300.0,
                            "payment_status": "paid",
                            "created_at": datetime.utcnow().isoformat(),
                            "completed_at": datetime.utcnow().isoformat(),
                            "items": [
                                {
                                    "product_id": test_data['product_id'],
                                    "quantity": 2,
                                    "unit_price": 150.0,
                                    "total_price": 300.0
                                }
                            ],
                            "payments": [
                                {
                                    "payment_method_id": test_data['payment_method_id'],
                                    "amount": 300.0,
                                    "created_at": datetime.utcnow().isoformat()
                                }
                            ]
                        }
                    }
                ]
            }
            
            response = requests.post(f"{self.base_url}/sync/upload", json=sync_batch, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                if results and results[0]['status'] == 'success':
                    self.log_test("Sync Upload - Sale Creation", True, f"Sale synced successfully: {sale_number}")
                    return True
                else:
                    self.log_test("Sync Upload - Sale Creation", False, f"Sync failed: {results}")
                    return False
            else:
                self.log_test("Sync Upload - Sale Creation", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Sync Upload - Sale Creation", False, f"Exception: {str(e)}")
            return False
    
    def test_sync_upload_sale_conflict(self, test_data: Dict[str, Any]) -> bool:
        """Test sync conflict detection for duplicate sale"""
        try:
            sync_id = f"sale_conflict_{int(time.time())}"
            sale_number = f"VTE{int(time.time())}"
            
            # First upload
            sync_batch = {
                "device_id": self.device_id,
                "sync_items": [
                    {
                        "sync_id": sync_id,
                        "data_type": "sale",
                        "action": "create",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {
                            "sale_number": sale_number,
                            "status": "completed",
                            "total_amount": 150.0,
                            "payment_status": "paid",
                            "created_at": datetime.utcnow().isoformat(),
                            "completed_at": datetime.utcnow().isoformat(),
                            "items": [
                                {
                                    "product_id": test_data['product_id'],
                                    "quantity": 1,
                                    "unit_price": 150.0,
                                    "total_price": 150.0
                                }
                            ]
                        }
                    }
                ]
            }
            
            # First upload should succeed
            response1 = requests.post(f"{self.base_url}/sync/upload", json=sync_batch, headers=self.headers)
            
            # Second upload with same sync_id should detect conflict
            response2 = requests.post(f"{self.base_url}/sync/upload", json=sync_batch, headers=self.headers)
            
            if response2.status_code == 200:
                data = response2.json()
                results = data.get('results', [])
                
                if results and results[0]['status'] == 'conflict':
                    self.log_test("Sync Upload - Sale Conflict Detection", True, f"Conflict detected correctly for duplicate sale")
                    return True
                else:
                    self.log_test("Sync Upload - Sale Conflict Detection", False, f"Expected conflict, got: {results}")
                    return False
            else:
                self.log_test("Sync Upload - Sale Conflict Detection", False, f"Status: {response2.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Sync Upload - Sale Conflict Detection", False, f"Exception: {str(e)}")
            return False
    
    def test_sync_upload_product_update(self, test_data: Dict[str, Any]) -> bool:
        """Test POST /api/sync/upload - Product update"""
        try:
            sync_id = f"product_sync_{int(time.time())}"
            
            sync_batch = {
                "device_id": self.device_id,
                "sync_items": [
                    {
                        "sync_id": sync_id,
                        "data_type": "product",
                        "action": "update",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {
                            "id": test_data['product_id'],
                            "name": "Produit Test Sync Modifié",
                            "selling_price": 175.0,
                            "stock": 45,
                            "updated_at": datetime.utcnow().isoformat()
                        }
                    }
                ]
            }
            
            response = requests.post(f"{self.base_url}/sync/upload", json=sync_batch, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                if results and results[0]['status'] == 'success':
                    self.log_test("Sync Upload - Product Update", True, f"Product updated successfully")
                    return True
                else:
                    self.log_test("Sync Upload - Product Update", False, f"Update failed: {results}")
                    return False
            else:
                self.log_test("Sync Upload - Product Update", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Sync Upload - Product Update", False, f"Exception: {str(e)}")
            return False
    
    def test_sync_upload_product_conflict(self, test_data: Dict[str, Any]) -> bool:
        """Test product update conflict detection"""
        try:
            # First, update the product on server to create a newer timestamp
            update_data = {
                "name": "Produit Serveur Plus Récent",
                "code": test_data['product']['code'],
                "category_id": test_data['product']['category_id'],
                "purchase_price": test_data['product']['purchase_price'],
                "selling_price": 200.0,
                "stock": 40
            }
            
            server_update = requests.put(f"{self.base_url}/products/{test_data['product_id']}", 
                                       json=update_data, headers=self.headers)
            
            if server_update.status_code != 200:
                self.log_test("Sync Upload - Product Conflict Setup", False, "Failed to update product on server")
                return False
            
            # Wait a moment to ensure timestamp difference
            time.sleep(1)
            
            # Now try to sync an older update from client
            sync_id = f"product_conflict_{int(time.time())}"
            old_timestamp = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
            
            sync_batch = {
                "device_id": self.device_id,
                "sync_items": [
                    {
                        "sync_id": sync_id,
                        "data_type": "product",
                        "action": "update",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {
                            "id": test_data['product_id'],
                            "name": "Produit Client Ancien",
                            "selling_price": 160.0,
                            "stock": 35,
                            "updated_at": old_timestamp
                        }
                    }
                ]
            }
            
            response = requests.post(f"{self.base_url}/sync/upload", json=sync_batch, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                if results and results[0]['status'] == 'conflict':
                    self.log_test("Sync Upload - Product Conflict Detection", True, f"Conflict detected for older client version")
                    return True
                else:
                    self.log_test("Sync Upload - Product Conflict Detection", False, f"Expected conflict, got: {results}")
                    return False
            else:
                self.log_test("Sync Upload - Product Conflict Detection", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Sync Upload - Product Conflict Detection", False, f"Exception: {str(e)}")
            return False
    
    def test_sync_upload_purchase_creation(self, test_data: Dict[str, Any]) -> bool:
        """Test POST /api/sync/upload - Purchase creation"""
        try:
            sync_id = f"purchase_sync_{int(time.time())}"
            purchase_number = f"ACH{int(time.time())}"
            
            sync_batch = {
                "device_id": self.device_id,
                "sync_items": [
                    {
                        "sync_id": sync_id,
                        "data_type": "purchase",
                        "action": "create",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {
                            "purchase_number": purchase_number,
                            "supplier_id": test_data['supplier_id'],
                            "invoice_number": f"INV{int(time.time())}",
                            "purchase_date": datetime.utcnow().isoformat(),
                            "total_amount": 500.0,
                            "notes": "Achat synchronisé depuis offline",
                            "created_at": datetime.utcnow().isoformat(),
                            "items": [
                                {
                                    "product_id": test_data['product_id'],
                                    "quantity": 5,
                                    "unit_cost": 100.0,
                                    "total_cost": 500.0
                                }
                            ]
                        }
                    }
                ]
            }
            
            response = requests.post(f"{self.base_url}/sync/upload", json=sync_batch, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                if results and results[0]['status'] == 'success':
                    self.log_test("Sync Upload - Purchase Creation", True, f"Purchase synced successfully: {purchase_number}")
                    return True
                else:
                    self.log_test("Sync Upload - Purchase Creation", False, f"Sync failed: {results}")
                    return False
            else:
                self.log_test("Sync Upload - Purchase Creation", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Sync Upload - Purchase Creation", False, f"Exception: {str(e)}")
            return False
    
    def test_sync_upload_batch_multiple_items(self, test_data: Dict[str, Any]) -> bool:
        """Test uploading multiple items in a single batch"""
        try:
            timestamp = int(time.time())
            
            sync_batch = {
                "device_id": self.device_id,
                "sync_items": [
                    {
                        "sync_id": f"batch_sale_{timestamp}",
                        "data_type": "sale",
                        "action": "create",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {
                            "sale_number": f"VTE{timestamp}",
                            "status": "completed",
                            "total_amount": 150.0,
                            "payment_status": "paid",
                            "created_at": datetime.utcnow().isoformat(),
                            "completed_at": datetime.utcnow().isoformat(),
                            "items": [
                                {
                                    "product_id": test_data['product_id'],
                                    "quantity": 1,
                                    "unit_price": 150.0,
                                    "total_price": 150.0
                                }
                            ]
                        }
                    },
                    {
                        "sync_id": f"batch_purchase_{timestamp}",
                        "data_type": "purchase",
                        "action": "create",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {
                            "purchase_number": f"ACH{timestamp}",
                            "supplier_id": test_data['supplier_id'],
                            "invoice_number": f"BATCH{timestamp}",
                            "purchase_date": datetime.utcnow().isoformat(),
                            "total_amount": 200.0,
                            "created_at": datetime.utcnow().isoformat(),
                            "items": [
                                {
                                    "product_id": test_data['product_id'],
                                    "quantity": 2,
                                    "unit_cost": 100.0,
                                    "total_cost": 200.0
                                }
                            ]
                        }
                    }
                ]
            }
            
            response = requests.post(f"{self.base_url}/sync/upload", json=sync_batch, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                if len(results) == 2 and all(r['status'] == 'success' for r in results):
                    self.log_test("Sync Upload - Batch Multiple Items", True, f"Batch with 2 items processed successfully")
                    return True
                else:
                    self.log_test("Sync Upload - Batch Multiple Items", False, f"Batch processing failed: {results}")
                    return False
            else:
                self.log_test("Sync Upload - Batch Multiple Items", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Sync Upload - Batch Multiple Items", False, f"Exception: {str(e)}")
            return False
    
    def test_sync_upload_invalid_data(self) -> bool:
        """Test sync upload with invalid data"""
        try:
            sync_batch = {
                "device_id": self.device_id,
                "sync_items": [
                    {
                        "sync_id": f"invalid_sync_{int(time.time())}",
                        "data_type": "sale",
                        "action": "create",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {
                            "sale_number": f"INVALID{int(time.time())}",
                            "status": "completed",
                            "total_amount": 150.0,
                            "items": [
                                {
                                    "product_id": "invalid_product_id",  # Invalid product ID
                                    "quantity": 1,
                                    "unit_price": 150.0,
                                    "total_price": 150.0
                                }
                            ]
                        }
                    }
                ]
            }
            
            response = requests.post(f"{self.base_url}/sync/upload", json=sync_batch, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                if results and results[0]['status'] == 'error':
                    self.log_test("Sync Upload - Invalid Data Handling", True, f"Invalid data correctly rejected")
                    return True
                else:
                    self.log_test("Sync Upload - Invalid Data Handling", False, f"Expected error, got: {results}")
                    return False
            else:
                self.log_test("Sync Upload - Invalid Data Handling", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Sync Upload - Invalid Data Handling", False, f"Exception: {str(e)}")
            return False
    
    def test_sync_download_all_data(self) -> bool:
        """Test GET /api/sync/download - Download all data types"""
        try:
            response = requests.get(f"{self.base_url}/sync/download", headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                sync_data = data.get('data', {})
                
                expected_types = ['products', 'categories', 'payment_methods', 'suppliers']
                found_types = list(sync_data.keys())
                
                if all(data_type in found_types for data_type in expected_types):
                    self.log_test("Sync Download - All Data Types", True, f"Downloaded: {found_types}")
                    return True
                else:
                    self.log_test("Sync Download - All Data Types", False, f"Missing data types. Found: {found_types}")
                    return False
            else:
                self.log_test("Sync Download - All Data Types", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Sync Download - All Data Types", False, f"Exception: {str(e)}")
            return False
    
    def test_sync_download_with_filters(self) -> bool:
        """Test GET /api/sync/download with date and type filters"""
        try:
            # Test with date filter
            last_sync = (datetime.utcnow() - timedelta(hours=1)).isoformat()
            params = {
                "last_sync": last_sync,
                "data_types": "products,categories"
            }
            
            response = requests.get(f"{self.base_url}/sync/download", params=params, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                sync_data = data.get('data', {})
                
                # Should only have products and categories
                if 'products' in sync_data and 'categories' in sync_data:
                    if 'suppliers' not in sync_data and 'payment_methods' not in sync_data:
                        self.log_test("Sync Download - With Filters", True, f"Filtered data correctly: {list(sync_data.keys())}")
                        return True
                    else:
                        self.log_test("Sync Download - With Filters", False, f"Filter not applied correctly: {list(sync_data.keys())}")
                        return False
                else:
                    self.log_test("Sync Download - With Filters", False, f"Missing expected data types: {list(sync_data.keys())}")
                    return False
            else:
                self.log_test("Sync Download - With Filters", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Sync Download - With Filters", False, f"Exception: {str(e)}")
            return False
    
    def test_sync_download_permissions(self) -> bool:
        """Test sync download respects user permissions"""
        try:
            # Create a server user (limited permissions)
            server_user_data = {
                "email": f"server{int(time.time())}@test.com",
                "password": "server123",
                "role": "serveur",
                "name": "Serveur Test"
            }
            
            register_response = requests.post(f"{self.base_url}/auth/register", json=server_user_data)
            
            if register_response.status_code != 200:
                self.log_test("Sync Download - Permissions Setup", False, "Failed to create server user")
                return False
            
            # Login as server user
            login_response = requests.post(f"{self.base_url}/auth/login", json={
                "email": server_user_data["email"],
                "password": server_user_data["password"]
            })
            
            if login_response.status_code != 200:
                self.log_test("Sync Download - Permissions Login", False, "Failed to login as server user")
                return False
            
            server_token = login_response.json()["access_token"]
            server_headers = {"Authorization": f"Bearer {server_token}"}
            
            # Try to download data as server user
            response = requests.get(f"{self.base_url}/sync/download", headers=server_headers)
            
            if response.status_code == 200:
                data = response.json()
                sync_data = data.get('data', {})
                
                # Server user should not have access to suppliers
                if 'suppliers' not in sync_data:
                    self.log_test("Sync Download - Permissions Check", True, f"Server user correctly denied suppliers access")
                    return True
                else:
                    self.log_test("Sync Download - Permissions Check", False, f"Server user incorrectly has suppliers access")
                    return False
            else:
                self.log_test("Sync Download - Permissions Check", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Sync Download - Permissions Check", False, f"Exception: {str(e)}")
            return False
    
    def test_sync_status_device(self) -> bool:
        """Test GET /api/sync/status/{device_id}"""
        try:
            response = requests.get(f"{self.base_url}/sync/status/{self.device_id}", headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                
                required_fields = ['device_id', 'last_sync', 'status']
                if all(field in data for field in required_fields):
                    if data['device_id'] == self.device_id:
                        self.log_test("Sync Status - Device Status", True, f"Status: {data['status']}, Last sync: {data['last_sync']}")
                        return True
                    else:
                        self.log_test("Sync Status - Device Status", False, f"Wrong device ID returned")
                        return False
                else:
                    self.log_test("Sync Status - Device Status", False, f"Missing required fields: {data}")
                    return False
            else:
                self.log_test("Sync Status - Device Status", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Sync Status - Device Status", False, f"Exception: {str(e)}")
            return False
    
    def test_sync_status_never_synced(self) -> bool:
        """Test sync status for device that never synced"""
        try:
            new_device_id = f"never_synced_{int(time.time())}"
            response = requests.get(f"{self.base_url}/sync/status/{new_device_id}", headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'never_synced' and data.get('last_sync') is None:
                    self.log_test("Sync Status - Never Synced Device", True, f"Correctly identified never synced device")
                    return True
                else:
                    self.log_test("Sync Status - Never Synced Device", False, f"Incorrect status for never synced device: {data}")
                    return False
            else:
                self.log_test("Sync Status - Never Synced Device", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Sync Status - Never Synced Device", False, f"Exception: {str(e)}")
            return False
    
    def test_unsupported_sync_type(self) -> bool:
        """Test sync upload with unsupported data type"""
        try:
            sync_batch = {
                "device_id": self.device_id,
                "sync_items": [
                    {
                        "sync_id": f"unsupported_{int(time.time())}",
                        "data_type": "unsupported_type",
                        "action": "create",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {"test": "data"}
                    }
                ]
            }
            
            response = requests.post(f"{self.base_url}/sync/upload", json=sync_batch, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                if results and results[0]['status'] == 'error' and 'Unsupported sync type' in results[0].get('error_message', ''):
                    self.log_test("Sync Upload - Unsupported Type", True, f"Unsupported type correctly rejected")
                    return True
                else:
                    self.log_test("Sync Upload - Unsupported Type", False, f"Expected error for unsupported type: {results}")
                    return False
            else:
                self.log_test("Sync Upload - Unsupported Type", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Sync Upload - Unsupported Type", False, f"Exception: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all sync tests"""
        print("=" * 80)
        print("PHASE 7 SYNCHRONISATION OFFLINE/ONLINE - BACKEND TESTS")
        print("=" * 80)
        
        # Authenticate
        if not self.authenticate():
            print("❌ Authentication failed. Cannot proceed with tests.")
            return
        
        # Setup test data
        test_data = self.setup_test_data()
        if not test_data:
            print("❌ Test data setup failed. Cannot proceed with tests.")
            return
        
        print(f"\n🔄 Testing with device_id: {self.device_id}")
        print(f"📊 Test data: Product ID: {test_data.get('product_id')}, Supplier ID: {test_data.get('supplier_id')}")
        
        # Run sync upload tests
        print("\n" + "=" * 50)
        print("SYNC UPLOAD TESTS")
        print("=" * 50)
        
        self.test_sync_upload_sale_creation(test_data)
        self.test_sync_upload_sale_conflict(test_data)
        self.test_sync_upload_product_update(test_data)
        self.test_sync_upload_product_conflict(test_data)
        self.test_sync_upload_purchase_creation(test_data)
        self.test_sync_upload_batch_multiple_items(test_data)
        self.test_sync_upload_invalid_data()
        self.test_unsupported_sync_type()
        
        # Run sync download tests
        print("\n" + "=" * 50)
        print("SYNC DOWNLOAD TESTS")
        print("=" * 50)
        
        self.test_sync_download_all_data()
        self.test_sync_download_with_filters()
        self.test_sync_download_permissions()
        
        # Run sync status tests
        print("\n" + "=" * 50)
        print("SYNC STATUS TESTS")
        print("=" * 50)
        
        self.test_sync_status_device()
        self.test_sync_status_never_synced()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['success']])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   - {result['test']}: {result['details']}")
        
        print("\n" + "=" * 80)
        
        # Return success status
        return failed_tests == 0

if __name__ == "__main__":
    tester = SalesManagerSyncTester()
    success = tester.run_all_tests()
    
    if success:
        print("🎉 ALL TESTS PASSED! Phase 7 Synchronisation is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the details above.")