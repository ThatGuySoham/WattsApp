from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.db import repository as repo
from app.services import analytics
from app.services.tariff import load_tariffs

router = APIRouter(tags=["households"])


@router.get("/households")
def list_households():
    return repo.list_households()


@router.get("/households/{household_id}")
def get_household(household_id: UUID):
    hh = repo.get_household(str(household_id))
    if not hh:
        raise HTTPException(status_code=404, detail="Household not found")
    return hh


@router.get("/households/{household_id}/usage-history")
def usage_history(household_id: UUID, days: int = Query(30, ge=1, le=365)):
    return analytics.history(str(household_id), days)


@router.get("/tariffs")
def tariffs():
    return load_tariffs()
