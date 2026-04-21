# png2svg Setup Verification

## What Was Installed

- **OpenCode Boomerang Plugin** (`opencode-boomerang`) - Multi-agent orchestration system
- **Super Memory MCP** (`super-memory-mcp`) - Long-term memory management
- **Sequential Thinking MCP** (`@modelcontextprotocol/server-sequential-thinking`) - Structured reasoning

## Dependencies to Install

```bash
# Core plugin
pip install opencode-boomerang

# Super memory server
pip install super-memory-mcp

# Optional: SearXNG for web research (disabled by default)
# pip install mcp-searxng
```

## Verify Setup

1. Check the configuration file exists:
   ```bash
   cat .opencode/opencode.json
   ```

2. Verify OpenCode can load the Boomerang plugin:
   ```bash
   opencode --version  # or similar
   ```

3. Test super-memory is accessible:
   ```bash
   uvx super-memory-mcp --help
   ```

## Next Steps

1. **Initialize Boomerang agents** for this project:
   ```
   /boomerang-init
   ```

2. **Start using OpenCode** with Boomerang orchestration:
   ```
   opencode
   ```

3. Explore the project with Boomerang agents:
   - `/explore` - Find files, understand structure
   - `/plan <task>` - Plan implementation
   - `/codegen <task>` - Generate code

## Notes

- The `searxng` MCP server is disabled by default. To enable, set `"enabled": true` in `opencode.json` and ensure a SearXNG instance is running at `http://localhost:8080`.
- For more configuration options, see the [OpenCode documentation](https://github.com/pydmd/OpenCode).