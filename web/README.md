# Narralytica Web

This is a design-first frontend scaffold for the Narralytica dashboard.

## Why it exists

The engine is still being evaluated, but the website can be designed in parallel so the frontend contract becomes clearer before the backend is frozen.

Right now this app:

- is deployable on Vercel
- uses local mock data only
- does not make live API calls
- helps shape what the website-facing JSON should eventually look like

## Local development

Install dependencies and run:

```bash
npm install
npm run dev
```

Then open `http://localhost:3000`.

## Vercel

Recommended deployment setup:

- import the repo into Vercel
- set the root directory to `web`
- framework preset should detect `Next.js`

## Current structure

- `app/page.tsx`
  dashboard homepage
- `app/globals.css`
  visual system and layout
- `lib/mock-dashboard.ts`
  local design-time data

## Later integration plan

When the engine is stable, replace the mock layer with the actual website-facing JSON contract, most likely based on `signal_story.json` and snapshot history.
