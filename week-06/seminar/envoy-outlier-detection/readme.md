# Outlier detection в Envoy

В load balancer'ах как правило существует механизм вывода бэкендов из балансировки.

Если бэкенд (апстрим) начинает отвечать ошибками или отвечает слишком долго,
это сигнализирует о том, что с ним что-то произошло. 
В данном случае бэкенд временно выводится из балансировки с надеждой, что ему полегчает.

В данной директории продемонстрирован пример с прокси-сервером [Envoy](https://www.envoyproxy.io/) и двумя апстримами, один из 
которых с 80% вероятностью отвечает ошибкой при запросе `/`.

Условие выведения из балансировки настраивается в секции `outlier_detection`:
```yaml
outlier_detection:
    consecutive_5xx: 2
    interval: "5s"
    base_ejection_time: "10s"
    max_ejection_percent: 100
```

Подробнее про устройство и параметры outlier detection в Envoy можно прочитать в [документации](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/outlier).