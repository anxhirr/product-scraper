from pydantic import BaseModel
from typing import List

class Product(BaseModel):
    title: str
    sku: str
    price: str
    description: str
    specifications: str
    images: List[str]
    url: str
