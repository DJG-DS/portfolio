# app.py
from fastapi import FastAPI, Request
import pandas as pd
import joblib
from ranker import rank_execs_for_new_opp, build_features

app = FastAPI()

model = joblib.load("models/lgbm_ranker.pkl")
exec_roles = pd.read_csv("exec_roles.csv")
exec_roles_wide = exec_roles.pivot_table(
    index="exec_entity_id", 
    columns="type", 
    values=["json_value", "string_value"], 
    aggfunc="first"
).reset_index()
exec_roles_wide.columns = [f"{a}_{b}" for a, b in exec_roles_wide.columns]

@app.post("/predict/")
async def predict(request: Request):
    new_opp = await request.json()
    new_opp_row = pd.Series(new_opp)
    result = rank_execs_for_new_opp(new_opp_row, exec_roles_wide, model, features=[
        "sector_match", "country_match", "scale_match",
        "sector_jaccard", "sub_sector_jaccard", "industry_jaccard"
    ])
    return result.to_dict(orient="records")
