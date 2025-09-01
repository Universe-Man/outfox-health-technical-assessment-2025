from sqlalchemy import Column, Integer, String, Float
from database import Base


class ProviderData(Base):
    __tablename__ = "provider_data"

    id = Column(Integer, primary_key=True, index=True)
    Rndrng_Prvdr_CCN = Column(String, index=True)
    Rndrng_Prvdr_Org_Name = Column(String)
    Rndrng_Prvdr_City = Column(String)
    Rndrng_Prvdr_St = Column(String)
    Rndrng_Prvdr_State_FIPS = Column(String)
    Rndrng_Prvdr_Zip5 = Column(String)
    Rndrng_Prvdr_State_Abrvtn = Column(String)
    Rndrng_Prvdr_RUCA = Column(String)
    Rndrng_Prvdr_RUCA_Desc = Column(String)
    DRG_Cd = Column(String)
    DRG_Desc = Column(String)
    Tot_Dschrgs = Column(Integer)
    Avg_Submtd_Cvrd_Chrg = Column(Float)
    Avg_Tot_Pymt_Amt = Column(Float)
    Avg_Mdcr_Pymt_Amt = Column(Float)
