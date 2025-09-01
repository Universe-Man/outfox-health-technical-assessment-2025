CREATE TABLE IF NOT EXISTS provider_data (
    id SERIAL PRIMARY KEY,
    Rndrng_Prvdr_CCN TEXT,
    Rndrng_Prvdr_Org_Name TEXT,
    Rndrng_Prvdr_City TEXT,
    Rndrng_Prvdr_St TEXT,
    Rndrng_Prvdr_State_FIPS TEXT,
    Rndrng_Prvdr_Zip5 TEXT,
    Rndrng_Prvdr_State_Abrvtn TEXT,
    Rndrng_Prvdr_RUCA TEXT,
    Rndrng_Prvdr_RUCA_Desc TEXT,
    DRG_Cd TEXT,
    DRG_Desc TEXT,
    Tot_Dschrgs INT,
    Avg_Submtd_Cvrd_Chrg FLOAT,
    Avg_Tot_Pymt_Amt FLOAT,
    Avg_Mdcr_Pymt_Amt FLOAT
);
