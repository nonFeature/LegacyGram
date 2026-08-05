# Contributing to LiteGram

## Technical Stack
| Tool                 | Purpose                                                                    |
|----------------------|----------------------------------------------------------------------------|
| **uv**               | Lightning-fast dependency management and environment isolation             |
| **Ruff**             | Strict linting and formatting                                              |
| **ty**               | Static type checking                                                       |
| **GitHub Actions**   | CI/CD - every commit automatically validates and builds `.plugin` artifact |
| **Chaquopy**         | Python-to-Java bridge                                                      |      
| **exteraGram Utils** | Plugin API System in Telegram                                              |


## Prerequisites
- Python 3.11
- [uv](https://docs.astral.sh/uv/) installed
- Android Device / Emulator with [exteraGram](https://exteragram.app) based client Installed
- [exteraGram plugins documentation](https://plugins.exteragram.app/docs/setup)

## Development Setup
```bash
git clone https://github.com/repinek/LegacyGram.git
cd LegacyGram
uv sync
uv run build.py # build a plugin
# Connect your phone using ADB, turn on development mode in exteragram Plugin Settings
uv run extera dist/LegacyGram.plugin # Runs a dev server
```


## Project Structure
```
├── LegacyGram/
│   ├── main.py                 # Entry Point
│   ├── data/                   # Constants
│   ├── features/               # Features by categories
│   ├── i18n/                   # Internationalization system
│   │   └── locales.py          # Localization
│   ├── ui/                     # Settings UI
│   └── utils/                  # Helper functions
│
├── typings/                    # Typings stubs for java, xposed and android view
│   ├── android/
│   │   └── view/               
│   ├── de/
│   │   └── robv/
│   │       └── android/
│   │           └── xposed/
│   └── java/
│       └── lang/
│           └── reflect/
│
├── assets/                     # Assets
│   └── sticker.webp            # Source for __icon__
│
├── build.py                    # Plugin Build Script
├── pyproject.toml              # Project Configuration File
└── uv.lock                     # lockfile for uv
```


## Coding Standards
### Required Checks
Runs automatically with building

```bash
uv run ruff check . --fix   # Fix linting issues
uv run ruff format .        # Format code
uv run ty check             # Type checking
```

### Style Rules
- **Strings**: Double quotes only (`"text"`)
- **Toggle keys**: camelCase (defined in `data/constants.py`)
- **Imports**: No relative imports - use `from LegacyGram.x import y, z`
- **Use Lazy Initizalition**
- **Feature structure**:
  ```python
  # Class Method Hook name pattern
  class ClassMethodHook(BaseHook):
      def before_hooked_method(self, param):
          if self.is_enabled():
              param.setResult(...)  # or do anything else

  def register_feature(plugin) -> None:
      # Use EXACT case-sensitive Java class name
      SomeClass = find_class("org.telegram.SomeClass")
      if SomeClass:
          plugin.hook_all_methods(SomeClass, "methodName", ClassMethodHook(plugin, Keys.toggle_key))
  ```

### Typings
The project includes `typings/` directory with stubs for:
- Android API (view)
- Xposed framework
- Java standard library
- Chaquopy Python-to-Java bridge

### Plugin icon
> `__icon__` uses the format `StickerPackShortName/index`, for example `exteraPlugins/1`.

The current icon is `LegacyGram/0`. If anything happens with sticker pack, a local copy is stored in `assets/sticker.webp`.

## Building
```bash
uv run build.py              # Increment version and build
uv run build.py --no-bump    # Build without version bump
```

Output: `dist/LegacyGram.plugin`

The build script:
1. Runs Ruff and ty (auto-fix + format)
2. Merges all `.py` files (excluding `__init__.py`) into a single file
3. Strips internal imports and commented lines
4. Generates consolidated import block
5. Outputs a single `.plugin` file for exteraGram