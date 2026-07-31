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
        link_html = f'<div class="meal-link">Повний рецепт → стор. {meal["page"]}</div>'
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


# ---------------------------------------------------------------------------
# ДАНІ ТИЖНЯ 1
# ---------------------------------------------------------------------------

SHOP_ATB = [
    ("М'ясо та птиця", [
        "Філе куряче — 2 кг",
        "Філе індички — 700 г",
        "Фарш курячий/індичий — 500 г",
        "Куряча печінка — 600 г",
    ]),
    ("Молочні продукти & яйця", [
        "Кисломолочний сир 5-9% — 5 пачок / 1 кг",
        "Яйця курячі — 2-3 десятка",
        "Грецький йогурт 0-2% — 6-7 баночок",
        "Сметана 15% — 1 стакан",
        "Молоко 2.5% або рослинне — 1 л",
    ]),
    ("Крупи та бакалія", [
        "Цільнозерновий хліб — 1 буханка",
        "Вівсяні пластівці — 1 пачка",
        "Гречка — 1 кг",
        "Кіноа — 1 пачка",
        "Цільнозерновий лаваш — 2 пачки",
        "Оливкова/соняшникова олія",
        "Какао-порошок — 1 пачка",
        "Гірчиця — 1 баночка",
    ]),
    ("Заморозка", [
        "Броколі заморожена — 2 пачки / 800 г",
        "Хек або минтай філе — 800 г",
        "Заморожена полуниця — 1 пачка",
    ]),
]

SHOP_SILPO = [
    ("Риба", [
        "Скумбрія свіжозаморожена — 2 шт.",
        "Сьомга/форель слабосолона — 100 г",
    ]),
    ("Овочі та зелень", [
        "Картопля — 1 кг",
        "Кабачки/цукіні — 1.5 кг",
        "Капуста білокачанна — 1 качан",
        "Морква — 0.5 кг",
        "Перець болгарський червоний — 2 шт.",
        "Помідори — 1 кг",
        "Огірки солоні/мариновані — 1 банка",
        "Томати у власному соку — 2 банки по 400 г",
        "Свіжий шпинат, зелень (кріп, петрушка, базилік)",
        "Лимони — 2 шт.",
        "Часник",
        "Червона цибуля",
    ]),
    ("Фрукти", [
        "Банани — 1.5 кг",
        "Яблука/персики — 0.5 кг",
        "Фініки — 100 г",
    ]),
    ("Сири", [
        "Моцарела — 150 г",
        "Фета — 100 г",
        "Твердий сир 45-50% — 150 г",
    ]),
    ("Смаколики та інше", [
        "Булочки цільнозернові для бургерів — 2-3 шт.",
        "Арахісова паста без цукру",
        "Насіння соняшника та гарбуза",
        "Глазуровані сирки — 2 шт.",
        "Батончик Fizi/EatMe — 1 шт.",
        "Морозиво «Хрещатик» — 1 шт.",
    ]),
]

# ---- фото по стравах (використовується і в меню, і в книзі рецептів) ------

PH = {
    "syrnyky": "IMG_20260730_222810_756.jpg",
    "milynets_solony": "IMG_20260730_222810_788.jpg",
    "milynets_solodky": "IMG_20260730_222800_042.jpg",
    "shaurma": "IMG_20260730_222827_092.jpg",
    "lavash_toast": "IMG_20260730_222800_095.jpg",
    "indychka_kartoplya": "IMG_20260730_222827_081.jpg",
    "kotletky_syr": "1785439198844.png",
    "pechinka_tomat": "IMG_20260730_222827_555.jpg",
    "burger": "IMG_20260730_222827_238.jpg",
    "ryba_marynad": "IMG_20260730_222800_556.jpg",
    "lazanya": "IMG_20260730_222827_195.jpg",
    "skumbria": "1785439376642.png",
    "kabachok_pizza": "IMG_20260730_222822_821.jpg",
    "morozyvo_finiky": "IMG_20260730_222752_114.jpg",
    "morozyvo_choc_banan": "IMG_20260730_222751_831.jpg",
    "morozyvo_polunytsya": "IMG_20260730_222756_855.jpg",
    "snack_fizi": "IMG_20260730_222807_868.jpg",
    "snack_syrok": "IMG_20260730_222740_883.jpg",
    "snack_pechyvo": "IMG_20260730_222808_010.jpg",
    "snack_morozyvo_khr": "IMG_20260730_222823_193.jpg",
}

