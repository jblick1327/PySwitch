# Keyboard Layout Files

Keyboard layouts are defined with simple JSON documents. The loader
`kb_layout_io` validates that every file contains at least one page with one
row of keys.

```json
{
  "metadata": {
    "name": "Layout Name",
    "description": "Layout description",
    "difficulty": "beginner",
    "features": ["feature1", "feature2"]
  },
  "pages": [
    {
      "rows": [
        {
          "keys": [
            {"label": "a"}
          ]
        }
      ]
    }
  ]
}
```

## Layout Metadata

Each layout can include a `metadata` section that describes its characteristics:

- `name` - Display name of the layout
- `description` - Detailed description of the layout and its purpose
- `difficulty` - One of: "beginner", "intermediate", "advanced"
- `features` - Array of features the layout provides (e.g., "predictive_text", "numbers", "punctuation")
- `target_users` - (Optional) Array of intended user types (e.g., "beginners", "power_users")
- `scan_complexity` - (Optional) Complexity level: "low", "medium", "high"

Example metadata from `qwerty_full.json`:

```json
{
  "metadata": {
    "name": "Complete QWERTY Layout",
    "description": "Comprehensive QWERTY keyboard layout with predictive text, numbers, punctuation, and common actions.",
    "difficulty": "intermediate",
    "features": ["predictive_text", "numbers", "punctuation", "symbols", "actions"],
    "target_users": ["experienced", "power_users"],
    "scan_complexity": "high"
  }
}
```

## Pages

`pages` is an array of keyboard pages. Most layouts only use a single page, but
multi‑page layouts can switch between pages using the virtual actions
`page_next` and `page_prev`.

Example (`alphabet_symbols.json` uses two pages):

```json
{
  "label": "Symbols",
  "action": "page_next"
}
```

## Rows

Each page contains an array of `rows`. Rows may optionally set
`"stretch": false` to disable horizontal stretching when rendered. Every row
must define a `keys` array.

Example from `numeric_pad.json`:

```json
{
  "rows": [
    { "keys": [ {"label": "7"}, {"label": "8"}, {"label": "9"} ] },
    { "keys": [ {"label": "4"}, {"label": "5"}, {"label": "6"} ] }
  ]
}
```

## Keys

A key requires a `label` and may specify additional fields:

- `action` – name from `Action` in `switch_interface.key_types`. If omitted,
  pressing the key types the label.
- `mode` – how to handle modifiers (`"tap"`, `"latch"` or `"toggle"`).
- `dwell` or `dwell_mult` – adjust scanning dwell time for this key.

Example from `media_controls.json`:

```json
{
  "label": "Play",
  "action": "media_play_pause"
}
```

Predictive layouts such as `pred_test.json` use special actions like
`predict_word` and `predict_letter` which insert suggestions rather than a fixed
key value.

## Further Reading

See the files under `switch_interface/resources/layouts/` for complete examples
that you can use as templates for your own layouts.
