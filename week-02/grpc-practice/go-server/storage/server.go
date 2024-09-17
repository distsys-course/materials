package storage

import (
	"context"
	"errors"
	storagepb "hsegrpc/proto"
	"sync"
	"time"

	"google.golang.org/protobuf/types/known/timestamppb"
)

type Value struct {
	payload   uint64
	updatedAt time.Time
}

// toProto transforms struct into protobuf wrapper.
func (v *Value) toProto() *storagepb.Value {
	return &storagepb.Value{
		Payload:   v.payload,
		UpdatedAt: timestamppb.New(v.updatedAt),
	}
}

type Server struct {
	// Server must implement the Storage protobuf interface.
	storagepb.UnimplementedStorageServer

	// We use mutex to synchronize access to the value.
	valueLocker sync.RWMutex
	value       Value
}

func NewServer() *Server {
	return &Server{}
}

func (s *Server) PutValue(_ context.Context, request *storagepb.PutRequest) (*storagepb.PutResponse, error) {
	s.valueLocker.Lock()
	defer s.valueLocker.Unlock()

	// Check if the given value not empty.
	if request.GetValue() == nil {
		return nil, errors.New("missed value")
	}

	s.value = Value{
		payload:   request.GetValue().GetPayload(),
		updatedAt: time.Now(),
	}

	return &storagepb.PutResponse{
		Value: s.value.payload,
	}, nil
}

func (s *Server) GetValue(_ context.Context, _ *storagepb.GetRequest) (*storagepb.GetResponse, error) {
	s.valueLocker.RLock()
	defer s.valueLocker.RUnlock()

	return &storagepb.GetResponse{
		Value: s.value.toProto(),
	}, nil
}
