import os
import sys
import pandas as pd
import numpy as np
import yfinance as yf
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit
import pickle

# Reconfigure stdout/stderr to handle UTF-8 printing on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass


# Ensure the models directory exists
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".models")
os.makedirs(MODELS_DIR, exist_ok=True)

def calculate_technical_indicators(df):
    """
    Calculate core technical indicators for feature engineering
    """
    df = df.copy()
    
    # Moving Averages
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    
    # MA Deviations
    df['MA_diff_5'] = (df['Close'] - df['MA5']) / df['MA5']
    df['MA_diff_10'] = (df['Close'] - df['MA10']) / df['MA10']
    df['MA_diff_20'] = (df['Close'] - df['MA20']) / df['MA20']
    df['MA_diff_60'] = (df['Close'] - df['MA60']) / df['MA60']
    
    # RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df['RSI14'] = 100 - (100 / (1 + rs))
    
    # Stochastic KD (9, 3, 3)
    low_9 = df['Low'].rolling(window=9).min()
    high_9 = df['High'].rolling(window=9).max()
    rsv = 100 * ((df['Close'] - low_9) / (high_9 - low_9 + 1e-9))
    df['K9'] = rsv.ewm(com=2, adjust=False).mean()
    df['D9'] = df['K9'].ewm(com=2, adjust=False).mean()
    
    # MACD
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']
    
    # Volume Indicators
    df['Vol_MA5'] = df['Volume'].rolling(window=5).mean()
    df['Volume_ratio'] = df['Volume'] / (df['Vol_MA5'] + 1e-9)
    
    # Price Return Momentum
    df['Return_1d'] = df['Close'].pct_change()
    df['Return_5d'] = df['Close'].pct_change(5)
    
    # Clean NaN values arising from indicators calculations
    df = df.dropna()
    return df

def train_model_for_stock(stock_id):
    """
    Train a LightGBM classifier for a specific stock code using 5 years of data.
    """
    ticker_str = f"{stock_id}.TW" # Use TWSE format
    print(f"\n=============================================")
    print(f"📊 開始訓練股票 {stock_id} ({ticker_str}) 的預測模型...")
    print(f"=============================================")
    
    # 1. Download 5 years of daily data from Yahoo Finance
    print("📡 正在從 yfinance 下載 5 年歷史日線數據...")
    try:
        # Download 5 years of data
        df = yf.download(ticker_str, period="5y")
        if df.empty or len(df) < 200:
            ticker_str = f"{stock_id}.TWO"
            print(f"📡 嘗試上櫃格式: {ticker_str}...")
            df = yf.download(ticker_str, period="5y")
    except Exception as e:
        print(f"❌ 下載數據失敗: {e}")
        return False
            
    if df.empty or len(df) < 200:
        print(f"❌ 資料量過少，無法訓練模型 (總行數: {len(df) if not df.empty else 0})")
        return False
        
    print(f"✅ 資料載入成功！共 {len(df)} 筆交易記錄。")
    
    # If df columns have a MultiIndex (sometimes yfinance returns multi-index columns), flatten them
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    # 2. Feature Engineering
    df_feat = calculate_technical_indicators(df)
    
    # 3. Label Definition
    # Target: 1 if tomorrow's Close > today's Close, else 0
    df_feat['Target'] = (df_feat['Close'].shift(-1) > df_feat['Close']).astype(int)
    
    # The last row won't have a label because we don't know tomorrow's price yet
    # We will exclude it from training but keep it for inference
    predict_target_features = df_feat.iloc[-1:].copy()
    train_data = df_feat.iloc[:-1].copy()
    
    # Define features
    features = [
        'MA_diff_5', 'MA_diff_10', 'MA_diff_20', 'MA_diff_60',
        'RSI14', 'K9', 'D9', 'MACD_hist', 'Volume_ratio',
        'Return_1d', 'Return_5d'
    ]
    
    X = train_data[features]
    y = train_data['Target']
    
    # 4. Time Series Split Training
    print("🤖 開始訓練 LightGBM 模型並進行時間序列交叉驗證...")
    tscv = TimeSeriesSplit(n_splits=5)
    
    accuracies = []
    
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
        X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
        X_val, y_val = X.iloc[val_idx], y.iloc[val_idx]
        
        model = lgb.LGBMClassifier(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=5,
            num_leaves=31,
            random_state=42,
            verbose=-1
        )
        
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(stopping_rounds=15, verbose=False)]
        )
        
        preds = model.predict(X_val)
        acc = np.mean(preds == y_val)
        accuracies.append(acc)
        # print(f"Fold {fold+1} Accuracy: {acc:.4f}")
        
    print(f"📈 平均驗證準確率 (Avg Validation Accuracy): {np.mean(accuracies):.4f}")
    
    # 5. Retrain on the entire dataset
    final_model = lgb.LGBMClassifier(
        n_estimators=150,
        learning_rate=0.03,
        max_depth=5,
        num_leaves=31,
        random_state=42,
        verbose=-1
    )
    final_model.fit(X, y)
    
    # Save the model and the features list
    model_path = os.path.join(MODELS_DIR, f"lgb_model_{stock_id}.pkl")
    model_data = {
        'model': final_model,
        'features': features,
        'last_data': df_feat.iloc[-1].to_dict() # Store last day's variables for debugging
    }
    
    with open(model_path, 'wb') as f:
        pickle.dump(model_data, f)
        
    print(f"💾 模型已成功儲存至: {model_path}")
    return True

if __name__ == "__main__":
    # 預設訓練這四隻股票的模型
    target_stocks = ["2330", "2317", "2454", "2408"]
    
    success_count = 0
    for stock in target_stocks:
        if train_model_for_stock(stock):
            success_count += 1
            
    print(f"\n🎉 訓練完成！成功訓練 {success_count}/{len(target_stocks)} 個模型。")
