# Работа над ATELIER NOIR

- Рабочая ветка: master. Исходные index.html, index-2.html, index-3.html сохраняются как референсы.
- Frontend: React, Vite, TypeScript strict, SCSS Modules. Backend: Django, Poetry, SQLite.
- Дизайн переносится из index.html без надзаголовков секций. Skeleton по геометрии компонентов и reduced motion обязательны.
- Нет покупательских аккаунтов. Django Admin доступна только сотрудникам с авторизацией.
- Каталог, остатки, итог заказа и скидки определяются сервером. Цены — Decimal, остатки меняются транзакционно.
- Секреты, база, реальные заказы и локальные ключи не коммитятся. Локальные интеграции не совершают внешних отправок.
- Проверки: frontend typecheck/build; Django checks/migrations; сценарии API заказа, повторного запроса, остатков, прав и импорта.

## Agent skills

### Issue tracker
Задачи проекта относятся к GitHub Issues 4ertopolohh/clothes-shop. См. docs/agents/issue-tracker.md.

### Triage labels
Стандартные needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix.

### Domain docs
Единый GLOSSARY.md; решения с существенными компромиссами — docs/adr/. См. docs/agents/domain.md.
