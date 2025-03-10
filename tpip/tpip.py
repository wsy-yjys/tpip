import subprocess
import sys
import argparse
import time
import asyncio
from urllib.parse import urlparse
import os
import tempfile
import re
import random
import platform
import requests
import json
import shutil
import configparser
from pathlib import Path
import aiohttp
from prettytable import PrettyTable

from .mirrors import MIRRORS
# from mirrors import MIRRORS

MIN_PYTHON_VERSION = (3, 6)
if sys.version_info < MIN_PYTHON_VERSION:
    sys.stderr.write(f"错误: tpip需要 Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]} 或更高版本。\n")
    sys.stderr.write("您也可直接使用以下命令快速安装包:\n")
    sys.stderr.write(">\tpip install [package_name] -i https://pypi.tuna.tsinghua.edu.cn/simple \n")
    sys.exit(1)

# 默认测试包
DEFAULT_TEST_PACKAGE = "torch"  # 默认使用torch包，几乎所有镜像源都有

# 常用的大型包列表，用于测试下载速度
POPULAR_PACKAGES = [
    "torch", "pandas", "matplotlib", "scikit-learn", "tensorflow",
    "numpy", "django", "flask", "requests", "pillow"
]

def extract_version(url):
    """提取URL中的版本号并转换为可比较的格式"""
    # 提取版本号
    version_match = re.search(r'[-_](\d+\.\d+\.\d+[^-_]*)', url)
    if version_match:
        version_str = version_match.group(1)
        # 将版本号转换为元组以便比较
        try:
            # 处理像 '2.0.0' 这样的标准版本号
            parts = version_str.split('.')
            # 确保至少有三个部分
            while len(parts) < 3:
                parts.append('0')
            # 处理像 '2.0.0rc1' 这样的后缀
            last_part = parts[-1]
            numeric_part = re.match(r'^\d+', last_part)
            suffix_part = re.search(r'[a-zA-Z].*$', last_part)
            
            if numeric_part and suffix_part:
                parts[-1] = numeric_part.group(0)
                parts.append(suffix_part.group(0))
            
            # 转换为整数进行比较
            version_tuple = []
            for part in parts:
                try:
                    version_tuple.append(int(part))
                except ValueError:
                    # 非数字部分（如 'rc1'）放在最后，按字母顺序排序
                    # 预发布版本（如rc, alpha, beta）应该排在正式版本之前
                    if part.startswith(('a', 'alpha')):
                        version_tuple.append(-3)  # alpha 最低
                    elif part.startswith(('b', 'beta')):
                        version_tuple.append(-2)  # beta 次之
                    elif part.startswith(('rc', 'c')):
                        version_tuple.append(-1)  # rc 接近正式版
                    else:
                        version_tuple.append(0)  # 正式版本
                    version_tuple.append(part)
            
            return tuple(version_tuple)
        except Exception:
            # 如果解析失败，返回一个很小的值
            return (-999,)
    return (-999,)  # 没有找到版本号

def sort_package_links(links):
    """对包链接按版本号排序，最新版本在前"""
    if links and len(links) > 1:
        links.sort(key=extract_version, reverse=True)
        print(f"找到 {len(links)} 个包版本，选择最新版本")
    return links

def get_system_info():
    """获取系统信息，用于构建User-Agent"""
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    system = platform.system()
    machine = platform.machine()
    return f"Python/{python_version} ({system}; {machine})"

def get_pip_like_user_agent():
    """构建类似pip的User-Agent"""
    system_info = get_system_info()
    return f"pip/{pip_version} {system_info}"

# 获取pip版本
def get_pip_version():
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        # 输出格式类似: "pip 21.3.1 from /path/to/pip (python 3.9)"
        version_str = result.stdout.split()[1]
        return version_str
    except Exception:
        return "21.0.1"  # 默认版本

# 获取pip版本
pip_version = get_pip_version()

async def measure_mirror_speed_async(session, name, url):
    """异步测速函数"""
    try:
        start_time = time.time()
        async with session.head(url, timeout=10) as response:
            if 200 <= response.status < 400:
                end_time = time.time()
                return name, round((end_time - start_time) * 1000, 2), url
            else:
                print(f"异步测速失败: {name} ({url}) - HTTP {response.status}")
                return name, None, url
    except Exception as e:
        print(f"异步测速失败: {name} ({url}) - {e}")
        return name, None, url

