//go:generate protoc --go_out=. --go_opt=paths=source_relative --go-grpc_out=. --go-grpc_opt=paths=source_relative proto/storage.proto
package main

import (
	"fmt"
	storagepb "hsegrpc/proto"
	"hsegrpc/storage"
	"log"
	"net"
	"os"

	"google.golang.org/grpc"
	"google.golang.org/grpc/reflection"
)

func main() {
	// Reading server address from env.
	addr := os.Getenv("SERVER_ADDR")
	if addr == "" {
		addr = "0.0.0.0:51000"

		fmt.Println("Missing SERVER_ADDR, using default value: " + addr)
	}

	// Creating a TCP socket.
	lis, err := net.Listen("tcp", addr)
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}

	grpcServer := grpc.NewServer()
	// If you want to connect to the server via grpcurl, you have to register the reflection service.
	reflection.Register(grpcServer)

	// Creating and registering implementation of the storage service.
	storageService := storage.NewServer()
	storagepb.RegisterStorageServer(grpcServer, storageService)

	// Starting the server.
	err = grpcServer.Serve(lis)
	if err != nil {
		log.Fatalf("server failed")
	}
}
