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
# Role-Based Access Control Functions
# ================================

def require_admin(current_user: UserResponse):
    """Require admin role"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

def require_admin_or_manager(current_user: UserResponse):
    """Require admin or manager role"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Manager access required"
        )

def require_any_role(current_user: UserResponse):
    """Allow any authenticated user (admin, manager, or server)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SERVER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Valid user role required"
        )

def can_access_purchases(current_user: UserResponse) -> bool:
    """Check if user can access purchase management"""
    return current_user.role in [UserRole.ADMIN, UserRole.MANAGER]

def can_access_reports(current_user: UserResponse) -> bool:
    """Check if user can access all reports"""
    return current_user.role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SERVER]

def can_manage_users(current_user: UserResponse) -> bool:
    """Check if user can manage other users"""
    return current_user.role == UserRole.ADMIN

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
# Role Management Routes (Admin Only)
# ================================

class UserRoleUpdate(BaseModel):
    role: str

@api_router.get("/users", response_model=List[UserResponse])
async def get_all_users(current_user: UserResponse = Depends(get_current_user)):
    """Get all users (Admin only)"""
    require_admin(current_user)
    
    users = await db.users.find({"is_active": True}).to_list(1000)
    for user in users:
        user["id"] = str(user["_id"])
        del user["_id"]
        del user["password"]
    
    return [UserResponse(**user) for user in users]

@api_router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: str,
    role_data: UserRoleUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Update user role (Admin only)"""
    require_admin(current_user)
    
    # Validate role
    if role_data.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.SERVER]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be admin, gérant, or serveur"
        )
    
    # Check if user exists
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    # Prevent admin from changing their own role
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role"
        )
    
    # Update role
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"role": role_data.role}}
    )
    
    # Return updated user
    updated_user = await db.users.find_one({"_id": ObjectId(user_id)})
    updated_user["id"] = str(updated_user["_id"])
    del updated_user["_id"]
    del updated_user["password"]
    
    return UserResponse(**updated_user)

