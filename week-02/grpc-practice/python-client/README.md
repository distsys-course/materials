# gRPC клиент

В данной директории реализован простой пример клиента на Python, обращающийся к gRPC серверу.

Программа запускает бесконечный цикл, в котором получает текущее значение с сервера и пытается
установить собственное значение, после чего засыпает на случайный промежуток времени. 
Процедура повторяется в цикле.

Конфигурация:
- `SERVER_ADDR` &mdash; адрес сервера для подключения.
- `VALUE_TO_PUT` &mdash; значение, которое будет устанавливать программа.

## protobuf

protubuf спецификация хранится в директории [./proto](./proto/). 

protobuf файл сервера должен являться надмножеством с точки зрения API относительно protobuf файла
клиента. Особенно важно сохранять оригинальные tag versions.

```bash
pip3 install grpcio-tools

python3 -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/storage.proto
```

## Docker

Сборка образа:
```bash
docker build -t hse-grpc-client .

docker run -d -e SERVER_ADDR=... -e VALUE_TO_PUT=200 hse-grpc-client
```
