"""Tests for Label Studio JSON parser."""

import pytest

from data_evaluator.models import DetectionSource
from data_evaluator.parsers.label_studio import parse_annotations, parse_predictions


class TestParsePredictions:
    """Tests for parse_predictions function."""

    def test_parses_single_prediction(self) -> None:
        """Given valid prediction data, should parse correctly."""
        json_data = [
            {
                "data": {"image": "page_1.png"},
                "predictions": [
                    {
                        "model_version": "ensemble-v1",
                        "result": [
                            {
                                "type": "rectanglelabels",
                                "value": {
                                    "x": 10.0,
                                    "y": 20.0,
                                    "width": 30.0,
                                    "height": 40.0,
                                    "rectanglelabels": ["income_statement"],
                                },
                            }
                        ],
                    }
                ],
            }
        ]

        result = parse_predictions(json_data)

        assert "page_1.png" in result
        assert len(result["page_1.png"]) == 1
        detection = result["page_1.png"][0]
        assert detection.bbox.x == 10.0
        assert detection.bbox.y == 20.0
        assert detection.bbox.width == 30.0
        assert detection.bbox.height == 40.0
        assert detection.label == "income_statement"
        assert detection.source == DetectionSource.PREDICTION

    def test_parses_multiple_predictions_per_image(self) -> None:
        """Given multiple predictions for one image, should parse all."""
        json_data = [
            {
                "data": {"image": "page_1.png"},
                "predictions": [
                    {
                        "result": [
                            {
                                "type": "rectanglelabels",
                                "value": {
                                    "x": 10.0,
                                    "y": 20.0,
                                    "width": 30.0,
                                    "height": 40.0,
                                    "rectanglelabels": ["income_statement"],
                                },
                            },
                            {
                                "type": "rectanglelabels",
                                "value": {
                                    "x": 50.0,
                                    "y": 60.0,
                                    "width": 20.0,
                                    "height": 30.0,
                                    "rectanglelabels": ["balance_sheet"],
                                },
                            },
                        ],
                    }
                ],
            }
        ]

        result = parse_predictions(json_data)

        assert len(result["page_1.png"]) == 2
        labels = {d.label for d in result["page_1.png"]}
        assert labels == {"income_statement", "balance_sheet"}

    def test_parses_multiple_images(self) -> None:
        """Given multiple images, should parse all separately."""
        json_data = [
            {
                "data": {"image": "page_1.png"},
                "predictions": [
                    {
                        "result": [
                            {
                                "type": "rectanglelabels",
                                "value": {
                                    "x": 10.0,
                                    "y": 20.0,
                                    "width": 30.0,
                                    "height": 40.0,
                                    "rectanglelabels": ["income_statement"],
                                },
                            }
                        ],
                    }
                ],
            },
            {
                "data": {"image": "page_2.png"},
                "predictions": [
                    {
                        "result": [
                            {
                                "type": "rectanglelabels",
                                "value": {
                                    "x": 5.0,
                                    "y": 10.0,
                                    "width": 90.0,
                                    "height": 80.0,
                                    "rectanglelabels": ["balance_sheet"],
                                },
                            }
                        ],
                    }
                ],
            },
        ]

        result = parse_predictions(json_data)

        assert len(result) == 2
        assert "page_1.png" in result
        assert "page_2.png" in result

    def test_skips_task_without_image(self) -> None:
        """Given task without image data, should skip it."""
        json_data = [
            {
                "data": {},
                "predictions": [
                    {
                        "result": [
                            {
                                "type": "rectanglelabels",
                                "value": {
                                    "x": 10.0,
                                    "y": 20.0,
                                    "width": 30.0,
                                    "height": 40.0,
                                    "rectanglelabels": ["income_statement"],
                                },
                            }
                        ],
                    }
                ],
            }
        ]

        result = parse_predictions(json_data)

        assert len(result) == 0

    def test_skips_non_rectanglelabels_type(self) -> None:
        """Given non-rectanglelabels type, should skip it."""
        json_data = [
            {
                "data": {"image": "page_1.png"},
                "predictions": [
                    {
                        "result": [
                            {
                                "type": "textarea",
                                "value": {"text": ["some text"]},
                            }
                        ],
                    }
                ],
            }
        ]

        result = parse_predictions(json_data)

        assert "page_1.png" in result
        assert len(result["page_1.png"]) == 0

    def test_handles_empty_predictions(self) -> None:
        """Given empty predictions, should return empty list for image."""
        json_data = [
            {
                "data": {"image": "page_1.png"},
                "predictions": [],
            }
        ]

        result = parse_predictions(json_data)

        assert "page_1.png" in result
        assert len(result["page_1.png"]) == 0

    def test_uses_unknown_label_when_missing(self) -> None:
        """Given missing labels, should use 'unknown'."""
        json_data = [
            {
                "data": {"image": "page_1.png"},
                "predictions": [
                    {
                        "result": [
                            {
                                "type": "rectanglelabels",
                                "value": {
                                    "x": 10.0,
                                    "y": 20.0,
                                    "width": 30.0,
                                    "height": 40.0,
                                    "rectanglelabels": [],
                                },
                            }
                        ],
                    }
                ],
            }
        ]

        result = parse_predictions(json_data)

        assert result["page_1.png"][0].label == "unknown"


