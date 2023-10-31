from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from src.api import auth
from enum import Enum
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"

@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """
    LIMIT = 5
    if search_page == "":
        offset = 0
    else:
        offset = int(search_page) * LIMIT        # assuming search page is 0 indexed

    with db.engine.begin() as connection:
        metadata = sqlalchemy.MetaData()
        ledger_transactions = sqlalchemy.Table("ledger_transactions", metadata, autoload_with=db.engine)
        ledger_gold = sqlalchemy.Table("ledger_gold", metadata, autoload_with=db.engine)
        ledger_potions = sqlalchemy.Table("ledger_potions", metadata, autoload_with=db.engine)
        carts = sqlalchemy.Table("carts", metadata, autoload_with=db.engine)
        potion_inv = sqlalchemy.Table("potion_inventory", metadata, autoload_with=db.engine)

        match sort_col:
            case search_sort_options.line_item_total:
                order_by = ledger_gold.c.change
            case search_sort_options.item_sku:
                order_by = potion_inv.c.sku
            case search_sort_options.customer_name:
                order_by = carts.c.customer
            case search_sort_options.timestamp:
                order_by = ledger_transactions.c.created_at
            case _:
                assert False

        match sort_order:
            case search_sort_order.desc:
                order_by = order_by.desc()
            case search_sort_order.asc:
                order_by = order_by.asc()
            case _:
                assert False

        join1 = sqlalchemy.join(ledger_transactions, carts, carts.c.transaction_id == ledger_transactions.c.id)
        join2 = sqlalchemy.join(join1, ledger_potions, ledger_potions.c.transaction_id == ledger_transactions.c.id)
        join3 = sqlalchemy.join(join2, potion_inv, potion_inv.c.id == ledger_potions.c.potion_id)
        join4 = sqlalchemy.join(join3, ledger_gold, ledger_gold.c.transaction_id == ledger_transactions.c.id)

        query = (
            sqlalchemy.select(
                ledger_transactions.c.id,
                ledger_transactions.c.created_at,
                carts.c.customer,
                potion_inv.c.sku,
                ledger_potions.c.change,
                ledger_gold.c.change,
            )
            .select_from(join4)
            .offset(offset)
            .limit(LIMIT)
            .order_by(order_by)
        )
        if customer_name != "":
            query = query.where(carts.c.customer.ilike(f"%{customer_name}%"))
        if potion_sku != "":
            query = query.where(potion_inv.c.sku.ilike(f"%{potion_sku}%"))

        response = connection.execute(query).all()

        query2 = (
            sqlalchemy.select(
                sqlalchemy.func.count(ledger_transactions.c.id)
            )
            .select_from(join4)
        )
        if customer_name != "":
            query2 = query2.where(carts.c.customer.ilike(f"%{customer_name}%"))
        if potion_sku != "":
            query2 = query2.where(potion_inv.c.sku.ilike(f"%{potion_sku}%"))

        num_rows = connection.execute(query2).first()[0]

    results = []
    for transaction in response:
        results.append({
            "line_item_id": transaction.id,
            "item_sku": f"{-transaction.change} {transaction.sku}",
            "customer_name": transaction.customer,
            "line_item_total": transaction[5],
            "timestamp": transaction.created_at,
        })

    prev = "1" if offset > LIMIT else ""
    next = "1" if num_rows > (offset + len(response)) else ""

    return {
        "previous": prev,
        "next": next,
        "results": results
    }

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
                                                          SELECT 
                                                          COALESCE(SUM(change), 0)
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

        # Update transactions ledger
        transaction_id = connection.execute(sqlalchemy.text("""
                                                            INSERT
                                                            INTO ledger_transactions
                                                            (description)
                                                            VALUES (:desc)
                                                            RETURNING id
                                                            """),
                                                            [{"desc": f"Potion(s) sold"}])
        transaction_id = transaction_id.first()[0]

        connection.execute(sqlalchemy.text("""
                                           UPDATE carts
                                           SET transaction_id = :transaction_id
                                           WHERE id = :cart_id
                                           """),
                                           [{"transaction_id": transaction_id,
                                             "cart_id": cart_id}])

        checkout_gold = 0
        checkout_quantity = 0
        for item in cart_items:
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