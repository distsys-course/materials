module github.com/distsys-course/2021/02-practice-grpc/client

go 1.16

replace github.com/distsys-course/2021/02-practice-grpc/grpc => ../proto

require (
	github.com/distsys-course/2021/02-practice-grpc/grpc v0.0.0-00010101000000-000000000000  // create this module in ../grpc folder
	github.com/gin-gonic/gin v1.7.4
	google.golang.org/grpc v1.40.0
)
