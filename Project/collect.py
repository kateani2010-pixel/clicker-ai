"""Задача 5. Автоматический сбор данных (скриншоты экрана).

Запуск:  uv run collect.py --n 40 --delay 2
Каждые `delay` секунд делает скриншот экрана и кладёт в папку screenshots/.
Пока идёт сбор — играйте: кликайте, покупайте, открывайте окна, чтобы
состояния игры были разными.
"""
import argparse
import os
import time

import mss
import mss.tools


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--delay", type=float, default=2.0)
    ap.add_argument("--out", default="screenshots")
    ap.add_argument("--monitor", type=int, default=1)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    start = len(os.listdir(args.out))
    print(f"Сбор {args.n} скриншотов, старт через 3 с...")
    time.sleep(3)
    with mss.mss() as sct:
        mon = sct.monitors[args.monitor]
        for i in range(args.n):
            img = sct.grab(mon)
            path = os.path.join(args.out, f"shot_{start + i:03d}.png")
            mss.tools.to_png(img.rgb, img.size, output=path)
            print(path)
            time.sleep(args.delay)


if __name__ == "__main__":
    main()
