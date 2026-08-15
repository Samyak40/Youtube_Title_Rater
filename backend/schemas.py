from pydantic import BaseModel

class ScoreRequest(BaseModel):
    title: str

class ScoreResponse(BaseModel):
    engagement_score: float
    percentile: float
    raw_prediction: float
