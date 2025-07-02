# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
import base64
from typing import Union

import cairosvg
import pandas as pd
from attr import dataclass

from .check import (
    chart_check,
    data_check,
    deconstruct,
    layout_check,
    order_check,
    readability_check,
    scale_and_ticks_check,
    surface_form_check
)


@dataclass
class CheckResult:
    answer: Union[bool, int]
    aspect: str
    rationale: str

    def get_json(self):
        return {
            "answer": self.answer,
            "aspect": self.aspect,
            "rationale": self.rationale,
        }


@dataclass
class EvaluationDetail:
    id: str
    results: list[list[CheckResult]]


VALID_ASPECTS = {"code execution", "surface-form check"}
LEGAL_ASPECTS = {"deconstruction", "chart type check", "data check", "order check"}

PASS_ASPECTS = VALID_ASPECTS | LEGAL_ASPECTS

READABILITY_ASPECT = {"layout check", "scale and ticks check", "readability check"}

FAIL_ASPECTS = VALID_ASPECTS | LEGAL_ASPECTS | {"layout check", "scale and ticks check"}


def results_passed(results):
    return all([result.answer for result in results if result.aspect in PASS_ASPECTS])


class EvaluationResult:
    details: list[EvaluationDetail]

    def __init__(self, tests, details: list[EvaluationDetail]):
        self.tests = {test['id']: test for test in tests}
        self.details = details

    def score(self):
        records = []
        for detail in self.details:
            id = detail.id
            instance_results = detail.results
            count = len(instance_results)
            record = {
                "id": id,
                "chart": self.tests[id]["ground_truth"]["chart"],
                "hardness": self.tests[id]["hardness"],
            }

            # fail rate
            for aspect in FAIL_ASPECTS:
                evaluate_result = [
                    all([item.answer for item in query_results if item.aspect == aspect])
                        for query_results in instance_results
                ]
                fail_result = [item for item in evaluate_result if not item]
                record[f"{aspect}_fail_rate"] = len(fail_result) / count

            pass_count = count
            for rate_name, aspects in [
                    ["invalid_rate", VALID_ASPECTS],
                    ["illegal rate", LEGAL_ASPECTS]]:
                evaluate_result = [
                    all([item.answer for item in query_results if item.aspect in aspects])
                        for query_results in instance_results
                ]
                false_count = len([item for item in evaluate_result if not item])
                record[rate_name] = false_count / count
                pass_count -= false_count
                records.append(record)

            # pass rate
            record["pass_rate"] = pass_count / count
            records.append(record)

            # readability score
            evaluate_result = [
                sum([item.answer for item in query_results if item.aspect == "readability check"])
                    for query_results in instance_results
            ]
            if pass_count > 0:
                record["readability_score"] = sum(evaluate_result) / pass_count

            record["quality_score"] = sum(evaluate_result) / count

        records = pd.DataFrame(records)
        metrics = [
            "invalid_rate",
            "illegal rate",
            "pass_rate",
            "readability_score",
            "quality_score",
        ]
        score = {}
        for metric in metrics:
            score[metric] = records[metric].mean()

        for key in records.keys():
            if key not in metrics and key not in {'id', 'chart', 'hardness'}:
                score[key] = records[key].mean()

        return score


def convert_svg_to_base64(svg_string):
    png_string = cairosvg.svg2png(bytestring=svg_string)
    base64_encoded = base64.b64encode(png_string).decode("utf-8")
    return f"data:image/png;base64,{base64_encoded}"


class Evaluator:
    def __init__(self, webdriver_path=None, vision_model=None):
        self.webdriver_path = webdriver_path
        self.vision_model = vision_model

    def surface_form_check(self, context) -> CheckResult:
        answer, rationale = surface_form_check(context["svg_string"])
        return CheckResult(
            answer=answer,
            aspect="surface-form check",
            rationale=rationale,
        )

    def deconstruction(self, context) -> CheckResult:
        svg_string = context["svg_string"]
        library = context["library"]
        if library == "seaborn":
            library = "matplotlib"
        try:
            chart_info, msg = deconstruct(svg_string, library)
            if chart_info is None:
                return CheckResult(
                    answer=False,
                    aspect="deconstruction",
                    rationale=msg,
                )
            context.update(chart_info)
            return CheckResult(
                answer=True,
                aspect="deconstruction",
                rationale="Deconstructed the chart successfully.",
            )
        except Exception:
            return CheckResult(
                answer=False,
                aspect="deconstruction",
                rationale="Cannot parse the visualization.",
            )

    def chart_type_check(self, context, ground_truth) -> CheckResult:
        answer, rationale = chart_check(
            context,
            ground_truth["chart"],
            (
                ground_truth["meta_info"]["stacked_bar"]
                if "stacked_bar" in ground_truth["meta_info"]
                else None
            ),
        )
        return CheckResult(
            answer=answer,
            aspect="chart type check",
            rationale=rationale,
        )

    def data_check(self, context, ground_truth) -> CheckResult:
        answer, rationale = data_check(
            context,
            ground_truth["vis_obj"],
            ground_truth["meta_info"]["channel_specified"],
        )
        return CheckResult(
            answer=answer,
            aspect="data check",
            rationale=rationale,
        )

    def order_check(self, context, ground_truth) -> CheckResult:
        answer, rationale = order_check(
            context,
            ground_truth["vis_obj"],
            (
                ground_truth["meta_info"]["sort_by"]
                if "sort_by" in ground_truth["meta_info"]
                else None
            ),
        )
        return CheckResult(
            answer=answer,
            aspect="order check",
            rationale=rationale,
        )

    def layout_check(self, context) -> CheckResult:
        assert "svg_string" in context
        assert self.webdriver_path is not None

        answer, rationale = layout_check(context, self.webdriver_path)
        return CheckResult(
            answer=answer,
            aspect="layout check",
            rationale=rationale,
        )

    def scale_and_ticks_check(self, context, query) -> CheckResult:
        assert "base64" in context and "encoding" in context and "chart" in context
        assert self.vision_model is not None

        answer, rationale = scale_and_ticks_check(context, query, self.vision_model)
        return CheckResult(
            answer=answer,
            aspect="scale and ticks check",
            rationale=rationale,
        )

    def readability_evaluate(self, context, query: str) -> list[CheckResult]:
        results = []
        if self.webdriver_path:
            layout_result = self.layout_check(context)
            if layout_result.answer is not None:
                results.append(layout_result)

        if self.vision_model:
            context["base64"] = convert_svg_to_base64(context["svg_string"])
            scale_and_ticks_result = self.scale_and_ticks_check(context, query)
            if scale_and_ticks_result.answer is not None:
                results.append(scale_and_ticks_result)

            aspect_format = {
                "layout check": "Overflow/Overlap",
                "scale and ticks check": "Scale/Ticks",
            }
            reviews = [
                {
                    "aspect": aspect_format[result.aspect],
                    "content": result.rationale,
                }
                for result in results
            ]
            context["reviews"] = reviews

            answer, rationale = readability_check(context, query, self.vision_model)
            if answer is not None:
                readability_result = CheckResult(
                    answer=answer,
                    aspect="readability check",
                    rationale=rationale,
                )
                results.append(readability_result)

        return results
