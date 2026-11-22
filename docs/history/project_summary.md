# GBA Dual Screen for Nintendo DS

> Historical development record. Some status, commands and artifact paths describe
> earlier builds. Start with the [current README](../../README.md) and
> [developer guide](../development.md) for current instructions.

## 1. Vision

Bring enhanced, dual-screen Game Boy Advance gameplay to original Nintendo DS hardware.

The project takes inspiration from [GBA DS](https://github.com/kyannon/gba-ds), an emulator that enhances existing GBA games by displaying maps, statistics, inventories and other contextual information on a secondary screen.

Rather than targeting modern emulation handhelds, this project targets original Nintendo DS hardware through flashcarts such as DSPico.

The experience should feel as though selected GBA games had originally been designed for the Nintendo DS, without fundamentally altering their gameplay.

## 2. Design Principles

- **Authentic hardware:** Run on original Nintendo DS and DS Lite hardware, with DSi and 3DS compatibility desirable.
- **Performance first:** Preserving the original game's performance takes precedence over secondary-screen functionality.
- **Authentic presentation:** Secondary-screen graphics should match the original game's visual language.
- **Non-invasive:** Avoid modifying game ROMs wherever possible.
- **Automatic:** Supported games should receive enhancements without manual configuration.
- **Extensible:** Adding support for a new game should not require modifying the core GBA runtime.

## 3. Example Experiences

| Game | Secondary screen |
|---|---|
| Metroid Fusion | Live exploration map |
| Metroid: Zero Mission | Live exploration map |
| Castlevania: Aria of Sorrow | Castle map |
| Castlevania: Harmony of Dissonance | Castle map |
| Castlevania: Circle of the Moon | Castle map and completion |
| Advance Wars | Unit and terrain statistics |
| Fire Emblem | Selected unit statistics |
| Golden Sun | Party status and statistics |
| Pokémon Emerald | Party status and map |
| Final Fantasy Tactics Advance | Selected unit information |

These are illustrative targets rather than committed features.

## 4. Technical Approach

### Existing GBA DS

The existing GBA DS project uses two instances of mGBA. One runs the game normally, while a second periodically receives a copy of the game's state, navigates to an information screen and captures its output.

This is an elegant and relatively general approach, but it is unlikely to be computationally practical on original Nintendo DS hardware.

### Proposed Architecture

Build on [GBARunner3](https://github.com/Gericom/GBARunner3), which leverages the Nintendo DS's native ARM hardware to execute GBA games.

Instead of running a second emulator, the enhanced runtime will inspect the running game's memory and independently render contextual information on the DS's secondary display.

The system consists of five main components:

1. **GBA runtime:** GBARunner3, with minimal modifications to its existing execution path.
2. **Memory inspection layer:** Read-only access to relevant GBA memory and ROM data.
3. **Game identification:** Identify supported games and regional revisions.
4. **Game adapters:** Game-specific logic for translating raw memory into meaningful gameplay state.
5. **Secondary-screen renderer:** Render maps, statistics and other information using the DS's graphics hardware.

The intended data flow is:

GBA runtime → Memory inspection → Game adapter → Secondary-screen renderer

The game itself continues executing normally.

## 5. Game Adapter System

Each supported game has a dedicated adapter responsible for understanding its internal memory structures.

For a Metroid game, an adapter might expose:

- Current area
- Current room
- Player position
- Explored map tiles
- Visited rooms
- Save stations
- Item locations and collection state

Adapters should be isolated from the underlying runtime and rendering implementation as much as possible.

Related games may share adapters, rendering logic or memory layouts.

Regional releases and ROM hacks should be supported only when their memory layouts have been verified.

Unsupported games should continue to function normally, without secondary-screen enhancements.

## 6. Leveraging Existing Work

### GBARunner3

Provides the foundation for executing GBA games on DS hardware.

The first engineering task is to determine:

- How GBA memory is mapped and accessed.
- Which DS graphics resources remain available.
- How additional logic can execute without disrupting game timing.
- Whether a secondary-screen renderer can coexist with the runtime.
- How much memory and CPU capacity remains available.

### GBA DS

Provides a reference for desired behavior and presentation.

Its game-specific memory addresses, detection logic, compatibility information and existing reverse-engineering work may be reusable.

Its dual-emulator architecture should not be carried over.

### Game Decompilation Projects

Existing GBA game decompilations and ROM hacking communities may provide documentation of internal memory layouts, map formats and gameplay state.

These should be investigated before performing reverse engineering from scratch.

## 7. Implementation Roadmap

### Phase 0 — Establish the baseline

- Build an unmodified version of GBARunner3.
- Run it on original DS hardware using DSPico.
- Verify normal gameplay.
- Establish a reproducible build and deployment process.

### Phase 1 — Secondary-screen rendering

- Display static text on the secondary screen while a GBA game runs.
- Render a simple tile grid.
- Verify that rendering does not corrupt the primary display.
- Measure any effect on gameplay performance.

This phase establishes whether the fundamental architecture is viable.

### Phase 2 — Live memory inspection

Select Metroid Fusion as the initial target.

- Identify the game's ROM revision.
- Locate the current room and area identifiers in memory.
- Display these values on the secondary screen.
- Update the values as the player moves between rooms.
- Verify that memory inspection does not interfere with gameplay.

At this point, the project has a complete, minimal end-to-end implementation.

### Phase 3 — Live map

- Reconstruct the map for one area.
- Render the map on the secondary screen.
- Highlight the player's current room.
- Display explored and unexplored rooms.
- Update the map automatically as the player progresses.

### Phase 4 — Complete first game

- Support every area of Metroid Fusion.
- Add map icons and relevant contextual information.
- Match the original game's graphical style.
- Handle transitions, menus, deaths and save loading.
- Test performance and stability on physical hardware.

### Phase 5 — Generalize

- Formalize the game adapter interface.
- Extract reusable map-rendering components.
- Add Metroid: Zero Mission.
- Add Castlevania: Aria of Sorrow.
- Document how contributors can add new games.

### Phase 6 — Distribution

- Provide a downloadable `.nds` executable.
- Support convenient installation on DSPico and compatible flashcarts.
- Publish a game compatibility matrix.
- Provide contributor documentation.

## 8. Initial Proof of Concept

The first deliverable should be deliberately minimal.

**Target game:** Metroid Fusion.

**Target hardware:** Nintendo DS or DS Lite with DSPico.

**Top screen:** Unmodified GBA gameplay.

**Bottom screen:**

- Game title
- Current area identifier
- Current room identifier
- A small graphical grid with the current room highlighted

No polished UI, touchscreen functionality, complete maps or additional game support are necessary.

### Success Criteria

- Runs on physical Nintendo DS hardware.
- Original gameplay remains stable.
- No perceptible slowdown relative to unmodified GBARunner3.
- Secondary-screen information responds to room transitions.
- No manual ROM modification is required.
- Build and deployment are reproducible.

## 9. Technical Risks

The proposed architecture is plausible but unverified.

The principal risks are:

- GBARunner3 may already rely on graphics resources needed for the secondary screen.
- Available CPU capacity may be insufficient for additional processing.
- Memory inspection may be difficult to perform safely during native ARM execution.
- DS memory limitations may constrain map data and rendering.
- Regional releases may require separate memory layouts.
- Individual games may require substantial reverse engineering.

These risks should be investigated experimentally before committing to an elaborate architecture.

Fallback options include reducing update frequency, using hardware tile rendering, precomputing map assets, and initially targeting more capable DSi hardware.

## 10. Non-Goals

The project will not initially attempt to:

- Port mGBA to the Nintendo DS.
- Run multiple instances of a GBA emulator.
- Support every GBA game.
- Add touchscreen controls to existing games.
- Improve the original game's graphics.
- Reimplement GBARunner3.
- Achieve feature parity with the modern GBA DS project.

## 11. Long-Term Vision

Eventually, the project should become an enhanced GBA compatibility layer for the Nintendo DS, with a growing library of game-specific enhancements.

Its most compelling achievement would be making the GBA Metroid and Castlevania games feel like native dual-screen Nintendo DS titles.

An original DS, a flashcart and an unmodified GBA ROM should be all a player needs.

## 12. References

- [GBA DS](https://github.com/kyannon/gba-ds)
- [GBARunner3](https://github.com/Gericom/GBARunner3)
- [DSPico](https://github.com/LNH-team/dspico)
- [GBATEK hardware documentation](https://problemkaputt.de/gbatek.htm)
- [Metroid Fusion decompilation](https://github.com/metroidret/mf)

Before implementation, review the licensing requirements of all reused code and assets.