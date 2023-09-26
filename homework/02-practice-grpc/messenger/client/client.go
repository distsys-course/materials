package main

import (
	"context"
	"fmt"
	mes_grpc "../proto"
	"github.com/gin-gonic/gin"
	"github.com/golang/protobuf/jsonpb"
	"google.golang.org/grpc"
	"net/http"
	"os"
	"sync"
	"time"
)

type ChatMessage struct {
	Author   string    `json:"author"`
	Text     string    `json:"text"`
	SendTime time.Time `json:"sendTime"`
}

type MessengerClient struct {
	pendingMessages []ChatMessage
	pendingMutex    sync.Mutex
	grpcClient      mes_grpc.messengerServerClient
}

func NewMessengerClient(serverAddr string) *MessengerClient {
	cc := grpc.NewClientConn(serverAddr, grpc.NewClientStream(context.Background(), ))
	return &MessengerClient{
		pendingMessages: []ChatMessage{},
        pendingMutex:    sync.Mutex{},
		grpcClient:      mes_grpc.NewMessengerServerClient(cc),
	}
}

func (c *MessengerClient) SendMessage(req mes_grpc.SendRequest) {
	c.pendingMutex.Lock()
    c.pendingMessages = append(c.pendingMessages, ChatMessage{
        Author:   req.Author,
        Text:     req.Text,
        SendTime: time.Now(),
    })
    c.pendingMutex.Unlock()
}

func (c *MessengerClient) GetPending() (messages []ChatMessage) {
	c.pendingMutex.Lock()
	result := c.pendingMessages
	c.pendingMessages = nil
	c.pendingMutex.Unlock()
	return result
}

type MessageResponse struct {
	SendTime *time.Time `json:"sendTime"`
	Error    *string    `json:"error"`
}

func main() {
	r := gin.Default()
	serverAddr := os.Getenv("MESSENGER_SERVER_ADDR")
	if serverAddr == "" {
		serverAddr = "localhost:51075"
		fmt.Println("Missing MESSENGER_SERVER_ADDR variable, using default value: " + serverAddr)
	}
	// TODO: create your grpc client with given address
	r.POST("/getAndFlushMessages", func(c *gin.Context) {
		c.JSON(http.StatusOK, client.GetPending())
	})

	r.POST("/sendMessage", func(c *gin.Context) {
		// TODO: implement send message here, that parses body into protobuf and sends to the server
		c.JSON(http.StatusOK, MessageResponse{SendTime: nil})  // TODO: do not forget to fill SendTime
		return
	})

	// TODO: run consumer in a goroutine

	addr := os.Getenv("MESSENGER_HTTP_PORT")
	if addr == "" {
		addr = "0.0.0.0:8080"
		fmt.Println("Missing MESSENGER_HTTP_PORT variable, using default value: 8080")
	} else {
		addr = "0.0.0.0:" + addr
	}
	if err := r.Run(addr); err != nil {
		panic(err)
	}
}