async def test_download_speed_async(session, name, url, package_url=None):
    """测试镜像源的实际下载速度（异步版本）"""
    try:
        # 使用用户指定的包或默认测试包
        test_package = DEFAULT_TEST_PACKAGE
        if hasattr(args, 'package') and args.package:
            test_package = args.package
        
        # 获取测试时间
        test_time = 5  # 默认值
        if hasattr(args, 'test_time'):
            test_time = args.test_time
            
        # 是否使用顺序测试模式
        sequential_mode = False
        if hasattr(args, 'sequential'):
            sequential_mode = args.sequential
            
            # 构建类似pip的请求头
            headers = {
                "User-Agent": get_pip_like_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Cache-Control": "max-age=0",
                "Upgrade-Insecure-Requests": "1"
            }
            
        if sequential_mode:
            print(f"测试 {name} 下载 {test_package} 包的速度（限时{test_time}秒）...")
            
        # 如果已经提供了包链接，直接使用
        if package_url:
            # 开始下载测试
            start_time = time.time()
            total_size = 0
            
            try:
                async with session.get(package_url, headers=headers, timeout=30) as response:
                    if response.status != 200:
                        if sequential_mode:  # 只在顺序模式下输出详细信息
                            print(f"下载测试失败: {name} - 无法下载包文件，状态码: {response.status}")
                        return name, None, url
                    
                    # 读取数据块并计算大小
                    while True:
                        if time.time() - start_time >= test_time:
                            break
                    
                        try:
                            chunk = await response.content.read(8192)
                            if not chunk:
                                break
                            total_size += len(chunk)
                        except Exception as e:
                            if sequential_mode:  # 只在顺序模式下输出详细信息
                                print(f"下载过程中出错: {e}")
                            break
            except asyncio.CancelledError:
                if sequential_mode:  # 只在顺序模式下输出详细信息
                    print(f"下载测试被取消: {name}")
                raise
            except Exception as e:
                if sequential_mode:  # 只在顺序模式下输出详细信息
                    print(f"下载测试失败: {name} - {e}")
                return name, None, url
            
            # 计算下载时间和速度
            download_time = time.time() - start_time
            if download_time > test_time:
                download_time = test_time  # 限制最大时间为测试时间
            
            if sequential_mode:  # 只在顺序模式下输出详细信息
                print(f"下载完成: {round(download_time, 2)}秒内下载了 {round(total_size/1024/1024, 2)} MB")
            
            # 计算下载速度 (MB/s)
            if download_time > 0 and total_size > 0:
                speed = (total_size / 1024 / 1024) / download_time
                # 确保速度不为0，最小显示0.01
                if speed < 0.01:
                    speed = 0.01
                
                if sequential_mode:  # 只在顺序模式下输出详细信息
                    print(f"{name} 下载速度: {round(speed, 2)} MB/s ({test_time}秒内下载: {round(total_size/1024/1024, 2)} MB)")
                return name, round(speed, 2), url
            else:
                if sequential_mode:  # 只在顺序模式下输出详细信息
                    print(f"下载测试失败: {name} - 下载时间过短或文件大小为0")
                return name, None, url
        else:
            # 如果没有提供包链接，尝试使用pip命令下载
            try:
                return await _download_with_pip_async(session, name, url, test_package)
            except Exception as e:
                if sequential_mode:
                    print(f"pip下载测试失败: {name} - {e}")
                return name, None, url
            
    except KeyboardInterrupt:
        print(f"下载测试被用户中断: {name}")
        raise
    except Exception as e:
        print(f"下载测试失败: {name} ({url}) - {e}")
        return name, None, url

