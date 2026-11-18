# Home ventilation & CO₂ explorer

A Streamlit app showing how ventilation rates (EN 16798) relate to steady-state CO₂ in a
**bedroom** or **living room**, for different occupants, ages and room sizes.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy (free) on Streamlit Community Cloud
1. Push this folder to a GitHub repository (see below).
2. Go to <https://share.streamlit.io>, sign in with GitHub, click **Create app**.
3. Choose the repo, branch `main`, main file `app.py`, then **Deploy**.

## Files
* `co2_model.py` – data tables and the calculation (edit rates / areas here)
* `app.py` – the Streamlit interface
* `requirements.txt` – dependencies
