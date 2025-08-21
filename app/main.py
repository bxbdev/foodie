from typing import Union
from decimal import Decimal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 導入聊天路由
from api.v1.chat.endpoints import router as chat_router

app = FastAPI(title="Foodie API", description="美食平台 API", version="1.0.0")

# 添加 CORS 中間件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允許所有來源，生產環境應該指定具體域名
    allow_credentials=True,
    allow_methods=["*"],  # 允許所有 HTTP 方法
    allow_headers=["*"],  # 允許所有標頭
)

# 註冊聊天路由
app.include_router(chat_router, prefix="/api/v1/chat", tags=["聊天"])

class Item(BaseModel):
    name: str
    price: float
    is_offr: Union[bool, None] = None

class Cart(BaseModel):
    name: str
    price: Decimal
    count: int

@app.get('/')
async def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
async def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}

@app.put("/items/{item_id}")
async def update_item(item: Item):
    return {"name": item.name, "price": item.price}

@app.post("/cart")
async def total_price(cart_items: list[Cart]):
    total = sum(item.price * item.count for item in cart_items)
    return {"total": total}
