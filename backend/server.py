from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from bson import ObjectId

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# JWT settings
SECRET_KEY = os.getenv("SECRET_KEY", "sales-manager-secret-key-2025")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Create the main app without a prefix
app = FastAPI(title="Sales Manager API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ================================
# Models
# ================================

class UserRole:
    ADMIN = "admin"
    MANAGER = "gérant" 
    SERVER = "serveur"

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    email: EmailStr
    password: str
    role: str = UserRole.SERVER
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str = UserRole.SERVER
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    name: str
    created_at: datetime
    is_active: bool

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class Category(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    name: str
    code: str
    category_id: str
    purchase_price: float
    selling_price: float
    stock: int = 0
    image: Optional[str] = None  # base64 image
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ProductCreate(BaseModel):
    name: str
    code: str
    category_id: str
    purchase_price: float
    selling_price: float
    stock: int = 0
    image: Optional[str] = None

class Sale(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    sale_number: str  # Unique sale number
    user_id: str  # Seller
    status: str = "pending"  # pending, on_hold, completed
    total_amount: float = 0.0
    payment_status: str = "pending"  # pending, paid, partial
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

class SaleItem(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    sale_id: str
    product_id: str
    quantity: int
    unit_price: float
    total_price: float

class PaymentMethod(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    name: str
    is_active: bool = True

class Payment(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    sale_id: str
    payment_method_id: str
    amount: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Supplier(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

class SupplierCreate(BaseModel):
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None

class Purchase(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    purchase_number: str  # Unique purchase number
    supplier_id: str
    invoice_number: str
    purchase_date: datetime = Field(default_factory=datetime.utcnow)
    total_amount: float = 0.0
    user_id: str  # Who recorded the purchase
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PurchaseCreate(BaseModel):
    supplier_id: str
    invoice_number: str
    purchase_date: Optional[datetime] = None
    notes: Optional[str] = None

class PurchaseItem(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    purchase_id: str
    product_id: str
    quantity: int
    unit_cost: float
    total_cost: float

class PurchaseItemCreate(BaseModel):
    product_id: str
    quantity: int
    unit_cost: float

class Debt(BaseModel):
    id: str = Field(default_factory=lambda: str(ObjectId()))
    sale_id: str
    debtor_name: str
    seller_name: str
    amount: float
    date: datetime = Field(default_factory=datetime.utcnow)
    is_settled: bool = False

# ================================
# Security Functions
# ================================

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise credentials_exception
    
    user["id"] = str(user["_id"])
    del user["_id"]
    return UserResponse(**user)

# ================================
# Authentication Routes
# ================================

@api_router.post("/auth/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    hashed_password = get_password_hash(user_data.password)
    
    # Create user
    user = User(
        email=user_data.email,
        password=hashed_password,
        role=user_data.role,
        name=user_data.name
    )
    
    user_dict = user.dict()
    user_dict["_id"] = ObjectId(user_dict["id"])
    del user_dict["id"]
    
    result = await db.users.insert_one(user_dict)
    user_dict["id"] = str(result.inserted_id)
    del user_dict["_id"]
    del user_dict["password"]
    
    return UserResponse(**user_dict)

@api_router.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not verify_password(user_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user["_id"])}, expires_delta=access_token_expires
    )
    
    user["id"] = str(user["_id"])
    del user["_id"]
    del user["password"]
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(**user)
    )

@api_router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(get_current_user)):
    return current_user

# ================================
# Categories Routes
# ================================

@api_router.get("/categories", response_model=List[Category])
async def get_categories(current_user: UserResponse = Depends(get_current_user)):
    categories = await db.categories.find().to_list(1000)
    for category in categories:
        category["id"] = str(category["_id"])
        del category["_id"]
    return [Category(**category) for category in categories]

@api_router.post("/categories", response_model=Category)
async def create_category(category_data: CategoryCreate, current_user: UserResponse = Depends(get_current_user)):
    category = Category(**category_data.dict())
    category_dict = category.dict()
    category_dict["_id"] = ObjectId(category_dict["id"])
    del category_dict["id"]
    
    result = await db.categories.insert_one(category_dict)
    category_dict["id"] = str(result.inserted_id)
    del category_dict["_id"]
    
    return Category(**category_dict)

# ================================
# Products Routes
# ================================

@api_router.get("/products", response_model=List[Product])
async def get_products(
    category_id: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user)
):
    query = {}
    if category_id:
        query["category_id"] = category_id
    
    products = await db.products.find(query).to_list(1000)
    for product in products:
        product["id"] = str(product["_id"])
        del product["_id"]
    return [Product(**product) for product in products]

@api_router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str, current_user: UserResponse = Depends(get_current_user)):
    try:
        product = await db.products.find_one({"_id": ObjectId(product_id)})
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        product["id"] = str(product["_id"])
        del product["_id"]
        return Product(**product)
    except Exception as e:
        if "not a valid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid product ID")
        raise HTTPException(status_code=400, detail="Invalid product ID")

@api_router.post("/products", response_model=Product)
async def create_product(
    product_data: ProductCreate, 
    current_user: UserResponse = Depends(get_current_user)
):
    # Check if user has permission (admin or manager)
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if category exists
    try:
        category = await db.categories.find_one({"_id": ObjectId(product_data.category_id)})
        if not category:
            raise HTTPException(status_code=400, detail="Category not found")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid category ID")
    
    # Check if product code already exists
    existing_product = await db.products.find_one({"code": product_data.code})
    if existing_product:
        raise HTTPException(status_code=400, detail="Product code already exists")
    
    product = Product(**product_data.dict())
    product_dict = product.dict()
    product_dict["_id"] = ObjectId(product_dict["id"])
    del product_dict["id"]
    
    result = await db.products.insert_one(product_dict)
    product_dict["id"] = str(result.inserted_id)
    del product_dict["_id"]
    
    return Product(**product_dict)

@api_router.put("/products/{product_id}", response_model=Product)
async def update_product(
    product_id: str,
    product_data: ProductCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    # Check if user has permission (admin or manager)
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Check if product exists
        existing_product = await db.products.find_one({"_id": ObjectId(product_id)})
        if not existing_product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Check if category exists
        try:
            category = await db.categories.find_one({"_id": ObjectId(product_data.category_id)})
            if not category:
                raise HTTPException(status_code=400, detail="Category not found")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid category ID")
        
        # Check if new code conflicts with another product
        code_conflict = await db.products.find_one({
            "code": product_data.code, 
            "_id": {"$ne": ObjectId(product_id)}
        })
        if code_conflict:
            raise HTTPException(status_code=400, detail="Product code already exists")
        
        # Update product
        update_data = product_data.dict()
        update_data["updated_at"] = datetime.utcnow()
        
        await db.products.update_one(
            {"_id": ObjectId(product_id)}, 
            {"$set": update_data}
        )
        
        # Return updated product
        updated_product = await db.products.find_one({"_id": ObjectId(product_id)})
        updated_product["id"] = str(updated_product["_id"])
        del updated_product["_id"]
        
        return Product(**updated_product)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        if "not a valid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid product ID")
        raise HTTPException(status_code=400, detail="Invalid product ID")

@api_router.delete("/products/{product_id}")
async def delete_product(
    product_id: str, 
    current_user: UserResponse = Depends(get_current_user)
):
    # Check if user has permission (admin or manager)
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        result = await db.products.delete_one({"_id": ObjectId(product_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Product not found")
        
        return {"message": "Product deleted successfully"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        if "not a valid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid product ID")
        raise HTTPException(status_code=400, detail="Invalid product ID")

@api_router.patch("/products/{product_id}/stock")
async def update_product_stock(
    product_id: str,
    stock_data: dict,
    current_user: UserResponse = Depends(get_current_user)
):
    # Check if user has permission (admin or manager)
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        new_stock = stock_data.get("stock")
        if new_stock is None or new_stock < 0:
            raise HTTPException(status_code=400, detail="Invalid stock value")
        
        result = await db.products.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": {"stock": new_stock, "updated_at": datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Return updated product
        updated_product = await db.products.find_one({"_id": ObjectId(product_id)})
        updated_product["id"] = str(updated_product["_id"])
        del updated_product["_id"]
        
        return Product(**updated_product)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        if "not a valid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid product ID")
        raise HTTPException(status_code=400, detail="Invalid product ID")

# ================================
# Categories Routes (Complete CRUD)
# ================================

@api_router.put("/categories/{category_id}", response_model=Category)
async def update_category(
    category_id: str,
    category_data: CategoryCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    # Check if user has permission (admin or manager)
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        result = await db.categories.update_one(
            {"_id": ObjectId(category_id)},
            {"$set": category_data.dict()}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Category not found")
        
        # Return updated category
        updated_category = await db.categories.find_one({"_id": ObjectId(category_id)})
        updated_category["id"] = str(updated_category["_id"])
        del updated_category["_id"]
        
        return Category(**updated_category)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        if "not a valid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid category ID")
        raise HTTPException(status_code=400, detail="Invalid category ID")

@api_router.delete("/categories/{category_id}")
async def delete_category(
    category_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    # Check if user has permission (admin or manager)
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Check if category has products
        products_count = await db.products.count_documents({"category_id": category_id})
        if products_count > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete category. It has {products_count} products."
            )
        
        result = await db.categories.delete_one({"_id": ObjectId(category_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Category not found")
        
        return {"message": "Category deleted successfully"}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        if "not a valid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid category ID")
        raise HTTPException(status_code=400, detail="Invalid category ID")

# ================================
# Sales and Cart Routes
# ================================

@api_router.post("/sales/generate-number")
async def generate_sale_number(current_user: UserResponse = Depends(get_current_user)):
    """Generate unique sale number"""
    import time
    timestamp = str(int(time.time() * 1000))[-8:]  # Last 8 digits of timestamp
    sale_number = f"VTE{timestamp}"
    
    # Ensure uniqueness
    while await db.sales.find_one({"sale_number": sale_number}):
        time.sleep(0.001)
        timestamp = str(int(time.time() * 1000))[-8:]
        sale_number = f"VTE{timestamp}"
    
    return {"sale_number": sale_number}

@api_router.post("/sales", response_model=Sale)
async def create_sale(current_user: UserResponse = Depends(get_current_user)):
    """Create new sale with generated number"""
    # Generate unique sale number
    number_response = await generate_sale_number(current_user)
    sale_number = number_response["sale_number"]
    
    sale = Sale(
        sale_number=sale_number,
        user_id=current_user.id,
        status="pending",
        total_amount=0.0,
        payment_status="pending"
    )
    
    sale_dict = sale.dict()
    sale_dict["_id"] = ObjectId(sale_dict["id"])
    del sale_dict["id"]
    
    result = await db.sales.insert_one(sale_dict)
    sale_dict["id"] = str(result.inserted_id)
    del sale_dict["_id"]
    
    return Sale(**sale_dict)

@api_router.get("/sales/pending", response_model=List[Sale])
async def get_pending_sales(current_user: UserResponse = Depends(get_current_user)):
    """Get all pending and on_hold sales"""
    sales = await db.sales.find({
        "status": {"$in": ["pending", "on_hold"]}
    }).sort("created_at", -1).to_list(100)
    
    for sale in sales:
        sale["id"] = str(sale["_id"])
        del sale["_id"]
    
    return [Sale(**sale) for sale in sales]

@api_router.get("/sales/history")
async def get_sales_history(
    current_user: UserResponse = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0
):
    """Get sales history with pagination"""
    try:
        # Get completed sales with pagination
        sales = await db.sales.find(
            {"status": "completed"}
        ).sort("completed_at", -1).skip(offset).limit(limit).to_list(limit)
        
        result = []
        for sale in sales:
            try:
                # Ensure we have the correct sale_id format
                sale_id = str(sale["_id"]) if "_id" in sale else sale.get("id", "")
                
                # Get sale items count
                items_count = await db.sale_items.count_documents({"sale_id": sale_id})
                
                # Get payments
                payments = await db.payments.find({"sale_id": sale_id}).to_list(100)
                payment_methods = []
                
                for payment in payments:
                    try:
                        method = await db.payment_methods.find_one({"_id": ObjectId(payment["payment_method_id"])})
                        if method:
                            payment_methods.append({
                                "method_name": method["name"],
                                "amount": payment["amount"]
                            })
                    except Exception as e:
                        print(f"Error processing payment method {payment.get('payment_method_id')}: {e}")
                        continue
                
                sale_data = {
                    "id": sale_id,
                    "sale_number": sale["sale_number"],
                    "total_amount": sale["total_amount"],
                    "payment_status": sale.get("payment_status", "paid"),
                    "completed_at": sale.get("completed_at"),
                    "created_at": sale["created_at"],
                    "items_count": items_count,
                    "payment_methods": payment_methods
                }
                result.append(sale_data)
            except Exception as e:
                print(f"Error processing sale {sale.get('_id', 'unknown')}: {e}")
                continue
        
        return result
        
    except Exception as e:
        print(f"Sales history error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error fetching sales history: {str(e)}")

@api_router.get("/sales/{sale_id}", response_model=Sale)
async def get_sale(sale_id: str, current_user: UserResponse = Depends(get_current_user)):
    """Get specific sale"""
    try:
        sale = await db.sales.find_one({"_id": ObjectId(sale_id)})
        if not sale:
            raise HTTPException(status_code=404, detail="Sale not found")
        
        sale["id"] = str(sale["_id"])
        del sale["_id"]
        return Sale(**sale)
    except Exception as e:
        if "not a valid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid sale ID")
        raise HTTPException(status_code=400, detail="Invalid sale ID")

@api_router.patch("/sales/{sale_id}/status")
async def update_sale_status(
    sale_id: str,
    status_data: dict,
    current_user: UserResponse = Depends(get_current_user)
):
    """Update sale status"""
    try:
        new_status = status_data.get("status")
        if new_status not in ["pending", "on_hold", "completed"]:
            raise HTTPException(status_code=400, detail="Invalid status")
        
        update_data = {"status": new_status}
        if new_status == "completed":
            update_data["completed_at"] = datetime.utcnow()
        
        result = await db.sales.update_one(
            {"_id": ObjectId(sale_id)},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Sale not found")
        
        # Return updated sale
        updated_sale = await db.sales.find_one({"_id": ObjectId(sale_id)})
        updated_sale["id"] = str(updated_sale["_id"])
        del updated_sale["_id"]
        
        return Sale(**updated_sale)
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        if "not a valid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid sale ID")
        raise HTTPException(status_code=400, detail="Invalid sale ID")

# ================================
# Sale Items Routes (Cart Management)
# ================================

@api_router.get("/sales/{sale_id}/items", response_model=List[dict])
async def get_sale_items(sale_id: str, current_user: UserResponse = Depends(get_current_user)):
    """Get all items in a sale (cart)"""
    try:
        # Verify sale exists
        sale = await db.sales.find_one({"_id": ObjectId(sale_id)})
        if not sale:
            raise HTTPException(status_code=404, detail="Sale not found")
        
        # Get sale items
        sale_items = await db.sale_items.find({"sale_id": sale_id}).to_list(100)
        
        # Get product details for each item
        result_items = []
        for item in sale_items:
            try:
                product = await db.products.find_one({"_id": ObjectId(item["product_id"])})
                if product:
                    result_item = {
                        "id": str(item["_id"]),
                        "sale_id": item["sale_id"],
                        "product_id": item["product_id"],
                        "quantity": item["quantity"],
                        "unit_price": item["unit_price"],
                        "total_price": item["total_price"],
                        "product_name": product["name"],
                        "product_code": product["code"],
                        "product_image": product.get("image"),
                        "available_stock": product["stock"]
                    }
                    result_items.append(result_item)
            except Exception as e:
                print(f"Error processing item {item.get('_id')}: {e}")
                continue
        
        return result_items
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        if "not a valid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid sale ID")
        raise HTTPException(status_code=400, detail="Invalid sale ID")

@api_router.post("/sales/{sale_id}/items")
async def add_item_to_sale(
    sale_id: str,
    item_data: dict,
    current_user: UserResponse = Depends(get_current_user)
):
    """Add item to sale (cart)"""
    try:
        product_id = item_data.get("product_id")
        quantity = item_data.get("quantity", 1)
        
        if not product_id or quantity <= 0:
            raise HTTPException(status_code=400, detail="Invalid product or quantity")
        
        # Verify sale exists and is editable
        sale = await db.sales.find_one({"_id": ObjectId(sale_id)})
        if not sale:
            raise HTTPException(status_code=404, detail="Sale not found")
        
        if sale["status"] == "completed":
            raise HTTPException(status_code=400, detail="Cannot modify completed sale")
        
        # Get product details and check stock
        try:
            product = await db.products.find_one({"_id": ObjectId(product_id)})
            if not product:
                raise HTTPException(status_code=404, detail="Product not found")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid product ID")
        
        if product["stock"] < quantity:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient stock. Available: {product['stock']}"
            )
        
        # Check if item already exists in sale
        existing_item = await db.sale_items.find_one({
            "sale_id": sale_id,
            "product_id": product_id
        })
        
        if existing_item:
            # Update existing item
            new_quantity = existing_item["quantity"] + quantity
            if product["stock"] < new_quantity:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Insufficient stock. Available: {product['stock']}"
                )
            
            new_total = new_quantity * product["selling_price"]
            
            await db.sale_items.update_one(
                {"_id": existing_item["_id"]},
                {"$set": {
                    "quantity": new_quantity,
                    "total_price": new_total
                }}
            )
            
            item_dict = {
                "id": str(existing_item["_id"]),
                "sale_id": sale_id,
                "product_id": product_id,
                "quantity": new_quantity,
                "unit_price": product["selling_price"],
                "total_price": new_total
            }
        else:
            # Create new item
            sale_item = SaleItem(
                sale_id=sale_id,
                product_id=product_id,
                quantity=quantity,
                unit_price=product["selling_price"],
                total_price=quantity * product["selling_price"]
            )
            
            item_dict = sale_item.dict()
            item_dict["_id"] = ObjectId(item_dict["id"])
            del item_dict["id"]
            
            result = await db.sale_items.insert_one(item_dict)
            item_dict["id"] = str(result.inserted_id)
            del item_dict["_id"]
        
        # Update sale total
        await update_sale_total(sale_id)
        
        return item_dict
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        if "not a valid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid ID")
        raise HTTPException(status_code=400, detail="Error adding item to sale")

@api_router.put("/sales/{sale_id}/items/{item_id}")
async def update_sale_item(
    sale_id: str,
    item_id: str,
    item_data: dict,
    current_user: UserResponse = Depends(get_current_user)
):
    """Update sale item quantity"""
    try:
        new_quantity = item_data.get("quantity")
        if new_quantity is None or new_quantity < 0:
            raise HTTPException(status_code=400, detail="Invalid quantity")
        
        # Get sale item
        sale_item = await db.sale_items.find_one({"_id": ObjectId(item_id)})
        if not sale_item:
            raise HTTPException(status_code=404, detail="Sale item not found")
        
        # Get product to check stock
        product = await db.products.find_one({"_id": ObjectId(sale_item["product_id"])})
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        if new_quantity == 0:
            # Remove item
            await db.sale_items.delete_one({"_id": ObjectId(item_id)})
            await update_sale_total(sale_id)
            return {"message": "Item removed from sale"}
        else:
            # Check stock
            if product["stock"] < new_quantity:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Insufficient stock. Available: {product['stock']}"
                )
            
            # Update item
            new_total = new_quantity * sale_item["unit_price"]
            
            await db.sale_items.update_one(
                {"_id": ObjectId(item_id)},
                {"$set": {
                    "quantity": new_quantity,
                    "total_price": new_total
                }}
            )
            
            await update_sale_total(sale_id)
            
            return {
                "id": item_id,
                "sale_id": sale_id,
                "product_id": sale_item["product_id"],
                "quantity": new_quantity,
                "unit_price": sale_item["unit_price"],
                "total_price": new_total
            }
            
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        if "not a valid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid ID")
        raise HTTPException(status_code=400, detail="Error updating sale item")

@api_router.delete("/sales/{sale_id}/items/{item_id}")
async def remove_sale_item(
    sale_id: str,
    item_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Remove item from sale"""
    try:
        result = await db.sale_items.delete_one({"_id": ObjectId(item_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Sale item not found")
        
        await update_sale_total(sale_id)
        return {"message": "Item removed from sale"}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        if "not a valid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid ID")
        raise HTTPException(status_code=400, detail="Error removing sale item")

# Helper function to update sale total
async def update_sale_total(sale_id: str):
    """Calculate and update sale total amount"""
    try:
        # Calculate total from sale items
        pipeline = [
            {"$match": {"sale_id": sale_id}},
            {"$group": {
                "_id": None,
                "total": {"$sum": "$total_price"}
            }}
        ]
        
        result = list(await db.sale_items.aggregate(pipeline).to_list(1))
        total_amount = result[0]["total"] if result else 0.0
        
        # Update sale
        await db.sales.update_one(
            {"_id": ObjectId(sale_id)},
            {"$set": {"total_amount": total_amount}}
        )
        
        return total_amount
    except Exception as e:
        print(f"Error updating sale total: {e}")
        return 0.0

# ================================
# Payment Methods Routes
# ================================

@api_router.get("/payment-methods", response_model=List[PaymentMethod])
async def get_payment_methods(current_user: UserResponse = Depends(get_current_user)):
    """Get all active payment methods"""
    payment_methods = await db.payment_methods.find({"is_active": True}).to_list(100)
    for method in payment_methods:
        method["id"] = str(method["_id"])
        del method["_id"]
    return [PaymentMethod(**method) for method in payment_methods]

# ================================
# Payment and Finalization Routes
# ================================

class PaymentData(BaseModel):
    payment_method_id: str
    amount: float

class CompletePaymentData(BaseModel):
    payments: List[PaymentData]
    seller_name: str

class DebtData(BaseModel):
    debtor_name: str
    seller_name: str
    amount: float

@api_router.post("/sales/{sale_id}/complete")
async def complete_sale(
    sale_id: str,
    payment_data: CompletePaymentData,
    current_user: UserResponse = Depends(get_current_user)
):
    """Complete sale with payments and update stock"""
    try:
        # Get sale details
        sale = await db.sales.find_one({"_id": ObjectId(sale_id)})
        if not sale:
            raise HTTPException(status_code=404, detail="Sale not found")
        
        if sale["status"] == "completed":
            raise HTTPException(status_code=400, detail="Sale already completed")
        
        # Calculate total payments
        total_payments = sum(payment.amount for payment in payment_data.payments)
        sale_total = sale["total_amount"]
        
        if total_payments > sale_total:
            raise HTTPException(status_code=400, detail="Payment exceeds sale total")
        
        # Process payments
        for payment in payment_data.payments:
            if payment.amount <= 0:
                continue
            
            # Verify payment method exists
            payment_method = await db.payment_methods.find_one({"_id": ObjectId(payment.payment_method_id)})
            if not payment_method:
                raise HTTPException(status_code=400, detail="Invalid payment method")
            
            # Create payment record
            payment_record = Payment(
                sale_id=sale_id,
                payment_method_id=payment.payment_method_id,
                amount=payment.amount
            )
            
            payment_dict = payment_record.dict()
            payment_dict["_id"] = ObjectId(payment_dict["id"])
            del payment_dict["id"]
            
            await db.payments.insert_one(payment_dict)
        
        # Handle remaining amount (debt)
        debt_amount = sale_total - total_payments
        debt_id = None
        
        if debt_amount > 0:
            # This will be handled by separate debt creation endpoint
            # For now, we'll mark as partial payment
            payment_status = "partial"
        else:
            payment_status = "paid"
        
        # Update stock for all items in the sale
        sale_items = await db.sale_items.find({"sale_id": sale_id}).to_list(100)
        
        for item in sale_items:
            # Reduce product stock
            await db.products.update_one(
                {"_id": ObjectId(item["product_id"])},
                {"$inc": {"stock": -item["quantity"]}}
            )
        
        # Mark sale as completed
        await db.sales.update_one(
            {"_id": ObjectId(sale_id)},
            {"$set": {
                "status": "completed",
                "payment_status": payment_status,
                "completed_at": datetime.utcnow()
            }}
        )
        
        # Create sales summary record
        await create_sales_summary(sale_id, payment_data.seller_name)
        
        return {
            "message": "Sale completed successfully",
            "sale_id": sale_id,
            "total_amount": sale_total,
            "paid_amount": total_payments,
            "debt_amount": debt_amount,
            "payment_status": payment_status
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        if "not a valid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid ID")
        raise HTTPException(status_code=400, detail=f"Error completing sale: {str(e)}")

@api_router.post("/sales/{sale_id}/debt")
async def create_debt(
    sale_id: str,
    debt_data: DebtData,
    current_user: UserResponse = Depends(get_current_user)
):
    """Create debt record for partial payment"""
    try:
        # Verify sale exists
        sale = await db.sales.find_one({"_id": ObjectId(sale_id)})
        if not sale:
            raise HTTPException(status_code=404, detail="Sale not found")
        
        # Create debt record
        debt = Debt(
            sale_id=sale_id,
            debtor_name=debt_data.debtor_name,
            seller_name=debt_data.seller_name,
            amount=debt_data.amount
        )
        
        debt_dict = debt.dict()
        debt_dict["_id"] = ObjectId(debt_dict["id"])
        del debt_dict["id"]
        
        result = await db.debts.insert_one(debt_dict)
        debt_dict["id"] = str(result.inserted_id)
        del debt_dict["_id"]
        
        return Debt(**debt_dict)
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        if "not a valid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid sale ID")
        raise HTTPException(status_code=400, detail="Error creating debt")

async def create_sales_summary(sale_id: str, seller_name: str):
    """Create sales summary record"""
    try:
        # Get sale details
        sale = await db.sales.find_one({"_id": ObjectId(sale_id)})
        if not sale:
            return
        
        # Get payment methods used
        payments = await db.payments.find({"sale_id": sale_id}).to_list(100)
        
        payment_methods = []
        for payment in payments:
            method = await db.payment_methods.find_one({"_id": ObjectId(payment["payment_method_id"])})
            if method:
                payment_methods.append({
                    "method_name": method["name"],
                    "amount": payment["amount"]
                })
        
        # Create summary record
        summary = {
            "_id": ObjectId(),
            "sale_number": sale["sale_number"],
            "sale_id": sale_id,
            "total_amount": sale["total_amount"],
            "payment_methods": payment_methods,
            "sale_date": sale["completed_at"] or datetime.utcnow(),
            "seller_name": seller_name,
            "created_at": datetime.utcnow()
        }
        
        await db.sales_summaries.insert_one(summary)
        
    except Exception as e:
        print(f"Error creating sales summary: {e}")

# ================================
# Suppliers Routes
# ================================

@api_router.get("/suppliers", response_model=List[Supplier])
async def get_suppliers(current_user: UserResponse = Depends(get_current_user)):
    """Get all active suppliers"""
    # Check if user has permission (admin or manager)
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    suppliers = await db.suppliers.find({"is_active": True}).sort("name", 1).to_list(1000)
    for supplier in suppliers:
        supplier["id"] = str(supplier["_id"])
        del supplier["_id"]
    return [Supplier(**supplier) for supplier in suppliers]

@api_router.post("/suppliers", response_model=Supplier)
async def create_supplier(
    supplier_data: SupplierCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Create new supplier"""
    # Check if user has permission (admin or manager)
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if supplier name already exists
    existing_supplier = await db.suppliers.find_one({"name": supplier_data.name})
    if existing_supplier:
        raise HTTPException(status_code=400, detail="Supplier name already exists")
    
    supplier = Supplier(**supplier_data.dict())
    supplier_dict = supplier.dict()
    supplier_dict["_id"] = ObjectId(supplier_dict["id"])
    del supplier_dict["id"]
    
    result = await db.suppliers.insert_one(supplier_dict)
    supplier_dict["id"] = str(result.inserted_id)
    del supplier_dict["_id"]
    
    return Supplier(**supplier_dict)

@api_router.put("/suppliers/{supplier_id}", response_model=Supplier)
async def update_supplier(
    supplier_id: str,
    supplier_data: SupplierCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Update supplier"""
    # Check if user has permission (admin or manager)
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Check if supplier name conflicts with another supplier
        existing_supplier = await db.suppliers.find_one({
            "name": supplier_data.name,
            "_id": {"$ne": ObjectId(supplier_id)}
        })
        if existing_supplier:
            raise HTTPException(status_code=400, detail="Supplier name already exists")
        
        result = await db.suppliers.update_one(
            {"_id": ObjectId(supplier_id)},
            {"$set": supplier_data.dict()}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Supplier not found")
        
        # Return updated supplier
        updated_supplier = await db.suppliers.find_one({"_id": ObjectId(supplier_id)})
        updated_supplier["id"] = str(updated_supplier["_id"])
        del updated_supplier["_id"]
        
        return Supplier(**updated_supplier)
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        if "not a valid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid supplier ID")
        raise HTTPException(status_code=400, detail="Error updating supplier")

@api_router.delete("/suppliers/{supplier_id}")
async def delete_supplier(
    supplier_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Deactivate supplier"""
    # Check if user has permission (admin or manager)
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        result = await db.suppliers.update_one(
            {"_id": ObjectId(supplier_id)},
            {"$set": {"is_active": False}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Supplier not found")
        
        return {"message": "Supplier deactivated successfully"}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        if "not a valid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid supplier ID")
        raise HTTPException(status_code=400, detail="Error deleting supplier")

# ================================
# Purchase Routes
# ================================

@api_router.post("/purchases/generate-number")
async def generate_purchase_number(current_user: UserResponse = Depends(get_current_user)):
    """Generate unique purchase number"""
    # Check if user has permission (admin or manager)
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    import time
    timestamp = str(int(time.time() * 1000))[-8:]  # Last 8 digits of timestamp
    purchase_number = f"ACH{timestamp}"
    
    # Ensure uniqueness
    while await db.purchases.find_one({"purchase_number": purchase_number}):
        time.sleep(0.001)
        timestamp = str(int(time.time() * 1000))[-8:]
        purchase_number = f"ACH{timestamp}"
    
    return {"purchase_number": purchase_number}

@api_router.post("/purchases", response_model=Purchase)
async def create_purchase(
    purchase_data: PurchaseCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Create new purchase"""
    # Check if user has permission (admin or manager)
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Verify supplier exists
        supplier = await db.suppliers.find_one({"_id": ObjectId(purchase_data.supplier_id)})
        if not supplier:
            raise HTTPException(status_code=400, detail="Supplier not found")
        
        # Generate unique purchase number
        number_response = await generate_purchase_number(current_user)
        purchase_number = number_response["purchase_number"]
        
        purchase = Purchase(
            purchase_number=purchase_number,
            supplier_id=purchase_data.supplier_id,
            invoice_number=purchase_data.invoice_number,
            purchase_date=purchase_data.purchase_date or datetime.utcnow(),
            user_id=current_user.id,
            notes=purchase_data.notes
        )
        
        purchase_dict = purchase.dict()
        purchase_dict["_id"] = ObjectId(purchase_dict["id"])
        del purchase_dict["id"]
        
        result = await db.purchases.insert_one(purchase_dict)
        purchase_dict["id"] = str(result.inserted_id)
        del purchase_dict["_id"]
        
        return Purchase(**purchase_dict)
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        if "not a valid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid supplier ID")
        raise HTTPException(status_code=400, detail="Error creating purchase")

@api_router.get("/purchases", response_model=List[dict])
async def get_purchases(
    current_user: UserResponse = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0
):
    """Get purchases with supplier details"""
    # Check if user has permission (admin or manager)
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        purchases = await db.purchases.find().sort("purchase_date", -1).skip(offset).limit(limit).to_list(limit)
        
        result = []
        for purchase in purchases:
            try:
                # Get supplier details
                supplier = await db.suppliers.find_one({"_id": ObjectId(purchase["supplier_id"])})
                
                # Get purchase items count and total
                items_count = await db.purchase_items.count_documents({"purchase_id": str(purchase["_id"])})
                
                purchase_data = {
                    "id": str(purchase["_id"]),
                    "purchase_number": purchase["purchase_number"],
                    "supplier_name": supplier["name"] if supplier else "Fournisseur inconnu",
                    "invoice_number": purchase["invoice_number"],
                    "purchase_date": purchase["purchase_date"],
                    "total_amount": purchase["total_amount"],
                    "items_count": items_count,
                    "notes": purchase.get("notes"),
                    "created_at": purchase["created_at"]
                }
                result.append(purchase_data)
            except Exception as e:
                print(f"Error processing purchase {purchase.get('_id')}: {e}")
                continue
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching purchases: {str(e)}")

@api_router.get("/purchases/{purchase_id}", response_model=Purchase)
async def get_purchase(
    purchase_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get specific purchase"""
    # Check if user has permission (admin or manager)
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        purchase = await db.purchases.find_one({"_id": ObjectId(purchase_id)})
        if not purchase:
            raise HTTPException(status_code=404, detail="Purchase not found")
        
        purchase["id"] = str(purchase["_id"])
        del purchase["_id"]
        return Purchase(**purchase)
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        if "not a valid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid purchase ID")
        raise HTTPException(status_code=400, detail="Error retrieving purchase")

# ================================
# Purchase Items Routes
# ================================

@api_router.get("/purchases/{purchase_id}/items", response_model=List[dict])
async def get_purchase_items(
    purchase_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get all items in a purchase"""
    # Check if user has permission (admin or manager)
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Verify purchase exists
        purchase = await db.purchases.find_one({"_id": ObjectId(purchase_id)})
        if not purchase:
            raise HTTPException(status_code=404, detail="Purchase not found")
        
        # Get purchase items with product details
        purchase_items = await db.purchase_items.find({"purchase_id": purchase_id}).to_list(100)
        
        result_items = []
        for item in purchase_items:
            try:
                product = await db.products.find_one({"_id": ObjectId(item["product_id"])})
                if product:
                    result_item = {
                        "id": str(item["_id"]),
                        "purchase_id": item["purchase_id"],
                        "product_id": item["product_id"],
                        "quantity": item["quantity"],
                        "unit_cost": item["unit_cost"],
                        "total_cost": item["total_cost"],
                        "product_name": product["name"],
                        "product_code": product["code"],
                        "product_image": product.get("image")
                    }
                    result_items.append(result_item)
            except Exception as e:
                print(f"Error processing purchase item {item.get('_id')}: {e}")
                continue
        
        return result_items
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        if "not a valid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid purchase ID")
        raise HTTPException(status_code=400, detail="Error retrieving purchase items")

@api_router.post("/purchases/{purchase_id}/items")
async def add_item_to_purchase(
    purchase_id: str,
    item_data: PurchaseItemCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Add item to purchase"""
    # Check if user has permission (admin or manager)
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Verify purchase exists
        purchase = await db.purchases.find_one({"_id": ObjectId(purchase_id)})
        if not purchase:
            raise HTTPException(status_code=404, detail="Purchase not found")
        
        # Verify product exists
        product = await db.products.find_one({"_id": ObjectId(item_data.product_id)})
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Check if item already exists in purchase
        existing_item = await db.purchase_items.find_one({
            "purchase_id": purchase_id,
            "product_id": item_data.product_id
        })
        
        if existing_item:
            # Update existing item
            new_quantity = existing_item["quantity"] + item_data.quantity
            new_total = new_quantity * item_data.unit_cost
            
            await db.purchase_items.update_one(
                {"_id": existing_item["_id"]},
                {"$set": {
                    "quantity": new_quantity,
                    "unit_cost": item_data.unit_cost,  # Update unit cost
                    "total_cost": new_total
                }}
            )
            
            item_dict = {
                "id": str(existing_item["_id"]),
                "purchase_id": purchase_id,
                "product_id": item_data.product_id,
                "quantity": new_quantity,
                "unit_cost": item_data.unit_cost,
                "total_cost": new_total
            }
        else:
            # Create new item
            purchase_item = PurchaseItem(
                purchase_id=purchase_id,
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                unit_cost=item_data.unit_cost,
                total_cost=item_data.quantity * item_data.unit_cost
            )
            
            item_dict = purchase_item.dict()
            item_dict["_id"] = ObjectId(item_dict["id"])
            del item_dict["id"]
            
            result = await db.purchase_items.insert_one(item_dict)
            item_dict["id"] = str(result.inserted_id)
            del item_dict["_id"]
        
        # Update purchase total
        await update_purchase_total(purchase_id)
        
        return item_dict
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        if "not a valid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid ID")
        raise HTTPException(status_code=400, detail="Error adding item to purchase")

@api_router.post("/purchases/{purchase_id}/finalize")
async def finalize_purchase(
    purchase_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Finalize purchase and update product stocks"""
    # Check if user has permission (admin or manager)
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        # Get purchase items
        purchase_items = await db.purchase_items.find({"purchase_id": purchase_id}).to_list(100)
        
        if not purchase_items:
            raise HTTPException(status_code=400, detail="No items in purchase")
        
        # Update stock for all items in the purchase
        for item in purchase_items:
            # Increase product stock
            await db.products.update_one(
                {"_id": ObjectId(item["product_id"])},
                {"$inc": {"stock": item["quantity"]}}
            )
        
        # Update purchase total if not already done
        await update_purchase_total(purchase_id)
        
        return {
            "message": "Purchase finalized successfully",
            "purchase_id": purchase_id,
            "items_processed": len(purchase_items)
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        if "not a valid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid purchase ID")
        raise HTTPException(status_code=400, detail=f"Error finalizing purchase: {str(e)}")

# Helper function to update purchase total
async def update_purchase_total(purchase_id: str):
    """Calculate and update purchase total amount"""
    try:
        # Calculate total from purchase items
        pipeline = [
            {"$match": {"purchase_id": purchase_id}},
            {"$group": {
                "_id": None,
                "total": {"$sum": "$total_cost"}
            }}
        ]
        
        result = list(await db.purchase_items.aggregate(pipeline).to_list(1))
        total_amount = result[0]["total"] if result else 0.0
        
        # Update purchase
        await db.purchases.update_one(
            {"_id": ObjectId(purchase_id)},
            {"$set": {"total_amount": total_amount}}
        )
        
        return total_amount
    except Exception as e:
        print(f"Error updating purchase total: {e}")
        return 0.0

# ================================
# Debt Management Routes
# ================================

@api_router.get("/debts")
async def get_debts(
    current_user: UserResponse = Depends(get_current_user),
    is_settled: Optional[bool] = None
):
    """Get debt records"""
    try:
        query = {}
        if is_settled is not None:
            query["is_settled"] = is_settled
        
        debts = await db.debts.find(query).sort("date", -1).to_list(100)
        
        result = []
        for debt in debts:
            debt_data = {
                "id": str(debt["_id"]),
                "sale_id": debt["sale_id"],
                "debtor_name": debt["debtor_name"],
                "seller_name": debt["seller_name"],
                "amount": debt["amount"],
                "date": debt["date"],
                "is_settled": debt["is_settled"]
            }
            
            # Get sale number if available
            try:
                sale = await db.sales.find_one({"_id": ObjectId(debt["sale_id"])})
                if sale:
                    debt_data["sale_number"] = sale["sale_number"]
            except:
                pass
            
            result.append(debt_data)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching debts: {str(e)}")

@api_router.patch("/debts/{debt_id}/settle")
async def settle_debt(
    debt_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Mark debt as settled"""
    try:
        result = await db.debts.update_one(
            {"_id": ObjectId(debt_id)},
            {"$set": {"is_settled": True}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Debt not found")
        
        return {"message": "Debt marked as settled"}
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        if "not a valid ObjectId" in str(e):
            raise HTTPException(status_code=400, detail="Invalid debt ID")
        raise HTTPException(status_code=400, detail="Error settling debt")

# ================================
# Initial Setup Routes
# ================================

@api_router.post("/setup/init")
async def initialize_app():
    """Initialize app with default data"""
    
    # Create default admin user if not exists
    admin_exists = await db.users.find_one({"email": "admin@salesmanager.com"})
    if not admin_exists:
        admin_user = User(
            email="admin@salesmanager.com",
            password=get_password_hash("admin123"),
            role=UserRole.ADMIN,
            name="Administrateur"
        )
        admin_dict = admin_user.dict()
        admin_dict["_id"] = ObjectId(admin_dict["id"])
        del admin_dict["id"]
        await db.users.insert_one(admin_dict)
    
    # Create default categories if not exist
    categories_count = await db.categories.count_documents({})
    if categories_count == 0:
        default_categories = [
            {"name": "Boissons", "description": "Boissons diverses"},
            {"name": "Alimentaire", "description": "Produits alimentaires"},
            {"name": "Hygiène", "description": "Produits d'hygiène"}
        ]
        
        for cat_data in default_categories:
            category = Category(**cat_data)
            category_dict = category.dict()
            category_dict["_id"] = ObjectId(category_dict["id"])
            del category_dict["id"]
            await db.categories.insert_one(category_dict)
    
    # Create default payment methods
    payment_methods_count = await db.payment_methods.count_documents({})
    if payment_methods_count == 0:
        default_payment_methods = [
            {"name": "Espèces"},
            {"name": "Carte bancaire"},
            {"name": "Mobile Money"},
            {"name": "Chèque"}
        ]
        
        for pm_data in default_payment_methods:
            payment_method = PaymentMethod(**pm_data)
            pm_dict = payment_method.dict()
            pm_dict["_id"] = ObjectId(pm_dict["id"])
            del pm_dict["id"]
            await db.payment_methods.insert_one(pm_dict)
    
    return {"message": "Application initialized successfully"}

@api_router.get("/")
async def root():
    return {"message": "Sales Manager API v1.0", "status": "running"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()