import os
import json
import gradio as gr
import numpy as np
from PIL import Image
from src.pipeline.prediction_pipeline import PredictionPipeline

# Initialize the inference pipeline
pipeline = PredictionPipeline()

PRODUCE_INFO = {
    "Apple": {"emoji": "🍎", "type": "Fruit", "tip": "Store in the refrigerator crisper drawer to maintain crispness for 4–6 weeks."},
    "Banana": {"emoji": "🍌", "type": "Fruit", "tip": "Keep at room temperature away from direct sunlight; wrap stems in foil to slow ripening."},
    "Bellpepper": {"emoji": "🫑", "type": "Vegetable", "tip": "Keep completely dry in the crisper drawer; use within 1–2 weeks."},
    "Carrot": {"emoji": "🥕", "type": "Vegetable", "tip": "Trim leafy tops and keep sealed in a perforated bag in the fridge crisper."},
    "Cucumber": {"emoji": "🥒", "type": "Vegetable", "tip": "Store on upper refrigerator shelves to protect from extreme cold damage."},
    "Mango": {"emoji": "🥭", "type": "Fruit", "tip": "Ripen at room temperature, then refrigerate for up to 5 days once soft."},
    "Orange": {"emoji": "🍊", "type": "Fruit", "tip": "Good at room temperature for 1 week, or in the fridge for 3–4 weeks."},
    "Potato": {"emoji": "🥔", "type": "Vegetable", "tip": "Store in a cool, dark, dry area; keep separated from onions and apples."},
    "Strawberry": {"emoji": "🍓", "type": "Fruit", "tip": "Keep unwashed in a paper-towel lined container in the fridge."},
    "Tomato": {"emoji": "🍅", "type": "Vegetable", "tip": "Store stem-side down at room temperature; refrigeration diminishes sweetness and aroma."},
}

def format_verdict_html(result):
    if not result:
        return """
        <div style="padding: 2.5rem; text-align: center; border: 2px dashed #334155; border-radius: 1rem; color: #94a3b8; background: rgba(15, 23, 42, 0.4);">
            <div style="font-size: 2.5rem; margin-bottom: 0.75rem;">📷</div>
            <div style="font-size: 1.15rem; font-weight: 600; color: #cbd5e1;">Awaiting Produce Image</div>
            <div style="font-size: 0.9rem; margin-top: 0.25rem;">Snap a picture using your camera or upload an image file to begin analysis.</div>
        </div>
        """

    cat_data = result["category"]
    fresh_data = result["freshness"]
    cat_label = cat_data["label"]
    fresh_label = fresh_data["label"]
    cat_score = cat_data["score"]
    fresh_score = fresh_data["score"]

    is_fresh = fresh_label.lower() == "fresh"
    info = PRODUCE_INFO.get(cat_label, {"emoji": "🥬", "type": "Produce", "tip": "Store in a cool, dry place."})

    status_theme = {
        "badge_bg": "rgba(16, 185, 129, 0.15)",
        "badge_border": "#10b981",
        "badge_text": "#34d399",
        "title": "FRESH & WHOLESOME",
        "icon": "🌿",
        "desc": "Optimal condition detected. Safe, nutritious, and ready for consumption or culinary use.",
        "bar_fill": "linear-gradient(90deg, #10b981, #059669)",
    } if is_fresh else {
        "badge_bg": "rgba(239, 68, 68, 0.15)",
        "badge_border": "#ef4444",
        "badge_text": "#f87171",
        "title": "SPOILED / ROTTEN",
        "icon": "⚠️",
        "desc": "Decay, mold, or cellular breakdown detected. Consumption is not recommended.",
        "bar_fill": "linear-gradient(90deg, #f87171, #dc2626)",
    }

    fresh_pct = f"{fresh_score * 100:.1f}%"
    cat_pct = f"{cat_score * 100:.1f}%"

    html = f"""
    <div style="display: flex; flex-direction: column; gap: 1rem; font-family: system-ui, -apple-system, sans-serif;">
        <!-- Freshness Status Hero Card -->
        <div style="background: {status_theme['badge_bg']}; border: 1.5px solid {status_theme['badge_border']}; border-radius: 1rem; padding: 1.25rem; box-shadow: 0 8px 24px -6px rgba(0,0,0,0.3);">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                <span style="font-size: 0.8rem; font-weight: 700; letter-spacing: 0.05em; color: {status_theme['badge_text']}; text-transform: uppercase;">
                    {status_theme['icon']} Freshness Verdict
                </span>
                <span style="font-size: 1.15rem; font-weight: 800; color: #ffffff;">{fresh_pct} Match</span>
            </div>
            <div style="font-size: 1.6rem; font-weight: 900; color: #ffffff; margin-bottom: 0.35rem; display: flex; align-items: center; gap: 0.5rem;">
                {status_theme['title']}
            </div>
            <!-- Progress Bar -->
            <div style="width: 100%; height: 8px; background: rgba(255,255,255,0.1); border-radius: 9999px; overflow: hidden; margin-bottom: 0.75rem;">
                <div style="width: {fresh_pct}; height: 100%; background: {status_theme['bar_fill']}; border-radius: 9999px;"></div>
            </div>
            <p style="font-size: 0.9rem; color: #e2e8f0; margin: 0; line-height: 1.4;">
                {status_theme['desc']}
            </p>
        </div>

        <!-- Produce Category Card -->
        <div style="background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 1rem; padding: 1.25rem;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                <span style="font-size: 0.8rem; font-weight: 700; letter-spacing: 0.05em; color: #38bdf8; text-transform: uppercase;">
                    Produce Identification
                </span>
                <span style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 9999px; border: 1px solid rgba(56, 189, 248, 0.3);">
                    {info['type']}
                </span>
            </div>
            <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem;">
                <span style="font-size: 2.2rem;">{info['emoji']}</span>
                <div>
                    <div style="font-size: 1.4rem; font-weight: 800; color: #f8fafc;">{cat_label}</div>
                    <div style="font-size: 0.85rem; color: #94a3b8;">Confidence: <strong style="color: #f1f5f9;">{cat_pct}</strong></div>
                </div>
            </div>
            <div style="width: 100%; height: 6px; background: rgba(255,255,255,0.1); border-radius: 9999px; overflow: hidden; margin-top: 0.25rem;">
                <div style="width: {cat_pct}; height: 100%; background: linear-gradient(90deg, #38bdf8, #0284c7); border-radius: 9999px;"></div>
            </div>
        </div>

        <!-- Shelf & Storage Recommendation -->
        <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 1rem; padding: 1.1rem; display: flex; align-items: flex-start; gap: 0.75rem;">
            <span style="font-size: 1.4rem;">💡</span>
            <div>
                <div style="font-size: 0.85rem; font-weight: 700; color: #fbbf24; text-transform: uppercase; margin-bottom: 0.2rem;">
                    Storage & Quality Tip
                </div>
                <div style="font-size: 0.85rem; color: #cbd5e1; line-height: 1.45;">
                    {info['tip']}
                </div>
            </div>
        </div>
    </div>
    """
    return html

