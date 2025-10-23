import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor
import pickle
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from src.storage.timescaledb_connector import TimescaleDBConnector
from src.utils.config_loader import settings
from src.utils.logger import setup_logger

logger = setup_logger("price_predictor")


class PricePredictor:
    def __init__(self):
        self.models: Dict[str, XGBRegressor] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.timescale_db = TimescaleDBConnector()
        self.model_path = settings.ml_model_path
        self.load_models()

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.sort_values('time').reset_index(drop=True)

        df['price_lag_1'] = df['price'].shift(1)
        df['price_lag_2'] = df['price'].shift(2)
        df['price_lag_3'] = df['price'].shift(3)
        df['price_lag_5'] = df['price'].shift(5)

        df['price_ma_5'] = df['price'].rolling(window=5).mean()
        df['price_ma_10'] = df['price'].rolling(window=10).mean()
        df['price_ma_20'] = df['price'].rolling(window=20).mean()

        df['volume_ma_5'] = df['volume'].rolling(window=5).mean()
        df['volume_ma_10'] = df['volume'].rolling(window=10).mean()

        df['price_std_5'] = df['price'].rolling(window=5).std()
        df['price_std_10'] = df['price'].rolling(window=10).std()

        df['price_min_5'] = df['price'].rolling(window=5).min()
        df['price_max_5'] = df['price'].rolling(window=5).max()

        df['price_change'] = df['price'].pct_change()
        df['price_change_lag_1'] = df['price_change'].shift(1)

        df['hour'] = pd.to_datetime(df['time']).dt.hour
        df['day_of_week'] = pd.to_datetime(df['time']).dt.dayofweek
        df['minute'] = pd.to_datetime(df['time']).dt.minute

        df = df.dropna()

        return df

    def train_model(self, symbol: str, lookback_days: int = 30):
        logger.info(f"Training model for {symbol}")

        end_time = datetime.now()
        start_time = end_time - timedelta(days=lookback_days)

        data = self.timescale_db.query_tick_data(symbol, start_time, end_time, limit=10000)

        if len(data) < 100:
            logger.error(f"Insufficient data for training {symbol}: {len(data)} records")
            return False

        df = pd.DataFrame(data)

        df = self.prepare_features(df)

        if len(df) < 50:
            logger.error(f"Insufficient data after feature engineering for {symbol}")
            return False

        feature_columns = [
            'price_lag_1', 'price_lag_2', 'price_lag_3', 'price_lag_5',
            'price_ma_5', 'price_ma_10', 'price_ma_20',
            'volume_ma_5', 'volume_ma_10',
            'price_std_5', 'price_std_10',
            'price_min_5', 'price_max_5',
            'price_change', 'price_change_lag_1',
            'hour', 'day_of_week', 'minute'
        ]

        X = df[feature_columns]
        y = df['price']

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        model = XGBRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1
        )

        model.fit(X_train_scaled, y_train)

        train_score = model.score(X_train_scaled, y_train)
        test_score = model.score(X_test_scaled, y_test)

        logger.info(f"Model for {symbol} - Train R²: {train_score:.4f}, Test R²: {test_score:.4f}")

        self.models[symbol] = model
        self.scalers[symbol] = scaler

        self.save_model(symbol)

        return True

    def predict_next_price(self, symbol: str, time_horizon_minutes: int = 5) -> Optional[Dict]:
        if symbol not in self.models or symbol not in self.scalers:
            logger.warning(f"No trained model found for {symbol}")
            return None

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=2)

        data = self.timescale_db.query_tick_data(symbol, start_time, end_time, limit=100)

        if len(data) < 30:
            logger.warning(f"Insufficient recent data for prediction: {symbol}")
            return None

        df = pd.DataFrame(data)
        df = self.prepare_features(df)

        if df.empty:
            return None

        feature_columns = [
            'price_lag_1', 'price_lag_2', 'price_lag_3', 'price_lag_5',
            'price_ma_5', 'price_ma_10', 'price_ma_20',
            'volume_ma_5', 'volume_ma_10',
            'price_std_5', 'price_std_10',
            'price_min_5', 'price_max_5',
            'price_change', 'price_change_lag_1',
            'hour', 'day_of_week', 'minute'
        ]

        X_latest = df[feature_columns].iloc[-1:].values
        X_latest_scaled = self.scalers[symbol].transform(X_latest)

        predicted_price = self.models[symbol].predict(X_latest_scaled)[0]
        current_price = df['price'].iloc[-1]

        confidence = min(1.0, max(0.0, 1.0 - abs(predicted_price - current_price) / current_price))

        return {
            "symbol": symbol,
            "timestamp": datetime.now(),
            "current_price": float(current_price),
            "predicted_price": float(predicted_price),
            "confidence": float(confidence),
            "time_horizon_minutes": time_horizon_minutes,
            "model_version": "xgboost_v1"
        }

    def save_model(self, symbol: str):
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)

            model_file = self.model_path.replace('.pkl', f'_{symbol}_model.pkl')
            scaler_file = self.model_path.replace('.pkl', f'_{symbol}_scaler.pkl')

            with open(model_file, 'wb') as f:
                pickle.dump(self.models[symbol], f)

            with open(scaler_file, 'wb') as f:
                pickle.dump(self.scalers[symbol], f)

            logger.info(f"Model saved for {symbol}")

        except Exception as e:
            logger.error(f"Error saving model for {symbol}: {e}", exc_info=True)

    def load_models(self):
        try:
            symbols = settings.symbols.split(',')

            for symbol in symbols:
                model_file = self.model_path.replace('.pkl', f'_{symbol}_model.pkl')
                scaler_file = self.model_path.replace('.pkl', f'_{symbol}_scaler.pkl')

                if os.path.exists(model_file) and os.path.exists(scaler_file):
                    with open(model_file, 'rb') as f:
                        self.models[symbol] = pickle.load(f)

                    with open(scaler_file, 'rb') as f:
                        self.scalers[symbol] = pickle.load(f)

                    logger.info(f"Model loaded for {symbol}")

        except Exception as e:
            logger.error(f"Error loading models: {e}", exc_info=True)

    def retrain_all_models(self):
        symbols = settings.symbols.split(',')

        for symbol in symbols:
            try:
                self.train_model(symbol)
            except Exception as e:
                logger.error(f"Error training model for {symbol}: {e}", exc_info=True)


def main():
    predictor = PricePredictor()

    symbols = settings.symbols.split(',')

    for symbol in symbols:
        predictor.train_model(symbol, lookback_days=7)

    for symbol in symbols:
        prediction = predictor.predict_next_price(symbol)
        if prediction:
            logger.info(f"Prediction for {symbol}: {prediction}")


if __name__ == "__main__":
    main()
