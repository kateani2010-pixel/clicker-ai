"""Задача 3. Обучение модели YOLO на размеченных скриншотах.

Запуск:  uv run train.py
Результат: runs/detect/clicker/weights/best.pt
"""
from pathlib import Path
from ultralytics import YOLO


def main():
    model = YOLO("yolov8n.pt")  # лёгкая модель, хватает CPU
    model.train(
        data="dataset/data.yaml",
        epochs=60,
        imgsz=800,          # крестики уведомлений мелкие, 640 мало
        batch=8,
        device="cpu",
        workers=0,          # на Windows с uv так надёжнее
        project=str(Path(__file__).resolve().parent / "runs" / "detect"),
        name="clicker",
        exist_ok=True,
        patience=20,
        # аугментации: скриншоты, а не фото -> без переворотов и сильных сдвигов цвета
        fliplr=0.0,
        mosaic=0.5,
        hsv_h=0.0,
        hsv_s=0.2,
        hsv_v=0.2,
        degrees=0.0,
        scale=0.3,
        translate=0.1,
    )
    metrics = model.val(data="dataset/data.yaml", imgsz=800, device="cpu")
    print("mAP50:", metrics.box.map50)


if __name__ == "__main__":
    main()
