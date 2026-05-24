"""
Weight Painter for Auto Rigger
Applies automatic weight painting to rigged meshes.
"""

import bpy
import bmesh
import numpy as np
from mathutils import Vector


class WeightPainter:
    """Handles automatic weight painting for rigged characters"""
    
    def __init__(self, mesh_obj, armature_obj, settings):
        """
        Initialize weight painter
        
        Args:
            mesh_obj: Mesh object to paint weights on
            armature_obj: Armature object with bones
            settings: Auto rig settings
        """
        self.mesh_obj = mesh_obj
        self.armature_obj = armature_obj
        self.settings = settings
        self.mesh = mesh_obj.data
    
    def apply_weights(self):
        """Apply automatic weights to the mesh"""
        method = self.settings.weight_method
        
        if method == 'AUTOMATIC':
            self._apply_automatic_weights()
        elif method == 'HEAT':
            self._apply_heat_weights()
        elif method == 'DISTANCE':
            self._apply_distance_weights()
        elif method == 'ENVELOPE':
            self._apply_envelope_weights()
        
        # Smooth weights if enabled
        if self.settings.smooth_weights:
            self._smooth_weights()
        
        # Validate weights if enabled
        if self.settings.validate_weights:
            issues = self._validate_weights()
            if issues:
                print(f"Weight validation found {len(issues)} issues")
    
    def _apply_automatic_weights(self):
        """Use Blender's automatic weights"""
        # Select mesh and armature
        bpy.ops.object.select_all(action='DESELECT')
        self.mesh_obj.select_set(True)
        self.armature_obj.select_set(True)
        bpy.context.view_layer.objects.active = self.armature_obj
        
        # Parent with automatic weights
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    
    def _apply_heat_weights(self):
        """Use heat diffusion method for weights (better quality)"""
        # First apply automatic weights as base
        self._apply_automatic_weights()
        
        # Heat diffusion is built into automatic weights in Blender
        # For custom implementation, would need complex heat diffusion algorithm
        pass
    
    def _apply_distance_weights(self):
        """Apply weights based on distance to bones"""
        # Create vertex groups for each bone
        bone_names = [bone.name for bone in self.armature_obj.data.bones]
        
        # Clear existing vertex groups
        self.mesh_obj.vertex_groups.clear()
        
        # Create vertex groups
        vgroups = {}
        for bone_name in bone_names:
            vgroup = self.mesh_obj.vertex_groups.new(name=bone_name)
            vgroups[bone_name] = vgroup
        
        # Get bone positions in world space
        bone_positions = {}
        bone_directions = {}
        
        for bone in self.armature_obj.data.bones:
            # Get head and tail in world space
            head = self.armature_obj.matrix_world @ bone.head_local
            tail = self.armature_obj.matrix_world @ bone.tail_local
            
            bone_positions[bone.name] = (head, tail)
            bone_directions[bone.name] = (tail - head).normalized()
        
        # Calculate weights for each vertex
        mesh_matrix = self.mesh_obj.matrix_world
        
        for vert_idx, vert in enumerate(self.mesh.vertices):
            vert_world = mesh_matrix @ vert.co
            
            # Calculate distance to each bone
            distances = {}
            
            for bone_name, (head, tail) in bone_positions.items():
                # Distance to bone axis (line segment)
                bone_vec = tail - head
                bone_length = bone_vec.length
                
                if bone_length > 0:
                    # Project vertex onto bone axis
                    vert_vec = vert_world - head
                    projection = vert_vec.dot(bone_vec) / bone_length
                    
                    # Clamp to bone segment
                    projection = max(0, min(1, projection / bone_length))
                    
                    # Closest point on bone
                    closest_point = head + bone_vec * projection
                    
                    # Distance to closest point
                    dist = (vert_world - closest_point).length
                    distances[bone_name] = dist
            
            # Convert distances to weights (inverse distance with falloff)
            weights = {}
            total_weight = 0.0
            
            for bone_name, dist in distances.items():
                # Inverse distance with falloff
                if dist < 0.001:
                    weight = 1.0
                else:
                    weight = 1.0 / (dist * dist)  # Quadratic falloff
                
                weights[bone_name] = weight
                total_weight += weight
            
            # Normalize weights
            if total_weight > 0:
                # Keep only top 4 influences (standard for games)
                sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:4]
                
                # Renormalize
                top_total = sum(w for _, w in sorted_weights)
                
                for bone_name, weight in sorted_weights:
                    normalized_weight = weight / top_total
                    
                    if normalized_weight > 0.01:  # Minimum threshold
                        vgroups[bone_name].add([vert_idx], normalized_weight, 'REPLACE')
    
    def _apply_envelope_weights(self):
        """Use bone envelope method"""
        # Select mesh and armature
        bpy.ops.object.select_all(action='DESELECT')
        self.mesh_obj.select_set(True)
        self.armature_obj.select_set(True)
        bpy.context.view_layer.objects.active = self.armature_obj
        
        # Parent with envelope weights
        bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')
    
    def _smooth_weights(self):
        """Smooth weight transitions"""
        # Select mesh
        bpy.ops.object.select_all(action='DESELECT')
        self.mesh_obj.select_set(True)
        bpy.context.view_layer.objects.active = self.mesh_obj
        
        # Enter weight paint mode
        bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
        
        # Select all vertices
        bpy.ops.paint.vert_select_all(action='SELECT')
        
        # Smooth weights
        for _ in range(self.settings.smooth_iterations):
            bpy.ops.object.vertex_group_smooth(
                group_select_mode='ALL',
                factor=0.5,
                repeat=1
            )
        
        # Return to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
    
    def _validate_weights(self):
        """
        Validate weight quality
        
        Returns:
            list: List of issues found
        """
        issues = []
        
        # Check each vertex
        for vert_idx, vert in enumerate(self.mesh.vertices):
            # Get all weights for this vertex
            total_weight = 0.0
            weight_count = 0
            
            for group in vert.groups:
                total_weight += group.weight
                weight_count += 1
            
            # Check for unweighted vertices
            if weight_count == 0:
                issues.append({
                    'type': 'UNWEIGHTED',
                    'vertex': vert_idx,
                    'message': f"Vertex {vert_idx} has no weights"
                })
            
            # Check for incorrect normalization
            elif abs(total_weight - 1.0) > 0.01:
                issues.append({
                    'type': 'UNNORMALIZED',
                    'vertex': vert_idx,
                    'total': total_weight,
                    'message': f"Vertex {vert_idx} weights sum to {total_weight:.3f}"
                })
        
        return issues
    
    def highlight_problem_areas(self, issues):
        """
        Highlight vertices with weight problems
        
        Args:
            issues: List of weight issues
        """
        # Create a vertex group for problem areas
        if "Weight_Issues" in self.mesh_obj.vertex_groups:
            problem_group = self.mesh_obj.vertex_groups["Weight_Issues"]
        else:
            problem_group = self.mesh_obj.vertex_groups.new(name="Weight_Issues")
        
        # Add problem vertices to group
        for issue in issues:
            if 'vertex' in issue:
                problem_group.add([issue['vertex']], 1.0, 'REPLACE')
