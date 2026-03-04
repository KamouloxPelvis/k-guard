import requests
import json

def fetch_and_verify():
    """
    Utility script to test connectivity with Cloudflare IP range API
    and validate the data structure for Ansible integration.
    """
    print("🌐 Attempting to fetch Cloudflare IP ranges...")
    try:
        # Querying the official Cloudflare IPv4 list
        response = requests.get("https://www.cloudflare.com/ips-v4", timeout=5)
        response.raise_for_status()
        
        # Convert response text into a list of CIDR ranges
        ips = response.text.strip().split('\n')
        
        print(f"✅ Success! {len(ips)} IPv4 ranges retrieved.")
        
        # Simulating the required format for Ansible injection (--extra-vars)
        ansible_extra_vars = json.dumps({"cf_ips": ips})
        print("\n📦 Ansible Injection Format (Extra Vars):")
        print(ansible_extra_vars)
        
        return True
    except Exception as e:
        print(f"❌ Operation Failed: {e}")
        return False

if __name__ == "__main__":
    fetch_and_verify()