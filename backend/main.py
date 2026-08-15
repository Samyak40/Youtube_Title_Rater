import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import pandas as pd
from scipy.sparse import hstack

from backend.schemas import ScoreRequest, ScoreResponse
from backend.features import extract_numeric_features
import backend.model_loader as model_loader

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    model_loader.load_models()
    yield
    # Shutdown
    pass

app = FastAPI(title="TitlePulse Score API", version="1.0.0", lifespan=lifespan)

# CORS setup
origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"name": "TitlePulse Score API", "version": "1.0.0", "docs_url": "/docs"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/score", response_model=ScoreResponse)
def predict_score(req: ScoreRequest):
    title = req.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Title cannot be empty.")
    if len(title) > 200:
        raise HTTPException(status_code=422, detail="Title is too long (max 200 characters).")
        
    try:
        # Feature extraction
        df_temp = pd.DataFrame([{"title": title}])
        num_feats = extract_numeric_features(df_temp).values
        
        tfidf_feats = model_loader.vectorizer.transform([title])
        
        X = hstack([tfidf_feats, num_feats])
        
        # Predict
        raw_pred = model_loader.model.predict(X)[0]
        
        # Percentile
        percentile = model_loader.get_percentile(raw_pred)
        
        return ScoreResponse(
            engagement_score=float(raw_pred),
            percentile=float(percentile),
            raw_prediction=float(raw_pred)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
