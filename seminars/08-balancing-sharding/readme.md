# Семинар 8: Балансировка нагрузки и шардирование

### Как вы поняли что такое шардирование?
Спрашиваем, обсуждаем

### Round-robin с помощью nginx

Написал два hello-world сервера на фласке, Hello Bob и Hello Alice
```
.
├── docker-compose.yml
├── hello-world
│   ├── Dockerfile
│   └── hello.py
└── nginx.conf
```
```python
# hello-world/hello.py
from flask import Flask
import sys

app = Flask(__name__)

if len(sys.argv) < 2:
    print('please add single positional argument')
    exit()

HOST=sys.argv[1]

@app.route('/')
def index():
    return 'Hello from ' + HOST

app.run(host='0.0.0.0', port=8000)
```

```docker
# hello-world/Dockerfile
FROM python:3.8

RUN pip install flask

WORKDIR hello
COPY . .

ENTRYPOINT ["python3", "hello.py"]
```

```yml
# docker-compose.yml
services:
    nginx:
        image: nginx
        volumes:
        - ./nginx.conf:/etc/nginx/conf.d/default.conf
        ports:
        - 8000:8000

    server1:
        image: hello
        build:
            context: hello-world
        command: "Alice"

    server2:
        image: hello
        build:
            context: hello-world
        command: "Bob"

```

Конфиг nginx, который делает round-robin балансировку:

```nginx
# nginx.conf
upstream rr_backend {
    server server2:8000;
    server server1:8000;
}

server {
    listen 8000;
    server_name _;

    location / {
        proxy_pass http://rr_backend;
    }
}
```

Другие стратегии балансировки: https://docs.nginx.com/nginx/admin-guide/load-balancer/http-load-balancer/
    
Посмотрели, что они реально разные. Можно дать народу ngrok на свой nginx, можно попросить кого-то написать свой hello-world, попросить его дать ngrok и добавить его в свой nginx, запросы будут ходить туда-сюда.

### Микро библиотека с выбором шарда из списка
```
consistent
├── client.py
└── lib.py
```

Написали очень простую функцию выбора шарда:
```python
# consistent/lib.py
MAX_HASH = 1000000


def f(x):
    return hash(x) % MAX_HASH


def get_shard(k, shards):
    sorted_shards = sorted([(f(s), s) for s in shards], key=lambda k: k[0])
    fk = f(k)
    for i in range(0, len(shards)):
        if sorted_shards[i][0] >= fk:
            return sorted_shards[i][1]
    return sorted_shards[0][1]
```

Написали очень простое шардирование запросов с помощью функции:
```python
# consistent/client.py
import requests

from lib import get_shard

shards = {
        'server1': 'http://server1:8000',
        'server2': 'http://server2:8000'
}

keys = [
    'aasdjkahsdl',
    'basdjahlkj',
    'clkjhlkajhd'
]


def call_by_key(key):
    shard = get_shard(key, shards.keys())
    resp = requests.get(shards[shard])
    return resp.text


if __name__=='__main__':
    for k in keys:
        print(call_by_key(k))
```

### Что можно сделать к следующему году

> К сожалению, залипли с багой в nginx конфиге, поэтому ниже не успели, но было бы очень наглядно. Возможно, простой k-v лучше написать заранее и использовать его для показывания round-robin и шардирования.

- Написать простейший http для k-v (dict)
- Рядом с функцией шардирования из списка написать класс, который делает http запросы по списку шардов
- Написать простенький http клиент для нашего kv
- Показать балансировку над над одинаковыми репликами
- Рассказать про шардирование запросов на прокси (будь то отдельный сервис или одна из существующих реплик)
