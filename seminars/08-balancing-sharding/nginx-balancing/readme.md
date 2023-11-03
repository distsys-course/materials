# Пример распределения нагрузки с помощью Nginx

В *hello-world/main.py* написан простейший hello-world сервер, который отвечает хостом, указанном при запуске сервера в формате `python3 main.py <HOST>`. 

В *nginx.conf* приведен пример конфигурации Nginx, который распределяет нагрузку между двумя инстансами hello-world сервера.


Другие стратегии балансировки: https://docs.nginx.com/nginx/admin-guide/load-balancer/http-load-balancer/

Запуск примера:

```bash
docker compose build
docker compose up

for i in {0..20}; do curl localhost:8000; done
```
