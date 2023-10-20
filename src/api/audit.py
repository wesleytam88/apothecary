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
                                                  SELECT
                                                  COALESCE(SUM(change), 0)
                                                  FROM ledger_gold
                                                  """)).first()[0]
        ml_count = connection.execute(sqlalchemy.text("""
                                                      SELECT
                                                      COALESCE(SUM(change), 0)
                                                      FROM ledger_ml
                                                      """)).first()[0]
        p_count = connection.execute(sqlalchemy.text("""
                                                     SELECT
                                                     COALESCE(SUM(change), 0)
                                                     FROM ledger_potions
                                                     """)).first()[0]

    return {"number_of_potions": p_count, 
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
