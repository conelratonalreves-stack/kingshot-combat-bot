# Auto Rigger - Installation Guide

## Quick Installation for Blender

### Step 1: Package the Addon

The addon folder structure is:
```
auto_rigger/
├── __init__.py
├── properties.py
├── panels.py
├── operators.py
├── mesh_analyzer.py
├── rig_generator.py
├── weight_painter.py
├── README.md
└── presets/
```

### Step 2: Create ZIP file

**Option A - Manual:**
1. Select the entire `auto_rigger` folder
2. Right-click → Send to → Compressed (zipped) folder
3. Rename to `auto_rigger.zip`

**Option B - PowerShell:**
```powershell
# From the parent directory
Compress-Archive -Path "auto_rigger" -DestinationPath "auto_rigger.zip" -Force
```

### Step 3: Install in Blender

1. Open Blender 4.0 or newer
2. Go to **Edit → Preferences** (or **Blender → Preferences** on macOS)
3. Select **Add-ons** tab
4. Click **Install...** button at top right
5. Navigate to and select `auto_rigger.zip`
6. Click **Install Add-on**
7. Enable the checkbox next to **Rigging: Auto Rigger**

### Step 4: Verify Installation

1. Open 3D Viewport
2. Press `N` key to show sidebar
3. Look for **Auto Rig** tab
4. If you see the panel, installation successful! ✅

## Testing the Addon

### Quick Test

1. Add a default mesh: **Add → Mesh → Monkey (Suzanne)** or **Add → Mesh → UV Sphere**
   - Note: These won't produce good results but will test if addon works

2. For proper testing, you need a humanoid mesh:
   - Download a free humanoid model from Mixamo, Sketchfab, or use MakeHuman
   - Import into Blender (File → Import → FBX/OBJ)

3. Select the mesh in the outliner

4. In the Auto Rig panel:
   - Select your mesh in "Target Mesh"
   - Click "Detect Body Parts"
   - Click "Generate Rig"

5. Wait for processing...

6. Success! You should see an armature created and parented to your mesh

## Troubleshooting

### Addon doesn't appear in preferences
- Check Blender version (must be 4.0+)
- Try restarting Blender
- Check for Python errors in Window → Toggle System Console

### "No module named auto_rigger"
- The ZIP structure might be wrong
- Ensure `__init__.py` is directly inside `auto_rigger/` folder
- Try manual installation (copy folder to addons directory)

### Addon won't enable (checkbox grays out)
- Check System Console for error messages
- Ensure all Python files are present
- Check file permissions

### Panel doesn't show in sidebar
- Press `N` to toggle sidebar
- Scroll down to find "Auto Rig" tab
- Check addon is actually enabled in preferences

## Manual Installation (Alternative)

If ZIP installation fails, try manual method:

1. Find your Blender addons folder:
   - **Windows**: `C:\Users\YourName\AppData\Roaming\Blender Foundation\Blender\4.x\scripts\addons\`
   - **macOS**: `~/Library/Application Support/Blender/4.x/scripts/addons/`
   - **Linux**: `~/.config/blender/4.x/scripts/addons/`

2. Copy the entire `auto_rigger` folder there

3. Restart Blender

4. Enable in preferences

## Next Steps

Once installed:
- Read the main [README.md](README.md) for usage instructions
- Try with simple humanoid models first
- Experiment with different settings
- Report any issues on GitHub

## Uninstallation

1. Go to Edit → Preferences → Add-ons
2. Find "Rigging: Auto Rigger"
3. Click the arrow to expand
4. Click **Remove** button

Or manually delete the `auto_rigger` folder from the addons directory.
