from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

carts = {}
cart_ids = 1

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
    global cart_ids, carts

    carts[cart_ids] = [new_cart.customer, {}]
    cart_ids += 1
    return {"cart_id": cart_ids - 1}


@router.get("/{cart_id}")
def get_cart(cart_id: int):
    """ """

    return carts[cart_id]


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    cart = carts[cart_id]
    cart_basket = cart[1]
    # Add item to cart
    if item_sku not in cart[1]:
        cart_basket[item_sku] = cart_item.quantity
    else:
        cart_basket[item_sku] += cart_item.quantity

    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    with db.engine.begin() as connection:
        gold = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory where id = 1")).first().gold
        red_pot_row = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory where id = 1")).first()
        green_pot_row = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory where id = 2")).first()
        blue_pot_row = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory where id = 3")).first()

    cart = carts[cart_id]
    cart_customer = cart[0]
    cart_basket = cart[1]
    
    red_quantity = 0
    green_quantity = 0
    blue_quantity = 0

    for sku, quantity in (cart_basket).items():
        match sku:
            case "RED_POTION":
                red_quantity, gold = checkout_logic(quantity, red_quantity, gold, red_pot_row)
            case "GREEN_POTION":
                green_quantity, gold = checkout_logic(quantity, green_quantity, gold, green_pot_row)
            case "BLUE_POTION":
                blue_quantity, gold = checkout_logic(quantity, blue_quantity, gold, blue_pot_row)
            case _:
                raise ValueError(f"unknown sku of {sku}")

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(f"UPDATE potion_inventory SET quantity = {red_pot_row.quantity - red_quantity} WHERE id = 1"))
        connection.execute(sqlalchemy.text(f"UPDATE potion_inventory SET quantity = {green_pot_row.quantity - green_quantity} WHERE id = 2"))
        connection.execute(sqlalchemy.text(f"UPDATE potion_inventory SET quantity = {blue_pot_row.quantity - blue_quantity} WHERE id = 3"))
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET gold = {gold} WHERE id = 1"))

    return {"total_potions_bought": sum([red_quantity, green_quantity, blue_quantity]), "total_gold_paid": gold}


def checkout_logic(customer_quantity: int, checkout_quantity: int, gold: int, potion_row):
    """ """
    if customer_quantity > potion_row.quantity:
        checkout_quantity = potion_row.quantity
    else:
        checkout_quantity = customer_quantity
    gold += potion_row.price * checkout_quantity
    return checkout_quantity, gold