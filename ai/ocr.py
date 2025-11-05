import os
import sys
import cv2
import numpy as np
import easyocr

# 👇 Dodaj ścieżkę do folderu YOLO (żeby znaleźć util.py)
sys.path.append('/Users/pawelplt/Desktop/stolencars/yolov3-from-opencv-object-detection')
import util

# Ścieżki do YOLOv3
MODEL_CFG_PATH = os.path.join('/Users/pawelplt/Desktop/stolencars/yolov3-from-opencv-object-detection', 'model', 'cfg', 'darknet-yolov3.cfg')
MODEL_WEIGHTS_PATH = os.path.join('/Users/pawelplt/Desktop/stolencars/yolov3-from-opencv-object-detection', 'model', 'weights', 'model.weights')
CLASS_NAMES_PATH = os.path.join('/Users/pawelplt/Desktop/stolencars/yolov3-from-opencv-object-detection', 'model', 'class.names')

# OCR reader
reader = easyocr.Reader(['en'], gpu=False)

def extract_license_plate(image_path: str) -> str | None:
    """Wykrywa tablicę rejestracyjną z jednego zdjęcia."""
    if not os.path.exists(image_path):
        print(f"[OCR] ❌ Plik nie istnieje: {image_path}")
        return None

    img = cv2.imread(image_path)
    if img is None:
        print(f"[OCR] ❌ Nie udało się wczytać obrazu: {image_path}")
        return None

    H, W, _ = img.shape

    # Wczytaj klasy YOLO
    with open(CLASS_NAMES_PATH, 'r') as f:
        class_names = [j.strip() for j in f.readlines() if len(j.strip()) > 0]

    # Załaduj model YOLO
    net = cv2.dnn.readNetFromDarknet(MODEL_CFG_PATH, MODEL_WEIGHTS_PATH)
    blob = cv2.dnn.blobFromImage(img, 1 / 255, (416, 416), (0, 0, 0), True)
    net.setInput(blob)

    detections = util.get_outputs(net)

    bboxes, class_ids, scores = [], [], []
    for detection in detections:
        bbox = detection[:4]
        xc, yc, w, h = bbox
        bbox = [int(xc * W), int(yc * H), int(w * W), int(h * H)]
        class_id = np.argmax(detection[5:])
        score = np.amax(detection[5:])
        bboxes.append(bbox)
        class_ids.append(class_id)
        scores.append(score)

    bboxes, class_ids, scores = util.NMS(bboxes, class_ids, scores)

    if bboxes is None or len(bboxes) == 0:
        print("[OCR] ❌ YOLO nie wykrył tablicy.")
        return None

    # OCR
    for bbox in bboxes:
        xc, yc, w, h = bbox
        y1, y2 = int(yc - h / 2), int(yc + h / 2)
        x1, x2 = int(xc - w / 2), int(xc + w / 2)

        plate_img = img[y1:y2, x1:x2]
        if plate_img.size == 0:
            continue

        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        output = reader.readtext(gray)

        texts = []

        for _, text, conf in output:
            if conf > 0.4:
                cleaned = text.strip().upper().replace(" ", "").replace("-", "").replace("]", "").replace("[", "")
                texts.append(cleaned)

        if texts:
            full_plate = "".join(texts)
            print(f"[OCR] ✅ Wykryto tablicę: {full_plate}")
            return full_plate
        else:
            print("[OCR] ❌ Nie udało się odczytać tablicy.")
            return None

    print("[OCR] ❌ Nie udało się odczytać tablicy.")
    return None


def extract_from_video(video_path: str) -> list[str] | None:
    """Zwraca listę wszystkich tablic wykrytych w filmie."""
    if not os.path.exists(video_path):
        print(f"[OCR] ❌ Plik wideo nie istnieje: {video_path}")
        return None

    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    plates = []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"[OCR] 🎬 Rozpoczynam analizę wideo ({total_frames} klatek, {fps:.1f} FPS)")

    while cap.isOpened() and frame_count < total_frames:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = frame_count / fps
        temp_path = "/tmp/frame_ocr.jpg"
        cv2.imwrite(temp_path, frame)

        plate = extract_license_plate(temp_path)
        if plate:
            print(f"[OCR] 🕒 {current_time:.2f}s → Wykryto tablicę: {plate}")
            plates.append(plate)

        frame_count += int(fps / 2)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count)

    cap.release()

    if plates:
        print("\n[OCR] 📊 Wykryte tablice:")
        for p in plates:
            print(f"   • {p}")
        unique = list(set(plates))
        print(f"\n[OCR] 🎥 Łącznie różnych tablic: {len(unique)}")
        return unique

    print("[OCR] ❌ Brak tablic w wideo.")
    return None


