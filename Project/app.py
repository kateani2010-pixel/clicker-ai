"""Задача 4 + отчёт (п.3-6). Бот-кликер на основе YOLO.

Логика одного цикла:
  1. снимаем экран (mss);
  2. модель находит объекты 4 классов:
        game     - большая печенька (основная цель кликов)
        bonus    - золотая печенька (бонус, кликнуть сразу)
        upgrade  - доступная покупка в магазине (улучшение/здание)
        close_ad - крестик закрытия всплывающего окна/"рекламы"
  3. приоритет действий: close_ad -> bonus -> upgrade -> game.

Защита от случайных кликов:
  * детекции в верхней полосе экрана (вкладки и адресная строка браузера)
    игнорируются;
  * детекции в правой колонке ВЫШЕ магазина (там рекламный баннер сайта)
    игнорируются;
  * для bonus/close_ad порог уверенности выше, чем для печеньки.

Запуск:  uv run app.py
Отладка: uv run app.py --dry-run --debug   (не кликает, пишет кадры в debug/)
Остановка: мышь в левый верхний угол экрана (fail-safe pyautogui) или Ctrl+C.
"""
import os
import time
import argparse

import cv2
import mss
import numpy as np
import pyautogui
from ultralytics import YOLO

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0

CLASSES = {0: "game", 1: "bonus", 2: "upgrade", 3: "close_ad"}
COLORS = {"game": (0, 0, 255), "bonus": (0, 255, 255), "upgrade": (0, 255, 0), "close_ad": (255, 255, 0)}


def grab(sct, monitor):
    img = np.array(sct.grab(monitor))[:, :, :3]  # BGRA -> BGR
    return np.ascontiguousarray(img)


def detect(model, frame, conf):
    res = model.predict(frame, imgsz=800, conf=conf, verbose=False, device="cpu")[0]
    dets = []
    for box, cls, score in zip(res.boxes.xyxy.tolist(), res.boxes.cls.tolist(), res.boxes.conf.tolist()):
        x1, y1, x2, y2 = box
        dets.append({"cls": CLASSES[int(cls)], "x": (x1 + x2) / 2, "y": (y1 + y2) / 2,
                     "box": (int(x1), int(y1), int(x2), int(y2)), "conf": float(score), "skip": ""})
    return dets


def apply_filters(dets, W, H, min_conf):
    """Помечает детекции, по которым кликать нельзя (dets[i]['skip'] = причина).

    Экран = панели браузера сверху + панель задач Windows снизу + страница игры.
    Магазин игры - правая колонка (~18% ширины). Рекламный баннер сайта
    показывается в той же колонке, но ОТДЕЛЬНО от списка покупок (большой отступ).
    """
    top_bar = 0.09 * H      # вкладки + адресная строка браузера
    bottom_bar = 0.94 * H   # панель задач Windows
    store_x = 0.80 * W      # левая граница колонки магазина

    games = [d for d in dets if d["cls"] == "game"]
    for d in dets:
        c = d["cls"]
        if d["conf"] < min_conf.get(c, 0):
            d["skip"] = "low conf"
        elif d["y"] < top_bar or d["y"] > bottom_bar:
            d["skip"] = "system bar"
        elif c in ("bonus", "close_ad") and d["x"] > store_x:
            d["skip"] = "store/ad column"
        elif c == "upgrade" and d["x"] < store_x:
            d["skip"] = "outside store"
        elif c == "game" and games and d is not max(games, key=lambda g: g["conf"]):
            d["skip"] = "dup"

    # покупки: берём только сплошную группу строк, идущую сверху магазина;
    # первый большой разрыв по вертикали - это начало рекламного блока
    ups = sorted([d for d in dets if d["cls"] == "upgrade" and not d["skip"]], key=lambda d: d["box"][1])
    prev_bottom = None
    for d in ups:
        x1, y1, x2, y2 = d["box"]
        h = y2 - y1
        if prev_bottom is not None and y1 - prev_bottom > 1.5 * h:
            d["skip"] = "ad block"
        if not d["skip"]:
            prev_bottom = max(prev_bottom or 0, y2)
        elif d["skip"] == "ad block":
            pass
    # всё, что ниже первого рекламного блока, тоже реклама
    first_ad = next((d["box"][1] for d in ups if d["skip"] == "ad block"), None)
    if first_ad is not None:
        for d in ups:
            if d["box"][1] >= first_ad:
                d["skip"] = "ad block"
    return dets


