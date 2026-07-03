import pathlib
import tempfile
from datetime import date

from wc2026.features.pipeline import run_feature_pipeline


def test_run_feature_pipeline():
    with tempfile.TemporaryDirectory() as td:
        csv_path = pathlib.Path(td) / "results.csv"
        db_path = pathlib.Path(td) / "features.duckdb"
        
        # Write dummy CSV
        csv_path.write_text("date,home_team,away_team,home_score,away_score,tournament,city,country,neutral\n2026-06-01,TeamA,TeamB,1,0,FIFA World Cup,City,Country,True\n")
        
        res = run_feature_pipeline(
            results_csv_path=csv_path,
            db_path=db_path,
            cutoff_date=date(2026, 6, 2),
            overwrite=True
        )
        assert res['matches_processed'] == 1
        assert res['features_written'] > 0
        
        # Test overwrite=False
        res2 = run_feature_pipeline(
            results_csv_path=csv_path,
            db_path=db_path,
            cutoff_date=date(2026, 6, 2),
            overwrite=False
        )
        assert res2['matches_processed'] == 0
