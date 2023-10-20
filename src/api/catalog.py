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
        potion_counts = connection.execute(sqlalchemy.text("""
                                                           SELECT 
                                                           potion_id, COALESCE(SUM(change), 0)
                                                           FROM ledger_potions
                                                           GROUP BY potion_id
                                                           """)).all()

        catalog_list = []
        for (potion_id, quantity) in potion_counts:
            if quantity > 0:
                potion = connection.execute(sqlalchemy.text("""
                                                            SELECT *
                                                            FROM potion_inventory
                                                            WHERE id = :p_id
                                                            """),
                                                            [{"p_id": potion_id}])
                potion = potion.first()

                catalog_list.append(
                    {
                        "sku": potion.sku,
                        "name": potion.name,
                        "quantity": quantity,
                        "price": potion.price,
                        "potion_type": potion.potion_type
                    })

    return catalog_list
