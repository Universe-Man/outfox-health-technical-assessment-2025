from fastapi import FastAPI, Depends, UploadFile, File
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import SessionLocal, engine, Base
from models import ProviderData

Base.metadata.create_all(bind=engine)

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/upload-csv/")
async def upload_csv(file: UploadFile = File(...)):
    df = pd.read_csv(file.file)
    async with SessionLocal() as session:
        for _, row in df.iterrows():
            await session.execute(
                text(
                    """
                    INSERT INTO provider_data (
                        Rndrng_Prvdr_CCN, Rndrng_Prvdr_Org_Name, Rndrng_Prvdr_City,
                        Rndrng_Prvdr_St, Rndrng_Prvdr_State_FIPS, Rndrng_Prvdr_Zip5,
                        Rndrng_Prvdr_State_Abrvtn, Rndrng_Prvdr_RUCA, Rndrng_Prvdr_RUCA_Desc,
                        DRG_Cd, DRG_Desc, Tot_Dschrgs, Avg_Submtd_Cvrd_Chrg, Avg_Tot_Pymt_Amt,
                        Avg_Mdcr_Pymt_Amt
                    ) VALUES (
                        :Rndrng_Prvdr_CCN, :Rndrng_Prvdr_Org_Name, :Rndrng_Prvdr_City,
                        :Rndrng_Prvdr_St, :Rndrng_Prvdr_State_FIPS, :Rndrng_Prvdr_Zip5,
                        :Rndrng_Prvdr_State_Abrvtn, :Rndrng_Prvdr_RUCA, :Rndrng_Prvdr_RUCA_Desc,
                        :DRG_Cd, :DRG_Desc, :Tot_Dschrgs, :Avg_Submtd_Cvrd_Chrg, :Avg_Tot_Pymt_Amt,
                        :Avg_Mdcr_Pymt_Amt
                    )
                """
                ),
                row.to_dict(),
            )
        await session.commit()
    return {"status": "CSV data inserted successfully"}
