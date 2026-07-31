#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Перебудовує index.html з нуля: base.html (обкладинка+вступ) + всі тижні."""
import build_week1
import build_week2
import build_week3
import build_week4

WEEKS = [build_week1, build_week2, build_week3, build_week4]


def main():
    with open("base.html", "r", encoding="utf-8") as f:
        content = f.read()

    all_pages = []
    for wk in WEEKS:
        all_pages.extend(wk.build())

    html = "\n\n".join(all_pages)
    marker = "</body>"
    assert marker in content
    content = content.replace(marker, "\n" + html + "\n\n" + marker)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Rebuilt index.html with {len(all_pages)} generated pages (+ cover + intro).")


if __name__ == "__main__":
    main()
