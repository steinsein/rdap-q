# -*- coding: utf-8 -*-
"""
blocks 패키지 — 각 블록(설문 화면)을 독립 모듈로 분리.

app.py는 RENDERERS 레지스트리를 통해 step 이름으로 해당 render() 함수를 호출한다.
블록을 추가/삭제할 때는 (1) 해당 모듈을 만들고 (2) 여기 import + RENDERERS에 등록 +
(3) state.STEP_ORDER 를 수정하면 된다.
"""
from blocks import (
    intro,
    demographics,
    prediction,
    word_card,
    thermometer,
    mirror,
    social_distance,
    scenario,
    results,
)

RENDERERS = {
    "intro": intro.render,
    "demographics": demographics.render,
    "prediction": prediction.render,
    "word_card": word_card.render,
    "thermometer": thermometer.render,
    "mirror": mirror.render,
    "social_distance": social_distance.render,
    "scenario": scenario.render,
    "results": results.render,
}
