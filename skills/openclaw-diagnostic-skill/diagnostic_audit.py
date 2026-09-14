import json
import os
import sys

def audit_openclaw():
    print("=== OpenClaw Provider & Configuration Audit ===")
    config_path = "/home/ec/.openclaw/openclaw.json"
    
    if not os.path.exists(config_path):
        print(f"[ERROR] Configuration file not found: {config_path}")
        return

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"[ERROR] Failed to parse {config_path}: {e}")
        return

    # 1. Audit Providers
    print("\n--- 1. Provider Configuration Audit ---")
    providers = config.get("models", {}).get("providers", {})
    
    if not providers:
        print("[CRITICAL] No providers defined in 'models.providers'.")
    else:
        # Check specifically for search providers to warn about web_search capability
        search_providers = ["brave", "serper", "tavily", "perplexity"]
        has_search_provider = any(p in providers for p in search_providers)
        
        if not has_search_provider:
            print("[WARNING] No search providers (Brave, Serper, Tavily, etc.) are registered. web_search will be disabled.")

        for name, details in providers.items():
            print(f"[*] Provider: {name}")
            # Check for common required fields
            required_fields = ["api"]
            # apiKey is often present but we don't want to print it
            
            missing = [f for f in required_fields if f not in details]
            if missing:
                print(f"    [!] MISSING FIELDS: {', '.join(missing)}")
            else:
                print(f"    [OK] Basic configuration present.")

            # Check for presence of API keys in values (redacting for safety)
            if "apiKey" in details:
                key_val = str(details["apiKey"])
                if len(key_val) > 4:
                    print(f"    [OK] apiKey is configured (redacted: {key_val[:4]}...)")
                else:
                    print(f"    [!] apiKey is empty or too short.")
            else:
                print(f"    [!] apiKey is missing.")

    # 2. Audit Environment Variables
    print("\n--- 2. Environment Variable Audit ---")
    # Mapping common providers to their expected env vars
    provider_env_map = {
        "brave": "BRAVE_API_KEY",
        "serper": "SERPER_API_KEY",
        "tavily": "TAVILY_API_KEY",
        "perplexity": "PERPLEXITY_API_KEY",
        "openai": "OPENAI_API_KEY"
    }

    found_any = False
    for provider_key, env_var in provider_env_map.items():
        # If the provider is in the config, check if its env var is present
        if provider_key in providers:
            found_any = True
            val = os.environ.get(env_var)
            if val:
                print(f"[*] [OK] {env_var} is set in environment.")
            else:
                print(f"[*] [!] {env_var} is NOT set in environment (required for {provider_key}).")
    
    if not found_any:
        print("[INFO] No common provider environment variables were checked (no matching providers in config).")

    # 3. Summary
    print("\n=== Audit Complete ===")

if __name__ == "__main__":
    audit_openclaw()
