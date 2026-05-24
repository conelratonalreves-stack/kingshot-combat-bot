"""
Operators for Auto Rigger addon
Main operations for rig generation and landmark detection.
"""

import bpy
from bpy.types import Operator
from bpy.props import BoolProperty
import time

from . import mesh_analyzer
from . import rig_generator
from . import weight_painter


class OBJECT_OT_auto_rig_detect_landmarks(Operator):
    """Detect body landmarks on the selected mesh"""
    bl_idname = "object.auto_rig_detect_landmarks"
    bl_label = "Detect Landmarks"
    bl_description = "Analyze mesh geometry to detect body parts"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        """Check if operator can run"""
        settings = context.scene.auto_rig_settings
        return (settings.target_mesh is not None and 
                settings.target_mesh.type == 'MESH')
    
    def execute(self, context):
        """Execute landmark detection"""
        settings = context.scene.auto_rig_settings
        mesh_obj = settings.target_mesh
        
        try:
            self.report({'INFO'}, f"Analyzing mesh: {mesh_obj.name}")
            
            # Perform landmark detection
            analyzer = mesh_analyzer.MeshAnalyzer(mesh_obj)
            landmarks = analyzer.detect_landmarks()
            
            # Store results (you could add these to properties if needed)
            if landmarks:
                settings.landmarks_detected = True
                
                # Report findings
                parts_found = len(landmarks)
                self.report({'INFO'}, 
                          f"✓ Detected {parts_found} body landmarks")
                
                # Check symmetry if enabled
                if settings.detect_symmetry:
                    is_symmetric, symmetry_plane = analyzer.detect_symmetry(
                        tolerance=settings.symmetry_tolerance
                    )
                    if is_symmetric:
                        self.report({'INFO'}, 
                                  f"✓ Symmetry detected on {symmetry_plane} axis")
                    else:
                        self.report({'WARNING'}, 
                                  "⚠ Mesh is not symmetric (may affect results)")
                
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, 
                          "Failed to detect body parts. Ensure mesh is a humanoid character")
                return {'CANCELLED'}
                
        except Exception as e:
            self.report({'ERROR'}, f"Landmark detection failed: {str(e)}")
            return {'CANCELLED'}


class OBJECT_OT_auto_rig_generate(Operator):
    """Generate automatic rig for the selected mesh"""
    bl_idname = "object.auto_rig_generate"
    bl_label = "Generate Auto Rig"
    bl_description = "Automatically generate rigged skeleton for humanoid character"
    bl_options = {'REGISTER', 'UNDO'}
    
    # Option to show dialog
    show_dialog: BoolProperty(
        name="Show Confirmation",
        default=False
    )
    
    @classmethod
    def poll(cls, context):
        """Check if operator can run"""
        settings = context.scene.auto_rig_settings
        return (settings.target_mesh is not None and 
                settings.target_mesh.type == 'MESH')
    
    def execute(self, context):
        """Execute rig generation"""
        settings = context.scene.auto_rig_settings
        mesh_obj = settings.target_mesh
        
        start_time = time.time()
        settings.generation_progress = 0.0
        
        try:
            # Step 1: Analyze mesh (10%)
            self.report({'INFO'}, "Step 1/5: Analyzing mesh geometry...")
            settings.generation_progress = 10.0
            
            analyzer = mesh_analyzer.MeshAnalyzer(mesh_obj)
            landmarks = analyzer.detect_landmarks()
            
            if not landmarks:
                raise Exception("Failed to detect body landmarks")
            
            # Check symmetry
            if settings.detect_symmetry:
                is_symmetric, symmetry_plane = analyzer.detect_symmetry(
                    tolerance=settings.symmetry_tolerance
                )
                if not is_symmetric:
                    self.report({'WARNING'}, 
                              "Mesh is not symmetric. Results may vary.")
            
            # Step 2: Duplicate mesh if preserving original (20%)
            settings.generation_progress = 20.0
            
            if settings.preserve_original:
                self.report({'INFO'}, "Step 2/5: Duplicating mesh...")
                # Duplicate the mesh
                bpy.ops.object.select_all(action='DESELECT')
                mesh_obj.select_set(True)
                context.view_layer.objects.active = mesh_obj
                bpy.ops.object.duplicate()
                working_mesh = context.active_object
                working_mesh.name = f"{mesh_obj.name}_Rigged"
            else:
                working_mesh = mesh_obj
            
            # Step 3: Generate skeleton (40%)
            self.report({'INFO'}, "Step 3/5: Generating skeleton...")
            settings.generation_progress = 40.0
            
            generator = rig_generator.RigGenerator(
                working_mesh,
                landmarks,
                settings
            )
            armature = generator.generate_rig()
            
            if not armature:
                raise Exception("Failed to generate armature")
            
            # Step 4: Apply weight painting (70%)
            self.report({'INFO'}, "Step 4/5: Applying automatic weights...")
            settings.generation_progress = 70.0
            
            painter = weight_painter.WeightPainter(
                working_mesh,
                armature,
                settings
            )
            painter.apply_weights()
            
            # Step 5: Finalize (90%)
            self.report({'INFO'}, "Step 5/5: Finalizing rig...")
            settings.generation_progress = 90.0
            
            # Parent mesh to armature
            bpy.ops.object.select_all(action='DESELECT')
            working_mesh.select_set(True)
            armature.select_set(True)
            context.view_layer.objects.active = armature
            
            # Add armature modifier if not exists
            if not any(mod.type == 'ARMATURE' for mod in working_mesh.modifiers):
                mod = working_mesh.modifiers.new(name="Armature", type='ARMATURE')
                mod.object = armature
            
            # Generate poses if requested
            if settings.auto_generate_poses:
                generator.create_default_poses(armature)
            
            # Complete!
            settings.generation_progress = 100.0
            elapsed = time.time() - start_time
            
            self.report({'INFO'}, 
                       f"✓ Rig generated successfully in {elapsed:.1f}s!")
            
            # Select the armature
            bpy.ops.object.select_all(action='DESELECT')
            armature.select_set(True)
            context.view_layer.objects.active = armature
            
            # Reset progress after a moment
            settings.generation_progress = 0.0
            
            return {'FINISHED'}
            
        except Exception as e:
            settings.generation_progress = 0.0
            self.report({'ERROR'}, f"Rig generation failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        """Show confirmation dialog if requested"""
        if self.show_dialog:
            return context.window_manager.invoke_props_dialog(self)
        else:
            return self.execute(context)
    
    def draw(self, context):
        """Draw confirmation dialog"""
        layout = self.layout
        layout.label(text="Generate automatic rig?")
        layout.label(text="This may take a moment...")
