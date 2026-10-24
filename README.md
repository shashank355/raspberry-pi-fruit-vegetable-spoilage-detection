# 🥗 FreshScan AI — Image-Based Food Freshness & Category Prediction System

![Banner](assets/Food%20Freshness%20Detection.jpg)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%20%7C%203.11-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![TensorFlow 2.x](https://img.shields.io/badge/TensorFlow-2.x-orange.svg?logo=tensorflow&logoColor=white)](https://tensorflow.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![HuggingFace Models](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Models-yellow.svg)](https://huggingface.co/samithcs)

---

## 📑 Table of Contents

1. [Executive Summary & Problem Statement](#1-executive-summary--problem-statement)
2. [Supported Produce Matrix](#2-supported-produce-matrix)
3. [System Architecture & End-to-End Pipeline](#3-system-architecture--end-to-end-pipeline)
4. [Deep Dive: Machine Learning Models & Training](#4-deep-dive-machine-learning-models--training)
   - [Model 1: Binary Freshness Classifier](#model-1-binary-freshness-classifier)
   - [Model 2: 10-Class Produce Category Classifier](#model-2-10-class-produce-category-classifier)
   - [Dataset Breakdown & Preprocessing Pipeline](#dataset-breakdown--preprocessing-pipeline)
   - [Evaluation Metrics & Performance Benchmarks](#evaluation-metrics--performance-benchmarks)
5. [Frontend & User Interface (HTML5, CSS3, Vanilla JS)](#5-frontend--user-interface-html5-css3-vanilla-js)
6. [Complete Project Directory Structure](#6-complete-project-directory-structure)
7. [Local Installation & Quickstart Guide](#7-local-installation--quickstart-guide)
8. [Production Deployment & Hosting Guide](#8-production-deployment--hosting-guide)
   - [Docker Containerization](#option-a-docker-recommended)
   - [Systemd Linux Daemon Service](#option-b-systemd-service-linux-vm)
   - [Nginx Reverse Proxy with HTTPS](#option-c-nginx-reverse-proxy--ssl)
   - [Cloud Hosting (AWS, GCP, Render, Hugging Face)](#option-d-cloud-platforms)
9. [REST API Documentation](#9-rest-api-documentation)
10. [Presentation & Viva Q&A Guide (Evaluator Questions)](#10-presentation--viva-qa-guide-evaluator-questions)
11. [Known Limitations & Future Roadmap](#11-known-limitations--future-roadmap)
12. [License & Acknowledgments](#12-license--acknowledgments)

---

## 1. Executive Summary & Problem Statement

Perishable food degradation—specifically in fruits and vegetables—accounts for billions of dollars in global agricultural loss and municipal food waste annually. Traditional manual freshness inspection in supermarkets, warehouses, and domestic kitchens is **subjective, labor-intensive, error-prone, and non-scalable**.

**FreshScan AI** is an end-to-end, real-time computer vision system that classifies produce items into their botanical categories while simultaneously determining their quality state (**Fresh** vs. **Rotten**).

### What the System Delivers:
- **Instant Produce Identification**: Accurately classifies 10 common fruits and vegetables with **99.91% test accuracy**.
- **Automated Freshness Inspection**: Determines spoilage vs. peak freshness with **98.31% test accuracy**.
- **Real-Time Camera Integration**: Interactive browser-based camera feed with target reticles, animated laser scanning, and snapshot capture.
- **Micro-Shelf-Life Guidance**: Produces tailored storage tips and consumption recommendations based on the detected item and condition.
- **Developer-Ready REST API**: High-throughput FastAPI backend with OpenAPI/Swagger documentation and instant base64 annotated image rendering.

---

## 2. Supported Produce Matrix

The dual-classifier system is trained and calibrated to recognize **10 distinct produce categories** across **2 quality states** (20 total combinations):

| Produce Type | Item Name | Emoji | Fresh State | Rotten / Spoiled State |
|:---|:---|:---:|:---|:---|
| **Vegetable** | **Bell Pepper** | 🫑 | Crisp, glossy skin, firm structure | Wrinkling, soft spots, mold patches |
| **Vegetable** | **Carrot** | 🥕 | Firm, bright orange, rigid body | Soft/bendy, dark rot rings, white mold |
| **Vegetable** | **Cucumber** | 🥒 | Firm, uniform green, stiff texture | Yellowing, mushy ends, water loss |
| **Vegetable** | **Potato** | 🥔 | Solid flesh, smooth surface | Green spots (solanine), sprouting, dark rot |
| **Vegetable** | **Tomato** | 🍅 | Bright red/pink, intact taut skin | Cracking, mold spots, collapsed watery flesh |
| **Fruit** | **Apple** | 🍎 | Smooth taut skin, vibrant color | Brown soft spots, fungal lesions |
| **Fruit** | **Banana** | 🍌 | Bright yellow or green-yellow | Blackened skin, structural collapse |
| **Fruit** | **Mango** | 🥭 | Rich yellow-red, uniform firmness | Black decay spots, sunken skin |
| **Fruit** | **Orange** | 🍊 | Taut textured rind, bright color | Green/blue penicillium mold, softening |
| **Fruit** | **Strawberry** | 🍓 | Deep red, glossy, green calyx | Gray mold (Botrytis), deflation, bruising |

---

## 3. System Architecture & End-to-End Pipeline

```
┌────────────────────────────────────────────────────────────────────────┐
│                        IMAGE ACQUISITION                               │
│  - Live Webcam Stream (getUserMedia)  /  File Dropzone  /  Clipboard   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP Multipart Form-Data
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    PREPROCESSING ENGINE (FastAPI)                      │
│  1. Read stream via PIL & convert RGBA / 4-channel to 3-channel RGB    │
│  2. Bilinear resize to target dimension: (224, 224)                    │
│  3. Pixel rescaling to range [0.0, 1.0]: img_array / 255.0             │
│  4. Dimension expansion: (1, 224, 224, 3)                              │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
                    ▼                                ▼
┌──────────────────────────────────────┐ ┌───────────────────────────────┐
│     CATEGORY CLASSIFIER MODEL        │ │     FRESHNESS CLASSIFIER      │
│  - Architecture: MobileNetV2 Base    │ │  - Architecture: MobileNetV2  │
│  - GlobalAveragePooling2D            │ │  - GlobalAveragePooling2D     │
│  - Dense(128, ReLU) + Dropout(0.3)   │ │  - Dense(2, Softmax)          │
│  - Dense(10, Softmax)                │ │  - Output: [P(Fresh), P(Rot)] │
│  - Output: 10 Class Probabilities    │ │                               │
└───────────────────┬──────────────────┘ └───────────────┬───────────────┘
                    │                                │
                    └────────────────┬───────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         POST-PROCESSING & JSON                         │
│  - Extract argmax class and probability confidence score               │
│  - Annotate image with dynamic bounding banner, label, and timestamp   │
│  - Generate base64 Data URI for instant frontend rendering             │
│  - Map category to storage tips & botanical metadata                   │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      REACTIVE FRONTEND (HTML/CSS/JS)                   │
│  - Freshness Verdict Card (Emerald Green ✅ vs. Crimson Red ⚠️)        │
│  - Category Badge & Animated Meter Bars                                │
│  - Side-by-side Visual Inspection with Modal Zoom                      │
│  - LocalStorage History Strip & Web Audio Feedback Chime               │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Deep Dive: Machine Learning Models & Training

Rather than utilizing a heavy monolithic model, the system uses an **asymmetric dual-model design**. Both models leverage **MobileNetV2** pre-trained on ImageNet as a lightweight, low-latency backbone, making CPU inference feasible at **< 90ms** per image.

### Model 1: Binary Freshness Classifier
- **Weights File**: `artifacts/models/mobilenetv2_baseline.keras` (~9.2 MB)
- **Objective**: Determine whether the produce item is in a **Fresh** or **Rotten** state.
- **Network Topology**:
  1. `Input`: `(224, 224, 3)`
  2. `Base Model`: MobileNetV2 (ImageNet weights, top omitted, frozen parameters)
  3. `GlobalAveragePooling2D`: Collapses $7 \times 7 \times 1280$ feature map to $1 \times 1280$
  4. `Dense(2, activation='softmax')`: Outputs binary distribution $[P(\text{Fresh}), P(\text{Rotten})]$
- **Training Parameters**:
  - Optimizer: `Adam(learning_rate=0.001)`
  - Loss Function: `SparseCategoricalCrossentropy()`
  - Regularization / Callbacks: `EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)`

### Model 2: 10-Class Produce Category Classifier
- **Weights File**: `artifacts/models/category_classifier.keras` (~11 MB)
- **Objective**: Identify which of the 10 produce categories the object belongs to.
- **Network Topology**:
  1. `Input`: `(224, 224, 3)`
  2. `Base Model`: MobileNetV2 (ImageNet weights, top omitted, frozen parameters)
  3. `GlobalAveragePooling2D`: $1 \times 1280$ vector
  4. `Dense(128, activation='relu')`: Feature refinement projection
  5. `Dropout(0.3)`: Prevents co-adaptation and overfitting
  6. `Dense(10, activation='softmax')`: Outputs normalized probability distribution across 10 classes
- **Training Parameters**:
  - Optimizer: `Adam(learning_rate=0.001)`
  - Loss Function: `SparseCategoricalCrossentropy()`
  - Callbacks:
    - `EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)`
    - `ReduceLROnPlateau(monitor='val_loss', factor=0.8, patience=2, min_lr=1e-5)`

### Dataset Breakdown & Preprocessing Pipeline
- **Dataset Origin**: [Kaggle Fruits and Vegetables Spoilage Dataset](https://www.kaggle.com/datasets/muhriddinmuxiddinov/fruits-and-vegetables-dataset)
- **Volume**: **12,000 images** partitioned into:
  - Fruits: 5,997 images
  - Vegetables: 6,003 images
- **Data Splits**: 70% Training (~8,400 images), 15% Validation (~1,800 images), 15% Holdout Testing (~1,800 images).
- **RGB / RGBA Standardization**: All images (including 4-channel PNGs with alpha channels and ICC profiles) are explicitly sanitized and converted to 3-channel RGB to eliminate dimensional mismatch exceptions.

### Evaluation Metrics & Performance Benchmarks

| Metric | Freshness Classifier | Category Classifier |
|:---|:---:|:---:|
| **Training Accuracy** | 98.62% | 99.86% |
| **Validation Accuracy** | 98.10% | 99.94% |
| **Holdout Test Accuracy** | **98.31%** | **99.91%** |
| **Test Loss** | `0.0645` | `0.0024` |
| **Inference Time (CPU)** | ~40 ms | ~45 ms |
| **Total Pipeline Latency** | \multicolumn{2}{c|}{**~85 - 110 ms** (including image decode and overlay)} |

---

## 5. Frontend & User Interface (HTML5, CSS3, Vanilla JS)

The UI was crafted from scratch to replace default interface frameworks with a clean, high-performance web experience.

```
frontend/
├── index.html        # Semantic HTML5 layout, video element, canvas, & dashboard
├── style.css         # Glassmorphism dark mode, laser scanning animation, & meters
├── app.js            # MediaDevices camera handling, drag-and-drop, & Web Audio
└── test_sample.jpg   # Bundled test sample (Carrot) for instant verification
```

### UI Features:
1. **Interactive Camera Viewfinder**:
   - Streams local webcam video using `navigator.mediaDevices.getUserMedia`.
   - Corner bracket reticles and an animated green laser sweep line indicating active detection.
   - Captures frames directly from `<video>` to an off-screen `<canvas>` at full camera resolution.
2. **Auto-Scan Toggle**: When enabled, the application takes periodic snapshots every 3 seconds to deliver hands-free continuous inspection.
3. **Dropzone & Clipboard Support**: Drag and drop any image or paste directly from clipboard (`Ctrl+V` / `Cmd+V`).
4. **Freshness State Theme Engine**: Dynamically re-skins the verdict card into glowing emerald green (Fresh) or warning crimson red (Rotten).
5. **Storage & Culinary Tips**: Displays practical domestic food-preservation advice tailored to the identified produce item.
6. **Recent Scans Gallery**: Stores the last 8 scans in browser `localStorage`, complete with base64 thumbnail previews.
7. **Audio Feedback**: Generates dynamic frequency chimes via the Web Audio API on successful inference.

---

## 6. Complete Project Directory Structure

```
vegies_classifier/
└── Image-Based-Food-Freshness-Prediction-System/
    ├── .gitignore                       # Git exclusions (.venv, artifacts/data, caches)
    ├── LICENSE                          # MIT Open Source License
    ├── Dockerfile                       # Multi-stage production container definition
    ├── requirements.txt                 # Exact pinned Python dependencies
    ├── test_sample.jpg                  # Standardized verification image (Fresh Carrot)
    ├── annotated_result.jpg             # Output image with visual overlay from last run
    ├── SETUP_GUIDE.md                   # Quick reference setup cheat-sheet
    ├── README.md                        # Complete technical documentation
    │
    ├── frontend/                        # Pure HTML5 / CSS3 / Vanilla JavaScript UI
    │   ├── index.html                   # Web app structure
    │   ├── style.css                    # Glassmorphism UI & responsive styling
    │   ├── app.js                       # Camera controller & async REST consumer
    │   └── test_sample.jpg              # Bundled sample image for quick UI demo
    │
    ├── artifacts/                       # Pre-trained models & generated assets
    │   └── models/
    │       ├── category_classifier.keras       # MobileNetV2 10-class model (~11 MB)
    │       ├── mobilenetv2_baseline.keras      # MobileNetV2 freshness model (~9.2 MB)
    │       └── category_labels.json            # 10 class labels list
    │
    ├── src/                             # Core Python application package
    │   ├── config.py                    # Global path constants & label configurations
    │   ├── utils.py                     # Directory creation & image helper utilities
    │   │
    │   ├── api/
    │   │   └── main.py                  # FastAPI server, REST routes, & static mount
    │   │
    │   ├── pipeline/
    │   │   ├── prediction_pipeline.py   # Dual-model inference & image annotation
    │   │   └── training_pipeline.py     # End-to-end data training orchestrator
    │   │
    │   ├── components/
    │   │   ├── data_ingestion.py        # Kaggle dataset extraction
    │   │   ├── data_transformation.py   # Preprocessing & image sanitation
    │   │   ├── model_trainer.py         # Freshness classifier training routine
    │   │   ├── category_trainer.py      # Category classifier training routine
    │   │   ├── model_evaluation.py      # ROC/AUC & confusion matrix calculation
    │   │   └── category_model_evaluation.py
    │   │
    │   └── app/
    │       └── app.py                   # Legacy Gradio application (fallback)
    │
    ├── notebooks/                       # Exploratory Data Analysis & experiments
    │   ├── 01_data_exploration.ipynb    # Distribution & resolution EDA
    │   ├── 02_train_classifier.ipynb    # Interactive training prototyping
    │   └── 03_model_evaluation.ipynb    # Evaluation plots & ROC curves
    │
    └── assets/                          # Documentation screenshots, confusion matrices
        ├── Food Freshness Detection.jpg
        ├── category_confusion_matrix.png
        ├── confusion_matrix.png
        ├── roc_curves.png
        └── category_roc_curves.png
```

---

## 7. Local Installation & Quickstart Guide

### Prerequisites
- **Python**: Version 3.10 or 3.11 (Python 3.10.12 tested and verified)
- **Git**: Installed and available in terminal
- **Operating System**: Linux (Ubuntu/Debian), macOS, or Windows 10/11

### Step 1: Clone the Repository
```bash
git clone https://github.com/samithcsachi/Image-Based-Food-Freshness-Prediction-System.git
cd Image-Based-Food-Freshness-Prediction-System
```

### Step 2: Create and Activate Virtual Environment
**Linux / macOS:**
```bash
python3.10 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```bash
pip install --upgrade pip
pip install --only-binary=:all: -r requirements.txt || pip install --prefer-binary -r requirements.txt
```

### Step 4: Download Pre-Trained Weights & Create Labels
```bash
# Create models directory
mkdir -p artifacts/models

# Download Freshness Classifier (MobileNetV2, ~9.2 MB)
curl -L -o artifacts/models/mobilenetv2_baseline.keras \
  https://huggingface.co/samithcs/Classifier_Fruits_Vegetables/resolve/main/mobilenetv2_baseline.keras

# Download Category Classifier (MobileNetV2, ~11 MB)
curl -L -o artifacts/models/category_classifier.keras \
  https://huggingface.co/samithcs/Category_Classifier/resolve/main/category_classifier.keras

# Create category_labels.json
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

### Step 5: Start the Application Server
```bash
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

- **Open Web Application**: [http://localhost:8000](http://localhost:8000)
- **Open Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 8. Production Deployment & Hosting Guide

### Option A: Docker (Recommended)

The included `Dockerfile` builds a lightweight container with OpenCV, curl, and TensorFlow dependencies.

```bash
# Build the Docker image
docker build -t freshscan-ai:latest .

# Run container on port 8000
docker run -d --name freshscan -p 8000:8000 --restart unless-stopped freshscan-ai:latest

# Check health and logs
docker logs -f freshscan
```

### Option B: Systemd Service (Linux VM)

To run the application as a background service that automatically restarts on boot:

1. Create service unit `/etc/systemd/system/freshscan.service`:
```ini
[Unit]
Description=FreshScan AI - Food Freshness Prediction System
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/Image-Based-Food-Freshness-Prediction-System
ExecStart=/home/ubuntu/Image-Based-Food-Freshness-Prediction-System/venv/bin/python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

2. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable freshscan
sudo systemctl start freshscan
sudo systemctl status freshscan
```

### Option C: Nginx Reverse Proxy + SSL

To expose the application safely on domain `freshscan.yourdomain.com`:

```nginx
server {
    server_name freshscan.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 25M;
    }
}
```
Obtain free SSL certificate via Certbot:
```bash
sudo certbot --nginx -d freshscan.yourdomain.com
```

### Option D: Cloud Platforms

| Platform | Recommended Setup | Free Tier / Specs |
|:---|:---|:---|
| **Render** | Deploy as Docker Web Service (Point to GitHub repo) | Free / 512MB RAM ($7 Starter recommended for TF) |
| **Hugging Face Spaces** | Create a `Docker` Space, push repository directly | Free (2 vCPU, 16GB RAM) |
| **AWS EC2** | `t3.medium` or `t3.large` running Ubuntu 22.04 | 2 vCPUs, 4GB RAM (~$30/mo) |
| **Railway** | Deploy via Dockerfile | Pay-as-you-go based on CPU/RAM usage |

---

## 9. REST API Documentation

### 1. Predict Freshness & Category
- **Endpoint**: `POST /predict/image`
- **Content-Type**: `multipart/form-data`
- **Parameters**: `image` (binary file: JPG, PNG, WEBP)

**cURL Request:**
```bash
curl -X POST "http://localhost:8000/predict/image" \
  -H "accept: application/json" \
  -F "image=@test_sample.jpg"
```

**JSON Response:**
```json
{
  "category": {
    "label": "Carrot",
    "idx": 3,
    "score": 1.0
  },
  "freshness": {
    "label": "Fresh",
    "idx": 0,
    "score": 0.9999991655349731
  },
  "metadata": {
    "emoji": "🥕",
    "type": "Vegetable",
    "tip": "Trim leafy tops and keep sealed in a perforated bag in the fridge crisper."
  },
  "annotated_filepath": "annotated_result.jpg",
  "annotated_image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ..."
}
```

### 2. Get Metadata & Supported Produce
- **Endpoint**: `GET /api/metadata`
- **Response**: List of 10 supported categories, freshness classes, and botanical metadata.

---

## 10. Presentation & Viva Q&A Guide (Evaluator Questions)

Preparing for project presentations, college vivas, or technical architecture reviews? Below are answers to 10 common questions:

---

### Q1: Why did you choose MobileNetV2 rather than a heavier architecture like ResNet50 or VGG16?
> **Answer**:
> MobileNetV2 utilizes **depthwise separable convolutions** and **inverted residual bottleneck blocks with linear bottlenecks**. This reduces both computational complexity (multiply-accumulate operations) and parameter footprint (~3.5 million parameters vs. 25.6M in ResNet50 and 138M in VGG16). 
> For an edge/web produce classifier, low latency (< 100ms on commodity CPU) and low memory consumption are essential. MobileNetV2 delivers **99.9% category accuracy** and **98.3% freshness accuracy** without requiring dedicated GPU infrastructure.

---

### Q2: Why use two separate classification models instead of a single multi-output (multi-task) model?
> **Answer**:
> Decoupling the architectures into two specialized models provides key engineering and operational advantages:
> 1. **Independent Lifecycle & Retraining**: Produce categories change when expanding inventory (e.g., adding Broccoli or Grapes) without altering the visual features of general biological rot (mold, discoloration, deflation).
> 2. **Loss Balancing**: Multi-task learning requires careful loss-weight tuning ($\mathcal{L}_{\text{total}} = \alpha \mathcal{L}_{\text{cat}} + \beta \mathcal{L}_{\text{fresh}}$) to prevent one task from dominating gradients. Separate heads prevent gradient interference.
> 3. **Modularity & Fallback**: If an item is an unknown vegetable, the freshness classifier can still evaluate surface rot independently.

---

### Q3: Why did you keep the base MobileNetV2 frozen instead of fine-tuning all layers?
> **Answer**:
> The features required to distinguish produce shapes, textures, fungal spots, and peel degradation are combinations of low-level and mid-level visual features (edges, color gradients, textures) that are already captured in early-to-mid ImageNet convolutional filters.
> Training with frozen weights acts as a strong regularizer that prevents catastrophic forgetting and overfitting on our ~12,000 image dataset. Furthermore, it accelerates training from hours to minutes.

---

### Q4: How does the system handle 4-channel PNG / RGBA images or camera frames?
> **Answer**:
> Standard OpenCV and NumPy conversions often fail when encountering 4-channel RGBA images (`(H, W, 4)`), raising shape mismatches (`Expected (H, W, 3)`). 
> In both [`src/api/main.py`](file:///home/shashank/Documents/vegies_classifier/Image-Based-Food-Freshness-Prediction-System/src/api/main.py) and [`src/pipeline/prediction_pipeline.py`](file:///home/shashank/Documents/vegies_classifier/Image-Based-Food-Freshness-Prediction-System/src/pipeline/prediction_pipeline.py), our preprocessing explicitly converts any input format (PIL, NumPy array, RGBA PNG, or raw byte stream) to standard 3-channel RGB:
> ```python
> img = Image.open(file).convert("RGB")
> ```
> This prevents runtime crashes from varying camera inputs or transparent PNG uploads.

---

### Q5: What preprocessing steps are executed before feeding an image to the model?
> **Answer**:
> 1. Format conversion to RGB.
> 2. Bilinear interpolation downsampling to `(224, 224)`.
> 3. Normalization from uint8 range $[0, 255]$ to floating-point range $[0.0, 1.0]$ via `img_array / 255.0`.
> 4. Batch expansion via `np.expand_dims(..., axis=0)` producing input shape `(1, 224, 224, 3)`.

---

### Q6: How did you mitigate overfitting during training?
> **Answer**:
> 1. **Transfer Learning**: Retaining pre-trained ImageNet feature extractors.
> 2. **Dropout Regularization**: Adding a `Dropout(0.3)` layer in the category classification head.
> 3. **Early Stopping**: Monitored `val_loss` with a patience threshold of 5 epochs and automatic restoration of the best weights.
> 4. **Learning Rate Reduction**: `ReduceLROnPlateau(factor=0.8, patience=2)` to ensure stable convergence into flat minima.

---

### Q7: What are the confusion cases or limitations of this model?
> **Answer**:
> 1. **Early Stage Spoilage**: Internal rot or micro-browning that does not alter surface texture cannot be reliably caught by optical RGB cameras without hyperspectral sensors.
> 2. **Subtle Spoilage in Dark Items**: Darker produce like deep purple eggplants or dark red tomatoes can mask early mold under dim lighting.
> 3. **Out-of-Distribution Inputs**: Feeding non-produce objects (e.g., shoes, tools) will force the Softmax layer to predict the closest produce category. Implementing an out-of-distribution (OOD) threshold or background class addresses this.

---

### Q8: Why did you move away from Gradio to a pure HTML, CSS, and Vanilla JavaScript UI?
> **Answer**:
> Gradio is well-suited for ML prototyping, but has architectural limitations for client-facing applications:
> 1. **Webcam Latency & Control**: Pure HTML5 `<video>` and `<canvas>` allow fine-grained access to webcam resolutions, constraints (`facingMode`), and automated scanning loops without WebSocket overhead.
> 2. **Visual Polish & Styling**: Standard Gradio components constrain layout customization. Vanilla CSS allows custom glassmorphism, responsive grids, and micro-interactions.
> 3. **Unified Single-Port Hosting**: Serving the static UI directly through FastAPI eliminates running two separate servers, reducing resource consumption.

---

### Q9: How can this system be scaled to a commercial grocery or warehouse setting?
> **Answer**:
> 1. **Edge Deployment**: Quantize `.keras` models to **TensorFlow Lite (TFLite)** or **ONNX Runtime** with INT8 quantization, deploying on Raspberry Pi 4 / 5 or NVIDIA Jetson Nano connected to an overhead conveyor camera.
> 2. **High-Throughput Serving**: Deploy FastAPI behind an ASGI server like Gunicorn with Uvicorn workers (`gunicorn -w 4 -k uvicorn.workers.UvicornWorker`) scaled horizontally across Kubernetes pods.
> 3. **Object Detection**: Incorporate YOLOv8 or Faster R-CNN as a pre-detector to isolate multiple produce items in a single bin, then pass individual cropped bounding boxes to the freshness classifier.

---

### Q10: What metrics were used to validate the model's reliability?
> **Answer**:
> Beyond standard accuracy, the models were evaluated using **Confusion Matrices**, **Area Under the ROC Curve (AUC-ROC)**, and **Per-Class Precision/Recall**:
> - Freshness Classifier holdout test accuracy: **98.31%** (AUC > 0.99).
> - Category Classifier holdout test accuracy: **99.91%** (AUC > 0.999).
> Evaluation graphs, ROC curves, and confusion matrices are saved in [`assets/`](file:///home/shashank/Documents/vegies_classifier/Image-Based-Food-Freshness-Prediction-System/assets/).

---

## 11. Known Limitations & Future Roadmap

### Current Limitations
- **Binary Quality State**: Current classification is strictly Fresh or Rotten; it does not measure degrees of ripeness (e.g., *Underripe*, *Ripe*, *Overripe*).
- **Single Object Assumption**: Optimized for scenes with a single dominant produce item in the viewfinder.

### Future Roadmap
1. **Multi-Item Object Detection**: Implement YOLOv8 to locate and score multiple produce items in a single grocery cart or refrigerator shelf.
2. **Explainable AI (XAI)**: Integrate Grad-CAM heatmaps into the UI so users can see the exact surface regions (mold patches, bruises) driving the classification decision.
3. **Multi-Stage Ripeness Grading**: Transition from binary classification to a 5-point freshness index (Unripe $\rightarrow$ Crisp $\rightarrow$ Ripe $\rightarrow$ Aging $\rightarrow$ Spoiled).
4. **Mobile Native App**: Package the model using Flutter / React Native with TFLite for offline mobile inference.

---

## 12. License & Acknowledgments

- **Dataset**: Provided by [Muhriddin Muxiddinov on Kaggle](https://www.kaggle.com/datasets/muhriddinmuxiddinov/fruits-and-vegetables-dataset).
- **Model Backbone**: MobileNetV2 architecture provided via Keras Applications / Google Research.
- **Original Project Creator**: [Samith Chimminiyan](https://github.com/samithcsachi).
- **License**: Released under the permissive **[MIT License](LICENSE)**.
