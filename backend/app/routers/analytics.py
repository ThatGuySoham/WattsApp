from uuid import UUID

from fastapi import APIRouter

from app.schemas import PredictRequest
from app.services import analytics

router = APIRouter(tags=["analytics"])


@router.post("/households/{household_id}/train")
def train(household_id: UUID):
    """On-demand retrain of the household's regression model."""
    return analytics.train_household(str(household_id))


@router.get("/households/{household_id}/model")
def model_report(household_id: UUID):
    """Stored coefficients + accuracy diagnostics + actual-vs-predicted points."""
    return analytics.model_report(str(household_id))


@router.post("/predict")
def predict(body: PredictRequest):
    """Forecast consumption for `days` days (default 30) and estimate the bill."""
    overrides = {o.appliance_id: o.hours_per_day for o in body.usage_patterns}
    return analytics.predict(str(UUID(body.household_id)), body.days, overrides, body.include_bill)
