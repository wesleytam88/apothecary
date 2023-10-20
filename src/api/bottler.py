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
        for potion in potions_delivered:
            # Update transaction ledger
            transaction_id = connection.execute(sqlalchemy.text("""
                                                                INSERT
                                                                INTO ledger_transactions
                                                                (description)
                                                                VALUES (:desc)
                                                                RETURNING id
                                                                """),
                                                                [{"desc": f"{potion.quantity} potion(s) of type {potion.potion_type} were delivered"}])
            transaction_id = transaction_id.first()[0]

            potion_id = connection.execute(sqlalchemy.text("""
                                                           SELECT *
                                                           FROM potion_inventory
                                                           WHERE potion_type = :p_type
                                                           """),
                                                           [{"p_type": potion.potion_type}])
            potion_id = potion_id.first()[0]

            # Update potion ledger
            connection.execute(sqlalchemy.text("""
                                               INSERT INTO ledger_potions
                                               (transaction_id, potion_id, change)
                                               VALUEs
                                               (:transaction_id, :p_id, :change)
                                               """),
                                               [{"transaction_id": transaction_id,
                                                 "p_id": potion_id,
                                                 "change": potion.quantity}])
            
            # Update ml ledger
            red_ml = potion.potion_type[0] * potion.quantity
            green_ml = potion.potion_type[1] * potion.quantity
            blue_ml = potion.potion_type[2] * potion.quantity
            dark_ml = potion.potion_type[3] * potion.quantity
            indx_to_ml = {0: (red_ml, [1, 0, 0, 0]), 
                          1: (green_ml, [0, 1, 0, 0]),
                          2: (blue_ml, [0, 0, 1, 0]),
                          3: (dark_ml, [0, 0, 0, 1])}

            for i in range(len(potion.potion_type)):
                if potion.potion_type[i] != 0:
                    connection.execute(sqlalchemy.text("""
                                                       INSERT INTO ledger_ml
                                                       (transaction_id, type, change)
                                                       VALUES
                                                       (:transaction_id, :type, :change)
                                                       """),
                                                       [{"transaction_id": transaction_id,
                                                         "type": indx_to_ml[i][1],
                                                         "change": -indx_to_ml[i][0]}])

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
        potion_inv = connection.execute(sqlalchemy.text("""
                                                        SELECT *
                                                        FROM potion_inventory
                                                        """)).all()
        red_ml = connection.execute(sqlalchemy.text("""
                                                     SELECT 
                                                     COALESCE(SUM(change), 0)
                                                     FROM ledger_ml
                                                     WHERE type = :type
                                                     """),
                                                     [{"type": [1, 0, 0, 0]}])
        red_ml = red_ml.first()[0]
        green_ml = connection.execute(sqlalchemy.text("""
                                                     SELECT
                                                     COALESCE(SUM(change), 0)
                                                     FROM ledger_ml
                                                     WHERE type = :type
                                                     """),
                                                     [{"type": [0, 1, 0, 0]}])
        green_ml = green_ml.first()[0]
        blue_ml = connection.execute(sqlalchemy.text("""
                                                     SELECT
                                                     COALESCE(SUM(change), 0)
                                                     FROM ledger_ml
                                                     WHERE type = :type
                                                     """),
                                                     [{"type": [0, 0, 1, 0]}])
        blue_ml = blue_ml.first()[0]
        dark_ml = connection.execute(sqlalchemy.text("""
                                                     SELECT
                                                     COALESCE(SUM(change), 0)
                                                     FROM ledger_ml
                                                     WHERE type = :type
                                                     """),
                                                     [{"type": [0, 0, 0, 1]}])
        dark_ml = dark_ml.first()[0]

    keep_bottling = True
    bottler_list = []
    potions_to_brew = {}

    while keep_bottling:
        failed_brews = 0
        for potion in potion_inv:
            # Check if potion cannot be brewed with available ml
            if potion.potion_type[0] > red_ml or \
               potion.potion_type[1] > green_ml or \
               potion.potion_type[2] > blue_ml or \
               potion.potion_type[3] > dark_ml:
                failed_brews += 1
                if failed_brews >= len(potion_inv):
                    # Can't brew ANY more potions, stop while loop
                    keep_bottling = False
                    break
                # Can't brew this specific potion, try another one
                continue

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
