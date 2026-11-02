"""Автолейблинг, шаг 1: best.pt -> best.onnx для X-AnyLabeling.

Запуск:  uv run export_onnx.py
"""
from ultralytics import YOLO

model = YOLO("runs/detect/clicker/weights/best.pt")
path = model.export(format="onnx", imgsz=800, opset=12, simplify=True)
print("ONNX сохранён:", path)
