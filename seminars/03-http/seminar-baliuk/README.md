# 03. HTTP

## Протокол HTTP

**HTTP** (Hypertext Transfer Protocol) &mdash; протокол прикладного уровня, которым неосознанно пользовались все, 
кто когда-либо открывали сайт в браузере. Изначально протокол предназначался для получения HTML сайта, сейчас HTTP
стал настолько популярным, что используется для передачи информации любого предназначения (файлы, изображения, API).

Протокол построен над транспортным уровнем и пользуется гарантиями на надежную доставку данных от TCP.

HTTP предполагает наличие запроса и ответа. 
Запросы выглядят следующим образом:
```bash
[$] telnet google.com 80
GET /search HTTP/1.1
Host: google.com
```

Ответ на данный запрос может выглядеть следующим образом:
```html
HTTP/1.1 301 Moved Permanently
Location: http://www.google.com/
Content-Type: text/html; charset=UTF-8
Cache-Control: public, max-age=2592000
Content-Length: 219

<HTML><HEAD><meta http-equiv="content-type" content="text/html;charset=utf-8">
<TITLE>301 Moved</TITLE></HEAD><BODY>
<H1>301 Moved</H1>
The document has moved
<A HREF="http://www.google.com/">here</A>.
</BODY></HTML>
```

Запрос имеет следующую структуру:
![HTTP request schema from https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview/http_request.png](img/http_request.png)

- [**Метод**](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods) &mdash; тип операции, которую хочет совершить клиент. 
  Набор методов зафиксирован в RFC протокола, то есть нельзя использовать нечто произвольное. 
  Наиболее популярные: GET &mdash; получение данных, POST &mdash; совершить действие (отправить деньги), 
  PUT &mdash; установить новое значение объекта, PATCH &mdash; частично изменить некоторый объект.

- **Path** &mdash; путь, по которому происходит доступ к ресурсу. Это то, что вы видите в браузерной строке после домена.

- **Версия протокола**, которую предлагает использовать клиент для общения с сервером. 
 Наиболее популярные сейчас это 1.1 и 2.0, набирает популярность 3.0 (Quic). 
 Если сервер не поддерживает указанную версию протокола, он дает об этом знать.

- **Заголовки** (опционально) &mdash; key-value значения, в которых зачастую указана метаинформация о запросе. 
 Например, в заголовках может быть указан домен сервера, требования к протоколу сжатия, информация о пользователе, токен доступа.

- **Тело запроса** (опционально) &mdash; данные, которые клиент хочет отправить на сервер.
 Например, в body могут передаваться детали платежа в формате JSON.

Ответ имеет следующую структуру:
![HTTP response schema from https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview/http_request.png](img/http_response.png)

- **Версия протокола**, чтобы клиент знал, как ему обрабатывать ответ.

- [**Status code**](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status) &mdash; числовой идентификатор,
 семантически определяющий статус обработки запроса (успех / не успех, и почему).

- **Status message** идет вместе со статус кодом и привязано к нему.

- **Заголовки** в том же формате, что и в запросе. В заголовках ответа указывается информация, в каком формате будет возвращен ответ и какая его длина (`Content-Length`).

- **Body** &mdash; тело ответа.