RECIPES_BREAKFAST = [
    dict(id="w1-b1", title="Ніжні сирники з бананом", photo=PH["syrnyky"],
         meta=("8 хв", "8 хв", "2-3"), ing_note="На всю родину (2-3 порції)",
         ingredients=["Сир 5% — 400 г", "Яйце — 1 шт.", "Банан — 1 шт.", "Вівсяне борошно — 3 ст. л.", "Ванілін, кориця"],
         steps=["Сир розімніть з яйцем та бананом.", "Додайте вівсянку.", "Сформуйте сирники та смажте на антипригарній пательні під кришкою по 4 хвилини з кожного боку."],
         portion_note="1.5 порції від загальної маси (~220 г) + 2 ст. л. грецького йогурту або 1 ст. л. сметани 15%."),
    dict(id="w1-b2", title="Солоний вівсяно-млинець", photo=PH["milynets_solony"],
         meta=("8 хв", "6 хв", "1"), ing_note="На 1 порцію для жінки",
         ingredients=["Вівсянка — 50 г", "Яйце — 1 шт.", "Дрібка солі", "Вода/молоко — 40 мл", "Начинка: сир/фета — 40 г", "Сьомга/шинка — 30 г", "Огірок, зелень"],
         steps=["Збийте вівсянку з яйцем та водою, вилийте на пательню, обсмажте з двох боків.", "На одну половину викладіть начинку та накрийте іншою половиною."]),
    dict(id="w1-b3", title="Солодкий протеїновий вівсяно-млинець", photo=PH["milynets_solodky"],
         meta=("8 хв", "6 хв", "1"), ing_note="На 1 порцію для жінки",
         ingredients=["Вівсянка — 60 г", "Яйце — 1 шт.", "Протеїн — 25 г (або +10 г вівсянки)", "Вода", "Начинка: арахісова паста — 10 г", "Банан — 1/2 шт."],
         steps=["Збийте блендером тісто, обсмажте млинець.", "Змастіть пастою та прикрасьте бананом."]),
    dict(id="w1-b4", title="Домашня ПП-шаурма", photo=PH["shaurma"],
         meta=("8 хв", "2 хв", "1"), ing_note="На 1 порцію для жінки",
         ingredients=["Лаваш цільнозерновий — 50 г", "Куряча грудка запечена — 120 г", "Огірок, помідор, капуста — 100 г", "Соус: 2 ст. л. йогурту + часник + кріп + сіль"],
         steps=["Змастіть лаваш соусом, викладіть курку та овочі.", "Загорніть конвертом та підрум'яньте на сухій пательні 2 хвилини."]),
]

RECIPES_LUNCH = [
    dict(id="w1-l1", title="Запечена індичка з картоплею у спеціях", photo=PH["indychka_kartoplya"],
         meta=("5 хв", "35 хв", "3-4"), ing_note="На форму для родини",
         ingredients=["Філе індички/курки — 700 г", "Картопля — 800 г", "Олія — 1.5 ст. л.", "Спеції (паприка, часник, сіль)"],
         steps=["Наріжте картоплю та м'ясо, перемішайте з олією та спеціями.", "Запікайте 35 хв при 180°C."],
         portion_note="1/4 частина всієї форми (~150 г м'яса + 160 г картоплі) + 150 г свіжого салату з капусти з 1 ч. л. насіння соняшника."),
    dict(id="w1-l2", title="Соковиті курячі котлетки з сиром", photo=PH["kotletky_syr"],
         meta=("8 хв", "15 хв", "10-12 шт."), ing_note="На родину (10-12 шт.)",
         ingredients=["Куряче філе — 600 г кубиками", "Твердий сир — 100 г", "Яйце — 1 шт.", "Грецький йогурт — 2 ст. л.", "Борошно — 2 ст. л.", "Сіль, зелень"],
         steps=["Змішайте інгредієнти.", "Ложкою викладайте на пательню, смажте під кришкою без олії."],
         portion_note="2-3 котлетки (~150 г) + 150 г вареної гречки/кіноа + свіжі овочі."),
    dict(id="w1-l3", title="Куряча печінка в томатах та перці", photo=PH["pechinka_tomat"],
         meta=("8 хв", "13 хв", "3-4"), ing_note="На родину",
         ingredients=["Печінка куряча — 600 г", "Томати у власному соку — 400 г", "Перець болгарський — 2 шт.", "Цибуля — 2 шт.", "Олія — 1 ст. л.", "Лимонний сік, часник, зелень"],
         steps=["Обсмажте овочі на олії 5 хв, додайте печінку (по 3 хв з боку).", "Залийте томатами і тушкуйте 8 хв.", "В кінці — сік лимона."],
         portion_note="~200 г печінки з овочевим соусом + 150 г вареної гречки/кіноа."),
    dict(id="w1-l4", title="Соковитий сімейний курячий бургер", photo=PH["burger"],
         meta=("8 хв", "5 хв", "1"), ing_note="На 1 порцію для жінки",
         ingredients=["Булочка цільнозернова — 60 г", "Рублена куряча котлета — 120 г", "Твердий сир — 15 г", "Помідор, солоний огірок, салат", "Соус: 1 ст. л. йогурту + 1/2 ч. л. гірчиці"],
         steps=["Підсушіть булочку.", "Зберіть бургер із гарячою котлетою та сиром."]),
]

