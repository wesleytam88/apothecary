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
        gold = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory")).first().gold
        red_pot_row = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory where id = 1")).first()
        green_pot_row = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory where id = 2")).first()
        blue_pot_row = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory where id = 3")).first()

    red_ml = red_pot_row.ml
    green_ml = green_pot_row.ml
    blue_ml = blue_pot_row.ml

    for barrel in barrels_delivered:
        match barrel.potion_type:
            case [1, 0, 0, 0]:
                red_ml += barrel.quantity * barrel.ml_per_barrel
            case [0, 1, 0, 0]:
                green_ml += barrel.quantity * barrel.ml_per_barrel
            case [0, 0, 1, 0]:
                blue_ml += barrel.quantity * barrel.ml_per_barrel
            case _:
                raise ValueError(f"potion type of {barrel.potion_type} not found")
        gold -= barrel.price * barrel.quantity
        
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(f"UPDATE potion_inventory SET ml = {red_ml} WHERE id = 1"))
        connection.execute(sqlalchemy.text(f"UPDATE potion_inventory SET ml = {green_ml} WHERE id = 2"))
        connection.execute(sqlalchemy.text(f"UPDATE potion_inventory SET ml = {blue_ml} WHERE id = 3"))
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET gold = {gold} WHERE id = 1"))
    
    print(barrels_delivered)

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    with db.engine.begin() as connection:
        gold = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory")).first().gold
        red_pot_row = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory where id = 1")).first()
        green_pot_row = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory where id = 2")).first()
        blue_pot_row = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory where id = 3")).first()

    # Barrel order logic
    order_list = []
    small_red_barrel = get_barrel(wholesale_catalog, "SMALL_RED_BARREL")
    small_green_barrel = get_barrel(wholesale_catalog, "SMALL_GREEN_BARREL")
    small_blue_barrel = get_barrel(wholesale_catalog, "SMALL_BLUE_BARREL")

    if red_pot_row.quantity < 10 and gold >= small_red_barrel.price and small_red_barrel.quantity > 0:
        order_list.append({
            "sku": small_red_barrel.sku,
            "ml_per_barrel": small_red_barrel.ml_per_barrel,
            "potion_type": small_red_barrel.potion_type,
            "price": small_red_barrel.price,
            "quantity": 1
        })
        gold -= small_red_barrel.price
    if green_pot_row.quantity < 10 and gold >= small_green_barrel.price and small_green_barrel.quantity > 0:
        order_list.append({
            "sku": small_green_barrel.sku,
            "ml_per_barrel": small_green_barrel.ml_per_barrel,
            "potion_type": small_green_barrel.potion_type,
            "price": small_green_barrel.price,
            "quantity": 1
        })
        gold -= small_green_barrel.price
    if blue_pot_row.quantity < 10 and gold >= small_blue_barrel.price and small_blue_barrel.quantity > 0:
        order_list.append({
            "sku": small_blue_barrel.sku,
            "ml_per_barrel": small_blue_barrel.ml_per_barrel,
            "potion_type": small_blue_barrel.potion_type,
            "price": small_blue_barrel.price,
            "quantity": 1
        })
        gold -= small_blue_barrel.price

    return order_list

def get_barrel(wholesale_catalog: list[Barrel], sku: str) -> Barrel:
    """ """
    for barrel in wholesale_catalog:
        if barrel.sku == sku:
            return barrel
    raise NameError(f"{sku} not found in catalog")