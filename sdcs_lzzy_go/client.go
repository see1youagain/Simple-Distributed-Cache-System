package main

import (
    "context"
    "fmt"
    "log" // 添加此行
    "time"

    "google.golang.org/grpc"
    "google.golang.org/grpc/credentials/insecure"
    pb "djhuang.top/cacheserver/cache"
)

func setupClient() {
    opts := []grpc.DialOption{grpc.WithTransportCredentials(insecure.NewCredentials())}
    var err error

    conn[0], err = grpc.Dial(address[2], opts...)
    if err != nil {
        log.Fatalf("Failed to connect to %s: %v", address[2], err)
    }
    fmt.Println("Set up client for", address[2])
    client[0] = pb.NewCacheClient(conn[0])

    conn[1], err = grpc.Dial(address[3], opts...)
    if err != nil {
        log.Fatalf("Failed to connect to %s: %v", address[3], err)
    }
    fmt.Println("Set up client for", address[3])
    client[1] = pb.NewCacheClient(conn[1])
}

// gRPC client Get request
func CacheGet(client pb.CacheClient, req *pb.GetRequest) {
    ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
    defer cancel()
    if _, err := client.GetCache(ctx, req); err != nil {
        fmt.Println("CacheGet failed:", err)
    }
}

// gRPC client Set request
func CacheSet(client pb.CacheClient, req *pb.SetRequest) {
    ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
    defer cancel()
    if _, err := client.SetCache(ctx, req); err != nil {
        fmt.Println("CacheSet failed:", err)
    }
}

// gRPC client Delete request
func CacheDelete(client pb.CacheClient, req *pb.DeleteRequest) {
    ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
    defer cancel()
    if _, err := client.DeleteCache(ctx, req); err != nil {
        fmt.Println("CacheDelete failed:", err)
    }
}
