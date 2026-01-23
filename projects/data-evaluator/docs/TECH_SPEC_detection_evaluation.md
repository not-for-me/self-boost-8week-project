# TECH_SPEC: Detection Evaluation Module

## 개요

fin-stat-table-detector의 테이블 탐지 결과를 Label Studio에서 검수한 Ground Truth와 비교하여 Detection 성능을 평가하는 모듈.

## 입력 데이터

### 1. Predictions (모델 예측)
- **소스**: fin-stat-table-detector의 Label Studio JSON export
- **형식**: Label Studio predictions format
```json
{
  "data": {"image": "page_1.png"},
  "predictions": [{
    "model_version": "ensemble-v1",
    "result": [{
      "type": "rectanglelabels",
      "value": {
        "x": 10.5,
        "y": 20.3,
        "width": 80.0,
        "height": 30.0,
        "rectanglelabels": ["income_statement"]
      }
    }]
  }]
}
```

### 2. Ground Truth (정답지)
- **소스**: Label Studio에서 수동 검수 완료된 annotations export
- **형식**: Label Studio annotations format
```json
{
  "data": {"image": "page_1.png"},
  "annotations": [{
    "result": [{
      "type": "rectanglelabels",
      "value": {
        "x": 10.0,
        "y": 20.0,
        "width": 81.0,
        "height": 31.0,
        "rectanglelabels": ["income_statement"]
      }
    }]
  }]
}
```

## 평가 메트릭

### Detection Metrics (bbox 평가)

#### IoU (Intersection over Union)
```
IoU = Area of Intersection / Area of Union
```

#### 매칭 로직
- 각 prediction bbox에 대해 모든 ground truth bbox와 IoU 계산
- IoU >= threshold (default: 0.5)이면 매칭
- 하나의 GT는 하나의 prediction에만 매칭 (greedy matching)

#### 평가 지표
| 지표 | 정의 | 의미 |
|------|------|------|
| TP (True Positive) | IoU >= threshold인 prediction | 정확히 탐지 |
| FP (False Positive) | IoU < threshold인 prediction | 잘못 탐지 |
| FN (False Negative) | 매칭되지 않은 GT | 누락 |
| Precision | TP / (TP + FP) | 탐지한 것 중 맞은 비율 |
| Recall | TP / (TP + FN) | 실제 테이블 중 찾은 비율 |
| F1 Score | 2 * P * R / (P + R) | Precision/Recall 조화평균 |

### Classification Metrics (카테고리 평가)

Detection이 매칭된 경우에만 카테고리 정확도 계산:
- 매칭된 (pred, gt) 쌍에서 label 일치 여부
- Category Accuracy = 일치 수 / 매칭 수

## 핵심 컴포넌트

### 1. Models (`models.py`)
```python
@dataclass
class BBox:
    x: float      # 퍼센트 (0-100)
    y: float
    width: float
    height: float

@dataclass
class Detection:
    bbox: BBox
    label: str
    source: str   # "prediction" or "ground_truth"

@dataclass
class EvaluationResult:
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    category_accuracy: float | None
    matched_pairs: list[tuple[Detection, Detection]]
```

### 2. IoU Calculator (`metrics/iou.py`)
```python
def calculate_iou(bbox1: BBox, bbox2: BBox) -> float:
    """두 bbox의 IoU 계산."""

def calculate_intersection_area(bbox1: BBox, bbox2: BBox) -> float:
    """교집합 영역 계산."""

def calculate_union_area(bbox1: BBox, bbox2: BBox) -> float:
    """합집합 영역 계산."""
```

### 3. Label Studio Parser (`parsers/label_studio.py`)
```python
def parse_predictions(json_data: list[dict]) -> dict[str, list[Detection]]:
    """Label Studio predictions JSON 파싱.

    Returns:
        {image_path: [Detection, ...]}
    """

def parse_annotations(json_data: list[dict]) -> dict[str, list[Detection]]:
    """Label Studio annotations JSON 파싱."""
```

### 4. Evaluator (`evaluator.py`)
```python
class DetectionEvaluator:
    def __init__(self, iou_threshold: float = 0.5):
        self.iou_threshold = iou_threshold

    def evaluate_page(
        self,
        predictions: list[Detection],
        ground_truths: list[Detection],
    ) -> EvaluationResult:
        """단일 페이지 평가."""

    def evaluate_dataset(
        self,
        predictions: dict[str, list[Detection]],
        ground_truths: dict[str, list[Detection]],
    ) -> EvaluationResult:
        """전체 데이터셋 평가."""
```

## 디렉토리 구조

```
data-evaluator/
├── docs/
│   └── TECH_SPEC_detection_evaluation.md
├── src/
│   └── data_evaluator/
│       ├── __init__.py
│       ├── models.py              # 데이터 모델
│       ├── metrics/
│       │   ├── __init__.py
│       │   └── iou.py             # IoU 계산
│       ├── parsers/
│       │   ├── __init__.py
│       │   └── label_studio.py    # Label Studio JSON 파싱
│       └── evaluator.py           # 평가 로직
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_iou.py
│   ├── test_label_studio_parser.py
│   └── test_evaluator.py
└── pyproject.toml
```

## 사용 예시

```python
from data_evaluator import DetectionEvaluator
from data_evaluator.parsers import parse_predictions, parse_annotations

# JSON 파일 로드
with open("predictions.json") as f:
    pred_data = json.load(f)
with open("ground_truth.json") as f:
    gt_data = json.load(f)

# 파싱
predictions = parse_predictions(pred_data)
ground_truths = parse_annotations(gt_data)

# 평가
evaluator = DetectionEvaluator(iou_threshold=0.5)
result = evaluator.evaluate_dataset(predictions, ground_truths)

print(f"Precision: {result.precision:.2%}")
print(f"Recall: {result.recall:.2%}")
print(f"F1 Score: {result.f1:.2%}")
```

## 향후 확장

1. **mAP (mean Average Precision)**: 다양한 IoU threshold에서의 평균 정밀도
2. **Per-category metrics**: 카테고리별 성능 분석
3. **Visualization**: 시각화 리포트 생성
4. **CLI**: 커맨드라인 인터페이스
