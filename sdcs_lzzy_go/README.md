### Docker 项目的创建


```shell
# 初始化docker部分，仅限于本机
# 将用户加入docker用户组
sudo usermod -aG docker $USER
newgrp docker

sudo mkdir -p /etc/systemd/system/docker.service.d
sudo vim /etc/systemd/system/docker.service.d/http-proxy.conf

# http-proxy.conf 在文件中添加：
[Service]
Environment="HTTP_PROXY=http://192.168.179.1:7890"
Environment="HTTPS_PROXY=http://192.168.179.1:7890"

sudo systemctl daemon-reload
sudo systemctl restart docker

# 验证：
sudo systemctl show --property=Environment docker
# Environment=HTTP_PROXY=http://192.168.179.1:7890 HTTPS_PROXY=http://192.168.179.1:7890

```

### Docker 项目的运行

若初始化完成，使用docker compose命令进行build和up

```shell
tar -xzvf distributed_system.tar.gz -C distributed_system

# 项目运行步骤
cd distributed_system # 转到项目目录

docker compose up --build # 使用docker compose工具

# 如果输出:bash: /usr/bin/docker-compose: 没有那个文件或目录，那就是没有docker-compose-plugin组件
sudo apt-get update
sudo apt-get install docker-compose-plugin # 安装docker plugin

# 等到node0-node1均输出:
# 执行测试程序:
./sdcs-test.sh 3
```