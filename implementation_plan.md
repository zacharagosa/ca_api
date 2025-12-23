# Styles to Add/Update in App.css

## Thinking Process Accordion (`.thoughts-accordion`)
- **Container**: `width: 100%`, `margin-bottom: 0.5rem`.
- **Header Button (`.thoughts-header-btn`)**:
  - `width: 100%`
  - `display: flex`, `justify-content: space-between`, `align-items: center`
  - `padding: 8px 12px`
  - `background: #f0f4f9` (Gemini light grey)
  - `border: none`
  - `border-radius: 8px`
  - `cursor: pointer`
  - `color: #444746` (Gemini text color)
  - `font-size: 0.85rem`
  - `font-weight: 500`
  - Hover effect: darken slightly.
- **List Container (`.thoughts-list`)**:
  - `padding: 12px`
  - `margin-top: 4px`
  - `background: #f8f9fa`
  - `border-radius: 8px`
  - `font-family: monospace`
  - `font-size: 0.8em`
  - `color: var(--text-secondary)`
  - `border: 1px solid var(--border-color)`

## Content/Chart Accordion (`.chart-accordion`)
- Ensure `width: 100%`.
- Update `background` to be white or very light grey to match new theme.
- Ensure transitions if possible (though auto-height transition is hard in pure CSS without max-height trick).

## Metadata Accordion (`.metadata-accordion`)
- Similar styling to Thinking Process but maybe distinct.

# Plan
1. Append these new styles to `App.css`.
2. Verify `App.jsx` structure matches these class names (confirmed previously).
