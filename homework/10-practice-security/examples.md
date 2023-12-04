```
$ curl -v -X POST 'localhost:8090/signup' \
    --data '{"username": "kek", "password": "kekpassword"}' \
*   Trying 127.0.0.1:8090...
* Connected to localhost (127.0.0.1) port 8090 (#0)
> POST /signup HTTP/1.1
> Host: localhost:8090
> User-Agent: curl/7.84.0
> Accept: */*
> Content-Length: 46
> Content-Type: application/x-www-form-urlencoded
>
* Mark bundle as not supporting multiuse
< HTTP/1.1 200 OK
< Set-Cookie: jwt=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImtlayIsImlhdCI6MTY3MDU3ODg1MH0.sVsvcV5GVJVyQcTEVGesoxMARIomGFNfHM8yG5XaRx60uJoreR5eteJP5sgDYOR1Rf9BGDw0Xu3brWBh29-XgworO7Ul6oSy1IO5Bn1N06K69cVEeXNdzlqS_XGYm-E-xmnt3MUmfOcN5Jx70Hsoe5vcHwB3kz2lHbE4VSeYhWpeaEcLxCR43Q7Ca9ouyx00mGgeEEqx83RQp87ORhDEaKGsxxg08oVbm4DPWIupiIOTGbwl21aTQFlXR1skWQJQWBqg4FjCcdXa3DVAUmaMZNi14Xwl3bBwoObKivH7hifPUhMjlo86m5BKqHgjuS6Vjl-doWSYrVG8zaxbXrhX-w
< Date: Fri, 09 Dec 2022 09:40:50 GMT
< Content-Length: 0
```

```
$ curl -v -X POST 'localhost:8090/login' \
    --data '{"username": "kek", "password": "kekpassword"}' \
*   Trying 127.0.0.1:8090...
* Connected to localhost (127.0.0.1) port 8090 (#0)
> POST /login HTTP/1.1
> Host: localhost:8090
> User-Agent: curl/7.84.0
> Accept: */*
> Content-Length: 46
> Content-Type: application/x-www-form-urlencoded
>
* Mark bundle as not supporting multiuse
< HTTP/1.1 200 OK
< Set-Cookie: jwt=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImtlayIsImlhdCI6MTY3MDU3ODkxOX0.V5iRJe-asej-1IDKth1taFabf5CU9jAPRph0UxYbPi0UnnMKeGuQmAAoVTLRPEbZSSPWkmD1MebAsNgIILpgnlvvxDqNU63fOn-GJ35vFgX5toGVCB6r7rIUimfFArIcOBb1k4eMOjlvCmxFnk133StHIzyZMFyw28v6FocqhhZ0pD5uNx1qTk5epWz1-KOrgWVlty9gi8kWU0ymWQ75R9Onpi8tuYG--Quv5K5WVt_b5j-ZCyakyb4lltzbovtc5QmYumujZuw2F1cm9tGCPgB7iaaQBFTQLXUPKIPj3WIaiCNwF3bQz7EXI8zuwkXCXjQgc8PdHIYuK5tMProg4g
< Date: Fri, 09 Dec 2022 09:41:59 GMT
< Content-Length: 0
```

```
$ curl -v -X GET 'localhost:8090/whoami' \
    -H 'Cookie: jwt=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImtlayIsImlhdCI6MTY3MDU3ODkxOX0.V5iRJe-asej-1IDKth1taFabf5CU9jAPRph0UxYbPi0UnnMKeGuQmAAoVTLRPEbZSSPWkmD1MebAsNgIILpgnlvvxDqNU63fOn-GJ35vFgX5toGVCB6r7rIUimfFArIcOBb1k4eMOjlvCmxFnk133StHIzyZMFyw28v6FocqhhZ0pD5uNx1qTk5epWz1-KOrgWVlty9gi8kWU0ymWQ75R9Onpi8tuYG--Quv5K5WVt_b5j-ZCyakyb4lltzbovtc5QmYumujZuw2F1cm9tGCPgB7iaaQBFTQLXUPKIPj3WIaiCNwF3bQz7EXI8zuwkXCXjQgc8PdHIYuK5tMProg4g'
Note: Unnecessary use of -X or --request, GET is already inferred.
*   Trying 127.0.0.1:8090...
* Connected to localhost (127.0.0.1) port 8090 (#0)
> GET /whoami HTTP/1.1
> Host: localhost:8090
> User-Agent: curl/7.84.0
> Accept: */*
> Cookie: jwt=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImtlayIsImlhdCI6MTY3MDU3ODkxOX0.V5iRJe-asej-1IDKth1taFabf5CU9jAPRph0UxYbPi0UnnMKeGuQmAAoVTLRPEbZSSPWkmD1MebAsNgIILpgnlvvxDqNU63fOn-GJ35vFgX5toGVCB6r7rIUimfFArIcOBb1k4eMOjlvCmxFnk133StHIzyZMFyw28v6FocqhhZ0pD5uNx1qTk5epWz1-KOrgWVlty9gi8kWU0ymWQ75R9Onpi8tuYG--Quv5K5WVt_b5j-ZCyakyb4lltzbovtc5QmYumujZuw2F1cm9tGCPgB7iaaQBFTQLXUPKIPj3WIaiCNwF3bQz7EXI8zuwkXCXjQgc8PdHIYuK5tMProg4g
>
* Mark bundle as not supporting multiuse
< HTTP/1.1 200 OK
< Date: Fri, 09 Dec 2022 09:43:08 GMT
< Content-Length: 10
< Content-Type: text/plain; charset=utf-8
<
* Connection #0 to host localhost left intact
Hello, kek%
```

