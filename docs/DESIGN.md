# Design System Specification: The Ethereal Canvas

## 1. Overview & Creative North Star
**Creative North Star: The Silent Architect**
This design system is built on the philosophy that a workspace should feel like a clean, physical desk under soft, natural morning light. It moves beyond the "standard SaaS" aesthetic by prioritizing cognitive ease over structural rigidity. By utilizing intentional asymmetry, expansive negative space, and tonal layering, we create an environment that recedes into the background, allowing the user’s thoughts and the AI’s responses to take center stage. 

We break the "template" look by treating the UI not as a grid of boxes, but as a series of soft, floating surfaces that interact through light and shadow rather than lines and borders.

---

## 2. Colors & Surface Philosophy
The palette is a study in sophisticated neutrality, anchored by a deep teal-green (`primary`) that provides a single, authoritative point of focus.

### The "No-Line" Rule
**Prohibition of 1px Borders:** To maintain a premium, editorial feel, 1px solid lines for sectioning are strictly prohibited. Boundaries must be defined solely through background color shifts.
- A sidebar uses `surface_container_low`.
- The main workspace uses `surface`.
- Floating panels use `surface_container_lowest`.

### Surface Hierarchy & Nesting
Treat the UI as physical layers. Use the `surface_container` tiers to create depth:
- **Level 0 (Base):** `background` (#f8f9fa)
- **Level 1 (Sections):** `surface_container_low` (#f1f4f6) for large structural areas like sidebars.
- **Level 2 (Cards):** `surface_container_lowest` (#ffffff) for active content modules.
- **Level 3 (Popovers):** `surface_bright` (#f8f9fa) with `backdrop-blur`.

### The "Glass & Gradient" Rule
For floating action bars or message inputs, use semi-transparent `surface_container_lowest` (80% opacity) with a `24px` backdrop blur. For primary actions, apply a subtle linear gradient from `primary` (#006c52) to `primary_dim` (#005e48) at a 135-degree angle to provide a "jewel" finish.

---

## 3. Typography: The Editorial Voice
Our typography pairing balances the technical precision of **Inter** with the approachable, modern character of **Manrope**.

| Role | Font Family | Size | Intent |
| :--- | :--- | :--- | :--- |
| **Display** | Manrope | 3.5rem - 2.25rem | Heroic AI greetings; low-contrast (`on_surface_variant`). |
| **Headline** | Manrope | 2.0rem - 1.5rem | Section headers; bold and authoritative. |
| **Title** | Inter | 1.375rem - 1.0rem | Card titles and message headers; high legibility. |
| **Body** | Inter | 1.0rem - 0.875rem | Primary reading experience; generous line-height (1.6). |
| **Label** | Inter | 0.75rem | Metadata, timestamps, and micro-copy. |

**Editorial Strategy:** Use `display-sm` for AI prompts to make the technology feel human. Ensure body text never exceeds a 70-character line width to maximize readability.

---

## 4. Elevation & Depth
We eschew the "flat" look for a tactile, layered experience.

- **The Layering Principle:** Depth is achieved by stacking `surface-container` tiers. A `surface_container_lowest` card placed on a `surface_container_low` background creates a natural lift.
- **Ambient Shadows:** When a true "float" is required (e.g., a dropdown), use an extra-diffused shadow: `0 12px 40px rgba(43, 52, 55, 0.06)`. The tint uses the `on_surface` color at a very low opacity to mimic natural light.
- **The "Ghost Border":** If a container requires more definition against an identical background, use a 1px border with `outline_variant` (#abb3b7) at **15% opacity**. Never use a 100% opaque border.
- **Roundedness:** Use the `xl` (1.5rem) radius for major workspace containers and `md` (0.75rem) for smaller buttons or input fields.

---

## 5. Components

### Primary Buttons
- **Style:** Gradient fill (`primary` to `primary_dim`), white text (`on_primary`), `full` roundedness.
- **State:** On hover, increase the gradient intensity. On press, scale down slightly (98%).

### Message Inputs
- **Style:** `surface_container_lowest` background, `xl` roundedness, with a `Ghost Border` (15% `outline_variant`). 
- **Interaction:** On focus, the border shifts to `primary` at 40% opacity with a 4px soft glow.

### Conversation List
- **The No-Divider Rule:** Forbid the use of horizontal lines between list items. Instead, use `16px` of vertical spacing and a subtle `surface_container_high` background shift on hover to indicate selection.

### AI Suggestions (Chips)
- **Style:** `surface_container_lowest` background, `sm` shadow, `md` roundedness. 
- **Visuals:** Use a leading icon with `secondary` (#506076) color to denote different AI capabilities.

---

## 6. Do's and Don'ts

### Do
- **Do** use generous whitespace (at least 32px) between major functional blocks.
- **Do** use `on_surface_variant` for secondary text to create a clear visual hierarchy against `on_surface` primary text.
- **Do** align elements asymmetrically to create a modern, "curated" feel (e.g., left-aligned text with a right-aligned action floating in negative space).

### Don't
- **Don't** use pure black (#000000) for text. Always use `on_surface` (#2b3437).
- **Don't** use traditional "Material" drop shadows. Always use the Ambient Shadow spec (large blur, low opacity).
- **Don't** use 100% width for text containers; keep AI responses contained to maintain an editorial layout.
- **Don't** use high-contrast dividers; use tonal shifts between `surface_container` tiers instead.
