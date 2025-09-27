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
        
        # Get sale items with product details
        pipeline = [
            {"$match": {"sale_id": sale_id}},
            {"$addFields": {
                "product_object_id": {"$toObjectId": "$product_id"}
            }},
            {"$lookup": {
                "from": "products",
                "localField": "product_object_id", 
                "foreignField": "_id",
                "as": "product"
            }},
            {"$unwind": "$product"},
            {"$project": {
                "id": {"$toString": "$_id"},
                "sale_id": 1,
                "product_id": 1,
                "quantity": 1,
                "unit_price": 1,
                "total_price": 1,
                "product_name": "$product.name",
                "product_code": "$product.code",
                "product_image": "$product.image",
                "available_stock": "$product.stock"
            }}
        ]
        
        items = await db.sale_items.aggregate(pipeline).to_list(100)
        return items
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