```
$ curl -v 'localhost:8091/put?key=kek' -d '{"value": "lol"}' -H 'Cookie: jwt=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImtlayIsImlhdCI6MTY3MDU3OTEyN30.CnDD1A1ogiX5jyGbxfblWpqQ1xEo6wafS9qdh73Gd9Z2_7_-V3t-g4kNDcivTASI6ELm2y5YxNbYhxFZipEl6PIwq19zJ3SAWIyagu2EmhcrL4TyF1fKJm4n5mX4j_pHdwiT-84KfBUt9igQJBGEM8YC7v7k5QuvCGlv2ShXBdwe-p4n2Lo1-LNyZY_DoHrWmaAAppsKQHH6x29Y6rD8Nh20V8ACZMoXJDW0OtQCPWGtb9p_xM4qYxb5KDmRbKoU4IUUvLOSa5Ktb1Om4uKvms0bHpZ3j8ATKELz4GVptNnfmvLuD8zaQBhtfEGOSioKzj3rEDkRrvJAybe3DlK1fA'
*   Trying 127.0.0.1:8091...
* Connected to localhost (127.0.0.1) port 8091 (#0)
> POST /put?key=kek HTTP/1.1
> Host: localhost:8091
> User-Agent: curl/7.84.0
> Accept: */*
> Cookie: jwt=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImtlayIsImlhdCI6MTY3MDU3OTEyN30.CnDD1A1ogiX5jyGbxfblWpqQ1xEo6wafS9qdh73Gd9Z2_7_-V3t-g4kNDcivTASI6ELm2y5YxNbYhxFZipEl6PIwq19zJ3SAWIyagu2EmhcrL4TyF1fKJm4n5mX4j_pHdwiT-84KfBUt9igQJBGEM8YC7v7k5QuvCGlv2ShXBdwe-p4n2Lo1-LNyZY_DoHrWmaAAppsKQHH6x29Y6rD8Nh20V8ACZMoXJDW0OtQCPWGtb9p_xM4qYxb5KDmRbKoU4IUUvLOSa5Ktb1Om4uKvms0bHpZ3j8ATKELz4GVptNnfmvLuD8zaQBhtfEGOSioKzj3rEDkRrvJAybe3DlK1fA
> Content-Length: 16
> Content-Type: application/x-www-form-urlencoded
>
* Mark bundle as not supporting multiuse
< HTTP/1.1 200 OK
< Date: Fri, 09 Dec 2022 09:49:58 GMT
< Content-Length: 0
```

```
$ curl -v 'localhost:8091/get?key=kek' -H 'Cookie: jwt=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImtlayIsImlhdCI6MTY3MDU3OTEyN30.CnDD1A1ogiX5jyGbxfblWpqQ1xEo6wafS9qdh73Gd9Z2_7_-V3t-g4kNDcivTASI6ELm2y5YxNbYhxFZipEl6PIwq19zJ3SAWIyagu2EmhcrL4TyF1fKJm4n5mX4j_pHdwiT-84KfBUt9igQJBGEM8YC7v7k5QuvCGlv2ShXBdwe-p4n2Lo1-LNyZY_DoHrWmaAAppsKQHH6x29Y6rD8Nh20V8ACZMoXJDW0OtQCPWGtb9p_xM4qYxb5KDmRbKoU4IUUvLOSa5Ktb1Om4uKvms0bHpZ3j8ATKELz4GVptNnfmvLuD8zaQBhtfEGOSioKzj3rEDkRrvJAybe3DlK1fA'
*   Trying 127.0.0.1:8091...
* Connected to localhost (127.0.0.1) port 8091 (#0)
> GET /get?key=kek HTTP/1.1
> Host: localhost:8091
> User-Agent: curl/7.84.0
> Accept: */*
> Cookie: jwt=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImtlayIsImlhdCI6MTY3MDU3OTEyN30.CnDD1A1ogiX5jyGbxfblWpqQ1xEo6wafS9qdh73Gd9Z2_7_-V3t-g4kNDcivTASI6ELm2y5YxNbYhxFZipEl6PIwq19zJ3SAWIyagu2EmhcrL4TyF1fKJm4n5mX4j_pHdwiT-84KfBUt9igQJBGEM8YC7v7k5QuvCGlv2ShXBdwe-p4n2Lo1-LNyZY_DoHrWmaAAppsKQHH6x29Y6rD8Nh20V8ACZMoXJDW0OtQCPWGtb9p_xM4qYxb5KDmRbKoU4IUUvLOSa5Ktb1Om4uKvms0bHpZ3j8ATKELz4GVptNnfmvLuD8zaQBhtfEGOSioKzj3rEDkRrvJAybe3DlK1fA
>
* Mark bundle as not supporting multiuse
< HTTP/1.1 200 OK
< Content-Type: application/json
< Date: Fri, 09 Dec 2022 09:50:09 GMT
< Content-Length: 15
<
* Connection #0 to host localhost left intact
{"value":"lol"}%
```