#!/usr/bin/env bash
""":"
exec python3 "$0" "$@"
"""
import sys
import os
import time
import argparse
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.pipeline.prediction_pipeline import PredictionPipeline
from src.camera import PiCameraManager
from src.events.event_manager import EventManager


def run_single_capture(
    pipeline: PredictionPipeline,
    camera: PiCameraManager,
    event_manager: EventManager,
    output_path: str = "annotated_result.jpg"
):
    print("\n📸 [Pi Camera Rev 1.3] Capturing frame...")
    start_time = time.time()
    rgb_arr, pil_img = camera.capture_frame()
    capture_time = (time.time() - start_time) * 1000

    print(f"⚡ Frame captured in {capture_time:.1f}ms ({rgb_arr.shape[1]}x{rgb_arr.shape[0]})")
    print("🧠 Running AI Freshness inference...")

    infer_start = time.time()
    result = pipeline.predict(rgb_arr)
    infer_time = (time.time() - infer_start) * 1000

    annotated = pipeline.annotate(rgb_arr, result)
    annotated.save(output_path)

    # Process through FreshScan AI 2.0 Decision Engine (Database + MQTT + Telegram)
    decision = event_manager.process_inspection(result, annotated_img=annotated)

    cat = result["category"]
    fresh = result["freshness"]
    is_fresh = fresh["label"].lower() == "fresh"

    badge = "\033[92m[FRESH]\033[0m" if is_fresh else "\033[91m[ROTTEN / SPOILED]\033[0m"

    print("\n" + "=" * 55)
    print(f"✨ FreshScan AI 2.0 Inspection Result (Engine: {result['engine'].upper()}):")
    print(f"   • Produce Category : {cat['label']} ({cat['score']*100:.1f}%)")
    print(f"   • Condition        : {badge} {fresh['label']} ({fresh['score']*100:.1f}%)")
    print(f"   • Inference Latency: {infer_time:.1f}ms")
    print(f"   • Saved Snapshot   : {output_path}")

    if decision.get("alert_created"):
        print(f"   🚨 SPOILAGE EVENT  : {decision['event_id']} created!")
        print(f"   📡 ESP32 Alert     : Published to LED #{decision.get('led_index')} (Blinking)")
        print(f"   ✈️  Telegram        : Alert & photograph queued")
    elif decision.get("is_spoiled"):
        print(f"   ℹ️  Duplicate Alert: Unresolved alert already active for {cat['label']} ({decision.get('event_id')})")
    print("=" * 55 + "\n")

    return result, decision


def main():
    parser = argparse.ArgumentParser(
        description="FreshScan AI 2.0 - Raspberry Pi 4B + Camera Rev 1.3 + ESP32 Classifier"
    )
    parser.add_argument(
        "--output", "-o", default="annotated_result.jpg", help="Path to save annotated snapshot"
    )
    parser.add_argument(
        "--loop", "-l", action="store_true", help="Run continuous monitoring loop"
    )
    parser.add_argument(
        "--interval", "-i", type=float, default=3.0, help="Interval in seconds between loops"
    )
    parser.add_argument(
        "--engine", choices=["tflite", "keras"], default=None, help="Force specific engine"
    )

    args = parser.parse_args()

    print("\n🍓 Initializing FreshScan AI 2.0 on Raspberry Pi 4B...")
    camera = PiCameraManager()
    cam_status = camera.get_status()
    print(f"📷 Camera Hardware: {cam_status['sensor']} (Backend: {cam_status['backend']})")

    pipeline = PredictionPipeline(force_engine=args.engine)
    event_manager = EventManager()

    if args.loop:
        print(f"🔄 Starting continuous scanning loop (Interval: {args.interval}s)... Press Ctrl+C to stop.")
        try:
            while True:
                run_single_capture(pipeline, camera, event_manager, args.output)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n🛑 Stopped continuous scan.")
    else:
        run_single_capture(pipeline, camera, event_manager, args.output)


if __name__ == "__main__":
    main()
