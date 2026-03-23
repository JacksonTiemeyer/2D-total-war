# Phase 2 Campaign Extraction Plan

## Goal

Finish the architecture stabilization pass on the campaign side without changing gameplay behavior.

The target outcome is:

- `campaign_scene.py` becomes a coordinator instead of a feature bucket.
- campaign simulation, UI, and interaction logic have clearer ownership.
- future faction and mechanic work can land in focused modules instead of widening one giant scene file.

## Current Read

The runtime split already started with [campaign/runtime.py](/C:/Users/jwtie/OneDrive/Documents/GitHub/2D-total-war/campaign/runtime.py), which now owns the campaign tick loop and pending battle handoff.

The biggest remaining pressure inside `campaign_scene.py` is concentrated in three areas:

- map interaction and click handling
- overlays and panel drawing
- side-system event handling for diplomacy, persuasion, prisoners, companions, tavern, capture, and army management

## Extraction Order

### 1. Extract campaign UI drawing first

Create a dedicated UI module for campaign overlays and panels.

Initial candidates:

- `_draw_hud`
- `_draw_settlement_info`
- `_draw_army_info_panel`
- `_draw_diplomacy`
- `_draw_quest_log`
- `_draw_tournament`
- `_draw_persuasion`
- `_draw_prisoners`
- `_draw_companion_panel`
- `_draw_tavern_panel`
- `_draw_capture_overlay`
- `_draw_army_panel`

Why first:

- this is the lowest-risk extraction
- it removes a large amount of file weight quickly
- it makes later behavior changes easier to reason about

Planned module:

- `campaign/ui.py`

Responsibilities:

- render-only helpers
- button rectangles and panel layout state
- no campaign simulation ownership

### 2. Extract campaign input and overlay event handling

Create a focused input/events module for player interactions and modal overlays.

Initial candidates:

- `_handle_left_click`
- `_handle_top_bar_click`
- `_handle_bottom_bar_click`
- `_handle_right_click`
- `_handle_diplomacy_event`
- `_handle_persuasion_event`
- `_handle_prisoner_event`
- `_handle_companion_event`
- `_handle_tavern_event`
- `_handle_capture_event`
- `_handle_army_panel_event`

Planned module:

- `campaign/input_handlers.py`

Responsibilities:

- click routing
- panel button actions
- modal event handling
- map interaction commands

Non-goal:

- do not move simulation or persistence logic into input code

### 3. Extract campaign map rendering helpers

Create a map/environment helper module for terrain and world-layer drawing.

Initial candidates:

- `_draw_territory_borders`
- `_draw_stronghold`
- `_draw_roads`
- `_draw_interaction_indicators`
- `_draw_terrain`
- `_draw_fog_of_war`

Planned module:

- `campaign/map_rendering.py`

Responsibilities:

- world presentation only
- no AI, save/load, or day processing ownership

### 4. Extract modal/service logic behind the overlays

Once UI and input are separated, pull the state mutation logic for major side systems into service helpers.

Initial candidates:

- tournament open/close and reward flow
- persuasion outcomes
- prisoner handling
- companion recruiting and management
- tavern actions
- capture resolution
- army panel organization actions

Possible modules:

- `campaign/services/tournament.py`
- `campaign/services/social.py`
- `campaign/services/army_management.py`

The exact split can stay practical rather than academic. The important rule is that scene methods should orchestrate these services, not absorb their rules.

### 5. Tighten battle-bridge ownership

Keep the campaign-to-battle handoff in typed contracts and make `campaign_scene.py` call explicit helpers instead of building battle state ad hoc.

Follow-up targets:

- keep pending battle creation in `campaign/runtime.py`
- keep battle launch payload creation in army/domain models
- avoid overlay code mutating battle handoff structures directly

## Guardrails

- Keep gameplay behavior frozen during extraction unless a bug blocks coherence.
- Prefer delegates first, cleanup second.
- Preserve save compatibility.
- New campaign rules should go into service modules, not scene draw methods.
- New campaign overlays should be added to a UI module, not directly into `campaign_scene.py`.

## Acceptance Criteria

This campaign extraction pass is done when:

- `campaign_scene.py` is materially smaller because large responsibilities moved out.
- campaign runtime, input, and rendering each have a clear home.
- the battle handoff still works through explicit contracts.
- new campaign features can be added without touching unrelated draw and event code.

## Recommended Next Slice

Start with `campaign/ui.py`.

That gives the safest win first, removes a large amount of noise from `campaign_scene.py`, and makes the later input extraction much easier to read and test.
