# nss-platform — Agent Knowledge Base

Initialized: 2026-06-29 16:52:58 UTC

## Summary
Stack: Java
Files: 21, Lines: 4350
Tests detected: 0
CI configs: .github/workflows/ci.yml

## Key Facts

## Shipped Features

## File Tree
```
    ci.yml  (109 lines)
CODEOWNERS  (1 lines)
Dockerfile  (47 lines)
README.md  (171 lines)
docker-compose.yml  (44 lines)
  README.md  (16 lines)
  eslint.config.js  (21 lines)
  index.html  (44 lines)
  package-lock.json  (2802 lines)
  package.json  (31 lines)
    National_Service_Scheme_logo.svg  (153 lines)
    favicon.svg  (1 lines)
    icons.svg  (24 lines)
    App.css  (184 lines)
    App.jsx  (105 lines)
    api.js  (61 lines)
    index.css  (289 lines)
    main.jsx  (10 lines)
  vite.config.js  (18 lines)
pom.xml  (192 lines)
render.yaml  (27 lines)
```

## Lint Baseline
[INFO] Scanning for projects...
Downloading from central: https://repo.maven.apache.org/maven2/org/springframework/boot/spring-boot-starter-parent/3.2.5/spring-boot-starter-parent-3.2.5.pom
Progress (1): 1.1 kB
Progress (1): 2.5 kB
Progress (1): 6.6 kB
Progress (1): 10 kB 
Progress (1): 13 kB
                   
Downloaded from central: https://repo.maven.apache.org/maven2/org/springframework/boot/spring-boot-starter-parent/3.2.5/spring-boot-starter-parent-3.2.5.pom (13 kB at 42 kB/s)
Downloading from central: https://repo.maven.apache.org/maven2/org/springframework/boot/spring-boot-dependencies/3.2.5/spring-boot-dependencies-3.2.5.pom
Progress (1): 995 B
Progress (1): 2.2 kB
Progress (1): 4.4 kB
Progress (1): 6.5 kB
Progress (1): 8.2 kB
Progress (1): 11 kB 
Progress (1): 16 kB
Progress (1): 23 kB
Progress (1): 31 kB
Progress (1): 40 kB
Progress (1): 45 kB
Progress (1): 54 kB
Progress (1): 64 kB
Progress (1): 72 kB
Progress (1): 84 kB
Progress (1): 93 kB
Progress (1): 97 kB
Progress (1

## Key Files

### README.md
```
# NSS VIIT Pune — Event Polling & Blood Donation Platform
  
  [![Java](https://img.shields.io/badge/Java-17-orange?logo=openjdk)](https://www.java.com/)
  [![Spring Boot](https://img.shields.io/badge/Spring_Boot-3.2-brightgreen?logo=spring)](https://spring.io/)
  [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)](https://www.postgresql.org/)
  [![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev/)
  [![License](https://img.shields.io/badge/Lice
```

### .gitignore
```
# ============================================================
  # .gitignore — NSS VIIT Pune Platform
  # Nothing sensitive leaves this machine.
  # ============================================================
  
  # ── Secrets & Credentials ───────────────────────────────────
  .env
  .env.*
  !.env.example          # only the template is safe to commit
  *.pem
  *.key
  *.p12
  *.jks
  *.pfx
  *.keystore
  *.truststore
  application-local.yml
  application-local.yaml
  application-secrets.yml
  secrets/
  credentials/
  
  # ── Java / 
```

### docker-compose.yml
```
services:
    db:
      image: postgres:16-alpine
      environment:
        POSTGRES_DB: nssdb
        POSTGRES_USER: postgres
        POSTGRES_PASSWORD: postgres
      ports:
        - "5432:5432"
      volumes:
        - pgdata:/var/lib/postgresql/data
      healthcheck:
        test: ["CMD-SHELL", "pg_isready -U postgres"]
        interval: 5s
        timeout: 5s
        retries: 5
  
    mailpit:
      image: axllent/mailpit:latest
      ports:
        - "1025:1025"
        - "8025:8025"
      restart: unless-stopped
  
    app:
      buil
```

### pom.xml
```
<?xml version="1.0" encoding="UTF-8"?>
  <project xmlns="http://maven.apache.org/POM/4.0.0"
           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
           xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
      <modelVersion>4.0.0</modelVersion>
  
      <parent>
          <groupId>org.springframework.boot</groupId>
          <artifactId>spring-boot-starter-parent</artifactId>
          <version>3.2.5</version>
          <relativePath/>
      </parent>
  
   
```

## Archived Suggestions
