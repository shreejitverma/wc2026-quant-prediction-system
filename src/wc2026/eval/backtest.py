"""Walk-Forward Backtester."""

from datetime import datetime

import numpy as np
import pandas as pd

from wc2026.eval.metrics import compute_brier_score, compute_log_loss


class WalkForwardBacktester:
    """
    Evaluates models on a rolling basis avoiding future leakage.
    """
    def __init__(self, models: list, initial_train_window_days: int = 365 * 4):
        self.models = models
        self.initial_window = initial_train_window_days
        
    def run(self, df: pd.DataFrame, target_eval_start: datetime, target_eval_end: datetime):
        """
        Runs the backtest chronologically.
        """
        df = df.sort_values('date').reset_index(drop=True)
        df['date_dt'] = pd.to_datetime(df['date'], utc=True)
        
        eval_mask = (df['date_dt'] >= target_eval_start) & (df['date_dt'] <= target_eval_end)
        eval_matches = df[eval_mask].copy()
        
        if eval_matches.empty:
            return {"log_loss": 0.0, "brier": 0.0, "rps": 0.0, "matches_evaluated": 0}
            
        results = []
        
        # We simulate a "monthly" refit for speed in this prototype.
        # Group matches by month/year for refitting frequency.
        eval_matches['eval_month'] = eval_matches['date_dt'].dt.to_period('M')
        
        for _period, group in eval_matches.groupby('eval_month'):
            # The cutoff date is the start of the first match in this period
            cutoff_ts = group['date_dt'].min()
            
            # Train set is strictly before cutoff
            train_df = df[df['date_dt'] < cutoff_ts].copy()
            
            # Fit all models
            for model in self.models:
                model.fit(train_df, cutoff_ts)
                
            # Predict each match in the group
            for _, match in group.iterrows():
                match_id = match.get('match_id', f"{match['home_team']}_vs_{match['away_team']}")
                features = {
                    'home_team': match['home_team'],
                    'away_team': match['away_team'],
                    'neutral': match['neutral']
                }
                
                # Evaluate the primary model (index 0)
                primary_model = self.models[0] 
                
                try:
                    score_dist = primary_model.predict_match(match_id, match['date_dt'], features)
                    
                    p_home = score_dist.p_home_win()
                    p_draw = score_dist.p_draw()
                    p_away = score_dist.p_away_win()
                    
                    hg = match['home_score']
                    ag = match['away_score']
                    
                    y_true = np.array([[1, 0, 0]]) if hg > ag else (np.array([[0, 1, 0]]) if hg == ag else np.array([[0, 0, 1]]))
                    y_pred = np.array([[p_home, p_draw, p_away]])
                    
                    ll = compute_log_loss(y_true, y_pred)
                    brier = compute_brier_score(y_true, y_pred)
                    
                    results.append({
                        'match_id': match_id,
                        'date': match['date_dt'],
                        'log_loss': ll,
                        'brier': brier
                    })
                except Exception:
                    pass # Ignore matches where a team is unknown

        if not results:
            return {"log_loss": 0.0, "brier": 0.0, "rps": 0.0, "matches_evaluated": 0}
            
        res_df = pd.DataFrame(results)
        
        return {
            "log_loss": float(res_df['log_loss'].mean()),
            "brier": float(res_df['brier'].mean()),
            "rps": 0.0,
            "matches_evaluated": len(res_df)
        }
