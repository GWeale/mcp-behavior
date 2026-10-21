# External observer examples

Run the two real subprocess observers with the commands in
[the extension guide](../../docs/EXTENSIONS.md). The fixture writes JSON and
SQLite invoice state; both probes return the same ordered versioned projection
for core's existing JSON comparisons. `--write-drift` demonstrates a successful
tool response with wrong stored totals.

The probes use only the standard library and do not import MCP Behavior. The
runner and MCP fixture use this repository's existing dependencies. These are
local clean-room examples, not independent adoption or a published plugin SDK.
