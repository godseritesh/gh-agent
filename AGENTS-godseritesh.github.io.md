# godseritesh.github.io — Agent Knowledge Base

Initialized: 2026-06-29 16:53:17 UTC

## Summary
Stack: Node.js
Files: 70, Lines: 27881
Tests detected: 1
CI configs: .github/workflows/lighthouse.yml, .github/workflows/deploy.yml, .github/workflows/ci.yml

## Key Facts

## Shipped Features

## File Tree
```
    ci.yml  (78 lines)
    deploy.yml  (53 lines)
    lighthouse.yml  (49 lines)
CODEOWNERS  (1 lines)
CONTRIBUTING.md  (206 lines)
DEPLOY.md  (62 lines)
LICENSE  (21 lines)
README.md  (348 lines)
    motion-BLm2Cfqc.js  (1 lines)
    react-vendor-BJsMWidF.js  (1 lines)
  geeksforgeeks.svg  (1 lines)
  hackerearth.svg  (11 lines)
  index.html  (86 lines)
  leetcode.svg  (54 lines)
  photo.png  (4507 lines)
  robots.txt  (13 lines)
  sitemap.xml  (27 lines)
index.html  (81 lines)
jest.config.cjs  (20 lines)
package-lock.json  (8409 lines)
package.json  (60 lines)
photo.png  (4507 lines)
postcss.config.cjs  (6 lines)
  geeksforgeeks.svg  (1 lines)
  hackerearth.svg  (11 lines)
  leetcode.svg  (54 lines)
    3d-poster.svg  (8 lines)
    README.md  (11 lines)
  photo.avif  (225 lines)
  photo.png  (4507 lines)
  photo.webp  (418 lines)
  robots.txt  (13 lines)
  sitemap.xml  (27 lines)
resume.json  (96 lines)
  optimize-images.js  (57 lines)
  App.tsx  (35 lines)
    Animations.tsx  (150 lines)
    Cursor.tsx  (69 lines)
    Footer.tsx  (144 lines)
    JourneyTimeline.tsx  (220 lines)
    LifelineRunner.tsx  (255 lines)
    MagicalCursor.tsx  (15 lines)
    Navbar.tsx  (114 lines)
    ParallaxSection.tsx  (39 lines)
    ProjectModal.tsx  (152 lines)
    ResponsiveImage.tsx  (36 lines)
    RevealPeekWrapper.tsx  (58 lines)
    ScrollRevealWrapper.tsx  (48 lines)
    ThreeDemo.tsx  (46 lines)
    portfolio.ts  (260 lines)
    resumeLoader.ts  (174 lines)
    index.ts  (57 lines)
    useMagicalCursor.ts  (170 lines)
    useParallax.ts  (32 lines)
    useRevealPeek.ts  (36 lines)
    useScrollReveal.ts  (49 lines)
  index.css  (77 lines)
  main.tsx  (33 lines)
    About.tsx  (214 lines)
    Certifications.tsx  (153 lines)
    Contact.tsx  (296 lines)
    Home.tsx  (238 lines)
    Journey.tsx  (322 lines)
    Projects.tsx  (126 lines)
  setupTests.ts  (15 lines)
    helpers.ts  (58 lines)
tailwind.config.ts  (70 lines)
tsconfig.json  (31 lines)
tsconfig.node.json  (10 lines)
```

## Lint Baseline

> ritesh-portfolio@1.0.0 lint
> eslint . --ext .ts,.tsx

sh: 1: eslint: not found


## Key Files

### README.md
```
# Ritesh Godse - Portfolio Website
  
  A production-quality, fully responsive portfolio website built with React, Vite, TypeScript, and Tailwind CSS. Showcasing backend engineering expertise and AI enthusiasm with interactive components, smooth animations, and optimized performance.
  
  ![React](https://img.shields.io/badge/React-18.2-blue)
  ![Vite](https://img.shields.io/badge/Vite-5.0-646cff)
  ![TypeScript](https://img.shields.io/badge/TypeScript-5.3-3178c6)
  ![Tailwind CSS](https://img.shields.io/badg
```

### CONTRIBUTING.md
```
# Contributing to Ritesh Godse's Portfolio
  
  Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.
  
  ## Code of Conduct
  
  - Be respectful and inclusive
  - Provide constructive feedback
  - Focus on the code, not the person
  - Help others learn and grow
  
  ## How to Contribute
  
  ### Reporting Bugs
  
  Before creating a bug report:
  - Check existing issues to avoid duplicates
  - Provide a clear, descriptive title
  - Include steps to repro
```

### .gitignore
```
.DS_Store
  .env.local
  .env.development.local
  .env.test.local
  .env.production.local
  
  npm-debug.log*
  yarn-debug.log*
  yarn-error.log*
  
  node_modules/
  dist/
  build/
  .next/
  
  # IDE
  .vscode/
  .idea/
  *.swp
  *.swo
  *~
  
  # OS
  Thumbs.db
  
  # Testing
  coverage/
  .nyc_output/
  
  # Build artifacts
  *.tsbuildinfo
  
  # Dependencies
  pnpm-lock.yaml
  yarn.lock
  
```

### package.json
```
{
    "name": "ritesh-portfolio",
    "private": true,
    "version": "1.0.0",
    "type": "module",
    "description": "Portfolio website for Ritesh Godse - Backend Engineer & AI Enthusiast",
    "author": "Ritesh Godse",
    "homepage": "https://godseritesh.github.io/",
    "repository": {
      "type": "git",
      "url": "https://github.com/godseritesh/portfolio.git"
    },
    "scripts": {
      "dev": "vite",
      "build": "tsc --noEmit && vite build",
      "preview": "vite preview",
      "optimize-images": "node scri
```

## Archived Suggestions
