from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/inventory")
def get_inventory():
    """ """
    with db.engine.begin() as connection:
        global_inv = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory")).first()
        red_pot_row = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory where id = 1")).first()
        green_pot_row = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory where id = 2")).first()
        blue_pot_row = connection.execute(sqlalchemy.text("SELECT * FROM potion_inventory where id = 3")).first()

    return {"number_of_potions": sum(red_pot_row.quantity, green_pot_row.quantity, blue_pot_row.quantity), 
            "ml_in_barrels": sum(global_inv.num_red_ml, global_inv.num_green_ml, global_inv.num_blue_ml), 
            "gold": global_inv.gold}

class Result(BaseModel):
    gold_match: bool
    barrels_match: bool
    potions_match: bool

# Gets called once a day
@router.post("/results")
def post_audit_results(audit_explanation: Result):
    """ """
    print(audit_explanation)

    return "OK"
