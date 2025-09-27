#!/usr/bin/env python3
"""
Backend Test Suite for Phase 6 - Reports and Analytics
Sales Management Application

Tests all Phase 6 features:
1. Sales Summary Reports with filters
2. Purchase Summary Reports with filters (admin/manager only)
3. Dashboard Statistics
4. Stock Status Reports
5. Permission validations
6. Filter functionality
"""

import requests
import json
from datetime import datetime, timedelta
import time
import sys

# Configuration
BASE_URL = "https://sales-manager-25.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@salesmanager.com"
ADMIN_PASSWORD = "admin123"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.ENDC}")

def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.ENDC}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.ENDC}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.ENDC}")

def print_header(message):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print(f"  {message}")
    print(f"{'='*60}{Colors.ENDC}")

class BackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.admin_token = None
        self.server_token = None
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'total': 0
        }
        
    def assert_test(self, condition, test_name, error_msg=""):
        """Assert test condition and track results"""
        self.test_results['total'] += 1
        if condition:
            self.test_results['passed'] += 1
            print_success(f"{test_name}")
            return True
        else:
            self.test_results['failed'] += 1
            print_error(f"{test_name} - {error_msg}")
            return False

    def login_admin(self):
        """Login as admin user"""
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            })
            
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data["access_token"]
                print_success("Admin login successful")
                return True
            else:
                print_error(f"Admin login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print_error(f"Admin login error: {str(e)}")
            return False

    def create_server_user(self):
        """Create a server user for permission testing"""
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.post(f"{BASE_URL}/auth/register", 
                json={
                    "email": "serveur@test.com",
                    "password": "server123",
                    "role": "serveur",
                    "name": "Serveur Test"
                },
                headers=headers
            )
            
            if response.status_code == 200:
                # Login as server
                login_response = self.session.post(f"{BASE_URL}/auth/login", json={
                    "email": "serveur@test.com",
                    "password": "server123"
                })
                
                if login_response.status_code == 200:
                    data = login_response.json()
                    self.server_token = data["access_token"]
                    print_success("Server user created and logged in")
                    return True
            
            print_warning("Server user might already exist, trying to login")
            # Try to login with existing server user
            login_response = self.session.post(f"{BASE_URL}/auth/login", json={
                "email": "serveur@test.com",
                "password": "server123"
            })
            
            if login_response.status_code == 200:
                data = login_response.json()
                self.server_token = data["access_token"]
                print_success("Server user login successful")
                return True
            
            return False
        except Exception as e:
            print_error(f"Server user creation error: {str(e)}")
            return False

    def setup_test_data(self):
        """Setup test data for reports testing"""
        print_info("Setting up test data for reports...")
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Initialize app (creates default categories and payment methods)
            init_response = self.session.post(f"{BASE_URL}/setup/init")
            
            # Get categories and payment methods
            categories_response = self.session.get(f"{BASE_URL}/categories", headers=headers)
            payment_methods_response = self.session.get(f"{BASE_URL}/payment-methods", headers=headers)
            
            if categories_response.status_code != 200 or payment_methods_response.status_code != 200:
                print_error("Failed to get categories or payment methods")
                return False
            
            categories = categories_response.json()
            payment_methods = payment_methods_response.json()
            
            if not categories or not payment_methods:
                print_error("No categories or payment methods found")
                return False
            
            # Create test products
            test_products = [
                {
                    "name": "Coca Cola 33cl",
                    "code": "COCA33",
                    "category_id": categories[0]["id"],
                    "purchase_price": 150.0,
                    "selling_price": 200.0,
                    "stock": 50
                },
                {
                    "name": "Pain de mie",
                    "code": "PAIN01",
                    "category_id": categories[1]["id"],
                    "purchase_price": 300.0,
                    "selling_price": 400.0,
                    "stock": 2  # Low stock
                },
                {
                    "name": "Savon Lux",
                    "code": "SAVON01",
                    "category_id": categories[2]["id"],
                    "purchase_price": 250.0,
                    "selling_price": 350.0,
                    "stock": 0  # Out of stock
                }
            ]
            
            created_products = []
            for product_data in test_products:
                response = self.session.post(f"{BASE_URL}/products", 
                    json=product_data, headers=headers)
                if response.status_code == 200:
                    created_products.append(response.json())
                elif response.status_code == 400 and "already exists" in response.text:
                    # Product already exists, get it
                    products_response = self.session.get(f"{BASE_URL}/products", headers=headers)
                    if products_response.status_code == 200:
                        products = products_response.json()
                        for product in products:
                            if product["code"] == product_data["code"]:
                                created_products.append(product)
                                break
            
            if len(created_products) < 2:
                print_error("Failed to create enough test products")
                return False
            
            # Create test supplier
            supplier_response = self.session.post(f"{BASE_URL}/suppliers", 
                json={
                    "name": "Fournisseur Test",
                    "contact_person": "Jean Dupont",
                    "phone": "+225 01 02 03 04",
                    "email": "contact@fournisseur.com"
                }, headers=headers)
            
            supplier_id = None
            if supplier_response.status_code == 200:
                supplier_id = supplier_response.json()["id"]
            elif supplier_response.status_code == 400 and "already exists" in supplier_response.text:
                # Get existing supplier
                suppliers_response = self.session.get(f"{BASE_URL}/suppliers", headers=headers)
                if suppliers_response.status_code == 200:
                    suppliers = suppliers_response.json()
                    for supplier in suppliers:
                        if supplier["name"] == "Fournisseur Test":
                            supplier_id = supplier["id"]
                            break
            
            if not supplier_id:
                print_error("Failed to create test supplier")
                return False
            
            # Create test sales with different scenarios
            self.create_test_sales(created_products, payment_methods, headers)
            
            # Create test purchases
            self.create_test_purchases(supplier_id, created_products, headers)
            
            print_success("Test data setup completed")
            return True
            
        except Exception as e:
            print_error(f"Test data setup error: {str(e)}")
            return False

    def create_test_sales(self, products, payment_methods, headers):
        """Create test sales for different scenarios"""
        try:
            # Create sales from different time periods
            today = datetime.now()
            last_month = today - timedelta(days=35)
            
            # Sale 1: This month - Cash payment
            sale1_response = self.session.post(f"{BASE_URL}/sales", headers=headers)
            if sale1_response.status_code == 200:
                sale1 = sale1_response.json()
                
                # Add items to sale
                self.session.post(f"{BASE_URL}/sales/{sale1['id']}/items", 
                    json={"product_id": products[0]["id"], "quantity": 2}, headers=headers)
                
                # Complete sale with cash payment
                self.session.post(f"{BASE_URL}/sales/{sale1['id']}/complete", 
                    json={
                        "payments": [{"payment_method_id": payment_methods[0]["id"], "amount": 400.0}],
                        "seller_name": "Vendeur Test"
                    }, headers=headers)
            
            # Sale 2: This month - Mixed payment (Card + Cash)
            sale2_response = self.session.post(f"{BASE_URL}/sales", headers=headers)
            if sale2_response.status_code == 200:
                sale2 = sale2_response.json()
                
                # Add items to sale
                self.session.post(f"{BASE_URL}/sales/{sale2['id']}/items", 
                    json={"product_id": products[1]["id"], "quantity": 1}, headers=headers)
                
                # Complete sale with mixed payment
                self.session.post(f"{BASE_URL}/sales/{sale2['id']}/complete", 
                    json={
                        "payments": [
                            {"payment_method_id": payment_methods[0]["id"], "amount": 200.0},
                            {"payment_method_id": payment_methods[1]["id"], "amount": 200.0}
                        ],
                        "seller_name": "Autre Vendeur"
                    }, headers=headers)
            
            # Sale 3: Partial payment with debt
            sale3_response = self.session.post(f"{BASE_URL}/sales", headers=headers)
            if sale3_response.status_code == 200:
                sale3 = sale3_response.json()
                
                # Add items to sale
                self.session.post(f"{BASE_URL}/sales/{sale3['id']}/items", 
                    json={"product_id": products[0]["id"], "quantity": 3}, headers=headers)
                
                # Complete sale with partial payment
                self.session.post(f"{BASE_URL}/sales/{sale3['id']}/complete", 
                    json={
                        "payments": [{"payment_method_id": payment_methods[2]["id"], "amount": 400.0}],
                        "seller_name": "Vendeur Test"
                    }, headers=headers)
                
                # Create debt for remaining amount
                self.session.post(f"{BASE_URL}/sales/{sale3['id']}/debt", 
                    json={
                        "debtor_name": "Client Débiteur",
                        "seller_name": "Vendeur Test",
                        "amount": 200.0
                    }, headers=headers)
            
        except Exception as e:
            print_warning(f"Error creating test sales: {str(e)}")

    def create_test_purchases(self, supplier_id, products, headers):
        """Create test purchases"""
        try:
            # Create purchase
            purchase_response = self.session.post(f"{BASE_URL}/purchases", 
                json={
                    "supplier_id": supplier_id,
                    "invoice_number": "INV-2025-001",
                    "notes": "Achat test pour rapports"
                }, headers=headers)
            
            if purchase_response.status_code == 200:
                purchase = purchase_response.json()
                
                # Add items to purchase
                self.session.post(f"{BASE_URL}/purchases/{purchase['id']}/items", 
                    json={
                        "product_id": products[0]["id"],
                        "quantity": 20,
                        "unit_cost": 140.0
                    }, headers=headers)
                
                # Finalize purchase
                self.session.post(f"{BASE_URL}/purchases/{purchase['id']}/finalize", headers=headers)
            
        except Exception as e:
            print_warning(f"Error creating test purchases: {str(e)}")

    def test_sales_summary_basic(self):
        """Test basic sales summary endpoint"""
        print_header("Testing Sales Summary - Basic Functionality")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        try:
            response = self.session.get(f"{BASE_URL}/reports/sales-summary", headers=headers)
            
            self.assert_test(
                response.status_code == 200,
                "Sales summary endpoint accessible",
                f"Status: {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                self.assert_test(
                    "sales" in data and "statistics" in data,
                    "Sales summary has correct structure",
                    "Missing 'sales' or 'statistics' keys"
                )
                
                if "statistics" in data:
                    stats = data["statistics"]
                    required_stats = ["total_sales", "total_amount", "average_sale", "payment_methods", "sellers"]
                    
                    for stat in required_stats:
                        self.assert_test(
                            stat in stats,
                            f"Statistics contains {stat}",
                            f"Missing {stat} in statistics"
                        )
                
                # Check if we have sales data
                if "sales" in data and len(data["sales"]) > 0:
                    sale = data["sales"][0]
                    required_fields = ["sale_number", "date", "seller_name", "total_amount", "payment_status", "payment_methods"]
                    
                    for field in required_fields:
                        self.assert_test(
                            field in sale,
                            f"Sale record contains {field}",
                            f"Missing {field} in sale record"
                        )
                    
                    print_success(f"Found {len(data['sales'])} sales in summary")
                    print_success(f"Total amount: {stats.get('total_amount', 0)}")
                else:
                    print_warning("No sales data found in summary")
            
        except Exception as e:
            self.assert_test(False, "Sales summary basic test", str(e))

    def test_sales_summary_filters(self):
        """Test sales summary with filters"""
        print_header("Testing Sales Summary - Filters")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        try:
            # Test date range filter
            today = datetime.now()
            start_date = (today - timedelta(days=7)).isoformat()
            end_date = today.isoformat()
            
            response = self.session.get(
                f"{BASE_URL}/reports/sales-summary",
                params={"start_date": start_date, "end_date": end_date},
                headers=headers
            )
            
            self.assert_test(
                response.status_code == 200,
                "Sales summary with date filter",
                f"Status: {response.status_code}"
            )
            
            # Test seller name filter
            response = self.session.get(
                f"{BASE_URL}/reports/sales-summary",
                params={"seller_name": "Vendeur Test"},
                headers=headers
            )
            
            self.assert_test(
                response.status_code == 200,
                "Sales summary with seller filter",
                f"Status: {response.status_code}"
            )
            
            # Test payment method filter
            response = self.session.get(
                f"{BASE_URL}/reports/sales-summary",
                params={"payment_method": "Espèces"},
                headers=headers
            )
            
            self.assert_test(
                response.status_code == 200,
                "Sales summary with payment method filter",
                f"Status: {response.status_code}"
            )
            
            # Test combined filters
            response = self.session.get(
                f"{BASE_URL}/reports/sales-summary",
                params={
                    "start_date": start_date,
                    "seller_name": "Vendeur",
                    "payment_method": "Espèces"
                },
                headers=headers
            )
            
            self.assert_test(
                response.status_code == 200,
                "Sales summary with combined filters",
                f"Status: {response.status_code}"
            )
            
        except Exception as e:
            self.assert_test(False, "Sales summary filters test", str(e))

    def test_purchases_summary_admin(self):
        """Test purchases summary with admin permissions"""
        print_header("Testing Purchases Summary - Admin Access")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        try:
            response = self.session.get(f"{BASE_URL}/reports/purchases-summary", headers=headers)
            
            self.assert_test(
                response.status_code == 200,
                "Purchases summary accessible by admin",
                f"Status: {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                self.assert_test(
                    "purchases" in data and "statistics" in data,
                    "Purchases summary has correct structure",
                    "Missing 'purchases' or 'statistics' keys"
                )
                
                if "statistics" in data:
                    stats = data["statistics"]
                    required_stats = ["total_purchases", "total_amount", "average_purchase", "suppliers"]
                    
                    for stat in required_stats:
                        self.assert_test(
                            stat in stats,
                            f"Purchase statistics contains {stat}",
                            f"Missing {stat} in statistics"
                        )
                
                print_success(f"Found {len(data.get('purchases', []))} purchases in summary")
            
        except Exception as e:
            self.assert_test(False, "Purchases summary admin test", str(e))

    def test_purchases_summary_server_denied(self):
        """Test purchases summary denied for server role"""
        print_header("Testing Purchases Summary - Server Access Denied")
        
        if not self.server_token:
            print_warning("Server token not available, skipping permission test")
            return
        
        headers = {"Authorization": f"Bearer {self.server_token}"}
        
        try:
            response = self.session.get(f"{BASE_URL}/reports/purchases-summary", headers=headers)
            
            self.assert_test(
                response.status_code == 403,
                "Purchases summary denied for server role",
                f"Expected 403, got {response.status_code}"
            )
            
        except Exception as e:
            self.assert_test(False, "Purchases summary permission test", str(e))

    def test_purchases_summary_filters(self):
        """Test purchases summary with filters"""
        print_header("Testing Purchases Summary - Filters")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        try:
            # Test date range filter
            today = datetime.now()
            start_date = (today - timedelta(days=30)).isoformat()
            end_date = today.isoformat()
            
            response = self.session.get(
                f"{BASE_URL}/reports/purchases-summary",
                params={"start_date": start_date, "end_date": end_date},
                headers=headers
            )
            
            self.assert_test(
                response.status_code == 200,
                "Purchases summary with date filter",
                f"Status: {response.status_code}"
            )
            
            # Test supplier name filter
            response = self.session.get(
                f"{BASE_URL}/reports/purchases-summary",
                params={"supplier_name": "Fournisseur Test"},
                headers=headers
            )
            
            self.assert_test(
                response.status_code == 200,
                "Purchases summary with supplier filter",
                f"Status: {response.status_code}"
            )
            
        except Exception as e:
            self.assert_test(False, "Purchases summary filters test", str(e))

    def test_dashboard_stats(self):
        """Test dashboard statistics endpoint"""
        print_header("Testing Dashboard Statistics")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        try:
            response = self.session.get(f"{BASE_URL}/reports/dashboard", headers=headers)
            
            self.assert_test(
                response.status_code == 200,
                "Dashboard endpoint accessible",
                f"Status: {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check main sections
                required_sections = ["sales", "products", "debts"]
                for section in required_sections:
                    self.assert_test(
                        section in data,
                        f"Dashboard contains {section} section",
                        f"Missing {section} section"
                    )
                
                # Check sales statistics
                if "sales" in data:
                    sales = data["sales"]
                    sales_fields = ["total_sales", "sales_this_month", "sales_amount_this_month", 
                                  "sales_amount_last_month", "sales_growth_percentage"]
                    
                    for field in sales_fields:
                        self.assert_test(
                            field in sales,
                            f"Sales section contains {field}",
                            f"Missing {field} in sales"
                        )
                
                # Check products statistics
                if "products" in data:
                    products = data["products"]
                    products_fields = ["total_products", "low_stock_products", "out_of_stock_products", "top_products"]
                    
                    for field in products_fields:
                        self.assert_test(
                            field in products,
                            f"Products section contains {field}",
                            f"Missing {field} in products"
                        )
                
                # Check debts statistics
                if "debts" in data:
                    debts = data["debts"]
                    debts_fields = ["total_unsettled_debts", "total_debt_amount"]
                    
                    for field in debts_fields:
                        self.assert_test(
                            field in debts,
                            f"Debts section contains {field}",
                            f"Missing {field} in debts"
                        )
                
                # Check if purchases section exists for admin
                self.assert_test(
                    "purchases" in data,
                    "Dashboard contains purchases section for admin",
                    "Missing purchases section for admin user"
                )
                
                print_success(f"Total products: {data.get('products', {}).get('total_products', 0)}")
                print_success(f"Low stock products: {data.get('products', {}).get('low_stock_products', 0)}")
                print_success(f"Out of stock products: {data.get('products', {}).get('out_of_stock_products', 0)}")
                print_success(f"Total sales: {data.get('sales', {}).get('total_sales', 0)}")
                print_success(f"Sales this month: {data.get('sales', {}).get('sales_this_month', 0)}")
            
        except Exception as e:
            self.assert_test(False, "Dashboard statistics test", str(e))

    def test_dashboard_server_permissions(self):
        """Test dashboard with server permissions (should not show purchases)"""
        print_header("Testing Dashboard - Server Permissions")
        
        if not self.server_token:
            print_warning("Server token not available, skipping permission test")
            return
        
        headers = {"Authorization": f"Bearer {self.server_token}"}
        
        try:
            response = self.session.get(f"{BASE_URL}/reports/dashboard", headers=headers)
            
            self.assert_test(
                response.status_code == 200,
                "Dashboard accessible by server role",
                f"Status: {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Server should NOT see purchases section
                self.assert_test(
                    "purchases" not in data,
                    "Dashboard hides purchases section from server role",
                    "Purchases section visible to server role"
                )
                
                # But should see other sections
                self.assert_test(
                    "sales" in data and "products" in data and "debts" in data,
                    "Dashboard shows allowed sections to server role",
                    "Missing allowed sections for server role"
                )
            
        except Exception as e:
            self.assert_test(False, "Dashboard server permissions test", str(e))

    def test_stock_status_report(self):
        """Test stock status report endpoint"""
        print_header("Testing Stock Status Report")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        try:
            response = self.session.get(f"{BASE_URL}/reports/stock-status", headers=headers)
            
            self.assert_test(
                response.status_code == 200,
                "Stock status endpoint accessible",
                f"Status: {response.status_code}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check response structure
                self.assert_test(
                    "products" in data and "summary" in data,
                    "Stock status has correct structure",
                    "Missing 'products' or 'summary' keys"
                )
                
                # Check summary statistics
                if "summary" in data:
                    summary = data["summary"]
                    summary_fields = ["total_products", "total_stock_value", "out_of_stock_count", 
                                    "low_stock_count", "normal_stock_count"]
                    
                    for field in summary_fields:
                        self.assert_test(
                            field in summary,
                            f"Stock summary contains {field}",
                            f"Missing {field} in summary"
                        )
                
                # Check product records
                if "products" in data and len(data["products"]) > 0:
                    product = data["products"][0]
                    product_fields = ["id", "name", "code", "category", "stock", "purchase_price", 
                                    "selling_price", "stock_value", "stock_status"]
                    
                    for field in product_fields:
                        self.assert_test(
                            field in product,
                            f"Product record contains {field}",
                            f"Missing {field} in product record"
                        )
                    
                    # Check stock status values
                    stock_statuses = [p["stock_status"] for p in data["products"]]
                    valid_statuses = ["Normal", "Faible", "Rupture"]
                    
                    self.assert_test(
                        all(status in valid_statuses for status in stock_statuses),
                        "All products have valid stock status",
                        f"Invalid stock statuses found: {set(stock_statuses) - set(valid_statuses)}"
                    )
                    
                    print_success(f"Found {len(data['products'])} products in stock report")
                    print_success(f"Total stock value: {summary.get('total_stock_value', 0)}")
                    print_success(f"Out of stock: {summary.get('out_of_stock_count', 0)}")
                    print_success(f"Low stock: {summary.get('low_stock_count', 0)}")
                    print_success(f"Normal stock: {summary.get('normal_stock_count', 0)}")
                else:
                    print_warning("No products found in stock report")
            
        except Exception as e:
            self.assert_test(False, "Stock status report test", str(e))

    def test_debts_endpoint(self):
        """Test debts management endpoint"""
        print_header("Testing Debts Management")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        try:
            # Test get all debts
            response = self.session.get(f"{BASE_URL}/debts", headers=headers)
            
            self.assert_test(
                response.status_code == 200,
                "Debts endpoint accessible",
                f"Status: {response.status_code}"
            )
            
            if response.status_code == 200:
                debts = response.json()
                
                if len(debts) > 0:
                    debt = debts[0]
                    debt_fields = ["id", "sale_id", "debtor_name", "seller_name", "amount", "date", "is_settled"]
                    
                    for field in debt_fields:
                        self.assert_test(
                            field in debt,
                            f"Debt record contains {field}",
                            f"Missing {field} in debt record"
                        )
                    
                    print_success(f"Found {len(debts)} debt records")
                else:
                    print_info("No debt records found")
            
            # Test filter by settlement status
            response = self.session.get(f"{BASE_URL}/debts", 
                params={"is_settled": False}, headers=headers)
            
            self.assert_test(
                response.status_code == 200,
                "Debts endpoint with filter",
                f"Status: {response.status_code}"
            )
            
        except Exception as e:
            self.assert_test(False, "Debts endpoint test", str(e))

    def test_reports_data_consistency(self):
        """Test data consistency across different reports"""
        print_header("Testing Reports Data Consistency")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        try:
            # Get data from different endpoints
            dashboard_response = self.session.get(f"{BASE_URL}/reports/dashboard", headers=headers)
            stock_response = self.session.get(f"{BASE_URL}/reports/stock-status", headers=headers)
            sales_response = self.session.get(f"{BASE_URL}/reports/sales-summary", headers=headers)
            
            if all(r.status_code == 200 for r in [dashboard_response, stock_response, sales_response]):
                dashboard_data = dashboard_response.json()
                stock_data = stock_response.json()
                sales_data = sales_response.json()
                
                # Check product count consistency
                dashboard_products = dashboard_data.get("products", {}).get("total_products", 0)
                stock_products = stock_data.get("summary", {}).get("total_products", 0)
                
                self.assert_test(
                    dashboard_products == stock_products,
                    "Product count consistent between dashboard and stock report",
                    f"Dashboard: {dashboard_products}, Stock: {stock_products}"
                )
                
                # Check sales count consistency
                dashboard_sales = dashboard_data.get("sales", {}).get("total_sales", 0)
                sales_count = sales_data.get("statistics", {}).get("total_sales", 0)
                
                self.assert_test(
                    dashboard_sales == sales_count,
                    "Sales count consistent between dashboard and sales summary",
                    f"Dashboard: {dashboard_sales}, Sales: {sales_count}"
                )
                
                # Check stock status counts
                dashboard_low_stock = dashboard_data.get("products", {}).get("low_stock_products", 0)
                dashboard_out_stock = dashboard_data.get("products", {}).get("out_of_stock_products", 0)
                
                stock_low_stock = stock_data.get("summary", {}).get("low_stock_count", 0)
                stock_out_stock = stock_data.get("summary", {}).get("out_of_stock_count", 0)
                
                self.assert_test(
                    dashboard_low_stock == stock_low_stock,
                    "Low stock count consistent between dashboard and stock report",
                    f"Dashboard: {dashboard_low_stock}, Stock: {stock_low_stock}"
                )
                
                self.assert_test(
                    dashboard_out_stock == stock_out_stock,
                    "Out of stock count consistent between dashboard and stock report",
                    f"Dashboard: {dashboard_out_stock}, Stock: {stock_out_stock}"
                )
                
            else:
                self.assert_test(False, "Data consistency test", "Failed to get data from all endpoints")
            
        except Exception as e:
            self.assert_test(False, "Reports data consistency test", str(e))

    def test_error_handling(self):
        """Test error handling in reports endpoints"""
        print_header("Testing Error Handling")
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        try:
            # Test invalid date format
            response = self.session.get(
                f"{BASE_URL}/reports/sales-summary",
                params={"start_date": "invalid-date"},
                headers=headers
            )
            
            # Should either handle gracefully or return appropriate error
            self.assert_test(
                response.status_code in [200, 400],
                "Invalid date format handled appropriately",
                f"Unexpected status: {response.status_code}"
            )
            
            # Test unauthorized access
            response = self.session.get(f"{BASE_URL}/reports/dashboard")
            
            self.assert_test(
                response.status_code == 401,
                "Unauthorized access properly rejected",
                f"Expected 401, got {response.status_code}"
            )
            
        except Exception as e:
            self.assert_test(False, "Error handling test", str(e))

    def run_all_tests(self):
        """Run all Phase 6 tests"""
        print_header("PHASE 6 BACKEND TESTING - REPORTS AND ANALYTICS")
        print_info("Testing all Phase 6 features: Reports, Dashboard, Stock Status, Permissions")
        
        # Setup
        if not self.login_admin():
            print_error("Failed to login as admin. Cannot continue tests.")
            return False
        
        if not self.create_server_user():
            print_warning("Failed to create server user. Permission tests may be limited.")
        
        if not self.setup_test_data():
            print_warning("Failed to setup complete test data. Some tests may have limited data.")
        
        # Run all tests
        self.test_sales_summary_basic()
        self.test_sales_summary_filters()
        self.test_purchases_summary_admin()
        self.test_purchases_summary_server_denied()
        self.test_purchases_summary_filters()
        self.test_dashboard_stats()
        self.test_dashboard_server_permissions()
        self.test_stock_status_report()
        self.test_debts_endpoint()
        self.test_reports_data_consistency()
        self.test_error_handling()
        
        # Print final results
        self.print_final_results()
        
        return self.test_results['failed'] == 0

    def print_final_results(self):
        """Print final test results"""
        print_header("PHASE 6 TEST RESULTS SUMMARY")
        
        total = self.test_results['total']
        passed = self.test_results['passed']
        failed = self.test_results['failed']
        
        print(f"\n{Colors.BOLD}Total Tests: {total}{Colors.ENDC}")
        print(f"{Colors.GREEN}✅ Passed: {passed}{Colors.ENDC}")
        print(f"{Colors.RED}❌ Failed: {failed}{Colors.ENDC}")
        
        if failed == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL PHASE 6 TESTS PASSED! 🎉{Colors.ENDC}")
            print(f"{Colors.GREEN}Phase 6 Reports and Analytics Backend is 100% functional!{Colors.ENDC}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}⚠️  {failed} TEST(S) FAILED{Colors.ENDC}")
            print(f"{Colors.YELLOW}Please review the failed tests above.{Colors.ENDC}")
        
        success_rate = (passed / total * 100) if total > 0 else 0
        print(f"\n{Colors.BLUE}Success Rate: {success_rate:.1f}%{Colors.ENDC}")

if __name__ == "__main__":
    tester = BackendTester()
    success = tester.run_all_tests()
    
    if success:
        print(f"\n{Colors.GREEN}Phase 6 Backend Testing Completed Successfully!{Colors.ENDC}")
        sys.exit(0)
    else:
        print(f"\n{Colors.RED}Phase 6 Backend Testing Completed with Failures!{Colors.ENDC}")
        sys.exit(1)