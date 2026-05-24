"""
UI Panels for Auto Rigger addon
Defines the user interface in the 3D View sidebar.
"""

import bpy
from bpy.types import Panel


class VIEW3D_PT_auto_rig_main(Panel):
    """Main panel for Auto Rigger"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Auto Rig'
    bl_label = "Auto Rigger"
    bl_idname = "VIEW3D_PT_auto_rig_main"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        settings = scene.auto_rig_settings
        
        # Header info
        layout.label(text="Automatic Humanoid Rigging", icon='ARMATURE_DATA')
        layout.separator()
        
        # Step 1: Mesh Selection
        box = layout.box()
        box.label(text="1. Select Target Mesh", icon='MESH_DATA')
        box.prop(settings, "target_mesh", text="")
        
        # Validation feedback
        if settings.target_mesh:
            obj = settings.target_mesh
            if obj.type != 'MESH':
                box.label(text="⚠ Not a mesh object", icon='ERROR')
            else:
                vert_count = len(obj.data.vertices)
                box.label(text=f"✓ Vertices: {vert_count}", icon='CHECKMARK')
                
                # Quick landmark detection
                row = box.row()
                row.operator("object.auto_rig_detect_landmarks", 
                           text="Detect Body Parts",
                           icon='VIEWZOOM')
                
                if settings.landmarks_detected:
                    box.label(text="✓ Landmarks detected", icon='CHECKMARK')
        
        layout.separator()
        
        # Step 2: Configuration
        box = layout.box()
        box.label(text="2. Configure Rig", icon='SETTINGS')
        
        col = box.column(align=True)
        col.prop(settings, "rig_source")
        col.prop(settings, "body_type")
        col.prop(settings, "rig_type")
        col.prop(settings, "bone_naming")
        
        layout.separator()
        
        # Step 3: Generate
        box = layout.box()
        box.label(text="3. Generate", icon='PLAY')
        
        # Main generation button
        row = box.row(align=True)
        row.scale_y = 1.5
        
        op = row.operator("object.auto_rig_generate", 
                         text="Generate Rig",
                         icon='ARMATURE_DATA')
        
        # Progress indicator
        if settings.generation_progress > 0:
            box.prop(settings, "generation_progress", text="Progress", slider=True)
        
        # Quick tips
        layout.separator()
        box = layout.box()
        box.label(text="💡 Tips:", icon='INFO')
        col = box.column(align=True)
        col.scale_y = 0.8
        col.label(text="• Ensure mesh is in T-pose or A-pose")
        col.label(text="• Remove applied modifiers first")
        col.label(text="• Check symmetry for best results")


class VIEW3D_PT_auto_rig_settings(Panel):
    """Settings panel for rig generation"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Auto Rig'
    bl_label = "Rig Settings"
    bl_idname = "VIEW3D_PT_auto_rig_settings"
    bl_parent_id = "VIEW3D_PT_auto_rig_main"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.auto_rig_settings
        
        # IK/FK options
        box = layout.box()
        box.label(text="Controls", icon='CONSTRAINT')
        col = box.column(align=True)
        
        row = col.row()
        row.prop(settings, "create_ik", toggle=True)
        
        if settings.create_ik:
            row = col.row()
            row.prop(settings, "create_pole_targets", toggle=True)
        
        col.separator()
        
        # Bone options
        if settings.rig_type == 'ADVANCED':
            col.prop(settings, "add_finger_bones", toggle=True)
        
        col.prop(settings, "add_twist_bones", toggle=True)
        col.prop(settings, "spine_bones")

        if settings.rig_source == 'RIGIFY_HUMAN':
            layout.separator()
            box = layout.box()
            box.label(text="Rigify", icon='ARMATURE_DATA')
            col = box.column(align=True)
            col.prop(settings, "rigify_generate_controls", toggle=True)
        
        layout.separator()
        
        # Weight painting options
        box = layout.box()
        box.label(text="Weight Painting", icon='WPAINT_HLT')
        col = box.column(align=True)
        
        col.prop(settings, "weight_method")
        col.separator()
        
        col.prop(settings, "smooth_weights", toggle=True)
        if settings.smooth_weights:
            col.prop(settings, "smooth_iterations")
        
        col.prop(settings, "validate_weights", toggle=True)


class VIEW3D_PT_auto_rig_advanced(Panel):
    """Advanced options panel"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Auto Rig'
    bl_label = "Advanced Options"
    bl_idname = "VIEW3D_PT_auto_rig_advanced"
    bl_parent_id = "VIEW3D_PT_auto_rig_main"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.auto_rig_settings
        
        # Symmetry detection
        box = layout.box()
        box.label(text="Symmetry", icon='MOD_MIRROR')
        col = box.column(align=True)
        
        col.prop(settings, "detect_symmetry", toggle=True)
        if settings.detect_symmetry:
            col.prop(settings, "symmetry_tolerance")
        
        layout.separator()
        
        # Generation options
        box = layout.box()
        box.label(text="Generation Options", icon='PREFERENCES')
        col = box.column(align=True)
        
        col.prop(settings, "preserve_original", toggle=True)
        col.prop(settings, "auto_generate_poses", toggle=True)
