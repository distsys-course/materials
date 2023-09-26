module github.com/distsys-course/2021/02-practice-grpc/server

go 1.16

replace github.com/distsys-course/2021/02-practice-grpc/grpc => ../proto

require (
	google.golang.org/grpc v1.58.2
	google.golang.org/protobuf v1.31.0
)

require (
	github.com/distsys-course/2021/02-practice-grpc/grpc v0.0.0-00010101000000-000000000000
	golang.org/x/net v0.15.0 // indirect
	google.golang.org/genproto v0.0.0-20230920204549-e6e6cdab5c13 // indirect
	google.golang.org/genproto/googleapis/rpc v0.0.0-20230920204549-e6e6cdab5c13 // indirect
)
