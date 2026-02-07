#!/usr/bin/env python3
"""
机场订阅链接转换为纯文本格式脚本

将机场订阅链接（通常是 base64 编码）转换为每行一个节点链接的纯文本格式。
"""

import requests
import base64
import sys
import os
import re
import argparse
from urllib.parse import unquote


def decode_subscription_content(content):
    """
    解码订阅内容，支持 base64 和 URL-safe base64
    
    Args:
        content: 原始订阅内容字符串
        
    Returns:
        list: 解码后的行列表
    """
    lines = []
    
    # 方法1: 尝试 base64 解码
    try:
        # 处理可能的 URL-safe base64
        content_to_decode = content.replace('-', '+').replace('_', '/')
        # 补齐 base64 padding
        missing_padding = len(content_to_decode) % 4
        if missing_padding:
            content_to_decode += '=' * (4 - missing_padding)
        
        decoded_bytes = base64.b64decode(content_to_decode)
        decoded_content = decoded_bytes.decode('utf-8', errors='ignore')
        lines = decoded_content.splitlines()
        print("成功使用 base64 解码")
        return lines, decoded_content
    except Exception as e:
        print(f"Base64 解码失败，尝试其他方法")
    
    # 方法2: 如果不是 base64 或解码失败，直接使用原始内容
    if not lines or len(lines) == 0:
        lines = content.splitlines()
        print("使用原始内容")
        return lines, None
    
    return lines, None


def extract_node_links(lines, decoded_content=None):
    """
    从解码后的内容中提取节点链接
    
    Args:
        lines: 内容行列表
        decoded_content: 解码后的完整内容（可选）
        
    Returns:
        list: 节点链接列表
    """
    node_links = []
    # 支持的代理协议
    protocols = ['ss://', 'ssr://', 'vmess://', 'vless://', 'trojan://', 
                 'hysteria://', 'hy2://', 'tuic://', 'wireguard://']
    
    for line in lines:
        line = line.strip()
        # 跳过空行和注释
        if not line or line.startswith('#'):
            continue
        
        # 检查是否是代理协议链接
        is_proxy_link = any(line.startswith(proto) for proto in protocols)
        
        if is_proxy_link:
            node_links.append(line)
        elif decoded_content and not is_proxy_link:
            # 如果解码后的内容不是链接格式，可能是 JSON 或其他格式
            # 尝试从 JSON 中提取链接
            if line.startswith('{') or line.startswith('['):
                # 可能是 JSON 格式的节点配置，跳过（需要更复杂的解析）
                continue
    
    # 如果还是没有找到链接，尝试从原始内容中查找
    if not node_links:
        print("警告: 未找到标准格式的节点链接")
        print("尝试从内容中提取所有可能的链接...")
        # 使用正则表达式查找所有可能的链接
        all_text = '\n'.join(lines)
        # 查找所有以协议开头的行
        pattern = r'^(' + '|'.join(re.escape(p) for p in protocols) + r').*$'
        matches = re.findall(pattern, all_text, re.MULTILINE)
        if matches:
            node_links = matches
            print(f"通过正则表达式找到 {len(node_links)} 个可能的链接")
        else:
            # 最后尝试：输出所有非空非注释行
            print("输出所有非空行作为备选方案")
            node_links = [line for line in lines if line.strip() and not line.strip().startswith('#')]
    
    return node_links


def process_subscription_content(content, output_filename='sub_xfltd'):
    """
    处理订阅内容（base64 编码或原始内容）并转换为纯文本格式
    
    Args:
        content: 订阅内容（base64 编码的字符串或原始内容）
        output_filename: 输出文件名（不含扩展名）
        
    Returns:
        str: 输出文件路径
    """
    print(f"正在处理订阅内容，内容长度: {len(content)} 字符")
    
    try:
        # 解码订阅内容
        lines, decoded_content = decode_subscription_content(content)
        
        # 提取节点链接
        node_links = extract_node_links(lines, decoded_content)
        
        if not node_links:
            print("错误: 无法从订阅内容中提取任何节点信息")
            sys.exit(1)
        
        # 去重并保持顺序
        seen = set()
        unique_links = []
        for link in node_links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)
        
        # 写入文件
        output_file = f"{output_filename}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            for link in unique_links:
                f.write(link + '\n')
        
        print(f"成功转换 {len(unique_links)} 个节点（去重后）")
        print(f"输出文件: {output_file}")
        print(f"文件大小: {os.path.getsize(output_file)} 字节")
        
        return output_file
        
    except Exception as e:
        print(f"错误: {type(e).__name__}")
        # 不打印详细错误信息，避免泄露敏感内容
        sys.exit(1)


def convert_subscription(subscription_url=None, subscription_content=None, output_filename='sub_xfltd'):
    """
    转换订阅链接或内容为纯文本格式
    
    Args:
        subscription_url: 机场订阅链接（可选）
        subscription_content: 订阅内容（base64 编码，可选）
        output_filename: 输出文件名（不含扩展名）
        
    Returns:
        str: 输出文件路径
    """
    # 优先使用直接提供的内容
    if subscription_content:
        return process_subscription_content(subscription_content.strip(), output_filename)
    
    # 如果没有提供内容，则从 URL 获取
    if not subscription_url:
        print("错误: 未提供订阅链接或订阅内容")
        print("请通过以下方式之一提供:")
        print("  - 命令行参数 --url 或环境变量 SUBSCRIPTION_URL（订阅链接）")
        print("  - 命令行参数 --content 或环境变量 SUBSCRIPTION_CONTENT（base64 内容）")
        sys.exit(1)

    # 不打印完整 URL，避免泄露敏感信息
    print("正在从订阅链接获取内容...")
    
    try:
        # 获取订阅内容
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(subscription_url, headers=headers, timeout=60)
        response.raise_for_status()
        
        # 订阅内容通常是 base64 编码的
        content = response.text.strip()
        
        return process_subscription_content(content, output_filename)
        
    except requests.exceptions.RequestException as e:
        print(f"网络请求错误: {type(e).__name__}")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {type(e).__name__}")
        # 不打印详细错误信息，避免泄露敏感内容
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='将机场订阅链接转换为纯文本格式',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用订阅链接
  python convert_subscription.py --url "https://example.com/sub" --output "sub_xfltd"
  
  # 使用 base64 内容
  python convert_subscription.py --content "dHJvamFuOi8v..." --output "sub_xfltd"
  
环境变量:
  SUBSCRIPTION_URL: 订阅链接
  SUBSCRIPTION_CONTENT: 订阅内容（base64 编码）
  OUTPUT_FILENAME: 输出文件名（不含扩展名）
        """
    )
    
    parser.add_argument(
        '--url', '-u',
        type=str,
        help='机场订阅链接'
    )
    
    parser.add_argument(
        '--content', '-c',
        type=str,
        help='订阅链接返回的 base64 内容（与 --url 二选一）'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='sub_xfltd',
        help='输出文件名（不含扩展名，默认: sub_xfltd）'
    )
    
    args = parser.parse_args()
    
    # 优先使用命令行参数，其次使用环境变量
    subscription_url = args.url or os.environ.get('SUBSCRIPTION_URL')
    subscription_content = args.content or os.environ.get('SUBSCRIPTION_CONTENT')
    output_filename = args.output or os.environ.get('OUTPUT_FILENAME', 'sub_xfltd')
    
    convert_subscription(
        subscription_url=subscription_url,
        subscription_content=subscription_content,
        output_filename=output_filename
    )


if __name__ == '__main__':
    main()
