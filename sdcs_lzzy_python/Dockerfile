# 基于 Ubuntu 20.04 的镜像
FROM ubuntu:20.04

# 设置工作目录
WORKDIR /app

# 更换 apt-get 镜像源
COPY ./sources.list /etc/apt/sources.list

# 更新系统并安装 Python 3.9 和所需组件
RUN apt-get update -y \
    && apt-get install -y software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update -y \
    && apt-get install -y python3.9 python3.9-distutils python3.9-venv python3-pip --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.9 1

# 设置 pip 镜像源为清华源，增加下载速度
RUN mkdir -p ~/.pip && \
    echo '[global]' > ~/.pip/pip.conf && \
    echo 'index-url = https://pypi.tuna.tsinghua.edu.cn/simple/' >> ~/.pip/pip.conf

# 拷贝项目文件
COPY . .

# 安装 Python 项目依赖
RUN python -m pip install --upgrade pip setuptools \
    && python -m pip install -r requirements.txt

# 暴露端口
EXPOSE 8000
EXPOSE 5000

# 启动 Flask 应用
CMD ["python", "cache_node.py"]
