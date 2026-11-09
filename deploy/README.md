# Обслуживание демонстрационного проекта

Рабочий каталог: `/srv/webprojects/clothes-shop`. Домен: `https://clothes-shop.nemida-studio.com`, админка `/admin/`.

Обновление из PowerShell: `./deploy/Deploy.ps1`. Скрипт использует системные SSH/scp и существующий доступ; пароли в файлах не хранит. Нужны Node.js/npm, Python и зависимости локального проекта. Существующая серверная `.env`, база и media не заменяются локальными данными. До распаковки новой версии создаётся серверная резервная копия.

Серверные операции из рабочего каталога:

```bash
./ops.sh status
./ops.sh logs
./ops.sh stop
./ops.sh start
./ops.sh backup
./ops.sh check-backup
./ops.sh update
./ops.sh restore /srv/webprojects/clothes-shop/backups/ИМЯ_КОПИИ --confirm=clothes-shop
./ops.sh remove --confirm=clothes-shop
```

Удаление затрагивает только этот каталог, Compose project clothes-shop, его контейнеры, том clothes-shop_postgres, сети clothes-shop_default/clothes-shop_ingress, собственный образ backend, собственную конфигурацию Nginx и сертификат. Удаляются также резервные копии внутри каталога; при необходимости заранее сохраните их вне сервера.

Backend и PostgreSQL подключены только к собственной внутренней сети без выхода в интернет. Контейнер web дополнительно подключён к отдельной сети ingress; порт привязан к 127.0.0.1. DEBUG выключен. Реальные платежи и отправки не разрешены; инфраструктура блокирует исходящие соединения backend.

`backend/config/deployment.py` содержит настройки серверной демонстрации. `.env.example` — только перечень переменных; при первом запуске заглушки нужно заменить защищёнными секретами. В действующей установке секреты настроены. Не копируйте пример поверх рабочей `.env`.

База, ключи шифрования и учётные записи перенесены. Исходные локальные базы не менялись. Начальный импорт повторно выполнять не нужно. Обновление упаковывает только код и собранный frontend, исключая `.env`, `.local`, `.venv`, SQLite и media.

Проверка сертификата: `certbot renew --dry-run --no-random-sleep-on-renew --cert-name clothes-shop.nemida-studio.com`. Продление выполняет существующий `certbot.timer`; deploy-hook проверяет Nginx и перечитывает конфигурацию.
