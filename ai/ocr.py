import os
import sys
import cv2 # OpenCV – wczytywanie obrazu/wideo, przetwarzanie, DNN (YOLO)
import numpy as np
import easyocr # OCR (czytanie tekstu ze zdjęć)

# Scieżka do folderu YOLO (żeby znaleźć util.py)
sys.path.append('/Users/pawelplt/Desktop/stolencars/yolov3-from-opencv-object-detection')
import util

# Ścieżki do YOLOv3
MODEL_CFG_PATH = os.path.join('/Users/pawelplt/Desktop/stolencars/yolov3-from-opencv-object-detection', 'model', 'cfg', 'darknet-yolov3.cfg')
MODEL_WEIGHTS_PATH = os.path.join('/Users/pawelplt/Desktop/stolencars/yolov3-from-opencv-object-detection', 'model', 'weights', 'model.weights')
CLASS_NAMES_PATH = os.path.join('/Users/pawelplt/Desktop/stolencars/yolov3-from-opencv-object-detection', 'model', 'class.names')

# OCR reader
reader = easyocr.Reader(['en'], gpu=False)

def extract_license_plate(image_path: str) -> str | None:
    """Wykrywa tablicę rejestracyjną z jednego zdjęcia i zwraca jej tekst w przeciwnym razie zwraca none."""
    if not os.path.exists(image_path):
        print(f"Plik nie istnieje: {image_path}")
        return None

    # Sprawdzamy czy plik istnieje w ogole
    img = cv2.imread(image_path)
    if img is None:
        print(f"Nie udało się wczytać obrazu: {image_path}")
        return None

    H, W, _ = img.shape # Wysokość, szerokość i liczba kanałów obrazu

    # Wczytaj klasy YOLO (w klasach opisane jest jakie obiekty mozna wykrywac, obecnie mamy tylko License Plate
    with open(CLASS_NAMES_PATH, 'r') as f:
        class_names = [j.strip() for j in f.readlines() if len(j.strip()) > 0]

    # Załaduj model YOLO
    net = cv2.dnn.readNetFromDarknet(MODEL_CFG_PATH, MODEL_WEIGHTS_PATH) #to bedzie nasz detektor obiektów (podaje cfg file i wagi (tam wyzej je okreslilem sciezki)
    # redNeTFromDarkNet - funkcja z OpenCV do wczytywania modeli YOLO
    # Teraz potrzebujemy przetworzyć obraz na format zrozumiały dla sieci neuronowej
    blob = cv2.dnn.blobFromImage(img, 1 / 255, (416, 416), (0, 0, 0), True)
    # 1/255 skala ktora bedzie mnożona kazdy piksel (normalizacja)
    # (416,416) - rozmiar wejściowy dla YOLOv3
    # 0,0,0 - srednia wartość do odjęcia od każdego kanału (tu nie odejmujemy nic)
    # True - zamiana kanałów BGR na RGB (OpenCV używa BGR domyślnie) - odwracamy kolejnosc kanałów niebieski, zielony, czerwony na czerwony, zielony, niebieski
    net.setInput(blob) # Ustawiamy blob jako wejście do sieci neuronowej

    detections = util.get_outputs(net) # Pobieramy wykryte obiekty za pomocą funkcji z util.py

    bboxes, class_ids, scores = [], [], [] # Listy na bounding boxy, id klas i pewności wykrycia
    for detection in detections:           # Przetwarzamy każde wykrycie
        bbox = detection[:4]               # Pierwsze 4 wartości to bounding box
        xc, yc, w, h = bbox                # Środek x, środek y, szerokość, wysokość (wszystko w proporcjach do rozmiaru obrazu)
        bbox = [int(xc * W), int(yc * H), int(w * W), int(h * H)] # Przeskalowujemy do rozmiaru oryginalnego obrazu
        class_id = np.argmax(detection[5:])      # Indeks klasy z najwyższą pewnością (począwszy od 5 pozycji)
        score = np.amax(detection[5:])           # Najwyższa pewność wykrycia
        bboxes.append(bbox)         # Dodajemy bounding box do listy
        class_ids.append(class_id)  # Dodajemy id klasy do listy
        scores.append(score)        # Dodajemy pewność wykrycia do listy

    bboxes, class_ids, scores = util.NMS(bboxes, class_ids, scores) # Zastosuj Non-Maximum Suppression (NMS) aby usunąć nakładające się boxy
    # Robimy to żeby zostawić tylko najlepsze wykrycia
    if bboxes is None or len(bboxes) == 0:
        print("[OCR] YOLO nie wykrył tablicy.")
        return None

    # OCR - odczyt tekstu z wykrytych tablic
    for bbox in bboxes:
        xc, yc, w, h = bbox
        y1, y2 = int(yc - h / 2), int(yc + h / 2) # Górny i dolny y
        x1, x2 = int(xc - w / 2), int(xc + w / 2) # Lewy i prawy x

        plate_img = img[y1:y2, x1:x2] # Wycinamy obraz tablicy z oryginalnego obrazu
        if plate_img.size == 0:       # Sprawdzamy czy wycinek nie jest pusty
            continue                  # Jeżeli pusty to przechodzimy do następnego wykrycia

        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY) # Konwertujemy wycinek do skali szarości (bo OCR działa lepiej na takich obrazach)
        output = reader.readtext(gray) # Używamy EasyOCR do odczytu tekstu z obrazu tablicy w skali szarości bpo lepsze wyniki

        texts = [] # Lista na odczytane teksty

        for _, text, conf in output: # Przetwarzamy każde wykrycie tekstu
            if conf > 0.4:          # Sprawdzamy czy pewność odczytu jest większa niż 0.4 (40%)
                cleaned = text.strip().upper().replace(" ", "").replace("-", "").replace("]", "").replace("[", "") # Czyszczenie tekstu: usuwamy spacje, myślniki i nawiasy, zamieniamy na wielkie litery
                texts.append(cleaned) # Dodajemy oczyszczony tekst do listy

        if texts: # Jeżeli znaleźliśmy jakieś teksty
            full_plate = "".join(texts) # Łączymy wszystkie fragmenty tekstu w jeden ciąg
            print(f"[OCR] Wykryto tablicę: {full_plate}") # Zwracamy wykrytą tablicę
            return full_plate
        else:
            print("[OCR] Nie udało się odczytać tablicy.")
            return None

    print("[OCR]Nie udało się odczytać tablicy.")
    return None

