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

# 2 2022.11.12
# 2.1 功能
- server有欢迎套接字和连接套接字, 支持多个client并行上传文件, client保证可靠传输并带有拥塞控制

- 每次传输的是一个包, C语言的结构体定义如下

    ```C
    typedef struct s_packet {
        int length; // data的有效长度
        int seq; // 序号
        int ack; // 确认号
        int isfin; // 结束传输(1)
        int issyn; // 握手连接(1)
        char[PACKET_SIZE] data; // 负载
    } packet;
    ```

- 连接建立采用3次握手

    - client向server发送seq=1,issyn=1
    - server的欢迎套接字分配连接端口号, 并向client返回issyn=1, data=connection_port
    - client向server发送seq=2, issyn=1, 并建立与connection_port的连接
    - server的欢迎套接字结束3次握手, 之后启动连接套接字线程

- 可靠传输采用流水线GBN

    - 每个client与server的连接都是持续连接, 也就是说一次连接可以串行传输任意数量的文件, 用户每上传一个文件前只需在命令行输入该文件的相对路径
    - 每个文件都被拆分为一系列负载大小为PACKET_SIZE的包传输, 方便起见, 对于每个文件的传输, seq都是从1开始的, 而且指的是第几个包而不是第几个字节
    - 实质上, 传输每个用户输入的相对路径的文件都是分两次传输两个文件, 第一次传输一个内容为文件名的temp.txt, 第二次才传输文件本身, 这是为了让接收端知道保存的文件名

- 拥塞控制采用TCP-Tahoe

    - 发送端维护定时器timer, 拥塞窗口cwnd和阈值ssthresh
    - cwnd的增长分为慢启动SS和拥塞避免CA两个阶段
    - 方便起见, 不支持快重传, 每次timeout会将cwnd设为1

- 终止连接采用服务端超时的方法

    - client用户输入一个空的相对路径则关闭客户端套接字
    - server对连接套接字设置timeout, 捕捉到超时异常则关闭连接套接字
# 2.2 TODO

- client的下载文件功能
- 记录平均上传下载速度，以及丢包率
- GBN -> TCP ?

# 附

# 附1 命令行
python server.py
python client.py
# 附2 源文件地址与目的地地址
client/sleep.png
server/sleep.png
