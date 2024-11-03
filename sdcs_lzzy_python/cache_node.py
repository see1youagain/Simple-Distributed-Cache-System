import hashlib
import json
import threading
import time
from concurrent import futures

import flask
import grpc
from flask import request, Response
import logging

import sdcs_pb2
import sdcs_pb2_grpc

# 配置日志
logging.basicConfig(level=logging.FATAL)

# 用于异步线程定时
_ONE_DAY_IN_SECONDS = 60 * 60 * 24

app = flask.Flask(__name__)

# 静态配置节点信息
server_rpc_url = ["node0:8000", "node1:8000", "node2:8000"]
server_cnt = 3

# 缓存 gRPC 通道和客户端
grpc_channels = {}
grpc_clients = {}

def get_grpc_client(server_id):
    if server_id not in grpc_clients:
        conn = grpc.insecure_channel(server_rpc_url[server_id])
        client = sdcs_pb2_grpc.CacheNodeStub(channel=conn)
        grpc_channels[server_id] = conn
        grpc_clients[server_id] = client
    return grpc_clients[server_id]

# 节点的本地缓存
cache = dict()
# 节点中已存储的键值对总数
total_cnt = 0

# rpc节点
class Node(sdcs_pb2_grpc.CacheNodeServicer):
    # rpc更新kv方法
    def UpdateKeyValue(self, request, context):
        global total_cnt
        update_cnt = 0
        # 入参
        kv_string = request.kv_string

        # 更新kv
        kv_map = json.loads(kv_string)
        for key, value in kv_map.items():
            # 校验本地无重复key值，则total_cnt+1
            is_exist = cache.get(key)
            if is_exist is None:
                total_cnt += 1
            # 更新键值对
            cache.update({key: value})
            update_cnt += 1

        return sdcs_pb2.UpdateKeyValueResponse(update_cnt=update_cnt)

    # rpc查询kv方法
    def SearchKeyValue(self, request, context):
        # 入参
        key = request.key

        # 查询kv
        value = cache.get(key)
        if value is None:
            resp_data = "{}"  # 返回空的 JSON 对象
        else:
            resp_data = json.dumps({key: value})
        return sdcs_pb2.SearchKeyValueResponse(kv_string=resp_data)

    # rpc删除kv方法
    def DeleteKeyValue(self, request, context):
        delete_cnt = 0
        # 入参
        key = request.key

        # 删除kv
        value = cache.pop(key, None)
        if value:
            delete_cnt += 1
        return sdcs_pb2.DeleteKeyValueResponse(delete_cnt=delete_cnt)

# grpc服务端
def run_grpc_server():
    grpc_server = grpc.server(futures.ThreadPoolExecutor(max_workers=100))
    sdcs_pb2_grpc.add_CacheNodeServicer_to_server(Node(), grpc_server)
    grpc_server.add_insecure_port("0.0.0.0:8000")
    grpc_server.start()
    logging.info("grpc_server starts..")

    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        grpc_server.stop(0)

# 启动grpc服务器
grpc_thread = threading.Thread(target=run_grpc_server)
grpc_thread.start()

# 计算哈希值
def get_hash_value(key):
    md5_hash = hashlib.md5(key.encode()).hexdigest()
    return int(md5_hash, 16)

# 写入/更新缓存请求
@app.route('/', methods=['POST'])
def update_cache():
    # 解析请求参数
    request_data = request.json

    # 构建存放列表，每个列表对应一个服务器节点
    kv_to_update_list = [{} for _ in range(server_cnt)]

    # 遍历键值对，计算key的哈希值
    for key, value in request_data.items():
        # 计算哈希值
        hash_value = get_hash_value(key)
        # 计算分配的节点位置
        index = hash_value % server_cnt
        # 将键值对添加到对应服务器节点的列表中
        kv_to_update_list[index][key] = value

    # 写入/更新至节点
    result_cnt = 0  # 累计写入/更新的键值对个数
    for server_i in range(server_cnt):
        if not kv_to_update_list[server_i]:
            continue
        # 发送rpc请求
        try:
            result = grpc_update_client(kv_to_update_list[server_i], server_i)
            result_cnt += result
        except Exception as e:
            logging.error(f"Update failed: {e}")
    return "update successfully!", 200

# grpc客户端 更新请求
def grpc_update_client(kv_map={}, server_id=0):
    client = get_grpc_client(server_id)
    kv_string = json.dumps(kv_map)
    rpc_request = sdcs_pb2.UpdateKeyValueRequest(kv_string=kv_string)
    rsp = client.UpdateKeyValue(rpc_request)
    update_cnt = rsp.update_cnt
    return update_cnt

# grpc客户端 查询请求
def grpc_search_client(key=None, server_id=0):
    client = get_grpc_client(server_id)
    rpc_request = sdcs_pb2.SearchKeyValueRequest(key=key)
    rsp = client.SearchKeyValue(rpc_request)
    kv_string = rsp.kv_string
    if not kv_string:
        kv_string = "{}"  # 确保返回有效的 JSON 字符串
    return kv_string

# 读取缓存请求
@app.route('/<key>', methods=['GET'])
def get_cache(key):
    # 计算哈希值
    hash_value = get_hash_value(key)
    index = hash_value % server_cnt

    # 发送rpc请求
    try:
        result = grpc_search_client(key, index)
        kv = json.loads(result)
    except Exception as e:
        logging.error(f"Search failed: {e}")
        return "", 500

    # 返回HTTP响应
    value = kv.get(key)
    if value is None:
        return "", 404
    else:
        response = json.dumps(kv, ensure_ascii=False)
        return Response(response, content_type='application/json; charset=utf-8'), 200

# 删除缓存请求
@app.route('/<key>', methods=['DELETE'])
def delete_cache(key):
    # 计算哈希值
    hash_value = get_hash_value(key)
    index = hash_value % server_cnt

    # 发送rpc请求
    try:
        result = grpc_delete_client(key, index)
        delete_cnt = result
    except Exception as e:
        logging.error(f"Delete failed: {e}")
        return "0", 200
    return str(delete_cnt), 200

# grpc客户端 删除请求
def grpc_delete_client(key=None, server_id=0):
    client = get_grpc_client(server_id)
    rpc_request = sdcs_pb2.DeleteKeyValueRequest(key=key)
    rsp = client.DeleteKeyValue(rpc_request)
    delete_cnt = rsp.delete_cnt
    return delete_cnt

import concurrent.futures

def preload_data():
    kv_to_update_list = [{} for _ in range(server_cnt)]
    for i in range(1, 500+1):
        key = f"key-{i}"
        value = f"value {i}"
        index = get_hash_value(key) % server_cnt
        kv_to_update_list[index][key] = value

    # 使用线程池并行处理预加载
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(grpc_update_client, kv_to_update_list[server_i], server_i)
            for server_i in range(server_cnt) if kv_to_update_list[server_i]
        ]
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                logging.info(f"Preloaded data with {result} updates.")
            except Exception as e:
                logging.error(f"Preload failed: {e}")
        
def ready_for_test():
    time.sleep(0.5)
    print("Flask app ready, running...")
    print("=" * 80)
    print("All nodes are initialized. Ready to start tests.")
    print("=" * 80)


if __name__ == '__main__':
    print("Starting initing grpc nodes, please don't shutdown...")
    preload_data()  # 在启动 Flask 之前预加载数据
    print("All nodes are initialized. Ready to start tests.")
    notice_thread = threading.Thread(target=ready_for_test)
    notice_thread.setDaemon(True)
    notice_thread.start()

    app.run('0.0.0.0', port=5000, threaded=True)


