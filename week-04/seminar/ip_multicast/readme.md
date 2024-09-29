## IP Multicast
Это простой пример IP Multicast. Один контейнер слушает порт 9999 и пересылает UDP-пакеты другим контейнерам.

## Использование
Запуск:
```
docker-compose up
```
Отправка пакета:
```
echo -n "hello" | nc -u -w1 localhost 9999
```
