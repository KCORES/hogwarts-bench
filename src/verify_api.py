"""API verification script for testing .env configurations."""

import argparse
import asyncio
import sys
import os
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.config import Config
from core.llm_client import LLMClient
from core.tokenizer import Tokenizer


@dataclass
class VerifyResult:
    """Result of API verification."""
    success: bool
    response: Optional[str] = None
    elapsed_time: float = 0.0
    output_tokens: int = 0
    tokens_per_second: float = 0.0
    error: Optional[str] = None


async def verify_api(env_path: str, verbose: bool = False) -> VerifyResult:
    """Verify API configuration by sending a simple request.
    
    Args:
        env_path: Path to .env file
        verbose: Whether to print detailed output
        
    Returns:
        VerifyResult with success status and performance metrics
    """
    print(f"🔍 验证 API 配置: {env_path}")
    print("-" * 50)
    
    # Check if file exists
    if not os.path.exists(env_path):
        print(f"❌ 错误: 文件不存在 - {env_path}")
        return VerifyResult(success=False, error="文件不存在")
    
    try:
        # Load configuration
        config = Config.load_from_env(env_path)
        
        # Display config info
        print(f"📡 Base URL: {config['base_url']}")
        print(f"🤖 Model: {config['model_name']}")
        print(f"🔑 API Key: {config['api_key'][:8]}...{config['api_key'][-4:]}" 
              if len(config['api_key']) > 12 else "***")
        print("-" * 50)
        
        # Validate configuration
        Config.validate_config(config)
        print("✅ 配置验证通过")
        
        # Create LLM client and tokenizer
        llm_config = Config.get_llm_config(config)
        client = LLMClient(llm_config)
        tokenizer = Tokenizer()
        
        # Send test request with timing
        print("📤 发送测试请求...")
        start_time = time.perf_counter()
        
        response = await client.generate(
            prompt="Hello, what is your model name, version and knowledge cutoff date?",
            max_retries=1
        )
        
        elapsed_time = time.perf_counter() - start_time
        
        if response:
            # Calculate token metrics
            output_tokens = tokenizer.count_tokens(response)
            tokens_per_second = output_tokens / elapsed_time if elapsed_time > 0 else 0
            
            print("✅ API 请求成功!")
            print("-" * 50)
            print(f"⏱️  响应时间: {elapsed_time:.2f}s")
            print(f"📊 输出 Tokens: {output_tokens}")
            print(f"🚀 输出速度: {tokens_per_second:.2f} tokens/s")
            
            if verbose:
                print("-" * 50)
                print(f"📥 响应内容:\n{response}")
            
            return VerifyResult(
                success=True,
                response=response,
                elapsed_time=elapsed_time,
                output_tokens=output_tokens,
                tokens_per_second=tokens_per_second
            )
        else:
            print("❌ API 请求失败: 未收到响应")
            return VerifyResult(success=False, error="未收到响应")
            
    except ValueError as e:
        print(f"❌ 配置错误: {e}")
        return VerifyResult(success=False, error=str(e))
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return VerifyResult(success=False, error=str(e))


def main():
    parser = argparse.ArgumentParser(
        description="验证 .env 文件中的 API 配置是否能正常工作"
    )
    parser.add_argument(
        "env_file",
        nargs="?",
        default=".env",
        help="要验证的 .env 文件路径 (默认: .env)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细输出，包括 API 响应内容"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="验证当前目录下所有 .env* 文件"
    )
    
    args = parser.parse_args()
    
    if args.all:
        # Find all .env files
        env_files = sorted(Path(".").glob(".env*"))
        env_files = [f for f in env_files if f.name != ".env.example"]
        
        if not env_files:
            print("未找到 .env 文件")
            sys.exit(1)
        
        print(f"找到 {len(env_files)} 个配置文件\n")
        
        results = {}
        for env_file in env_files:
            result = asyncio.run(verify_api(str(env_file), args.verbose))
            results[str(env_file)] = result
            print()
        
        # Summary
        print("=" * 50)
        print("📊 验证结果汇总:")
        print("=" * 50)
        for env_file, result in results.items():
            if result.success:
                print(f"  {env_file}: ✅ 通过 | {result.tokens_per_second:.2f} tokens/s")
            else:
                print(f"  {env_file}: ❌ 失败")
        
        failed = sum(1 for r in results.values() if not r.success)
        sys.exit(1 if failed > 0 else 0)
    else:
        result = asyncio.run(verify_api(args.env_file, args.verbose))
        sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    main()
