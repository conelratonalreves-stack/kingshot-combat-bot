# Auto Rigger for Blender

![Blender Version](https://img.shields.io/badge/Blender-4.0%2B-orange)
![License](https://img.shields.io/badge/license-GPL--3.0-blue)

**Automatic humanoid rigging addon for Blender with intelligent geometry detection.**

## Features

✨ **Automatic Body Detection** - Detects head, torso, arms, legs automatically from mesh geometry  
🦴 **Smart Skeleton Generation** - Creates properly hierarchical bone structures  
⚖️ **Symmetry Detection** - Automatically finds and uses mesh symmetry  
🎮 **IK/FK Controls** - Generates IK controls for arms and legs with pole targets  
🎨 **Auto Weight Painting** - Multiple methods: Heat Diffusion, Distance-based, Automatic  
📐 **Multiple Naming Conventions** - Mixamo, Unreal Engine, Unity/Mecanim, Rigify  
👤 **Body Type Presets** - Male, Female, Child, Stylized proportions  
🔧 **Customizable** - Adjust spine bones, finger bones, twist bones, and more  

## Installation

### Method 1: From ZIP (Recommended)

1. Download the latest release `auto_rigger.zip`
2. Open Blender → Edit → Preferences → Add-ons
3. Click "Install..." button
4. Select the downloaded `auto_rigger.zip`
5. Enable the checkbox next to "Rigging: Auto Rigger"

### Method 2: From Source

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/auto-rigger.git
   ```

2. Copy the `auto_rigger` folder to your Blender addons directory:
   - **Windows**: `%APPDATA%\Blender Foundation\Blender\4.x\scripts\addons\`
   - **macOS**: `~/Library/Application Support/Blender/4.x/scripts/addons/`
   - **Linux**: `~/.config/blender/4.x/scripts/addons/`

3. Enable in Blender preferences under Add-ons → Rigging → Auto Rigger

## Quick Start

### Basic Usage

1. **Import or create your humanoid mesh** (should be in T-pose or A-pose)

2. **Open the Auto Rig panel** in the 3D Viewport sidebar (press `N` key → Auto Rig tab)

3. **Select your mesh** in the "Target Mesh" field

4. **Click "Detect Body Parts"** to analyze the geometry (optional but recommended)

5. **Configure settings**:
   - Body Type: Male, Female, Child, or Stylized
   - Rig Type: Basic, Standard (IK/FK), or Advanced (with fingers)
   - Naming Convention: Choose your preferred standard

6. **Click "Generate Rig"** and wait for the magic! ✨

### Settings Explained

#### Main Settings

- **Body Type**: Adjusts proportions and bone placement
  - Male: Standard male proportions
  - Female: Wider hips, narrower shoulders
  - Child: Larger head-to-body ratio
  - Stylized: For cartoon/anime characters

- **Rig Type**: Complexity level
  - Basic: Simple FK skeleton
  - Standard: IK/FK for limbs (recommended)
  - Advanced: Full control rig with fingers

- **Naming Convention**:
  - Mixamo: Most universal, works with Mixamo animations
  - Unreal Engine: For UE4/UE5 projects
  - Unity/Mecanim: For Unity humanoid rigs
  - Rigify: Compatible with Blender Rigify system

#### Rig Settings

- **Create IK Controls**: Enables Inverse Kinematics for limbs
- **Create Pole Targets**: Adds control for elbow/knee direction
- **Add Fingers**: Adds finger bones (Advanced rig only)
- **Add Twist Bones**: Extra bones for forearm/shin rotation
- **Spine Bones**: Number of spine segments (1-6)

#### Weight Painting

- **Weight Method**:
  - Heat Diffusion: Best quality, slower (recommended)
  - Automatic: Blender's built-in method, fast
  - Distance Based: Simple, fastest
  - Envelope: Classic envelope-based

- **Smooth Weights**: Applies smoothing passes to weight transitions
- **Validate Weights**: Checks for unweighted vertices and normalization issues

#### Advanced Options

- **Detect Symmetry**: Uses mesh symmetry for better bone placement
- **Preserve Original**: Duplicates mesh before rigging (recommended)
- **Generate Poses**: Creates default T-pose and A-pose

## Best Practices

### For Best Results

✅ **DO:**
- Use clean, manifold geometry
- Ensure mesh is in T-pose or A-pose
- Apply all transforms (Ctrl+A → All Transforms) before rigging
- Check mesh has proper scale (humanoid ~1.7-2.0 units tall)
- Use symmetric models when possible

❌ **DON'T:**
- Apply modifiers that affect vertex positions before rigging
- Use extremely low-poly or high-poly models (sweet spot: 5k-50k vertices)
- Rig meshes with disconnected body parts
- Use meshes with extreme non-uniform scaling

### Troubleshooting

**Problem**: "Failed to detect body parts"
- **Solution**: Ensure mesh is humanoid shaped and not too stylized. Try adjusting symmetry tolerance.

**Problem**: Bones in wrong positions
- **Solution**: Mesh might not be in T-pose. Manually adjust pose and re-run detection.

**Problem**: Weight painting issues
- **Solution**: Try different weight methods. Heat Diffusion is most reliable but slower.

**Problem**: Addon doesn't appear
- **Solution**: Check Blender version (needs 4.0+). Look in Rigging category of addons.

## Examples

### Character Types Supported

- ✅ Realistic humans (male/female)
- ✅ Cartoon/stylized characters
- ✅ Children and teens
- ✅ Anime-style characters
- ✅ Game-ready models
- ⚠️ Creatures (partial support, humanoid-shaped only)
- ❌ Quadrupeds (not supported)
- ❌ Non-humanoid (not supported)

## Technical Details

### Detection Algorithm

The addon uses a multi-stage approach:
1. Analyzes mesh bounding box and vertex distribution
2. Detects symmetry plane using KDTree spatial queries
3. Identifies landmarks (head, hands, feet) using extreme point detection
4. Segments body parts using geodesic distance and clustering
5. Places bones using Principal Component Analysis (PCA) on segments

### Dependencies

- **Blender 4.0+** (uses latest Python API)
- **NumPy** (included with Blender)
- **BMesh** module (built-in)

### Performance

Typical processing times on modern hardware:
- Mesh analysis: 0.5-2 seconds
- Rig generation: 1-3 seconds
- Weight painting: 2-10 seconds (depends on method and vertex count)

**Total**: 3-15 seconds for complete auto-rigging

## Development

### Project Structure

```
auto_rigger/
├── __init__.py           # Addon registration
├── properties.py         # Custom properties and settings
├── panels.py            # UI panels
├── operators.py         # Main operators
├── mesh_analyzer.py     # Geometry analysis
├── rig_generator.py     # Skeleton generation
├── weight_painter.py    # Weight painting
└── presets/             # Preset configurations
```

### Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with clear commit messages
4. Test thoroughly with different character types
5. Submit a pull request

## Roadmap

### Phase 1 (Current) - MVP ✅
- [x] Basic mesh analysis
- [x] Skeleton generation
- [x] Automatic weights
- [x] Simple UI

### Phase 2 - Essential Features 🚧
- [ ] Advanced IK/FK controls
- [ ] Custom bone shapes and colors
- [ ] Face rigging detection
- [ ] Improved weight smoothing
- [ ] Batch processing

### Phase 3 - Polish
- [ ] Validation and quality reports
- [ ] Animation retargeting
- [ ] Preset library system
- [ ] Video tutorials

### Phase 4 - Advanced
- [ ] Machine learning detection
- [ ] Facial rig automation
- [ ] Automatic control rig painting
- [ ] Asset library integration

## License

This addon is licensed under the **GNU General Public License v3.0** (GPL-3.0).

This means:
- ✅ Free to use, modify, and distribute
- ✅ Can be used in commercial projects
- ⚠️ Modifications must also be open-source (GPL-3.0)
- ⚠️ No warranty provided

See [LICENSE](LICENSE) file for full terms.

## Credits

**Developed by**: Auto Rigger Team  
**Inspired by**: Rigify, Auto-Rig Pro, Mixamo  
**Built with**: Blender Python API

## Support

- 📖 [Documentation](https://github.com/yourusername/auto-rigger/wiki)
- 🐛 [Report Issues](https://github.com/yourusername/auto-rigger/issues)
- 💬 [Discussions](https://github.com/yourusername/auto-rigger/discussions)
- 📧 Email: support@example.com

## Changelog

### Version 1.0.0 (2026-01-28)
- Initial release
- Automatic humanoid detection
- Multiple naming conventions
- IK/FK setup
- Multiple weight painting methods
- Body type presets

---

**Made with ❤️ for the Blender community**
