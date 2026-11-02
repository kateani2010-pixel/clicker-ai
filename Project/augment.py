"""Искусственное увеличение датасета (albumentations).

Запуск:  uv run augment.py --k 3
Для каждой картинки из dataset/images/train создаёт k аугментированных копий
с пересчитанными YOLO-боксами. Только train, val не трогаем.
"""
import argparse
import glob
import os

import albumentations as A
import cv2


def read_labels(path):
    boxes, classes = [], []
    if os.path.exists(path):
        for line in open(path):
            p = line.split()
            if len(p) == 5:
                classes.append(int(p[0]))
                boxes.append([float(v) for v in p[1:]])
    return boxes, classes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--root", default="dataset")
    args = ap.parse_args()

    # Скриншоты: без отражений и поворотов - интерфейс так не выглядит.
    tf = A.Compose([
        A.RandomBrightnessContrast(0.2, 0.2, p=0.8),
        A.HueSaturationValue(5, 20, 15, p=0.5),
        A.GaussNoise(p=0.3),
        A.ImageCompression(quality_range=(50, 95), p=0.5),
        A.Affine(scale=(0.85, 1.1), translate_percent=(-0.05, 0.05), p=0.7,
                 border_mode=cv2.BORDER_CONSTANT),
        A.MotionBlur(blur_limit=3, p=0.2),
    ], bbox_params=A.BboxParams(format="yolo", label_fields=["cls"], min_visibility=0.4))

    imgs = glob.glob(os.path.join(args.root, "images", "train", "*.*"))
    n = 0
    for img_path in imgs:
        base = os.path.splitext(os.path.basename(img_path))[0]
        if "_aug" in base:
            continue
        img = cv2.imread(img_path)
        boxes, cls = read_labels(os.path.join(args.root, "labels", "train", base + ".txt"))
        for i in range(args.k):
            try:
                r = tf(image=img, bboxes=boxes, cls=cls)
            except Exception as e:
                print("skip", base, e)
                continue
            name = f"{base}_aug{i}"
            cv2.imwrite(os.path.join(args.root, "images", "train", name + ".jpg"), r["image"])
            with open(os.path.join(args.root, "labels", "train", name + ".txt"), "w") as f:
                for b, c in zip(r["bboxes"], r["cls"]):
                    f.write(f"{c} " + " ".join(f"{v:.6f}" for v in b) + "\n")
            n += 1
    print("создано", n, "аугментированных изображений")


if __name__ == "__main__":
    main()
