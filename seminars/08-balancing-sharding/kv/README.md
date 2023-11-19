# Шардирование и репликация на примере простейшего key-value

В файле *storage/main.py* реализован очень простой key-value, который хранит все ключи и значения в памяти. Flask сервер реализует три ручки:

- `curl .../put?key=... -d '{"value": "..."}'` запишет значение из `value` по указанному ключу в параметре `key`.
- `curl .../get?key=...` вернет `{"value": "..."}` или 404
- `/state` предназначена для того, чтобы открывать её в браузере. Если ваш сторадж запущен на локалхосте и 5000 порту, то это http://localhost:5000/state. Страница содержит все ключи и значения в памяти, чтобы было более наглядно.

Запуск одного инстанса key-value и примеры запросов:

```bash
cd kv
pip install Flask==2.3.3 pyyaml==6.0.1 # если нет фласка

python3 storage/main.py -n 'kv store' -p 5000

curl 'http://localhost:5000/put?key=kek' \
  -X POST \
  -H 'Content-type: application/json' \
  -d '{"value": "my value"}'

curl 'http://localhost:5000/get?key=kek'

# или в браузере
open 'http://localhost:5000/state'
```

В файле `proxy/main.py` реализован прокси для вышеописанного key-value сервиса. Он поддерживает два режима работы — репликацию по указанным нодам или шардирование ключей по указанным нодам. API идентичное вышеописанному с отличием лишь в том, что `/state` возвращает состояние всех нод.

Режим работы прокси указан в конфиге в параметре `mode`, он может быть либо `sharding`, либо `replication`. В режиме `sharding` на запросы `/put?key=...` и `/get?key=...` сервис выбирает узел для данного значения ключа (в данной реализации с помощью остатка от деления хэша на количество ключей) и осуществляет вызов (повторяет запрос целиком) на выбранный узел, ответ от узла возвращает в неизменном виде пользователю. В режиме `replication` запись (`/put`) осуществляется на все узлы, а `/get` последовательно вызывает все узлы и возвращает первый 200 OK ответ.

Запуск трёх нод и одной прокси локально:

```bash
python3 storage/main.py -n 'kv1' -p 5000
python3 storage/main.py -n 'kv2' -p 5001
python3 storage/main.py -n 'kv3' -p 5002

# для данного примера проверьте, что mode: sharding
python3 proxy/main.py -c proxy/localhost_config.yml -p 5003

open 'http://localhost:5003/state'

# 20 запросов на запись
for i in {0..20}; do 
  curl 'http://localhost:5003/put?key=key-'$i'' \
    -X POST \
    -H 'Content-type: application/json' \
    -d '{"value": "value-'$i'"}';
done

```

*Вместо локальных нод можно попросить студентов запустить ноду у себя и открыть её через [ngrok](https://ngrok.com/): `ngrok http 5003`. После этого можно открыть прокси через `ngrok http 5003` и предложить всем поделать в неё запросы.*

Вышеописанный набор сервисов можно поднять с помощью docker compose:

```bash
docker compose build
docker compose up

open 'http://localhost:5003/state'

# 20 запросов на запись
for i in {0..20}; do 
  curl 'http://localhost:5003/put?key=key-'$i'' \
    -X POST \
    -H 'Content-type: application/json' \
    -d '{"value": "value-'$i'"}';
done
```

Тем не менее, поднять локально кажется более познавательным.