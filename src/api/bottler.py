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
        red_pot_row = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory where id = 1")).first()
        green_pot_row = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory where id = 2")).first()
        blue_pot_row = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory where id = 3")).first()

    num_red_potions = red_pot_row.quantity
    red_ml = red_pot_row.ml
    num_green_potions = green_pot_row.quantity
    green_ml = green_pot_row.ml
    num_blue_potions = blue_pot_row.quantity
    blue_ml = blue_pot_row.ml

    for potion in potions_delivered:
        red_ml -= potion.potion_type[0] * potion.quantity
        green_ml -= potion.potion_type[1] * potion.quantity
        blue_ml -= potion.potion_type[2] * potion.quantity

        match potion.potion_type:
            case [100, 0, 0, 0]:
                num_red_potions += potion.quantity
            case [0, 100, 0, 0]:
                num_green_potions += potion.quantity
            case [0, 0, 100, 0]:
                num_blue_potions += potion.quantity
            case _:
                raise ValueError(f"unknown potion type {potion.potion_type}")

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(f"UPDATE potion_inventory SET quantity = {num_red_potions}, ml = {red_ml} WHERE id = 1"))
        connection.execute(sqlalchemy.text(f"UPDATE potion_inventory SET quantity = {num_green_potions}, ml = {green_ml} WHERE id = 2"))
        connection.execute(sqlalchemy.text(f"UPDATE potion_inventory SET quantity = {num_blue_potions}, ml = {blue_ml} WHERE id = 3"))

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
        red_pot_row = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory where id = 1")).first()
        green_pot_row = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory where id = 2")).first()
        blue_pot_row = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory where id = 3")).first()

    num_red_potions_to_brew = red_pot_row.ml // 100
    num_green_potions_to_brew = green_pot_row.ml // 100
    num_blue_potions_to_brew = blue_pot_row.ml // 100

    bottler_list = []
    if num_red_potions_to_brew > 0:
        bottler_list.append({"potion_type": [100, 0, 0, 0],
                             "quantity": num_red_potions_to_brew}
        )
    if num_green_potions_to_brew > 0:
        bottler_list.append({"potion_type": [0, 100, 0, 0],
                             "quantity": num_green_potions_to_brew}
        )
    if num_blue_potions_to_brew > 0:
        bottler_list.append({"potion_type": [0, 0, 100, 0],
                             "quantity": num_blue_potions_to_brew}
        )

    return bottler_list
