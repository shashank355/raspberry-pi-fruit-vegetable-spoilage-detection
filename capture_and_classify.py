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
from src.pipeline.gemini_service import GeminiQualityInspector
from src.camera import USBCameraManager
from src.events.event_manager import EventManager


def run_single_capture(
    pipeline: PredictionPipeline,
    camera: USBCameraManager,
    event_manager: EventManager,
    gemini_inspector: GeminiQualityInspector,
    output_path: str = "annotated_result.jpg",
    use_ai_pro: bool = False
):
    print("\n📸 [USB Camera] Capturing frame from external camera...")
    start_time = time.time()
    rgb_arr, pil_img = camera.capture_frame()
    capture_time = (time.time() - start_time) * 1000

    print(f"⚡ Frame captured in {capture_time:.1f}ms ({rgb_arr.shape[1]}x{rgb_arr.shape[0]})")
    print("🧠 Running Local Edge AI Freshness inference...")

    infer_start = time.time()
    result = pipeline.predict(rgb_arr)
    infer_time = (time.time() - infer_start) * 1000

    annotated = pipeline.annotate(rgb_arr, result)
    annotated.save(output_path)

    # Process through FreshScan Decision Engine (Database + MQTT + Telegram)
    decision = event_manager.process_inspection(result, annotated_img=annotated)

    cat = result["category"]
    fresh = result["freshness"]
    is_fresh = fresh["label"].lower() == "fresh"

    badge = "\033[92m[FRESH]\033[0m" if is_fresh else "\033[91m[ROTTEN / SPOILED]\033[0m"

    print("\n" + "=" * 60)
    print(f"✨ FreshScan AI 2.0 (RPi 5) Inspection Result:")
    print(f"   • Produce Category : {cat['label']} ({cat['score']*100:.1f}%)")
    print(f"   • Condition        : {badge} {fresh['label']} ({fresh['score']*100:.1f}%)")
    print(f"   • Edge Latency     : {infer_time:.1f}ms ({result['engine'].upper()})")
    print(f"   • Saved Snapshot   : {output_path}")

    # Gemini AI Pro Deep Quality Inspection (if enabled)
    if use_ai_pro:
        print("\n✨ [Gemini AI Pro] Evaluating deep multimodal quality & defects...")
        ai_pro_res = gemini_inspector.inspect_produce(pil_img, force=False, local_prediction=result)
        if ai_pro_res.get("success"):
            if ai_pro_res.get("skipped"):
                print(f"   🛡️ Token Saver   : {ai_pro_res.get('message')}")
            else:
                d = ai_pro_res["data"]
                print(f"   • Quality Grade  : \033[96m{d.get('quality_grade')}\033[0m (Score: {d.get('quality_score')}/100)")
                print(f"   • Ripeness State : {d.get('ripeness')}")
                print(f"   • Shelf Life     : ~{d.get('estimated_shelf_life_days')} days remaining")
                print(f"   • Defects Found  : {', '.join(d.get('defects', [])) if d.get('defects') else 'None observed'}")
                print(f"   • Assessment     : {d.get('detailed_summary')}")
                print(f"   • Token Cost     : {d.get('tokens_used')} tokens ({d.get('latency_ms')}ms)")
        else:
            print(f"   ⚠️ AI Pro Notice : {ai_pro_res.get('error')}")

    if decision.get("alert_created"):
        print(f"\n   🚨 SPOILAGE EVENT  : {decision['event_id']} created!")
        print(f"   📡 ESP32 Alert     : Published to LED #{decision.get('led_index')} (Blinking)")
        print(f"   ✈️  Telegram        : Alert & photograph dispatched")
    elif decision.get("is_spoiled"):
        print(f"\n   ℹ️  Duplicate Alert: Unresolved alert already active for {cat['label']} ({decision.get('event_id')})")
    print("=" * 60 + "\n")

    return result, decision


def main():
    parser = argparse.ArgumentParser(
        description="FreshScan AI 2.0 - Raspberry Pi 5 + External USB Camera + Gemini AI Pro"
    )
    parser.add_argument(
        "--output", "-o", default="annotated_result.jpg", help="Path to save annotated snapshot"
    )
    parser.add_argument(
        "--loop", "-l", action="store_true", help="Run continuous monitoring loop"
    )
    parser.add_argument(
        "--interval", "-i", type=float, default=5.0, help="Interval in seconds between loops"
    )
    parser.add_argument(
        "--engine", choices=["tflite", "keras"], default=None, help="Force specific engine"
    )
    parser.add_argument(
        "--camera-index", "-c", default=None, help="Camera device index (e.g. 2 or 'auto')"
    )
    parser.add_argument(
        "--ai-pro", action="store_true", help="Enable Gemini AI Pro quality inspection (with token saver)"
    )

    args = parser.parse_args()

    print("\n🍓 Initializing FreshScan AI 2.0 on Raspberry Pi 5...")
    camera = USBCameraManager(camera_index=args.camera_index)
    cam_status = camera.get_status()
    print(f"📷 Camera Hardware: {cam_status['sensor']} ({cam_status['device_path']})")

    pipeline = PredictionPipeline(force_engine=args.engine)
    event_manager = EventManager()
    gemini_inspector = GeminiQualityInspector()

    if args.loop:
        print(f"🔄 Starting continuous scanning loop (Interval: {args.interval}s)... Press Ctrl+C to stop.")
        try:
            while True:
                run_single_capture(
                    pipeline, camera, event_manager, gemini_inspector,
                    output_path=args.output, use_ai_pro=args.ai_pro
                )
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n🛑 Stopped continuous scanning loop.")
    else:
        run_single_capture(
            pipeline, camera, event_manager, gemini_inspector,
            output_path=args.output, use_ai_pro=args.ai_pro
        )


if __name__ == "__main__":
    main()
