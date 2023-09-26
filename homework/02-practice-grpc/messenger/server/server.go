package main

import (
	"context"
	"fmt"
	"log"
	"net"
	"os"
	mes_grpc "../proto"
	"sync"
	"time"
	"google.golang.org/grpc"
	"google.golang.org/grpc/reflection"
	"google.golang.org/protobuf/types/known/timestamppb"
)

type Server struct {
	mes_grpc.UnimplementedMessengerServerServer
	Mutex sync.Mutex
	MessageQueue []*mes_grpc.Message
}

func NewServer() *Server {
	return &Server{
		Mutex: sync.Mutex{},
        MessageQueue: []*mes_grpc.Message{},
    }
}

func (s *Server) SendMessage(ctx context.Context, in *mes_grpc.SendRequest) (*mes_grpc.SendResponse, error) {
	cur_time := time.Now()
	mes := &mes_grpc.Message{
		Author: in.Author,
		Text: in.Text,
        SendTime: timestamppb.New(cur_time),
	}
	s.Mutex.Lock()
    s.MessageQueue = append(s.MessageQueue, mes)
    s.Mutex.Unlock()
    return &mes_grpc.SendResponse{
		SendTime: timestamppb.New(cur_time),
	}, nil
}

func (s *Server) ReadMessages(req *mes_grpc.ReadRequest, rec mes_grpc.MessengerServer_ReadMessagesServer) error {
	cur_timestamp := time.Now()
	s.Mutex.Lock()
	defer s.Mutex.Unlock()
	for mes := range s.MessageQueue {
		if cur_timestamp.Before(s.MessageQueue[mes].SendTime.AsTime()) {
			continue
		}
		if err := rec.Send(s.MessageQueue[mes]); err != nil {
			return err
		}
	}
	return nil
}

func main() {
	port := os.Getenv("MESSENGER_SERVER_PORT")
	addr := ""
	if port == "" {
		addr = "0.0.0.0:51075"
		fmt.Println("Missing MESSENGER_SERVER_PORT, using default value: 51075")
	} else {
		addr = "0.0.0.0:" + port
	}
	// Creating a TCP socket.
	lis, err := net.Listen("tcp", addr)
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}

	grpcServer := grpc.NewServer()
	reflection.Register(grpcServer)

	messengerService := NewServer()
	mes_grpc.RegisterMessengerServerServer(grpcServer, messengerService)
	
	if err = grpcServer.Serve(lis); err != nil {
		log.Fatalf("failed to serve: %v", err)
	}
}
