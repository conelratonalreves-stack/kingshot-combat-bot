"""
Mesh Analyzer for Auto Rigger
Analyzes mesh geometry to detect body parts, landmarks, and symmetry.
"""

import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree


class MeshAnalyzer:
    """Analyzes mesh geometry for automatic rigging"""
    
    def __init__(self, mesh_obj):
        """
        Initialize analyzer with mesh object
        
        Args:
            mesh_obj: Blender mesh object to analyze
        """
        self.mesh_obj = mesh_obj
        self.mesh = mesh_obj.data
        self.landmarks = {}
        self.symmetry_plane = None
        
    def detect_landmarks(self):
        """
        Detect key body landmarks on the mesh
        
        Returns:
            dict: Dictionary of landmark positions
        """
        # Get world matrix for transformations
        world_matrix = self.mesh_obj.matrix_world
        
        # Get all vertex positions in world space
        vertices = [world_matrix @ v.co for v in self.mesh.vertices]
        
        if len(vertices) == 0:
            return None
        
        # Convert to numpy for easier calculations
        verts_np = np.array([(v.x, v.y, v.z) for v in vertices])
        
        # Detect key landmarks
        self.landmarks = {}
        
        # 1. Find extremes
        # Highest point (head top)
        max_z_idx = np.argmax(verts_np[:, 2])
        self.landmarks['head_top'] = vertices[max_z_idx]
        
        # Lowest points (feet)
        min_z = np.min(verts_np[:, 2])
        foot_threshold = min_z + 0.1  # 10cm above lowest point
        foot_verts = verts_np[verts_np[:, 2] < foot_threshold]
        
        if len(foot_verts) > 0:
            # Find left and right foot (assuming X is left-right)
            left_foot_idx = np.argmin(foot_verts[:, 0])
            right_foot_idx = np.argmax(foot_verts[:, 0])
            
            self.landmarks['foot_left'] = Vector(foot_verts[left_foot_idx])
            self.landmarks['foot_right'] = Vector(foot_verts[right_foot_idx])
        
        # 2. Find hands (outermost points on Y axis)
        # Filter vertices around middle height (likely arms)
        z_min, z_max = np.min(verts_np[:, 2]), np.max(verts_np[:, 2])
        z_mid = (z_min + z_max) * 0.5
        z_range = z_max - z_min
        
        arm_z_min = z_mid - z_range * 0.15
        arm_z_max = z_mid + z_range * 0.25
        
        arm_verts_mask = (verts_np[:, 2] > arm_z_min) & (verts_np[:, 2] < arm_z_max)
        arm_verts = verts_np[arm_verts_mask]
        
        if len(arm_verts) > 0:
            # Find extremes on Y axis (front-back in Blender default)
            # Or X axis if using different orientation
            # Let's check which axis has more spread
            x_range = np.max(arm_verts[:, 0]) - np.min(arm_verts[:, 0])
            y_range = np.max(arm_verts[:, 1]) - np.min(arm_verts[:, 1])
            
            if x_range > y_range:
                # Arms extend on X axis
                left_hand_idx = np.argmin(arm_verts[:, 0])
                right_hand_idx = np.argmax(arm_verts[:, 0])
                self.landmarks['hand_left'] = Vector(arm_verts[left_hand_idx])
                self.landmarks['hand_right'] = Vector(arm_verts[right_hand_idx])
            else:
                # Arms extend on Y axis
                front_hand_idx = np.argmax(arm_verts[:, 1])
                back_hand_idx = np.argmin(arm_verts[:, 1])
                # Determine which is left/right based on X position
                front_pos = arm_verts[front_hand_idx]
                back_pos = arm_verts[back_hand_idx]
                
                if abs(front_pos[0]) > abs(back_pos[0]):
                    if front_pos[0] < 0:
                        self.landmarks['hand_left'] = Vector(front_pos)
                        self.landmarks['hand_right'] = Vector(back_pos)
                    else:
                        self.landmarks['hand_right'] = Vector(front_pos)
                        self.landmarks['hand_left'] = Vector(back_pos)
        
        # 3. Find center points (hips, spine)
        # Center of bottom third (hips)
        hip_z_max = z_min + z_range * 0.35
        hip_verts_mask = (verts_np[:, 2] > z_min) & (verts_np[:, 2] < hip_z_max)
        hip_verts = verts_np[hip_verts_mask]
        
        if len(hip_verts) > 0:
            hip_center = np.mean(hip_verts, axis=0)
            self.landmarks['hips'] = Vector(hip_center)
        
        # Spine points
        spine_z_min = z_min + z_range * 0.35
        spine_z_max = z_max - z_range * 0.25
        
        # Detect center line vertices for spine
        center_tolerance = np.std(verts_np[:, 0]) * 0.5  # Dynamic tolerance
        center_verts_mask = (np.abs(verts_np[:, 0]) < center_tolerance) & \
                           (verts_np[:, 2] > spine_z_min) & \
                           (verts_np[:, 2] < spine_z_max)
        center_verts = verts_np[center_verts_mask]
        
        if len(center_verts) > 0:
            # Find center at different heights for spine
            spine_bottom = np.mean(center_verts[center_verts[:, 2] < spine_z_min + z_range * 0.15], axis=0)
            spine_mid = np.mean(center_verts, axis=0)
            spine_top = np.mean(center_verts[center_verts[:, 2] > spine_z_max - z_range * 0.1], axis=0)
            
            self.landmarks['spine_bottom'] = Vector(spine_bottom)
            self.landmarks['spine_mid'] = Vector(spine_mid)
            self.landmarks['chest'] = Vector(spine_top)
        
        # 4. Neck detection (narrowing before head)
        neck_z_min = z_max - z_range * 0.25
        neck_z_max = z_max - z_range * 0.15
        
        neck_verts_mask = (verts_np[:, 2] > neck_z_min) & (verts_np[:, 2] < neck_z_max)
        neck_verts = verts_np[neck_verts_mask]
        
        if len(neck_verts) > 0:
            neck_center = np.mean(neck_verts, axis=0)
            self.landmarks['neck'] = Vector(neck_center)
        
        # 5. Head center (between neck and top)
        if 'neck' in self.landmarks and 'head_top' in self.landmarks:
            head_pos = (self.landmarks['neck'] + self.landmarks['head_top']) * 0.5
            self.landmarks['head'] = head_pos
        
        # 6. Shoulder positions (wider points near chest)
        if 'chest' in self.landmarks:
            chest_z = self.landmarks['chest'].z
            shoulder_z_range = z_range * 0.05
            
            shoulder_verts_mask = (verts_np[:, 2] > chest_z - shoulder_z_range) & \
                                 (verts_np[:, 2] < chest_z + shoulder_z_range)
            shoulder_verts = verts_np[shoulder_verts_mask]
            
            if len(shoulder_verts) > 0:
                # Find outermost points on X axis
                left_shoulder_idx = np.argmin(shoulder_verts[:, 0])
                right_shoulder_idx = np.argmax(shoulder_verts[:, 0])
                
                self.landmarks['shoulder_left'] = Vector(shoulder_verts[left_shoulder_idx])
                self.landmarks['shoulder_right'] = Vector(shoulder_verts[right_shoulder_idx])
        
        return self.landmarks
    
    def detect_symmetry(self, tolerance=0.001):
        """
        Detect if mesh is symmetric and find symmetry plane
        
        Args:
            tolerance: Tolerance for symmetry detection
            
        Returns:
            tuple: (is_symmetric, plane_axis) where plane_axis is 'X', 'Y', or 'Z'
        """
        vertices = [self.mesh_obj.matrix_world @ v.co for v in self.mesh.vertices]
        verts_np = np.array([(v.x, v.y, v.z) for v in vertices])
        
        # Check each axis for symmetry
        for axis_idx, axis_name in enumerate(['X', 'Y', 'Z']):
            # Mirror vertices across the axis
            mirrored = verts_np.copy()
            mirrored[:, axis_idx] *= -1
            
            # Build KDTree for fast nearest neighbor search
            kd = KDTree(len(vertices))
            for i, v in enumerate(vertices):
                kd.insert(v, i)
            kd.balance()
            
            # Check if each mirrored vertex has a close match
            symmetric_count = 0
            for mir_v in mirrored:
                co, index, dist = kd.find(Vector(mir_v))
                if dist < tolerance:
                    symmetric_count += 1
            
            # If most vertices are symmetric (>90%), consider it symmetric
            symmetry_ratio = symmetric_count / len(vertices)
            if symmetry_ratio > 0.9:
                self.symmetry_plane = axis_name
                return True, axis_name
        
        return False, None
    
    def get_mesh_bounds(self):
        """Get bounding box of the mesh"""
        world_matrix = self.mesh_obj.matrix_world
        vertices = [world_matrix @ v.co for v in self.mesh.vertices]
        
        if not vertices:
            return None
        
        verts_np = np.array([(v.x, v.y, v.z) for v in vertices])
        
        min_bound = Vector(np.min(verts_np, axis=0))
        max_bound = Vector(np.max(verts_np, axis=0))
        center = (min_bound + max_bound) * 0.5
        size = max_bound - min_bound
        
        return {
            'min': min_bound,
            'max': max_bound,
            'center': center,
            'size': size,
        }
    
    def estimate_body_type(self):
        """
        Estimate body type from proportions
        
        Returns:
            str: Estimated body type ('MALE', 'FEMALE', 'CHILD', 'STYLIZED')
        """
        if not self.landmarks:
            self.detect_landmarks()
        
        bounds = self.get_mesh_bounds()
        if not bounds:
            return 'MALE'  # Default
        
        height = bounds['size'].z
        
        # Calculate proportions
        if 'head_top' in self.landmarks and 'hips' in self.landmarks:
            head_height = self.landmarks['head_top'].z - self.landmarks['neck'].z if 'neck' in self.landmarks else height * 0.12
            head_to_body_ratio = head_height / height
            
            # Child detection (larger head ratio)
            if head_to_body_ratio > 0.16:
                return 'CHILD'
            
            # Stylized detection (exaggerated proportions)
            if head_to_body_ratio > 0.14 or head_to_body_ratio < 0.10:
                return 'STYLIZED'
        
        # Check shoulder to hip ratio for male/female
        if 'shoulder_left' in self.landmarks and 'shoulder_right' in self.landmarks:
            shoulder_width = (self.landmarks['shoulder_right'] - self.landmarks['shoulder_left']).length
            
            # Estimate hip width from lower body
            if 'hips' in self.landmarks:
                hip_verts_z = self.landmarks['hips'].z
                z_tolerance = height * 0.05
                
                # Get vertices near hip height
                verts_np = np.array([(self.mesh_obj.matrix_world @ v.co).x 
                                    for v in self.mesh.vertices 
                                    if abs((self.mesh_obj.matrix_world @ v.co).z - hip_verts_z) < z_tolerance])
                
                if len(verts_np) > 0:
                    hip_width = np.max(verts_np) - np.min(verts_np)
                    
                    # Female typically has hip_width >= shoulder_width
                    if hip_width >= shoulder_width * 0.95:
                        return 'FEMALE'
        
        return 'MALE'  # Default
