#!/usr/bin/env python3
"""CLI for managing LLM providers in MAGoCo-Self-Evo.

Usage:
    python -m apps.backend.scripts.manage_providers list
    python -m apps.backend.scripts.manage_providers add --name "My OpenAI" --kind openai-compatible --base-url https://api.openai.com/v1 --api-key sk-xxx --model gpt-4o
    python -m apps.backend.scripts.manage_providers add --name "Local Ollama" --kind ollama-local --base-url http://localhost:11434 --model llama3.1:8b
    python -m apps.backend.scripts.manage_providers remove --id my-provider
    python -m apps.backend.scripts.manage_providers test --id my-provider
    python -m apps.backend.scripts.manage_providers export --output providers.json --include-secrets
    python -m apps.backend.scripts.manage_providers import --file providers.json --overwrite
    python -m apps.backend.scripts.manage_providers autodetect-ollama
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from magoco_core.llm.registry import ProviderRegistry, get_provider_registry
from magoco_core.llm.providers import ProviderKind, ProviderConfig
from magoco_core.core.config import settings


def get_registry():
    """Get provider registry with proper paths."""
    return ProviderRegistry(
        db_path="./data/providers/registry.db",
        data_dir="./data"
    )


def cmd_list(args):
    """List all providers."""
    reg = get_registry()
    providers = reg.list(enabled_only=False)
    
    if not providers:
        print("No providers configured.")
        return
    
    print(f"{'ID':<25} {'Name':<25} {'Kind':<18} {'Base URL':<35} {'Models':<10} {'Enabled'}")
    print("-" * 130)
    for p in providers:
        models_str = ", ".join(p.models[:2]) + ("..." if len(p.models) > 2 else "")
        print(f"{p.id:<25} {p.name:<25} {p.kind.value:<18} {p.base_url:<35} {models_str:<10} {p.enabled}")


def cmd_add(args):
    """Add a new provider."""
    reg = get_registry()
    
    # Validate kind
    try:
        kind = ProviderKind(args.kind)
    except ValueError:
        print(f"Error: Invalid kind '{args.kind}'. Must be 'ollama-local' or 'openai-compatible'")
        sys.exit(1)
    
    # Parse models
    models = [m.strip() for m in args.models.split(",")] if args.models else []
    
    cfg = reg.create(
        name=args.name,
        kind=kind,
        base_url=args.base_url,
        api_key=args.api_key or "",
        models=models,
        default_model=args.default_model or (models[0] if models else ""),
        enabled=args.enabled,
        timeout=args.timeout,
        extra_headers=json.loads(args.extra_headers) if args.extra_headers else {},
    )
    print(f"Created provider: {cfg.id} ({cfg.name})")
    print(f"  Kind: {cfg.kind.value}")
    print(f"  Base URL: {cfg.base_url}")
    print(f"  Models: {cfg.models}")
    print(f"  Default Model: {cfg.default_model}")
    print(f"  Enabled: {cfg.enabled}")


def cmd_remove(args):
    """Remove a provider."""
    reg = get_registry()
    if reg.delete(args.id):
        print(f"Removed provider: {args.id}")
    else:
        print(f"Provider not found: {args.id}")
        sys.exit(1)


def cmd_test(args):
    """Test a provider connection."""
    reg = get_registry()
    cfg = reg.get(args.id)
    if not cfg:
        print(f"Provider not found: {args.id}")
        sys.exit(1)
    
    print(f"Testing provider: {cfg.name} ({cfg.id})...")
    
    async def _test():
        provider = reg.to_runtime(cfg)
        try:
            models = await provider.fetch_models()
            print(f"✓ Success! Found {len(models)} models:")
            for m in models[:10]:
                print(f"  - {m}")
            if len(models) > 10:
                print(f"  ... and {len(models) - 10} more")
        except Exception as e:
            print(f"✗ Failed: {e}")
            sys.exit(1)
    
    asyncio.run(_test())


def cmd_export(args):
    """Export providers to JSON file."""
    reg = get_registry()
    providers = reg.list(enabled_only=False)
    
    data = {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat(),
        "count": len(providers),
        "providers": []
    }
    
    for p in providers:
        d = p.to_dict(include_secret=args.include_secrets)
        data["providers"].append(d)
    
    if args.output:
        Path(args.output).write_text(json.dumps(data, indent=2))
        print(f"Exported {len(providers)} providers to {args.output}")
    else:
        print(json.dumps(data, indent=2))


def cmd_import(args):
    """Import providers from JSON file."""
    reg = get_registry()
    
    data = json.loads(Path(args.file).read_text())
    providers_data = data.get("providers", [])
    
    if not providers_data:
        print("No providers found in file")
        return
    
    results = {"created": 0, "updated": 0, "skipped": 0, "errors": []}
    
    for p_data in providers_data:
        try:
            # Handle both export formats (with or without encrypted key)
            pid = p_data.get("id", p_data.get("name", "").lower().strip().replace(" ", "-"))
            existing = reg.get(pid)
            
            if existing:
                if args.overwrite:
                    reg.delete(existing.id)
                    results["updated"] += 1
                else:
                    results["skipped"] += 1
                    results["errors"].append(f"'{p_data.get('name', pid)}' already exists (use --overwrite)")
                    continue
            
            # Create provider
            reg.create(
                name=p_data["name"],
                kind=ProviderKind(p_data["kind"]),
                base_url=p_data.get("base_url", ""),
                api_key=p_data.get("api_key_encrypted", "") if args.include_secrets else p_data.get("api_key", ""),
                models=p_data.get("models", []),
                default_model=p_data.get("default_model", ""),
                enabled=p_data.get("enabled", True),
                timeout=p_data.get("timeout", 120.0),
                extra_headers=p_data.get("extra_headers", {}),
            )
            results["created"] += 1
            print(f"  ✓ Imported: {p_data['name']}")
        except Exception as e:
            results["errors"].append(f"{p_data.get('name', 'unknown')}: {str(e)}")
            print(f"  ✗ Failed: {p_data.get('name', 'unknown')} - {e}")
    
    print(f"\nImport complete: {results['created']} created, {results['updated']} updated, {results['skipped']} skipped, {len(results['errors'])} errors")


def cmd_autodetect(args):
    """Auto-detect local Ollama."""
    reg = get_registry()
    
    async def _detect():
        cfg = await reg.autodetect_ollama()
        if cfg:
            print(f"✓ Auto-detected Ollama: {cfg.base_url}")
            print(f"  Created provider: {cfg.id} ({cfg.name})")
        else:
            print("No Ollama detected or already configured")
    
    asyncio.run(_detect())


def cmd_config_file(args):
    """Generate a sample providers.json config file."""
    sample = {
        "version": "1.0",
        "description": "MAGoCo Provider Configuration. Copy to providers.json and modify.",
        "providers": [
            {
                "name": "OpenAI",
                "kind": "openai-compatible",
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-your-key-here",
                "models": ["gpt-4o", "gpt-4o-mini"],
                "default_model": "gpt-4o",
                "enabled": True,
                "timeout": 120.0,
                "extra_headers": {}
            },
            {
                "name": "Anthropic via Gateway",
                "kind": "openai-compatible",
                "base_url": "https://api.anthropic.com/v1",
                "api_key": "sk-ant-your-key-here",
                "models": ["claude-3.5-sonnet", "claude-3.5-haiku"],
                "default_model": "claude-3.5-sonnet",
                "enabled": True,
                "timeout": 120.0,
                "extra_headers": {
                    "anthropic-version": "2023-06-01"
                }
            },
            {
                "name": "Local Ollama",
                "kind": "ollama-local",
                "base_url": "http://localhost:11434",
                "api_key": "",
                "models": ["llama3.1:8b", "llama3.1:70b"],
                "default_model": "llama3.1:8b",
                "enabled": True,
                "timeout": 120.0,
                "extra_headers": {}
            },
            {
                "name": "Custom Gateway (9Router/OpenRouter)",
                "kind": "openai-compatible",
                "base_url": "https://openrouter.ai/api/v1",
                "api_key": "sk-or-your-key-here",
                "models": ["openai/gpt-4o", "anthropic/claude-3.5-sonnet", "meta-llama/llama-3.1-70b"],
                "default_model": "openai/gpt-4o",
                "enabled": True,
                "timeout": 120.0,
                "extra_headers": {
                    "HTTP-Referer": "https://magoco.ai",
                    "X-Title": "MAGoCo-Self-Evo"
                }
            }
        ]
    }
    
    output = args.output or "providers.json"
    Path(output).write_text(json.dumps(sample, indent=2))
    print(f"Sample config written to {output}")
    print("Edit the file with your API keys, then run:")
    print(f"  python -m apps.backend.scripts.manage_providers import --file {output}")


def main():
    parser = argparse.ArgumentParser(description="MAGoCo Provider Management CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # list
    subparsers.add_parser("list", help="List all providers")
    
    # add
    add_p = subparsers.add_parser("add", help="Add a new provider")
    add_p.add_argument("--name", required=True, help="Provider display name")
    add_p.add_argument("--kind", required=True, choices=["ollama-local", "openai-compatible"], help="Provider type")
    add_p.add_argument("--base-url", required=True, help="Base URL of the provider")
    add_p.add_argument("--api-key", default="", help="API key (empty for ollama-local)")
    add_p.add_argument("--models", default="", help="Comma-separated model IDs")
    add_p.add_argument("--default-model", default="", help="Default model ID")
    add_p.add_argument("--enabled", type=bool, default=True, help="Enable provider")
    add_p.add_argument("--timeout", type=float, default=120.0, help="Request timeout")
    add_p.add_argument("--extra-headers", default="{}", help="Extra headers as JSON")
    
    # remove
    remove_p = subparsers.add_parser("remove", help="Remove a provider")
    remove_p.add_argument("--id", required=True, help="Provider ID")
    
    # test
    test_p = subparsers.add_parser("test", help="Test provider connection")
    test_p.add_argument("--id", required=True, help="Provider ID")
    
    # export
    export_p = subparsers.add_parser("export", help="Export providers to JSON")
    export_p.add_argument("--output", "-o", help="Output file path")
    export_p.add_argument("--include-secrets", action="store_true", help="Include encrypted API keys")
    
    # import
    import_p = subparsers.add_parser("import", help="Import providers from JSON file")
    import_p.add_argument("--file", "-f", required=True, help="Input JSON file")
    import_p.add_argument("--overwrite", action="store_true", help="Overwrite existing providers")
    
    # autodetect
    subparsers.add_parser("autodetect-ollama", help="Auto-detect local Ollama")
    
    # config-file
    config_p = subparsers.add_parser("config-file", help="Generate sample providers.json")
    config_p.add_argument("--output", "-o", help="Output file path")
    
    args = parser.parse_args()
    
    commands = {
        "list": cmd_list,
        "add": cmd_add,
        "remove": cmd_remove,
        "test": cmd_test,
        "export": cmd_export,
        "import": cmd_import,
        "autodetect-ollama": cmd_autodetect,
        "config-file": cmd_config_file,
    }
    
    if args.command not in commands:
        parser.print_help()
        sys.exit(1)
    
    try:
        commands[args.command](args)
    except KeyboardInterrupt:
        print("\nCancelled")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    from datetime import datetime
    main()