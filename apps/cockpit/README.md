# Enterprise DNA Cockpit

Next.js management interface for the Enterprise DNA platform.

## Features

- **Objects Management**: Browse and filter golden business objects by type
- **Object Details**: View detailed information about objects including sources and attributes
- **Scanner Status**: Monitor scanner run status and results

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- API Gateway running on http://localhost:8000

### Installation

```bash
cd apps/cockpit
npm install
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Configuration

Create a `.env.local` file:

```bash
NEXT_PUBLIC_API_GATEWAY_URL=http://localhost:8000
```

### Build

```bash
npm run build
npm start
```

## Routes

- `/` - Home page with navigation
- `/objects` - List all objects with type filter
- `/objects/[id]` - Object detail page with sources
- `/scans` - Scanner status and latest run information

## Tech Stack

- Next.js 14 (App Router)
- React 18
- TypeScript
- Tailwind CSS

