package main

/*
Connect client 1:

  wscat --connect 'localhost:8000/connect?author=lupa'

Connect client 2:

    wscat --connect 'localhost:8000/connect?author=lupa'
Message: {"Text": "hi there"}
*/

import (
	"log"
	"net/http"
	"os"
	"time"

	"github.com/google/uuid"
	"github.com/gorilla/websocket"
)

type MessageStream struct {
	Text     string
	Author   string
	SendTime *time.Time
}

type MessengerServer struct {
	history chan *MessageStream
	toSend  map[string]chan *MessageStream
}

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
}

func (s *MessengerServer) Connect(w http.ResponseWriter, r *http.Request) {
	// Extract author from the URL query parameters
	author := r.URL.Query().Get("author")
	if author == "" {
		w.WriteHeader(http.StatusBadRequest)
		return
	}

	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("failed to upgrade: %s\n", err)
		return
	}

	id := uuid.New()
	s.toSend[id.String()] = make(chan *MessageStream, 1000)
	log.Printf("Connected: %v\n", id)

	go func() {
		for {
			var msg MessageStream
			err := conn.ReadJSON(&msg)
			if err != nil {
				log.Println("Failed to decode a message:", err)
				return
			}

			log.Printf("Received from %s: %v\n", author, msg)

			now := time.Now()
			msg.SendTime = &now
			msg.Author = author
			s.history <- &msg
		}
	}()

	for {
		mes := <-s.toSend[id.String()]
		err := conn.WriteJSON(mes)
		if err != nil {
			log.Printf("Deleted %v stream, sending error: %v", id.String(), err)
			delete(s.toSend, id.String())

			return
		}

		log.Printf("Sent to stream %v: %v\n", id, mes)
	}
}

func (s *MessengerServer) fanout() {
	for {
		mes := <-s.history

		log.Printf("Got from history: %v", mes)

		for _, ch := range s.toSend {
			ch <- mes
		}
	}
}

func main() {
	port := os.Getenv("MESSENGER_SERVER_PORT")
	if port == "" {
		port = "8000"
		log.Println("Missing MESSENGER_SERVER_PORT, using default value: " + port)
	}
	server := MessengerServer{
		history: make(chan *MessageStream, 1000),
		toSend:  make(map[string]chan *MessageStream),
	}

	http.HandleFunc("/connect", server.Connect)

	go server.fanout()

	log.Fatal(http.ListenAndServe("0.0.0.0:"+port, nil))
}