async def list_mirrors_async():
    """改进的异步测速主函数"""
    try:
        start_time = time.monotonic()
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(limit=5)  # 限制并发连接数

        async with aiohttp.ClientSession(timeout=timeout,
                                         connector=connector) as session:
            print("正在异步测试镜像源延迟，请稍候...")
            tasks = [measure_mirror_speed_async(session, name, url)
                     for name, url in MIRRORS.items()]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 过滤掉异常结果
            valid_results = [r for r in results if isinstance(r, tuple) and r[1] is not None]
            valid_results.sort(key=lambda x: x[1])
            
            print_mirror_results(valid_results, "耗时 (ms)")
            print(f"异步延迟测试总耗时: {round((time.monotonic() - start_time) * 1000, 2)} ms")
            
            # 检查是否需要跳过下载测试
            if hasattr(args, 'no_download_test') and args.no_download_test:
                print("\n已跳过下载速度测试")
                return valid_results[0][0] if valid_results else None
            
            # 选择延迟最低的几个镜像源进行下载速度测试
            top_count = 3  # 默认值
            if hasattr(args, 'top_count'):
                top_count = args.top_count
            top_count = min(top_count, len(valid_results))
            top_mirrors = valid_results[:top_count]
                
            print(f"\n正在对延迟最低的{top_count}个镜像源进行下载速度测试...")
            
            # 获取并显示每个镜像源的包链接
            package_links = {}  # 存储每个镜像源的包链接
            for name, _, url in top_mirrors:
                try:
                    package_name = DEFAULT_TEST_PACKAGE
                    if hasattr(args, 'package') and args.package:
                        package_name = args.package
                    package_url = f"{url}/{package_name}/"
                    
                    # 构建类似pip的请求头
                    headers = {
                        "User-Agent": get_pip_like_user_agent(),
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.5",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Connection": "keep-alive",
                        "Cache-Control": "max-age=0",
                        "Upgrade-Insecure-Requests": "1"
                    }
                    
                    # 获取包信息页面
                    async with session.get(package_url, headers=headers, timeout=10) as response:
                        if response.status != 200:
                            print(f"{name} 的包链接获取失败: 无法访问包信息页面")
                            continue
                        html = await response.text()
                    
                    # 查找包文件链接
                    py_version = f"cp{sys.version_info.major}{sys.version_info.minor}"
                    platform_tag = "manylinux1_x86_64" if platform.system() == "Linux" else "win_amd64" if platform.system() == "Windows" else "macosx_10_15_x86_64"
                    
                    # 首先尝试找到适合当前系统的wheel包
                    wheel_pattern = fr'href=[\'"]?([^\'" >]+{py_version}[^\'" >]*{platform_tag}[^\'" >]*\.whl)'
                    whl_links = re.findall(wheel_pattern, html)
                    
                    # 如果没找到特定版本，尝试任何wheel包
                    if not whl_links:
                        whl_links = re.findall(r'href=[\'"]?([^\'" >]+\.whl)', html)
                    
                    # 对找到的包进行版本排序
                    whl_links = sort_package_links(whl_links)
                    
                    if not whl_links:
                        # 如果没有wheel包，尝试找任何包格式
                        all_links = re.findall(r'href=[\'"]?([^\'" >]+\.(tar\.gz|zip|whl))', html)
                        if all_links and len(all_links) > 0:
                            # 检查all_links的结构
                            if isinstance(all_links[0], tuple) and len(all_links[0]) > 0:
                                whl_links = [all_links[0][0]]
                            else:
                                whl_links = [all_links[0]]
                    
                    if whl_links:
                        package_file = whl_links[0]
                        # 确保链接是完整的URL
                        if package_file.startswith('http'):
                            package_url = package_file
                        else:
                            # 处理相对路径
                            if package_file.startswith('/'):
                                base_url = url.split('//', 1)[0] + '//' + url.split('//', 1)[1].split('/', 1)[0]
                                package_url = base_url + package_file
                            else:
                                package_url = f"{url}/{package_name}/{package_file}"
                        print(f"{name} 的包链接: @{package_url}")
                        package_links[name] = package_url
                    else:
                        print(f"{name} 的包链接获取失败: 未找到适合的包文件")
                except Exception as e:
                    print(f"{name} 的包链接获取失败: {str(e)}")
            
            print("\n开始进行下载速度测试...")
            
            # 下载速度测试
            if hasattr(args, 'sequential') and args.sequential:
                print("使用顺序测试模式...")
                download_results = []
                for name, _, url in top_mirrors:
                    if name in package_links:
                        # 使用已获取的包链接
                        result = await test_download_speed_async(session, name, url, package_links.get(name))
                        download_results.append(result)
            else:
                print("使用并行测试模式...")
                download_tasks = []
                for name, _, url in top_mirrors:
                    if name in package_links:
                        # 使用已获取的包链接
                        task = asyncio.create_task(test_download_speed_async(session, name, url, package_links.get(name)))
                        download_tasks.append(task)
                
                download_results = await asyncio.gather(*download_tasks, return_exceptions=True)
                download_results = [r for r in download_results if isinstance(r, tuple)]
            
            # 过滤掉失败的结果
            valid_download_results = [r for r in download_results if r[1] is not None]
            
            if not valid_download_results:
                print("所有镜像源下载测试失败")
                return valid_results[0][0] if valid_results else None
            
            # 按下载速度排序
            valid_download_results.sort(key=lambda x: x[1] if x[1] is not None else 0, reverse=True)
            
            # 合并延迟和下载速度结果
            final_results = []
            for name, speed, url in valid_download_results:
                # 查找对应的延迟结果
                latency = next((r[1] for r in valid_results if r[0] == name), None)
                final_results.append((name, latency, speed, url))
            
            # 打印最终结果
            print_final_results(final_results)
            
            # 返回下载速度最快的镜像源
            return valid_download_results[0][0]
    except Exception as e:
        print(f"测试过程中出错: {e}")
        return None