@api_router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Deactivate user (Admin only)"""
    require_admin(current_user)
    
    # Check if user exists
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    # Prevent admin from deactivating themselves
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    # Deactivate user
    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_active": False}}
    )
    
    return {"message": "User deactivated successfully"}

@api_router.get("/roles")
async def get_available_roles(current_user: UserResponse = Depends(get_current_user)):
    """Get list of available roles"""
    require_any_role(current_user)
    
    return {
        "roles": [
            {"value": UserRole.ADMIN, "label": "Administrateur", "description": "Accès complet à toutes les fonctionnalités"},
            {"value": UserRole.MANAGER, "label": "Gérant", "description": "Accès aux ventes et achats"},
            {"value": UserRole.SERVER, "label": "Serveur", "description": "Accès aux ventes uniquement"}
        ]
    }

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
    # Check permissions
    require_admin_or_manager(current_user)
    
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
    # Check permissions
    require_admin_or_manager(current_user)
    
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
    # Check permissions
    require_admin_or_manager(current_user)
    
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
    # Check permissions
    require_admin_or_manager(current_user)
    
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
    # Check permissions
    require_admin_or_manager(current_user)
    
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
    # Check permissions
    require_admin_or_manager(current_user)
    
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
    # Check permissions
    require_admin_or_manager(current_user)
    
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
    # Check permissions
    require_admin_or_manager(current_user)
    
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
    # Check permissions
    require_admin_or_manager(current_user)
    
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
    # Check permissions
    require_admin_or_manager(current_user)
    
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
    # Check permissions
    require_admin_or_manager(current_user)
    
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
    # Check permissions
    require_admin_or_manager(current_user)
    
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
    # Check permissions
    require_admin_or_manager(current_user)
    
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
    # Check permissions
    require_admin_or_manager(current_user)
    
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
    # Check permissions
    require_admin_or_manager(current_user)
    
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
    # Check permissions
    require_admin_or_manager(current_user)
    
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
    # Check permissions
    require_admin_or_manager(current_user)
    
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
    # Check permissions
    require_admin_or_manager(current_user)
    
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
# Reports and Analytics Routes
# ================================

@api_router.get("/reports/sales-summary")
async def get_sales_summary(
    current_user: UserResponse = Depends(get_current_user),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    seller_name: Optional[str] = None,
    payment_method: Optional[str] = None
):
    """Get sales summary with filters"""
    try:
        # Build query filter
        query = {"status": "completed"}
        
        # Date range filter
        if start_date or end_date:
            date_filter = {}
            if start_date:
                try:
                    date_filter["$gte"] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                except:
                    date_filter["$gte"] = datetime.fromisoformat(start_date)
            if end_date:
                try:
                    date_filter["$lte"] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                except:
                    date_filter["$lte"] = datetime.fromisostring(end_date)
            query["completed_at"] = date_filter
        
        # Get sales data
        sales = await db.sales.find(query).sort("completed_at", -1).to_list(1000)
        
        summary_data = []
        total_amount = 0
        total_sales = 0
        
        for sale in sales:
            try:
                sale_id = str(sale["_id"])
                
                # Get payment methods for this sale
                payments = await db.payments.find({"sale_id": sale_id}).to_list(100)
                payment_methods = []
                
                for payment in payments:
                    method = await db.payment_methods.find_one({"_id": ObjectId(payment["payment_method_id"])})
                    if method:
                        payment_methods.append({
                            "method_name": method["name"],
                            "amount": payment["amount"]
                        })
                
                # Filter by payment method if specified
                if payment_method:
                    has_payment_method = any(pm["method_name"].lower() == payment_method.lower() for pm in payment_methods)
                    if not has_payment_method:
                        continue
                
                # Get seller name from sales_summaries or use user lookup
                seller = "Vendeur inconnu"
                sales_summary = await db.sales_summaries.find_one({"sale_id": sale_id})
                if sales_summary and sales_summary.get("seller_name"):
                    seller = sales_summary["seller_name"]
                else:
                    # Fallback to user lookup
                    user = await db.users.find_one({"_id": ObjectId(sale["user_id"])})
                    if user:
                        seller = user["name"]
                
                # Filter by seller if specified
                if seller_name and seller_name.lower() not in seller.lower():
                    continue
                
                sale_data = {
                    "sale_number": sale["sale_number"],
                    "date": sale["completed_at"].isoformat() if sale.get("completed_at") else sale["created_at"].isoformat(),
                    "seller_name": seller,
                    "total_amount": sale["total_amount"],
                    "payment_status": sale.get("payment_status", "paid"),
                    "payment_methods": payment_methods
                }
                
                summary_data.append(sale_data)
                total_amount += sale["total_amount"]
                total_sales += 1
                
            except Exception as e:
                print(f"Error processing sale {sale.get('_id')}: {e}")
                continue
        
        # Calculate summary statistics
        average_sale = total_amount / total_sales if total_sales > 0 else 0
        
        # Group by payment methods
        payment_method_stats = {}
        for sale in summary_data:
            for pm in sale["payment_methods"]:
                method_name = pm["method_name"]
                if method_name not in payment_method_stats:
                    payment_method_stats[method_name] = {"count": 0, "amount": 0}
                payment_method_stats[method_name]["count"] += 1
                payment_method_stats[method_name]["amount"] += pm["amount"]
        
        # Group by sellers
        seller_stats = {}
        for sale in summary_data:
            seller = sale["seller_name"]
            if seller not in seller_stats:
                seller_stats[seller] = {"count": 0, "amount": 0}
            seller_stats[seller]["count"] += 1
            seller_stats[seller]["amount"] += sale["total_amount"]
        
        return {
            "sales": summary_data,
            "statistics": {
                "total_sales": total_sales,
                "total_amount": total_amount,
                "average_sale": average_sale,
                "payment_methods": payment_method_stats,
                "sellers": seller_stats
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error generating sales summary: {str(e)}")

@api_router.get("/reports/purchases-summary")
async def get_purchases_summary(
    current_user: UserResponse = Depends(get_current_user),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    supplier_name: Optional[str] = None
):
    """Get purchases summary with filters"""
    # Check permissions
    require_admin_or_manager(current_user)
    
    try:
        # Build query filter
        query = {}
        
        # Date range filter
        if start_date or end_date:
            date_filter = {}
            if start_date:
                try:
                    date_filter["$gte"] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                except:
                    date_filter["$gte"] = datetime.fromisoformat(start_date)
            if end_date:
                try:
                    date_filter["$lte"] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                except:
                    date_filter["$lte"] = datetime.fromisoformat(end_date)
            query["purchase_date"] = date_filter
        
        # Get purchases data
        purchases = await db.purchases.find(query).sort("purchase_date", -1).to_list(1000)
        
        summary_data = []
        total_amount = 0
        total_purchases = 0
        
        for purchase in purchases:
            try:
                # Get supplier details
                supplier = await db.suppliers.find_one({"_id": ObjectId(purchase["supplier_id"])})
                supplier_name_actual = supplier["name"] if supplier else "Fournisseur inconnu"
                
                # Filter by supplier if specified
                if supplier_name and supplier_name.lower() not in supplier_name_actual.lower():
                    continue
                
                # Get purchase items count
                items_count = await db.purchase_items.count_documents({"purchase_id": str(purchase["_id"])})
                
                purchase_data = {
                    "purchase_number": purchase["purchase_number"],
                    "date": purchase["purchase_date"].isoformat(),
                    "supplier_name": supplier_name_actual,
                    "invoice_number": purchase["invoice_number"],
                    "total_amount": purchase["total_amount"],
                    "items_count": items_count,
                    "notes": purchase.get("notes")
                }
                
                summary_data.append(purchase_data)
                total_amount += purchase["total_amount"]
                total_purchases += 1
                
            except Exception as e:
                print(f"Error processing purchase {purchase.get('_id')}: {e}")
                continue
        
        # Calculate summary statistics
        average_purchase = total_amount / total_purchases if total_purchases > 0 else 0
        
        # Group by suppliers
        supplier_stats = {}
        for purchase in summary_data:
            supplier = purchase["supplier_name"]
            if supplier not in supplier_stats:
                supplier_stats[supplier] = {"count": 0, "amount": 0}
            supplier_stats[supplier]["count"] += 1
            supplier_stats[supplier]["amount"] += purchase["total_amount"]
        
        return {
            "purchases": summary_data,
            "statistics": {
                "total_purchases": total_purchases,
                "total_amount": total_amount,
                "average_purchase": average_purchase,
                "suppliers": supplier_stats
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error generating purchases summary: {str(e)}")

@api_router.get("/reports/dashboard")
async def get_dashboard_stats(current_user: UserResponse = Depends(get_current_user)):
    """Get dashboard statistics"""
    try:
        # Get date ranges
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        this_month_start = today.replace(day=1)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        
        # Sales statistics
        total_sales = await db.sales.count_documents({"status": "completed"})
        
        # Sales this month
        sales_this_month = await db.sales.find({
            "status": "completed",
            "completed_at": {"$gte": this_month_start}
        }).to_list(1000)
        
        sales_amount_this_month = sum(sale["total_amount"] for sale in sales_this_month)
        
        # Sales last month
        sales_last_month = await db.sales.find({
            "status": "completed", 
            "completed_at": {"$gte": last_month_start, "$lt": this_month_start}
        }).to_list(1000)
        
        sales_amount_last_month = sum(sale["total_amount"] for sale in sales_last_month)
        
        # Products statistics
        total_products = await db.products.count_documents({})
        low_stock_products = await db.products.count_documents({"stock": {"$lte": 5}})
        out_of_stock_products = await db.products.count_documents({"stock": 0})
        
        # Purchases statistics (only for admin/manager)
        purchases_stats = {}
        if current_user.role in [UserRole.ADMIN, UserRole.MANAGER]:
            total_purchases = await db.purchases.count_documents({})
            
            purchases_this_month = await db.purchases.find({
                "purchase_date": {"$gte": this_month_start}
            }).to_list(1000)
            
            purchases_amount_this_month = sum(purchase["total_amount"] for purchase in purchases_this_month)
            
            purchases_stats = {
                "total_purchases": total_purchases,
                "purchases_this_month": len(purchases_this_month),
                "purchases_amount_this_month": purchases_amount_this_month,
                "total_suppliers": await db.suppliers.count_documents({"is_active": True})
            }
        
        # Debts statistics
        total_debts = await db.debts.count_documents({"is_settled": False})
        unsettled_debts = await db.debts.find({"is_settled": False}).to_list(1000)
        total_debt_amount = sum(debt["amount"] for debt in unsettled_debts)
        
        # Top products by sales (this month)
        top_products = []
        if sales_this_month:
            # Get sale items for this month's sales
            sale_ids = [str(sale["_id"]) for sale in sales_this_month]
            
            # Aggregate sale items by product
            pipeline = [
                {"$match": {"sale_id": {"$in": sale_ids}}},
                {"$group": {
                    "_id": "$product_id",
                    "total_quantity": {"$sum": "$quantity"},
                    "total_revenue": {"$sum": "$total_price"}
                }},
                {"$sort": {"total_quantity": -1}},
                {"$limit": 5}
            ]
            
            product_stats = await db.sale_items.aggregate(pipeline).to_list(5)
            
            for stat in product_stats:
                try:
                    product = await db.products.find_one({"_id": ObjectId(stat["_id"])})
                    if product:
                        top_products.append({
                            "product_name": product["name"],
                            "quantity_sold": stat["total_quantity"],
                            "revenue": stat["total_revenue"]
                        })
                except Exception as e:
                    print(f"Error processing top product {stat['_id']}: {e}")
                    continue
        
        # Calculate growth percentages
        sales_growth = 0
        if sales_amount_last_month > 0:
            sales_growth = ((sales_amount_this_month - sales_amount_last_month) / sales_amount_last_month) * 100
        
        dashboard_data = {
            "sales": {
                "total_sales": total_sales,
                "sales_this_month": len(sales_this_month),
                "sales_amount_this_month": sales_amount_this_month,
                "sales_amount_last_month": sales_amount_last_month,
                "sales_growth_percentage": sales_growth
            },
            "products": {
                "total_products": total_products,
                "low_stock_products": low_stock_products,
                "out_of_stock_products": out_of_stock_products,
                "top_products": top_products
            },
            "debts": {
                "total_unsettled_debts": total_debts,
                "total_debt_amount": total_debt_amount
            }
        }
        
        # Add purchases data if user has permission
        if purchases_stats:
            dashboard_data["purchases"] = purchases_stats
        
        return dashboard_data
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error generating dashboard stats: {str(e)}")

@api_router.get("/reports/stock-status")
async def get_stock_status(current_user: UserResponse = Depends(get_current_user)):
    """Get detailed stock status report"""
    try:
        # Get all products with stock information
        products = await db.products.find().sort("stock", 1).to_list(1000)
        
        stock_report = []
        total_value = 0
        
        for product in products:
            try:
                # Get category name
                category = await db.categories.find_one({"_id": ObjectId(product["category_id"])})
                category_name = category["name"] if category else "Non catégorisé"
                
                # Calculate stock value
                stock_value = product["stock"] * product["purchase_price"]
                total_value += stock_value
                
                # Determine stock status
                stock_status = "Normal"
                if product["stock"] == 0:
                    stock_status = "Rupture"
                elif product["stock"] <= 5:
                    stock_status = "Faible"
                
                product_data = {
                    "id": str(product["_id"]),
                    "name": product["name"],
                    "code": product["code"],
                    "category": category_name,
                    "stock": product["stock"],
                    "purchase_price": product["purchase_price"],
                    "selling_price": product["selling_price"],
                    "stock_value": stock_value,
                    "stock_status": stock_status,
                    "image": product.get("image")
                }
                
                stock_report.append(product_data)
                
            except Exception as e:
                print(f"Error processing product {product.get('_id')}: {e}")
                continue
        
        # Calculate summary statistics
        total_products = len(stock_report)
        out_of_stock = len([p for p in stock_report if p["stock_status"] == "Rupture"])
        low_stock = len([p for p in stock_report if p["stock_status"] == "Faible"])
        normal_stock = len([p for p in stock_report if p["stock_status"] == "Normal"])
        
        return {
            "products": stock_report,
            "summary": {
                "total_products": total_products,
                "total_stock_value": total_value,
                "out_of_stock_count": out_of_stock,
                "low_stock_count": low_stock,
                "normal_stock_count": normal_stock
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error generating stock status report: {str(e)}")

# ================================
# Synchronization Routes
# ================================

class SyncData(BaseModel):
    sync_id: str
    data_type: str  # 'sale', 'purchase', 'product', etc.
    action: str  # 'create', 'update', 'delete'
    data: dict
    timestamp: datetime
    device_id: Optional[str] = None

class SyncBatch(BaseModel):
    device_id: str
    sync_items: List[SyncData]

class SyncResponse(BaseModel):
    sync_id: str
    status: str  # 'success', 'conflict', 'error'
    server_data: Optional[dict] = None
    error_message: Optional[str] = None

@api_router.post("/sync/upload")
async def sync_upload_data(
    sync_batch: SyncBatch,
    current_user: UserResponse = Depends(get_current_user)
):
    """Upload and sync data from offline device"""
    try:
        sync_results = []
        
        for sync_item in sync_batch.sync_items:
            try:
                result = await process_sync_item(sync_item, current_user)
                sync_results.append(result)
            except Exception as e:
                sync_results.append(SyncResponse(
                    sync_id=sync_item.sync_id,
                    status="error",
                    error_message=str(e)
                ))
        
        # Store sync batch info
        await store_sync_batch(sync_batch, current_user.id, sync_results)
        
        return {
            "batch_id": sync_batch.device_id,
            "processed_items": len(sync_results),
            "results": sync_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Sync upload error: {str(e)}")

async def process_sync_item(sync_item: SyncData, current_user: UserResponse) -> SyncResponse:
    """Process individual sync item"""
    try:
        if sync_item.data_type == "sale" and sync_item.action == "create":
            return await sync_sale_creation(sync_item, current_user)
        elif sync_item.data_type == "product" and sync_item.action == "update":
            return await sync_product_update(sync_item, current_user)
        elif sync_item.data_type == "purchase" and sync_item.action == "create":
            return await sync_purchase_creation(sync_item, current_user)
        else:
            return SyncResponse(
                sync_id=sync_item.sync_id,
                status="error",
                error_message=f"Unsupported sync type: {sync_item.data_type}.{sync_item.action}"
            )
    except Exception as e:
        return SyncResponse(
            sync_id=sync_item.sync_id,
            status="error",
            error_message=str(e)
        )

async def sync_sale_creation(sync_item: SyncData, current_user: UserResponse) -> SyncResponse:
    """Sync sale creation from offline"""
    try:
        sale_data = sync_item.data
        
        # Check if sale already exists by sync_id or sale_number
        existing_sale = await db.sales.find_one({
            "$or": [
                {"sync_id": sync_item.sync_id},
                {"sale_number": sale_data.get("sale_number")}
            ]
        })
        
        if existing_sale:
            return SyncResponse(
                sync_id=sync_item.sync_id,
                status="conflict",
                server_data={"id": str(existing_sale["_id"]), "sale_number": existing_sale["sale_number"]},
                error_message="Sale already exists"
            )
        
        # Create sale
        sale = Sale(
            sale_number=sale_data["sale_number"],
            user_id=current_user.id,
            status=sale_data.get("status", "completed"),
            total_amount=sale_data["total_amount"],
            payment_status=sale_data.get("payment_status", "paid"),
            created_at=datetime.fromisoformat(sale_data["created_at"]) if sale_data.get("created_at") else datetime.utcnow(),
            completed_at=datetime.fromisoformat(sale_data["completed_at"]) if sale_data.get("completed_at") else datetime.utcnow()
        )
        
        sale_dict = sale.dict()
        sale_dict["_id"] = ObjectId(sale_dict["id"])
        sale_dict["sync_id"] = sync_item.sync_id  # Store sync ID for tracking
        del sale_dict["id"]
        
        result = await db.sales.insert_one(sale_dict)
        sale_id = str(result.inserted_id)
        
        # Create sale items
        if "items" in sale_data:
            for item_data in sale_data["items"]:
                sale_item = SaleItem(
                    sale_id=sale_id,
                    product_id=item_data["product_id"],
                    quantity=item_data["quantity"],
                    unit_price=item_data["unit_price"],
                    total_price=item_data["total_price"]
                )
                
                item_dict = sale_item.dict()
                item_dict["_id"] = ObjectId(item_dict["id"])
                del item_dict["id"]
                
                await db.sale_items.insert_one(item_dict)
                
                # Update product stock
                await db.products.update_one(
                    {"_id": ObjectId(item_data["product_id"])},
                    {"$inc": {"stock": -item_data["quantity"]}}
                )
        
        # Create payments
        if "payments" in sale_data:
            for payment_data in sale_data["payments"]:
                payment = Payment(
                    sale_id=sale_id,
                    payment_method_id=payment_data["payment_method_id"],
                    amount=payment_data["amount"],
                    created_at=datetime.fromisoformat(payment_data["created_at"]) if payment_data.get("created_at") else datetime.utcnow()
                )
                
                payment_dict = payment.dict()
                payment_dict["_id"] = ObjectId(payment_dict["id"])
                del payment_dict["id"]
                
                await db.payments.insert_one(payment_dict)
        
        return SyncResponse(
            sync_id=sync_item.sync_id,
            status="success",
            server_data={"id": sale_id, "sale_number": sale_data["sale_number"]}
        )
        
    except Exception as e:
        return SyncResponse(
            sync_id=sync_item.sync_id,
            status="error",
            error_message=f"Sale sync error: {str(e)}"
        )

async def sync_product_update(sync_item: SyncData, current_user: UserResponse) -> SyncResponse:
    """Sync product update from offline"""
    try:
        product_data = sync_item.data
        product_id = product_data.get("id")
        
        if not product_id:
            return SyncResponse(
                sync_id=sync_item.sync_id,
                status="error",
                error_message="Product ID required for update"
            )
        
        # Check if product exists
        existing_product = await db.products.find_one({"_id": ObjectId(product_id)})
        if not existing_product:
            return SyncResponse(
                sync_id=sync_item.sync_id,
                status="error",
                error_message="Product not found"
            )
        
        # Check for conflicts based on timestamp
        server_updated = existing_product.get("updated_at", existing_product.get("created_at"))
        client_updated = datetime.fromisoformat(product_data.get("updated_at"))
        
        if server_updated and server_updated > client_updated:
            return SyncResponse(
                sync_id=sync_item.sync_id,
                status="conflict",
                server_data={
                    "id": str(existing_product["_id"]),
                    "name": existing_product["name"],
                    "updated_at": server_updated.isoformat()
                },
                error_message="Server version is newer"
            )
        
        # Update product
        update_data = {
            "name": product_data["name"],
            "selling_price": product_data["selling_price"],
            "stock": product_data["stock"],
            "updated_at": datetime.utcnow()
        }
        
        await db.products.update_one(
            {"_id": ObjectId(product_id)},
            {"$set": update_data}
        )
        
        return SyncResponse(
            sync_id=sync_item.sync_id,
            status="success",
            server_data={"id": product_id, "updated_at": update_data["updated_at"].isoformat()}
        )
        
    except Exception as e:
        return SyncResponse(
            sync_id=sync_item.sync_id,
            status="error",
            error_message=f"Product sync error: {str(e)}"
        )

async def sync_purchase_creation(sync_item: SyncData, current_user: UserResponse) -> SyncResponse:
    """Sync purchase creation from offline"""
    try:
        purchase_data = sync_item.data
        
        # Check if purchase already exists
        existing_purchase = await db.purchases.find_one({
            "$or": [
                {"sync_id": sync_item.sync_id},
                {"purchase_number": purchase_data.get("purchase_number")}
            ]
        })
        
        if existing_purchase:
            return SyncResponse(
                sync_id=sync_item.sync_id,
                status="conflict",
                server_data={"id": str(existing_purchase["_id"]), "purchase_number": existing_purchase["purchase_number"]},
                error_message="Purchase already exists"
            )
        
        # Create purchase
        purchase = Purchase(
            purchase_number=purchase_data["purchase_number"],
            supplier_id=purchase_data["supplier_id"],
            invoice_number=purchase_data["invoice_number"],
            purchase_date=datetime.fromisoformat(purchase_data["purchase_date"]) if purchase_data.get("purchase_date") else datetime.utcnow(),
            total_amount=purchase_data["total_amount"],
            user_id=current_user.id,
            notes=purchase_data.get("notes"),
            created_at=datetime.fromisoformat(purchase_data["created_at"]) if purchase_data.get("created_at") else datetime.utcnow()
        )
        
        purchase_dict = purchase.dict()
        purchase_dict["_id"] = ObjectId(purchase_dict["id"])
        purchase_dict["sync_id"] = sync_item.sync_id
        del purchase_dict["id"]
        
        result = await db.purchases.insert_one(purchase_dict)
        purchase_id = str(result.inserted_id)
        
        # Create purchase items and update stock
        if "items" in purchase_data:
            for item_data in purchase_data["items"]:
                purchase_item = PurchaseItem(
                    purchase_id=purchase_id,
                    product_id=item_data["product_id"],
                    quantity=item_data["quantity"],
                    unit_cost=item_data["unit_cost"],
                    total_cost=item_data["total_cost"]
                )
                
                item_dict = purchase_item.dict()
                item_dict["_id"] = ObjectId(item_dict["id"])
                del item_dict["id"]
                
                await db.purchase_items.insert_one(item_dict)
                
                # Update product stock
                await db.products.update_one(
                    {"_id": ObjectId(item_data["product_id"])},
                    {"$inc": {"stock": item_data["quantity"]}}
                )
        
        return SyncResponse(
            sync_id=sync_item.sync_id,
            status="success",
            server_data={"id": purchase_id, "purchase_number": purchase_data["purchase_number"]}
        )
        
    except Exception as e:
        return SyncResponse(
            sync_id=sync_item.sync_id,
            status="error",
            error_message=f"Purchase sync error: {str(e)}"
        )

async def store_sync_batch(sync_batch: SyncBatch, user_id: str, results: List[SyncResponse]):
    """Store sync batch information for audit"""
    try:
        sync_record = {
            "_id": ObjectId(),
            "device_id": sync_batch.device_id,
            "user_id": user_id,
            "sync_timestamp": datetime.utcnow(),
            "items_count": len(sync_batch.sync_items),
            "success_count": len([r for r in results if r.status == "success"]),
            "conflict_count": len([r for r in results if r.status == "conflict"]),
            "error_count": len([r for r in results if r.status == "error"]),
            "results": [r.dict() for r in results]
        }
        
        await db.sync_batches.insert_one(sync_record)
    except Exception as e:
        print(f"Error storing sync batch: {e}")

@api_router.get("/sync/status/{device_id}")
async def get_sync_status(
    device_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get sync status for a device"""
    try:
        # Get latest sync batch for device
        latest_sync = await db.sync_batches.find_one(
            {"device_id": device_id, "user_id": current_user.id},
            sort=[("sync_timestamp", -1)]
        )
        
        if not latest_sync:
            return {
                "device_id": device_id,
                "last_sync": None,
                "status": "never_synced"
            }
        
        return {
            "device_id": device_id,
            "last_sync": latest_sync["sync_timestamp"].isoformat(),
            "items_count": latest_sync["items_count"],
            "success_count": latest_sync["success_count"],
            "conflict_count": latest_sync["conflict_count"],
            "error_count": latest_sync["error_count"],
            "status": "synced" if latest_sync["error_count"] == 0 and latest_sync["conflict_count"] == 0 else "needs_attention"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error getting sync status: {str(e)}")

@api_router.get("/sync/download")
async def sync_download_data(
    current_user: UserResponse = Depends(get_current_user),
    last_sync: Optional[str] = None,
    data_types: Optional[str] = None
):
    """Download updated data for offline sync"""
    try:
        # Parse parameters
        since_date = None
        if last_sync:
            try:
                since_date = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
            except:
                since_date = datetime.fromisoformat(last_sync)
        
        types = data_types.split(',') if data_types else ['products', 'categories', 'payment_methods', 'suppliers']
        
        sync_data = {}
        
        # Get updated products
        if 'products' in types:
            query = {}
            if since_date:
                query["updated_at"] = {"$gt": since_date}
            
            products = await db.products.find(query).to_list(1000)
            sync_data['products'] = []
            
            for product in products:
                product["id"] = str(product["_id"])
                del product["_id"]
                sync_data['products'].append(product)
        
        # Get categories
        if 'categories' in types:
            categories = await db.categories.find().to_list(100)
            sync_data['categories'] = []
            
            for category in categories:
                category["id"] = str(category["_id"])
                del category["_id"]
                sync_data['categories'].append(category)
        
        # Get payment methods
        if 'payment_methods' in types:
            payment_methods = await db.payment_methods.find({"is_active": True}).to_list(100)
            sync_data['payment_methods'] = []
            
            for pm in payment_methods:
                pm["id"] = str(pm["_id"])
                del pm["_id"]
                sync_data['payment_methods'].append(pm)
        
        # Get suppliers (if user has permission)
        if 'suppliers' in types and current_user.role in [UserRole.ADMIN, UserRole.MANAGER]:
            suppliers = await db.suppliers.find({"is_active": True}).to_list(100)
            sync_data['suppliers'] = []
            
            for supplier in suppliers:
                supplier["id"] = str(supplier["_id"])
                del supplier["_id"]
                sync_data['suppliers'].append(supplier)
        
        return {
            "sync_timestamp": datetime.utcnow().isoformat(),
            "data": sync_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Sync download error: {str(e)}")

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