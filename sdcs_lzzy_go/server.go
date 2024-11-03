package main

import (
    "context"
    "fmt"
    "log"
    "net"
    "net/http"
    "os"
    "regexp"
    "sync"
    "io/ioutil"
    pb "djhuang.top/cacheserver/cache"
    "google.golang.org/grpc"
)

var server cacheServer // server instance
var address [4]string
var client [2] pb.CacheClient // 2 rpc clients for communication with other servers
var conn [2] *grpc.ClientConn // 2 connections for the rpc clients

func setAddress() {
    switch os.Args[1] {
    case "1":
        address = [4]string{"127.0.0.1:9527", "127.0.0.1:9530", "127.0.0.1:9531", "127.0.0.1:9532"}
    case "2":
        address = [4]string{"127.0.0.1:9528", "127.0.0.1:9531", "127.0.0.1:9530", "127.0.0.1:9532"}
    case "3":
        address = [4]string{"127.0.0.1:9529", "127.0.0.1:9532", "127.0.0.1:9530", "127.0.0.1:9531"}
    default:
        fmt.Println("only 3 cacheservers.")
    }
}

// http Get handler
func handleGet(w http.ResponseWriter, key string) {
    fmt.Println("get", key)
    server.mu.RLock()
    defer server.mu.RUnlock()
    if value, ok := server.cache[key]; ok {
        w.WriteHeader(http.StatusOK)
        w.Header().Set("Content-Type", "application/json")
        fmt.Fprintf(w, "{\"%s\":\"%s\"}", key, value)
        return
    }
    w.WriteHeader(http.StatusNotFound)
}

// http Set handler
func handleSet(w http.ResponseWriter, jsonStr string) {
    reg := regexp.MustCompile(`{\s*"(.*)"\s*:\s*"(.*)"\s*}`)
    result := reg.FindAllStringSubmatch(jsonStr, -1)
    if len(result) == 0 || len(result[0]) < 3 {
        fmt.Println("Invalid JSON format")
        http.Error(w, "Invalid JSON format", http.StatusBadRequest)
        return
    }
    key, value := result[0][1], result[0][2]
    fmt.Println("set", key, ":", value)

    server.mu.Lock()
    server.cache[key] = value
    server.mu.Unlock()

    go CacheSet(client[0], &pb.SetRequest{Key: key, Value: value})
    go CacheSet(client[1], &pb.SetRequest{Key: key, Value: value})
    w.WriteHeader(http.StatusOK)
}

// http Delete handler
func handleDelete(w http.ResponseWriter, key string) {
    fmt.Println("delete", key)
    server.mu.Lock()
    defer server.mu.Unlock()
    if _, ok := server.cache[key]; ok {
        delete(server.cache, key)
        go CacheDelete(client[0], &pb.DeleteRequest{Key: key})
        go CacheDelete(client[1], &pb.DeleteRequest{Key: key})
        w.WriteHeader(http.StatusOK)
        fmt.Fprintln(w, "1")
    } else {
        w.WriteHeader(http.StatusOK)
        fmt.Fprintln(w, "0")
    }
}

// http request handler
func handleHttpRequest(w http.ResponseWriter, r *http.Request) {
    switch r.Method {
    case http.MethodGet:
        handleGet(w, r.URL.Path[1:])
    case http.MethodPost:
        body, err := ioutil.ReadAll(r.Body)
        if err != nil {
            http.Error(w, "Unable to read request body.", http.StatusInternalServerError)
            return
        }
        handleSet(w, string(body))
    case http.MethodDelete:
        handleDelete(w, r.URL.Path[1:])
    default:
        http.Error(w, "Unsupported HTTP request.", http.StatusMethodNotAllowed)
    }
}

// cacheServer type
type cacheServer struct {
    pb.UnimplementedCacheServer
    cache map[string]string
    mu    sync.RWMutex
}

// rpc server Get handler
func (s *cacheServer) GetCache(ctx context.Context, req *pb.GetRequest) (*pb.GetReply, error) {
    s.mu.RLock()
    defer s.mu.RUnlock()
    return &pb.GetReply{Key: req.Key, Value: s.cache[req.Key]}, nil
}

// rpc server Set handler
func (s *cacheServer) SetCache(ctx context.Context, req *pb.SetRequest) (*pb.SetReply, error) {
    s.mu.Lock()
    s.cache[req.Key] = req.Value
    s.mu.Unlock()
    return &pb.SetReply{}, nil
}

// rpc server Delete handler
func (s *cacheServer) DeleteCache(ctx context.Context, req *pb.DeleteRequest) (*pb.DeleteReply, error) {
    s.mu.Lock()
    defer s.mu.Unlock()
    if _, ok := s.cache[req.Key]; ok {
        delete(s.cache, req.Key)
        return &pb.DeleteReply{Num: 1}, nil
    }
    return &pb.DeleteReply{Num: 0}, nil
}

func startHttpServer() {
    http.HandleFunc("/", handleHttpRequest)
    fmt.Println("Listening HTTP on", address[0])
    log.Fatal(http.ListenAndServe(address[0], nil))
}

func startRpcServer() {
    lis, err := net.Listen("tcp", address[1])
    if err != nil {
        log.Fatalf("Failed to listen: %v", err)
    }

    grpcServer := grpc.NewServer()
    server = cacheServer{cache: make(map[string]string)}
    pb.RegisterCacheServer(grpcServer, &server)
    fmt.Println("Listening RPC on", address[1])
    grpcServer.Serve(lis)
}

func main() {
    if len(os.Args) != 2 {
        fmt.Println("Please specify server index (1-3).")
        return
    }

    setAddress()
    go startHttpServer()
    go startRpcServer()
    setupClient()

    select {}
}
