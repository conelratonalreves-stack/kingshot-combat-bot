"""
Rig Generator for Auto Rigger
Creates armature skeleton with bones, constraints, and controls.
"""

import bpy
import bmesh
from mathutils import Vector, Matrix
import math


class RigGenerator:
    """Generates rigged armature from mesh landmarks"""
    
    # Naming convention mappings
    BONE_NAMES = {
        'MIXAMO': {
            'root': 'Hips',
            'spine': ['Spine', 'Spine1', 'Spine2'],
            'neck': 'Neck',
            'head': 'Head',
            'shoulder_l': 'LeftShoulder',
            'shoulder_r': 'RightShoulder',
            'upper_arm_l': 'LeftArm',
            'upper_arm_r': 'RightArm',
            'forearm_l': 'LeftForeArm',
            'forearm_r': 'RightForeArm',
            'hand_l': 'LeftHand',
            'hand_r': 'RightHand',
            'thigh_l': 'LeftUpLeg',
            'thigh_r': 'RightUpLeg',
            'shin_l': 'LeftLeg',
            'shin_r': 'RightLeg',
            'foot_l': 'LeftFoot',
            'foot_r': 'RightFoot',
            'toe_l': 'LeftToeBase',
            'toe_r': 'RightToeBase',
        },
        'UNREAL': {
            'root': 'root',
            'spine': ['pelvis', 'spine_01', 'spine_02', 'spine_03'],
            'neck': 'neck_01',
            'head': 'head',
            'shoulder_l': 'clavicle_l',
            'shoulder_r': 'clavicle_r',
            'upper_arm_l': 'upperarm_l',
            'upper_arm_r': 'upperarm_r',
            'forearm_l': 'lowerarm_l',
            'forearm_r': 'lowerarm_r',
            'hand_l': 'hand_l',
            'hand_r': 'hand_r',
            'thigh_l': 'thigh_l',
            'thigh_r': 'thigh_r',
            'shin_l': 'calf_l',
            'shin_r': 'calf_r',
            'foot_l': 'foot_l',
            'foot_r': 'foot_r',
            'toe_l': 'ball_l',
            'toe_r': 'ball_r',
        },
        'UNITY': {
            'root': 'Hips',
            'spine': ['Spine', 'Chest', 'UpperChest'],
            'neck': 'Neck',
            'head': 'Head',
            'shoulder_l': 'LeftShoulder',
            'shoulder_r': 'RightShoulder',
            'upper_arm_l': 'LeftUpperArm',
            'upper_arm_r': 'RightUpperArm',
            'forearm_l': 'LeftLowerArm',
            'forearm_r': 'RightLowerArm',
            'hand_l': 'LeftHand',
            'hand_r': 'RightHand',
            'thigh_l': 'LeftUpperLeg',
            'thigh_r': 'RightUpperLeg',
            'shin_l': 'LeftLowerLeg',
            'shin_r': 'RightLowerLeg',
            'foot_l': 'LeftFoot',
            'foot_r': 'RightFoot',
            'toe_l': 'LeftToes',
            'toe_r': 'RightToes',
        },
        'RIGIFY': {
            'root': 'spine',
            'spine': ['spine.001', 'spine.002', 'spine.003'],
            'neck': 'spine.004',
            'head': 'spine.006',
            'shoulder_l': 'shoulder.L',
            'shoulder_r': 'shoulder.R',
            'upper_arm_l': 'upper_arm.L',
            'upper_arm_r': 'upper_arm.R',
            'forearm_l': 'forearm.L',
            'forearm_r': 'forearm.R',
            'hand_l': 'hand.L',
            'hand_r': 'hand.R',
            'thigh_l': 'thigh.L',
            'thigh_r': 'thigh.R',
            'shin_l': 'shin.L',
            'shin_r': 'shin.R',
            'foot_l': 'foot.L',
            'foot_r': 'foot.R',
            'toe_l': 'toe.L',
            'toe_r': 'toe.R',
        },
    }
    
    def __init__(self, mesh_obj, landmarks, settings):
        """
        Initialize rig generator
        
        Args:
            mesh_obj: Target mesh object
            landmarks: Dict of detected body landmarks
            settings: Auto rig settings from properties
        """
        self.mesh_obj = mesh_obj
        self.landmarks = landmarks
        self.settings = settings
        self.armature = None
        self.bones = {}  # Store bone references
        self.naming = self.BONE_NAMES.get(settings.bone_naming, self.BONE_NAMES['MIXAMO'])
    
    def generate_rig(self):
        """
        Generate complete armature rig
        
        Returns:
            bpy.types.Object: Generated armature object
        """
        if self.settings.rig_source == 'RIGIFY_HUMAN':
            return self._generate_rigify_metarig()

        # Create armature
        armature_data = bpy.data.armatures.new(name=f"{self.mesh_obj.name}_Armature")
        armature_obj = bpy.data.objects.new(name=f"{self.mesh_obj.name}_Rig", object_data=armature_data)
        
        # Link to scene
        bpy.context.collection.objects.link(armature_obj)
        
        # Set as active and enter edit mode
        bpy.context.view_layer.objects.active = armature_obj
        bpy.ops.object.mode_set(mode='EDIT')
        
        self.armature = armature_obj
        
        # Generate bone structure
        self._create_spine_bones()
        self._create_leg_bones()
        self._create_arm_bones()
        
        # Exit edit mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Setup constraints if needed
        if self.settings.rig_type in ['STANDARD', 'ADVANCED']:
            self._setup_constraints()
        
        # Create control bones if advanced
        if self.settings.rig_type == 'ADVANCED':
            self._create_control_bones()
        
        return armature_obj

    def _generate_rigify_metarig(self):
        """Generate and fit Blender Rigify human meta-rig to the mesh"""
        # Ensure Rigify addon is enabled
        if "rigify" not in bpy.context.preferences.addons:
            try:
                bpy.ops.preferences.addon_enable(module="rigify")
            except Exception as exc:
                raise Exception("Rigify addon is not available or could not be enabled") from exc

        # Create Rigify human meta-rig
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.armature_human_metarig_add()
        armature_obj = bpy.context.active_object
        armature_obj.name = f"{self.mesh_obj.name}_metarig"

        # Align armature to mesh transform
        armature_obj.matrix_world = self.mesh_obj.matrix_world.copy()

        # Fit bones to landmarks
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = armature_obj.data.edit_bones
        inv_matrix = armature_obj.matrix_world.inverted()

        def to_local(world_vec):
            return inv_matrix @ world_vec

        def set_bone_head_tail(bone_name, head, tail):
            if bone_name in edit_bones and head and tail:
                bone = edit_bones[bone_name]
                bone.head = to_local(head)
                bone.tail = to_local(tail)

        # Spine chain (Rigify uses spine, spine.001, spine.002, ...)
        spine_bone_names = [b.name for b in edit_bones if b.name.startswith("spine")]
        spine_bone_names.sort()

        if 'hips' in self.landmarks and 'chest' in self.landmarks:
            hips = self.landmarks['hips']
            chest = self.landmarks['chest']
            spine_count = max(1, len(spine_bone_names))

            spine_points = [hips + (chest - hips) * (i / spine_count) for i in range(spine_count + 1)]

            for i, bone_name in enumerate(spine_bone_names):
                if i + 1 < len(spine_points):
                    set_bone_head_tail(bone_name, spine_points[i], spine_points[i + 1])

        # Neck and head (Rigify uses spine.004/spine.005/spine.006 in many cases)
        if 'neck' in self.landmarks and 'head_top' in self.landmarks:
            neck = self.landmarks['neck']
            head_top = self.landmarks['head_top']

            for name in ["spine.004", "spine.005"]:
                if name in edit_bones:
                    set_bone_head_tail(name, neck, head_top)
                    break

            if "spine.006" in edit_bones:
                set_bone_head_tail("spine.006", neck, head_top)

        # Shoulders, arms, hands
        for side, suffix in [("left", ".L"), ("right", ".R")]:
            shoulder_key = f"shoulder_{side}"
            hand_key = f"hand_{side}"

            if shoulder_key in self.landmarks and hand_key in self.landmarks:
                shoulder = self.landmarks[shoulder_key]
                hand = self.landmarks[hand_key]
                elbow = (shoulder + hand) * 0.5
                elbow.y += (hand - shoulder).length * 0.05

                set_bone_head_tail(f"upper_arm{suffix}", shoulder, elbow)
                set_bone_head_tail(f"forearm{suffix}", elbow, hand)

                # Hand tail extend
                hand_dir = (hand - elbow).normalized()
                hand_tail = hand + hand_dir * (hand - elbow).length * 0.12
                set_bone_head_tail(f"hand{suffix}", hand, hand_tail)

        # Legs, feet, toes
        for side, suffix in [("left", ".L"), ("right", ".R")]:
            foot_key = f"foot_{side}"

            if 'hips' in self.landmarks and foot_key in self.landmarks:
                hip = self.landmarks['hips']
                foot = self.landmarks[foot_key]
                knee = (hip + foot) * 0.5
                knee.y += (foot - hip).length * 0.05

                set_bone_head_tail(f"thigh{suffix}", hip, knee)
                set_bone_head_tail(f"shin{suffix}", knee, foot)

                foot_tail = foot + Vector((0, (foot - hip).length * 0.15, 0))
                set_bone_head_tail(f"foot{suffix}", foot, foot_tail)
                set_bone_head_tail(f"toe{suffix}", foot_tail, foot_tail + Vector((0, (foot - hip).length * 0.08, 0)))

        bpy.ops.object.mode_set(mode='OBJECT')

        # Optionally generate Rigify control rig
        if self.settings.rigify_generate_controls:
            bpy.context.view_layer.objects.active = armature_obj
            bpy.ops.object.mode_set(mode='POSE')
            try:
                bpy.ops.pose.rigify_generate()
            except Exception as exc:
                bpy.ops.object.mode_set(mode='OBJECT')
                raise Exception("Rigify control generation failed") from exc
            bpy.ops.object.mode_set(mode='OBJECT')

        return armature_obj
    
    def _create_spine_bones(self):
        """Create spine, neck, and head bones"""
        armature_data = self.armature.data
        
        # Root bone (Hips)
        if 'hips' in self.landmarks:
            root_bone = armature_data.edit_bones.new(self.naming['root'])
            hips_pos = self.landmarks['hips']
            
            # Root bone from hips downward
            root_bone.head = hips_pos
            root_bone.tail = hips_pos - Vector((0, 0, 0.1))  # Small downward
            
            self.bones['root'] = root_bone
        
        # Spine bones
        spine_positions = []
        if 'hips' in self.landmarks:
            spine_positions.append(self.landmarks['hips'])
        if 'spine_bottom' in self.landmarks:
            spine_positions.append(self.landmarks['spine_bottom'])
        if 'spine_mid' in self.landmarks:
            spine_positions.append(self.landmarks['spine_mid'])
        if 'chest' in self.landmarks:
            spine_positions.append(self.landmarks['chest'])
        
        # Create spine bones based on count setting
        spine_count = min(self.settings.spine_bones, len(spine_positions) - 1)
        spine_names = self.naming['spine']
        
        if isinstance(spine_names, list):
            spine_names = spine_names[:spine_count]
        else:
            spine_names = [spine_names]
        
        prev_bone = self.bones.get('root')
        
        for i, spine_name in enumerate(spine_names):
            if i + 1 < len(spine_positions):
                spine_bone = armature_data.edit_bones.new(spine_name)
                spine_bone.head = spine_positions[i]
                spine_bone.tail = spine_positions[i + 1]
                
                if prev_bone:
                    spine_bone.parent = prev_bone
                
                self.bones[f'spine_{i}'] = spine_bone
                prev_bone = spine_bone
        
        # Neck bone
        if 'chest' in self.landmarks and 'neck' in self.landmarks:
            neck_bone = armature_data.edit_bones.new(self.naming['neck'])
            neck_bone.head = self.landmarks['chest']
            neck_bone.tail = self.landmarks['neck']
            
            if prev_bone:
                neck_bone.parent = prev_bone
            
            self.bones['neck'] = neck_bone
            prev_bone = neck_bone
        
        # Head bone
        if 'neck' in self.landmarks and 'head_top' in self.landmarks:
            head_bone = armature_data.edit_bones.new(self.naming['head'])
            head_bone.head = self.landmarks['neck']
            head_bone.tail = self.landmarks['head_top']
            
            if prev_bone:
                head_bone.parent = prev_bone
            
            self.bones['head'] = head_bone
    
    def _create_arm_bones(self):
        """Create arm bones for both sides"""
        armature_data = self.armature.data
        
        for side in ['left', 'right']:
            side_suffix = '_l' if side == 'left' else '_r'
            
            shoulder_key = f'shoulder_{side}'
            hand_key = f'hand_{side}'
            
            if shoulder_key not in self.landmarks or hand_key not in self.landmarks:
                continue
            
            shoulder_pos = self.landmarks[shoulder_key]
            hand_pos = self.landmarks[hand_key]
            
            # Calculate elbow position (midpoint with slight bend)
            elbow_pos = (shoulder_pos + hand_pos) * 0.5
            
            # Add slight bend forward (Y axis)
            arm_length = (hand_pos - shoulder_pos).length
            elbow_pos.y += arm_length * 0.05
            
            # Shoulder/Clavicle bone
            if 'chest' in self.landmarks:
                shoulder_bone = armature_data.edit_bones.new(self.naming[f'shoulder{side_suffix}'])
                chest_pos = self.landmarks['chest']
                
                # From chest to shoulder
                shoulder_bone.head = chest_pos
                shoulder_bone.tail = shoulder_pos
                
                # Parent to upper spine
                if 'spine_2' in self.bones:
                    shoulder_bone.parent = self.bones['spine_2']
                elif 'spine_1' in self.bones:
                    shoulder_bone.parent = self.bones['spine_1']
                
                self.bones[f'shoulder{side_suffix}'] = shoulder_bone
                parent_bone = shoulder_bone
            else:
                parent_bone = None
            
            # Upper arm
            upper_arm = armature_data.edit_bones.new(self.naming[f'upper_arm{side_suffix}'])
            upper_arm.head = shoulder_pos
            upper_arm.tail = elbow_pos
            
            if parent_bone:
                upper_arm.parent = parent_bone
            
            self.bones[f'upper_arm{side_suffix}'] = upper_arm
            
            # Forearm
            forearm = armature_data.edit_bones.new(self.naming[f'forearm{side_suffix}'])
            forearm.head = elbow_pos
            forearm.tail = hand_pos
            forearm.parent = upper_arm
            
            self.bones[f'forearm{side_suffix}'] = forearm
            
            # Hand
            hand = armature_data.edit_bones.new(self.naming[f'hand{side_suffix}'])
            hand.head = hand_pos
            
            # Hand tail extends slightly
            hand_direction = (hand_pos - elbow_pos).normalized()
            hand.tail = hand_pos + hand_direction * (arm_length * 0.08)
            hand.parent = forearm
            
            self.bones[f'hand{side_suffix}'] = hand
    
    def _create_leg_bones(self):
        """Create leg bones for both sides"""
        armature_data = self.armature.data
        
        for side in ['left', 'right']:
            side_suffix = '_l' if side == 'left' else '_r'
            
            foot_key = f'foot_{side}'
            
            if foot_key not in self.landmarks or 'hips' not in self.landmarks:
                continue
            
            hip_pos = self.landmarks['hips']
            foot_pos = self.landmarks[foot_key]
            
            # Calculate knee position (midpoint with slight bend)
            knee_pos = (hip_pos + foot_pos) * 0.5
            
            # Add slight bend forward
            leg_length = (foot_pos - hip_pos).length
            knee_pos.y += leg_length * 0.05
            
            # Thigh
            thigh = armature_data.edit_bones.new(self.naming[f'thigh{side_suffix}'])
            thigh.head = hip_pos
            thigh.tail = knee_pos
            
            # Parent to root
            if 'root' in self.bones:
                thigh.parent = self.bones['root']
            
            self.bones[f'thigh{side_suffix}'] = thigh
            
            # Shin
            shin = armature_data.edit_bones.new(self.naming[f'shin{side_suffix}'])
            shin.head = knee_pos
            shin.tail = foot_pos
            shin.parent = thigh
            
            self.bones[f'shin{side_suffix}'] = shin
            
            # Foot
            foot = armature_data.edit_bones.new(self.naming[f'foot{side_suffix}'])
            foot.head = foot_pos
            
            # Foot tail extends forward
            foot.tail = foot_pos + Vector((0, leg_length * 0.15, 0))
            foot.parent = shin
            
            self.bones[f'foot{side_suffix}'] = foot
            
            # Toe (optional)
            toe = armature_data.edit_bones.new(self.naming[f'toe{side_suffix}'])
            toe.head = foot.tail
            toe.tail = foot.tail + Vector((0, leg_length * 0.08, 0))
            toe.parent = foot
            
            self.bones[f'toe{side_suffix}'] = toe
    
    def _setup_constraints(self):
        """Setup IK constraints for arms and legs"""
        if not self.settings.create_ik:
            return
        
        # Switch to pose mode
        bpy.ops.object.mode_set(mode='POSE')
        
        # Create IK for legs
        for side in ['_l', '_r']:
            shin_name = self.naming[f'shin{side}']
            foot_name = self.naming[f'foot{side}']
            
            if shin_name in self.armature.pose.bones:
                shin_bone = self.armature.pose.bones[shin_name]
                
                # Add IK constraint
                ik_constraint = shin_bone.constraints.new('IK')
                ik_constraint.target = self.armature
                ik_constraint.subtarget = foot_name
                ik_constraint.chain_count = 2  # Thigh + Shin
                
                # Pole target if enabled
                if self.settings.create_pole_targets:
                    # Would create pole target bone here
                    pass
        
        # Create IK for arms
        for side in ['_l', '_r']:
            forearm_name = self.naming[f'forearm{side}']
            hand_name = self.naming[f'hand{side}']
            
            if forearm_name in self.armature.pose.bones:
                forearm_bone = self.armature.pose.bones[forearm_name]
                
                # Add IK constraint
                ik_constraint = forearm_bone.constraints.new('IK')
                ik_constraint.target = self.armature
                ik_constraint.subtarget = hand_name
                ik_constraint.chain_count = 2  # Upper arm + Forearm
        
        # Return to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
    
    def _create_control_bones(self):
        """Create control rig bones (advanced mode)"""
        # This would create additional control bones
        # For now, basic implementation
        pass
    
    def create_default_poses(self, armature_obj):
        """
        Create default poses (T-pose, A-pose, rest pose)
        
        Args:
            armature_obj: Armature object to create poses for
        """
        # Switch to pose mode
        bpy.context.view_layer.objects.active = armature_obj
        bpy.ops.object.mode_set(mode='POSE')
        
        # Create pose library (Blender 4.x uses Action system)
        if not armature_obj.animation_data:
            armature_obj.animation_data_create()
        
        # T-Pose (default is usually already T-pose)
        bpy.ops.pose.select_all(action='SELECT')
        
        # Store rest pose
        bpy.ops.pose.armature_apply(selected=False)
        
        # Return to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
