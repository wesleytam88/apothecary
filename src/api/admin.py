from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    with db.engine.begin() as connection:
        # Clear all ml, potions, gold, and carts
        transaction_id = connection.execute(sqlalchemy.text("""
                                                            TRUNCATE TABLE
                                                            ledger_transactions, ledger_gold, ledger_ml, ledger_potions, carts, cart_items;

                                                            INSERT INTO ledger_transactions
                                                            (description)
                                                            VALUES
                                                            (:desc)
                                                            RETURNING id;
                                                            """),
                                                            [{"desc": "Add 100 starting gold"}])
        transaction_id = transaction_id.first()[0]

        # Add 100 starting gold
        connection.execute(sqlalchemy.text("""
                                           INSERT INTO ledger_gold
                                           (transaction_id, change)
                                           VALUES
                                           (:transaction_id, :change);
                                           """),
                                           [{"transaction_id": transaction_id,
                                             "change": 100}])

    return "OK"


@router.get("/shop_info/")
def get_shop_info():
    """ """
    return {
        "shop_name": "The Apothecary",
        "shop_owner": "Wesley Tam",
    }
