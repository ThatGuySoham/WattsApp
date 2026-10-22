"""Pydantic request models (validation at the API boundary)."""
from datetime import date

from pydantic import BaseModel, Field, field_validator


class ApplianceCreate(BaseModel):
    appliance_name: str = Field(min_length=2, max_length=80)
    category: str = Field(min_length=2, max_length=40)
    power_rating_watts: int = Field(gt=0, le=10000)
    age_years: int = Field(ge=0, le=40)
    is_smart: bool = False

    @field_validator("appliance_name", "category")
    @classmethod
    def strip(cls, v: str) -> str:
        return v.strip()


class UsageLogCreate(BaseModel):
    date: date
    hours_used: float = Field(ge=0, le=24)


class UsageOverride(BaseModel):
    appliance_id: str
    hours_per_day: float = Field(ge=0, le=24)


class PredictRequest(BaseModel):
    household_id: str
    days: int = Field(default=30, ge=1, le=120)
    usage_patterns: list[UsageOverride] = Field(
        default_factory=list,
        description="Optional current usage patterns; appliances not listed use learned weekday habits.",
    )
    include_bill: bool = True
