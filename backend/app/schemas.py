"""ARZON 2.0 schema definitions."""
from pydantic import BaseModel, ConfigDict, Field

class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    store_id: int
    nomi: str
    narxi: float
    kategoriya: str | None = None
    holat_turi: str = "yangi"
    holat_izohi: str | None = None
    porsiya: str | None = None
    tayyorlanish_daq: int | None = None
    stop_list: bool = False
    rasm_url: str | None = None
    rasm_urls: list | None = None
    tavsif: str | None = None
    miqdor: int | None = None

class CheckoutItem(BaseModel):
    product_id: int
    soni: int = Field(ge=1)

class CheckoutRequest(BaseModel):
    items: list[CheckoutItem]
    promo_kod: str | None = None
    yetkazish_turi: str = "kuryer"
    manzil: str | None = None
    lokatsiya_lat: float | None = None
    lokatsiya_lng: float | None = None
    pickup_point_id: int | None = None
