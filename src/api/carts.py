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
    shopping_cart: dict


@router.post("/")
def create_cart(new_cart: NewCart):
    """ """
    global cart_ids, carts

    new_cart.shopping_cart = {}
    carts[cart_ids] = new_cart
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
    if item_sku not in cart.shopping_cart:
        cart.shopping_cart[item_sku] = cart_item.quantity
    else:
        cart.shopping_cart[item_sku] += cart_item.quantity

    return "OK"


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory"))

    first_row = result.first()
    num_red_potions = first_row.num_red_potions
    gold = first_row.gold

    cart = carts[cart_id]
    print(cart.shopping_cart)
    for item, quantity in (cart.shopping_cart).items():
        match item:
            case "RED_POTION_0":
                if quantity > num_red_potions:
                    # If buying more potions than in stock, buy available stock
                    quantity = num_red_potions
                    cart.shopping_cart[item] = num_red_potions
                gold += 50 * quantity
            case _:
                raise ValueError(f"Unknown item of {item}")
    
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_red_potions = {num_red_potions - quantity}, gold = {gold} WHERE id = 1"))

    return {"total_potions_bought": 1, "total_gold_paid": 50}
