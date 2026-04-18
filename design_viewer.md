## Design System: Sharp GUI Image Viewer

### Pattern
- **Name:** Hero + Features + CTA
- **Conversion Focus:** Deep CTA placement. Use contrasting color (at least 7:1 contrast ratio). Sticky navbar CTA.
- **CTA Placement:** Hero (sticky) + Bottom
- **Color Strategy:** Hero: Brand primary or vibrant. Features: Card bg #FAFAFA. CTA: Contrasting accent color
- **Sections:** 1. Hero with headline/image, 2. Value prop, 3. Key features (3-5), 4. CTA section, 5. Footer

### Style
- **Name:** Liquid Glass
- **Keywords:** Flowing glass, morphing, smooth transitions, fluid effects, translucent, animated blur, iridescent, chromatic aberration
- **Best For:** Premium SaaS, high-end e-commerce, creative platforms, branding experiences, luxury portfolios
- **Performance:** ⚠ Moderate-Poor | **Accessibility:** ⚠ Text contrast

### Colors
| Role | Hex |
|------|-----|
| Primary | #DB2777 |
| Secondary | #F472B6 |
| CTA | #CA8A04 |
| Background | #FDF2F8 |
| Text | #831843 |

*Notes: Romantic pink + elegant gold*

### Typography
- **Heading:** Playfair Display
- **Body:** Inter
- **Mood:** elegant, luxury, sophisticated, timeless, premium, editorial
- **Best For:** Luxury brands, fashion, spa, beauty, editorial, magazines, high-end e-commerce
- **Google Fonts:** https://fonts.google.com/share?selection.family=Inter:wght@300;400;500;600;700|Playfair+Display:wght@400;500;600;700
- **CSS Import:**
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Playfair+Display:wght@400;500;600;700&display=swap');
```

### Key Effects
Morphing elements (SVG/CSS), fluid animations (400-600ms curves), dynamic blur (backdrop-filter), color transitions

### Avoid (Anti-patterns)
- Cheap visuals
- Fast animations

### Pre-Delivery Checklist
- [ ] No emojis as icons (use SVG: Heroicons/Lucide)
- [ ] cursor-pointer on all clickable elements
- [ ] Hover states with smooth transitions (150-300ms)
- [ ] Light mode: text contrast 4.5:1 minimum
- [ ] Focus states visible for keyboard nav
- [ ] prefers-reduced-motion respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px

