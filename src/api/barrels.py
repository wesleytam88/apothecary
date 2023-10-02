from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver")
def post_deliver_barrels(barrels_delivered: list[Barrel]):
    """ """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory"))

    first_row = result.first()
    num_red_ml = first_row.num_red_ml
    gold = first_row.gold

    for barrel in barrels_delivered:
        match barrel.sku:
            case "SMALL_RED_BARREL":
                num_red_ml += barrel.ml_per_barrel
                gold -= barrel.price
            case _:
                raise ValueError(f"Unknown barrel sku of {barrel.sku}")
        
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_red_ml = {num_red_ml}, gold = {gold} WHERE id = 1"))
    
    print(barrels_delivered)

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory"))

    first_row = result.first()

    for barrel in wholesale_catalog:
        match barrel.sku:
            case "SMALL_RED_BARREL":
                barrel_price = barrel.price
            case _:
                raise ValueError(f"Unknown sku of {barrel.sku}")
        if first_row.num_red_potions < 10 and first_row.gold >= barrel_price:
            return [
                {
                    "sku": "SMALL_RED_BARREL",
                    "quantity": 1,
                }
            ]
        else:
            return [
                {
                    "sku": "SMALL_RED_BARREL",
                    "quantity": 0,
                }
            ]
