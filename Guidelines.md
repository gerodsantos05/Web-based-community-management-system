# Learning Hub Design System - AI Prompt

## Overview
Create a modern, minimal Learning Hub interface that feels like a curated digital library focused on exploration and discovery rather than progress tracking. Use 2026 design trends: clean layouts, generous whitespace, soft shadows, and warm photography.

---

## Design Principles

### What to AVOID:
- ❌ Progress bars, percentages, completion tracking
- ❌ XP systems, streaks, statistics, gamification
- ❌ Dense boxed layouts with heavy containers
- ❌ Large solid color blocks without purpose
- ❌ Excessive buttons (use clickable cards instead)
- ❌ Dashboard-style layouts

### What to EMBRACE:
- ✅ Content-driven, visually rich cards
- ✅ Generous whitespace and breathing room
- ✅ Soft, warm photography or consistent illustrations
- ✅ Minimal, purposeful interactions
- ✅ Clean typography hierarchy
- ✅ Subtle hover effects and transitions

---

## Layout Structure

### Overall Layout
- **Two-column responsive grid** on desktop:
  - LEFT: Main content area (learning topic cards)
  - RIGHT: Sticky sidebar (recommended, recently viewed, popular)
- **Single column stack** on mobile/tablet
- **Background**: Soft neutral (`#fafafa` or similar off-white)
- **Max width**: Contained (e.g., `max-w-7xl`)
- **Padding**: Generous (`px-6 py-10`)

### Header Section
```
[Title] Learning Hub
[Subtitle] One-line description
[Search Bar] Rounded, clean, with icon
[Category Filters] Pill-style chips (All, Community, Children, New, Popular)
```

- Title: Large, clear hierarchy
- Subtitle: Single line, muted color
- Search: Full-width rounded input with left-aligned search icon
- Filters: Horizontal pill buttons, filled state for active

---

## Component Specifications

### Topic Card Component

**Visual Structure:**
```
┌─────────────────────────┐
│                         │
│   [Image 40-50%]        │
│   + Gradient Overlay    │
│   [Tag: top-right]      │
│                         │
├─────────────────────────┤
│  Title (bold)           │
│  Description (1-2 lines)│
│  "Open →" (on hover)    │
└─────────────────────────┘
```

**Specifications:**
- **Image**: 
  - Height: ~192px (h-48)
  - Object-fit: cover
  - Gradient overlay: `from-black/40 via-black/10 to-transparent`
  - Hover: subtle zoom effect (scale-105)
- **Tag**: 
  - Position: absolute top-right
  - Style: `bg-white/95 backdrop-blur-sm px-3 py-1 rounded-full`
  - Font size: xs
- **Card Container**:
  - Border radius: `rounded-2xl`
  - Shadow: `shadow-sm` default, `shadow-lg` on hover
  - Background: white/card color
  - Hover: lift up slightly (`-translate-y-1`)
  - Transition: smooth 300ms
- **Content Padding**: `p-5`
- **"Open →" indicator**: 
  - Hidden by default (`opacity-0`)
  - Visible on hover (`group-hover:opacity-100`)
  - Uses arrow-right icon

**Interactive States:**
- Entire card is clickable
- Hover effects:
  - Card lifts and gains stronger shadow
  - Image zooms subtly
  - "Open →" indicator appears

### Sidebar Component

**Sections:**
1. **Recommended** (top)
2. **Popular Topics** (bottom)

**Each Section:**
- Container: `bg-card rounded-2xl p-5 shadow-sm`
- Title: h3, margin-bottom
- Spacing between sections: `space-y-6`

**Recommended Items:**
- Layout: Horizontal flex with thumbnail
- Thumbnail: `w-16 h-16 rounded-lg` (left side)
- Content: Title (2-line clamp) + small tag
- Hover: subtle background change (`hover:bg-accent/50`)

**Popular Topics:**
- Simple text list
- Each item: `px-3 py-2 rounded-lg`
- Hover: `hover:bg-accent/50`

**Positioning:**
- Desktop: `sticky top-6` (stays in view on scroll)
- Hidden on mobile: `hidden lg:block`

### Search Bar