def save_first_frames(video_path: str, output_dir: str = "/Users/pawelplt/Desktop/debug_frames", limit: int = 10):
    """Zapisuje pierwsze kilka klatek z filmu do folderu (do podglądu w Finderze)."""
    import cv2
    import os

    if not os.path.exists(video_path):
        print(f"[OCR] ❌ Plik wideo nie istnieje: {video_path}")
        return

    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"[DEBUG] 🎬 Wideo: {video_path} ({total} klatek)")

    count = 0
    while cap.isOpened() and count < limit:
        ret, frame = cap.read()
        if not ret:
            break

        frame_path = os.path.join(output_dir, f"frame_{count+1:03d}.jpg")
        cv2.imwrite(frame_path, frame)
        print(f"[DEBUG] 💾 Zapisano: {frame_path}")
        count += 1

    cap.release()
    print(f"[DEBUG] ✅ Zapisano {count} klatek do folderu: {output_dir}")


def debug_yolo_on_video(video_path: str, output_dir: str = "/Users/pawelplt/Desktop/debug_yolo", limit: int = 5):
    """
    Zapisuje pierwsze klatki z filmu z detekcjami YOLO + OCR.
    Kolor zielony = tablica rejestracyjna, niebieski = inne obiekty.
    """
    import cv2, os, numpy as np
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(video_path):
        print(f"[OCR] ❌ Plik wideo nie istnieje: {video_path}")
        return

    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    print(f"[DEBUG] 🎬 Wideo: {video_path} ({total} klatek, {fps:.1f} FPS)")

    # 📦 Załaduj YOLO
    net = cv2.dnn.readNetFromDarknet(MODEL_CFG_PATH, MODEL_WEIGHTS_PATH)
    with open(CLASS_NAMES_PATH, "r") as f:
        class_names = [c.strip() for c in f.readlines()]

    count = 0
    while cap.isOpened() and count < limit:
        ret, frame = cap.read()
        if not ret:
            break

        H, W, _ = frame.shape

        # 🔧 większa rozdzielczość wejściowa (lepsze wykrywanie małych obiektów)
        blob = cv2.dnn.blobFromImage(frame, 1 / 255, (608, 608), (0, 0, 0), True)
        net.setInput(blob)
        detections = util.get_outputs(net)

        bboxes, class_ids, scores = [], [], []
        for detection in detections:
            bbox = detection[:4]
            xc, yc, w, h = bbox
            bbox = [int(xc * W), int(yc * H), int(w * W), int(h * H)]
            class_id = np.argmax(detection[5:])
            score = np.amax(detection[5:])
            if score > 0.05:  # ⬅️ obniżony próg pewności
                bboxes.append(bbox)
                class_ids.append(class_id)
                scores.append(score)

        bboxes, class_ids, scores = util.NMS(bboxes, class_ids, scores, 0.3)
        texts_found = []

        for (xc, yc, w, h), class_id, score in zip(bboxes, class_ids, scores):
            label = class_names[class_id] if class_id < len(class_names) else "unknown"

            x1, y1 = int(xc - w / 2), int(yc - h / 2)
            x2, y2 = int(xc + w / 2), int(yc + h / 2)
            if x1 < 0 or y1 < 0 or x2 > W or y2 > H:
                continue  # unikamy błędów przy krawędziach

            color = (0, 255, 0) if "plate" in label.lower() else (255, 0, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"{label} ({score:.2f})", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            print(f"[DEBUG] 🟡 {label} ({score:.2f})")

            # 🧠 OCR dla tablic
            if "plate" in label.lower():
                plate_crop = frame[y1:y2, x1:x2]
                if plate_crop.size == 0:
                    continue

                gray = cv2.cvtColor(plate_crop, cv2.COLOR_BGR2GRAY)
                ocr_output = reader.readtext(gray)

                for _, text, conf in ocr_output:
                    if conf > 0.3:
                        cleaned = text.strip().upper().replace(" ", "").replace("-", "")
                        texts_found.append(cleaned)
                        print(f"[OCR] 🔤 Kl.{count+1}: {cleaned} ({conf:.2f})")

        # 💾 zapisanie podglądu klatki
        frame_path = os.path.join(output_dir, f"debug_{count+1:03d}.jpg")
        cv2.imwrite(frame_path, frame)
        print(f"[DEBUG] 💾 Zapisano: {frame_path}")
        count += 1

    cap.release()
    print(f"[DEBUG] ✅ Przetworzono {count} klatek. Wyniki zapisano w: {output_dir}")
