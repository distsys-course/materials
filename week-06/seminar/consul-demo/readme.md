# Демо Consul

В данной директории находится демонстрационный пример для знакомства с [Consul](https://www.consul.io/). 

В `docker-compose.yaml` запускаются три экземпляра Consul, образующих отказоустойчивый кластер, а также три экземпляра простейшего сервиса из `app`. Экземпляры сервиса при запуске регистрируют себя в Consul вместе с [health check](https://developer.hashicorp.com/consul/docs/services/usage/checks).

После запуска (`docker compose up`) можно отправлять запросы Consul через [REST API](https://developer.hashicorp.com/consul/api-docs) любым удобным инструментом, например:

```shell
curl http://localhost:8500/v1/catalog/services
curl http://localhost:8500/v1/health/checks/flask-hello-world
```

Попробуйте выключить контейнеры `app-*` и посмотрите как изменяется информация, выдаваемая Consul. Включите снова хотя бы один из контейнеров и проверьте ответ Consul.

Также можно попробовать выключать инстансы самого Сonsul и проверить выход скольки (из трех) инстансов он выдерживает без нарушения доступности. 
