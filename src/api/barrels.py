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
    print("Barrels delivered:", barrels_delivered)
    
    with db.engine.begin() as connection:
        for barrel in barrels_delivered:
            # Update transaction ledger
            transaction_id = connection.execute(sqlalchemy.text("""
                                                                INSERT
                                                                INTO ledger_transactions
                                                                (description)
                                                                VALUES (:desc)
                                                                RETURNING id
                                                                """),
                                                                [{"desc": f"{barrel.quantity} {barrel.sku} bought for {barrel.price} gold"}])
            transaction_id = transaction_id.first()[0]

            # Update ml ledger
            connection.execute(sqlalchemy.text("""
                                               INSERT INTO ledger_ml
                                               (transaction_id, type, change)
                                               VALUES
                                               (:transaction_id, :p_type, :change)
                                               """),
                                               [{"transaction_id": transaction_id,
                                                 "p_type": barrel.potion_type,
                                                 "change": barrel.quantity * barrel.ml_per_barrel}])
            
            # Update gold ledger
            connection.execute(sqlalchemy.text("""
                                               INSERT INTO ledger_gold
                                               (transaction_id, change)
                                               VALUES
                                               (:transaction_id, :change)
                                               """),
                                               [{"transaction_id": transaction_id,
                                                  "change": -barrel.price}])

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print("Wholesale catalog:", wholesale_catalog)

    with db.engine.begin() as connection:
        gold = connection.execute(sqlalchemy.text("""
                                                  SELECT
                                                  COALESCE(SUM(change), 0)
                                                  FROM ledger_gold
                                                  """)).first()[0]

    # Barrel order logic
    order_list = []
    small_red_barrel = get_barrel(wholesale_catalog, "SMALL_RED_BARREL")
    small_green_barrel = get_barrel(wholesale_catalog, "SMALL_GREEN_BARREL")
    small_blue_barrel = get_barrel(wholesale_catalog, "SMALL_BLUE_BARREL")
    large_dark_barrel = get_barrel(wholesale_catalog, "LARGE_DARK_BARREL")

    if gold >= small_red_barrel.price and small_red_barrel.quantity > 0:
        order_list = order_barrel(order_list, small_red_barrel, 1)
        gold -= small_red_barrel.price
    if gold >= small_green_barrel.price and small_green_barrel.quantity > 0:
        order_list = order_barrel(order_list, small_green_barrel, 1)
        gold -= small_green_barrel.price
    if gold >= small_blue_barrel.price and small_blue_barrel.quantity > 0:
        order_list = order_barrel(order_list, small_blue_barrel, 1)
        gold -= small_blue_barrel.price
    if gold >= large_dark_barrel.price and large_dark_barrel.quantity > 0:
        order_list = order_barrel(order_list, large_dark_barrel, 1)
        gold -= large_dark_barrel.price

    return order_list

def get_barrel(wholesale_catalog: list[Barrel], sku: str) -> Barrel:
    """ """
    for barrel in wholesale_catalog:
        if barrel.sku == sku:
            return barrel
    raise NameError(f"{sku} not found in catalog")

def order_barrel(l: list[Barrel], b: Barrel, quantity: int) -> list[Barrel]:
    """Appends barrel b to order_list l, returns new order_list"""
    l.append({
        "sku": b.sku,
        "ml_per_barrel": b.ml_per_barrel,
        "potion_type": b.potion_type,
        "price": b.price,
        "quantity": quantity
    })
    return l
