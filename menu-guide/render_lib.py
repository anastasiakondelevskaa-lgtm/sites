#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Генерує сторінки Тижня 1 (список покупок, 7 днів меню, книга рецептів)
і вставляє їх у index.html перед </body>."""

IMG = "images/{}"

def esc(s):
    return s

# ---------------------------------------------------------------------------
# ДОПОМІЖНІ РЕНДЕРИ
# ---------------------------------------------------------------------------

def render_ph(left, right="Сімейний раціон · 4 тижні"):
    return f'''  <div class="ph">
    <div>{left}</div>
    <div class="ph-right">{right}</div>
  </div>'''

def render_pf(page_num, week_num):
    return f'''  <div class="pf">
    <div class="pf-nav"><a href="#intro">Зміст</a><span class="sep">·</span><a href="#w{week_num}-shopping">Покупки</a><span class="sep">·</span><a href="#w{week_num}-menu">Меню</a><span class="sep">·</span><a href="#w{week_num}-recipes">Рецепти</a></div>
    <div class="pf-page">{page_num}</div>
  </div>'''


def render_shop_col(title, categories):
    html = f'    <div class="shop-card">\n      <div class="shop-card-title">{title}</div>\n'
    for cat, items in categories:
        html += f'      <div class="shop-cat">{cat}</div>\n'
        for it in items:
            html += f'      <div class="shop-item"><span class="shop-check"></span>{it}</div>\n'
    html += '    </div>\n'
    return html


def render_shopping_page(week_num, page_num, subtitle, atb_cols, silpo_cols, anchor_id):
    ph = render_ph(f"Тиждень {week_num} · Покупки")
    pf = render_pf(page_num, week_num)
    body = f'''<section class="page" id="{anchor_id}">
{ph}
  <div class="page-body">
    <div class="kicker">Покупки</div>
    <h1 class="h1">🛒 Список покупок — тиждень {week_num}</h1>
    <div class="shop-subtitle">{subtitle}</div>
    <div class="shop-columns">
{render_shop_col("АТБ · Базовий кошик", atb_cols)}{render_shop_col("Сільпо / Новус · Спец-товари", silpo_cols)}    </div>
  </div>
{pf}
</section>'''
    return body


MEAL_TYPES = {
    "breakfast": ("Сніданок", "breakfast"),
    "lunch": ("Обід", "lunch"),
    "snack": ("Перекус", "snack"),
    "dinner": ("Вечеря", "dinner"),
}

def render_meal_card(meal):
    label, cls = MEAL_TYPES[meal["type"]]
    photo = meal.get("photo")
    if photo:
        bg = f' style="background-image:url(\'{IMG.format(photo)}\');"'
        inner = ""
    else:
        bg = ""
        inner = '<div class="meal-placeholder">📷</div>'
    if meal.get("ready"):
        link_html = '<div class="meal-link ready">Готовий смаколик — без приготування</div>'
    else:
        label_text = meal.get("link_label", "Повний рецепт")
        link_html = f'<div class="meal-link">{label_text} → стор. {meal["page"]}</div>'
    kbzhu = meal["kbzhu"]
    return f'''      <div class="meal-card"{bg}>
        {inner}<div class="meal-badge {cls}">{label}</div>
        <div class="meal-label">
          <div class="meal-name">{meal["name"]}</div>
          <div class="meal-kbzhu"><b>{kbzhu[0]} ккал</b> · Б {kbzhu[1]} г · Ж {kbzhu[2]} г · В {kbzhu[3]} г</div>
          {link_html}
        </div>
      </div>'''


def render_day_page(week_num, page_num, day_name, mood, meals, totals, tip, anchor_id=None):
    ph = render_ph(f"Тиждень {week_num} · Меню")
    pf = render_pf(page_num, week_num)
    aid = f' id="{anchor_id}"' if anchor_id else ""
    cards = "\n".join(render_meal_card(m) for m in meals)
    return f'''<section class="page"{aid}>
{ph}
  <div class="page-body">
    <div class="day-badge-row"><div class="day-badge">🌿 {day_name} · Тиждень {week_num}</div></div>
    <div class="day-mood">{mood}</div>
    <div class="meal-grid">
{cards}
    </div>
    <div class="day-kbzhu-row">
      <div class="day-kbzhu-chip k1"><div class="day-kbzhu-value">{totals[0]}</div><div class="day-kbzhu-label">ккал</div></div>
      <div class="day-kbzhu-chip k2"><div class="day-kbzhu-value">{totals[1]} г</div><div class="day-kbzhu-label">білки</div></div>
      <div class="day-kbzhu-chip k3"><div class="day-kbzhu-value">{totals[2]} г</div><div class="day-kbzhu-label">жири</div></div>
      <div class="day-kbzhu-chip k4"><div class="day-kbzhu-value">{totals[3]} г</div><div class="day-kbzhu-label">вугл.</div></div>
    </div>
    <div class="tip-card"><span class="tip-label">порада дня:</span><span class="tip-text">{tip}</span></div>
  </div>
{pf}
</section>'''


def render_recipe_card(idx, r):
    photo = r.get("photo")
    bg = f" style=\"background-image:url('{IMG.format(photo)}');\"" if photo else ""
    ph_inner = "" if photo else '<div class="meal-placeholder">📷</div>'
    ing_html = "".join(
        f'<div class="recipe-ing-item"><span class="recipe-ing-check"></span>{i}</div>' for i in r["ingredients"]
    )
    steps_html = "".join(
        f'<div class="recipe-step"><span class="recipe-step-num">{i+1}</span><span>{s}</span></div>'
        for i, s in enumerate(r["steps"])
    )
    if r.get("dessert_kbzhu"):
        k = r["dessert_kbzhu"]
        extra = f'<div class="recipe-kbzhu-capsule"><b>{k[0]} ккал</b><span>Б {k[1]} г</span><span>Ж {k[2]} г</span><span>В {k[3]} г</span></div>'
    elif r.get("portion_note"):
        extra = f'<div class="recipe-portion"><b>Порція для жінки:</b> {r["portion_note"]}</div>'
    else:
        extra = ""
    meta = r.get("meta")
    meta_html = f'<div class="recipe-meta"><span>Підготовка <b>{meta[0]}</b></span><span>Готування <b>{meta[1]}</b></span><span>Порцій <b>{meta[2]}</b></span></div>' if meta else ""
    return f'''    <div class="recipe-card" id="{r["id"]}">
      <div class="recipe-photo"{bg}>{ph_inner}<div class="recipe-num">{idx+1}</div></div>
      <div class="recipe-body">
        <div class="recipe-title">{r["title"]}</div>
        {meta_html}
        <div class="recipe-cols">
          <div class="recipe-col">
            <div class="recipe-col-title">Інгредієнти</div>
            <div class="recipe-ing-note">{r["ing_note"]}</div>
            {ing_html}
          </div>
          <div class="recipe-col">
            <div class="recipe-col-title">Спосіб приготування</div>
            {steps_html}
          </div>
        </div>
        {extra}
      </div>
    </div>'''


def render_recipe_page(week_num, page_num, section_emoji, section_title, mood, recipes, anchor_id=None):
    ph = render_ph(f"Тиждень {week_num} · Книга рецептів")
    pf = render_pf(page_num, week_num)
    aid = f' id="{anchor_id}"' if anchor_id else ""
    cards = "\n".join(render_recipe_card(i, r) for i, r in enumerate(recipes))
    return f'''<section class="page"{aid}>
{ph}
  <div class="page-body">
    <div class="kicker">Книга рецептів</div>
    <h1 class="h1">{section_emoji} {section_title}</h1>
    <div class="recipe-mood">{mood}</div>
    <div class="recipe-list">
{cards}
    </div>
  </div>
{pf}
</section>'''

