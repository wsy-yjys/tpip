# tpip


`tpip` 是一个帮助你快速切换 `pip` 镜像源，基于cnpip构建，提升 Python 包的下载速度的命令行工具。  
它可以测试各镜像源的实际下载速度，并**自动选择下载速度最快的镜像源**。

## 致谢

本项目基于 [cnpip](https://github.com/Fenghuapiao/cnpip) 项目开发，感谢 cnpip 项目的开发者提供的优秀工具和灵感。tpip 在 cnpip 的基础上进行了功能扩展和优化，为中国用户提供更好的 pip 镜像源管理体验。

## 快速使用

运行以下命令，快速切换为最快的镜像源：

```bash
pip install tpip
tpip set
```

## 功能

- **列出并测试镜像源速度**，按连接速度排序
- **快速切换 pip 镜像源**，支持*手动选择*或*自动选择*最快镜像
- **美化表格输出**，使用 `prettytable` 库显示更清晰的结果
- **显示包下载链接**，方便查看各镜像源中包的实际下载地址
- **支持异步测试**，提高测试效率

## 安装

```bash
pip install tpip
```

### 开发者安装（可编辑模式）

```bash
pip install -e .
```

## 支持的镜像源

- [清华大学 TUNA](https://pypi.tuna.tsinghua.edu.cn/simple)
- [中国科学技术大学 USTC](https://pypi.mirrors.ustc.edu.cn/simple)
- [阿里云 Aliyun](https://mirrors.aliyun.com/pypi/simple)
- [腾讯 Tencent](https://mirrors.cloud.tencent.com/pypi/simple)
- [华为 Huawei](https://repo.huaweicloud.com/repository/pypi/simple)
- [西湖大学 Westlake University](https://mirrors.westlake.edu.cn)
- [默认源 PyPi](https://pypi.org/simple)

## 使用方法

### 1. 列出所有可用的镜像源

```bash
tpip list
```

示例输出：

```
+----------+-----------+----------------------------------------+
| 镜像名称 | 耗时(ms)  | 地址                                   |
+----------+-----------+----------------------------------------+
| ustc     | 135.71    | https://pypi.mirrors.ustc.edu.cn/simple|
| aliyun   | 300.77    | https://mirrors.aliyun.com/pypi/simple |
| tuna     | 499.51    | https://pypi.tuna.tsinghua.edu.cn/simple|
| default  | 1252.75   | https://pypi.org/simple                |
| tencent  | 1253.07   | https://mirrors.cloud.tencent.com/pypi/simple|
+----------+-----------+----------------------------------------+
```

### 2. 测试特定包的下载速度

```bash
tpip list --package numpy
```

这将测试各镜像源下载 numpy 包的速度，并显示包的下载链接。

示例输出：

```
正在对延迟最低的3个镜像源进行下载速度测试，这可能需要几分钟时间...

ustc 的包链接: @https://pypi.mirrors.ustc.edu.cn/packages/65/6e/09db2a15a75e9cca1c8a5b89b5d5a6d945b3bc551898b4b8d2c4a08e09b9/numpy-1.26.4-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
tuna 的包链接: @https://pypi.tuna.tsinghua.edu.cn/packages/65/6e/09db2a15a75e9cca1c8a5b89b5d5a6d945b3bc551898b4b8d2c4a08e09b9/numpy-1.26.4-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
aliyun 的包链接: @https://mirrors.aliyun.com/pypi/packages/65/6e/09db2a15a75e9cca1c8a5b89b5d5a6d945b3bc551898b4b8d2c4a08e09b9/numpy-1.26.4-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl

开始进行下载速度测试...
```

### 3. 自动选择最快的镜像源

```bash
tpip set
```

示例输出：

```
未指定镜像源，自动选择最快的镜像源: ustc
成功设置 pip 镜像源为 'https://pypi.mirrors.ustc.edu.cn/simple'
```

### 4. 选择指定的镜像源

```bash
tpip set <镜像名称>
```

示例：

```bash
tpip set tuna
```

输出：

```
成功设置 pip 镜像源为 'https://pypi.tuna.tsinghua.edu.cn/simple'
```

### 5. 取消自定义镜像源设置

```bash
tpip unset
```

输出：

```
成功取消 pip 镜像源设置，已恢复为默认源。
```

### 6. 高级选项

#### 顺序测试模式

默认情况下，tpip 使用并行测试模式。如果需要更详细的输出，可以使用顺序测试模式：

```bash
tpip list --sequential
```

#### 指定测试时间

可以指定下载测试的时间限制：

```bash
tpip list --test-time 10
```

#### 指定测试的镜像源数量

可以指定要测试下载速度的镜像源数量：

```bash
tpip list --top-count 5
```

## 配置文件

`tpip` 会修改或创建 `pip` 的配置文件来设置镜像源：

- **Linux/macOS**: `~/.pip/pip.conf`
- **Windows**: `%APPDATA%\pip\pip.ini`

在设置镜像源时，`tpip` 只会修改或添加 `index-url` 配置，不会覆盖其他配置项。

## 常见问题

### 1. 为什么我无法连接到某些镜像源？

某些镜像源（如豆瓣）可能由于网络问题或镜像源本身的原因无法连接。在这种情况下，`tpip` 会显示"无法连接"，并将其排在速度测试结果的最后。

### 2. 如何恢复为默认的 `pip` 镜像源？

使用 `unset` 命令恢复为默认的 `pip` 镜像源：

```bash
tpip unset
```

### 3. `tpip` 会覆盖我的 `pip.conf` 文件吗？

不会。`tpip` 只会修改或添加 `index-url` 配置项，其他配置项会被保留。

## 许可证

本项目使用 [MIT 许可证](LICENSE)。

---

# tpip (English)

`tpip` is a command-line tool designed specifically for users in **mainland China** to help quickly switch `pip`
mirrors and improve Python package download speeds.       
It tests the connection speed of various mirrors and **automatically selects the fastest one**.

> **Attention: This Python package is only available in Chinese mainland.**

## Quick Start

Run the following commands to quickly switch to the fastest mirror:

```bash
pip install tpip
tpip set
```

## Features

- **List and test mirror speeds**, sorted by connection time
- **Quickly switch pip mirrors**, supporting *manual selection* or *automatic selection* of the fastest mirror
- **Beautiful table output** using the `prettytable` library
- **Display package download links** for each mirror
- **Support for asynchronous testing** to improve efficiency
- Designed specifically for users in mainland China

## Installation

```bash
pip install tpip
```

### Developer Installation (Editable Mode)

```bash
pip install -e .
```