def measure_mirror_speed_sync(name, url):
    """同步测速函数"""
    try:
        start_time = time.monotonic()
        response = requests.head(url, timeout=10)
        response.raise_for_status()
        return name, round((time.monotonic() - start_time) * 1000, 2), url
    except requests.RequestException as e:
        print(f"同步测速失败: {name} ({url}) - {e}")
        return name, None, url

def test_download_speed_sync(name, url, package_url=None):
    """测试镜像源的实际下载速度（同步版本）"""
    try:
        # 使用用户指定的包或默认测试包
        test_package = DEFAULT_TEST_PACKAGE
        if hasattr(args, 'package') and args.package:
            test_package = args.package
        
        # 获取测试时间
        test_time = 5  # 默认值
        if hasattr(args, 'test_time'):
            test_time = args.test_time
        
        print(f"测试 {name} 下载 {test_package} 包的速度（限时{test_time}秒）...")
        
        # 构建类似pip的请求头
        headers = {
            "User-Agent": get_pip_like_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "Upgrade-Insecure-Requests": "1"
        }
        
        # 如果已经提供了包链接，直接使用
        if package_url:
            # 开始下载测试
            start_time = time.time()
            total_size = 0
            
            try:
                with requests.get(package_url, headers=headers, timeout=30, stream=True) as response:
                    if response.status_code != 200:
                        print(f"下载测试失败: {name} - 无法下载包文件，状态码: {response.status_code}")
                        return name, None, url
                    
                    # 读取数据块并计算大小
                    for chunk in response.iter_content(chunk_size=8192):
                        if time.time() - start_time >= test_time:
                            break
                        if chunk:
                            total_size += len(chunk)
            except Exception as e:
                print(f"下载测试失败: {name} - {e}")
                return name, None, url
            
            # 计算下载时间和速度
            download_time = time.time() - start_time
            if download_time > test_time:
                download_time = test_time  # 限制最大时间为测试时间
            
            print(f"下载完成: {round(download_time, 2)}秒内下载了 {round(total_size/1024/1024, 2)} MB")
            
            # 计算下载速度 (MB/s)
            if download_time > 0 and total_size > 0:
                speed = (total_size / 1024 / 1024) / download_time
                # 确保速度不为0，最小显示0.01
                if speed < 0.01:
                    speed = 0.01
                
                print(f"{name} 下载速度: {round(speed, 2)} MB/s ({test_time}秒内下载: {round(total_size/1024/1024, 2)} MB)")
                return name, round(speed, 2), url
            else:
                print(f"下载测试失败: {name} - 下载时间过短或文件大小为0")
                return name, None, url
        else:
            # 如果没有提供包链接，获取包信息页面
            package_url = f"{url}/{test_package}/"
            
            # 这里应该有获取包链接的代码，但是在当前函数中缺少这部分代码
            # 为了修复缩进错误，我们暂时返回一个错误结果
            print(f"下载测试失败: {name} - 未提供包链接且无法自动获取")
            return name, None, url
    except Exception as e:
        print(f"下载测试失败: {name} - {e}")
        return name, None, url

def list_mirrors_sync():
    """同步测速主函数"""
    # ... existing code ...

def print_mirror_results(results, header_text="测试结果"):
    print(f"\n{header_text}:")
    
    # 使用PrettyTable创建表格
    table = PrettyTable()
    table.field_names = ["镜像名称", "耗时(ms)", "地址"]
    
    # 设置列对齐方式
    table.align["镜像名称"] = "l"
    table.align["耗时(ms)"] = "r"
    table.align["地址"] = "l"
    
    # 添加数据行
    for name, value, url in results:
        if value is not None:
            table.add_row([name, f"{value:.2f}", url])
        else:
            table.add_row([name, "未测试", url])

    # 打印表格
    print(table)

def print_final_results(results):
    # 使用PrettyTable创建表格
    table = PrettyTable()
    table.field_names = ["镜像名称", "耗时(ms)", "下载速度(MB/s)", "地址"]
    
    # 设置列对齐方式
    table.align["镜像名称"] = "l"
    table.align["耗时(ms)"] = "r"
    table.align["下载速度(MB/s)"] = "r"
    table.align["地址"] = "l"
    
    # 添加数据行
    for name, latency, speed, url in results:
        # 处理速度值
        if speed is not None:
            speed_str = f"{speed:.2f}"
        else:
            speed_str = "未测试"
        
        table.add_row([name, f"{latency:.2f}", speed_str, url])
    
    # 打印表格
    print(table)

