# Walmart Big Data Analytics Dashboard

## Files
- `app.py`: Streamlit dashboard
- `requirements.txt`: dependencies

## Run locally
1. Install Python 3.10+.
2. Put `train.csv` in the same folder as `app.py`, or upload it in the app sidebar.
3. Install dependencies:
   `pip install -r requirements.txt`
4. Launch:
   `streamlit run app.py`

## Hadoop results
In your Hadoop Colab notebook, export `/walmart/output/part-r-00000` to a local text file and upload it in the app sidebar under "Hadoop output".

This dashboard presents interactive analytics from the dataset and displays exported MapReduce results. It does not directly connect to a running Colab Spark/Hadoop session.