HTTP запросы можно выполнять из браузера, из приложений с помощью готовых фреймворков и из терминала. 
Классической утилитой для терминала является curl:
<details>
  <summary><code>$ curl https://google.com -vvv</code></summary>

  ```
*   Trying 142.251.42.206:443...
* Connected to google.com (142.251.42.206) port 443 (#0)
* ALPN: offers h2,http/1.1
* (304) (OUT), TLS handshake, Client hello (1):
*  CAfile: /etc/ssl/cert.pem
*  CApath: none
* (304) (IN), TLS handshake, Server hello (2):
* (304) (IN), TLS handshake, Unknown (8):
* (304) (IN), TLS handshake, Certificate (11):
* (304) (IN), TLS handshake, CERT verify (15):
* (304) (IN), TLS handshake, Finished (20):
* (304) (OUT), TLS handshake, Finished (20):
* SSL connection using TLSv1.3 / AEAD-CHACHA20-POLY1305-SHA256
* ALPN: server accepted h2
* Server certificate:
*  subject: CN=*.google.com
*  start date: Aug 14 08:16:28 2023 GMT
*  expire date: Nov  6 08:16:27 2023 GMT
*  subjectAltName: host "google.com" matched cert's "google.com"
*  issuer: C=US; O=Google Trust Services LLC; CN=GTS CA 1C3
*  SSL certificate verify ok.
* using HTTP/2
* h2h3 [:method: GET]
* h2h3 [:path: /]
* h2h3 [:scheme: https]
* h2h3 [:authority: google.com]
* h2h3 [user-agent: curl/7.88.1]
* h2h3 [accept: */*]
* Using Stream ID: 1 (easy handle 0x140810a00)
> GET / HTTP/2
> Host: google.com
> user-agent: curl/7.88.1
> accept: */*
>
< HTTP/2 301
< location: https://www.google.com/
< content-type: text/html; charset=UTF-8
< content-security-policy-report-only: object-src 'none';base-uri 'self';script-src 'nonce-MY9T0aSWsg8XW1F1GXOKUw' 'strict-dynamic' 'report-sample' 'unsafe-eval' 'unsafe-inline' https: http:;report-uri https://csp.withgoogle.com/csp/gws/other-hp
< date: Fri, 22 Sep 2023 00:33:01 GMT
< expires: Sun, 22 Oct 2023 00:33:01 GMT
< cache-control: public, max-age=2592000
< server: gws
< content-length: 220
< x-xss-protection: 0
< x-frame-options: SAMEORIGIN
< alt-svc: h3=":443"; ma=2592000,h3-29=":443"; ma=2592000
<
<HTML><HEAD><meta http-equiv="content-type" content="text/html;charset=utf-8">
<TITLE>301 Moved</TITLE></HEAD><BODY>
<H1>301 Moved</H1>
The document has moved
<A HREF="https://www.google.com/">here</A>.
</BODY></HTML>
* Connection #0 to host google.com left intact
  ```

</details>

<details>
  <summary><code>$ curl https://api.thecatapi.com/v1/images/search\?api_</code></summary>

  ```
[{"id":"MjA2MTgzMw","url":"https://cdn2.thecatapi.com/images/MjA2MTgzMw.jpg","width":440,"height":298}]
  ```

</details>

<details>
  <summary><code>$ curl https://api.thecatapi.com/v1/images/search\?api_ -v</code></summary>

  ```
*   Trying 172.217.175.51:443...
* Connected to api.thecatapi.com (172.217.175.51) port 443 (#0)
* ALPN: offers h2,http/1.1
* (304) (OUT), TLS handshake, Client hello (1):
*  CAfile: /etc/ssl/cert.pem
*  CApath: none
* (304) (IN), TLS handshake, Server hello (2):
* (304) (IN), TLS handshake, Unknown (8):
* (304) (IN), TLS handshake, Certificate (11):
* (304) (IN), TLS handshake, CERT verify (15):
* (304) (IN), TLS handshake, Finished (20):
* (304) (OUT), TLS handshake, Finished (20):
* SSL connection using TLSv1.3 / AEAD-CHACHA20-POLY1305-SHA256
* ALPN: server accepted h2
* Server certificate:
*  subject: CN=api.thecatapi.com
*  start date: Aug 15 22:33:33 2023 GMT
*  expire date: Nov 13 23:21:03 2023 GMT
*  subjectAltName: host "api.thecatapi.com" matched cert's "api.thecatapi.com"
*  issuer: C=US; O=Google Trust Services LLC; CN=GTS CA 1D4
*  SSL certificate verify ok.
* using HTTP/2
* h2h3 [:method: GET]
* h2h3 [:path: /v1/images/search?api_]
* h2h3 [:scheme: https]
* h2h3 [:authority: api.thecatapi.com]
* h2h3 [user-agent: curl/7.88.1]
* h2h3 [accept: */*]
* Using Stream ID: 1 (easy handle 0x11e810a00)
> GET /v1/images/search?api_ HTTP/2
> Host: api.thecatapi.com
> user-agent: curl/7.88.1
> accept: */*
>
< HTTP/2 200
< x-dns-prefetch-control: off
< x-frame-options: SAMEORIGIN
< strict-transport-security: max-age=15552000; includeSubDomains
< x-download-options: noopen
< x-content-type-options: nosniff
< x-xss-protection: 1; mode=block
< vary: Origin
< expires: Tue, 03 Jul 2001 06:00:00 GMT
< last-modified: Fri Sep 22 2023 00:34:23 GMT+0000 (Coordinated Universal Time)
< cache-control: post-check=0, pre-check=0
< authenticated: false
< content-type: application/json; charset=utf-8
< x-response-time: 2ms
< x-cloud-trace-context: 1cac74d299df233cece7ac59ae68e5a3
< date: Fri, 22 Sep 2023 00:34:23 GMT
< server: Google Frontend
< content-length: 103
<
* Connection #0 to host api.thecatapi.com left intact
[{"id":"MjA2MTgzMw","url":"https://cdn2.thecatapi.com/images/MjA2MTgzMw.jpg","width":440,"height":298}]
  ```

