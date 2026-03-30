# Stolen Cars Detection System

Web application built with Django for detecting and reporting stolen vehicles.  
The system uses YOLOv3 and EasyOCR to recognize license plates from images and videos.

## Features
- Upload images/videos of vehicles
- Detect license plates using YOLOv3
- Extract text using EasyOCR
- Store and manage reports in Django
- User authentication and dashboard

## AI Model Setup

This project uses YOLOv3 weights which are not included in the repository due to file size.

Download weights from:
https://pjreddie.com/darknet/yolo/

After downloading, place the file here:
yolov3-from-opencv-object-detection/model/weights

## Installation

1. Clone the repository:
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO

2. Create virtual environment (recommended):
python3 -m venv .venv
source .venv/bin/activate

3. Install dependencies:
pip install -r requirements.txt

4. Run the server:
python manage.py migrate
python manage.py runserver