def is_pip_installed():
    """检查 pip 是否安装"""
    try:
        subprocess.run([sys.executable, '-m', 'pip', '--version'],
                       check=True,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False

def update_pip_config(mirror_url):
    # 提取主机名
    host = urlparse(mirror_url).netloc
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'config', 'set', 'global.index-url', mirror_url], check=True)
        subprocess.run([sys.executable, '-m', 'pip', 'config', 'set', 'global.trusted-host', host], check=True)
        print(f"成功设置 pip 镜像源为 '{mirror_url}'，并添加 trusted-host '{host}'")
    except subprocess.CalledProcessError as e:
        print(f"更新 pip 配置时出错: {e}, 详细报错如下：")
        raise e

def unset_pip_mirror() -> None:
    """取消pip镜像源设置"""
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'config', 'unset', 'global.index-url'], check=True)
        subprocess.run([sys.executable, '-m', 'pip', 'config', 'unset', 'global.trusted-host'], check=True)
        print("成功取消 pip 镜像源设置，已恢复为默认源")
    except subprocess.CalledProcessError as e:
        print(f"取消 pip 镜像源设置时出错: {e}, 详细报错如下：")
        raise e

def main():
    """主函数，解析命令行参数并执行相应操作"""
    global args

    # 解析命令行参数
    parser = argparse.ArgumentParser(description="快速切换pip镜像源的工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # list 子命令
    list_parser = subparsers.add_parser("list", help="列出所有可用的镜像源")
    list_parser.add_argument("--no-download-test", action="store_true", help="跳过下载速度测试")
    list_parser.add_argument("--top-count", type=int, default=3, help="测试下载速度的镜像源数量")
    list_parser.add_argument("--package", type=str, help="指定用于测试的包名")
    list_parser.add_argument("--test-time", type=int, default=5, help="下载测试的时间限制（秒）")
    list_parser.add_argument("--sequential", action="store_true", help="使用顺序测试模式")

    # set 子命令
    set_parser = subparsers.add_parser("set", help="设置pip镜像源")
    set_parser.add_argument("mirror", nargs="?", help="镜像源名称")
    set_parser.add_argument("--no-download-test", action="store_true", help="跳过下载速度测试")
    set_parser.add_argument("--top-count", type=int, default=3, help="测试下载速度的镜像源数量")
    set_parser.add_argument("--package", type=str, help="指定用于测试的包名")
    set_parser.add_argument("--test-time", type=int, default=5, help="下载测试的时间限制（秒）")
    set_parser.add_argument("--sequential", action="store_true", help="使用顺序测试模式")

    # unset 子命令
    subparsers.add_parser("unset", help="取消pip镜像源设置")

    args = parser.parse_args()

    # 如果没有指定子命令，显示帮助信息
    if not args.command:
        parser.print_help()
        sys.exit(0)

    # 执行相应的子命令
    if args.command == "list":
        # 检查Python版本
        if sys.version_info < MIN_PYTHON_VERSION:
            print(f"错误: 需要Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}或更高版本")
            sys.exit(1)

        # 使用异步或同步方式测试镜像源
        if asyncio and 'aiohttp' in sys.modules:
            # 使用异步方式测试
            if sys.platform == 'win32':
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            best_mirror = asyncio.run(list_mirrors_async())
        else:
            # 使用同步方式测试
            best_mirror = list_mirrors_sync()

        # 返回最佳镜像源
        print(f"\n速度最佳的镜像源: {best_mirror}")

    elif args.command == "set":
        # 检查pip是否安装
        if not is_pip_installed():
            print("错误: 未找到pip，请先安装pip")
            sys.exit(1)

        # 如果没有指定镜像源，自动选择最快的镜像源
        if not args.mirror:
            # 使用异步或同步方式测试镜像源
            if asyncio and 'aiohttp' in sys.modules:
                # 使用异步方式测试
                if sys.platform == 'win32':
                    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                best_mirror = asyncio.run(list_mirrors_async())
            else:
                # 使用同步方式测试
                best_mirror = list_mirrors_sync()

            if not best_mirror:
                print("错误: 无法连接到任何镜像源")
                sys.exit(1)

            mirror_name = best_mirror
            print(f"\n自动选择最佳的镜像源: {mirror_name}")
        else:
            mirror_name = args.mirror

        if mirror_name not in MIRRORS:
            print(f"错误: 未找到镜像源 '{mirror_name}'")
            sys.exit(1)

        mirror_url = MIRRORS[mirror_name]
        update_pip_config(mirror_url)
    elif args.command == "unset":
        unset_pip_mirror()
        sys.exit(0)

if __name__ == "__main__":
    main()