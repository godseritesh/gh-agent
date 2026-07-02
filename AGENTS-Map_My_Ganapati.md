# Map_My_Ganapati — Agent Knowledge Base

Initialized: 2026-06-29 16:53:05 UTC

## Summary
Stack: Node.js
Files: 33, Lines: 16830
Tests detected: 0
CI configs: .github/workflows/ci.yml

## Key Facts

## Shipped Features

## File Tree
```
    ci.yml  (81 lines)
CODEOWNERS  (1 lines)
README.md  (347 lines)
next.config.js  (21 lines)
package-lock.json  (6359 lines)
package.json  (37 lines)
postcss.config.js  (6 lines)
  manifest.json  (26 lines)
    img1.png  (6660 lines)
    marker-icon-2x.png  (1 lines)
    marker-icon.png  (1 lines)
    marker-shadow.png  (1 lines)
  fetchGoogleData.ts  (170 lines)
  seedData.ts  (70 lines)
  setupDatabase.ts  (69 lines)
  tsconfig.json  (12 lines)
    globals.css  (31 lines)
    layout.tsx  (40 lines)
    page.tsx  (329 lines)
    CrowdSummary.tsx  (136 lines)
    Header.tsx  (147 lines)
    Map.tsx  (432 lines)
    SimpleLocationButton.tsx  (231 lines)
    SuggestionPanel.tsx  (554 lines)
    crowdService.ts  (230 lines)
    googlePlacesService.ts  (198 lines)
    pandalService.ts  (217 lines)
    routeOptimizer.ts  (259 lines)
    supabase.ts  (24 lines)
    pandal.ts  (57 lines)
tailwind.config.ts  (28 lines)
tsconfig.json  (28 lines)
vercel.json  (27 lines)
```

## Lint Baseline

> map-my-ganapati@0.1.0 lint
> next lint

sh: 1: next: not found


## Key Files

### README.md
```
<p align="center">
    <img src="public/markers/img1.png" alt="marker" width="300" height="300"/>
  </p>
  
  A modern navigation app to help devotees find and navigate to Ganapati pandals during the festival. Built with Next.js, Supabase, and Leaflet.js.
  
  
  
  ## 🚀 Features
  
  - **Interactive Map**: View all Ganapati pandals on an interactive OpenStreetMap
  - **Location-based Search**: Find pandals near your current location
  - **Detailed Information**: View pandal details, timings, contact info, and special 
```

### .gitignore
```
# Dependencies
  /node_modules
  /.pnp
  .pnp.js
  
  # Testing
  /coverage
  
  # Next.js
  /.next/
  /out/
  
  # Production
  /build
  
  # Misc
  .DS_Store
  *.pem
  
  # Debug
  npm-debug.log*
  yarn-debug.log*
  yarn-error.log*
  
  # Local env files
  .env*.local
  .env
  
  # Vercel
  .vercel
  
  # TypeScript
  *.tsbuildinfo
  next-env.d.ts
  
  # Firebase
  .firebase/
  firebase-debug.log
  firestore-debug.log
  
  # IDE
  .vscode/
  .idea/
  *.swp
  *.swo
  
  # OS
  Thumbs.db
  .vercel
  
```

### package.json
```
{
    "name": "map-my-ganapati",
    "version": "0.1.0",
    "private": true,
    "scripts": {
      "dev": "next dev",
      "build": "next build",
      "start": "next start",
      "lint": "next lint",
      "seed": "npx ts-node --project scripts/tsconfig.json scripts/seedData.ts",
      "setup-db": "npx ts-node --project scripts/tsconfig.json scripts/setupDatabase.ts",
      "fetch-google": "npx ts-node --project scripts/tsconfig.json scripts/fetchGoogleData.ts"
    },
    "dependencies": {
      "@supabase/supabase-js
```

## Archived Suggestions
