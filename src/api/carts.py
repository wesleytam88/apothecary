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
            p_sku = connection.execute(sqlalchemy.text("""
                                                       SELECT sku
                                                       FROM potion_inventory
                                                       WHERE id = :p_id
                                                       """),
                                                       [{"p_id": row.potion_id}])
            p_sku = p_sku.first()[0]

            items[p_sku] = row.quantity

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

        potion_count = connection.execute(sqlalchemy.text("""
                                                          SELECT SUM(change)
                                                          FROM ledger_potions
                                                          WHERE potion_id = :p_id
                                                          """),
                                                          [{"p_id": potion.id}])
        potion_count = potion_count.first()[0]

        # Check if enough potions in stock
        if cart_item.quantity > potion_count:
            raise HTTPException(status_code=500, detail=f"Trying to buy {cart_item.quantity} {potion.sku} when {potion_count} available")

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
        # Update payment
        connection.execute(sqlalchemy.text("""
                                           UPDATE carts
                                           SET payment = :payment
                                           WHERE id = :cart_id
                                           """),
                                           [{"payment": cart_checkout.payment,
                                             "cart_id": cart_id}])

        cart_items = connection.execute(sqlalchemy.text("""
                                                        SELECT *
                                                        FROM cart_items
                                                        WHERE cart_id = :c_id
                                                        """),
                                                        [{"c_id": cart_id}])
        cart_items = cart_items.all()

        checkout_gold = 0
        checkout_quantity = 0
        for item in cart_items:
            # Update transactions ledger
            transaction_id = connection.execute(sqlalchemy.text("""
                                                                INSERT
                                                                INTO ledger_transactions
                                                                (description)
                                                                VALUES (:desc)
                                                                RETURNING id
                                                                """),
                                                                [{"desc": f"{item.quantity} potion(s) of id {item.potion_id} sold"}])
            transaction_id = transaction_id.first()[0]

            # Update potions ledger
            connection.execute(sqlalchemy.text("""
                                               INSERT
                                               INTO ledger_potions
                                               (transaction_id, potion_id, change)
                                               VALUES
                                               (:transaction_id, :p_id, :change)
                                               """),
                                               [{"transaction_id": transaction_id,
                                                 "p_id": item.potion_id,
                                                 "change": -item.quantity}])

            # Update gold ledger
            price = connection.execute(sqlalchemy.text("""
                                                      SELECT price
                                                      FROM potion_inventory
                                                      WHERE id = :p_id
                                                      """),
                                                      [{"p_id": item.potion_id}])
            price = price.first()[0]
            connection.execute(sqlalchemy.text("""
                                               INSERT
                                               INTO ledger_gold
                                               (transaction_id, change)
                                               VALUES
                                               (:transaction_id, :change)
                                               """),
                                               [{"transaction_id": transaction_id,
                                                 "change": price * item.quantity}])
            
            checkout_gold += price * item.quantity
            checkout_quantity += item.quantity

    return {"total_potions_bought": checkout_quantity, 
            "total_gold_paid": checkout_gold}