def predict_single(image):
    if image is None:
        empty_html = format_verdict_html(None)
        return None, empty_html, {}, {}, "{}"

    img = Image.fromarray(image) if isinstance(image, np.ndarray) else image
    result = pipeline.predict(img)
    annotated_img = pipeline.annotate(img, result)

    verdict_html = format_verdict_html(result)

    # Freshness distribution for gr.Label
    fresh_score = result["freshness"]["score"]
    fresh_label = result["freshness"]["label"]
    if fresh_label == "Fresh":
        freshness_dist = {"Fresh": fresh_score, "Rotten": 1.0 - fresh_score}
    else:
        freshness_dist = {"Rotten": fresh_score, "Fresh": 1.0 - fresh_score}

    # Category distribution for gr.Label
    cat_dist = {result["category"]["label"]: result["category"]["score"]}

    clean_json = json.dumps({
        "category": result["category"],
        "freshness": result["freshness"]
    }, indent=2)

    return annotated_img, verdict_html, freshness_dist, cat_dist, clean_json

# Custom Modern Glassmorphic CSS
custom_css = """
/* Hero Header Container */
.hero-container {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(14, 165, 233, 0.12) 100%);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 1.25rem;
    padding: 1.75rem 2rem;
    margin-bottom: 1.5rem;
    text-align: center;
    backdrop-filter: blur(12px);
    box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.4);
}
.hero-title {
    font-size: 2.2rem !important;
    font-weight: 900 !important;
    background: linear-gradient(135deg, #34d399 0%, #38bdf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.4rem !important;
    letter-spacing: -0.02em;
}
.hero-subtitle {
    font-size: 1.05rem !important;
    color: #94a3b8 !important;
    max-width: 650px;
    margin: 0 auto 1.2rem auto !important;
    line-height: 1.5;
}
.produce-badges {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 0.5rem;
    margin-top: 0.5rem;
}
.produce-pill {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #e2e8f0;
    padding: 0.3rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 600;
    transition: all 0.2s ease;
}
.produce-pill:hover {
    border-color: #34d399;
    transform: translateY(-2px);
}
/* Primary Analyze Button */
.analyze-btn {
    background: linear-gradient(135deg, #059669 0%, #0284c7 100%) !important;
    color: #ffffff !important;
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 0.75rem !important;
    padding: 0.85rem 1.5rem !important;
    box-shadow: 0 10px 25px -5px rgba(5, 150, 105, 0.4) !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
.analyze-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 15px 30px -5px rgba(5, 150, 105, 0.55) !important;
}
"""

