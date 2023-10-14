from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver")
def post_deliver_bottles(potions_delivered: list[PotionInventory]):
    """ """
    print("Potions delivered:", potions_delivered)

    with db.engine.begin() as connection:
        global_inv = connection.execute(sqlalchemy.text("SELECT * \
                                                         FROM global_inventory \
                                                         WHERE id = 1")).first()

        red_ml = global_inv.red_ml
        green_ml = global_inv.green_ml
        blue_ml = global_inv.blue_ml
        dark_ml = global_inv.dark_ml

        for potion in potions_delivered:
            red_ml -= potion.potion_type[0] * potion.quantity
            green_ml -= potion.potion_type[1] * potion.quantity
            blue_ml -= potion.potion_type[2] * potion.quantity
            dark_ml -= potion.potion_type[3] * potion.quantity

            connection.execute(sqlalchemy.text(f"""UPDATE potion_inventory \
                                                   SET quantity = quantity + :quantity \
                                                   WHERE potion_type = :type"""),
                                               [{"quantity": potion.quantity, 
                                                 "type": potion.potion_type}])

        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET \
                                             red_ml = {red_ml}, \
                                             green_ml = {green_ml}, \
                                             blue_ml = {blue_ml}, \
                                             dark_ml = {dark_ml} \
                                             WHERE id = 1"))

    return "OK"

# Gets called 4 times a day
@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    with db.engine.begin() as connection:
        global_inv = connection.execute(sqlalchemy.text("SELECT * \
                                                        FROM global_inventory \
                                                        WHERE id = 1")).first()
        potion_inv = connection.execute(sqlalchemy.text("SELECT *  \
                                                        FROM potion_inventory")).all()

    red_ml = global_inv.red_ml
    green_ml = global_inv.green_ml
    blue_ml = global_inv.blue_ml
    dark_ml = global_inv.dark_ml

    keep_bottling = True
    bottler_list = []
    potions_to_brew = {}
    while keep_bottling:
        for potion in potion_inv:
            # Check if potion cannot be brewed with available ml
            if potion.potion_type[0] > red_ml or \
               potion.potion_type[1] > green_ml or \
               potion.potion_type[2] > blue_ml or \
               potion.potion_type[3] > dark_ml:
                keep_bottling = False
                break

            # Potion can be brewed
            red_ml -= potion.potion_type[0]
            green_ml -= potion.potion_type[1]
            blue_ml -= potion.potion_type[2]
            dark_ml -= potion.potion_type[3]

            if potion.sku not in potions_to_brew:
                potions_to_brew[potion.sku] = [potion.potion_type, 0]
            potion_type, quantity = potions_to_brew[potion.sku]
            potions_to_brew[potion.sku] = [potion_type, quantity + 1]

    for potion_type, quantity in potions_to_brew.values():
        bottler_list.append({"potion_type": potion_type,
                            "quantity": quantity})

    return bottler_list