</details>

### Различия между версиями

Протоколу HTTP уже более 30 лет и он постоянно развивается.
С новыми версиями появляется больше возможностей и протокол становится все более оптимальным.

Полезно знать основные различия между версиями.

Подробно с историей развития HTTP можно ознакомиться на [hpbn](https://hpbn.co/brief-history-of-http/).

#### HTTP 0.9

Тупой как палка. Запрос клиента &mdash; ASCII строка, ответ сервера &mdash; тоже ASCII строка. Всё. 1991 год как никак.

#### HTTP 1.0 

В 1996 выходит [RFC 1945](https://datatracker.ietf.org/doc/html/rfc1945), в рамках которого описывают HTTP 1.0. 

В данной версии протокол приобретает такой внешний вид, под которым мы его знаем.

В запросе и ответе появляются заголовки. Теперь можно возвращать не только HTML, но и любую другую информацию.

**Соединение между клиентом и сервером закрывается после каждого запроса.**

#### HTTP 1.1

В 1999 финализируют следующую версию HTTP в [RFC 2616](https://www.ietf.org/rfc/rfc2616.txt). 

Изменения в основном заключаются в оптимизациях.

Внезапно все поняли, что TCP handshake для отправки одного запроса это слишком долго и можно все сделать эффективнее.
Появляется механизм keep-alive: 
TCP соединение держится активным и становится возможным в рамках одного соединения делать много запросов, что экономит ресурсы и latency.

#### HTTP 2.0

В 2015 протокол оптимизируют еще сильнее. Протокол становится "бинарным", заголовки лучше сжимаются, в рамках одного соединения можно обмениваться сообщениями в несколько потоков и становится разрешен server push.

Подробнее в блоге [CloudFlare](https://www.cloudflare.com/learning/performance/http2-vs-http1.1/).

![](https://freecontent.manning.com/wp-content/uploads/mentalmodel-HTTP2_in_Action2.png)

#### HTTP 3.0

В какой-то момент человечество решило, что TCP уже надоел, давайте сделаем HTTP над UDP. И придумали [HTTP/3.0 над QUIC](https://en.wikipedia.org/wiki/HTTP/3). 

В основном эта версия позволяет уменьшить latency при выполнении запросов. Но adoption пока небольшой.

## Раздаем картинки через HTTP

В директории [kittens](./website/kittens) реализовано простое Flask приложение,
которое является HTTP сервером, отдающим фото.

Также в директории можно найти [Dockerfile](./website/kittens/Dockerfile), который "запаковывает" данное приложение в Docker образ. 

И можно ознакомиться с [docker-compose.yaml](./website/docker-compose.yaml) файлом, поднимающем два контейнера сервера.

## Используем nginx как reverse proxy

Попробуем с помощью nginx сделать раздачу статики и балансировку по бэкендам.

Подробнее [тут](https://github.com/osukhoroslov/distsys-course-hse/tree/2023/seminars/03-http#nginx).