theme = gr.themes.Soft(
    primary_hue="emerald",
    secondary_hue="cyan",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"]
)

with gr.Blocks(theme=theme, css=custom_css, title="FreshScan AI • Produce Freshness & Category Classifier") as demo:
    with gr.Column():
        # Hero Banner
        gr.HTML("""
        <div class="hero-container">
            <div style="display: inline-flex; align-items: center; gap: 0.5rem; background: rgba(52, 211, 153, 0.15); border: 1px solid rgba(52, 211, 153, 0.3); padding: 0.25rem 0.85rem; border-radius: 9999px; font-size: 0.78rem; font-weight: 700; color: #34d399; margin-bottom: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;">
                <span>✨ MobileNetV2 Deep Learning</span> • <span>Live Camera & Upload</span>
            </div>
            <h1 class="hero-title">🥗 FreshScan AI</h1>
            <p class="hero-subtitle">
                Instant computer-vision analysis of fruit & vegetable freshness and category.
                Use your camera to capture live produce or upload a photo.
            </p>
            <div class="produce-badges">
                <span class="produce-pill">🍎 Apple</span>
                <span class="produce-pill">🍌 Banana</span>
                <span class="produce-pill">🫑 Bell Pepper</span>
                <span class="produce-pill">🥕 Carrot</span>
                <span class="produce-pill">🥒 Cucumber</span>
                <span class="produce-pill">🥭 Mango</span>
                <span class="produce-pill">🍊 Orange</span>
                <span class="produce-pill">🥔 Potato</span>
                <span class="produce-pill">🍓 Strawberry</span>
                <span class="produce-pill">🍅 Tomato</span>
            </div>
        </div>
        """)

        with gr.Row(equal_height=False):
            # Left Column: Input methods (Camera + Upload)
            with gr.Column(scale=5):
                with gr.Tabs():
                    with gr.Tab("📸 Camera & Upload"):
                        gr.Markdown("💡 **Take a snapshot** using your device camera or **upload / drag & drop** an image file:")
                        unified_input = gr.Image(
                            sources=["webcam", "upload", "clipboard"],
                            type="pil",
                            label="Produce Camera & Image Input",
                            height=360
                        )

                    with gr.Tab("📹 Dedicated Webcam"):
                        gr.Markdown("💡 **Direct webcam studio** for real-time snapshots:")
                        webcam_input = gr.Image(
                            sources=["webcam"],
                            type="pil",
                            label="Live Camera Feed",
                            height=360
                        )

                with gr.Row():
                    analyze_btn = gr.Button("🔍 Analyze Produce", elem_classes=["analyze-btn"], scale=3)
                    clear_btn = gr.Button("🔄 Clear", variant="secondary", scale=1)

                # Sample test images
                test_sample_path = "test_sample.jpg" if os.path.exists("test_sample.jpg") else None
                if test_sample_path:
                    gr.Examples(
                        examples=[[test_sample_path]],
                        inputs=unified_input,
                        label="💡 Quick Test Samples"
                    )

            # Right Column: Visual and structured results
            with gr.Column(scale=5):
                # Verdict Card HTML
                verdict_output = gr.HTML(format_verdict_html(None), label="Analysis Verdict")

                # Annotated Result Image
                annotated_output = gr.Image(label="Annotated Visual Result", height=320)

                with gr.Row():
                    fresh_label_out = gr.Label(num_top_classes=2, label="Freshness Confidence")
                    cat_label_out = gr.Label(num_top_classes=3, label="Category Match")

                with gr.Accordion("⚙️ Technical Details (JSON Response)", open=False):
                    json_output = gr.Code(label="API Output", language="json")

        # Event handling for Unified Input
        analyze_btn.click(
            fn=predict_single,
            inputs=unified_input,
            outputs=[annotated_output, verdict_output, fresh_label_out, cat_label_out, json_output]
        )

        # Event handling for Dedicated Webcam Input
        webcam_input.change(
            fn=predict_single,
            inputs=webcam_input,
            outputs=[annotated_output, verdict_output, fresh_label_out, cat_label_out, json_output]
        )

        # Auto-predict when an image is snapped/uploaded on the unified tab
        unified_input.change(
            fn=predict_single,
            inputs=unified_input,
            outputs=[annotated_output, verdict_output, fresh_label_out, cat_label_out, json_output]
        )

        # Clear button logic
        def clear_all():
            return None, None, format_verdict_html(None), {}, {}, "{}"

        clear_btn.click(
            fn=clear_all,
            inputs=[],
            outputs=[unified_input, annotated_output, verdict_output, fresh_label_out, cat_label_out, json_output]
        )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
