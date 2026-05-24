# Auto Rigger - Usage Examples

## Example 1: Basic Character Rig

### Scenario
You have a simple humanoid character in T-pose that needs a basic rig for animation.

### Steps

1. **Prepare Your Mesh**
   ```
   - Import your character (File → Import → FBX/OBJ)
   - Ensure character is in T-pose
   - Select the mesh
   - Apply transforms: Ctrl+A → All Transforms
   ```

2. **Open Auto Rig Panel**
   - Press `N` in 3D Viewport
   - Click "Auto Rig" tab

3. **Configure Settings**
   ```
   Target Mesh: [Select your character]
   Body Type: Male (or Female/Child)
   Rig Type: Standard
   Naming: Mixamo
   ```

4. **Generate**
   - Click "Detect Body Parts" (optional but recommended)
   - Click "Generate Rig"
   - Wait 5-10 seconds

5. **Result**
   - Armature created with proper hierarchy
   - Mesh automatically weighted
   - Ready to animate!

### Use Case
Perfect for: Game characters, animation practice, quick prototypes

---

## Example 2: Game-Ready Character (Unreal Engine)

### Scenario
Creating a character rig compatible with Unreal Engine for game development.

### Steps

1. **Import Character**
   - Character should be in A-pose or T-pose
   - Verify proper scale (1.7-2.0 units tall)

2. **Configure for Unreal**
   ```
   Target Mesh: [Your character]
   Body Type: Auto-detect or choose
   Rig Type: Standard
   Naming: Unreal Engine ← Important!
   Weight Method: Heat Diffusion
   ```

3. **Rig Settings**
   ```
   ✓ Create IK Controls
   ✓ Create Pole Targets
   ✓ Smooth Weights
   Spine Bones: 3
   ```

4. **Generate & Export**
   - Generate rig
   - Test animations
   - Export as FBX with:
     - ✓ Selected Objects Only
     - ✓ Apply Transform
     - ✓ Bake Animation (if animated)

5. **Import to Unreal**
   - Import FBX to Unreal Engine
   - Bones automatically map to UE skeleton
   - Retarget animations easily

### Result
Character with Unreal-compatible bone names, ready for game integration.

---

## Example 3: Stylized Character with Fingers

### Scenario
Anime/cartoon character needing detailed control including fingers.

### Steps

1. **Character Setup**
   - Import stylized character (anime, cartoon, etc.)
   - Ensure proportions are correct

2. **Advanced Configuration**
   ```
   Target Mesh: [Character]
   Body Type: Stylized
   Rig Type: Advanced ← For fingers
   Naming: Mixamo or Unity
   ```

3. **Advanced Settings Panel**
   ```
   ✓ Add Fingers
   ✓ Add Twist Bones (for better deformation)
   Spine Bones: 4 (more flexibility)
   ```

4. **Weight Settings**
   ```
   Weight Method: Heat Diffusion
   ✓ Smooth Weights
   Smooth Iterations: 5
   ✓ Validate Weights
   ```

5. **Generate**
   - Detection might take longer due to complexity
   - Finger bones will be created automatically
   - Weight painting for fingers handled automatically

### Result
Fully rigged character with finger controls, perfect for detailed animations.

---

## Example 4: Batch Processing Multiple Characters

### Scenario
You have 10+ characters that all need rigging with the same settings.

### Steps

1. **Prepare All Meshes**
   - Import all characters
   - Ensure all are in same pose
   - Name them clearly (Character_01, Character_02, etc.)

2. **Rig First Character**
   - Use Auto Rigger with your desired settings
   - Test to ensure settings are correct
   - Note the settings used

3. **Script for Batch (Future Feature)**
   ```python
   # Example Python script (to be implemented)
   import bpy
   
   for obj in bpy.data.objects:
       if obj.type == 'MESH' and obj.name.startswith('Character_'):
           # Set target
           bpy.context.scene.auto_rig_settings.target_mesh = obj
           # Generate
           bpy.ops.object.auto_rig_generate()
   ```

4. **Current Workaround**
   - Manually select each character
   - Use same settings in panel
   - Click Generate Rig for each
   - (Batch feature coming in Phase 2)

### Result
Consistent rigs across all characters with same naming and structure.

---

## Example 5: Fixing Weight Painting Issues

### Scenario
Auto weights didn't work perfectly, need manual adjustments.

