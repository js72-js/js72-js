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

class UserRole(str):
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