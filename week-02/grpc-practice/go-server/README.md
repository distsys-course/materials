# gRPC сервер

Пример gRPC сервера, реализующего 2 rpc: положить и получить значение.

В env переменной `SERVER_ADDR` передается адрес и порт, которые будет "слушать" сервер.
Если переменная не задана, используется параметр по умолчанию &mdash; `0.0.0.0:51000`.

## protobuf

protobuf спецификация хранится в [storage.proto](./proto/storage.proto).
Для перегенерации *pb.go-файлов, необходимо в корне проекта вызвать protoc:
```bash
protoc --go_out=. --go_opt=paths=source_relative \
    --go-grpc_out=. --go-grpc_opt=paths=source_relative \
    proto/storage.proto
```

Подробнее о gRPC можно узнать в [документации](https://grpc.io/docs/languages/go/basics/) (там же есть блок про stream'ы). С более сложным примером proto-файла можно ознакомиться [здесь](https://github.com/paralin/raft-grpc/blob/master/raft-grpc.proto).

## Тестирование

Сервер можно запустить с помощью команды `go run main.go`.

Подключиться к серверу можно с помощью [grpcurl](https://github.com/fullstorydev/grpcurl):
```bash
# Установить значение 100500
grpcurl -d '{"value": {"payload": 100500}}' -plaintext localhost:51000 storage.Storage/PutValue

# Получить актуальное значение
grpcurl -d '{}' -plaintext localhost:51000 storage.Storage/GetValue
```
## Docker

```bash
# Собрать Docker образ с сервером
docker build -t hse-grpc-server .

# Запустить Docker контейнер:
# -d - запуск в фоне
# -p 50000:51000 - проброс портов: по порту 50000 с хоста будет доступен порт 51000 из контейнера
docker run -d -p 50000:51000 hse-grpc-server

docker ps
docker stop CONTAINER_ID
```