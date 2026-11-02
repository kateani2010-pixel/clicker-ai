"""Полная автоматизация сбора И разметки данных для Cookie Clicker.

Идея: игра — обычная веб-страница. Запускаем её в управляемом браузере
(Playwright), программно меняем состояние игры (количество печенья, покупки,
золотые печеньки, уведомления), делаем скриншот и берём координаты нужных
элементов прямо из DOM (getBoundingClientRect). Это даёт идеально точную
разметку в формате YOLO без ручной работы в X-AnyLabeling.

Установка:  uv add playwright && uv run playwright install chromium
Запуск:     uv run collect_and_label.py --n 40
Результат:  dataset/images/{train,val}, dataset/labels/{train,val}

Классы: 0 game (большая печенька), 1 bonus (золотая печенька),
        2 upgrade (доступная покупка), 3 close_ad (крестик уведомления).
"""
import argparse
import os
import random
import time

from playwright.sync_api import sync_playwright

URL = "https://orteil.dashnet.org/cookieclicker/"

# Меняет состояние игры случайным образом и возвращает строки разметки YOLO.
JS_STEP = r"""
async () => {
  const R = n => Math.floor(Math.random() * n);
  try { Game.shimmers.slice().forEach(s => s.die()); } catch (e) {}
  try { Game.CloseNotes(); } catch (e) {}
  Game.prefs.particles = Math.random() < 0.5 ? 1 : 0;
  if (Math.random() < 0.5) { try { Game.ObjectsById[R(4)].buy(1); } catch (e) {} }
  const ups = ['Reinforced index finger','Carpal tunnel prevention cream','Forwards from grandma',
               'Steel-plated rolling pins','Lubricated dentures','Ambidextrous','Cheap hoes'];
  if (Math.random() < 0.5) { try { Game.Unlock(ups[R(ups.length)]); } catch (e) {} }
  for (let i = 0; i < R(3); i++) { try { new Game.shimmer('golden'); } catch (e) {} }
  for (let i = 0; i < R(3); i++) {
    try { Game.Notify(['Реклама','Бонус!','Специальное предложение','Новости'][R(4)],
                      'Нажмите × чтобы закрыть', [R(10), R(10)]); } catch (e) {}
  }
  try { document.getElementById('sectionRight').scrollTop = Math.random() < 0.3 ? R(250) : 0; } catch (e) {}
  const lv = [0, 50, 300, 2000, 15000, 100000, 1e6, 1e8][R(8)];
  Game.cookies = lv; Game.cookiesEarned = Math.max(Game.cookiesEarned, lv);
  await new Promise(r => setTimeout(r, 900));

  const W = innerWidth, H = innerHeight, out = [];
  const add = (c, el, pad = 0, clip = null) => {
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) return;
    let x0 = r.left - pad, y0 = r.top - pad, x1 = r.right + pad, y1 = r.bottom + pad;
    if (clip) { x0 = Math.max(x0, clip.left); y0 = Math.max(y0, clip.top); x1 = Math.min(x1, clip.right); y1 = Math.min(y1, clip.bottom); }
    x0 = Math.max(0, x0); y0 = Math.max(0, y0); x1 = Math.min(W, x1); y1 = Math.min(H, y1);
    if (x1 - x0 < 4 || y1 - y0 < 4) return;
    out.push([c, (x0 + x1) / 2 / W, (y0 + y1) / 2 / H, (x1 - x0) / W, (y1 - y0) / H].map(v => typeof v === 'number' ? v.toFixed(6) : v).join(' '));
  };
  add(0, document.getElementById('bigCookie'));
  document.querySelectorAll('#shimmers .shimmer').forEach(e => add(1, e, 4));
  document.querySelectorAll('#products .product.enabled').forEach(e => add(2, e));
  const upClip = document.getElementById('upgrades').getBoundingClientRect();
  document.querySelectorAll('#upgrades .crate.upgrade.enabled').forEach(e => add(2, e, 0, upClip));
  document.querySelectorAll('#notes .note .close').forEach(e => add(3, e, 8));
  return out.join('\n');
}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--out", default="dataset")
    ap.add_argument("--val", type=float, default=0.2)
    ap.add_argument("--headless", action="store_true")
    args = ap.parse_args()

    for d in ["images/train", "images/val", "labels/train", "labels/val"]:
        os.makedirs(os.path.join(args.out, d), exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        page = browser.new_page(viewport={"width": 1600, "height": 900})
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_function("typeof Game === 'object' && Game.ready", timeout=120000)
        # выбор языка при первом запуске
        try:
            page.click("#langSelect-RU", timeout=5000)
            page.wait_for_function("Game.ready", timeout=60000)
            time.sleep(2)
        except Exception:
            pass
        page.evaluate("Game.prefs.cookiesound = 0")

        for i in range(args.n):
            labels = page.evaluate(JS_STEP)
            split = "val" if random.random() < args.val else "train"
            name = f"auto_{i:03d}"
            page.screenshot(path=os.path.join(args.out, "images", split, name + ".png"))
            with open(os.path.join(args.out, "labels", split, name + ".txt"), "w") as f:
                f.write(labels.strip() + "\n")
            print(name, split, len(labels.splitlines()), "boxes")
        browser.close()

    with open(os.path.join(args.out, "data.yaml"), "w") as f:
        f.write("path: ./dataset\ntrain: images/train\nval: images/val\n\nnc: 4\nnames:\n"
                "  0: game\n  1: bonus\n  2: upgrade\n  3: close_ad\n")
    print("Готово:", args.out)


if __name__ == "__main__":
    main()
