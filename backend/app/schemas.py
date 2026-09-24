from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

TransactionType = Literal["CREDIT", "DEBIT"]

##validation

class TransactionCreate(BaseModel):
    transaction_id: str = Field(min_length=1, max_length=64)
    customer_id: str = Field(min_length=1, max_length=64)
    type: TransactionType
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    customer_id: str
    type: str
    amount: Decimal
    status: str
    attempts: int
    failure_reason: str | None


class BalanceResponse(BaseModel):
    customer_id: str
    balance: Decimal


class HealthResponse(BaseModel):
    status: str
    database: str
    workers: int


class TransactionPage(BaseModel):
    items: list[TransactionResponse]
    page: int
    page_size: int
    total: int
