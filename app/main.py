from typing import Union
from decimal import Decimal
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

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
