import xmlrpc.client
import json
import sys
import os
from typing import Dict, List, Any

class WorksheetTemplateDesigner:
    """
    Designs existing Worksheet Templates in Field Service
    Adds custom fields to the worksheet template model and creates the form view
    """
    
    def __init__(self, url: str, db: str, username: str, password: str):
        self.url = url
        self.db = db
        self.username = username
        self.password = password
        self.uid = None
        self.models = None
        
        print(f"🔌 Connecting to {url}...")
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Odoo and get user ID."""
        common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
        
        try:
            self.uid = common.authenticate(self.db, self.username, self.password, {})
            if not self.uid:
                raise Exception("Authentication failed. Check credentials.")
            
            self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
            print(f"✅ Successfully authenticated as user ID: {self.uid}\n")
            
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            sys.exit(1)
    
    def _execute(self, model: str, method: str, *args, **kwargs):
        """Execute an Odoo method via XML-RPC."""
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, method, args, kwargs
        )
    
    def find_worksheet_template_by_name(self, template_name: str) -> tuple:
        """Find the worksheet template and its corresponding model."""
        try:
            # Search in worksheet.template
            template_ids = self._execute(
                'worksheet.template', 'search',
                [['name', '=', template_name]]
            )
            
            if not template_ids:
                print(f"  ❌ Worksheet template '{template_name}' not found")
                return None, None
            
            template_id = template_ids[0]
            
            # Read the template to get its model
            template_data = self._execute(
                'worksheet.template', 'read',
                [template_id], ['name', 'model_id']
            )
            
            if not template_data or not template_data[0].get('model_id'):
                print(f"  ❌ Could not find model for template")
                return None, None
            
            model_id = template_data[0]['model_id'][0]
            
            # Get the model technical name
            model_data = self._execute(
                'ir.model', 'read',
                [model_id], ['model', 'name']
            )
            
            if not model_data:
                print(f"  ❌ Could not read model data")
                return None, None
            
            worksheet_model = model_data[0]['model']
            
            print(f"  ✅ Found template: '{template_name}'")
            print(f"  ✅ Template ID: {template_id}")
            print(f"  ✅ Worksheet Model: {worksheet_model}")
            
            return template_id, worksheet_model
            
        except Exception as e:
            print(f"  ❌ Error finding template: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def check_field_exists(self, model: str, field_name: str) -> bool:
        """Check if a field already exists on a model."""
        try:
            field_ids = self._execute(
                'ir.model.fields', 'search',
                [['model', '=', model], ['name', '=', field_name]]
            )
            return len(field_ids) > 0
        except:
            return False
    
    def create_field(self, model: str, field_config: Dict[str, Any]) -> bool:
        """Create a custom field on the worksheet template model."""
        field_name = field_config['name']
        
        if self.check_field_exists(model, field_name):
            print(f"  ⊙ Field '{field_name}' already exists, skipping...")
            return True
        
        try:
            model_ids = self._execute('ir.model', 'search', [['model', '=', model]])
            if not model_ids:
                print(f"  ❌ Model '{model}' not found")
                return False
            
            model_id = model_ids[0]
            
            field_type_map = {
                'char': 'char',
                'text': 'text',
                'integer': 'integer',
                'float': 'float',
                'date': 'date',
                'datetime': 'datetime',
                'boolean': 'boolean',
                'selection': 'selection',
            }
            
            ttype = field_type_map.get(field_config['field_type'], 'char')
            
            field_values = {
                'name': field_name,
                'field_description': field_config['label'],
                'model_id': model_id,
                'ttype': ttype,
                'state': 'manual',
                'required': field_config.get('required', False),
                'readonly': field_config.get('readonly', False),
            }
            
            # REMOVED: Default value setting - not supported via XML-RPC field creation
            # Default values will be handled in the view or via ir.default separately
            
            if ttype == 'selection' and 'selection' in field_config:
                selection_str = str(field_config['selection'])
                field_values['selection'] = selection_str
            
            field_id = self._execute('ir.model.fields', 'create', field_values)
            print(f"  ✅ Created field '{field_name}' (ID: {field_id})")
            
            # Try to set default value using ir.default if specified
            if 'default_value' in field_config and field_config['default_value']:
                self.set_field_default(model, field_name, field_config['default_value'])
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error creating field '{field_name}': {e}")
            return False
    
    def set_field_default(self, model: str, field_name: str, default_value: Any) -> bool:
        """Set default value for a field using ir.default."""
        try:
            # Use ir.default to set default values
            self._execute('ir.default', 'set', 
                         model, field_name, default_value)
            print(f"    ↳ Set default value for '{field_name}'")
            return True
        except Exception as e:
            print(f"    ⚠️ Could not set default for '{field_name}': {e}")
            return False
    
    def generate_worksheet_xml_vibracion(self, template_config: Dict[str, Any]) -> str:
        """Generate XML for Vibration test worksheet."""
        template_name = template_config['template_name']
        
        # Get default values from config
        default_objective = ""
        default_procedure = ""
        default_method = ""
        default_criteria = ""
        
        for field in template_config['fields']:
            if field['name'] == 'x_test_objective' and 'default_value' in field:
                default_objective = field['default_value']
            elif field['name'] == 'x_test_procedure' and 'default_value' in field:
                default_procedure = field['default_value']
            elif field['name'] == 'x_test_method' and 'default_value' in field:
                default_method = field['default_value']
            elif field['name'] == 'x_acceptance_criteria' and 'default_value' in field:
                default_criteria = field['default_value']
        
        xml = '''<form string="''' + template_name + '''">
    <sheet>
        <div class="oe_title">
            <h1>Test de vibración</h1>
        </div>
        
        <group string="Información del Equipo" col="2">
            <field name="x_assistance_code"/>
            <field name="x_client"/>
            <field name="x_model"/>
            <field name="x_project"/>
            <field name="x_serial_number"/>
        </group>
        
        <separator string="1. Test de vibración"/>
        
        <group string="1.1. Objetivo">
            <field name="x_test_objective" widget="text" readonly="1"/>
        </group>
        
        <group string="1.2. Procedimiento">
            <field name="x_test_procedure" widget="text" readonly="1"/>
        </group>
        
        <group string="1.3. Método">
            <field name="x_test_method" widget="text" readonly="1"/>
        </group>
        
        <group string="1.4. Criterio de aceptación">
            <field name="x_acceptance_criteria" widget="text" readonly="1"/>
        </group>
        
        <separator string="1.5. Instrumento de medición"/>
        
        <group col="4">
            <field name="x_instrument_brand_model"/>
            <field name="x_instrument_serial"/>
            <field name="x_calibration_certificate"/>
            <field name="x_calibration_date"/>
        </group>
        
        <separator string="1.6. Datos de la prueba - Reglajes"/>
        
        <group col="4">
            <field name="x_limit_1"/>
            <field name="x_limit_2"/>
            <field name="x_max_speed"/>
            <field name="x_test_weights"/>
        </group>
        
        <separator string="Ensayo 1"/>
        <group col="4">
            <field name="x_test_1_imbalance"/>
            <newline/>
            <field name="x_test_1_speed_50"/>
            <field name="x_test_1_vibration_50"/>
            <field name="x_test_1_speed_75"/>
            <field name="x_test_1_vibration_75"/>
            <field name="x_test_1_speed_100"/>
            <field name="x_test_1_vibration_100"/>
        </group>
        <group>
            <field name="x_test_1_comments" widget="text" nolabel="1" placeholder="Comentarios Ensayo 1"/>
        </group>
        
        <separator string="Ensayo 2"/>
        <group col="4">
            <field name="x_test_2_imbalance"/>
            <newline/>
            <field name="x_test_2_speed_50"/>
            <field name="x_test_2_vibration_50"/>
            <field name="x_test_2_speed_75"/>
            <field name="x_test_2_vibration_75"/>
            <field name="x_test_2_speed_100"/>
            <field name="x_test_2_vibration_100"/>
        </group>
        <group>
            <field name="x_test_2_comments" widget="text" nolabel="1" placeholder="Comentarios Ensayo 2"/>
        </group>
        
        <separator string="Ensayo 3"/>
        <group col="4">
            <field name="x_test_3_imbalance"/>
            <newline/>
            <field name="x_test_3_speed_50"/>
            <field name="x_test_3_vibration_50"/>
            <field name="x_test_3_speed_75"/>
            <field name="x_test_3_vibration_75"/>
            <field name="x_test_3_speed_100"/>
            <field name="x_test_3_vibration_100"/>
        </group>
        <group>
            <field name="x_test_3_comments" widget="text" nolabel="1" placeholder="Comentarios Ensayo 3"/>
        </group>
        
        <separator string="1.7. Resultados test"/>
        
        <group>
            <field name="x_test_comments" widget="text" placeholder="Comentarios generales"/>
            <field name="x_result_status" widget="radio"/>
        </group>
        
        <separator/>
        
        <group col="4">
            <field name="x_performed_by"/>
            <field name="x_department"/>
            <field name="x_test_date"/>
            <field name="x_signature"/>
        </group>
        
    </sheet>
</form>'''
        
        return xml
    
    def create_worksheet_view(self, worksheet_model: str, template_config: Dict[str, Any]) -> int:
        """Create the form view for the worksheet template."""
        try:
            view_name = f"view_{worksheet_model.replace('.', '_')}_form"
            view_xml = self.generate_worksheet_xml_vibracion(template_config)
            
            # Check if view exists
            existing_views = self._execute(
                'ir.ui.view', 'search',
                [['name', '=', view_name], ['model', '=', worksheet_model]]
            )
            
            if existing_views:
                print(f"  ⊙ View '{view_name}' already exists, updating...")
                view_id = existing_views[0]
                self._execute('ir.ui.view', 'write', [view_id], {
                    'arch': view_xml,
                })
                print(f"  ✅ Updated view (ID: {view_id})")
                return view_id
            
            # Create new view
            view_values = {
                'name': view_name,
                'model': worksheet_model,
                'type': 'form',
                'arch': view_xml,
                'priority': 1,
            }
            
            view_id = self._execute('ir.ui.view', 'create', view_values)
            print(f"  ✅ Created worksheet view '{view_name}' (ID: {view_id})")
            return view_id
            
        except Exception as e:
            print(f"  ❌ Error creating view: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def design_template(self, json_path: str) -> Dict[str, Any]:
        """
        Main function: Design an existing worksheet template.
        Adds fields and creates the form view.
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                template = json.load(f)
        except Exception as e:
            print(f"❌ Error loading JSON: {e}")
            return {'success': False, 'error': str(e)}
        
        template_name = template['template_name']
        fields = template['fields']
        
        print(f"{'='*70}")
        print(f"🎨 WORKSHEET TEMPLATE DESIGNER")
        print(f"{'='*70}")
        print(f"Template: {template_name}")
        print(f"Fields to add: {len(fields)}")
        print(f"{'='*70}\n")
        
        # Step 1: Find the worksheet template and its model
        print("🔍 STEP 1: Finding worksheet template...")
        template_id, worksheet_model = self.find_worksheet_template_by_name(template_name)
        
        if not template_id or not worksheet_model:
            print("\n❌ Could not find the worksheet template!")
            print("💡 Make sure you created it in Field Service → Configuration → Worksheet Templates")
            return {'success': False}
        
        results = {
            'template_name': template_name,
            'template_id': template_id,
            'worksheet_model': worksheet_model,
            'total_fields': len(fields),
            'created': 0,
            'failed': 0,
            'failed_fields': []
        }
        
        # Step 2: Add custom fields to the worksheet model
        print(f"\n📝 STEP 2: Adding custom fields to '{worksheet_model}'...")
        for idx, field_config in enumerate(fields, 1):
            print(f"[{idx}/{len(fields)}] {field_config['name']}")
            success = self.create_field(worksheet_model, field_config)
            
            if success:
                results['created'] += 1
            else:
                results['failed'] += 1
                results['failed_fields'].append(field_config['name'])
        
        # Step 3: Create the worksheet form view
        print(f"\n🎨 STEP 3: Creating worksheet form view...")
        view_id = self.create_worksheet_view(worksheet_model, template)
        results['view_id'] = view_id
        
        # Summary
        print(f"\n{'='*70}")
        print(f"✅ WORKSHEET DESIGN COMPLETE!")
        print(f"{'='*70}")
        print(f"Template: {template_name} (ID: {template_id})")
        print(f"Model: {worksheet_model}")
        print(f"Fields created: {results['created']}/{results['total_fields']}")
        print(f"Form view: {'✅' if view_id else '❌'} (ID: {view_id})")
        if results['failed_fields']:
            print(f"Failed fields: {', '.join(results['failed_fields'])}")
        print(f"{'='*70}\n")
        
        results['success'] = view_id is not None
        return results


