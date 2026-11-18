# Учебная практика

Сайт для аренды строительных инструментов. Проект сделан на Django.

## Запуск сайта в Windows

Откройте папку проекта в VS Code и терминал PowerShell. Перейдите в папку, где находится `manage.py`.

Активируйте виртуальное окружение:

```powershell
.\.venv\Scripts\Activate.ps1
```

Если Windows не разрешает запуск сценария, выполните эту команду в текущем окне PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Затем снова активируйте окружение и запустите сайт:

```powershell
.\.venv\Scripts\Activate.ps1
$env:DJANGO_DEBUG = "True"
python manage.py migrate
python manage.py runserver
```

Откройте в браузере адрес:

```text
http://127.0.0.1:8000/
```

Чтобы остановить сайт, нажмите `Ctrl + C` в терминале.

## Если не отображается CSS

1. Убедитесь, что сервер запущен с `DJANGO_DEBUG = "True"`.
2. Обновите страницу сочетанием `Ctrl + F5`.
3. Убедитесь, что файл `static/style.css` есть в проекте.
4. Посмотрите терминал сервера. Запрос `/static/style.css` должен завершиться с кодом `200`, а не `404`.
5. Если в терминале всё ещё `404`, остановите сервер сочетанием `Ctrl + C` и запустите его снова командой `python manage.py runserver`.

## Основные страницы

- Каталог: `http://127.0.0.1:8000/`
- Вход: `http://127.0.0.1:8000/accounts/login/`
- Регистрация: `http://127.0.0.1:8000/registraciya/`
- Мои заказы: `http://127.0.0.1:8000/moi-zakazy/`
- О сервисе: `http://127.0.0.1:8000/o-servise/`
