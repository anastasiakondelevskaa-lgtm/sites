FROM python:3.12-slim

# Некорневой пользователь: у приложения есть файл сессии Telegram, и лишние права ему ни к чему.
RUN useradd -m -u 10001 tg
WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Каталог данных создаём В ОБРАЗЕ и отдаём пользователю: Docker переносит владельца
# на пустой том, иначе том достаётся root и приложение не может писать (грабли CRM, 20.08).
RUN mkdir -p /data && chown tg:tg /data
USER tg
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
