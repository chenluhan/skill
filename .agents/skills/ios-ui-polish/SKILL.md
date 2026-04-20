---
name: ios-ui-polish
description: Use when working on BabyWhisper or similar iOS product surfaces that need stronger hierarchy, warmer visual language, clearer CTA placement, better single-hand flows, and more intentional motion. Apply during SwiftUI page reviews, UI refinements, interaction audits, and design-to-code cleanups.
---

# iOS UI Polish

Use this skill when the task is to improve the feel, clarity, or beauty of an iOS interface rather than to add backend logic.

## Goals

- Make the primary action visually undeniable.
- Reduce tap count and hesitation, especially for one-handed use.
- Preserve a warm, premium, non-cartoon tone.
- Keep screens clear at night and under tired-parent usage conditions.

## Review Order

1. Find the single most important action on the screen.
2. Check whether the action is visible without scrolling and reachable by the thumb.
3. Check whether visual weight matches product importance.
4. Check whether the page explains itself in under five seconds.
5. Tighten spacing, type contrast, and state feedback only after hierarchy is correct.

## BabyWhisper-Specific Rules

- The voice CTA is the product signature. It must sit above normal navigation weight.
- Distinguish tap and long-press behaviors with copy, motion, and state change.
- Avoid childish mother-baby tropes. Prefer soft premium warmth over cartoon decoration.
- Use cards, gradients, and shadows sparingly; emphasis should come from hierarchy, not clutter.
- Numeric outcomes such as `150ml`, `7.4kg`, and `2h 10m` should read faster than supporting labels.

## Interaction Checklist

- Is the main CTA reachable with one hand on large phones?
- Is accidental activation unlikely?
- Does long press have an obvious live state?
- Does cancel behavior feel safe and reversible?
- Are high-frequency tasks fewer than three taps away?
- Does any modal open with a clear next step?

## Motion Rules

- Use one strong motion for the primary CTA and lighter transitions elsewhere.
- Recording state should add scale, glow, and a darker backdrop.
- Processing should feel calm, not urgent.
- Confirmation should bias toward trust and reversibility.

## Accessibility Baseline

- Maintain clear contrast on soft backgrounds.
- Avoid conveying meaning with color alone.
- Provide explicit accessibility labels and hints for custom controls.
- Keep critical copy concise for VoiceOver.

## Output Style

- Give concrete UI changes, not vague taste opinions.
- Prioritize hierarchy, reachability, and task clarity before decoration.
- When reviewing a screen, return: `what is weak`, `what to change`, `why it matters`.