RECIPES_DINNER = [
    dict(id="w1-d1", title="Соковита риба під пряним маринадом", photo=PH["ryba_marynad"],
         meta=("5 хв", "25 хв", "3-4"), ing_note="На родину",
         ingredients=["Філе хека або минтая — 800 г", "Олія — 1 ст. л.", "Сік 1/2 лимона, часник, кріп, паприка"],
         steps=["Змастіть рибу маринадом, викладіть на деко.", "Накрийте фольгою і запікайте 25 хв при 200°C."],
         portion_note="~180-200 г готової риби + 150-200 г броколі + 1 скибка цільнозернового хліба (30 г)."),
    dict(id="w1-d2", title="Цукіні-лазанья з курячим фаршем", photo=PH["lazanya"],
         meta=("12 хв", "30 хв", "3-4"), ing_note="На велику форму",
         ingredients=["Цукіні — 700 г слайсами", "Курячий фарш — 500 г", "Томати у власному соку — 400 г", "Моцарела — 150 г", "Йогурт — 150 г + 1 яйце"],
         steps=["Обсмажте фарш з томатами.", "Посоліть цукіні та промокніть вологу.", "У форму шарами: цукіні → фарш → йогуртовий соус. Зверху моцарела.", "Запікайте 30 хв при 180°C."],
         portion_note="рівно 1/4 частина всієї форми (~280-300 г)."),
    dict(id="w1-d3", title="Запечена скумбрія з броколі та насінням", photo=PH["skumbria"],
         meta=("8 хв", "20 хв", "3-4"), ing_note="На родину",
         ingredients=["Філе скумбрії — 2 шт.", "Броколі — 500 г", "Шпинат — 100 г", "Насіння гарбуза — 30 г", "Лимон, трави"],
         steps=["Запікайте скумбрію 20 хв при 180°C.", "Броколі припустіть на пательні з водою 5-7 хв."],
         portion_note="1/2 філе скумбрії (~130 г) + 150 г броколі + жменя шпинату + 1 ст. л. насіння (10 г)."),
    dict(id="w1-d4", title="Запечений кабачок з фетою та курячі «піци»", photo=PH["kabachok_pizza"],
         meta=("8 хв", "20 хв", "1"), ing_note="На 1 порцію для жінки",
         ingredients=["Кабачок: 1/2 розрізати вздовж, надрізи, 30 г фети, часник", "Курячі піци: 150 г філе розрізати, помідор + 30 г моцарели"],
         steps=["Кабачок запекти з фетою та часником 20 хв.", "Курячу піцу викласти з помідором і моцарелою та запекти 15 хв."]),
]

RECIPES_DESSERT = [
    dict(id="w1-s1", title="Морозиво «Творожно-фінікове» (найсолодше)", photo=PH["morozyvo_finiky"],
         meta=("5 хв", "35 хв", "1"), ing_note="1 порція",
         ingredients=["Сир 5% — 150 г", "Фініки без кісточки — 3 шт. (~30 г)", "Кориця — дрібка"],
         steps=["Зблендерити до ідеальної однорідності.", "Покласти у морозилку на 30-40 хвилин."],
         dessert_kbzhu=(310, 21, 6, 42)),
    dict(id="w1-s2", title="Шоколадно-бананове морозиво", photo=PH["morozyvo_choc_banan"],
         meta=("5 хв", "5 хв", "1"), ing_note="1 порція",
         ingredients=["Заморожений банан — 100 г", "Какао-порошок — 1 ст. л.", "Протеїн шоколадний — 20 г (або йогурт 100 г)", "Молоко — 50 мл"],
         steps=["Збити все у блендері до кремового стану."],
         dessert_kbzhu=(310, 22, 4, 45)),
    dict(id="w1-s3", title="Полунично-протеїнове морозиво", photo=PH["morozyvo_polunytsya"],
         meta=("5 хв", "5 хв", "1"), ing_note="1 порція",
         ingredients=["Заморожена полуниця — 100 г", "Протеїн ванільний/полуничний — 20 г (або йогурт 120 г + 1 ч. л. меду)", "Вода/молоко — 30 мл"],
         steps=["Зблендерити заморожену ягоду з білковою основою."],
         dessert_kbzhu=(270, 18, 4, 39)),
]

