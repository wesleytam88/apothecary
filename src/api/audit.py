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
        gold = connection.execute(sqlalchemy.text("""
                                                  SELECT *
                                                  FROM global_inventory
                                                  """)).first().gold
        ml_count = connection.execute(sqlalchemy.text("""
                                                      SELECT SUM(red_ml + green_ml + blue_ml + dark_ml)
                                                      FROM global_inventory
                                                      """)).first()[0]
        potion_count = connection.execute(sqlalchemy.text("""
                                                          SELECT SUM(quantity)
                                                          FROM potion_inventory
                                                          """)).first()[0]

    return {"number_of_potions": potion_count, 
            "ml_in_barrels": ml_count, 
            "gold": gold}

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
