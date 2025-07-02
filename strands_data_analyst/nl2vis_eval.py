import os
import json
import pickle
import pathlib
from io import StringIO
from collections import defaultdict

import jsonlines
from langchain_aws import ChatBedrock

from joblib import Parallel, delayed
from joblib_progress import joblib_progress

from viseval.evaluate import Evaluator, CheckResult, EvaluationResult, EvaluationDetail

from strands_data_analyst.agent import DataAnalystAgent
from strands_data_analyst.databases import SQLiteDB



WEBDRIVER_PATH = "/opt/homebrew/bin/chromedriver"
JUDGE_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

DATA_DIR = pathlib.Path(__file__).parent.resolve() / ".." / "data"
CACHE_DIR = DATA_DIR / "cache"

VISEVAL_CACHE_DIR = CACHE_DIR / "visEval"
VISEVAL_TESTS = DATA_DIR / "visEval_tests.jsonl"
VISEVAL_DBS = DATA_DIR / "visEval_dataset" / "databases"


def get_tests():
    for test in jsonlines.open(VISEVAL_TESTS):
        db_id = test["db_id"]
        test["dp_path"] = VISEVAL_DBS / db_id / f"{db_id}.sqlite"
        
        # Cache agent execution
        test["cache_obj"] = VISEVAL_CACHE_DIR / f"{test['id']}.pkl"

        # Cache LLM-as-a-Judge result 
        test["cache_results"] = VISEVAL_CACHE_DIR / f"{test['id']}.json"

        yield test


def execute_test(test, analyst, verbose):
    if test["cache_obj"].exists():
        if verbose: print(f"Loading cache: {test['cache_obj']}")
        output = pickle.load(open(test['cache_obj'], 'rb'))
        return output
    
    output = None
    if verbose: print("Executing: ", end='', flush=True)
    output = analyst.query("Generate a good visualization for this query: " + test["question"])
    if verbose: print()

    try:
        pickle.dump(output, open(test['cache_obj'], 'wb'))
    except Exception as e:
        print(f"Cannot pickle: {output}\n{e}")
        if test['cache_obj'].exists():
            os.remove(test['cache_obj'])
    
    return output


def execution_check(test, analyst, context, verbose):
    try:
        analyst.set_db(test["db_id"], SQLiteDB({'db_location': test["dp_path"]}))
        output = execute_test(test, analyst, verbose)
        vis = output['visualization']
        f = StringIO()
        vis.savefig(f, format="svg")
        context["svg_string"] = f.getvalue()
        return CheckResult(
            answer=True,
            aspect="code execution",
            rationale="Code executed successfully.",
        )
    except Exception as e:
        return CheckResult(answer=False, aspect="code execution", rationale=str(e))


def evaluate_test(test, analyst, verbose):
    evaluator = Evaluator(
        webdriver_path=WEBDRIVER_PATH,
        vision_model=ChatBedrock(model_id=JUDGE_MODEL_ID),
    )
    if verbose: print(f"\n# Test {test['id']} - DB {test['db_id']}\nQuestion: {test['question']}")
    if test['cache_results'].exists():
        data = json.load(open(test['cache_results']))
        return test, [CheckResult(**result) for result in data]

    context = {'library': 'matplotlib'}
    results = []
    for label, check in [
        ("Execution", lambda: [execution_check(test, analyst, context, verbose)]),
        ("Surface form check", lambda: [evaluator.surface_form_check(context)]),
        ("Deconstruction", lambda: [evaluator.deconstruction(context)]),
        ("Chart type and data check", lambda: [
            evaluator.chart_type_check(context, test['ground_truth']),
            evaluator.data_check(context, test['ground_truth'])]),
        ("Order check", lambda: [evaluator.order_check(context, test['ground_truth'])]),
        ("Readability check", lambda: evaluator.readability_evaluate(context, test['question']))
    ]:
        results = check()
        results.extend(results)
        passed = all([result.answer for result in results])
        if verbose: print(f" - {label}: {'Passed' if passed else 'Failed'}")
        if not passed:
            break
    
    json.dump(
        [result.get_json() for result in results],
        open(test['cache_results'], 'w'),
        indent=4)

    return test, results


def evaluate_parallel(tests):
    # Get an agent for each DB, to avoid repeating the DB introspection code
    agent_workers = {}
    for test in tests:
        db = test['db_id']
        if db in agent_workers: continue
        def run_db_test(test):
            analyst = DataAnalystAgent(verbose=False, always_reset=True)
            return evaluate_test(test, analyst, verbose=False)
        agent_workers[db] = run_db_test
    with joblib_progress("Running Tests", total=len(tests)):
        processed = Parallel(n_jobs=10)(delayed(agent_workers[test['db_id']])(test) for test in tests)
    return processed


def evaluate(parallel):
    print("# NL2VIS Benchmark")
    os.makedirs(VISEVAL_CACHE_DIR, exist_ok=True)
    tests = list(get_tests())
    if parallel:
        processed = evaluate_parallel(tests)
    else:
        analyst = DataAnalystAgent(verbose=False, always_reset=True)
        processed = [evaluate_test(test, analyst, verbose=True) for test in tests]

    eval_results = defaultdict(list)
    for test, results in processed:
        eval_results[test["id"]].append(results)
    
    return EvaluationResult(tests, [
                    EvaluationDetail(test_id, test_results)
                        for test_id, test_results in eval_results.items()])


if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    result = evaluate(parallel=(not args.debug))
    
    print("Scores:")
    scores = result.score()
    for check, score in scores.items():
        if check.endswith("rate"):
            formatted_score = f"{score*100:.1f}%"
        else:
            formatted_score = f"{score:.1f}"
        print(f"  {check}: {formatted_score}")

    print(f"\nPASS RATE: {scores['pass_rate']*100:.1f}%\n\n")
