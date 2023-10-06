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

    catalog_list = []
    for potion in table:
        if potion.quantity > 0:
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
