# Executive Matching with LightGBM Ranker

This repository contains a daily retraining pipeline for a LightGBM Ranker that matches executives to business opportunities. It also provides a FastAPI service to serve predictions.

## Project Structure

```
nexus/
  github-actions/
    ranker.py          # Daily training script
    predict.py         # FastAPI scoring script
  data/                # CSVs (ignored in git)
  logs/                # Precision@5 logs
  models/              # Trained model output
  .github/workflows/   # GitHub Actions setup
  requirements.txt
  README.md
```

## GitHub Actions

Runs daily at 6 AM UTC. Trains the model and logs Precision@5 to `logs/precision_log.csv`. Uploads model as artifact.

You can also trigger manually via the Actions tab.

## FastAPI Prediction

Start the server:

```bash
uvicorn github-actions.predict:app --reload
```

Then send a POST request to:

```
http://localhost:8000/predict/
```

**Payload example:**
```json
{
  "assignment_id": 101,
  "country": "UK",
  "sectors": "[\"Finance\"]",
  "sub_sectors": "[\"FinTech\"]",
  "industry": "[\"Banking\"]",
  "scale": "Medium"
}
```

Returns ranked top 10 executives.

## Setup

```bash
pip install -r requirements.txt
python github-actions/ranker.py
```

## Logs

Precision@5 is recorded daily in:

```
logs/precision_log.csv
```

## Output

Model saved as:

```
models/lgbm_ranker.pkl
```

