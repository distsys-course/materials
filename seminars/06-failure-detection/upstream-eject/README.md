# Upsteam ejection

В load balancer'ах как правило существует механизм вывода бэкендов из балансировки.

Если бэкенд (апстрим) начинает отвечать ошибками или отвечает слишком долго,
это сигнализирует о том, что с ним что-то произошло. 
В данном случае бэкенд временно выводится из балансировки с надеждой, что ему полегчает.

В данной директории продемонстрирован пример с `envoy` proxy и двумя апстримами, один из 
которых с 80% вероятностью отвечает ошибкой при запросе `/`.

Условие выведение из балансировки настраивается в секции `outlier_detection`:
```yaml
outlier_detection:
    consecutive_5xx: 2
    interval: "5s"
    base_ejection_time: "10s"
    max_ejection_percent: 100
```

Со значением параметров можно ознакомиться в [документации](https://www.envoyproxy.io/docs/envoy/latest/api-v3/config/cluster/v3/outlier_detection.proto#envoy-v3-api-field-config-cluster-v3-outlierdetection-consecutive-5xx) envoy.