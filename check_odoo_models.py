import xmlrpc.client
import json

def check_odoo_models():
    """
    Diagnostic script to check what Field Service models are available
    """
    
    print("""
╔═══════════════════════════════════════════════════════════════╗
║          ODOO MODEL DIAGNOSTIC TOOL                          ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Load config
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    url = config['odoo_url'].rstrip('/')
    db = config['odoo_db']
    username = config['odoo_username']
    password = config['odoo_password']
    
    print(f"🔌 Connecting to {url}...")
    
    # Authenticate
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        print("❌ Authentication failed!")
        return
    
    print(f"✅ Authenticated as user ID: {uid}\n")
    
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    
    # Search for Field Service related models
    print("🔍 Searching for Field Service models...\n")
    
    field_service_keywords = [
        'fsm', 'field', 'service', 'worksheet', 
        'project.task', 'maintenance', 'helpdesk'
    ]
    
    found_models = {}
    
    for keyword in field_service_keywords:
        try:
            model_ids = models.execute_kw(
                db, uid, password,
                'ir.model', 'search_read',
                [[['model', 'ilike', keyword]]],
                {'fields': ['model', 'name']}
            )
            
            if model_ids:
                for model in model_ids:
                    found_models[model['model']] = model['name']
        except:
            pass
    
    if found_models:
        print("✅ Found the following models:")
        print("=" * 70)
        for model, name in sorted(found_models.items()):
            print(f"  📦 {model:<35} → {name}")
        print("=" * 70)
    else:
        print("❌ No Field Service models found!")
        print("   The Field Service module might not be installed.")
    
    # Check for project.task specifically
    print("\n🔍 Checking project.task model...")
    try:
        project_task = models.execute_kw(
            db, uid, password,
            'ir.model', 'search_read',
            [[['model', '=', 'project.task']]],
            {'fields': ['model', 'name']}
        )
        
        if project_task:
            print("✅ project.task model EXISTS")
            print("   You can use 'project.task' as base_model")
            
            # Check fields on project.task
            print("\n🔍 Checking existing fields on project.task...")
            fields = models.execute_kw(
                db, uid, password,
                'ir.model.fields', 'search_read',
                [[['model', '=', 'project.task'], ['name', 'ilike', 'worksheet']]],
                {'fields': ['name', 'field_description'], 'limit': 10}
            )
            
            if fields:
                print("   Found worksheet-related fields:")
                for field in fields:
                    print(f"     • {field['name']}: {field['field_description']}")
        else:
            print("❌ project.task model NOT found (unusual)")
    except Exception as e:
        print(f"❌ Error checking project.task: {e}")
    
    # Check installed modules
    print("\n🔍 Checking installed Field Service modules...")
    try:
        modules = models.execute_kw(
            db, uid, password,
            'ir.module.module', 'search_read',
            [[['name', 'ilike', 'field'], ['state', '=', 'installed']]],
            {'fields': ['name', 'shortdesc']}
        )
        
        if modules:
            print("✅ Installed Field Service modules:")
            for mod in modules:
                print(f"   • {mod['name']:<30} → {mod['shortdesc']}")
        else:
            print("❌ No Field Service modules found!")
    except Exception as e:
        print(f"❌ Error checking modules: {e}")
    
    # Recommendations
    print("\n" + "=" * 70)
    print("💡 RECOMMENDATIONS:")
    print("=" * 70)
    
    if 'fsm.worksheet' in found_models:
        print("✅ Use 'fsm.worksheet' as base_model (Field Service Enterprise)")
    elif 'project.task' in found_models:
        print("✅ Use 'project.task' as base_model (Standard approach)")
        print("   This works with Project module for field service tasks")
    else:
        print("⚠️  Consider installing one of these modules:")
        print("   • Field Service (Enterprise)")
        print("   • Project (for basic task management)")
        print("   • Industry FSM (Community alternative)")

if __name__ == '__main__':
    check_odoo_models()