def draw(frame, dets, actions):
    for d in dets:
        x1, y1, x2, y2 = d["box"]
        col = (128, 128, 128) if d["skip"] else COLORS[d["cls"]]
        cv2.rectangle(frame, (x1, y1), (x2, y2), col, 2)
        txt = f"{d['cls']} {d['conf']:.2f}" + (f" [{d['skip']}]" if d["skip"] else "")
        cv2.putText(frame, txt, (x1, max(12, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 1)
    for (x, y, what) in actions:
        cv2.circle(frame, (int(x), int(y)), 14, (255, 0, 255), 3)
        cv2.putText(frame, "CLICK " + what, (int(x) + 16, int(y)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
    return frame


def click(x, y, ox, oy, dry, n=1, interval=0.0):
    if dry:
        return
    pyautogui.moveTo(ox + x, oy + y, duration=0)
    for _ in range(n):
        pyautogui.click()
        if interval:
            time.sleep(interval)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="runs/detect/clicker/weights/best.pt")
    ap.add_argument("--conf", type=float, default=0.30, help="порог для печеньки/покупок")
    ap.add_argument("--conf-small", type=float, default=0.55, help="порог для bonus/close_ad")
    ap.add_argument("--clicks", type=int, default=15, help="кликов по печеньке за цикл")
    ap.add_argument("--buy-every", type=float, default=4.0, help="сек между попытками покупки")
    ap.add_argument("--monitor", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true", help="не кликать, только смотреть")
    ap.add_argument("--debug", action="store_true", help="сохранять кадры с рамками в debug/")
    ap.add_argument("--max-cycles", type=int, default=0, help="остановиться после N циклов (0 = бесконечно)")
    args = ap.parse_args()

    model = YOLO(args.weights)
    min_conf = {"game": args.conf, "upgrade": args.conf, "bonus": args.conf_small, "close_ad": args.conf_small}
    if args.debug:
        os.makedirs("debug", exist_ok=True)
    last_buy = 0.0
    print("Старт через 3 секунды. Переключитесь на окно с игрой.")
    time.sleep(3)

    cycle = 0
    with mss.mss() as sct:
        mon = sct.monitors[args.monitor]
        ox, oy = mon["left"], mon["top"]
        while True:
            t0 = time.time()
            frame = grab(sct, mon)
            H, W = frame.shape[:2]
            dets = apply_filters(detect(model, frame, min(min_conf.values())), W, H, min_conf)
            ok = [d for d in dets if not d["skip"]]
            by = lambda c: [d for d in ok if d["cls"] == c]
            actions = []

            # 1) закрыть всплывающие окна
            for d in by("close_ad"):
                actions.append((d["x"], d["y"], "close_ad"))
                click(d["x"], d["y"], ox, oy, args.dry_run)
                time.sleep(0.15)

            # 2) бонусы (золотые печеньки)
            for d in by("bonus"):
                actions.append((d["x"], d["y"], "bonus"))
                click(d["x"], d["y"], ox, oy, args.dry_run)
                time.sleep(0.1)

            # 3) покупка: самое нижнее (дорогое) из доступных, не чаще buy_every
            if by("upgrade") and time.time() - last_buy > args.buy_every:
                d = max(by("upgrade"), key=lambda b: (b["y"], b["x"]))
                actions.append((d["x"], d["y"], "upgrade"))
                click(d["x"], d["y"], ox, oy, args.dry_run)
                last_buy = time.time()
                time.sleep(0.2)

            # 4) печенька
            if by("game"):
                d = by("game")[0]
                actions.append((d["x"], d["y"], "game"))
                click(d["x"], d["y"], ox, oy, args.dry_run, n=args.clicks, interval=0.01)
            else:
                time.sleep(0.5)

            if args.debug:
                cv2.imwrite(f"debug/frame_{cycle:04d}.jpg", draw(frame.copy(), dets, actions),
                            [cv2.IMWRITE_JPEG_QUALITY, 80])

            skipped = [f"{d['cls']}({d['skip']})" for d in dets if d["skip"] and d["skip"] != "dup"]
            print(f"#{cycle} {time.time()-t0:.2f}s | действия: {[a[2] for a in actions]}"
                  + (f" | пропущено: {skipped}" if skipped else ""))
            cycle += 1
            if args.max_cycles and cycle >= args.max_cycles:
                break


if __name__ == "__main__":
    main()
