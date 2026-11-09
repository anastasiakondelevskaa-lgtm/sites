# ТЗ: 3 сторінки подяки з Purchase + value (Meta Pixel)

## Вихідні дані
- **Meta Pixel ID: `1345733194177265`.** Він має бути підключений у `<head>` сайту: init + PageView. Інший піксель не додавати.
- **Сайт:** `https://<ДОМЕН>` — вписати домен нового сайту.
- **Три тарифи.** Суми перевірити перед стартом:

| Тариф | Ціна, грн | Сторінка подяки | value | currency |
|---|---|---|---|---|
| Тариф 1 | 290 | `/thank-you` | 290 | UAH |
| Тариф 2 | 490 | `/thank-you-2` | 490 | UAH |
| Тариф 3 | 990 | `/thank-you-3` | 990 | UAH |

**Мета.** Після оплати людина повертається на сторінку подяки свого тарифу. Сторінка один раз відправляє в Meta подію `Purchase` з правильною сумою. Так Meta рахує реальний ROAS і вчиться приводити покупців дорожчих тарифів.

---

## 1. Сторінки
Три маршрути з таблиці вище. Вміст кожної сторінки:
- **Заголовок.** «Дякуємо за оплату! 🎉» і назва тарифу.
- **Що далі.** Як отримати доступ (email / Telegram-бот / кабінет) і кнопка з тим посиланням, яке зараз дають після оплати.
- **Обмеження.** Без редиректів, таймерів і форм. Сторінка має повністю завантажитись, щоб піксель встиг спрацювати.
- **Індексація.** `<meta name="robots" content="noindex">`.

> Допродаж за 99 грн (якщо він є на сторінці подяки) **не** шле `Purchase`. Для нього окрема подія `Upsell99`, приклад у п. 3.

## 2. Подія Purchase (головне)
На кожній сторінці подяки при першому рендері:

```js
const PIXEL_ID = "1345733194177265";
const VALUES = { "/thank-you": 290, "/thank-you-2": 490, "/thank-you-3": 990 };

const path = window.location.pathname.replace(/\/+$/, "") || "/";
const value = VALUES[path];
if (value) {
  const params = new URLSearchParams(window.location.search);
  const orderRef = params.get("orderReference") || params.get("order_id") || null;
  const key = orderRef
    ? `purchase_order_${orderRef}`
    : `purchase_${path}_${new Date().toISOString().slice(0, 10)}`;

  if (!localStorage.getItem(key)) {
    const send = () => {
      window.fbq("trackSingle", PIXEL_ID, "Purchase",
        { value: value, currency: "UAH", content_name: `Tariff ${value}`, content_type: "product" },
        orderRef ? { eventID: orderRef } : undefined);
      try { localStorage.setItem(key, String(Date.now())); } catch (e) {}
    };
    if (window.fbq) send();
    else {
      let tries = 0;
      const t = setInterval(() => {
        if (window.fbq || ++tries > 50) { clearInterval(t); if (window.fbq) send(); }
      }, 100);
    }
  }
}
```

Вимоги:
1. **`trackSingle` з pixel ID**, а не `track`. Так подія піде лише в наш піксель.
2. **Одна оплата — одна подія.** Оновлення сторінки або «назад» не шле `Purchase` вдруге. Захист через localStorage, як у коді вище.
3. **Формат даних.** `value` — **число** (290 / 490 / 990), `currency` — рядок `"UAH"`.
4. **`eventID`.** Якщо WayForPay передав `orderReference`, він іде в `eventID`. Це потрібно для майбутньої дедуплікації з CAPI.
5. **Жодних інших `Purchase` на сайті.** Прибрати всі інші виклики `fbq('track','Purchase')`, зокрема на головній і на кнопках. Також прибрати Custom Conversion по URL, якщо він дублює покупку.
6. **POST-повернення.** WayForPay може повертати людину POST-запитом. Сторінка подяки має відкриватись і після POST, без 404/405. Якщо хостинг не приймає POST, зробити проміжний маршрут: він приймає POST і робить redirect на GET-сторінку з тими самими параметрами.

## 3. Інші події
**InitiateCheckout** — на кожній кнопці оплати, перед переходом у WFP:
```js
window.fbq && fbq("trackSingle", "1345733194177265", "InitiateCheckout", { value: 290, currency: "UAH" }); // 490 / 990 для інших кнопок
```

**Upsell99** — якщо є допродаж за 99 грн. Відправляти на його окремій сторінці подяки:
```js
fbq("trackSingle", "1345733194177265", "Upsell99", { value: 99, currency: "UAH" });
```
Сторінку допродажу **не** називати `/thank-you…`.

## 4. Рекламні мітки
- **`fbclid`.** Не прибирати `?fbclid=` з URL до ініціалізації пікселя: з нього ставиться cookie `_fbc`.
- **UTM і `fbclid`.** При першому візиті зберегти їх у `localStorage` (`utm_data`), вони знадобляться для CAPI.

## 5. WayForPay (робить власник кабінету)
Для кожного тарифу в кнопці/товарі WFP вказати **URL повернення (returnUrl)**:

| Тариф | returnUrl |
|---|---|
| 290 | `https://<ДОМЕН>/thank-you` |
| 490 | `https://<ДОМЕН>/thank-you-2` |
| 990 | `https://<ДОМЕН>/thank-you-3` |

Якщо кнопки спільні з іншим сайтом, створити окремі кнопки, інакше людей поверне не на той домен.

## 6. Що НЕ робити
- Не міняти pixel ID і не додавати другий піксель.
- Не ставити cookie-банер, який блокує піксель.
- Не міняти ціни, тексти тарифів і кнопки оплати, окрім додавання InitiateCheckout.

## 7. Перевірка перед здачею (обов'язково)
1. **Pixel Helper (розширення Chrome).** Відкрити `/thank-you`, `/thank-you-2`, `/thank-you-3`. На кожній рівно одна `Purchase` з `value` 290 / 490 / 990 і `currency` UAH.
2. **Оновлення сторінки.** Після оновлення другої `Purchase` немає.
3. **`eventID`.** На `/thank-you-2?orderReference=TEST123` видно `eventID: TEST123`.
4. **Кнопки тарифів.** На кожній кнопці видно `InitiateCheckout` з правильною сумою.
5. **Events Manager → Тестові події.** Ті самі дії, події приходять з потрібного домену.
6. **Реальна тестова оплата найдешевшого тарифу.** Відкривається правильна сторінка подяки, у Тестових подіях одна `Purchase` з правильним value.
7. **Скріншоти.** Додати скріншоти Pixel Helper з трьох сторінок і з Тестових подій.
