# Sockets, ZeroMQ, gRPC

## Сокеты

Вы уже скорее всего изучали из курса АКОС некоторые системные вызовы и функции
для работы с сетью. Давайте кратко напомним, что надо сделать, чтобы написать
простейший клиент и сервер с различными гарантиями.

Первый системный вызов, который надо знать --
[`socket(2)`](https://man7.org/linux/man-pages/man2/socket.2.html).

У него три аргумента:

```c
int socket(int domain, int type, int protocol);
```

domain -- это (IP) протокол общения, который, например, может быть
`AF_INET` -- IPv4, `AF_INET6` -- IPv6 или `AF_UNSPEC`, который умеет работать с
сокетами обоих типов. Существует ещё много транспортов, но эти три самые часто
используемые. Например, `AF_BLUETOOTH` создан для общения по bluetooth.

type -- это тип сокета. Если вы хотите использовать TCP, то стоит выбирать
`SOCK_STREAM` -- это упорядоченный, двуканальный, надёжный протокол. Если UDP
ваш выбор, используйте `SOCK_DGRAM` -- это обычная пересылка сообщений до 512
байт, если сообщение потерялось или не доставилось, то никаких гарантий нет,
также нет никаких гарантий на порядок. Пример использования `SOCK_DGRAM` это
какие-нибудь системы, ответ в которых не важен порядок или ответ помещается в
один пакет и не страшно перезапросить, например, DNS системы. Иногда ещё
используют `SOCK_SEQPACKET` для ускорения -- гарантии такие же как и в STREAM,
но размер пакета ограничен и надо их вычитывать полностью, иногда используется
в HFT системах, а `SOCK_RDM` -- делает из DGRAM надёжный протокол.

protocol -- выбирайте число 0, тип сокета завязан на протокол и для упрощения
можно считать, что каждый тип сокета имеет один протокол. Для экспрессивности
вы можете указать `IPPROTO_TCP` или `IPPROTO_UDP`, если соответствующий тип
сокета подходит.

Сокет открывает соединение, к которому можно подключаться. Далее стоит открыть
порт и проассоциировать сокет с портом на машине. Для минимального примера
достаточно сделать

```c
struct sockaddr_in {
   sa_family_t    sin_family; /* address family: AF_INET */
   in_port_t      sin_port;   /* port in network byte order */
   struct in_addr sin_addr;   /* internet address */
};

/* Internet address. */
struct in_addr {
   uint32_t       s_addr;     /* address in network byte order */
};

struct sockaddr_in server; // sockaddr_in используется для IP коммуникаций
server.sin_family = AF_INET;
// Любой адрес, можно ещё использовать INADDR_LOOPBACK -- 127.0.0.1
server.sin_addr.s_addr = INADDR_ANY;
server.sin_port = htons(strtoul(argv[1], NULL, 10));
// Каст к sockaddr это просто договоренность, так как не все протоколы -- IP.
if (bind(socket_desc,(struct sockaddr *)&server , sizeof(server)) < 0) {
  perror("bind failed. Error");
  _exit(1);
}
```

Далее если вы используйте `SOCK_STREAM`, то надо начать слушать на порту при
помощи системного вызова [`listen(2)`](https://man7.org/linux/man-pages/man2/listen.2.html).

```c
listen(socket_desc, 5); // 5 -- максимальное количество соединений.
```

Если вы используйте `SOCK_DGRAM`, то дальше стоит уже получать сообщения с
помощью [`recvfrom(2)`](https://man7.org/linux/man-pages/man2/recvfrom.2.html)
и отправлять через [`sendto(2)`](https://man7.org/linux/man-pages/man2/sendto.2.html).
В примерах можно
посмотреть самую простую реализацию [клиента](./sockets/udp_client.c) и
[сервера](./sockets/udp_server.c). Если останется время мы покажем на семинаре,
что сервер не обязательно получает все сообщения в порядке их отправки.

Далее со стороны сервера надо принимать соединения с помощью
[`accept(2)`](https://man7.org/linux/man-pages/man2/accept.2.html)
и он выдаст файловый дескриптор, с которым можно общаться при помощи
`read(2)/write(2)` или [`send(2)/recv(2)`](https://man7.org/linux/man-pages/man2/send.2.html)
(последние отличаются только тем, что можно указывать специальные флаги в
зависимости от прокола).

Со стороны клиента нужно сначала зарезолвить хост и порт до байтового
представления, для этого используется POSIX функция [`getaddrinfo(3)`](https://man7.org/linux/man-pages/man3/getaddrinfo.3.html).

```c
struct addrinfo hints;
memset(&hints, 0, sizeof(hints));
hints.ai_family = AF_INET;
hints.ai_socktype = SOCK_STREAM;
int getaddrinfo(const char *node, // host
                const char *service, // port
                const struct addrinfo *hints, // hints по протоколу
                struct addrinfo **res); // массив результатов
```

Вернется массив результатов, по которому уже стоит делать connect, по hints
должно вернуться TCP и IPv4, потом UDP IPv4, потом TCP IPv6, потом UDP IPv6,
потом все остальные протоколы, которые поддерживаются. Нужно пройтись по массиву
в этом порядке и выбрать первый протокол, с которым получается сделать
[`connect(2)`](https://man7.org/linux/man-pages/man2/connect.2.html) с
`res[i].ai_addr, res[i].ai_addrlen`. Системный вызов вернёт файловый дескриптор,
с которым уже можно работать по read/write операциям.

Схематично для TCP и UDP получаются такие вызовы:

Для UPD

<p align="center"><img src="./sockets/udp.png" width="50%" /></p>

Для TCP

<p align="center"><img src="./sockets/tcp.png" width="50%" /></p>

## ZeroMQ

[ZeroMQ](https://zeromq.org/) это более простой фреймворк для обработки сетевых
сообщений, который нацелен на высокую скорость. Особенные любители этого
фреймворка -- трейдинг компании (конечно, они ещё наворачивают поверх этой
библиотеки всякого разного).

Вообще говоря, обычные сокеты представляют собой синхронный интерфейс либо для
надежных байтовых потоков с установлением соединения (SOCK_STREAM),
либо с ненадежными дейтаграммами без установления соединения (SOCK_DGRAM).
Для сравнения, сокеты ZeroMQ представляют собой абстракцию асинхронной очереди
сообщений с точной семантикой очереди в зависимости от типа используемого
сокета. Там, где обычные сокеты передают потоки байтов или дискретных
дейтаграмм, сокеты ZeroMQ передают дискретные сообщения и вся логика спрятана
внутри.

Асинхронность сокетов ZeroMQ означает, что время установки и разрыва физического
соединения, повторного подключения и эффективной доставки прозрачно для
пользователя и организовано самим ZeroMQ.

Можно считать, что ZeroMQ абстрагирует удобным образом сокеты,
существуют несколько видов сокетов:

1. REQ(uest)/REP(ly) sockets. Обычные двусторонние сокеты, который чередует
   send/recieve и в round-robin или fair-robin стиле посылает запросы.
2. PUB/SUB sockets.
3. PUSH/PULL sockets. Для task distribution.
4. PAIR sockets. Созданы для долго живущих машин, соединения почти никогда не
   закрываются.
5. CLIENT/SERVER.

По факту пока вам не нужны сложные механизмы, хватит первых трёх. Пример REQ/REP
сокетов достаточно просты. В примерах используется обёртка
[cppzmq](https://github.com/zeromq/cppzmq).

Сервер:

```cpp
#include <string>
#include <chrono>
#include <thread>
#include <iostream>

#include <zmq.hpp>

int main() {
  using namespace std::chrono_literals;
  // initialize the zmq context with a single IO thread
  zmq::context_t context{1};
  // construct a REP (reply) socket and bind to interface
  zmq::socket_t socket{context, zmq::socket_type::rep};
  socket.bind("tcp://*:5555");
  // prepare some static data for responses
  const std::string data{"World"};

  for (;;) {
    zmq::message_t request;
    // receive a request from client
    socket.recv(request, zmq::recv_flags::none);
    std::cout << "Received " << request.to_string() << std::endl;
    // simulate work
    std::this_thread::sleep_for(1s);
    // send the reply to the client
    socket.send(zmq::buffer(data), zmq::send_flags::none);
  }
  return 0;
}
```

Клиент:

```cpp
#include <string>
#include <iostream>

#include <zmq.hpp>

int main() {
  // initialize the zmq context with a single IO thread
  zmq::context_t context{1};
  // construct a REQ (request) socket and connect to interface
  zmq::socket_t socket{context, zmq::socket_type::req};
  socket.connect("tcp://localhost:5555");
  // set up some static data to send
  const std::string data{"Hello"};
  for (auto request_num = 0; request_num < 10; ++request_num) {
    // send the request message
    std::cout << "Sending Hello " << request_num << "..." << std::endl;
    socket.send(zmq::buffer(data), zmq::send_flags::none);
    // wait for reply from server
    zmq::message_t reply{};
    socket.recv(reply, zmq::recv_flags::none);
    std::cout << "Received " << reply.to_string();
    std::cout << " (" << request_num << ")";
    std::cout << std::endl;
  }
  return 0;
}
```

Дальнейшее чтение:

1. [Socket API](https://zeromq.org/socket-api/)

## gRPC

[gRPC](https://grpc.io/) является универсальным фреймворком для RPC вызовов.
Используется повсеместно в Google, Netflix, Yandex, etc. Чтобы понять как он
работает, давайте сначала поговорим о протобуфах.

## Protobuf

Если кратно, то всё, что полезно знать о [Protobuf](https://developers.google.com/protocol-buffers)
это то, что это статический формат сообщения данных с удобной и быстрой
(400+MB/s) сериализаций и десериализацией с гибкой обратной совместимостью.
На данный момент это второй по популярности сетевой формат данных, используемый
в мире после JSON, например, запрос в Google или Yandex проходит через несколько
десятков и сотен протобуфов.

В Protobuf можно указывать множество полей, поддерживаемые низкоуровневые типы
`{u,s,''}int{32,64}`, `bool`, `{s,''}fixed{32,64}`, `float`, `double`,
`string`, `bytes`, `enum`, `map`.

Также вы можете указывать submessages и делать из любого типа его `repeated`
версию (также есть ещё директива [`oneof`](https://developers.google.com/protocol-buffers/docs/proto3#oneof)).
Например:

```protobuf
syntax = "proto3";

message Person {
  string name = 1;
  int32 id = 2;
  string email = 3;

  enum PhoneType {
    MOBILE = 0;
    HOME = 1;
    WORK = 2;
  }

  message PhoneNumber {
    string number = 1;
    PhoneType type = 2;
  }

  repeated PhoneNumber phones = 4;
}

message AddressBook {
  repeated Person people = 1;
}
```

После этого напротив каждого поля надо указывать его тэг. Это помогает протобуфу
быть обратно совместимым с изменениями схемы. Например, если вы решили удалить
поле `email` у `Person` достаточно лишь пометить, что этот тэг больше нельзя
использовать.

```protobuf
message Person {
  reserved 3;
  string name = 1;
  int32 id = 2;
  // ...
  repeated PhoneNumber phones = 4;
}
```

Теперь при сериализации и десериализации, если был `tag` в сообщении, он
проигнорируется, но не упадёт с ошибкой. Также нельзя будет его
переиспользовать. Если вы поменяете номер тэга у сообщения, возможна потеря
данных. Это позволяет быть протобуфу обратно совместимым и статическим типом в
отличие от JSON.

Также протобуф можно улучшать, например, такие операции с полями являются
безопасными в плане обратной бинарной совместимости:

1. Добавление любого поля.
2. Удаление любого поля с последующей пометкой `reserved`.
3. Добавление `repeated` к `string`/`bytes`/`submessages` полям.
4. Замена `int32` на `int64` (но не `int32` на `fixed32`).
5. Замена `string` на `bytes`.
6. Замена `enum` на `{u}int{32,64}`.
7. Переименование любого поля (не не тэга!).
8. Добавление `oneof` с другими полями.

## Спецификация формата

Протобуф по умолчанию не сжимает данные, кроме чисел. Он использует так
называемый [variable length encoding](https://developers.google.com/protocol-buffers/docs/encoding),
который хранит меньше байт для маленьких чисел путем хранения 7 бит числа и
одного бита, последний ли это байт в кодировке. Так было сделано из-за того, что
маленькие числа намного чаще встречаются в сообщениях, а если у вас случайные
числа и вам надо лучший перформанс, используйте fixed типы.

Сообщение использует свой собственный тэг, который вычисляется следующим
образом и этот `proto_tag` пишется первым в бинарном сообщении:

```cpp
int proto_tag = (message_tag << 3) | (wire_type & 0x7);
```

`wire_type` это тип поля

```cpp
enum WireType {
  WIRETYPE_VARINT = 0, // int32, int64, uint32, uint64, sint32, sint64, bool, enum
  WIRETYPE_FIXED64 = 1, // fixed64, double
  WIRETYPE_LENGTH_DELIMITED = 2, // string, bytes, embedded messages, packed repeated fields
  WIRETYPE_START_GROUP = 3, // deprecated
  WIRETYPE_END_GROUP = 4, // deprecated
  WIRETYPE_FIXED32 = 5, // fixed32, float
};
```

В итоге получится, что декодирование одного байта самое быстрое, поэтому для
поля с номерами 1 до 15 самые быстрые (15\*8 = 120, один бит ещё для varint
декодирования).
16 до 2047 вторые по скорости. Поля с номерами 2048 или больше не рекомендуются.
Стоит отметить, что максимальное число для тэга является `2^29 - 1`.

В итоге сначала пишется `proto_tag`, далее если формат фиксированный длины --
столько количество байт. Если формат `VARINT`, то пишется varint число после
этого. Если формат требует размера, то пишется размер количества дальнейших байт
(тоже в varint кодировке), дальше читаются эти байт поэлементово
(если это repeated varint, то тоже кодируется).

В итоге сохранение бинарной совместимости возможно только при сохранении
`message_tag` и `wire_format`, поэтому добавлят `repeated` к `string` можно, а
`repeated` к `varint` -- нельзя, обратная совместимость потеряется. Одной из
особенностью протобуфа ещё является, что его размер должен быть меньше `2^31`
байт, это сделано из-за того, что код так был написан и некоторые платформы
не поддерживают 8 байтные размеры и адресные пространства. Плюс если вы
отправляете протобуфы таких размеров, то, кажется, вы делаете что-то не то.
Также сериализация хранит все числа в формате little-endian (в отличие от
сетевого стандарта по big-endian). Big-endian платформы дополнительно
конвертируют числа в свой формат представления байт.

Так как varint использует меньше байт для маленьких чисел, поэтому используйте
числовые типы в соответствии с данной таблицей:

Диапазон       | Лучший по памяти  | Лучший по скорости
:------------- | ----------------: | ------------------:
[2^49, 2^64)   | `fixed64`         | `fixed64`
[2^32, 2^49)   | `int64`           | `fixed64`
[2^21, 2^32)   | `fixed32`         | `fixed32`
[2^7, 2^21)    | `int32`           | `fixed32`
[0, 2^7)       | `int32`           | `int32`
[-2^20, 0)     | `sint32`          | `sfixed32`
(-2^31, -2^20) | `sfixed32`        | `sfixed32`
(-2^48, -2^32] | `sint64`          | `sfixed64`
(-2^63, -2^48] | `sfixed64`        | `sfixed64`

Но не спешите везде использовать `fixed{32,64}`, так как у них теряется
особенность в обновлении, например, до больших типов (протобуф когда-нибудь
будет поддерживать 128-битные типы, наверное).

`int32` отличается от `sint32` тем, что первый воспринимает отрицительные числа
с большим количеством единиц и поэтому бинарный формат будет достаточно большим.
`sint32` отпимизирует это.

Также `bytes` быстрее `string`, так как последнее проверяет, что строка
корректная UTF-8 последовательность. Об этой особенности тоже стоит помнить.

## Компиляция

После этого, чтобы использовать сообщение, оно должно быть скомпилировано под
удобный вам язык. Поддерживаются C++, C#, Dart, Go, Java, Python, Ruby, PHP.
Чтобы скомпилировать protobuf под C++, сначала надо получить protobuf
компилятор. Его можно скачать из [release страницы](https://github.com/protocolbuffers/protobuf/releases)
или получить самому (git, cmake и C++ компилятор сами установите, уже 3 курс
как никак):

```shell
$ git clone https://github.com/protocolbuffers/protobuf
$ cd protobuf
$ mkdir build && cd build
$ cmake -DCMAKE_BUILD_TYPE=Release -Dprotobuf_BUILD_TESTS=OFF ../cmake/ && make -j 7
$ cp $HOME/distsys-course/seminars/02/proto/person.proto ../src/
$ ./protoc -I=$HOME/protobuf/src/ --cpp_out=$HOME/distsys-course/seminars/02/proto $HOME/protobuf/src/person.proto
```
Теперь в семинарской папке будет сгенерировано два файла `person.pb.{h,cc}`. Вы
должны будете добавить их в вашу систему сборки, а также `libprotobuf.a`,
который был скомпилирован на build стадии.

`protoc` умеет компилировать под все языки, просто замените `cpp_out` на,
например, `python_out`.

## API

[C++ API](https://developers.google.com/protocol-buffers/docs/cpptutorial#the-protocol-buffer-api)
и остальные языки состоят из аксессоров полей, например, для поля email будет сгенерировано

```cpp
  // Удалить email
  void clear_email();
  // Получить email()
  const std::string& email() const;
  // Выставить соответствующий email.
  void set_email(const std::string& value);
  void set_email(std::string&& value);
  void set_email(const char* value);
  void set_email(const char* value, size_t size);
  // Через mutable_email() можно менять email
  std::string* mutable_email();
  // Не используйте это, оно просто вам выдаст сырую память и оно C++ specific
  std::string* release_email();
```

А для поля `PhoneNumber`

```cpp
  // Размер repeated поля
  int phones_size() const;
  void clear_phones();
  // Мутабельный доступ по индексу и вообще весь
  ::Person_PhoneNumber* mutable_phones(int index);
  ::google::protobuf::RepeatedPtrField<::Person_PhoneNumber>* mutable_phones();
  // Константный доступ
  const ::Person_PhoneNumber& phones(int index) const;
  // Добавление ещё одного Phone_Number
  ::Person_PhoneNumber* add_phones();
  // Полный константный доступ
  const ::google::protobuf::RepeatedPtrField<::Person_PhoneNumber>& phones() const;
```

После этого с вашим сообщением можно работать как с обычными структурами данных.
Чтобы научиться его сериализовать и десериализовать, можно использовать
следующие функции.

```cpp
// Сериализация, есть ещё много других методов
bool SerializeToString(std::string* output) const;
bool SerializeToOstream(std::ostream* output) const;
// Десериализация
bool ParseFromString(const std::string& data);
bool ParseFromIstream(std::istream* input);
```

Остальные языки различаются в деталях мутабельного доступа и в функциях
сериализации, например, в Go сериализация и десериализация названа `Marshal`
и `Unmarshal`, а в Python любой доступ к данным по умолчанию мутабельный.

Полная документация по всем API находится [здесь](https://developers.google.com/protocol-buffers/docs/reference/overview).

## gRPC

Если кратко, то [gRPC](https://grpc.io/) это просто сервисный RPC протокол над
протобуфами. Он также поддерживается везде, где поддерживаются протобуфы, а
также большой упор делается на кроссплатформенность -- оно работает на
Linux, MacOS, Windows, Android, iOS, FreeBSD, etc.

Если коротко, то его преимущества такие:

![Overview](https://grpc.io/img/landing-2.svg)

Из-за того, что протобуфы хорошо обратно совместимы: можно добавлять поля и
выкладывать клиент-сервер в любом порядке, а также удалять или заменять поля,
то микросервисная архитектура получается достаточно расширяемой. А так как ещё
протобуф статический, количество ошибок с типами заметно уменьшается по
сравнению с нестрого типизированным JSON. Одна из "коробочных" особенностей у gRPC
также является возвращение аннотированного статуса, например, ошибка на
неправильный запрос с пояснением, почему он неправильный итд.

gRPC под собой использует транспорт HTTP/2 из-за скорости, бинарности и сжатия
(в основном header). gRPC имеет встроенный балансер для Kubernetes, мониторинг,
например в Prometheus, безопасную авторизацию. Это полноценная экосистема,
которой стоит пользоваться из-за преимуществ контрактности и меньшим количеством
ошибок.

Чтобы написать первый gRPC сервер-клиент, нужно написать определение сервиса:

```protobuf
service HelloService {
  rpc SayHello (HelloRequest) returns (HelloResponse);
}

message HelloRequest {
  string greeting = 1;
}

message HelloResponse {
  string reply = 1;
}
```

Давайте теперь попробуем собрать gRPC и продемонстрируем всю силу. Инструкции по
сбору можно посмотреть [здесь](https://grpc.io/docs/languages/cpp/quickstart/#setup).

Сервер необычайно просто устроен

```cpp
// Logic and data behind the server's behavior.
class GreeterServiceImpl final : public Greeter::Service {
  grpc::Status SayHello(grpc::ServerContext* context, const HelloRequest* request,
                        HelloReply* reply) override {
    std::string prefix("Hello ");
    reply->set_message(prefix + request->name());
    // You can return more complex things like grpc::Status::Cancelled.
    return grpc::Status::OK;
  }
};
```

И чтобы установить сам сервер, его достаточно легко зарегистрировать:

```cpp
void RunServer() {
  std::string server_address("0.0.0.0:50051");
  grpc::GreeterServiceImpl service;
  grpc::EnableDefaultHealthCheckService(true);
  grpc::reflection::InitProtoReflectionServerBuilderPlugin();
  grpc::ServerBuilder builder;
  // Listen on the given address without any authentication mechanism.
  builder.AddListeningPort(server_address, grpc::InsecureServerCredentials());
  // Register "service" as the instance through which we'll communicate with
  // clients. In this case it corresponds to an *synchronous* service.
  builder.RegisterService(&service);
  // Finally assemble the server.
  std::unique_ptr<Server> server(builder.BuildAndStart());
  // Wait for the server to shutdown. Note that some other thread must be
  // responsible for shutting down the server for this call to ever return.
  server->Wait();
}
```

Синхронный клиент тоже не сильно сложнее устроен

```cpp
class GreeterClient {
 public:
  GreeterClient(std::shared_ptr<Channel> channel)
      : stub_(Greeter::NewStub(channel)) {}
  // Assembles the client's payload, sends it and presents the response back
  // from the server.
  std::string SayHello(std::string_view user) {
    // Data we are sending to the server.
    HelloRequest request;
    request.set_name(user);
    // Container for the data we expect from the server.
    HelloReply reply;
    // Context for the client. It could be used to convey extra information to
    // the server and/or tweak certain RPC behaviors.
    ClientContext context;
    // The actual RPC.
    Status status = stub_->SayHello(&context, request, &reply);
    // Act upon its status.
    if (status.ok()) {
      return reply.message();
    } else {
      std::cout << status.error_code() << ": " << status.error_message()
                << std::endl;
      return "RPC failed";
    }
  }
 private:
  std::unique_ptr<Greeter::Stub> stub_;
};

...
GreeterClient greeter(grpc::CreateChannel(
      // host:port
      "localhost:50051", grpc::InsecureChannelCredentials()));
...
```

Это был пример синхронного клиента. Также существует асинхронная версия такого
клиента (и сервера), так, мы, например, можем асинхронно выполнять в различных
потоках или корутинах запросы. Основной структурой данных в данном случае будет
являться `grpc::CompletionQueue`, которая умеет ждать на условии ответа

```cpp
class GreeterAsyncClient {
 public:
  explicit GreeterAsyncClient(std::shared_ptr<Channel> channel)
      : stub_(Greeter::NewStub(channel)) {}
  // Assembles the client's payload, sends it and presents the response back
  // from the server.
  std::string SayHello(const std::string& user) {
    // Data we are sending to the server.
    HelloRequest request;
    request.set_name(user);
    HelloReply reply;
    // Context for the client. It could be used to convey extra information to
    // the server and/or tweak certain RPC behaviors.
    ClientContext context;
    // The producer-consumer queue we use to communicate asynchronously with the
    // gRPC runtime.
    CompletionQueue cq;
    // Storage for the status of the RPC upon completion.
    Status status;
    // stub_->PrepareAsyncSayHello() creates an RPC object, returning
    // an instance to store in "call" but does not actually start the RPC
    // Because we are using the asynchronous API, we need to hold on to
    // the "call" instance in order to get updates on the ongoing RPC.
    std::unique_ptr<ClientAsyncResponseReader<HelloReply> > rpc(
        stub_->PrepareAsyncSayHello(&context, request, &cq));
    // StartCall initiates the RPC call
    rpc->StartCall();
    // Request that, upon completion of the RPC, "reply" be updated with the
    // server's response; "status" with the indication of whether the operation
    // was successful. Tag the request with the integer 1.
    rpc->Finish(&reply, &status, (void*)1);
    void* got_tag;
    bool ok = false;
    // Block until the next result is available in the completion queue "cq".
    // The return value of Next should always be checked. This return value
    // tells us whether there is any kind of event or the cq_ is shutting down.
    GPR_ASSERT(cq.Next(&got_tag, &ok));
    // Verify that the result from "cq" corresponds, by its tag, our previous
    // request.
    GPR_ASSERT(got_tag == (void*)1);
    // ... and that the request was completed successfully. Note that "ok"
    // corresponds solely to the request for updates introduced by Finish().
    GPR_ASSERT(ok);
    // Act upon the status of the actual RPC.
    if (status.ok()) {
      return reply.message();
    } else {
      return "RPC failed";
    }
  }
 private:
  // Out of the passed in Channel comes the stub, stored here, our view of the
  // server's exposed services.
  std::unique_ptr<Greeter::Stub> stub_;
};
```

В gRPC можно указывать дедлайны и некоторые опции в [`ClientContext`](https://grpc.github.io/grpc/cpp/classgrpc__impl_1_1_client_context.html#ab256e11c0d598dfbbf051dd4dc3e235d), например

```cpp
  ClientContext context;
  context.set_deadline(100);
  context.set_credentials(...);
  context.set_compression_algorithm(...);
  ...
```

Также вы можете указывать ключевое слово `stream` в ваших дефиниций сервисов.

```protobuf
service HelloService {
  rpc SayHello (HelloRequest) returns (HelloResponse);
  rpc LotsOfReplies (HelloRequest) returns (stream HelloResponse);
  rpc LotsOfGreetings (stream HelloRequest) returns (HelloResponse);
  rpc BidiHello (stream HelloRequest) returns (stream HelloResponse);
}
```

То есть вы можете возвращать stream объектов, как синхронно, так и асинхронно,
порядок в stream сохраняется в таком, в котором вы его записали.

Стримы бывают полезны, когда

1. Запросов очень много и хочется возвращать куски данных. Например, бывает
   полезно загрузить информацию почанково асинхронно на диск. Ускоряет процесс
   доставки и в итоге вы утилизируете всю свою сеть.
2. Надо открыть какое-то двуканальное соединение для длительного общения.

Дальше семинарист должен был вам показать async_bidi_* клиента и сервера. Если
вы не присутствовали на семинаре, почитайте внимательно код [клиента](./proto/greeter_async_bidi_client.cc)
и [сервера](./proto/greeter_async_bidi_server.cc),
обратите внимание на `grpc::CompletionQueue` и как сервер и клиент читают и
записывают данные, поиграйтесь с таким примером в grpc examples, если хочется
потрогать, но преждевременно примените такой [патч](https://pastebin.com/D5uXLPF5)
на grpc и скопируйте клиента и сервера в `examples/cpp/helloworld` и
[следуйте инструкциям установки и примерам](https://grpc.io/docs/languages/cpp/quickstart/#setup).

Стоит отметить, что gRPC всё ещё достаточно новая технология и многие (в том
числе и Google) сталкиваются со сложностями до сих пор в gRPC, особенно в
асинхронных гарантиях и streaming RPCs одновременно.

# Полезные ссылки

## Сокеты

- [Beej's Guide to Network Programming](http://beej.us/guide/bgnet/)
- [Unix Network Programming, Volume 1: The Sockets Networking API](https://www.amazon.com/dp/0131411551/) (главы 3-8)
- [TCP Puzzlers](https://www.joyent.com/blog/tcp-puzzlers) (Dave Pacheco, 2016)
- [The Ultimate SO_LINGER Page, or: Why Is My TCP Not Reliable](https://blog.netherlabs.nl/articles/2009/01/18/the-ultimate-so_linger-page-or-why-is-my-tcp-not-reliable) (Bert Hubert, 2009)

## ZeroMQ

- Hintjens P. et al. [ZeroMQ Guide](http://zguide.zeromq.org/) (глава 1)

## gRPC

- [gRPC Up and Running](https://medium.com/@dknkuruppu/a-new-book-on-grpc-oreilly-grpc-up-and-running-8317bcfc775f)
- [gRPC Design and Implementation](https://platformlab.stanford.edu/Seminar%20Talks/gRPC.pdf)
- [Презентации о gRPC](https://grpc.io/docs/talks/)
- [gRPC benchmarking](https://github.com/grpc/grpc.io/blob/master/content/docs/guides/benchmarking.md)
- [gRPC ошибки](https://grpc.io/docs/guides/error/)
