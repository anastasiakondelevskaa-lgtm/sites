#!/bin/bash
# Смена пароля панели парсера. Запуск: bash /root/tg-parser/set-password.sh 'новый-пароль'
set -e
[ -z "$1" ] && { echo "Использование: bash set-password.sh 'новый-пароль'"; exit 1; }
HASH=$(python3 -c "
import hashlib, os, sys
salt = os.urandom(16)
h = hashlib.scrypt(sys.argv[1].encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
print(salt.hex() + ':' + h.hex())" "$1")
cd /root/tg-parser
sed -i "s|^PANEL_PASSWORD_HASH=.*|PANEL_PASSWORD_HASH=$HASH|" .env
docker compose up -d >/dev/null
echo "Пароль сменён. Прежние входы в браузере продолжают работать до 12 часов."
