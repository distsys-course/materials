# Домашнее задание по REST HTTP

**Дедлайн:** 13 декабря 2020

**Оценивание:** 5 баллов (обычные ДЗ весят 10), сверху суммы основных ДЗ

На третьем семинаре по HTTP мы разобрали примеры RESTful API. В качестве простого небольшого упражнения предлагается спроектировать и написать свой маленький REST на любом HTTP фреймворке с тестами.

## Что хотим получить?

В третьем семинаре был пример RESTful HTTP API для `article`. Вам предлагается придумать любую сущность и спроектировать HTTP интерфейс для создания сущностей, получения полного списка (фильтры не нужны), удаления и изменения отдельных сущностей. Для реализации сервера можно выбрать любой популярный язык и любой удобный фреймворк, в примере лежит hello-world-пример из Flask. Тесты необходимо написать с помощью прямых HTTP запросов к серверу с помощью библиотеки `requests`.

Задание считается выполненым, если
1. написана простая описывающая документация на доступные endpoint'ы в `docs/readme.md`,
2. сервер поднимается на 80 порту в контейнере server (о шаблоне ниже)
3. на каждый endpoint написан хотя бы один тест и он зелёный

## Как сдавать?

Этот репозиторий предлагается [форкнуть на GitLab](https://gitlab.com/NanoBjorn/hse-distsys-http-hw-2020), так как у него есть бесплатный CI для приватных репозиториев. Пайплайн CI описан в файле `.gitlab-ci.yml`, но вам его трогать не надо. Пайплайн собирает контейнеры с сервером и тестами и запускает тесты. Наличие документации он не проверяет. **Для сдачи ДЗ необходимо, чтобы пайплайн в вашем репозитории был зелёным.** В репозиторий надо добавить как минимум @NanoBjorn, @danlark и @narolov на правах Maintainer, логины ассистентов объявим позже.

## Описание шаблона

В `src` есть две папки:
  - `server`, папка с вашим сервером, содержащая любой код и Dockerfile
  - `client`, папка с тестами на pytest и Dockerfile

Рядом с `src` лежит `docs`, в ней надо будет написать `readme.md`.

### Запуск сервера и тестов с docker-compose

Этот вариант имеет неоспоримое преимущество — вам не надо ставить никаких зависимостей, всё просто запускается в уже настроенном контейнере в одну команду и в одном терминале.

Сначала надо поставить Docker и docker-compose, если у вас их нет.

Для Windows и Mac Docker Desktop поставляется вместе с docker-compose и ничего больше ставить не надо. Для Linux надо будет воспользоваться инструкцией подлиннее. В любом случае, всё есть по ссылке: https://docs.docker.com/compose/install/.

Теперь соберём сервер и тесты:
```bash
$ cd src
$ docker-compose build
```

После успешной сборки обоих контейнеров их можно запустить: сначала нам надо запустить сервер, потом тесты.

```bash
$ docker-compose up -d server
$ docker-compose run pytest -vs
```

После того, как тесты прошли, можно выключать сервер до следующего запуска:
```bash
$ docker-compose down
```

Во время разработки рекомендую объединить все команды в одну строку и проверять написанное фактически одной строкой:
```bash
$ docker-compose build && docker-compose up -d server && docker-compose run pytest && docker-compose down
```

Замечу, что пересборка будет происходить из кэша, а заново будет только копироваться ваш код в контейнер, поэтому выполнение команды будет происходить довольно быстро.

На самом деле, ровно это и происходит внутри GitLab CI, поэтому этот метод даёт вам возможность быть наиболее уверенными в том, что запуск произойдёт близко к тому, как это происходит в пайплайне.

### Запуск сервера и тестов локально

Единственный плюс этого варианта: можно увидеть красивые зелёные галочки в PyCharm. Хотя если вы умеете работать с Docker, то сможете настроить их и для запуска в контейнере.

Сначала делаем virtualenv в корне репозитория, потом ставим зависимости:

```bash
$ python3 -m virtualenv env  # если нет virtualenv, то надо сделать $ python3 -m pip install virtualenv
$ source env/bin/activate
(env) $ cd src
(env) $ pip install -r server/requirements.txt
(env) $ pip install -r tests/requirements.txt
```

Теперь можно проверить, что шаблон работает — сервер запускаются, а тесты зелёные. В одном окне запускаем сервер:
```bash
(env) $ export HSE_HTTP_FLASK_PORT=25565
(env) $ python server/server.py
 * Serving Flask app "server" (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: off
 * Running on http://0.0.0.0:25565/ (Press CTRL+C to quit)
```

В другом окне терминала запускаем тесты:

```bash
$ source env/bin/activate
(env) $ export HSE_HTTP_FLASK_PORT=25565
(env) $ export HSE_HTTP_TESTS_SERVER_HOST=localhost
(env) $ cd src/tests
(env) $ pytest -vs
========== test session starts ==========
platform darwin -- Python 3.8.5, pytest-6.0.2, py-1.9.0, pluggy-0.13.1 -- /Users/gleb-novikov/Projects/distsys-course/homework/rest-http/env/bin/python
cachedir: .pytest_cache
rootdir: /Users/gleb-novikov/Projects/distsys-course/homework/rest-http/src/tests
collected 1 item                                                                                                                                                                    

test_hello_world.py::test_hello_world PASSED

=========== 1 passed in 0.12s ===========
```