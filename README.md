## 项目详情

UESTC 分布式系统大作业。

目标：完成一个简易分布式缓存系统


要求：
1. Cache数据以key-value形式存储在缓存系统节点内存中（不需要持久化）；
2. Cache数据以既定策略（round-robin或hash均可，不做限定）分布在不同节点（不考虑副本存储）；
3. 服务至少启动3个节点，不考虑节点动态变化（即运行中无新节点加入，也无故障节点退出）；
    1. 所有节点均提供HTTP访问入口；
    2. 客户端读写访问可从任意节点接入，每个请求只支持一个key存取；
    3. 若数据所在目标存储服务器与接入服务器不同，则接入服务器需通过内部RPC向目标存储服务器发起相同操作请求，并将目标服务器结果返回客户端。
4. HTTP API约定
    1. Content-type: application/json; charset=utf-8
    2. 写入/更新缓存：POST /。使用HTTP POST方法，请求发送至根路径，请求体为JSON格式的KV内容，示例如下：
    ```bash
    curl -XPOST -H "Content-type: application/json" http://server1/ -d '{"myname": "电子科技大学@2024"}'
    curl -XPOST -H "Content-type: application/json" http://server2/ -d '{"tasks": ["task 1", "task 2", "task 3"]}'
    curl -XPOST -H "Content-type: application/json" http://server3/ -d '{"age": 123}'
    ```
    3. 读取缓存 GET /{key}。使用HTTP GET方法，key直接拼接在根路径之后。为简化程序，对key格式不做要求（非URL安全字符需要进行urlencode）。
      1. 正常：返回HTTP 200，body为JSON格式的KV结果；
      2. 错误：返回HTTP 404，body为空。
        ```bash    
        curl http://server2/myname
        {"myname": "电子科技大学@2024"}

        curl http://server1/tasks
        {"tasks": ["task 1", "task 2", "task 3"]}

        curl http://server1/notexistkey
        # 404, not found
        ```

    4. 删除缓存 DELETE /{key}。永远返回HTTP 200，body为删除的数量。
        ```bash
        curl -XDELETE http://server3/myname
        1

        curl http://server1/myname


        curl -XDELETE http://server3/myname
        0
        ```
    5. 每个server将内部HTTP服务端口映射至Host，外部端口从9527递增，即若启动3个server，则通过http://127.0.0.1:9527，http://127.0.0.1:9528，http://127.0.0.1:9529可分别访问3个cache server。

## 项目概述

本项目使用两种语言均完成项目要求，分别位于``sdcs_lzzy_go``和``sdcs_lzzy_python``。go语言效率更高，但要求go语言基础和多线程等方面知识；python更为易懂，使用Flask和多线程。

可进入任一文件夹下完成项目执行，两个项目均具备README.md文件。

