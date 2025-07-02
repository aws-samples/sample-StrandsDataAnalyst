import json
import pathlib
import sqlite3
from collections import defaultdict

import pandas as pd
import jsonlines
from tqdm import tqdm


MAX_TEST_PER_DB = 1

DATA_DIR = pathlib.Path(__file__).parent.resolve() / ".." / "data"

VISEVAL_DIR = DATA_DIR / "visEval_dataset"
VISEVAL_TESTS_SRC = VISEVAL_DIR / "visEval.json"
VISEVAL_TESTS_TRG = DATA_DIR / 'visEval_tests.jsonl'
VISEVAL_DBS = VISEVAL_DIR / "databases"


def build_test_file():
    tests = list(json.load(open(VISEVAL_TESTS_SRC)).items())
    tests_by_db = defaultdict(list)
    for test_id, test_data in tqdm(tests):
        db_id = test_data['db_id']

        db = sqlite3.connect(VISEVAL_DBS / db_id / f"{db_id}.sqlite")
        sql = test_data["vis_query"]["data_part"]["sql_part"]

        try:
            results_df = pd.read_sql_query(sql, db)
            if results_df.empty:
                continue
            
            tests_by_db[db_id].append({
                'id': test_id,
                'db_id': db_id,
                'question': test_data['nl_queries'][0],
                'hardness': test_data['hardness'],
                "ground_truth": {
                    "chart": test_data["chart"],
                    "vis_obj": test_data["vis_obj"],
                    "meta_info": test_data["query_meta"][0],
                    "vis_query": sql,
                    "data": results_df.to_dict(orient='records')
                },
            })
        except Exception as e:
            print(e)

    sampled_tests = []
    for db_id, db_tests in tests_by_db.items():
        sampled_tests.extend(db_tests[:MAX_TEST_PER_DB])

    print(f"Number of Databases: {len(tests_by_db.keys())}")
    print(f"Sampled Tests: {len(sampled_tests)}")
    with jsonlines.open(VISEVAL_TESTS_TRG, mode='w') as writer:
        for test in sampled_tests:
            writer.write(test)


if __name__ == "__main__":
    build_test_file()
