python -m backend.fetch_data
python -m backend.build_features
python -m backend.train_xgboost
python -m backend.infer_cross_sectional
python -m backend.backtest_cross_sectional
python -m backend.ensemble_alpha full_ensemble
python -m backend.backtest_ensemble
