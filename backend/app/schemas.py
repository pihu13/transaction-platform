from decimal import Decimal
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

TransactionType = Literal["CREDIT", "DEBIT"]

class TransactionCreate(BaseModel):
    transaction_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Unique transaction identifier",
    )
    customer_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Customer identifier",
    )
    type: TransactionType
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)

    @field_validator("transaction_id", "customer_id")
    @classmethod
    def validate_id_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be empty")
        if not re.fullmatch(r"^[A-Za-z0-9_-]+$", value):
            raise ValueError("only letters, numbers, underscores and hyphens are allowed")
        return value

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, value):
        if isinstance(value, str):
            return value.strip().upper()
        return value


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