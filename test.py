import xmlrpc.client
import json

print("Loading configuration...")
with open('config.json', 'r') as f:
    config = json.load(f)

url = config['odoo_url']
db = config['odoo_db']
username = config['odoo_username']
password = config['odoo_password']

print(f"\nTesting connection to: {url}")
print(f"Database: {db}")
print(f"Username: {username}")

try:
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    
    if uid:
        print(f"\n✓ SUCCESS! Connected as user ID: {uid}")
        print("Your configuration is correct!")
    else:
        print("\n✗ FAILED! Authentication returned False")
        print("Check your credentials in config.json")
        
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    print("\nPossible issues:")
    print("  - Wrong URL (check spelling and https://)")
    print("  - Wrong database name")
    print("  - Wrong username or API key")
    print("  - Network/firewall blocking connection")