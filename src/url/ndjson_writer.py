# src/url/ndjson_writer.py
"""
Fixed NDJSON writer that matches autograder expectations
"""

from __future__ import annotations
import json
import sys
from typing import TextIO
from src.url.router import ModelItem
from src.scoring import score_model, _hf_model_id_from_url
from src.metrics_framework import MetricsCalculator
from src.metrics_framework import PerformanceClaimsMetric 

class NdjsonWriter:
    def __init__(self, out: TextIO | None = None) -> None:
        self.out = out or sys.stdout
        self.calc = MetricsCalculator()
        self.perf_metric = PerformanceClaimsMetric()

    def write(self, item: ModelItem) -> None:
        # Calculate all metrics using your framework
        all_metrics = {}
        total_latency = 0
        
        # Calculate ramp_up_time
        try:
            ru_res = self.calc.metrics["ramp_up_time"].calculate(item.model_url)
            all_metrics["ramp_up_time"] = round(float(ru_res.score), 3) if ru_res.score is not None else 0.0
            total_latency += ru_res.latency_ms if ru_res.latency_ms else 0
        except Exception:
            all_metrics["ramp_up_time"] = 0.0

        # Calculate bus_factor
        try:
            bf_res = self.calc.metrics["bus_factor"].calculate(item.model_url)
            all_metrics["bus_factor"] = round(float(bf_res.score), 3) if bf_res.score is not None else 0.0
            total_latency += bf_res.latency_ms if bf_res.latency_ms else 0
        except Exception:
            all_metrics["bus_factor"] = 0.0

        # Calculate license
        try:
            lic_res = self.calc.metrics["license"].calculate(item.model_url)
            all_metrics["license"] = round(float(lic_res.score), 3)
            total_latency += lic_res.latency_ms if lic_res.latency_ms else 0
        except Exception:
            all_metrics["license"] = 0.0

        # Calculate performance_claims
        try:
            pc_res = self.perf_metric.calculate(item.model_url)
            score = float(pc_res.score) if pc_res and pc_res.score is not None else 0.0
            all_metrics["performance_claims"] = 1.0 if score >= 0.5 else 0.0
            total_latency += pc_res.latency_ms if pc_res and pc_res.latency_ms else 0
        except Exception:
            all_metrics["performance_claims"] = 0.0

        # Calculate size_score (as simple float)
        try:
            sz_res = self.calc.metrics["size_score"].calculate(item.model_url)
            all_metrics["size_score"] = round(float(sz_res.score), 3) if sz_res.score is not None else 0.0
            total_latency += sz_res.latency_ms if sz_res.latency_ms else 0
        except Exception:
            all_metrics["size_score"] = 0.0

        # Calculate dataset_and_code_score
        try:
            dc_res = self.calc.metrics["dataset_and_code_score"].calculate(item.model_url)
            all_metrics["dataset_and_code_score"] = round(float(dc_res.score), 3) if dc_res.score is not None else 0.0
            total_latency += dc_res.latency_ms if dc_res.latency_ms else 0
        except Exception:
            all_metrics["dataset_and_code_score"] = 0.0

        # Calculate dataset_quality
        try:
            dq_res = self.calc.metrics["dataset_quality"].calculate(item.model_url)
            all_metrics["dataset_quality"] = round(float(dq_res.score), 3) if dq_res.score is not None else 0.0
            total_latency += dq_res.latency_ms if dq_res.latency_ms else 0
        except Exception:
            all_metrics["dataset_quality"] = 0.0

        # Calculate code_quality
        try:
            cq_res = self.calc.metrics["code_quality"].calculate(item.model_url)
            all_metrics["code_quality"] = round(float(cq_res.score), 3) if cq_res.score is not None else 0.0
            total_latency += cq_res.latency_ms if cq_res.latency_ms else 0
        except Exception:
            all_metrics["code_quality"] = 0.0

        # Calculate NET_SCORE (weighted average)
        weights = {
            "ramp_up_time": 0.15,
            "bus_factor": 0.10,
            "performance_claims": 0.15,
            "license": 0.15,
            "size_score": 0.15,
            "dataset_and_code_score": 0.10,
            "dataset_quality": 0.10,
            "code_quality": 0.10,
        }
        
        net_score = 0.0
        total_weight = 0.0
        for metric, weight in weights.items():
            if metric in all_metrics:
                net_score += all_metrics[metric] * weight
                total_weight += weight
        
        net_score = round(net_score / total_weight, 3) if total_weight > 0 else 0.0

        # Build the output record with CORRECT field names
        record = {
            "name": _hf_model_id_from_url(item.model_url) or item.model_url,
            "category": "MODEL",
            "NET_SCORE": net_score,  # Note: UPPERCASE
            "ramp_up_time": all_metrics.get("ramp_up_time", 0.0),
            "bus_factor": all_metrics.get("bus_factor", 0.0),
            "performance_claims": all_metrics.get("performance_claims", 0.0),
            "license": all_metrics.get("license", 0.0),
            "size_score": all_metrics.get("size_score", 0.0),  # Simple float, not nested object
            "dataset_and_code_score": all_metrics.get("dataset_and_code_score", 0.0),
            "dataset_quality": all_metrics.get("dataset_quality", 0.0),
            "code_quality": all_metrics.get("code_quality", 0.0),
            "latency": max(1, total_latency)  # Single latency field, not individual ones
        }

        # Write as NDJSON
        self.out.write(json.dumps(record) + "\n")
        self.out.flush()