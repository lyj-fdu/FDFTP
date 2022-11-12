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

# 2 2022.11.12
# 2.1 功能
- server有欢迎套接字和连接套接字, 支持多个client并行上传文件
- 每个client串行上传, file被拆分为packet传输, 采用GBN的流水线可靠传输机制
- 采用TCP-Tahoe拥塞控制
# 2.2 TODO
- client的下载文件功能
- 记录平均上传下载速度，以及丢包率
- GBN -> TCP ?

# 附: 命令行
python server.py
python client.py
