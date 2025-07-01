# pxy6.com

A React application built with Vite and TypeScript that integrates with app.pxy6.com for backend services.

## Technologies

- **Frontend**: React 18, TypeScript, Vite
- **UI Framework**: Tailwind CSS, shadcn/ui components
- **Backend**: API integration with app.pxy6.com (Remix application)
- **Testing**: Jest, Playwright
- **Build**: Vite with hot module reloading

## Development Setup

### Prerequisites

- Node.js 18+ and npm
- Git

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd pxy6.com

# Install dependencies
npm install

# Set up the database
npm run setup
```

## Available Scripts

### Development Commands

```bash
# Start development server with type checking and hot reload
npm run dev

# Start development server in Docker container
npm run docker:dev
```

### Build Commands

```bash
# Build for production
npm run build

# Build for development (with source maps)
npm run build:dev

# Preview production build locally
npm run preview
```

### API Integration

This application uses app.pxy6.com as its backend API for data operations. No local database setup is required.

### Testing Commands

```bash
# Run unit tests
npm run test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage report
npm run test:coverage

# Run end-to-end tests
npm run test:e2e

# Run e2e tests with UI
npm run test:e2e:ui

# Debug e2e tests
npm run test:e2e:debug
```

### Code Quality Commands

```bash
# Run TypeScript type checking
npm run typecheck

# Run ESLint
npm run lint
```

### Docker Commands

```bash
# Build Docker image
npm run docker:build

# Run Docker container
npm run docker:run

# Start development environment with Docker Compose
npm run docker:dev

# Stop Docker Compose services
npm run docker:down
```

## API Configuration

### Local Development
- Uses app.pxy6.com running on `http://localhost:3000`
- Set `API_BASE_URL=http://localhost:3000` in `.env.local`

### Production
- Connects to app.pxy6.com backend service
- Environment variable: `API_BASE_URL=http://app_pxy6_com:3000`

### Available API Endpoints

The application integrates with the following app.pxy6.com endpoints:

- **POST /api/waitlist**: Submit waitlist email with source tracking
- **POST /api/follow-up**: Submit additional user information from follow-up forms
- **POST /api/loi-click**: Track letter of intent clicks

## Environment Variables

### Development
- `API_BASE_URL`: API base URL (default: `http://localhost:3000`)

### Production
- `API_BASE_URL`: API base URL for app.pxy6.com backend
- `NODE_ENV`: Set to `production`

## Project Structure

```
src/
├── components/          # React components
├── services/           # API integration and business logic
└── ...
```

## Development Workflow

1. Start development server: `npm run dev`
2. Make changes to code
3. Run type checking: `npm run typecheck`
4. Run tests: `npm run test`
5. Build for production: `npm run build`

## Deployment

The application is configured for containerized deployment:

1. Build Docker image: `npm run docker:build`
2. Deploy with app.pxy6.com backend service connection
3. Ensure app.pxy6.com is running and accessible

## Testing

- **Unit Tests**: Jest with React Testing Library
- **E2E Tests**: Playwright for browser automation
- **Type Checking**: TypeScript compiler
- **Linting**: ESLint with React and TypeScript rules

## Support

For issues and questions, refer to the project documentation or contact the development team.