class TestParseAnnotations:
    """Tests for parse_annotations function."""

    def test_parses_single_annotation(self) -> None:
        """Given valid annotation data, should parse correctly."""
        json_data = [
            {
                "data": {"image": "page_1.png"},
                "annotations": [
                    {
                        "result": [
                            {
                                "type": "rectanglelabels",
                                "value": {
                                    "x": 10.0,
                                    "y": 20.0,
                                    "width": 30.0,
                                    "height": 40.0,
                                    "rectanglelabels": ["income_statement"],
                                },
                            }
                        ],
                    }
                ],
            }
        ]

        result = parse_annotations(json_data)

        assert "page_1.png" in result
        assert len(result["page_1.png"]) == 1
        detection = result["page_1.png"][0]
        assert detection.source == DetectionSource.GROUND_TRUTH

    def test_parses_multiple_annotations_per_image(self) -> None:
        """Given multiple annotations for one image, should parse all."""
        json_data = [
            {
                "data": {"image": "page_1.png"},
                "annotations": [
                    {
                        "result": [
                            {
                                "type": "rectanglelabels",
                                "value": {
                                    "x": 10.0,
                                    "y": 20.0,
                                    "width": 30.0,
                                    "height": 40.0,
                                    "rectanglelabels": ["income_statement"],
                                },
                            },
                            {
                                "type": "rectanglelabels",
                                "value": {
                                    "x": 50.0,
                                    "y": 60.0,
                                    "width": 20.0,
                                    "height": 30.0,
                                    "rectanglelabels": ["cash_flow_statement"],
                                },
                            },
                        ],
                    }
                ],
            }
        ]

        result = parse_annotations(json_data)

        assert len(result["page_1.png"]) == 2

    def test_handles_empty_json(self) -> None:
        """Given empty JSON array, should return empty dict."""
        result = parse_annotations([])

        assert result == {}

    def test_skips_incomplete_bbox_data(self) -> None:
        """Given incomplete bbox data, should skip that result."""
        json_data = [
            {
                "data": {"image": "page_1.png"},
                "annotations": [
                    {
                        "result": [
                            {
                                "type": "rectanglelabels",
                                "value": {
                                    "x": 10.0,
                                    "y": 20.0,
                                    # missing width and height
                                    "rectanglelabels": ["income_statement"],
                                },
                            }
                        ],
                    }
                ],
            }
        ]

        result = parse_annotations(json_data)

        assert "page_1.png" in result
        assert len(result["page_1.png"]) == 0
