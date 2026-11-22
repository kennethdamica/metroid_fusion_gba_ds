# Documentation

| Guide | Purpose |
| --- | --- |
| [Development](development.md) | Set up a checkout, build the runtime and packager, run local tests |
| [GitHub setup](github-setup.md) | Initialize, review, commit and push the source; keep binary releases separate |
| [Packager CLI](packager-cli.md) | Input validation, output behavior, frozen builds and recorded evidence |
| [Troubleshooting](troubleshooting.md) | Input errors, flashcart boot, emulator setup and saves |
| [Live map adapter](fusion-map.md) | Memory layout, display resources, map rendering and coverage |
| [Hardware investigation](hardware-debug.md) | DSpico/3DS boot failure and ARM interworking fix |
| [Release readiness](releasing.md) | Source review, binary packaging, licensing and platform checks |
| [Licensing review](licensing-review.md) | Findings, upstream permissions, source/binary obligations and proposed resolution order |

`artifacts/`, `.tools/`, `vendor/` and `fixtures/local/` are generated or private
local directories. Paths to them in these guides describe local outputs; they
are not files included in a fresh clone or links to published downloads.

## Historical research

These records retain the investigation and earlier assumptions. Prefer the
current guides for setup and compatibility:

- [Original project summary](history/project_summary.md)
- [Implementation plan and research](history/implementation_plan.md)
- [Packaging design and milestones](history/packaging_plan.md)
- [Baseline experiment notes](history/BASELINE_NOTES.md)
- [Earlier development README](history/development-log.md)
