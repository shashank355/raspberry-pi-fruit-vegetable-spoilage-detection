# Image-Based Food Freshness Prediction System — Setup & Run Guide

This guide contains everything needed to set up and run the Image-Based Food Freshness Prediction System locally, including:
1. A ready-to-paste Antigravity prompt (so Antigravity can set everything up automatically in one go, including known repo fixes).
2. Manual step-by-step instructions (macOS / Linux / Windows).

---

## Option 1: One-Shot Prompt for Antigravity (Recommended)

Copy and paste the entire block below into Antigravity on your computer:

```markdown
Set up and run the Image-Based Food Freshness Prediction System locally in the current workspace by performing the following steps:

1. **Clone the Repository**:
```bash
git clone https://github.com/samithcsachi/Image-Based-Food-Freshness-Prediction-System.git
cd Image-Based-Food-Freshness-Prediction-System
```

2. Create a Python 3.10 or 3.11 Virtual Environment & Install Dependencies:
- Locate python3.11 or python3.10 (fallback to python3).
- Create venv inside Image-Based-Food-Freshness-Prediction-System.
- Install dependencies using pre-built binary wheels (--only-binary=:all: with fallback to --prefer-binary) to avoid source compilation issues:
```bash
python3.10 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install --only-binary=:all: -r requirements.txt || ./venv/bin/pip install --prefer-binary -r requirements.txt
```

3. Download Pre-Trained MobileNetV2 Models & Category Labels: `src/pipeline/prediction_pipeline.py` expects three files inside `artifacts/models/` (note: `category_labels.json` is not in the GitHub repo, so create it explicitly):
- Create directory `artifacts/models`
- Download `mobilenetv2_baseline.keras` from Hugging Face:
  https://huggingface.co/samithcs/Classifier_Fruits_Vegetables/resolve/main/mobilenetv2_baseline.keras
- Download `category_classifier.keras` from Hugging Face:
  https://huggingface.co/samithcs/Category_Classifier/resolve/main/category_classifier.keras
- Create `artifacts/models/category_labels.json` with exact content:
```json
[
  "Apple",
  "Banana",
  "Bellpepper",
  "Carrot",
  "Cucumber",
  "Mango",
  "Orange",
  "Potato",
  "Strawberry",
  "Tomato"
]
```

4. Apply RGBA / PNG Image Compatibility Fix: By default, uploading 4-channel PNG images raises `ValueError: NumPy input must be shape (H, W, 3)`.
- In `src/api/main.py`, update `read_imagefile` to convert images to RGB:
```python
def read_imagefile(file) -> np.ndarray:
    img = Image.open(file).convert("RGB")
    return np.array(img)
```
- In `src/pipeline/prediction_pipeline.py`, update `_preprocess_image` so both 3-channel and 4-channel NumPy arrays and PIL images are converted to "RGB":
```python
elif isinstance(img, np.ndarray):
    if img.ndim == 3 and img.shape[2] in (3, 4):
        img = Image.fromarray(img).convert("RGB")
    else:
        raise ValueError("NumPy input must be shape (H, W, 3) or (H, W, 4)")
elif isinstance(img, Image.Image):
    img = img.convert("RGB")
```

5. Launch & Verify Both Servers:
- Start FastAPI backend on port 8000: `./venv/bin/python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000`
- Start Gradio web UI on port 7860: `./venv/bin/python -m src.app.app`
- Test POST `http://localhost:8000/predict/image` using `test_sample.jpg` and report the JSON output.
```

---

## Option 2: Manual Step-by-Step Setup

### 1. Clone the Repository
```bash
git clone https://github.com/samithcsachi/Image-Based-Food-Freshness-Prediction-System.git
cd Image-Based-Food-Freshness-Prediction-System
```

### 2. Create & Activate Virtual Environment
**macOS / Linux:**
```bash
python3.10 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install --only-binary=:all: -r requirements.txt || pip install --prefer-binary -r requirements.txt
```

### 4. Download Model Weights & Create `category_labels.json`
```bash
mkdir -p artifacts/models

# Download Freshness Classifier (MobileNetV2, ~9.2 MB)
curl -L -o artifacts/models/mobilenetv2_baseline.keras \
  https://huggingface.co/samithcs/Classifier_Fruits_Vegetables/resolve/main/mobilenetv2_baseline.keras

# Download Category Classifier (MobileNetV2, ~11 MB)
curl -L -o artifacts/models/category_classifier.keras \
  https://huggingface.co/samithcs/Category_Classifier/resolve/main/category_classifier.keras

# Create category_labels.json required by PredictionPipeline
cat << 'EOF' > artifacts/models/category_labels.json
[
  "Apple",
  "Banana",
  "Bellpepper",
  "Carrot",
  "Cucumber",
  "Mango",
  "Orange",
  "Potato",
  "Strawberry",
  "Tomato"
]
EOF
```

### 5. Fix PNG (RGBA) Image Upload Support
Open `src/api/main.py` and change `read_imagefile` from:
```python
def read_imagefile(file) -> np.ndarray:
    img = Image.open(file)
    return np.array(img)
```
to:
```python
def read_imagefile(file) -> np.ndarray:
    img = Image.open(file).convert("RGB")
    return np.array(img)
```

In `src/pipeline/prediction_pipeline.py`, update `_preprocess_image`:
```python
elif isinstance(img, np.ndarray):
    if img.ndim == 3 and img.shape[2] in (3, 4):
        img = Image.fromarray(img).convert("RGB")
    else:
        raise ValueError("NumPy input must be shape (H, W, 3) or (H, W, 4)")
elif isinstance(img, Image.Image):
    img = img.convert("RGB")
```

### 6. Run the Server (Web UI & REST API)

**Single Unified Web App (Port 8000):**
The application now uses a custom HTML5, CSS3, and modern JavaScript frontend with camera support and real-time inference served directly via FastAPI:

```bash
source venv/bin/activate
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

- **Web Application UI**: [http://localhost:8000/](http://localhost:8000/)
  - Real-time webcam viewfinder & snapshot capture (`getUserMedia`)
  - Drag-and-drop file upload, file browsing, and clipboard image paste (`Ctrl+V`)
  - Auto-scan mode (continuous inference every 3s)
  - Freshness verdict banner (Fresh vs Rotten) with confidence meter & quality tips
  - Annotated visual inspection & recent scan history strip
- **Interactive Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 7. Quick Test via CLI
```bash
curl -X POST "http://localhost:8000/predict/image" -F "image=@test_sample.jpg"
```

Expected response:
```json
{
  "category": {"label": "Carrot", "idx": 3, "score": 1.0},
  "freshness": {"label": "Fresh", "idx": 0, "score": 0.999991655349731},
  "annotated_filepath": "annotated_result.jpg"
}
```

### Supported Produce Classes (10 Categories × 2 Freshness States)
- **Vegetables (5)**: Bellpepper, Carrot, Cucumber, Potato, Tomato (Fresh / Rotten)
- **Fruits (5)**: Apple, Banana, Mango, Orange, Strawberry (Fresh / Rotten)