DAYS = [
    dict(name="Понеділок", mood="старт тижня — легко й смачно!",
         tip="Сьогодні готуємо обід і вечерю одразу на 2 дні — завтра просто розігрієш і заощадиш час на кухні.",
         totals=(1580, 114, 49, 166),
         meals=[
             dict(type="breakfast", name="Сирники з бананом та йогуртом", kbzhu=(390,32,11,40), photo=PH["syrnyky"], page=11),
             dict(type="lunch", name="Індичка запечена з картоплею + салат з капусти", kbzhu=(460,38,14,45), photo=PH["indychka_kartoplya"], page=12),
             dict(type="snack", name="Капучино + ПП-батончик Fizi/EatMe", kbzhu=(320,8,12,43), photo=PH["snack_fizi"], ready=True),
             dict(type="dinner", name="Риба під пряним маринадом + броколі + хліб", kbzhu=(410,36,12,38), photo=PH["ryba_marynad"], page=13),
         ]),
    dict(name="Вівторок", mood="ще один смачний день",
         tip="День «з учора»: просто розігрій учорашній обід та вечерю — жодної зайвої готовки сьогодні.",
         totals=(1590, 123, 48, 163),
         meals=[
             dict(type="breakfast", name="Солоний вівсяно-млинець із сьомгою та сиром", kbzhu=(410,28,16,38), photo=PH["milynets_solony"], page=11),
             dict(type="lunch", name="Індичка запечена з картоплею + салат з капусти", kbzhu=(460,38,14,45), photo=PH["indychka_kartoplya"], page=12),
             dict(type="snack", name="Морозиво «Творожно-фінікове»", kbzhu=(310,21,6,42), photo=PH["morozyvo_finiky"], page=14),
             dict(type="dinner", name="Риба під пряним маринадом + броколі + хліб", kbzhu=(410,36,12,38), photo=PH["ryba_marynad"], page=13),
         ]),
    dict(name="Середа", mood="середина тижня, тримаємось!",
         tip="Знову готуємо на 2 дні наперед — тримай темп, залишилось до кінця тижня зовсім трохи.",
         totals=(1610, 124, 55, 150),
         meals=[
             dict(type="breakfast", name="Солодкий протеїновий вівсяно-млинець з бананом", kbzhu=(430,34,13,44), photo=PH["milynets_solodky"], page=11),
             dict(type="lunch", name="Курячі котлетки з сиром + гречка + овочі", kbzhu=(480,42,14,46), photo=PH["kotletky_syr"], page=12),
             dict(type="snack", name="Глазурований сирок + 1 яблуко", kbzhu=(290,6,12,38), photo=PH["snack_syrok"], ready=True),
             dict(type="dinner", name="Цукіні-лазанья з курячим фаршем та моцарелою", kbzhu=(410,42,16,22), photo=PH["lazanya"], page=13),
         ]),
    dict(name="Четвер", mood="майже вихідні",
         tip="Розігрій учорашні страви — сьогодні кухня відпочиває, а ти економиш час.",
         totals=(1590, 131, 52, 144),
         meals=[
             dict(type="breakfast", name="Хрусткий лаваш-тост із яйцем та сиром", kbzhu=(390,25,18,31), photo=PH["lavash_toast"], page=11),
             dict(type="lunch", name="Курячі котлетки з сиром + гречка + овочі", kbzhu=(480,42,14,46), photo=PH["kotletky_syr"], page=12),
             dict(type="snack", name="Шоколадно-бананове морозиво", kbzhu=(310,22,4,45), photo=PH["morozyvo_choc_banan"], page=14),
             dict(type="dinner", name="Цукіні-лазанья з курячим фаршем та моцарелою", kbzhu=(410,42,16,22), photo=PH["lazanya"], page=13),
         ]),
    dict(name="П'ятниця", mood="фінішна пряма цього тижня!",
         tip="Фінішна пряма! Готуємо обід і вечерю на вихідні наперед.",
         totals=(1610, 108, 66, 141),
         meals=[
             dict(type="breakfast", name="Сирники з бананом та сметаною", kbzhu=(390,30,12,40), photo=PH["syrnyky"], page=11),
             dict(type="lunch", name="Куряча печінка в томатах + кіноа/гречка", kbzhu=(440,38,12,43), photo=PH["pechinka_tomat"], page=12),
             dict(type="snack", name="Печиво «До кави» 40г + мигдаль 15г", kbzhu=(330,7,17,37), photo=PH["snack_pechyvo"], ready=True),
             dict(type="dinner", name="Скумбрія запечена з овочами та гарбузовим насінням", kbzhu=(450,33,25,21), photo=PH["skumbria"], page=13),
         ]),
    dict(name="Субота", mood="вихідного дня смаку",
         tip="Вихідного дня смаку — просто розігрій те, що приготували в п'ятницю.",
         totals=(1580, 124, 50, 151),
         meals=[
             dict(type="breakfast", name="Соковита домашня ПП-шаурма з куркою", kbzhu=(420,35,9,48), photo=PH["shaurma"], page=11),
             dict(type="lunch", name="Куряча печінка в томатах + кіноа/гречка", kbzhu=(440,38,12,43), photo=PH["pechinka_tomat"], page=12),
             dict(type="snack", name="Полунично-протеїнове морозиво або йогурт з ягодами", kbzhu=(270,18,4,39), photo=PH["morozyvo_polunytsya"], page=14),
             dict(type="dinner", name="Скумбрія запечена з овочами та насінням", kbzhu=(450,33,25,21), photo=PH["skumbria"], page=13),
         ]),
    dict(name="Неділя", mood="останній день — попереду новий тиждень",
         tip="Новий тиждень попереду: онови список покупок і заплануй закупівлю наперед 🛒",
         totals=(1560, 119, 60, 131),
         meals=[
             dict(type="breakfast", name="Солодкий протеїновий вівсяно-млинець", kbzhu=(430,34,13,44), photo=PH["milynets_solodky"], page=11),
             dict(type="lunch", name="Соковитий сімейний курячий бургер", kbzhu=(470,38,15,45), photo=PH["burger"], page=12),
             dict(type="snack", name="Морозиво «Хрещатик» або «Каштан» 75г", kbzhu=(240,3,14,24), photo=PH["snack_morozyvo_khr"], ready=True),
             dict(type="dinner", name="Кабачок з фетою + курячі «піци» з моцарелою", kbzhu=(420,44,18,18), photo=PH["kabachok_pizza"], page=13),
         ]),
]

