# ReliAI Design System & Visual Direction

This document defines the permanent visual and design direction for the ReliAI frontend. All future frontend implementation must follow this standard. When building new features, extend this design system rather than inventing new visual styles.

## Visual Principles
ReliAI is a professional SRE and observability platform. The visual personality is:
- Professional and technical
- Calm and precise
- Information-dense and trustworthy
- Modern, feeling premium without being flashy

The interface must communicate that this is software used by engineers to investigate real production incidents. It should draw inspiration from the quality bars of Datadog, Grafana, Linear, Vercel, and GitHub.

## Prohibited Visual Patterns (The "AI-Generated" Look)
Do **NOT** use visual tropes common in generic AI-generated SaaS websites:
- Excessive purple/blue gradients or neon glowing backgrounds.
- Giant gradient text, oversized marketing typography, or meaningless abstract AI illustrations.
- Decorative blobs, random decorative icons, generic AI robot imagery, or excessive emojis.
- Excessive glassmorphism, floating glass cards everywhere, huge rounded cards, or excessive pill-shaped UI.
- Every section wrapped in a card or unnecessary attention-grabbing animations.
- Generic "AI-powered everything" copy.

## Color Philosophy
Use a restrained, engineering-oriented palette where color communicates system state rather than decorating the UI.

**Base Colors:**
- **Primary Background:** Very dark charcoal / near-black.
- **Surfaces:** Slightly lighter than the background to establish hierarchy.
- **Borders:** Subtle neutral grays.
- **Text:** Off-white for primary text, muted gray for secondary text.

**Semantic Colors (Functional):**
- **Green:** Healthy / Success.
- **Amber:** Warning / Degraded.
- **Red:** Incident / Critical.
- **Blue/Indigo:** Informational / Interactive accent.
*(Do not make the entire application blue/purple).*

## Typography
Use a clean, modern sans-serif stack.
- **Preferred Fonts:** Inter, Geist, or IBM Plex Sans.
- **Hierarchy:** Rely on typographic weight and color hierarchy rather than enormous headings.
- **Technical Data:** Engineering data (timestamps, request IDs, incident IDs, latency, status codes, metrics) must receive a clear technical, monospace, or data-oriented treatment.

## Layout Principles
- **Visual Hierarchy:** Prioritize strong visual hierarchy. Use consistent spacing to group related data.
- **Information Density:** Use whitespace intentionally, but do not waste screen space. The interface should be information-dense.
- **Surfaces:** Use restrained surfaces. Not every component needs a card. Avoid "card-ception".
- **Alignment:** Maintain excellent alignment for readability, particularly in tables and charts. Predictable interaction patterns are critical.

## Component Style
- **Borders & Shadows:** Prefer subtle 1px borders and minimal shadows over heavily elevated components.
- **Shapes:** Restrained corner radius. Avoid making every component excessively rounded or pill-shaped.
- **Controls:** Use compact controls with consistent button hierarchy and clear hover/focus states.

## Data Visualization
Charts and graphs must be functional first. They exist to help engineers understand:
- Latency and error rates
- Traffic and resource utilization
- Incidents, service health, timelines, and correlations
- Avoid decorative charts that exist only to make the UI look impressive.

## Dashboard Direction
The main dashboard serves as an engineering control center. The layout should flow logically:
1. **Sidebar:** Global navigation.
2. **Top Navigation:** Global status & context.
3. **System Overview:** High-level system state.
4. **Key Reliability Metrics:** Core SLIs/metrics.
5. **Service Health:** Status of specific microservices.
6. **Charts / Timelines:** Time-series visualizations.
7. **Recent Incidents/Events:** Actionable feeds of recent anomalies.

## Incident Experience
The incident page is the core of the ReliAI investigation experience. The visual hierarchy must make the investigation process completely obvious:

**Signals → Incident → Evidence → Correlation → Root Cause → Recommended Remediation**

An engineer must immediately understand:
- What happened and when it happened.
- Which services are affected.
- What evidence was observed.
- What the system believes caused it and how confident the RCA is.
- What remediation is recommended.
*Crucial evidence must never be hidden behind decorative UI elements.*

## Motion
Use animation sparingly.
- **Good uses:** State transitions, loading states, chart updates, navigation, and incident status changes.
- **Avoid:** Constant floating animations, excessive page transitions, attention-grabbing effects, and any animations that reduce usability or speed.

## Accessibility
The design must support:
- Keyboard navigation
- Visible focus states
- Readable contrast ratios (WCAG AA at minimum)
- Semantic HTML tags
- Accessible interactive controls
- Support for reduced-motion preferences

## Responsive Design
- **Desktop First:** The primary target is desktop displays because SRE engineers commonly use large screens.
- **Scalability:** However, the interface should gracefully degrade and remain usable on smaller screens or half-width windows.

## Design System Extension Rule
Future frontend implementation must follow this visual language consistently. When a future feature needs a new component, prefer extending the existing design system rather than inventing a new visual style.