# Funkcja do ekstrakcji tablic z wideo
def extract_from_video(video_path: str) -> list[str] | None:
    """Zwraca listę wszystkich tablic wykrytych w filmie."""
    if not os.path.exists(video_path):
        print(f"[OCR] Plik wideo nie istnieje: {video_path}")
        return None

    cap = cv2.VideoCapture(video_path) # Otwieramy plik wideo za pomocą OpenCV
    frame_count = 0 # Licznik klatek, potrzebny do przeskakiwania klatek
    plates = [] # Lista na wykryte tablice

    fps = cap.get(cv2.CAP_PROP_FPS) or 30 # Pobieramy liczbę klatek na sekundę (FPS) wideo, domyślnie 30 jeśli nie uda się pobrać
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) # Całkowita liczba klatek w wideo
    print(f"[OCR] Rozpoczynam analizę wideo ({total_frames} klatek, {fps:.1f} FPS)") # Informacja o rozpoczęciu analizy wideo

    while cap.isOpened() and frame_count < total_frames: # Pętla przez klatki wideo
        ret, frame = cap.read() # Wczytujemy klatkę
        if not ret: # Jeżeli nie udało się wczytać klatki, przerywamy pętlę
            break

        current_time = frame_count / fps # Obliczamy aktualny czas w sekundach
        temp_path = "/tmp/frame_ocr.jpg" # Tymczasowa ścieżka do zapisu klatki
        cv2.imwrite(temp_path, frame) # Zapisujemy klatkę jako obraz tymczasowy

        plate = extract_license_plate(temp_path) # Wykrywamy tablicę na klatce
        if plate: # Jeżeli wykryto tablicę
            print(f"[OCR] {current_time:.2f}s → Wykryto tablicę: {plate}") # Informacja o wykryciu tablicy z czasem
            plates.append(plate) # Dodajemy wykrytą tablicę do listy

        frame_count += int(fps / 2) # Przechodzimy do następnej klatki co pół sekundy
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count) # Ustawiamy pozycję klatki wideo

    cap.release() # Zwalniamy zasoby wideo

    if plates: # Jeżeli wykryto jakieś tablice
        print("\n[OCR] Wykryte tablice:")
        for p in plates:   # Wypisujemy wszystkie wykryte tablice
            print(f"   • {p}")
        unique = list(set(plates)) # Usuwamy duplikaty, zostawiamy tylko unikalne tablice
        print(f"\n[OCR] 🎥 Łącznie różnych tablic: {len(unique)}") # Informacja o liczbie unikalnych tablic
        return unique  # Zwracamy listę unikalnych tablic

    print("[OCR] Brak tablic w wideo.")
    return None