**Specifications:**
- Width: `max-w-xl`
- Padding: `pl-12 pr-4 py-3`
- Border radius: `rounded-full`
- Background: white
- Border: subtle (`border-border`)
- Focus state: ring effect (`focus:ring-2 focus:ring-ring/20`)
- Icon: positioned absolute, left side, muted color

### Category Filter Pills

**Layout:**
- Horizontal flex wrap: `flex flex-wrap gap-2`

**Individual Pill:**
- Padding: `px-4 py-2`
- Border radius: `rounded-full`
- Active state:
  - Background: `bg-primary`
  - Text: `text-primary-foreground`
- Inactive state:
  - Background: white
  - Border: `border-border`
  - Hover: `hover:bg-accent`

---

## Topic Detail Page

### Structure
```
[Back Button]
[Title]
[Description]

Materials
├─ [Material Item 1]
├─ [Material Item 2]
├─ [Material Item 3]
└─ [Material Item 4]
```

### Header
- **Back Button**: 
  - Arrow left icon + text
  - Color: muted, hover to foreground
  - Margin bottom: `mb-6`
- **Title**: h1, `mb-3`
- **Description**: Paragraph, muted color, max-width `max-w-2xl`

### Material List

**Container:**
- Section title "Materials": h2, `mb-6`
- Items: vertical stack with `space-y-3`

**Material Item Card:**
```
┌────────────────────────────────────────┐
│ [Icon]  Title                  [Arrow] │
│         [Type Badge] [Duration]        │
│         Description                    │
└────────────────────────────────────────┐
```

**Specifications:**
- Layout: `flex items-start gap-4`
- Padding: `p-5`
- Background: card color
- Border radius: `rounded-xl`
- Border: transparent default, visible on hover
- Hover: shadow increase, arrow moves right

**Icon Area:**
- Size: `w-12 h-12`
- Background: `bg-accent`
- Border radius: `rounded-lg`
- Icon types:
  - Video → PlayCircle
  - Document → FileText
  - Activity → Sparkles
  - Template → FileCheck

**Content:**
- Title: h4 (medium weight)
- Badge: `bg-muted px-2 py-1 rounded-md text-xs`
- Duration: optional, muted, xs
- Description: text-sm, muted color

**Arrow Indicator:**
- Right side, aligned with title
- Hover: translate right (`group-hover:translate-x-1`)
- Color: muted default, foreground on hover

---

## Color Palette

**Use theme tokens:**
- Background: `bg-[#fafafa]` or `bg-background`
- Card: `bg-card` (white)
- Text: `text-foreground` (dark)
- Muted text: `text-muted-foreground`
- Primary: `bg-primary` / `text-primary`
- Accent: `bg-accent` (light gray)
- Border: `border-border` (subtle)

**Shadows:**
- Default: `shadow-sm`
- Hover: `shadow-md` or `shadow-lg`

---

## Typography

**Use default HTML element styles:**
- h1: Largest, medium weight
- h2: Section headers
- h3: Card/section titles
- h4: Item titles
- p: Body text, normal weight

**Text sizing:**
- Small: `text-sm`
- Extra small: `text-xs`
- Default: base (from theme)

---

## Spacing & Layout

**Container:**
- Max width: `max-w-7xl mx-auto`
- Padding: `px-6 py-10`

**Grid:**
- Main content: `grid-cols-1 md:grid-cols-2 gap-6` (topic cards)
- Layout: `grid-cols-1 lg:grid-cols-[1fr_320px] gap-8` (main + sidebar)

**Spacing scales:**
- Tight: `gap-2` or `space-y-2`
- Normal: `gap-4` or `space-y-4`
- Generous: `gap-6` or `space-y-6`
- Section spacing: `mb-8`, `mb-10`

---

## Interaction & Animation

### Transitions
- Duration: 300ms (cards), 500ms (images)
- Easing: default ease

### Hover Effects
**Cards:**
- Lift: `hover:-translate-y-1`
- Shadow increase
- Image zoom: `group-hover:scale-105`

**Buttons/Pills:**
- Background color change
- Smooth transition

**Material Items:**
- Border visibility
- Shadow increase
- Arrow movement

