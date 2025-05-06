from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import pandas as pd
import joblib
from datetime import datetime, timedelta
import logging
import os
from flask import request
app = Flask(__name__, static_folder='static')
CORS(app)
logging.basicConfig(level=logging.DEBUG)

# Correct relative path to the model
model_path = os.path.join(os.path.dirname(__file__), 'Models', 'best_random_forest_model.joblib')
volatility_model = joblib.load(model_path)

market_signal_model_path = os.path.join(os.path.dirname(__file__), 'Models', 'random_forest_market_signal_model.joblib')
market_signal_model = joblib.load(market_signal_model_path)

# Initialize empty data
data = pd.DataFrame()

# Define update_data
def update_data():
    global data
    try:
        data = process_dataset()
        if not data.empty:
            data['timestamp'] = pd.to_datetime(data['timestamp'])
        logging.info(f"Data loaded successfully. Data shape: {data.shape}")
        print(data.head())  # <-- ADD THIS
    except Exception as e:
        logging.error(f"Error loading data: {str(e)}")



"""
data = pd.DataFrame()
def update_data():
    global data, sentiment_data
    try:
        new_market_data = process_dataset()
        
        if new_market_data is not None and not new_market_data.empty:
            if data.empty:
                data = new_market_data
            else:
                data = pd.concat([data, new_market_data]).drop_duplicates(subset='timestamp', keep='last')
            data['timestamp'] = pd.to_datetime(data['timestamp'])
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(days=7)
        data = data[data['timestamp'] > cutoff_time]
        logging.info(f"Data updated successfully. Market data shape: {data.shape}")
    except Exception as e:
        logging.error(f"Error updating data: {str(e)}")

scheduler = BackgroundScheduler()
scheduler.add_job(func=update_data, trigger="interval", hours=1)
scheduler.start()
"""

def process_dataset():
    try:
        csv_path = r"C:\Users\somya\Downloads\Hybrid Model for Crypto Volatility Prediction using Sentiment Analysis\Data_set\final-data.csv"
        return pd.read_csv(csv_path)
    except Exception as e:
        print("Error loading final-data.csv:", e)
        return pd.DataFrame()

@app.route('/', methods=['GET'])
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/historical_data', methods=['GET'])
def get_historical_data():
    global data
    logging.info(f"get_historical_data called. Data shape: {data.shape}")
    if not data.empty:
        # Get 'days' query param from frontend
        days = int(request.args.get('days', 30))  # Default 30 if not provided
        historical_data = data.sort_values('timestamp').tail(days)
        
        result = {
            'timestamp': historical_data['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(),
            'price': historical_data['price'].tolist(),  # Assuming you fixed 'price' column earlier
            'sentiment': historical_data['total_sentiment'].tolist(),
        }
        logging.info(f"Returning historical data: {result}")
        return jsonify(result)
    else:
        logging.warning("No historical data available")
        return jsonify({'error': 'No historical data available'}), 404

@app.route('/api/market_signal', methods=['GET'])
def get_market_signal():
    global data
    if not data.empty:
        features = data.drop(['timestamp', 'market_signal'], axis=1, errors='ignore').tail(1)

        # Fix column mismatch
        features = features.rename(columns={
            'bitcoin_market_cap': 'market_cap',
            'bitcoin_price': 'price',
            'bitcoin_volume': 'total_volume'
        })
        
        # DROP extra columns
        features = features.drop(columns=['Unnamed: 0', 'bitcoin_volatility', 'coin_name'], errors='ignore')

        prediction = market_signal_model.predict(features)[0]

        # Map prediction to label
        signal_mapping = {
            0: 'Bearish 📉',
            1: 'Neutral ⚖️',
            2: 'Bullish 📈'
        }
        mapped_signal = signal_mapping.get(prediction, "Unknown")

        return jsonify({
            'predicted_signal': mapped_signal,
            'forecast_period': '24 hours'
        })
    else:
        return jsonify({'error': 'Unable to make market signal forecast'}), 500


@app.route('/api/volatility_forecast', methods=['GET'])
def get_volatility_forecast():
    global data
    if not data.empty:
        features = data.copy()
        features = features.drop(['timestamp', 'bitcoin_volatility', 'market_signal', 'coin_name', 'Unnamed: 0'], axis=1, errors='ignore').tail(1)
        
        # ✨ Rename here
        features = features.rename(columns={
            'price': 'bitcoin_price',
            'market_cap': 'bitcoin_market_cap',
            'total_volume': 'bitcoin_volume'
        })
        
        prediction = volatility_model.predict(features)[0]
        return jsonify({
            'predicted_volatility': float(prediction),
            'forecast_period': '24 hours'
        })
    else:
        return jsonify({'error': 'Unable to make volatility forecast'}), 500

"""
@app.route('/api/sentiment_analysis', methods=['GET'])
def get_sentiment_analysis():
    global data
    if not data.empty:
        recent_sentiment = data
        sentiment= recent_sentiment['total_sentiment'].to_list()
        return jsonify({
            'sentiment_score': float(sum(sentiment)/len(sentiment)),
            'analysis_period': '24 hours'
        })
    else:
        return jsonify({'error': 'No sentiment data available'}), 404
"""
@app.route('/api/sentiment_analysis', methods=['GET'])
def get_sentiment_analysis():
    global data
    if not data.empty:
        # Simulate "recent" by taking last 100 rows
        recent_sentiment = data.tail(100)
        
        sentiment_scores = recent_sentiment['total_sentiment'].tolist()
        average_sentiment = sum(sentiment_scores) / len(sentiment_scores)

        # Optional sentiment label
        if average_sentiment > 0.1:
            sentiment_label = "Positive 😄"
        elif average_sentiment < -0.1:
            sentiment_label = "Negative 😟"
        else:
            sentiment_label = "Neutral 😐"

        return jsonify({
            'sentiment_score': round(float(average_sentiment), 4),
            'sentiment_label': sentiment_label,
            'analysis_period': '24 hours'
        })
    else:
        return jsonify({'error': 'No sentiment data available'}), 404


if __name__ == '__main__':
    update_data()  # load data from final.csv
    app.run(debug=True, use_reloader=False)
