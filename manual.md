# FDFTP使用手册

## 1 项目结构

- 请先创建一个任意名称的文件夹，用来存放代码和文件，以下假设你已经创建好了名为`code`的文件夹

- 如果你同时部署客户端和服务器，需要保证如下项目结构

  ```plain
  |__code
     |__client
        |__temp
     |__server
        |__temp
     client.py
     config.py
     FDFTPsocket.py
     rdt.py
     server.py
  ```

  - 创建`client`文件夹，并在其中创建`temp`文件夹
  - 创建`server`文件夹，并在其中创建`temp`文件夹
  - 把写好的5份python代码放进`code`文件夹
  - 把需要上传的文件放进`client`文件夹
  - 把需要下载的文件放进`server`文件夹

- 如果你只部署客户端，需要保证如下项目结构

  ``` plain
  |__code
     |__client
        |__temp
     client.py
     config.py
     FDFTPsocket.py
     rdt.py
  ```

- 如果你只部署服务器，需要保证如下项目结构

  ``` plain
  |__code
     |__server
        |__temp
     config.py
     FDFTPsocket.py
     rdt.py
     server.py
  ```

## 2 配置文件

- 必做
  - `CLIENT_IP`：客户端的IP地址，根据运行环境修改
  - `SERVER_IP`：服务器的IP地址，根据运行环境修改
- 选做
  - `SERVER_PORT`：服务器欢迎套接字端口号，随意修改，只要不与你电脑在使用的端口号冲突即可
  - `DEBUG`：调试输出，你可以将其设为True以查看程序运行的细节
  - `PERFORMANCE`：传输详情输出，你可以将其设为True以查看每次传送了多大的文件、用时、速度、丢包率等信息
  - `CONG_TIMEOUT`：发送端超时重传的时间，你可以根据网络的状况设置，如果网络非常拥塞建议设大点，如果网络环境好可以设小点，但请注意设置太大或太小会严重影响性能，你可以直接使用1s的默认设置
- 不建议修改（在文件中有设置这些值的依据与建议，不当的修改会导致错误！）
  - `MSS`：每个包的最大负载长度，这是根据UDP负载与我自定义的包结构体设置的
  - `BUFSIZE`：socket的recvfrom的最大接收缓存，这是根据包长度设置的
  - `CONG_DEFALUT_SSTHRESH`：初始的慢启动阈值，这是根据Google的研究的推荐值设置的
  - `RWND`：接收端窗口大小，这是根据os的write函数的最大负载设置的

## 3 运行程序

### 3.1 启动服务器

- 在客户端运行之前，你必须先运行服务器，服务器启动的命令是`python server.py`

### 3.2 启动客户端

- 在服务器启动之后，你可以开启任意数量个客户端并行上传文件，每个客户端启动的命令是`python client.py`
- 每个客户端都是持久连接，每输入一个命令，就可以下载或上传一个文件，上传或下载完毕后可以输入下一个命令，以此类推

### 3.3 操作客户端

- 连接

  - 如果运行完客户端启动命令`python client.py`后，发现输出下列的提示字，说明与服务器成功建立连接

    ``` bash
    >>> input `fsnd filename` to upload, or `frcv filename` to download, or nothing to exit:)
      > upload file should be under folder `client`, download file should be under folder `server`
    ```

  - 如果你发现什么也没输出，说明3次握手失败（小概率事件），你需要直接关闭该客户端终端并重新开一个连接

- 上传

  - 如果你想从客户端上传一个文件给服务器，则命令格式是`fsnd filename`。`fsnd`是`file send`的缩写，表示你想从客户端发送文件，`filename`是该文件在`client`文件夹下的相对路径。请注意，你只能上传`client`文件夹中的文件！

  - 比如，你想上传位于文件夹`client`下的文件`filename2.xxx`，请输入如下命令

    ``` bash
    fsnd filename2.xxx
    ```

  - 如果该文件不存在，命令行会输出提示，接下来你可以输入下一个命令

  - 等待一段文件上传时间，如果上传成功，命令行会输出提示，你会发现文件在`server\filename2.xxx`，接下来你可以输入下一个命令

- 下载

  - 如果你想从服务器下载一个文件到客户端，则命令格式是`frcv filename`。`frcv`是`file receive`的缩写，表示你想从服务器下载文件，`filename`是该文件在`server`文件夹下的相对路径。请注意，你只能下载`server`文件夹中的文件！

  - 比如，你想下载位于文件夹`server`下的文件`filename3.xxx`，请输入如下命令

    ``` bash
    frcv filename3.xxx
    ```

  - 如果该文件不存在，命令行会输出提示，接下来你可以输入下一个命令

  - 等待一段文件下载时间，如果下载成功，命令行会输出提示，你会发现文件在`client\filename3.xxx`，接下来你可以输入下一个命令

- 关闭

  - 如果你想关闭客户端，最暴力的方法是直接关闭终端，但并不推荐这样做，因为这样并没有断开和服务器的连接，而且文件夹`client/temp`和`server/temp`下各自的产生的缓存文件不会被自动清掉，你就得手动清除（当然不管这些缓存文件也行）
  - 推荐的方法是，在提示你输入下一个命令时，直接输入回车，就会被解析为请求中断，客户端会向服务器握手中断，然后分别删除文件夹`client/temp`和`server/temp`下相应的缓存文件

### 3.4 关闭服务器

 - 最好的做法是，确保客户端都退出后，直接关闭服务器终端即可
 - 如果有些客户端还没退出就关闭服务端，会导致缓存文件无法自动清除，你得手动清除（当然不管这些缓存文件也行）