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
            template_ids = self._execute(
                'worksheet.template', 'search',
                [['name', '=', template_name]]
            )
            
            if not template_ids:
                print(f"  ❌ Worksheet template '{template_name}' not found")
                return None, None
            
            template_id = template_ids[0]
            
            template_data = self._execute(
                'worksheet.template', 'read',
                [template_id], ['name', 'model_id']
            )
            
            if not template_data or not template_data[0].get('model_id'):
                print(f"  ❌ Could not find model for template")
                return None, None
            
            model_id = template_data[0]['model_id'][0]
            
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
            
            if ttype == 'selection' and 'selection' in field_config:
                selection_str = str(field_config['selection'])
                field_values['selection'] = selection_str
            
            field_id = self._execute('ir.model.fields', 'create', field_values)
            print(f"  ✅ Created field '{field_name}' (ID: {field_id})")
            return True
            
        except Exception as e:
            print(f"  ❌ Error creating field '{field_name}': {e}")
            return False
    
    def generate_worksheet_xml(self, template_config: Dict[str, Any]) -> str:
        """Generate XML for the centrifuge revision worksheet form view."""
        template_name = template_config['template_name']
        
        xml = '''<form string="''' + template_name + '''">
    <sheet>
        <div class="oe_title">
            <h1>''' + template_name + '''</h1>
            <h3>Electrical &amp; Mechanical Inspection</h3>
        </div>
        
        <group string="Equipment Information" col="4">
            <field name="x_assistance_code"/>
            <field name="x_customer"/>
            <field name="x_model"/>
            <field name="x_project"/>
            <field name="x_serial_number" colspan="1"/>
        </group>
        
        <separator string="Inspection Details"/>
        
        <group string="Performed by" col="3">
            <field name="x_performed_by"/>
            <field name="x_position_dept"/>
            <field name="x_inspection_date"/>
        </group>
        
        <group string="Received by Customer" col="3">
            <field name="x_received_by"/>
            <field name="x_received_position"/>
            <field name="x_received_date"/>
        </group>
        
        <separator string="1. Revision Centrifuge"/>
        
        <group string="1.1. Objective">
            <field name="x_objective" widget="text" readonly="1"/>
        </group>
        
        <group string="1.2. Procedure">
            <field name="x_procedure" widget="text" readonly="1"/>
        </group>
        
        <group string="1.3. Standard">
            <field name="x_standard" widget="text" readonly="1"/>
        </group>
        
        <separator string="1.4. Inspection Points / Maintenance"/>
        
        <group string="Confirmation of Previous Status with Client" col="2">
            <field name="x_prev_no_defects" widget="radio"/>
            <field name="x_prev_regular_use" widget="radio"/>
            <field name="x_prev_minor_defects" widget="radio"/>
            <field name="x_prev_customer_comments" widget="text" colspan="2"/>
        </group>
        
        <separator string="Previous Verifications"/>
        
        <group string="Basic Checks" col="2">
            <field name="x_verify_id_plate" widget="radio"/>
            <field name="x_verify_emergency_stop" widget="radio"/>
            <field name="x_verify_hmi" widget="radio"/>
            <field name="x_verify_collector" widget="radio"/>
            <field name="x_verify_rotation" widget="radio"/>
            <field name="x_verify_vibration" widget="radio"/>
            <field name="x_verify_comments" widget="text" colspan="2"/>
        </group>
        
        <separator string="Inertial Baseplate"/>
        
        <group string="Baseplate Inspection" col="2">
            <field name="x_baseplate_corrosion" widget="radio"/>
            <field name="x_baseplate_remains" widget="radio"/>
            <field name="x_support_structure" widget="radio"/>
            <field name="x_motor_support" widget="radio"/>
            <field name="x_connection_boxes" widget="radio"/>
            <field name="x_cover_condition" widget="radio"/>
            <field name="x_cable_protection" widget="radio"/>
            <field name="x_vibration_sensor" widget="radio"/>
            <field name="x_baseplate_comments" widget="text" colspan="2"/>
        </group>
        
        <separator string="Suspension System"/>
        
        <group col="2">
            <field name="x_suspension_maintenance"/>
            <newline/>
            <field name="x_dampers_condition" widget="radio"/>
            <field name="x_tripendular_condition" widget="radio"/>
            <field name="x_visco_dampers" widget="radio"/>
            <field name="x_suspension_comments" widget="text" colspan="2"/>
        </group>
        
        <separator string="Casing"/>
        
        <group col="2">
            <field name="x_casing_maintenance"/>
            <newline/>
            <field name="x_temp_probe" widget="radio"/>
            <field name="x_sensor_interlock" widget="radio"/>
            <field name="x_pneumatic_system" widget="radio"/>
            <field name="x_casing_gasket" widget="radio"/>
            <field name="x_casing_closure" widget="radio"/>
            <field name="x_casing_comments" widget="text" colspan="2"/>
        </group>
        
        <separator string="Lid"/>
        
        <group col="2">
            <field name="x_lid_maintenance"/>
            <newline/>
            <field name="x_sight_glasses" widget="radio"/>
            <field name="x_hinges" widget="radio"/>
            <field name="x_opening_cylinder" widget="radio"/>
            <field name="x_lid_comments" widget="text" colspan="2"/>
        </group>
        
        <separator string="Feeding Detector"/>
        
        <group col="2">
            <field name="x_feeding_detector_maintenance"/>
            <newline/>
            <field name="x_feeding_corrosion" widget="radio"/>
            <field name="x_feeding_instrumentation" widget="radio"/>
            <field name="x_feeding_comments" widget="text" colspan="2"/>
        </group>
        
        <separator string="Piping and Connections"/>
        
        <group col="2">
            <field name="x_feeding_pipe" widget="radio"/>
            <field name="x_washing_pipe" widget="radio"/>
            <field name="x_outlet_liquid" widget="radio"/>
            <field name="x_cip_system" widget="radio"/>
            <field name="x_solid_discharge_pipe" widget="radio"/>
            <field name="x_piping_comments" widget="text" colspan="2"/>
        </group>
        
        <separator string="Scrapper"/>
        
        <group col="2">
            <field name="x_scrapper_maintenance"/>
            <newline/>
            <field name="x_scrapper_hydraulic" widget="radio"/>
            <field name="x_hydraulic_circuit" widget="radio"/>
            <field name="x_blade_condition" widget="radio"/>
            <field name="x_blade_blowing" widget="radio"/>
            <field name="x_scrapper_comments" widget="text" colspan="2"/>
        </group>
        
        <separator string="Antagonic Blowing"/>
        
        <group col="2">
            <field name="x_antagonic_maintenance"/>
            <newline/>
            <field name="x_antagonic_clearances" widget="radio"/>
            <field name="x_antagonic_comments" widget="text" colspan="2"/>
        </group>
        
        <separator string="Drive"/>
        
        <group col="2">
            <field name="x_drive_maintenance"/>
            <newline/>
            <field name="x_belt_condition" widget="radio"/>
            <field name="x_main_motor" widget="radio"/>
            <field name="x_pulley_condition" widget="radio"/>
            <field name="x_static_discharge" widget="radio"/>
            <field name="x_tachometric" widget="radio"/>
            <field name="x_drive_comments" widget="text" colspan="2"/>
        </group>
        
        <separator string="Basket"/>
        
        <group col="2">
            <field name="x_basket_bottom" widget="radio"/>
            <field name="x_basket_boarding" widget="radio"/>
            <field name="x_basket_ferrule" widget="radio"/>
            <field name="x_basket_comments" widget="text" colspan="2"/>
        </group>
        
        <separator string="Bearing Box"/>
        
        <group col="2">
            <field name="x_bearing_maintenance"/>
            <newline/>
            <field name="x_greasing_system" widget="radio"/>
            <field name="x_oil_system" widget="radio"/>
            <field name="x_bearing_temp_probe" widget="radio"/>
            <field name="x_inerting" widget="radio"/>
            <field name="x_bearing_comments" widget="text" colspan="2"/>
        </group>
        
        <separator string="Hoses"/>
        
        <group col="2">
            <field name="x_hoses_maintenance"/>
            <newline/>
            <field name="x_liquid_outlet_hose" widget="radio"/>
            <field name="x_hoses_comments" widget="text" colspan="2"/>
        </group>
        
        <separator string="Filtercloth"/>
        
        <group col="2">
            <field name="x_filtercloth_fixing_ring" widget="radio"/>
            <field name="x_filtercloth_clip" widget="radio"/>
            <field name="x_filtercloth_gasket" widget="radio"/>
            <field name="x_filtercloth_comments" widget="text" colspan="2"/>
        </group>
        
        <separator string="Solid Discharge"/>
        
        <group col="2">
            <field name="x_butterfly_valve" widget="radio"/>
            <field name="x_screw_conveyor" widget="radio"/>
            <field name="x_solid_discharge_comments" widget="text" colspan="2"/>
        </group>
        
        <separator string="Inertization"/>
        
        <group col="2">
            <field name="x_inertization_maintenance"/>
            <newline/>
            <field name="x_blanketing_panel" widget="radio"/>
            <field name="x_oxygen_analyzer" widget="radio"/>
            <field name="x_siphonic_tank" widget="radio"/>
            <field name="x_inertization_comments" widget="text" colspan="2"/>
        </group>
        
        <separator string="Hydraulic Unit"/>
        
        <group col="2">
            <field name="x_hydraulic_unit_maintenance"/>
            <newline/>
            <field name="x_hydraulic_actuators" widget="radio"/>
            <field name="x_hydraulic_comments" widget="text" colspan="2"/>
        </group>
        
        <separator string="Lubrication Unit"/>
        
        <group col="2">
            <field name="x_lubrication_maintenance"/>
            <newline/>
            <field name="x_lubrication_actuators" widget="radio"/>
            <field name="x_lubrication_comments" widget="text" colspan="2"/>
        </group>
        
        <separator string="Electrical Cabinets"/>
        
        <group col="2">
            <field name="x_power_cabinet" widget="radio"/>
            <field name="x_control_cabinet" widget="radio"/>
            <field name="x_operator_panel_cabinet" widget="radio"/>
            <field name="x_brake_resistors" widget="radio"/>
            <field name="x_electrical_comments" widget="text" colspan="2"/>
        </group>
        
        <separator string="Tests"/>
        
        <group col="2">
            <field name="x_temperature_test" widget="radio"/>
            <field name="x_vibrations_test" widget="radio"/>
            <field name="x_leak_test" widget="radio"/>
            <field name="x_tests_comments" widget="text" colspan="2"/>
        </group>
        
        <separator string="Others Before Not Mentioned"/>
        
        <group>
            <field name="x_others_not_mentioned" widget="text" nolabel="1"/>
        </group>
        
        <separator string="1.5. Notes, Comments and Final Conclusions"/>
        
        <group>
            <field name="x_final_notes" widget="text" nolabel="1"/>
        </group>
        
        <separator/>
        
        <group string="Overall Inspection Result">
            <field name="x_overall_result" widget="radio"/>
        </group>
        
    </sheet>
</form>'''
        
        return xml
    
    def create_worksheet_view(self, worksheet_model: str, template_config: Dict[str, Any]) -> int:
        """Create the form view for the worksheet template."""
        try:
            view_name = f"view_{worksheet_model.replace('.', '_')}_form"
            view_xml = self.generate_worksheet_xml(template_config)
            
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
        """Main function: Design an existing worksheet template."""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                template = json.load(f)
        except Exception as e:
            print(f"❌ Error loading JSON: {e}")
            return {'success': False, 'error': str(e)}
        
        template_name = template['template_name']
        fields = template['fields']
        
        print(f"{'='*70}")
        print(f"🎨 WORKSHEET TEMPLATE DESIGNER - CENTRIFUGE REVISION")
        print(f"{'='*70}")
        print(f"Template: {template_name}")
        print(f"Fields to add: {len(fields)}")
        print(f"{'='*70}\n")
        
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
        
        print(f"\n🔧 STEP 2: Adding custom fields to '{worksheet_model}'...")
        for idx, field_config in enumerate(fields, 1):
            print(f"[{idx}/{len(fields)}] {field_config['name']}")
            success = self.create_field(worksheet_model, field_config)
            
            if success:
                results['created'] += 1
            else:
                results['failed'] += 1
                results['failed_fields'].append(field_config['name'])
        
        print(f"\n🎨 STEP 3: Creating worksheet form view...")
        view_id = self.create_worksheet_view(worksheet_model, template)
        results['view_id'] = view_id
        
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
║   🎨 ODOO CENTRIFUGE REVISION WORKSHEET DESIGNER              ║
║   Automatically design comprehensive inspection templates!    ║
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
    TEMPLATE_FILE = config.get('template_file', 'centrifuge_revision_template.json')
    
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
            print("🎉 SUCCESS! Centrifuge revision worksheet designed!\n")
            print("📋 HOW TO USE YOUR WORKSHEET TEMPLATE:")
            print("="*70)
            print("1. Go to Field Service → Configuration → Worksheet Templates")
            print(f"2. Find '{results['template_name']}'")
            print("3. Click 'Design Template' to preview/edit in Studio")
            print()
            print("TO USE IN TASKS:")
            print("1. Go to Field Service → My Tasks")
            print("2. Create or open a task")
            print("3. In 'Worksheet Template' field, select your template")
            print("4. Click 'Create Worksheet' - your inspection form will appear!")
            print()
            print("✨ All inspection points are organized by section!")
            print("✨ Radio buttons for OK/No OK/N/A selections!")
            print("✨ Comment fields for detailed notes!")
            
        else:
            print("\n⚠️ Worksheet design completed with errors.")
            print("\n💡 TIP: Make sure the worksheet template exists first!")
            print("   Create it in: Field Service → Configuration → Worksheet Templates")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()