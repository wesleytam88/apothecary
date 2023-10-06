from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """

    # Can return a max of 20 items.

    with db.engine.begin() as connection:
        table = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory")).all()
        red_pot_row = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory where id = 1")).first()
        green_pot_row = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory where id = 2")).first()
        blue_pot_row = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory where id = 3")).first()

    quantity_list = [red_pot_row.quantity,
                     green_pot_row.quantity,
                     blue_pot_row.quantity]

    if sum(quantity_list) > 0:
        catalog_list = []
        for potion in table:
            catalog_list.append(
                {
                    "sku": potion.sku,
                    "name": potion.name,
                    "quantity": potion.quantity,
                    "price": potion.price,
                    "potion_type": potion.potion_type
                }
            )
        return catalog_list
    else:
        return []