# ---------------------------------------------------------------------------
# ГЕНЕРАЦІЯ
# ---------------------------------------------------------------------------

def main():
    week = 1
    pages = []

    pages.append(render_shopping_page(
        week, 3, "Розраховано на родину з 3–4 осіб на 7 днів",
        SHOP_ATB, SHOP_SILPO, anchor_id="w1-shopping"))

    for i, d in enumerate(DAYS):
        page_num = 4 + i
        pages.append(render_day_page(
            week, page_num, f"{d['name']}", d["mood"], d["meals"], d["totals"], d["tip"],
            anchor_id="w1-menu" if i == 0 else None))

    pages.append(render_recipe_page(week, 11, "🍳", "Сніданки", "доброго ранку!", RECIPES_BREAKFAST, anchor_id="w1-recipes"))
    pages.append(render_recipe_page(week, 12, "🍽", "Обіди для всієї родини", "смачного обіду!", RECIPES_LUNCH))
    pages.append(render_recipe_page(week, 13, "🌙", "Вечері для всієї родини", "приємного вечора!", RECIPES_DINNER))
    pages.append(render_recipe_page(week, 14, "🍨", "Нові ПП-десерти", "солодкого!", RECIPES_DESSERT))

    html = "\n\n".join(pages)

    with open("index.html", "r", encoding="utf-8") as f:
        content = f.read()

    marker = "</body>"
    assert marker in content
    content = content.replace(marker, "\n" + html + "\n\n" + marker)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Inserted {len(pages)} pages for week 1.")


if __name__ == "__main__":
    main()
