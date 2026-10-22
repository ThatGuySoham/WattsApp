from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.db import repository as repo
from app.schemas import ApplianceCreate, UsageLogCreate

router = APIRouter(tags=["appliances"])


@router.get("/households/{household_id}/appliances")
def list_appliances(household_id: UUID):
    if not repo.get_household(str(household_id)):
        raise HTTPException(status_code=404, detail="Household not found")
    return repo.list_appliances(str(household_id))


@router.post("/households/{household_id}/appliances", status_code=201)
def create_appliance(household_id: UUID, body: ApplianceCreate):
    if not repo.get_household(str(household_id)):
        raise HTTPException(status_code=404, detail="Household not found")
    return repo.create_appliance(str(household_id), body.model_dump())


@router.delete("/appliances/{appliance_id}", status_code=204)
def delete_appliance(appliance_id: UUID):
    if not repo.delete_appliance(str(appliance_id)):
        raise HTTPException(status_code=404, detail="Appliance not found")


@router.post("/appliances/{appliance_id}/usage-logs", status_code=201)
def log_usage(appliance_id: UUID, body: UsageLogCreate):
    appliance = repo.get_appliance(str(appliance_id))
    if not appliance:
        raise HTTPException(status_code=404, detail="Appliance not found")
    return repo.create_usage_log(appliance, body.date, body.hours_used)