def main():
    """Main execution function."""
    
    print("""
╔═══════════════════════════════════════════════════════════════╗
║   🎨 TEST DE VIBRACION - WORKSHEET DESIGNER                  ║
║   Automatically design the vibration test template!          ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    if not os.path.exists('config.json'):
        print("❌ ERROR: config.json not found!")
        sys.exit(1)
    
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    ODOO_URL = config['odoo_url'].rstrip('/')
    ODOO_DB = config['odoo_db']
    ODOO_USERNAME = config['odoo_username']
    ODOO_PASSWORD = config['odoo_password']
    TEMPLATE_FILE = config['template_file']
    
    if not os.path.exists(TEMPLATE_FILE):
        print(f"❌ ERROR: Template file not found: {TEMPLATE_FILE}")
        sys.exit(1)
    
    print(f"✅ Configuration loaded")
    print(f"  URL: {ODOO_URL}")
    print(f"  Database: {ODOO_DB}")
    print(f"  Template: {TEMPLATE_FILE}\n")
    
    try:
        designer = WorksheetTemplateDesigner(
            ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD
        )
        results = designer.design_template(TEMPLATE_FILE)
        
        if results.get('success'):
            print("🎉 SUCCESS! Test de Vibracion template designed!\n")
            print("📋 HOW TO USE YOUR WORKSHEET:")
            print("="*70)
            print("1. Go to Field Service → My Tasks")
            print("2. Create or open a task")
            print("3. Set Worksheet Template = 'Test de vibracion'")
            print("4. Click the 'Worksheet' button at the top")
            print("5. Fill out the vibration test with 3 test runs!")
            print()
            print("✨ All 47 fields are ready!")
            print("✨ 3 complete test runs (Ensayo 1, 2, 3)")
            print("✨ Measurements at 50%, 75%, 100% speed")
            
        else:
            print("\n⚠️ Template design completed with errors.")
            print("\n💡 TIP: Make sure 'Test de vibracion' template exists!")
            print("   Create it in: Field Service → Configuration → Worksheet Templates")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()