### Steps

1. **Generate Initial Rig**
   - Use Auto Rigger as normal
   - Notice some areas have poor deformation

2. **Identify Problem Areas**
   ```
   - Enable "Validate Weights" before generation
   - Check console/output for weight issues
   - Test rig by posing in Pose Mode
   ```

3. **Manual Weight Adjustment**
   ```
   - Select mesh
   - Enter Weight Paint mode (Ctrl+Tab → Weight Paint)
   - Select bone in Armature (shows its weights)
   - Paint weights manually:
     - Draw (add weight)
     - Subtract (remove weight)
     - Smooth (blend weights)
   ```

4. **Use Weight Tools**
   ```
   - Weights → Normalize All (fix weight sum)
   - Weights → Clean (remove tiny weights)
   - Weights → Smooth (blend transitions)
   ```

5. **Re-test**
   - Return to Pose Mode
   - Test problematic areas
   - Iterate until satisfied

### Common Problem Areas
- **Shoulders**: Often need manual painting for natural deformation
- **Hips/Groin**: May need adjustment for sitting poses
- **Elbows/Knees**: Might pinch, need smoother transition
- **Neck**: Could pull chest geometry, limit influence

---

## Example 6: Creating Custom Poses

### Scenario
You want to save specific poses after rigging.

### Steps

1. **Generate Rig**
   - Use Auto Rigger with "Generate Poses" enabled
   - This creates T-pose and A-pose automatically

2. **Create Custom Pose**
   ```
   - Select armature
   - Enter Pose Mode (Ctrl+Tab)
   - Pose the character (rotate bones)
   - Select all bones (A key)
   ```

3. **Save as Action**
   ```
   - Open Action Editor (change editor type)
   - Click "New Action" button
   - Name it (e.g., "Attack_Pose")
   - Press I key → LocRotScale to keyframe
   ```

4. **Use with Asset Browser (Blender 4.x)**
   ```
   - In Action Editor, click folder icon
   - "Mark as Asset"
   - Add tags for easy searching
   - Available in Asset Browser for all projects
   ```

### Result
Reusable pose library that can be applied to any similarly rigged character.

---

## Tips & Tricks

### Tip 1: Symmetry Matters
Always use symmetric meshes when possible. Asymmetric characters may produce uneven bone placement.

### Tip 2: Clean Geometry
Remove doubles, fix normals, and triangulate problem areas before rigging:
```
- Mesh → Clean Up → Merge by Distance
- Mesh → Normals → Recalculate Outside
```

### Tip 3: Scale Properly
Ensure your character is properly scaled (humanoid ~1.7-2.0 Blender units):
```
- Select character
- Check dimensions in properties (N panel)
- Scale if needed: S key, type number, Enter
- Apply scale: Ctrl+A → Scale
```

### Tip 4: Test Animations
After rigging, test with basic animations:
1. Download free Mixamo animations
2. Import to Blender
3. Retarget to your rig
4. Check deformation quality

### Tip 5: Preserve Original
Always enable "Preserve Original" in settings. This keeps your original mesh untouched for re-rigging if needed.

---

## Common Workflows

### For Game Development
1. Model in Blender/Maya/Other
2. Import to Blender
3. Auto Rig with matching naming (Unreal/Unity)
4. Test basic animations
5. Export FBX
6. Import to game engine

### For Animation
1. Character in T-pose
2. Auto Rig with Standard or Advanced
3. Manual weight paint refinement
4. Create pose library
5. Animate using keyframes
6. Render

### For VRChat/Virtual Avatars
1. Import avatar mesh
2. Auto Rig with Unity naming
3. Check bone count (must be under limits)
4. Test with VRChat SDK
5. Upload

---

## Performance Benchmarks

Typical processing times:

| Character Type | Vertices | Time | Settings |
|---------------|----------|------|----------|
| Simple low-poly | 2,000 | 3s | Basic rig |
| Game character | 15,000 | 8s | Standard rig |
| High-poly sculpt | 50,000 | 15s | Standard + Heat |
| Detailed w/ fingers | 20,000 | 20s | Advanced rig |

*Tested on: Intel i7, 16GB RAM, Blender 4.0*

---

Need more examples? Check the [GitHub discussions](https://github.com/yourusername/auto-rigger/discussions) or [open an issue](https://github.com/yourusername/auto-rigger/issues)!
