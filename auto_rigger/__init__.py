"""
Auto Rigger - Automatic Humanoid Rigging for Blender
Automatically generates rigged skeletons for humanoid 3D models with automatic geometry detection.
"""

bl_info = {
    "name": "Auto Rigger",
    "author": "Auto Rigger Team",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Auto Rig",
    "description": "Automatic rigging for humanoid characters with geometry detection",
    "category": "Rigging",
    "doc_url": "https://github.com/yourusername/auto-rigger",
    "tracker_url": "https://github.com/yourusername/auto-rigger/issues",
}

import bpy
from . import properties
from . import operators
from . import panels

# List of classes to register
classes = (
    properties.AutoRigSettings,
    operators.OBJECT_OT_auto_rig_generate,
    operators.OBJECT_OT_auto_rig_detect_landmarks,
    panels.VIEW3D_PT_auto_rig_main,
    panels.VIEW3D_PT_auto_rig_settings,
    panels.VIEW3D_PT_auto_rig_advanced,
)


def register():
    """Register addon classes and properties"""
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Add custom properties to Scene
    bpy.types.Scene.auto_rig_settings = bpy.props.PointerProperty(
        type=properties.AutoRigSettings
    )
    
    print("Auto Rigger addon registered successfully")


def unregister():
    """Unregister addon classes and properties"""
    # Remove custom properties
    del bpy.types.Scene.auto_rig_settings
    
    # Unregister classes in reverse order
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    print("Auto Rigger addon unregistered")


if __name__ == "__main__":
    register()