### States
- Default: clean, minimal
- Hover: enhanced, interactive
- Active (filters): filled, distinct
- Focus: ring effect on inputs

---

## Data Structure

### Topic Object
```typescript
{
  id: string
  title: string
  description: string
  image: string (URL)
  tag: string (e.g., "Video", "Activity", "Document")
  category: "Community" | "Children"
  materials: Material[]
}
```

### Material Object
```typescript
{
  title: string
  type: "Video" | "Document" | "Activity" | "Template"
  description: string
  duration?: string (optional)
}
```

---

## Content Categories

### Community Learning
- Planting & Gardening
- Rag Making & Upcycling
- Livelihood Starter Skills

### Children's Learning
- Reading & Phonics
- Math Basics
- Creative Activities
- Values & Social Skills

---

## Image Guidelines

**Use:**
- Warm, soft photography (real-life learning scenes)
- OR consistent modern illustrations (pick one style)
- High quality, relevant to topic
- Aspect ratio: landscape (approximately 3:2)

**Sources:**
- Unsplash for photography
- Illustration libraries for consistent style

**Avoid:**
- Mixing photography and illustrations
- Stock photos that feel generic
- Low quality or pixelated images
- Inconsistent visual styles

---

## Responsive Behavior

**Desktop (lg+):**
- Two-column layout with sidebar
- Cards in 2-column grid
- Sidebar sticky

**Tablet (md):**
- Topic cards: 2 columns
- Sidebar hidden or moved to bottom

**Mobile:**
- Single column stack
- Full-width cards
- Condensed spacing
- Sidebar content integrated or hidden

---

## User Experience Goals

The interface should feel:
- **Calm** - not overwhelming
- **Scannable** - easy to browse
- **Engaging** - visually interesting
- **Focused** - on exploration and discovery
- **Professional** - modern SaaS quality
- **Inviting** - like a curated library

---

## Implementation Notes

**Components to create:**
1. `TopicCard.tsx` - Reusable topic card component
2. `Sidebar.tsx` - Recommended and popular sections
3. `TopicDetail.tsx` - Detail page view
4. `App.tsx` - Main hub with state management

**Key libraries:**
- React (state management)
- Tailwind CSS (styling)
- Lucide React (icons)

**State management:**
- Selected category filter
- Search query
- Selected topic (for detail view)
- Filter/search logic

---

## Example Use Cases

**User Journey 1: Browse by Category**
1. User arrives at Learning Hub
2. Clicks "Community" filter pill
3. Sees filtered topic cards
4. Clicks on "Planting & Gardening" card
5. Views materials list
6. Clicks "Back to Learning Hub"

**User Journey 2: Search**
1. User types "reading" in search
2. Results filter in real-time
3. Clicks on result
4. Explores materials

**User Journey 3: Recommended**
1. User sees sidebar recommendations
2. Clicks on recommended item
3. Navigates to that topic

---

## Quality Checklist

Before shipping, ensure:
- [ ] All images load and are high quality
- [ ] Hover effects work smoothly
- [ ] Responsive on mobile, tablet, desktop
- [ ] Search filters correctly
- [ ] Category pills update state
- [ ] Navigation to detail page works
- [ ] Back button returns to hub
- [ ] No layout shift on hover
- [ ] Consistent spacing throughout
- [ ] Typography hierarchy is clear
- [ ] Colors follow theme tokens
- [ ] Interactive elements have feedback
- [ ] Empty states are handled (no results)
- [ ] Sidebar is sticky on desktop
- [ ] Cards are fully clickable

---

## Future Enhancements (Optional)

- Pagination or infinite scroll for many topics
- Recently viewed persistence (localStorage)
- Bookmarking/favorites
- User progress (if needed, but minimal)
- Filter by material type
- Sort options (newest, popular, alphabetical)
- Topic tags/keywords for better filtering
- Print/download materials
- Share functionality

---

## Design Philosophy

> "Create a polished, modern learning experience that feels like a curated digital library rather than a feature-heavy dashboard. Every element should serve the goal of helping users discover and explore learning materials in a calm, inviting environment."

Focus on **content discovery**, not **progress tracking**.
Focus on **visual clarity**, not **feature density**.
Focus on **exploration**, not **completion**.
