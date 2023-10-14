from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)


class NewCart(BaseModel):
    customer: str


@router.post("/")
def create_cart(new_cart: NewCart):
    """ """
    with db.engine.begin() as connection:
        id = connection.execute(sqlalchemy.text("""
                                                INSERT INTO carts (customer)
                                                VALUES (:customer)
                                                RETURNING id
                                                """),
                                                [{"customer": new_cart.customer}])
    return {"cart_id": id.first()[0]}


@router.get("/{cart_id}")
def get_cart(cart_id: int):
    """ """
    with db.engine.begin() as connection:
        cart_row = connection.execute(sqlalchemy.text("""
                                                      SELECT *
                                                      FROM carts
                                                      WHERE id = :cart_id
                                                      """),
                                                      [{"cart_id": cart_id}])
        cart = cart_row.first()

        items = connection.execute(sqlalchemy.text("""
                                                   SELECT *
                                                   FROM cart_items
                                                   WHERE cart_id = :cart_id
                                                   """),
                                                   [{"cart_id": cart_id}])
        items_table = items.all()

        items = {}
        for row in items_table:
            potion = connection.execute(sqlalchemy.text("""
                                                        SELECT *
                                                        FROM potion_inventory
                                                        WHERE id = :potion_id
                                                        """),
                                                        [{"potion_id": row.potion_id}])
            potion = potion.first()
            items[potion.sku] = row.quantity

        return [cart.customer, items]


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    with db.engine.begin() as connection:
        potion = connection.execute(sqlalchemy.text("""
                                                    SELECT *
                                                    FROM potion_inventory
                                                    WHERE sku = :p_sku
                                                    """),
                                                    [{"p_sku": item_sku}])
        potion = potion.first()

        # Update cart_items table
        connection.execute(sqlalchemy.text("""
                                           INSERT INTO cart_items (cart_id, potion_id, quantity)
                                           VALUES (:cart_id, :potion_id, :quantity)
                                           """),
                                           [{"cart_id": cart_id,
                                             "potion_id": potion.id,
                                             "quantity": cart_item.quantity}])

    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    with db.engine.begin() as connection:
        cart_items = connection.execute(sqlalchemy.text("""
                                                        SELECT *
                                                        FROM cart_items
                                                        WHERE cart_id = :c_id
                                                        """),
                                                        [{"c_id": cart_id}])
        cart_items = cart_items.all()

        # Update quantities in potion table
        checkout_gold = 0
        sum_quantity = 0
        for item in cart_items:
            price = connection.execute(sqlalchemy.text("""
                                                      UPDATE potion_inventory
                                                      SET quantity = quantity - :c_quantity
                                                      WHERE id = :p_id
                                                      RETURNING price
                                                      """),
                                                      [{"c_quantity": item.quantity,
                                                        "p_id": item.potion_id}])
            checkout_gold += price.first()[0]
            sum_quantity += item.quantity

        # Update gold
        connection.execute(sqlalchemy.text("""
                                           UPDATE global_inventory
                                           SET gold = gold + :checkout_gold
                                           WHERE id = 1
                                           """),
                                           [{"checkout_gold": checkout_gold}])

    return {"total_potions_bought": sum_quantity, 
            "total_gold_paid": checkout_gold}