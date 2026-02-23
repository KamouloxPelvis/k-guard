import requests
import json

def fetch_and_verify():
    print("🌐 Tentative de récupération des IPs Cloudflare...")
    try:
        # On interroge l'API Cloudflare
        response = requests.get("https://www.cloudflare.com/ips-v4", timeout=5)
        response.raise_for_status()
        
        # Transformation en liste
        ips = response.text.strip().split('\n')
        
        print(f"✅ Succès ! {len(ips)} plages IPv4 récupérées.")
        
        # Simulation du format attendu par Ansible (--extra-vars)
        ansible_extra_vars = json.dumps({"cf_ips": ips})
        print("\n📦 Format d'injection Ansible (Extra Vars) :")
        print(ansible_extra_vars)
        
        return True
    except Exception as e:
        print(f"❌ Échec : {e}")
        return False

if __name__ == "__main__":
    fetch_and_verify()