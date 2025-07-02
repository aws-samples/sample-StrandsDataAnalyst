# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
import json

from langchain.chat_models.base import BaseChatModel
from langchain.schema import HumanMessage, SystemMessage

from .generated_json import clean_json

INSTRUCTION = """You will be provided with a visualization and its specifications. Consider the following aspect:

    - If the scale selected for the visualization is appropriate for accurate interpretation of values, avoid using unconventional scales, such as an inverted y-axis scale.
    - When axes are present, ensure that the selected ticks are appropriate for clarity, avoiding unconventional choices, such as representing counts of individual entities with floating-point ticks.


Report your findings, focusing solely on scale and tick appropriateness without considering the order.
```
    {
        "Appropriate": true/false,
        "Rationale": "reason ..."
    }
```
"""


def scale_and_ticks_check(context: dict, query: str, vision_model: BaseChatModel):
    base64 = context["base64"]
    encoding = context["encoding"]
    chart = context["chart"]
    if chart == "pie":
        ticks_desc = ""
    else:
        x_ticks = encoding["x"]["scale"]["ticks"]
        y_ticks = encoding["y"]["scale"]["ticks"]
        ticks_desc = f"Ticks extracted from the visualization:\n- x axis ticks: {','.join(x_ticks)}\n- y axis ticks: {','.join(y_ticks)}\n\n"
    
    response = vision_model.invoke([
        SystemMessage(content=INSTRUCTION),
        HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": f"Visualization specification:{query}\n\n{ticks_desc}Visualization image that has been verified for DATA and ORDER accuracy:",
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": base64,
                    }
                },
            ]
        )
    ])
    
    result = json.loads(clean_json(response.content))
    return result["Appropriate"], result["Rationale"]
