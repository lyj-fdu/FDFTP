# 1 题目

## 1.1 概述

基于UDP，通过Python的socket库实现可靠的文件传输：FDFTP

## 1.2 基本要求

- 基于Python3.6
- 编写server程序和client程序，client可以通过命令行的命令向server上传和下载大文件，server可以同时支持多个client。
- 自选算法解决丢包，超时，乱序等问题
- 自选算法进行拥塞控制
- 记录平均上传下载速度，以及丢包率

## 1.3 加分项

- 多线程下载同一个文件
- 自己设计的可靠传输和拥塞控制算法
- 选用课程内容以外的算法
- 设计安全机制
- 支持断点续传
- ……
- 以及其他在基本要求之上的功能实现

## 1.4 测试

- 用VMware安装两台Ubuntu虚拟机, 并改为桥接模式, 通过ifconfig获得各自的IP地址, 
    NOTE: 注意不要连校园网, 用自己的路由器或者手机热点才行
- 利用tc命令模拟丢包, 延迟, 乱序等情况
- 利用md5sum命令比较传输的文件是否准确无误

## 1.5 报告

- 设计思路
- 算法细节
- 在模拟环境下的性能测试
- 使用手册……

# 2 2022.11.11 - 2022.11.13

## 2.1 功能

​	server可以并行连接多个client上传下载文件, 保证可靠传输并带有拥塞控制

## 2.2 运行

- 必须首先运行server, server运行的命令为`python server.py`
- 接下来可以开启多个client, 每个client运行的命令为`python client.py`
- 在client的通过命令行可以上传或下载位于指定文件夹下的文件, 示例如下:
  - 上传位于文件夹`client/`下的文件`sleep.png`的命令为`fsnd sleep.png`
  - 下载位于文件夹`server/`下的文件`sleep.png`的命令为`frcv sleep.png`

## 2.3 设计

- 项目结构如下: 

    ``` plain
    |_client: 存储客户端文件
      |_temp: 存储客户端socket的临时文件
        ...
      ...
    |_server: 存储服务器文件
      |_temp: 存储服务器socket的临时文件
        ...
      ...
    client.py: 客户端, 其中有类Client及其实例化运行
    config.py: 配置参数
    rdt.py: 可靠传输与拥塞控制的主要实现, 其中有类rdt, 作为类Client和类Server的父类
    README.md: 说明文档(本文档)
    server.py: 服务器, 其中有类Server及其实例化运行
    ```

- 连接建立采用3次握手

    - client向server发送seq=1,issyn=1
    - server的欢迎套接字分配连接端口号, 并向client返回issyn=1, data=connection_port
    - client向server发送seq=2, issyn=1, 并建立与connection_port的连接
    - server的欢迎套接字结束3次握手, 之后启动连接套接字线程

- 可靠传输采用流水线GBN

    - 每个client与server的连接都是持续连接, 也就是说一次连接可以串行传输任意数量的文件, 用户输入空字符串则退出, 用户输入`fsnd filename`就可以将文件`client/filename`上传到`server/filename`, 用户输入`frcv filename`就可以将文件`server/filename`下载到`client/filename`, 用户输入其他字符串则要重新输入

    - 发送方将每个文件拆分为一系列负载大小为PACKET_SIZE的包传输, 方便起见, 对于每个文件的传输, seq都是从1开始的, 而且指的是第几个包而不是第几个字节。其中, 包的C语言的结构体定义如下: 

      ``` c
      typedef struct s_packet {
          int length; // data的有效长度
          int seq; // 序号
          int ack; // 确认号
          int isfin; // 结束传输(1)
          int issyn; // 握手连接(1)
          char[PACKET_SIZE] data; // 负载
      } packet;
      ```

    - 实质上, client每个命令会引发两次的文件传输：如果client想上传文件, 先发送一个带有用户输入命令的临时文件给server, 然后再发送想上传的文件给server; 如果client想下载文件, 先发送一个带有用户输入命令的临时文件给server, 然后从server接收想下载的文件。临时文件的名称为该socket的端口号, client和server的临时文件分别为`client/temp/<client_port>.txt`和`server/temp/<server_port>.txt`

    - 如果client尝试传送一个不存在的文件, 则不会与server交换报文, 而是直接请求用户输入下一个命令; 如果client请求server下载一个不存在的文件, server在接收文件名后, 会定时发送fin并等待client的finack

- 拥塞控制采用TCP-Tahoe

    - 发送端维护定时器timer, 拥塞窗口cwnd和阈值ssthresh
    - cwnd的增长分为慢启动SS和拥塞避免CA两个阶段
    - 方便起见, 不支持快重传, 仅每次timeout会将cwnd设为1

- 终止连接采用服务端超时的方法

    - client用户输入一个空的相对路径则关闭客户端套接字, 同时删除临时文件
    - server对连接套接字设置timeout, 捕捉到超时异常则关闭连接套接字, 同时删除临时文件
    - client能够检测到server的timeout, 再次尝试上传或下载文件时, 会关闭客户端套接字, 同时删除临时文件
    
## 2.4 TODO

- 记录平均上传下载速度，以及丢包率
- 写一下算法细节
- 校验和？
- 加分项？

# 附

## 附1 命令行

python server.py
python client.py

## 附2 上传下载文件命令示例

fsnd sleep.png
frcv sleep.png
