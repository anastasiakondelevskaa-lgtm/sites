#!/usr/bin/env bash
# Снимок состояния сервера. Шаг 0 плана: смотрим и ничего не трогаем.
#
# ЧИТАЕТ И НЕ ПИШЕТ. Ни одной команды, меняющей файлы, службы, правила или пакеты.
# Запускать можно повторно и в любой момент.
#
# СЕКРЕТЫ НЕ ПЕЧАТАЕТ НАМЕРЕННО: у .env выводятся только ИМЕНА переменных без значений,
# содержимое сессий, кук и базы n8n не читается вовсе — только размеры и пути. Вывод
# этого скрипта можно спокойно вставить в переписку; если что-то похожее на секрет всё
# же попадёт в вывод — скажите, уберу из скрипта.
#
#   bash audit.sh              # на экран
#   bash audit.sh > audit.txt  # в файл, и пришлите файл

set -u

h() { printf '\n\n===== %s =====\n' "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }
# Мягкий запуск: отсутствие утилиты — не повод обрывать снимок.
try() { if have "$1"; then "$@" 2>&1; else echo "(нет команды: $1)"; fi; }

echo "СНИМОК СЕРВЕРА — $(date -Is)"
echo "хост: $(hostname) / $(hostname -I 2>/dev/null | awk '{print $1}')"

h "1. Машина: ядра, память, диск"
echo "--- процессор ---";        nproc 2>&1; grep -m1 'model name' /proc/cpuinfo 2>/dev/null
echo "--- память ---";           free -h 2>&1
echo "--- диск ---";             df -hT -x tmpfs -x devtmpfs 2>&1
echo "--- ОС и ядро ---";        (. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME"); uname -r
echo "--- аптайм и нагрузка ---"; uptime 2>&1
echo "--- своп ---";             swapon --show 2>&1 || echo "(свопа нет)"

h "2. Что слушает порты"
# Главный вопрос шага 1: доступен ли Whisper (:5001) снаружи.
try ss -tulnp
echo "--- слушают НЕ на localhost (это и есть наружу) ---"
ss -tulnp 2>/dev/null | awk 'NR==1 || ($5 !~ /^127\./ && $5 !~ /^\[::1\]/)'

h "3. Межсетевой экран"
echo "--- ufw ---";      try ufw status verbose
echo "--- nftables ---"; try nft list ruleset
echo "--- iptables ---"; try iptables -S
echo "--- docker цепочки (docker правит iptables в обход ufw) ---"
iptables -S DOCKER 2>/dev/null | head -30 || echo "(цепочки DOCKER нет)"

h "4. Доступ по SSH"
echo "--- действующие настройки (не файл, а то, как их понял демон) ---"
try sshd -T | grep -Ei 'permitrootlogin|passwordauthentication|pubkeyauth|port|allowusers|permitempty'
echo "--- ключи root ---"
[ -f /root/.ssh/authorized_keys ] && { echo "ключей: $(grep -c . /root/.ssh/authorized_keys)"; \
  awk '{print $1, $NF}' /root/.ssh/authorized_keys; } || echo "authorized_keys НЕТ — вход только по паролю"
echo "--- fail2ban ---"; try fail2ban-client status
echo "--- неудачные входы за последнее время ---"
{ journalctl -u ssh -u sshd --since '7 days ago' 2>/dev/null | grep -ci 'failed password' \
  || grep -ci 'Failed password' /var/log/auth.log 2>/dev/null; } | tail -1 | \
  sed 's/^/попыток подбора пароля за 7 дней: /'

h "5. Docker"
echo "--- версия ---";     try docker --version
echo "--- контейнеры ---"; try docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}'
echo "--- тома и их размер ---"; try docker volume ls
try docker system df -v 2>/dev/null | head -40
echo "--- где лежат compose-проекты ---"
find /root /home /opt /srv -maxdepth 4 -name 'docker-compose.y*ml' -o -maxdepth 4 -name 'compose.y*ml' 2>/dev/null

h "6. Службы systemd (кроме штатных)"
systemctl list-units --type=service --state=running --no-pager --no-legend 2>/dev/null \
  | grep -vE 'systemd-|dbus|cron|rsyslog|getty|polkit|unattended|networkd|resolved|udev|logind|journald' \
  || echo "(не удалось получить список)"
echo "--- таймеры ---"; systemctl list-timers --no-pager --no-legend 2>/dev/null | head -20
echo "--- cron ---"; crontab -l 2>/dev/null || echo "(у root пустой)"; ls -la /etc/cron.d/ 2>/dev/null

h "7. nginx и TLS"
echo "--- версия и проверка конфига ---"; try nginx -v; try nginx -t
echo "--- включённые сайты ---"; ls -la /etc/nginx/sites-enabled/ 2>/dev/null
echo "--- имена и куда проксируют ---"
grep -rhE '^\s*(server_name|proxy_pass|listen)' /etc/nginx/sites-enabled/ /etc/nginx/conf.d/ 2>/dev/null | sed 's/^\s*//'
echo "--- сертификаты и сроки ---"; try certbot certificates

h "8. Python-окружения и пакеты"
for V in /root/venv /opt/whisper-venv; do
  echo "--- $V ---"
  if [ -x "$V/bin/python3" ]; then
    "$V/bin/python3" -V 2>&1
    "$V/bin/pip" list 2>/dev/null | grep -iE 'playwright|selenium|whisper|ctranslate|faster|torch|flask|gunicorn|requests|beautifulsoup|instagrapi|httpx|telethon' \
      || echo "(интересующих пакетов нет)"
  else
    echo "(нет такого окружения)"
  fi
done
echo "--- системный python и утилиты ---"; python3 -V 2>&1; try ffmpeg -version | head -1; have yt-dlp && yt-dlp --version || echo "(yt-dlp нет)"

h "9. Whisper"
echo "--- процессы ---"; ps aux 2>/dev/null | grep -iE 'whisper|gunicorn' | grep -v grep || echo "(процессов нет)"
echo "--- сколько воркеров задано ---"
grep -rhiE 'workers|bind' /etc/systemd/system/*whisper* /opt/whisper-venv/*.conf 2>/dev/null || echo "(конфиг не найден)"
echo "--- файлы моделей (размер = какая модель реально скачана) ---"
find /root /opt /home -maxdepth 6 -path '*whisper*' \( -name '*.pt' -o -name '*.bin' \) -size +10M \
  -printf '%s\t%p\n' 2>/dev/null | sort -rn | head
echo "--- мусор во временном каталоге (утечка из almanac 6.2) ---"
ls -la /tmp/*.mp4 2>/dev/null | tail -5; echo "файлов .mp4 в /tmp: $(ls /tmp/*.mp4 2>/dev/null | wc -l)"

h "10. n8n — там живут куки, гасить нельзя до извлечения"
echo "--- процесс и контейнер ---"; ps aux 2>/dev/null | grep -i '[n]8n' | head -3 || echo "(процесса нет)"
docker ps -a --filter name=n8n --format '{{.Names}} {{.Status}} {{.Ports}}' 2>/dev/null
echo "--- где данные (СОДЕРЖИМОЕ НЕ ЧИТАЮ, только размер) ---"
for D in /root/.n8n /home/*/.n8n /var/lib/docker/volumes/*n8n*; do
  [ -e "$D" ] && du -sh "$D" 2>/dev/null
done
ls -la /root/.n8n/*.sqlite* 2>/dev/null

h "11. tg-parser — что в проде"
echo "--- контейнер ---"; docker ps -a --filter name=tg-parser --format '{{.Names}} {{.Status}} {{.Ports}}' 2>/dev/null
echo "--- ИМЕНА переменных .env, БЕЗ значений ---"
for F in /root/tg-parser/.env /opt/tg-parser/.env /srv/tg-parser/.env; do
  [ -f "$F" ] && { echo "файл: $F"; grep -oE '^[A-Za-z_][A-Za-z0-9_]*=' "$F" | tr -d '='; }
done
echo "--- сколько данных в томе (содержимое не читаю) ---"
docker run --rm -v tgdata:/d alpine sh -c \
  'echo "сессий: $(ls /d/sessions 2>/dev/null | wc -l)"; echo "результатов json: $(ls /d/results/*.json 2>/dev/null | wc -l)"; echo "выгрузок csv: $(ls /d/results/*.csv 2>/dev/null | wc -l)"; du -sh /d 2>/dev/null' \
  2>/dev/null || echo "(том tgdata не смонтировался — проверьте имя тома в docker volume ls)"

h "12. Что ещё на диске"
echo "--- крупное в /root /opt /srv /home ---"
du -sh /root /opt /srv /home 2>/dev/null
ls -la /root /opt /srv 2>/dev/null
echo "--- питоновские файлы, похожие на парсеры ---"
find /root /opt /srv /home -maxdepth 4 -iname '*insta*' -o -maxdepth 4 -iname '*parser*' -o -maxdepth 4 -iname '*whisper*' 2>/dev/null | head -40

h "13. Обновления и состояние пакетов"
try apt list --upgradable 2>/dev/null | tail -20
echo "--- автообновления безопасности ---"
[ -f /etc/apt/apt.conf.d/20auto-upgrades ] && cat /etc/apt/apt.conf.d/20auto-upgrades || echo "(не настроены)"
echo "--- нужен ли перезапуск ---"; [ -f /var/run/reboot-required ] && cat /var/run/reboot-required || echo "нет"

h "КОНЕЦ СНИМКА"
echo "Ничего не изменено. Пришлите вывод целиком."
